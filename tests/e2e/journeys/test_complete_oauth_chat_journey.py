from shared.isolated_environment import get_env
"""
Complete User Journey: OAuth Login → User Creation → Chat Test

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: ALL (Free, Early, Mid, Enterprise) - First-time user experience
2. **Business Goal**: Prevent conversion loss at critical OAuth → Chat transition
3. **Value Impact**: Validates complete new user onboarding pipeline
4. **Revenue Impact**: $100K+ MRR protection through validated OAuth to revenue flow
5. **Strategic Impact**: Critical path for all new user acquisitions via OAuth providers

**CRITICAL E2E FLOW:**
- OAuth provider authentication simulation (mock provider, real services)
- Real Auth service callback processing and user creation
- User sync verification between auth_users and userbase tables
- JWT token extraction and validation
- WebSocket connection with OAuth-derived token
- Chat message sending and AI response reception
- Conversation persistence verification in database
- Returning user OAuth flow (no duplicate users)

**REQUIREMENTS:**
- Complete flow works without manual intervention
- User data consistent across all services
- Chat functionality immediately available post-login
- Conversations properly attributed to user
- <20 second execution for optimal UX
- Real Auth and Backend services - no internal mocking
- Maximum 300 lines, functions ≤8 lines each
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import pytest
try:
    import websockets
except ImportError:
    websockets = None

# Set test environment
get_env().set("TESTING", "1", "test")
get_env().set("USE_REAL_SERVICES", "true", "test")
get_env().set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
get_env().set("BACKEND_SERVICE_URL", "http://localhost:8000", "test")

# Add parent directories to sys.path for imports

from tests.e2e.helpers.core.chat_helpers import (
    ChatInteractionHelper,
    ConversationPersistenceHelper,
    WebSocketConnectionHelper,
)
from tests.e2e.helpers.journey.journey_validation_helpers import (
    validate_auth_callback,
    validate_chat_interaction,
    validate_conversation_persistence,
    validate_oauth_authentication,
    validate_returning_user_flow,
    validate_user_sync,
    validate_websocket_connection,
)
from tests.e2e.helpers.auth.oauth_journey_helpers import (
    OAuthAuthenticationHelper,
    OAuthCallbackHelper,
    OAuthReturningUserHelper,
    OAuthUserSyncHelper,
)

from netra_backend.app.logging_config import central_logger
try:
    from tests.e2e.service_manager import RealServicesManager
    
    def create_real_services_manager():
        project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return RealServicesManager(project_root)
except ImportError:
    # Fallback service manager
    class RealServicesManagerFallback:
        def __init__(self, project_root=None):
            self.services = {}
        
        async def start_all_services(self, **kwargs):
            pass
        
        async def stop_all_services(self):
            pass
        
        def get_service_urls(self):
            return {
                "auth": "http://localhost:8001",
                "backend": "http://localhost:8000"
            }
        
        def get_service_info(self, service_name):
            ports = {"auth": 8001, "backend": 8000}
            return type('ServiceInfo', (), {'port': ports.get(service_name, 8000)})()
    
    def create_real_services_manager():
        return RealServicesManagerFallback()

logger = central_logger.get_logger(__name__)


class TestCompleteOAuthChatJourneyer:
    """Tests complete OAuth to chat journey with real services only."""
    
    def __init__(self):
        self.services_manager = create_real_services_manager()
        self.http_client: Optional[httpx.AsyncClient] = None
        self.websocket: Optional[Any] = None  # WebSocket connection
        self.journey_results: Dict[str, Any] = {}
        self.oauth_user_data: Dict[str, Any] = {}
        self.tokens: Dict[str, str] = {}
        
    @asynccontextmanager
    async def setup_real_services(self):
        """Setup real service connections for OAuth journey."""
        try:
            await self.services_manager.start_all_services()
            self.http_client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
            yield self
        finally:
            await self._cleanup_journey_resources()
            
    async def _cleanup_journey_resources(self):
        """Cleanup OAuth journey resources."""
        if self.websocket:
            await self.websocket.close()
        if self.http_client:
            await self.http_client.aclose()
        await self.services_manager.stop_all_services()
        
    async def execute_complete_oauth_chat_journey(self) -> Dict[str, Any]:
        """Execute complete OAuth to chat journey with real services."""
        journey_start = time.time()
        
        # Step 1: OAuth provider authentication simulation
        oauth_result = await OAuthAuthenticationHelper.execute_oauth_authentication_flow()
        self.oauth_user_data = oauth_result.get("user_data", {})
        self._store_journey_step("oauth_auth", oauth_result)
        
        # Step 2: Auth service callback processing and user creation
        if oauth_result.get("success"):
            callback_result = await OAuthCallbackHelper.execute_auth_service_callback(
                self.http_client, self.services_manager, oauth_result, self.oauth_user_data
            )
            self.tokens = {
                "access_token": callback_result.get("access_token"),
                "refresh_token": callback_result.get("refresh_token")
            }
            self._store_journey_step("auth_callback", callback_result)
            
            # Step 3: User sync verification (only if callback succeeded)
            if callback_result.get("success"):
                sync_result = await OAuthUserSyncHelper.verify_user_database_sync(
                    self.http_client, self.services_manager, self.tokens, self.oauth_user_data
                )
                self._store_journey_step("user_sync", sync_result)
                
                # Step 4: WebSocket connection with OAuth token (only if sync succeeded)
                if sync_result.get("success"):
                    websocket_result = await WebSocketConnectionHelper.execute_websocket_connection(
                        self.services_manager, self.tokens
                    )
                    self.websocket = websocket_result.get("websocket")
                    self._store_journey_step("websocket", websocket_result)
                    
                    # Step 5: Chat message and AI response (only if WebSocket succeeded)
                    if websocket_result.get("success") and self.websocket:
                        user_id = sync_result.get("user_id", f"oauth_user_{time.time()}")
                        chat_result = await ChatInteractionHelper.execute_chat_interaction(
                            self.websocket, user_id
                        )
                        self._store_journey_step("chat", chat_result)
                        
                        # Step 6: Conversation persistence verification (only if chat succeeded)
                        if chat_result.get("success"):
                            thread_id = chat_result.get("thread_id")
                            persistence_result = await ConversationPersistenceHelper.verify_conversation_persistence(
                                self.http_client, self.services_manager, self.tokens, thread_id
                            )
                            self._store_journey_step("persistence", persistence_result)
                            
                            # Step 7: Returning user OAuth flow (only if persistence succeeded)
                            if persistence_result.get("success"):
                                returning_user_result = await OAuthReturningUserHelper.test_returning_user_oauth(
                                    self.http_client, self.services_manager, self.oauth_user_data
                                )
                                self._store_journey_step("returning_user", returning_user_result)
        
        journey_time = time.time() - journey_start
        return self._format_complete_journey_results(journey_time)
        
            
            
        
            
            
            
            
            
    def _store_journey_step(self, step_name: str, result: Dict[str, Any]):
        """Store journey step result for analysis."""
        self.journey_results[step_name] = result
        
    def _format_complete_journey_results(self, journey_time: float) -> Dict[str, Any]:
        """Format complete journey results for validation."""
        # Calculate overall success
        all_steps_successful = all(
            step_result.get("success", False) 
            for step_result in self.journey_results.values()
        )
        
        return {
            "success": all_steps_successful,
            "total_execution_time": journey_time,
            "performance_valid": journey_time < 20.0,
            "oauth_user_data": self.oauth_user_data,
            "tokens": self.tokens,
            "journey_steps": self.journey_results,
            "step_count": len(self.journey_results)
        }


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_oauth_chat_journey():
    """
    Test: Complete OAuth Login → User Creation → Chat Interaction Journey
    
    BVJ: Critical first-time user experience validation - prevents conversion loss
    - OAuth provider authentication (mocked external, real internal services)
    - Auth service callback processing and user creation
    - User database sync verification across services
    - JWT token extraction and WebSocket authentication
    - Chat message sending and AI response reception
    - Conversation persistence verification
    - Returning user OAuth flow validation
    - Must complete in <20 seconds for optimal UX
    """
    tester = CompleteOAuthChatJourneyTester()
    
    async with tester.setup_real_services():
        # Execute complete OAuth to chat journey
        results = await tester.execute_complete_oauth_chat_journey()
        
        # Validate critical business requirements
        assert results["success"], f"Complete OAuth to chat journey failed: {results}"
        assert results["performance_valid"], f"Journey too slow: {results['total_execution_time']:.2f}s > 20s"
        
        # Validate each critical step
        validate_oauth_authentication(results["journey_steps"]["oauth_auth"])
        validate_auth_callback(results["journey_steps"]["auth_callback"])
        validate_user_sync(results["journey_steps"]["user_sync"])
        validate_websocket_connection(results["journey_steps"]["websocket"])
        validate_chat_interaction(results["journey_steps"]["chat"])
        validate_conversation_persistence(results["journey_steps"]["persistence"])
        validate_returning_user_flow(results["journey_steps"]["returning_user"])
        
        print(f"[SUCCESS] Complete OAuth to Chat Journey: {results['total_execution_time']:.2f}s")
        print(f"[PROTECTED] New user acquisition pipeline validated")
        print(f"[USER] {results['oauth_user_data']['email']} -> OAuth to revenue flow confirmed")


if __name__ == "__main__":
    # Execute critical OAuth to chat journey test
    pytest.main([__file__, "-v", "--tb=short", "-x"])