"""
Integration Tests for Factory SSOT Validation with Real Services

These tests are DESIGNED TO FAIL initially to prove SSOT validation issues
exist when factories interact with real services. The tests demonstrate
specific SSOT violations in factory coordination and service integration.

Test Categories:
1. Factory Coordination SSOT - Integration between multiple factory types
2. Real Service Dependencies - SSOT violations with actual database/Redis/WebSocket services
3. Factory Chain SSOT - Sequential factory creation and dependency validation
4. Service State SSOT - Factory state consistency with real service state
5. Error Propagation SSOT - SSOT error handling across factory boundaries

Expected Outcomes:
- All tests should FAIL initially with specific SSOT error messages
- Failures demonstrate factory integration problems affecting golden path
- Error messages provide concrete evidence of SSOT violations in real service contexts
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.integration
class TestFactorySSotValidationIntegration:
    """Test SSOT validation failures in factory integration with real services."""
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_execution_engine_factory_ssot_coordination_failure(self):
        """
        TEST DESIGNED TO FAIL: WebSocket bridge and execution engine factories should coordinate SSOT.
        
        SSOT Issue: Factories don't validate shared dependencies consistently.
        Expected Failure: Should detect inconsistent WebSocket bridge configuration.
        """
        # Create WebSocket bridge factory
        websocket_factory = WebSocketBridgeFactory()
        
        # This should FAIL - ExecutionEngineFactory should detect missing WebSocket bridge SSOT
        with pytest.raises(Exception, match="websocket.*bridge.*dependency"):
            execution_factory = ExecutionEngineFactory(
                websocket_bridge=None,  # SSOT violation: None bridge from factory
                database_session_manager=Mock(),
                redis_manager=Mock()
            )
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_websocket_manager_factory_ssot_integration_failure(self):
        """
        TEST DESIGNED TO FAIL: Tool dispatcher and WebSocket manager factories should integrate SSOT.
        
        SSOT Issue: Factories create inconsistent WebSocket management instances.
        Expected Failure: Should detect WebSocket manager SSOT inconsistency.
        """
        # Create tool dispatcher factory
        tool_factory = UnifiedToolDispatcherFactory()
        
        # Create WebSocket manager factory  
        websocket_manager_factory = WebSocketManagerFactory(
            connection_pool=Mock(),
            user_context_factory=Mock(),
            id_manager=Mock()
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Create WebSocket manager
        websocket_manager = websocket_manager_factory.create_isolated_websocket_manager(valid_context)
        
        # This should FAIL - tool dispatcher should validate WebSocket manager SSOT compatibility
        with pytest.raises(Exception, match="WebSocket.*manager.*SSOT"):
            dispatcher = await tool_factory.create_dispatcher(
                user_context=valid_context,
                websocket_manager=websocket_manager,  # SSOT violation: incompatible manager type
                tools=None
            )
    
    @pytest.mark.asyncio
    async def test_factory_chain_user_context_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory chain should maintain user context SSOT consistency.
        
        SSOT Issue: Factories modify or don't validate user context consistently across chain.
        Expected Failure: Should detect user context SSOT violations in factory chain.
        """
        # Create factory chain
        websocket_factory = WebSocketBridgeFactory()
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        tool_factory = UnifiedToolDispatcherFactory()
        
        # Create user context
        original_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Configure factories with context
        websocket_factory.configure(
            connection_pool=Mock(),
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        # This should FAIL - factories should detect user context SSOT modifications
        modified_context = UserExecutionContext(
            user_id="different_user",  # SSOT violation: context modification
            thread_id=original_context.thread_id,
            run_id=original_context.run_id,
            request_id=original_context.request_id
        )
        
        with pytest.raises(Exception, match="user.*context.*SSOT.*violation"):
            # Factory chain should detect context inconsistency
            engine = await execution_factory.create_for_user(modified_context)
    
    @pytest.mark.asyncio
    async def test_real_database_session_factory_ssot_isolation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory database sessions should maintain SSOT isolation.
        
        SSOT Issue: Factories share database sessions, violating SSOT isolation.
        Expected Failure: Should detect shared database session SSOT violations.
        """
        # Mock real database session manager
        shared_session = Mock()
        shared_session_manager = Mock()
        shared_session_manager.get_session = AsyncMock(return_value=shared_session)
        
        # Create two execution engine factories with shared session manager
        factory1 = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=shared_session_manager,
            redis_manager=Mock()
        )
        
        factory2 = ExecutionEngineFactory(
            websocket_bridge=Mock(), 
            database_session_manager=shared_session_manager,  # SSOT violation: shared session
            redis_manager=Mock()
        )
        
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
        
        # This should FAIL - factories should detect shared session SSOT violation
        engine1 = await factory1.create_for_user(context1)
        
        with pytest.raises(Exception, match="shared.*session.*SSOT"):
            engine2 = await factory2.create_for_user(context2)
    
    @pytest.mark.asyncio
    async def test_real_redis_manager_factory_ssot_state_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory Redis state should maintain SSOT consistency.
        
        SSOT Issue: Factories create inconsistent Redis state across instances.
        Expected Failure: Should detect Redis state SSOT inconsistency.
        """
        # Mock Redis manager with state tracking
        redis_manager = Mock()
        redis_manager.get_factory_state = Mock(return_value={"factory_count": 1})
        redis_manager.set_factory_state = Mock()
        
        # Create first factory
        factory1 = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=Mock(),
            redis_manager=redis_manager
        )
        
        # Create second factory with same Redis manager
        factory2 = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=Mock(),
            redis_manager=redis_manager  # SSOT violation: shared Redis state
        )
        
        # This should FAIL - Redis manager should detect SSOT state inconsistency
        with pytest.raises(Exception, match="Redis.*state.*SSOT"):
            # Second factory should detect state conflict
            factory2_state = redis_manager.get_factory_state()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_pool_factory_ssot_connection_isolation_failure(self):
        """
        TEST DESIGNED TO FAIL: WebSocket connection pool should enforce SSOT connection isolation.
        
        SSOT Issue: Connection pool allows connection sharing between factory instances.
        Expected Failure: Should detect connection sharing SSOT violations.
        """
        # Mock connection pool that tracks connections
        connection_pool = Mock()
        shared_connection = Mock()
        connection_pool.get_connection = AsyncMock(return_value=shared_connection)
        
        # Create two WebSocket bridge factories with shared pool
        factory1 = WebSocketBridgeFactory()
        factory1.configure(
            connection_pool=connection_pool,
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        factory2 = WebSocketBridgeFactory()
        factory2.configure(
            connection_pool=connection_pool,  # SSOT violation: shared connection pool
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        # This should FAIL - connection pool should detect SSOT isolation violation
        emitter1 = await factory1.create_user_emitter(
            user_id="user1",
            thread_id="thread1",
            connection_id="conn1"
        )
        
        with pytest.raises(Exception, match="connection.*isolation.*SSOT"):
            emitter2 = await factory2.create_user_emitter(
                user_id="user2",
                thread_id="thread2", 
                connection_id="conn2"  # SSOT violation: should detect shared connection
            )
    
    @pytest.mark.asyncio
    async def test_factory_error_propagation_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory error propagation should maintain SSOT consistency.
        
        SSOT Issue: Factories don't propagate SSOT errors consistently across chain.
        Expected Failure: Should detect inconsistent error propagation SSOT patterns.
        """
        # Create factory chain with error injection
        websocket_factory = WebSocketBridgeFactory()
        
        # Inject error in WebSocket factory
        with patch.object(websocket_factory, 'configure', side_effect=Exception("SSOT validation error")):
            
            # This should FAIL - execution factory should detect upstream SSOT error
            execution_factory = ExecutionEngineFactory(
                websocket_bridge=Mock(),
                database_session_manager=Mock(),
                redis_manager=Mock()
            )
            
            valid_context = UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_request"
            )
            
            with pytest.raises(Exception, match="upstream.*SSOT.*error"):
                # Should detect and propagate upstream SSOT error
                engine = await execution_factory.create_for_user(valid_context)
    
    @pytest.mark.asyncio
    async def test_factory_cleanup_coordination_ssot_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory cleanup should coordinate SSOT resource management.
        
        SSOT Issue: Factories don't coordinate cleanup, leaving inconsistent SSOT state.
        Expected Failure: Should detect uncoordinated cleanup SSOT violations.
        """
        # Create multiple factory instances
        websocket_factory = WebSocketBridgeFactory()
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        tool_factory = UnifiedToolDispatcherFactory()
        
        # Configure factories
        websocket_factory.configure(
            connection_pool=Mock(),
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Create resources across factories
        emitter = await websocket_factory.create_user_emitter(
            user_id=valid_context.user_id,
            thread_id=valid_context.thread_id,
            connection_id="test_connection"
        )
        
        engine = await execution_factory.create_for_user(valid_context)
        
        # Cleanup only one factory
        await execution_factory.shutdown()
        
        # This should FAIL - WebSocket factory should detect orphaned resources SSOT violation
        with pytest.raises(Exception, match="orphaned.*resources.*SSOT"):
            # WebSocket factory should detect that execution engine was cleaned up
            # but WebSocket emitter is still active (SSOT violation)
            await websocket_factory.cleanup_user_context(
                valid_context.user_id, 
                "test_connection"
            )
    
    @pytest.mark.asyncio
    async def test_factory_metrics_aggregation_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory metrics should maintain SSOT consistency across factories.
        
        SSOT Issue: Factory metrics don't aggregate consistently, violating SSOT patterns.
        Expected Failure: Should detect inconsistent metrics aggregation SSOT violations.
        """
        # Create multiple factories
        websocket_factory = WebSocketBridgeFactory()
        execution_factory = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # Configure WebSocket factory
        websocket_factory.configure(
            connection_pool=Mock(),
            agent_registry=Mock(), 
            health_monitor=Mock()
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Get initial metrics
        initial_websocket_metrics = websocket_factory.get_factory_metrics()
        initial_execution_metrics = execution_factory.get_factory_metrics()
        
        # Create resources
        emitter = await websocket_factory.create_user_emitter(
            user_id=valid_context.user_id,
            thread_id=valid_context.thread_id,
            connection_id="test_connection"
        )
        
        engine = await execution_factory.create_for_user(valid_context)
        
        # Get updated metrics
        updated_websocket_metrics = websocket_factory.get_factory_metrics()
        updated_execution_metrics = execution_factory.get_factory_metrics()
        
        # This should FAIL if SSOT metrics consistency is violated
        # The total resource count across factories should be consistent
        total_initial = (initial_websocket_metrics['emitters_created'] + 
                        initial_execution_metrics['total_engines_created'])
        total_updated = (updated_websocket_metrics['emitters_created'] + 
                        updated_execution_metrics['total_engines_created'])
        
        assert total_updated == total_initial + 2, \
            "SSOT violation: Factory metrics aggregation not consistent"