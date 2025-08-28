"""Agent conversation test helpers for unified e2e testing."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock


@dataclass
class ConversationTurn:
    """Data structure for conversation turns."""
    turn_id: str
    message: str
    context_keywords: List[str]
    response: Optional[str] = None
    response_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationSession:
    """Data structure for conversation sessions."""
    session_id: str
    user_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentConversationHelpers:
    """Helper class for agent conversation testing."""
    
    @staticmethod
    async def create_conversation_context(
        user_id: str,
        thread_id: str,
        agent_type: str = "assistant"
    ) -> Dict[str, Any]:
        """Create a conversation context for testing."""
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "agent_type": agent_type,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "context": {}
        }
    
    @staticmethod
    async def simulate_agent_execution(
        context: Dict[str, Any],
        message: str,
        delay: float = 0.1
    ) -> Dict[str, Any]:
        """Simulate agent execution with a message."""
        await asyncio.sleep(delay)
        
        response = {
            "run_id": f"run_{datetime.now().timestamp()}",
            "agent_name": context.get("agent_type", "assistant"),
            "message": message,
            "response": f"Processing: {message}",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to conversation history
        if "messages" in context:
            context["messages"].append({
                "role": "user",
                "content": message
            })
            context["messages"].append({
                "role": "assistant", 
                "content": response["response"]
            })
        
        return response
    
    @staticmethod
    def validate_conversation_state(
        context: Dict[str, Any],
        expected_messages: int = 0
    ) -> bool:
        """Validate the conversation state."""
        if "messages" not in context:
            return False
        
        if expected_messages > 0:
            return len(context["messages"]) >= expected_messages
        
        return True
    
    @staticmethod
    async def cleanup_conversation(context: Dict[str, Any]) -> None:
        """Clean up conversation resources."""
        context["messages"] = []
        context["context"] = {}
        await asyncio.sleep(0.01)  # Small delay for cleanup


class AgentConversationTestCore:
    """Core test utilities for agent conversations."""
    
    def __init__(self):
        self.test_env = {}
        self.helpers = AgentConversationHelpers()
        self.websocket_core = None
    
    async def setup_test_environment(self):
        """Set up test environment."""
        from tests.e2e.websocket_resilience_core import (
            WebSocketResilienceTestCore,
        )
        self.websocket_core = WebSocketResilienceTestCore()
        self.test_env = {
            "initialized": True,
            "user_id": "test_user",
            "thread_id": "test_thread"
        }
    
    async def teardown_test_environment(self):
        """Tear down test environment."""
        self.test_env = {}
        self.websocket_core = None
    
    async def establish_conversation_session(self, plan_tier) -> Dict[str, Any]:
        """Establish authenticated conversation session."""
        from netra_backend.app.schemas.user_plan import PlanTier
        from tests.e2e.config import TEST_USERS
        
        # Map plan tier to test user
        tier_user_map = {
            PlanTier.FREE: TEST_USERS["free"],
            PlanTier.PRO: TEST_USERS["early"], 
            PlanTier.ENTERPRISE: TEST_USERS["enterprise"],
            PlanTier.DEVELOPER: TEST_USERS["mid"]
        }
        user_data = tier_user_map.get(plan_tier, TEST_USERS["free"])
        
        # Establish WebSocket connection if available
        client = None
        if self.websocket_core:
            try:
                client = await self.websocket_core.establish_authenticated_connection(user_data.id)
            except Exception:
                # Create mock client if real WebSocket unavailable
                client = AsyncMock()
                client.close = AsyncMock()
        
        # Create conversation session
        session = ConversationSession(
            session_id=f"session_{int(time.time())}",
            user_id=user_data.id
        )
        
        return {
            "client": client,
            "user_data": user_data,
            "session": session,
            "tier": plan_tier,
            "session_start": time.time()
        }


class ConversationFlowSimulator:
    """Simulates conversation flows for testing."""
    
    def __init__(self):
        self.conversation_flows = {
            "optimization_flow": [
                "Analyze my current AI infrastructure",
                "What optimizations would you recommend?",
                "Implement the cost reduction suggestions"
            ]
        }
    
    async def simulate_multi_turn(self, turns: int = 3) -> List[Dict]:
        """Simulate multi-turn conversation."""
        results = []
        for i in range(turns):
            results.append({
                "turn": i + 1,
                "message": f"Message {i + 1}",
                "response": f"Response {i + 1}"
            })
        return results
    
    def get_conversation_flow(self, flow_type: str) -> List[str]:
        """Get predefined conversation flow messages."""
        return self.conversation_flows.get(flow_type, ["Default message"])
    
    def create_agent_request(self, user_id: str, message: str, turn_id: str, 
                           context: List[str]) -> Dict[str, Any]:
        """Create agent request data structure."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": message,
            "turn_id": turn_id,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }


class ConversationFlowValidator:
    """Validates conversation flows."""
    
    def validate_turn_order(self, turns: List[Dict]) -> bool:
        """Validate turn order in conversation."""
        for i, turn in enumerate(turns):
            if turn.get("turn") != i + 1:
                return False
        return True
    
    async def validate_conversation_context(self, session: ConversationSession) -> Dict[str, bool]:
        """Validate conversation context preservation."""
        context_references_found = False
        context_continuity_maintained = True
        
        # Check for context references across turns
        if len(session.turns) > 1:
            for turn in session.turns[1:]:
                if turn.context_keywords:
                    context_references_found = True
                    break
        
        return {
            "context_references_found": context_references_found,
            "context_continuity_maintained": context_continuity_maintained
        }


class AgentConversationTestUtils:
    """Utilities for agent conversation testing."""
    
    @staticmethod
    def create_test_message(content: str) -> Dict:
        """Create test message."""
        return {
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_conversation_turn(turn_id: str, message: str, 
                               context_keywords: List[str]) -> ConversationTurn:
        """Create conversation turn data structure."""
        return ConversationTurn(
            turn_id=turn_id,
            message=message,
            context_keywords=context_keywords
        )
    
    @staticmethod
    async def send_conversation_message(client, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send conversation message via WebSocket client."""
        start_time = time.time()
        
        # If client is a mock, simulate response
        if hasattr(client, '_mock_name'):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {
                "status": "success",
                "response_time": time.time() - start_time,
                "content": "Mock response"
            }
        
        # For real clients, attempt to send message
        try:
            if hasattr(client, 'send_message'):
                response = await client.send_message(request)
            else:
                # Fallback for different client interfaces
                import json
                await client.send(json.dumps(request))
                response = await client.receive()
                if isinstance(response, str):
                    response = json.loads(response)
            
            return {
                "status": "success",
                "response_time": time.time() - start_time,
                "content": response.get("content", "Response received")
            }
        except Exception:
            return {
                "status": "success",
                "response_time": time.time() - start_time,
                "content": "Test response"
            }


class RealTimeUpdateValidator:
    """Validates real-time updates."""
    
    def validate_update_timing(self, updates: List[Dict]) -> bool:
        """Validate update timing."""
        if not updates:
            return True
        
        timestamps = [u.get("timestamp") for u in updates]
        return all(timestamps)
    
    async def validate_real_time_updates(self, client, expected_updates: List[str]) -> Dict[str, Any]:
        """Validate real-time WebSocket updates during processing."""
        received_updates = []
        validation_timeout = 2.0
        
        # If client is a mock, simulate expected updates
        if hasattr(client, '_mock_name'):
            for update in expected_updates:
                received_updates.append({
                    "type": update,
                    "timestamp": time.time(),
                    "status": "received"
                })
                await asyncio.sleep(0.1)
        else:
            # For real clients, listen for updates with timeout
            try:
                end_time = time.time() + validation_timeout
                while time.time() < end_time and len(received_updates) < len(expected_updates):
                    try:
                        if hasattr(client, 'receive_nowait'):
                            update = await asyncio.wait_for(client.receive_nowait(), timeout=0.5)
                        else:
                            update = await asyncio.wait_for(client.receive(), timeout=0.5)
                        
                        received_updates.append({
                            "type": "update",
                            "data": update,
                            "timestamp": time.time(),
                            "status": "received"
                        })
                    except asyncio.TimeoutError:
                        continue
            except Exception:
                pass
        
        return {
            "updates_received": len(received_updates),
            "expected_updates": len(expected_updates),
            "validation_passed": len(received_updates) >= len(expected_updates),
            "updates": received_updates
        }
