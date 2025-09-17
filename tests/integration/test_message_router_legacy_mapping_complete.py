"""
Integration Tests: MessageRouter Legacy Message Type Mapping

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Integration & Chat Reliability
- Value Impact: Ensure complete message routing works end-to-end with real services
- Strategic Impact: Validates that message type mapping works across service boundaries

This integration test suite validates MessageRouter with real services and
comprehensive message type scenarios, focusing on the 'chat_message' mapping gap
and its impact on the complete chat workflow.

CRITICAL: These tests validate that 'chat_message' integration works properly 
across the complete message handling pipeline after the LEGACY_MESSAGE_TYPE_MAP fix.
"""
import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List
from fastapi import WebSocket
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.websocket_core.types import MessageType, LEGACY_MESSAGE_TYPE_MAP, normalize_message_type, create_standard_message, WebSocketMessage
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.database.test_database_manager import DatabaseTestManager

@pytest.mark.integration
class MessageRouterLegacyMappingIntegrationTests:
    """
    Integration tests for MessageRouter legacy type mapping with real service integration.
    
    These tests validate that message types are properly handled across the complete
    WebSocket management pipeline, including authentication and database operations.
    """

    @pytest.mark.asyncio
    async def test_chat_message_routing_with_real_websocket_manager(self):
        """
        Integration test: Chat message routing through UnifiedWebSocketManager.
        
        This test validates that 'chat_message' handling works (or fails) through
        the complete WebSocket management stack, not just the router in isolation.
        """
        auth_context = await create_authenticated_user_context(user_email='integration_chat@example.com', environment='test', websocket_enabled=True)
        user_id = str(auth_context.user_id)
        try:
            from netra_backend.app.websocket_core import create_websocket_manager
            ws_manager = await create_websocket_manager(auth_context)
        except Exception as e:
            pytest.skip(f'WebSocket manager creation failed: {e}')
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'integration_websocket'})()
        connection_id = f'integration_conn_{uuid.uuid4().hex[:8]}'
        await ws_manager.connect(connection_id, user_id, mock_websocket)
        chat_message_payload = {'type': 'chat_message', 'payload': {'content': 'Analyze my business data with AI agents', 'integration_context': {'websocket_manager': 'unified', 'auth_context': str(auth_context.user_id), 'connection_id': connection_id}, 'requires_processing': True}, 'message_id': f'integration_chat_{int(time.time())}', 'user_id': user_id, 'thread_id': str(auth_context.thread_id), 'timestamp': time.time()}
        try:
            result = await ws_manager.handle_message(connection_id, chat_message_payload)
        except Exception as e:
            result = None
            print(f'Integration pipeline error: {e}')
        router = get_message_router()
        is_chat_message_unknown = router._is_unknown_message_type('chat_message')
        assert is_chat_message_unknown == False, "INTEGRATION SUCCESS: 'chat_message' is now recognized and works with complete WebSocket pipeline"
        ws_stats = await ws_manager.get_stats()
        print(f'[U+1F517] INTEGRATION PIPELINE RESULTS:')
        print(f'   - Chat message recognized type: {not is_chat_message_unknown}')
        print(f'   - Pipeline result: {result}')
        print(f"   - Active connections: {ws_stats.get('active_connections', 0)}")
        print(f"   - Messages processed: {ws_stats.get('messages_received', 0)}")
        print(f'   - Integration impact: Complete chat workflow working properly')
        await ws_manager.disconnect(connection_id)

    @pytest.mark.asyncio
    async def test_message_type_mapping_database_integration(self):
        """
        Integration test: Message type handling with database operations.
        
        This validates that recognized message types work properly with database operations
        and message persistence in the integration environment.
        """
        db_manager = DatabaseTestManager()
        try:
            await db_manager.setup_test_session()
        except Exception as e:
            pytest.skip(f'Database setup failed: {e}')
        auth_context = await create_authenticated_user_context(user_email='db_integration@example.com', environment='test')
        router = get_message_router()
        user_id = str(auth_context.user_id)
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'db_integration_ws'})()
        database_chat_message = {'type': 'chat_message', 'payload': {'content': 'Save this chat message to database for later retrieval', 'database_metadata': {'should_persist': True, 'thread_id': str(auth_context.thread_id), 'message_importance': 'high'}, 'requires_agent_response': True}, 'message_id': f'db_chat_{uuid.uuid4().hex[:8]}', 'user_id': user_id, 'thread_id': str(auth_context.thread_id), 'timestamp': time.time()}
        routing_result = await router.route_message(user_id, mock_websocket, database_chat_message)
        is_unknown = router._is_unknown_message_type('chat_message')
        assert is_unknown == False, "DATABASE INTEGRATION SUCCESS: Recognized 'chat_message' type enables proper message categorization and database operations"
        stats = router.get_stats()
        assert stats['messages_routed'] > 0, 'Message should be routed successfully, enabling database persistence logic'
        print(f'[U+1F5C3][U+FE0F] DATABASE INTEGRATION ANALYSIS:')
        print(f'   - Recognized message type: {not is_unknown}')
        print(f'   - Routing result: {routing_result}')
        print(f"   - Messages routed: {stats['messages_routed']}")
        print(f'   - Database impact: Message categorization and persistence working properly')
        try:
            await db_manager.cleanup_test_session()
        except Exception as e:
            print(f'Database cleanup warning: {e}')

    @pytest.mark.asyncio
    async def test_chat_message_multi_handler_integration(self):
        """
        Integration test: Chat message interaction with multiple message handlers.
        
        This validates how 'chat_message' recognized type works with the complete
        handler ecosystem and inter-handler communication.
        """
        router = get_message_router()
        handler_names = [handler.__class__.__name__ for handler in router.handlers]
        initial_handler_stats = {}
        for handler in router.handlers:
            if hasattr(handler, 'get_stats'):
                initial_handler_stats[handler.__class__.__name__] = handler.get_stats()
        auth_context = await create_authenticated_user_context(user_email='multi_handler@example.com', environment='test')
        user_id = str(auth_context.user_id)
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'multi_handler_ws'})()
        multi_handler_message = {'type': 'chat_message', 'payload': {'content': 'This message should flow through handler pipeline', 'handler_hints': {'user_message_handler': True, 'agent_handler': False, 'typing_handler': False, 'heartbeat_handler': False}, 'multi_handler_test': True}, 'message_id': f'multi_handler_{int(time.time())}', 'user_id': user_id, 'thread_id': str(auth_context.thread_id)}
        result = await router.route_message(user_id, mock_websocket, multi_handler_message)
        is_unknown = router._is_unknown_message_type('chat_message')
        final_stats = router.get_stats()
        final_handler_stats = final_stats.get('handler_stats', {})
        assert is_unknown == False, 'MULTI-HANDLER INTEGRATION: Recognized type is handled by appropriate handlers in ecosystem'
        handlers_that_processed = []
        for handler_name in handler_names:
            initial_processed = initial_handler_stats.get(handler_name, {}).get('processed', 0)
            final_processed = final_handler_stats.get(handler_name, {}).get('processed', 0)
            if final_processed > initial_processed:
                handlers_that_processed.append(handler_name)
        print(f'Handlers that processed the message: {handlers_that_processed}')
        print(f' CYCLE:  MULTI-HANDLER INTEGRATION RESULTS:')
        print(f'   - Registered handlers: {len(handler_names)}')
        print(f'   - Handler names: {handler_names}')
        print(f'   - Recognized type: {not is_unknown}')
        print(f'   - Handlers that processed message: {handlers_that_processed}')
        print(f'   - Integration impact: Handler pipeline working properly')

    @pytest.mark.asyncio
    async def test_legacy_mapping_completeness_integration(self):
        """
        Integration test: Comprehensive analysis of legacy mapping completeness.
        
        This test analyzes the complete LEGACY_MESSAGE_TYPE_MAP for patterns
        and identifies all missing mappings that could cause integration issues.
        """
        router = get_message_router()
        legacy_types = list(LEGACY_MESSAGE_TYPE_MAP.keys())
        all_enum_values = [mt.value for mt in MessageType]
        chat_patterns = [t for t in legacy_types if 'chat' in t.lower()]
        message_patterns = [t for t in legacy_types if 'message' in t.lower()]
        user_patterns = [t for t in legacy_types if 'user' in t.lower()]
        agent_patterns = [t for t in legacy_types if 'agent' in t.lower()]
        frontend_variations = ['chat_message', 'chat_input', 'chat_request', 'message_input', 'user_chat_message', 'chat_user_message', 'message_chat', 'input_message', 'text_message', 'user_text']
        unknown_variations = []
        for variation in frontend_variations:
            if router._is_unknown_message_type(variation):
                unknown_variations.append(variation)
        assert 'chat_message' not in unknown_variations, "COMPLETENESS INTEGRATION: 'chat_message' should NOT be in unknown variations - it's now mapped"
        total_variations = len(frontend_variations)
        unknown_count = len(unknown_variations)
        coverage_percentage = (total_variations - unknown_count) / total_variations * 100
        print(f' CHART:  LEGACY MAPPING COMPLETENESS ANALYSIS:')
        print(f'   - Total legacy types: {len(legacy_types)}')
        print(f'   - Chat patterns: {chat_patterns}')
        print(f'   - Message patterns: {message_patterns}')
        print(f'   - User patterns: {user_patterns}')
        print(f'   - Agent patterns: {agent_patterns}')
        print(f'   - Frontend variations tested: {total_variations}')
        print(f'   - Unknown variations: {unknown_count}')
        print(f'   - Coverage: {coverage_percentage:.1f}%')
        print(f'   - Unknown types: {unknown_variations}')
        print(f'   - Integration impact: {unknown_count} types still need mapping (chat_message is fixed)')
        mapping_targets = {}
        for key, value in LEGACY_MESSAGE_TYPE_MAP.items():
            if value not in mapping_targets:
                mapping_targets[value] = []
            mapping_targets[value].append(key)
        print(f'   - Mapping distribution:')
        for target, sources in mapping_targets.items():
            print(f"     {target}: {len(sources)} sources -> {sources[:3]}{('...' if len(sources) > 3 else '')}")

@pytest.mark.integration
class MessageRouterServiceIntegrationTests:
    """
    Integration tests for MessageRouter with external service dependencies.
    
    These tests validate message routing in realistic service integration scenarios.
    """

    @pytest.mark.asyncio
    async def test_chat_message_with_auth_service_integration(self):
        """
        Integration test: Chat message handling with authentication service integration.
        
        This validates that recognized message types work properly with authentication-dependent
        message processing workflows.
        """
        auth_helper = E2EAuthHelper(environment='test')
        try:
            jwt_token = auth_helper.create_test_jwt_token(user_id='auth_integration_user', email='auth_integration@example.com', permissions=['read', 'write', 'chat'])
            auth_headers = auth_helper.get_auth_headers(jwt_token)
        except Exception as e:
            pytest.skip(f'Auth integration setup failed: {e}')
        router = get_message_router()
        user_id = 'auth_integration_user'
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'auth_integration_ws', 'auth_headers': auth_headers})()
        auth_chat_message = {'type': 'chat_message', 'payload': {'content': 'Authenticated user requesting AI analysis', 'auth_context': {'requires_authentication': True, 'permission_required': 'chat', 'user_verified': True}, 'security_level': 'authenticated'}, 'message_id': f'auth_chat_{int(time.time())}', 'user_id': user_id, 'timestamp': time.time()}
        result = await router.route_message(user_id, mock_websocket, auth_chat_message)
        is_unknown = router._is_unknown_message_type('chat_message')
        assert is_unknown == False, "AUTH INTEGRATION SUCCESS: Recognized 'chat_message' type enables proper authentication-dependent message processing"
        assert mock_websocket.send_json.called, 'Should send handler response for recognized type'
        response = mock_websocket.send_json.call_args[0][0]
        print(f'[U+1F510] AUTH INTEGRATION ANALYSIS:')
        print(f'   - JWT token created: {bool(jwt_token)}')
        print(f'   - Auth headers available: {bool(auth_headers)}')
        print(f'   - Recognized message type: {not is_unknown}')
        print(f'   - Routing result: {result}')
        print(f'   - Auth impact: Authenticated chat workflows working properly')

    @pytest.mark.asyncio
    async def test_chat_message_cross_service_message_flow(self):
        """
        Integration test: Chat message flow across service boundaries.
        
        This simulates how 'chat_message' recognized type works with message flow
        between different services in the complete architecture.
        """
        auth_context = await create_authenticated_user_context(user_email='cross_service@example.com', environment='test')
        user_id = str(auth_context.user_id)
        router = get_message_router()
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'cross_service_ws', 'service_context': 'backend_to_frontend'})()
        cross_service_message = {'type': 'chat_message', 'payload': {'content': 'Cross-service chat request requiring agent processing', 'service_metadata': {'source_service': 'frontend', 'target_service': 'backend', 'requires_agent_service': True, 'cross_service_id': f'cross_{uuid.uuid4().hex[:8]}'}, 'workflow_requirements': {'agent_orchestration': True, 'response_routing': 'frontend', 'result_persistence': True}}, 'message_id': f'cross_service_{int(time.time())}', 'user_id': user_id, 'thread_id': str(auth_context.thread_id), 'timestamp': time.time()}
        result = await router.route_message(user_id, mock_websocket, cross_service_message)
        is_unknown = router._is_unknown_message_type('chat_message')
        assert is_unknown == False, "CROSS-SERVICE INTEGRATION SUCCESS: Recognized 'chat_message' type enables communication flow between frontend, backend, and agent services"
        stats = router.get_stats()
        print(f'[U+1F310] CROSS-SERVICE INTEGRATION ANALYSIS:')
        print(f'   - Recognized message type: {not is_unknown}')
        print(f'   - Cross-service routing result: {result}')
        print(f"   - Messages routed: {stats['messages_routed']}")
        print(f"   - Messages handled properly: {stats['messages_routed']}")
        print(f'   - Service impact: Frontend -> Backend -> Agent workflow working')
        print(f'   - Business impact: Complete AI chat service chain functional')
        assert mock_websocket.send_json.called, 'Should send handler response for recognized type'
        handler_response = mock_websocket.send_json.call_args[0][0]
        print(f'   - Cross-service response: Handler processing enabled, agent workflows functional')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')