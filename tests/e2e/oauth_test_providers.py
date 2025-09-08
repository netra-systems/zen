"""
OAuth Test Data Providers - Phase 2 Unified Testing

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise customers requiring OAuth/SSO
2. **Business Goal**: Standardized OAuth test data for reliable enterprise testing
3. **Value Impact**: Prevents OAuth integration failures blocking enterprise deals
4. **Revenue Impact**: Critical for $1M+ ARR enterprise customer acquisition

**ARCHITECTURE:** 450-line limit, 25-line functions, focused test data provision
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

# Enterprise OAuth Configuration
OAUTH_ENTERPRISE_CONFIG = {
    "google_client_id": "test-google-client-id",
    "github_client_id": "test-github-enterprise-client-id", 
    "auth_service_url": "http://localhost:8001",
    "backend_service_url": "http://localhost:8000",
    "frontend_url": "http://localhost:3000",
    "enterprise_domain": "enterprise-test.com",
    "timeout": 30
}

class GoogleOAuthProvider:
    """Google OAuth test data provider"""
    
    @staticmethod
    def get_oauth_response() -> Dict[str, Any]:
        """Get mock Google OAuth API response"""
        return {
            "access_token": f"google_access_{uuid.uuid4()}",
            "token_type": "Bearer", 
            "expires_in": 3600,
            "refresh_token": f"google_refresh_{uuid.uuid4()}",
            "scope": "openid email profile"
        }
    
    @staticmethod
    def get_user_info() -> Dict[str, Any]:
        """Get mock Google user profile data"""
        return {
            "id": "google_oauth_enterprise_123",
            "email": "enterprise.user@enterprise-test.com",
            "name": "Enterprise OAuth User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True,
            "hd": "enterprise-test.com"  # Enterprise domain
        }
    
    @staticmethod
    def get_oauth_url(redirect_uri: str, state: str) -> str:
        """Build Google OAuth authorization URL"""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = [
            f"client_id={OAUTH_ENTERPRISE_CONFIG['google_client_id']}",
            f"redirect_uri={redirect_uri}",
            "response_type=code",
            "scope=openid%20email%20profile",
            f"state={state}"
        ]
        return f"{base_url}?{'&'.join(params)}"

class GitHubOAuthProvider:
    """GitHub Enterprise OAuth test data provider"""
    
    @staticmethod
    def get_oauth_response() -> Dict[str, Any]:
        """Get mock GitHub Enterprise OAuth response"""
        return {
            "access_token": f"ghp_enterprise_{uuid.uuid4()}",
            "token_type": "bearer",
            "scope": "read:user,user:email"
        }
    
    @staticmethod
    def get_user_info() -> Dict[str, Any]:
        """Get mock GitHub Enterprise user data"""
        return {
            "id": 987654321,
            "login": "enterprise-user",
            "email": "enterprise.user@enterprise-test.com",
            "name": "GitHub Enterprise User",
            "company": "Enterprise Test Corp",
            "avatar_url": "https://github.com/avatars/enterprise.jpg"
        }
    
    @staticmethod
    def get_oauth_url(redirect_uri: str, state: str) -> str:
        """Build GitHub OAuth authorization URL"""
        base_url = "https://github.com/login/oauth/authorize"
        params = [
            f"client_id={OAUTH_ENTERPRISE_CONFIG['github_client_id']}",
            f"redirect_uri={redirect_uri}",
            "scope=read:user,user:email",
            f"state={state}"
        ]
        return f"{base_url}?{'&'.join(params)}"

class OAuthErrorProvider:
    """OAuth error scenario test data provider"""
    
    @staticmethod
    def get_token_exchange_error() -> Dict[str, Any]:
        """Get token exchange failure scenario"""
        return {
            "error": "invalid_grant",
            "error_description": "Authorization code was already used",
            "recovered": True,
            "graceful": True,
            "fallback_action": "redirect_to_login"
        }
    
    @staticmethod
    def get_user_info_error() -> Dict[str, Any]:
        """Get user info retrieval failure scenario"""
        return {
            "error": "insufficient_scope",
            "error_description": "Missing required scopes",
            "recovered": True,
            "graceful": True,
            "fallback_action": "partial_profile_creation"
        }
    
    @staticmethod
    def get_network_error() -> Dict[str, Any]:
        """Get network error scenario"""
        return {
            "error": "network_timeout",
            "error_description": "OAuth provider unreachable",
            "recovered": True,
            "graceful": True,
            "fallback_action": "retry_with_backoff"
        }

class OAuthUserFactory:
    """Factory for creating OAuth user test data"""
    
    @staticmethod
    def create_oauth_user(user_info: Dict, provider: str) -> Dict[str, Any]:
        """Create OAuth user from provider data"""
        return {
            "id": f"{provider}_{user_info.get('id', uuid.uuid4())}",
            "email": user_info["email"],
            "full_name": user_info.get("name", ""),
            "auth_provider": provider,
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
            "enterprise_domain": user_info.get("hd", None)
        }
    
    @staticmethod
    def create_google_user() -> Dict[str, Any]:
        """Create Google OAuth user test data"""
        return GoogleOAuthProvider.get_user_info()
    
    @staticmethod
    def create_github_user() -> Dict[str, Any]:
        """Create GitHub OAuth user test data"""
        return GitHubOAuthProvider.get_user_info()
    
    @staticmethod
    def create_generic_user() -> Dict[str, Any]:
        """Create generic OAuth user test data"""
        return {
            "id": "generic_oauth_123",
            "email": "oauth.user@test.com",
            "name": "Generic OAuth User",
            "verified_email": True
        }
    
    @staticmethod
    def create_existing_user(email: str) -> Dict[str, Any]:
        """Create existing user for merge scenarios"""
        return {
            "id": f"existing_user_{uuid.uuid4()}",
            "email": email,
            "auth_provider": "local",
            "created_at": datetime.now(timezone.utc),
            "is_verified": True
        }
    
    @staticmethod
    def create_enterprise_permissions() -> list:
        """Create enterprise user permissions"""
        return ["read", "write", "enterprise_features", "admin_access"]
    
    @staticmethod
    def create_merged_user(existing_user: Dict, oauth_user: Dict) -> Dict[str, Any]:
        """Create merged user data"""
        return {
            "id": existing_user["id"],
            "email": oauth_user["email"],
            "auth_provider": oauth_user["auth_provider"],
            "merged_with_id": existing_user["id"],
            "oauth_linked": True,
            "created_at": existing_user["created_at"],
            "updated_at": datetime.now(timezone.utc)
        }

class OAuthMockResponseHelper:
    """Helper for creating mock OAuth responses"""
    
    @staticmethod
    def get_all_google_responses() -> Dict[str, Dict[str, Any]]:
        """Get all Google OAuth mock responses"""
        return {
            "token_response": GoogleOAuthProvider.get_oauth_response(),
            "user_info": GoogleOAuthProvider.get_user_info()
        }
    
    @staticmethod
    def get_all_github_responses() -> Dict[str, Dict[str, Any]]:
        """Get all GitHub OAuth mock responses"""
        return {
            "token_response": GitHubOAuthProvider.get_oauth_response(),
            "user_info": GitHubOAuthProvider.get_user_info()
        }
    
    @staticmethod
    def get_all_error_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get all OAuth error scenarios"""
        return {
            "token_exchange": OAuthErrorProvider.get_token_exchange_error(),
            "user_info": OAuthErrorProvider.get_user_info_error(),
            "network": OAuthErrorProvider.get_network_error()
        }

def get_enterprise_config() -> Dict[str, Any]:
    """Get enterprise OAuth configuration"""
    return OAUTH_ENTERPRISE_CONFIG.copy()

def create_oauth_test_data(provider: str) -> Dict[str, Any]:
    """Create comprehensive OAuth test data for provider"""
    if provider == "google":
        return OAuthMockResponseHelper.get_all_google_responses()
    elif provider == "github":
        return OAuthMockResponseHelper.get_all_github_responses()
    else:
        raise ValueError(f"Unsupported OAuth provider: {provider}")