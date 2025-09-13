
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
MISSION CRITICAL: WebSocket ConnectionHandler Golden Path Test Suite.

This test suite validates the complete authenticated chat flow that is currently
broken due to ConnectionHandler issues identified in the Five WHYs analysis.

CRITICAL: This is the golden path that customers use - if this breaks, the entire
product value proposition fails for authenticated users.

Business Value:
- Validates end-to-end authenticated chat experience works
- Catches golden path failures before they reach customers
- Ensures WebSocket events are properly sent during agent execution  
- Validates proper authentication integration with WebSocket connections
- Prevents customer-facing failures in the core product flow

Test Strategy:
- Use REAL authentication via e2e_auth_helper.py (MANDATORY)
- Test complete flow: auth  ->  connect  ->  send message  ->  receive response
- Validate all WebSocket events are sent during agent processing
- Use real services (no mocks) to catch integration issues
- Test with the actual problematic user ID from production logs

Expected Test Behavior:
- CURRENT STATE: Tests FAIL due to ConnectionHandler silent failures
- AFTER FIX: Tests PASS with complete golden path working end-to-end

ULTRA CRITICAL: These tests MUST use authentication - no exceptions.
"""

import asyncio
import json
import logging
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)

# MISSION CRITICAL configuration for golden path testing
GOLDEN_PATH_CONFIG = {
    'problematic_user_id': '105945141827451681156',  # Actual user from production logs
    'connection_timeout': 20.0,  # Allow time for authentication
    'agent_response_timeout': 45.0,  # Allow time for agent processing
    'required_websocket_events': {
        'agent_started',
        'agent_completed'  
    },
    'optional_websocket_events': {
        'agent_thinking',
        'tool_executing', 
        'tool_completed'
    }
}


class TestWebSocketConnectionHandlerGoldenPath(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    MISSION CRITICAL: Tests for the complete authenticated chat golden path.
    
    This test suite validates that authenticated users can successfully:
    1. Authenticate via JWT/OAuth
    2. Establish WebSocket connection
    3. Send agent execution requests
    4. Receive proper WebSocket events during processing
    5. Get complete agent responses
    6. Experience no silent failures or connection drops
    
    CRITICAL: All tests MUST use real authentication - this is non-negotiable.
    """
    
    def setup_method(self):
        """Set up each test with authenticated user context."""
        super().setup_method()
        self.env = get_env()
        
        # Determine environment - prefer staging for golden path tests
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "staging"))
        logger.info(f"Setting up golden path tests for environment: {self.test_environment}")
        
        # CRITICAL: Initialize authenticated WebSocket helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        # Track connections for cleanup
        self.active_connections: List[websockets.WebSocketServerProtocol] = []
        
        # Track received events for validation
        self.websocket_events_received: List[Dict[str, Any]] = []
        self.agent_responses_received: List[Dict[str, Any]] = []
        
        # Golden path metrics
        self.golden_path_metrics = {
            'test_start_time': time.time(),
            'authentication_time': 0.0,
            'connection_time': 0.0,
            'first_response_time': 0.0,
            'total_response_time': 0.0,
            'events_received_count': 0,
            'successful_completion': False
        }
        
    def teardown_method(self):
        """Clean up connections after each test."""
        # Close WebSocket connections
        if self.active_connections:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for ws in self.active_connections:
                    if not ws.closed:
                        loop.run_until_complete(ws.close())
            except Exception as e:
                logger.warning(f"Error closing connections in teardown: {e}")
            finally:
                loop.close()
                
        self.active_connections.clear()
        self.websocket_events_received.clear()
        self.agent_responses_received.clear()
        super().teardown_method()
        
    async def _create_authenticated_connection(self) -> websockets.WebSocketServerProtocol:
        """
        Create authenticated WebSocket connection using SSOT patterns.
        
        CRITICAL: This MUST use real authentication - no mocking allowed.
        
        Returns:
            Authenticated WebSocket connection
            
        Raises:
            Exception: If authentication or connection fails
        """
        auth_start = time.time()
        
        try:
            # CRITICAL: Use real authentication helper
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=GOLDEN_PATH_CONFIG['connection_timeout']
            )
            
            self.active_connections.append(websocket)
            
            # Record authentication timing
            self.golden_path_metrics['authentication_time'] = time.time() - auth_start
            self.golden_path_metrics['connection_time'] = time.time() - auth_start
            
            logger.info(f" PASS:  Authenticated WebSocket connection established in {self.golden_path_metrics['connection_time']:.2f}s")
            
            return websocket
            
        except Exception as e:
            logger.error(f" FAIL:  Failed to create authenticated WebSocket connection: {e}")
            raise
            
    async def _send_agent_request(self, websocket: websockets.WebSocketServerProtocol, 
                                 agent_name: str = "data_analysis_agent") -> str:
        """
        Send agent execution request through WebSocket.
        
        Args:
            websocket: Authenticated WebSocket connection
            agent_name: Name of agent to execute
            
        Returns:
            Request ID for tracking responses
        """
        request_id = f"golden-path-{int(time.time())}-{agent_name}"
        
        agent_request = {
            "type": "agent_execution",
            "agent_name": agent_name,
            "message": "Please analyze the current system status and provide recommendations for optimization.",
            "request_id": request_id,
            "user_id": GOLDEN_PATH_CONFIG['problematic_user_id'],
            "thread_id": f"thread-{request_id}",
            "metadata": {
                "test_mode": True,
                "golden_path_test": True,
                "environment": self.test_environment,
                "priority": "high"
            }
        }
        
        logger.info(f"[U+1F4E4] Sending agent request: {agent_name} (request_id: {request_id})")
        
        await websocket.send(json.dumps(agent_request))
        
        return request_id
        
    async def _collect_websocket_responses(self, websocket: websockets.WebSocketServerProtocol,
                                         request_id: str,
                                         timeout: float) -> Dict[str, Any]:
        """
        Collect WebSocket responses until completion or timeout.
        
        Args:
            websocket: WebSocket connection to listen on
            request_id: Request ID to match responses
            timeout: Maximum time to wait for responses
            
        Returns:
            Dict with response collection results
        """
        start_time = time.time()
        first_response_received = False
        completion_received = False
        
        required_events = set(GOLDEN_PATH_CONFIG['required_websocket_events'])
        received_events = set()
        
        logger.info(f"[U+1F442] Listening for WebSocket responses (timeout: {timeout}s)")
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Wait for response with short interval timeout
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    # Record first response timing
                    if not first_response_received:
                        self.golden_path_metrics['first_response_time'] = time.time() - start_time
                        first_response_received = True
                        logger.info(f"[U+23F1][U+FE0F] First response received in {self.golden_path_metrics['first_response_time']:.2f}s")
                    
                    # Parse response
                    try:
                        response_data = json.loads(response_text)
                        self.websocket_events_received.append(response_data)
                        
                        # Check response type
                        response_type = response_data.get('type', 'unknown')
                        response_request_id = response_data.get('request_id', '')
                        
                        # Only process responses for our request
                        if response_request_id == request_id or response_type in ['agent_started', 'agent_completed']:
                            logger.info(f"  [U+1F4E1] Received: {response_type}")
                            
                            # Track events received
                            if response_type in GOLDEN_PATH_CONFIG['required_websocket_events'] or \
                               response_type in GOLDEN_PATH_CONFIG['optional_websocket_events']:
                                received_events.add(response_type)
                                
                            # Check for completion
                            if response_type in ['agent_completed', 'agent_response']:
                                completion_received = True
                                self.agent_responses_received.append(response_data)
                                logger.info(" PASS:  Agent execution completed")
                                break
                                
                        else:
                            logger.debug(f"  [U+1F4E1] Received unrelated: {response_type} (request_id: {response_request_id})")
                            
                    except json.JSONDecodeError:
                        logger.warning(f"   WARNING: [U+FE0F] Received non-JSON response: {response_text[:100]}...")
                        
                except asyncio.TimeoutError:
                    # No message in this interval - continue waiting
                    logger.debug("  [U+23F3] Waiting for more responses...")
                    continue
                    
        except Exception as e:
            logger.error(f"Error collecting WebSocket responses: {e}")
            
        # Record final timing
        self.golden_path_metrics['total_response_time'] = time.time() - start_time
        self.golden_path_metrics['events_received_count'] = len(self.websocket_events_received)
        self.golden_path_metrics['successful_completion'] = completion_received
        
        return {
            'first_response_received': first_response_received,
            'completion_received': completion_received,
            'required_events_received': required_events.intersection(received_events),
            'all_events_received': received_events,
            'missing_required_events': required_events - received_events,
            'total_responses': len(self.websocket_events_received),
            'response_time': self.golden_path_metrics['total_response_time']
        }
        
    @pytest.mark.mission_critical
    @pytest.mark.e2e
    @pytest.mark.auth_required
    async def test_authenticated_user_complete_chat_flow_gcp_staging(self):
        """
        MISSION CRITICAL: Tests complete authenticated chat flow in real environment.
        
        This is THE golden path test that validates the entire customer experience:
        1. Real authentication (JWT/OAuth)
        2. Real WebSocket connection
        3. Real agent execution request
        4. Real WebSocket events during processing
        5. Real agent response received
        
        CRITICAL: This test MUST fail in current state due to ConnectionHandler
        silent failures that prevent users from receiving agent responses.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - User authenticates but gets no agent responses
        - AFTER FIX: PASS - Complete golden path works end-to-end
        """
        logger.info(" ALERT:  MISSION CRITICAL: Testing complete authenticated chat golden path")
        logger.info(f"Environment: {self.test_environment}")
        logger.info(f"Target user ID: {GOLDEN_PATH_CONFIG['problematic_user_id']}")
        
        # Step 1: Create authenticated WebSocket connection
        logger.info("Step 1: Creating authenticated WebSocket connection")
        websocket = await self._create_authenticated_connection()
        
        # Step 2: Send agent execution request  
        logger.info("Step 2: Sending agent execution request")
        request_id = await self._send_agent_request(websocket, "data_analysis_agent")
        
        # Step 3: Collect responses and WebSocket events
        logger.info("Step 3: Collecting WebSocket responses and events")
        results = await self._collect_websocket_responses(
            websocket, 
            request_id, 
            GOLDEN_PATH_CONFIG['agent_response_timeout']
        )
        
        # Step 4: Analyze and validate results
        logger.info("Step 4: Validating golden path results")
        self._log_golden_path_metrics()
        
        # CRITICAL ASSERTION 1: Must receive some responses (not silent failure)
        assert results['total_responses'] > 0, (
            f" FAIL:  GOLDEN PATH FAILURE: No WebSocket responses received from agent execution. "
            f"This indicates ConnectionHandler silent failure where the request is processed "
            f"but no responses are sent back to the authenticated user. "
            f"Customer experience is completely broken - users authenticate successfully "
            f"but receive no responses from AI agents. "
            f"Request ID: {request_id}, User ID: {GOLDEN_PATH_CONFIG['problematic_user_id']}"
        )
        
        # CRITICAL ASSERTION 2: Must receive first response within reasonable time
        assert results['first_response_received'], (
            f" FAIL:  GOLDEN PATH FAILURE: No first response received within "
            f"{GOLDEN_PATH_CONFIG['agent_response_timeout']}s timeout. "
            f"This indicates WebSocket connection or agent execution failure. "
            f"Customers will experience timeout and assume service is down."
        )
        
        # CRITICAL ASSERTION 3: Must receive required WebSocket events
        missing_events = results['missing_required_events']
        assert len(missing_events) == 0, (
            f" FAIL:  GOLDEN PATH FAILURE: Missing required WebSocket events: {missing_events}. "
            f"Received events: {results['all_events_received']}. "
            f"This indicates the WebSocket notification system is not working properly. "
            f"Users won't see agent activity indicators and will think the system is frozen."
        )
        
        # CRITICAL ASSERTION 4: Must receive completion notification
        assert results['completion_received'], (
            f" FAIL:  GOLDEN PATH FAILURE: No agent completion notification received. "
            f"Agent may have failed to execute or ConnectionHandler dropped the completion response. "
            f"Users will never know if their request was processed successfully. "
            f"Total responses: {results['total_responses']}, "
            f"Events: {results['all_events_received']}"
        )
        
        # CRITICAL ASSERTION 5: Performance must be acceptable
        total_time = self.golden_path_metrics['total_response_time']
        assert total_time < GOLDEN_PATH_CONFIG['agent_response_timeout'] * 0.8, (
            f" FAIL:  GOLDEN PATH PERFORMANCE FAILURE: Total response time {total_time:.1f}s "
            f"exceeds acceptable threshold ({GOLDEN_PATH_CONFIG['agent_response_timeout'] * 0.8:.1f}s). "
            f"This indicates performance issues that will frustrate customers."
        )
        
        # Success logging
        logger.info(" PASS:  GOLDEN PATH SUCCESS: Complete authenticated chat flow working")
        logger.info(f"   - Total responses: {results['total_responses']}")
        logger.info(f"   - Events received: {results['all_events_received']}")
        logger.info(f"   - Response time: {total_time:.2f}s")
        logger.info(f"   - Authentication time: {self.golden_path_metrics['authentication_time']:.2f}s")
        
        # Mark success in metrics
        self.golden_path_metrics['successful_completion'] = True
        
    @pytest.mark.mission_critical
    @pytest.mark.e2e
    @pytest.mark.auth_required  
    async def test_multiple_concurrent_authenticated_users_golden_path(self):
        """
        MISSION CRITICAL: Tests golden path with multiple concurrent authenticated users.
        
        This validates that the ConnectionHandler resource management issues
        don't prevent multiple users from having successful chat experiences simultaneously.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - Resource accumulation causes failures for later users
        - AFTER FIX: PASS - All concurrent users get proper responses
        """
        logger.info(" ALERT:  MISSION CRITICAL: Testing concurrent authenticated users golden path")
        
        num_concurrent_users = 3  # Start conservative for mission critical test
        concurrent_results = []
        
        async def single_user_golden_path(user_index: int) -> Dict[str, Any]:
            """Execute golden path for a single user."""
            try:
                # Create unique user context
                user_context = await create_authenticated_user_context(
                    user_email=f"golden_path_user_{user_index}@test.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                # Create authenticated connection
                auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
                websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
                
                # Send agent request
                request_id = f"concurrent-{user_index}-{int(time.time())}"
                agent_request = {
                    "type": "agent_execution",
                    "agent_name": "data_analysis_agent",
                    "message": f"Concurrent user {user_index} requesting analysis",
                    "request_id": request_id,
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id)
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect responses (shorter timeout for concurrent test)
                responses = []
                start_time = time.time()
                timeout = 30.0
                
                while time.time() - start_time < timeout:
                    try:
                        response_text = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response_text)
                        responses.append(response_data)
                        
                        # Check for completion
                        if response_data.get('type') in ['agent_completed', 'agent_response']:
                            break
                            
                    except (asyncio.TimeoutError, json.JSONDecodeError):
                        continue
                        
                # Close connection
                await websocket.close()
                
                return {
                    'user_index': user_index,
                    'success': len(responses) > 0,
                    'responses_count': len(responses),
                    'response_time': time.time() - start_time,
                    'user_id': str(user_context.user_id),
                    'error': None
                }
                
            except Exception as e:
                logger.error(f"User {user_index} golden path failed: {e}")
                return {
                    'user_index': user_index,
                    'success': False,
                    'responses_count': 0,
                    'response_time': 0,
                    'user_id': None,
                    'error': str(e)
                }
                
        # Execute concurrent golden paths
        logger.info(f"Executing {num_concurrent_users} concurrent golden paths")
        
        tasks = [single_user_golden_path(i) for i in range(num_concurrent_users)]
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_users = [r for r in concurrent_results if isinstance(r, dict) and r.get('success')]
        failed_users = [r for r in concurrent_results if isinstance(r, dict) and not r.get('success')]
        exception_users = [r for r in concurrent_results if not isinstance(r, dict)]
        
        success_rate = len(successful_users) / num_concurrent_users
        
        logger.info(f"Concurrent golden path results:")
        logger.info(f"  - Successful users: {len(successful_users)}/{num_concurrent_users}")
        logger.info(f"  - Failed users: {len(failed_users)}")
        logger.info(f"  - Exception users: {len(exception_users)}")
        logger.info(f"  - Success rate: {success_rate:.1%}")
        
        # Log details for failed users
        for failed_user in failed_users:
            logger.error(f"  - User {failed_user['user_index']} failed: {failed_user.get('error', 'Unknown error')}")
            
        # CRITICAL ASSERTIONS
        
        # 1. All users should succeed (no resource exhaustion)
        assert success_rate >= 0.9, (
            f" FAIL:  CONCURRENT GOLDEN PATH FAILURE: Success rate {success_rate:.1%} too low. "
            f"Expected at least 90% success rate for concurrent authenticated users. "
            f"This indicates resource management issues or connection handling failures. "
            f"Failed users: {len(failed_users)}, Exception users: {len(exception_users)}"
        )
        
        # 2. No user should hit resource limits
        resource_limit_errors = [
            r for r in failed_users 
            if r.get('error') and ('maximum' in r['error'].lower() or '20' in r['error'])
        ]
        
        assert len(resource_limit_errors) == 0, (
            f" FAIL:  RESOURCE LIMIT FAILURE: {len(resource_limit_errors)} users hit resource limits. "
            f"This indicates WebSocket manager cleanup is not working properly. "
            f"Sample errors: {[r['error'] for r in resource_limit_errors[:2]]}"
        )
        
        # 3. Performance should be consistent across users
        response_times = [r['response_time'] for r in successful_users]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            assert max_response_time < 60.0, (
                f" FAIL:  PERFORMANCE FAILURE: Max response time {max_response_time:.1f}s too high. "
                f"Average: {avg_response_time:.1f}s. This indicates performance degradation "
                f"under concurrent load."
            )
            
        logger.info(" PASS:  CONCURRENT GOLDEN PATH SUCCESS: All users received proper responses")
        
    def _log_golden_path_metrics(self):
        """Log detailed golden path performance metrics."""
        metrics = self.golden_path_metrics
        
        logger.info(" CHART:  Golden Path Metrics:")
        logger.info(f"  - Authentication time: {metrics['authentication_time']:.2f}s")
        logger.info(f"  - Connection time: {metrics['connection_time']:.2f}s")
        logger.info(f"  - First response time: {metrics['first_response_time']:.2f}s")
        logger.info(f"  - Total response time: {metrics['total_response_time']:.2f}s")
        logger.info(f"  - Events received: {metrics['events_received_count']}")
        logger.info(f"  - Successful completion: {metrics['successful_completion']}")
        
        # Performance evaluation
        if metrics['total_response_time'] > 0:
            if metrics['total_response_time'] < 10.0:
                logger.info("[U+1F680] EXCELLENT: Response time under 10s")
            elif metrics['total_response_time'] < 20.0:
                logger.info(" PASS:  GOOD: Response time under 20s")
            elif metrics['total_response_time'] < 30.0:
                logger.info(" WARNING: [U+FE0F] ACCEPTABLE: Response time under 30s")
            else:
                logger.info(" FAIL:  SLOW: Response time over 30s - needs optimization")


if __name__ == "__main__":
    """
    Run golden path tests directly for debugging.
    
    Usage:
        python -m pytest tests/mission_critical/test_websocket_connectionhandler_golden_path.py -v -s
        
    For staging environment:
        TEST_ENV=staging python -m pytest tests/mission_critical/test_websocket_connectionhandler_golden_path.py -v -s
    """
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])