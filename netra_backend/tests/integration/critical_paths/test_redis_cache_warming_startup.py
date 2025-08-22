"""Redis Cache Warming on Startup - L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (affects all tiers as startup performance impacts conversion)
- Business Goal: Performance & User Experience (fast initial response times improve conversion)
- Value Impact: Fast initial response times reduce bounce rate and improve user satisfaction
- Revenue Impact: $35K MRR - Poor startup performance costs conversions and retention

Critical Path: System startup -> Cache warming initiation -> Source data loading -> Cache population -> Performance validation
L3 Realism: Real Redis container with actual cache warming on startup, source databases, performance monitoring
Performance Requirements: Warming completion < 30s, critical keys pre-loaded, cache hit rate > 80% after warming
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import random
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.asyncio as aioredis

from netra_backend.app.logging_config import central_logger

# Add project root to path
from netra_backend.tests.integration.helpers.redis_l3_helpers import (
    RedisContainer as NetraRedisContainer,
)

# Add project root to path

logger = central_logger.get_logger(__name__)


@dataclass
class StartupWarmingMetrics:
    """Metrics for Redis cache warming on startup testing."""
    startup_operations: int = 0
    warming_start_times: List[float] = field(default_factory=list)
    warming_completion_times: List[float] = field(default_factory=list)
    critical_keys_loaded: List[int] = field(default_factory=list)
    cache_hit_rates_post_warming: List[float] = field(default_factory=list)
    warming_memory_usage: List[int] = field(default_factory=list)
    parallel_warming_times: List[float] = field(default_factory=list)
    incremental_warming_cycles: List[Dict[str, Any]] = field(default_factory=list)
    invalidation_recovery_times: List[float] = field(default_factory=list)
    failed_warming_attempts: int = 0
    
    @property
    def avg_warming_time(self) -> float:
        """Calculate average warming completion time."""
        return statistics.mean(self.warming_completion_times) if self.warming_completion_times else 0.0
    
    @property
    def avg_cache_hit_rate(self) -> float:
        """Calculate average cache hit rate after warming."""
        return statistics.mean(self.cache_hit_rates_post_warming) if self.cache_hit_rates_post_warming else 0.0
    
    @property
    def avg_critical_keys_loaded(self) -> float:
        """Calculate average number of critical keys loaded."""
        return statistics.mean(self.critical_keys_loaded) if self.critical_keys_loaded else 0.0
    
    @property
    def warming_reliability(self) -> float:
        """Calculate warming operation reliability."""
        total_ops = self.startup_operations + self.failed_warming_attempts
        return (self.startup_operations / total_ops * 100) if total_ops > 0 else 0.0


class DatabaseSourceMock:
    """Mock database source for cache warming data."""
    
    def __init__(self, source_type: str):
        self.source_type = source_type
        self.data_sets = {
            "user_profiles": self._generate_user_profiles,
            "frequently_accessed": self._generate_frequent_data,
            "critical_configs": self._generate_critical_configs,
            "session_data": self._generate_session_data,
            "metadata_cache": self._generate_metadata
        }
    
    async def get_warming_data(self, data_type: str, limit: int = 100) -> Dict[str, Any]:
        """Get data for cache warming from source."""
        if data_type not in self.data_sets:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Simulate database query time
        await asyncio.sleep(random.uniform(0.01, 0.05))
        
        generator_func = self.data_sets[data_type]
        return await generator_func(limit)
    
    async def _generate_user_profiles(self, limit: int) -> Dict[str, Any]:
        """Generate user profile data for warming."""
        profiles = {}
        for i in range(limit):
            user_id = f"user_{i}_{uuid.uuid4().hex[:8]}"
            profiles[f"profile:{user_id}"] = {
                "user_id": user_id,
                "tier": random.choice(["free", "early", "mid", "enterprise"]),
                "last_active": datetime.utcnow().isoformat(),
                "preferences": {"theme": "dark", "notifications": True},
                "usage_stats": {"daily_requests": random.randint(10, 500)}
            }
        
        return {
            "data_type": "user_profiles",
            "count": len(profiles),
            "data": profiles,
            "priority": "high"
        }
    
    async def _generate_frequent_data(self, limit: int) -> Dict[str, Any]:
        """Generate frequently accessed data."""
        frequent_data = {}
        for i in range(limit):
            key = f"frequent:{uuid.uuid4().hex[:12]}"
            frequent_data[key] = {
                "access_count": random.randint(100, 1000),
                "last_access": datetime.utcnow().isoformat(),
                "data_size": random.randint(1024, 10240),
                "content": f"Frequently accessed content {i}"
            }
        
        return {
            "data_type": "frequently_accessed",
            "count": len(frequent_data),
            "data": frequent_data,
            "priority": "high"
        }
    
    async def _generate_critical_configs(self, limit: int) -> Dict[str, Any]:
        """Generate critical configuration data."""
        configs = {}
        config_types = ["api_limits", "feature_flags", "rate_limits", "circuit_breakers"]
        
        for i in range(limit):
            config_type = random.choice(config_types)
            key = f"config:{config_type}:{i}"
            configs[key] = {
                "type": config_type,
                "value": random.randint(100, 10000),
                "enabled": random.choice([True, False]),
                "last_updated": datetime.utcnow().isoformat()
            }
        
        return {
            "data_type": "critical_configs",
            "count": len(configs),
            "data": configs,
            "priority": "critical"
        }
    
    async def _generate_session_data(self, limit: int) -> Dict[str, Any]:
        """Generate session data for warming."""
        sessions = {}
        for i in range(limit):
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            sessions[f"session:{session_id}"] = {
                "session_id": session_id,
                "user_id": f"user_{i % 50}",  # Some overlap
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "active": True
            }
        
        return {
            "data_type": "session_data",
            "count": len(sessions),
            "data": sessions,
            "priority": "medium"
        }
    
    async def _generate_metadata(self, limit: int) -> Dict[str, Any]:
        """Generate metadata for warming."""
        metadata = {}
        for i in range(limit):
            key = f"meta:{uuid.uuid4().hex[:10]}"
            metadata[key] = {
                "schema_version": "1.0",
                "created_by": "system",
                "tags": ["cache", "metadata", f"batch_{i//10}"],
                "content_hash": uuid.uuid4().hex
            }
        
        return {
            "data_type": "metadata_cache",
            "count": len(metadata),
            "data": metadata,
            "priority": "low"
        }


class RedisCacheWarmingStartupL3Manager:
    """L3 Redis cache warming on startup test manager with real Redis and startup simulation."""
    
    def __init__(self):
        self.redis_containers = {}
        self.redis_clients = {}
        self.database_sources = {}
        self.metrics = StartupWarmingMetrics()
        self.warmed_keys = set()
        self.startup_scenarios = [
            "cold_start", "warm_restart", "crash_recovery", "deployment_update"
        ]
        
    async def setup_redis_for_startup_warming(self) -> Dict[str, str]:
        """Setup Redis instances for startup cache warming testing."""
        redis_configs = {
            "main_cache": {"port": 6420, "role": "main application cache"},
            "session_cache": {"port": 6421, "role": "session and auth cache"},
            "metadata_cache": {"port": 6422, "role": "metadata and config cache"},
            "backup_cache": {"port": 6423, "role": "backup and recovery"}
        }
        
        redis_urls = {}
        
        for name, config in redis_configs.items():
            try:
                container = NetraRedisContainer(port=config["port"])
                container.container_name = f"netra-startup-{name}-{uuid.uuid4().hex[:8]}"
                
                url = await container.start()
                
                self.redis_containers[name] = container
                redis_urls[name] = url
                
                # Create Redis client
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                self.redis_clients[name] = client
                
                logger.info(f"Redis {name} ({config['role']}) started: {url}")
                
            except Exception as e:
                logger.error(f"Failed to start Redis {name}: {e}")
                raise
        
        return redis_urls
    
    async def setup_database_sources(self) -> Dict[str, DatabaseSourceMock]:
        """Setup mock database sources for cache warming data."""
        source_types = ["postgres", "clickhouse", "config_service", "user_service"]
        
        for source_type in source_types:
            self.database_sources[source_type] = DatabaseSourceMock(source_type)
        
        logger.info(f"Database sources initialized: {list(self.database_sources.keys())}")
        return self.database_sources
    
    async def simulate_startup_cache_warming(self, scenario: str = "cold_start") -> Dict[str, Any]:
        """Simulate complete startup cache warming process."""
        start_time = time.time()
        self.metrics.warming_start_times.append(start_time)
        
        try:
            # Phase 1: Initialize warming process
            warming_plan = await self._create_warming_plan(scenario)
            
            # Phase 2: Execute warming in phases
            warming_results = await self._execute_startup_warming(warming_plan)
            
            # Phase 3: Validate warming completion
            validation_results = await self._validate_warming_completion()
            
            completion_time = time.time() - start_time
            self.metrics.warming_completion_times.append(completion_time)
            self.metrics.startup_operations += 1
            
            return {
                "scenario": scenario,
                "warming_time": completion_time,
                "warming_plan": warming_plan,
                "warming_results": warming_results,
                "validation": validation_results,
                "success": completion_time < 30.0 and validation_results["hit_rate"] > 80.0
            }
            
        except Exception as e:
            self.metrics.failed_warming_attempts += 1
            logger.error(f"Startup warming failed for {scenario}: {e}")
            raise
    
    async def _create_warming_plan(self, scenario: str) -> Dict[str, Any]:
        """Create cache warming plan based on startup scenario."""
        warming_plan = {
            "scenario": scenario,
            "phases": [],
            "priority_order": ["critical_configs", "user_profiles", "frequently_accessed", "session_data", "metadata_cache"],
            "parallel_execution": True,
            "incremental_loading": scenario in ["warm_restart", "deployment_update"]
        }
        
        # Define warming phases based on scenario
        if scenario == "cold_start":
            warming_plan["phases"] = [
                {"name": "critical_bootstrap", "data_types": ["critical_configs"], "parallel": False},
                {"name": "user_essentials", "data_types": ["user_profiles", "session_data"], "parallel": True},
                {"name": "performance_optimization", "data_types": ["frequently_accessed", "metadata_cache"], "parallel": True}
            ]
        elif scenario == "warm_restart":
            warming_plan["phases"] = [
                {"name": "validation_check", "data_types": ["critical_configs"], "parallel": False},
                {"name": "incremental_update", "data_types": ["user_profiles", "session_data"], "parallel": True}
            ]
        elif scenario == "crash_recovery":
            warming_plan["phases"] = [
                {"name": "emergency_bootstrap", "data_types": ["critical_configs", "user_profiles"], "parallel": False},
                {"name": "service_restoration", "data_types": ["frequently_accessed", "session_data"], "parallel": True},
                {"name": "full_recovery", "data_types": ["metadata_cache"], "parallel": False}
            ]
        elif scenario == "deployment_update":
            warming_plan["phases"] = [
                {"name": "config_refresh", "data_types": ["critical_configs"], "parallel": False},
                {"name": "gradual_warming", "data_types": ["user_profiles", "frequently_accessed"], "parallel": True}
            ]
        
        return warming_plan
    
    async def _execute_startup_warming(self, warming_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute startup cache warming according to plan."""
        warming_results = {
            "phases_completed": [],
            "total_keys_warmed": 0,
            "warming_errors": [],
            "phase_timings": {}
        }
        
        for phase in warming_plan["phases"]:
            phase_start = time.time()
            
            try:
                if phase["parallel"]:
                    phase_result = await self._execute_parallel_warming(phase["data_types"])
                else:
                    phase_result = await self._execute_sequential_warming(phase["data_types"])
                
                warming_results["phases_completed"].append(phase["name"])
                warming_results["total_keys_warmed"] += phase_result["keys_warmed"]
                warming_results["phase_timings"][phase["name"]] = time.time() - phase_start
                
            except Exception as e:
                warming_results["warming_errors"].append(f"Phase {phase['name']}: {e}")
                logger.error(f"Warming phase {phase['name']} failed: {e}")
        
        self.metrics.critical_keys_loaded.append(warming_results["total_keys_warmed"])
        return warming_results
    
    async def _execute_parallel_warming(self, data_types: List[str]) -> Dict[str, Any]:
        """Execute parallel cache warming for multiple data types."""
        parallel_start = time.time()
        
        warming_tasks = []
        for data_type in data_types:
            task = asyncio.create_task(self._warm_data_type(data_type))
            warming_tasks.append(task)
        
        results = await asyncio.gather(*warming_tasks, return_exceptions=True)
        
        parallel_time = time.time() - parallel_start
        self.metrics.parallel_warming_times.append(parallel_time)
        
        total_keys = sum(r["keys_warmed"] for r in results if isinstance(r, dict))
        
        return {
            "execution_type": "parallel",
            "data_types": data_types,
            "keys_warmed": total_keys,
            "execution_time": parallel_time
        }
    
    async def _execute_sequential_warming(self, data_types: List[str]) -> Dict[str, Any]:
        """Execute sequential cache warming for data types."""
        total_keys = 0
        
        for data_type in data_types:
            result = await self._warm_data_type(data_type)
            total_keys += result["keys_warmed"]
        
        return {
            "execution_type": "sequential",
            "data_types": data_types,
            "keys_warmed": total_keys
        }
    
    async def _warm_data_type(self, data_type: str) -> Dict[str, Any]:
        """Warm cache for specific data type."""
        # Get data from source
        source = self.database_sources["postgres"]  # Default source
        data_result = await source.get_warming_data(data_type, limit=50)
        
        # Select target cache based on data type
        cache_mapping = {
            "critical_configs": "metadata_cache",
            "user_profiles": "main_cache",
            "session_data": "session_cache",
            "frequently_accessed": "main_cache",
            "metadata_cache": "metadata_cache"
        }
        
        target_cache = cache_mapping.get(data_type, "main_cache")
        cache_client = self.redis_clients[target_cache]
        
        # Warm cache with data
        keys_warmed = 0
        data_entries = data_result["data"]
        
        # Use pipeline for efficiency
        pipe = cache_client.pipeline()
        
        for key, value in data_entries.items():
            try:
                cache_value = json.dumps(value)
                
                # Set TTL based on priority
                priority = data_result["priority"]
                if priority == "critical":
                    ttl = 86400  # 24 hours
                elif priority == "high":
                    ttl = 21600  # 6 hours
                elif priority == "medium":
                    ttl = 7200   # 2 hours
                else:
                    ttl = 3600   # 1 hour
                
                pipe.setex(key, ttl, cache_value)
                self.warmed_keys.add(key)
                keys_warmed += 1
                
            except Exception as e:
                logger.error(f"Failed to warm key {key}: {e}")
        
        # Execute pipeline
        await pipe.execute()
        
        return {
            "data_type": data_type,
            "keys_warmed": keys_warmed,
            "target_cache": target_cache
        }
    
    async def _validate_warming_completion(self) -> Dict[str, Any]:
        """Validate that cache warming completed successfully."""
        validation_results = {
            "critical_keys_present": 0,
            "total_keys_checked": 0,
            "hit_rate": 0.0,
            "memory_usage": {},
            "cache_distribution": {}
        }
        
        # Test cache hit rate
        test_keys = list(self.warmed_keys)[:100]  # Sample test
        hits = 0
        
        for key in test_keys:
            # Determine which cache should have this key
            for cache_name, client in self.redis_clients.items():
                try:
                    result = await client.get(key)
                    if result:
                        hits += 1
                        break
                except Exception:
                    continue
        
        hit_rate = (hits / len(test_keys) * 100) if test_keys else 0.0
        self.metrics.cache_hit_rates_post_warming.append(hit_rate)
        validation_results["hit_rate"] = hit_rate
        validation_results["total_keys_checked"] = len(test_keys)
        validation_results["critical_keys_present"] = hits
        
        # Check memory usage
        for cache_name, client in self.redis_clients.items():
            try:
                info = await client.info('memory')
                memory_used = info.get('used_memory', 0)
                validation_results["memory_usage"][cache_name] = memory_used
                self.metrics.warming_memory_usage.append(memory_used)
            except Exception:
                validation_results["memory_usage"][cache_name] = 0
        
        return validation_results
    
    async def test_incremental_cache_warming(self) -> Dict[str, Any]:
        """Test incremental cache warming strategy."""
        incremental_cycles = []
        
        # Initial warming
        initial_result = await self.simulate_startup_cache_warming("cold_start")
        
        # Simulate incremental warming cycles
        for cycle in range(3):
            cycle_start = time.time()
            
            # Add new data to sources
            source = self.database_sources["postgres"]
            new_data = await source.get_warming_data("user_profiles", limit=20)
            
            # Warm new data incrementally
            warming_result = await self._warm_data_type("user_profiles")
            
            cycle_time = time.time() - cycle_start
            
            cycle_result = {
                "cycle": cycle + 1,
                "new_keys_warmed": warming_result["keys_warmed"],
                "cycle_time": cycle_time,
                "success": cycle_time < 5.0  # Incremental should be fast
            }
            
            incremental_cycles.append(cycle_result)
        
        self.metrics.incremental_warming_cycles.extend(incremental_cycles)
        
        return {
            "initial_warming": initial_result,
            "incremental_cycles": incremental_cycles,
            "total_cycles": len(incremental_cycles),
            "avg_incremental_time": statistics.mean([c["cycle_time"] for c in incremental_cycles])
        }
    
    async def test_cache_invalidation_handling(self) -> Dict[str, Any]:
        """Test cache warming with invalidation scenarios."""
        # Initial warming
        await self.simulate_startup_cache_warming("cold_start")
        
        # Simulate cache invalidation
        invalidation_start = time.time()
        
        # Clear random cache sections
        cache_to_clear = random.choice(list(self.redis_clients.keys()))
        client = self.redis_clients[cache_to_clear]
        
        # Clear some keys (simulate invalidation)
        keys_to_clear = list(self.warmed_keys)[:20]
        if keys_to_clear:
            await client.delete(*keys_to_clear)
        
        # Re-warm invalidated cache
        rewarm_start = time.time()
        rewarm_result = await self._warm_data_type("user_profiles")
        rewarm_time = time.time() - rewarm_start
        
        total_recovery_time = time.time() - invalidation_start
        self.metrics.invalidation_recovery_times.append(total_recovery_time)
        
        return {
            "invalidated_cache": cache_to_clear,
            "keys_invalidated": len(keys_to_clear),
            "rewarm_time": rewarm_time,
            "total_recovery_time": total_recovery_time,
            "recovery_success": total_recovery_time < 10.0
        }
    
    async def test_parallel_cache_warming_efficiency(self) -> Dict[str, Any]:
        """Test efficiency of parallel cache warming."""
        # Test sequential vs parallel warming
        
        # Sequential timing
        sequential_start = time.time()
        await self._execute_sequential_warming(["user_profiles", "frequently_accessed", "session_data"])
        sequential_time = time.time() - sequential_start
        
        # Clear caches
        for client in self.redis_clients.values():
            await client.flushdb()
        
        # Parallel timing
        parallel_start = time.time()
        await self._execute_parallel_warming(["user_profiles", "frequently_accessed", "session_data"])
        parallel_time = time.time() - parallel_start
        
        efficiency_improvement = ((sequential_time - parallel_time) / sequential_time * 100) if sequential_time > 0 else 0
        
        return {
            "sequential_time": sequential_time,
            "parallel_time": parallel_time,
            "efficiency_improvement": efficiency_improvement,
            "parallel_advantage": parallel_time < sequential_time,
            "performance_gain": f"{efficiency_improvement:.1f}%"
        }
    
    def get_startup_warming_summary(self) -> Dict[str, Any]:
        """Get comprehensive startup cache warming test summary."""
        return {
            "startup_metrics": {
                "startup_operations": self.metrics.startup_operations,
                "avg_warming_time": self.metrics.avg_warming_time,
                "avg_cache_hit_rate": self.metrics.avg_cache_hit_rate,
                "avg_critical_keys_loaded": self.metrics.avg_critical_keys_loaded,
                "warming_reliability": self.metrics.warming_reliability
            },
            "sla_compliance": {
                "warming_under_30s": self.metrics.avg_warming_time < 30.0,
                "hit_rate_above_80": self.metrics.avg_cache_hit_rate > 80.0,
                "critical_keys_loaded": self.metrics.avg_critical_keys_loaded > 100,
                "reliability_above_95": self.metrics.warming_reliability > 95.0
            },
            "performance_insights": {
                "parallel_warming_available": len(self.metrics.parallel_warming_times) > 0,
                "incremental_warming_tested": len(self.metrics.incremental_warming_cycles) > 0,
                "invalidation_recovery_tested": len(self.metrics.invalidation_recovery_times) > 0
            },
            "recommendations": self._generate_startup_warming_recommendations()
        }
    
    def _generate_startup_warming_recommendations(self) -> List[str]:
        """Generate startup cache warming recommendations."""
        recommendations = []
        
        if self.metrics.avg_warming_time > 30.0:
            recommendations.append(f"Warming time {self.metrics.avg_warming_time:.1f}s exceeds 30s - optimize warming strategy")
        
        if self.metrics.avg_cache_hit_rate < 80.0:
            recommendations.append(f"Cache hit rate {self.metrics.avg_cache_hit_rate:.1f}% below 80% - review data selection")
        
        if self.metrics.avg_critical_keys_loaded < 100:
            recommendations.append(f"Critical keys loaded {self.metrics.avg_critical_keys_loaded:.0f} below target - increase warming scope")
        
        if self.metrics.warming_reliability < 95.0:
            recommendations.append(f"Warming reliability {self.metrics.warming_reliability:.1f}% below 95% - improve error handling")
        
        if self.metrics.failed_warming_attempts > 0:
            recommendations.append(f"{self.metrics.failed_warming_attempts} warming attempts failed - review failure patterns")
        
        if len(self.metrics.parallel_warming_times) > 0:
            avg_parallel_time = statistics.mean(self.metrics.parallel_warming_times)
            if avg_parallel_time > 15.0:
                recommendations.append(f"Parallel warming time {avg_parallel_time:.1f}s too high - optimize concurrency")
        
        if not recommendations:
            recommendations.append("All startup cache warming metrics meet SLA requirements")
        
        return recommendations
    
    async def cleanup(self):
        """Clean up Redis containers and test resources."""
        try:
            # Clean up warmed keys
            for key in self.warmed_keys:
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
            logger.error(f"Startup warming cleanup failed: {e}")


@pytest.fixture
async def startup_warming_manager():
    """Create L3 Redis cache warming startup manager."""
    manager = RedisCacheWarmingStartupL3Manager()
    await manager.setup_redis_for_startup_warming()
    await manager.setup_database_sources()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_redis_cache_warming_on_startup_l3(startup_warming_manager):
    """L3: Test Redis cache warming completes on startup."""
    result = await startup_warming_manager.simulate_startup_cache_warming("cold_start")
    
    # Verify warming completion time
    assert result["warming_time"] < 30.0, f"Cache warming time {result['warming_time']:.1f}s exceeds 30s limit"
    
    # Verify warming success
    assert result["success"], f"Cache warming failed: {result}"
    
    # Verify critical keys loaded
    warming_results = result["warming_results"]
    assert warming_results["total_keys_warmed"] > 100, f"Insufficient keys warmed: {warming_results['total_keys_warmed']}"
    
    # Verify cache hit rate
    validation = result["validation"]
    assert validation["hit_rate"] > 80.0, f"Cache hit rate {validation['hit_rate']:.1f}% below 80%"
    
    logger.info(f"Startup warming completed in {result['warming_time']:.1f}s with {validation['hit_rate']:.1f}% hit rate")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_critical_data_preloaded_startup(startup_warming_manager):
    """L3: Test critical data is correctly pre-loaded during startup."""
    result = await startup_warming_manager.simulate_startup_cache_warming("cold_start")
    
    # Verify critical configuration data is loaded first
    warming_plan = result["warming_plan"]
    first_phase = warming_plan["phases"][0]
    assert "critical_configs" in first_phase["data_types"], "Critical configs not in first warming phase"
    
    # Verify critical keys are accessible
    validation = result["validation"]
    assert validation["critical_keys_present"] > 0, "No critical keys found in cache after warming"
    
    # Test access to critical configuration
    config_client = startup_warming_manager.redis_clients["metadata_cache"]
    config_keys = [k for k in startup_warming_manager.warmed_keys if k.startswith("config:")]
    
    if config_keys:
        sample_config = await config_client.get(config_keys[0])
        assert sample_config is not None, "Critical config key not accessible after warming"
        
        config_data = json.loads(sample_config)
        assert "type" in config_data, "Critical config data structure invalid"
    
    logger.info(f"Critical data preloading verified: {validation['critical_keys_present']} keys accessible")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cache_hit_rate_after_warming(startup_warming_manager):
    """L3: Test cache hit rate exceeds 80% after warming."""
    result = await startup_warming_manager.simulate_startup_cache_warming("cold_start")
    
    # Initial hit rate validation
    validation = result["validation"]
    initial_hit_rate = validation["hit_rate"]
    assert initial_hit_rate > 80.0, f"Initial hit rate {initial_hit_rate:.1f}% below 80%"
    
    # Extended hit rate testing with more samples
    test_keys = list(startup_warming_manager.warmed_keys)[:200]
    hits = 0
    total_tests = 0
    
    for key in test_keys:
        for client in startup_warming_manager.redis_clients.values():
            try:
                result_val = await client.get(key)
                total_tests += 1
                if result_val:
                    hits += 1
                    break
            except Exception:
                total_tests += 1
    
    extended_hit_rate = (hits / total_tests * 100) if total_tests > 0 else 0.0
    assert extended_hit_rate > 80.0, f"Extended hit rate {extended_hit_rate:.1f}% below 80%"
    
    # Verify hit rate consistency
    assert abs(initial_hit_rate - extended_hit_rate) < 20.0, "Hit rate inconsistency detected"
    
    logger.info(f"Cache hit rate validation: initial {initial_hit_rate:.1f}%, extended {extended_hit_rate:.1f}%")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_warming_time_under_30_seconds(startup_warming_manager):
    """L3: Test cache warming completes within 30 seconds."""
    scenarios = ["cold_start", "warm_restart", "deployment_update"]
    
    for scenario in scenarios:
        result = await startup_warming_manager.simulate_startup_cache_warming(scenario)
        
        warming_time = result["warming_time"]
        assert warming_time < 30.0, f"Warming time for {scenario}: {warming_time:.1f}s exceeds 30s"
        
        # Verify warming actually completed
        assert result["success"], f"Warming failed for scenario {scenario}"
        
        # Clear caches between scenarios
        for client in startup_warming_manager.redis_clients.values():
            await client.flushdb()
        startup_warming_manager.warmed_keys.clear()
    
    # Verify average warming time
    avg_time = startup_warming_manager.metrics.avg_warming_time
    assert avg_time < 25.0, f"Average warming time {avg_time:.1f}s approaches 30s limit"
    
    logger.info(f"Warming time validation completed: average {avg_time:.1f}s across scenarios")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_parallel_warming_efficiency(startup_warming_manager):
    """L3: Test parallel warming of multiple caches."""
    result = await startup_warming_manager.test_parallel_cache_warming_efficiency()
    
    # Verify parallel execution is more efficient
    assert result["parallel_advantage"], f"Parallel warming not faster: {result['parallel_time']:.1f}s vs {result['sequential_time']:.1f}s"
    
    # Verify efficiency improvement
    efficiency_improvement = result["efficiency_improvement"]
    assert efficiency_improvement > 20.0, f"Parallel efficiency improvement {efficiency_improvement:.1f}% too low"
    
    # Verify parallel warming time is reasonable
    parallel_time = result["parallel_time"]
    assert parallel_time < 20.0, f"Parallel warming time {parallel_time:.1f}s too high"
    
    logger.info(f"Parallel warming efficiency: {efficiency_improvement:.1f}% improvement, {parallel_time:.1f}s execution")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_incremental_warming_strategy(startup_warming_manager):
    """L3: Test incremental cache warming strategy."""
    result = await startup_warming_manager.test_incremental_cache_warming()
    
    # Verify incremental cycles completed
    incremental_cycles = result["incremental_cycles"]
    assert len(incremental_cycles) >= 3, f"Insufficient incremental cycles: {len(incremental_cycles)}"
    
    # Verify incremental warming is fast
    avg_incremental_time = result["avg_incremental_time"]
    assert avg_incremental_time < 5.0, f"Incremental warming too slow: {avg_incremental_time:.1f}s"
    
    # Verify all cycles succeeded
    failed_cycles = [c for c in incremental_cycles if not c["success"]]
    assert len(failed_cycles) == 0, f"Incremental warming cycles failed: {failed_cycles}"
    
    # Verify incremental adds new keys
    for cycle in incremental_cycles:
        assert cycle["new_keys_warmed"] > 0, f"Incremental cycle {cycle['cycle']} warmed no new keys"
    
    logger.info(f"Incremental warming validated: {len(incremental_cycles)} cycles, avg {avg_incremental_time:.1f}s")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_cache_invalidation_recovery(startup_warming_manager):
    """L3: Test cache warming handles invalidation scenarios."""
    result = await startup_warming_manager.test_cache_invalidation_handling()
    
    # Verify invalidation was handled
    assert result["keys_invalidated"] > 0, "No keys were invalidated for testing"
    
    # Verify recovery time is acceptable
    recovery_time = result["total_recovery_time"]
    assert recovery_time < 10.0, f"Cache invalidation recovery time {recovery_time:.1f}s too high"
    
    # Verify recovery succeeded
    assert result["recovery_success"], f"Cache invalidation recovery failed: {result}"
    
    # Verify re-warming completed
    rewarm_time = result["rewarm_time"]
    assert rewarm_time < 5.0, f"Cache re-warming time {rewarm_time:.1f}s too high"
    
    logger.info(f"Invalidation recovery validated: {recovery_time:.1f}s total, {rewarm_time:.1f}s rewarm")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_memory_usage_within_limits(startup_warming_manager):
    """L3: Test cache warming memory usage stays within limits."""
    await startup_warming_manager.simulate_startup_cache_warming("cold_start")
    
    # Check memory usage for each cache
    total_memory = 0
    for cache_name, client in startup_warming_manager.redis_clients.items():
        try:
            info = await client.info('memory')
            memory_used = info.get('used_memory', 0)
            
            # Individual cache memory limit (50MB per cache)
            assert memory_used < 50 * 1024 * 1024, f"Cache {cache_name} memory usage {memory_used} exceeds 50MB limit"
            
            total_memory += memory_used
            
        except Exception as e:
            logger.warning(f"Could not check memory for {cache_name}: {e}")
    
    # Total memory limit (200MB across all caches)
    assert total_memory < 200 * 1024 * 1024, f"Total cache memory usage {total_memory} exceeds 200MB limit"
    
    # Verify memory tracking
    assert len(startup_warming_manager.metrics.warming_memory_usage) > 0, "No memory usage tracked"
    
    logger.info(f"Memory usage validation completed: {total_memory / (1024*1024):.1f}MB total")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_startup_warming_sla_compliance(startup_warming_manager):
    """L3: Test comprehensive startup cache warming SLA compliance."""
    # Execute multiple warming scenarios
    scenarios = ["cold_start", "warm_restart", "crash_recovery"]
    for scenario in scenarios:
        await startup_warming_manager.simulate_startup_cache_warming(scenario)
        
        # Clear between scenarios for independent testing
        for client in startup_warming_manager.redis_clients.values():
            await client.flushdb()
        startup_warming_manager.warmed_keys.clear()
    
    # Test advanced scenarios
    await startup_warming_manager.test_incremental_cache_warming()
    await startup_warming_manager.test_cache_invalidation_handling()
    
    # Get comprehensive summary
    summary = startup_warming_manager.get_startup_warming_summary()
    
    # Verify SLA compliance
    sla = summary["sla_compliance"]
    assert sla["warming_under_30s"], f"Warming time SLA violation: {startup_warming_manager.metrics.avg_warming_time:.1f}s"
    assert sla["hit_rate_above_80"], f"Hit rate SLA violation: {startup_warming_manager.metrics.avg_cache_hit_rate:.1f}%"
    assert sla["critical_keys_loaded"], f"Critical keys SLA violation: {startup_warming_manager.metrics.avg_critical_keys_loaded:.0f}"
    assert sla["reliability_above_95"], f"Reliability SLA violation: {startup_warming_manager.metrics.warming_reliability:.1f}%"
    
    # Verify overall performance
    assert startup_warming_manager.metrics.failed_warming_attempts == 0, f"Warming attempts failed: {startup_warming_manager.metrics.failed_warming_attempts}"
    assert startup_warming_manager.metrics.startup_operations >= 3, f"Insufficient startup operations tested: {startup_warming_manager.metrics.startup_operations}"
    
    # Verify no critical recommendations
    critical_recommendations = [r for r in summary["recommendations"] if "exceeds" in r or "below" in r]
    assert len(critical_recommendations) == 0, f"Critical startup warming issues: {critical_recommendations}"
    
    logger.info(f"Startup cache warming SLA compliance verified successfully")
    logger.info(f"Summary: {summary}")