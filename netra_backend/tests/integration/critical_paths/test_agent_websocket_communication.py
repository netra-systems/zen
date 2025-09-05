#!/usr/bin/env python3
"""
Comprehensive Agent WebSocket Communication Test

This test validates:
1. Agent creation via WebSocket
2. Message passing between agents
3. Agent state management and synchronization
4. Error handling and recovery
5. Concurrent agent operations
6. Agent supervisor functionality
"""

import asyncio
import json
import uuid
import pytest
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from shared.isolated_environment import IsolatedEnvironment

from test_framework.test_patterns import L3IntegrationTest


class MessageType(Enum):
    """WebSocket message types."""
    AGENT_CREATE = "agent_create"
    AGENT_MESSAGE = "agent_message"
    AGENT_STATUS = "agent_status"
    AGENT_RESPONSE = "agent_response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class AgentTestMessage:
    """Test message for agents."""
    message_id: str
    message_type: MessageType
    agent_id: str
    content: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "type": self.message_type.value,
            "agent_id": self.agent_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


class AgentWebSocketTester:
    """WebSocket agent communication tester."""
    
    def __init__(self, websocket_url: str, auth_token: str):
        self.websocket_url = websocket_url
        self.auth_token = auth_token
        self.websocket = None
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.messages: List[Dict[str, Any]] = []
        self.response_futures: Dict[str, asyncio.Future] = {}
        
    async def connect(self):
        """Connect to WebSocket with authentication."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        self.websocket = await websockets.connect(
            self.websocket_url,
            additional_headers=headers
        )
        
        # Start message handler
        asyncio.create_task(self._handle_messages())
        
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
    async def _handle_messages(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.messages.append(data)
                
                # Handle specific message types
                if data.get("type") == "agent_response":
                    message_id = data.get("message_id")
                    if message_id in self.response_futures:
                        future = self.response_futures.pop(message_id)
                        if not future.done():
                            future.set_result(data)
                            
                elif data.get("type") == "agent_status":
                    agent_id = data.get("agent_id")
                    if agent_id:
                        self.agents[agent_id] = data.get("status", {})
                        
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Error handling messages: {e}")
            
    async def send_message(self, message: AgentTestMessage) -> Dict[str, Any]:
        """Send message and wait for response."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
            
        # Create future for response
        future = asyncio.Future()
        self.response_futures[message.message_id] = future
        
        # Send message
        await self.websocket.send(json.dumps(message.to_dict()))
        
        # Wait for response with timeout
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self.response_futures.pop(message.message_id, None)
            raise TimeoutError(f"No response for message {message.message_id}")
            
    async def create_agent(self, agent_type: str, capabilities: List[str] = None) -> str:
        """Create a new agent."""
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        message = AgentTestMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.AGENT_CREATE,
            agent_id=agent_id,
            content={
                "agent_type": agent_type,
                "capabilities": capabilities or [],
                "config": {
                    "timeout": 30,
                    "max_retries": 3
                }
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        response = await self.send_message(message)
        if response.get("status") == "success":
            self.agents[agent_id] = {
                "type": agent_type,
                "capabilities": capabilities or [],
                "status": "active"
            }
            return agent_id
        else:
            raise RuntimeError(f"Failed to create agent: {response}")
            
    async def send_agent_message(self, agent_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to specific agent."""
        message = AgentTestMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.AGENT_MESSAGE,
            agent_id=agent_id,
            content=content,
            timestamp=datetime.now(timezone.utc)
        )
        
        return await self.send_message(message)
        
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent status."""
        message = AgentTestMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.AGENT_STATUS,
            agent_id=agent_id,
            content={},
            timestamp=datetime.now(timezone.utc)
        )
        
        response = await self.send_message(message)
        return response.get("content", {})
        
    async def wait_for_agent_completion(self, agent_id: str, task_id: str, timeout: float = 60.0):
        """Wait for agent task completion."""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            status = await self.get_agent_status(agent_id)
            if status.get("current_task") != task_id:
                return status
            await asyncio.sleep(1.0)
            
        raise TimeoutError(f"Agent {agent_id} did not complete task {task_id}")


class TestAgentWebSocketCommunication(L3IntegrationTest):
    """Test agent communication via WebSocket."""
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_basic_communication(self):
        """Test agent creation and basic message exchange."""
        user_data = await self.create_test_user("agent_ws_test1@test.com")
        token = await self.get_auth_token(user_data)
        
        # Create WebSocket connection
        websocket_url = "ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create a supervisor agent
            supervisor_id = await tester.create_agent("supervisor", ["coordination", "task_management"])
            assert supervisor_id in tester.agents
            assert tester.agents[supervisor_id]["type"] == "supervisor"
            
            # Send a basic message to the supervisor
            response = await tester.send_agent_message(supervisor_id, {
                "action": "ping",
                "data": {"test": "hello"}
            })
            
            assert response["status"] == "success"
            assert "pong" in response.get("content", {}).get("action", "")
            
        finally:
            await tester.disconnect()
            
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self):
        """Test coordination between multiple agents."""
        user_data = await self.create_test_user("agent_ws_test2@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = f"ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create supervisor and worker agents
            supervisor_id = await tester.create_agent("supervisor", ["coordination"])
            worker1_id = await tester.create_agent("worker", ["data_processing"])
            worker2_id = await tester.create_agent("worker", ["analysis"])
            
            # Create collaborative task
            task_id = str(uuid.uuid4())
            response = await tester.send_agent_message(supervisor_id, {
                "action": "coordinate_task",
                "task_id": task_id,
                "workers": [worker1_id, worker2_id],
                "task": {
                    "type": "data_analysis",
                    "data": [1, 2, 3, 4, 5],
                    "steps": ["process", "analyze", "summarize"]
                }
            })
            
            assert response["status"] == "success"
            
            # Wait for task completion
            final_status = await tester.wait_for_agent_completion(supervisor_id, task_id)
            assert final_status["status"] == "completed"
            assert "result" in final_status
            
        finally:
            await tester.disconnect()
            
    @pytest.mark.asyncio
    async def test_agent_error_handling_and_recovery(self):
        """Test agent error handling and recovery mechanisms."""
        user_data = await self.create_test_user("agent_ws_test3@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = f"ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create agent
            agent_id = await tester.create_agent("processor", ["error_recovery"])
            
            # Send message that will cause error
            response = await tester.send_agent_message(agent_id, {
                "action": "divide",
                "values": [10, 0]  # Division by zero
            })
            
            # Should receive error response
            assert response["status"] == "error"
            assert "division by zero" in response.get("error", "").lower()
            
            # Agent should still be responsive
            ping_response = await tester.send_agent_message(agent_id, {
                "action": "ping"
            })
            assert ping_response["status"] == "success"
            
        finally:
            await tester.disconnect()
            
    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self):
        """Test concurrent operations across multiple agents."""
        user_data = await self.create_test_user("agent_ws_test4@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = f"ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create multiple agents
            agent_ids = []
            for i in range(3):
                agent_id = await tester.create_agent(f"worker_{i}", ["concurrent_processing"])
                agent_ids.append(agent_id)
            
            # Send concurrent tasks
            tasks = []
            for i, agent_id in enumerate(agent_ids):
                task = tester.send_agent_message(agent_id, {
                    "action": "process",
                    "data": f"task_{i}",
                    "delay": 2  # 2 second processing time
                })
                tasks.append(task)
            
            # Wait for all to complete
            start_time = asyncio.get_event_loop().time()
            responses = await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()
            
            # All should succeed
            for response in responses:
                assert response["status"] == "success"
            
            # Should complete concurrently (not sequentially)
            total_time = end_time - start_time
            assert total_time < 5  # Should be less than 3*2 seconds
            
        finally:
            await tester.disconnect()
            
    @pytest.mark.asyncio
    async def test_agent_state_synchronization(self):
        """Test agent state management and synchronization."""
        user_data = await self.create_test_user("agent_ws_test5@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = f"ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create stateful agent
            agent_id = await tester.create_agent("stateful", ["state_management"])
            
            # Set initial state
            response = await tester.send_agent_message(agent_id, {
                "action": "set_state",
                "key": "counter",
                "value": 0
            })
            assert response["status"] == "success"
            
            # Increment state multiple times
            for i in range(5):
                response = await tester.send_agent_message(agent_id, {
                    "action": "increment_counter"
                })
                assert response["status"] == "success"
                assert response["content"]["counter"] == i + 1
            
            # Verify final state
            status = await tester.get_agent_status(agent_id)
            assert status.get("state", {}).get("counter") == 5
            
        finally:
            await tester.disconnect()
            
    @pytest.mark.asyncio 
    async def test_agent_message_routing_and_filtering(self):
        """Test message routing and filtering between agents."""
        user_data = await self.create_test_user("agent_ws_test6@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = f"ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create router agent
            router_id = await tester.create_agent("router", ["message_routing"])
            
            # Create target agents
            target1_id = await tester.create_agent("target", ["data_processing"])
            target2_id = await tester.create_agent("target", ["analysis"])
            
            # Configure routing rules
            await tester.send_agent_message(router_id, {
                "action": "configure_routing",
                "rules": [
                    {"filter": {"type": "data"}, "target": target1_id},
                    {"filter": {"type": "analysis"}, "target": target2_id}
                ]
            })
            
            # Send routed messages
            response1 = await tester.send_agent_message(router_id, {
                "action": "route_message",
                "message": {"type": "data", "content": "process this"}
            })
            
            response2 = await tester.send_agent_message(router_id, {
                "action": "route_message", 
                "message": {"type": "analysis", "content": "analyze this"}
            })
            
            # Verify routing worked
            assert response1["status"] == "success"
            assert response1["content"]["routed_to"] == target1_id
            
            assert response2["status"] == "success"
            assert response2["content"]["routed_to"] == target2_id
            
        finally:
            await tester.disconnect()
            
    @pytest.mark.asyncio
    async def test_agent_lifecycle_management(self):
        """Test complete agent lifecycle: create, run, pause, resume, terminate."""
        user_data = await self.create_test_user("agent_ws_test7@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = f"ws://localhost:8000/websocket"
        tester = AgentWebSocketTester(websocket_url, token)
        
        try:
            await tester.connect()
            
            # Create agent
            agent_id = await tester.create_agent("lifecycle_test", ["lifecycle_management"])
            
            # Start long-running task
            task_response = await tester.send_agent_message(agent_id, {
                "action": "start_long_task",
                "duration": 10
            })
            task_id = task_response["content"]["task_id"]
            
            # Pause task
            pause_response = await tester.send_agent_message(agent_id, {
                "action": "pause_task",
                "task_id": task_id
            })
            assert pause_response["status"] == "success"
            
            # Verify paused
            status = await tester.get_agent_status(agent_id)
            assert status["task_status"] == "paused"
            
            # Resume task
            resume_response = await tester.send_agent_message(agent_id, {
                "action": "resume_task",
                "task_id": task_id
            })
            assert resume_response["status"] == "success"
            
            # Terminate task
            terminate_response = await tester.send_agent_message(agent_id, {
                "action": "terminate_task", 
                "task_id": task_id
            })
            assert terminate_response["status"] == "success"
            
            # Verify terminated
            final_status = await tester.get_agent_status(agent_id)
            assert final_status["task_status"] == "terminated"
            
        finally:
            await tester.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])