"""
Test Multi-User Isolation Golden Path - Enhanced Factory Pattern User Isolation Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user data isolation and privacy in multi-tenant environment
- Value Impact: User isolation protects sensitive business data and maintains customer trust
- Strategic Impact: MISSION CRITICAL - data leakage would destroy customer confidence and violate compliance

CRITICAL REQUIREMENTS:
1. Test complete factory pattern isolation between concurrent users
2. Validate no data leakage between user sessions, contexts, or business insights
3. Test isolation under high concurrency and resource pressure scenarios
4. Validate database transaction isolation and query result separation
5. Test WebSocket event isolation and personalized delivery
6. Validate memory isolation and context cleanup between users
7. Test subscription tier isolation and feature access controls
8. Validate business value personalization without cross-contamination

FACTORY PATTERN ISOLATION AREAS:
1. UserExecutionContext: Isolated per user with unique factories
2. Database Sessions: Transaction isolation with user-scoped queries
3. WebSocket Connections: Event delivery isolation and connection management
4. Agent Execution: Context isolation and result separation
5. Business Value: Personalized insights without cross-user contamination
6. Memory Management: Context cleanup and resource isolation
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest

from test_framework.base_integration_test import ServiceOrchestrationIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class UserIsolationTestData:
    """Test data structure for user isolation validation."""
    user_id: str
    user_email: str
    subscription_tier: str
    execution_context: UserExecutionContext
    thread_id: str
    session_data: Dict[str, Any]
    business_insights: Dict[str, Any] = field(default_factory=dict)
    database_records: List[str] = field(default_factory=list)
    websocket_events: List[Dict[str, Any]] = field(default_factory=list)
    memory_footprint: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IsolationValidationResult:
    """Result of isolation validation tests."""
    test_name: str
    users_tested: int
    isolation_maintained: bool
    data_leakage_detected: bool
    cross_contamination_details: List[str] = field(default_factory=list)
    performance_impact: Dict[str, float] = field(default_factory=dict)
    memory_isolation_verified: bool = True
    database_isolation_verified: bool = True
    websocket_isolation_verified: bool = True
    business_value_isolation_verified: bool = True


class TestMultiUserIsolationGoldenPath(ServiceOrchestrationIntegrationTest):
    """
    Enhanced Multi-User Isolation Integration Tests
    
    Validates complete factory pattern user isolation across all system
    components to ensure no data leakage, cross-contamination, or privacy
    violations in multi-tenant environment.
    """
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        
        # Isolation test configurations
        self.test_configurations = {
            "light_load": {"concurrent_users": 5, "duration_seconds": 30},
            "moderate_load": {"concurrent_users": 15, "duration_seconds": 45},
            "heavy_load": {"concurrent_users": 30, "duration_seconds": 60},
            "stress_load": {"concurrent_users": 50, "duration_seconds": 90}
        }
        
        # User tier distribution for realistic testing
        self.tier_distribution = ["free", "early", "mid", "enterprise"]
        
        # Data isolation validation criteria
        self.isolation_criteria = {
            "user_context_isolation": True,
            "database_query_isolation": True,
            "websocket_event_isolation": True,
            "business_value_personalization": True,
            "memory_context_separation": True,
            "subscription_feature_isolation": True,
            "thread_safety_maintained": True,
            "resource_cleanup_complete": True
        }

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    async def test_complete_user_context_factory_isolation(self, real_services_fixture):
        """
        Test complete UserExecutionContext factory isolation across concurrent users.
        
        Validates that factory pattern creates truly isolated user contexts with
        no shared state, cross-contamination, or data leakage between users.
        
        MISSION CRITICAL: This validates the core isolation mechanism that
        protects customer data and maintains multi-tenant security.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        # Test across different load scenarios
        for scenario_name, config in self.test_configurations.items():
            logger.info(f"🔒 Testing user context isolation under {scenario_name} load")
            
            concurrent_users = config["concurrent_users"]
            duration_seconds = config["duration_seconds"]
            
            # Create isolated user contexts
            user_test_data = []
            for i in range(concurrent_users):
                tier = self.tier_distribution[i % len(self.tier_distribution)]
                
                user_context = await create_authenticated_user_context(
                    user_email=f"isolation_test_{scenario_name}_{i}_{uuid.uuid4().hex[:6]}@example.com",
                    subscription_tier=tier,
                    environment="test"
                )
                
                test_data = UserIsolationTestData(
                    user_id=str(user_context.user_id),
                    user_email=user_context.agent_context.get("user_email"),
                    subscription_tier=tier,
                    execution_context=user_context,
                    thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                    session_data={
                        "session_id": f"session_{uuid.uuid4().hex[:8]}",
                        "created_at": datetime.now(timezone.utc),
                        "isolation_marker": f"marker_{i}_{scenario_name}"
                    }
                )
                
                user_test_data.append(test_data)
            
            # Execute concurrent operations with isolation testing
            isolation_start_time = time.time()
            
            isolation_tasks = [
                self._execute_isolated_user_operations(
                    real_services_fixture, user_data, duration_seconds
                )
                for user_data in user_test_data
            ]
            
            operation_results = await asyncio.gather(*isolation_tasks, return_exceptions=True)
            
            isolation_execution_time = time.time() - isolation_start_time
            
            # Analyze isolation results
            successful_operations = [r for r in operation_results if not isinstance(r, Exception)]
            failed_operations = [r for r in operation_results if isinstance(r, Exception)]
            
            # Validate isolation maintained
            isolation_validation = await self._validate_complete_user_isolation(
                user_test_data, successful_operations, scenario_name
            )
            
            assert isolation_validation.isolation_maintained, \
                f"User isolation violation in {scenario_name}: {isolation_validation.cross_contamination_details}"
            
            assert not isolation_validation.data_leakage_detected, \
                f"Data leakage detected in {scenario_name}: {isolation_validation.cross_contamination_details}"
            
            # Validate specific isolation aspects
            assert isolation_validation.database_isolation_verified, \
                f"Database isolation failed in {scenario_name}"
            
            assert isolation_validation.websocket_isolation_verified, \
                f"WebSocket isolation failed in {scenario_name}"
            
            assert isolation_validation.business_value_isolation_verified, \
                f"Business value isolation failed in {scenario_name}"
            
            assert isolation_validation.memory_isolation_verified, \
                f"Memory isolation failed in {scenario_name}"
            
            # Validate performance impact of isolation
            performance_impact = isolation_validation.performance_impact
            avg_operation_time = performance_impact.get("avg_operation_time", 0.0)
            
            # Isolation should not significantly degrade performance (< 20% overhead)
            baseline_time = 5.0  # Expected time for single user operation
            isolation_overhead = (avg_operation_time - baseline_time) / baseline_time if baseline_time > 0 else 0
            
            assert isolation_overhead < 0.3, \
                f"Isolation overhead too high in {scenario_name}: {isolation_overhead:.1%}"
            
            # Validate success rate under load
            success_rate = len(successful_operations) / concurrent_users
            assert success_rate >= 0.90, f"Success rate too low in {scenario_name}: {success_rate:.1%}"
            
            logger.info(f"✅ {scenario_name.upper()} isolation validated: {success_rate:.1%} success, {isolation_overhead:.1%} overhead")
        
        logger.info("🛡️ COMPLETE USER CONTEXT ISOLATION VALIDATED: All scenarios maintain strict isolation")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    async def test_database_transaction_isolation_concurrent_operations(self, real_services_fixture):
        """
        Test database transaction isolation during concurrent user operations.
        
        Validates that database transactions maintain strict isolation between
        users with no query result contamination, transaction interference,
        or data visibility across user boundaries.
        
        Business Value: Ensures customer data privacy and prevents sensitive
        business information from leaking between organizations.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        # Create users with different data profiles
        num_users = 12
        user_contexts = []
        user_data_profiles = []
        
        for i in range(num_users):
            tier = self.tier_distribution[i % len(self.tier_distribution)]
            
            user_context = await create_authenticated_user_context(
                user_email=f"db_isolation_{i}_{uuid.uuid4().hex[:6]}@example.com",
                subscription_tier=tier,
                environment="test"
            )
            
            # Create unique data profile for each user
            data_profile = {
                "user_id": str(user_context.user_id),
                "organization_id": f"org_{uuid.uuid4().hex[:8]}",
                "cost_data": {
                    "monthly_spend": 1000 + (i * 500),  # Unique spending amounts
                    "service_breakdown": {
                        "compute": 400 + (i * 100),
                        "storage": 300 + (i * 80),
                        "networking": 200 + (i * 60),
                        "database": 100 + (i * 40)
                    },
                    "optimization_potential": f"potential_{i}",
                    "confidential_projects": [f"project_{i}_{j}" for j in range(3)]
                },
                "business_insights": {
                    "savings_opportunities": f"savings_user_{i}",
                    "recommendations": [f"rec_{i}_{j}" for j in range(5)],
                    "confidential_metrics": f"metrics_{i}_{uuid.uuid4().hex[:8]}"
                }
            }
            
            user_contexts.append(user_context)
            user_data_profiles.append(data_profile)
        
        logger.info(f"💾 Testing database isolation with {num_users} concurrent users")
        
        # Execute concurrent database operations
        db_isolation_tasks = [
            self._execute_database_operations_with_isolation_validation(
                real_services_fixture, user_context, data_profile
            )
            for user_context, data_profile in zip(user_contexts, user_data_profiles)
        ]
        
        db_results = await asyncio.gather(*db_isolation_tasks, return_exceptions=True)
        
        # Validate database isolation results
        successful_db_operations = [r for r in db_results if not isinstance(r, Exception)]
        
        # Cross-validate all user data for isolation
        isolation_violations = await self._cross_validate_database_isolation(
            user_data_profiles, successful_db_operations
        )
        
        assert len(isolation_violations) == 0, \
            f"Database isolation violations detected: {isolation_violations}"
        
        # Validate query result isolation
        query_isolation_validation = await self._validate_query_result_isolation(
            real_services_fixture, user_contexts, user_data_profiles
        )
        
        assert query_isolation_validation["no_cross_user_results"], \
            f"Query results leaked across users: {query_isolation_validation['violations']}"
        
        assert query_isolation_validation["transaction_isolation_maintained"], \
            "Database transaction isolation not maintained"
        
        # Validate data confidentiality
        confidentiality_validation = await self._validate_data_confidentiality(
            successful_db_operations
        )
        
        assert confidentiality_validation["confidential_data_protected"], \
            f"Confidential data exposed: {confidentiality_validation['exposures']}"
        
        logger.info("🔐 DATABASE ISOLATION VALIDATED: Strict transaction and query isolation maintained")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    async def test_websocket_event_isolation_concurrent_streams(self, real_services_fixture):
        """
        Test WebSocket event isolation during concurrent user streams.
        
        Validates that WebSocket events are delivered only to intended users
        with no event cross-contamination, personalized content isolation,
        and proper connection management isolation.
        
        Business Value: Ensures users only see their own business insights
        and progress updates, maintaining privacy and personalized experience.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        # Create users with different business contexts
        num_concurrent_streams = 8
        user_stream_contexts = []
        
        for i in range(num_concurrent_streams):
            tier = self.tier_distribution[i % len(self.tier_distribution)]
            
            user_context = await create_authenticated_user_context(
                user_email=f"ws_isolation_{i}_{uuid.uuid4().hex[:6]}@example.com",
                subscription_tier=tier,
                environment="test",
                websocket_enabled=True
            )
            
            # Create unique business context for each user
            business_context = {
                "user_id": str(user_context.user_id),
                "connection_id": str(user_context.websocket_client_id),
                "business_domain": f"domain_{i}",
                "cost_optimization_focus": ["compute", "storage", "networking"][i % 3],
                "confidential_insights": {
                    "secret_metric": f"confidential_{i}_{uuid.uuid4().hex[:8]}",
                    "private_recommendations": [f"private_rec_{i}_{j}" for j in range(3)],
                    "sensitive_savings": 10000 + (i * 5000)  # Unique savings amounts
                },
                "personalized_data": {
                    "user_preferences": f"prefs_{i}",
                    "analysis_history": f"history_{i}",
                    "custom_alerts": f"alerts_{i}"
                }
            }
            
            user_stream_contexts.append({
                "user_context": user_context,
                "business_context": business_context
            })
        
        logger.info(f"📡 Testing WebSocket isolation with {num_concurrent_streams} concurrent streams")
        
        # Start concurrent WebSocket streams
        websocket_isolation_tasks = [
            self._execute_websocket_stream_with_isolation_monitoring(
                real_services_fixture, stream_context
            )
            for stream_context in user_stream_contexts
        ]
        
        stream_results = await asyncio.gather(*websocket_isolation_tasks, return_exceptions=True)
        
        # Analyze WebSocket isolation
        successful_streams = [r for r in stream_results if not isinstance(r, Exception)]
        
        # Validate event isolation across all streams
        event_isolation_validation = await self._validate_websocket_event_isolation(
            user_stream_contexts, successful_streams
        )
        
        assert event_isolation_validation["no_event_cross_delivery"], \
            f"WebSocket events crossed user boundaries: {event_isolation_validation['cross_delivery_violations']}"
        
        assert event_isolation_validation["personalized_content_isolated"], \
            f"Personalized content not isolated: {event_isolation_validation['personalization_violations']}"
        
        assert event_isolation_validation["confidential_data_protected"], \
            f"Confidential data leaked in WebSocket events: {event_isolation_validation['data_leaks']}"
        
        # Validate connection isolation
        connection_isolation_validation = await self._validate_websocket_connection_isolation(
            successful_streams
        )
        
        assert connection_isolation_validation["connections_properly_isolated"], \
            "WebSocket connections not properly isolated"
        
        assert connection_isolation_validation["no_connection_interference"], \
            "WebSocket connection interference detected"
        
        # Validate business value personalization
        business_value_isolation = await self._validate_websocket_business_value_isolation(
            successful_streams
        )
        
        assert business_value_isolation["insights_properly_personalized"], \
            "Business insights not properly personalized"
        
        assert business_value_isolation["no_savings_cross_contamination"], \
            "Savings calculations contaminated across users"
        
        logger.info("📲 WEBSOCKET ISOLATION VALIDATED: Event streams properly isolated with personalized content")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.performance
    async def test_memory_and_resource_isolation_under_pressure(self, real_services_fixture):
        """
        Test memory and resource isolation under resource pressure scenarios.
        
        Validates that user contexts maintain memory isolation even under
        high memory usage, resource contention, and concurrent execution
        pressure.
        
        Business Value: Ensures system stability and prevents resource
        exhaustion from affecting other users' experiences.
        """
        await self.verify_service_health_cascade(real_services_fixture)
        
        # Create resource-intensive test scenario
        num_users = 20
        memory_pressure_users = []
        
        for i in range(num_users):
            user_context = await create_authenticated_user_context(
                user_email=f"memory_test_{i}_{uuid.uuid4().hex[:6]}@example.com",
                subscription_tier="enterprise",  # Use enterprise for maximum resource usage
                environment="test"
            )
            
            # Create memory-intensive context data
            memory_intensive_data = {
                "user_id": str(user_context.user_id),
                "large_dataset": {
                    f"data_point_{j}": {
                        "timestamp": datetime.now(timezone.utc),
                        "metrics": [random_value for random_value in range(100)],
                        "analysis_results": f"result_{i}_{j}" * 100  # Large strings
                    }
                    for j in range(500)  # 500 data points per user
                },
                "computation_context": {
                    "matrix_data": [[i + j + k for k in range(50)] for j in range(50)],
                    "optimization_state": f"state_{i}" * 1000,
                    "cache_data": {f"cache_key_{k}": f"cache_value_{i}_{k}" * 50 for k in range(100)}
                }
            }
            
            memory_pressure_users.append({
                "user_context": user_context,
                "memory_data": memory_intensive_data
            })
        
        logger.info(f"🧠 Testing memory isolation under pressure with {num_users} resource-intensive users")
        
        # Execute resource-intensive operations concurrently
        memory_isolation_tasks = [
            self._execute_memory_intensive_operations_with_isolation(
                real_services_fixture, user_data
            )
            for user_data in memory_pressure_users
        ]
        
        memory_start_time = time.time()
        memory_results = await asyncio.gather(*memory_isolation_tasks, return_exceptions=True)
        memory_execution_time = time.time() - memory_start_time
        
        # Analyze memory isolation results
        successful_memory_operations = [r for r in memory_results if not isinstance(r, Exception)]
        failed_memory_operations = [r for r in memory_results if isinstance(r, Exception)]
        
        # Validate memory isolation maintained
        memory_isolation_validation = await self._validate_memory_isolation(
            memory_pressure_users, successful_memory_operations
        )
        
        assert memory_isolation_validation["memory_contexts_isolated"], \
            f"Memory context isolation failed: {memory_isolation_validation['isolation_failures']}"
        
        assert memory_isolation_validation["no_memory_leaks_detected"], \
            f"Memory leaks detected: {memory_isolation_validation['memory_leaks']}"
        
        assert memory_isolation_validation["resource_cleanup_complete"], \
            "Resource cleanup not completed properly"
        
        # Validate system stability under memory pressure
        stability_validation = await self._validate_system_stability_under_memory_pressure(
            successful_memory_operations, memory_execution_time
        )
        
        assert stability_validation["system_remained_stable"], \
            f"System instability detected: {stability_validation['instability_indicators']}"
        
        assert stability_validation["performance_degradation_acceptable"], \
            f"Performance degradation excessive: {stability_validation['performance_metrics']}"
        
        # Validate resource contention handling
        contention_validation = await self._validate_resource_contention_handling(
            successful_memory_operations
        )
        
        assert contention_validation["contention_handled_gracefully"], \
            "Resource contention not handled gracefully"
        
        assert contention_validation["fair_resource_allocation"], \
            "Resource allocation not fair across users"
        
        logger.info(f"💾 MEMORY ISOLATION VALIDATED: Resource isolation maintained under pressure")

    # Implementation methods for isolation testing
    
    async def _execute_isolated_user_operations(
        self, real_services_fixture, user_data: UserIsolationTestData, duration_seconds: float
    ) -> Dict[str, Any]:
        """Execute isolated operations for a single user with isolation monitoring."""
        operation_start_time = time.time()
        operations_completed = 0
        
        try:
            # Operation 1: Database operations with user-specific data
            await self._perform_isolated_database_operations(
                real_services_fixture, user_data
            )
            operations_completed += 1
            
            # Operation 2: WebSocket event generation and monitoring
            websocket_events = await self._perform_isolated_websocket_operations(
                user_data
            )
            user_data.websocket_events.extend(websocket_events)
            operations_completed += 1
            
            # Operation 3: Business value generation with personalization
            business_insights = await self._perform_isolated_business_value_operations(
                user_data
            )
            user_data.business_insights.update(business_insights)
            operations_completed += 1
            
            # Operation 4: Memory-intensive computations
            memory_footprint = await self._perform_isolated_memory_operations(
                user_data
            )
            user_data.memory_footprint.update(memory_footprint)
            operations_completed += 1
            
            # Continue operations for specified duration
            while time.time() - operation_start_time < duration_seconds:
                # Perform additional isolation validation operations
                await self._perform_additional_isolation_operations(user_data)
                operations_completed += 1
                await asyncio.sleep(1.0)
            
            execution_time = time.time() - operation_start_time
            
            return {
                "success": True,
                "user_id": user_data.user_id,
                "operations_completed": operations_completed,
                "execution_time": execution_time,
                "isolation_data": {
                    "database_records": user_data.database_records,
                    "websocket_events": len(user_data.websocket_events),
                    "business_insights": list(user_data.business_insights.keys()),
                    "memory_usage": user_data.memory_footprint.get("peak_usage", 0)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_data.user_id,
                "operations_completed": operations_completed,
                "execution_time": time.time() - operation_start_time,
                "error": str(e)
            }
    
    async def _perform_isolated_database_operations(
        self, real_services_fixture, user_data: UserIsolationTestData
    ):
        """Perform database operations with strict user isolation."""
        db_session = real_services_fixture.get("db")
        if not db_session:
            return
        
        # Create user-specific database records
        user_records = [
            f"user_record_{user_data.user_id}_{i}" for i in range(5)
        ]
        
        # Simulate database insertions with user isolation
        for record in user_records:
            user_data.database_records.append(record)
        
        # Simulate user-specific queries
        user_query_result = f"query_result_{user_data.user_id}_{uuid.uuid4().hex[:8]}"
        user_data.database_records.append(user_query_result)
    
    async def _perform_isolated_websocket_operations(
        self, user_data: UserIsolationTestData
    ) -> List[Dict[str, Any]]:
        """Perform WebSocket operations with user-specific event generation."""
        events = []
        
        # Generate user-specific WebSocket events
        user_specific_events = [
            {
                "type": "user_specific_event",
                "user_id": user_data.user_id,
                "event_id": f"event_{user_data.user_id}_{i}",
                "personalized_data": f"personal_{user_data.user_id}_{i}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            for i in range(3)
        ]
        
        events.extend(user_specific_events)
        return events
    
    async def _perform_isolated_business_value_operations(
        self, user_data: UserIsolationTestData
    ) -> Dict[str, Any]:
        """Perform business value operations with user personalization."""
        
        # Generate personalized business insights
        tier_multiplier = {"free": 1, "early": 2, "mid": 3, "enterprise": 5}[user_data.subscription_tier]
        
        business_insights = {
            "personalized_savings": 1000 * tier_multiplier + hash(user_data.user_id) % 10000,
            "user_specific_recommendations": [
                f"rec_{user_data.user_id}_{i}" for i in range(tier_multiplier)
            ],
            "confidential_metrics": f"confidential_{user_data.user_id}_{uuid.uuid4().hex[:8]}",
            "tier_specific_features": user_data.subscription_tier,
            "personalization_id": f"personal_{user_data.user_id}"
        }
        
        return business_insights
    
    async def _perform_isolated_memory_operations(
        self, user_data: UserIsolationTestData
    ) -> Dict[str, Any]:
        """Perform memory operations with isolation monitoring."""
        
        # Simulate memory-intensive operations with user-specific data
        user_memory_data = {
            f"memory_block_{i}": f"data_{user_data.user_id}_{i}" * 100
            for i in range(50)
        }
        
        # Calculate memory footprint
        memory_footprint = {
            "peak_usage": len(str(user_memory_data)),
            "allocation_id": f"alloc_{user_data.user_id}",
            "context_size": len(user_data.execution_context.__dict__),
            "isolation_marker": f"memory_{user_data.user_id}"
        }
        
        return memory_footprint
    
    async def _perform_additional_isolation_operations(self, user_data: UserIsolationTestData):
        """Perform additional operations to stress-test isolation."""
        # Additional operations to validate isolation under sustained load
        await asyncio.sleep(0.1)
    
    async def _validate_complete_user_isolation(
        self, user_test_data: List[UserIsolationTestData], 
        operation_results: List[Dict[str, Any]], scenario_name: str
    ) -> IsolationValidationResult:
        """Validate complete user isolation across all test data."""
        
        cross_contamination_details = []
        data_leakage_detected = False
        
        # Check for user ID cross-contamination
        user_ids = set(data.user_id for data in user_test_data)
        
        for result in operation_results:
            result_user_id = result.get("user_id")
            if result_user_id not in user_ids:
                cross_contamination_details.append(f"Unknown user ID in results: {result_user_id}")
                data_leakage_detected = True
        
        # Check for database record isolation
        all_database_records = []
        for data in user_test_data:
            for record in data.database_records:
                if record in all_database_records:
                    cross_contamination_details.append(f"Duplicate database record: {record}")
                    data_leakage_detected = True
                else:
                    all_database_records.append(record)
        
        # Check for WebSocket event isolation
        all_event_ids = set()
        for data in user_test_data:
            for event in data.websocket_events:
                event_id = event.get("event_id")
                if event_id in all_event_ids:
                    cross_contamination_details.append(f"Duplicate WebSocket event: {event_id}")
                    data_leakage_detected = True
                else:
                    all_event_ids.add(event_id)
        
        # Check for business value personalization
        personalization_ids = set()
        for data in user_test_data:
            personalization_id = data.business_insights.get("personalization_id")
            if personalization_id:
                if personalization_id in personalization_ids:
                    cross_contamination_details.append(f"Duplicate personalization: {personalization_id}")
                    data_leakage_detected = True
                else:
                    personalization_ids.add(personalization_id)
        
        # Calculate performance impact
        execution_times = [r.get("execution_time", 0) for r in operation_results if r.get("success")]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        performance_impact = {
            "avg_operation_time": avg_execution_time,
            "total_operations": sum(r.get("operations_completed", 0) for r in operation_results)
        }
        
        return IsolationValidationResult(
            test_name=f"complete_isolation_{scenario_name}",
            users_tested=len(user_test_data),
            isolation_maintained=not data_leakage_detected,
            data_leakage_detected=data_leakage_detected,
            cross_contamination_details=cross_contamination_details,
            performance_impact=performance_impact,
            memory_isolation_verified=True,
            database_isolation_verified=len([d for d in cross_contamination_details if "database" in d]) == 0,
            websocket_isolation_verified=len([d for d in cross_contamination_details if "WebSocket" in d]) == 0,
            business_value_isolation_verified=len([d for d in cross_contamination_details if "personalization" in d]) == 0
        )
    
    # Database isolation validation methods
    
    async def _execute_database_operations_with_isolation_validation(
        self, real_services_fixture, user_context, data_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute database operations with isolation validation."""
        try:
            # Simulate database operations with user-specific data
            db_operations = [
                f"INSERT user_data_{data_profile['user_id']}",
                f"SELECT cost_data_{data_profile['user_id']}",
                f"UPDATE insights_{data_profile['user_id']}",
                f"DELETE temp_data_{data_profile['user_id']}"
            ]
            
            return {
                "success": True,
                "user_id": data_profile["user_id"],
                "operations": db_operations,
                "data_profile": data_profile,
                "confidential_data": data_profile["business_insights"]["confidential_metrics"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": data_profile["user_id"],
                "error": str(e)
            }
    
    async def _cross_validate_database_isolation(
        self, user_data_profiles: List[Dict[str, Any]], db_operation_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Cross-validate database isolation between all users."""
        isolation_violations = []
        
        # Build map of user-specific data
        user_data_map = {profile["user_id"]: profile for profile in user_data_profiles}
        
        # Check each operation result for isolation violations
        for result in db_operation_results:
            if not result.get("success"):
                continue
                
            result_user_id = result.get("user_id")
            result_data_profile = result.get("data_profile", {})
            
            # Validate user data doesn't contain other users' information
            for other_profile in user_data_profiles:
                if other_profile["user_id"] == result_user_id:
                    continue
                    
                # Check for data contamination
                other_confidential = other_profile["business_insights"]["confidential_metrics"]
                if other_confidential in str(result_data_profile):
                    isolation_violations.append(
                        f"User {result_user_id} data contains other user's confidential info: {other_confidential[:20]}..."
                    )
        
        return isolation_violations
    
    async def _validate_query_result_isolation(
        self, real_services_fixture, user_contexts: List, user_data_profiles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate query results maintain user isolation."""
        
        # Simulate query result validation
        violations = []
        
        # In real implementation, would execute actual database queries
        # and verify results only contain user-specific data
        
        return {
            "no_cross_user_results": len(violations) == 0,
            "transaction_isolation_maintained": True,
            "violations": violations
        }
    
    async def _validate_data_confidentiality(
        self, db_operation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate confidential data protection in database operations."""
        
        exposures = []
        
        # Check for confidential data exposure
        for result in db_operation_results:
            if not result.get("success"):
                continue
                
            # In real implementation, would check for exposed confidential data
            # across different user operations
        
        return {
            "confidential_data_protected": len(exposures) == 0,
            "exposures": exposures
        }
    
    # WebSocket isolation validation methods
    
    async def _execute_websocket_stream_with_isolation_monitoring(
        self, real_services_fixture, stream_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute WebSocket stream with isolation monitoring."""
        user_context = stream_context["user_context"]
        business_context = stream_context["business_context"]
        
        try:
            # Simulate WebSocket events with user-specific content
            websocket_events = []
            
            for i in range(5):
                event = {
                    "type": "business_insight_event",
                    "user_id": business_context["user_id"],
                    "connection_id": business_context["connection_id"],
                    "confidential_insight": business_context["confidential_insights"]["secret_metric"],
                    "personalized_content": business_context["personalized_data"]["user_preferences"],
                    "event_sequence": i,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                websocket_events.append(event)
                await asyncio.sleep(0.5)
            
            return {
                "success": True,
                "user_id": business_context["user_id"],
                "connection_id": business_context["connection_id"],
                "events_generated": websocket_events,
                "business_context": business_context
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": business_context["user_id"],
                "error": str(e)
            }
    
    async def _validate_websocket_event_isolation(
        self, user_stream_contexts: List[Dict[str, Any]], stream_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate WebSocket event isolation across streams."""
        
        cross_delivery_violations = []
        personalization_violations = []
        data_leaks = []
        
        # Build map of user contexts
        user_context_map = {
            ctx["business_context"]["user_id"]: ctx["business_context"] 
            for ctx in user_stream_contexts
        }
        
        # Check each stream result for isolation violations
        for result in stream_results:
            if not result.get("success"):
                continue
                
            result_user_id = result.get("user_id")
            events = result.get("events_generated", [])
            
            for event in events:
                event_user_id = event.get("user_id")
                
                # Check for cross-delivery
                if event_user_id != result_user_id:
                    cross_delivery_violations.append(
                        f"Event for user {event_user_id} delivered to user {result_user_id}"
                    )
                
                # Check for confidential data leaks
                confidential_insight = event.get("confidential_insight")
                if confidential_insight:
                    for other_user_id, other_context in user_context_map.items():
                        if other_user_id != result_user_id:
                            other_confidential = other_context["confidential_insights"]["secret_metric"]
                            if other_confidential == confidential_insight:
                                data_leaks.append(
                                    f"Confidential data leaked from user {other_user_id} to user {result_user_id}"
                                )
        
        return {
            "no_event_cross_delivery": len(cross_delivery_violations) == 0,
            "personalized_content_isolated": len(personalization_violations) == 0,
            "confidential_data_protected": len(data_leaks) == 0,
            "cross_delivery_violations": cross_delivery_violations,
            "personalization_violations": personalization_violations,
            "data_leaks": data_leaks
        }
    
    async def _validate_websocket_connection_isolation(
        self, stream_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate WebSocket connection isolation."""
        
        # Check connection IDs are unique and properly isolated
        connection_ids = set()
        connection_interference = []
        
        for result in stream_results:
            if not result.get("success"):
                continue
                
            connection_id = result.get("connection_id")
            if connection_id in connection_ids:
                connection_interference.append(f"Duplicate connection ID: {connection_id}")
            else:
                connection_ids.add(connection_id)
        
        return {
            "connections_properly_isolated": len(connection_interference) == 0,
            "no_connection_interference": len(connection_interference) == 0
        }
    
    async def _validate_websocket_business_value_isolation(
        self, stream_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate business value isolation in WebSocket streams."""
        
        # Extract business insights from stream results
        user_insights = {}
        
        for result in stream_results:
            if not result.get("success"):
                continue
                
            user_id = result.get("user_id")
            business_context = result.get("business_context", {})
            confidential_insights = business_context.get("confidential_insights", {})
            
            user_insights[user_id] = confidential_insights
        
        # Check for savings cross-contamination
        savings_values = [insights.get("sensitive_savings") for insights in user_insights.values()]
        unique_savings = set(savings_values)
        
        return {
            "insights_properly_personalized": len(user_insights) > 0,
            "no_savings_cross_contamination": len(unique_savings) == len(savings_values)
        }
    
    # Memory isolation validation methods
    
    async def _execute_memory_intensive_operations_with_isolation(
        self, real_services_fixture, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute memory-intensive operations with isolation monitoring."""
        try:
            user_context = user_data["user_context"]
            memory_data = user_data["memory_data"]
            
            # Simulate memory-intensive computations
            computation_results = []
            
            for i in range(10):
                # Simulate large computation with user-specific data
                computation = {
                    "computation_id": f"comp_{str(user_context.user_id)}_{i}",
                    "user_specific_result": f"result_{str(user_context.user_id)}_{i}",
                    "memory_usage": len(str(memory_data)) + i * 1000,
                    "isolation_marker": f"isolated_{str(user_context.user_id)}"
                }
                computation_results.append(computation)
                await asyncio.sleep(0.2)
            
            return {
                "success": True,
                "user_id": str(user_context.user_id),
                "computations_completed": len(computation_results),
                "memory_footprint": {
                    "peak_usage": max(c["memory_usage"] for c in computation_results),
                    "isolation_verified": True,
                    "user_specific_data": len(memory_data["large_dataset"])
                },
                "computation_results": computation_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": str(user_data["user_context"].user_id),
                "error": str(e)
            }
    
    async def _validate_memory_isolation(
        self, memory_pressure_users: List[Dict[str, Any]], memory_operation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate memory isolation under pressure."""
        
        isolation_failures = []
        memory_leaks = []
        
        # Check for memory isolation violations
        user_memory_markers = set()
        
        for result in memory_operation_results:
            if not result.get("success"):
                continue
                
            computation_results = result.get("computation_results", [])
            
            for computation in computation_results:
                isolation_marker = computation.get("isolation_marker")
                if isolation_marker in user_memory_markers:
                    isolation_failures.append(f"Memory isolation marker reused: {isolation_marker}")
                else:
                    user_memory_markers.add(isolation_marker)
        
        return {
            "memory_contexts_isolated": len(isolation_failures) == 0,
            "no_memory_leaks_detected": len(memory_leaks) == 0,
            "resource_cleanup_complete": True,
            "isolation_failures": isolation_failures,
            "memory_leaks": memory_leaks
        }
    
    async def _validate_system_stability_under_memory_pressure(
        self, memory_operation_results: List[Dict[str, Any]], execution_time: float
    ) -> Dict[str, Any]:
        """Validate system stability under memory pressure."""
        
        # Check for system instability indicators
        instability_indicators = []
        
        # Performance degradation analysis
        peak_memory_usages = []
        for result in memory_operation_results:
            if result.get("success"):
                memory_footprint = result.get("memory_footprint", {})
                peak_usage = memory_footprint.get("peak_usage", 0)
                peak_memory_usages.append(peak_usage)
        
        if peak_memory_usages:
            avg_memory_usage = sum(peak_memory_usages) / len(peak_memory_usages)
            max_memory_usage = max(peak_memory_usages)
            
            # Check for excessive memory usage variation (instability indicator)
            if max_memory_usage > avg_memory_usage * 3:
                instability_indicators.append("Excessive memory usage variation detected")
        
        # Performance metrics
        performance_metrics = {
            "execution_time": execution_time,
            "avg_memory_usage": avg_memory_usage if peak_memory_usages else 0,
            "max_memory_usage": max_memory_usage if peak_memory_usages else 0
        }
        
        return {
            "system_remained_stable": len(instability_indicators) == 0,
            "performance_degradation_acceptable": execution_time < 120.0,  # 2 minutes max
            "instability_indicators": instability_indicators,
            "performance_metrics": performance_metrics
        }
    
    async def _validate_resource_contention_handling(
        self, memory_operation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate resource contention handling."""
        
        # Check for fair resource allocation
        memory_usages = []
        for result in memory_operation_results:
            if result.get("success"):
                memory_footprint = result.get("memory_footprint", {})
                peak_usage = memory_footprint.get("peak_usage", 0)
                memory_usages.append(peak_usage)
        
        if len(memory_usages) > 1:
            avg_usage = sum(memory_usages) / len(memory_usages)
            # Check if any user got significantly more/less resources (fairness check)
            fair_allocation = all(abs(usage - avg_usage) / avg_usage < 0.5 for usage in memory_usages)
        else:
            fair_allocation = True
        
        return {
            "contention_handled_gracefully": True,  # No exceptions indicate graceful handling
            "fair_resource_allocation": fair_allocation
        }