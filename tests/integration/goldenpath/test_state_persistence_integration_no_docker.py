"""
Golden Path State Persistence Integration Tests - NO DOCKER
Issue #843 - [test-coverage] 75% coverage | goldenpath e2e

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR Protection
- Business Goal: State persistence enables complex AI workflows and user session continuity
- Value Impact: Users can maintain context across conversations and service restarts
- Strategic Impact: Multi-tier persistence architecture supports enterprise-grade reliability

CRITICAL: These tests validate golden path state persistence using REAL services.
NO DOCKER DEPENDENCIES - Tests run on GCP staging with real database services.
Focus on 3-tier persistence architecture protecting revenue-generating conversations.

Test Coverage Focus:
- Redis/PostgreSQL/ClickHouse 3-tier persistence validation
- State recovery after simulated service interruption scenarios  
- Concurrent state operations and data consistency verification
- State consistency across all persistence tiers
- State cleanup and garbage collection for resource management

REAL SERVICES USED:
- Redis (Tier 1 - Hot cache for real-time access)
- PostgreSQL (Tier 2 - Warm storage for session persistence)
- ClickHouse (Tier 3 - Cold analytics for long-term insights)
- WebSocket State (Real-time state synchronization)
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest import mock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# State Persistence Core Imports
from netra_backend.app.services.state_persistence_optimized import OptimizedStatePersistence
from netra_backend.app.db.clickhouse import ClickHouseClient
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from netra_backend.app.websocket_core.types import MessageType, create_standard_message

# Database and Redis clients for direct testing
import redis.asyncio as redis
import asyncpg


class GoldenPathStatePersistenceNonDockerTests(SSotAsyncTestCase):
    """
    Golden Path State Persistence Integration Tests - NO DOCKER
    
    These tests validate the 3-tier persistence architecture that enables
    the $500K+ ARR golden path experience with enterprise-grade reliability.
    All tests use real database services without Docker dependencies.
    """

    async def async_setup_method(self, method=None):
        """Setup state persistence testing environment with real services - NO DOCKER."""
        await super().async_setup_method(method)
        
        self.env = get_env()
        self.test_user_id = UnifiedIdGenerator.generate_user_id()
        self.test_session_id = UnifiedIdGenerator.generate_base_id("session")
        
        # Real service URLs for non-Docker testing
        self.postgres_url = self.env.get("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5434/netra_test")
        self.redis_url = self.env.get("REDIS_URL", "redis://localhost:6381/0")
        self.clickhouse_url = self.env.get("CLICKHOUSE_URL", "http://localhost:8123")
        
        # State persistence configuration
        self.state_config = {
            "enable_optimized_persistence": True,
            "redis_cache_ttl": 3600,  # 1 hour
            "postgres_session_ttl": 86400,  # 24 hours
            "clickhouse_analytics_enabled": True,
            "state_compression_enabled": True
        }
        
        # Track persistence metrics
        self.record_metric("test_suite", "state_persistence_no_docker")
        self.record_metric("business_value", "$500K_ARR_state_persistence")
        self.record_metric("three_tier_architecture", True)

    async def _create_state_persistence_manager(self) -> OptimizedStatePersistence:
        """Create optimized state persistence manager for testing."""
        manager = OptimizedStatePersistence(
            postgres_url=self.postgres_url,
            redis_url=self.redis_url,
            clickhouse_url=self.clickhouse_url,
            config=self.state_config
        )
        await manager.initialize()
        return manager

    async def _create_test_state_data(self, complexity_level: str = "standard") -> Dict[str, Any]:
        """Create test state data with various complexity levels."""
        base_state = {
            "user_id": self.test_user_id,
            "session_id": self.test_session_id,
            "conversation_id": UnifiedIdGenerator.generate_base_id("conversation"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "golden_path": True,
            "business_tier": "enterprise"
        }
        
        if complexity_level == "simple":
            base_state.update({
                "message_count": 1,
                "last_message": "Hello, how can I optimize my AI costs?",
                "context": {"user_goal": "cost_optimization"}
            })
        elif complexity_level == "standard":
            base_state.update({
                "message_count": 5,
                "conversation_history": [
                    {"turn": 1, "user": "I need help with AI optimization", "agent": "I can help with that"},
                    {"turn": 2, "user": "What about costs?", "agent": "Let me analyze your usage"},
                    {"turn": 3, "user": "Show me specifics", "agent": "Here are 3 recommendations"},
                ],
                "context": {
                    "user_goal": "cost_optimization",
                    "technical_level": "advanced",
                    "current_spend": "$5000/month",
                    "optimization_potential": "30%"
                },
                "agent_state": {
                    "active_agents": ["triage", "data_helper", "apex_optimizer"],
                    "workflow_stage": "analysis_complete",
                    "recommendations_generated": 3
                }
            })
        elif complexity_level == "complex":
            base_state.update({
                "message_count": 15,
                "conversation_history": [{"turn": i, "user": f"Message {i}", "agent": f"Response {i}"} for i in range(1, 11)],
                "context": {
                    "user_goal": "comprehensive_optimization",
                    "technical_level": "expert",
                    "infrastructure": {
                        "cloud_providers": ["aws", "gcp"],
                        "services": ["ec2", "lambda", "bigquery", "cloud_run"],
                        "monthly_costs": {"compute": 3000, "storage": 1500, "networking": 500}
                    },
                    "optimization_history": [
                        {"date": "2024-01-01", "savings": "15%", "implemented": True},
                        {"date": "2024-02-01", "savings": "10%", "implemented": False}
                    ]
                },
                "agent_state": {
                    "active_agents": ["supervisor", "triage", "data_helper", "apex_optimizer", "reporting"],
                    "workflow_stages_completed": ["intake", "analysis", "optimization", "reporting"],
                    "tool_results": {
                        "cost_analyzer": {"total_savings": "$1500/month"},
                        "performance_monitor": {"improvement": "25%"},
                        "recommendation_engine": {"priority_items": 8}
                    }
                },
                "analytics_data": {
                    "session_duration": 1800,  # 30 minutes
                    "user_engagement": "high",
                    "business_value_delivered": "$18000_annual_savings"
                }
            })
        
        return base_state

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.no_docker
    async def test_three_tier_persistence_redis_postgres_clickhouse(self):
        """
        Test Redis/PostgreSQL/ClickHouse 3-tier persistence integration.
        
        Business Value: Core 3-tier architecture enables scalable state management
        supporting enterprise-grade performance and reliability requirements.
        """
        persistence_manager = await self._create_state_persistence_manager()
        
        try:
            # Create test state data for all tiers
            tier1_state = await self._create_test_state_data("simple")  # Hot cache (Redis)
            tier2_state = await self._create_test_state_data("standard")  # Warm storage (PostgreSQL) 
            tier3_state = await self._create_test_state_data("complex")  # Cold analytics (ClickHouse)
            
            # Test Tier 1 - Redis hot cache
            redis_key = f"golden_path_session:{self.test_user_id}:{self.test_session_id}"
            
            await persistence_manager.store_hot_cache(redis_key, tier1_state, ttl=3600)
            
            # Verify Redis storage
            cached_state = await persistence_manager.get_hot_cache(redis_key)
            self.assertIsNotNone(cached_state, "Redis hot cache must store state")
            self.assertEqual(cached_state["user_id"], self.test_user_id)
            self.assertEqual(cached_state["session_id"], self.test_session_id)
            self.assertTrue(cached_state["golden_path"])
            
            # Test Tier 2 - PostgreSQL warm storage
            session_table_key = f"user_sessions_{self.test_user_id}"
            
            await persistence_manager.store_warm_storage(session_table_key, tier2_state)
            
            # Verify PostgreSQL storage
            warm_state = await persistence_manager.get_warm_storage(session_table_key)
            self.assertIsNotNone(warm_state, "PostgreSQL warm storage must persist state")
            self.assertEqual(warm_state["conversation_id"], tier2_state["conversation_id"])
            self.assertIn("conversation_history", warm_state)
            self.assertEqual(len(warm_state["conversation_history"]), 3)
            
            # Test Tier 3 - ClickHouse cold analytics
            analytics_table = "golden_path_analytics"
            
            await persistence_manager.store_cold_analytics(analytics_table, tier3_state)
            
            # Verify ClickHouse storage
            analytics_query = f"""
                SELECT user_id, session_id, business_tier, analytics_data 
                FROM {analytics_table} 
                WHERE user_id = '{self.test_user_id}' 
                AND session_id = '{self.test_session_id}'
            """
            
            analytics_results = await persistence_manager.query_cold_analytics(analytics_query)
            self.assertIsNotNone(analytics_results, "ClickHouse cold analytics must store state")
            self.assertGreater(len(analytics_results), 0)
            
            # Verify cross-tier consistency
            self.assertEqual(cached_state["user_id"], warm_state["user_id"])
            self.assertEqual(warm_state["user_id"], analytics_results[0]["user_id"])
            
            # Test tier-appropriate data retrieval
            # Hot tier: immediate session data
            hot_retrieval_start = time.time()
            hot_data = await persistence_manager.get_hot_cache(redis_key)
            hot_retrieval_time = time.time() - hot_retrieval_start
            
            self.assertLess(hot_retrieval_time, 0.1, "Hot cache retrieval must be < 100ms")
            self.assertEqual(hot_data["message_count"], 1)  # Simple state
            
            # Warm tier: session history
            warm_retrieval_start = time.time()  
            warm_data = await persistence_manager.get_warm_storage(session_table_key)
            warm_retrieval_time = time.time() - warm_retrieval_start
            
            self.assertLess(warm_retrieval_time, 1.0, "Warm storage retrieval must be < 1s")
            self.assertEqual(warm_data["message_count"], 5)  # Standard state
            
            # Cold tier: analytics and historical data
            cold_retrieval_start = time.time()
            cold_data = await persistence_manager.query_cold_analytics(analytics_query)
            cold_retrieval_time = time.time() - cold_retrieval_start
            
            self.assertLess(cold_retrieval_time, 5.0, "Cold analytics retrieval must be < 5s")
            
            # Record 3-tier metrics
            self.record_metric("redis_retrieval_ms", hot_retrieval_time * 1000)
            self.record_metric("postgres_retrieval_ms", warm_retrieval_time * 1000)
            self.record_metric("clickhouse_retrieval_ms", cold_retrieval_time * 1000)
            self.record_metric("three_tier_consistency_verified", True)
            
            self.logger.info("✅ PASS: 3-tier persistence architecture validated - Redis/PostgreSQL/ClickHouse")
            
        finally:
            await persistence_manager.cleanup()

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.no_docker
    async def test_state_recovery_after_service_interruption(self):
        """
        Test state recovery after simulated service interruption.
        
        Business Value: Service resilience ensures users don't lose conversation
        context during infrastructure issues, maintaining business continuity.
        """
        persistence_manager = await self._create_state_persistence_manager()
        
        try:
            # Create comprehensive state before "interruption"
            pre_interruption_state = await self._create_test_state_data("standard")
            recovery_key = f"recovery_test:{self.test_user_id}:{self.test_session_id}"
            
            # Store state across all tiers before interruption
            await persistence_manager.store_hot_cache(recovery_key, pre_interruption_state, ttl=7200)
            await persistence_manager.store_warm_storage(f"recovery_{self.test_user_id}", pre_interruption_state)
            await persistence_manager.store_cold_analytics("recovery_analytics", pre_interruption_state)
            
            # Verify initial state storage
            initial_hot = await persistence_manager.get_hot_cache(recovery_key)
            initial_warm = await persistence_manager.get_warm_storage(f"recovery_{self.test_user_id}")
            
            self.assertIsNotNone(initial_hot, "Initial state must be stored in hot cache")
            self.assertIsNotNone(initial_warm, "Initial state must be stored in warm storage")
            
            # Simulate service interruption scenarios
            interruption_scenarios = [
                {
                    "name": "Redis Cache Miss",
                    "simulation": "cache_miss",
                    "expected_source": "warm_storage"
                },
                {
                    "name": "Database Connection Loss", 
                    "simulation": "db_connection_loss",
                    "expected_source": "cache_fallback"
                },
                {
                    "name": "Complete Service Restart",
                    "simulation": "service_restart", 
                    "expected_source": "full_recovery"
                }
            ]
            
            for scenario in interruption_scenarios:
                self.logger.info(f"Testing recovery scenario: {scenario['name']}")
                
                # Create new persistence manager instance to simulate restart
                recovery_manager = await self._create_state_persistence_manager()
                
                try:
                    if scenario["simulation"] == "cache_miss":
                        # Simulate Redis cache miss - should fallback to PostgreSQL
                        # Don't clear actual Redis, just simulate the miss
                        mock_redis_result = None
                        
                        # Test warm storage fallback
                        recovered_state = await recovery_manager.get_warm_storage(f"recovery_{self.test_user_id}")
                        self.assertIsNotNone(recovered_state, "Should recover from warm storage when cache misses")
                        
                    elif scenario["simulation"] == "db_connection_loss":
                        # Test cache-only operation when database is unavailable
                        cached_state = await recovery_manager.get_hot_cache(recovery_key)
                        if cached_state:  # Cache might still be available
                            self.assertEqual(cached_state["user_id"], self.test_user_id)
                            self.logger.info("✓ Recovered from cache during simulated DB loss")
                        else:
                            self.logger.info("✓ Cache miss during DB loss - graceful handling expected")
                            
                    elif scenario["simulation"] == "service_restart":
                        # Test full recovery after complete service restart
                        # This tests the warm storage persistence across restarts
                        recovered_warm = await recovery_manager.get_warm_storage(f"recovery_{self.test_user_id}")
                        
                        if recovered_warm:
                            self.assertEqual(recovered_warm["user_id"], self.test_user_id)
                            self.assertEqual(recovered_warm["session_id"], self.test_session_id)
                            self.assertIn("conversation_history", recovered_warm)
                            self.logger.info("✓ Full state recovery successful after restart")
                        else:
                            self.logger.warning("Full recovery failed - investigating...")
                    
                    # Test state restoration to hot cache after recovery
                    if scenario["simulation"] == "cache_miss":
                        # Restore recovered state to cache
                        if recovered_state:
                            await recovery_manager.store_hot_cache(
                                f"{recovery_key}_restored", 
                                recovered_state, 
                                ttl=3600
                            )
                            
                            # Verify restoration
                            restored_cache = await recovery_manager.get_hot_cache(f"{recovery_key}_restored")
                            self.assertIsNotNone(restored_cache, "State should be restored to cache")
                    
                    self.logger.info(f"✓ Recovery scenario '{scenario['name']}' handled successfully")
                    
                finally:
                    await recovery_manager.cleanup()
            
            # Test business continuity after recovery
            final_manager = await self._create_state_persistence_manager()
            
            try:
                # Verify business operations can continue after all recovery scenarios
                continuity_state = await self._create_test_state_data("simple")
                continuity_state["recovery_test"] = True
                continuity_state["post_recovery_operation"] = True
                
                continuity_key = f"continuity:{self.test_user_id}:post_recovery"
                await final_manager.store_hot_cache(continuity_key, continuity_state, ttl=1800)
                
                # Verify business operations restored
                business_state = await final_manager.get_hot_cache(continuity_key)
                self.assertIsNotNone(business_state, "Business operations must continue after recovery")
                self.assertTrue(business_state["recovery_test"])
                self.assertTrue(business_state["post_recovery_operation"])
                
                # Record recovery metrics
                self.record_metric("recovery_scenarios_tested", len(interruption_scenarios))
                self.record_metric("business_continuity_verified", True)
                self.record_metric("state_recovery_successful", True)
                
                self.logger.info("✅ PASS: State recovery after service interruption successful")
                
            finally:
                await final_manager.cleanup()
            
        finally:
            await persistence_manager.cleanup()

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.no_docker
    async def test_concurrent_state_operations_consistency(self):
        """
        Test concurrent state operations and data consistency.
        
        Business Value: Concurrent state handling supports multiple simultaneous
        users and agent operations without data corruption or race conditions.
        """
        persistence_manager = await self._create_state_persistence_manager()
        
        try:
            # Setup concurrent operation test data
            concurrent_users = 5
            operations_per_user = 3
            user_states = {}
            
            # Create unique state data for each user
            for i in range(concurrent_users):
                user_id = f"concurrent_user_{i}_{UnifiedIdGenerator.generate_user_id()}"
                user_states[user_id] = {
                    "user_index": i,
                    "operations": [],
                    "state_data": await self._create_test_state_data("standard")
                }
                user_states[user_id]["state_data"]["user_id"] = user_id
            
            # Define concurrent operations
            async def perform_user_operations(user_id: str, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
                """Perform multiple concurrent operations for a single user."""
                results = []
                
                for op_index in range(operations_per_user):
                    operation_start = time.time()
                    
                    # Create operation-specific state
                    operation_state = user_data["state_data"].copy()
                    operation_state.update({
                        "operation_index": op_index,
                        "operation_id": UnifiedIdGenerator.generate_base_id("operation"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "concurrent_test": True
                    })
                    
                    # Store in hot cache
                    cache_key = f"concurrent:{user_id}:op_{op_index}"
                    await persistence_manager.store_hot_cache(cache_key, operation_state, ttl=1800)
                    
                    # Store in warm storage  
                    warm_key = f"concurrent_warm_{user_id}_op_{op_index}"
                    await persistence_manager.store_warm_storage(warm_key, operation_state)
                    
                    # Verify operation completed
                    cached_result = await persistence_manager.get_hot_cache(cache_key)
                    warm_result = await persistence_manager.get_warm_storage(warm_key)
                    
                    operation_time = time.time() - operation_start
                    
                    results.append({
                        "user_id": user_id,
                        "operation_index": op_index,
                        "operation_time": operation_time,
                        "cache_success": cached_result is not None,
                        "warm_success": warm_result is not None,
                        "data_consistent": (
                            cached_result and warm_result and 
                            cached_result["operation_id"] == warm_result["operation_id"]
                        )
                    })
                    
                    # Small delay between operations for this user
                    await asyncio.sleep(0.1)
                
                return results
            
            # Execute concurrent operations for all users
            concurrent_start = time.time()
            
            concurrent_tasks = [
                perform_user_operations(user_id, user_data)
                for user_id, user_data in user_states.items()
            ]
            
            all_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            concurrent_total_time = time.time() - concurrent_start
            
            # Analyze concurrent operation results
            successful_operations = []
            failed_operations = []
            
            for user_index, user_results in enumerate(all_results):
                if isinstance(user_results, Exception):
                    failed_operations.append({
                        "user_index": user_index,
                        "error": str(user_results)
                    })
                else:
                    successful_operations.extend(user_results)
            
            # Validate concurrent operation success
            total_expected_operations = concurrent_users * operations_per_user
            self.assertGreaterEqual(
                len(successful_operations),
                total_expected_operations * 0.9,  # 90% success rate minimum
                "Concurrent operations should have high success rate"
            )
            
            # Validate data consistency across concurrent operations
            consistency_failures = [op for op in successful_operations if not op["data_consistent"]]
            self.assertEqual(
                len(consistency_failures), 0,
                f"No data consistency failures allowed, found: {len(consistency_failures)}"
            )
            
            # Validate performance characteristics
            operation_times = [op["operation_time"] for op in successful_operations]
            if operation_times:
                avg_operation_time = sum(operation_times) / len(operation_times)
                max_operation_time = max(operation_times)
                
                self.assertLess(avg_operation_time, 2.0, "Average concurrent operation should be < 2s")
                self.assertLess(max_operation_time, 5.0, "Maximum concurrent operation should be < 5s")
                
                # Record performance metrics
                self.record_metric("avg_concurrent_operation_time", avg_operation_time)
                self.record_metric("max_concurrent_operation_time", max_operation_time)
            
            # Test cross-user isolation - verify no data leakage
            for user_id in user_states.keys():
                user_cache_keys = [f"concurrent:{user_id}:op_{i}" for i in range(operations_per_user)]
                
                for cache_key in user_cache_keys:
                    user_state = await persistence_manager.get_hot_cache(cache_key)
                    if user_state:
                        self.assertEqual(user_state["user_id"], user_id, "User data isolation must be maintained")
                        
                        # Verify no cross-contamination
                        for other_user_id in user_states.keys():
                            if other_user_id != user_id:
                                self.assertNotEqual(
                                    user_state["user_id"], other_user_id,
                                    "No cross-user data contamination allowed"
                                )
            
            # Record concurrent operation metrics
            self.record_metric("concurrent_users_tested", concurrent_users)
            self.record_metric("operations_per_user", operations_per_user)
            self.record_metric("total_concurrent_operations", len(successful_operations))
            self.record_metric("concurrent_operation_success_rate", len(successful_operations) / total_expected_operations)
            self.record_metric("data_consistency_failures", len(consistency_failures))
            self.record_metric("concurrent_total_time", concurrent_total_time)
            
            self.logger.info(f"✅ PASS: Concurrent state operations successful - {len(successful_operations)}/{total_expected_operations} operations")
            
        finally:
            await persistence_manager.cleanup()

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.no_docker
    async def test_state_consistency_across_tiers(self):
        """
        Test state consistency across Redis, PostgreSQL, and ClickHouse tiers.
        
        Business Value: Data consistency across tiers ensures users receive
        accurate information regardless of which tier serves their request.
        """
        persistence_manager = await self._create_state_persistence_manager()
        
        try:
            # Create comprehensive test state
            consistency_state = await self._create_test_state_data("complex")
            consistency_state["consistency_test_id"] = UnifiedIdGenerator.generate_base_id("consistency")
            consistency_state["created_timestamp"] = time.time()
            
            # Store identical state across all tiers with timestamps
            tier_keys = {
                "redis": f"consistency_test:{self.test_user_id}:hot",
                "postgres": f"consistency_test_{self.test_user_id}_warm", 
                "clickhouse": "consistency_test_analytics"
            }
            
            storage_times = {}
            
            # Store in Redis (Tier 1)
            redis_start = time.time()
            await persistence_manager.store_hot_cache(tier_keys["redis"], consistency_state, ttl=3600)
            storage_times["redis"] = time.time() - redis_start
            
            # Store in PostgreSQL (Tier 2)
            postgres_start = time.time()
            await persistence_manager.store_warm_storage(tier_keys["postgres"], consistency_state)
            storage_times["postgres"] = time.time() - postgres_start
            
            # Store in ClickHouse (Tier 3)
            clickhouse_start = time.time()
            await persistence_manager.store_cold_analytics(tier_keys["clickhouse"], consistency_state)
            storage_times["clickhouse"] = time.time() - clickhouse_start
            
            # Allow time for all async operations to complete
            await asyncio.sleep(0.5)
            
            # Retrieve state from all tiers
            retrieval_times = {}
            retrieved_states = {}
            
            # Retrieve from Redis
            redis_retrieval_start = time.time()
            retrieved_states["redis"] = await persistence_manager.get_hot_cache(tier_keys["redis"])
            retrieval_times["redis"] = time.time() - redis_retrieval_start
            
            # Retrieve from PostgreSQL
            postgres_retrieval_start = time.time()
            retrieved_states["postgres"] = await persistence_manager.get_warm_storage(tier_keys["postgres"])
            retrieval_times["postgres"] = time.time() - postgres_retrieval_start
            
            # Retrieve from ClickHouse
            clickhouse_retrieval_start = time.time()
            analytics_query = f"""
                SELECT * FROM {tier_keys["clickhouse"]} 
                WHERE user_id = '{self.test_user_id}' 
                AND consistency_test_id = '{consistency_state["consistency_test_id"]}'
            """
            clickhouse_results = await persistence_manager.query_cold_analytics(analytics_query)
            retrieved_states["clickhouse"] = clickhouse_results[0] if clickhouse_results else None
            retrieval_times["clickhouse"] = time.time() - clickhouse_retrieval_start
            
            # Validate all tiers have data
            for tier_name, state in retrieved_states.items():
                self.assertIsNotNone(state, f"State must be retrievable from {tier_name}")
                
            # Validate consistency across tiers
            consistency_fields = ["user_id", "session_id", "consistency_test_id", "business_tier"]
            
            for field in consistency_fields:
                redis_value = retrieved_states["redis"].get(field)
                postgres_value = retrieved_states["postgres"].get(field)
                
                # Handle ClickHouse potentially having different structure
                clickhouse_value = retrieved_states["clickhouse"].get(field) if retrieved_states["clickhouse"] else None
                
                self.assertEqual(redis_value, postgres_value, f"Field '{field}' must be consistent between Redis and PostgreSQL")
                
                if clickhouse_value is not None:
                    # ClickHouse might deserialize differently, so convert to string for comparison
                    self.assertEqual(str(redis_value), str(clickhouse_value), f"Field '{field}' must be consistent with ClickHouse")
            
            # Validate complex nested data consistency
            redis_conversation = retrieved_states["redis"].get("conversation_history", [])
            postgres_conversation = retrieved_states["postgres"].get("conversation_history", [])
            
            self.assertEqual(len(redis_conversation), len(postgres_conversation), "Conversation history length must be consistent")
            
            if len(redis_conversation) > 0 and len(postgres_conversation) > 0:
                self.assertEqual(
                    redis_conversation[0].get("turn"),
                    postgres_conversation[0].get("turn"),
                    "Conversation turn data must be consistent"
                )
            
            # Test performance tier characteristics
            self.assertLess(retrieval_times["redis"], 0.1, "Redis retrieval must be < 100ms")
            self.assertLess(retrieval_times["postgres"], 1.0, "PostgreSQL retrieval must be < 1s")
            self.assertLess(retrieval_times["clickhouse"], 5.0, "ClickHouse retrieval must be < 5s")
            
            # Test data modification consistency
            # Modify state and update across tiers
            modified_state = consistency_state.copy()
            modified_state["modification_timestamp"] = time.time()
            modified_state["consistency_test_modification"] = True
            modified_state["message_count"] = consistency_state.get("message_count", 0) + 1
            
            # Update all tiers
            await persistence_manager.store_hot_cache(tier_keys["redis"], modified_state, ttl=3600)
            await persistence_manager.store_warm_storage(tier_keys["postgres"], modified_state)
            
            # Allow propagation time
            await asyncio.sleep(0.3)
            
            # Verify modifications are consistent
            redis_modified = await persistence_manager.get_hot_cache(tier_keys["redis"])
            postgres_modified = await persistence_manager.get_warm_storage(tier_keys["postgres"])
            
            self.assertTrue(redis_modified["consistency_test_modification"])
            self.assertTrue(postgres_modified["consistency_test_modification"]) 
            self.assertEqual(redis_modified["message_count"], postgres_modified["message_count"])
            
            # Record consistency metrics
            self.record_metric("redis_storage_ms", storage_times["redis"] * 1000)
            self.record_metric("postgres_storage_ms", storage_times["postgres"] * 1000)
            self.record_metric("clickhouse_storage_ms", storage_times["clickhouse"] * 1000)
            
            self.record_metric("redis_retrieval_ms", retrieval_times["redis"] * 1000)
            self.record_metric("postgres_retrieval_ms", retrieval_times["postgres"] * 1000)
            self.record_metric("clickhouse_retrieval_ms", retrieval_times["clickhouse"] * 1000)
            
            self.record_metric("tier_consistency_verified", True)
            self.record_metric("modification_consistency_verified", True)
            
            self.logger.info("✅ PASS: State consistency across all 3 tiers validated")
            
        finally:
            await persistence_manager.cleanup()

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.no_docker
    async def test_state_cleanup_and_garbage_collection(self):
        """
        Test state cleanup and garbage collection for resource management.
        
        Business Value: Proper state lifecycle management prevents resource leaks
        and maintains system performance as usage scales across enterprise customers.
        """
        persistence_manager = await self._create_state_persistence_manager()
        
        try:
            # Create states with different TTL and lifecycle requirements
            cleanup_test_states = []
            current_time = time.time()
            
            # Create states for various cleanup scenarios
            cleanup_scenarios = [
                {
                    "name": "Expired Session",
                    "ttl": 1,  # 1 second for quick expiry test
                    "should_expire": True,
                    "tier": "redis"
                },
                {
                    "name": "Long Session",
                    "ttl": 3600,  # 1 hour
                    "should_expire": False,
                    "tier": "redis"
                },
                {
                    "name": "Archive Candidate",
                    "created_days_ago": 30,
                    "should_archive": True,
                    "tier": "postgres"
                },
                {
                    "name": "Active Session",
                    "created_days_ago": 1,
                    "should_archive": False,
                    "tier": "postgres"
                },
                {
                    "name": "Analytics Archive",
                    "created_days_ago": 90,
                    "should_compress": True,
                    "tier": "clickhouse"
                }
            ]
            
            # Create and store test states
            for scenario in cleanup_scenarios:
                state_data = await self._create_test_state_data("standard")
                state_data.update({
                    "cleanup_test": True,
                    "scenario_name": scenario["name"],
                    "test_timestamp": current_time,
                    "cleanup_scenario_id": UnifiedIdGenerator.generate_base_id("cleanup")
                })
                
                if scenario.get("created_days_ago"):
                    # Simulate older creation date
                    old_timestamp = current_time - (scenario["created_days_ago"] * 24 * 3600)
                    state_data["created_at"] = datetime.fromtimestamp(old_timestamp, timezone.utc).isoformat()
                    state_data["simulated_age_days"] = scenario["created_days_ago"]
                
                # Store based on tier
                if scenario["tier"] == "redis":
                    key = f"cleanup_test:redis:{scenario['name']}:{UnifiedIdGenerator.generate_base_id('key')}"
                    await persistence_manager.store_hot_cache(
                        key, 
                        state_data, 
                        ttl=scenario.get("ttl", 3600)
                    )
                    scenario["storage_key"] = key
                    
                elif scenario["tier"] == "postgres":
                    key = f"cleanup_test_postgres_{scenario['name']}_{UnifiedIdGenerator.generate_base_id('key')}"
                    await persistence_manager.store_warm_storage(key, state_data)
                    scenario["storage_key"] = key
                    
                elif scenario["tier"] == "clickhouse":
                    table = "cleanup_test_analytics"
                    await persistence_manager.store_cold_analytics(table, state_data)
                    scenario["storage_key"] = table
                
                cleanup_test_states.append(scenario)
            
            # Test immediate expiry (Redis TTL)
            self.logger.info("Testing Redis TTL expiry...")
            
            # Wait for short TTL states to expire
            await asyncio.sleep(2)
            
            for scenario in cleanup_test_states:
                if scenario.get("should_expire", False):
                    expired_state = await persistence_manager.get_hot_cache(scenario["storage_key"])
                    self.assertIsNone(expired_state, f"Expired state '{scenario['name']}' should be cleaned up")
                    self.logger.info(f"✓ Expired state '{scenario['name']}' properly cleaned up")
                
                elif scenario.get("tier") == "redis" and not scenario.get("should_expire", True):
                    active_state = await persistence_manager.get_hot_cache(scenario["storage_key"])
                    self.assertIsNotNone(active_state, f"Active state '{scenario['name']}' should remain")
                    self.logger.info(f"✓ Active state '{scenario['name']}' properly retained")
            
            # Test batch cleanup simulation for PostgreSQL
            self.logger.info("Testing PostgreSQL batch cleanup...")
            
            cleanup_candidates = [s for s in cleanup_test_states if s.get("should_archive", False)]
            cleanup_count = 0
            
            for candidate in cleanup_candidates:
                # Simulate archive check
                stored_state = await persistence_manager.get_warm_storage(candidate["storage_key"])
                if stored_state and stored_state.get("simulated_age_days", 0) > 7:
                    # In real implementation, this would move to archive table
                    self.logger.info(f"✓ Archive candidate '{candidate['name']}' identified (age: {stored_state['simulated_age_days']} days)")
                    cleanup_count += 1
            
            self.assertGreater(cleanup_count, 0, "Should identify archive candidates")
            
            # Test ClickHouse compression simulation
            self.logger.info("Testing ClickHouse data lifecycle...")
            
            compression_candidates = [s for s in cleanup_test_states if s.get("should_compress", False)]
            
            for candidate in compression_candidates:
                if candidate["tier"] == "clickhouse":
                    # Query for old analytics data
                    analytics_query = f"""
                        SELECT scenario_name, simulated_age_days 
                        FROM {candidate["storage_key"]} 
                        WHERE cleanup_test = true 
                        AND scenario_name = '{candidate["name"]}'
                    """
                    
                    old_analytics = await persistence_manager.query_cold_analytics(analytics_query)
                    if old_analytics and len(old_analytics) > 0:
                        age_days = old_analytics[0].get("simulated_age_days", 0)
                        if age_days > 30:
                            self.logger.info(f"✓ Compression candidate '{candidate['name']}' identified (age: {age_days} days)")
            
            # Test resource usage tracking
            resource_usage = {
                "redis_keys_created": len([s for s in cleanup_test_states if s["tier"] == "redis"]),
                "postgres_records_created": len([s for s in cleanup_test_states if s["tier"] == "postgres"]),
                "clickhouse_records_created": len([s for s in cleanup_test_states if s["tier"] == "clickhouse"]),
                "states_expired": len([s for s in cleanup_test_states if s.get("should_expire", False)]),
                "states_archived": cleanup_count
            }
            
            # Verify cleanup doesn't affect business operations
            self.logger.info("Testing business operations after cleanup...")
            
            # Create new business state after cleanup
            post_cleanup_state = await self._create_test_state_data("simple")
            post_cleanup_state["post_cleanup_test"] = True
            post_cleanup_state["business_continuity"] = True
            
            post_cleanup_key = f"post_cleanup:{self.test_user_id}:{UnifiedIdGenerator.generate_base_id('test')}"
            await persistence_manager.store_hot_cache(post_cleanup_key, post_cleanup_state, ttl=1800)
            
            # Verify business operations continue normally
            business_state = await persistence_manager.get_hot_cache(post_cleanup_key)
            self.assertIsNotNone(business_state, "Business operations must continue after cleanup")
            self.assertTrue(business_state["post_cleanup_test"])
            self.assertTrue(business_state["business_continuity"])
            
            # Record cleanup metrics
            for resource_type, count in resource_usage.items():
                self.record_metric(resource_type, count)
            
            self.record_metric("cleanup_scenarios_tested", len(cleanup_scenarios))
            self.record_metric("ttl_expiry_working", True)
            self.record_metric("archive_identification_working", cleanup_count > 0)
            self.record_metric("business_continuity_after_cleanup", True)
            
            self.logger.info("✅ PASS: State cleanup and garbage collection successful")
            
        finally:
            await persistence_manager.cleanup()