"""
SSOT Message Route Authentication Delegation Test - ISSUE #814

PURPOSE: Integration test validating message route authentication delegates to auth service
EXPECTED: PASS after SSOT remediation - validates proper route auth delegation
TARGET: Message/chat route authentication must use auth service, never direct JWT handling

BUSINESS VALUE: Ensures $500K+ ARR Golden Path message routing authentication reliability
"""
import logging
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestMessageRouteAuthDelegation(SSotAsyncTestCase):
    """
    Integration test validating message route authentication SSOT compliance.
    Tests proper delegation to auth service for all message route operations.
    """

    async def asyncSetUp(self):
        """Setup message route authentication testing environment"""
        await super().asyncSetUp()
        self.valid_message_auth = {'valid': True, 'user_id': 'message-user-456', 'email': 'messages@example.com', 'tier': 'enterprise', 'permissions': ['send_messages', 'view_history', 'create_threads'], 'rate_limit_remaining': 90}
        self.invalid_message_auth = {'valid': False, 'error': 'Insufficient permissions', 'code': 'PERMISSION_DENIED'}

    async def test_threads_messages_route_delegates_auth(self):
        """
        Integration test: Threads/messages route delegates authentication to auth service

        VALIDATES: Message routes use auth service for user authentication
        ENSURES: No direct JWT handling in route handlers
        """
        with patch('netra_backend.app.routes.threads_messages.auth_client') as mock_auth_client:
            mock_auth_client.validate_route_auth.return_value = self.valid_message_auth
            from netra_backend.app.routes.threads_messages import send_message_endpoint
            mock_request = Mock()
            mock_request.headers = {'Authorization': 'Bearer threads-test-token'}
            auth_result = await send_message_endpoint.authenticate_request(mock_request)
            mock_auth_client.validate_route_auth.assert_called_once_with(token='threads-test-token', route='threads_messages', action='send_message')
            assert auth_result.authenticated is True, 'Route authentication successful'
            assert auth_result.user_id == 'message-user-456', 'User ID from auth service'
            assert 'send_messages' in auth_result.permissions, 'Permissions from auth service'

    async def test_message_history_route_uses_auth_delegation(self):
        """
        Integration test: Message history route uses auth service delegation

        VALIDATES: History retrieval authenticated through auth service
        ENSURES: No custom permission logic in history routes
        """
        with patch('netra_backend.app.routes.message_history.auth_client') as mock_auth_client:
            mock_auth_client.validate_history_access.return_value = {'valid': True, 'user_id': 'history-user-789', 'can_view_history': True, 'accessible_threads': ['thread-1', 'thread-2', 'thread-3'], 'history_limit': 100}
            from netra_backend.app.routes.message_history import get_message_history
            test_token = 'history-access-token'
            thread_id = 'thread-1'
            history_auth = await get_message_history.authenticate_access(token=test_token, thread_id=thread_id)
            mock_auth_client.validate_history_access.assert_called_once_with(test_token, thread_id)
            assert history_auth['valid'] is True, 'History access valid'
            assert history_auth['user_id'] == 'history-user-789', 'History user from auth service'
            assert thread_id in history_auth['accessible_threads'], 'Thread access from auth service'

    async def test_thread_creation_route_delegates_permissions(self):
        """
        Integration test: Thread creation route delegates permissions to auth service

        VALIDATES: Thread creation permissions managed by auth service
        ENSURES: No custom thread permission logic in routes
        """
        with patch('netra_backend.app.routes.thread_management.auth_client') as mock_auth_client:
            mock_auth_client.validate_thread_creation.return_value = {'valid': True, 'user_id': 'thread-creator-321', 'can_create_threads': True, 'thread_limit': 50, 'current_thread_count': 12, 'workspace_access': ['default', 'project-a']}
            from netra_backend.app.routes.thread_management import create_thread_endpoint
            test_token = 'thread-creation-token'
            workspace = 'default'
            creation_auth = await create_thread_endpoint.validate_creation_permissions(token=test_token, workspace=workspace)
            mock_auth_client.validate_thread_creation.assert_called_once_with(test_token, workspace)
            assert creation_auth['valid'] is True, 'Thread creation valid'
            assert creation_auth['can_create_threads'] is True, 'Creation permission from auth service'
            assert workspace in creation_auth['workspace_access'], 'Workspace access from auth service'

    async def test_agent_message_route_uses_auth_context(self):
        """
        Integration test: Agent message route uses auth service context

        VALIDATES: Agent interactions authenticated through auth service
        ENSURES: Agent message routing uses auth service user context
        """
        with patch('netra_backend.app.routes.agent_messages.auth_client') as mock_auth_client:
            mock_auth_client.validate_agent_interaction.return_value = {'valid': True, 'user_id': 'agent-user-654', 'tier': 'enterprise', 'agent_permissions': ['supervisor', 'data_helper', 'apex_optimizer'], 'interaction_limits': {'daily_messages': 1000, 'concurrent_agents': 5, 'used_today': 150}}
            from netra_backend.app.routes.agent_messages import process_agent_message
            test_token = 'agent-interaction-token'
            agent_type = 'supervisor'
            message_data = {'content': 'Analyze market data'}
            agent_auth = await process_agent_message.authenticate_agent_interaction(token=test_token, agent_type=agent_type, message_data=message_data)
            mock_auth_client.validate_agent_interaction.assert_called_once_with(test_token, agent_type)
            assert agent_auth['valid'] is True, 'Agent interaction valid'
            assert agent_auth['user_id'] == 'agent-user-654', 'Agent user from auth service'
            assert agent_type in agent_auth['agent_permissions'], 'Agent permission from auth service'

    async def test_message_route_rate_limiting_uses_auth_service(self):
        """
        Integration test: Message route rate limiting managed by auth service

        VALIDATES: Rate limiting decisions made by auth service
        ENSURES: No custom rate limiting logic bypassing auth service
        """
        with patch('netra_backend.app.routes.rate_limiting.auth_client') as mock_auth_client:
            mock_auth_client.check_rate_limit.return_value = {'allowed': True, 'user_id': 'rate-limit-user-987', 'remaining_requests': 45, 'reset_time': '2025-09-13T13:00:00Z', 'limit_type': 'messages_per_hour'}
            from netra_backend.app.routes.rate_limiting import MessageRateLimiter
            rate_limiter = MessageRateLimiter()
            test_token = 'rate-limit-token'
            rate_check = await rate_limiter.check_message_rate_limit(token=test_token, route='send_message')
            mock_auth_client.check_rate_limit.assert_called_once_with(test_token, 'send_message')
            assert rate_check['allowed'] is True, 'Rate limit check from auth service'
            assert rate_check['remaining_requests'] == 45, 'Remaining requests from auth service'
            assert rate_check['user_id'] == 'rate-limit-user-987', 'Rate limit user from auth service'

    async def test_route_middleware_auth_delegation_integration(self):
        """
        Integration test: Route middleware properly integrates auth service delegation

        VALIDATES: Route-level middleware uses auth service integration
        ENSURES: Consistent auth service delegation across all message routes
        """
        with patch('netra_backend.app.middleware.route_auth.auth_client') as mock_auth_client:
            mock_auth_client.validate_route_middleware.return_value = {'valid': True, 'user_id': 'middleware-user-147', 'route_permissions': ['messages', 'threads', 'history'], 'middleware_context': {'request_id': 'req-789', 'user_context': {'workspace': 'default'}}}
            from netra_backend.app.middleware.route_auth import MessageRouteAuthMiddleware
            middleware = MessageRouteAuthMiddleware()
            test_token = 'route-middleware-token'
            route_context = {'path': '/api/v1/messages', 'method': 'POST', 'route_name': 'send_message'}
            middleware_auth = await middleware.authenticate_route(token=test_token, route_context=route_context)
            mock_auth_client.validate_route_middleware.assert_called_once_with(test_token, route_context)
            assert middleware_auth['valid'] is True, 'Middleware auth valid'
            assert middleware_auth['user_id'] == 'middleware-user-147', 'Middleware user from auth service'
            assert 'messages' in middleware_auth['route_permissions'], 'Route permissions from auth service'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')