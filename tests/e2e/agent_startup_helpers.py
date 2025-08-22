"""
Agent Startup Test Helpers - Modular components for E2E testing

Business Value Justification (BVJ):
- Segment: ALL customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Provide reusable test components for agent startup validation
- Value Impact: Reduces test duplication and ensures consistent validation patterns
- Revenue Impact: Enables comprehensive testing protecting $200K+ MRR

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Modular design for reuse across test suites
"""

import asyncio
import time
import json
import uuid
from typing import Dict, Any, Optional, List
import httpx
import websockets

from tests.config import (
    TestTier, get_test_user,
    get_auth_service_url, get_backend_service_url
)
from tests.database_test_operations import (
    UserDataOperations, ChatMessageOperations,
    UserDataOperations, ChatMessageOperations
)
from tests.database_test_connections import DatabaseConnectionManager


class ContextTestManager:
    """Manages context loading test execution and validation."""
    
    def __init__(self):
        """Initialize context test manager."""
        self.harness = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.ws_connection = None
        self.test_user = get_test_user(TestTier.MID.value)  
        self.db_manager: Optional[DatabaseConnectionManager] = None
        self.user_ops: Optional[UserDataOperations] = None
        self.message_ops: Optional[ChatMessageOperations] = None
    
    async def setup_database_operations(self) -> None:
        """Setup database operations for context testing."""
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize_connections()
        self.user_ops = UserDataOperations(self.db_manager)
        self.message_ops = ChatMessageOperations(self.db_manager)
    
    async def create_user_with_history(self) -> Dict[str, Any]:
        """Create test user with conversation history."""
        user_data = self._generate_user_data()
        await self.user_ops.create_auth_user(user_data)
        await self.user_ops.sync_to_backend(user_data)
        return user_data
    
    def _generate_user_data(self) -> Dict[str, Any]:
        """Generate test user data."""
        return {
            "id": str(uuid.uuid4()),
            "email": f"context-test-{int(time.time())}@example.com",
            "full_name": "Context Test User",
            "is_active": True,
            "role": "user",
            "created_at": time.time()
        }
    
    async def seed_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Seed conversation history for user."""
        messages = self._create_history_messages(user_id)
        for message in messages:
            await self.message_ops.store_message(message)
        return messages
    
    def _create_history_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """Create historical conversation messages."""
        return [
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "content": "What are my current AI optimization opportunities?",
                "timestamp": time.time() - 3600
            },
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "content": "I'm spending $5000/month on OpenAI GPT-4 calls",
                "timestamp": time.time() - 1800
            }
        ]


class MultiAgentTestManager:
    """Manages multi-agent orchestration initialization tests."""
    
    def __init__(self):
        """Initialize multi-agent test manager."""
        self.harness = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.ws_connection = None
        self.test_user = get_test_user(TestTier.ENTERPRISE.value)
        self.agent_responses: List[Dict[str, Any]] = []
    
    async def setup_http_client(self) -> None:
        """Setup HTTP client for API requests."""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        )
    
    async def authenticate_and_connect(self) -> str:
        """Authenticate user and establish WebSocket connection."""
        auth_url = f"{get_auth_service_url()}/auth/login"
        login_data = {
            "username": self.test_user.email,
            "password": "testpass123"
        }
        response = await self.http_client.post(auth_url, json=login_data)
        assert response.status_code == 200, f"Auth failed: {response.status_code}"
        token = response.json()["access_token"]
        await self._connect_websocket(token)
        return token
    
    async def _connect_websocket(self, token: str) -> None:
        """Connect WebSocket with JWT token."""
        ws_url = f"ws://localhost:8000/ws?token={token}"
        self.ws_connection = await websockets.connect(
            ws_url,
            extra_headers={"Authorization": f"Bearer {token}"}
        )
    
    async def send_multi_agent_message(self) -> Dict[str, Any]:
        """Send message requiring multiple agents."""
        message = {
            "type": "chat_message",
            "content": "Analyze my AI spend optimization and generate a detailed report with data insights",
            "timestamp": time.time(),
            "requires_multi_agent": True
        }
        await self.ws_connection.send(json.dumps(message))
        return await self._collect_agent_responses()
    
    async def _collect_agent_responses(self) -> Dict[str, Any]:
        """Collect responses from multiple agents."""
        responses = []
        timeout_time = time.time() + 15
        
        while time.time() < timeout_time:
            try:
                response_text = await asyncio.wait_for(self.ws_connection.recv(), timeout=3.0)
                response = json.loads(response_text)
                responses.append(response)
                
                if self._is_final_response(response):
                    break
            except asyncio.TimeoutError:
                break
        
        return {"responses": responses, "count": len(responses)}
    
    def _is_final_response(self, response: Dict[str, Any]) -> bool:
        """Check if response indicates completion."""
        return response.get("type") == "final_response" or response.get("complete", False)


class AgentInitializationValidator:
    """Validates agent initialization and context loading."""
    
    def __init__(self):
        """Initialize agent initialization validator."""
        self.start_time: Optional[float] = None
        self.expected_agents = ["triage", "data", "reporting"]
    
    def start_timer(self) -> None:
        """Start performance measurement timer."""
        self.start_time = time.time()
    
    def validate_context_loading_performance(self, max_seconds: float = 2.0) -> None:
        """Validate context loading completes within time limit."""
        assert self.start_time is not None, "Performance timer not started"
        duration = time.time() - self.start_time
        assert duration < max_seconds, f"Context loading took {duration:.2f}s, max {max_seconds}s"
    
    def validate_historical_context_loaded(self, response: Dict[str, Any], expected_messages: List[Dict[str, Any]]) -> None:
        """Validate agent loaded and used historical context."""
        content = response.get("content", "").lower()
        context_keywords = ["previous", "earlier", "history", "mentioned", "discussed"]
        has_context = any(keyword in content for keyword in context_keywords)
        assert has_context, "Agent response shows no historical context awareness"
    
    def validate_multi_agent_initialization(self, multi_response: Dict[str, Any]) -> None:
        """Validate all expected agents initialized correctly."""
        responses = multi_response.get("responses", [])
        assert len(responses) >= 2, f"Expected multiple agent responses, got {len(responses)}"
        
        agent_types_found = set()
        for response in responses:
            agent_type = self._extract_agent_type(response)
            if agent_type:
                agent_types_found.add(agent_type)
        
        assert len(agent_types_found) >= 2, f"Expected multiple agent types, found: {agent_types_found}"
    
    def _extract_agent_type(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract agent type from response."""
        metadata = response.get("metadata", {})
        agent_type = metadata.get("agent_type")
        
        if not agent_type:
            content = response.get("content", "").lower()
            for expected_agent in self.expected_agents:
                if expected_agent in content:
                    return expected_agent
        
        return agent_type
    
    def validate_agent_coordination(self, multi_response: Dict[str, Any]) -> None:
        """Validate agents coordinated properly."""
        responses = multi_response.get("responses", [])
        
        coordination_found = False
        for response in responses:
            content = response.get("content", "").lower()
            coordination_keywords = ["analysis", "report", "data", "insights"]
            if any(keyword in content for keyword in coordination_keywords):
                coordination_found = True
                break
        
        assert coordination_found, "No evidence of multi-agent coordination"
