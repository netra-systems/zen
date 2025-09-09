"""
Unit Tests for ExecutionEngineFactory SSOT Validation Failures

These tests are DESIGNED TO FAIL initially to prove SSOT validation issues
exist in the ExecutionEngineFactory implementation. The tests demonstrate
specific SSOT violations that prevent proper factory initialization.

Test Categories:
1. WebSocket Bridge SSOT Validation - Missing or invalid WebSocket dependencies
2. Factory Dependency Injection - SSOT violations in dependency management
3. User Context Engine Creation - SSOT validation failures during engine creation  
4. Resource Limits SSOT - Inconsistent resource management patterns
5. Cleanup Lifecycle SSOT - Factory cleanup and lifecycle management violations

Expected Outcomes:
- All tests should FAIL initially with specific SSOT error messages
- Failures demonstrate the factory initialization problems affecting golden path
- Error messages provide concrete evidence of SSOT validation violations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError,
    get_execution_engine_factory,
    configure_execution_engine_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineFactorySSotValidation:
    """Test SSOT validation failures in ExecutionEngineFactory."""
    
    def test_factory_requires_websocket_bridge_ssot_validation(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce WebSocket bridge SSOT requirement.
        
        SSOT Issue: Factory allows None websocket_bridge, violating SSOT dependency pattern.
        Expected Failure: Factory should reject initialization without WebSocket bridge.
        """
        # This should FAIL with SSOT validation error
        with pytest.raises(ExecutionEngineFactoryError, match="websocket_bridge"):
            ExecutionEngineFactory(
                websocket_bridge=None,  # SSOT violation: None dependency
                database_session_manager=Mock(),
                redis_manager=Mock()
            )
    
    def test_factory_websocket_bridge_type_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate WebSocket bridge type SSOT.
        
        SSOT Issue: Factory accepts invalid WebSocket bridge types without validation.
        Expected Failure: Factory should validate bridge interface compliance.
        """
        # This should FAIL - invalid bridge type should be rejected
        invalid_bridge = "not_a_websocket_bridge"  # SSOT violation: wrong type
        
        with pytest.raises(ExecutionEngineFactoryError, match="AgentWebSocketBridge"):
            ExecutionEngineFactory(
                websocket_bridge=invalid_bridge,  # SSOT violation: invalid type
                database_session_manager=Mock(),
                redis_manager=Mock()
            )
    
    @pytest.mark.asyncio
    async def test_user_engine_creation_ssot_context_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Engine creation should validate user context SSOT.
        
        SSOT Issue: Factory creates engines without validating UserExecutionContext.
        Expected Failure: Should reject invalid or incomplete user contexts.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # This should FAIL - invalid user context should be rejected
        invalid_context = UserExecutionContext(
            user_id="",  # SSOT violation: empty user_id
            thread_id="valid_thread",
            run_id="valid_run",
            request_id="valid_request"
        )
        
        with pytest.raises(ExecutionEngineFactoryError, match="Invalid user context"):
            await factory.create_for_user(invalid_context)
    
    @pytest.mark.asyncio 
    async def test_agent_factory_dependency_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate agent factory dependency SSOT.
        
        SSOT Issue: Factory proceeds without valid agent factory instance.
        Expected Failure: Should reject engine creation when agent factory unavailable.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            request_id="test_request"
        )
        
        # Mock agent factory to return None (SSOT violation)
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
                   return_value=None):
            
            # This should FAIL - missing agent factory dependency
            with pytest.raises(ExecutionEngineFactoryError, match="AgentInstanceFactory not available"):
                await factory.create_for_user(valid_context)
    
    @pytest.mark.asyncio
    async def test_user_engine_limits_ssot_enforcement_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce per-user engine limits SSOT.
        
        SSOT Issue: Factory allows unlimited engines per user, violating resource SSOT.
        Expected Failure: Should reject engine creation when user exceeds limits.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # Set low limit for testing
        factory._max_engines_per_user = 1
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run", 
            request_id="test_request"
        )
        
        # Mock agent factory
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
                   return_value=mock_agent_factory):
            with patch.object(factory, '_create_user_websocket_emitter',
                            return_value=mock_websocket_emitter):
                
                # Create first engine (should succeed)
                engine1 = await factory.create_for_user(valid_context)
                
                # Create second engine (should FAIL - exceeds limit)
                second_context = UserExecutionContext(
                    user_id="test_user",  # Same user
                    thread_id="test_thread2",
                    run_id="test_run2",
                    request_id="test_request2"
                )
                
                with pytest.raises(ExecutionEngineFactoryError, match="maximum engine limit"):
                    await factory.create_for_user(second_context)
    
    def test_factory_singleton_ssot_configuration_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory singleton should validate configuration SSOT.
        
        SSOT Issue: get_execution_engine_factory() returns factory without configuration.
        Expected Failure: Should reject unconfigured factory access.
        """
        # Clear any existing factory instance
        import netra_backend.app.agents.supervisor.execution_engine_factory as factory_module
        factory_module._factory_instance = None
        
        # This should FAIL - factory not configured
        with pytest.raises(ExecutionEngineFactoryError, match="not configured during startup"):
            asyncio.run(get_execution_engine_factory())
    
    @pytest.mark.asyncio
    async def test_factory_configuration_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory configuration should validate dependencies SSOT.
        
        SSOT Issue: configure_execution_engine_factory() accepts None bridge.
        Expected Failure: Should reject configuration with invalid dependencies.
        """
        # This should FAIL - None websocket bridge violates SSOT
        with pytest.raises(ExecutionEngineFactoryError, match="WebSocket bridge"):
            await configure_execution_engine_factory(
                websocket_bridge=None,  # SSOT violation: None dependency
                database_session_manager=Mock(),
                redis_manager=Mock()
            )
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_creation_ssot_bridge_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: WebSocket emitter creation should validate bridge SSOT.
        
        SSOT Issue: Factory creates emitters without validating bridge connection.
        Expected Failure: Should reject emitter creation with invalid bridge.
        """
        # Create factory with bridge that becomes invalid
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # Invalidate the bridge after factory creation (SSOT violation)
        factory._websocket_bridge = None
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # This should FAIL - invalid bridge state
        with pytest.raises(ExecutionEngineFactoryError, match="WebSocket emitter creation failed"):
            await factory._create_user_websocket_emitter(valid_context, Mock())
    
    @pytest.mark.asyncio
    async def test_factory_metrics_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory metrics should maintain SSOT consistency.
        
        SSOT Issue: Factory metrics don't match actual state during operations.
        Expected Failure: Metrics should accurately reflect factory state.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        initial_metrics = factory.get_factory_metrics()
        initial_created = initial_metrics['total_engines_created']
        initial_active = initial_metrics['active_engines_count']
        
        valid_context = UserExecutionContext(
            user_id="test_user", 
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Mock dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
                   return_value=mock_agent_factory):
            with patch.object(factory, '_create_user_websocket_emitter', 
                            return_value=mock_websocket_emitter):
                
                # Create engine
                engine = await factory.create_for_user(valid_context)
                
                updated_metrics = factory.get_factory_metrics()
                
                # This should FAIL if metrics SSOT is violated
                assert updated_metrics['total_engines_created'] == initial_created + 1, \
                    "SSOT violation: total_engines_created not incremented correctly"
                assert updated_metrics['active_engines_count'] == initial_active + 1, \
                    "SSOT violation: active_engines_count not incremented correctly"
    
    @pytest.mark.asyncio
    async def test_cleanup_lifecycle_ssot_isolation_failure(self):
        """
        TEST DESIGNED TO FAIL: Cleanup should maintain SSOT isolation between users.
        
        SSOT Issue: Engine cleanup affects other users' engines (SSOT violation).
        Expected Failure: Engine cleanup should be completely isolated per user.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # Create contexts for two users
        context1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1", 
            run_id="run1",
            request_id="request1"
        )
        
        context2 = UserExecutionContext(
            user_id="user2",
            thread_id="thread2",
            run_id="run2", 
            request_id="request2"
        )
        
        # Mock dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
                   return_value=mock_agent_factory):
            with patch.object(factory, '_create_user_websocket_emitter',
                            return_value=mock_websocket_emitter):
                
                # Create engines for both users
                engine1 = await factory.create_for_user(context1)
                engine2 = await factory.create_for_user(context2)
                
                initial_active = factory.get_factory_metrics()['active_engines_count']
                
                # Cleanup user1 engines only
                await factory.cleanup_user_context("user1")
                
                final_metrics = factory.get_factory_metrics()
                final_active = final_metrics['active_engines_count'] 
                
                # This should FAIL if SSOT isolation is violated
                assert final_active == initial_active - 1, \
                    "SSOT violation: Cleanup affected wrong number of engines"
                
                # Verify user2 engine still exists in active engines
                user2_engines = [eng for eng in factory._active_engines.values() 
                               if eng.get_user_context().user_id == "user2"]
                assert len(user2_engines) == 1, \
                    "SSOT violation: user2 engine affected by user1 cleanup"
    
    def test_factory_tool_dispatcher_integration_ssot_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate tool dispatcher integration SSOT.
        
        SSOT Issue: Factory accepts invalid tool dispatcher factory types.
        Expected Failure: Should validate tool dispatcher factory interface.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # This should FAIL - invalid tool dispatcher factory type
        invalid_tool_dispatcher = "not_a_tool_dispatcher_factory"
        
        with pytest.raises(TypeError, match="tool dispatcher factory"):
            factory.set_tool_dispatcher_factory(invalid_tool_dispatcher)
    
    @pytest.mark.asyncio
    async def test_factory_shutdown_ssot_cleanup_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory shutdown should enforce complete SSOT cleanup.
        
        SSOT Issue: Factory shutdown leaves active engines in inconsistent state.
        Expected Failure: Should cleanup all engines and reset metrics completely.
        """
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run", 
            request_id="test_request"
        )
        
        # Mock dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory',
                   return_value=mock_agent_factory):
            with patch.object(factory, '_create_user_websocket_emitter',
                            return_value=mock_websocket_emitter):
                
                # Create engine
                engine = await factory.create_for_user(valid_context)
                
                # Verify engine exists
                assert len(factory._active_engines) > 0
                
                # Shutdown factory
                await factory.shutdown()
                
                # This should FAIL if SSOT cleanup is incomplete
                final_metrics = factory.get_factory_metrics()
                
                assert final_metrics['active_engines_count'] == 0, \
                    "SSOT violation: Active engines count not reset to 0 after shutdown"
                assert len(factory._active_engines) == 0, \
                    "SSOT violation: Active engines dict not cleared after shutdown"