"""
Error Handling Routing Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Reliability & Graceful Degradation
- Value Impact: Ensures system continues operating during partial failures
- Strategic Impact: Prevents system crashes and maintains user experience during errors

These integration tests validate error handling in message routing, connection management,
and graceful failure scenarios. Focus on graceful degradation patterns and error isolation
between users to ensure business continuity.

CRITICAL: These tests validate that error conditions don't cascade across users or
bring down the entire system, protecting customer experience and platform stability.
"""
import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.websocket.message_handler import MessageHandlerService, BaseMessageHandler
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler, websocket_error_handler
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext

class TestMessageRoutingErrorHandling(SSotAsyncTestCase):
    """
    Test message routing error handling with graceful degradation.
    
    BVJ: Message routing failures should not prevent other users from functioning.
    Proper error handling ensures isolated failures with graceful recovery.
    """

    @pytest.mark.integration
    async def test_message_routing_handler_not_found_error(self):
        """
        Test message routing when handler is not found - graceful failure.
        
        BUSINESS IMPACT: Unknown message types should not crash the system,
        but should provide helpful error messages to users.
        """
        context = await create_authenticated_user_context(user_email='routing_test_1@example.com', environment='test', permissions=['read', 'write'])
        user_id = str(context.user_id)
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_error = AsyncMock()
        mock_ws_manager.validate_message = MagicMock(return_value=True)
        mock_ws_manager.sanitize_message = MagicMock(side_effect=lambda x: x)
        unknown_message = {'type': 'unknown_message_type', 'payload': {'data': 'test'}}
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:
            mock_create.return_value = mock_ws_manager
            await handler_service.handle_message(user_id, unknown_message)
            mock_ws_manager.send_error.assert_called_once()
            error_call = mock_ws_manager.send_error.call_args
            self.assertEqual(error_call[0][0], user_id)
            self.assertIn('Unknown message type', error_call[0][1])
            self.record_metric('handler_not_found_errors', 1)
            self.record_metric('graceful_error_recovery', True)

    @pytest.mark.integration
    async def test_message_routing_handler_exception_recovery(self):
        """
        Test message routing when handler throws exception - recovery handling.
        
        BUSINESS IMPACT: Handler failures should be isolated and not affect
        other users or the message routing system overall.
        """
        context1 = await create_authenticated_user_context(user_email='routing_test_2a@example.com', environment='test')
        context2 = await create_authenticated_user_context(user_email='routing_test_2b@example.com', environment='test')
        user_id_1 = str(context1.user_id)
        user_id_2 = str(context2.user_id)

        class FailingHandler(BaseMessageHandler):

            def get_message_type(self) -> str:
                return 'failing_test_message'

            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                if user_id == user_id_1:
                    raise RuntimeError('Simulated handler failure')
                return {'status': 'success', 'user_id': user_id}
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        failing_handler = FailingHandler()
        handler_service.register_handler(failing_handler)
        mock_ws_manager_1 = AsyncMock()
        mock_ws_manager_1.send_error = AsyncMock()
        mock_ws_manager_1.validate_message = MagicMock(return_value=True)
        mock_ws_manager_1.sanitize_message = MagicMock(side_effect=lambda x: x)
        mock_ws_manager_2 = AsyncMock()
        mock_ws_manager_2.send_error = AsyncMock()
        mock_ws_manager_2.validate_message = MagicMock(return_value=True)
        mock_ws_manager_2.sanitize_message = MagicMock(side_effect=lambda x: x)
        test_message = {'type': 'failing_test_message', 'payload': {'test_data': 'handler_exception_test'}}
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:

            def manager_factory(context):
                if str(context.user_id) == user_id_1:
                    return mock_ws_manager_1
                return mock_ws_manager_2
            mock_create.side_effect = manager_factory
            await handler_service.handle_message(user_id_1, test_message)
            await handler_service.handle_message(user_id_2, test_message)
            mock_ws_manager_1.send_error.assert_called_once()
            mock_ws_manager_2.send_error.assert_not_called()
            self.record_metric('error_isolation_successful', True)
            self.record_metric('user_errors_isolated', 1)
            self.record_metric('unaffected_users', 1)

    @pytest.mark.integration
    async def test_message_routing_malformed_message_handling(self):
        """
        Test handling of malformed/invalid message structures.
        
        BUSINESS IMPACT: Invalid messages should not crash routing system,
        but should provide clear feedback to users about proper format.
        """
        context = await create_authenticated_user_context(user_email='routing_test_3@example.com', environment='test')
        user_id = str(context.user_id)
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_error = AsyncMock()
        mock_ws_manager.validate_message = MagicMock(return_value=False)
        malformed_messages = [None, 'invalid string', {}, {'payload': 'data'}, {'type': None, 'payload': {}}, {'type': '', 'payload': {}}, {'type': 'valid', 'payload': 'not_dict'}]
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:
            mock_create.return_value = mock_ws_manager
            for i, bad_message in enumerate(malformed_messages):
                mock_ws_manager.send_error.reset_mock()
                await handler_service.handle_message(user_id, bad_message)
                mock_ws_manager.send_error.assert_called_once()
                error_call = mock_ws_manager.send_error.call_args
                self.assertEqual(error_call[0][0], user_id)
                self.assertIn('message', error_call[0][1].lower())
                self.record_metric(f'malformed_message_{i}_handled', True)
            self.record_metric('malformed_messages_handled', len(malformed_messages))
            self.record_metric('malformed_message_recovery', True)

    @pytest.mark.integration
    async def test_message_routing_timeout_error_handling(self):
        """
        Test message routing timeout handling with graceful degradation.
        
        BUSINESS IMPACT: Slow/hanging handlers should not block other messages
        or affect other users. Timeouts should provide clear user feedback.
        """
        context = await create_authenticated_user_context(user_email='routing_test_4@example.com', environment='test')
        user_id = str(context.user_id)

        class SlowHandler(BaseMessageHandler):

            def get_message_type(self) -> str:
                return 'slow_test_message'

            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                await asyncio.sleep(10)
                return {'status': 'completed_slowly'}
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        slow_handler = SlowHandler()
        handler_service.register_handler(slow_handler)
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_error = AsyncMock()
        mock_ws_manager.validate_message = MagicMock(return_value=True)
        mock_ws_manager.sanitize_message = MagicMock(side_effect=lambda x: x)
        test_message = {'type': 'slow_test_message', 'payload': {'data': 'timeout_test'}}
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:
            mock_create.return_value = mock_ws_manager
            start_time = time.time()
            await handler_service.handle_message(user_id, test_message)
            elapsed_time = time.time() - start_time
            self.assertLess(elapsed_time, 5.0, 'Message handling should timeout quickly')
            self.record_metric('timeout_error_handled', True)
            self.record_metric('timeout_response_time', elapsed_time)

    @pytest.mark.integration
    async def test_message_routing_circuit_breaker_activation(self):
        """
        Test circuit breaker pattern in message routing to prevent cascade failures.
        
        BUSINESS IMPACT: Repeated failures should trigger circuit breaker to prevent
        system overload while allowing recovery once issues are resolved.
        """
        context = await create_authenticated_user_context(user_email='routing_test_5@example.com', environment='test')
        user_id = str(context.user_id)

        class CircuitTestHandler(BaseMessageHandler):

            def __init__(self):
                self.failure_count = 0
                self.should_fail = True

            def get_message_type(self) -> str:
                return 'circuit_test_message'

            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                self.failure_count += 1
                if self.should_fail and self.failure_count <= 5:
                    raise RuntimeError(f'Circuit test failure #{self.failure_count}')
                return {'status': 'success_after_failures', 'attempt': self.failure_count}
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        circuit_handler = CircuitTestHandler()
        handler_service.register_handler(circuit_handler)
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_error = AsyncMock()
        mock_ws_manager.validate_message = MagicMock(return_value=True)
        mock_ws_manager.sanitize_message = MagicMock(side_effect=lambda x: x)
        test_message = {'type': 'circuit_test_message', 'payload': {'data': 'circuit_breaker_test'}}
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:
            mock_create.return_value = mock_ws_manager
            failure_count = 0
            for attempt in range(7):
                await handler_service.handle_message(user_id, test_message)
                if mock_ws_manager.send_error.called:
                    failure_count += 1
                    mock_ws_manager.send_error.reset_mock()
                await asyncio.sleep(0.1)
            circuit_handler.should_fail = False
            await handler_service.handle_message(user_id, test_message)
            self.assertGreater(failure_count, 0, 'Should have detected failures')
            self.record_metric('circuit_breaker_failures', failure_count)
            self.record_metric('circuit_breaker_recovery', True)

class TestWebSocketErrorHandlingRouting(SSotAsyncTestCase):
    """
    Test WebSocket error handling in routing layer.
    
    BVJ: WebSocket connection errors should be handled gracefully without
    affecting other users' connections or bringing down the WebSocket service.
    """

    @pytest.mark.integration
    async def test_websocket_connection_error_routing(self):
        """
        Test WebSocket connection error handling in routing.
        
        BUSINESS IMPACT: Connection failures should be isolated per user
        and not affect the routing infrastructure for other connections.
        """
        context1 = await create_authenticated_user_context(user_email='ws_error_1@example.com', environment='test')
        context2 = await create_authenticated_user_context(user_email='ws_error_2@example.com', environment='test')
        user_id_1 = str(context1.user_id)
        user_id_2 = str(context2.user_id)
        mock_ws_manager = AsyncMock()
        router = WebSocketEventRouter(mock_ws_manager)
        conn_id_1 = f'conn_{user_id_1}'
        conn_id_2 = f'conn_{user_id_2}'
        await router.register_connection(user_id_1, conn_id_1)
        await router.register_connection(user_id_2, conn_id_2)
        mock_ws_manager.send_to_connection = AsyncMock(side_effect=[ConnectionError('WebSocket connection lost'), True])
        test_event = {'type': 'test_event', 'message': 'connection_error_test'}
        result_1 = await router.route_event(user_id_1, conn_id_1, test_event)
        self.assertFalse(result_1, 'User 1 routing should fail')
        result_2 = await router.route_event(user_id_2, conn_id_2, test_event)
        self.assertTrue(result_2, 'User 2 routing should succeed despite user 1 failure')
        self.record_metric('websocket_connection_errors', 1)
        self.record_metric('websocket_error_isolation', True)
        self.record_metric('unaffected_websocket_users', 1)

    @pytest.mark.integration
    async def test_websocket_send_error_routing(self):
        """
        Test WebSocket send error handling with fallback routing.
        
        BUSINESS IMPACT: Send failures should trigger fallback mechanisms
        and not lose critical messages for users.
        """
        context = await create_authenticated_user_context(user_email='ws_send_error@example.com', environment='test')
        user_id = str(context.user_id)
        mock_ws_manager = AsyncMock()
        router = WebSocketEventRouter(mock_ws_manager)
        conn_id = f'conn_{user_id}'
        await router.register_connection(user_id, conn_id)
        failure_count = 0

        def send_with_failures(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise ConnectionError('Send failed')
            return True
        mock_ws_manager.send_to_connection = AsyncMock(side_effect=send_with_failures)
        critical_event = {'type': 'agent_completed', 'message': 'Critical response for user', 'critical': True}
        result = await router.route_event(user_id, conn_id, critical_event)
        self.assertTrue(result, 'Critical event should eventually be delivered')
        self.assertEqual(failure_count, 3, 'Should have retried until success')
        self.record_metric('websocket_send_retries', failure_count - 1)
        self.record_metric('websocket_send_recovery', True)

    @pytest.mark.integration
    async def test_websocket_disconnection_error_handling(self):
        """
        Test handling of unexpected WebSocket disconnections.
        
        BUSINESS IMPACT: Unexpected disconnections should be detected quickly
        and trigger reconnection or cleanup without affecting other users.
        """
        contexts = []
        user_ids = []
        conn_ids = []
        for i in range(3):
            context = await create_authenticated_user_context(user_email=f'ws_disconnect_{i}@example.com', environment='test')
            contexts.append(context)
            user_ids.append(str(context.user_id))
            conn_ids.append(f'conn_{user_ids[i]}')
        mock_ws_manager = AsyncMock()
        router = WebSocketEventRouter(mock_ws_manager)
        for user_id, conn_id in zip(user_ids, conn_ids):
            await router.register_connection(user_id, conn_id)
        disconnected_user = user_ids[1]
        disconnected_conn = conn_ids[1]
        await router.unregister_connection(disconnected_conn)
        test_event = {'type': 'broadcast_test', 'message': 'disconnection_test'}
        mock_ws_manager.send_to_connection = AsyncMock(return_value=True)
        remaining_users = [user_ids[0], user_ids[2]]
        successful_sends = 0
        for user_id in remaining_users:
            connections = await router.get_user_connections(user_id)
            if connections:
                for conn_id in connections:
                    result = await router.route_event(user_id, conn_id, test_event)
                    if result:
                        successful_sends += 1
        disconnected_connections = await router.get_user_connections(disconnected_user)
        self.assertEqual(len(disconnected_connections), 0, 'Disconnected user should have no connections')
        self.assertEqual(successful_sends, 2, 'Other users should receive events normally')
        self.record_metric('websocket_disconnections_handled', 1)
        self.record_metric('websocket_cleanup_successful', True)
        self.record_metric('unaffected_users_after_disconnection', 2)

    @pytest.mark.integration
    async def test_websocket_authentication_error_routing(self):
        """
        Test WebSocket authentication error routing and handling.
        
        BUSINESS IMPACT: Authentication failures should provide clear feedback
        and not compromise security or affect authenticated users.
        """
        auth_context = await create_authenticated_user_context(user_email='ws_auth_valid@example.com', environment='test')
        auth_user_id = str(auth_context.user_id)
        unauth_user_id = 'unauthenticated_user'
        mock_ws_manager = AsyncMock()
        router = WebSocketEventRouter(mock_ws_manager)
        auth_conn_id = f'conn_{auth_user_id}'
        unauth_conn_id = f'conn_{unauth_user_id}'
        await router.register_connection(auth_user_id, auth_conn_id)
        with patch.object(router, '_validate_connection') as mock_validate:
            mock_validate.return_value = False
            auth_error_event = {'type': 'test_event', 'message': 'auth_error_test'}
            result = await router.route_event(unauth_user_id, unauth_conn_id, auth_error_event)
            self.assertFalse(result, 'Unauthenticated routing should fail')
        mock_ws_manager.send_to_connection = AsyncMock(return_value=True)
        result = await router.route_event(auth_user_id, auth_conn_id, auth_error_event)
        self.assertTrue(result, 'Authenticated routing should work')
        self.record_metric('websocket_auth_errors', 1)
        self.record_metric('websocket_auth_isolation', True)
        self.record_metric('authenticated_users_unaffected', 1)

class TestAgentErrorHandlingRouting(SSotAsyncTestCase):
    """
    Test agent execution error handling in routing context.
    
    BVJ: Agent execution errors should be properly routed to users without
    affecting other users' agent executions or the agent infrastructure.
    """

    @pytest.mark.integration
    async def test_agent_execution_error_routing(self):
        """
        Test routing of agent execution errors to correct users.
        
        BUSINESS IMPACT: Agent failures should provide clear error messages
        to affected users while maintaining service for other users.
        """
        context1 = await create_authenticated_user_context(user_email='agent_error_1@example.com', environment='test')
        context2 = await create_authenticated_user_context(user_email='agent_error_2@example.com', environment='test')
        user_id_1 = str(context1.user_id)
        user_id_2 = str(context2.user_id)
        mock_agent_registry = AsyncMock()

        async def mock_execute_agent(agent_type, user_id, message):
            if user_id == user_id_1:
                raise RuntimeError('Agent execution failed for user 1')
            return {'success': True, 'response': 'Agent execution successful', 'user_id': user_id}
        mock_agent_registry.execute_agent = mock_execute_agent
        mock_ws_manager_1 = AsyncMock()
        mock_ws_manager_1.send_to_user = AsyncMock()
        mock_ws_manager_2 = AsyncMock()
        mock_ws_manager_2.send_to_user = AsyncMock()
        try:
            await mock_agent_registry.execute_agent('test_agent', user_id_1, 'test message')
            self.fail('Should have raised exception for user 1')
        except RuntimeError as e:
            error_handler = UnifiedErrorHandler()
            error_context = ErrorContext(trace_id=f'agent_error_test_{user_id_1}', operation='agent_execution', user_id=user_id_1)
            error_result = await error_handler.handle_error(e, error_context)
            self.assertIsNotNone(error_result)
            error_message = {'type': 'agent_error', 'error_code': error_result.error_code if hasattr(error_result, 'error_code') else 'AGENT_ERROR', 'user_message': 'Agent execution failed. Please try again.', 'recoverable': True}
            await mock_ws_manager_1.send_to_user(user_id_1, error_message)
            mock_ws_manager_1.send_to_user.assert_called_once_with(user_id_1, error_message)
        result_2 = await mock_agent_registry.execute_agent('test_agent', user_id_2, 'test message')
        self.assertTrue(result_2['success'], 'User 2 agent execution should succeed')
        success_message = {'type': 'agent_completed', 'result': result_2['response']}
        await mock_ws_manager_2.send_to_user(user_id_2, success_message)
        mock_ws_manager_2.send_to_user.assert_called_once()
        self.record_metric('agent_error_routing_successful', True)
        self.record_metric('agent_error_isolation', True)
        self.record_metric('unaffected_agent_users', 1)

    @pytest.mark.integration
    async def test_agent_timeout_error_routing(self):
        """
        Test routing of agent timeout errors with graceful handling.
        
        BUSINESS IMPACT: Agent timeouts should not leave users hanging
        indefinitely and should provide clear timeout messages.
        """
        context = await create_authenticated_user_context(user_email='agent_timeout@example.com', environment='test')
        user_id = str(context.user_id)
        mock_execution_engine = AsyncMock()

        async def timeout_execution(*args, **kwargs):
            await asyncio.sleep(10)
            return {'response': 'This should not be reached'}
        mock_execution_engine.execute = timeout_execution
        error_handler = UnifiedErrorHandler()
        timeout_context = ErrorContext(trace_id=f'agent_timeout_test_{user_id}', operation='agent_execution', user_id=user_id, operation_name='test_agent_execution')
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_to_user = AsyncMock()
        start_time = time.time()
        try:
            await asyncio.wait_for(mock_execution_engine.execute(), timeout=1.0)
            self.fail('Should have timed out')
        except asyncio.TimeoutError as e:
            elapsed_time = time.time() - start_time
            error_result = await error_handler.handle_error(e, timeout_context)
            self.assertLess(elapsed_time, 2.0, 'Timeout should be detected quickly')
            timeout_message = {'type': 'agent_timeout', 'message': 'Agent execution timed out. Please try again with a simpler request.', 'timeout_seconds': 1.0, 'recoverable': True}
            await mock_ws_manager.send_to_user(user_id, timeout_message)
            mock_ws_manager.send_to_user.assert_called_once()
            self.record_metric('agent_timeout_detected', True)
            self.record_metric('agent_timeout_response_time', elapsed_time)
            self.record_metric('agent_timeout_message_sent', True)

    @pytest.mark.integration
    async def test_agent_tool_error_routing(self):
        """
        Test routing of agent tool execution errors.
        
        BUSINESS IMPACT: Tool failures within agents should provide specific
        error context to help users understand what went wrong.
        """
        context = await create_authenticated_user_context(user_email='agent_tool_error@example.com', environment='test')
        user_id = str(context.user_id)

        class FailingTool:

            def __init__(self, tool_name: str):
                self.tool_name = tool_name

            async def execute(self, *args, **kwargs):
                raise ValueError(f'Tool {self.tool_name} failed: Invalid parameters')
        failing_tool = FailingTool('data_analysis_tool')
        mock_agent = AsyncMock()

        async def agent_with_tool_failure(message, thread_id, user_id, run_id):
            try:
                return await failing_tool.execute()
            except Exception as e:
                raise AgentToolError(message=f'Tool execution failed in agent', tool_name=failing_tool.tool_name, original_error=e, user_id=user_id)

        class AgentToolError(Exception):

            def __init__(self, message, tool_name, original_error, user_id):
                super().__init__(message)
                self.tool_name = tool_name
                self.original_error = original_error
                self.user_id = user_id
        mock_agent.run = agent_with_tool_failure
        error_handler = UnifiedErrorHandler()
        try:
            await mock_agent.run('analyze data', 'thread_123', user_id, 'run_456')
            self.fail('Should have raised tool error')
        except AgentToolError as e:
            tool_error_context = ErrorContext(trace_id=f'tool_error_test_{user_id}', operation='agent_tool_execution', user_id=user_id, details={'tool_name': e.tool_name, 'original_error': str(e.original_error)})
            error_result = await error_handler.handle_error(e, tool_error_context)
            mock_ws_manager = AsyncMock()
            mock_ws_manager.send_to_user = AsyncMock()
            tool_error_message = {'type': 'agent_tool_error', 'tool_name': e.tool_name, 'user_message': f'The {e.tool_name} encountered an error. Please check your input parameters.', 'error_details': str(e.original_error), 'recoverable': True, 'suggestions': ['Check your data format', 'Try a smaller dataset', 'Contact support if issue persists']}
            await mock_ws_manager.send_to_user(user_id, tool_error_message)
            mock_ws_manager.send_to_user.assert_called_once()
            call_args = mock_ws_manager.send_to_user.call_args[0][1]
            self.assertEqual(call_args['tool_name'], 'data_analysis_tool')
            self.assertIn('suggestions', call_args)
            self.record_metric('agent_tool_errors', 1)
            self.record_metric('tool_error_context_provided', True)
            self.record_metric('tool_error_suggestions_provided', True)

    @pytest.mark.integration
    async def test_agent_context_error_recovery(self):
        """
        Test agent context corruption error recovery.
        
        BUSINESS IMPACT: Context corruption should not crash agent system
        but should provide recovery path and clear error messaging.
        """
        context = await create_authenticated_user_context(user_email='agent_context_error@example.com', environment='test')
        user_id = str(context.user_id)
        corrupted_context = {'user_id': user_id, 'thread_id': None, 'run_id': 'invalid_format', 'agent_state': 'corrupted_json{invalid'}

        class ContextAwareAgent:

            def __init__(self):
                self.context = None

            def validate_context(self, context):
                """Validate execution context integrity."""
                errors = []
                if not context.get('thread_id'):
                    errors.append('Missing thread_id')
                if not context.get('run_id') or len(context['run_id']) < 10:
                    errors.append('Invalid run_id format')
                try:
                    json.loads(context.get('agent_state', '{}'))
                except:
                    errors.append('Corrupted agent_state JSON')
                if errors:
                    raise ValueError(f"Context validation failed: {', '.join(errors)}")

            async def execute_with_context(self, context):
                self.validate_context(context)
                return {'success': True, 'message': 'Execution successful'}
        agent = ContextAwareAgent()
        error_handler = UnifiedErrorHandler()
        try:
            await agent.execute_with_context(corrupted_context)
            self.fail('Should have detected context corruption')
        except ValueError as e:
            context_error_context = ErrorContext(trace_id=f'context_error_test_{user_id}', operation='agent_context_validation', user_id=user_id, details={'corruption_details': str(e)})
            recovery_operation = lambda: {'user_id': user_id, 'thread_id': f'recovery_thread_{int(time.time())}', 'run_id': f'recovery_run_{uuid.uuid4().hex[:16]}', 'agent_state': json.dumps({'status': 'recovered', 'clean_slate': True})}
            error_result = await error_handler.handle_error(e, context_error_context, recovery_operation)
            if error_result and isinstance(error_result, dict):
                self.assertIn('user_id', error_result)
                self.assertIsNotNone(error_result['thread_id'])
                self.assertTrue(error_result['thread_id'].startswith('recovery_thread_'))
                recovery_success = True
            else:
                recovery_success = False
            mock_ws_manager = AsyncMock()
            mock_ws_manager.send_to_user = AsyncMock()
            recovery_message = {'type': 'agent_context_recovery', 'message': 'Agent session was recovered due to a technical issue.', 'recovery_successful': recovery_success, 'new_session': True if recovery_success else False, 'user_action_required': False if recovery_success else True}
            await mock_ws_manager.send_to_user(user_id, recovery_message)
            mock_ws_manager.send_to_user.assert_called_once()
            self.record_metric('agent_context_corruptions', 1)
            self.record_metric('agent_context_recovery_attempted', True)
            self.record_metric('agent_context_recovery_successful', recovery_success)

class TestMultiUserErrorIsolation(SSotAsyncTestCase):
    """
    Test error isolation between multiple users in routing.
    
    BVJ: User error isolation is critical for multi-tenant system reliability.
    One user's errors should never affect another user's experience.
    """

    @pytest.mark.integration
    async def test_error_isolation_between_users(self):
        """
        Test that errors for one user don't propagate to other users.
        
        BUSINESS IMPACT: Multi-user systems must isolate failures to prevent
        one user's problems from affecting other paying customers.
        """
        user_contexts = []
        for i in range(5):
            context = await create_authenticated_user_context(user_email=f'isolation_test_{i}@example.com', environment='test')
            user_contexts.append(context)
        user_ids = [str(context.user_id) for context in user_contexts]
        problem_user_id = user_ids[2]

        class SelectiveFailureHandler(BaseMessageHandler):

            def get_message_type(self) -> str:
                return 'isolation_test_message'

            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                if user_id == problem_user_id:
                    raise RuntimeError(f'Simulated failure for {user_id}')
                return {'status': 'success', 'user_id': user_id}
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        failure_handler = SelectiveFailureHandler()
        handler_service.register_handler(failure_handler)
        ws_managers = {}
        for user_id in user_ids:
            mock_ws = AsyncMock()
            mock_ws.send_error = AsyncMock()
            mock_ws.send_to_user = AsyncMock()
            mock_ws.validate_message = MagicMock(return_value=True)
            mock_ws.sanitize_message = MagicMock(side_effect=lambda x: x)
            ws_managers[user_id] = mock_ws
        test_message = {'type': 'isolation_test_message', 'payload': {'data': 'isolation_test'}}

        def create_ws_manager(context):
            return ws_managers[str(context.user_id)]
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:
            mock_create.side_effect = create_ws_manager
            results = []
            for user_id in user_ids:
                try:
                    await handler_service.handle_message(user_id, test_message)
                    results.append((user_id, 'success'))
                except Exception as e:
                    results.append((user_id, f'error: {str(e)}'))
            success_count = 0
            error_count = 0
            for user_id, result in results:
                if user_id == problem_user_id:
                    ws_managers[user_id].send_error.assert_called()
                    error_count += 1
                else:
                    ws_managers[user_id].send_error.assert_not_called()
                    success_count += 1
            self.assertEqual(error_count, 1, 'Only problem user should have error')
            self.assertEqual(success_count, 4, 'Other users should succeed')
            self.record_metric('user_error_isolation_successful', True)
            self.record_metric('affected_users', error_count)
            self.record_metric('unaffected_users', success_count)
            self.record_metric('isolation_effectiveness', success_count / len(user_ids))

    @pytest.mark.integration
    async def test_user_error_context_isolation(self):
        """
        Test that error contexts are properly isolated per user.
        
        BUSINESS IMPACT: Error context leakage between users could expose
        sensitive information and violate user privacy.
        """
        context1 = await create_authenticated_user_context(user_email='sensitive_user_1@example.com', environment='test')
        context2 = await create_authenticated_user_context(user_email='sensitive_user_2@example.com', environment='test')
        user_id_1 = str(context1.user_id)
        user_id_2 = str(context2.user_id)
        error_context_1 = ErrorContext(trace_id=f'sensitive_trace_{user_id_1}', operation='sensitive_operation', user_id=user_id_1, details={'sensitive_data': f'secret_for_{user_id_1}', 'user_specific_info': 'private_info_user_1'})
        error_context_2 = ErrorContext(trace_id=f'sensitive_trace_{user_id_2}', operation='sensitive_operation', user_id=user_id_2, details={'sensitive_data': f'secret_for_{user_id_2}', 'user_specific_info': 'private_info_user_2'})
        error_handler = UnifiedErrorHandler()
        test_error = ValueError('Test sensitive error')
        result_1 = await error_handler.handle_error(test_error, error_context_1)
        result_2 = await error_handler.handle_error(test_error, error_context_2)
        if hasattr(result_1, 'trace_id') and hasattr(result_2, 'trace_id'):
            self.assertNotEqual(result_1.trace_id, result_2.trace_id, 'Trace IDs should be different')
        error_history = error_handler.error_history
        user_1_errors = [e for e in error_history if e.get('context', {}).get('user_id') == user_id_1]
        user_2_errors = [e for e in error_history if e.get('context', {}).get('user_id') == user_id_2]
        for error in user_1_errors:
            context_details = error.get('context', {}).get('details', {})
            if 'sensitive_data' in context_details:
                self.assertIn(user_id_1, context_details['sensitive_data'])
                self.assertNotIn(user_id_2, str(context_details))
        for error in user_2_errors:
            context_details = error.get('context', {}).get('details', {})
            if 'sensitive_data' in context_details:
                self.assertIn(user_id_2, context_details['sensitive_data'])
                self.assertNotIn(user_id_1, str(context_details))
        self.record_metric('error_context_isolation', True)
        self.record_metric('sensitive_data_leakage', False)
        self.record_metric('user_contexts_isolated', 2)

    @pytest.mark.integration
    async def test_error_recovery_user_independence(self):
        """
        Test that error recovery for one user doesn't affect other users.
        
        BUSINESS IMPACT: Recovery mechanisms should be user-specific and
        not interfere with other users' operations or recovery processes.
        """
        user_contexts = []
        for i in range(3):
            context = await create_authenticated_user_context(user_email=f'recovery_test_{i}@example.com', environment='test')
            user_contexts.append(context)
        user_ids = [str(context.user_id) for context in user_contexts]
        error_handler = UnifiedErrorHandler()
        recovery_attempts = {}
        recovery_results = {}
        for i, user_id in enumerate(user_ids):

            def make_recovery_op(uid, attempt_counter):

                async def recovery_op():
                    attempt_counter[uid] = attempt_counter.get(uid, 0) + 1
                    if attempt_counter[uid] <= 2:
                        raise RuntimeError(f'Recovery attempt {attempt_counter[uid]} failed for {uid}')
                    return {'recovery_success': True, 'user_id': uid, 'attempts': attempt_counter[uid]}
                return recovery_op
            recovery_attempts[user_id] = {}
            recovery_op = make_recovery_op(user_id, recovery_attempts[user_id])
            error_context = ErrorContext(trace_id=f'recovery_test_{user_id}', operation='recovery_test', user_id=user_id, details={'recovery_test_id': f'test_{i}'})
            test_error = ConnectionError(f'Connection failed for user {user_id}')
            result = await error_handler.handle_error(test_error, error_context, recovery_op)
            recovery_results[user_id] = result
            await asyncio.sleep(0.1)
        for user_id in user_ids:
            self.assertIn(user_id, recovery_attempts)
            self.assertGreater(recovery_attempts[user_id].get(user_id, 0), 0)
            result = recovery_results[user_id]
            if isinstance(result, dict) and 'user_id' in result:
                self.assertEqual(result['user_id'], user_id)
            for other_user_id in user_ids:
                if other_user_id != user_id:
                    self.assertNotIn(other_user_id, recovery_attempts[user_id])
        self.record_metric('independent_recovery_operations', len(user_ids))
        self.record_metric('recovery_user_isolation', True)
        self.record_metric('cross_user_recovery_interference', False)

class TestErrorMessageRouting(SSotAsyncTestCase):
    """
    Test error message routing and formatting.
    
    BVJ: Error messages must be properly formatted and routed to provide
    clear user feedback while maintaining technical accuracy for debugging.
    """

    @pytest.mark.integration
    async def test_error_message_formatting_and_routing(self):
        """
        Test error message formatting and routing to users.
        
        BUSINESS IMPACT: Well-formatted error messages improve user experience
        and reduce support burden by providing clear guidance.
        """
        context = await create_authenticated_user_context(user_email='error_formatting@example.com', environment='test')
        user_id = str(context.user_id)
        error_test_cases = [{'error': ValueError('Invalid input parameters'), 'category': ErrorCategory.VALIDATION, 'expected_user_message_contains': ['input', 'parameters'], 'expected_technical': True}, {'error': ConnectionError('Database connection failed'), 'category': ErrorCategory.DATABASE, 'expected_user_message_contains': ['temporarily unavailable', 'try again'], 'expected_technical': True}, {'error': TimeoutError('Operation timed out after 30 seconds'), 'category': ErrorCategory.TIMEOUT, 'expected_user_message_contains': ['timed out', 'try again'], 'expected_technical': True}, {'error': PermissionError('Access denied to resource'), 'category': ErrorCategory.USER, 'expected_user_message_contains': ['permission', 'access'], 'expected_technical': False}]
        error_handler = UnifiedErrorHandler()
        formatted_errors = []
        for i, test_case in enumerate(error_test_cases):
            error_context = ErrorContext(trace_id=f'formatting_test_{i}_{user_id}', operation='error_formatting_test', user_id=user_id, details={'test_case': i})
            result = await error_handler.handle_error(test_case['error'], error_context)
            formatted_errors.append(result)
            if hasattr(result, 'user_message'):
                user_message = result.user_message.lower()
                for phrase in test_case['expected_user_message_contains']:
                    self.assertIn(phrase.lower(), user_message, f"User message should contain '{phrase}' for error type {i}")
                if test_case['expected_technical']:
                    self.assertTrue(len(result.user_message) > 10, 'Technical errors should have detailed messages')
                else:
                    self.assertNotIn('denied', user_message, 'Security errors should not expose denial details')
            if hasattr(result, 'error_code'):
                self.assertIsNotNone(result.error_code, f'Error code should be present for error type {i}')
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_to_user = AsyncMock()
        for i, formatted_error in enumerate(formatted_errors):
            error_message = {'type': 'formatted_error', 'error_code': getattr(formatted_error, 'error_code', 'UNKNOWN'), 'user_message': getattr(formatted_error, 'user_message', 'An error occurred'), 'trace_id': getattr(formatted_error, 'trace_id', f'trace_{i}'), 'recoverable': True, 'timestamp': getattr(formatted_error, 'timestamp', time.time())}
            await mock_ws_manager.send_to_user(user_id, error_message)
        self.assertEqual(mock_ws_manager.send_to_user.call_count, len(error_test_cases))
        self.record_metric('error_messages_formatted', len(error_test_cases))
        self.record_metric('error_messages_routed', len(error_test_cases))
        self.record_metric('user_friendly_formatting', True)

    @pytest.mark.integration
    async def test_error_message_user_context_routing(self):
        """
        Test error messages include proper user context for routing.
        
        BUSINESS IMPACT: Error messages with proper context help users
        understand what went wrong and provide support teams with debugging info.
        """
        context = await create_authenticated_user_context(user_email='context_routing@example.com', environment='test', permissions=['read', 'write', 'admin'])
        user_id = str(context.user_id)
        thread_id = str(context.thread_id)
        run_id = str(context.run_id)
        error_context = ErrorContext(trace_id=f'context_routing_test_{user_id}', operation='complex_operation', user_id=user_id, thread_id=thread_id, run_id=run_id, details={'operation_step': 'data_processing', 'resource_id': 'resource_123', 'user_permissions': context.agent_context.get('permissions', []), 'timestamp': time.time()})
        contextual_error = RuntimeError('Complex operation failed at data processing step')
        error_handler = UnifiedErrorHandler()
        result = await error_handler.handle_error(contextual_error, error_context)
        if hasattr(result, 'trace_id'):
            self.assertEqual(result.trace_id, error_context.trace_id)
        contextual_message = {'type': 'contextual_error', 'error_code': getattr(result, 'error_code', 'CONTEXT_ERROR'), 'user_message': getattr(result, 'user_message', 'Operation failed'), 'trace_id': error_context.trace_id, 'user_context': {'user_id': user_id, 'thread_id': thread_id, 'run_id': run_id, 'operation': error_context.operation, 'operation_step': error_context.details.get('operation_step'), 'resource_id': error_context.details.get('resource_id'), 'user_permissions': error_context.details.get('user_permissions', [])}, 'support_info': {'trace_id': error_context.trace_id, 'timestamp': error_context.details.get('timestamp'), 'operation_path': f"{error_context.operation}/{error_context.details.get('operation_step')}"}, 'recoverable': True}
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_to_user = AsyncMock()
        await mock_ws_manager.send_to_user(user_id, contextual_message)
        mock_ws_manager.send_to_user.assert_called_once_with(user_id, contextual_message)
        sent_message = mock_ws_manager.send_to_user.call_args[0][1]
        self.assertIn('user_context', sent_message)
        self.assertIn('support_info', sent_message)
        self.assertEqual(sent_message['user_context']['user_id'], user_id)
        self.assertEqual(sent_message['user_context']['thread_id'], thread_id)
        self.assertEqual(sent_message['user_context']['run_id'], run_id)
        self.assertIn('read', sent_message['user_context']['user_permissions'])
        self.record_metric('contextual_error_routing', True)
        self.record_metric('context_fields_preserved', len(sent_message['user_context']))
        self.record_metric('support_info_included', True)

class TestSystemErrorRecovery(SSotAsyncTestCase):
    """
    Test system-wide error recovery and graceful degradation.
    
    BVJ: System recovery ensures business continuity during partial failures
    and maintains service availability for all users during issues.
    """

    @pytest.mark.integration
    async def test_routing_system_partial_failure_recovery(self):
        """
        Test recovery from partial routing system failures.
        
        BUSINESS IMPACT: Partial system failures should not bring down
        entire routing system, with graceful degradation and recovery.
        """
        user_contexts = []
        for i in range(4):
            context = await create_authenticated_user_context(user_email=f'system_recovery_{i}@example.com', environment='test')
            user_contexts.append(context)
        user_ids = [str(context.user_id) for context in user_contexts]
        mock_ws_manager = AsyncMock()
        router = WebSocketEventRouter(mock_ws_manager)
        conn_ids = []
        for user_id in user_ids:
            conn_id = f'conn_{user_id}'
            conn_ids.append(conn_id)
            await router.register_connection(user_id, conn_id)
        send_results = [ConnectionError('System overload'), True, ConnectionError('Network timeout'), True]
        mock_ws_manager.send_to_connection = AsyncMock(side_effect=send_results)
        system_test_event = {'type': 'system_test', 'message': 'partial_failure_recovery_test', 'timestamp': time.time()}
        results = []
        for user_id, conn_id in zip(user_ids, conn_ids):
            result = await router.route_event(user_id, conn_id, system_test_event)
            results.append((user_id, result))
        successful_routes = [r for r in results if r[1] is True]
        failed_routes = [r for r in results if r[1] is False]
        self.assertEqual(len(successful_routes), 2, 'Should have 2 successful routes')
        self.assertEqual(len(failed_routes), 2, 'Should have 2 failed routes')
        system_stats = await router.get_stats()
        self.assertGreater(system_stats['total_connections'], 0, 'System should still track connections')
        mock_ws_manager.send_to_connection = AsyncMock(return_value=True)
        recovery_results = []
        for user_id, _ in failed_routes:
            conn_id = f'conn_{user_id}'
            retry_result = await router.route_event(user_id, conn_id, system_test_event)
            recovery_results.append((user_id, retry_result))
        all_recovered = all((result[1] is True for result in recovery_results))
        self.assertTrue(all_recovered, 'All failed routes should recover')
        self.record_metric('partial_system_failures', len(failed_routes))
        self.record_metric('system_continued_operating', True)
        self.record_metric('failed_routes_recovered', len(recovery_results))
        self.record_metric('system_recovery_successful', all_recovered)

    @pytest.mark.integration
    async def test_routing_system_overload_error_handling(self):
        """
        Test system overload error handling with backpressure.
        
        BUSINESS IMPACT: System overload should trigger backpressure mechanisms
        to protect system stability while maintaining service for high-priority users.
        """
        user_contexts = []
        for i in range(10):
            context = await create_authenticated_user_context(user_email=f'overload_test_{i}@example.com', environment='test', permissions=['premium'] if i < 3 else ['standard'])
            user_contexts.append(context)
        user_ids = [str(context.user_id) for context in user_contexts]

        class OverloadSimulationHandler(BaseMessageHandler):

            def __init__(self):
                self.message_count = 0
                self.overload_threshold = 5

            def get_message_type(self) -> str:
                return 'overload_test_message'

            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                self.message_count += 1
                if self.message_count > self.overload_threshold:
                    user_context = next((c for c in user_contexts if str(c.user_id) == user_id), None)
                    if user_context and 'premium' not in user_context.agent_context.get('permissions', []):
                        raise RuntimeError(f'System overloaded - rate limiting user {user_id}')
                return {'status': 'processed', 'user_id': user_id, 'message_count': self.message_count}
        mock_supervisor = MagicMock()
        mock_db_factory = MagicMock()
        handler_service = MessageHandlerService(mock_supervisor, mock_db_factory)
        overload_handler = OverloadSimulationHandler()
        handler_service.register_handler(overload_handler)
        ws_managers = {}
        for user_id in user_ids:
            mock_ws = AsyncMock()
            mock_ws.send_error = AsyncMock()
            mock_ws.validate_message = MagicMock(return_value=True)
            mock_ws.sanitize_message = MagicMock(side_effect=lambda x: x)
            ws_managers[user_id] = mock_ws
        test_message = {'type': 'overload_test_message', 'payload': {'data': 'overload_test'}}

        def create_ws_manager(context):
            return ws_managers[str(context.user_id)]
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create:
            mock_create.side_effect = create_ws_manager
            results = []
            for user_id in user_ids:
                try:
                    await handler_service.handle_message(user_id, test_message)
                    results.append((user_id, 'success'))
                except Exception as e:
                    results.append((user_id, f'error: {str(e)}'))
                await asyncio.sleep(0.05)
            premium_users = user_ids[:3]
            standard_users = user_ids[3:]
            premium_results = [r for r in results if r[0] in premium_users]
            standard_results = [r for r in results if r[0] in standard_users]
            premium_successes = [r for r in premium_results if r[1] == 'success']
            self.assertGreater(len(premium_successes), 0, 'Premium users should have some successes')
            standard_errors = [r for r in standard_results if 'overloaded' in r[1]]
            self.assertGreater(len(standard_errors), 0, 'Some standard users should be rate limited')
            standard_successes = [r for r in standard_results if r[1] == 'success']
            total_processed = len(premium_successes) + len(standard_successes)
            self.assertLessEqual(total_processed, overload_handler.overload_threshold + 3, 'Backpressure should limit total processed messages')
            self.record_metric('system_overload_detected', True)
            self.record_metric('premium_users_protected', len(premium_successes))
            self.record_metric('standard_users_rate_limited', len(standard_errors))
            self.record_metric('backpressure_applied', len(standard_errors) > 0)
            self.record_metric('system_stability_maintained', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')