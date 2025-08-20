"""
OAuth Flow Manager - Phase 2 Unified Testing

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise customers requiring OAuth/SSO validation
2. **Business Goal**: Centralized OAuth flow management for enterprise testing
3. **Value Impact**: Ensures OAuth flows work correctly across all enterprise scenarios
4. **Revenue Impact**: Prevents OAuth failures that block $1M+ ARR deals

**ARCHITECTURE:** 450-line limit, 25-line functions, focused flow management
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional

from .config import TEST_CONFIG, TestTokenManager
from .oauth_test_providers import (
    GoogleOAuthProvider,
    GitHubOAuthProvider,
    OAuthUserFactory,
    get_enterprise_config
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class OAuthFlowManager:
    """Manager for OAuth flow operations and enterprise validations"""
    
    def __init__(self):
        self.token_manager = TestTokenManager(TEST_CONFIG.secrets)
        self.enterprise_config = get_enterprise_config()
        self.validation_results = {}
    
    async def initiate_google_oauth(self, redirect_uri: str) -> Tuple[str, str]:
        """Initiate Google OAuth flow"""
        state = f"oauth_state_{uuid.uuid4()}"
        oauth_url = GoogleOAuthProvider.get_oauth_url(redirect_uri, state)
        return oauth_url, state
    
    async def initiate_github_oauth(self, redirect_uri: str) -> Tuple[str, str]:
        """Initiate GitHub OAuth flow"""
        state = f"github_state_{uuid.uuid4()}"
        oauth_url = GitHubOAuthProvider.get_oauth_url(redirect_uri, state)
        return oauth_url, state
    
    async def process_oauth_callback(self, code: str, provider: str) -> Dict[str, Any]:
        """Process OAuth callback and create user session"""
        if provider == "google":
            return await self._process_google_callback(code)
        elif provider == "github":
            return await self._process_github_callback(code)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
    
    async def _process_google_callback(self, code: str) -> Dict[str, Any]:
        """Process Google OAuth callback"""
        user_info = GoogleOAuthProvider.get_user_info()
        created_user = OAuthUserFactory.create_oauth_user(user_info, "google")
        tokens = await self._create_user_tokens(created_user)
        return {"provider": "google", "user": created_user, "tokens": tokens, "processed": True}
    
    async def _process_github_callback(self, code: str) -> Dict[str, Any]:
        """Process GitHub OAuth callback"""
        user_info = GitHubOAuthProvider.get_user_info()
        created_user = OAuthUserFactory.create_oauth_user(user_info, "github")
        tokens = await self._create_user_tokens(created_user)
        return {"provider": "github", "user": created_user, "tokens": tokens, "processed": True}
    
    async def _create_user_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create JWT tokens for OAuth user"""
        access_token = self.token_manager.create_test_token(user_data)
        refresh_token = f"refresh_{uuid.uuid4()}"
        return {"access_token": access_token, "refresh_token": refresh_token}

class OAuthValidator:
    """Validator for OAuth flow steps and enterprise requirements"""
    
    def __init__(self):
        self.enterprise_validations = {}
        self.error_scenarios = {}
        self.enterprise_config = get_enterprise_config()
    
    async def validate_oauth_initiation(self, oauth_url: str, state: str) -> bool:
        """Validate OAuth flow initiation"""
        url_valid = self._validate_oauth_url(oauth_url)
        state_valid = state in oauth_url and len(state) > 10
        return url_valid and state_valid
    
    def _validate_oauth_url(self, oauth_url: str) -> bool:
        """Validate OAuth URL format"""
        google_valid = "accounts.google.com" in oauth_url
        github_valid = "github.com/login/oauth" in oauth_url
        return google_valid or github_valid
    
    async def validate_enterprise_sso(self, user_data: Dict[str, Any]) -> bool:
        """Validate enterprise SSO requirements"""
        domain_valid = await self._validate_enterprise_domain(user_data)
        permissions_valid = await self._validate_enterprise_permissions(user_data)
        self.enterprise_validations["sso"] = domain_valid and permissions_valid
        return self.enterprise_validations["sso"]
    
    async def _validate_enterprise_domain(self, user_data: Dict[str, Any]) -> bool:
        """Validate user belongs to enterprise domain"""
        email = user_data.get("email", "")
        enterprise_domain = user_data.get("enterprise_domain")
        expected_domain = self.enterprise_config["enterprise_domain"]
        return enterprise_domain == expected_domain
    
    async def _validate_enterprise_permissions(self, user_data: Dict[str, Any]) -> bool:
        """Validate enterprise user permissions"""
        expected_permissions = ["read", "write", "enterprise_features"]
        user_permissions = user_data.get("permissions", [])
        return all(perm in user_permissions for perm in expected_permissions)
    
    async def validate_error_recovery(self, error_scenario: str, recovery_data: Dict) -> bool:
        """Validate OAuth error recovery scenarios"""
        recovery_successful = recovery_data.get("recovered", False)
        error_handled_gracefully = recovery_data.get("graceful", False)
        has_fallback = "fallback_action" in recovery_data
        recovery_complete = recovery_successful and error_handled_gracefully and has_fallback
        self.error_scenarios[error_scenario] = recovery_complete
        return recovery_complete
    
    async def validate_user_merge(self, existing_user: Dict, merged_user: Dict) -> bool:
        """Validate user merge for existing accounts"""
        merge_successful = existing_user["id"] == merged_user.get("merged_with_id")
        email_consistent = existing_user["email"] == merged_user["email"]
        oauth_linked = merged_user.get("oauth_linked", False)
        merge_complete = merge_successful and email_consistent and oauth_linked
        self.enterprise_validations["user_merge"] = merge_complete
        return merge_complete
    
    async def validate_data_consistency(self, auth_user: Dict, backend_user: Dict) -> bool:
        """Validate data consistency across services"""
        email_consistent = auth_user["email"] == backend_user.get("email")
        id_linked = backend_user.get("auth_user_id") == auth_user["id"]
        sync_valid = backend_user.get("synced", False)
        consistency_valid = email_consistent and id_linked and sync_valid
        self.enterprise_validations["data_consistency"] = consistency_valid
        return consistency_valid

class OAuthSessionManager:
    """Manager for OAuth session operations"""
    
    def __init__(self):
        self.active_sessions = {}
        self.enterprise_config = get_enterprise_config()
    
    async def create_oauth_session(self, user_data: Dict[str, Any], tokens: Dict[str, str]) -> str:
        """Create OAuth user session"""
        session_id = f"oauth_session_{uuid.uuid4()}"
        session_data = self._build_session_data(user_data, tokens)
        self.active_sessions[session_id] = session_data
        return session_id
    
    def _build_session_data(self, user_data: Dict, tokens: Dict) -> Dict[str, Any]:
        """Build session data from OAuth user and tokens"""
        return {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "auth_provider": user_data["auth_provider"],
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
    
    async def validate_session(self, session_id: str) -> bool:
        """Validate OAuth session is active and valid"""
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        session_active = self._is_session_active(session)
        token_valid = await self._validate_session_token(session)
        return session_active and token_valid
    
    def _is_session_active(self, session: Dict[str, Any]) -> bool:
        """Check if session is still active"""
        last_activity = session.get("last_activity", datetime.min.replace(tzinfo=timezone.utc))
        session_timeout = timedelta(hours=24)  # 24 hour session timeout
        return datetime.now(timezone.utc) - last_activity < session_timeout
    
    async def _validate_session_token(self, session: Dict[str, Any]) -> bool:
        """Validate session access token"""
        access_token = session.get("access_token")
        return access_token is not None and len(access_token) > 0
    
    async def refresh_session(self, session_id: str) -> bool:
        """Refresh OAuth session activity"""
        session = self.active_sessions.get(session_id)
        if session:
            session["last_activity"] = datetime.now(timezone.utc)
            return True
        return False
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate OAuth session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False

def create_oauth_flow_manager() -> OAuthFlowManager:
    """Factory function for OAuth flow manager"""
    return OAuthFlowManager()

def create_oauth_validator() -> OAuthValidator:
    """Factory function for OAuth validator"""
    return OAuthValidator()

def create_oauth_session_manager() -> OAuthSessionManager:
    """Factory function for OAuth session manager"""
    return OAuthSessionManager()