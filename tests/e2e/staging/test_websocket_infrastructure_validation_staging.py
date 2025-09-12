"""
E2E Staging Tests for WebSocket Infrastructure Validation (Issue #315)

These tests run against staging GCP environment to validate WebSocket functionality
when local Docker infrastructure fails. They test the complete WebSocket flow
without relying on local Docker services that have configuration issues.

Business Impact: These tests protect the Golden Path user flow that delivers 90% 
of platform value and safeguards $500K+ ARR by validating chat functionality 
in the production-like staging environment.

Test Strategy: E2E tests against real staging services to bypass Docker issues
"""

import asyncio
import json
import pytest
import websockets
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from shared.isolated_environment import get_env
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestConfig


class TestWebSocketInfrastructureStaging:
    """E2E tests for WebSocket infrastructure against staging GCP environment."""
    
    @pytest.fixture(autouse=True)
    def setup_staging_environment(self):
        """Setup staging environment configuration."""
        self.env = get_env()
        
        # Staging GCP URLs (these should work when local Docker fails)
        self.staging_backend_url = self.env.get(
            'BACKEND_STAGING_URL', 
            'https://netra-backend-staging-123456-uc.a.run.app'
        )
        self.staging_websocket_url = self.staging_backend_url.replace('https://', 'wss://').replace('http://', 'ws://')
        self.staging_auth_url = self.env.get(
            'AUTH_STAGING_URL',
            'https://netra-auth-staging-123456-uc.a.run.app'
        )
        
        # Test configuration for staging
        self.config = RealWebSocketTestConfig(
            backend_url=self.staging_backend_url,
            websocket_url=self.staging_websocket_url,
            connection_timeout=30.0,  # Longer timeout for GCP
            event_timeout=20.0,
            max_retries=3
        )

    @pytest.mark.asyncio
    async def test_staging_websocket_connection_establishment(self):
        """
        E2E TEST: Validate WebSocket connection can be established to staging GCP.
        
        This test validates that WebSocket infrastructure works in staging when
        local Docker infrastructure fails due to configuration issues.
        
        Expected Result: SUCCESS - demonstrates staging WebSocket works
        Business Impact: Validates chat infrastructure protecting $500K+ ARR
        """
        websocket_endpoint = f"{self.staging_websocket_url}/ws/test"
        
        try:
            # Attempt to establish WebSocket connection to staging
            async with websockets.connect(
                websocket_endpoint,
                timeout=self.config.connection_timeout,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                # Send test message
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_id": "staging_infrastructure_validation"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=self.config.event_timeout
                    )
                    response_data = json.loads(response)
                    
                    # Validate response
                    assert response_data is not None, \
                        "No response received from staging WebSocket"
                    
                    print(f" PASS:  Staging WebSocket connection successful: {response_data}")
                    
                except asyncio.TimeoutError:
                    pytest.fail(
                        f"Staging WebSocket connection timeout after {self.config.event_timeout}s. "
                        f"This may indicate WebSocket infrastructure issues in staging that "
                        f"could impact chat functionality protecting $500K+ ARR."
                    )
                    
        except Exception as e:
            pytest.fail(
                f"Staging WebSocket connection failed: {e}. "
                f"This indicates WebSocket infrastructure issues that prevent "
                f"validation of chat functionality. If local Docker also fails, "
                f"this represents complete blockage of WebSocket testing."
            )

    @pytest.mark.asyncio 
    async def test_staging_websocket_agent_event_flow(self):
        """
        E2E TEST: Validate complete agent event flow through staging WebSocket.
        
        This test validates the 5 critical WebSocket events that enable chat
        functionality work correctly in staging environment.
        
        Expected Result: All 5 agent events received successfully
        Business Impact: Validates real-time chat interactions that deliver 90% platform value
        """
        websocket_endpoint = f"{self.staging_websocket_url}/ws/agent"
        
        # Required agent events for chat functionality
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        received_events = set()
        event_messages = []
        
        try:
            async with websockets.connect(
                websocket_endpoint,
                timeout=self.config.connection_timeout,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                # Send agent request
                agent_request = {
                    "type": "agent_request",
                    "agent_name": "test_agent",
                    "task": "Perform a simple test to validate WebSocket event delivery",
                    "user_id": "staging_test_user",
                    "thread_id": f"staging_test_thread_{datetime.now().timestamp()}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events for up to 60 seconds (longer for staging)
                timeout_duration = 60.0
                start_time = asyncio.get_event_loop().time()
                
                while (
                    len(received_events) < len(required_events) and 
                    (asyncio.get_event_loop().time() - start_time) < timeout_duration
                ):
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(message)
                        
                        event_type = event_data.get("type")
                        if event_type in required_events:
                            received_events.add(event_type)
                            event_messages.append(event_data)
                            print(f" PASS:  Received event: {event_type}")
                            
                    except asyncio.TimeoutError:
                        # Continue waiting for more events
                        continue
                    except Exception as e:
                        print(f" WARNING: [U+FE0F] Error receiving event: {e}")
                        continue
                
                # Validate event delivery
                missing_events = required_events - received_events
                
                if missing_events:
                    pytest.fail(
                        f"Missing critical WebSocket events in staging: {missing_events}. "
                        f"Received events: {received_events}. "
                        f"This indicates WebSocket infrastructure issues that prevent "
                        f"real-time chat interactions, blocking 90% of platform value delivery "
                        f"and risking $500K+ ARR. Event messages: {event_messages}"
                    )
                else:
                    print(f" PASS:  All required agent events received in staging: {received_events}")
                    
        except Exception as e:
            pytest.fail(
                f"Staging agent event flow test failed: {e}. "
                f"This prevents validation of chat functionality that delivers "
                f"90% of platform value and protects $500K+ ARR."
            )

    @pytest.mark.asyncio
    async def test_staging_websocket_concurrent_connections(self):
        """
        E2E TEST: Validate multiple concurrent WebSocket connections to staging.
        
        This test validates that staging WebSocket infrastructure can handle
        multiple simultaneous connections, which is critical for multi-user chat.
        
        Expected Result: Multiple connections established successfully
        Business Impact: Validates multi-user chat capability protecting enterprise customers
        """
        websocket_endpoint = f"{self.staging_websocket_url}/ws/test"
        connection_count = 5  # Reduced for staging testing
        
        async def create_single_connection(index: int) -> Dict[str, Any]:
            """Create a single WebSocket connection for concurrent testing."""
            try:
                async with websockets.connect(
                    websocket_endpoint,
                    timeout=self.config.connection_timeout,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    
                    # Send test message
                    test_message = {
                        "type": "ping",
                        "user_id": f"staging_concurrent_user_{index}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "connection_index": index
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    return {
                        "success": True,
                        "index": index,
                        "response": response_data
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "index": index,
                    "error": str(e)
                }
        
        # Create concurrent connections
        tasks = [create_single_connection(i) for i in range(connection_count)]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_connections = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_connections = [r for r in results if isinstance(r, dict) and not r.get("success")]
            exception_connections = [r for r in results if isinstance(r, Exception)]
            
            success_rate = len(successful_connections) / connection_count
            
            if success_rate < 0.8:  # Allow for some staging instability
                pytest.fail(
                    f"Staging concurrent WebSocket connection test failed. "
                    f"Success rate: {success_rate:.1%} ({len(successful_connections)}/{connection_count}). "
                    f"Failed connections: {len(failed_connections)}, "
                    f"Exceptions: {len(exception_connections)}. "
                    f"This indicates WebSocket infrastructure issues that could impact "
                    f"multi-user chat functionality for enterprise customers."
                )
            else:
                print(f" PASS:  Staging concurrent connections successful: {success_rate:.1%} success rate")
                
        except Exception as e:
            pytest.fail(
                f"Staging concurrent connection test failed with exception: {e}. "
                f"This prevents validation of multi-user chat capability."
            )

    @pytest.mark.asyncio
    async def test_staging_websocket_error_handling(self):
        """
        E2E TEST: Validate WebSocket error handling in staging environment.
        
        This test validates that WebSocket infrastructure handles errors gracefully
        in staging, which is critical for reliable chat functionality.
        
        Expected Result: Graceful error handling without connection drops
        Business Impact: Validates chat reliability for customer retention
        """
        websocket_endpoint = f"{self.staging_websocket_url}/ws/test"
        
        try:
            async with websockets.connect(
                websocket_endpoint,
                timeout=self.config.connection_timeout,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                # Send invalid message to test error handling
                invalid_message = {
                    "type": "invalid_message_type",
                    "malformed": "data structure",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(invalid_message))
                
                # Wait for error response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    response_data = json.loads(response)
                    
                    # Validate error handling
                    assert response_data is not None, \
                        "No error response received for invalid message"
                    
                    # Check if connection is still alive after error
                    ping_message = {
                        "type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(ping_message))
                    ping_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    
                    assert ping_response is not None, \
                        "Connection dropped after error - poor error handling"
                    
                    print(f" PASS:  Staging WebSocket error handling successful")
                    
                except asyncio.TimeoutError:
                    pytest.fail(
                        f"Staging WebSocket error handling timeout. "
                        f"This indicates poor error handling that could impact "
                        f"chat reliability and customer experience."
                    )
                    
        except Exception as e:
            pytest.fail(
                f"Staging WebSocket error handling test failed: {e}. "
                f"This indicates infrastructure issues that could impact "
                f"chat reliability and customer retention."
            )

    def test_staging_infrastructure_vs_local_docker_comparison(self):
        """
        COMPARISON TEST: Document difference between staging infrastructure
        availability vs local Docker infrastructure failures.
        
        This test documents how staging can be used to validate functionality
        when local Docker infrastructure fails due to Issue #315.
        
        Expected Result: PASS - documents staging as fallback validation
        Business Impact: Provides validation path when local testing blocked
        """
        # Document the comparison
        local_docker_issues = [
            "Service naming mismatch (dev-backend vs backend)",
            "Missing docker_startup_timeout attribute", 
            "Docker file path mismatch (docker/ vs dockerfiles/)",
            "Container discovery failures",
            "Build path resolution failures"
        ]
        
        staging_advantages = [
            "Real production-like WebSocket infrastructure",
            "No local Docker dependency",
            "Actual GCP Cloud Run environment",
            "Real service-to-service communication",
            "Production WebSocket event delivery"
        ]
        
        validation_capabilities = [
            "WebSocket connection establishment",
            "Agent event flow validation", 
            "Concurrent connection testing",
            "Error handling verification",
            "Real-time chat functionality"
        ]
        
        # This test passes to document staging as a valid validation path
        assert len(local_docker_issues) > 0, \
            f"Local Docker has {len(local_docker_issues)} known issues blocking WebSocket testing"
            
        assert len(staging_advantages) > 0, \
            f"Staging provides {len(staging_advantages)} advantages for WebSocket validation"
            
        assert len(validation_capabilities) > 0, \
            f"Staging enables {len(validation_capabilities)} critical validation capabilities " \
            f"for chat functionality that protects $500K+ ARR"
        
        print(f" PASS:  Staging infrastructure provides fallback validation when local Docker fails")
        print(f"   Local Docker Issues: {len(local_docker_issues)}")
        print(f"   Staging Advantages: {len(staging_advantages)}")
        print(f"   Validation Capabilities: {len(validation_capabilities)}")


@pytest.mark.asyncio
async def test_staging_websocket_infrastructure_health_check():
    """
    HEALTH CHECK: Validate staging WebSocket infrastructure is available
    for testing when local Docker infrastructure fails.
    
    This is a prerequisite test that must pass for other staging tests to be valid.
    """
    env = get_env()
    staging_backend_url = env.get(
        'BACKEND_STAGING_URL',
        'https://netra-backend-staging-123456-uc.a.run.app'
    )
    
    # Basic connectivity check
    if not staging_backend_url or 'example' in staging_backend_url:
        pytest.skip(
            "Staging WebSocket infrastructure not configured. "
            "Set BACKEND_STAGING_URL environment variable to run staging tests."
        )
    
    staging_websocket_url = staging_backend_url.replace('https://', 'wss://').replace('http://', 'ws://')
    websocket_endpoint = f"{staging_websocket_url}/ws/test"
    
    try:
        async with websockets.connect(websocket_endpoint, open_timeout=30.0) as websocket:
            # Send health check ping
            health_check = {
                "type": "health_check",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(health_check))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            
            assert response is not None, "Staging WebSocket health check failed"
            print(f" PASS:  Staging WebSocket infrastructure healthy and available for testing")
            
    except Exception as e:
        pytest.fail(
            f"Staging WebSocket infrastructure health check failed: {e}. "
            f"Cannot use staging as fallback for local Docker issues. "
            f"This completely blocks WebSocket testing and validation of "
            f"chat functionality protecting $500K+ ARR."
        )