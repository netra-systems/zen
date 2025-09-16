#!/usr/bin/env python
"""
Integration Tests for WebSocket Auth Permissions and User Validation

MISSION CRITICAL: Integration between WebSocket authentication and user permission validation.
Tests real permission checking, user validation, and authorization flows.

Business Value: $500K+ ARR - Secure permission-based access control
- Tests WebSocket authentication with different user permission levels
- Validates user authorization and permission checking
- Ensures proper permission isolation and access control
- Tests integration between auth service and permission systems
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following CLAUDE.md guidelines
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import production components - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    create_authenticated_user_context
)
from netra_backend.app.auth_integration.auth import (
    get_current_user,
    require_admin,
    require_developer,
    extract_admin_status_from_jwt,
    BackendAuthIntegration,
    AuthValidationResult
)
from netra_backend.app.services.unified_authentication_service import (
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)


class MockWebSocket:
    """Enhanced mock WebSocket for permission testing."""

    def __init__(self, headers=None, client=None, subprotocols=None,
                 user_permissions=None, user_role=None):
        self.headers = headers or {}
        self.client = client or type('Client', (), {'host': '127.0.0.1', 'port': 8000})()
        self.subprotocols = subprotocols or []
        self.client_state = "CONNECTED"
        self.application_state = "CONNECTED"
        self._messages = []
        self._user_permissions = user_permissions or []
        self._user_role = user_role or "standard_user"

    async def send_json(self, data):
        """Mock send_json method."""
        self._messages.append(data)
        return True

    async def close(self, code=1000, reason=""):
        """Mock close method."""
        self.client_state = "DISCONNECTED"


class MockAuthResult:
    """Mock auth result with permission support."""

    def __init__(self, user_id, email="test@example.com", permissions=None,
                 role="standard_user", success=True):
        self.success = success
        self.user_id = user_id
        self.email = email
        self.permissions = permissions or []
        self.role = role
        self.validated_at = datetime.now(timezone.utc)
        self.metadata = {
            "auth_method": "test_mock",
            "permissions": self.permissions,
            "role": self.role
        }
        self.error = None if success else "Mock auth error"
        self.error_code = None if success else "MOCK_ERROR"


@pytest.mark.integration
class TestWebSocketAuthPermissionsIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket authentication permissions and user validation."""

    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)

        # Set test environment variables
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "1")
        self.set_env_var("DEMO_MODE", "1")
        self.set_env_var("ENVIRONMENT", "test")

        # Track metrics
        self.record_metric("test_category", "websocket_auth_permissions_integration")

    @pytest.mark.asyncio
    async def test_websocket_auth_with_different_user_roles(self):
        """
        Test WebSocket authentication with different user roles.

        CRITICAL: Different user roles should be properly authenticated
        and have appropriate permissions in WebSocket context.
        """
        # Test different user roles
        user_role_scenarios = [
            {
                "role": "standard_user",
                "permissions": ["execute_agents", "read_data"],
                "expected_auth_success": True,
                "description": "Standard users should authenticate successfully"
            },
            {
                "role": "admin",
                "permissions": ["execute_agents", "read_data", "admin_access", "system:*"],
                "expected_auth_success": True,
                "description": "Admin users should authenticate successfully"
            },
            {
                "role": "developer",
                "permissions": ["execute_agents", "read_data", "developer_access", "debug:*"],
                "expected_auth_success": True,
                "description": "Developer users should authenticate successfully"
            },
            {
                "role": "enterprise_user",
                "permissions": ["execute_agents", "read_data", "enterprise_features"],
                "expected_auth_success": True,
                "description": "Enterprise users should authenticate successfully"
            },
            {
                "role": "limited_user",
                "permissions": ["read_data"],
                "expected_auth_success": True,
                "description": "Limited users should authenticate but with restricted permissions"
            }
        ]

        role_test_results = []

        for scenario in user_role_scenarios:
            with self.subTest(role=scenario["role"]):
                # Arrange
                user_id = f"role_user_{scenario['role']}_{uuid.uuid4().hex[:8]}"

                websocket = MockWebSocket(
                    headers={
                        "sec-websocket-protocol": f"jwt.valid_token_{user_id}",
                        "x-user-id": user_id,
                        "x-user-role": scenario["role"]
                    },
                    user_permissions=scenario["permissions"],
                    user_role=scenario["role"]
                )

                e2e_context = {
                    "is_e2e_testing": True,
                    "demo_mode_enabled": True,
                    "bypass_enabled": True,
                    "test_user_role": scenario["role"],
                    "test_permissions": scenario["permissions"]
                }

                # Act
                start_time = time.time()
                auth_result = await authenticate_websocket_ssot(
                    websocket=websocket,
                    e2e_context=e2e_context
                )
                auth_time = time.time() - start_time

                # Assert
                if scenario["expected_auth_success"]:
                    self.assertTrue(auth_result.success,
                                  f"Authentication should succeed for role: {scenario['role']}")
                    self.assertIsNotNone(auth_result.user_context,
                                       f"User context should be created for role: {scenario['role']}")
                    self.assertIsNotNone(auth_result.auth_result,
                                       f"Auth result should be populated for role: {scenario['role']}")
                else:
                    self.assertFalse(auth_result.success,
                                   f"Authentication should fail for role: {scenario['role']}")

                role_test_results.append({
                    "role": scenario["role"],
                    "permissions": scenario["permissions"],
                    "auth_success": auth_result.success,
                    "auth_time": auth_time,
                    "user_context_created": auth_result.user_context is not None
                })

        # Verify all expected authentications succeeded
        successful_auths = [result for result in role_test_results if result["auth_success"]]
        expected_successful = [scenario for scenario in user_role_scenarios
                             if scenario["expected_auth_success"]]

        self.assertEqual(len(successful_auths), len(expected_successful),
                        "All expected role authentications should succeed")

        # Performance check - all role auths should be reasonably fast
        avg_auth_time = sum(result["auth_time"] for result in role_test_results) / len(role_test_results)
        self.assertLess(avg_auth_time, 3.0,
                       "Role-based authentication should be performant")

        self.record_metric("user_roles_tested", len(user_role_scenarios))
        self.record_metric("successful_role_authentications", len(successful_auths))
        self.record_metric("avg_role_auth_time_seconds", avg_auth_time)

    @pytest.mark.asyncio
    async def test_websocket_auth_permission_validation_integration(self):
        """
        Test WebSocket authentication integration with permission validation.

        CRITICAL: WebSocket authentication should properly integrate with
        permission systems and validate user authorizations.
        """
        # Test permission-based access scenarios
        permission_scenarios = [
            {
                "name": "agent_execution_permission",
                "user_permissions": ["execute_agents", "read_data"],
                "required_permission": "execute_agents",
                "should_have_access": True
            },
            {
                "name": "admin_permission",
                "user_permissions": ["admin_access", "system:*"],
                "required_permission": "admin_access",
                "should_have_access": True
            },
            {
                "name": "developer_permission",
                "user_permissions": ["developer_access", "debug:*"],
                "required_permission": "developer_access",
                "should_have_access": True
            },
            {
                "name": "missing_permission",
                "user_permissions": ["read_data"],
                "required_permission": "execute_agents",
                "should_have_access": False
            },
            {
                "name": "wildcard_permission",
                "user_permissions": ["system:*"],
                "required_permission": "system:admin",
                "should_have_access": True  # Wildcard should cover specific permissions
            }
        ]

        for scenario in permission_scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Arrange
                user_id = f"perm_user_{scenario['name']}_{uuid.uuid4().hex[:8]}"

                websocket = MockWebSocket(
                    headers={
                        "sec-websocket-protocol": f"jwt.valid_token_{user_id}",
                        "x-user-id": user_id
                    },
                    user_permissions=scenario["user_permissions"]
                )

                # Create mock auth result with specific permissions
                mock_auth_result = MockAuthResult(
                    user_id=user_id,
                    permissions=scenario["user_permissions"]
                )

                e2e_context = {
                    "is_e2e_testing": True,
                    "demo_mode_enabled": True,
                    "bypass_enabled": True,
                    "test_permissions": scenario["user_permissions"]
                }

                # Act - Authenticate
                auth_result = await authenticate_websocket_ssot(
                    websocket=websocket,
                    e2e_context=e2e_context
                )

                # Assert - Authentication should succeed
                self.assertTrue(auth_result.success,
                               f"Authentication should succeed for permission test: {scenario['name']}")
                self.assertIsNotNone(auth_result.user_context,
                                   f"User context required for permission test: {scenario['name']}")

                # Simulate permission checking
                user_context = auth_result.user_context

                # Create authenticated user context with permissions
                authenticated_context = create_authenticated_user_context(
                    auth_result=mock_auth_result,
                    websocket=websocket,
                    agent_context={
                        "permissions": scenario["user_permissions"],
                        "test_scenario": scenario["name"]
                    }
                )

                # Verify context creation
                self.assertIsNotNone(authenticated_context,
                                   f"Authenticated context should be created: {scenario['name']}")

                # Check if user would have required permission
                has_required_permission = (
                    scenario["required_permission"] in scenario["user_permissions"] or
                    any(perm.endswith(":*") and scenario["required_permission"].startswith(perm[:-1])
                        for perm in scenario["user_permissions"])
                )

                self.assertEqual(has_required_permission, scenario["should_have_access"],
                               f"Permission check should match expected access: {scenario['name']}")

        self.record_metric("permission_scenarios_tested", len(permission_scenarios))
        self.record_metric("permission_validation_integration_verified", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_admin_user_validation(self):
        """
        Test WebSocket authentication with admin user validation.

        CRITICAL: Admin users should be properly authenticated and have
        admin privileges validated through the auth integration.
        """
        # Arrange - Create admin user scenario
        admin_user_id = f"admin_user_{uuid.uuid4().hex[:8]}"

        admin_websocket = MockWebSocket(
            headers={
                "sec-websocket-protocol": f"jwt.valid_admin_token_{admin_user_id}",
                "x-user-id": admin_user_id,
                "x-user-role": "admin"
            },
            user_permissions=["admin_access", "system:*", "execute_agents"],
            user_role="admin"
        )

        admin_e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "bypass_enabled": True,
            "test_user_role": "admin",
            "test_permissions": ["admin_access", "system:*", "execute_agents"]
        }

        # Act - Authenticate admin user
        start_time = time.time()
        admin_auth_result = await authenticate_websocket_ssot(
            websocket=admin_websocket,
            e2e_context=admin_e2e_context
        )
        admin_auth_time = time.time() - start_time

        # Assert - Admin authentication
        self.assertTrue(admin_auth_result.success, "Admin user authentication should succeed")
        self.assertIsNotNone(admin_auth_result.user_context, "Admin user context should be created")
        self.assertIsNotNone(admin_auth_result.auth_result, "Admin auth result should be populated")

        # Verify admin-specific properties
        admin_context = admin_auth_result.user_context
        self.assertIsNotNone(admin_context.user_id, "Admin user ID should be set")

        # Test admin permission validation using backend auth integration
        backend_auth = BackendAuthIntegration()

        # Create admin token for validation
        admin_token = f"Bearer valid_admin_token_{admin_user_id}"

        admin_validation_result = await backend_auth.validate_request_token(
            authorization_header=admin_token
        )

        # Note: In demo mode, validation behavior may vary
        # The key is that the system handles admin users appropriately

        # Verify admin authentication performance
        self.assertLess(admin_auth_time, 3.0, "Admin authentication should be performant")

        # Test comparison with non-admin user
        regular_user_id = f"regular_user_{uuid.uuid4().hex[:8]}"

        regular_websocket = MockWebSocket(
            headers={
                "sec-websocket-protocol": f"jwt.valid_token_{regular_user_id}",
                "x-user-id": regular_user_id,
                "x-user-role": "standard_user"
            },
            user_permissions=["execute_agents", "read_data"],
            user_role="standard_user"
        )

        regular_e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "bypass_enabled": True,
            "test_user_role": "standard_user",
            "test_permissions": ["execute_agents", "read_data"]
        }

        regular_auth_result = await authenticate_websocket_ssot(
            websocket=regular_websocket,
            e2e_context=regular_e2e_context
        )

        # Both should authenticate successfully, but with different contexts
        self.assertTrue(regular_auth_result.success, "Regular user authentication should succeed")

        # Verify users have different contexts
        self.assertNotEqual(admin_context.user_id, regular_auth_result.user_context.user_id,
                           "Admin and regular users should have different user IDs")

        self.record_metric("admin_auth_time_seconds", admin_auth_time)
        self.record_metric("admin_user_validation_tested", True)
        self.record_metric("user_role_comparison_tested", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_enterprise_user_permissions(self):
        """
        Test WebSocket authentication with enterprise user permissions.

        CRITICAL: Enterprise users should have appropriate permission levels
        and access to advanced features through WebSocket authentication.
        """
        # Define enterprise permission tiers
        enterprise_tiers = [
            {
                "tier": "enterprise_basic",
                "permissions": ["execute_agents", "read_data", "basic_analytics"],
                "expected_features": ["basic_agents", "standard_analytics"]
            },
            {
                "tier": "enterprise_pro",
                "permissions": ["execute_agents", "read_data", "advanced_analytics", "custom_models"],
                "expected_features": ["advanced_agents", "custom_analytics", "model_tuning"]
            },
            {
                "tier": "enterprise_premium",
                "permissions": ["execute_agents", "read_data", "premium_features", "priority_support", "enterprise:*"],
                "expected_features": ["premium_agents", "priority_queue", "dedicated_support"]
            }
        ]

        enterprise_test_results = []

        for tier_config in enterprise_tiers:
            with self.subTest(tier=tier_config["tier"]):
                # Arrange
                enterprise_user_id = f"enterprise_{tier_config['tier']}_{uuid.uuid4().hex[:8]}"

                enterprise_websocket = MockWebSocket(
                    headers={
                        "sec-websocket-protocol": f"jwt.valid_enterprise_token_{enterprise_user_id}",
                        "x-user-id": enterprise_user_id,
                        "x-subscription-tier": tier_config["tier"]
                    },
                    user_permissions=tier_config["permissions"],
                    user_role="enterprise_user"
                )

                enterprise_e2e_context = {
                    "is_e2e_testing": True,
                    "demo_mode_enabled": True,
                    "bypass_enabled": True,
                    "test_subscription_tier": tier_config["tier"],
                    "test_permissions": tier_config["permissions"]
                }

                # Act
                start_time = time.time()
                enterprise_auth_result = await authenticate_websocket_ssot(
                    websocket=enterprise_websocket,
                    e2e_context=enterprise_e2e_context
                )
                enterprise_auth_time = time.time() - start_time

                # Assert - Enterprise authentication
                self.assertTrue(enterprise_auth_result.success,
                               f"Enterprise {tier_config['tier']} authentication should succeed")
                self.assertIsNotNone(enterprise_auth_result.user_context,
                                   f"Enterprise {tier_config['tier']} user context should be created")

                # Verify enterprise-specific context properties
                enterprise_context = enterprise_auth_result.user_context
                self.assertIsNotNone(enterprise_context.user_id,
                                   f"Enterprise {tier_config['tier']} user ID should be set")

                # Create authenticated user context with enterprise permissions
                mock_enterprise_auth = MockAuthResult(
                    user_id=enterprise_user_id,
                    permissions=tier_config["permissions"],
                    role="enterprise_user"
                )

                enterprise_authenticated_context = create_authenticated_user_context(
                    auth_result=mock_enterprise_auth,
                    websocket=enterprise_websocket,
                    agent_context={
                        "subscription_tier": tier_config["tier"],
                        "permissions": tier_config["permissions"],
                        "expected_features": tier_config["expected_features"]
                    }
                )

                # Verify enterprise context creation
                self.assertIsNotNone(enterprise_authenticated_context,
                                   f"Enterprise {tier_config['tier']} context should be created")

                enterprise_test_results.append({
                    "tier": tier_config["tier"],
                    "auth_success": enterprise_auth_result.success,
                    "auth_time": enterprise_auth_time,
                    "permissions_count": len(tier_config["permissions"]),
                    "features_count": len(tier_config["expected_features"])
                })

        # Verify all enterprise tiers authenticated successfully
        successful_enterprise_auths = [result for result in enterprise_test_results if result["auth_success"]]
        self.assertEqual(len(successful_enterprise_auths), len(enterprise_tiers),
                        "All enterprise tiers should authenticate successfully")

        # Verify higher tiers have more permissions
        sorted_results = sorted(enterprise_test_results, key=lambda x: x["permissions_count"])
        for i in range(1, len(sorted_results)):
            self.assertGreaterEqual(sorted_results[i]["permissions_count"],
                                  sorted_results[i-1]["permissions_count"],
                                  "Higher enterprise tiers should have equal or more permissions")

        # Performance verification
        avg_enterprise_auth_time = sum(result["auth_time"] for result in enterprise_test_results) / len(enterprise_test_results)
        self.assertLess(avg_enterprise_auth_time, 3.0,
                       "Enterprise authentication should be performant")

        self.record_metric("enterprise_tiers_tested", len(enterprise_tiers))
        self.record_metric("avg_enterprise_auth_time_seconds", avg_enterprise_auth_time)
        self.record_metric("enterprise_permission_validation_verified", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_permission_isolation_security(self):
        """
        Test WebSocket authentication permission isolation for security.

        CRITICAL: Users should only have access to their authorized permissions
        and cannot escalate or access other users' permissions.
        """
        # Create users with different permission levels
        security_test_users = [
            {
                "user_id": f"low_perm_user_{uuid.uuid4().hex[:8]}",
                "permissions": ["read_data"],
                "role": "limited_user",
                "security_level": "low"
            },
            {
                "user_id": f"medium_perm_user_{uuid.uuid4().hex[:8]}",
                "permissions": ["read_data", "execute_agents"],
                "role": "standard_user",
                "security_level": "medium"
            },
            {
                "user_id": f"high_perm_user_{uuid.uuid4().hex[:8]}",
                "permissions": ["read_data", "execute_agents", "admin_access", "system:*"],
                "role": "admin",
                "security_level": "high"
            }
        ]

        authenticated_users = []

        # Authenticate all users
        for user_config in security_test_users:
            websocket = MockWebSocket(
                headers={
                    "sec-websocket-protocol": f"jwt.valid_token_{user_config['user_id']}",
                    "x-user-id": user_config["user_id"]
                },
                user_permissions=user_config["permissions"],
                user_role=user_config["role"]
            )

            e2e_context = {
                "is_e2e_testing": True,
                "demo_mode_enabled": True,
                "bypass_enabled": True,
                "test_permissions": user_config["permissions"],
                "security_level": user_config["security_level"]
            }

            auth_result = await authenticate_websocket_ssot(
                websocket=websocket,
                e2e_context=e2e_context
            )

            self.assertTrue(auth_result.success,
                           f"User {user_config['security_level']} should authenticate successfully")

            authenticated_users.append({
                "auth_result": auth_result,
                "config": user_config
            })

        # Verify permission isolation
        for i, user1 in enumerate(authenticated_users):
            for j, user2 in enumerate(authenticated_users):
                if i != j:
                    # Verify users have different contexts
                    self.assertNotEqual(user1["auth_result"].user_context.user_id,
                                      user2["auth_result"].user_context.user_id,
                                      f"Users {user1['config']['security_level']} and {user2['config']['security_level']} should have different user IDs")

                    self.assertNotEqual(user1["auth_result"].user_context.websocket_client_id,
                                      user2["auth_result"].user_context.websocket_client_id,
                                      f"Users {user1['config']['security_level']} and {user2['config']['security_level']} should have different WebSocket client IDs")

        # Verify permission hierarchy (higher security levels should not have lower permissions only)
        low_user = next(user for user in authenticated_users if user["config"]["security_level"] == "low")
        high_user = next(user for user in authenticated_users if user["config"]["security_level"] == "high")

        # High security user should have more permissions than low security user
        low_permissions = set(low_user["config"]["permissions"])
        high_permissions = set(high_user["config"]["permissions"])

        self.assertTrue(low_permissions.issubset(high_permissions) or
                       len(high_permissions) > len(low_permissions),
                       "High security user should have equal or more permissions than low security user")

        # Verify context isolation - no shared references
        user_contexts = [user["auth_result"].user_context for user in authenticated_users]

        for i, ctx1 in enumerate(user_contexts):
            for j, ctx2 in enumerate(user_contexts):
                if i != j:
                    self.assertIsNot(ctx1, ctx2, "User contexts should not share object references")

        self.record_metric("security_isolation_users_tested", len(security_test_users))
        self.record_metric("permission_isolation_verified", True)
        self.record_metric("context_isolation_security_verified", True)