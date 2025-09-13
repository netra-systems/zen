"""Configuration for E2E tests in unified/e2e directory."""



from dataclasses import dataclass

from typing import Any, Dict





@dataclass

class TestUser:

    """Test user data structure."""

    id: str

    email: str

    role: str = "user"





@dataclass

class TestEndpoints:

    """Test endpoint configuration."""

    ws_url: str = "ws://localhost:8000/ws"

    api_url: str = "http://localhost:8000"

    api_base: str = "http://localhost:8000"  # Alias for compatibility

    auth_url: str = "http://localhost:8081"

    auth_base: str = "http://localhost:8081"  # Alias for compatibility





class TestDataFactory:

    """Factory for creating test data structures."""

    

    @staticmethod

    def create_websocket_auth(token: str) -> Dict[str, str]:

        """Create WebSocket authentication headers."""

        return {

            "Authorization": f"Bearer {token}",

            "X-Test-Mode": "true"

        }

    

    @staticmethod

    def create_message_data(user_id: str, content: str) -> Dict[str, Any]:

        """Create test message data."""

        return {

            "type": "message",

            "user_id": user_id,

            "content": content,

            "timestamp": "2024-01-01T00:00:00Z"

        }





# Test users for different segments

TEST_USERS = {

    "free": TestUser(id="test_user_free", email="free@test.com", role="user"),

    "early": TestUser(id="test_user_early", email="early@test.com", role="user"), 

    "mid": TestUser(id="test_user_mid", email="mid@test.com", role="user"),

    "enterprise": TestUser(id="test_user_enterprise", email="enterprise@test.com", role="admin")

}





# Test endpoints

TEST_ENDPOINTS = TestEndpoints()





# Test configuration

TEST_CONFIG = {

    "redis_enabled": False,  # Set to False for environments without Redis

    "auth_service_url": "http://localhost:8081",

    "websocket_timeout": 30.0,

    "token_expiry_seconds": 3600,

    "reconnection_timeout": 2.0,

    "performance_thresholds": {

        "reconnection_time": 2.0,

        "token_validation_time": 0.1,

        "connection_time": 1.0

    }

}



# Test secrets - REMOVED mock API key fallbacks per CLAUDE.md

# Configuration must require real API keys from environment

TEST_SECRETS = {

    "jwt_secret": "test_jwt_secret_key_for_testing_only",

    # API keys must come from environment variables - no mock fallbacks allowed

}

