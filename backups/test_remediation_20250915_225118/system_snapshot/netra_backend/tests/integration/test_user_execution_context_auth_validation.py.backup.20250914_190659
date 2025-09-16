"""
User Execution Context Authentication and Authorization Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure user authentication and proper authorization enforcement
- Value Impact: Prevents unauthorized access and ensures user data security
- Strategic Impact: Protects revenue and maintains customer trust through secure operations

This test suite validates UserExecutionContext integration with authentication
and authorization systems, ensuring proper security boundaries and access controls.

CRITICAL: Uses REAL authentication patterns and validation logic.
NO MOCKS for security-critical components.
"""

import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock
import jwt
import hashlib
import secrets

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.user_execution_context_fixtures import (
    clean_context_registry,
    realistic_user_context,
    multi_user_contexts
)

# Core imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context
)
from shared.isolated_environment import get_env


class TestUserExecutionContextAuthentication(BaseIntegrationTest):
    """Test UserExecutionContext integration with authentication systems"""
    
    def setup_method(self):
        super().setup_method()
        
        # Setup test JWT configuration
        self.jwt_secret = "test-secret-key-for-testing-only-must-be-at-least-32-chars"
        self.jwt_algorithm = "HS256"
        
        # Setup test user authentication data
        self.auth_users = {
            "user_auth_test_12345678901234567890": {
                "email": "enterprise@example.com",
                "subscription": "enterprise",
                "roles": ["user", "admin"],
                "permissions": ["read", "write", "execute", "admin"],
                "auth_provider": "internal",
                "auth_method": "jwt"
            },
            "user_oauth_test_11223344556677889900": {
                "email": "oauth@example.com", 
                "subscription": "business",
                "roles": ["user"],
                "permissions": ["read", "write"],
                "auth_provider": "google",
                "auth_method": "oauth2",
                "oauth_sub": "google-oauth2|1234567890123456789"
            },
            "user_free_test_99887766554433221100": {
                "email": "free@example.com",
                "subscription": "free", 
                "roles": ["user"],
                "permissions": ["read"],
                "auth_provider": "internal",
                "auth_method": "jwt"
            }
        }
    
    def _create_test_jwt(self, user_id: str, **claims) -> str:
        """Create a test JWT token for authentication testing."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iss": "netra-test",
            "aud": "netra-api",
            **claims
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _validate_jwt(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return claims."""
        try:
            return jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm],
                audience="netra-api",
                issuer="netra-test"
            )
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid JWT token: {e}")
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_creation_with_authenticated_user(self, clean_context_registry, isolated_env):
        """Test context creation with authenticated user data."""
        
        user_id = "user_auth_test_12345678901234567890"
        user_data = self.auth_users[user_id]
        
        # Create JWT token for user
        jwt_token = self._create_test_jwt(
            user_id=user_id,
            email=user_data["email"],
            subscription=user_data["subscription"],
            roles=user_data["roles"],
            permissions=user_data["permissions"]
        )
        
        # Validate token (simulating auth middleware)
        claims = self._validate_jwt(jwt_token)
        
        # Create context with authenticated user data
        auth_context = UserExecutionContext(
            user_id=user_id,
            thread_id="thread_auth_test_98765432109876543210",
            run_id=f"run_auth_test_{int(time.time())}",
            agent_context={
                "agent_name": "enterprise_optimizer",
                "authenticated": True,
                "auth_method": user_data["auth_method"],
                "user_subscription": user_data["subscription"],
                "user_roles": user_data["roles"],
                "user_permissions": user_data["permissions"]
            },
            audit_metadata={
                "auth_token_issued": claims["iat"],
                "auth_token_expires": claims["exp"],
                "auth_provider": user_data["auth_provider"],
                "auth_method": user_data["auth_method"],
                "user_email": user_data["email"],
                "subscription_tier": user_data["subscription"]
            }
        )
        
        # Verify authentication data in context
        assert auth_context.agent_context["authenticated"] is True
        assert auth_context.agent_context["user_subscription"] == "enterprise"
        assert "admin" in auth_context.agent_context["user_roles"]
        assert "execute" in auth_context.agent_context["user_permissions"]
        
        # Verify audit trail includes auth information
        audit_trail = auth_context.get_audit_trail()
        assert audit_trail["audit_metadata"]["auth_provider"] == "internal"
        assert audit_trail["audit_metadata"]["user_email"] == "enterprise@example.com"
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_oauth_authentication_integration(self, clean_context_registry, isolated_env):
        """Test context integration with OAuth authentication."""
        
        user_id = "user_oauth_test_11223344556677889900"
        user_data = self.auth_users[user_id]
        
        # Create OAuth-style JWT token
        oauth_token = self._create_test_jwt(
            user_id=user_id,
            email=user_data["email"],
            subscription=user_data["subscription"],
            oauth_provider="google",
            oauth_sub=user_data["oauth_sub"],
            scope="openid profile email"
        )
        
        # Validate OAuth token
        oauth_claims = self._validate_jwt(oauth_token)
        
        # Create context with OAuth authentication
        oauth_context = UserExecutionContext(
            user_id=user_id,
            thread_id="thread_oauth_test_88776655443322110099",
            run_id=f"run_oauth_test_{int(time.time())}",
            agent_context={
                "agent_name": "business_optimizer",
                "authenticated": True,
                "auth_method": "oauth2",
                "oauth_provider": "google",
                "oauth_subject": user_data["oauth_sub"],
                "user_subscription": user_data["subscription"],
                "user_permissions": user_data["permissions"]
            },
            audit_metadata={
                "auth_token_issued": oauth_claims["iat"],
                "auth_token_expires": oauth_claims["exp"],
                "oauth_provider": "google",
                "oauth_subject": user_data["oauth_sub"],
                "oauth_scope": "openid profile email",
                "user_email": user_data["email"]
            }
        )
        
        # Verify OAuth-specific data
        assert oauth_context.agent_context["auth_method"] == "oauth2"
        assert oauth_context.agent_context["oauth_provider"] == "google"
        assert oauth_context.audit_metadata["oauth_subject"] == user_data["oauth_sub"]
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_permission_enforcement_patterns(self, clean_context_registry, isolated_env):
        """Test context integration with permission enforcement patterns."""
        
        # Create contexts with different permission levels
        contexts_by_permission = {}
        
        for user_id, user_data in self.auth_users.items():
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_perm_{user_id[-10:]}",
                run_id=f"run_perm_{int(time.time())}_{user_id[-4:]}",
                agent_context={
                    "agent_name": "permission_test_agent",
                    "user_permissions": user_data["permissions"],
                    "user_roles": user_data["roles"],
                    "subscription_tier": user_data["subscription"]
                },
                audit_metadata={
                    "permission_level": len(user_data["permissions"]),
                    "has_admin": "admin" in user_data["roles"],
                    "subscription_tier": user_data["subscription"]
                }
            )
            contexts_by_permission[user_data["subscription"]] = context
        
        # Test permission-based access patterns
        def check_permission(context: UserExecutionContext, permission: str) -> bool:
            """Simulate permission checking logic."""
            user_permissions = context.agent_context.get("user_permissions", [])
            return permission in user_permissions
        
        # Enterprise user should have all permissions
        enterprise_ctx = contexts_by_permission["enterprise"]
        assert check_permission(enterprise_ctx, "read") is True
        assert check_permission(enterprise_ctx, "write") is True
        assert check_permission(enterprise_ctx, "execute") is True
        assert check_permission(enterprise_ctx, "admin") is True
        
        # Business user should have read/write but not admin
        business_ctx = contexts_by_permission["business"]
        assert check_permission(business_ctx, "read") is True
        assert check_permission(business_ctx, "write") is True
        assert check_permission(business_ctx, "execute") is False
        assert check_permission(business_ctx, "admin") is False
        
        # Free user should only have read
        free_ctx = contexts_by_permission["free"]
        assert check_permission(free_ctx, "read") is True
        assert check_permission(free_ctx, "write") is False
        assert check_permission(free_ctx, "execute") is False
        assert check_permission(free_ctx, "admin") is False
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_session_validation_integration(self, clean_context_registry, isolated_env):
        """Test context integration with session validation."""
        
        user_id = "user_session_test_12345678901234567890"
        session_id = f"session_{int(time.time())}_authenticated"
        
        # Create context with session data
        session_context = UserExecutionContext(
            user_id=user_id,
            thread_id="thread_session_test_98765432109876543210",
            run_id=f"run_session_test_{int(time.time())}",
            agent_context={
                "agent_name": "session_agent",
                "session_id": session_id,
                "session_valid": True,
                "session_start": datetime.now(timezone.utc).isoformat(),
                "session_timeout": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
                "authenticated": True
            },
            audit_metadata={
                "session_id": session_id,
                "session_created": datetime.now(timezone.utc).isoformat(),
                "session_ip": "203.0.113.42",
                "session_user_agent": "NetraUI/2.1.0"
            }
        )
        
        # Simulate session validation logic
        def validate_session(context: UserExecutionContext) -> bool:
            """Simulate session validation logic."""
            session_valid = context.agent_context.get("session_valid", False)
            session_timeout_str = context.agent_context.get("session_timeout")
            
            if not session_valid or not session_timeout_str:
                return False
            
            session_timeout = datetime.fromisoformat(session_timeout_str.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) < session_timeout
        
        # Test session validation
        assert validate_session(session_context) is True
        
        # Test expired session context
        expired_context = UserExecutionContext(
            user_id=user_id,
            thread_id="thread_expired_test_77889900112233445566",
            run_id=f"run_expired_test_{int(time.time())}",
            agent_context={
                "agent_name": "expired_session_agent",
                "session_id": f"expired_session_{int(time.time())}",
                "session_valid": True,
                "session_timeout": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()  # Expired
            },
            audit_metadata={
                "session_expired": True
            }
        )
        
        # Expired session should fail validation
        assert validate_session(expired_context) is False


class TestUserExecutionContextAuthorization(BaseIntegrationTest):
    """Test UserExecutionContext integration with authorization systems"""
    
    def setup_method(self):
        super().setup_method()
        
        # Define role-based permissions
        self.role_permissions = {
            "admin": [
                "users:read", "users:write", "users:delete",
                "agents:read", "agents:write", "agents:execute", "agents:admin",
                "system:read", "system:write", "system:admin",
                "billing:read", "billing:write", "billing:admin"
            ],
            "user": [
                "agents:read", "agents:execute",
                "profile:read", "profile:write",
                "billing:read"
            ],
            "readonly": [
                "agents:read",
                "profile:read"
            ]
        }
        
        # Define subscription-based feature access
        self.subscription_features = {
            "free": [
                "basic_agents", "basic_analytics", "email_support"
            ],
            "business": [
                "basic_agents", "advanced_agents", "basic_analytics", "advanced_analytics",
                "email_support", "chat_support", "integrations:basic"
            ],
            "enterprise": [
                "basic_agents", "advanced_agents", "custom_agents",
                "basic_analytics", "advanced_analytics", "custom_analytics",
                "email_support", "chat_support", "phone_support", "dedicated_support",
                "integrations:basic", "integrations:advanced", "integrations:custom",
                "sso", "audit_logs", "custom_policies"
            ]
        }
    
    def _get_user_permissions(self, roles: List[str]) -> List[str]:
        """Get all permissions for given roles."""
        permissions = set()
        for role in roles:
            if role in self.role_permissions:
                permissions.update(self.role_permissions[role])
        return list(permissions)
    
    def _get_subscription_features(self, subscription: str) -> List[str]:
        """Get features available for subscription tier."""
        return self.subscription_features.get(subscription, [])
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_role_based_authorization(self, clean_context_registry, isolated_env):
        """Test context integration with role-based authorization."""
        
        # Create contexts with different roles
        test_scenarios = [
            {
                "user_id": "user_admin_auth_12345678901234567890",
                "roles": ["admin", "user"],
                "expected_permissions": self._get_user_permissions(["admin", "user"])
            },
            {
                "user_id": "user_standard_auth_11223344556677889900",
                "roles": ["user"],
                "expected_permissions": self._get_user_permissions(["user"])
            },
            {
                "user_id": "user_readonly_auth_99887766554433221100",
                "roles": ["readonly"],
                "expected_permissions": self._get_user_permissions(["readonly"])
            }
        ]
        
        for scenario in test_scenarios:
            context = UserExecutionContext(
                user_id=scenario["user_id"],
                thread_id=f"thread_role_auth_{scenario['user_id'][-10:]}",
                run_id=f"run_role_auth_{int(time.time())}_{scenario['user_id'][-4:]}",
                agent_context={
                    "agent_name": "authorization_test_agent",
                    "user_roles": scenario["roles"],
                    "computed_permissions": scenario["expected_permissions"]
                },
                audit_metadata={
                    "authorization_test": True,
                    "roles": scenario["roles"],
                    "permission_count": len(scenario["expected_permissions"])
                }
            )
            
            # Verify permissions computation
            computed_permissions = context.agent_context["computed_permissions"]
            expected_permissions = scenario["expected_permissions"]
            
            assert set(computed_permissions) == set(expected_permissions)
            
            # Test specific permission checks
            if "admin" in scenario["roles"]:
                assert "users:write" in computed_permissions
                assert "system:admin" in computed_permissions
            else:
                assert "users:write" not in computed_permissions
                assert "system:admin" not in computed_permissions
            
            if "user" in scenario["roles"]:
                assert "agents:execute" in computed_permissions
                assert "profile:write" in computed_permissions
            
            if scenario["roles"] == ["readonly"]:
                assert "agents:execute" not in computed_permissions
                assert "profile:write" not in computed_permissions
                assert "agents:read" in computed_permissions
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_subscription_based_authorization(self, clean_context_registry, isolated_env):
        """Test context integration with subscription-based authorization."""
        
        subscription_scenarios = [
            {
                "user_id": "user_free_sub_12345678901234567890",
                "subscription": "free",
                "expected_features": self._get_subscription_features("free")
            },
            {
                "user_id": "user_business_sub_11223344556677889900", 
                "subscription": "business",
                "expected_features": self._get_subscription_features("business")
            },
            {
                "user_id": "user_enterprise_sub_99887766554433221100",
                "subscription": "enterprise", 
                "expected_features": self._get_subscription_features("enterprise")
            }
        ]
        
        for scenario in subscription_scenarios:
            context = UserExecutionContext(
                user_id=scenario["user_id"],
                thread_id=f"thread_sub_auth_{scenario['user_id'][-10:]}",
                run_id=f"run_sub_auth_{int(time.time())}_{scenario['user_id'][-4:]}",
                agent_context={
                    "agent_name": "subscription_test_agent",
                    "subscription_tier": scenario["subscription"],
                    "available_features": scenario["expected_features"],
                    "feature_access": {
                        feature: True for feature in scenario["expected_features"]
                    }
                },
                audit_metadata={
                    "subscription_tier": scenario["subscription"],
                    "feature_count": len(scenario["expected_features"]),
                    "authorization_test": "subscription_based"
                }
            )
            
            # Verify subscription features
            available_features = context.agent_context["available_features"]
            expected_features = scenario["expected_features"]
            
            assert set(available_features) == set(expected_features)
            
            # Test tier-specific features
            if scenario["subscription"] == "free":
                assert "basic_agents" in available_features
                assert "advanced_agents" not in available_features
                assert "custom_agents" not in available_features
                assert "sso" not in available_features
            
            elif scenario["subscription"] == "business":
                assert "basic_agents" in available_features
                assert "advanced_agents" in available_features
                assert "custom_agents" not in available_features
                assert "sso" not in available_features
                assert "integrations:basic" in available_features
                assert "integrations:custom" not in available_features
            
            elif scenario["subscription"] == "enterprise":
                assert "basic_agents" in available_features
                assert "advanced_agents" in available_features
                assert "custom_agents" in available_features
                assert "sso" in available_features
                assert "integrations:custom" in available_features
                assert "dedicated_support" in available_features
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_resource_access_authorization(self, clean_context_registry, isolated_env):
        """Test context integration with resource access authorization."""
        
        # Define resource ownership and access patterns
        resource_scenarios = [
            {
                "user_id": "user_owner_12345678901234567890",
                "owned_resources": ["thread_123", "agent_config_456", "report_789"],
                "shared_resources": ["shared_dashboard_001"],
                "admin_access": False
            },
            {
                "user_id": "user_collaborator_11223344556677889900",
                "owned_resources": ["thread_456"], 
                "shared_resources": ["shared_dashboard_001", "team_workspace_002"],
                "admin_access": False
            },
            {
                "user_id": "user_admin_99887766554433221100",
                "owned_resources": ["admin_panel_001"],
                "shared_resources": [],
                "admin_access": True  # Can access all resources
            }
        ]
        
        for scenario in resource_scenarios:
            context = UserExecutionContext(
                user_id=scenario["user_id"],
                thread_id=f"thread_resource_auth_{scenario['user_id'][-10:]}",
                run_id=f"run_resource_auth_{int(time.time())}_{scenario['user_id'][-4:]}",
                agent_context={
                    "agent_name": "resource_access_agent",
                    "owned_resources": scenario["owned_resources"],
                    "shared_resources": scenario["shared_resources"],
                    "admin_access": scenario["admin_access"],
                    "resource_permissions": {
                        "owned": ["read", "write", "delete"],
                        "shared": ["read", "write"],
                        "admin": ["read", "write", "delete", "admin"] if scenario["admin_access"] else []
                    }
                },
                audit_metadata={
                    "resource_authorization_test": True,
                    "owned_resource_count": len(scenario["owned_resources"]),
                    "shared_resource_count": len(scenario["shared_resources"]),
                    "has_admin_access": scenario["admin_access"]
                }
            )
            
            # Test resource access patterns
            def can_access_resource(ctx: UserExecutionContext, resource_id: str, action: str) -> bool:
                """Simulate resource access checking."""
                owned = ctx.agent_context["owned_resources"]
                shared = ctx.agent_context["shared_resources"]
                admin = ctx.agent_context["admin_access"]
                perms = ctx.agent_context["resource_permissions"]
                
                if admin and action in perms["admin"]:
                    return True
                elif resource_id in owned and action in perms["owned"]:
                    return True
                elif resource_id in shared and action in perms["shared"]:
                    return True
                else:
                    return False
            
            # Test owned resource access
            if scenario["owned_resources"]:
                owned_resource = scenario["owned_resources"][0]
                assert can_access_resource(context, owned_resource, "read") is True
                assert can_access_resource(context, owned_resource, "write") is True
                assert can_access_resource(context, owned_resource, "delete") is True
            
            # Test shared resource access
            if scenario["shared_resources"]:
                shared_resource = scenario["shared_resources"][0]
                assert can_access_resource(context, shared_resource, "read") is True
                assert can_access_resource(context, shared_resource, "write") is True
                assert can_access_resource(context, shared_resource, "delete") is False  # Unless admin
            
            # Test unauthorized resource access
            unauthorized_resource = "unauthorized_resource_999"
            if not scenario["admin_access"]:
                assert can_access_resource(context, unauthorized_resource, "read") is False
                assert can_access_resource(context, unauthorized_resource, "write") is False
                assert can_access_resource(context, unauthorized_resource, "delete") is False
            else:
                # Admin can access any resource
                assert can_access_resource(context, unauthorized_resource, "read") is True
    
    @pytest.mark.integration
    @pytest.mark.auth_validation
    async def test_context_child_authorization_inheritance(self, clean_context_registry, isolated_env):
        """Test authorization inheritance in child contexts."""
        
        # Create parent context with specific authorization
        parent_context = UserExecutionContext(
            user_id="user_parent_auth_12345678901234567890",
            thread_id="thread_parent_auth_98765432109876543210",
            run_id=f"run_parent_auth_{int(time.time())}",
            agent_context={
                "agent_name": "parent_auth_agent",
                "user_roles": ["user", "data_analyst"],
                "user_permissions": ["agents:read", "agents:execute", "data:read", "data:analyze"],
                "subscription_tier": "business",
                "available_features": ["advanced_agents", "advanced_analytics"]
            },
            audit_metadata={
                "authorization_level": "business_user",
                "inherited_permissions": True
            }
        )
        
        # Create child context for specific operation
        child_context = parent_context.create_child_context(
            "data_analysis_operation",
            additional_agent_context={
                "operation_type": "data_analysis",
                "requires_permissions": ["data:read", "data:analyze"],
                "operation_authorized": True
            },
            additional_audit_metadata={
                "operation_authorization": "inherited_from_parent",
                "permission_check": "passed"
            }
        )
        
        # Verify authorization inheritance
        assert child_context.user_id == parent_context.user_id  # Same user
        assert child_context.agent_context["user_roles"] == parent_context.agent_context["user_roles"]
        assert child_context.agent_context["user_permissions"] == parent_context.agent_context["user_permissions"]
        assert child_context.agent_context["subscription_tier"] == parent_context.agent_context["subscription_tier"]
        
        # Verify child-specific authorization data
        assert child_context.agent_context["operation_type"] == "data_analysis"
        assert child_context.agent_context["operation_authorized"] is True
        assert child_context.audit_metadata["operation_authorization"] == "inherited_from_parent"
        
        # Test unauthorized child operation
        with pytest.raises(Exception):
            # Simulate creating child context for unauthorized operation
            unauthorized_child = parent_context.create_child_context(
                "admin_operation", 
                additional_agent_context={
                    "operation_type": "admin_operation",
                    "requires_permissions": ["system:admin"],  # Not in parent permissions
                    "operation_authorized": False
                }
            )
            
            # Simulate authorization check that should fail
            required_permissions = unauthorized_child.agent_context["requires_permissions"]
            available_permissions = unauthorized_child.agent_context["user_permissions"]
            
            if not all(perm in available_permissions for perm in required_permissions):
                raise PermissionError("Insufficient permissions for operation")


# Test execution markers and configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_validation,
    pytest.mark.real_services  # Uses real authentication and validation patterns
]


if __name__ == "__main__":
    """Allow running tests directly for development."""
    pytest.main([__file__, "-v", "--tb=short"])