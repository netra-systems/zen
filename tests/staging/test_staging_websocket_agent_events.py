"""
Test 2: Staging WebSocket Agent Events

CRITICAL: Test WebSocket agent communication flow in staging environment.
This validates the mission-critical WebSocket events that enable chat value delivery.

Business Value: Free/Early/Mid/Enterprise - Chat is King (90% value delivery)
WebSocket events enable real-time AI interactions, the core of our business value.
"""

import pytest
import asyncio
import websockets
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Required WebSocket Events for Chat Value
REQUIRED_EVENTS = [
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
]

class StagingWebSocketTestRunner:
    """Test runner for WebSocket agent event validation in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["websocket"]
        self.received_events = []
        
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for the environment."""
        return StagingConfig.get_service_url("websocket")
        
    async def get_test_token(self) -> Optional[str]:
        """Get a test token for WebSocket authentication."""
        import httpx
        
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return None
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers={"Content-Type": "application/json"},
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-ws-test-user",
                        "email": "staging-ws-test@netrasystems.ai"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
        except Exception as e:
            print(f"Token generation failed: {e}")
            
        return None
        
    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Test 2.1: Verify WebSocket connection can be established."""
        try:
            ws_url = self.get_websocket_url()
            token = await self.get_test_token()
            
            if not token:
                return {
                    "success": False,
                    "error": "Could not obtain test token",
                    "suggestion": "Check E2E_OAUTH_SIMULATION_KEY configuration"
                }
                
            # Test WebSocket connection
            headers = {"Authorization": f"Bearer {token}"}
            
            async with websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                
                # Send a ping to test connection
                ping_message = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                await websocket.send(json.dumps(ping_message))
                
                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                return {
                    "success": True,
                    "ws_url": ws_url,
                    "connection_time": response_data.get("timestamp", 0),
                    "response": response_data
                }
                
        except websockets.exceptions.WebSocketException as e:
            return {
                "success": False,
                "error": f"WebSocket connection failed: {str(e)}",
                "ws_url": ws_url if 'ws_url' in locals() else "unknown"
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "WebSocket connection timeout",
                "ws_url": ws_url if 'ws_url' in locals() else "unknown"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "ws_url": ws_url if 'ws_url' in locals() else "unknown"
            }
            
    async def test_agent_event_flow(self) -> Dict[str, Any]:
        """Test 2.2: Test full agent execution with required events."""
        try:
            ws_url = self.get_websocket_url()
            token = await self.get_test_token()
            
            if not token:
                return {
                    "success": False,
                    "error": "Could not obtain test token",
                    "events_received": []
                }
                
            headers = {"Authorization": f"Bearer {token}"}
            received_events = []
            
            async with websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                
                # Send agent execution request
                execution_request = {
                    "type": "agent_execution",
                    "request_id": str(uuid.uuid4()),
                    "agent_type": "supervisor",
                    "query": "Test staging environment connectivity and provide a simple status report",
                    "context": {
                        "environment": "staging",
                        "test_mode": True
                    }
                }
                
                await websocket.send(json.dumps(execution_request))
                
                # Listen for events with timeout
                timeout_time = time.time() + 60  # 60 second timeout for agent execution
                
                while time.time() < timeout_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(message)
                        
                        if event_data.get("type") in REQUIRED_EVENTS:
                            received_events.append(event_data.get("type"))
                            
                        # Stop when we get agent_completed
                        if event_data.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
                        
                # Check which required events we received
                events_status = {}
                for required_event in REQUIRED_EVENTS:
                    events_status[required_event] = required_event in received_events
                    
                all_events_received = all(events_status.values())
                
                return {
                    "success": len(received_events) > 0,  # At least some events
                    "all_required_events": all_events_received,
                    "events_received": received_events,
                    "events_status": events_status,
                    "total_events": len(received_events),
                    "missing_events": [event for event, received in events_status.items() if not received]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Agent event test failed: {str(e)}",
                "events_received": received_events if 'received_events' in locals() else [],
                "all_required_events": False
            }
            
    async def test_websocket_authentication(self) -> Dict[str, Any]:
        """Test 2.3: Test WebSocket authentication scenarios."""
        try:
            ws_url = self.get_websocket_url()
            
            # Test 1: No token (should fail)
            try:
                async with asyncio.timeout(10):
                    async with websockets.connect(ws_url, close_timeout=5) as websocket:
                    await websocket.send('{"type": "ping"}')
                    await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    no_token_result = "UNEXPECTED_SUCCESS"  # Should not reach here
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException):
                no_token_result = "CORRECTLY_REJECTED"
            except Exception:
                no_token_result = "CORRECTLY_REJECTED"
                
            # Test 2: Invalid token (should fail)  
            invalid_headers = {"Authorization": "Bearer invalid-token-123"}
            try:
                async with asyncio.timeout(10):
                    async with websockets.connect(ws_url, extra_headers=invalid_headers, close_timeout=5) as websocket:
                    await websocket.send('{"type": "ping"}')
                    await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    invalid_token_result = "UNEXPECTED_SUCCESS"
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException):
                invalid_token_result = "CORRECTLY_REJECTED"
            except Exception:
                invalid_token_result = "CORRECTLY_REJECTED"
                
            # Test 3: Valid token (should succeed)
            token = await self.get_test_token()
            if token:
                valid_headers = {"Authorization": f"Bearer {token}"}
                try:
                    async with asyncio.timeout(10):
                        async with websockets.connect(ws_url, extra_headers=valid_headers, close_timeout=5) as websocket:
                        await websocket.send('{"type": "ping"}')
                        await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        valid_token_result = "CORRECTLY_ACCEPTED"
                except Exception:
                    valid_token_result = "UNEXPECTED_FAILURE"
            else:
                valid_token_result = "TOKEN_GENERATION_FAILED"
                
            return {
                "success": (no_token_result == "CORRECTLY_REJECTED" and 
                           invalid_token_result == "CORRECTLY_REJECTED" and
                           valid_token_result == "CORRECTLY_ACCEPTED"),
                "no_token": no_token_result,
                "invalid_token": invalid_token_result,
                "valid_token": valid_token_result,
                "authentication_working": valid_token_result == "CORRECTLY_ACCEPTED"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Authentication test failed: {str(e)}",
                "authentication_working": False
            }
            
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all WebSocket agent event tests."""
        print(f"[WebSocket] Running WebSocket Agent Events Tests")
        print(f"Environment: {self.environment}")
        print(f"WebSocket URL: {self.get_websocket_url()}")
        print()
        
        results = {}
        
        # Test 2.1: WebSocket connection
        print("2.1 Testing WebSocket connection...")
        results["websocket_connection"] = await self.test_websocket_connection()
        print(f"     [OK] Connection: {results['websocket_connection']['success']}")
        
        # Test 2.2: Agent event flow
        print("2.2 Testing agent event flow...")
        results["agent_events"] = await self.test_agent_event_flow()
        print(f"     [OK] Agent events: {results['agent_events']['success']}")
        print(f"     [Events] Required events: {results['agent_events'].get('all_required_events', False)}")
        if results['agent_events'].get('missing_events'):
            print(f"     [WARNING] Missing events: {results['agent_events']['missing_events']}")
            
        # Test 2.3: WebSocket authentication
        print("2.3 Testing WebSocket authentication...")
        results["websocket_auth"] = await self.test_websocket_authentication()
        print(f"     [OK] Authentication: {results['websocket_auth']['success']}")
        
        # Summary
        all_passed = all(result["success"] for result in results.values())
        critical_chat_issue = not results.get("agent_events", {}).get("all_required_events", False)
        
        results["summary"] = {
            "all_tests_passed": all_passed,
            "environment": self.environment,
            "total_tests": len(results) - 1,
            "passed_tests": sum(1 for result in results.values() if isinstance(result, dict) and result.get("success", False)),
            "critical_chat_issue": critical_chat_issue,
            "websocket_url": self.get_websocket_url()
        }
        
        print()
        print(f"[Summary] {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
        if critical_chat_issue:
            print("[CRITICAL] Missing required WebSocket events - Chat functionality compromised!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging  
async def test_staging_websocket_agent_events():
    """Main test entry point for WebSocket agent events."""
    runner = StagingWebSocketTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["all_tests_passed"], f"WebSocket tests failed: {results}"
    assert not results["summary"]["critical_chat_issue"], "Missing critical WebSocket events for chat"
    assert results["agent_events"]["all_required_events"], "Not all required agent events received"


if __name__ == "__main__":
    async def main():
        runner = StagingWebSocketTestRunner()
        results = await runner.run_all_tests()
        
        if not results["summary"]["all_tests_passed"]:
            exit(1)
            
    asyncio.run(main())