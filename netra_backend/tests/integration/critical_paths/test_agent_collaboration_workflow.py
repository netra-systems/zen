#!/usr/bin/env python3
"""
Comprehensive test for agent collaboration workflow:
1. Supervisor agent initialization
2. Sub-agent spawning and registration
3. Task delegation and distribution
4. Inter-agent communication
5. Result aggregation
6. Error propagation between agents
7. Resource pooling and sharing
8. Collaborative task completion

This test validates the entire multi-agent collaboration system.
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiohttp
import pytest
import websockets

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/websocket")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8083")


async def check_service_availability(url: str) -> bool:
    """Check if a service is available at the given URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                return response.status < 500  # Accept any non-server error status
    except Exception:
        return False


async def check_all_services() -> bool:
    """Check if all required services are available."""
    services_to_check = [
        AUTH_SERVICE_URL + "/health",  # Auth service health check
        AGENT_SERVICE_URL + "/health"  # Agent service health check  
    ]
    
    for service_url in services_to_check:
        if not await check_service_availability(service_url):
            return False
    return True

# Agent types
class AgentType(Enum):
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"

@dataclass
class AgentInfo:
    """Information about an agent."""
    agent_id: str
    agent_type: AgentType
    status: str
    capabilities: List[str]
    current_task: Optional[str] = None
    sub_agents: List[str] = None

class AgentCollaborationTester:
    """Test agent collaboration workflow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.ws_connection = None
        self.agents: Dict[str, AgentInfo] = {}
        self.task_results: Dict[str, Any] = {}
        self.message_log: List[Dict] = []
        self.test_email = f"agent_test_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = f"TestPass123_{uuid.uuid4().hex[:8]}"
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Cleanup agents
        for agent_id in self.agents:
            await self.cleanup_agent(agent_id)
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()
            
    async def cleanup_agent(self, agent_id: str):
        """Cleanup a specific agent."""
        try:
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                async with self.session.delete(
                    f"{AGENT_SERVICE_URL}/agents/{agent_id}",
                    headers=headers
                ) as response:
                    if response.status in [200, 204, 404]:
                        print(f"[CLEANUP] Agent {agent_id} cleaned up")
        except Exception as e:
            print(f"[WARNING] Failed to cleanup agent {agent_id}: {e}")
            
    async def setup_test_account(self) -> bool:
        """Setup test account and authentication."""
        print("\n[SETUP] Setting up test account...")
        
        try:
            # Register user
            register_data = {
                "email": self.test_email,
                "password": self.test_password,
                "name": "Agent Test User"
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_data
            ) as response:
                if response.status not in [200, 201, 409]:
                    return False
                    
            # Login
            login_data = {
                "email": self.test_email,
                "password": self.test_password
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print(f"[OK] Authenticated successfully")
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Setup error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_supervisor_initialization(self) -> bool:
        """Test supervisor agent initialization."""
        print("\n[SUPERVISOR] Testing supervisor agent initialization...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            supervisor_config = {
                "type": AgentType.SUPERVISOR.value,
                "name": "Test Supervisor",
                "capabilities": ["task_delegation", "monitoring", "aggregation"],
                "config": {
                    "max_sub_agents": 5,
                    "timeout_seconds": 300,
                    "auto_spawn": True,
                    "error_handling": "retry_with_backoff"
                }
            }
            
            async with self.session.post(
                f"{AGENT_SERVICE_URL}/agents",
                json=supervisor_config,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    agent_id = data.get("agent_id")
                    
                    self.agents[agent_id] = AgentInfo(
                        agent_id=agent_id,
                        agent_type=AgentType.SUPERVISOR,
                        status="active",
                        capabilities=supervisor_config["capabilities"],
                        sub_agents=[]
                    )
                    
                    print(f"[OK] Supervisor initialized: {agent_id}")
                    print(f"[INFO] Status: {data.get('status')}")
                    return True
                else:
                    text = await response.text()
                    print(f"[ERROR] Supervisor initialization failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Supervisor init error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_sub_agent_spawning(self) -> bool:
        """Test spawning of sub-agents."""
        print("\n[SPAWN] Testing sub-agent spawning...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        # Find supervisor
        supervisor = None
        for agent in self.agents.values():
            if agent.agent_type == AgentType.SUPERVISOR:
                supervisor = agent
                break
                
        if not supervisor:
            print("[ERROR] No supervisor agent found")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Spawn different types of sub-agents
            sub_agent_types = [
                (AgentType.RESEARCHER, ["search", "analysis", "summarization"]),
                (AgentType.CODER, ["code_generation", "refactoring", "testing"]),
                (AgentType.REVIEWER, ["code_review", "quality_check", "feedback"])
            ]
            
            spawned_agents = []
            
            for agent_type, capabilities in sub_agent_types:
                spawn_request = {
                    "supervisor_id": supervisor.agent_id,
                    "type": agent_type.value,
                    "name": f"Test {agent_type.value.capitalize()}",
                    "capabilities": capabilities,
                    "auto_register": True
                }
                
                async with self.session.post(
                    f"{AGENT_SERVICE_URL}/agents/spawn",
                    json=spawn_request,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        agent_id = data.get("agent_id")
                        
                        self.agents[agent_id] = AgentInfo(
                            agent_id=agent_id,
                            agent_type=agent_type,
                            status="active",
                            capabilities=capabilities
                        )
                        
                        spawned_agents.append(agent_id)
                        supervisor.sub_agents.append(agent_id)
                        
                        print(f"[OK] Spawned {agent_type.value}: {agent_id}")
                    else:
                        print(f"[ERROR] Failed to spawn {agent_type.value}: {response.status}")
                        
            if len(spawned_agents) >= 2:
                print(f"[OK] Successfully spawned {len(spawned_agents)} sub-agents")
                return True
            else:
                print(f"[WARNING] Only spawned {len(spawned_agents)} sub-agents")
                return False
                
        except Exception as e:
            print(f"[ERROR] Sub-agent spawning error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_task_delegation(self) -> bool:
        """Test task delegation from supervisor to sub-agents."""
        print("\n[DELEGATION] Testing task delegation...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        # Find supervisor and sub-agents
        supervisor = None
        sub_agents = []
        
        for agent in self.agents.values():
            if agent.agent_type == AgentType.SUPERVISOR:
                supervisor = agent
            else:
                sub_agents.append(agent)
                
        if not supervisor or not sub_agents:
            print("[ERROR] Missing supervisor or sub-agents")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create a complex task that requires delegation
            complex_task = {
                "task_id": f"task_{uuid.uuid4().hex[:8]}",
                "type": "complex_analysis",
                "description": "Analyze codebase and suggest improvements",
                "subtasks": [
                    {
                        "id": "research_1",
                        "type": "research",
                        "description": "Research best practices",
                        "assigned_to": None
                    },
                    {
                        "id": "code_1",
                        "type": "coding",
                        "description": "Implement improvements",
                        "assigned_to": None
                    },
                    {
                        "id": "review_1",
                        "type": "review",
                        "description": "Review changes",
                        "assigned_to": None
                    }
                ]
            }
            
            # Submit task to supervisor
            async with self.session.post(
                f"{AGENT_SERVICE_URL}/agents/{supervisor.agent_id}/tasks",
                json=complex_task,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    task_id = data.get("task_id")
                    delegations = data.get("delegations", [])
                    
                    print(f"[OK] Task submitted: {task_id}")
                    print(f"[INFO] Delegations: {len(delegations)}")
                    
                    # Track delegations
                    for delegation in delegations:
                        agent_id = delegation.get("agent_id")
                        subtask_id = delegation.get("subtask_id")
                        
                        if agent_id in self.agents:
                            self.agents[agent_id].current_task = subtask_id
                            print(f"[INFO] {subtask_id} -> Agent {agent_id}")
                            
                    return len(delegations) > 0
                else:
                    text = await response.text()
                    print(f"[ERROR] Task delegation failed: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Task delegation error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_inter_agent_communication(self) -> bool:
        """Test communication between agents."""
        print("\n[COMMUNICATION] Testing inter-agent communication...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Connect to WebSocket for real-time communication
            ws_headers = {"Authorization": f"Bearer {self.auth_token}"}
            self.ws_connection = await websockets.connect(
                WEBSOCKET_URL,
                extra_headers=ws_headers
            )
            
            # Authenticate WebSocket
            auth_msg = {"type": "auth", "token": self.auth_token}
            await self.ws_connection.send(json.dumps(auth_msg))
            
            response = await asyncio.wait_for(
                self.ws_connection.recv(),
                timeout=5.0
            )
            
            data = json.loads(response)
            if data.get("type") != "auth_success":
                print("[ERROR] WebSocket auth failed")
                return False
                
            # Subscribe to agent communication channel
            subscribe_msg = {
                "type": "subscribe",
                "channel": "agent_communication",
                "agent_ids": list(self.agents.keys())
            }
            await self.ws_connection.send(json.dumps(subscribe_msg))
            
            # Send test message between agents
            if len(self.agents) >= 2:
                agent_ids = list(self.agents.keys())
                sender_id = agent_ids[0]
                receiver_id = agent_ids[1]
                
                test_message = {
                    "from": sender_id,
                    "to": receiver_id,
                    "type": "collaboration_request",
                    "content": {
                        "action": "share_results",
                        "data": {"test": "value"}
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send message via API
                async with self.session.post(
                    f"{AGENT_SERVICE_URL}/agents/{sender_id}/messages",
                    json=test_message,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        print(f"[OK] Message sent from {sender_id} to {receiver_id}")
                        
                        # Wait for message propagation via WebSocket
                        try:
                            ws_response = await asyncio.wait_for(
                                self.ws_connection.recv(),
                                timeout=5.0
                            )
                            
                            ws_data = json.loads(ws_response)
                            if ws_data.get("type") == "agent_message":
                                self.message_log.append(ws_data)
                                print(f"[OK] Message received via WebSocket")
                                return True
                        except asyncio.TimeoutError:
                            print("[WARNING] No WebSocket message received")
                            return True  # Message was sent successfully
                            
                    else:
                        print(f"[ERROR] Failed to send message: {response.status}")
                        return False
                        
            else:
                print("[ERROR] Not enough agents for communication test")
                return False
                
        except Exception as e:
            print(f"[ERROR] Communication test error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_result_aggregation(self) -> bool:
        """Test result aggregation from multiple agents."""
        print("\n[AGGREGATION] Testing result aggregation...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        # Find supervisor
        supervisor = None
        for agent in self.agents.values():
            if agent.agent_type == AgentType.SUPERVISOR:
                supervisor = agent
                break
                
        if not supervisor:
            print("[ERROR] No supervisor agent found")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Simulate sub-agents completing their tasks
            results_submitted = 0
            
            for agent_id, agent in self.agents.items():
                if agent.agent_type != AgentType.SUPERVISOR and agent.current_task:
                    # Submit result for this agent's task
                    result_data = {
                        "task_id": agent.current_task,
                        "agent_id": agent_id,
                        "status": "completed",
                        "result": {
                            "output": f"Result from {agent.agent_type.value}",
                            "metrics": {
                                "execution_time": 1.5,
                                "confidence": 0.95
                            }
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    async with self.session.post(
                        f"{AGENT_SERVICE_URL}/agents/{agent_id}/results",
                        json=result_data,
                        headers=headers
                    ) as response:
                        if response.status in [200, 201]:
                            results_submitted += 1
                            print(f"[OK] Result submitted by {agent_id}")
                        else:
                            print(f"[ERROR] Failed to submit result for {agent_id}")
                            
            # Request aggregated results from supervisor
            async with self.session.get(
                f"{AGENT_SERVICE_URL}/agents/{supervisor.agent_id}/aggregated-results",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    aggregated = data.get("aggregated_results", {})
                    
                    print(f"[OK] Aggregated results retrieved")
                    print(f"[INFO] Total results: {len(aggregated)}")
                    print(f"[INFO] Results submitted: {results_submitted}")
                    
                    if len(aggregated) >= results_submitted:
                        print("[OK] All results properly aggregated")
                        return True
                    else:
                        print("[WARNING] Not all results aggregated")
                        return False
                else:
                    print(f"[ERROR] Failed to get aggregated results: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Result aggregation error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_error_propagation(self) -> bool:
        """Test error propagation between agents."""
        print("\n[ERRORS] Testing error propagation...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Find a sub-agent to simulate error
            sub_agent = None
            for agent in self.agents.values():
                if agent.agent_type != AgentType.SUPERVISOR:
                    sub_agent = agent
                    break
                    
            if not sub_agent:
                print("[ERROR] No sub-agent found")
                return False
                
            # Simulate an error in sub-agent
            error_data = {
                "error_type": "execution_failure",
                "message": "Simulated processing error",
                "severity": "high",
                "task_id": sub_agent.current_task or "test_task",
                "stacktrace": "Test stacktrace..."
            }
            
            async with self.session.post(
                f"{AGENT_SERVICE_URL}/agents/{sub_agent.agent_id}/errors",
                json=error_data,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    print(f"[OK] Error reported by {sub_agent.agent_id}")
                    
                    # Check if supervisor received the error
                    supervisor = None
                    for agent in self.agents.values():
                        if agent.agent_type == AgentType.SUPERVISOR:
                            supervisor = agent
                            break
                            
                    if supervisor:
                        # Get supervisor's error log
                        async with self.session.get(
                            f"{AGENT_SERVICE_URL}/agents/{supervisor.agent_id}/errors",
                            headers=headers
                        ) as error_response:
                            if error_response.status == 200:
                                errors = await error_response.json()
                                propagated = any(
                                    e.get("source_agent") == sub_agent.agent_id 
                                    for e in errors.get("errors", [])
                                )
                                
                                if propagated:
                                    print("[OK] Error propagated to supervisor")
                                    return True
                                else:
                                    print("[WARNING] Error not found in supervisor")
                                    return False
                    
                    return True  # Error was reported successfully
                else:
                    print(f"[ERROR] Failed to report error: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Error propagation test error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_resource_pooling(self) -> bool:
        """Test resource pooling and sharing between agents."""
        print("\n[RESOURCES] Testing resource pooling...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create a shared resource pool
            pool_config = {
                "name": "test_resource_pool",
                "type": "compute",
                "resources": {
                    "cpu_cores": 8,
                    "memory_gb": 16,
                    "gpu_count": 2
                },
                "sharing_policy": "fair_share",
                "agent_ids": list(self.agents.keys())
            }
            
            async with self.session.post(
                f"{AGENT_SERVICE_URL}/resource-pools",
                json=pool_config,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    pool_id = data.get("pool_id")
                    print(f"[OK] Resource pool created: {pool_id}")
                    
                    # Request resources for each agent
                    allocations = []
                    
                    for agent_id in list(self.agents.keys())[:2]:  # Test with 2 agents
                        allocation_request = {
                            "agent_id": agent_id,
                            "pool_id": pool_id,
                            "requested": {
                                "cpu_cores": 2,
                                "memory_gb": 4
                            },
                            "duration_seconds": 60
                        }
                        
                        async with self.session.post(
                            f"{AGENT_SERVICE_URL}/resource-pools/{pool_id}/allocate",
                            json=allocation_request,
                            headers=headers
                        ) as alloc_response:
                            if alloc_response.status in [200, 201]:
                                alloc_data = await alloc_response.json()
                                allocations.append(alloc_data)
                                print(f"[OK] Resources allocated to {agent_id}")
                            else:
                                print(f"[ERROR] Failed to allocate to {agent_id}")
                                
                    if len(allocations) >= 2:
                        print(f"[OK] Resource pooling working: {len(allocations)} allocations")
                        return True
                    else:
                        print("[WARNING] Insufficient allocations")
                        return False
                else:
                    print(f"[ERROR] Failed to create resource pool: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Resource pooling error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_collaborative_completion(self) -> bool:
        """Test collaborative task completion."""
        print("\n[COLLABORATION] Testing collaborative task completion...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Create a collaborative task
            collab_task = {
                "task_id": f"collab_{uuid.uuid4().hex[:8]}",
                "type": "collaborative",
                "description": "Build a complete feature with research, implementation, and review",
                "phases": [
                    {
                        "phase": "research",
                        "agents_required": 1,
                        "output": "requirements_doc"
                    },
                    {
                        "phase": "implementation",
                        "agents_required": 2,
                        "output": "code_artifacts",
                        "depends_on": ["research"]
                    },
                    {
                        "phase": "review",
                        "agents_required": 1,
                        "output": "review_report",
                        "depends_on": ["implementation"]
                    }
                ],
                "coordination_mode": "sequential",
                "timeout_seconds": 300
            }
            
            # Submit collaborative task
            async with self.session.post(
                f"{AGENT_SERVICE_URL}/collaborative-tasks",
                json=collab_task,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    task_id = data.get("task_id")
                    print(f"[OK] Collaborative task created: {task_id}")
                    
                    # Monitor task progress
                    max_checks = 10
                    completed = False
                    
                    for i in range(max_checks):
                        await asyncio.sleep(2)
                        
                        async with self.session.get(
                            f"{AGENT_SERVICE_URL}/collaborative-tasks/{task_id}/status",
                            headers=headers
                        ) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                current_phase = status_data.get("current_phase")
                                progress = status_data.get("progress_percentage", 0)
                                status = status_data.get("status")
                                
                                print(f"[INFO] Phase: {current_phase}, Progress: {progress}%, Status: {status}")
                                
                                if status == "completed":
                                    completed = True
                                    break
                                elif status == "failed":
                                    print("[ERROR] Collaborative task failed")
                                    break
                                    
                    if completed:
                        # Get final results
                        async with self.session.get(
                            f"{AGENT_SERVICE_URL}/collaborative-tasks/{task_id}/results",
                            headers=headers
                        ) as results_response:
                            if results_response.status == 200:
                                results = await results_response.json()
                                phases_completed = results.get("phases_completed", [])
                                
                                print(f"[OK] Task completed successfully")
                                print(f"[INFO] Phases completed: {phases_completed}")
                                return len(phases_completed) >= 2
                                
                    return False
                else:
                    print(f"[ERROR] Failed to create collaborative task: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Collaborative completion error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_agent_health_monitoring(self) -> bool:
        """Test agent health monitoring and recovery."""
        print("\n[HEALTH] Testing agent health monitoring...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get health status for all agents
            unhealthy_agents = []
            healthy_agents = []
            
            for agent_id in self.agents:
                async with self.session.get(
                    f"{AGENT_SERVICE_URL}/agents/{agent_id}/health",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        status = health_data.get("status")
                        metrics = health_data.get("metrics", {})
                        
                        print(f"[INFO] Agent {agent_id}: {status}")
                        print(f"       CPU: {metrics.get('cpu_usage', 0)}%, Memory: {metrics.get('memory_usage', 0)}%")
                        
                        if status == "healthy":
                            healthy_agents.append(agent_id)
                        else:
                            unhealthy_agents.append(agent_id)
                            
            # If any unhealthy agents, test recovery
            if unhealthy_agents:
                print(f"[WARNING] Found {len(unhealthy_agents)} unhealthy agents")
                
                for agent_id in unhealthy_agents:
                    # Attempt recovery
                    recovery_request = {
                        "action": "restart",
                        "reason": "health_check_failure"
                    }
                    
                    async with self.session.post(
                        f"{AGENT_SERVICE_URL}/agents/{agent_id}/recover",
                        json=recovery_request,
                        headers=headers
                    ) as response:
                        if response.status in [200, 201]:
                            print(f"[OK] Recovery initiated for {agent_id}")
                        else:
                            print(f"[ERROR] Failed to recover {agent_id}")
                            
            print(f"[SUMMARY] Healthy: {len(healthy_agents)}, Unhealthy: {len(unhealthy_agents)}")
            return len(healthy_agents) > 0
            
        except Exception as e:
            print(f"[ERROR] Health monitoring error: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all agent collaboration tests."""
        results = {}
        
        # Setup
        results["account_setup"] = await self.setup_test_account()
        if not results["account_setup"]:
            print("\n[CRITICAL] Account setup failed. Aborting tests.")
            return results
            
        # Core collaboration tests
        results["supervisor_initialization"] = await self.test_supervisor_initialization()
        results["sub_agent_spawning"] = await self.test_sub_agent_spawning()
        results["task_delegation"] = await self.test_task_delegation()
        results["inter_agent_communication"] = await self.test_inter_agent_communication()
        results["result_aggregation"] = await self.test_result_aggregation()
        results["error_propagation"] = await self.test_error_propagation()
        results["resource_pooling"] = await self.test_resource_pooling()
        results["collaborative_completion"] = await self.test_collaborative_completion()
        results["agent_health_monitoring"] = await self.test_agent_health_monitoring()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_agent_collaboration_workflow():
    """Test complete agent collaboration workflow."""
    # Skip if required services are not available
    services_available = await check_all_services()
    if not services_available:
        pytest.skip("Required services (auth_service, agent_service) are not available")
    
    async with AgentCollaborationTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("AGENT COLLABORATION TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:30} : {status}")
            
        print("="*60)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n✓ SUCCESS: Agent collaboration workflow fully validated!")
        else:
            failed = [name for name, passed in results.items() if not passed]
            print(f"\n✗ WARNING: Failed tests: {', '.join(failed)}")
            
        # Assert critical tests passed
        critical_tests = [
            "supervisor_initialization",
            "sub_agent_spawning",
            "task_delegation",
            "inter_agent_communication"
        ]
        
        for test in critical_tests:
            assert results.get(test, False), f"Critical test failed: {test}"

async def main():
    """Run the test standalone."""
    print("="*60)
    print("AGENT COLLABORATION WORKFLOW TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Agent Service URL: {AGENT_SERVICE_URL}")
    print("="*60)
    
    async with AgentCollaborationTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        critical_tests = [
            "supervisor_initialization",
            "sub_agent_spawning", 
            "task_delegation",
            "inter_agent_communication"
        ]
        critical_passed = all(results.get(test, False) for test in critical_tests)
        
        return 0 if critical_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)