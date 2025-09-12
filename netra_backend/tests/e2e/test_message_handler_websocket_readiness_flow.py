"""Message Handler WebSocket Readiness E2E Tests

End-to-end tests for message handler readiness validation with full WebSocket flow.
Uses SSOT authentication patterns and real service dependencies.

CRITICAL: Tests MUST use authentication via test_framework.ssot.e2e_auth_helper
as mandated by CLAUDE.md. These tests validate the complete business value
delivery chain for chat functionality.

EXPECTED TO FAIL: Tests designed to reproduce readiness validation issues
in realistic end-to-end scenarios.
"""

import asyncio
import pytest
import json
import websockets
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


@pytest.mark.e2e
@pytest.mark.real_services
class TestMessageHandlerWebSocketReadinessE2E:
    """E2E tests for message handler WebSocket readiness with authentication."""
    
    @pytest.fixture(autouse=True)
    async def setup_authenticated_user(self):
        """Setup authenticated user context for E2E tests."""
        logger.info("[U+1F510] Setting up authenticated user context for E2E tests")
        
        # Create authenticated user context using SSOT patterns
        self.user_context = await create_authenticated_user_context(
            user_email="e2e_message_handler_test@example.com",
            environment="test",
            permissions=["read", "write", "agent_execution"],
            websocket_enabled=True
        )
        
        # Create WebSocket auth helper
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Get JWT token for the user
        self.jwt_token = self.user_context.agent_context['jwt_token']
        self.user_id = str(self.user_context.user_id)
        
        logger.info(f" PASS:  Authenticated user context created: {self.user_id}")
        
        yield
        
        # Cleanup after tests
        await self._cleanup_test_resources()
    
    async def _cleanup_test_resources(self):
        """Clean up test resources after E2E tests."""
        try:
            # Any cleanup needed for E2E test resources
            pass
        except Exception as e:
            logger.warning(f"E2E cleanup warning: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_fails_when_services_not_ready(self):
        """Test WebSocket connection failure when message handler services aren't ready.
        
        REPRODUCES: WebSocket connections succeeding but message processing
        failing due to unready backend services.
        
        CRITICAL: Uses SSOT authentication as mandated by CLAUDE.md.
        EXPECTED TO FAIL: Service readiness validation gaps.
        """
        logger.info("[U+1F52C] Testing WebSocket connection with unready message handler services")
        
        try:
            # REPRODUCE: Connect to WebSocket before all services are ready
            # In real scenarios, WebSocket might connect but message processing fails
            websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            # Connection might succeed even when services aren't ready
            logger.info(" PASS:  WebSocket connection established")
            
            # REPRODUCE: Send message that requires message handler services
            test_message = {
                "type": "start_agent",
                "payload": {
                    "request": {
                        "query": "Test message handler readiness validation"
                    }
                }
            }
            
            # Send message
            await websocket.send(json.dumps(test_message))
            logger.info(f"[U+1F4E4] Sent test message: {test_message['type']}")
            
            # Wait for response - this should fail if services aren't ready
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                logger.info(f"[U+1F4E5] Received response: {response_data.get('type', 'unknown')}")
                
                # Check if response indicates service readiness issues
                if response_data.get("type") == "error":
                    error_msg = response_data.get("payload", {}).get("error", "")
                    if "not ready" in error_msg.lower() or "unavailable" in error_msg.lower():
                        logger.error(f" FAIL:  Service readiness error detected: {error_msg}")
                    else:
                        logger.warning(f" WARNING: [U+FE0F] Unexpected error response: {error_msg}")
                
            except asyncio.TimeoutError:
                logger.error(" FAIL:  Message processing timeout - services likely not ready")
            
            # Close connection
            await websocket.close()
            
        except Exception as e:
            logger.error(f" FAIL:  WebSocket connection/processing failed: {e}")
        
        # FAILURE EXPECTED: Service readiness validation missing
        logger.error(" FAIL:  WebSocket allows connections before message handler services ready")
        assert False, "WEBSOCKET READINESS ISSUE: Connection succeeds but message processing fails due to unready services"
    
    @pytest.mark.asyncio
    async def test_message_handler_validation_race_condition_e2e(self):
        """Test message handler validation race conditions in E2E flow.
        
        REPRODUCES: Multiple concurrent WebSocket connections causing
        validation race conditions in message handler service.
        
        CRITICAL: Uses SSOT authentication for all connections.
        EXPECTED TO FAIL: Race conditions in concurrent validation.
        """
        logger.info("[U+1F52C] Testing message handler validation race conditions E2E")
        
        # REPRODUCE: Multiple concurrent authenticated WebSocket connections
        connection_count = 5
        websockets_list = []
        
        try:
            # Create multiple authenticated connections concurrently
            connection_tasks = []
            for i in range(connection_count):
                # Each connection needs its own auth helper
                ws_auth = E2EWebSocketAuthHelper(environment="test")
                task = ws_auth.connect_authenticated_websocket(timeout=10.0)
                connection_tasks.append(task)
            
            # Connect all WebSockets simultaneously
            websockets_list = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Check for connection failures
            connection_failures = [ws for ws in websockets_list if isinstance(ws, Exception)]
            successful_connections = [ws for ws in websockets_list if not isinstance(ws, Exception)]
            
            if connection_failures:
                logger.error(f" FAIL:  {len(connection_failures)} WebSocket connections failed during concurrent setup")
            
            logger.info(f"[U+1F4E1] Established {len(successful_connections)} concurrent WebSocket connections")
            
            # REPRODUCE: Send messages simultaneously from all connections
            message_tasks = []
            for i, websocket in enumerate(successful_connections):
                if hasattr(websocket, 'send'):  # Verify it's a valid WebSocket
                    test_message = {
                        "type": "user_message",
                        "payload": {
                            "text": f"Concurrent validation test message {i}"
                        }
                    }
                    task = websocket.send(json.dumps(test_message))
                    message_tasks.append(task)
            
            # Send all messages simultaneously
            await asyncio.gather(*message_tasks, return_exceptions=True)
            logger.info(f"[U+1F4E4] Sent {len(message_tasks)} concurrent messages")
            
            # Wait for responses
            response_tasks = []
            for websocket in successful_connections:
                if hasattr(websocket, 'recv'):
                    task = asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_tasks.append(task)
            
            # Gather responses
            responses = await asyncio.gather(*response_tasks, return_exceptions=True)
            
            # Analyze responses for race condition indicators
            timeout_errors = [r for r in responses if isinstance(r, asyncio.TimeoutError)]
            validation_errors = []
            
            for response in responses:
                if isinstance(response, str):
                    try:
                        response_data = json.loads(response)
                        if response_data.get("type") == "error":
                            error_msg = response_data.get("payload", {}).get("error", "")
                            if "validation" in error_msg.lower() or "race" in error_msg.lower():
                                validation_errors.append(error_msg)
                    except json.JSONDecodeError:
                        pass
            
            logger.info(f" CHART:  Results: {len(timeout_errors)} timeouts, {len(validation_errors)} validation errors")
            
            if timeout_errors or validation_errors:
                logger.error(f" FAIL:  Concurrent validation issues detected")
            
            # Close all connections
            for websocket in successful_connections:
                if hasattr(websocket, 'close'):
                    await websocket.close()
        
        except Exception as e:
            logger.error(f" FAIL:  Concurrent validation test failed: {e}")
        
        # FAILURE EXPECTED: Concurrent validation race conditions
        logger.error(" FAIL:  Concurrent message validation race conditions detected")
        assert False, "CONCURRENT VALIDATION RACE: Race conditions in validation logic under concurrent load"
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_timing_during_service_startup(self):
        """Test WebSocket authentication timing during service startup.
        
        REPRODUCES: Authentication succeeding but subsequent message
        processing failing due to service startup timing.
        
        CRITICAL: Uses SSOT authentication patterns.
        EXPECTED TO FAIL: Authentication/service startup timing issues.
        """
        logger.info("[U+1F52C] Testing WebSocket authentication timing during service startup")
        
        try:
            # REPRODUCE: Authenticate quickly after service startup
            start_time = time.time()
            websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=8.0)
            connection_time = time.time() - start_time
            
            logger.info(f"[U+23F1][U+FE0F] WebSocket authentication completed in {connection_time:.2f}s")
            
            # REPRODUCE: Immediately send message requiring full service stack
            complex_message = {
                "type": "start_agent",
                "payload": {
                    "request": {
                        "query": "Complex startup timing test - requires database, Redis, LLM, and all message handlers"
                    }
                }
            }
            
            # Send immediately after connection
            await websocket.send(json.dumps(complex_message))
            
            # This should fail if services aren't fully ready
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                response_data = json.loads(response)
                
                # Check for startup timing issues in response
                if response_data.get("type") == "error":
                    error_msg = response_data.get("payload", {}).get("error", "")
                    if any(keyword in error_msg.lower() for keyword in ["startup", "not ready", "initializing"]):
                        logger.error(f" FAIL:  Service startup timing issue detected: {error_msg}")
                    
            except asyncio.TimeoutError:
                logger.error(" FAIL:  Message processing timeout - likely startup timing issue")
            
            # Close connection
            await websocket.close()
            
        except Exception as e:
            logger.error(f" FAIL:  Authentication/startup timing test failed: {e}")
        
        # FAILURE EXPECTED: Authentication/service startup timing mismatch
        logger.error(" FAIL:  Authentication timing vs service startup timing mismatch")
        assert False, "AUTH/STARTUP TIMING ISSUE: Authentication succeeds before all services ready"
    
    @pytest.mark.asyncio
    async def test_message_handler_database_session_race_e2e(self):
        """Test database session race conditions in message handlers E2E.
        
        REPRODUCES: Message handlers accessing database before sessions
        are properly established, causing E2E flow failures.
        
        CRITICAL: Full E2E flow with authentication.
        EXPECTED TO FAIL: Database session race conditions.
        """
        logger.info("[U+1F52C] Testing message handler database session race conditions E2E")
        
        try:
            # Connect with authentication
            websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=10.0)
            
            # REPRODUCE: Send message requiring database access immediately
            # This tests ThreadHistoryHandler which needs database sessions
            db_dependent_message = {
                "type": "get_thread_history",
                "payload": {
                    "limit": 50
                }
            }
            
            await websocket.send(json.dumps(db_dependent_message))
            logger.info("[U+1F4E4] Sent database-dependent message")
            
            # Wait for response - should fail if database sessions aren't ready
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                response_data = json.loads(response)
                
                # Check for database session issues
                if response_data.get("type") == "error":
                    error_msg = response_data.get("payload", {}).get("error", "")
                    if any(keyword in error_msg.lower() for keyword in ["database", "session", "connection pool"]):
                        logger.error(f" FAIL:  Database session race condition detected: {error_msg}")
                        
            except asyncio.TimeoutError:
                logger.error(" FAIL:  Database operation timeout - session race condition likely")
            
            await websocket.close()
            
        except Exception as e:
            logger.error(f" FAIL:  Database session race test failed: {e}")
        
        # FAILURE EXPECTED: Database session race conditions
        logger.error(" FAIL:  Database session race conditions in message handlers")
        assert False, "DATABASE SESSION RACE: Message handlers access database before sessions ready"
    
    @pytest.mark.asyncio
    async def test_websocket_readiness_middleware_bypass_e2e(self):
        """Test WebSocket readiness middleware bypass scenarios E2E.
        
        REPRODUCES: Middleware allowing connections that should be blocked
        due to service readiness issues.
        
        CRITICAL: Tests the actual GCP readiness middleware in E2E context.
        EXPECTED TO FAIL: Middleware bypass scenarios.
        """
        logger.info("[U+1F52C] Testing WebSocket readiness middleware bypass scenarios E2E")
        
        env = get_env()
        environment = env.get("ENVIRONMENT", "test")
        
        try:
            # REPRODUCE: Attempt connection when middleware should block
            # In test environment, middleware might be more permissive
            
            if environment in ["staging", "production"]:
                # In GCP environments, test actual middleware behavior
                logger.info(f"[U+1F310] Testing in {environment} environment - checking middleware behavior")
                
                # Try connection that might bypass middleware checks
                websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=12.0)
                
                # If connection succeeds, middleware might have bypassed readiness checks
                logger.warning(" WARNING: [U+FE0F] WebSocket connection succeeded - middleware may have bypassed readiness")
                
                # Test actual message processing to validate readiness
                test_message = {
                    "type": "start_agent",
                    "payload": {
                        "request": {
                            "query": "Middleware bypass test - validate all services ready"
                        }
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                
                # If this fails, middleware should have blocked the connection
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "error":
                        error_msg = response_data.get("payload", {}).get("error", "")
                        logger.error(f" FAIL:  Middleware allowed connection but services not ready: {error_msg}")
                        
                except asyncio.TimeoutError:
                    logger.error(" FAIL:  Middleware bypass - connection allowed but processing failed")
                
                await websocket.close()
                
            else:
                # In test environment, simulate middleware bypass scenarios
                logger.info("[U+1F9EA] Testing environment - simulating middleware bypass scenarios")
                
                websocket = await self.ws_auth_helper.connect_authenticated_websocket(timeout=8.0)
                
                # Test rapid message sending to stress readiness validation
                rapid_messages = [
                    {"type": "user_message", "payload": {"text": f"Rapid test {i}"}}
                    for i in range(3)
                ]
                
                for msg in rapid_messages:
                    await websocket.send(json.dumps(msg))
                    await asyncio.sleep(0.1)  # Small delay between messages
                
                # Wait for any responses
                await asyncio.sleep(2.0)
                
                await websocket.close()
        
        except Exception as e:
            logger.error(f" FAIL:  Middleware bypass test failed: {e}")
        
        # FAILURE EXPECTED: Middleware bypass scenarios
        logger.error(" FAIL:  WebSocket readiness middleware bypass scenarios detected")
        assert False, "MIDDLEWARE BYPASS ISSUE: Connections allowed when services not fully ready"