"""
Test 9: Staging Agent Execution

CRITICAL: Test agent execution end-to-end in staging environment.
This validates the core AI functionality that delivers primary business value.

Business Value: Free/Early/Mid/Enterprise - Core AI Value Delivery
Agent execution is the primary value proposition - without it, the platform delivers no AI value.
"""

import pytest
import asyncio
import httpx
import websockets
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Agent Types to Test
AGENT_TYPES = [
    "supervisor",
    "triage"
]

# Required Agent Events (from mission-critical WebSocket specification)
REQUIRED_AGENT_EVENTS = [
    "agent_started",
    "agent_thinking",
    "tool_executing", 
    "tool_completed",
    "agent_completed"
]

class StagingAgentExecutionTestRunner:
    """Test runner for agent execution validation in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["agent_execution"]
        self.access_token = None
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json", 
            "User-Agent": "Netra-Staging-Agent-Test/1.0"
        }
        
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for agent communication."""
        return StagingConfig.get_service_url("websocket")
        
    async def get_test_token(self) -> Optional[str]:
        """Get test token for authenticated agent execution."""
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return None
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-agent-test-user",
                        "email": "staging-agent-test@netrasystems.ai"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
        except Exception as e:
            print(f"Token generation failed: {e}")
            
        return None
        
    async def test_agent_http_execution(self, agent_type: str) -> Dict[str, Any]:
        """Test agent execution via HTTP API."""
        if not self.access_token:
            return {
                "success": False,
                "error": "No access token available",
                "skipped": True
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare agent execution request
                execution_request = {
                    "query": f"Analyze the staging environment health and provide a brief status report. This is a test execution for agent type {agent_type}.",
                    "agent_type": agent_type,
                    "context": {
                        "environment": self.environment,
                        "test_mode": True,
                        "execution_type": "staging_validation"
                    },
                    "request_id": str(uuid.uuid4())
                }
                
                # Execute agent request
                response = await client.post(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/agents/execute",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    },
                    json=execution_request
                )
                
                execution_success = response.status_code in [200, 202]  # 200 = sync, 202 = async
                response_data = {}
                
                if execution_success:
                    try:
                        response_data = response.json()
                    except:
                        pass
                        
                return {
                    "success": execution_success,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "agent_type": agent_type,
                    "execution_id": response_data.get("execution_id"),
                    "request_id": execution_request["request_id"],
                    "execution_type": "http",
                    "response_data": response_data,
                    "error": None if execution_success else response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "agent_type": agent_type,
                "execution_type": "http",
                "error": f"HTTP agent execution failed: {str(e)}"
            }
            
    async def test_agent_websocket_execution(self, agent_type: str) -> Dict[str, Any]:
        """Test agent execution via WebSocket with event monitoring.""" 
        if not self.access_token:
            return {
                "success": False,
                "error": "No access token available",
                "skipped": True
            }
            
        try:
            ws_url = self.get_websocket_url()
            headers = {"Authorization": f"Bearer {self.access_token}"}
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
                    "agent_type": agent_type,
                    "query": f"Test agent execution in staging environment. Provide a simple status check for {agent_type} agent.",
                    "context": {
                        "environment": self.environment,
                        "test_mode": True,
                        "websocket_test": True
                    }
                }
                
                await websocket.send(json.dumps(execution_request))
                
                # Monitor for agent events
                start_time = time.time()
                timeout_time = start_time + 90  # 90 second timeout for full execution
                final_response = None
                
                while time.time() < timeout_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(message)
                        
                        event_type = event_data.get("type")
                        if event_type:
                            received_events.append(event_type)
                            
                        # Capture final response
                        if event_type == "agent_completed":
                            final_response = event_data.get("data", {})
                            break
                            
                        # Also break on error
                        if event_type == "agent_error":
                            final_response = {"error": event_data.get("error", "Agent execution error")}
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
                        
                execution_time = time.time() - start_time
                
                # Analyze received events
                required_events_received = {
                    event: event in received_events 
                    for event in REQUIRED_AGENT_EVENTS
                }
                all_required_events = all(required_events_received.values())
                
                # Determine execution success
                execution_completed = "agent_completed" in received_events
                execution_errored = "agent_error" in received_events
                execution_success = execution_completed and not execution_errored
                
                return {
                    "success": execution_success and all_required_events,
                    "execution_completed": execution_completed,
                    "execution_errored": execution_errored,
                    "execution_time": execution_time,
                    "agent_type": agent_type,
                    "execution_type": "websocket",
                    "events_received": received_events,
                    "required_events_received": required_events_received,
                    "all_required_events": all_required_events,
                    "missing_events": [event for event, received in required_events_received.items() if not received],
                    "total_events": len(received_events),
                    "final_response": final_response
                }
                
        except Exception as e:
            return {
                "success": False,
                "agent_type": agent_type,
                "execution_type": "websocket",
                "error": f"WebSocket agent execution failed: {str(e)}"
            }
            
    async def test_agent_status_endpoints(self) -> Dict[str, Any]:
        """Test 9.1: Agent status and availability endpoints."""
        print("9.1 Testing agent status endpoints...")
        
        results = {}
        
        if not self.access_token:
            return {
                "agent_status": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                }
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test agent status endpoint
                status_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/agents/status",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    }
                )
                
                status_success = status_response.status_code == 200
                status_data = {}
                
                if status_success:
                    try:
                        status_data = status_response.json()
                    except:
                        pass
                        
                # Check available agents
                available_agents = status_data.get("available_agents", [])
                supervisor_available = "supervisor" in available_agents
                triage_available = "triage" in available_agents
                
                results["agent_status"] = {
                    "success": status_success and supervisor_available,
                    "status_code": status_response.status_code,
                    "available_agents": available_agents,
                    "supervisor_available": supervisor_available,
                    "triage_available": triage_available,
                    "total_agents_available": len(available_agents),
                    "status_data": status_data
                }
                
                # Test individual agent availability
                for agent_type in AGENT_TYPES:
                    agent_info_response = await client.get(
                        f"{StagingConfig.get_service_url('netra_backend')}/api/agents/{agent_type}/info",
                        headers={
                            **self.get_base_headers(),
                            "Authorization": f"Bearer {self.access_token}"
                        }
                    )
                    
                    agent_available = agent_info_response.status_code == 200
                    agent_info = {}
                    
                    if agent_available:
                        try:
                            agent_info = agent_info_response.json()
                        except:
                            pass
                            
                    results[f"{agent_type}_availability"] = {
                        "success": agent_available,
                        "status_code": agent_info_response.status_code,
                        "agent_type": agent_type,
                        "agent_info": agent_info,
                        "agent_ready": agent_info.get("status") == "ready" if isinstance(agent_info, dict) else False
                    }
                    
        except Exception as e:
            results["agent_status"] = {
                "success": False,
                "error": f"Agent status test failed: {str(e)}"
            }
            
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all agent execution tests."""
        print(f"[U+1F916] Running Agent Execution Tests")
        print(f"Environment: {self.environment}")
        print(f"Backend URL: {StagingConfig.get_service_url('netra_backend')}")
        print(f"WebSocket URL: {self.get_websocket_url()}")
        print()
        
        # Get test token first
        print("[U+1F511] Getting test token...")
        self.access_token = await self.get_test_token()
        print(f"     Token obtained: {bool(self.access_token)}")
        print()
        
        results = {}
        
        # Test 9.1: Agent status endpoints
        status_results = await self.test_agent_status_endpoints()
        results.update(status_results)
        
        # Test 9.2: HTTP agent execution for each agent type
        print("9.2 Testing HTTP agent execution...")
        for agent_type in AGENT_TYPES:
            print(f"     Testing {agent_type} agent via HTTP...")
            http_result = await self.test_agent_http_execution(agent_type)
            results[f"{agent_type}_http_execution"] = http_result
            print(f"      PASS:  {agent_type} HTTP: {http_result['success']}")
            
        # Test 9.3: WebSocket agent execution for primary agent
        print("9.3 Testing WebSocket agent execution...")
        primary_agent = "supervisor"  # Focus on supervisor for WebSocket test
        print(f"     Testing {primary_agent} agent via WebSocket...")
        
        ws_result = await self.test_agent_websocket_execution(primary_agent)
        results[f"{primary_agent}_websocket_execution"] = ws_result
        
        print(f"      PASS:  {primary_agent} WebSocket: {ws_result['success']}")
        print(f"     [U+1F4CB] All required events: {ws_result.get('all_required_events', False)}")
        
        if ws_result.get('missing_events'):
            print(f"      WARNING: [U+FE0F]  Missing events: {ws_result['missing_events']}")
            
        # Calculate summary
        all_tests = {k: v for k, v in results.items() if isinstance(v, dict) and "success" in v}
        total_tests = len(all_tests)
        passed_tests = sum(1 for result in all_tests.values() if result["success"])
        skipped_tests = sum(1 for result in all_tests.values() if result.get("skipped", False))
        
        # Check core agent functionality
        agent_status_working = results.get("agent_status", {}).get("success", False)
        supervisor_available = results.get("supervisor_availability", {}).get("success", False)
        http_execution_working = results.get("supervisor_http_execution", {}).get("success", False)
        websocket_execution_working = results.get("supervisor_websocket_execution", {}).get("success", False)
        websocket_events_complete = results.get("supervisor_websocket_execution", {}).get("all_required_events", False)
        
        core_agent_functionality = all([
            agent_status_working,
            supervisor_available,
            http_execution_working or websocket_execution_working
        ])
        
        results["summary"] = {
            "core_agent_functionality_working": core_agent_functionality,
            "agent_status_working": agent_status_working,
            "http_execution_working": http_execution_working,
            "websocket_execution_working": websocket_execution_working,
            "websocket_events_complete": websocket_events_complete,
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "skipped_tests": skipped_tests,
            "critical_agent_failure": not core_agent_functionality
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed ({results['summary']['skipped_tests']} skipped)")
        print(f"[U+1F916] Core agent functionality: {' PASS:  Working' if core_agent_functionality else ' FAIL:  Broken'}")
        print(f"[U+1F50C] HTTP execution: {' PASS:  Working' if http_execution_working else ' FAIL:  Failed'}")
        print(f"[U+1F4E1] WebSocket execution: {' PASS:  Working' if websocket_execution_working else ' FAIL:  Failed'}")
        print(f"[U+1F4CB] WebSocket events: {' PASS:  Complete' if websocket_events_complete else ' FAIL:  Missing events'}")
        
        if results["summary"]["critical_agent_failure"]:
            print(" ALERT:  CRITICAL: Core agent functionality is broken!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_agent_execution():
    """Main test entry point for agent execution validation."""
    runner = StagingAgentExecutionTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["core_agent_functionality_working"], "Core agent functionality is not working"
    assert not results["summary"]["critical_agent_failure"], "Critical agent execution failure detected"
    assert results["summary"]["agent_status_working"], "Agent status endpoints not working"


if __name__ == "__main__":
    async def main():
        runner = StagingAgentExecutionTestRunner()
        results = await runner.run_all_tests()
        
        if results["summary"]["critical_agent_failure"]:
            exit(1)
            
    asyncio.run(main())