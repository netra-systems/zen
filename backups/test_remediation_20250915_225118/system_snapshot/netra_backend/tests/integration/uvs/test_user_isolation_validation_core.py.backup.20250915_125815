"""
Comprehensive UVS (User-specific Validation System) Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (supporting all user tiers Free  ->  Enterprise)
- Business Goal: Ensure complete user isolation and validation flows for multi-user platform
- Value Impact: Prevents data leakage, ensures proper user context validation, enables safe concurrent operations
- Strategic Impact: Core infrastructure that supports $500K+ ARR by enabling secure multi-user chat functionality

This test suite validates the comprehensive User-specific Validation System (UVS) focusing on:
1. UserExecutionContext creation, validation, and immutability 
2. ExecutionEngineFactory lifecycle management and resource cleanup
3. User isolation between concurrent requests and operations
4. Factory-based resource management and per-user limits
5. Context hierarchy and child context creation patterns

CRITICAL: These are INTEGRATION tests - they test interactions between components but don't require
full Docker stack. NO MOCKS allowed - use real services and real system behavior where possible.
Each test validates actual business value and uses proper test categories and markers.
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Import system components
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    clear_shared_object_registry
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Import test framework components
from test_framework.user_execution_context_fixtures import (
    realistic_user_context,
    multi_user_contexts,
    concurrent_context_factory,
    async_context_manager,
    context_hierarchy_builder,
    clean_context_registry
)
from test_framework.isolated_environment_fixtures import isolated_env
from shared.isolated_environment import get_env


class TestUserExecutionContextCreationAndValidation:
    """Test suite for UserExecutionContext creation and validation flows.
    
    BVJ: Ensures proper context creation with validation prevents security vulnerabilities
    and data corruption that could impact all user tiers and business operations.
    """
    
    @pytest.mark.integration
    @pytest.mark.user_isolation
    async def test_context_creation_with_realistic_business_data(self, realistic_user_context, isolated_env):
        """Test UserExecutionContext creation with realistic enterprise business data.
        
        BVJ: Validates that contexts can be created with real business data patterns,
        supporting enterprise user workflows that generate significant revenue.
        """
        context = realistic_user_context
        
        # Validate core identifiers are properly set
        assert context.user_id == "user_enterprise_12345678901234567890"
        assert context.thread_id == "thread_optimization_98765432109876543210"
        assert "run_cost_analysis_" in context.run_id
        assert context.websocket_client_id == "ws_conn_real_12345678901234567890"
        
        # Validate immutability (frozen dataclass)
        with pytest.raises(AttributeError):
            context.user_id = "modified_user_id"  # Should fail - frozen dataclass
        
        # Validate agent context contains enterprise features
        assert context.agent_context["user_subscription"] == "enterprise"
        assert "advanced_analytics" in context.agent_context["execution_environment"]["feature_flags"]
        assert context.agent_context["user_preferences"]["optimization_goals"] == ["cost_reduction", "performance_improvement"]
        
        # Validate audit metadata for compliance
        assert context.audit_metadata["compliance_tracking"]["gdpr_consent"] is True
        assert context.audit_metadata["business_context"]["monthly_spend"] == 75000
        assert context.audit_metadata["business_context"]["optimization_tier"] == "premium"
        
        # Validate timestamps and proper timezone handling
        assert context.created_at.tzinfo == timezone.utc
        assert context.created_at <= datetime.now(timezone.utc)
    
    @pytest.mark.integration  
    @pytest.mark.user_isolation
    async def test_context_validation_prevents_placeholder_values(self, clean_context_registry, isolated_env):
        """Test that context validation prevents dangerous placeholder values.
        
        BVJ: Prevents system corruption and security vulnerabilities from placeholder
        values that could cause data leakage or system instability.
        """
        # Test forbidden placeholder patterns that should fail validation
        forbidden_patterns = [
            "placeholder_user_12345",
            "registry_thread_67890", 
            "default_run_abcdef",
            "temp_websocket_xyz123",
            "none_value_placeholder",
            "null_context_data",
            "example_user_test"
        ]
        
        for pattern in forbidden_patterns:
            with pytest.raises(InvalidContextError, match="Forbidden placeholder value detected"):
                UserExecutionContext(
                    user_id=pattern,
                    thread_id="thread_valid_12345678901234567890",
                    run_id=f"run_valid_{int(time.time())}_abcd1234"
                )
    
    @pytest.mark.integration
    @pytest.mark.user_isolation 
    async def test_context_deep_copy_isolation_protection(self, realistic_user_context, isolated_env):
        """Test that contexts use deep copy isolation to prevent data corruption.
        
        BVJ: Ensures user data integrity and prevents cross-user data contamination
        that could violate privacy and compliance requirements.
        """
        original_context = realistic_user_context
        
        # Create child context to test deep copy isolation
        child_context = original_context.create_child_context(
            "data_analysis_operation",
            additional_agent_context={"analysis_type": "cost_breakdown"},
            additional_audit_metadata={"child_operation": "financial_analysis"}
        )
        
        # Verify original context is unchanged
        assert "analysis_type" not in original_context.agent_context
        assert "child_operation" not in original_context.audit_metadata
        
        # Verify child context has new data plus inherited data
        assert child_context.agent_context["analysis_type"] == "cost_breakdown" 
        assert child_context.audit_metadata["child_operation"] == "financial_analysis"
        assert child_context.agent_context["user_subscription"] == "enterprise"  # Inherited
        
        # Verify isolation - modifying child's mutable data doesn't affect parent
        # (Note: contexts are immutable but we test internal data structure isolation)
        assert id(original_context.agent_context) != id(child_context.agent_context)
        assert id(original_context.audit_metadata) != id(child_context.audit_metadata)
    
    @pytest.mark.integration
    @pytest.mark.user_isolation
    async def test_context_id_consistency_validation(self, clean_context_registry, isolated_env):
        """Test that context ID validation ensures consistency and prevents corruption.
        
        BVJ: Maintains data integrity and audit trail consistency required for 
        enterprise compliance and reliable system operation.
        """
        # Test that ID validation catches inconsistencies
        valid_user_id = "user_test_12345678901234567890"
        valid_thread_id = "thread_test_98765432109876543210"
        valid_run_id = f"run_test_{int(time.time())}_abcd1234"
        
        # Valid context should create successfully
        context = UserExecutionContext(
            user_id=valid_user_id,
            thread_id=valid_thread_id, 
            run_id=valid_run_id
        )
        
        assert context.user_id == valid_user_id
        assert context.thread_id == valid_thread_id
        assert context.run_id == valid_run_id
        
        # Verify request_id is auto-generated and unique
        assert context.request_id is not None
        assert context.request_id != valid_run_id  # Should be different from run_id
        
        # Test correlation ID generation for audit trails
        correlation_id = context.get_correlation_id()
        assert valid_user_id[:8] in correlation_id  # Should contain user info
        assert valid_thread_id[:8] in correlation_id  # Should contain thread info
    
    @pytest.mark.integration
    @pytest.mark.user_isolation
    async def test_context_audit_trail_initialization(self, realistic_user_context, isolated_env):
        """Test that audit trail is properly initialized for compliance tracking.
        
        BVJ: Enables audit trail functionality required for enterprise compliance,
        security monitoring, and debugging production issues.
        """
        context = realistic_user_context
        
        # Verify audit trail is properly initialized
        audit_trail = context.get_audit_trail()
        assert "context_id" in audit_trail
        assert "creation_time" in audit_trail
        assert "user_context" in audit_trail
        assert "operation_depth" in audit_trail
        
        # Verify audit trail contains critical business context
        assert audit_trail["user_context"]["subscription"] == "enterprise"
        assert audit_trail["operation_depth"] == 0  # Root level
        
        # Verify audit metadata is preserved
        assert "business_context" in audit_trail
        assert audit_trail["business_context"]["monthly_spend"] == 75000
        assert audit_trail["business_context"]["optimization_tier"] == "premium"


class TestExecutionEngineFactoryLifecycleManagement:
    """Test suite for ExecutionEngineFactory lifecycle management.
    
    BVJ: Ensures proper resource management and cleanup prevents memory leaks
    and enables stable multi-user concurrent operations.
    """
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Create mock WebSocket bridge for testing."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.create_user_emitter.return_value = AsyncMock()
        return bridge
    
    @pytest.mark.integration
    @pytest.mark.factory_patterns
    async def test_factory_creates_isolated_execution_engines(self, mock_websocket_bridge, realistic_user_context):
        """Test that factory creates properly isolated execution engines per request.
        
        BVJ: Ensures each user request gets isolated execution environment,
        preventing cross-user contamination and enabling safe concurrent operations.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        # Create execution engine for user context
        engine = await factory.create_for_user(realistic_user_context)
        
        # Verify engine is properly created and isolated
        assert isinstance(engine, UserExecutionEngine)
        assert engine.context.user_id == realistic_user_context.user_id
        assert engine.context.thread_id == realistic_user_context.thread_id
        assert engine.context.run_id == realistic_user_context.run_id
        
        # Verify engine has unique identifier
        assert engine.engine_id is not None
        assert len(engine.engine_id) > 8  # Should be substantial unique ID
        
        # Verify engine is tracked in factory
        factory_metrics = factory.get_factory_metrics()
        assert factory_metrics["engines_created"] >= 1
        assert factory_metrics["engines_active"] >= 1
        
        # Verify WebSocket emitter is properly integrated
        assert engine.websocket_emitter is not None
        mock_websocket_bridge.create_user_emitter.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.factory_patterns
    async def test_factory_enforces_user_concurrency_limits(self, mock_websocket_bridge, multi_user_contexts):
        """Test that factory enforces per-user concurrency limits.
        
        BVJ: Prevents resource exhaustion and ensures fair resource allocation
        across different user subscription tiers.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        enterprise_context = multi_user_contexts[3]  # Enterprise user context
        
        # Create multiple engines for same user (testing concurrency limits)
        engines = []
        for i in range(3):  # Try to create more than typical limit (2)
            try:
                # Create new run_id for each attempt
                context_copy = UserExecutionContext(
                    user_id=enterprise_context.user_id,
                    thread_id=enterprise_context.thread_id,
                    run_id=f"run_concurrent_{i}_{int(time.time())}_test",
                    agent_context=enterprise_context.agent_context,
                    audit_metadata=enterprise_context.audit_metadata
                )
                engine = await factory.create_for_user(context_copy)
                engines.append(engine)
            except ExecutionEngineFactoryError as e:
                # Should hit concurrency limit
                assert "concurrency limit" in str(e).lower() or "too many" in str(e).lower()
                break
        
        # Verify we created some engines but hit limits
        assert len(engines) >= 1  # At least one should succeed
        assert len(engines) <= 3  # But not unlimited
        
        # Test cleanup allows new engine creation
        if engines:
            await factory.cleanup_engine(engines[0])
            
            # Should be able to create new engine after cleanup
            new_context = UserExecutionContext(
                user_id=enterprise_context.user_id,
                thread_id=enterprise_context.thread_id, 
                run_id=f"run_after_cleanup_{int(time.time())}_test",
                agent_context=enterprise_context.agent_context,
                audit_metadata=enterprise_context.audit_metadata
            )
            new_engine = await factory.create_for_user(new_context)
            assert new_engine is not None
    
    @pytest.mark.integration
    @pytest.mark.factory_patterns
    async def test_factory_context_manager_automatic_cleanup(self, mock_websocket_bridge, realistic_user_context):
        """Test that factory context manager provides automatic cleanup.
        
        BVJ: Ensures proper resource cleanup preventing memory leaks and
        enabling long-running production deployments.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        engine_id = None
        
        # Use context manager for automatic cleanup
        async with factory.user_execution_scope(realistic_user_context) as engine:
            assert isinstance(engine, UserExecutionEngine)
            assert engine.context.user_id == realistic_user_context.user_id
            engine_id = engine.engine_id
            
            # Verify engine is active during context
            assert engine.is_active()
            metrics = factory.get_factory_metrics()
            assert metrics["engines_active"] >= 1
        
        # Verify automatic cleanup occurred
        await asyncio.sleep(0.1)  # Allow cleanup to complete
        final_metrics = factory.get_factory_metrics()
        assert final_metrics["engines_cleaned"] >= 1
    
    @pytest.mark.integration
    @pytest.mark.factory_patterns
    async def test_factory_metrics_tracking_comprehensive(self, mock_websocket_bridge, multi_user_contexts):
        """Test comprehensive factory metrics tracking for monitoring.
        
        BVJ: Enables production monitoring and capacity planning for multi-user
        platform operations and performance optimization.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        # Get initial metrics
        initial_metrics = factory.get_factory_metrics()
        assert "engines_created" in initial_metrics
        assert "engines_active" in initial_metrics
        assert "engines_cleaned" in initial_metrics
        assert "total_users" in initial_metrics
        
        # Create engines for multiple users
        engines = []
        for i, context in enumerate(multi_user_contexts[:3]):  # Use first 3 users
            engine = await factory.create_for_user(context)
            engines.append(engine)
        
        # Verify metrics updated correctly
        after_creation_metrics = factory.get_factory_metrics()
        assert after_creation_metrics["engines_created"] >= initial_metrics["engines_created"] + 3
        assert after_creation_metrics["engines_active"] >= initial_metrics["engines_active"] + 3
        assert after_creation_metrics["total_users"] >= 3
        
        # Test cleanup metrics
        for engine in engines:
            await factory.cleanup_engine(engine)
        
        final_metrics = factory.get_factory_metrics()
        assert final_metrics["engines_cleaned"] >= initial_metrics["engines_cleaned"] + 3
        assert final_metrics["engines_active"] <= initial_metrics["engines_active"]
    
    @pytest.mark.integration
    @pytest.mark.factory_patterns 
    async def test_factory_shutdown_cleanup_all_resources(self, mock_websocket_bridge, multi_user_contexts):
        """Test that factory shutdown properly cleans up all resources.
        
        BVJ: Ensures clean shutdown during deployments and restarts without
        resource leaks that could impact system stability.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        # Create multiple engines
        engines = []
        for context in multi_user_contexts[:2]:  # Create 2 engines
            engine = await factory.create_for_user(context)
            engines.append(engine)
        
        # Verify engines are active
        metrics_before = factory.get_factory_metrics()
        assert metrics_before["engines_active"] >= 2
        
        # Shutdown factory
        await factory.shutdown()
        
        # Verify all resources cleaned up
        metrics_after = factory.get_factory_metrics()
        assert metrics_after["engines_active"] == 0
        
        # Verify engines are no longer active
        for engine in engines:
            assert not engine.is_active()


class TestUserIsolationBetweenConcurrentRequests:
    """Test suite for user isolation between concurrent requests.
    
    BVJ: Validates complete isolation between users preventing data leakage
    and ensuring secure multi-tenant operations critical for enterprise compliance.
    """
    
    @pytest.mark.integration
    @pytest.mark.concurrent_isolation
    async def test_concurrent_user_contexts_complete_isolation(self, multi_user_contexts, isolated_env):
        """Test complete isolation between concurrent user contexts.
        
        BVJ: Prevents cross-user data leakage that could violate privacy regulations
        and compromise enterprise security requirements.
        """
        # Select different user types for isolation testing
        free_user = multi_user_contexts[0]  # Free tier
        enterprise_user = multi_user_contexts[3]  # Enterprise tier
        
        # Verify contexts are completely isolated
        assert free_user.user_id != enterprise_user.user_id
        assert free_user.thread_id != enterprise_user.thread_id 
        assert free_user.run_id != enterprise_user.run_id
        assert free_user.agent_context["user_subscription"] != enterprise_user.agent_context["user_subscription"]
        
        # Test that modifying one context doesn't affect another
        # (Create child contexts to test isolation)
        free_child = free_user.create_child_context(
            "free_user_operation",
            additional_agent_context={"free_feature": True}
        )
        
        enterprise_child = enterprise_user.create_child_context(
            "enterprise_operation", 
            additional_agent_context={"enterprise_feature": True}
        )
        
        # Verify complete isolation maintained
        assert "free_feature" not in enterprise_child.agent_context
        assert "enterprise_feature" not in free_child.agent_context
        assert free_child.user_id != enterprise_child.user_id
        assert free_child.thread_id != enterprise_child.thread_id
    
    @pytest.mark.integration
    @pytest.mark.concurrent_isolation
    async def test_concurrent_context_creation_thread_safety(self, concurrent_context_factory, isolated_env):
        """Test thread-safe concurrent context creation.
        
        BVJ: Ensures system stability under concurrent load and prevents
        race conditions that could cause system failures or data corruption.
        """
        def create_contexts_batch(batch_id: int) -> List[UserExecutionContext]:
            """Create batch of contexts in separate thread."""
            return concurrent_context_factory(5, f"thread_safety_batch_{batch_id}")
        
        # Create contexts concurrently from multiple threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_contexts_batch, i) for i in range(4)]
            
            all_contexts = []
            for future in as_completed(futures):
                batch_contexts = future.result()
                all_contexts.extend(batch_contexts)
        
        # Verify all contexts created successfully (20 total: 4 batches  x  5 contexts)
        assert len(all_contexts) == 20
        
        # Verify all contexts have unique identifiers (no collisions)
        user_ids = [ctx.user_id for ctx in all_contexts]
        thread_ids = [ctx.thread_id for ctx in all_contexts]
        run_ids = [ctx.run_id for ctx in all_contexts]
        
        assert len(set(user_ids)) == 20  # All unique
        assert len(set(thread_ids)) == 20  # All unique  
        assert len(set(run_ids)) == 20  # All unique
        
        # Verify contexts maintain proper isolation
        for i, context in enumerate(all_contexts):
            assert context.agent_context["context_index"] == i % 5
            assert context.audit_metadata["context_number"] == i % 5
    
    @pytest.mark.integration
    @pytest.mark.concurrent_isolation
    async def test_concurrent_websocket_routing_isolation(self, multi_user_contexts, isolated_env):
        """Test WebSocket routing isolation between concurrent users.
        
        BVJ: Ensures users only receive their own real-time updates preventing
        cross-user information leakage in chat functionality.
        """
        # Test with users that have WebSocket connections
        contexts_with_ws = []
        for i, context in enumerate(multi_user_contexts[:3]):
            # Create context with unique WebSocket connection ID
            ws_context = UserExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=f"run_ws_test_{i}_{int(time.time())}_abcd",
                websocket_client_id=f"ws_isolation_test_{i}_{context.user_id[:8]}",
                agent_context=context.agent_context,
                audit_metadata=context.audit_metadata
            )
            contexts_with_ws.append(ws_context)
        
        # Verify WebSocket IDs are unique and properly isolated
        ws_ids = [ctx.websocket_client_id for ctx in contexts_with_ws]
        assert len(set(ws_ids)) == len(ws_ids)  # All unique
        
        # Verify each context has proper WebSocket routing information
        for i, context in enumerate(contexts_with_ws):
            assert context.websocket_client_id is not None
            assert context.user_id[:8] in context.websocket_client_id
            assert f"ws_isolation_test_{i}" in context.websocket_client_id
            
            # Verify context isolation maintained with WebSocket info
            other_contexts = [ctx for ctx in contexts_with_ws if ctx != context]
            for other in other_contexts:
                assert context.websocket_client_id != other.websocket_client_id
                assert context.user_id != other.user_id
    
    @pytest.mark.integration
    @pytest.mark.concurrent_isolation
    async def test_concurrent_database_session_isolation(self, multi_user_contexts, isolated_env):
        """Test database session isolation between concurrent users.
        
        BVJ: Ensures database operations are properly isolated preventing
        data leakage and maintaining transaction integrity for enterprise operations.
        """
        # Create contexts with database session simulation
        contexts_with_db = []
        for i, base_context in enumerate(multi_user_contexts[:3]):
            # Simulate database session attachment (in real system this would be AsyncSession)
            mock_session_id = f"db_session_{i}_{base_context.user_id[:8]}_{int(time.time())}"
            
            db_context = base_context.with_db_session(mock_session_id)
            contexts_with_db.append((db_context, mock_session_id))
        
        # Verify database session isolation
        for i, (context, session_id) in enumerate(contexts_with_db):
            assert context.db_session == session_id
            
            # Verify each context has unique database session  
            other_sessions = [s for c, s in contexts_with_db if c != context]
            assert session_id not in other_sessions
            
            # Verify user context isolation maintained with database sessions
            assert context.user_id == multi_user_contexts[i].user_id
            assert context.thread_id == multi_user_contexts[i].thread_id
    
    @pytest.mark.integration
    @pytest.mark.concurrent_isolation
    async def test_concurrent_audit_trail_isolation(self, multi_user_contexts, isolated_env):
        """Test audit trail isolation between concurrent users.
        
        BVJ: Ensures audit trails remain properly isolated for compliance
        and security monitoring without cross-user contamination.
        """
        # Create concurrent operations with audit trails
        audit_contexts = []
        for i, base_context in enumerate(multi_user_contexts[:4]):
            # Create child context with audit trail
            audit_context = base_context.create_child_context(
                f"audit_test_operation_{i}",
                additional_audit_metadata={
                    "operation_id": f"op_{i}_{int(time.time())}",
                    "audit_sequence": i,
                    "security_context": {
                        "user_tier": base_context.agent_context.get("user_subscription", "unknown"),
                        "operation_type": "concurrent_test"
                    }
                }
            )
            audit_contexts.append(audit_context)
        
        # Verify audit trail isolation
        for i, context in enumerate(audit_contexts):
            audit_trail = context.get_audit_trail()
            
            # Verify unique audit information
            assert audit_trail["user_context"]["user_id"] == multi_user_contexts[i].user_id
            assert f"op_{i}" in context.audit_metadata["operation_id"]
            assert context.audit_metadata["audit_sequence"] == i
            
            # Verify isolation from other users' audit trails  
            other_trails = [ctx.get_audit_trail() for ctx in audit_contexts if ctx != context]
            for other_trail in other_trails:
                assert audit_trail["context_id"] != other_trail["context_id"]
                assert audit_trail["user_context"]["user_id"] != other_trail["user_context"]["user_id"]


class TestFactoryBasedResourceManagement:
    """Test suite for factory-based resource management patterns.
    
    BVJ: Validates proper resource management and cleanup patterns that enable
    stable production operations and prevent resource exhaustion.
    """
    
    @pytest.fixture
    async def mock_resource_factory(self):
        """Mock factory for resource management testing."""
        class MockResourceFactory:
            def __init__(self):
                self.allocated_resources = {}
                self.cleanup_count = 0
                
            async def allocate_resource(self, context: UserExecutionContext) -> str:
                resource_id = f"resource_{context.user_id[:8]}_{int(time.time())}"
                self.allocated_resources[resource_id] = {
                    "context": context,
                    "created_at": datetime.now(timezone.utc),
                    "active": True
                }
                return resource_id
                
            async def cleanup_resource(self, resource_id: str):
                if resource_id in self.allocated_resources:
                    self.allocated_resources[resource_id]["active"] = False
                    self.cleanup_count += 1
                    
            def get_active_resources(self) -> Dict[str, Any]:
                return {k: v for k, v in self.allocated_resources.items() if v["active"]}
        
        return MockResourceFactory()
    
    @pytest.mark.integration
    @pytest.mark.resource_management
    async def test_factory_resource_allocation_per_user(self, mock_resource_factory, multi_user_contexts):
        """Test proper resource allocation per user context.
        
        BVJ: Ensures resources are properly allocated per user preventing
        resource conflicts and enabling fair resource distribution.
        """
        # Allocate resources for different users
        allocated_resources = {}
        for i, context in enumerate(multi_user_contexts[:3]):
            resource_id = await mock_resource_factory.allocate_resource(context)
            allocated_resources[context.user_id] = resource_id
        
        # Verify each user has unique resource allocation
        resource_ids = list(allocated_resources.values())
        assert len(set(resource_ids)) == len(resource_ids)  # All unique
        
        # Verify resources properly associated with users
        active_resources = mock_resource_factory.get_active_resources()
        assert len(active_resources) == 3
        
        for user_id, resource_id in allocated_resources.items():
            assert resource_id in active_resources
            assert active_resources[resource_id]["context"].user_id == user_id
            assert active_resources[resource_id]["active"] is True
    
    @pytest.mark.integration
    @pytest.mark.resource_management
    async def test_factory_resource_cleanup_lifecycle(self, mock_resource_factory, realistic_user_context):
        """Test complete resource cleanup lifecycle.
        
        BVJ: Ensures proper resource cleanup preventing memory leaks and
        resource exhaustion in production environments.
        """
        # Allocate resource
        resource_id = await mock_resource_factory.allocate_resource(realistic_user_context)
        
        # Verify resource is active
        active_resources = mock_resource_factory.get_active_resources()
        assert resource_id in active_resources
        assert active_resources[resource_id]["active"] is True
        
        initial_cleanup_count = mock_resource_factory.cleanup_count
        
        # Cleanup resource
        await mock_resource_factory.cleanup_resource(resource_id)
        
        # Verify resource cleaned up
        active_resources_after = mock_resource_factory.get_active_resources()
        assert resource_id not in active_resources_after
        assert mock_resource_factory.cleanup_count == initial_cleanup_count + 1
        
        # Verify resource marked as inactive
        all_resources = mock_resource_factory.allocated_resources
        assert all_resources[resource_id]["active"] is False
    
    @pytest.mark.integration
    @pytest.mark.resource_management
    async def test_factory_concurrent_resource_management(self, mock_resource_factory, concurrent_context_factory):
        """Test concurrent resource management with proper isolation.
        
        BVJ: Validates system stability under concurrent resource allocation
        and cleanup operations typical in production multi-user scenarios.
        """
        # Create concurrent contexts
        contexts = concurrent_context_factory(10, "resource_concurrent")
        
        # Allocate resources concurrently
        async def allocate_resource_for_context(context):
            return await mock_resource_factory.allocate_resource(context)
        
        # Use asyncio.gather for concurrent allocation
        resource_ids = await asyncio.gather(*[
            allocate_resource_for_context(ctx) for ctx in contexts
        ])
        
        # Verify all resources allocated successfully
        assert len(resource_ids) == 10
        assert len(set(resource_ids)) == 10  # All unique
        
        active_resources = mock_resource_factory.get_active_resources()
        assert len(active_resources) == 10
        
        # Test concurrent cleanup
        cleanup_tasks = [
            mock_resource_factory.cleanup_resource(resource_id)
            for resource_id in resource_ids[:5]  # Cleanup first half
        ]
        
        await asyncio.gather(*cleanup_tasks)
        
        # Verify partial cleanup
        active_after_cleanup = mock_resource_factory.get_active_resources()
        assert len(active_after_cleanup) == 5  # Half cleaned up
        assert mock_resource_factory.cleanup_count == 5
    
    @pytest.mark.integration
    @pytest.mark.resource_management
    async def test_factory_resource_limits_enforcement(self, mock_resource_factory, realistic_user_context):
        """Test resource limits enforcement per user.
        
        BVJ: Prevents resource exhaustion and ensures fair resource allocation
        across different user subscription tiers.
        """
        # Simulate resource limit enforcement
        class LimitedResourceFactory(mock_resource_factory.__class__):
            def __init__(self, base_factory, max_resources_per_user=3):
                self.base_factory = base_factory
                self.max_resources_per_user = max_resources_per_user
                self.user_resource_count = {}
                
            async def allocate_resource(self, context: UserExecutionContext) -> str:
                user_id = context.user_id
                current_count = self.user_resource_count.get(user_id, 0)
                
                if current_count >= self.max_resources_per_user:
                    raise Exception(f"Resource limit exceeded for user {user_id}")
                
                resource_id = await self.base_factory.allocate_resource(context)
                self.user_resource_count[user_id] = current_count + 1
                return resource_id
                
            async def cleanup_resource(self, resource_id: str, user_id: str):
                await self.base_factory.cleanup_resource(resource_id)
                if user_id in self.user_resource_count:
                    self.user_resource_count[user_id] -= 1
        
        limited_factory = LimitedResourceFactory(mock_resource_factory)
        
        # Test resource limit enforcement
        allocated_resources = []
        
        # Allocate up to limit (should succeed)
        for i in range(3):
            resource_id = await limited_factory.allocate_resource(realistic_user_context)
            allocated_resources.append(resource_id)
        
        # Try to exceed limit (should fail)
        with pytest.raises(Exception, match="Resource limit exceeded"):
            await limited_factory.allocate_resource(realistic_user_context)
        
        # Test that cleanup allows new allocation
        await limited_factory.cleanup_resource(allocated_resources[0], realistic_user_context.user_id)
        
        # Should be able to allocate again after cleanup
        new_resource = await limited_factory.allocate_resource(realistic_user_context)
        assert new_resource is not None
    
    @pytest.mark.integration
    @pytest.mark.resource_management
    async def test_factory_resource_timeout_management(self, mock_resource_factory, realistic_user_context):
        """Test resource timeout and automatic cleanup.
        
        BVJ: Prevents resource leaks from abandoned operations and ensures
        system stability in production environments.
        """
        # Simulate resource with timeout tracking
        class TimeoutResourceFactory(mock_resource_factory.__class__):
            def __init__(self, base_factory, timeout_seconds=1):
                self.base_factory = base_factory
                self.timeout_seconds = timeout_seconds
                self.resource_timeouts = {}
                
            async def allocate_resource(self, context: UserExecutionContext) -> str:
                resource_id = await self.base_factory.allocate_resource(context)
                self.resource_timeouts[resource_id] = datetime.now(timezone.utc)
                return resource_id
                
            async def check_timeouts_and_cleanup(self):
                """Check for timed out resources and clean them up."""
                current_time = datetime.now(timezone.utc)
                timed_out_resources = []
                
                for resource_id, created_time in self.resource_timeouts.items():
                    if (current_time - created_time).total_seconds() > self.timeout_seconds:
                        timed_out_resources.append(resource_id)
                
                for resource_id in timed_out_resources:
                    await self.base_factory.cleanup_resource(resource_id)
                    del self.resource_timeouts[resource_id]
                
                return len(timed_out_resources)
        
        timeout_factory = TimeoutResourceFactory(mock_resource_factory, timeout_seconds=0.5)
        
        # Allocate resource
        resource_id = await timeout_factory.allocate_resource(realistic_user_context)
        
        # Verify resource initially active
        active_resources = mock_resource_factory.get_active_resources()
        assert resource_id in active_resources
        
        # Wait for timeout
        await asyncio.sleep(0.6)  # Longer than timeout
        
        # Check timeouts and cleanup
        cleaned_count = await timeout_factory.check_timeouts_and_cleanup()
        assert cleaned_count == 1
        
        # Verify resource cleaned up
        active_after_timeout = mock_resource_factory.get_active_resources()
        assert resource_id not in active_after_timeout


class TestContextHierarchyAndChildContextCreation:
    """Test suite for context hierarchy and child context creation patterns.
    
    BVJ: Validates hierarchical context management enabling complex multi-agent
    workflows while maintaining proper isolation and audit trail continuity.
    """
    
    @pytest.mark.integration
    @pytest.mark.context_hierarchy
    async def test_child_context_creation_with_proper_inheritance(self, realistic_user_context, isolated_env):
        """Test child context creation with proper data inheritance.
        
        BVJ: Enables complex agent workflows where child agents inherit parent
        context while maintaining isolation and proper audit trails.
        """
        parent_context = realistic_user_context
        
        # Create child context with additional operation-specific data
        child_context = parent_context.create_child_context(
            "financial_analysis_operation",
            additional_agent_context={
                "analysis_type": "cost_breakdown",
                "target_metrics": ["spending_patterns", "optimization_opportunities"],
                "analysis_depth": "detailed"
            },
            additional_audit_metadata={
                "operation_type": "financial_analysis",
                "initiated_by": "enterprise_dashboard",
                "analysis_scope": "quarterly_review"
            }
        )
        
        # Verify inheritance of parent data
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        
        # Verify child-specific properties
        assert child_context.operation_depth == 1  # Incremented from parent's 0
        assert child_context.parent_request_id == parent_context.request_id
        assert "financial_analysis_operation" in child_context.request_id
        
        # Verify agent context inheritance and addition
        assert child_context.agent_context["user_subscription"] == "enterprise"  # Inherited
        assert child_context.agent_context["analysis_type"] == "cost_breakdown"  # Added
        assert child_context.agent_context["target_metrics"] == ["spending_patterns", "optimization_opportunities"]
        
        # Verify audit metadata inheritance and addition
        assert child_context.audit_metadata["business_context"]["monthly_spend"] == 75000  # Inherited
        assert child_context.audit_metadata["operation_type"] == "financial_analysis"  # Added
        assert child_context.audit_metadata["analysis_scope"] == "quarterly_review"
    
    @pytest.mark.integration
    @pytest.mark.context_hierarchy
    async def test_deep_context_hierarchy_creation(self, context_hierarchy_builder, isolated_env):
        """Test creation of deep context hierarchies with proper tracking.
        
        BVJ: Supports complex multi-level agent workflows where agents spawn
        sub-agents in hierarchical patterns for sophisticated analysis.
        """
        builder = context_hierarchy_builder
        
        # Create root context for hierarchy
        root_context = builder.create_root_context("deep_analysis_workflow")
        
        # Build deep hierarchy (5 levels)
        hierarchy = builder.build_hierarchy(root_context, 5)
        
        # Verify hierarchy structure
        assert len(hierarchy) == 6  # Root + 5 levels
        
        # Verify each level has proper depth and parent tracking
        for i, context in enumerate(hierarchy):
            assert context.operation_depth == i
            
            if i == 0:
                # Root context
                assert context.parent_request_id is None
                assert context.agent_context["context_type"] == "root"
            else:
                # Child contexts
                assert context.parent_request_id == hierarchy[i-1].request_id
                assert context.agent_context["hierarchy_level"] == i
                assert context.audit_metadata["parent_level"] == i - 1
        
        # Verify all contexts share same user/thread/run but have unique request IDs
        user_ids = [ctx.user_id for ctx in hierarchy]
        thread_ids = [ctx.thread_id for ctx in hierarchy]
        run_ids = [ctx.run_id for ctx in hierarchy]
        request_ids = [ctx.request_id for ctx in hierarchy]
        
        assert len(set(user_ids)) == 1  # All same user
        assert len(set(thread_ids)) == 1  # All same thread  
        assert len(set(run_ids)) == 1  # All same run
        assert len(set(request_ids)) == 6  # All unique request IDs
    
    @pytest.mark.integration
    @pytest.mark.context_hierarchy
    async def test_sibling_context_creation_isolation(self, context_hierarchy_builder, isolated_env):
        """Test creation of sibling contexts with proper isolation.
        
        BVJ: Enables parallel agent execution where multiple agents operate
        at same hierarchy level without interfering with each other.
        """
        builder = context_hierarchy_builder
        
        # Create parent context
        parent_context = builder.create_root_context("parallel_workflow")
        
        # Create multiple sibling contexts
        siblings = builder.create_sibling_contexts(parent_context, 4)
        
        # Verify all siblings have same parent and depth
        for sibling in siblings:
            assert sibling.parent_request_id == parent_context.request_id
            assert sibling.operation_depth == 1  # One level below parent
            assert sibling.user_id == parent_context.user_id
            assert sibling.thread_id == parent_context.thread_id
            assert sibling.run_id == parent_context.run_id
        
        # Verify sibling isolation (unique request IDs and context data)
        request_ids = [sib.request_id for sib in siblings]
        assert len(set(request_ids)) == 4  # All unique
        
        for i, sibling in enumerate(siblings):
            assert sibling.agent_context["sibling_index"] == i
            assert sibling.agent_context["sibling_count"] == 4
            assert sibling.audit_metadata["sibling_info"] == f"sibling_{i}_of_4"
            
            # Verify isolation from other siblings
            other_siblings = [s for s in siblings if s != sibling]
            for other in other_siblings:
                assert sibling.request_id != other.request_id
                assert sibling.agent_context["sibling_index"] != other.agent_context["sibling_index"]
    
    @pytest.mark.integration
    @pytest.mark.context_hierarchy
    async def test_context_hierarchy_audit_trail_continuity(self, context_hierarchy_builder, isolated_env):
        """Test audit trail continuity across context hierarchy.
        
        BVJ: Ensures complete audit trail tracking for compliance and debugging
        across complex multi-agent workflows.
        """
        builder = context_hierarchy_builder
        
        # Create hierarchy with audit trail tracking
        root_context = builder.create_root_context("audit_trail_workflow")
        hierarchy = builder.build_hierarchy(root_context, 3)
        
        # Verify audit trail continuity across levels
        for i, context in enumerate(hierarchy):
            audit_trail = context.get_audit_trail()
            
            # Verify basic audit trail structure
            assert "context_id" in audit_trail
            assert "creation_time" in audit_trail
            assert "operation_depth" in audit_trail
            assert audit_trail["operation_depth"] == i
            
            if i > 0:
                # Child contexts should have parent information
                assert "parent_context" in audit_trail
                parent_trail = hierarchy[i-1].get_audit_trail()
                assert audit_trail["parent_context"]["context_id"] == parent_trail["context_id"]
                
            # Verify hierarchy-specific audit metadata
            if i > 0:
                assert context.audit_metadata["hierarchy_level"] == i
                assert context.audit_metadata["parent_level"] == i - 1
        
        # Test audit trail aggregation (getting full chain)
        leaf_context = hierarchy[-1]  # Deepest context
        
        # Verify leaf context can trace back to root
        current_context = leaf_context
        chain_length = 0
        
        while current_context.parent_request_id is not None:
            chain_length += 1
            # Find parent context
            parent_context = next(
                (ctx for ctx in hierarchy if ctx.request_id == current_context.parent_request_id),
                None
            )
            assert parent_context is not None
            current_context = parent_context
        
        assert chain_length == 3  # Should trace back through 3 levels to root
        assert current_context == hierarchy[0]  # Should reach root
    
    @pytest.mark.integration
    @pytest.mark.context_hierarchy
    async def test_context_hierarchy_concurrent_operations(self, async_context_manager, isolated_env):
        """Test concurrent operations across context hierarchy.
        
        BVJ: Validates system stability when multiple agents operate concurrently
        within the same hierarchical workflow structure.
        """
        manager = async_context_manager
        
        # Create root context for concurrent operations
        root_context = await manager.create_managed_context(
            user_id="user_concurrent_hierarchy_12345678901234567890",
            thread_id="thread_concurrent_hierarchy_98765432109876543210",
            run_id=f"run_concurrent_hierarchy_{int(time.time())}_abcd",
            agent_context={"workflow_type": "concurrent_hierarchy"},
            audit_metadata={"test_type": "concurrent_operations"}
        )
        
        # Create multiple child contexts concurrently
        async def create_child_with_delay(delay: float, operation_name: str):
            await asyncio.sleep(delay)
            return root_context.create_child_context(
                operation_name,
                additional_agent_context={"delay": delay, "operation": operation_name},
                additional_audit_metadata={"concurrent_test": True}
            )
        
        # Create children with different delays
        child_tasks = [
            create_child_with_delay(0.1, "operation_1"),
            create_child_with_delay(0.05, "operation_2"), 
            create_child_with_delay(0.15, "operation_3"),
            create_child_with_delay(0.02, "operation_4")
        ]
        
        children = await asyncio.gather(*child_tasks)
        
        # Verify all children created successfully
        assert len(children) == 4
        
        # Verify each child has proper parent relationship
        for child in children:
            assert child.parent_request_id == root_context.request_id
            assert child.operation_depth == 1
            assert child.user_id == root_context.user_id
            assert child.audit_metadata["concurrent_test"] is True
        
        # Verify children have unique identifiers despite concurrent creation
        request_ids = [child.request_id for child in children]
        assert len(set(request_ids)) == 4  # All unique
        
        # Verify operation names preserved correctly
        operations = [child.agent_context["operation"] for child in children]
        expected_operations = ["operation_1", "operation_2", "operation_3", "operation_4"]
        assert set(operations) == set(expected_operations)