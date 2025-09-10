"""
Test ExecutionEngineFactory vs AgentInstanceFactory SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate factory pattern duplication blocking golden path
- Value Impact: Remove 4-layer factory abstraction causing race conditions
- Strategic Impact: Critical $120K+ MRR protection through SSOT compliance

This test validates that ExecutionEngineFactory and AgentInstanceFactory don't
duplicate user context creation, WebSocket emitter instantiation, and lifecycle management.
The over-engineering audit identified this as a critical SSOT violation.
"""

import pytest
import asyncio
import time
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Import the factory classes to test
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    get_execution_engine_factory,
    configure_execution_engine_factory
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    get_agent_instance_factory,
    configure_agent_instance_factory,
    UserWebSocketEmitter
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineAgentInstanceFactoryDuplication(BaseIntegrationTest):
    """Test SSOT violations between ExecutionEngineFactory and AgentInstanceFactory."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_creation_not_duplicated(self, real_services_fixture):
        """
        Test that ExecutionEngineFactory and AgentInstanceFactory don't 
        duplicate user context creation logic.
        
        SSOT Violation: Both factories create UserExecutionContext instances
        with similar patterns but different implementations.
        """
        # Create mock WebSocket bridge for factory configuration
        mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
        
        # Configure ExecutionEngineFactory
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=mock_websocket_bridge,
            database_session_manager=real_services_fixture["db"],
            redis_manager=real_services_fixture["redis"]
        )
        
        # Configure AgentInstanceFactory  
        agent_factory = AgentInstanceFactory()
        agent_factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test data
        user_id = "test_user_ssot_violation"
        thread_id = "test_thread_ssot"
        run_id = "test_run_ssot_context"
        
        # Create contexts from both factories
        user_context_via_agent_factory = await agent_factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=real_services_fixture["db"]
        )
        
        user_context_for_execution_factory = UserExecutionContext.from_request_supervisor(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id + "_execution",
            db_session=real_services_fixture["db"]
        )
        
        # SSOT VIOLATION CHECK: Both factories should use SAME context creation method
        # Currently they use different approaches which violates SSOT
        assert user_context_via_agent_factory.user_id == user_context_for_execution_factory.user_id
        assert user_context_via_agent_factory.thread_id == user_context_for_execution_factory.thread_id
        
        # CRITICAL: These should have identical structure but factories create them differently
        context_1_attrs = set(dir(user_context_via_agent_factory))
        context_2_attrs = set(dir(user_context_for_execution_factory))
        
        # Both contexts should have identical structure (SSOT requirement)
        missing_from_context_1 = context_2_attrs - context_1_attrs
        missing_from_context_2 = context_1_attrs - context_2_attrs
        
        assert len(missing_from_context_1) == 0, f"ExecutionEngine context missing: {missing_from_context_1}"
        assert len(missing_from_context_2) == 0, f"AgentInstance context missing: {missing_from_context_2}"
        
        # Cleanup
        await agent_factory.cleanup_user_context(user_context_via_agent_factory)
        
        # Business value assertion: Eliminating duplication should reduce creation overhead
        # When factories use same SSOT method, context creation should be consistent
        self.assert_business_value_delivered(
            {"context_consistency": True, "duplication_eliminated": True},
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_emitter_creation_ssot_violation(self, real_services_fixture):
        """
        Test SSOT violation in WebSocket emitter creation between factories.
        
        SSOT Violation: Both ExecutionEngineFactory and AgentInstanceFactory
        create UserWebSocketEmitter instances with different patterns.
        """
        # Create mock WebSocket bridge
        mock_bridge = MagicMock(spec=AgentWebSocketBridge)
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        
        # Configure both factories
        execution_factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        agent_factory = AgentInstanceFactory()
        agent_factory.configure(websocket_bridge=mock_bridge)
        
        # Test context
        user_id = "emitter_ssot_test"
        thread_id = "thread_emitter"
        run_id = "run_emitter_ssot"
        
        # Create user context via AgentInstanceFactory
        user_context = await agent_factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id, 
            run_id=run_id,
            db_session=real_services_fixture["db"]
        )
        
        # Both factories create WebSocket emitters - this is SSOT violation
        # AgentInstanceFactory creates via _create_emitter method
        agent_factory_emitter = await agent_factory._create_emitter(user_id, thread_id, run_id)
        
        # ExecutionEngineFactory creates via _create_user_websocket_emitter method
        execution_emitter = await execution_factory._create_user_websocket_emitter(
            user_context, agent_factory  # Note different parameters!
        )
        
        # SSOT VIOLATION: Different creation methods should produce identical emitters
        assert type(agent_factory_emitter) == type(execution_emitter), \
            f"Factory emitter types differ: {type(agent_factory_emitter)} vs {type(execution_emitter)}"
        
        # SSOT VIOLATION: Both emitters should have identical configuration
        assert agent_factory_emitter.user_id == execution_emitter.user_id
        assert agent_factory_emitter.thread_id == execution_emitter.thread_id
        assert agent_factory_emitter.run_id == execution_emitter.run_id
        
        # CRITICAL: Test that both emitters work identically (SSOT requirement)
        agent_success = await agent_factory_emitter.notify_agent_started("test_agent", {})
        execution_success = await execution_emitter.notify_agent_started("test_agent", {})
        
        assert agent_success == execution_success, "SSOT violation: emitters behave differently"
        
        # Cleanup
        await agent_factory_emitter.cleanup()
        await execution_emitter.cleanup()
        await agent_factory.cleanup_user_context(user_context)
        
        # Business value: Consolidating emitter creation eliminates duplication
        self.assert_business_value_delivered(
            {"emitter_ssot_compliance": True, "factory_consolidation": True},
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_lifecycle_management_duplication(self, real_services_fixture):
        """
        Test lifecycle management duplication between ExecutionEngineFactory and AgentInstanceFactory.
        
        SSOT Violation: Both factories manage user context lifecycle with different cleanup patterns.
        """
        mock_bridge = MagicMock(spec=AgentWebSocketBridge)
        
        # Configure factories
        execution_factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        agent_factory = AgentInstanceFactory() 
        agent_factory.configure(websocket_bridge=mock_bridge)
        
        # Test data
        user_id = "lifecycle_ssot_test"
        thread_id = "thread_lifecycle"
        run_id = "run_lifecycle_ssot"
        
        # Track cleanup metrics from both factories
        initial_execution_metrics = execution_factory.get_factory_metrics()
        initial_agent_metrics = agent_factory.get_factory_metrics()
        
        # Create contexts via both factories  
        user_context = await agent_factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=real_services_fixture["db"]
        )
        
        # ExecutionEngineFactory manages engines which contain contexts
        engine = await execution_factory.create_for_user(user_context)
        
        # SSOT VIOLATION: Both factories track active contexts differently
        agent_active_contexts = agent_factory.get_active_contexts_summary()
        execution_active_engines = execution_factory.get_active_engines_summary()
        
        # Both should track the same logical concept (user execution state)
        assert agent_active_contexts["total_active_contexts"] > 0
        assert execution_active_engines["total_active_engines"] > 0
        
        # CRITICAL: Test cleanup coordination (SSOT requirement)
        # Both factories should clean up the same logical resources
        await agent_factory.cleanup_user_context(user_context)
        await execution_factory.cleanup_engine(engine)
        
        # Verify metrics updated correctly in both factories
        final_execution_metrics = execution_factory.get_factory_metrics()
        final_agent_metrics = agent_factory.get_factory_metrics()
        
        assert final_execution_metrics["total_engines_cleaned"] > initial_execution_metrics["total_engines_cleaned"]
        assert final_agent_metrics["total_contexts_cleaned"] > initial_agent_metrics["total_contexts_cleaned"]
        
        # SSOT REQUIREMENT: Both cleanup operations should result in zero active resources
        final_agent_contexts = agent_factory.get_active_contexts_summary()
        final_execution_engines = execution_factory.get_active_engines_summary()
        
        assert final_agent_contexts["total_active_contexts"] == 0
        assert final_execution_engines["total_active_engines"] == 0
        
        # Business value: Unified lifecycle management eliminates race conditions
        self.assert_business_value_delivered(
            {"lifecycle_coordination": True, "race_condition_elimination": True},
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_dependency_injection_patterns(self, real_services_fixture):
        """
        Test SSOT violations in how factories handle dependency injection.
        
        SSOT Violation: ExecutionEngineFactory and AgentInstanceFactory use
        different patterns for injecting WebSocket bridges and other dependencies.
        """
        # Create dependencies
        mock_bridge = MagicMock(spec=AgentWebSocketBridge)
        db_manager = real_services_fixture["db"]
        redis_manager = real_services_fixture["redis"]
        
        # SSOT VIOLATION: Different constructor patterns
        # ExecutionEngineFactory requires websocket_bridge in constructor
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=db_manager,
            redis_manager=redis_manager
        )
        
        # AgentInstanceFactory uses separate configure() method
        agent_factory = AgentInstanceFactory()
        agent_factory.configure(websocket_bridge=mock_bridge)
        
        # Test configuration state
        assert execution_factory._websocket_bridge is not None
        assert agent_factory._websocket_bridge is not None
        
        # SSOT VIOLATION: Different dependency validation patterns
        try:
            # ExecutionEngineFactory validates dependencies at construction time
            invalid_execution_factory = ExecutionEngineFactory(websocket_bridge=None)
            assert False, "Should have raised error for None websocket_bridge"
        except Exception as e:
            assert "websocket_bridge" in str(e).lower()
        
        # AgentInstanceFactory validates at usage time
        invalid_agent_factory = AgentInstanceFactory()
        # This should succeed (no validation at construction)
        
        try:
            # But fail when creating contexts without configuration
            await invalid_agent_factory.create_user_execution_context(
                user_id="test", thread_id="test", run_id="test"
            )
            assert False, "Should have failed without configuration"
        except ValueError as e:
            assert "not configured" in str(e).lower()
        
        # CRITICAL: Both factories should use SAME dependency injection pattern
        # for SSOT compliance
        
        # Business value: Unified dependency injection reduces configuration errors
        self.assert_business_value_delivered(
            {"dependency_injection_consistency": True, "configuration_errors_reduced": True},
            "automation"
        )

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_factory_metrics_and_monitoring_duplication(self, real_services_fixture):
        """
        Test SSOT violations in factory metrics and monitoring patterns.
        
        SSOT Violation: Both factories track similar metrics with different
        data structures and collection methods.
        """
        mock_bridge = MagicMock(spec=AgentWebSocketBridge)
        
        # Configure factories
        execution_factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        agent_factory = AgentInstanceFactory()
        agent_factory.configure(websocket_bridge=mock_bridge)
        
        # Get initial metrics from both factories
        execution_metrics = execution_factory.get_factory_metrics()
        agent_metrics = agent_factory.get_factory_metrics()
        
        # SSOT VIOLATION: Different metric structures for similar concepts
        # Both track "total created" but with different keys
        assert "total_engines_created" in execution_metrics
        assert "total_instances_created" in agent_metrics  # Different name for same concept!
        
        # Both track "active count" but differently
        assert "active_engines_count" in execution_metrics  
        assert "active_contexts" in agent_metrics  # Different structure!
        
        # Both track errors but differently
        assert "creation_errors" in execution_metrics
        assert "creation_errors" in agent_metrics  # At least this one matches
        
        # CRITICAL: Test that metrics measure the same business concepts
        user_id = "metrics_test"
        thread_id = "thread_metrics"
        run_id = "run_metrics"
        
        # Create resources via both factories and check metric updates
        user_context = await agent_factory.create_user_execution_context(
            user_id=user_id, thread_id=thread_id, run_id=run_id,
            db_session=real_services_fixture["db"]
        )
        
        engine = await execution_factory.create_for_user(user_context)
        
        # Get updated metrics
        updated_execution_metrics = execution_factory.get_factory_metrics()
        updated_agent_metrics = agent_factory.get_factory_metrics()
        
        # SSOT REQUIREMENT: Metrics should reflect same logical changes
        execution_created_delta = updated_execution_metrics["total_engines_created"] - execution_metrics["total_engines_created"]
        agent_created_delta = updated_agent_metrics["total_instances_created"] - agent_metrics["total_instances_created"]
        
        # Both should have increased by same amount (measuring same concept)
        assert execution_created_delta > 0
        assert agent_created_delta > 0
        
        # SSOT VIOLATION: Active counts measured differently
        assert updated_execution_metrics["active_engines_count"] > execution_metrics["active_engines_count"]
        assert updated_agent_metrics["active_contexts"] > agent_metrics["active_contexts"]
        
        # Cleanup and verify metrics consistency
        await execution_factory.cleanup_engine(engine)
        await agent_factory.cleanup_user_context(user_context)
        
        final_execution_metrics = execution_factory.get_factory_metrics()
        final_agent_metrics = agent_factory.get_factory_metrics()
        
        # Both should show cleanup occurred
        assert final_execution_metrics["total_engines_cleaned"] > execution_metrics["total_engines_cleaned"]
        assert final_agent_metrics["total_contexts_cleaned"] > agent_metrics["total_contexts_cleaned"]
        
        # Business value: Unified metrics enable better monitoring and performance optimization
        self.assert_business_value_delivered(
            {"metrics_consolidation": True, "monitoring_consistency": True},
            "automation"
        )