"""
Dependencies SSOT Factory Integration Tests for Issue #1142

PURPOSE: Validate that FastAPI dependencies.py uses the correct SSOT per-request
agent factory pattern instead of singleton configuration.

CRITICAL: These tests validate the production dependency injection patterns
that serve the Golden Path user flow.

Created: 2025-09-14
Issue: #1142 - SSOT Agent Factory Singleton violation blocking Golden Path
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import Request
from typing import Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.dependencies import get_agent_instance_factory_dependency, AgentInstanceFactoryDep
from netra_backend.app.services.user_execution_context import UserExecutionContext

class MockAppState:
    """Mock FastAPI app state for dependency testing."""

    def __init__(self):
        self.agent_websocket_bridge = MagicMock()
        self.llm_manager = MagicMock()
        self.agent_class_registry = MagicMock()
        self.tool_dispatcher = MagicMock()

class MockRequest:
    """Mock FastAPI request for dependency testing."""

    def __init__(self, user_id: Optional[str]=None):
        self.app = MagicMock()
        self.app.state = MockAppState()
        self.headers = {}
        self.user_id = user_id
        if user_id:
            self.headers['user-id'] = user_id

class TestDependenciesSSOTFactory1142(SSotAsyncTestCase):
    """Validate SSOT factory pattern in FastAPI dependencies."""

    async def asyncSetUp(self):
        """Set up test fixtures for dependency testing."""
        await super().asyncSetUp()
        self.healthcare_user_id = 'healthcare_user_001'
        self.fintech_user_id = 'fintech_user_002'
        self.healthcare_request = MockRequest(self.healthcare_user_id)
        self.fintech_request = MockRequest(self.fintech_user_id)

    async def test_get_agent_instance_factory_dependency_creates_per_request_factory(self):
        """
        CRITICAL: Test that dependency creates NEW factory for each request.
        
        This validates that the FastAPI dependency injection uses the correct
        SSOT pattern instead of returning a shared singleton factory.
        
        Expected: PASS - Each request gets isolated factory instance
        """
        with patch('netra_backend.app.dependencies._extract_user_id_from_request') as mock_extract:
            mock_extract.side_effect = [self.healthcare_user_id, self.fintech_user_id]
            factory1 = await get_agent_instance_factory_dependency(self.healthcare_request)
            factory2 = await get_agent_instance_factory_dependency(self.fintech_request)
            assert factory1 is not factory2, f'DEPENDENCY ISOLATION SUCCESS: Each request gets separate factory. Factory1: {id(factory1)}, Factory2: {id(factory2)}. This proves per-request SSOT pattern is working.'
            assert factory1._user_context.user_id == self.healthcare_user_id
            assert factory2._user_context.user_id == self.fintech_user_id

    async def test_concurrent_dependency_requests_no_contamination(self):
        """
        CRITICAL: Test concurrent FastAPI requests don't cause factory contamination.
        
        This validates that simultaneous API requests each get isolated factories
        without race conditions or shared state contamination.
        
        Expected: PASS - No cross-request factory contamination
        """

        async def create_factory_via_dependency(request: MockRequest, user_id: str):
            """Simulate FastAPI dependency injection for a specific request."""
            with patch('netra_backend.app.dependencies._extract_user_id_from_request') as mock_extract:
                mock_extract.return_value = user_id
                return await get_agent_instance_factory_dependency(request)
        user_requests = [(MockRequest(f'concurrent_user_{i}'), f'concurrent_user_{i}') for i in range(5)]
        tasks = [create_factory_via_dependency(request, user_id) for request, user_id in user_requests]
        factories = await asyncio.gather(*tasks)
        factory_ids = [id(factory) for factory in factories]
        unique_ids = set(factory_ids)
        assert len(unique_ids) == len(factories), f'CONCURRENT DEPENDENCY CONTAMINATION: {len(factories)} requests but only {len(unique_ids)} unique factories. This indicates singleton sharing. Factory IDs: {factory_ids}'
        user_ids = [factory._user_context.user_id for factory in factories]
        expected_user_ids = [f'concurrent_user_{i}' for i in range(5)]
        for actual_id, expected_id in zip(user_ids, expected_user_ids):
            assert actual_id == expected_id, f'USER CONTEXT DEPENDENCY VIOLATION: Expected {expected_id}, got {actual_id}. This indicates user context contamination in dependency injection.'

    async def test_dependency_factory_configuration_isolation(self):
        """
        CRITICAL: Test that dependency factories maintain configuration isolation.
        
        This validates that factories created through dependency injection
        properly isolate shared infrastructure components per user.
        
        Expected: PASS - Configuration isolation maintained in dependency injection
        """
        with patch('netra_backend.app.dependencies._extract_user_id_from_request') as mock_extract:
            mock_extract.side_effect = [self.healthcare_user_id, self.fintech_user_id]
            factory1 = await get_agent_instance_factory_dependency(self.healthcare_request)
            factory2 = await get_agent_instance_factory_dependency(self.fintech_request)
            assert hasattr(factory1, '_websocket_bridge'), 'DEPENDENCY CONFIGURATION: Factory1 should be configured with WebSocket bridge'
            assert hasattr(factory2, '_websocket_bridge'), 'DEPENDENCY CONFIGURATION: Factory2 should be configured with WebSocket bridge'
            assert factory1._user_context.user_id == self.healthcare_user_id
            assert factory2._user_context.user_id == self.fintech_user_id
            assert factory1._user_context.run_id != factory2._user_context.run_id, f'RUN ID CONTAMINATION: Both factories have same run_id ({factory1._user_context.run_id}). This indicates run ID collision.'

    async def test_dependency_injection_without_user_id(self):
        """
        CRITICAL: Test dependency handles missing user ID gracefully.
        
        This validates that the dependency can create factories even when
        user ID extraction fails, using service context as fallback.
        
        Expected: PASS - Graceful fallback to service context
        """
        anonymous_request = MockRequest()
        with patch('netra_backend.app.dependencies._extract_user_id_from_request') as mock_extract:
            with patch('netra_backend.app.dependencies.get_service_user_context') as mock_service:
                mock_extract.return_value = None
                mock_service.return_value = 'service_user_context'
                factory = await get_agent_instance_factory_dependency(anonymous_request)
                assert factory is not None, 'DEPENDENCY FALLBACK: Should create factory even without user ID'
                assert factory._user_context.user_id == 'service_user_context', f"FALLBACK USER CONTEXT: Expected 'service_user_context', got '{factory._user_context.user_id}'"

    async def test_dependency_infrastructure_validation(self):
        """
        CRITICAL: Test dependency validates required infrastructure components.
        
        This validates that the dependency injection fails gracefully when
        required infrastructure (WebSocket bridge) is not available.
        
        Expected: PASS - Proper error handling for missing infrastructure
        """
        broken_request = MockRequest(self.healthcare_user_id)
        delattr(broken_request.app.state, 'agent_websocket_bridge')
        with patch('netra_backend.app.dependencies._extract_user_id_from_request') as mock_extract:
            mock_extract.return_value = self.healthcare_user_id
            with pytest.raises(Exception) as exc_info:
                await get_agent_instance_factory_dependency(broken_request)
            assert 'WebSocket bridge not initialized' in str(exc_info.value), f'INFRASTRUCTURE VALIDATION: Expected WebSocket bridge error, got: {exc_info.value}'

    async def test_dependency_user_context_generation(self):
        """
        CRITICAL: Test dependency generates complete user execution context.
        
        This validates that dependency injection creates proper UserExecutionContext
        with all required identifiers for isolated execution.
        
        Expected: PASS - Complete user context generated with unique identifiers
        """
        with patch('netra_backend.app.dependencies._extract_user_id_from_request') as mock_extract:
            mock_extract.return_value = self.healthcare_user_id
            factory = await get_agent_instance_factory_dependency(self.healthcare_request)
            user_context = factory._user_context
            assert user_context.user_id == self.healthcare_user_id, f'USER ID BINDING: Expected {self.healthcare_user_id}, got {user_context.user_id}'
            assert user_context.thread_id is not None, 'THREAD ID GENERATION: Thread ID should be generated'
            assert user_context.thread_id.startswith('thread'), f'THREAD ID FORMAT: Expected thread prefix, got {user_context.thread_id}'
            assert user_context.run_id is not None, 'RUN ID GENERATION: Run ID should be generated'
            assert user_context.run_id.startswith('run'), f'RUN ID FORMAT: Expected run prefix, got {user_context.run_id}'
            assert user_context.websocket_client_id is not None, 'WEBSOCKET CLIENT ID GENERATION: WebSocket client ID should be generated'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')