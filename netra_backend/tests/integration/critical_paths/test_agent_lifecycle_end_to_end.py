#!/usr/bin/env python3
"""
Comprehensive test to verify the complete agent lifecycle flow:
1. Agent initialization and registration
2. Task delegation and execution
3. Context management and memory
4. Error handling and recovery
5. Graceful termination and cleanup

This test runs against the actual dev environment to ensure agent system works end-to-end.
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest
import websockets

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
DEV_WEBSOCKET_URL = "ws://localhost:8000/websocket"
AUTH_SERVICE_URL = "http://localhost:8081"
AGENT_API_URL = f"{DEV_BACKEND_URL}/api/agents"

# Test credentials
TEST_USER_EMAIL = "agent_test@example.com"
TEST_USER_PASSWORD = "agenttest123"

class AgentLifecycleTester:
    """Test the complete agent lifecycle flow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.ws_connection = None
        self.agent_id: Optional[str] = None
        self.thread_id: Optional[str] = None
        self.message_queue: List[Dict] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()
            
    async def setup_authentication(self) -> bool:
        """Setup user authentication."""
        print("\n[AUTH] STEP 1: Setting up authentication...")
        
        try:
            # Register user
            register_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": "Agent Test User"
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_data
            ) as response:
                if response.status not in [200, 201, 409]:
                    print(f"[ERROR] Registration failed: {response.status}")
                    return False
                    
            # Login
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print(f"[OK] Authentication successful")
                    return True
                else:
                    print(f"[ERROR] Login failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Authentication error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_agent_initialization(self) -> bool:
        """Test agent initialization and registration."""
        print("\n[INIT] STEP 2: Initializing agent...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create agent configuration
            agent_config = {
                "name": "TestSupervisorAgent",
                "type": "supervisor",
                "configuration": {
                    "max_context_size": 8192,
                    "temperature": 0.7,
                    "model": "gpt-4",
                    "tools": ["search", "code_analysis", "task_delegation"]
                },
                "metadata": {
                    "test_id": str(uuid.uuid4()),
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/create",
                json=agent_config,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    self.agent_id = data.get("agent_id")
                    print(f"[OK] Agent initialized: {self.agent_id}")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Agent initialization failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Agent initialization error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_agent_registration(self) -> bool:
        """Test agent registration with the system."""
        print("\n[REGISTER] STEP 3: Registering agent with system...")
        
        if not self.agent_id:
            print("[ERROR] No agent ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Register agent
            registration_data = {
                "agent_id": self.agent_id,
                "capabilities": ["task_execution", "context_management", "sub_agent_creation"],
                "status": "ready"
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/{self.agent_id}/register",
                json=registration_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Agent registered: {data}")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Registration failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Registration error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_context_creation(self) -> bool:
        """Test agent context creation and management."""
        print("\n[CONTEXT] STEP 4: Creating agent context...")
        
        if not self.agent_id:
            print("[ERROR] No agent ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create context
            context_data = {
                "agent_id": self.agent_id,
                "context": {
                    "user_intent": "Test agent capabilities",
                    "task_description": "Execute a series of test operations",
                    "constraints": {
                        "max_execution_time": 300,
                        "max_sub_agents": 5
                    },
                    "initial_state": {
                        "test_mode": True,
                        "environment": "development"
                    }
                }
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/{self.agent_id}/context",
                json=context_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.thread_id = data.get("thread_id")
                    print(f"[OK] Context created: {self.thread_id}")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Context creation failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Context creation error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_task_delegation(self) -> bool:
        """Test task delegation to agent."""
        print("\n[DELEGATE] STEP 5: Delegating task to agent...")
        
        if not self.agent_id or not self.thread_id:
            print("[ERROR] Missing agent or thread ID")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create task
            task_data = {
                "thread_id": self.thread_id,
                "task": {
                    "type": "analysis",
                    "description": "Analyze system performance metrics",
                    "parameters": {
                        "metrics": ["cpu", "memory", "network"],
                        "duration": "5m",
                        "aggregation": "average"
                    },
                    "priority": "high",
                    "timeout": 60
                }
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/{self.agent_id}/execute",
                json=task_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Task delegated: {data.get('task_id')}")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Task delegation failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Task delegation error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_agent_websocket_communication(self) -> bool:
        """Test agent communication via WebSocket."""
        print("\n[WS] STEP 6: Testing agent WebSocket communication...")
        
        if not self.auth_token or not self.agent_id:
            print("[ERROR] Missing authentication or agent ID")
            return False
            
        try:
            # Connect with auth token
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            self.ws_connection = await websockets.connect(
                DEV_WEBSOCKET_URL,
                extra_headers=headers
            )
            
            # Send auth message
            auth_message = {
                "type": "auth",
                "token": self.auth_token,
                "agent_id": self.agent_id
            }
            await self.ws_connection.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=5.0
            )
            
            data = json.loads(response)
            if data.get("type") == "auth_success":
                print(f"[OK] WebSocket authenticated for agent")
                
                # Subscribe to agent events
                subscribe_message = {
                    "type": "subscribe",
                    "channels": [
                        f"agent:{self.agent_id}",
                        f"thread:{self.thread_id}"
                    ]
                }
                await self.ws_connection.send(json.dumps(subscribe_message))
                
                # Wait for subscription confirmation
                response = await asyncio.wait_for(
                    self.ws_connection.recv(),
                    timeout=5.0
                )
                
                data = json.loads(response)
                if data.get("type") == "subscribed":
                    print(f"[OK] Subscribed to agent events")
                    return True
                    
            print(f"[ERROR] WebSocket setup failed: {data}")
            return False
            
        except Exception as e:
            print(f"[ERROR] WebSocket error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_sub_agent_creation(self) -> bool:
        """Test sub-agent creation by supervisor."""
        print("\n[SUB-AGENT] STEP 7: Creating sub-agent...")
        
        if not self.agent_id:
            print("[ERROR] No agent ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create sub-agent request
            sub_agent_data = {
                "parent_agent_id": self.agent_id,
                "sub_agent_config": {
                    "name": "TestImplementationAgent",
                    "type": "implementation",
                    "configuration": {
                        "max_context_size": 4096,
                        "specialized_tools": ["code_generation", "testing"]
                    }
                }
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/{self.agent_id}/create_sub_agent",
                json=sub_agent_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Sub-agent created: {data.get('sub_agent_id')}")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Sub-agent creation failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Sub-agent creation error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_error_recovery(self) -> bool:
        """Test agent error handling and recovery."""
        print("\n[RECOVERY] STEP 8: Testing error recovery...")
        
        if not self.agent_id:
            print("[ERROR] No agent ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Send invalid task to trigger error
            invalid_task = {
                "thread_id": "invalid_thread_id",
                "task": {
                    "type": "invalid_type",
                    "parameters": None
                }
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/{self.agent_id}/execute",
                json=invalid_task,
                headers=headers
            ) as response:
                if response.status in [400, 422]:
                    # Expected error, now test recovery
                    recovery_data = {
                        "agent_id": self.agent_id,
                        "action": "reset_context",
                        "reason": "Error recovery test"
                    }
                    
                    async with self.session.post(
                        f"{AGENT_API_URL}/{self.agent_id}/recover",
                        json=recovery_data,
                        headers=headers
                    ) as recovery_response:
                        if recovery_response.status == 200:
                            data = await recovery_response.json()
                            print(f"[OK] Agent recovered: {data}")
                            return True
                        else:
                            print(f"[ERROR] Recovery failed: {recovery_response.status}")
                            return False
                else:
                    print(f"[ERROR] Expected error not triggered: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Recovery test error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_context_persistence(self) -> bool:
        """Test agent context persistence and retrieval."""
        print("\n[PERSIST] STEP 9: Testing context persistence...")
        
        if not self.agent_id or not self.thread_id:
            print("[ERROR] Missing agent or thread ID")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Update context
            context_update = {
                "thread_id": self.thread_id,
                "updates": {
                    "progress": 75,
                    "completed_tasks": ["analysis", "validation"],
                    "current_state": {
                        "phase": "execution",
                        "metrics": {
                            "tokens_used": 1500,
                            "api_calls": 12
                        }
                    }
                }
            }
            
            async with self.session.put(
                f"{AGENT_API_URL}/{self.agent_id}/context",
                json=context_update,
                headers=headers
            ) as response:
                if response.status == 200:
                    # Retrieve context to verify persistence
                    async with self.session.get(
                        f"{AGENT_API_URL}/{self.agent_id}/context/{self.thread_id}",
                        headers=headers
                    ) as get_response:
                        if get_response.status == 200:
                            data = await get_response.json()
                            if data.get("current_state", {}).get("phase") == "execution":
                                print(f"[OK] Context persisted and retrieved")
                                return True
                                
            print("[ERROR] Context persistence failed")
            return False
            
        except Exception as e:
            print(f"[ERROR] Context persistence error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_graceful_termination(self) -> bool:
        """Test agent graceful termination."""
        print("\n[TERMINATE] STEP 10: Testing graceful termination...")
        
        if not self.agent_id:
            print("[ERROR] No agent ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Send termination request
            termination_data = {
                "agent_id": self.agent_id,
                "graceful": True,
                "timeout": 30,
                "save_state": True
            }
            
            async with self.session.post(
                f"{AGENT_API_URL}/{self.agent_id}/terminate",
                json=termination_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify agent status
                    async with self.session.get(
                        f"{AGENT_API_URL}/{self.agent_id}/status",
                        headers=headers
                    ) as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            if status_data.get("status") in ["terminated", "inactive"]:
                                print(f"[OK] Agent terminated gracefully")
                                return True
                                
            print("[ERROR] Termination failed")
            return False
            
        except Exception as e:
            print(f"[ERROR] Termination error: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Setup authentication first
        results["authentication"] = await self.setup_authentication()
        if not results["authentication"]:
            print("\n[CRITICAL] Authentication failed. Aborting tests.")
            return results
            
        # Run agent lifecycle tests
        results["agent_initialization"] = await self.test_agent_initialization()
        results["agent_registration"] = await self.test_agent_registration()
        results["context_creation"] = await self.test_context_creation()
        results["task_delegation"] = await self.test_task_delegation()
        results["websocket_communication"] = await self.test_agent_websocket_communication()
        results["sub_agent_creation"] = await self.test_sub_agent_creation()
        results["error_recovery"] = await self.test_error_recovery()
        results["context_persistence"] = await self.test_context_persistence()
        results["graceful_termination"] = await self.test_graceful_termination()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_agent_lifecycle_end_to_end():
    """Test the complete agent lifecycle flow."""
    async with AgentLifecycleTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("AGENT LIFECYCLE TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:30} : {status}")
            
        print("="*60)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All agent lifecycle tests passed!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"

async def main():
    """Run the test standalone."""
    print("="*60)
    print("AGENT LIFECYCLE END-TO-END TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with AgentLifecycleTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)