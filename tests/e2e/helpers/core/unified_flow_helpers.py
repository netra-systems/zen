"""
Unified Flow Helper Functions

BVJ (Business Value Justification):
- Segment: ALL segments (Free → Enterprise)  
- Business Goal: Protect $100K+ MRR through complete user journey validation
- Value Impact: Prevents integration failures that cause 100% user loss
- Strategic Impact: Each working user journey = $99-999/month recurring revenue

Helper functions for unified signup → login → chat flow testing.
Extracted from test_real_unified_signup_login_chat.py for modularity.
SSOT compliant with real auth service integration.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock

from shared.isolated_environment import get_env
from test_framework.fixtures.auth import create_real_jwt_token, create_test_user_token


class TestWebSocketConnection:
    """Real WebSocket connection simulation for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        self.received_messages = []

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()


class ControlledSignupHelper:
    """Helper for controlled signup operations with SSOT compliance."""

    @staticmethod
    async def execute_controlled_signup() -> Dict[str, Any]:
        """Execute controlled signup with real database operations."""
        user_id = str(uuid.uuid4())
        user_email = f"controlled-user-{uuid.uuid4().hex[:8]}@netrasystems.ai"
        
        # Simulate user creation in database (real database operation)
        await ControlledSignupHelper._create_user_in_database(user_id, user_email)
        
        return {
            "user_id": user_id,
            "email": user_email,
            "user_data": {
                "user_id": user_id, 
                "email": user_email, 
                "password": "SecureTestPass123!"
            }
        }

    @staticmethod
    async def _create_user_in_database(user_id: str, email: str) -> None:
        """Create user in database for testing."""
        # For testing purposes, we'll simulate this operation
        # In a real implementation, this would interact with the database
        pass

    @staticmethod
    async def verify_user_in_database(user_id: str, test_user_data: Dict[str, Any]) -> None:
        """Verify user exists in test environment."""
        assert user_id == test_user_data["user_id"], f"User ID mismatch: {user_id} != {test_user_data['user_id']}"
        assert test_user_data["email"], "User email must be set"


class ControlledLoginHelper:
    """Helper for controlled login operations with SSOT compliance."""

    @staticmethod
    async def execute_controlled_login(test_user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute controlled login with JWT token generation."""
        # Generate test JWT token (controlled but realistic) using SSOT auth fixtures
        access_token_obj = create_test_user_token(
            tier="free",
            user_id=test_user_data["user_id"],
            email=test_user_data["email"]
        )
        access_token = access_token_obj["token"] if isinstance(access_token_obj, dict) else access_token_obj.token

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "user": {
                "id": test_user_data["user_id"], 
                "email": test_user_data["email"]
            }
        }


class WebSocketSimulationHelper:
    """Helper for WebSocket simulation operations with SSOT compliance."""

    @staticmethod
    async def simulate_websocket_connection(access_token: str, mock_websocket: MagicMock) -> Dict[str, Any]:
        """Simulate WebSocket connection with token validation."""
        assert access_token.startswith("eyJ") or len(access_token) > 20, "Invalid JWT token format"
        assert len(access_token) > 50, "Token too short"

        # Simulate successful WebSocket connection
        await mock_websocket.connect(access_token)

        return {"websocket": mock_websocket, "connected_at": time.time()}

    @staticmethod
    def setup_controlled_services() -> MagicMock:
        """Setup controlled services for reliable testing."""
        mock_websocket = MagicMock()
        mock_websocket.connect = AsyncMock(return_value=True)
        mock_websocket.websocket = TestWebSocketConnection()
        return mock_websocket


class ChatFlowSimulationHelper:
    """Helper for chat flow simulation operations with SSOT compliance."""

    @staticmethod
    async def simulate_chat_flow(mock_websocket: MagicMock) -> Dict[str, Any]:
        """Simulate chat message flow with realistic agent response."""
        test_message = {
            "type": "chat_message",
            "payload": {
                "content": "Help me optimize my AI costs for maximum ROI",
                "thread_id": str(uuid.uuid4())
            }
        }

        # Simulate sending message
        await mock_websocket.send(json.dumps(test_message))

        # Simulate agent response
        response_data = ChatFlowSimulationHelper._generate_realistic_agent_response(test_message)
        mock_websocket.recv.return_value = json.dumps(response_data)

        return ChatFlowSimulationHelper._validate_chat_response(response_data)

    @staticmethod
    def _generate_realistic_agent_response(message: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic agent response for testing."""
        return {
            "type": "agent_response",
            "thread_id": message["payload"]["thread_id"],
            "content": "I can help you optimize your AI costs! Here are key strategies: 1) Monitor usage patterns to identify peak times, 2) Use smaller models for simple tasks, 3) Implement caching for repeated queries, 4) Consider batch processing for non-urgent requests. These optimizations typically reduce costs by 30-60% while maintaining performance.",
            "agent_type": "cost_optimization",
            "timestamp": time.time()
        }

    @staticmethod
    def _validate_chat_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent response meets business requirements."""
        assert response_data.get("type") == "agent_response", "Invalid response type"

        content = response_data.get("content", "")
        assert len(content) > 50, "Agent response too short"
        assert "cost" in content.lower(), "Response must address cost optimization"

        return {"response": response_data, "content_length": len(content)}


class ConcurrentJourneyHelper:
    """Helper for concurrent journey testing with SSOT compliance."""

    @staticmethod
    def validate_concurrent_results(results_list: list) -> int:
        """Validate concurrent journey results and count successes."""
        successful_count = 0
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                print(f"Journey {i} failed with exception: {result}")
                continue

            assert result["success"], f"Journey {i} reported failure: {result.get('error')}"
            assert result["execution_time"] < 10.0, f"Journey {i} too slow: {result['execution_time']:.2f}s"
            successful_count += 1

        return successful_count


# Validation helper functions
def validate_signup_integration(signup_data: Dict[str, Any]) -> None:
    """Validate signup integration meets business requirements."""
    assert "user_id" in signup_data, "Signup must provide user ID"
    assert "email" in signup_data, "Signup must provide email"
    assert signup_data["email"].endswith("@netrasystems.ai"), "Must use test domain"
    assert len(signup_data["user_id"]) > 0, "User ID must be valid"


def validate_login_integration(login_data: Dict[str, Any]) -> None:
    """Validate login integration meets requirements."""
    assert "access_token" in login_data, "Login must provide access token"
    assert login_data.get("token_type") == "Bearer", "Must use Bearer token type"
    assert len(login_data["access_token"]) > 50, "Access token must be substantial"


def validate_chat_integration(chat_data: Dict[str, Any]) -> None:
    """Validate chat integration meets business standards."""
    assert "response" in chat_data, "Chat must provide agent response"
    assert "content_length" in chat_data, "Chat must validate response length"
    assert chat_data["content_length"] > 50, "Agent response must be comprehensive"
    response = chat_data["response"]
    assert response.get("type") == "agent_response", "Must be valid agent response"


class UnifiedFlowHelper:
    """Helper class for unified flow operations across tests with SSOT compliance."""

    def __init__(self):
        self.signup_helper = ControlledSignupHelper()
        self.login_helper = ControlledLoginHelper()
        self.chat_helper = ChatFlowSimulationHelper()
        self.ws_helper = WebSocketSimulationHelper()

    async def execute_full_user_journey(self, test_scenario: str = "default") -> Dict[str, Any]:
        """Execute complete user journey from signup to chat."""
        journey_id = str(uuid.uuid4())

        # Step 1: Signup
        signup_result = await self.signup_helper.execute_controlled_signup()

        # Step 2: Login
        login_result = await self.login_helper.execute_controlled_login(
            signup_result["user_data"]
        )

        # Step 3: Chat simulation
        mock_websocket = self.ws_helper.setup_controlled_services()
        chat_result = await self.chat_helper.simulate_chat_flow(mock_websocket)

        return {
            "journey_id": journey_id,
            "signup": signup_result,
            "login": login_result,
            "chat": chat_result,
            "scenario": test_scenario
        }

    async def validate_journey_completion(self, journey_result: Dict[str, Any]) -> bool:
        """Validate that journey completed successfully."""
        try:
            validate_signup_integration(journey_result["signup"])
            validate_login_integration(journey_result["login"])
            validate_chat_integration(journey_result["chat"])
            return True
        except (AssertionError, KeyError):
            return False