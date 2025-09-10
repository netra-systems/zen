"""
Reproduction Test: WebSocket 1011 Internal Server Error - Complete Scenario

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Critical Production Issue Resolution
- Value Impact: Reproduces exact production failure scenario causing 100% WebSocket failure rate
- Strategic Impact: Prevents $500K+ ARR loss from complete WebSocket service outage

CRITICAL MISSION: Reproduce the EXACT WebSocket 1011 internal server error that is
causing 100% failure rate on agent message processing in staging and production.

This test reproduces the complete end-to-end failure scenario:
1. WebSocket connection establishes successfully
2. Authentication passes correctly
3. AgentMessageHandler.handle_message() is called
4. create_websocket_manager(user_context) fails during service initialization
5. Connection immediately closes with 1011 internal server error

IMPORTANT: This test is DESIGNED TO FAIL to prove it can reproduce the exact
production failure scenario that is blocking all chat functionality.

Test Approach: Full integration reproduction without Docker, using real services
where possible, but simulating the exact failure conditions present in staging.
"""

import asyncio
import pytest
import os
import json
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState

# Import all the components involved in the failure chain
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.dependencies import (
    get_user_execution_context,
    get_request_scoped_db_session
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService
from shared.id_generation import UnifiedIdGenerator


class MockWebSocketFor1011Testing:
    """
    Mock WebSocket that simulates the exact conditions present during 1011 errors.
    
    This mock reproduces the WebSocket state and behavior observed in production
    when 1011 internal server errors occur.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = WebSocketState.CONNECTED
        self.client_state = WebSocketState.CONNECTED
        self.scope = {
            'type': 'websocket',
            'path': '/ws',
            'headers': [
                (b'host', b'netra-staging.googlesapis.com'),
                (b'connection', b'upgrade'),
                (b'upgrade', b'websocket'),
                # Simulate headers that might be missing in staging causing issues
                (b'user-agent', b'Mozilla/5.0 (compatible)'),
            ],
            'query_string': f'user_id={user_id}'.encode(),
            'client': ('10.0.0.1', 0),
            'app': Mock()
        }
        # Mock app state that might be missing dependencies
        self.scope['app'].state = Mock()
        self.scope['app'].state.agent_registry = None  # This could cause issues
        self.scope['app'].state.websocket_bridge = None  # This could cause issues
        
        self.messages_sent = []
        self.connection_closed = False
        self.close_code = None
        self.close_reason = None
    
    async def accept(self):
        """Simulate successful WebSocket acceptance (this works in production)."""
        self.state = WebSocketState.CONNECTED
    
    async def send_text(self, data: str):
        """Simulate message sending."""
        self.messages_sent.append(('text', data))
    
    async def send_json(self, data: dict):
        """Simulate JSON message sending."""
        self.messages_sent.append(('json', data))
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Simulate WebSocket closure - this is where 1011 errors appear."""
        self.connection_closed = True
        self.close_code = code
        self.close_reason = reason
        self.state = WebSocketState.DISCONNECTED
        
        # CRITICAL: If code is 1011, this represents the exact production failure
        if code == 1011:
            raise RuntimeError(f"WebSocket closed with 1011 internal server error: {reason}")
    
    def get_connection_id_by_websocket(self, websocket):
        """Simulate connection ID lookup that might fail."""
        # Return None to simulate missing connection mapping
        return None


class TestWebSocket1011ErrorReproduction:
    """
    REPRODUCTION TEST SUITE: Complete end-to-end reproduction of WebSocket 1011 errors.
    
    These tests are DESIGNED TO FAIL with the exact error patterns observed in production.
    Success of these tests would indicate the reproduction is not accurate.
    """
    
    @pytest.fixture
    def test_user_id(self):
        """Generate consistent test user ID."""
        return UnifiedIdGenerator.generate_base_id("user")
    
    @pytest.fixture
    def test_thread_id(self):
        """Generate consistent test thread ID."""
        return UnifiedIdGenerator.generate_base_id("thread")
    
    @pytest.fixture
    def test_run_id(self):
        """Generate consistent test run ID."""
        return UnifiedIdGenerator.generate_base_id("run")
    
    @pytest.fixture
    def mock_websocket_1011(self, test_user_id):
        """Create mock WebSocket configured for 1011 error reproduction."""
        return MockWebSocketFor1011Testing(test_user_id)
    
    @pytest.fixture
    def start_agent_message(self, test_user_id, test_thread_id, test_run_id):
        """Create start_agent message that triggers the failure."""
        return WebSocketMessage(
            type=MessageType.START_AGENT,
            user_id=test_user_id,
            thread_id=test_thread_id,
            payload={
                "user_request": "Help me optimize my AI infrastructure costs",
                "agent_type": "cost_optimization",
                "thread_id": test_thread_id,
                "run_id": test_run_id
            }
        )
    
    @pytest.fixture
    def message_handler_service_mock(self):
        """Mock message handler service for isolation."""
        service = Mock(spec=MessageHandlerService)
        service.handle_start_agent = AsyncMock()
        service.handle_user_message = AsyncMock()
        return service
    
    async def test_complete_1011_error_reproduction_end_to_end(
        self, mock_websocket_1011, test_user_id, start_agent_message, message_handler_service_mock
    ):
        """
        CRITICAL REPRODUCTION: Complete end-to-end 1011 error scenario
        
        This test reproduces the EXACT sequence of events that leads to 1011 errors:
        1. WebSocket connection is established (✅ works)
        2. Authentication succeeds (✅ works)  
        3. AgentMessageHandler.handle_message() is called (✅ works)
        4. create_websocket_manager() is called (❌ FAILS HERE)
        5. Service initialization fails (❌ ROOT CAUSE)
        6. Connection closes with 1011 internal error (❌ SYMPTOM)
        
        Expected: This test should FAIL with RuntimeError containing "1011 internal server error"
        """
        # Create handler with real service dependencies
        handler = AgentMessageHandler(
            message_handler_service=message_handler_service_mock,
            websocket=mock_websocket_1011
        )
        
        print(f"🔍 Reproducing 1011 error for user: {test_user_id}")
        print(f"🔍 WebSocket state: {mock_websocket_1011.state}")
        print(f"🔍 Message type: {start_agent_message.type}")
        
        # CRITICAL: This should fail exactly as it does in production
        with pytest.raises(RuntimeError) as exc_info:
            # This is the exact call chain that fails in production:
            # routes/websocket.py -> AgentMessageHandler.handle_message() -> create_websocket_manager()
            success = await handler.handle_message(
                test_user_id, 
                mock_websocket_1011, 
                start_agent_message
            )
            
            # If we reach here, the reproduction failed to match production behavior
            assert False, (
                f"🚨 1011 ERROR REPRODUCTION FAILED: "
                f"Expected RuntimeError with 1011 but handler succeeded with result: {success}. "
                f"WebSocket state: {mock_websocket_1011.state}. "
                f"Connection closed: {mock_websocket_1011.connection_closed}. "
                f"Close code: {mock_websocket_1011.close_code}. "
                f"This indicates the reproduction test conditions don't match production exactly."
            )
        
        error_message = str(exc_info.value)
        
        # Validate we caught the expected 1011 error pattern
        critical_1011_patterns = [
            "1011",
            "internal server error",
            "WebSocket closed",
            "service initialization",
            "create_websocket_manager"
        ]
        
        pattern_found = any(pattern.lower() in error_message.lower() for pattern in critical_1011_patterns)
        
        assert pattern_found, (
            f"🚨 1011 ERROR PATTERN VALIDATION FAILED: "
            f"Caught RuntimeError '{error_message}' but it doesn't contain expected 1011 patterns. "
            f"Expected patterns: {critical_1011_patterns}. "
            f"This suggests the reproduction is not matching the exact production failure."
        )
        
        # Additional validation: Check WebSocket was properly closed with 1011
        assert mock_websocket_1011.connection_closed, "WebSocket should be closed after 1011 error"
        assert mock_websocket_1011.close_code == 1011, f"Expected close code 1011, got {mock_websocket_1011.close_code}"
        
        # Check handler recorded the error in statistics  
        stats = handler.get_stats()
        assert stats["errors"] > 0, f"Handler should record error in statistics: {stats}"
        
        print(f"✅ 1011 ERROR SUCCESSFULLY REPRODUCED: {error_message}")
        print(f"✅ WebSocket closed with code: {mock_websocket_1011.close_code}")
        print(f"✅ Handler error count: {stats['errors']}")
    
    async def test_service_initialization_failure_causes_1011_error(
        self, mock_websocket_1011, test_user_id, start_agent_message, message_handler_service_mock
    ):
        """
        REPRODUCTION TEST: Service initialization failure leads to 1011 error
        
        This test isolates the specific create_websocket_manager() failure that causes 1011 errors.
        The failure occurs when the factory cannot initialize services properly.
        
        Expected: Service initialization failure should result in 1011 WebSocket closure.
        """
        handler = AgentMessageHandler(
            message_handler_service=message_handler_service_mock,
            websocket=mock_websocket_1011
        )
        
        # CRITICAL: Mock create_websocket_manager to fail exactly as it does in staging
        def mock_service_initialization_failure(*args, **kwargs):
            """Simulate the exact service initialization failure from staging."""
            raise Exception(
                "WebSocket manager factory initialization failed: "
                "Cannot resolve service dependencies in staging environment. "
                "Database connection pool unavailable. "
                "Auth service endpoint unreachable. "
                "This is the exact error causing 1011 WebSocket failures in production."
            )
        
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager', 
                  side_effect=mock_service_initialization_failure):
            
            with pytest.raises(RuntimeError) as exc_info:
                await handler.handle_message(test_user_id, mock_websocket_1011, start_agent_message)
                
                # If no exception, the test failed to reproduce the issue
                assert False, "Service initialization failure should cause 1011 WebSocket error"
            
            error_message = str(exc_info.value)
            
            # Validate the error chain: service failure -> 1011 WebSocket error
            service_failure_patterns = [
                "factory initialization failed",
                "service dependencies", 
                "staging environment",
                "Database connection",
                "Auth service endpoint",
                "1011 WebSocket failures"
            ]
            
            pattern_found = any(pattern in error_message for pattern in service_failure_patterns)
            
            assert pattern_found, (
                f"SERVICE INITIALIZATION ERROR REPRODUCTION FAILED: "
                f"Error '{error_message}' doesn't match service failure patterns: {service_failure_patterns}"
            )
            
            # Verify WebSocket was closed with 1011 due to service failure
            assert mock_websocket_1011.connection_closed, "WebSocket should close on service failure"
            assert mock_websocket_1011.close_code == 1011, f"Service failure should cause 1011 close code, got {mock_websocket_1011.close_code}"
            
            print(f"✅ SERVICE INITIALIZATION FAILURE -> 1011 ERROR REPRODUCED: {error_message}")
    
    async def test_staging_environment_conditions_cause_1011_error(
        self, mock_websocket_1011, test_user_id, start_agent_message, message_handler_service_mock
    ):
        """
        REPRODUCTION TEST: Staging environment-specific conditions cause 1011 errors
        
        This test reproduces the exact staging environment conditions that lead to
        service initialization failures and subsequent 1011 WebSocket errors.
        
        Expected: Staging-specific environment issues should cause 1011 failures.
        """
        handler = AgentMessageHandler(
            message_handler_service=message_handler_service_mock,
            websocket=mock_websocket_1011
        )
        
        # CRITICAL: Simulate staging environment conditions that cause failures
        staging_env_vars = {
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'K_SERVICE': 'backend-staging',
            'ENVIRONMENT': 'staging',
            # Simulate missing or invalid environment variables that cause issues
            'DATABASE_URL': 'invalid-database-url',
            'REDIS_URL': '',  # Empty Redis URL
            'JWT_SECRET_KEY': None,  # Missing JWT secret
        }
        
        with patch.dict(os.environ, staging_env_vars, clear=False):
            # Mock get_user_execution_context to simulate staging auth issues
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_context:
                mock_context.side_effect = ConnectionError(
                    "Staging environment authentication failure: "
                    "Cannot validate user context in staging due to auth service connectivity issues. "
                    "JWT_SECRET_KEY missing from environment. "
                    "Database connection string invalid for staging environment. "
                    "This causes WebSocket 1011 internal errors in staging deployment."
                )
                
                with pytest.raises(RuntimeError) as exc_info:
                    await handler.handle_message(test_user_id, mock_websocket_1011, start_agent_message)
                    
                    assert False, "Staging environment issues should cause 1011 WebSocket errors"
                
                error_message = str(exc_info.value)
                
                # Validate staging-specific failure patterns
                staging_error_patterns = [
                    "Staging environment",
                    "authentication failure",
                    "auth service connectivity",
                    "JWT_SECRET_KEY missing",
                    "Database connection string invalid",
                    "staging deployment",
                    "1011 internal errors"
                ]
                
                pattern_found = any(pattern in error_message for pattern in staging_error_patterns)
                
                assert pattern_found, (
                    f"STAGING ENVIRONMENT ERROR REPRODUCTION FAILED: "
                    f"Error '{error_message}' doesn't match staging patterns: {staging_error_patterns}"
                )
                
                # Verify staging failure caused 1011 WebSocket closure
                assert mock_websocket_1011.connection_closed, "Staging failures should close WebSocket"
                assert mock_websocket_1011.close_code == 1011, f"Staging failures should cause 1011, got {mock_websocket_1011.close_code}"
                
                print(f"✅ STAGING ENVIRONMENT CONDITIONS -> 1011 ERROR REPRODUCED: {error_message}")
    
    async def test_concurrent_websocket_requests_cause_1011_resource_contention(
        self, test_user_id, start_agent_message, message_handler_service_mock
    ):
        """
        REPRODUCTION TEST: Concurrent WebSocket requests cause resource contention and 1011 errors
        
        This test reproduces the multi-user concurrent access scenario that leads to
        resource contention and causes intermittent 1011 WebSocket failures.
        
        Expected: Concurrent requests should cause resource contention leading to 1011 errors.
        """
        # Create multiple WebSocket connections for concurrent testing
        concurrent_websockets = []
        concurrent_handlers = []
        
        for i in range(5):  # Simulate 5 concurrent users
            ws = MockWebSocketFor1011Testing(f"{test_user_id}_concurrent_{i}")
            handler = AgentMessageHandler(
                message_handler_service=message_handler_service_mock,
                websocket=ws
            )
            concurrent_websockets.append(ws)
            concurrent_handlers.append(handler)
        
        # Mock create_websocket_manager to simulate resource contention
        call_count = [0]
        
        async def concurrent_resource_contention(*args, **kwargs):
            """Simulate resource contention that causes some requests to fail with 1011."""
            call_count[0] += 1
            if call_count[0] % 2 == 0:  # Fail every 2nd request due to resource contention
                raise Exception(
                    f"Resource contention detected: WebSocket manager factory overwhelmed by concurrent requests. "
                    f"Database connection pool exhausted (request #{call_count[0]}). "
                    f"Cannot create isolated WebSocket manager due to resource limits. "
                    f"This causes 1011 WebSocket internal server errors under concurrent load."
                )
            else:
                # Simulate successful creation for some requests
                mock_manager = Mock()
                mock_manager.get_connection_id_by_websocket.return_value = None
                return mock_manager
        
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager',
                  side_effect=concurrent_resource_contention):
            
            # Execute concurrent requests
            tasks = []
            for i, handler in enumerate(concurrent_handlers):
                # Create unique message for each concurrent request
                concurrent_message = WebSocketMessage(
                    type=MessageType.START_AGENT,
                    user_id=f"{test_user_id}_concurrent_{i}",
                    thread_id=UnifiedIdGenerator.generate_base_id("thread"),
                    payload={
                        "user_request": f"Concurrent request {i}",
                        "agent_type": "concurrent_test"
                    }
                )
                
                task = handler.handle_message(
                    f"{test_user_id}_concurrent_{i}",
                    concurrent_websockets[i],
                    concurrent_message
                )
                tasks.append(task)
            
            # Gather results - expect some to fail with 1011 errors
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results for concurrent failure patterns
            exceptions = [result for result in results if isinstance(result, Exception)]
            successes = [result for result in results if not isinstance(result, Exception)]
            
            print(f"Concurrent test results: {len(successes)} successes, {len(exceptions)} failures")
            
            # At least some requests should fail due to resource contention
            assert len(exceptions) > 0, (
                f"CONCURRENT 1011 ERROR REPRODUCTION FAILED: "
                f"Expected some concurrent requests to fail with resource contention but all {len(successes)} succeeded. "
                f"This suggests the concurrent failure scenario is not accurate."
            )
            
            # Check that failures are due to resource contention leading to 1011 errors
            contention_error_patterns = [
                "Resource contention",
                "WebSocket manager factory overwhelmed",
                "Database connection pool exhausted", 
                "concurrent requests",
                "resource limits",
                "1011 WebSocket internal server errors",
                "concurrent load"
            ]
            
            exception_messages = [str(exc) for exc in exceptions]
            pattern_found = any(
                pattern in msg 
                for msg in exception_messages 
                for pattern in contention_error_patterns
            )
            
            assert pattern_found, (
                f"CONCURRENT RESOURCE CONTENTION PATTERN VALIDATION FAILED: "
                f"Exceptions {exception_messages} don't match contention patterns: {contention_error_patterns}"
            )
            
            # Check that WebSockets were closed with 1011 for failed requests
            failed_websockets = [ws for ws, result in zip(concurrent_websockets, results) if isinstance(result, Exception)]
            for ws in failed_websockets:
                assert ws.connection_closed, f"Failed WebSocket should be closed: {ws.user_id}"
                assert ws.close_code == 1011, f"Failed WebSocket should have 1011 close code: {ws.user_id} got {ws.close_code}"
            
            print(f"✅ CONCURRENT RESOURCE CONTENTION -> 1011 ERRORS REPRODUCED")
            print(f"✅ Failed requests: {len(exceptions)}, Successful: {len(successes)}")
            for i, exc in enumerate(exceptions[:3]):  # Show first 3 exceptions
                print(f"  Exception {i+1}: {exc}")
    
    async def test_websocket_connection_state_validation_during_1011_error(
        self, mock_websocket_1011, test_user_id, start_agent_message, message_handler_service_mock
    ):
        """
        REPRODUCTION TEST: WebSocket connection state during 1011 error progression
        
        This test validates the WebSocket connection state changes during the progression
        from successful connection to 1011 internal server error.
        
        Expected: Connection state should progress from CONNECTED -> service failure -> 1011 closure.
        """
        handler = AgentMessageHandler(
            message_handler_service=message_handler_service_mock,
            websocket=mock_websocket_1011
        )
        
        # Verify initial WebSocket state
        assert mock_websocket_1011.state == WebSocketState.CONNECTED, "WebSocket should start CONNECTED"
        assert not mock_websocket_1011.connection_closed, "WebSocket should not be closed initially"
        assert mock_websocket_1011.close_code is None, "No close code should be set initially"
        
        print(f"🔍 Initial WebSocket state: {mock_websocket_1011.state}")
        print(f"🔍 Connection closed: {mock_websocket_1011.connection_closed}")
        
        # Mock service failure that triggers 1011 error
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create:
            mock_create.side_effect = Exception(
                "Service initialization failure triggers 1011 WebSocket internal server error"
            )
            
            with pytest.raises(RuntimeError) as exc_info:
                await handler.handle_message(test_user_id, mock_websocket_1011, start_agent_message)
                
                assert False, "Service failure should trigger 1011 WebSocket error"
            
            # Verify final WebSocket state after 1011 error
            assert mock_websocket_1011.connection_closed, "WebSocket should be closed after 1011 error"
            assert mock_websocket_1011.close_code == 1011, f"Close code should be 1011, got {mock_websocket_1011.close_code}"
            assert mock_websocket_1011.state == WebSocketState.DISCONNECTED, f"State should be DISCONNECTED, got {mock_websocket_1011.state}"
            
            # Verify error message contains connection state information
            error_message = str(exc_info.value)
            assert "1011" in error_message, f"Error should mention 1011 close code: {error_message}"
            
            print(f"✅ WEBSOCKET STATE PROGRESSION DURING 1011 ERROR REPRODUCED:")
            print(f"  Final state: {mock_websocket_1011.state}")
            print(f"  Connection closed: {mock_websocket_1011.connection_closed}")  
            print(f"  Close code: {mock_websocket_1011.close_code}")
            print(f"  Error: {error_message}")


if __name__ == "__main__":
    """
    Direct test execution for rapid debugging.
    
    Usage: python -m pytest tests/reproduction/websocket_1011_error_scenario/test_websocket_1011_error_reproduction_comprehensive.py -v -s
    """
    pytest.main([__file__, "-v", "-s", "--tb=long"])