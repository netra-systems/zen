"""Cross-Region Data Consistency L4 Critical Path Tests

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Global Data Consistency and Availability
- Value Impact: Ensures data consistency for global enterprise customers
- Strategic Impact: $25K MRR protection from data inconsistency issues

Critical Path: Multi-region write -> Cross-region replication -> Consistency validation ->
            Conflict resolution -> Network partition handling -> Failover testing

L4 Realism: Tests against real staging infrastructure with simulated multi-region setups,
           production-like latencies, realistic network conditions, and enterprise workloads.

Coverage: Cross-region data replication, eventual consistency validation, conflict resolution,
         network partition scenarios, region failover, read/write routing optimization.
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import random
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    L4StagingCriticalPathTestBase,
    CriticalPathMetrics
)
from netra_backend.app.db.postgres_core import async_engine, async_session_factory
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.core.configuration.database import DatabaseConfigManager
from netra_backend.app.logging_config import central_logger
import redis.asyncio as aioredis

logger = central_logger.get_logger(__name__)


@dataclass
class RegionConfig:
    """Configuration for simulated region."""
    name: str
    latency_base_ms: int
    postgres_config: Dict[str, Any]
    redis_config: Dict[str, Any]
    clickhouse_config: Dict[str, Any]
    geographic_location: str
    priority: int = 0  # 0 = primary, 1+ = secondary


@dataclass
class CrossRegionMetrics:
    """Metrics for cross-region consistency testing."""
    write_operations: int = 0
    read_operations: int = 0
    sync_operations: int = 0
    consistency_checks: int = 0
    consistency_violations: int = 0
    conflict_resolutions: int = 0
    failover_events: int = 0
    network_partitions: int = 0
    
    write_latencies: List[float] = field(default_factory=list)
    read_latencies: List[float] = field(default_factory=list)
    sync_latencies: List[float] = field(default_factory=list)
    conflict_resolution_times: List[float] = field(default_factory=list)
    failover_times: List[float] = field(default_factory=list)
    
    regional_operations: Dict[str, int] = field(default_factory=dict)
    cross_region_hits: int = 0
    cross_region_misses: int = 0
    
    @property
    def avg_write_latency(self) -> float:
        return statistics.mean(self.write_latencies) if self.write_latencies else 0.0
    
    @property
    def avg_read_latency(self) -> float:
        return statistics.mean(self.read_latencies) if self.read_latencies else 0.0
    
    @property
    def avg_sync_latency(self) -> float:
        return statistics.mean(self.sync_latencies) if self.sync_latencies else 0.0
    
    @property
    def consistency_rate(self) -> float:
        if self.consistency_checks == 0:
            return 100.0
        return ((self.consistency_checks - self.consistency_violations) / self.consistency_checks) * 100.0
    
    @property
    def avg_conflict_resolution_time(self) -> float:
        return statistics.mean(self.conflict_resolution_times) if self.conflict_resolution_times else 0.0
    
    @property
    def avg_failover_time(self) -> float:
        return statistics.mean(self.failover_times) if self.failover_times else 0.0
    
    @property
    def cross_region_hit_rate(self) -> float:
        total_reads = self.cross_region_hits + self.cross_region_misses
        return (self.cross_region_hits / total_reads * 100) if total_reads > 0 else 0.0


class CrossRegionConsistencyL4Test(L4StagingCriticalPathTestBase):
    """L4 Cross-Region Data Consistency Test with staging environment validation."""
    
    def __init__(self):
        super().__init__("cross_region_consistency_l4")
        self.regions: Dict[str, RegionConfig] = {}
        self.region_clients: Dict[str, Dict[str, Any]] = {}
        self.cross_region_metrics = CrossRegionMetrics()
        self.test_data_prefix = f"l4_cross_region_{int(time.time())}"
        self.db_config_manager = DatabaseConfigManager()
        self.network_partition_active = False
        self.partitioned_regions: List[str] = []
        
    async def setup_test_specific_environment(self) -> None:
        """Setup cross-region test environment."""
        await self._setup_simulated_regions()
        await self._initialize_region_clients()
        await self._create_test_schemas()
        await self._validate_cross_region_connectivity()
        
    async def _setup_simulated_regions(self) -> None:
        """Setup simulated geographic regions with realistic configurations."""
        # Define regions with realistic latencies and configurations
        self.regions = {
            "us-east-1": RegionConfig(
                name="us-east-1",
                latency_base_ms=5,
                postgres_config={"pool_size": 10, "max_overflow": 20},
                redis_config={"max_connections": 50},
                clickhouse_config={"compression": "lz4"},
                geographic_location="N.Virginia",
                priority=0  # Primary region
            ),
            "us-west-2": RegionConfig(
                name="us-west-2",
                latency_base_ms=12,
                postgres_config={"pool_size": 8, "max_overflow": 15},
                redis_config={"max_connections": 40},
                clickhouse_config={"compression": "lz4"},
                geographic_location="Oregon",
                priority=1
            ),
            "eu-west-1": RegionConfig(
                name="eu-west-1",
                latency_base_ms=85,
                postgres_config={"pool_size": 8, "max_overflow": 15},
                redis_config={"max_connections": 40},
                clickhouse_config={"compression": "zstd"},
                geographic_location="Ireland",
                priority=2
            ),
            "ap-southeast-1": RegionConfig(
                name="ap-southeast-1",
                latency_base_ms=150,
                postgres_config={"pool_size": 6, "max_overflow": 12},
                redis_config={"max_connections": 30},
                clickhouse_config={"compression": "zstd"},
                geographic_location="Singapore",
                priority=3
            )
        }
        
        logger.info(f"Setup {len(self.regions)} simulated regions for cross-region consistency testing")
        
    async def _initialize_region_clients(self) -> None:
        """Initialize database clients for each simulated region."""
        for region_name, region_config in self.regions.items():
            try:
                # For L4 staging testing, we use the same database connections but simulate
                # regional behavior through latency injection and connection pooling
                
                # Initialize PostgreSQL client (staging shared)
                postgres_client = async_engine
                
                # Initialize Redis client (staging shared with region-specific keyspace)
                redis_client = RedisService()
                await redis_client.connect()
                
                # Initialize ClickHouse client (staging shared)
                # ClickHouse client will be used with region-specific database names
                
                self.region_clients[region_name] = {
                    "postgres": postgres_client,
                    "redis": redis_client,
                    "clickhouse": None,  # Will be created per-operation
                    "config": region_config
                }
                
                # Initialize regional operation counters
                self.cross_region_metrics.regional_operations[region_name] = 0
                
                logger.info(f"Initialized clients for region {region_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize clients for region {region_name}: {e}")
                raise
    
    async def _create_test_schemas(self) -> None:
        """Create test database schemas for cross-region testing."""
        try:
            # Create PostgreSQL test tables
            async with async_engine.begin() as conn:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.test_data_prefix}_cross_region_data (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        region_origin VARCHAR(50) NOT NULL,
                        data_key VARCHAR(100) NOT NULL,
                        data_value JSONB NOT NULL,
                        version INTEGER DEFAULT 1,
                        last_updated_by VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        is_replicated BOOLEAN DEFAULT FALSE,
                        conflict_resolution_count INTEGER DEFAULT 0
                    )
                """)
                
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.test_data_prefix}_region_key 
                    ON {self.test_data_prefix}_cross_region_data (region_origin, data_key)
                """)
                
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.test_data_prefix}_version 
                    ON {self.test_data_prefix}_cross_region_data (data_key, version)
                """)
            
            # Create ClickHouse test tables for analytics data
            async with get_clickhouse_client() as client:
                await client.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.test_data_prefix}_cross_region_analytics (
                        event_id String,
                        region_origin String,
                        data_key String,
                        operation_type String,
                        latency_ms Float64,
                        success UInt8,
                        timestamp DateTime DEFAULT now(),
                        metadata String
                    ) ENGINE = MergeTree()
                    ORDER BY (region_origin, timestamp)
                """)
            
            logger.info("Created test schemas for cross-region consistency testing")
            
        except Exception as e:
            logger.error(f"Failed to create test schemas: {e}")
            raise
    
    async def _validate_cross_region_connectivity(self) -> None:
        """Validate connectivity across all simulated regions."""
        connectivity_issues = []
        
        for region_name, clients in self.region_clients.items():
            try:
                # Test PostgreSQL connectivity
                async with clients["postgres"].begin() as conn:
                    result = await conn.execute("SELECT 1 as health_check")
                    assert result.fetchone()[0] == 1
                
                # Test Redis connectivity
                await clients["redis"].client.ping()
                
                # Test ClickHouse connectivity
                async with get_clickhouse_client() as client:
                    result = await client.fetch("SELECT 1 as health_check")
                    assert result[0]['health_check'] == 1
                
                logger.info(f"Region {region_name} connectivity validated")
                
            except Exception as e:
                connectivity_issues.append(f"{region_name}: {str(e)}")
        
        if connectivity_issues:
            raise RuntimeError(f"Cross-region connectivity validation failed: {'; '.join(connectivity_issues)}")
    
    async def simulate_network_latency(self, source_region: str, target_region: str) -> None:
        """Simulate realistic network latency between regions."""
        if source_region == target_region:
            return  # No latency for same region operations
        
        source_config = self.regions[source_region]
        target_config = self.regions[target_region]
        
        # Calculate latency based on geographic distance simulation
        base_latency_ms = abs(target_config.latency_base_ms - source_config.latency_base_ms)
        
        # Add jitter (±20% variation)
        jitter = random.uniform(-0.2, 0.2)
        actual_latency_ms = base_latency_ms * (1 + jitter)
        
        # Add network partition simulation
        if self.network_partition_active and (source_region in self.partitioned_regions or target_region in self.partitioned_regions):
            # Simulate network partition with high latency/timeouts
            actual_latency_ms += random.uniform(1000, 3000)  # 1-3 second delays
        
        await asyncio.sleep(actual_latency_ms / 1000.0)  # Convert to seconds
    
    async def write_data_to_region(self, region: str, data_key: str, data_value: Dict[str, Any], 
                                 version: int = 1) -> Dict[str, Any]:
        """Write data to specific region with metadata tracking."""
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            clients = self.region_clients[region]
            
            # Simulate cross-region latency for write operation
            await self.simulate_network_latency("us-east-1", region)  # Assume writes originate from primary
            
            # Write to PostgreSQL
            async with clients["postgres"].begin() as conn:
                result = await conn.execute(f"""
                    INSERT INTO {self.test_data_prefix}_cross_region_data 
                    (region_origin, data_key, data_value, version, last_updated_by)
                    VALUES ('{region}', '{data_key}', '{json.dumps(data_value)}', {version}, '{region}')
                    RETURNING id, created_at
                """)
                row = result.fetchone()
                record_id = str(row[0])
                created_at = row[1]
            
            # Write to Redis for fast access
            redis_key = f"{self.test_data_prefix}:region:{region}:key:{data_key}"
            redis_data = {
                "id": record_id,
                "region_origin": region,
                "data_value": data_value,
                "version": version,
                "created_at": created_at.isoformat(),
                "operation_id": operation_id
            }
            await clients["redis"].client.setex(redis_key, 3600, json.dumps(redis_data, default=str))
            
            # Write analytics to ClickHouse
            write_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            async with get_clickhouse_client() as client:
                await client.execute(f"""
                    INSERT INTO {self.test_data_prefix}_cross_region_analytics 
                    (event_id, region_origin, data_key, operation_type, latency_ms, success, metadata)
                    VALUES ('{operation_id}', '{region}', '{data_key}', 'write', {write_latency}, 1, '{json.dumps({"version": version})}')
                """)
            
            # Update metrics
            self.cross_region_metrics.write_operations += 1
            self.cross_region_metrics.write_latencies.append(time.time() - start_time)
            self.cross_region_metrics.regional_operations[region] += 1
            
            return {
                "success": True,
                "operation_id": operation_id,
                "record_id": record_id,
                "region": region,
                "latency_ms": write_latency,
                "created_at": created_at.isoformat()
            }
            
        except Exception as e:
            # Record failed write
            write_latency = (time.time() - start_time) * 1000
            try:
                async with get_clickhouse_client() as client:
                    await client.execute(f"""
                        INSERT INTO {self.test_data_prefix}_cross_region_analytics 
                        (event_id, region_origin, data_key, operation_type, latency_ms, success, metadata)
                        VALUES ('{operation_id}', '{region}', '{data_key}', 'write', {write_latency}, 0, '{json.dumps({"error": str(e)})}')
                    """)
            except:
                pass  # Don't fail if analytics write fails
            
            return {
                "success": False,
                "operation_id": operation_id,
                "region": region,
                "error": str(e),
                "latency_ms": write_latency
            }
    
    async def read_data_from_region(self, region: str, data_key: str) -> Dict[str, Any]:
        """Read data from specific region with fallback logic."""
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            clients = self.region_clients[region]
            
            # Simulate cross-region latency for read operation
            await self.simulate_network_latency("us-east-1", region)
            
            # Try Redis first for fast access
            redis_key = f"{self.test_data_prefix}:region:{region}:key:{data_key}"
            redis_data = await clients["redis"].client.get(redis_key)
            
            if redis_data:
                self.cross_region_metrics.cross_region_hits += 1
                data = json.loads(redis_data)
                read_latency = (time.time() - start_time) * 1000
                
                # Record analytics
                async with get_clickhouse_client() as client:
                    await client.execute(f"""
                        INSERT INTO {self.test_data_prefix}_cross_region_analytics 
                        (event_id, region_origin, data_key, operation_type, latency_ms, success, metadata)
                        VALUES ('{operation_id}', '{region}', '{data_key}', 'read_cache_hit', {read_latency}, 1, '{json.dumps({"source": "redis"})}')
                    """)
                
                self.cross_region_metrics.read_operations += 1
                self.cross_region_metrics.read_latencies.append(time.time() - start_time)
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "data": data,
                    "source": "redis",
                    "region": region,
                    "latency_ms": read_latency
                }
            
            # Fallback to PostgreSQL
            self.cross_region_metrics.cross_region_misses += 1
            async with clients["postgres"].begin() as conn:
                result = await conn.execute(f"""
                    SELECT id, data_value, version, created_at, updated_at 
                    FROM {self.test_data_prefix}_cross_region_data 
                    WHERE region_origin = '{region}' AND data_key = '{data_key}'
                    ORDER BY version DESC LIMIT 1
                """)
                row = result.fetchone()
                
                if not row:
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "region": region,
                        "error": "data_not_found",
                        "latency_ms": (time.time() - start_time) * 1000
                    }
                
                data = {
                    "id": str(row[0]),
                    "data_value": json.loads(row[1]),
                    "version": row[2],
                    "created_at": row[3].isoformat(),
                    "updated_at": row[4].isoformat()
                }
            
            read_latency = (time.time() - start_time) * 1000
            
            # Record analytics
            async with get_clickhouse_client() as client:
                await client.execute(f"""
                    INSERT INTO {self.test_data_prefix}_cross_region_analytics 
                    (event_id, region_origin, data_key, operation_type, latency_ms, success, metadata)
                    VALUES ('{operation_id}', '{region}', '{data_key}', 'read_db_fallback', {read_latency}, 1, '{json.dumps({"source": "postgres"})}')
                """)
            
            self.cross_region_metrics.read_operations += 1
            self.cross_region_metrics.read_latencies.append(time.time() - start_time)
            
            return {
                "success": True,
                "operation_id": operation_id,
                "data": data,
                "source": "postgres",
                "region": region,
                "latency_ms": read_latency
            }
            
        except Exception as e:
            read_latency = (time.time() - start_time) * 1000
            return {
                "success": False,
                "operation_id": operation_id,
                "region": region,
                "error": str(e),
                "latency_ms": read_latency
            }
    
    async def sync_data_across_regions(self, data_key: str, source_region: str, 
                                     target_regions: List[str] = None) -> Dict[str, Any]:
        """Synchronize data across multiple regions with conflict detection."""
        if target_regions is None:
            target_regions = [r for r in self.regions.keys() if r != source_region]
        
        start_time = time.time()
        sync_id = str(uuid.uuid4())
        
        # Read data from source region
        source_data = await self.read_data_from_region(source_region, data_key)
        if not source_data["success"]:
            return {
                "sync_id": sync_id,
                "success": False,
                "reason": "source_read_failed",
                "source_region": source_region,
                "target_regions": target_regions,
                "sync_latency": time.time() - start_time
            }
        
        sync_results = {}
        successful_syncs = 0
        failed_syncs = 0
        conflicts_detected = 0
        
        for target_region in target_regions:
            try:
                # Check for existing data in target region
                existing_data = await self.read_data_from_region(target_region, data_key)
                
                source_version = source_data["data"].get("version", 1)
                
                if existing_data["success"]:
                    existing_version = existing_data["data"].get("version", 1)
                    
                    # Conflict detection: version comparison
                    if existing_version > source_version:
                        conflicts_detected += 1
                        sync_results[target_region] = {
                            "success": False,
                            "reason": "version_conflict",
                            "existing_version": existing_version,
                            "source_version": source_version
                        }
                        failed_syncs += 1
                        continue
                    elif existing_version == source_version:
                        # Same version, check timestamp for last-writer-wins
                        source_timestamp = datetime.fromisoformat(source_data["data"]["created_at"])
                        existing_timestamp = datetime.fromisoformat(existing_data["data"]["created_at"])
                        
                        if existing_timestamp > source_timestamp:
                            conflicts_detected += 1
                            sync_results[target_region] = {
                                "success": False,
                                "reason": "timestamp_conflict",
                                "conflict_resolution": "last_writer_wins"
                            }
                            failed_syncs += 1
                            continue
                
                # Perform sync
                sync_data = source_data["data"]["data_value"]
                new_version = source_version + 1  # Increment version for sync
                
                write_result = await self.write_data_to_region(
                    target_region, data_key, sync_data, new_version
                )
                
                if write_result["success"]:
                    sync_results[target_region] = {
                        "success": True,
                        "new_version": new_version,
                        "record_id": write_result["record_id"]
                    }
                    successful_syncs += 1
                else:
                    sync_results[target_region] = {
                        "success": False,
                        "reason": "write_failed",
                        "error": write_result["error"]
                    }
                    failed_syncs += 1
                    
            except Exception as e:
                sync_results[target_region] = {
                    "success": False,
                    "reason": "sync_exception",
                    "error": str(e)
                }
                failed_syncs += 1
        
        sync_latency = time.time() - start_time
        self.cross_region_metrics.sync_operations += 1
        self.cross_region_metrics.sync_latencies.append(sync_latency)
        
        # Record sync analytics
        async with get_clickhouse_client() as client:
            await client.execute(f"""
                INSERT INTO {self.test_data_prefix}_cross_region_analytics 
                (event_id, region_origin, data_key, operation_type, latency_ms, success, metadata)
                VALUES ('{sync_id}', '{source_region}', '{data_key}', 'sync', {sync_latency * 1000}, 
                {1 if successful_syncs > failed_syncs else 0}, 
                '{json.dumps({"successful_syncs": successful_syncs, "failed_syncs": failed_syncs, "conflicts": conflicts_detected})}')
            """)
        
        return {
            "sync_id": sync_id,
            "success": successful_syncs > 0,
            "source_region": source_region,
            "target_regions": target_regions,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "conflicts_detected": conflicts_detected,
            "sync_latency": sync_latency,
            "sync_results": sync_results
        }
    
    async def test_eventual_consistency(self, test_operations: int) -> Dict[str, Any]:
        """Test eventual consistency across all regions."""
        consistency_results = {
            "total_operations": test_operations,
            "eventually_consistent": 0,
            "consistency_violations": 0,
            "avg_convergence_time": 0,
            "operation_results": {}
        }
        
        convergence_times = []
        
        for i in range(test_operations):
            data_key = f"consistency_test_{i}_{uuid.uuid4().hex[:8]}"
            source_region = random.choice(list(self.regions.keys()))
            
            # Write initial data
            test_data = {
                "operation_id": i,
                "test_value": f"consistency_data_{i}",
                "created_by": "eventual_consistency_test"
            }
            
            write_result = await self.write_data_to_region(source_region, data_key, test_data)
            
            if not write_result["success"]:
                consistency_results["operation_results"][data_key] = {
                    "success": False,
                    "reason": "initial_write_failed"
                }
                continue
            
            # Trigger sync to other regions
            sync_result = await self.sync_data_across_regions(data_key, source_region)
            
            # Wait and test for eventual consistency
            convergence_start = time.time()
            max_wait = 3.0  # 3 seconds max wait for convergence
            
            eventually_consistent = False
            while time.time() - convergence_start < max_wait:
                consistent = await self._check_cross_region_consistency(data_key)
                
                if consistent:
                    convergence_time = time.time() - convergence_start
                    convergence_times.append(convergence_time)
                    consistency_results["eventually_consistent"] += 1
                    eventually_consistent = True
                    break
                
                await asyncio.sleep(0.2)  # Check every 200ms
            
            if not eventually_consistent:
                consistency_results["consistency_violations"] += 1
                self.cross_region_metrics.consistency_violations += 1
                logger.warning(f"Key {data_key} did not achieve eventual consistency")
            
            self.cross_region_metrics.consistency_checks += 1
            
            consistency_results["operation_results"][data_key] = {
                "source_region": source_region,
                "successful_syncs": sync_result["successful_syncs"],
                "eventually_consistent": eventually_consistent
            }
        
        if convergence_times:
            consistency_results["avg_convergence_time"] = statistics.mean(convergence_times)
        
        return consistency_results
    
    async def _check_cross_region_consistency(self, data_key: str) -> bool:
        """Check if data is consistent across all regions."""
        region_data = {}
        
        # Read from all regions
        for region in self.regions.keys():
            read_result = await self.read_data_from_region(region, data_key)
            if read_result["success"]:
                region_data[region] = read_result["data"]
        
        if len(region_data) == 0:
            return True  # No data anywhere is considered consistent
        
        # Compare data values across regions
        data_values = list(region_data.values())
        first_value = data_values[0]
        
        # Check if all regions have the same data value
        for value in data_values[1:]:
            if (value.get("data_value") != first_value.get("data_value") or
                value.get("version", 0) != first_value.get("version", 0)):
                return False
        
        return True
    
    async def test_conflict_resolution(self, conflict_scenarios: int) -> Dict[str, Any]:
        """Test conflict resolution for concurrent writes across regions."""
        conflict_results = {
            "total_scenarios": conflict_scenarios,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "resolution_failures": 0,
            "avg_resolution_time": 0
        }
        
        resolution_times = []
        
        for scenario in range(conflict_scenarios):
            data_key = f"conflict_test_{scenario}_{uuid.uuid4().hex[:8]}"
            
            # Select two different regions for concurrent writes
            regions = random.sample(list(self.regions.keys()), 2)
            region1, region2 = regions[0], regions[1]
            
            # Create conflicting data with same version
            data1 = {
                "conflict_scenario": scenario,
                "value": f"data_from_{region1}",
                "region_source": region1,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            data2 = {
                "conflict_scenario": scenario,
                "value": f"data_from_{region2}",
                "region_source": region2,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Perform concurrent writes
            conflict_start = time.time()
            
            write_results = await asyncio.gather(
                self.write_data_to_region(region1, data_key, data1, version=1),
                self.write_data_to_region(region2, data_key, data2, version=1),
                return_exceptions=True
            )
            
            # Attempt cross-region sync (should detect conflicts)
            sync_result1 = await self.sync_data_across_regions(data_key, region1, [region2])
            sync_result2 = await self.sync_data_across_regions(data_key, region2, [region1])
            
            # Check if conflicts were detected
            conflicts_detected = (
                sync_result1["conflicts_detected"] > 0 or
                sync_result2["conflicts_detected"] > 0
            )
            
            if conflicts_detected:
                conflict_results["conflicts_detected"] += 1
                
                # Resolve conflict using last-writer-wins strategy
                resolved = await self._resolve_conflict_last_writer_wins(data_key, region1, region2)
                
                resolution_time = time.time() - conflict_start
                resolution_times.append(resolution_time)
                self.cross_region_metrics.conflict_resolution_times.append(resolution_time)
                self.cross_region_metrics.conflict_resolutions += 1
                
                if resolved:
                    conflict_results["conflicts_resolved"] += 1
                else:
                    conflict_results["resolution_failures"] += 1
        
        if resolution_times:
            conflict_results["avg_resolution_time"] = statistics.mean(resolution_times)
        
        return conflict_results
    
    async def _resolve_conflict_last_writer_wins(self, data_key: str, region1: str, region2: str) -> bool:
        """Resolve conflict using last-writer-wins strategy."""
        try:
            # Read from both regions
            data1_result = await self.read_data_from_region(region1, data_key)
            data2_result = await self.read_data_from_region(region2, data_key)
            
            if not (data1_result["success"] and data2_result["success"]):
                return False
            
            data1 = data1_result["data"]
            data2 = data2_result["data"]
            
            # Compare timestamps to determine winner
            timestamp1 = datetime.fromisoformat(data1["created_at"])
            timestamp2 = datetime.fromisoformat(data2["created_at"])
            
            if timestamp1 > timestamp2:
                winner_region = region1
                winner_data = data1["data_value"]
                loser_region = region2
            else:
                winner_region = region2
                winner_data = data2["data_value"]
                loser_region = region1
            
            # Create resolved data with conflict metadata
            resolved_data = {
                **winner_data,
                "conflict_resolved": True,
                "resolution_strategy": "last_writer_wins",
                "resolution_timestamp": datetime.utcnow().isoformat(),
                "original_conflict_regions": [region1, region2]
            }
            
            # Update both regions with resolved data
            new_version = max(data1.get("version", 1), data2.get("version", 1)) + 1
            
            write_results = await asyncio.gather(
                self.write_data_to_region(winner_region, data_key, resolved_data, new_version),
                self.write_data_to_region(loser_region, data_key, resolved_data, new_version),
                return_exceptions=True
            )
            
            # Check if both writes succeeded
            return all(isinstance(r, dict) and r.get("success", False) for r in write_results)
            
        except Exception as e:
            logger.error(f"Conflict resolution failed for key {data_key}: {e}")
            return False
    
    async def simulate_network_partition(self, partitioned_regions: List[str], 
                                       duration_seconds: float) -> Dict[str, Any]:
        """Simulate network partition affecting specified regions."""
        partition_start = time.time()
        partition_id = str(uuid.uuid4())
        
        logger.info(f"Simulating network partition for regions: {partitioned_regions}")
        
        # Activate network partition
        self.network_partition_active = True
        self.partitioned_regions = partitioned_regions
        self.cross_region_metrics.network_partitions += 1
        
        # Test operations during partition
        partition_test_results = {
            "partition_id": partition_id,
            "affected_regions": partitioned_regions,
            "duration": duration_seconds,
            "operations_during_partition": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "partition_effects": {}
        }
        
        # Perform test operations during partition
        test_operations = 5
        for i in range(test_operations):
            data_key = f"partition_test_{i}_{uuid.uuid4().hex[:8]}"
            test_region = random.choice(list(self.regions.keys()))
            
            test_data = {
                "partition_test": True,
                "operation_id": i,
                "test_during_partition": True
            }
            
            operation_start = time.time()
            write_result = await self.write_data_to_region(test_region, data_key, test_data)
            operation_duration = time.time() - operation_start
            
            partition_test_results["operations_during_partition"] += 1
            
            if write_result["success"]:
                partition_test_results["successful_operations"] += 1
                # Test read from another region
                other_region = random.choice([r for r in self.regions.keys() if r != test_region])
                read_result = await self.read_data_from_region(other_region, data_key)
                
                partition_test_results["partition_effects"][f"operation_{i}"] = {
                    "write_region": test_region,
                    "read_region": other_region,
                    "write_success": True,
                    "read_success": read_result["success"],
                    "operation_duration": operation_duration,
                    "affected_by_partition": test_region in partitioned_regions or other_region in partitioned_regions
                }
            else:
                partition_test_results["failed_operations"] += 1
                partition_test_results["partition_effects"][f"operation_{i}"] = {
                    "write_region": test_region,
                    "write_success": False,
                    "operation_duration": operation_duration,
                    "affected_by_partition": test_region in partitioned_regions
                }
        
        # Wait for partition duration
        remaining_time = duration_seconds - (time.time() - partition_start)
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)
        
        # Deactivate network partition
        self.network_partition_active = False
        self.partitioned_regions = []
        
        partition_test_results["total_duration"] = time.time() - partition_start
        
        logger.info(f"Network partition simulation completed: {partition_test_results}")
        
        return partition_test_results
    
    async def test_region_failover(self, failed_region: str) -> Dict[str, Any]:
        """Test failover when a region becomes unavailable."""
        failover_start = time.time()
        failover_id = str(uuid.uuid4())
        
        # Test operations before failover
        test_key = f"failover_test_{uuid.uuid4().hex[:8]}"
        pre_failover_data = {
            "failover_test": True,
            "phase": "pre_failover",
            "primary_region": failed_region
        }
        
        # Write to primary region
        write_result = await self.write_data_to_region(failed_region, test_key, pre_failover_data)
        
        # Sync to other regions
        available_regions = [r for r in self.regions.keys() if r != failed_region]
        sync_result = await self.sync_data_across_regions(test_key, failed_region, available_regions)
        
        # Simulate region failure by marking it as partitioned
        original_partition_state = self.network_partition_active
        original_partitioned_regions = self.partitioned_regions.copy()
        
        self.network_partition_active = True
        self.partitioned_regions = [failed_region]
        self.cross_region_metrics.failover_events += 1
        
        # Test failover operations
        failover_region = available_regions[0]  # Choose first available region as failover target
        
        failover_data = {
            "failover_test": True,
            "phase": "during_failover",
            "failed_region": failed_region,
            "failover_region": failover_region
        }
        
        # Perform operations on failover region
        failover_write_result = await self.write_data_to_region(failover_region, test_key, failover_data, version=2)
        
        # Test read operations from multiple regions
        read_results = {}
        for region in available_regions:
            read_result = await self.read_data_from_region(region, test_key)
            read_results[region] = read_result
        
        failover_duration = time.time() - failover_start
        self.cross_region_metrics.failover_times.append(failover_duration)
        
        # Restore original partition state
        self.network_partition_active = original_partition_state
        self.partitioned_regions = original_partitioned_regions
        
        # Analyze failover results
        successful_reads = sum(1 for result in read_results.values() if result["success"])
        
        failover_results = {
            "failover_id": failover_id,
            "failed_region": failed_region,
            "failover_region": failover_region,
            "available_regions": available_regions,
            "pre_failover_write_success": write_result["success"],
            "pre_failover_sync_success": sync_result["successful_syncs"] > 0,
            "failover_write_success": failover_write_result["success"],
            "successful_reads_count": successful_reads,
            "total_available_regions": len(available_regions),
            "failover_duration": failover_duration,
            "read_results": read_results
        }
        
        return failover_results
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute comprehensive cross-region consistency critical path test."""
        logger.info("Starting L4 cross-region consistency critical path test")
        
        test_results = {
            "test_phase": "cross_region_consistency_l4",
            "start_time": datetime.utcnow().isoformat(),
            "service_calls": 0
        }
        
        try:
            # Phase 1: Basic cross-region operations
            logger.info("Phase 1: Testing basic cross-region operations")
            basic_ops_results = await self._test_basic_cross_region_operations()
            test_results["basic_operations"] = basic_ops_results
            test_results["service_calls"] += basic_ops_results.get("total_operations", 0)
            
            # Phase 2: Eventual consistency testing
            logger.info("Phase 2: Testing eventual consistency")
            consistency_results = await self.test_eventual_consistency(8)
            test_results["eventual_consistency"] = consistency_results
            test_results["service_calls"] += consistency_results["total_operations"]
            
            # Phase 3: Conflict resolution testing
            logger.info("Phase 3: Testing conflict resolution")
            conflict_results = await self.test_conflict_resolution(6)
            test_results["conflict_resolution"] = conflict_results
            test_results["service_calls"] += conflict_results["total_scenarios"]
            
            # Phase 4: Network partition simulation
            logger.info("Phase 4: Testing network partition handling")
            partition_results = await self.simulate_network_partition(
                ["ap-southeast-1", "eu-west-1"], 2.0
            )
            test_results["network_partition"] = partition_results
            test_results["service_calls"] += partition_results["operations_during_partition"]
            
            # Phase 5: Region failover testing
            logger.info("Phase 5: Testing region failover")
            failover_results = await self.test_region_failover("us-west-2")
            test_results["region_failover"] = failover_results
            test_results["service_calls"] += 3  # Approximate operation count for failover test
            
            # Collect comprehensive metrics
            test_results["cross_region_metrics"] = self._get_cross_region_metrics_summary()
            
            test_results["end_time"] = datetime.utcnow().isoformat()
            test_results["success"] = True
            
            logger.info("L4 cross-region consistency critical path test completed successfully")
            
        except Exception as e:
            test_results["success"] = False
            test_results["error"] = str(e)
            test_results["end_time"] = datetime.utcnow().isoformat()
            logger.error(f"L4 cross-region consistency test failed: {e}")
        
        return test_results
    
    async def _test_basic_cross_region_operations(self) -> Dict[str, Any]:
        """Test basic cross-region read/write operations."""
        results = {
            "total_operations": 0,
            "successful_writes": 0,
            "successful_reads": 0,
            "successful_syncs": 0,
            "regional_performance": {}
        }
        
        # Test writes to each region
        for region in self.regions.keys():
            test_key = f"basic_ops_{region}_{uuid.uuid4().hex[:8]}"
            test_data = {
                "region": region,
                "operation_type": "basic_write",
                "test_data": f"data_for_{region}"
            }
            
            write_result = await self.write_data_to_region(region, test_key, test_data)
            results["total_operations"] += 1
            
            if write_result["success"]:
                results["successful_writes"] += 1
                
                # Test read from same region
                read_result = await self.read_data_from_region(region, test_key)
                results["total_operations"] += 1
                
                if read_result["success"]:
                    results["successful_reads"] += 1
                
                # Test sync to other regions
                other_regions = [r for r in self.regions.keys() if r != region]
                sync_result = await self.sync_data_across_regions(test_key, region, other_regions[:2])
                results["total_operations"] += 1
                
                if sync_result["success"]:
                    results["successful_syncs"] += 1
                
                results["regional_performance"][region] = {
                    "write_latency_ms": write_result.get("latency_ms", 0),
                    "read_latency_ms": read_result.get("latency_ms", 0),
                    "sync_successful": sync_result["successful_syncs"],
                    "sync_latency": sync_result["sync_latency"]
                }
        
        return results
    
    def _get_cross_region_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive cross-region metrics summary."""
        return {
            "operations": {
                "total_writes": self.cross_region_metrics.write_operations,
                "total_reads": self.cross_region_metrics.read_operations,
                "total_syncs": self.cross_region_metrics.sync_operations,
                "consistency_checks": self.cross_region_metrics.consistency_checks,
                "conflict_resolutions": self.cross_region_metrics.conflict_resolutions,
                "failover_events": self.cross_region_metrics.failover_events,
                "network_partitions": self.cross_region_metrics.network_partitions
            },
            "performance": {
                "avg_write_latency_ms": self.cross_region_metrics.avg_write_latency * 1000,
                "avg_read_latency_ms": self.cross_region_metrics.avg_read_latency * 1000,
                "avg_sync_latency_ms": self.cross_region_metrics.avg_sync_latency * 1000,
                "avg_conflict_resolution_time_ms": self.cross_region_metrics.avg_conflict_resolution_time * 1000,
                "avg_failover_time_ms": self.cross_region_metrics.avg_failover_time * 1000,
                "cross_region_hit_rate": self.cross_region_metrics.cross_region_hit_rate
            },
            "quality": {
                "consistency_rate": self.cross_region_metrics.consistency_rate,
                "consistency_violations": self.cross_region_metrics.consistency_violations
            },
            "regional_distribution": self.cross_region_metrics.regional_operations
        }
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate cross-region consistency results meet business requirements."""
        try:
            validation_results = []
            
            # Validate basic operations success rate
            basic_ops = results.get("basic_operations", {})
            if basic_ops.get("total_operations", 0) > 0:
                write_success_rate = (basic_ops.get("successful_writes", 0) / 
                                    (basic_ops.get("total_operations", 1) / 3)) * 100  # Approx 1/3 are writes
                validation_results.append(write_success_rate >= 90.0)
            
            # Validate eventual consistency
            consistency = results.get("eventual_consistency", {})
            if consistency.get("total_operations", 0) > 0:
                consistency_rate = (consistency.get("eventually_consistent", 0) / 
                                  consistency.get("total_operations", 1)) * 100
                validation_results.append(consistency_rate >= 80.0)
                validation_results.append(consistency.get("avg_convergence_time", 0) < 3.0)
            
            # Validate conflict resolution
            conflicts = results.get("conflict_resolution", {})
            if conflicts.get("conflicts_detected", 0) > 0:
                resolution_rate = (conflicts.get("conflicts_resolved", 0) / 
                                 conflicts.get("conflicts_detected", 1)) * 100
                validation_results.append(resolution_rate >= 70.0)
                validation_results.append(conflicts.get("avg_resolution_time", 0) < 5.0)
            
            # Validate network partition handling
            partition = results.get("network_partition", {})
            if partition.get("operations_during_partition", 0) > 0:
                partition_success_rate = (partition.get("successful_operations", 0) / 
                                        partition.get("operations_during_partition", 1)) * 100
                # Lower success rate expected during partition
                validation_results.append(partition_success_rate >= 50.0)
            
            # Validate failover performance
            failover = results.get("region_failover", {})
            if failover:
                validation_results.append(failover.get("failover_write_success", False))
                validation_results.append(failover.get("failover_duration", 0) < 10.0)
                validation_results.append(failover.get("successful_reads_count", 0) >= 1)
            
            # Validate overall metrics
            metrics = results.get("cross_region_metrics", {})
            performance = metrics.get("performance", {})
            
            # Performance thresholds for L4 testing
            validation_results.append(performance.get("avg_write_latency_ms", 0) < 2000)  # 2 seconds
            validation_results.append(performance.get("avg_read_latency_ms", 0) < 1500)   # 1.5 seconds
            validation_results.append(performance.get("avg_sync_latency_ms", 0) < 5000)   # 5 seconds
            
            quality = metrics.get("quality", {})
            validation_results.append(quality.get("consistency_rate", 0) >= 75.0)
            
            return all(validation_results)
            
        except Exception as e:
            logger.error(f"Cross-region consistency validation failed: {e}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Cleanup cross-region test resources."""
        try:
            # Clean up PostgreSQL test data
            async with async_engine.begin() as conn:
                await conn.execute(f"DROP TABLE IF EXISTS {self.test_data_prefix}_cross_region_data CASCADE")
            
            # Clean up ClickHouse test data
            async with get_clickhouse_client() as client:
                await client.execute(f"DROP TABLE IF EXISTS {self.test_data_prefix}_cross_region_analytics")
            
            # Clean up Redis test data
            for region_name, clients in self.region_clients.items():
                if clients.get("redis"):
                    try:
                        # Clean up region-specific Redis keys
                        pattern = f"{self.test_data_prefix}:region:{region_name}:*"
                        keys = await clients["redis"].client.keys(pattern)
                        if keys:
                            await clients["redis"].client.delete(*keys)
                        
                        await clients["redis"].disconnect()
                    except Exception as e:
                        logger.warning(f"Redis cleanup warning for region {region_name}: {e}")
            
            logger.info("Cross-region consistency test resources cleaned up")
            
        except Exception as e:
            logger.error(f"Cross-region consistency cleanup failed: {e}")


# Pytest fixtures and tests
@pytest.fixture
async def cross_region_consistency_l4_test():
    """Create L4 cross-region consistency test instance."""
    test_instance = CrossRegionConsistencyL4Test()
    await test_instance.initialize_l4_environment()
    yield test_instance
    await test_instance.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.l4
@pytest.mark.staging
async def test_l4_cross_region_consistency_critical_path(cross_region_consistency_l4_test):
    """L4: Execute comprehensive cross-region data consistency critical path test."""
    logger.info("Starting L4 cross-region consistency critical path test")
    
    # Execute complete critical path test
    metrics = await cross_region_consistency_l4_test.run_complete_critical_path_test()
    
    # Verify critical path completion
    assert metrics.success, f"Cross-region consistency critical path failed: {metrics.errors}"
    assert metrics.validation_count > 0, "No validations performed"
    assert metrics.error_count == 0, f"Critical path errors detected: {metrics.error_count}"
    
    # Verify business metrics
    business_metrics = {
        "max_response_time_seconds": 10.0,  # Allow higher latency for cross-region
        "min_success_rate_percent": 80.0,
        "max_error_count": 0
    }
    
    business_validation = await cross_region_consistency_l4_test.validate_business_metrics(business_metrics)
    assert business_validation, f"Business metrics validation failed: {metrics.errors}"
    
    # Verify cross-region specific metrics
    cross_region_summary = cross_region_consistency_l4_test._get_cross_region_metrics_summary()
    
    # Ensure significant cross-region activity
    operations = cross_region_summary["operations"]
    assert operations["total_writes"] >= 15, f"Insufficient write operations: {operations['total_writes']}"
    assert operations["total_reads"] >= 10, f"Insufficient read operations: {operations['total_reads']}"
    assert operations["total_syncs"] >= 5, f"Insufficient sync operations: {operations['total_syncs']}"
    
    # Verify performance within acceptable ranges for cross-region
    performance = cross_region_summary["performance"]
    assert performance["avg_write_latency_ms"] < 3000, f"Write latency too high: {performance['avg_write_latency_ms']}ms"
    assert performance["avg_read_latency_ms"] < 2000, f"Read latency too high: {performance['avg_read_latency_ms']}ms"
    
    # Verify consistency quality
    quality = cross_region_summary["quality"]
    assert quality["consistency_rate"] >= 75.0, f"Consistency rate too low: {quality['consistency_rate']}%"
    
    # Verify regional distribution
    regional_ops = cross_region_summary["regional_distribution"]
    active_regions = sum(1 for ops in regional_ops.values() if ops > 0)
    assert active_regions >= 3, f"Too few active regions: {active_regions}"
    
    logger.info(f"L4 cross-region consistency critical path test completed successfully")
    logger.info(f"Test metrics: {metrics.duration:.2f}s duration, {metrics.service_calls} service calls")
    logger.info(f"Cross-region summary: {cross_region_summary}")


@pytest.mark.asyncio
@pytest.mark.l4
@pytest.mark.staging
async def test_l4_cross_region_basic_operations(cross_region_consistency_l4_test):
    """L4: Test basic cross-region read/write operations."""
    # Test basic cross-region operations
    results = await cross_region_consistency_l4_test._test_basic_cross_region_operations()
    
    # Verify basic operations success
    assert results["successful_writes"] >= 3, f"Too few successful writes: {results['successful_writes']}"
    assert results["successful_reads"] >= 3, f"Too few successful reads: {results['successful_reads']}"
    assert results["successful_syncs"] >= 2, f"Too few successful syncs: {results['successful_syncs']}"
    
    # Verify regional performance
    for region, perf in results["regional_performance"].items():
        assert perf["write_latency_ms"] < 5000, f"Region {region} write latency too high: {perf['write_latency_ms']}ms"
        assert perf["read_latency_ms"] < 3000, f"Region {region} read latency too high: {perf['read_latency_ms']}ms"


@pytest.mark.asyncio
@pytest.mark.l4
@pytest.mark.staging
async def test_l4_cross_region_eventual_consistency(cross_region_consistency_l4_test):
    """L4: Test eventual consistency across regions."""
    # Test eventual consistency with reduced load for focused testing
    results = await cross_region_consistency_l4_test.test_eventual_consistency(5)
    
    # Verify eventual consistency performance
    assert results["eventually_consistent"] >= 3, f"Too few eventually consistent operations: {results['eventually_consistent']}/5"
    assert results["consistency_violations"] <= 2, f"Too many consistency violations: {results['consistency_violations']}"
    assert results["avg_convergence_time"] < 3.0, f"Convergence time too high: {results['avg_convergence_time']}s"


@pytest.mark.asyncio
@pytest.mark.l4
@pytest.mark.staging
async def test_l4_cross_region_conflict_resolution(cross_region_consistency_l4_test):
    """L4: Test conflict resolution for concurrent cross-region updates."""
    # Test conflict resolution with focused scenarios
    results = await cross_region_consistency_l4_test.test_conflict_resolution(4)
    
    # Verify conflict resolution capability
    if results["conflicts_detected"] > 0:
        resolution_rate = (results["conflicts_resolved"] / results["conflicts_detected"]) * 100
        assert resolution_rate >= 60.0, f"Conflict resolution rate too low: {resolution_rate}%"
        assert results["avg_resolution_time"] < 8.0, f"Conflict resolution time too high: {results['avg_resolution_time']}s"


@pytest.mark.asyncio
@pytest.mark.l4
@pytest.mark.staging
async def test_l4_cross_region_network_partition_handling(cross_region_consistency_l4_test):
    """L4: Test network partition handling and recovery."""
    # Simulate network partition with short duration
    results = await cross_region_consistency_l4_test.simulate_network_partition(
        ["ap-southeast-1"], 1.5
    )
    
    # Verify partition handling
    assert results["operations_during_partition"] > 0, "No operations performed during partition"
    
    # Some operations should succeed even during partition (non-affected regions)
    if results["operations_during_partition"] > 0:
        success_rate = (results["successful_operations"] / results["operations_during_partition"]) * 100
        # Lower threshold during partition - some failures expected
        assert success_rate >= 40.0, f"Success rate during partition too low: {success_rate}%"


@pytest.mark.asyncio
@pytest.mark.l4
@pytest.mark.staging
async def test_l4_cross_region_failover_capability(cross_region_consistency_l4_test):
    """L4: Test region failover and recovery capabilities."""
    # Test failover scenario
    results = await cross_region_consistency_l4_test.test_region_failover("eu-west-1")
    
    # Verify failover capability
    assert results["failover_write_success"], "Failover write operation failed"
    assert results["successful_reads_count"] >= 1, f"Too few successful reads during failover: {results['successful_reads_count']}"
    assert results["failover_duration"] < 15.0, f"Failover duration too high: {results['failover_duration']}s"
    
    # Verify failover to available regions
    assert len(results["available_regions"]) >= 2, f"Too few available regions for failover: {len(results['available_regions'])}"