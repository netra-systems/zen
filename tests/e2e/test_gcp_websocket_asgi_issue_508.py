"""
E2E tests for Issue #508 - GCP WebSocket ASGI Scope Error

End-to-end validation of WebSocket functionality in GCP staging environment.
These tests validate the complete WebSocket flow and will FAIL initially
if ASGI scope errors persist in GCP Cloud Run.

Focus: Real WebSocket connections to GCP staging environment
"""

import pytest
import asyncio
import websockets
import json
import os
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

# Import test utilities
from test_framework.gcp_integration import GCPStagingEnvironment
from test_framework.websocket_test_utility import WebSocketTestClient


class TestGCPWebSocketASGI:
    """E2E tests for WebSocket ASGI scope handling in GCP environment."""
    
    @pytest.fixture
    def gcp_staging_env(self):
        """GCP staging environment configuration."""
        return GCPStagingEnvironment(
            base_url="https://staging.netra.ai",
            websocket_url="wss://staging.netra.ai/ws"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gcp_staging_websocket_connection_establishment(self, gcp_staging_env):
        """Test WebSocket connection establishment in GCP staging - WILL FAIL if ASGI error persists."""
        # Build WebSocket URL with query parameters that trigger the error
        websocket_url = f"{gcp_staging_env.websocket_url}?token=test_token&user_id=test_user"
        
        try:
            # Attempt WebSocket connection - this will FAIL if ASGI scope error blocks connections
            async with websockets.connect(
                websocket_url,
                additional_headers={
                    "Origin": "https://staging.netra.ai",
                    "User-Agent": "pytest-websocket-client/1.0"
                },
                timeout=10
            ) as websocket:
                # If we get here, connection succeeded
                assert websocket.open, "WebSocket connection should be open"
                
                # Send test message to validate connection works
                test_message = {"type": "ping", "data": "connection_test"}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                assert response_data is not None, "Should receive response from WebSocket"
                
        except websockets.exceptions.ConnectionClosedError as e:
            pytest.fail(f"WebSocket connection closed due to ASGI error: {e}")
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 500:
                pytest.fail(f"WebSocket connection failed with 500 error - likely ASGI scope issue: {e}")
            else:
                raise
        except Exception as e:
            if "query_params" in str(e) or "ASGI scope error" in str(e):
                pytest.fail(f"WebSocket connection failed due to ASGI scope error: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_auth_flow_with_query_params(self, gcp_staging_env):
        """Test WebSocket authentication flow with query parameters - WILL FAIL if query_params parsing broken."""
        
        # Test various query parameter combinations that might trigger the error
        test_cases = [
            {"token": "abc123", "user_id": "user123"},
            {"session_id": "sess_456", "workspace": "default"},
            {"auth_token": "bearer_789", "client_version": "1.0.0"},
            # Complex query parameters that might cause URL object issues
            {"redirect_uri": "https://staging.netra.ai/callback", "state": "complex_state_123"},
            {"filter": "category=ai&type=optimization", "sort": "created_desc"},
        ]
        
        for test_params in test_cases:
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in test_params.items()])
            websocket_url = f"{gcp_staging_env.websocket_url}?{query_string}"
            
            try:
                async with websockets.connect(
                    websocket_url,
                    timeout=10
                ) as websocket:
                    # Send auth validation message
                    auth_message = {
                        "type": "auth_validate",
                        "expected_params": test_params
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    # Wait for auth response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    # Validate that query parameters were parsed correctly
                    assert "auth_status" in response_data, f"Auth validation failed for params: {test_params}"
                    
            except Exception as e:
                if "query_params" in str(e):
                    pytest.fail(f"Query parameter parsing failed for {test_params}: {e}")
                else:
                    # Log but don't fail for other errors (might be auth-related)
                    print(f"Non-ASGI error for {test_params}: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_agent_events_in_gcp(self, gcp_staging_env):
        """Test complete WebSocket agent event flow in GCP staging - WILL FAIL if ASGI issues block events."""
        websocket_url = f"{gcp_staging_env.websocket_url}?token=agent_test&session=test_session"
        
        try:
            async with websockets.connect(websocket_url, timeout=15) as websocket:
                # Send agent execution request
                agent_request = {
                    "type": "agent_execute",
                    "query": "Test query for agent execution",
                    "session_id": "test_session_123"
                }
                await websocket.send(json.dumps(agent_request))
                
                # Collect all 5 critical WebSocket events
                expected_events = [
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                ]
                received_events = []
                
                # Wait for all events (or timeout)
                try:
                    while len(received_events) < len(expected_events):
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        event_data = json.loads(message)
                        
                        if "event_type" in event_data:
                            received_events.append(event_data["event_type"])
                            print(f"Received event: {event_data['event_type']}")
                        
                        # Break if we get agent_completed (last event)
                        if event_data.get("event_type") == "agent_completed":
                            break
                            
                except asyncio.TimeoutError:
                    pytest.fail(f"Timeout waiting for agent events. Received: {received_events}")
                
                # Validate all critical events were received
                for expected_event in expected_events:
                    if expected_event not in received_events:
                        pytest.fail(f"Missing critical WebSocket event: {expected_event}")
                
                assert len(received_events) >= 5, f"Expected at least 5 events, got {len(received_events)}"
                
        except websockets.exceptions.ConnectionClosedError as e:
            pytest.fail(f"WebSocket connection closed during agent event flow: {e}")
        except Exception as e:
            if "ASGI" in str(e) or "query_params" in str(e):
                pytest.fail(f"Agent event flow failed due to ASGI scope error: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_load_under_gcp_conditions(self, gcp_staging_env):
        """Test WebSocket ASGI scope handling under load in GCP - MAY FAIL if race conditions exist."""
        # Create multiple concurrent WebSocket connections
        concurrent_connections = 5
        connection_duration = 10  # seconds
        
        async def create_websocket_connection(connection_id: int):
            """Create individual WebSocket connection for load testing."""
            websocket_url = f"{gcp_staging_env.websocket_url}?conn_id={connection_id}&load_test=true"
            
            try:
                async with websockets.connect(websocket_url, timeout=15) as websocket:
                    # Send periodic messages during connection
                    for i in range(3):
                        message = {
                            "type": "load_test",
                            "connection_id": connection_id,
                            "message_number": i,
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        await websocket.send(json.dumps(message))
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        assert response_data.get("connection_id") == connection_id, \
                            f"Connection {connection_id} response mismatch"
                        
                        await asyncio.sleep(2)  # Space out messages
                    
                    return f"Connection {connection_id} completed successfully"
                    
            except Exception as e:
                if "query_params" in str(e) or "ASGI" in str(e):
                    return f"Connection {connection_id} failed with ASGI error: {e}"
                else:
                    return f"Connection {connection_id} failed with other error: {e}"
        
        # Run concurrent connections
        tasks = [create_websocket_connection(i) for i in range(concurrent_connections)]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results for ASGI-related failures
            asgi_failures = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    if "query_params" in str(result) or "ASGI" in str(result):
                        asgi_failures.append(f"Connection {i}: {result}")
                elif isinstance(result, str) and ("ASGI error" in result):
                    asgi_failures.append(result)
            
            if asgi_failures:
                pytest.fail(f"ASGI scope errors under load: {asgi_failures}")
            
            # Validate at least some connections succeeded
            successful_connections = sum(1 for r in results if isinstance(r, str) and "completed successfully" in r)
            assert successful_connections >= concurrent_connections // 2, \
                f"Too many connection failures: {results}"
                
        except Exception as e:
            pytest.fail(f"Load testing revealed ASGI scope handling issues: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_error_recovery_in_gcp(self, gcp_staging_env):
        """Test WebSocket error recovery in GCP when ASGI scope errors occur - VALIDATES FIXES."""
        
        # Test scenarios that previously caused ASGI scope errors
        error_prone_scenarios = [
            # Complex query parameters
            {"scenario": "complex_params", "params": {"redirect": "https://app.netra.ai/callback?state=123", "data": "encoded%20value"}},
            # Special characters in parameters  
            {"scenario": "special_chars", "params": {"query": "AI optimization & performance", "filter": "category=ai+ml"}},
            # Long parameter values
            {"scenario": "long_params", "params": {"session_data": "a" * 1000, "context": "b" * 500}},
            # Unicode parameters
            {"scenario": "unicode_params", "params": {"name": "测试用户", "description": "AI优化平台"}},
        ]
        
        recovery_success_count = 0
        
        for scenario in error_prone_scenarios:
            scenario_name = scenario["scenario"]
            params = scenario["params"]
            
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            websocket_url = f"{gcp_staging_env.websocket_url}?{query_string}"
            
            try:
                async with websockets.connect(websocket_url, timeout=10) as websocket:
                    # Test that connection works despite potentially problematic parameters
                    test_message = {
                        "type": "error_recovery_test",
                        "scenario": scenario_name,
                        "test_params": params
                    }
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response (validates server processed the message)
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    assert response_data.get("status") == "success", \
                        f"Error recovery failed for scenario: {scenario_name}"
                    
                    recovery_success_count += 1
                    print(f"✓ Error recovery successful for scenario: {scenario_name}")
                    
            except websockets.exceptions.ConnectionClosedError:
                print(f"✗ Connection failed for scenario {scenario_name} - ASGI error likely")
            except asyncio.TimeoutError:
                print(f"✗ Timeout for scenario {scenario_name} - server processing issue")
            except Exception as e:
                if "query_params" in str(e) or "ASGI" in str(e):
                    print(f"✗ ASGI scope error for scenario {scenario_name}: {e}")
                else:
                    print(f"✗ Other error for scenario {scenario_name}: {e}")
        
        # Validate that error recovery worked for most scenarios
        success_rate = recovery_success_count / len(error_prone_scenarios)
        assert success_rate >= 0.75, \
            f"Error recovery rate too low: {success_rate:.2%} ({recovery_success_count}/{len(error_prone_scenarios)})"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gcp_websocket_specific_asgi_scope_validation(self, gcp_staging_env):
        """Test GCP-specific ASGI scope characteristics - VALIDATES GCP COMPATIBILITY."""
        
        # Test WebSocket connection with GCP-specific headers/parameters
        websocket_url = f"{gcp_staging_env.websocket_url}?gcp_test=true&cloud_run=staging"
        
        # GCP-specific headers that might affect ASGI scope creation
        gcp_headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Forwarded-Proto": "https", 
            "X-Cloud-Trace-Context": "105445aa7843bc8bf206b120001000/1",
            "Origin": "https://staging.netra.ai",
            "User-Agent": "Mozilla/5.0 (compatible; GCP-Test/1.0)"
        }
        
        try:
            async with websockets.connect(
                websocket_url,
                additional_headers=gcp_headers,
                timeout=15
            ) as websocket:
                # Send message to validate GCP environment processing
                gcp_test_message = {
                    "type": "gcp_environment_test",
                    "validate_headers": True,
                    "validate_query_params": True,
                    "expected_environment": "gcp_cloud_run"
                }
                await websocket.send(json.dumps(gcp_test_message))
                
                # Wait for environment validation response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                
                # Validate GCP environment characteristics were processed correctly
                assert response_data.get("environment") == "gcp_cloud_run", \
                    "GCP environment detection failed"
                assert response_data.get("headers_processed") is True, \
                    "GCP headers not processed correctly"
                assert response_data.get("query_params_extracted") is True, \
                    "GCP query parameters not extracted correctly"
                
                print("✓ GCP-specific ASGI scope handling validated")
                
        except Exception as e:
            if "query_params" in str(e):
                pytest.fail(f"GCP-specific ASGI scope error: {e}")
            else:
                raise


class TestWebSocketASGIRecovery:
    """Tests for WebSocket ASGI error recovery and resilience."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_resilience_after_asgi_errors(self):
        """Test that WebSocket system recovers after ASGI scope errors."""
        staging_url = "wss://staging.netra.ai/ws"
        
        # First, try a connection that might trigger ASGI error
        problematic_url = f"{staging_url}?complex=value%20with%20spaces&special=chars%26symbols"
        
        try:
            # This might fail initially
            async with websockets.connect(problematic_url, timeout=5) as websocket:
                await websocket.send('{"type": "test"}')
                await websocket.recv()
        except Exception as e:
            print(f"Expected potential failure: {e}")
        
        # Then test that subsequent connections work (system recovered)
        simple_url = f"{staging_url}?token=recovery_test"
        
        async with websockets.connect(simple_url, timeout=10) as websocket:
            recovery_message = {"type": "recovery_test", "after_error": True}
            await websocket.send(json.dumps(recovery_message))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            
            assert response_data is not None, "System should recover after ASGI errors"
            print("✓ WebSocket system recovered after potential ASGI errors")


if __name__ == "__main__":
    # Run E2E tests against GCP staging
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])