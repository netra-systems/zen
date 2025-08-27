"""
Test Caching Performance Strategies - Iteration 64

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Response Time Optimization
- Value Impact: Improves user experience through faster data access
- Strategic Impact: Reduces computational costs and increases throughput

Focus: Multi-level caching, cache coherence, and intelligent eviction
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time
import hashlib
from datetime import datetime, timedelta
import random
import statistics

from netra_backend.app.core.async_resource_manager import AsyncResourceManager


class TestCachingPerformanceStrategies:
    """Test caching performance strategies and effectiveness"""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock multi-level cache manager"""
        manager = MagicMock()
        manager.l1_cache = {}  # Memory cache
        manager.l2_cache = {}  # Redis-like distributed cache  
        manager.l3_cache = {}  # Database/persistent cache
        manager.cache_stats = {
            "l1_hits": 0, "l1_misses": 0,
            "l2_hits": 0, "l2_misses": 0,
            "l3_hits": 0, "l3_misses": 0
        }
        return manager
    
    @pytest.fixture
    def mock_eviction_policy(self):
        """Mock cache eviction policy manager"""
        policy = MagicMock()
        policy.lru_tracker = {}
        policy.lfu_tracker = {}
        policy.ttl_tracker = {}
        return policy
    
    @pytest.mark.asyncio
    async def test_multi_level_caching_performance(self, mock_cache_manager):
        """Test multi-level caching hierarchy performance"""
        
        async def multi_level_cache_get(key):
            """Simulate multi-level cache retrieval"""
            access_start = time.time()
            
            # L1 Cache (Memory) - Fastest
            if key in mock_cache_manager.l1_cache:
                mock_cache_manager.cache_stats["l1_hits"] += 1
                await asyncio.sleep(0.0001)  # 0.1ms access time
                return {
                    "data": mock_cache_manager.l1_cache[key]["data"],
                    "cache_level": "L1",
                    "access_time_ms": (time.time() - access_start) * 1000
                }
            
            mock_cache_manager.cache_stats["l1_misses"] += 1
            
            # L2 Cache (Distributed) - Medium speed
            if key in mock_cache_manager.l2_cache:
                mock_cache_manager.cache_stats["l2_hits"] += 1
                await asyncio.sleep(0.002)  # 2ms access time (network)
                
                # Promote to L1 cache
                l2_data = mock_cache_manager.l2_cache[key]
                mock_cache_manager.l1_cache[key] = {
                    "data": l2_data["data"],
                    "promoted_from": "L2",
                    "timestamp": time.time()
                }
                
                return {
                    "data": l2_data["data"],
                    "cache_level": "L2",
                    "access_time_ms": (time.time() - access_start) * 1000
                }
            
            mock_cache_manager.cache_stats["l2_misses"] += 1
            
            # L3 Cache (Database/Persistent) - Slowest
            if key in mock_cache_manager.l3_cache:
                mock_cache_manager.cache_stats["l3_hits"] += 1
                await asyncio.sleep(0.01)  # 10ms access time (disk I/O)
                
                # Populate L2 and L1 caches
                l3_data = mock_cache_manager.l3_cache[key]
                
                mock_cache_manager.l2_cache[key] = {
                    "data": l3_data["data"],
                    "promoted_from": "L3",
                    "timestamp": time.time()
                }
                
                mock_cache_manager.l1_cache[key] = {
                    "data": l3_data["data"],
                    "promoted_from": "L3",
                    "timestamp": time.time()
                }
                
                return {
                    "data": l3_data["data"],
                    "cache_level": "L3",
                    "access_time_ms": (time.time() - access_start) * 1000
                }
            
            mock_cache_manager.cache_stats["l3_misses"] += 1
            
            # Cache miss - simulate expensive data generation
            await asyncio.sleep(0.05)  # 50ms generation time
            generated_data = f"generated_data_for_{key}_{time.time()}"
            
            # Store in all cache levels
            cache_entry = {"data": generated_data, "generated_at": time.time()}
            mock_cache_manager.l3_cache[key] = cache_entry
            mock_cache_manager.l2_cache[key] = cache_entry
            mock_cache_manager.l1_cache[key] = cache_entry
            
            return {
                "data": generated_data,
                "cache_level": "MISS",
                "access_time_ms": (time.time() - access_start) * 1000
            }
        
        # Test cache hierarchy with different access patterns
        async def test_cache_access_pattern(access_pattern):
            """Test specific cache access pattern"""
            pattern_results = []
            
            for request in access_pattern:
                key = request["key"]
                result = await multi_level_cache_get(key)
                pattern_results.append({
                    "key": key,
                    "cache_level": result["cache_level"],
                    "access_time_ms": result["access_time_ms"]
                })
            
            return pattern_results
        
        # Hot data pattern (frequent access to same keys)
        hot_pattern = [{"key": f"hot_key_{i % 5}"} for i in range(50)]  # 5 keys accessed 10 times each
        hot_results = await test_cache_access_pattern(hot_pattern)
        
        # Should show high L1 cache hit rate after initial misses
        l1_hits_hot = len([r for r in hot_results if r["cache_level"] == "L1"])
        total_hot_requests = len(hot_results)
        hot_l1_hit_rate = l1_hits_hot / total_hot_requests
        
        assert hot_l1_hit_rate > 0.7  # Should achieve > 70% L1 hit rate
        
        # Average access time should be low due to L1 hits
        avg_hot_access_time = statistics.mean([r["access_time_ms"] for r in hot_results])
        assert avg_hot_access_time < 5  # Should average < 5ms
        
        # Cold data pattern (unique keys each time)
        cold_pattern = [{"key": f"cold_key_{i}"} for i in range(30)]  # 30 unique keys
        cold_results = await test_cache_access_pattern(cold_pattern)
        
        # Should show mostly cache misses
        misses_cold = len([r for r in cold_results if r["cache_level"] == "MISS"])
        cold_miss_rate = misses_cold / len(cold_results)
        
        assert cold_miss_rate > 0.8  # Should have > 80% miss rate for unique keys
        
        # Average access time should be higher due to misses
        avg_cold_access_time = statistics.mean([r["access_time_ms"] for r in cold_results])
        assert avg_cold_access_time > avg_hot_access_time  # Should be slower than hot pattern
        
        # Mixed pattern (combination of hot and cold)
        mixed_pattern = (
            [{"key": f"hot_key_{i % 3}"} for i in range(20)] +  # Some hot keys
            [{"key": f"unique_key_{i}"} for i in range(15)]     # Some unique keys
        )
        mixed_results = await test_cache_access_pattern(mixed_pattern)
        
        # Should show balanced cache performance
        mixed_l1_hits = len([r for r in mixed_results if r["cache_level"] == "L1"])
        mixed_l1_hit_rate = mixed_l1_hits / len(mixed_results)
        
        assert 0.3 < mixed_l1_hit_rate < 0.8  # Should be between hot and cold patterns
    
    @pytest.mark.asyncio
    async def test_cache_eviction_algorithms(self, mock_cache_manager, mock_eviction_policy):
        """Test different cache eviction algorithms performance"""
        
        class CacheWithEviction:
            def __init__(self, max_size, eviction_policy="LRU"):
                self.max_size = max_size
                self.eviction_policy = eviction_policy
                self.data = {}
                self.access_order = []  # For LRU
                self.access_frequency = {}  # For LFU
                self.access_times = {}  # For TTL
                self.evictions = 0
            
            async def get(self, key):
                if key in self.data:
                    self._record_access(key)
                    return self.data[key]
                return None
            
            async def put(self, key, value, ttl=None):
                # If cache is full, evict based on policy
                if len(self.data) >= self.max_size and key not in self.data:
                    await self._evict_one()
                
                self.data[key] = value
                self._record_access(key)
                
                if ttl:
                    self.access_times[key] = time.time() + ttl
            
            def _record_access(self, key):
                current_time = time.time()
                
                # Update LRU tracking
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                
                # Update LFU tracking
                self.access_frequency[key] = self.access_frequency.get(key, 0) + 1
                
                # Update access time for TTL
                if key not in self.access_times:
                    self.access_times[key] = current_time
            
            async def _evict_one(self):
                if not self.data:
                    return
                
                evict_key = None
                
                if self.eviction_policy == "LRU":
                    # Evict least recently used
                    evict_key = self.access_order[0] if self.access_order else None
                
                elif self.eviction_policy == "LFU":
                    # Evict least frequently used
                    evict_key = min(self.access_frequency.keys(), 
                                  key=lambda k: self.access_frequency[k])
                
                elif self.eviction_policy == "TTL":
                    # Evict expired items first, then oldest
                    current_time = time.time()
                    expired_keys = [k for k, expiry in self.access_times.items() 
                                  if expiry < current_time]
                    
                    if expired_keys:
                        evict_key = expired_keys[0]
                    else:
                        evict_key = min(self.access_times.keys(), 
                                      key=lambda k: self.access_times[k])
                
                elif self.eviction_policy == "RANDOM":
                    # Random eviction
                    evict_key = random.choice(list(self.data.keys()))
                
                if evict_key:
                    del self.data[evict_key]
                    if evict_key in self.access_order:
                        self.access_order.remove(evict_key)
                    self.access_frequency.pop(evict_key, None)
                    self.access_times.pop(evict_key, None)
                    self.evictions += 1
            
            def get_stats(self):
                return {
                    "size": len(self.data),
                    "evictions": self.evictions,
                    "eviction_policy": self.eviction_policy
                }
        
        async def test_eviction_policy_performance(policy, workload_pattern):
            """Test specific eviction policy with workload pattern"""
            cache = CacheWithEviction(max_size=20, eviction_policy=policy)
            
            hits = 0
            misses = 0
            access_times = []
            
            for operation in workload_pattern:
                start_time = time.time()
                
                if operation["type"] == "get":
                    result = await cache.get(operation["key"])
                    if result is not None:
                        hits += 1
                    else:
                        misses += 1
                
                elif operation["type"] == "put":
                    await cache.put(operation["key"], operation["value"], 
                                  operation.get("ttl"))
                
                access_time = (time.time() - start_time) * 1000
                access_times.append(access_time)
            
            stats = cache.get_stats()
            stats.update({
                "hits": hits,
                "misses": misses,
                "hit_rate": hits / max(1, hits + misses),
                "avg_access_time_ms": statistics.mean(access_times),
                "total_operations": len(workload_pattern)
            })
            
            return stats
        
        # Test different eviction policies with the same workload
        workload = []
        
        # Phase 1: Fill cache
        for i in range(25):  # Exceed cache size of 20
            workload.append({"type": "put", "key": f"key_{i}", "value": f"value_{i}"})
        
        # Phase 2: Access some keys repeatedly (create hot keys)
        for i in range(50):
            hot_key = f"key_{i % 5}"  # Access first 5 keys repeatedly
            workload.append({"type": "get", "key": hot_key})
        
        # Phase 3: Add new keys (force evictions)
        for i in range(25, 40):
            workload.append({"type": "put", "key": f"new_key_{i}", "value": f"new_value_{i}"})
        
        # Phase 4: Access mix of old and new keys
        for i in range(30):
            key = f"key_{i % 10}" if i % 2 == 0 else f"new_key_{25 + (i % 5)}"
            workload.append({"type": "get", "key": key})
        
        # Test all eviction policies
        eviction_policies = ["LRU", "LFU", "TTL", "RANDOM"]
        policy_results = []
        
        for policy in eviction_policies:
            result = await test_eviction_policy_performance(policy, workload)
            policy_results.append(result)
        
        # Analyze eviction policy effectiveness
        lru_result = next(r for r in policy_results if r["eviction_policy"] == "LRU")
        lfu_result = next(r for r in policy_results if r["eviction_policy"] == "LFU")
        random_result = next(r for r in policy_results if r["eviction_policy"] == "RANDOM")
        
        # LRU should perform well with temporal locality
        assert lru_result["hit_rate"] > 0.3  # Should achieve reasonable hit rate
        
        # LFU should perform well with frequency-based access patterns
        assert lfu_result["hit_rate"] > 0.25  # Should handle hot keys well
        
        # Random should perform worse than intelligent policies
        assert lru_result["hit_rate"] > random_result["hit_rate"]
        assert lfu_result["hit_rate"] > random_result["hit_rate"]
        
        # All policies should maintain cache size limit
        for result in policy_results:
            assert result["size"] <= 20  # Should not exceed max_size
            assert result["evictions"] > 0  # Should have performed evictions
    
    @pytest.mark.asyncio
    async def test_cache_coherence_strategies(self, mock_cache_manager):
        """Test cache coherence and consistency strategies"""
        
        class DistributedCache:
            def __init__(self, node_id):
                self.node_id = node_id
                self.local_cache = {}
                self.version_vector = {}  # For versioning
                self.invalidation_log = []
                self.coherence_messages = []
            
            async def put(self, key, value, broadcast=True):
                """Put value and maintain coherence"""
                # Update local cache
                version = self.version_vector.get(key, 0) + 1
                self.version_vector[key] = version
                
                self.local_cache[key] = {
                    "value": value,
                    "version": version,
                    "timestamp": time.time(),
                    "node_id": self.node_id
                }
                
                # Broadcast invalidation to other nodes
                if broadcast:
                    invalidation_msg = {
                        "type": "invalidate",
                        "key": key,
                        "version": version,
                        "from_node": self.node_id,
                        "timestamp": time.time()
                    }
                    self.coherence_messages.append(invalidation_msg)
                    return invalidation_msg
                
                return None
            
            async def get(self, key):
                """Get value with coherence checks"""
                if key in self.local_cache:
                    entry = self.local_cache[key]
                    return {
                        "value": entry["value"],
                        "version": entry["version"],
                        "cache_hit": True,
                        "node_id": self.node_id
                    }
                
                return {"cache_hit": False, "node_id": self.node_id}
            
            async def handle_invalidation(self, invalidation_msg):
                """Handle invalidation message from other nodes"""
                key = invalidation_msg["key"]
                remote_version = invalidation_msg["version"]
                
                if key in self.local_cache:
                    local_version = self.local_cache[key]["version"]
                    
                    if remote_version > local_version:
                        # Remote version is newer, invalidate local
                        del self.local_cache[key]
                        self.invalidation_log.append({
                            "key": key,
                            "action": "invalidated",
                            "local_version": local_version,
                            "remote_version": remote_version,
                            "timestamp": time.time()
                        })
                        return "invalidated"
                    elif remote_version < local_version:
                        # Local version is newer, ignore
                        return "ignored_older"
                    else:
                        # Same version, check timestamp for tie-breaking
                        remote_timestamp = invalidation_msg["timestamp"]
                        local_timestamp = self.local_cache[key]["timestamp"]
                        
                        if remote_timestamp > local_timestamp:
                            del self.local_cache[key]
                            self.invalidation_log.append({
                                "key": key,
                                "action": "invalidated_by_timestamp",
                                "timestamp": time.time()
                            })
                            return "invalidated_by_timestamp"
                        
                        return "ignored_same_version"
                
                return "key_not_found"
            
            def get_coherence_stats(self):
                return {
                    "node_id": self.node_id,
                    "cache_size": len(self.local_cache),
                    "invalidations_received": len(self.invalidation_log),
                    "coherence_messages_sent": len(self.coherence_messages),
                    "invalidation_types": {}
                }
        
        async def test_cache_coherence_scenario(scenario_operations):
            """Test cache coherence under specific scenarios"""
            # Create 3 distributed cache nodes
            nodes = [
                DistributedCache("node_1"),
                DistributedCache("node_2"), 
                DistributedCache("node_3")
            ]
            
            coherence_events = []
            
            for operation in scenario_operations:
                if operation["type"] == "write":
                    node_id = operation["node"]
                    node = nodes[node_id]
                    key = operation["key"]
                    value = operation["value"]
                    
                    # Perform write
                    invalidation_msg = await node.put(key, value)
                    
                    # Simulate broadcast to other nodes
                    if invalidation_msg:
                        for i, other_node in enumerate(nodes):
                            if i != node_id:
                                result = await other_node.handle_invalidation(invalidation_msg)
                                coherence_events.append({
                                    "from_node": node_id,
                                    "to_node": i,
                                    "key": key,
                                    "action": result
                                })
                
                elif operation["type"] == "read":
                    node_id = operation["node"]
                    node = nodes[node_id]
                    key = operation["key"]
                    
                    result = await node.get(key)
                    coherence_events.append({
                        "operation": "read",
                        "node": node_id,
                        "key": key,
                        "cache_hit": result["cache_hit"]
                    })
                
                # Simulate processing delay
                await asyncio.sleep(0.001)
            
            # Collect final stats
            node_stats = [node.get_coherence_stats() for node in nodes]
            
            return {
                "coherence_events": coherence_events,
                "node_stats": node_stats,
                "total_invalidations": sum(len(node.invalidation_log) for node in nodes),
                "total_coherence_messages": sum(len(node.coherence_messages) for node in nodes)
            }
        
        # Test write-intensive workload with coherence
        write_intensive_ops = [
            {"type": "write", "node": 0, "key": "shared_key_1", "value": "value_1_v1"},
            {"type": "write", "node": 1, "key": "shared_key_1", "value": "value_1_v2"},
            {"type": "read", "node": 0, "key": "shared_key_1"},
            {"type": "read", "node": 2, "key": "shared_key_1"},
            {"type": "write", "node": 2, "key": "shared_key_1", "value": "value_1_v3"},
            {"type": "read", "node": 0, "key": "shared_key_1"},
            {"type": "read", "node": 1, "key": "shared_key_1"}
        ]
        
        write_results = await test_cache_coherence_scenario(write_intensive_ops)
        
        # Should show coherence maintenance
        assert write_results["total_invalidations"] > 0  # Should have invalidations
        assert write_results["total_coherence_messages"] > 0  # Should send coherence messages
        
        # Check that invalidations occurred
        invalidation_events = [e for e in write_results["coherence_events"] 
                             if e.get("action") in ["invalidated", "invalidated_by_timestamp"]]
        assert len(invalidation_events) > 0  # Should have successful invalidations
        
        # Test read-heavy workload
        read_heavy_ops = [
            {"type": "write", "node": 0, "key": "read_key_1", "value": "stable_value"},
            {"type": "read", "node": 0, "key": "read_key_1"},
            {"type": "read", "node": 1, "key": "read_key_1"},
            {"type": "read", "node": 2, "key": "read_key_1"},
            {"type": "read", "node": 0, "key": "read_key_1"},
            {"type": "read", "node": 1, "key": "read_key_1"}
        ]
        
        read_results = await test_cache_coherence_scenario(read_heavy_ops)
        
        # Read-heavy should have fewer coherence events
        assert read_results["total_invalidations"] < write_results["total_invalidations"]
        
        # Should show cache misses for nodes that didn't have the key
        read_events = [e for e in read_results["coherence_events"] 
                      if e.get("operation") == "read"]
        cache_misses = [e for e in read_events if not e["cache_hit"]]
        assert len(cache_misses) > 0  # Should have some cache misses for distributed reads
    
    def test_cache_performance_monitoring(self, mock_cache_manager):
        """Test cache performance monitoring and optimization"""
        
        class CachePerformanceMonitor:
            def __init__(self):
                self.metrics = {
                    "hit_rate_history": [],
                    "latency_history": [],
                    "eviction_rate_history": [],
                    "memory_usage_history": []
                }
                self.alerts = []
                self.recommendations = []
            
            def record_cache_operation(self, operation_type, cache_level, latency_ms, hit=True):
                """Record cache operation metrics"""
                timestamp = time.time()
                
                # Record hit rate
                current_hit_rate = 1.0 if hit else 0.0
                self.metrics["hit_rate_history"].append({
                    "timestamp": timestamp,
                    "hit_rate": current_hit_rate,
                    "cache_level": cache_level
                })
                
                # Record latency
                self.metrics["latency_history"].append({
                    "timestamp": timestamp,
                    "latency_ms": latency_ms,
                    "operation_type": operation_type,
                    "cache_level": cache_level
                })
            
            def analyze_performance(self, time_window_seconds=60):
                """Analyze cache performance and generate insights"""
                current_time = time.time()
                cutoff_time = current_time - time_window_seconds
                
                # Filter recent metrics
                recent_hits = [m for m in self.metrics["hit_rate_history"] 
                             if m["timestamp"] > cutoff_time]
                recent_latencies = [m for m in self.metrics["latency_history"] 
                                  if m["timestamp"] > cutoff_time]
                
                if not recent_hits or not recent_latencies:
                    return {"status": "insufficient_data"}
                
                # Calculate performance metrics
                overall_hit_rate = sum(m["hit_rate"] for m in recent_hits) / len(recent_hits)
                avg_latency = statistics.mean([m["latency_ms"] for m in recent_latencies])
                
                # Analyze by cache level
                level_stats = {}
                for level in ["L1", "L2", "L3"]:
                    level_hits = [m for m in recent_hits if m["cache_level"] == level]
                    level_latencies = [m for m in recent_latencies if m["cache_level"] == level]
                    
                    if level_hits and level_latencies:
                        level_stats[level] = {
                            "hit_rate": sum(m["hit_rate"] for m in level_hits) / len(level_hits),
                            "avg_latency_ms": statistics.mean([m["latency_ms"] for m in level_latencies]),
                            "operation_count": len(level_latencies)
                        }
                
                # Generate alerts and recommendations
                self._generate_performance_alerts(overall_hit_rate, avg_latency, level_stats)
                
                return {
                    "overall_hit_rate": overall_hit_rate,
                    "avg_latency_ms": avg_latency,
                    "level_stats": level_stats,
                    "alerts": self.alerts[-5:],  # Last 5 alerts
                    "recommendations": self.recommendations[-3:]  # Last 3 recommendations
                }
            
            def _generate_performance_alerts(self, hit_rate, avg_latency, level_stats):
                """Generate performance alerts and recommendations"""
                timestamp = datetime.now().isoformat()
                
                # Hit rate alerts
                if hit_rate < 0.5:
                    self.alerts.append({
                        "type": "low_hit_rate",
                        "severity": "high",
                        "message": f"Cache hit rate is low: {hit_rate:.2%}",
                        "timestamp": timestamp
                    })
                    self.recommendations.append({
                        "type": "cache_sizing",
                        "message": "Consider increasing cache size or reviewing eviction policy",
                        "timestamp": timestamp
                    })
                
                # Latency alerts
                if avg_latency > 10:  # 10ms threshold
                    self.alerts.append({
                        "type": "high_latency",
                        "severity": "medium",
                        "message": f"Average cache latency is high: {avg_latency:.2f}ms",
                        "timestamp": timestamp
                    })
                
                # Level-specific analysis
                if "L1" in level_stats and level_stats["L1"]["hit_rate"] < 0.6:
                    self.recommendations.append({
                        "type": "l1_optimization",
                        "message": "L1 cache hit rate is low, consider increasing L1 cache size",
                        "timestamp": timestamp
                    })
                
                if "L3" in level_stats and level_stats["L3"]["operation_count"] > level_stats.get("L1", {}).get("operation_count", 0):
                    self.recommendations.append({
                        "type": "cache_hierarchy",
                        "message": "Too many L3 cache accesses, optimize upper cache levels",
                        "timestamp": timestamp
                    })
        
        # Test performance monitoring with different scenarios
        monitor = CachePerformanceMonitor()
        
        # Simulate good cache performance
        good_operations = [
            ("get", "L1", 0.2, True),   # Fast L1 hits
            ("get", "L1", 0.3, True),
            ("get", "L2", 2.1, True),   # Some L2 hits
            ("get", "L1", 0.1, True),
            ("get", "L1", 0.4, True),
        ]
        
        for op_type, level, latency, hit in good_operations:
            monitor.record_cache_operation(op_type, level, latency, hit)
        
        good_analysis = monitor.analyze_performance()
        
        assert good_analysis["overall_hit_rate"] == 1.0  # All hits
        assert good_analysis["avg_latency_ms"] < 5       # Low average latency
        assert len(good_analysis["alerts"]) == 0         # No alerts for good performance
        
        # Simulate poor cache performance
        poor_operations = [
            ("get", "L3", 12.0, True),    # Slow L3 hits
            ("get", "MISS", 50.0, False), # Cache misses
            ("get", "L3", 15.0, True),
            ("get", "MISS", 45.0, False),
            ("get", "L2", 8.0, True),
        ]
        
        for op_type, level, latency, hit in poor_operations:
            monitor.record_cache_operation(op_type, level, latency, hit)
        
        poor_analysis = monitor.analyze_performance()
        
        assert poor_analysis["overall_hit_rate"] < 1.0   # Some misses
        assert poor_analysis["avg_latency_ms"] > 10      # High average latency
        assert len(poor_analysis["alerts"]) > 0          # Should generate alerts
        assert len(poor_analysis["recommendations"]) > 0 # Should provide recommendations
        
        # Check for specific alert types
        alert_types = [alert["type"] for alert in poor_analysis["alerts"]]
        assert "low_hit_rate" in alert_types or "high_latency" in alert_types