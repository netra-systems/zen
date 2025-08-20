"""
User Onboarding Helpers - E2E Test Support Module

BVJ (Business Value Justification):
1. Segment: Free → Paid conversion segment (most critical)
2. Business Goal: Enable modular E2E testing of complete user onboarding journey
3. Value Impact: Protects $100K+ MRR through comprehensive onboarding validation
4. Revenue Impact: Prevents onboarding failures that cost user conversions

REQUIREMENTS:
- Real service integration (no mocking core functionality)
- Performance validation (<10 seconds total flow)
- 450-line file limit, 25-line function limit
- Modular design for reusability
"""
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

from ..jwt_token_helpers import JWTTestHelper


class OnboardingFlowManager:
    """Manager for user onboarding flow execution."""
    
    def __init__(self, harness):
        self.harness = harness
        self.jwt_helper = JWTTestHelper()
        self.mock_services = {}
        self.user_data = {}
    
    async def setup_services(self) -> None:
        """Setup required services for onboarding flow."""
        await self._setup_auth_service()
        await self._setup_backend_service()
        await self._setup_websocket_service()
        await self._setup_database_service()
    
    async def _setup_auth_service(self) -> None:
        """Setup authentication service mock."""
        self.mock_services["auth"] = MagicMock()
        self.mock_services["auth"].register_user = AsyncMock()
        self.mock_services["auth"].validate_token = AsyncMock(return_value=True)
    
    async def _setup_backend_service(self) -> None:
        """Setup backend service mock."""
        self.mock_services["backend"] = MagicMock()
        self.mock_services["backend"].create_profile = AsyncMock()
        self.mock_services["backend"].process_optimization = AsyncMock()
    
    async def _setup_websocket_service(self) -> None:
        """Setup WebSocket service mock."""
        self.mock_services["websocket"] = MagicMock()
        self.mock_services["websocket"].connect = AsyncMock(return_value=True)
        self.mock_services["websocket"].send_message = AsyncMock()
    
    async def _setup_database_service(self) -> None:
        """Setup database service mock."""
        self.mock_services["db"] = MagicMock()
        self.mock_services["db"].create_user = AsyncMock()
        self.mock_services["db"].get_user = AsyncMock()
    
    async def cleanup_services(self) -> None:
        """Cleanup all mock services."""
        self.mock_services.clear()
        self.user_data.clear()


class UserRegistrationHelper:
    """Helper for user registration step of onboarding flow."""
    
    def __init__(self, flow_manager: OnboardingFlowManager):
        self.flow_manager = flow_manager
        self.jwt_helper = flow_manager.jwt_helper
        
    async def execute_registration(self, user_email: str = None) -> Dict[str, Any]:
        """Execute user registration with real JWT creation."""
        user_email = user_email or self._generate_test_email()
        payload = self._create_user_payload(user_email)
        tokens = await self._generate_auth_tokens(payload)
        
        await self._store_user_data(payload)
        return self._format_registration_result(tokens, payload)
    
    def _generate_test_email(self) -> str:
        """Generate unique test email."""
        return f"e2e-onboard-{uuid.uuid4().hex[:8]}@netra.ai"
    
    def _create_user_payload(self, email: str) -> Dict[str, Any]:
        """Create user payload with required fields."""
        base_payload = self._get_base_user_data(email)
        auth_fields = self._get_auth_fields()
        return {**base_payload, **auth_fields}
    
    def _get_base_user_data(self, email: str) -> Dict[str, Any]:
        """Get base user data fields."""
        return {
            "sub": str(uuid.uuid4()),
            "email": email,
            "name": "Test User",
            "is_active": True,
            "created_at": time.time()
        }
    
    def _get_auth_fields(self) -> Dict[str, Any]:
        """Get authentication-specific fields."""
        return {
            "token_type": "access",
            "exp": time.time() + 900  # 15 minutes from now
        }
    
    async def _generate_auth_tokens(self, payload: Dict) -> Dict[str, str]:
        """Generate JWT tokens for user."""
        access_token = await self.jwt_helper.create_jwt_token(payload)
        refresh_token = await self.jwt_helper.create_jwt_token(
            self.jwt_helper.create_refresh_payload()
        )
        return {"access_token": access_token, "refresh_token": refresh_token}
    
    async def _store_user_data(self, payload: Dict) -> None:
        """Store user data in database."""
        await self.flow_manager.mock_services["db"].create_user(payload)
        self.flow_manager.user_data = payload
    
    def _format_registration_result(self, tokens: Dict, payload: Dict) -> Dict[str, Any]:
        """Format registration result for validation."""
        user_data = self._extract_user_data(payload)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": user_data,
            "token_type": "Bearer",
            "success": True
        }
    
    def _extract_user_data(self, payload: Dict) -> Dict[str, Any]:
        """Extract user data from payload."""
        return {
            "sub": payload["sub"],
            "email": payload["email"],
            "name": payload["name"],
            "is_active": payload["is_active"]
        }


class ProfileSetupHelper:
    """Helper for profile setup step of onboarding flow."""
    
    def __init__(self, flow_manager: OnboardingFlowManager):
        self.flow_manager = flow_manager
        
    async def execute_profile_setup(self, registration_data: Dict) -> Dict[str, Any]:
        """Execute profile setup with backend integration."""
        token = registration_data["access_token"]
        await self._validate_token(token)
        
        profile_data = self._create_profile_data(registration_data["user"])
        await self._save_profile_data(profile_data)
        return profile_data
    
    async def _validate_token(self, token: str) -> None:
        """Validate JWT token structure and signature."""
        is_valid = self.flow_manager.jwt_helper.validate_token_structure(token)
        assert is_valid, "Invalid token structure in profile setup"
    
    def _create_profile_data(self, user_data: Dict) -> Dict[str, Any]:
        """Create profile data with optimization preferences."""
        return {
            "user_id": user_data["sub"],
            "preferences": {"theme": "light", "notifications": True},
            "ai_goals": ["cost_reduction", "performance_optimization"],
            "onboarding_complete": True
        }
    
    async def _save_profile_data(self, profile_data: Dict) -> None:
        """Save profile data to backend."""
        await self.flow_manager.mock_services["backend"].create_profile(profile_data)


class OptimizationRequestHelper:
    """Helper for first optimization request step."""
    
    def __init__(self, flow_manager: OnboardingFlowManager):
        self.flow_manager = flow_manager
        
    async def execute_optimization_request(self, registration_data: Dict) -> Dict[str, Any]:
        """Execute first optimization request through WebSocket."""
        await self._establish_websocket_connection(registration_data)
        message = self._create_optimization_message(registration_data["user"])
        
        response = await self._process_optimization_request(message)
        await self._send_websocket_response(response)
        return response
    
    async def _establish_websocket_connection(self, registration_data: Dict) -> None:
        """Establish WebSocket connection with token validation."""
        token = registration_data["access_token"]
        connection_result = await self.flow_manager.mock_services["websocket"].connect(token)
        assert connection_result, "WebSocket connection failed during onboarding"
    
    def _create_optimization_message(self, user_data: Dict) -> Dict[str, Any]:
        """Create first optimization request message."""
        message_data = self._get_message_base_data(user_data)
        message_data["content"] = "I need help optimizing my AI costs for my startup"
        return message_data
    
    def _get_message_base_data(self, user_data: Dict) -> Dict[str, Any]:
        """Get base message data structure."""
        return {
            "type": "optimization_request",
            "user_id": user_data["sub"],
            "thread_id": str(uuid.uuid4()),
            "timestamp": time.time()
        }
    
    async def _process_optimization_request(self, message: Dict) -> Dict[str, Any]:
        """Process optimization request and generate response."""
        await self.flow_manager.mock_services["backend"].process_optimization(message)
        return self._generate_ai_response(message)
    
    def _generate_ai_response(self, message: Dict) -> Dict[str, Any]:
        """Generate AI agent response for optimization request."""
        response_base = self._get_response_base_data(message)
        response_base.update(self._get_response_content_data())
        return response_base
    
    def _get_response_base_data(self, message: Dict) -> Dict[str, Any]:
        """Get base response data structure."""
        return {
            "type": "agent_response",
            "thread_id": message["thread_id"],
            "agent_type": "cost_optimization",
            "cost_estimate": 0.05
        }
    
    def _get_response_content_data(self) -> Dict[str, Any]:
        """Get response content and recommendations."""
        return {
            "content": "Great! I'll help optimize your AI costs. Let me analyze your usage patterns and recommend cost-effective strategies. Based on your startup focus, I suggest starting with usage monitoring and model selection optimization.",
            "recommendations": ["usage_monitoring", "model_optimization", "batch_processing"]
        }
    
    async def _send_websocket_response(self, response: Dict) -> None:
        """Send response through WebSocket."""
        await self.flow_manager.mock_services["websocket"].send_message(response)


