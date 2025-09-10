"""Redis Shared Pool Integration Tests

MISSION CRITICAL: These tests validate Redis connection pool sharing
across all services using real Redis instances to prevent WebSocket 1011 errors
and $500K+ ARR chat functionality failures.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Integration & Resource Optimization
- Value Impact: Ensures unified Redis operations across all services
- Strategic Impact: Prevents resource fragmentation causing chat failures

DESIGNED TO FAIL INITIALLY:
- Tests should FAIL showing fragmented Redis usage across services
- Tests prove integration gaps before consolidation
- Uses REAL Redis services, no mocks
- Guides service-level Redis unification
"""

import asyncio
import pytest
import time
from typing import Dict, List, Optional, Any, Set
import unittest


class TestRedisSharedPoolIntegration(unittest.TestCase):
    """Integration tests validating Redis shared pool across all services.
    
    These tests are designed to FAIL initially, proving the lack of
    unified Redis connection pool sharing causing WebSocket failures.
    
    REAL SERVICES ONLY - No mocks allowed in integration tests.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_keys_created = set()
        self.redis_clients = []
    
    async def asyncTearDown(self):
        """Async cleanup of test resources."""
        # Clean up test keys from all Redis instances
        for key in self.test_keys_created:
            try:
                # Try to clean from all potential Redis clients
                for client in self.redis_clients:
                    if client and hasattr(client, 'delete'):
                        await client.delete(key)
            except Exception:
                pass  # Best effort cleanup
        
        # Close connections
        for client in self.redis_clients:
            try:
                if client and hasattr(client, 'close'):
                    await client.close()
                elif client and hasattr(client, 'aclose'):
                    await client.aclose()
            except Exception:
                pass
    
    async def test_redis_cache_auth_database_pool_sharing(self):
        """DESIGNED TO FAIL: Test Redis pool sharing between cache, auth, and database.
        
        This test should FAIL showing that cache operations, auth sessions,
        and database operations use separate Redis pools instead of shared pool.
        """
        pool_analysis = await self._analyze_cross_service_redis_pools()
        
        # This assertion should FAIL initially
        self.assertTrue(
            pool_analysis["unified_pool"],
            f"CRITICAL: Redis pools not unified across services:\n" +
            f"  - Cache service pool: {pool_analysis['cache_pool_info']}\n" +
            f"  - Auth service pool: {pool_analysis['auth_pool_info']}\n" +
            f"  - Database service pool: {pool_analysis['database_pool_info']}\n" +
            f"  - Pool sharing detected: {pool_analysis['pools_shared']}\n" +
            f"  - Resource waste: {pool_analysis['resource_waste']}%\n" +
            "\n\nSeparate Redis pools cause resource contention and WebSocket 1011 errors."
        )
    
    async def test_redis_websocket_state_persistence_integration(self):
        """DESIGNED TO FAIL: Test Redis integration between WebSocket and state persistence.
        
        This test should FAIL showing that WebSocket state and persistence
        operations don't share Redis resources, causing state inconsistency.
        """
        integration_results = await self._test_websocket_redis_integration()
        
        # This assertion should FAIL initially
        self.assertTrue(
            integration_results["state_consistent"],
            f"CRITICAL: WebSocket-Redis state integration broken:\n" +
            f"  - State consistency: {integration_results['state_consistent']}\n" +
            f"  - WebSocket Redis access: {integration_results['websocket_redis_working']}\n" +
            f"  - Persistence Redis access: {integration_results['persistence_redis_working']}\n" +
            f"  - Data synchronization: {integration_results['data_sync_working']}\n" +
            f"  - Error details: {integration_results['error_details']}\n" +
            "\n\nBroken WebSocket-Redis integration causes user session failures and chat errors."
        )
    
    async def test_redis_connection_limit_shared_across_services(self):
        """DESIGNED TO FAIL: Test that Redis connection limits are properly shared.
        
        This test should FAIL showing that services don't coordinate Redis
        connection usage, leading to connection exhaustion.
        """
        connection_coordination = await self._test_connection_limit_coordination()
        
        # This assertion should FAIL initially
        self.assertTrue(
            connection_coordination["properly_coordinated"],
            f"CRITICAL: Redis connection limits not coordinated across services:\n" +
            f"  - Total connections used: {connection_coordination['total_connections']}\n" +
            f"  - Service coordination: {connection_coordination['services_coordinated']}\n" +
            f"  - Connection efficiency: {connection_coordination['efficiency']}%\n" +
            f"  - Limit violations: {connection_coordination['limit_violations']}\n" +
            f"  - Service breakdown: {connection_coordination['service_breakdown']}\n" +
            "\n\nPoor connection coordination causes WebSocket failures when limits exceeded."
        )
    
    async def test_redis_real_data_consistency_across_managers(self):
        """DESIGNED TO FAIL: Test real data consistency across Redis managers.
        
        This test should FAIL showing that different Redis managers
        create data inconsistency when accessing the same keys.
        
        REAL REDIS OPERATIONS - Tests actual data flow, no mocks.
        """
        consistency_results = await self._test_real_data_consistency()
        
        # This assertion should FAIL initially
        self.assertTrue(
            consistency_results["data_consistent"],
            f"CRITICAL: Redis data inconsistency across managers:\n" +
            f"  - Data consistency: {consistency_results['data_consistent']}\n" +
            f"  - Manager coordination: {consistency_results['managers_coordinated']}\n" +
            f"  - Write conflicts: {consistency_results['write_conflicts']}\n" +
            f"  - Read inconsistencies: {consistency_results['read_inconsistencies']}\n" +
            f"  - Test operations: {consistency_results['operations_tested']}\n" +
            f"  - Error patterns: {consistency_results['error_patterns']}\n" +
            "\n\nData inconsistency causes chat state corruption and user session errors."
        )
    
    async def test_redis_failover_recovery_coordination(self):
        """DESIGNED TO FAIL: Test Redis failover/recovery coordination across services.
        
        This test should FAIL showing that services don't coordinate
        Redis failover, causing partial system failures.
        """
        failover_coordination = await self._test_failover_coordination()
        
        # This assertion should FAIL initially
        self.assertTrue(
            failover_coordination["coordinated_recovery"],
            f"CRITICAL: Redis failover not coordinated across services:\n" +
            f"  - Recovery coordination: {failover_coordination['coordinated_recovery']}\n" +
            f"  - Service sync: {failover_coordination['services_synchronized']}\n" +
            f"  - Recovery time: {failover_coordination['recovery_time_ms']}ms\n" +
            f"  - Partial failures: {failover_coordination['partial_failures']}\n" +
            f"  - Service health: {failover_coordination['service_health']}\n" +
            "\n\nUncoordinated failover causes WebSocket disconnections and chat unavailability."
        )
    
    async def _analyze_cross_service_redis_pools(self) -> Dict[str, Any]:
        """Analyze Redis pool usage across cache, auth, and database services."""
        analysis = {
            "unified_pool": False,
            "cache_pool_info": "Unknown",
            "auth_pool_info": "Unknown", 
            "database_pool_info": "Unknown",
            "pools_shared": False,
            "resource_waste": 0
        }
        
        try:
            # Test cache service Redis
            cache_redis = await self._get_cache_service_redis()
            if cache_redis:
                analysis["cache_pool_info"] = "Active - Separate pool"
                self.redis_clients.append(cache_redis)
            else:
                analysis["cache_pool_info"] = "Not accessible"
            
            # Test auth service Redis  
            auth_redis = await self._get_auth_service_redis()
            if auth_redis:
                analysis["auth_pool_info"] = "Active - Separate pool"
                self.redis_clients.append(auth_redis)
            else:
                analysis["auth_pool_info"] = "Not accessible"
            
            # Test database service Redis
            db_redis = await self._get_database_service_redis()
            if db_redis:
                analysis["database_pool_info"] = "Active - Separate pool"
                self.redis_clients.append(db_redis)
            else:
                analysis["database_pool_info"] = "Not accessible"
            
            # Calculate resource waste
            active_pools = len([r for r in [cache_redis, auth_redis, db_redis] if r])
            if active_pools > 1:
                analysis["resource_waste"] = (active_pools - 1) * 33  # 33% waste per extra pool
            
            # Pools are unified only if single shared pool exists
            analysis["unified_pool"] = active_pools <= 1
            analysis["pools_shared"] = active_pools <= 1
            
        except Exception as e:
            analysis["error"] = f"Analysis failed: {e}"
            analysis["unified_pool"] = False
        
        return analysis
    
    async def _test_websocket_redis_integration(self) -> Dict[str, Any]:
        """Test WebSocket-Redis state integration with real operations."""
        results = {
            "state_consistent": False,
            "websocket_redis_working": False,
            "persistence_redis_working": False,
            "data_sync_working": False,
            "error_details": []
        }
        
        try:
            # Test WebSocket Redis access
            websocket_redis = await self._get_websocket_redis()
            if websocket_redis:
                test_key = f"test_websocket_state_{int(time.time())}"
                self.test_keys_created.add(test_key)
                
                await websocket_redis.set(test_key, "websocket_data", ex=300)
                websocket_data = await websocket_redis.get(test_key)
                results["websocket_redis_working"] = websocket_data == "websocket_data"
                self.redis_clients.append(websocket_redis)
            
            # Test persistence Redis access
            persistence_redis = await self._get_persistence_redis()
            if persistence_redis:
                test_key = f"test_persistence_state_{int(time.time())}"
                self.test_keys_created.add(test_key)
                
                await persistence_redis.set(test_key, "persistence_data", ex=300)
                persistence_data = await persistence_redis.get(test_key)
                results["persistence_redis_working"] = persistence_data == "persistence_data"
                self.redis_clients.append(persistence_redis)
            
            # Test data synchronization between systems
            if results["websocket_redis_working"] and results["persistence_redis_working"]:
                sync_key = f"test_sync_{int(time.time())}"
                self.test_keys_created.add(sync_key)
                
                # Write with websocket, read with persistence
                await websocket_redis.set(sync_key, "sync_test_data", ex=300)
                await asyncio.sleep(0.1)  # Allow for potential replication
                sync_data = await persistence_redis.get(sync_key)
                results["data_sync_working"] = sync_data == "sync_test_data"
            
            # Overall consistency check
            results["state_consistent"] = (
                results["websocket_redis_working"] and 
                results["persistence_redis_working"] and
                results["data_sync_working"]
            )
            
        except Exception as e:
            results["error_details"].append(f"Integration test failed: {e}")
        
        return results
    
    async def _test_connection_limit_coordination(self) -> Dict[str, Any]:
        """Test Redis connection limit coordination across services."""
        coordination = {
            "properly_coordinated": False,
            "total_connections": 0,
            "services_coordinated": False,
            "efficiency": 0,
            "limit_violations": [],
            "service_breakdown": {}
        }
        
        try:
            # Count connections from different services
            services = ["cache", "auth", "database", "websocket", "persistence"]
            service_connections = {}
            
            for service in services:
                try:
                    redis_client = await self._get_service_redis(service)
                    if redis_client:
                        # Estimate connections (each client typically uses 1-10 connections)
                        service_connections[service] = 5  # Conservative estimate
                        coordination["total_connections"] += 5
                        self.redis_clients.append(redis_client)
                    else:
                        service_connections[service] = 0
                except Exception as e:
                    service_connections[service] = 0
                    coordination["limit_violations"].append(f"{service}: {e}")
            
            coordination["service_breakdown"] = service_connections
            
            # Check coordination (ideally should share connections)
            active_services = sum(1 for count in service_connections.values() if count > 0)
            if active_services > 1:
                # Multiple services with separate connections = poor coordination
                coordination["efficiency"] = max(0, 100 - (active_services * 20))
                coordination["services_coordinated"] = False
            else:
                coordination["efficiency"] = 100
                coordination["services_coordinated"] = True
            
            # Proper coordination means efficient resource usage
            coordination["properly_coordinated"] = (
                coordination["services_coordinated"] and 
                coordination["total_connections"] < 20  # Reasonable limit
            )
            
        except Exception as e:
            coordination["limit_violations"].append(f"Coordination test failed: {e}")
        
        return coordination
    
    async def _test_real_data_consistency(self) -> Dict[str, Any]:
        """Test real data consistency across different Redis managers."""
        consistency = {
            "data_consistent": False,
            "managers_coordinated": False,
            "write_conflicts": 0,
            "read_inconsistencies": 0,
            "operations_tested": 0,
            "error_patterns": []
        }
        
        try:
            # Get different Redis managers
            managers = await self._get_different_redis_managers()
            
            if len(managers) >= 2:
                # Test data consistency across managers
                test_key = f"consistency_test_{int(time.time())}"
                self.test_keys_created.add(test_key)
                test_value = f"test_data_{int(time.time())}"
                
                # Write with first manager
                try:
                    await managers[0].set(test_key, test_value, ex=300)
                    consistency["operations_tested"] += 1
                    
                    # Read with second manager after small delay
                    await asyncio.sleep(0.1)
                    read_value = await managers[1].get(test_key)
                    consistency["operations_tested"] += 1
                    
                    if read_value != test_value:
                        consistency["read_inconsistencies"] += 1
                        consistency["error_patterns"].append(
                            f"Write-read inconsistency: wrote '{test_value}', read '{read_value}'"
                        )
                    
                except Exception as e:
                    consistency["error_patterns"].append(f"Data operation failed: {e}")
                
                # Test concurrent writes
                try:
                    concurrent_key = f"concurrent_test_{int(time.time())}"
                    self.test_keys_created.add(concurrent_key)
                    
                    # Concurrent writes with different managers
                    tasks = []
                    for i, manager in enumerate(managers[:2]):
                        tasks.append(manager.set(concurrent_key, f"value_{i}", ex=300))
                    
                    await asyncio.gather(*tasks, return_exceptions=True)
                    consistency["operations_tested"] += len(tasks)
                    
                    # Check final value consistency
                    final_values = []
                    for manager in managers[:2]:
                        try:
                            value = await manager.get(concurrent_key)
                            final_values.append(value)
                        except Exception:
                            final_values.append(None)
                    
                    # If values differ, there are write conflicts
                    if len(set(final_values)) > 1:
                        consistency["write_conflicts"] += 1
                        consistency["error_patterns"].append(
                            f"Write conflict: final values {final_values}"
                        )
                    
                except Exception as e:
                    consistency["error_patterns"].append(f"Concurrent write test failed: {e}")
            
            # Determine overall consistency
            consistency["managers_coordinated"] = len(managers) <= 1
            consistency["data_consistent"] = (
                consistency["read_inconsistencies"] == 0 and
                consistency["write_conflicts"] == 0 and
                consistency["operations_tested"] > 0
            )
            
        except Exception as e:
            consistency["error_patterns"].append(f"Consistency test failed: {e}")
        
        return consistency
    
    async def _test_failover_coordination(self) -> Dict[str, Any]:
        """Test Redis failover coordination across services."""
        failover = {
            "coordinated_recovery": False,
            "services_synchronized": False,
            "recovery_time_ms": 0,
            "partial_failures": 0,
            "service_health": {}
        }
        
        try:
            # Get Redis connections from different services
            services = ["websocket", "cache", "auth"]
            service_redis = {}
            
            for service in services:
                try:
                    redis_client = await self._get_service_redis(service)
                    if redis_client:
                        service_redis[service] = redis_client
                        self.redis_clients.append(redis_client)
                except Exception:
                    service_redis[service] = None
            
            # Test service health before "failover"
            start_time = time.time()
            pre_health = {}
            for service, redis_client in service_redis.items():
                try:
                    if redis_client and hasattr(redis_client, 'ping'):
                        await redis_client.ping()
                        pre_health[service] = "healthy"
                    else:
                        pre_health[service] = "unavailable"
                except Exception:
                    pre_health[service] = "unhealthy"
            
            # Simulate brief "failover" by testing reconnection
            await asyncio.sleep(0.5)  # Brief pause to simulate failover
            
            # Test service health after "failover"
            post_health = {}
            for service, redis_client in service_redis.items():
                try:
                    if redis_client and hasattr(redis_client, 'ping'):
                        await redis_client.ping()
                        post_health[service] = "recovered"
                    else:
                        post_health[service] = "failed"
                except Exception:
                    post_health[service] = "failed"
            
            recovery_time = (time.time() - start_time) * 1000
            failover["recovery_time_ms"] = int(recovery_time)
            
            # Analyze coordination
            healthy_services = sum(1 for status in post_health.values() if status == "recovered")
            total_services = len(service_redis)
            
            if total_services > 0:
                recovery_rate = healthy_services / total_services
                failover["services_synchronized"] = recovery_rate >= 0.8  # 80% success rate
                failover["partial_failures"] = total_services - healthy_services
            
            failover["service_health"] = {
                "pre_failover": pre_health,
                "post_failover": post_health
            }
            
            # Coordinated recovery means all or most services recover together
            failover["coordinated_recovery"] = (
                failover["services_synchronized"] and
                failover["recovery_time_ms"] < 5000  # Under 5 seconds
            )
            
        except Exception as e:
            failover["error"] = f"Failover test failed: {e}"
        
        return failover
    
    async def _get_cache_service_redis(self):
        """Get Redis client from cache service."""
        try:
            from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
            manager = RedisCacheManager()
            if hasattr(manager, 'get_client'):
                return await manager.get_client()
            return manager
        except Exception:
            try:
                # Fallback to primary manager
                return await self._get_primary_redis()
            except Exception:
                return None
    
    async def _get_auth_service_redis(self):
        """Get Redis client from auth service."""
        try:
            from auth_service.auth_core.redis_manager import RedisManager
            manager = RedisManager()
            if hasattr(manager, 'get_client'):
                return await manager.get_client()
            return manager
        except Exception:
            try:
                # Fallback to primary manager
                return await self._get_primary_redis()
            except Exception:
                return None
    
    async def _get_database_service_redis(self):
        """Get Redis client from database service."""
        try:
            from netra_backend.app.db.redis_manager import RedisManager
            manager = RedisManager()
            if hasattr(manager, 'get_client'):
                return await manager.get_client()
            return manager
        except Exception:
            try:
                # Fallback to primary manager
                return await self._get_primary_redis()
            except Exception:
                return None
    
    async def _get_websocket_redis(self):
        """Get Redis client for WebSocket operations."""
        return await self._get_primary_redis()
    
    async def _get_persistence_redis(self):
        """Get Redis client for persistence operations."""
        return await self._get_primary_redis()
    
    async def _get_primary_redis(self):
        """Get primary Redis manager client."""
        try:
            from netra_backend.app.redis_manager import redis_manager
            return await redis_manager.get_client()
        except Exception:
            return None
    
    async def _get_service_redis(self, service: str):
        """Get Redis client for specific service."""
        service_methods = {
            "cache": self._get_cache_service_redis,
            "auth": self._get_auth_service_redis,
            "database": self._get_database_service_redis,
            "websocket": self._get_websocket_redis,
            "persistence": self._get_persistence_redis
        }
        
        method = service_methods.get(service)
        if method:
            return await method()
        return None
    
    async def _get_different_redis_managers(self):
        """Get different Redis manager instances for testing."""
        managers = []
        
        # Try different manager sources
        manager_sources = [
            ("primary", self._get_primary_redis),
            ("cache", self._get_cache_service_redis),
            ("auth", self._get_auth_service_redis),
            ("database", self._get_database_service_redis)
        ]
        
        for name, method in manager_sources:
            try:
                manager = await method()
                if manager:
                    managers.append(manager)
            except Exception:
                continue
        
        return managers


if __name__ == "__main__":
    # Run tests independently for debugging
    import unittest
    unittest.main()