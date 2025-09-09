"""
Golden Path Unit Tests: Authentication Token Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Ensure secure authentication enables trusted access to AI platform
- Value Impact: Secure token validation prevents unauthorized access while enabling seamless user experience
- Strategic/Revenue Impact: Critical for $500K+ ARR - enterprise security and compliance requirements

CRITICAL: This test validates the business logic for JWT/OAuth token processing that enables
secure access to the AI platform. Authentication failures block business value delivery,
while security vulnerabilities can cause enterprise customer loss and regulatory violations.

Key Authentication Areas Tested:
1. JWT Token Creation - Secure token generation with proper claims
2. Token Validation - Business rules for token verification and security
3. OAuth Flow Processing - Third-party authentication integration business logic
4. Permission Management - Role-based access control for different user tiers
5. Session Lifecycle - Token refresh, expiration, and cleanup business logic
"""

import pytest
import jwt
import hashlib
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass, field
from enum import Enum

# Import business logic components for testing
from test_framework.base import BaseTestCase
from shared.types.core_types import (
    UserID, SessionID, ensure_user_id
)


class UserTier(Enum):
    """Business tiers for user access levels."""
    FREE = "free"
    EARLY = "early"  
    MID = "mid"
    ENTERPRISE = "enterprise"


class AuthenticationMethod(Enum):
    """Authentication methods supported by the business."""
    EMAIL_PASSWORD = "email_password"
    OAUTH_GOOGLE = "oauth_google"
    OAUTH_GITHUB = "oauth_github"
    OAUTH_MICROSOFT = "oauth_microsoft"
    API_KEY = "api_key"


class TokenType(Enum):
    """Types of tokens used in authentication business logic."""
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    SESSION_TOKEN = "session_token"
    API_TOKEN = "api_token"


@dataclass
class UserProfile:
    """Business user profile for authentication context."""
    user_id: UserID
    email: str
    tier: UserTier
    permissions: Set[str]
    subscription_active: bool = True
    enterprise_features_enabled: bool = False
    mfa_enabled: bool = False
    last_login: Optional[datetime] = None


@dataclass
class TokenClaims:
    """JWT token claims for business authentication."""
    user_id: UserID
    email: str
    tier: UserTier
    permissions: List[str]
    session_id: SessionID
    issued_at: datetime
    expires_at: datetime
    token_type: TokenType
    business_context: Dict[str, Any] = field(default_factory=dict)


class AuthenticationTokenManager:
    """Business logic for managing authentication tokens."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or "test-secret-key-for-business-logic-validation"
        self.token_algorithm = "HS256"
        self.business_permission_rules = self._initialize_permission_rules()
        self.active_tokens: Dict[str, TokenClaims] = {}
        self.revoked_tokens: Set[str] = set()
        self.login_attempts: List[Dict[str, Any]] = []
        
    def _initialize_permission_rules(self) -> Dict[UserTier, Dict[str, Any]]:
        """Initialize business rules for user tier permissions."""
        return {
            UserTier.FREE: {
                "permissions": ["basic_chat", "view_usage"],
                "rate_limits": {"requests_per_minute": 10, "tokens_per_day": 1000},
                "features": ["basic_ai_chat"],
                "business_value": "freemium_conversion_funnel"
            },
            UserTier.EARLY: {
                "permissions": ["basic_chat", "view_usage", "export_data", "priority_support"],
                "rate_limits": {"requests_per_minute": 30, "tokens_per_day": 10000},
                "features": ["basic_ai_chat", "data_export", "email_support"],
                "business_value": "early_adopter_retention"
            },
            UserTier.MID: {
                "permissions": ["basic_chat", "view_usage", "export_data", "advanced_analytics", "api_access"],
                "rate_limits": {"requests_per_minute": 100, "tokens_per_day": 100000},
                "features": ["advanced_ai_chat", "analytics_dashboard", "api_integration"],
                "business_value": "primary_revenue_segment"
            },
            UserTier.ENTERPRISE: {
                "permissions": ["basic_chat", "view_usage", "export_data", "advanced_analytics", "api_access", 
                              "admin_panel", "user_management", "custom_integrations", "priority_processing"],
                "rate_limits": {"requests_per_minute": 1000, "tokens_per_day": 1000000},
                "features": ["enterprise_ai_chat", "admin_dashboard", "sso_integration", "dedicated_support"],
                "business_value": "high_value_enterprise_accounts"
            }
        }
    
    def create_jwt_token(self, user_profile: UserProfile, token_type: TokenType = TokenType.ACCESS_TOKEN) -> str:
        """Create JWT token with business-appropriate claims."""
        
        # Business Rule: Determine token lifetime based on type and user tier
        if token_type == TokenType.ACCESS_TOKEN:
            lifetime_hours = 8 if user_profile.tier in [UserTier.ENTERPRISE] else 1
        elif token_type == TokenType.REFRESH_TOKEN:
            lifetime_hours = 720 if user_profile.tier in [UserTier.ENTERPRISE] else 168  # 30 days vs 7 days
        else:
            lifetime_hours = 24
            
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=lifetime_hours)
        session_id = SessionID(f"session-{secrets.token_urlsafe(16)}")
        
        # Business Rule: Build token claims based on user tier and business permissions
        permission_rules = self.business_permission_rules[user_profile.tier]
        
        token_claims = TokenClaims(
            user_id=user_profile.user_id,
            email=user_profile.email,
            tier=user_profile.tier,
            permissions=permission_rules["permissions"],
            session_id=session_id,
            issued_at=now,
            expires_at=expires_at,
            token_type=token_type,
            business_context={
                "rate_limits": permission_rules["rate_limits"],
                "features": permission_rules["features"],
                "business_value": permission_rules["business_value"],
                "subscription_active": user_profile.subscription_active,
                "enterprise_features": user_profile.enterprise_features_enabled
            }
        )
        
        # Business Rule: Create JWT with standardized claims
        jwt_payload = {
            "user_id": str(token_claims.user_id),
            "email": token_claims.email,
            "tier": token_claims.tier.value,
            "permissions": token_claims.permissions,
            "session_id": str(token_claims.session_id),
            "iat": int(token_claims.issued_at.timestamp()),
            "exp": int(token_claims.expires_at.timestamp()),
            "token_type": token_claims.token_type.value,
            "business_context": token_claims.business_context
        }
        
        # Create and store token
        jwt_token = jwt.encode(jwt_payload, self.secret_key, algorithm=self.token_algorithm)
        self.active_tokens[jwt_token] = token_claims
        
        return jwt_token
    
    def validate_jwt_token(self, jwt_token: str) -> Dict[str, Any]:
        """Validate JWT token with business rule verification."""
        validation_result = {
            "valid": False,
            "user_id": None,
            "permissions": [],
            "business_context": {},
            "validation_errors": [],
            "security_warnings": []
        }
        
        try:
            # Business Rule 1: Check if token was revoked
            if jwt_token in self.revoked_tokens:
                validation_result["validation_errors"].append("Token has been revoked")
                return validation_result
            
            # Business Rule 2: Decode and validate JWT structure
            decoded_payload = jwt.decode(
                jwt_token, 
                self.secret_key, 
                algorithms=[self.token_algorithm],
                options={"verify_exp": True}
            )
            
            # Business Rule 3: Validate required business claims are present
            required_claims = ["user_id", "email", "tier", "permissions", "session_id", "business_context"]
            for claim in required_claims:
                if claim not in decoded_payload:
                    validation_result["validation_errors"].append(f"Missing required claim: {claim}")
            
            if validation_result["validation_errors"]:
                return validation_result
            
            # Business Rule 4: Validate user tier permissions
            user_tier = UserTier(decoded_payload["tier"])
            expected_permissions = self.business_permission_rules[user_tier]["permissions"]
            token_permissions = decoded_payload["permissions"]
            
            # Check for permission escalation - unexpected permissions
            for permission in token_permissions:
                if permission not in expected_permissions:
                    validation_result["security_warnings"].append(f"Unexpected permission: {permission}")
            
            # Business Security Rule: Detect potential tier escalation attempts
            # A legitimate token for a tier should have ALL expected permissions for that tier
            # Tokens with only some permissions suggest possible escalation from a lower tier
            if user_tier in [UserTier.ENTERPRISE, UserTier.MID]:
                missing_permissions = set(expected_permissions) - set(token_permissions)
                if missing_permissions:
                    # If high-value permissions are missing, this suggests tier escalation
                    high_value_permissions = {"admin_panel", "user_management", "advanced_analytics", "api_access", "custom_integrations"}
                    has_high_value_perms = any(perm in token_permissions for perm in high_value_permissions)
                    missing_high_value_perms = missing_permissions & high_value_permissions
                    
                    if has_high_value_perms and missing_high_value_perms:
                        validation_result["security_warnings"].append(
                            f"Potential tier escalation detected: {user_tier.value} tier token missing expected permissions: {sorted(missing_permissions)}"
                        )
                        
                        # Also specifically flag the suspicious escalated permissions
                        escalated_high_value_perms = set(token_permissions) & high_value_permissions
                        if escalated_high_value_perms:
                            for perm in escalated_high_value_perms:
                                validation_result["security_warnings"].append(f"Suspicious {perm} permission in incomplete {user_tier.value} token")
            
            # Business Rule 5: Validate business context integrity
            business_context = decoded_payload["business_context"]
            if not business_context.get("subscription_active", False):
                validation_result["validation_errors"].append("Subscription is not active")
                return validation_result
            
            # Business Rule 6: Success - populate validation result
            validation_result.update({
                "valid": True,
                "user_id": ensure_user_id(decoded_payload["user_id"]),
                "permissions": token_permissions,
                "business_context": business_context,
                "tier": user_tier,
                "session_id": decoded_payload["session_id"]
            })
            
        except jwt.ExpiredSignatureError:
            validation_result["validation_errors"].append("Token has expired")
        except jwt.InvalidTokenError as e:
            validation_result["validation_errors"].append(f"Invalid token: {str(e)}")
        except Exception as e:
            validation_result["validation_errors"].append(f"Token validation error: {str(e)}")
            
        return validation_result
    
    def process_oauth_callback(self, oauth_provider: str, oauth_code: str, state: str) -> Dict[str, Any]:
        """Process OAuth callback with business logic validation."""
        oauth_result = {
            "success": False,
            "user_profile": None,
            "access_token": None,
            "business_context": {},
            "errors": []
        }
        
        # Business Rule: Validate OAuth provider is supported
        supported_providers = ["google", "github", "microsoft"]
        if oauth_provider not in supported_providers:
            oauth_result["errors"].append(f"Unsupported OAuth provider: {oauth_provider}")
            return oauth_result
        
        # Simulate OAuth provider response (in real implementation, this would call external APIs)
        mock_oauth_response = self._simulate_oauth_provider_response(oauth_provider, oauth_code)
        
        if not mock_oauth_response["success"]:
            oauth_result["errors"].extend(mock_oauth_response["errors"])
            return oauth_result
        
        # Business Rule: Create or update user profile from OAuth data
        oauth_user_data = mock_oauth_response["user_data"]
        user_profile = UserProfile(
            user_id=ensure_user_id(f"oauth-{oauth_provider}-{oauth_user_data['id']}"),
            email=oauth_user_data["email"],
            tier=UserTier.FREE,  # New OAuth users start with free tier
            permissions=set(self.business_permission_rules[UserTier.FREE]["permissions"]),
            enterprise_features_enabled=False
        )
        
        # Business Rule: Generate business-appropriate access token
        access_token = self.create_jwt_token(user_profile, TokenType.ACCESS_TOKEN)
        
        oauth_result.update({
            "success": True,
            "user_profile": user_profile,
            "access_token": access_token,
            "business_context": {
                "auth_method": f"oauth_{oauth_provider}",
                "new_user": True,
                "conversion_opportunity": True,
                "business_tier": user_profile.tier.value
            }
        })
        
        return oauth_result
    
    def _simulate_oauth_provider_response(self, provider: str, code: str) -> Dict[str, Any]:
        """Simulate OAuth provider response for testing business logic."""
        # This simulates successful OAuth responses for testing
        provider_responses = {
            "google": {
                "success": True,
                "user_data": {
                    "id": "google-123456",
                    "email": "user@gmail.com",
                    "name": "Test Google User",
                    "verified_email": True
                }
            },
            "github": {
                "success": True,
                "user_data": {
                    "id": "github-789012",
                    "email": "developer@github.com",
                    "name": "Test GitHub User",
                    "login": "testdev"
                }
            },
            "microsoft": {
                "success": True,
                "user_data": {
                    "id": "microsoft-345678",
                    "email": "enterprise@company.com",
                    "name": "Test Microsoft User",
                    "userPrincipalName": "enterprise@company.com"
                }
            }
        }
        
        return provider_responses.get(provider, {
            "success": False,
            "errors": [f"Unknown provider: {provider}"]
        })
    
    def revoke_token(self, jwt_token: str, reason: str = "user_logout") -> bool:
        """Revoke token for business security requirements."""
        if jwt_token in self.active_tokens:
            # Business Rule: Add to revoked tokens for security
            self.revoked_tokens.add(jwt_token)
            
            # Business Rule: Remove from active tokens
            del self.active_tokens[jwt_token]
            
            # Business Rule: Log revocation for audit trail
            self.login_attempts.append({
                "action": "token_revoked",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc),
                "token_hash": hashlib.sha256(jwt_token.encode()).hexdigest()[:16]
            })
            
            return True
        return False


@pytest.mark.unit
@pytest.mark.golden_path
class TestAuthenticationTokenBusinessLogic(BaseTestCase):
    """Test authentication token business logic for secure platform access."""

    def setup_method(self):
        """Setup test environment for each test."""
        super().setup_method()
        self.token_manager = AuthenticationTokenManager()
        self.test_user_free = UserProfile(
            user_id=ensure_user_id("free-user-123"),
            email="free.user@test.com",
            tier=UserTier.FREE,
            permissions=set(["basic_chat", "view_usage"])
        )
        self.test_user_enterprise = UserProfile(
            user_id=ensure_user_id("enterprise-user-456"),
            email="enterprise.user@company.com",
            tier=UserTier.ENTERPRISE,
            permissions=set(["basic_chat", "view_usage", "admin_panel", "user_management"]),
            enterprise_features_enabled=True
        )

    def test_jwt_token_creation_business_requirements(self):
        """Test JWT token creation includes all required business claims."""
        # Business Value: Tokens must contain sufficient information for business operations
        
        # Test access token creation for free user
        free_token = self.token_manager.create_jwt_token(self.test_user_free, TokenType.ACCESS_TOKEN)
        assert isinstance(free_token, str), "Token must be a string"
        assert len(free_token) > 100, "Token must contain substantial claims data"
        
        # Decode token to verify business claims
        decoded = jwt.decode(free_token, self.token_manager.secret_key, algorithms=["HS256"])
        
        # Business Rule 1: Required user identification claims
        assert decoded["user_id"] == str(self.test_user_free.user_id), "Token must identify correct user"
        assert decoded["email"] == self.test_user_free.email, "Token must contain user email"
        assert decoded["tier"] == UserTier.FREE.value, "Token must specify user tier"
        
        # Business Rule 2: Business permissions must be included
        assert "permissions" in decoded, "Token must contain permissions"
        assert "basic_chat" in decoded["permissions"], "Free users must have basic chat permission"
        assert "admin_panel" not in decoded["permissions"], "Free users must not have admin permissions"
        
        # Business Rule 3: Business context must be present
        assert "business_context" in decoded, "Token must contain business context"
        business_context = decoded["business_context"]
        assert "rate_limits" in business_context, "Token must specify rate limits"
        assert "business_value" in business_context, "Token must indicate business segment"
        assert business_context["business_value"] == "freemium_conversion_funnel", "Free users must be marked for conversion"
        
        # Business Rule 4: Token expiration appropriate for tier
        exp_time = datetime.fromtimestamp(decoded["exp"], timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], timezone.utc)
        token_lifetime = exp_time - iat_time
        assert token_lifetime.total_seconds() <= 3600, "Free user tokens must expire within 1 hour"

    def test_enterprise_token_business_privileges(self):
        """Test enterprise tokens have appropriate business privileges."""
        # Business Value: Enterprise users must have extended privileges and token lifetime
        
        enterprise_token = self.token_manager.create_jwt_token(self.test_user_enterprise, TokenType.ACCESS_TOKEN)
        decoded = jwt.decode(enterprise_token, self.token_manager.secret_key, algorithms=["HS256"])
        
        # Business Rule 1: Enterprise permissions must be present
        permissions = decoded["permissions"]
        enterprise_permissions = ["admin_panel", "user_management", "custom_integrations", "priority_processing"]
        for perm in enterprise_permissions:
            assert perm in permissions, f"Enterprise users must have {perm} permission"
        
        # Business Rule 2: Enterprise business context
        business_context = decoded["business_context"]
        assert business_context["business_value"] == "high_value_enterprise_accounts", "Enterprise users must be flagged as high value"
        assert business_context["rate_limits"]["requests_per_minute"] == 1000, "Enterprise users must have high rate limits"
        assert business_context["enterprise_features"] is True, "Enterprise features must be enabled"
        
        # Business Rule 3: Extended token lifetime for enterprise
        exp_time = datetime.fromtimestamp(decoded["exp"], timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], timezone.utc)
        token_lifetime = exp_time - iat_time
        assert token_lifetime.total_seconds() >= 28800, "Enterprise tokens must have at least 8 hour lifetime"

    def test_jwt_token_validation_business_security(self):
        """Test JWT token validation enforces business security rules."""
        # Business Value: Token validation must prevent unauthorized access while allowing legitimate users
        
        # Create valid token
        valid_token = self.token_manager.create_jwt_token(self.test_user_free)
        
        # Test valid token validation
        validation_result = self.token_manager.validate_jwt_token(valid_token)
        assert validation_result["valid"] is True, "Valid token must pass validation"
        assert validation_result["user_id"] == self.test_user_free.user_id, "Validation must return correct user ID"
        assert len(validation_result["validation_errors"]) == 0, "Valid token must have no validation errors"
        
        # Business Rule 1: Expired tokens must be rejected
        # Create token with past expiration (simulate expired token)
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        expired_payload = {
            "user_id": str(self.test_user_free.user_id),
            "email": self.test_user_free.email,
            "tier": self.test_user_free.tier.value,
            "permissions": ["basic_chat"],
            "session_id": "test-session",
            "iat": int(past_time.timestamp()),
            "exp": int((past_time + timedelta(hours=1)).timestamp()),  # Already expired
            "token_type": TokenType.ACCESS_TOKEN.value,
            "business_context": {"subscription_active": True}
        }
        
        expired_token = jwt.encode(expired_payload, self.token_manager.secret_key, algorithm="HS256")
        expired_validation = self.token_manager.validate_jwt_token(expired_token)
        assert expired_validation["valid"] is False, "Expired tokens must be rejected"
        assert "expired" in expired_validation["validation_errors"][0].lower(), "Expiration error must be specified"
        
        # Business Rule 2: Invalid signature must be rejected
        tampered_token = valid_token[:-5] + "XXXXX"  # Tamper with signature
        tampered_validation = self.token_manager.validate_jwt_token(tampered_token)
        assert tampered_validation["valid"] is False, "Tampered tokens must be rejected"
        assert len(tampered_validation["validation_errors"]) > 0, "Tampered tokens must have validation errors"
        
        # Business Rule 3: Revoked tokens must be rejected
        self.token_manager.revoke_token(valid_token, "security_breach")
        revoked_validation = self.token_manager.validate_jwt_token(valid_token)
        assert revoked_validation["valid"] is False, "Revoked tokens must be rejected"
        assert "revoked" in revoked_validation["validation_errors"][0].lower(), "Revocation error must be specified"

    def test_oauth_callback_processing_business_logic(self):
        """Test OAuth callback processing follows business user onboarding rules."""
        # Business Value: OAuth integration must create proper business user profiles and conversion opportunities
        
        # Test Google OAuth callback
        google_result = self.token_manager.process_oauth_callback("google", "auth-code-123", "state-456")
        assert google_result["success"] is True, "Google OAuth must succeed"
        
        # Business Rule 1: New OAuth users start with free tier for conversion
        user_profile = google_result["user_profile"]
        assert user_profile.tier == UserTier.FREE, "OAuth users must start with free tier"
        assert "basic_chat" in user_profile.permissions, "OAuth users must have basic permissions"
        assert user_profile.enterprise_features_enabled is False, "OAuth users must not have enterprise features initially"
        
        # Business Rule 2: Business context must indicate conversion opportunity
        business_context = google_result["business_context"]
        assert business_context["new_user"] is True, "OAuth must identify new users"
        assert business_context["conversion_opportunity"] is True, "OAuth users must be flagged for conversion"
        assert business_context["auth_method"] == "oauth_google", "Auth method must be tracked for analytics"
        
        # Business Rule 3: Access token must be generated for immediate use
        access_token = google_result["access_token"]
        assert access_token, "OAuth must generate access token"
        
        # Validate the generated token has proper business claims
        token_validation = self.token_manager.validate_jwt_token(access_token)
        assert token_validation["valid"] is True, "OAuth-generated token must be valid"
        assert token_validation["tier"] == UserTier.FREE, "OAuth token must reflect free tier"
        
        # Test unsupported OAuth provider
        unsupported_result = self.token_manager.process_oauth_callback("unsupported", "code", "state")
        assert unsupported_result["success"] is False, "Unsupported providers must be rejected"
        assert "Unsupported OAuth provider" in unsupported_result["errors"][0], "Error message must be clear"

    def test_permission_escalation_prevention_business_security(self):
        """Test permission escalation attempts are blocked for business security."""
        # Business Value: Prevent unauthorized access to higher-tier business features
        
        # Create free user token
        free_token = self.token_manager.create_jwt_token(self.test_user_free)
        
        # Attempt to tamper with token to add enterprise permissions
        decoded_payload = jwt.decode(free_token, self.token_manager.secret_key, algorithms=["HS256"])
        decoded_payload["permissions"].extend(["admin_panel", "user_management"])  # Escalate permissions
        decoded_payload["tier"] = "enterprise"  # Escalate tier
        
        # Create tampered token
        tampered_token = jwt.encode(decoded_payload, self.token_manager.secret_key, algorithm="HS256")
        
        # Business Rule: Validation must detect permission escalation
        validation_result = self.token_manager.validate_jwt_token(tampered_token)
        
        # The validation should still succeed technically (since signature is valid)
        # but should flag security warnings for unexpected permissions
        assert len(validation_result["security_warnings"]) > 0, "Permission escalation must trigger security warnings"
        
        # Verify specific escalated permissions are flagged
        warning_text = " ".join(validation_result["security_warnings"])
        assert "admin_panel" in warning_text, "Admin permission escalation must be detected"
        assert "user_management" in warning_text, "Management permission escalation must be detected"

    def test_multi_tier_token_business_differentiation(self):
        """Test tokens properly differentiate between business tiers."""
        # Business Value: Different tiers must have appropriate access levels and business treatment
        
        # Create users for all tiers
        users = {
            UserTier.FREE: UserProfile(
                user_id=ensure_user_id("free-user-001"), email="free@test.com", tier=UserTier.FREE,
                permissions=set(["basic_chat", "view_usage"])
            ),
            UserTier.EARLY: UserProfile(
                user_id=ensure_user_id("early-user-002"), email="early@test.com", tier=UserTier.EARLY,
                permissions=set(["basic_chat", "view_usage", "export_data"])
            ),
            UserTier.MID: UserProfile(
                user_id=ensure_user_id("mid-user-003"), email="mid@test.com", tier=UserTier.MID,
                permissions=set(["basic_chat", "view_usage", "export_data", "advanced_analytics"])
            ),
            UserTier.ENTERPRISE: UserProfile(
                user_id=ensure_user_id("enterprise-user-004"), email="enterprise@test.com", tier=UserTier.ENTERPRISE,
                permissions=set(["basic_chat", "view_usage", "admin_panel"])
            )
        }
        
        tokens = {}
        for tier, user in users.items():
            tokens[tier] = self.token_manager.create_jwt_token(user)
        
        # Business Rule 1: Rate limits must scale with tier
        rate_limits = {}
        for tier, token in tokens.items():
            decoded = jwt.decode(token, self.token_manager.secret_key, algorithms=["HS256"])
            rate_limits[tier] = decoded["business_context"]["rate_limits"]["requests_per_minute"]
        
        assert rate_limits[UserTier.FREE] < rate_limits[UserTier.EARLY], "Early tier must have higher rate limits than Free"
        assert rate_limits[UserTier.EARLY] < rate_limits[UserTier.MID], "Mid tier must have higher rate limits than Early"
        assert rate_limits[UserTier.MID] < rate_limits[UserTier.ENTERPRISE], "Enterprise must have highest rate limits"
        
        # Business Rule 2: Business value classification must be tier-appropriate
        business_values = {}
        for tier, token in tokens.items():
            decoded = jwt.decode(token, self.token_manager.secret_key, algorithms=["HS256"])
            business_values[tier] = decoded["business_context"]["business_value"]
        
        assert business_values[UserTier.FREE] == "freemium_conversion_funnel", "Free tier must focus on conversion"
        assert business_values[UserTier.ENTERPRISE] == "high_value_enterprise_accounts", "Enterprise must be flagged as high value"
        
        # Business Rule 3: Feature access must be tier-appropriate
        for tier, token in tokens.items():
            decoded = jwt.decode(token, self.token_manager.secret_key, algorithms=["HS256"])
            features = decoded["business_context"]["features"]
            
            if tier == UserTier.FREE:
                assert "basic_ai_chat" in features, "Free tier must have basic features"
                assert "admin_dashboard" not in features, "Free tier must not have admin features"
            elif tier == UserTier.ENTERPRISE:
                assert "enterprise_ai_chat" in features, "Enterprise must have advanced features"
                assert "admin_dashboard" in features, "Enterprise must have admin features"

    def test_token_lifecycle_business_management(self):
        """Test token lifecycle management supports business operations."""
        # Business Value: Proper token lifecycle prevents security issues and supports user experience
        
        # Create token for lifecycle testing
        test_token = self.token_manager.create_jwt_token(self.test_user_free)
        
        # Business Rule 1: Active tokens must be trackable
        assert test_token in self.token_manager.active_tokens, "Active tokens must be tracked"
        token_claims = self.token_manager.active_tokens[test_token]
        assert token_claims.user_id == self.test_user_free.user_id, "Token claims must match user"
        
        # Business Rule 2: Token validation must work for active tokens
        validation = self.token_manager.validate_jwt_token(test_token)
        assert validation["valid"] is True, "Active tokens must validate successfully"
        
        # Business Rule 3: Token revocation must work for security
        revocation_success = self.token_manager.revoke_token(test_token, "user_logout")
        assert revocation_success is True, "Token revocation must succeed"
        
        # Business Rule 4: Revoked tokens must not validate
        post_revocation_validation = self.token_manager.validate_jwt_token(test_token)
        assert post_revocation_validation["valid"] is False, "Revoked tokens must not validate"
        assert "revoked" in post_revocation_validation["validation_errors"][0], "Revocation reason must be clear"
        
        # Business Rule 5: Revocation must be audited
        assert len(self.token_manager.login_attempts) > 0, "Token revocation must be logged"
        latest_log = self.token_manager.login_attempts[-1]
        assert latest_log["action"] == "token_revoked", "Revocation must be logged correctly"
        assert latest_log["reason"] == "user_logout", "Revocation reason must be logged"

    def test_business_subscription_validation_in_tokens(self):
        """Test tokens validate business subscription status."""
        # Business Value: Inactive subscriptions must block access to prevent revenue loss
        
        # Create user with inactive subscription
        inactive_user = UserProfile(
            user_id=ensure_user_id("inactive-user-005"),
            email="inactive@test.com",
            tier=UserTier.MID,
            permissions=set(["basic_chat", "advanced_analytics"]),
            subscription_active=False  # Inactive subscription
        )
        
        # Business Rule 1: Tokens for inactive subscriptions should still be created (for grace period handling)
        token = self.token_manager.create_jwt_token(inactive_user)
        decoded = jwt.decode(token, self.token_manager.secret_key, algorithms=["HS256"])
        assert decoded["business_context"]["subscription_active"] is False, "Inactive subscription must be reflected in token"
        
        # Business Rule 2: Token validation must catch inactive subscriptions
        validation = self.token_manager.validate_jwt_token(token)
        assert validation["valid"] is False, "Tokens with inactive subscriptions must not validate"
        assert "Subscription is not active" in validation["validation_errors"], "Subscription status must be validated"
        
        # Business Rule 3: Active subscriptions must validate successfully
        active_user = UserProfile(
            user_id=ensure_user_id("active-user-006"),
            email="active@test.com",
            tier=UserTier.MID,
            permissions=set(["basic_chat", "advanced_analytics"]),
            subscription_active=True
        )
        
        active_token = self.token_manager.create_jwt_token(active_user)
        active_validation = self.token_manager.validate_jwt_token(active_token)
        assert active_validation["valid"] is True, "Active subscriptions must validate successfully"
        assert active_validation["business_context"]["subscription_active"] is True, "Active status must be preserved"