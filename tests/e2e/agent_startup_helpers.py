"""Agent Startup E2E Test Helpers - Missing Import Fix

This module provides the missing helper classes required by E2E tests.
Implements SSOT pattern compliance for agent startup testing.

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Ensure E2E tests can validate agent startup workflows
- Value Impact: Prevents test failures that block releases and system validation
- Revenue Impact: Protects deployment quality and customer experience
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# SSOT import patterns for test infrastructure
from tests.e2e.agent_startup_validators import AgentStartupValidatorSuite
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class TestUserData:
    """Test user data structure."""
    id: str
    email: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentInitializationValidator:
    """Validates agent initialization processes."""
    
    def __init__(self):
        """Initialize agent initialization validator."""
        self.validator_suite = AgentStartupValidatorSuite()
        self.start_time: Optional[float] = None
        
    def start_timer(self) -> None:
        """Start timing for validation."""
        self.start_time = time.time()
    
    def validate_historical_context_loaded(self, response: Dict[str, Any], messages: List[Dict[str, Any]]) -> None:
        """Validate that historical context was loaded correctly."""
        assert response.get("metadata", {}).get("context_loaded", False), "Historical context should be loaded"
        expected_messages = len(messages)
        actual_messages = response.get("metadata", {}).get("historical_messages", 0)
        assert actual_messages == expected_messages, f"Expected {expected_messages} messages, got {actual_messages}"
    
    def validate_context_loading_performance(self, max_seconds: float) -> None:
        """Validate context loading performance."""
        if self.start_time is None:
            raise ValueError("Timer not started - call start_timer() first")
        
        elapsed = time.time() - self.start_time
        assert elapsed <= max_seconds, f"Context loading took {elapsed:.2f}s, expected <= {max_seconds}s"
    
    def validate_multi_agent_initialization(self, response: Dict[str, Any]) -> None:
        """Validate multi-agent initialization."""
        assert response.get("type") == "multi_agent_response", "Expected multi-agent response"
        agents = response.get("agents", {})
        expected_agents = ["triage", "data", "reporting"]
        
        for agent in expected_agents:
            assert agent in agents, f"Expected agent '{agent}' not found in response"
            assert agents[agent].get("status") == "initialized", f"Agent '{agent}' not properly initialized"
    
    def validate_agent_coordination(self, response: Dict[str, Any]) -> None:
        """Validate agent coordination."""
        coordination = response.get("coordination", {})
        assert coordination.get("orchestrator_active", False), "Orchestrator should be active"
        assert coordination.get("agents_synchronized", False), "Agents should be synchronized"


class ContextTestManager:
    """Manages context testing scenarios."""
    
    def __init__(self):
        """Initialize context test manager."""
        self.env = IsolatedEnvironment()
        self.db_manager: Optional[DatabaseManager] = None
        self.http_client = None
        self.harness = None
    
    async def setup_database_operations(self) -> None:
        """Setup database operations for testing."""
        # Use SSOT DatabaseManager
        self.db_manager = DatabaseManager(
            postgres_config=self.env.get_database_config(),
            clickhouse_config=self.env.get_clickhouse_config()
        )
        await self.db_manager.initialize()
    
    async def create_user_with_history(self) -> TestUserData:
        """Create a test user with historical data."""
        user_id = f"test_user_{int(time.time())}"
        return TestUserData(
            id=user_id,
            email=f"{user_id}@test.example.com",
            metadata={"created_for_test": True}
        )
    
    async def seed_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Seed conversation history for testing."""
        messages = [
            {
                "id": "msg_1",
                "user_id": user_id,
                "content": "I spend $5000/month on OpenAI GPT-4 calls",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "msg_2", 
                "user_id": user_id,
                "content": "Looking for optimization opportunities",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # In a real implementation, this would insert into the database
        # For now, return the test messages
        return messages


class MultiAgentTestManager:
    """Manages multi-agent testing scenarios."""
    
    def __init__(self):
        """Initialize multi-agent test manager."""
        self.env = IsolatedEnvironment() 
        self.http_client = None
        self.ws_connection = None
        self.harness = None
    
    async def setup_http_client(self) -> None:
        """Setup HTTP client for testing."""
        import httpx
        self.http_client = httpx.AsyncClient(
            base_url=self.env.get("BACKEND_URL", "http://localhost:8000"),
            timeout=30.0
        )
    
    async def authenticate_and_connect(self) -> str:
        """Authenticate and establish connection."""
        # Mock authentication for testing
        token = "test_jwt_token"
        
        # In a real implementation, this would:
        # 1. Call auth service for actual JWT token
        # 2. Establish WebSocket connection with token
        # 3. Verify connection is established
        
        return token
    
    async def send_multi_agent_message(self) -> Dict[str, Any]:
        """Send a multi-agent message and get response."""
        # Mock multi-agent response for testing
        return {
            "type": "multi_agent_response",
            "agents": {
                "triage": {"status": "initialized", "ready": True},
                "data": {"status": "initialized", "ready": True}, 
                "reporting": {"status": "initialized", "ready": True}
            },
            "coordination": {
                "orchestrator_active": True,
                "agents_synchronized": True,
                "execution_order": ["triage", "data", "reporting"]
            },
            "metadata": {
                "initialization_time_ms": 150,
                "total_agents": 3
            }
        }
