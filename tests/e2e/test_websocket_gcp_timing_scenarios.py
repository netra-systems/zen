"""
E2E tests for WebSocket GCP timing scenarios - DESIGNED TO FAIL

Business Value:
- Reproduces import scope bugs under GCP Cloud Run timing constraints
- Validates WebSocket authentication flows expose function-scoped import issues
- Tests real production scenarios where import timing failures occur

CRITICAL: ALL E2E TESTS REQUIRE AUTHENTICATION per CLAUDE.md mandate.
These tests use test_framework/ssot/e2e_auth_helper.py for proper auth flows.

DESIGNED TO FAIL: These tests reproduce "name 'get_connection_state_machine' is not defined"
under real GCP timing conditions and concurrent user scenarios.
"""

import pytest
import asyncio
import json
import time
import aiohttp
import websockets
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class TestWebSocketGCPTimingScenarios(SSotBaseTestCase):
    """
    E2E tests with REQUIRED AUTHENTICATION reproducing WebSocket import bugs under GCP conditions.
    
    These tests simulate real GCP Cloud Run timing constraints where function-scoped
    imports fail during WebSocket operations under load and timing pressure.
    
    CRITICAL: ALL tests use authentication as mandated by CLAUDE.md.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_authenticated_e2e_environment(self):
        """Set up authenticated E2E testing environment."""
        self.env = get_env()
        
        # CRITICAL: Use SSOT E2E auth helper as mandated
        test_environment = self.env.get("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=test_environment)
        
        # Create authenticated users for multi-user scenarios
        self.primary_user = await self.auth_helper.create_authenticated_user(
            email="e2e_primary@websocket.test",
            full_name="E2E Primary User",
            permissions=["read", "write", "websocket_access"]
        )
        
        self.secondary_user = await self.auth_helper.create_authenticated_user(
            email="e2e_secondary@websocket.test", 
            full_name="E2E Secondary User",
            permissions=["read", "write", "websocket_access"]
        )
        
        # Set URLs based on environment
        if test_environment == "staging":
            self.websocket_url = "wss://staging-backend.netraapex.com/ws"
            self.backend_url = "https://staging-backend.netraapex.com"
        else:
            self.websocket_url = "ws://localhost:8000/ws"
            self.backend_url = "http://localhost:8000"
        
        print(f"🔐 E2E Auth Setup Complete:")
        print(f"   Primary User: {self.primary_user.user_id}")
        print(f"   Secondary User: {self.secondary_user.user_id}")
        print(f"   Environment: {test_environment}")
        print(f"   WebSocket URL: {self.websocket_url}")
        
        yield
        
        # E2E cleanup
        print(f"🧹 E2E test cleanup complete")
    
    @pytest.mark.asyncio
    async def test_authenticated_websocket_gcp_timeout_import_scope_failure(self):
        """
        DESIGNED TO FAIL: Test GCP timeout conditions trigger import scope errors with auth.
        
        This E2E test reproduces the import scope bug under GCP Cloud Run timeout
        constraints using real authenticated WebSocket connections.
        
        Expected Failure: GCP timing constraints expose function-scoped import issues
        """
        # CRITICAL: Use authentication as mandated by CLAUDE.md
        auth_headers = self.auth_helper.get_websocket_headers(self.primary_user.jwt_token)
        auth_subprotocols = self.auth_helper.get_websocket_subprotocols(self.primary_user.jwt_token)
        
        gcp_timeout_scenarios = []
        import_scope_failures = []
        
        # Simulate GCP Cloud Run timeout scenarios (15-second request timeout)
        gcp_timing_constraints = [
            {"timeout": 2.0, "scenario": "rapid_timeout"},
            {"timeout": 5.0, "scenario": "moderate_timeout"},
            {"timeout": 10.0, "scenario": "near_gcp_limit"},
            {"timeout": 15.0, "scenario": "gcp_limit_timeout"}
        ]
        
        for constraint in gcp_timing_constraints:
            scenario_result = {
                "scenario": constraint["scenario"],
                "timeout": constraint["timeout"],
                "user_id": self.primary_user.user_id,
                "start_time": time.time()
            }
            
            try:
                print(f"🔬 Testing GCP scenario: {constraint['scenario']} (timeout: {constraint['timeout']}s)")
                
                # Create authenticated WebSocket connection with GCP timing constraints
                connection_future = websockets.connect(
                    self.websocket_url,
                    additional_headers=auth_headers,
                    subprotocols=auth_subprotocols,
                    open_timeout=constraint["timeout"],
                    close_timeout=2.0,
                    ping_interval=None,  # Disable ping during short timeouts
                    ping_timeout=None
                )
                
                # Apply GCP timeout pressure
                websocket = await asyncio.wait_for(
                    connection_future,
                    timeout=constraint["timeout"]
                )
                
                # Send authenticated message that might trigger state machine operations
                gcp_test_message = {
                    "type": "agent_request",
                    "user_id": self.primary_user.user_id,
                    "data": {
                        "message": f"GCP timing test for {constraint['scenario']}",
                        "gcp_timeout_test": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "auth": {
                        "user_id": self.primary_user.user_id,
                        "jwt_token": self.primary_user.jwt_token[:32] + "..."  # Truncated for logging
                    }
                }
                
                await websocket.send(json.dumps(gcp_test_message))
                
                # Wait for response under GCP timing constraints
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=constraint["timeout"] - 1.0  # Leave 1s buffer
                    )
                    scenario_result["response_received"] = True
                    scenario_result["response_length"] = len(response)
                except asyncio.TimeoutError:
                    scenario_result["response_timeout"] = True
                    # Timeout might trigger cleanup with import scope issues
                
                # Close connection (might trigger exception handling with import scope bug)
                await asyncio.wait_for(websocket.close(), timeout=2.0)
                scenario_result["success"] = True
                
            except websockets.exceptions.WebSocketException as ws_error:
                scenario_result["websocket_error"] = str(ws_error)
                # Check for import scope issues in WebSocket errors
                if "get_connection_state_machine" in str(ws_error) and "not defined" in str(ws_error):
                    scenario_result["import_scope_error"] = True
                    import_scope_failures.append(scenario_result)
                    print(f"✅ GCP WEBSOCKET IMPORT SCOPE BUG: {ws_error}")
                    
            except asyncio.TimeoutError as timeout_error:
                scenario_result["timeout_error"] = str(timeout_error)
                # GCP timeouts might expose import scope issues
                if "get_connection_state_machine" in str(timeout_error):
                    scenario_result["import_scope_error"] = True
                    import_scope_failures.append(scenario_result)
                    print(f"✅ GCP TIMEOUT IMPORT SCOPE BUG: {timeout_error}")
                    
            except Exception as general_error:
                scenario_result["general_error"] = str(general_error)
                # Any error mentioning import scope issues
                if "get_connection_state_machine" in str(general_error) and "not defined" in str(general_error):
                    scenario_result["import_scope_error"] = True
                    import_scope_failures.append(scenario_result)
                    print(f"✅ GCP GENERAL IMPORT SCOPE BUG: {general_error}")
            finally:
                scenario_result["duration_ms"] = (time.time() - scenario_result["start_time"]) * 1000
                gcp_timeout_scenarios.append(scenario_result)
        
        # Analyze results for import scope failures under GCP conditions
        if import_scope_failures:
            failure_summary = json.dumps(import_scope_failures, indent=2)
            raise AssertionError(
                f"GCP TIMEOUT IMPORT SCOPE BUGS REPRODUCED in {len(import_scope_failures)} scenarios:\n"
                f"{failure_summary}"
            )
        
        # If no GCP import scope failures, test should fail as designed
        pytest.fail(
            f"GCP timing import scope bugs not reproduced. "
            f"All {len(gcp_timeout_scenarios)} GCP timeout scenarios completed without import scope errors."
        )
    
    @pytest.mark.asyncio
    async def test_authenticated_concurrent_users_import_scope_race_conditions(self):
        """
        DESIGNED TO FAIL: Test concurrent authenticated users trigger import scope race conditions.
        
        This E2E test creates multiple authenticated users connecting simultaneously
        to reproduce import scope race conditions under realistic load.
        
        Expected Failure: Concurrent user connections expose function-scoped import timing bugs
        """
        # CRITICAL: Use multiple authenticated users as mandated by CLAUDE.md
        authenticated_users = [self.primary_user, self.secondary_user]
        
        # Create additional authenticated users for concurrent testing
        for i in range(3):
            additional_user = await self.auth_helper.create_authenticated_user(
                email=f"e2e_concurrent_{i}@websocket.test",
                full_name=f"E2E Concurrent User {i}",
                permissions=["read", "write", "websocket_access"]
            )
            authenticated_users.append(additional_user)
        
        concurrent_connection_results = []
        race_condition_import_failures = []
        
        async def create_authenticated_concurrent_connection(user: AuthenticatedUser, conn_index: int) -> Dict[str, Any]:
            """Create authenticated WebSocket connection for concurrent testing."""
            connection_result = {
                "user_id": user.user_id,
                "connection_index": conn_index,
                "start_time": time.time(),
                "authenticated": True
            }
            
            try:
                # Get authenticated headers and subprotocols
                auth_headers = self.auth_helper.get_websocket_headers(user.jwt_token)
                auth_subprotocols = self.auth_helper.get_websocket_subprotocols(user.jwt_token)
                
                print(f"🔐 Concurrent connection {conn_index} for user {user.user_id}")
                
                # Create concurrent authenticated connection with race condition timing
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_url,
                        additional_headers=auth_headers,
                        subprotocols=auth_subprotocols,
                        open_timeout=3.0,
                        close_timeout=1.0
                    ),
                    timeout=5.0
                )
                
                # Send concurrent authenticated messages rapidly
                concurrent_messages = [
                    {
                        "type": "ping",
                        "user_id": user.user_id,
                        "connection_index": conn_index,
                        "message_index": msg_idx,
                        "timestamp": time.time()
                    }
                    for msg_idx in range(3)
                ]
                
                # Send all messages rapidly to create timing pressure
                for message in concurrent_messages:
                    await websocket.send(json.dumps(message))
                    await asyncio.sleep(0.1)  # Minimal delay for race conditions
                
                # Rapid close to trigger cleanup race conditions
                await websocket.close()
                connection_result["success"] = True
                
            except Exception as concurrent_error:
                connection_result["error"] = str(concurrent_error)
                connection_result["error_type"] = type(concurrent_error).__name__
                
                # Check for race condition import scope issues
                if "get_connection_state_machine" in str(concurrent_error) and "not defined" in str(concurrent_error):
                    connection_result["race_condition_import_scope"] = True
                    race_condition_import_failures.append(connection_result)
                    print(f"✅ CONCURRENT RACE CONDITION IMPORT SCOPE BUG: {concurrent_error}")
                    
            finally:
                connection_result["duration_ms"] = (time.time() - connection_result["start_time"]) * 1000
            
            return connection_result
        
        try:
            # Create all concurrent connections simultaneously
            concurrent_tasks = [
                create_authenticated_concurrent_connection(user, i)
                for i, user in enumerate(authenticated_users)
            ]
            
            print(f"🚀 Starting {len(concurrent_tasks)} concurrent authenticated WebSocket connections")
            
            # Execute all connections concurrently to maximize race conditions
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Process results for race condition import scope failures
            for result in results:
                if isinstance(result, dict):
                    concurrent_connection_results.append(result)
                    if result.get("race_condition_import_scope"):
                        print(f"✅ Race condition import scope detected: {result}")
                elif isinstance(result, Exception):
                    if "get_connection_state_machine" in str(result) and "not defined" in str(result):
                        race_condition_import_failures.append({
                            "exception": str(result),
                            "exception_type": type(result).__name__,
                            "race_condition_import_scope": True
                        })
                        print(f"✅ EXCEPTION RACE CONDITION IMPORT SCOPE BUG: {result}")
            
            if race_condition_import_failures:
                failure_summary = json.dumps(race_condition_import_failures, indent=2)
                raise AssertionError(
                    f"CONCURRENT USER RACE CONDITION IMPORT SCOPE BUGS REPRODUCED in {len(race_condition_import_failures)} connections:\n"
                    f"{failure_summary}"
                )
            
            # If no race condition import scope failures, test should fail as designed
            pytest.fail(
                f"Concurrent user race condition import scope bugs not reproduced. "
                f"All {len(authenticated_users)} authenticated users connected successfully without import scope race conditions."
            )
            
        except AssertionError:
            # Re-raise expected test failures
            raise
        except Exception as e:
            # Any other exception might indicate race condition import scope issues
            if "get_connection_state_machine" in str(e) and "not defined" in str(e):
                print(f"✅ CONCURRENT EXECUTION IMPORT SCOPE BUG: {e}")
                raise AssertionError(f"CONCURRENT EXECUTION IMPORT SCOPE BUG CONFIRMED: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_authenticated_websocket_agent_execution_import_scope_failure(self):
        """
        DESIGNED TO FAIL: Test authenticated agent execution triggers import scope failures.
        
        This E2E test reproduces import scope bugs during authenticated agent execution
        workflows that trigger WebSocket state machine operations.
        
        Expected Failure: Agent execution paths expose function-scoped import timing issues
        """
        # CRITICAL: Use authentication for agent execution as mandated
        auth_headers = self.auth_helper.get_websocket_headers(self.primary_user.jwt_token)
        auth_subprotocols = self.auth_helper.get_websocket_subprotocols(self.primary_user.jwt_token)
        
        agent_execution_scenarios = [
            {
                "agent_type": "data_analysis",
                "complexity": "high",
                "expected_duration": 10.0
            },
            {
                "agent_type": "optimization",
                "complexity": "medium", 
                "expected_duration": 5.0
            },
            {
                "agent_type": "cost_analysis",
                "complexity": "low",
                "expected_duration": 2.0
            }
        ]
        
        agent_import_scope_failures = []
        
        for scenario in agent_execution_scenarios:
            scenario_result = {
                "scenario": scenario,
                "user_id": self.primary_user.user_id,
                "start_time": time.time()
            }
            
            try:
                print(f"🤖 Testing authenticated agent execution: {scenario['agent_type']}")
                
                # Create authenticated WebSocket for agent execution
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_url,
                        additional_headers=auth_headers,
                        subprotocols=auth_subprotocols,
                        open_timeout=5.0
                    ),
                    timeout=10.0
                )
                
                # Send authenticated agent execution request
                agent_request = {
                    "type": "agent_request",
                    "user_id": self.primary_user.user_id,
                    "agent_type": scenario["agent_type"],
                    "data": {
                        "message": f"Execute {scenario['agent_type']} agent with {scenario['complexity']} complexity",
                        "complexity": scenario["complexity"],
                        "import_scope_test": True,
                        "authenticated_execution": True
                    },
                    "auth": {
                        "user_id": self.primary_user.user_id,
                        "permissions": self.primary_user.permissions
                    },
                    "timing": {
                        "max_duration": scenario["expected_duration"],
                        "start_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Monitor agent execution for import scope failures
                agent_messages = []
                start_time = time.time()
                
                while (time.time() - start_time) < scenario["expected_duration"] + 5.0:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        agent_messages.append(json.loads(message))
                        
                        # Check for agent completion or errors
                        parsed_message = json.loads(message)
                        if parsed_message.get("type") == "agent_completed":
                            break
                        elif parsed_message.get("type") == "error":
                            if "get_connection_state_machine" in parsed_message.get("error", ""):
                                scenario_result["agent_import_scope_error"] = True
                                agent_import_scope_failures.append(scenario_result)
                                break
                                
                    except asyncio.TimeoutError:
                        # Continue waiting for agent completion
                        continue
                    except Exception as message_error:
                        if "get_connection_state_machine" in str(message_error):
                            scenario_result["message_import_scope_error"] = True
                            agent_import_scope_failures.append(scenario_result)
                            break
                
                await websocket.close()
                scenario_result["success"] = True
                scenario_result["messages_received"] = len(agent_messages)
                
            except Exception as agent_error:
                scenario_result["agent_error"] = str(agent_error)
                
                # Check for import scope issues in agent execution
                if "get_connection_state_machine" in str(agent_error) and "not defined" in str(agent_error):
                    scenario_result["agent_execution_import_scope_error"] = True
                    agent_import_scope_failures.append(scenario_result)
                    print(f"✅ AGENT EXECUTION IMPORT SCOPE BUG: {agent_error}")
            finally:
                scenario_result["total_duration_ms"] = (time.time() - scenario_result["start_time"]) * 1000
        
        if agent_import_scope_failures:
            failure_summary = json.dumps(agent_import_scope_failures, indent=2)
            raise AssertionError(
                f"AGENT EXECUTION IMPORT SCOPE BUGS REPRODUCED in {len(agent_import_scope_failures)} scenarios:\n"
                f"{failure_summary}"
            )
        
        # If no agent execution import scope failures, test should fail as designed
        pytest.fail(
            f"Agent execution import scope bugs not reproduced. "
            f"All {len(agent_execution_scenarios)} authenticated agent execution scenarios completed without import scope errors."
        )
    
    @pytest.mark.asyncio
    async def test_authenticated_websocket_error_recovery_import_scope_failure(self):
        """
        DESIGNED TO FAIL: Test authenticated error recovery triggers import scope failures.
        
        This E2E test reproduces import scope bugs in error recovery and exception
        handling paths during authenticated WebSocket operations.
        
        Expected Failure: Error recovery paths expose function-scoped import issues
        """
        # CRITICAL: Use authentication for error recovery testing
        auth_headers = self.auth_helper.get_websocket_headers(self.primary_user.jwt_token)
        
        error_recovery_scenarios = [
            {"error_type": "invalid_message", "trigger": "malformed_json"},
            {"error_type": "authentication_error", "trigger": "expired_token"},
            {"error_type": "permission_error", "trigger": "insufficient_permissions"},
            {"error_type": "connection_error", "trigger": "rapid_reconnection"}
        ]
        
        error_recovery_import_failures = []
        
        for scenario in error_recovery_scenarios:
            scenario_result = {
                "scenario": scenario,
                "user_id": self.primary_user.user_id,
                "start_time": time.time()
            }
            
            try:
                print(f"🔧 Testing authenticated error recovery: {scenario['error_type']}")
                
                # Create authenticated connection for error recovery testing
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.websocket_url,
                        additional_headers=auth_headers,
                        open_timeout=5.0
                    ),
                    timeout=10.0
                )
                
                # Trigger specific error scenarios
                if scenario["trigger"] == "malformed_json":
                    # Send malformed JSON to trigger error handling
                    await websocket.send('{"type": "invalid", "malformed": json}')
                    
                elif scenario["trigger"] == "expired_token":
                    # Send request with expired token simulation
                    expired_request = {
                        "type": "agent_request",
                        "auth": {"jwt_token": "expired-token-simulation"},
                        "data": {"message": "Test with expired token"}
                    }
                    await websocket.send(json.dumps(expired_request))
                    
                elif scenario["trigger"] == "insufficient_permissions":
                    # Send request requiring higher permissions
                    permission_request = {
                        "type": "admin_request",
                        "user_id": self.primary_user.user_id,
                        "data": {"action": "system_admin_operation"}
                    }
                    await websocket.send(json.dumps(permission_request))
                    
                elif scenario["trigger"] == "rapid_reconnection":
                    # Close and immediately reconnect to trigger race conditions
                    await websocket.close()
                    websocket = await websockets.connect(
                        self.websocket_url,
                        additional_headers=auth_headers,
                        open_timeout=2.0
                    )
                
                # Wait for error recovery response
                try:
                    error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    scenario_result["error_response"] = error_response
                except Exception as recovery_error:
                    if "get_connection_state_machine" in str(recovery_error):
                        scenario_result["recovery_import_scope_error"] = True
                        error_recovery_import_failures.append(scenario_result)
                
                await websocket.close()
                scenario_result["success"] = True
                
            except Exception as error_scenario_exception:
                scenario_result["error"] = str(error_scenario_exception)
                
                # Check for import scope issues in error recovery
                if "get_connection_state_machine" in str(error_scenario_exception) and "not defined" in str(error_scenario_exception):
                    scenario_result["error_recovery_import_scope_error"] = True
                    error_recovery_import_failures.append(scenario_result)
                    print(f"✅ ERROR RECOVERY IMPORT SCOPE BUG: {error_scenario_exception}")
            finally:
                scenario_result["duration_ms"] = (time.time() - scenario_result["start_time"]) * 1000
        
        if error_recovery_import_failures:
            failure_summary = json.dumps(error_recovery_import_failures, indent=2)
            raise AssertionError(
                f"ERROR RECOVERY IMPORT SCOPE BUGS REPRODUCED in {len(error_recovery_import_failures)} scenarios:\n"
                f"{failure_summary}"
            )
        
        # If no error recovery import scope failures, test should fail as designed
        pytest.fail(
            f"Error recovery import scope bugs not reproduced. "
            f"All {len(error_recovery_scenarios)} authenticated error recovery scenarios completed without import scope errors."
        )


if __name__ == "__main__":
    # Run E2E tests to reproduce import scope bugs under GCP timing conditions
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "not slow"])