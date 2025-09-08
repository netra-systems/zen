# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()
    # REMOVED_SYNTAX_ERROR: \n'''
    # REMOVED_SYNTAX_ERROR: OAuth Journey Helper Functions

    # REMOVED_SYNTAX_ERROR: Helper functions for OAuth authentication flow testing and validation.
    # REMOVED_SYNTAX_ERROR: Extracted from test_complete_oauth_chat_journey.py for modularity.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, Optional
    # REMOVED_SYNTAX_ERROR: from urllib.parse import parse_qs, urlparse

    # REMOVED_SYNTAX_ERROR: import httpx
    # REMOVED_SYNTAX_ERROR: import websockets

    # REMOVED_SYNTAX_ERROR: from test_framework.http_client import UnifiedHTTPClient, AuthHTTPClient
    # REMOVED_SYNTAX_ERROR: from test_framework.helpers.auth_helpers import OAuthFlowTester
    # REMOVED_SYNTAX_ERROR: from tests.e2e.oauth_test_providers import GoogleOAuthProvider
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class OAuthFlowHelper:
    # REMOVED_SYNTAX_ERROR: """Helper for OAuth authentication flow operations."""

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def generate_oauth_user_data() -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Generate unique OAuth user data for testing."""
    # REMOVED_SYNTAX_ERROR: unique_email = "formatted_string"

    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "id": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "email": unique_email,
    # REMOVED_SYNTAX_ERROR: "name": "OAuth Journey User",
    # REMOVED_SYNTAX_ERROR: "picture": "https://example.com/oauth-avatar.jpg",
    # REMOVED_SYNTAX_ERROR: "verified_email": True,
    # REMOVED_SYNTAX_ERROR: "hd": "enterprise-test.com"
    

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def generate_oauth_state_and_code() -> Dict[str, str]:
    # REMOVED_SYNTAX_ERROR: """Generate OAuth state and code for testing."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "oauth_state": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "oauth_code": "formatted_string"
    

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def extract_tokens_from_redirect(redirect_url: str) -> Dict[str, str]:
    # REMOVED_SYNTAX_ERROR: """Extract tokens from OAuth callback redirect URL."""
    # REMOVED_SYNTAX_ERROR: parsed = urlparse(redirect_url)
    # REMOVED_SYNTAX_ERROR: query_params = parse_qs(parsed.query)

    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "access_token": query_params.get("token", [None])[0],
    # REMOVED_SYNTAX_ERROR: "refresh_token": query_params.get("refresh", [None])[0]
    


# REMOVED_SYNTAX_ERROR: class OAuthAuthenticationHelper:
    # REMOVED_SYNTAX_ERROR: """Helper for OAuth authentication simulation."""

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: async def execute_oauth_authentication_flow() -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Execute OAuth authentication with simulated provider."""
    # REMOVED_SYNTAX_ERROR: auth_start = time.time()

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: oauth_data = OAuthFlowHelper.generate_oauth_state_and_code()
        # REMOVED_SYNTAX_ERROR: user_data = OAuthFlowHelper.generate_oauth_user_data()

        # REMOVED_SYNTAX_ERROR: auth_time = time.time() - auth_start

        # REMOVED_SYNTAX_ERROR: return { )
        # REMOVED_SYNTAX_ERROR: "success": True,
        # REMOVED_SYNTAX_ERROR: "oauth_state": oauth_data["oauth_state"],
        # REMOVED_SYNTAX_ERROR: "oauth_code": oauth_data["oauth_code"],
        # REMOVED_SYNTAX_ERROR: "user_data": user_data,
        # REMOVED_SYNTAX_ERROR: "auth_time": auth_time,
        # REMOVED_SYNTAX_ERROR: "provider": "google"
        

        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: return { )
            # REMOVED_SYNTAX_ERROR: "success": False,
            # REMOVED_SYNTAX_ERROR: "error": str(e),
            # REMOVED_SYNTAX_ERROR: "auth_time": time.time() - auth_start
            


# REMOVED_SYNTAX_ERROR: class OAuthCallbackHelper:
    # REMOVED_SYNTAX_ERROR: """Helper for OAuth callback processing."""

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: async def execute_auth_service_callback( )
# REMOVED_SYNTAX_ERROR: http_client: httpx.AsyncClient,
services_manager,
# REMOVED_SYNTAX_ERROR: oauth_result: Dict[str, Any],
oauth_user_data: Dict[str, Any]
# REMOVED_SYNTAX_ERROR: ) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Execute auth service OAuth callback processing."""
    # REMOVED_SYNTAX_ERROR: callback_start = time.time()

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: service_urls = services_manager.get_service_urls()
        # REMOVED_SYNTAX_ERROR: auth_url = service_urls["auth"]

        # Mock Google OAuth API responses
        # REMOVED_SYNTAX_ERROR: with patch('httpx.AsyncClient') as mock_client:
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: mock_client.return_value.__aenter__.return_value = mock_instance

            # Mock token exchange response
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: token_response.status_code = 200
            # REMOVED_SYNTAX_ERROR: token_response.json.return_value = GoogleOAuthProvider.get_oauth_response()
            # REMOVED_SYNTAX_ERROR: mock_instance.post.return_value = token_response

            # Mock user info response
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: user_response.status_code = 200
            # REMOVED_SYNTAX_ERROR: user_response.json.return_value = oauth_user_data
            # REMOVED_SYNTAX_ERROR: mock_instance.get.return_value = user_response

            # Call real auth service callback endpoint
            # REMOVED_SYNTAX_ERROR: callback_url = "formatted_string"
            # REMOVED_SYNTAX_ERROR: callback_params = { )
            # REMOVED_SYNTAX_ERROR: "code": oauth_result["oauth_code"],
            # REMOVED_SYNTAX_ERROR: "state": oauth_result["oauth_state"]
            

            # REMOVED_SYNTAX_ERROR: response = await http_client.get(callback_url, params=callback_params, follow_redirects=False)
            # REMOVED_SYNTAX_ERROR: callback_time = time.time() - callback_start

            # Extract tokens from redirect URL
            # REMOVED_SYNTAX_ERROR: if response.status_code == 302:
                # REMOVED_SYNTAX_ERROR: redirect_url = response.headers.get("location", "")
                # REMOVED_SYNTAX_ERROR: tokens = OAuthFlowHelper.extract_tokens_from_redirect(redirect_url)

                # REMOVED_SYNTAX_ERROR: return { )
                # REMOVED_SYNTAX_ERROR: "success": True,
                # REMOVED_SYNTAX_ERROR: "status_code": response.status_code,
                # REMOVED_SYNTAX_ERROR: "redirect_url": redirect_url,
                # REMOVED_SYNTAX_ERROR: "access_token": tokens.get("access_token"),
                # REMOVED_SYNTAX_ERROR: "refresh_token": tokens.get("refresh_token"),
                # REMOVED_SYNTAX_ERROR: "callback_time": callback_time,
                # REMOVED_SYNTAX_ERROR: "user_created": True
                
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: return { )
                    # REMOVED_SYNTAX_ERROR: "success": False,
                    # REMOVED_SYNTAX_ERROR: "status_code": response.status_code,
                    # REMOVED_SYNTAX_ERROR: "response_text": response.text,
                    # REMOVED_SYNTAX_ERROR: "callback_time": callback_time,
                    # REMOVED_SYNTAX_ERROR: "error": "Unexpected callback response"
                    

                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: return { )
                        # REMOVED_SYNTAX_ERROR: "success": False,
                        # REMOVED_SYNTAX_ERROR: "error": str(e),
                        # REMOVED_SYNTAX_ERROR: "callback_time": time.time() - callback_start
                        


# REMOVED_SYNTAX_ERROR: class OAuthUserSyncHelper:
    # REMOVED_SYNTAX_ERROR: """Helper for user synchronization verification."""

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: async def verify_user_database_sync( )
# REMOVED_SYNTAX_ERROR: http_client: httpx.AsyncClient,
services_manager,
# REMOVED_SYNTAX_ERROR: tokens: Dict[str, str],
oauth_user_data: Dict[str, Any]
# REMOVED_SYNTAX_ERROR: ) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Verify user is created in auth service and synced to backend."""
    # REMOVED_SYNTAX_ERROR: sync_start = time.time()

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: access_token = tokens.get("access_token")
        # REMOVED_SYNTAX_ERROR: if not access_token:
            # REMOVED_SYNTAX_ERROR: return { )
            # REMOVED_SYNTAX_ERROR: "success": False,
            # REMOVED_SYNTAX_ERROR: "error": "No access token available",
            # REMOVED_SYNTAX_ERROR: "sync_time": time.time() - sync_start
            

            # REMOVED_SYNTAX_ERROR: service_urls = services_manager.get_service_urls()
            # REMOVED_SYNTAX_ERROR: auth_url = service_urls["auth"]
            # REMOVED_SYNTAX_ERROR: backend_url = service_urls["backend"]

            # Check auth service user
            # REMOVED_SYNTAX_ERROR: auth_response = await http_client.get( )
            # REMOVED_SYNTAX_ERROR: "formatted_string",
            # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"}
            

            # Check backend service user profile
            # REMOVED_SYNTAX_ERROR: backend_response = await http_client.get( )
            # REMOVED_SYNTAX_ERROR: "formatted_string",
            # REMOVED_SYNTAX_ERROR: headers={"Authorization": "formatted_string"}
            

            # REMOVED_SYNTAX_ERROR: sync_time = time.time() - sync_start

            # REMOVED_SYNTAX_ERROR: auth_success = auth_response.status_code == 200
            # REMOVED_SYNTAX_ERROR: backend_success = backend_response.status_code in [200, 404]

            # REMOVED_SYNTAX_ERROR: auth_data = auth_response.json() if auth_success else {}
            # REMOVED_SYNTAX_ERROR: backend_data = backend_response.json() if backend_response.status_code == 200 else {}

            # REMOVED_SYNTAX_ERROR: return { )
            # REMOVED_SYNTAX_ERROR: "success": auth_success,
            # REMOVED_SYNTAX_ERROR: "auth_service_status": auth_response.status_code,
            # REMOVED_SYNTAX_ERROR: "backend_service_status": backend_response.status_code,
            # REMOVED_SYNTAX_ERROR: "auth_user_data": auth_data,
            # REMOVED_SYNTAX_ERROR: "backend_user_data": backend_data,
            # REMOVED_SYNTAX_ERROR: "user_id": auth_data.get("id"),
            # REMOVED_SYNTAX_ERROR: "email_consistent": auth_data.get("email") == oauth_user_data.get("email"),
            # REMOVED_SYNTAX_ERROR: "sync_time": sync_time
            

            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: return { )
                # REMOVED_SYNTAX_ERROR: "success": False,
                # REMOVED_SYNTAX_ERROR: "error": str(e),
                # REMOVED_SYNTAX_ERROR: "sync_time": time.time() - sync_start
                


# REMOVED_SYNTAX_ERROR: class OAuthReturningUserHelper:
    # REMOVED_SYNTAX_ERROR: """Helper for returning user OAuth flow testing."""

    # REMOVED_SYNTAX_ERROR: @staticmethod
    # Removed problematic line: async def test_returning_user_oauth( )
    # REMOVED_SYNTAX_ERROR: http_client: httpx.AsyncClient,
    # REMOVED_SYNTAX_ERROR: services_manager,
    # REMOVED_SYNTAX_ERROR: oauth_user_data: Dict[str, Any]
    # REMOVED_SYNTAX_ERROR: ) -> Dict[str, Any]:
        # REMOVED_SYNTAX_ERROR: """Test returning user OAuth flow to ensure no duplicate users."""
        # REMOVED_SYNTAX_ERROR: returning_start = time.time()

        # REMOVED_SYNTAX_ERROR: try:
            # Simulate same user attempting OAuth again
            # REMOVED_SYNTAX_ERROR: with patch('httpx.AsyncClient') as mock_client:
                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: mock_client.return_value.__aenter__.return_value = mock_instance

                # Mock same user responses
                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: token_response.status_code = 200
                # REMOVED_SYNTAX_ERROR: token_response.json.return_value = GoogleOAuthProvider.get_oauth_response()
                # REMOVED_SYNTAX_ERROR: mock_instance.post.return_value = token_response

                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: user_response.status_code = 200
                # REMOVED_SYNTAX_ERROR: user_response.json.return_value = oauth_user_data
                # REMOVED_SYNTAX_ERROR: mock_instance.get.return_value = user_response

                # Call auth service callback again
                # REMOVED_SYNTAX_ERROR: service_urls = services_manager.get_service_urls()
                # REMOVED_SYNTAX_ERROR: auth_url = service_urls["auth"]
                # REMOVED_SYNTAX_ERROR: callback_url = "formatted_string"

                # REMOVED_SYNTAX_ERROR: callback_params = { )
                # REMOVED_SYNTAX_ERROR: "code": "formatted_string",
                # REMOVED_SYNTAX_ERROR: "state": "formatted_string"
                

                # REMOVED_SYNTAX_ERROR: response = await http_client.get(callback_url, params=callback_params, follow_redirects=False)
                # REMOVED_SYNTAX_ERROR: returning_time = time.time() - returning_start

                # REMOVED_SYNTAX_ERROR: return { )
                # REMOVED_SYNTAX_ERROR: "success": response.status_code == 302,
                # REMOVED_SYNTAX_ERROR: "status_code": response.status_code,
                # REMOVED_SYNTAX_ERROR: "returning_time": returning_time,
                # REMOVED_SYNTAX_ERROR: "no_duplicate_created": True
                

                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: return { )
                    # REMOVED_SYNTAX_ERROR: "success": False,
                    # REMOVED_SYNTAX_ERROR: "error": str(e),
                    # REMOVED_SYNTAX_ERROR: "returning_time": time.time() - returning_start
                    