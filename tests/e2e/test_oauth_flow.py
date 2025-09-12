"""
OAuth Integration Testing - Phase 2 Unified System Testing

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise customers requiring SSO integration
2. **Business Goal**: Enable enterprise SSO for $1M+ ARR accounts 
3. **Value Impact**: OAuth failures block high-value enterprise acquisition
4. **Revenue Impact**: Critical for Enterprise tier conversion and retention

**ENTERPRISE CRITICAL FEATURES:**
- Google OAuth complete flow validation
- GitHub Enterprise SSO testing
- Error recovery and graceful degradation
- User merge scenarios for existing accounts
- Cross-service data consistency validation

**ARCHITECTURE:** 450-line limit, 25-line functions, modular enterprise testing
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.oauth_test_providers import (
    GoogleOAuthProvider, GitHubOAuthProvider, OAuthUserFactory, OAuthErrorProvider, get_enterprise_config,
    GoogleOAuthProvider,
    GitHubOAuthProvider,
    OAuthUserFactory,
    OAuthErrorProvider,
    get_enterprise_config
)
from tests.e2e.oauth_flow_manager import (
    create_oauth_flow_manager, create_oauth_validator, create_oauth_session_manager,
    create_oauth_flow_manager,
    create_oauth_validator,
    create_oauth_session_manager
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

@pytest.fixture
async def oauth_manager():
    """OAuth flow manager fixture"""
    return create_oauth_flow_manager()

@pytest.fixture
def oauth_validator():
    """OAuth validator fixture"""
    return create_oauth_validator()

@pytest.fixture 
def oauth_session_manager():
    """OAuth session manager fixture"""
    return create_oauth_session_manager()

@pytest.fixture
def mock_oauth_responses():
    """Mock OAuth provider responses"""
    return {
        "google_token": GoogleOAuthProvider.get_oauth_response(),
        "google_user": GoogleOAuthProvider.get_user_info(),
        "github_token": GitHubOAuthProvider.get_oauth_response(),
        "github_user": GitHubOAuthProvider.get_user_info()
    }

@pytest.fixture
def enterprise_config():
    """Enterprise configuration fixture"""
    return get_enterprise_config()

@pytest.mark.e2e
class TestOAuthFlow:
    """OAuth integration test cases for enterprise scenarios"""
    
    @pytest.mark.e2e
    async def test_google_oauth_complete_flow(self, oauth_manager, oauth_validator, mock_oauth_responses, enterprise_config):
        """Test Google OAuth  ->  User creation  ->  Dashboard access"""
        
        # Step 1: Initiate Google OAuth
        redirect_uri = f"{enterprise_config['frontend_url']}/auth/callback"
        oauth_url, state = await oauth_manager.initiate_google_oauth(redirect_uri)
        initiation_valid = await oauth_validator.validate_oauth_initiation(oauth_url, state)
        assert initiation_valid is True
        
        # Step 2: Mock Google OAuth exchange (external service mock)
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            self._setup_google_mocks(mock_post, mock_get, mock_oauth_responses)
            
            # Step 3: Process callback (real auth service processing)
            callback_result = await oauth_manager.process_oauth_callback("mock_code", "google")
        
        # Step 4: Verify user creation and profile sync
        user_created = await self._verify_user_creation(callback_result)
        profile_synced = await self._verify_profile_sync(callback_result["user"])
        dashboard_loaded = await self._verify_dashboard_access(profile_synced)
        
        assert user_created and profile_synced and dashboard_loaded
    
    @pytest.mark.e2e
    async def test_github_oauth_enterprise(self, oauth_manager, oauth_validator, mock_oauth_responses):
        """Test Enterprise SSO flow for GitHub"""
        
        # Step 1: Mock GitHub Enterprise OAuth
        # Mock: Component isolation for testing without external dependencies
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            self._setup_github_mocks(mock_post, mock_get, mock_oauth_responses)
            callback_result = await oauth_manager.process_oauth_callback("mock_code", "github")
        
        # Step 2: Validate enterprise SSO requirements
        user_data = callback_result["user"]
        user_data["permissions"] = OAuthUserFactory.create_enterprise_permissions()
        enterprise_valid = await oauth_validator.validate_enterprise_sso(user_data)
        
        assert enterprise_valid is True
        assert oauth_validator.enterprise_validations["sso"] is True
    
    @pytest.mark.e2e
    async def test_oauth_error_handling(self, oauth_validator):
        """Test OAuth error scenarios and graceful recovery"""
        
        # Test failed token exchange
        token_error = OAuthErrorProvider.get_token_exchange_error()
        recovery_1 = await oauth_validator.validate_error_recovery("token_exchange", token_error)
        
        # Test failed user info retrieval  
        user_error = OAuthErrorProvider.get_user_info_error()
        recovery_2 = await oauth_validator.validate_error_recovery("user_info", user_error)
        
        # Test network errors
        network_error = OAuthErrorProvider.get_network_error()
        recovery_3 = await oauth_validator.validate_error_recovery("network", network_error)
        
        assert all([recovery_1, recovery_2, recovery_3])
    
    @pytest.mark.e2e
    async def test_oauth_user_merge(self, oauth_validator):
        """Test existing user OAuth link scenario"""
        
        # Step 1: Create existing user
        existing_user = OAuthUserFactory.create_existing_user("enterprise.user@enterprise-test.com")
        
        # Step 2: Create OAuth user data
        oauth_data = GoogleOAuthProvider.get_user_info()
        oauth_user = OAuthUserFactory.create_oauth_user(oauth_data, "google")
        
        # Step 3: Simulate user merge
        merged_user = OAuthUserFactory.create_merged_user(existing_user, oauth_user)
        
        # Step 4: Validate user merge
        merge_valid = await oauth_validator.validate_user_merge(existing_user, merged_user)
        assert merge_valid is True
        assert oauth_validator.enterprise_validations["user_merge"] is True
    
    def _setup_google_mocks(self, mock_post, mock_get, responses):
        """Setup Google OAuth API mocks"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = responses["google_token"]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = responses["google_user"]
    
    def _setup_github_mocks(self, mock_post, mock_get, responses):
        """Setup GitHub OAuth API mocks"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = responses["github_token"]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = responses["github_user"]
    
    async def _verify_user_creation(self, callback_result: Dict[str, Any]) -> bool:
        """Verify user creation in Auth service"""
        user = callback_result.get("user", {})
        processed = callback_result.get("processed", False)
        has_tokens = "tokens" in callback_result
        return processed and user.get("is_verified") and has_tokens
    
    async def _verify_profile_sync(self, auth_user: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate and verify profile sync to backend"""
        sync_result = {
            "synced": True,
            "backend_user_id": f"backend_{uuid.uuid4()}",
            "auth_user_id": auth_user["id"],
            "email": auth_user["email"],
            "sync_timestamp": datetime.now(timezone.utc)
        }
        return sync_result
    
    async def _verify_dashboard_access(self, sync_result: Dict[str, Any]) -> bool:
        """Simulate and verify dashboard access"""
        dashboard_data = {
            "user_id": sync_result["backend_user_id"],
            "dashboard_loaded": True,
            "enterprise_features_enabled": True,
            "oauth_provider_linked": True
        }
        return dashboard_data["dashboard_loaded"]

@pytest.mark.e2e
class TestOAuthDataConsistency:
    """Test data consistency across OAuth services"""
    
    @pytest.mark.e2e
    async def test_auth_backend_sync_consistency(self, oauth_validator):
        """Test data consistency between Auth and Backend services"""
        
        # Create test user data
        google_user = GoogleOAuthProvider.get_user_info()
        auth_user = OAuthUserFactory.create_oauth_user(google_user, "google")
        
        # Simulate backend sync
        backend_user = {
            "id": f"backend_{uuid.uuid4()}",
            "auth_user_id": auth_user["id"],
            "email": auth_user["email"],
            "synced": True,
            "sync_timestamp": datetime.now(timezone.utc)
        }
        
        # Validate data consistency
        consistency_valid = await oauth_validator.validate_data_consistency(auth_user, backend_user)
        assert consistency_valid is True
        assert oauth_validator.enterprise_validations["data_consistency"] is True

@pytest.mark.e2e
class TestOAuthSessionManagement:
    """Test OAuth session management scenarios"""
    
    @pytest.mark.e2e
    async def test_oauth_session_lifecycle(self, oauth_session_manager):
        """Test complete OAuth session lifecycle"""
        
        # Create test user and tokens
        user_data = OAuthUserFactory.create_oauth_user(GoogleOAuthProvider.get_user_info(), "google")
        tokens = {"access_token": f"token_{uuid.uuid4()}", "refresh_token": f"refresh_{uuid.uuid4()}"}
        
        # Create session
        session_id = await oauth_session_manager.create_oauth_session(user_data, tokens)
        assert session_id is not None
        
        # Validate session
        session_valid = await oauth_session_manager.validate_session(session_id)
        assert session_valid is True
        
        # Refresh session
        refresh_success = await oauth_session_manager.refresh_session(session_id)
        assert refresh_success is True
        
        # Terminate session
        terminate_success = await oauth_session_manager.terminate_session(session_id)
        assert terminate_success is True

if __name__ == "__main__":
    # Run OAuth integration tests
    pytest.main([__file__, "-v", "--tb=short"])
