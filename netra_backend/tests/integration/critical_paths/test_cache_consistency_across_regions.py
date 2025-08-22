"""Cache Consistency Across Regions - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise tier (multi-region deployments for global customers)
- Business Goal: Ensure cache consistency across geographic regions for global operations
- Value Impact: Maintains data consistency for global users, supports multi-region deployments
- Strategic Impact: $12K MRR protection through reliable global cache consistency and enterprise readiness

Critical Path: Multi-region cache sync -> Consistency validation -> Conflict resolution -> Performance verification
L3 Realism: Real Redis instances simulating different regions, actual sync mechanisms, consistency protocols
Performance Requirements: Sync latency < 200ms, consistency accuracy 99.9%, conflict resolution < 500ms
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import logging
import random
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest
import redis.asyncio as aioredis

from netra_backend.app.logging_config import central_logger

from netra_backend.tests.integration.critical_paths.integration.helpers.redis_l3_helpers import (
    RedisContainer as NetraRedisContainer,
)

logger = central_logger.get_logger(__name__)

@dataclass
class RegionalConsistencyMetrics:
    """Metrics for regional cache consistency testing."""
    sync_operations: int = 0
    sync_latencies: List[float] = None
    consistency_checks: int = 0
    consistency_violations: int = 0
    conflict_resolutions: int = 0
    conflict_resolution_times: List[float] = None
    regional_operations: Dict[str, int] = None
    cross_region_reads: int = 0
    cross_region_hits: int = 0
    
    def __post_init__(self):
        if self.sync_latencies is None:
            self.sync_latencies = []
        if self.conflict_resolution_times is None:
            self.conflict_resolution_times = []
        if self.regional_operations is None:
            self.regional_operations = {}
    
    @property
    def avg_sync_latency(self) -> float:
        """Calculate average sync latency."""
        return statistics.mean(self.sync_latencies) if self.sync_latencies else 0.0
    
    @property
    def consistency_rate(self) -> float:
        """Calculate consistency accuracy rate."""
        if self.consistency_checks == 0:
            return 100.0
        return ((self.consistency_checks - self.consistency_violations) / self.consistency_checks) * 100.0
    
    @property
    def avg_conflict_resolution_time(self) -> float:
        """Calculate average conflict resolution time."""
        return statistics.mean(self.conflict_resolution_times) if self.conflict_resolution_times else 0.0
    
    @property
    def cross_region_hit_rate(self) -> float:
        """Calculate cross-region cache hit rate."""
        if self.cross_region_reads == 0:
            return 100.0
        return (self.cross_region_hits / self.cross_region_reads) * 100.0

class CacheConsistencyAcrossRegionsL3Manager:
    """L3 cache consistency across regions test manager with simulated regional Redis instances."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.metrics = RegionalConsistencyMetrics()
        self.test_keys = set()
        self.regions = ["us-east", "us-west", "eu-west", "asia-pacific"]
        self.region_data = {}
        
    async def setup_multi_region_redis(self) -> Dict[str, str]:
        """Setup Redis instances simulating different geographic regions."""
        redis_urls = {}
        base_port = 6430
        
        for region in self.regions:
            try:
                container = NetraRedisContainer(port=base_port)
                container.container_name = f"netra-region-{region}-{uuid.uuid4().hex[:8]}"
                
                url = await container.start()
                
                self.redis_containers[region] = container
                redis_urls[region] = url
                
                # Create Redis client
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                self.redis_clients[region] = client
                
                # Initialize region metadata
                self.region_data[region] = {
                    "url": url,
                    "latency_simulation": self._get_region_latency(region),
                    "operations": 0
                }
                
                logger.info(f"Regional Redis {region} started: {url}")
                base_port += 1
                
            except Exception as e:
                logger.error(f"Failed to start Redis for region {region}: {e}")
                raise
        
        return redis_urls
    
    def _get_region_latency(self, region: str) -> float:
        """Get simulated network latency for region."""
        # Simulate realistic network latencies between regions
        latencies = {
            "us-east": 0.005,    # 5ms base latency
            "us-west": 0.010,    # 10ms cross-US latency
            "eu-west": 0.080,    # 80ms transatlantic latency
            "asia-pacific": 0.150  # 150ms trans-pacific latency
        }
        return latencies.get(region, 0.020)
    
    async def simulate_network_latency(self, source_region: str, target_region: str) -> None:
        """Simulate network latency between regions."""
        if source_region == target_region:
            return  # No latency for same region
        
        base_latency = self.region_data[target_region]["latency_simulation"]
        # Add some jitter
        actual_latency = base_latency + random.uniform(0, base_latency * 0.2)
        await asyncio.sleep(actual_latency)
    
    async def write_to_region(self, region: str, key: str, value: Dict[str, Any], ttl: int = 3600) -> bool:
        """Write data to specific region with metadata."""
        try:
            client = self.redis_clients[region]
            
            # Add regional metadata
            value_with_metadata = {
                **value,
                "region_origin": region,
                "timestamp": datetime.utcnow().isoformat(),
                "version": value.get("version", 1)
            }
            
            await client.setex(key, ttl, json.dumps(value_with_metadata))
            
            self.region_data[region]["operations"] += 1
            self.metrics.regional_operations[region] = self.metrics.regional_operations.get(region, 0) + 1
            self.test_keys.add(key)
            
            return True
            
        except Exception as e:
            logger.error(f"Write to region {region} failed for key {key}: {e}")
            return False
    
    async def read_from_region(self, region: str, key: str) -> Optional[Dict[str, Any]]:
        """Read data from specific region."""
        try:
            # Simulate network latency
            await self.simulate_network_latency("us-east", region)  # Assume reading from us-east
            
            client = self.redis_clients[region]
            value_str = await client.get(key)
            
            if value_str:
                return json.loads(value_str)
            return None
            
        except Exception as e:
            logger.error(f"Read from region {region} failed for key {key}: {e}")
            return None
    
    async def sync_across_regions(self, key: str, source_region: str, target_regions: List[str] = None) -> Dict[str, Any]:
        """Synchronize cache data across regions."""
        if target_regions is None:
            target_regions = [r for r in self.regions if r != source_region]
        
        start_time = time.time()
        self.metrics.sync_operations += 1
        
        # Read from source region
        source_data = await self.read_from_region(source_region, key)
        if not source_data:
            return {"success": False, "reason": "source_not_found"}
        
        sync_results = {}
        successful_syncs = 0
        failed_syncs = 0
        
        # Sync to target regions
        for target_region in target_regions:
            try:
                # Simulate cross-region network latency
                await self.simulate_network_latency(source_region, target_region)
                
                # Check for conflicts
                existing_data = await self.read_from_region(target_region, key)
                
                if existing_data and existing_data.get("version", 0) > source_data.get("version", 0):
                    # Conflict: target has newer version
                    sync_results[target_region] = {
                        "success": False,
                        "reason": "version_conflict",
                        "existing_version": existing_data.get("version"),
                        "source_version": source_data.get("version")
                    }
                    failed_syncs += 1
                    continue
                
                # Write to target region
                success = await self.write_to_region(target_region, key, source_data)
                
                if success:
                    sync_results[target_region] = {"success": True}
                    successful_syncs += 1
                else:
                    sync_results[target_region] = {"success": False, "reason": "write_failed"}
                    failed_syncs += 1
                    
            except Exception as e:
                sync_results[target_region] = {"success": False, "reason": str(e)}
                failed_syncs += 1
        
        sync_latency = time.time() - start_time
        self.metrics.sync_latencies.append(sync_latency)
        
        return {
            "key": key,
            "source_region": source_region,
            "target_regions": target_regions,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "sync_latency": sync_latency,
            "sync_results": sync_results
        }
    
    async def test_eventual_consistency(self, test_keys_count: int) -> Dict[str, Any]:
        """Test eventual consistency across regions."""
        test_keys = [f"consistency_test_{i}_{uuid.uuid4().hex[:8]}" for i in range(test_keys_count)]
        
        consistency_results = {
            "total_keys": test_keys_count,
            "eventually_consistent": 0,
            "consistency_violations": 0,
            "avg_convergence_time": 0,
            "key_results": {}
        }
        
        convergence_times = []
        
        for key in test_keys:
            # Write initial data to random region
            source_region = random.choice(self.regions)
            initial_data = {
                "data": f"initial_value_{key}",
                "version": 1,
                "test_key": True
            }
            
            await self.write_to_region(source_region, key, initial_data)
            
            # Trigger sync to other regions
            sync_result = await self.sync_across_regions(key, source_region)
            
            # Wait for eventual consistency
            convergence_start = time.time()
            max_wait = 2.0  # 2 seconds max wait
            
            eventually_consistent = False
            while time.time() - convergence_start < max_wait:
                # Check consistency across all regions
                consistent = await self._check_consistency_across_regions(key)
                
                if consistent:
                    convergence_time = time.time() - convergence_start
                    convergence_times.append(convergence_time)
                    consistency_results["eventually_consistent"] += 1
                    eventually_consistent = True
                    break
                
                await asyncio.sleep(0.1)  # Check every 100ms
            
            if not eventually_consistent:
                consistency_results["consistency_violations"] += 1
                logger.warning(f"Key {key} did not achieve eventual consistency")
            
            consistency_results["key_results"][key] = {
                "source_region": source_region,
                "sync_successful": sync_result["successful_syncs"],
                "sync_failed": sync_result["failed_syncs"],
                "eventually_consistent": eventually_consistent
            }
        
        if convergence_times:
            consistency_results["avg_convergence_time"] = statistics.mean(convergence_times)
        
        return consistency_results
    
    async def _check_consistency_across_regions(self, key: str) -> bool:
        """Check if a key is consistent across all regions."""
        values = {}
        
        # Read from all regions
        for region in self.regions:
            value = await self.read_from_region(region, key)
            values[region] = value
        
        # Check if all non-None values are identical
        non_none_values = [v for v in values.values() if v is not None]
        
        if len(non_none_values) == 0:
            return True  # No data anywhere is consistent
        
        # Compare versions and data
        first_value = non_none_values[0]
        
        for value in non_none_values[1:]:
            if (value.get("version") != first_value.get("version") or 
                value.get("data") != first_value.get("data")):
                return False
        
        return True
    
    async def test_conflict_resolution(self, conflict_scenarios: int) -> Dict[str, Any]:
        """Test conflict resolution mechanisms for concurrent updates."""
        conflict_results = {
            "total_scenarios": conflict_scenarios,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "resolution_failures": 0,
            "avg_resolution_time": 0
        }
        
        resolution_times = []
        
        for scenario in range(conflict_scenarios):
            key = f"conflict_test_{scenario}_{uuid.uuid4().hex[:8]}"
            
            # Create concurrent updates in different regions
            region1 = random.choice(self.regions[:2])  # First half of regions
            region2 = random.choice(self.regions[2:])  # Second half of regions
            
            # Write different versions simultaneously
            data1 = {
                "data": f"version_from_{region1}",
                "version": 1,
                "region_origin": region1
            }
            
            data2 = {
                "data": f"version_from_{region2}",
                "version": 1,  # Same version number = conflict
                "region_origin": region2
            }
            
            # Write to both regions simultaneously
            await asyncio.gather(
                self.write_to_region(region1, key, data1),
                self.write_to_region(region2, key, data2)
            )
            
            # Attempt cross-region sync (should detect conflict)
            conflict_start = time.time()
            
            sync_result1 = await self.sync_across_regions(key, region1, [region2])
            sync_result2 = await self.sync_across_regions(key, region2, [region1])
            
            # Check if conflicts were detected
            conflicts_detected = (
                any("conflict" in result.get("reason", "") for result in sync_result1["sync_results"].values()) or
                any("conflict" in result.get("reason", "") for result in sync_result2["sync_results"].values())
            )
            
            if conflicts_detected:
                conflict_results["conflicts_detected"] += 1
                
                # Resolve conflict using "last writer wins" strategy
                resolved = await self._resolve_conflict_last_writer_wins(key, region1, region2)
                
                resolution_time = time.time() - conflict_start
                resolution_times.append(resolution_time)
                self.metrics.conflict_resolution_times.append(resolution_time)
                self.metrics.conflict_resolutions += 1
                
                if resolved:
                    conflict_results["conflicts_resolved"] += 1
                else:
                    conflict_results["resolution_failures"] += 1
        
        if resolution_times:
            conflict_results["avg_resolution_time"] = statistics.mean(resolution_times)
        
        return conflict_results
    
    async def _resolve_conflict_last_writer_wins(self, key: str, region1: str, region2: str) -> bool:
        """Resolve conflict using last-writer-wins strategy."""
        try:
            # Read from both regions
            value1 = await self.read_from_region(region1, key)
            value2 = await self.read_from_region(region2, key)
            
            if not value1 or not value2:
                return False
            
            # Compare timestamps
            timestamp1 = datetime.fromisoformat(value1.get("timestamp", "1970-01-01T00:00:00"))
            timestamp2 = datetime.fromisoformat(value2.get("timestamp", "1970-01-01T00:00:00"))
            
            # Determine winner
            if timestamp1 > timestamp2:
                winner_region = region1
                winner_value = value1
                loser_region = region2
            else:
                winner_region = region2
                winner_value = value2
                loser_region = region1
            
            # Update winner's version and sync to loser
            winner_value["version"] = winner_value.get("version", 1) + 1
            winner_value["conflict_resolved"] = True
            winner_value["resolution_timestamp"] = datetime.utcnow().isoformat()
            
            # Write winning value to both regions
            await asyncio.gather(
                self.write_to_region(winner_region, key, winner_value),
                self.write_to_region(loser_region, key, winner_value)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Conflict resolution failed for key {key}: {e}")
            return False
    
    async def test_cross_region_read_performance(self, read_operations: int) -> Dict[str, Any]:
        """Test performance of cross-region cache reads."""
        # Pre-populate data across regions
        test_keys = []
        for i in range(read_operations // 4):  # Quarter of reads will be hits
            key = f"cross_region_read_{i}_{uuid.uuid4().hex[:8]}"
            region = random.choice(self.regions)
            data = {"data": f"cross_region_data_{i}", "region": region}
            
            await self.write_to_region(region, key, data)
            test_keys.append(key)
        
        # Execute cross-region reads
        read_results = {
            "total_reads": read_operations,
            "cache_hits": 0,
            "cache_misses": 0,
            "read_latencies": [],
            "region_performance": {}
        }
        
        for region in self.regions:
            read_results["region_performance"][region] = {
                "reads": 0,
                "hits": 0,
                "avg_latency": 0
            }
        
        for read_op in range(read_operations):
            # Select random region to read from
            read_region = random.choice(self.regions)
            
            # Select key (some exist, some don't)
            if read_op < len(test_keys):
                key = test_keys[read_op % len(test_keys)]
            else:
                key = f"nonexistent_key_{read_op}"
            
            # Measure read performance
            start_time = time.time()
            value = await self.read_from_region(read_region, key)
            read_latency = time.time() - start_time
            
            read_results["read_latencies"].append(read_latency)
            read_results["region_performance"][read_region]["reads"] += 1
            
            if value:
                read_results["cache_hits"] += 1
                read_results["region_performance"][read_region]["hits"] += 1
                self.metrics.cross_region_hits += 1
            else:
                read_results["cache_misses"] += 1
            
            self.metrics.cross_region_reads += 1
        
        # Calculate average latencies per region
        for region in self.regions:
            region_perf = read_results["region_performance"][region]
            if region_perf["reads"] > 0:
                # Filter latencies for this region
                region_latencies = [
                    read_results["read_latencies"][i] 
                    for i in range(len(read_results["read_latencies"])) 
                    if i % len(self.regions) == self.regions.index(region)
                ]
                if region_latencies:
                    region_perf["avg_latency"] = statistics.mean(region_latencies)
        
        read_results["avg_read_latency"] = statistics.mean(read_results["read_latencies"]) if read_results["read_latencies"] else 0
        read_results["hit_rate"] = (read_results["cache_hits"] / read_operations * 100) if read_operations > 0 else 0
        
        return read_results
    
    def get_regional_consistency_summary(self) -> Dict[str, Any]:
        """Get comprehensive regional consistency test summary."""
        return {
            "consistency_metrics": {
                "sync_operations": self.metrics.sync_operations,
                "avg_sync_latency": self.metrics.avg_sync_latency,
                "consistency_rate": self.metrics.consistency_rate,
                "consistency_violations": self.metrics.consistency_violations,
                "conflict_resolutions": self.metrics.conflict_resolutions,
                "avg_conflict_resolution_time": self.metrics.avg_conflict_resolution_time,
                "cross_region_hit_rate": self.metrics.cross_region_hit_rate,
                "regional_operations": self.metrics.regional_operations
            },
            "sla_compliance": {
                "sync_latency_under_200ms": self.metrics.avg_sync_latency < 0.2,
                "consistency_above_99_9": self.metrics.consistency_rate > 99.9,
                "conflict_resolution_under_500ms": self.metrics.avg_conflict_resolution_time < 0.5
            },
            "recommendations": self._generate_consistency_recommendations()
        }
    
    def _generate_consistency_recommendations(self) -> List[str]:
        """Generate regional consistency recommendations."""
        recommendations = []
        
        if self.metrics.avg_sync_latency > 0.2:
            recommendations.append(f"Sync latency {self.metrics.avg_sync_latency*1000:.1f}ms exceeds 200ms - optimize cross-region networking")
        
        if self.metrics.consistency_rate < 99.9:
            recommendations.append(f"Consistency rate {self.metrics.consistency_rate:.2f}% below 99.9% - review sync mechanisms")
        
        if self.metrics.avg_conflict_resolution_time > 0.5:
            recommendations.append(f"Conflict resolution time {self.metrics.avg_conflict_resolution_time*1000:.1f}ms exceeds 500ms - optimize resolution strategy")
        
        if self.metrics.consistency_violations > 0:
            recommendations.append(f"{self.metrics.consistency_violations} consistency violations detected - review conflict detection")
        
        if self.metrics.cross_region_hit_rate < 80.0:
            recommendations.append(f"Cross-region hit rate {self.metrics.cross_region_hit_rate:.1f}% low - consider regional warming")
        
        if not recommendations:
            recommendations.append("All regional consistency metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up Redis containers and test resources."""
        try:
            # Clean up test keys
            for key in self.test_keys:
                for client in self.redis_clients.values():
                    try:
                        await client.delete(key)
                    except Exception:
                        pass
            
            # Close Redis clients
            for client in self.redis_clients.values():
                await client.close()
            
            # Stop Redis containers
            for container in self.redis_containers.values():
                await container.stop()
                
        except Exception as e:
            logger.error(f"Regional consistency cleanup failed: {e}")

@pytest.fixture
async def regional_consistency_manager():
    """Create L3 regional cache consistency manager."""
    manager = CacheConsistencyAcrossRegionsL3Manager()
    await manager.setup_multi_region_redis()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_multi_region_cache_sync(regional_consistency_manager):
    """L3: Test cache synchronization across multiple regions."""
    # Test sync for a key across all regions
    test_key = f"sync_test_{uuid.uuid4().hex[:8]}"
    source_region = "us-east"
    
    # Write initial data
    await regional_consistency_manager.write_to_region(
        source_region, test_key, {"data": "sync_test_data", "version": 1}
    )
    
    # Sync across regions
    sync_result = await regional_consistency_manager.sync_across_regions(test_key, source_region)
    
    # Verify sync results
    assert sync_result["successful_syncs"] >= 2, f"Too few successful syncs: {sync_result['successful_syncs']}"
    assert sync_result["sync_latency"] < 1.0, f"Sync latency {sync_result['sync_latency']*1000:.1f}ms too high"
    assert sync_result["failed_syncs"] == 0, f"Sync failures detected: {sync_result['failed_syncs']}"
    
    logger.info(f"Multi-region sync: {sync_result['successful_syncs']} successful, {sync_result['sync_latency']*1000:.1f}ms latency")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_eventual_consistency_convergence(regional_consistency_manager):
    """L3: Test eventual consistency convergence across regions."""
    result = await regional_consistency_manager.test_eventual_consistency(10)
    
    # Verify eventual consistency
    assert result["eventually_consistent"] >= 8, f"Too few keys achieved consistency: {result['eventually_consistent']}/10"
    assert result["consistency_violations"] <= 2, f"Too many consistency violations: {result['consistency_violations']}"
    assert result["avg_convergence_time"] < 1.0, f"Convergence time {result['avg_convergence_time']*1000:.1f}ms too high"
    
    logger.info(f"Eventual consistency: {result['eventually_consistent']}/10 consistent, {result['avg_convergence_time']*1000:.1f}ms convergence")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cross_region_conflict_resolution(regional_consistency_manager):
    """L3: Test conflict resolution for concurrent cross-region updates."""
    result = await regional_consistency_manager.test_conflict_resolution(8)
    
    # Verify conflict resolution
    assert result["conflicts_detected"] >= 4, f"Too few conflicts detected: {result['conflicts_detected']}"
    assert result["conflicts_resolved"] >= result["conflicts_detected"] * 0.8, f"Poor conflict resolution rate: {result['conflicts_resolved']}/{result['conflicts_detected']}"
    assert result["avg_resolution_time"] < 1.0, f"Resolution time {result['avg_resolution_time']*1000:.1f}ms too high"
    
    logger.info(f"Conflict resolution: {result['conflicts_resolved']}/{result['conflicts_detected']} resolved, {result['avg_resolution_time']*1000:.1f}ms avg time")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cross_region_read_performance(regional_consistency_manager):
    """L3: Test cross-region cache read performance."""
    result = await regional_consistency_manager.test_cross_region_read_performance(80)
    
    # Verify cross-region read performance
    assert result["hit_rate"] > 15.0, f"Cross-region hit rate {result['hit_rate']:.1f}% too low"
    assert result["avg_read_latency"] < 0.3, f"Average read latency {result['avg_read_latency']*1000:.1f}ms too high"
    
    # Verify regional performance distribution
    for region, perf in result["region_performance"].items():
        if perf["reads"] > 0:
            assert perf["avg_latency"] < 0.5, f"Region {region} latency {perf['avg_latency']*1000:.1f}ms too high"
    
    logger.info(f"Cross-region reads: {result['hit_rate']:.1f}% hit rate, {result['avg_read_latency']*1000:.1f}ms avg latency")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_regional_consistency_sla_compliance(regional_consistency_manager):
    """L3: Test comprehensive regional cache consistency SLA compliance."""
    # Execute comprehensive test suite
    await regional_consistency_manager.test_eventual_consistency(6)
    await regional_consistency_manager.test_conflict_resolution(5)
    await regional_consistency_manager.test_cross_region_read_performance(40)
    
    # Get comprehensive summary
    summary = regional_consistency_manager.get_regional_consistency_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["sync_latency_under_200ms"], f"Sync latency SLA violation: {regional_consistency_manager.metrics.avg_sync_latency*1000:.1f}ms"
    assert sla["consistency_above_99_9"], f"Consistency rate SLA violation: {regional_consistency_manager.metrics.consistency_rate:.2f}%"
    
    # If conflicts were resolved, verify resolution time
    if regional_consistency_manager.metrics.conflict_resolutions > 0:
        assert sla["conflict_resolution_under_500ms"], f"Conflict resolution SLA violation: {regional_consistency_manager.metrics.avg_conflict_resolution_time*1000:.1f}ms"
    
    # Verify operational metrics
    assert regional_consistency_manager.metrics.sync_operations > 0, "Should have performed sync operations"
    assert sum(regional_consistency_manager.metrics.regional_operations.values()) > 0, "Should have regional operations"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical regional consistency issues: {critical_recommendations}"
    
    logger.info(f"Regional consistency SLA compliance test completed successfully")
    logger.info(f"Summary: {summary}")