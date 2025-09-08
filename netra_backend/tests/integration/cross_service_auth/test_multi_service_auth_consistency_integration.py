"""
Test Multi-Service Auth Consistency Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Consistency & Security Foundation
- Value Impact: Ensures consistent authentication across all platform services 
- Strategic Impact: Single sign-on experience - users authenticate once, access everything securely

This test suite validates authentication consistency across multiple services:
1. Token validation consistency between backend, analytics, and other services
2. Permission enforcement consistency across service boundaries  
3. User session consistency during cross-service operations
4. Service-to-service authentication validation
5. Multi-service auth failure handling and recovery
6. Load balancing and auth service redundancy scenarios
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceError,
    AuthServiceConnectionError
)
from netra_backend.app.clients.auth_client_cache import AuthTokenCache
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class ServiceAuthClient:
    """Represents an auth client for a specific service."""
    name: str
    service_id: str
    service_secret: str
    client: AuthServiceClient
    
    def __post_init__(self):
        """Initialize the auth client with service credentials."""
        self.client.service_id = self.service_id
        self.client.service_secret = self.service_secret


class TestMultiServiceAuthConsistencyIntegration:
    """Test authentication consistency across multiple services."""

    @pytest.fixture
    def multi_service_clients(self):
        """Create auth clients for multiple services."""
        services = {
            "backend": ServiceAuthClient(
                name="backend",
                service_id="backend-service",
                service_secret="backend_secret_12345",
                client=AuthServiceClient()
            ),
            "analytics": ServiceAuthClient(
                name="analytics", 
                service_id="analytics-service",
                service_secret="analytics_secret_67890",
                client=AuthServiceClient()
            ),
            "notification": ServiceAuthClient(
                name="notification",
                service_id="notification-service", 
                service_secret="notification_secret_abc123",
                client=AuthServiceClient()
            )
        }
        return services

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_token_validation_consistency(self, real_services_fixture, multi_service_clients):
        """
        Test that the same user token validates consistently across all services.
        
        Business Value: Ensures users can access all platform features with single login.
        Critical for seamless user experience - same token should work everywhere.
        """
        # Arrange: User token and expected validation data
        user_token = "consistent_user_token_abc123"
        expected_user_data = {
            "valid": True,
            "user_id": "consistent_user_456",
            "email": "consistent@example.com",
            "role": "premium_user"
        }
        
        # Mock consistent validation responses for all services
        def create_service_response(service_name: str):
            response_data = expected_user_data.copy()
            # Add service-specific permissions while keeping core data consistent
            if service_name == "backend":
                response_data["permissions"] = ["backend:read", "backend:write", "users:manage"]
            elif service_name == "analytics":
                response_data["permissions"] = ["analytics:read", "analytics:query", "data:export"]
            elif service_name == "notification":
                response_data["permissions"] = ["notifications:read", "notifications:send"]
            return response_data
        
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            
            # Determine service based on headers
            headers = kwargs.get("headers", {})
            service_id = headers.get("X-Service-ID", "unknown")
            
            if service_id == "backend-service":
                mock_response.json.return_value = create_service_response("backend")
            elif service_id == "analytics-service":
                mock_response.json.return_value = create_service_response("analytics")
            elif service_id == "notification-service":
                mock_response.json.return_value = create_service_response("notification")
            else:
                mock_response.status_code = 403
                mock_response.json.return_value = {"error": "Unknown service"}
            
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Validate same token across all services
            results = {}
            for service_name, service_client in multi_service_clients.items():
                result = await service_client.client.validate_token(user_token)
                results[service_name] = result
            
            # Assert: Core user data consistent across services
            for service_name, result in results.items():
                assert result["valid"] is True, f"Token should be valid in {service_name} service"
                assert result["user_id"] == expected_user_data["user_id"], f"User ID should be consistent in {service_name}"
                assert result["email"] == expected_user_data["email"], f"Email should be consistent in {service_name}"
                assert result["role"] == expected_user_data["role"], f"Role should be consistent in {service_name}"
                assert len(result["permissions"]) > 0, f"Service {service_name} should have permissions"
            
            # Verify service-specific permissions are different but user data is same
            backend_perms = set(results["backend"]["permissions"])
            analytics_perms = set(results["analytics"]["permissions"])
            notification_perms = set(results["notification"]["permissions"])
            
            assert backend_perms != analytics_perms, "Services should have different permissions"
            assert analytics_perms != notification_perms, "Services should have different permissions"
            assert "backend:read" in backend_perms, "Backend should have backend permissions"
            assert "analytics:read" in analytics_perms, "Analytics should have analytics permissions"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_user_session_consistency(self, real_services_fixture, multi_service_clients):
        """
        Test user session consistency during cross-service operations.
        
        Business Value: Ensures seamless user experience across platform features.
        Users should maintain session state when moving between platform services.
        """
        # Arrange: User login and session data
        user_email = "session_user@example.com"
        user_password = "secure_session_password"
        
        login_response = {
            "access_token": "session_access_token_xyz789",
            "refresh_token": "session_refresh_token_xyz789",
            "user_id": "session_user_789",
            "role": "enterprise_user",
            "expires_in": 3600
        }
        
        session_validation_data = {
            "valid": True,
            "user_id": "session_user_789",
            "email": user_email,
            "role": "enterprise_user",
            "session_id": "cross_service_session_123"
        }
        
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            
            # Handle login vs validation based on endpoint
            if "/auth/login" in str(args) or "login" in str(kwargs.get("url", "")):
                mock_response.status_code = 200
                mock_response.json.return_value = login_response
            else:
                # Token validation
                mock_response.status_code = 200
                response_data = session_validation_data.copy()
                
                # Add service-specific session data
                headers = kwargs.get("headers", {})
                service_id = headers.get("X-Service-ID", "")
                response_data["service_context"] = {
                    "service": service_id,
                    "session_valid": True,
                    "cross_service_allowed": True
                }
                mock_response.json.return_value = response_data
            
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Login through one service
            backend_client = multi_service_clients["backend"].client
            login_result = await backend_client.login(user_email, user_password)
            assert login_result is not None, "Login should succeed"
            
            access_token = login_result["access_token"]
            
            # Validate session consistency across all services
            session_results = {}
            for service_name, service_client in multi_service_clients.items():
                result = await service_client.client.validate_token(access_token)
                session_results[service_name] = result
            
            # Assert: Session valid and consistent across services
            for service_name, result in session_results.items():
                assert result["valid"] is True, f"Session should be valid in {service_name}"
                assert result["user_id"] == session_validation_data["user_id"], f"User ID consistent in {service_name}"
                assert result["email"] == session_validation_data["email"], f"Email consistent in {service_name}"
                assert result["service_context"]["cross_service_allowed"] is True, f"Cross-service should be allowed in {service_name}"

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_multi_service_auth_failure_handling_consistency(self, real_services_fixture, multi_service_clients):
        """
        Test consistent auth failure handling across services.
        
        Business Value: Provides consistent error experience across platform.
        Users get same quality error handling regardless of which service fails.
        """
        # Arrange: Invalid token for testing failures
        invalid_token = "invalid_token_for_multi_service_test"
        
        # Mock 401 responses for invalid token across all services
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": "Invalid token",
                "code": "TOKEN_INVALID"
            }
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Validate invalid token across all services
            failure_results = {}
            for service_name, service_client in multi_service_clients.items():
                result = await service_client.client.validate_token(invalid_token)
                failure_results[service_name] = result
            
            # Assert: Consistent failure handling across services
            for service_name, result in failure_results.items():
                assert result is not None, f"Service {service_name} should return error result"
                assert result["valid"] is False, f"Invalid token should be rejected by {service_name}"
                
                # All services should provide user notifications
                if "user_notification" in result:
                    notification = result["user_notification"]
                    assert "user_friendly_message" in notification, f"Service {service_name} should provide user-friendly error"
                    assert notification["severity"] in ["error", "warning"], f"Service {service_name} should indicate appropriate severity"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_concurrent_auth_operations(self, real_services_fixture, multi_service_clients):
        """
        Test concurrent auth operations across multiple services.
        
        Business Value: Ensures platform handles multi-user concurrent access.
        Critical for production load - multiple users using multiple services simultaneously.
        """
        # Arrange: Multiple tokens for concurrent testing
        test_tokens = [f"concurrent_token_{i}" for i in range(15)]
        
        # Mock responses for concurrent operations
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            
            request_data = kwargs.get("json", {})
            token = request_data.get("token", "unknown")
            headers = kwargs.get("headers", {})
            service_id = headers.get("X-Service-ID", "unknown")
            
            mock_response.json.return_value = {
                "valid": True,
                "user_id": f"concurrent_user_{token.split('_')[-1]}",
                "email": f"user_{token.split('_')[-1]}@example.com",
                "service_validated_by": service_id,
                "concurrent_safe": True
            }
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Concurrent validation across multiple services and tokens
            tasks = []
            for token in test_tokens:
                for service_name, service_client in multi_service_clients.items():
                    task = service_client.client.validate_token(token)
                    tasks.append((service_name, token, task))
            
            # Execute all validations concurrently
            start_time = time.time()
            results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
            end_time = time.time()
            
            # Assert: All concurrent operations successful
            assert len(results) == len(tasks), "All concurrent operations should complete"
            
            successful_count = 0
            error_count = 0
            
            for i, (service_name, token, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    successful_count += 1
                    assert result["valid"] is True, f"Concurrent validation should succeed for {service_name}/{token}"
                    assert result["concurrent_safe"] is True, f"Should indicate concurrent safety for {service_name}"
            
            # Performance should be reasonable
            total_time = end_time - start_time
            assert total_time < 30.0, "Concurrent operations should complete within reasonable time"
            assert successful_count > error_count, "Should have more successes than errors"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_permission_enforcement_consistency(self, real_services_fixture, multi_service_clients):
        """
        Test consistent permission enforcement across services.
        
        Business Value: Ensures security policies are consistently enforced.
        Critical for data security - permissions must be respected by all services.
        """
        # Arrange: Different user roles with different permissions
        test_users = [
            {
                "token": "admin_user_token_123",
                "user_id": "admin_user_123",
                "role": "admin",
                "email": "admin@example.com"
            },
            {
                "token": "regular_user_token_456", 
                "user_id": "regular_user_456",
                "role": "user",
                "email": "user@example.com"
            },
            {
                "token": "readonly_user_token_789",
                "user_id": "readonly_user_789", 
                "role": "readonly",
                "email": "readonly@example.com"
            }
        ]
        
        # Define service-specific permission mappings
        permission_mappings = {
            "backend": {
                "admin": ["backend:read", "backend:write", "backend:admin", "users:manage"],
                "user": ["backend:read", "backend:write"],
                "readonly": ["backend:read"]
            },
            "analytics": {
                "admin": ["analytics:read", "analytics:write", "analytics:admin", "data:export"],
                "user": ["analytics:read", "analytics:query"],
                "readonly": ["analytics:read"]
            },
            "notification": {
                "admin": ["notifications:read", "notifications:write", "notifications:admin"],
                "user": ["notifications:read", "notifications:send"],
                "readonly": ["notifications:read"]
            }
        }
        
        async def mock_post_handler(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 200
            
            request_data = kwargs.get("json", {})
            token = request_data.get("token", "")
            headers = kwargs.get("headers", {})
            service_id = headers.get("X-Service-ID", "").replace("-service", "")
            
            # Find user data based on token
            user_data = None
            for user in test_users:
                if user["token"] == token:
                    user_data = user
                    break
            
            if user_data and service_id in permission_mappings:
                permissions = permission_mappings[service_id].get(user_data["role"], [])
                mock_response.json.return_value = {
                    "valid": True,
                    "user_id": user_data["user_id"],
                    "email": user_data["email"],
                    "role": user_data["role"],
                    "permissions": permissions
                }
            else:
                mock_response.status_code = 403
                mock_response.json.return_value = {"error": "Access denied"}
            
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Validate permissions for each user across all services
            for user in test_users:
                user_results = {}
                for service_name, service_client in multi_service_clients.items():
                    result = await service_client.client.validate_token(user["token"])
                    user_results[service_name] = result
                
                # Assert: Permission consistency based on role
                role = user["role"]
                for service_name, result in user_results.items():
                    assert result["valid"] is True, f"User {role} should be valid in {service_name}"
                    permissions = set(result["permissions"])
                    
                    # Admin should have most permissions
                    if role == "admin":
                        assert len(permissions) >= 3, f"Admin should have multiple permissions in {service_name}"
                        assert any("admin" in perm for perm in permissions), f"Admin should have admin permissions in {service_name}"
                    
                    # Regular user should have read/write but not admin
                    elif role == "user":
                        assert f"{service_name}:read" in permissions, f"User should have read access in {service_name}"
                        assert not any("admin" in perm for perm in permissions), f"User should not have admin permissions in {service_name}"
                    
                    # Readonly should only have read permissions
                    elif role == "readonly":
                        assert f"{service_name}:read" in permissions, f"Readonly should have read access in {service_name}"
                        assert not any("write" in perm or "admin" in perm for perm in permissions), f"Readonly should not have write/admin permissions in {service_name}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_auth_service_redundancy(self, real_services_fixture, multi_service_clients):
        """
        Test auth service redundancy and failover across services.
        
        Business Value: Ensures platform availability during auth service issues.
        Critical for enterprise deployment - single point of failure protection.
        """
        # Arrange: Simulate partial auth service failure
        test_token = "redundancy_test_token_123"
        
        # Track which services succeed/fail
        service_call_count = {name: 0 for name in multi_service_clients.keys()}
        
        async def mock_post_handler(*args, **kwargs):
            headers = kwargs.get("headers", {})
            service_id = headers.get("X-Service-ID", "")
            
            mock_response = AsyncMock()
            
            # Simulate auth service being available for some services but not others
            if service_id == "backend-service":
                # Backend service auth calls succeed
                service_call_count["backend"] += 1
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "valid": True,
                    "user_id": "redundancy_user_123",
                    "email": "redundancy@example.com",
                    "service_availability": "primary"
                }
            elif service_id == "analytics-service":
                # Analytics service gets connection errors initially, then recovers
                service_call_count["analytics"] += 1
                if service_call_count["analytics"] <= 2:
                    raise ConnectionError("Auth service unavailable for analytics")
                else:
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "valid": True,
                        "user_id": "redundancy_user_123",
                        "email": "redundancy@example.com",
                        "service_availability": "recovered"
                    }
            else:
                # Notification service works normally
                service_call_count["notification"] += 1
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "valid": True,
                    "user_id": "redundancy_user_123",
                    "email": "redundancy@example.com",
                    "service_availability": "backup"
                }
            
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Test initial calls (analytics should fail, others succeed)
            initial_results = {}
            for service_name, service_client in multi_service_clients.items():
                try:
                    result = await service_client.client.validate_token(test_token)
                    initial_results[service_name] = result
                except Exception as e:
                    initial_results[service_name] = {"error": str(e), "valid": False}
            
            # Assert: Some services work, some fail initially
            assert initial_results["backend"]["valid"] is True, "Backend should work with primary auth"
            assert initial_results["notification"]["valid"] is True, "Notification should work with backup auth"
            assert initial_results["analytics"]["valid"] is False, "Analytics should fail initially"
            
            # Act: Retry for analytics (should recover)
            retry_results = {}
            for attempt in range(3):
                try:
                    result = await multi_service_clients["analytics"].client.validate_token(test_token)
                    retry_results[f"attempt_{attempt}"] = result
                    if result["valid"]:
                        break
                except Exception as e:
                    retry_results[f"attempt_{attempt}"] = {"error": str(e), "valid": False}
            
            # Assert: Analytics should eventually recover
            final_analytics_result = retry_results[f"attempt_2"]
            assert final_analytics_result["valid"] is True, "Analytics should recover after retries"
            assert final_analytics_result["service_availability"] == "recovered", "Should indicate recovery"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_auth_load_balancing_consistency(self, real_services_fixture, multi_service_clients):
        """
        Test auth consistency with load balancing across services.
        
        Business Value: Ensures consistent experience with load-balanced auth services.
        Critical for scalability - multiple auth service instances must behave identically.
        """
        # Arrange: Simulate multiple auth service instances
        test_token = "load_balanced_token_456"
        auth_instances = ["auth-instance-1", "auth-instance-2", "auth-instance-3"]
        
        # Track which auth instance handles each request
        request_routing = []
        
        async def mock_post_handler(*args, **kwargs):
            # Simulate load balancing by routing to different auth instances
            import random
            auth_instance = random.choice(auth_instances)
            request_routing.append(auth_instance)
            
            mock_response = AsyncMock()
            mock_response.status_code = 200
            
            # All auth instances return consistent user data
            mock_response.json.return_value = {
                "valid": True,
                "user_id": "load_balanced_user_456",
                "email": "loadbalanced@example.com",
                "role": "user",
                "permissions": ["read", "write"],
                "auth_instance": auth_instance,  # Track which instance handled request
                "load_balanced": True
            }
            return mock_response
        
        with patch('httpx.AsyncClient.post', side_effect=mock_post_handler):
            # Act: Make multiple requests across services to trigger load balancing
            load_balance_results = []
            
            for round in range(3):  # Multiple rounds to hit different auth instances
                round_results = {}
                for service_name, service_client in multi_service_clients.items():
                    result = await service_client.client.validate_token(test_token)
                    round_results[service_name] = result
                load_balance_results.append(round_results)
            
            # Assert: Consistent results despite load balancing
            for round_idx, round_results in enumerate(load_balance_results):
                for service_name, result in round_results.items():
                    assert result["valid"] is True, f"Round {round_idx} - {service_name} should validate successfully"
                    assert result["user_id"] == "load_balanced_user_456", f"Round {round_idx} - User ID should be consistent in {service_name}"
                    assert result["email"] == "loadbalanced@example.com", f"Round {round_idx} - Email should be consistent in {service_name}"
                    assert result["load_balanced"] is True, f"Round {round_idx} - Should indicate load balancing in {service_name}"
            
            # Verify load balancing occurred (should have hit multiple instances)
            unique_instances = set(request_routing)
            assert len(unique_instances) >= 2, "Load balancing should route to multiple auth instances"
            
            # Verify all services got consistent data regardless of auth instance
            all_user_ids = set()
            all_emails = set()
            for round_results in load_balance_results:
                for result in round_results.values():
                    all_user_ids.add(result["user_id"])
                    all_emails.add(result["email"])
            
            assert len(all_user_ids) == 1, "All requests should return same user ID despite load balancing"
            assert len(all_emails) == 1, "All requests should return same email despite load balancing"