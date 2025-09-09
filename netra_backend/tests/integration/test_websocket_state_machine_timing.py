"""
Integration tests for WebSocket state machine timing issues - DESIGNED TO FAIL

Business Value:
- Reproduces timing-dependent import scope bugs in WebSocket connections
- Validates state machine transitions trigger import resolution errors
- Tests real service interactions that expose function-scoped import issues

CRITICAL: These tests use REAL SERVICES and are DESIGNED TO FAIL to reproduce:
"name 'get_connection_state_machine' is not defined" under timing pressure.

The integration tests create realistic timing conditions where the import scope
bug manifests during actual WebSocket state transitions and exception handling.
"""

import pytest
import asyncio
import json
import time
import concurrent.futures
from typing import Dict, Any, List
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env


class TestWebSocketStateMachineTiming(SSotBaseTestCase):
    """
    Integration tests using REAL SERVICES to reproduce WebSocket import timing bugs.
    
    These tests create realistic conditions where function-scoped imports fail
    during actual WebSocket operations with state machine transitions.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_real_services(self):
        """Set up real services for integration testing."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Real service URLs for integration testing
        self.websocket_url = "ws://localhost:8000/ws"
        self.backend_url = "http://localhost:8000"
        
        # Create authenticated user for real WebSocket connections
        self.test_user = await self.auth_helper.create_authenticated_user()
        self.jwt_token = self.test_user.jwt_token
        
        yield
        
        # Cleanup after tests
        # No explicit cleanup needed for integration tests
    
    @pytest.mark.asyncio
    async def test_websocket_connection_state_transition_import_failure(self):
        """
        DESIGNED TO FAIL: Test state machine transitions trigger import scope errors.
        
        This test creates real WebSocket connections and forces state transitions
        that should trigger the import scope bug in the exception handling paths.
        
        Expected Failure: NameError during state machine operations
        """
        import websockets
        from websockets.exceptions import ConnectionClosed
        
        connection_attempts = []
        import_failures = []
        
        try:
            # Create multiple rapid WebSocket connections to trigger timing issues
            tasks = []
            for i in range(3):
                task = self._create_timed_websocket_connection(f"test-timing-{i}")
                tasks.append(task)
            
            # Execute connections concurrently to create timing pressure
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results for import scope failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_str = str(result)
                    if "get_connection_state_machine" in error_str and "not defined" in error_str:
                        import_failures.append({
                            'connection_id': f"test-timing-{i}",
                            'error': error_str,
                            'error_type': type(result).__name__
                        })
                        print(f"✅ IMPORT SCOPE BUG REPRODUCED in connection {i}: {error_str}")
            
            if import_failures:
                failure_details = json.dumps(import_failures, indent=2)
                raise AssertionError(
                    f"INTEGRATION TEST SUCCESS: Import scope bugs reproduced in {len(import_failures)} connections:\n"
                    f"{failure_details}"
                )
            
            # If no import failures occurred, the test should fail as designed
            pytest.fail(
                "Import scope timing bug not reproduced in integration test. "
                "Real WebSocket connections did not trigger the expected NameError."
            )
            
        except ConnectionClosed as e:
            # Connection issues might indicate the import scope bug
            if "get_connection_state_machine" in str(e):
                print(f"✅ IMPORT SCOPE BUG REPRODUCED via ConnectionClosed: {e}")
                raise AssertionError(f"CONNECTION FAILURE DUE TO IMPORT BUG: {e}")
            else:
                # Normal connection error, re-raise
                raise
        except Exception as e:
            # Any exception mentioning the import scope issue
            if "get_connection_state_machine" in str(e) and "not defined" in str(e):
                print(f"✅ IMPORT SCOPE BUG REPRODUCED in integration test: {e}")
                raise AssertionError(f"INTEGRATION IMPORT BUG CONFIRMED: {e}")
            else:
                # Re-raise other exceptions
                raise
    
    async def _create_timed_websocket_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Create a timed WebSocket connection that may trigger import scope issues.
        
        This helper creates real WebSocket connections with authentication
        and measures timing to identify import scope failures.
        """
        import websockets
        from websockets.exceptions import WebSocketException
        
        start_time = time.time()
        connection_result = {
            'connection_id': connection_id,
            'start_time': start_time,
            'success': False,
            'error': None,
            'timing_ms': 0
        }
        
        try:
            # Create authenticated WebSocket headers
            headers = self.auth_helper.get_websocket_headers(self.jwt_token)
            
            # Add timing pressure by connecting rapidly
            connection_timeout = 5.0  # Short timeout to trigger timing issues
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    open_timeout=connection_timeout,
                    close_timeout=2.0
                ),
                timeout=connection_timeout
            )
            
            # Send a message that might trigger state machine transitions
            test_message = {
                "type": "agent_request",
                "data": {
                    "message": f"Test message from {connection_id}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait for response that might trigger exception handling
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                connection_result['response'] = response
                connection_result['success'] = True
            except asyncio.TimeoutError:
                # Timeout might trigger cleanup code with import scope issues
                connection_result['error'] = "Response timeout - may trigger cleanup import scope bug"
            
            # Close connection (may trigger exception handling with import scope issues)
            await websocket.close()
            
        except WebSocketException as e:
            connection_result['error'] = f"WebSocket error: {e}"
            # Check if error indicates import scope issue
            if "get_connection_state_machine" in str(e):
                connection_result['import_scope_error'] = True
        except Exception as e:
            connection_result['error'] = f"Connection error: {e}"
            # Check if error indicates import scope issue
            if "get_connection_state_machine" in str(e) and "not defined" in str(e):
                connection_result['import_scope_error'] = True
                # Re-raise to trigger test failure as designed
                raise
        finally:
            connection_result['timing_ms'] = (time.time() - start_time) * 1000
        
        return connection_result
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_state_machine_race_conditions(self):
        """
        DESIGNED TO FAIL: Test concurrent connections create import scope race conditions.
        
        This test creates multiple concurrent WebSocket connections to trigger
        race conditions in state machine code that expose import scope issues.
        
        Expected Failure: Race conditions expose function-scoped import timing bugs
        """
        import websockets
        
        concurrent_connections = 5
        race_condition_errors = []
        
        async def create_racing_connection(conn_id: int) -> Dict[str, Any]:
            """Create a WebSocket connection designed to race with others."""
            try:
                headers = self.auth_helper.get_websocket_headers(self.jwt_token)
                
                # Use very short timeout to create timing pressure
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_url,
                        additional_headers=headers,
                        open_timeout=2.0
                    ),
                    timeout=2.0
                )
                
                # Immediately send message to trigger state transitions
                rapid_message = {
                    "type": "ping",
                    "connection_id": f"race-{conn_id}",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(rapid_message))
                
                # Quick close to trigger cleanup race conditions
                await websocket.close()
                
                return {"success": True, "connection_id": conn_id}
                
            except Exception as e:
                error_info = {
                    "connection_id": conn_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                
                # Check for import scope issues in race conditions
                if "get_connection_state_machine" in str(e) and "not defined" in str(e):
                    error_info["import_scope_race"] = True
                    race_condition_errors.append(error_info)
                
                return error_info
        
        try:
            # Create all connections concurrently to maximize race conditions
            connection_tasks = [
                create_racing_connection(i) for i in range(concurrent_connections)
            ]
            
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Analyze results for race condition import scope failures
            for result in results:
                if isinstance(result, dict) and result.get("import_scope_race"):
                    print(f"✅ RACE CONDITION IMPORT SCOPE BUG: {result}")
                elif isinstance(result, Exception):
                    if "get_connection_state_machine" in str(result):
                        race_condition_errors.append({
                            "error": str(result),
                            "error_type": type(result).__name__,
                            "import_scope_race": True
                        })
            
            if race_condition_errors:
                error_summary = json.dumps(race_condition_errors, indent=2)
                raise AssertionError(
                    f"RACE CONDITION IMPORT SCOPE BUGS REPRODUCED in {len(race_condition_errors)} connections:\n"
                    f"{error_summary}"
                )
            
            # If no race condition import errors, test should fail as designed
            pytest.fail(
                "Race condition import scope bugs not reproduced. "
                f"All {concurrent_connections} concurrent connections succeeded without timing errors."
            )
            
        except AssertionError:
            # Re-raise AssertionErrors (these are our expected test failures)
            raise
        except Exception as e:
            # Any other exception might indicate the import scope race bug
            if "get_connection_state_machine" in str(e) and "not defined" in str(e):
                print(f"✅ CONCURRENT CONNECTION IMPORT SCOPE BUG: {e}")
                raise AssertionError(f"CONCURRENT IMPORT SCOPE BUG CONFIRMED: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_websocket_exception_handler_import_scope_timing(self):
        """
        DESIGNED TO FAIL: Test exception handlers trigger import scope timing issues.
        
        This test forces WebSocket exceptions that should trigger the exception
        handling code around line 1214 where import scope issues occur.
        
        Expected Failure: Exception handlers cannot access function-scoped imports
        """
        import websockets
        from websockets.exceptions import InvalidStatusCode, InvalidHandshake
        
        exception_handler_failures = []
        
        # Test different exception scenarios that trigger different handler paths
        test_scenarios = [
            {"invalid_url": "ws://localhost:8000/ws/invalid", "expected": "Invalid endpoint"},
            {"malformed_headers": True, "expected": "Header processing"},
            {"rapid_disconnect": True, "expected": "Rapid disconnection"},
        ]
        
        for i, scenario in enumerate(test_scenarios):
            try:
                if scenario.get("invalid_url"):
                    # Connect to invalid URL to trigger exception handling
                    headers = self.auth_helper.get_websocket_headers(self.jwt_token)
                    
                    try:
                        websocket = await asyncio.wait_for(
                            websockets.connect(scenario["invalid_url"], additional_headers=headers),
                            timeout=3.0
                        )
                        await websocket.close()
                    except Exception as url_error:
                        if "get_connection_state_machine" in str(url_error):
                            exception_handler_failures.append({
                                "scenario": "invalid_url",
                                "error": str(url_error),
                                "import_scope_error": True
                            })
                
                elif scenario.get("malformed_headers"):
                    # Use malformed headers to trigger exception handling
                    malformed_headers = {
                        "Authorization": "Bearer invalid-token-format",
                        "X-Invalid-Header": "malformed-value-to-trigger-error"
                    }
                    
                    try:
                        websocket = await asyncio.wait_for(
                            websockets.connect(self.websocket_url, additional_headers=malformed_headers),
                            timeout=3.0
                        )
                        await websocket.close()
                    except Exception as header_error:
                        if "get_connection_state_machine" in str(header_error):
                            exception_handler_failures.append({
                                "scenario": "malformed_headers",
                                "error": str(header_error),
                                "import_scope_error": True
                            })
                
                elif scenario.get("rapid_disconnect"):
                    # Connect and immediately disconnect to trigger cleanup exception handling
                    headers = self.auth_helper.get_websocket_headers(self.jwt_token)
                    
                    try:
                        websocket = await websockets.connect(self.websocket_url, additional_headers=headers)
                        # Immediately close to trigger rapid cleanup
                        await websocket.close()
                        # Try to send after close to trigger exception
                        await websocket.send('{"type": "test"}')
                    except Exception as disconnect_error:
                        if "get_connection_state_machine" in str(disconnect_error):
                            exception_handler_failures.append({
                                "scenario": "rapid_disconnect",
                                "error": str(disconnect_error),
                                "import_scope_error": True
                            })
                
            except Exception as scenario_error:
                # Check if any scenario triggered import scope issues
                if "get_connection_state_machine" in str(scenario_error) and "not defined" in str(scenario_error):
                    exception_handler_failures.append({
                        "scenario": f"scenario_{i}",
                        "error": str(scenario_error),
                        "import_scope_error": True
                    })
        
        if exception_handler_failures:
            failure_summary = json.dumps(exception_handler_failures, indent=2)
            raise AssertionError(
                f"EXCEPTION HANDLER IMPORT SCOPE BUGS REPRODUCED in {len(exception_handler_failures)} scenarios:\n"
                f"{failure_summary}"
            )
        
        # If no exception handler import scope errors, test should fail as designed
        pytest.fail(
            "Exception handler import scope timing bugs not reproduced. "
            "All exception scenarios completed without triggering import scope errors."
        )


if __name__ == "__main__":
    # Run integration tests to reproduce import scope timing bugs with real services
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "not slow"])