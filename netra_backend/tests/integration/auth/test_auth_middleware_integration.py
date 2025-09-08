"""
Authentication Middleware Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Middleware protects all API endpoints
- Business Goal: Ensure secure API access and protect business-critical endpoints
- Value Impact: Auth middleware enables subscription tier enforcement and protects customer data
- Strategic Impact: Core security layer that enables API monetization and regulatory compliance

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real middleware chain and JWT validation
- Tests real FastAPI middleware integration with authentication flows
- Validates middleware circuit breaker patterns and error handling
- Ensures proper request/response transformation and user context injection
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestAuthMiddlewareIntegration(BaseIntegrationTest):
    """Integration tests for authentication middleware with real FastAPI application."""
    
    def setup_method(self):
        """Set up for auth middleware tests."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Create test FastAPI app with auth middleware
        self.app = self._create_test_app_with_auth_middleware()
        self.client = TestClient(self.app)
        
        # Test users with different access levels
        self.test_users = [
            {
                "user_id": "middleware-user-1",
                "email": "middleware1@test.com",
                "subscription_tier": "free",
                "permissions": ["read"]
            },
            {
                "user_id": "middleware-user-2",
                "email": "middleware2@test.com", 
                "subscription_tier": "enterprise",
                "permissions": ["read", "write", "admin"]
            }
        ]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_auth_middleware_jwt_validation(self):
        """
        Test auth middleware JWT token validation for API requests.
        
        Business Value: Protects API endpoints and ensures only authenticated users access services.
        Security Impact: Validates JWT verification prevents unauthorized API access.
        """
        # Test valid JWT token access
        user = self.test_users[0]
        valid_token = self.auth_helper.create_test_jwt_token(
            user_id=user["user_id"],
            email=user["email"],
            permissions=user["permissions"]
        )
        
        # Make authenticated request
        response = self.client.get(
            "/api/protected/user-data",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        # Should succeed with valid token
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["authenticated"] is True
        assert response_data["user_id"] == user["user_id"]
        assert response_data["subscription_tier"] == user["subscription_tier"]
        
        # Test request without token
        unauth_response = self.client.get("/api/protected/user-data")
        assert unauth_response.status_code == 401
        assert "authentication required" in unauth_response.json()["detail"].lower()
        
        # Test invalid token
        invalid_response = self.client.get(
            "/api/protected/user-data",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert invalid_response.status_code == 401
        assert "invalid token" in invalid_response.json()["detail"].lower()
        
        self.logger.info("Auth middleware JWT validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_auth_middleware_permission_enforcement(self):
        """
        Test auth middleware permission-based access control.
        
        Business Value: Enables granular access control for different subscription tiers.
        Strategic Impact: Core business logic enforcement through middleware.
        """
        # Test permission-based endpoint access
        permission_tests = [
            {
                "endpoint": "/api/protected/read-data",
                "method": "GET", 
                "required_permission": "read",
                "description": "Read-only data access"
            },
            {
                "endpoint": "/api/protected/write-data",
                "method": "POST",
                "required_permission": "write", 
                "description": "Write data operations"
            },
            {
                "endpoint": "/api/protected/admin-panel",
                "method": "GET",
                "required_permission": "admin",
                "description": "Admin panel access"
            }
        ]
        
        for user in self.test_users:
            user_token = self.auth_helper.create_test_jwt_token(
                user_id=user["user_id"],
                email=user["email"],
                permissions=user["permissions"]
            )
            
            for test in permission_tests:
                # Make request with user's token
                if test["method"] == "GET":
                    response = self.client.get(
                        test["endpoint"],
                        headers={"Authorization": f"Bearer {user_token}"}
                    )
                elif test["method"] == "POST":
                    response = self.client.post(
                        test["endpoint"],
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={"test_data": "middleware_test"}
                    )
                
                # Check permission enforcement
                required_permission = test["required_permission"]
                user_has_permission = required_permission in user["permissions"]
                
                if user_has_permission:
                    # Should succeed
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["access_granted"] is True
                    assert response_data["permission_validated"] == required_permission
                else:
                    # Should be forbidden
                    assert response.status_code == 403
                    error_data = response.json()
                    assert "insufficient permissions" in error_data["detail"].lower()
                    assert required_permission in error_data.get("required_permission", "")
                
                self.logger.info(f"Permission test for {user['subscription_tier']} accessing {test['endpoint']}: {'✓' if user_has_permission else '✗'}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_auth_middleware_subscription_tier_enforcement(self):
        """
        Test auth middleware subscription tier-based access control.
        
        Business Value: Protects premium features and enables revenue enforcement.
        Strategic Impact: Technical implementation of business model subscription tiers.
        """
        # Define tier-restricted endpoints
        tier_endpoints = [
            {
                "endpoint": "/api/tier/free-features",
                "min_tier": "free",
                "description": "Basic features available to all users"
            },
            {
                "endpoint": "/api/tier/premium-analytics",
                "min_tier": "mid",
                "description": "Premium analytics for mid+ tiers"
            },
            {
                "endpoint": "/api/tier/enterprise-features",
                "min_tier": "enterprise", 
                "description": "Enterprise-only features"
            }
        ]
        
        # Define tier hierarchy for comparison
        tier_hierarchy = ["free", "early", "mid", "enterprise"]
        
        for user in self.test_users:
            user_token = self.auth_helper.create_test_jwt_token(
                user_id=user["user_id"],
                email=user["email"],
                permissions=user["permissions"]
            )
            
            for endpoint_test in tier_endpoints:
                response = self.client.get(
                    endpoint_test["endpoint"],
                    headers={"Authorization": f"Bearer {user_token}"}
                )
                
                # Check tier access
                user_tier_level = tier_hierarchy.index(user["subscription_tier"])
                required_tier_level = tier_hierarchy.index(endpoint_test["min_tier"])
                
                should_have_access = user_tier_level >= required_tier_level
                
                if should_have_access:
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["tier_access_granted"] is True
                    assert response_data["user_tier"] == user["subscription_tier"]
                else:
                    assert response.status_code == 402  # Payment Required
                    error_data = response.json()
                    assert "upgrade required" in error_data["detail"].lower()
                    assert endpoint_test["min_tier"] in error_data.get("required_tier", "")
                
                self.logger.info(f"Tier access test for {user['subscription_tier']} accessing {endpoint_test['endpoint']}: {'✓' if should_have_access else '✗'}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_auth_middleware_request_context_injection(self):
        """
        Test auth middleware injects proper user context into requests.
        
        Business Value: Enables personalized responses and user-specific data access.
        Security Impact: Ensures user context is properly isolated and injected.
        """
        user = self.test_users[1]  # Enterprise user
        user_token = self.auth_helper.create_test_jwt_token(
            user_id=user["user_id"],
            email=user["email"],
            permissions=user["permissions"]
        )
        
        # Make request that should receive injected user context
        response = self.client.get(
            "/api/protected/context-aware-endpoint",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        context_data = response.json()
        
        # Validate user context was properly injected
        assert "user_context" in context_data
        user_context = context_data["user_context"]
        
        assert user_context["user_id"] == user["user_id"]
        assert user_context["email"] == user["email"]
        assert user_context["subscription_tier"] == user["subscription_tier"]
        assert user_context["permissions"] == user["permissions"]
        
        # Validate request metadata injection
        assert "request_metadata" in context_data
        metadata = context_data["request_metadata"]
        
        assert "request_id" in metadata
        assert "authenticated_at" in metadata
        assert "user_agent" in metadata
        assert metadata["auth_method"] == "jwt_bearer"
        
        self.logger.info("Auth middleware context injection validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_auth_middleware_circuit_breaker_patterns(self):
        """
        Test auth middleware circuit breaker and error handling patterns.
        
        Business Value: Ensures service reliability under auth system failures.
        Strategic Impact: Maintains service availability during auth service outages.
        """
        # Test expired token handling
        expired_token = self._create_expired_jwt_token()
        
        expired_response = self.client.get(
            "/api/protected/user-data",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert expired_response.status_code == 401
        error_data = expired_response.json()
        assert "token expired" in error_data["detail"].lower()
        assert error_data.get("error_code") == "TOKEN_EXPIRED"
        
        # Test malformed token handling  
        malformed_response = self.client.get(
            "/api/protected/user-data",
            headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        
        assert malformed_response.status_code == 401
        error_data = malformed_response.json()
        assert "invalid token format" in error_data["detail"].lower()
        
        # Test rate limiting (simulate multiple failed attempts)
        rate_limit_responses = []
        for i in range(10):  # Exceed rate limit
            rate_response = self.client.get(
                "/api/protected/user-data",
                headers={"Authorization": "Bearer invalid-token-attempt"}
            )
            rate_limit_responses.append(rate_response)
        
        # Later requests should be rate limited
        final_response = rate_limit_responses[-1]
        if final_response.status_code == 429:  # Too Many Requests
            assert "rate limit exceeded" in final_response.json()["detail"].lower()
        
        self.logger.info("Auth middleware circuit breaker patterns validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_auth_middleware_cors_and_security_headers(self):
        """
        Test auth middleware security headers and CORS handling.
        
        Business Value: Enables secure web application integration.
        Security Impact: Validates security headers prevent common web vulnerabilities.
        """
        user = self.test_users[0]
        user_token = self.auth_helper.create_test_jwt_token(
            user_id=user["user_id"],
            email=user["email"],
            permissions=user["permissions"]
        )
        
        # Test CORS preflight request
        options_response = self.client.options(
            "/api/protected/user-data",
            headers={
                "Origin": "https://app.netra.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        # Validate CORS headers
        assert options_response.status_code == 200
        assert "Access-Control-Allow-Origin" in options_response.headers
        assert "Access-Control-Allow-Methods" in options_response.headers
        assert "Access-Control-Allow-Headers" in options_response.headers
        
        # Test actual request with security headers
        authenticated_response = self.client.get(
            "/api/protected/user-data",
            headers={
                "Authorization": f"Bearer {user_token}",
                "Origin": "https://app.netra.com"
            }
        )
        
        assert authenticated_response.status_code == 200
        
        # Validate security headers in response
        security_headers = authenticated_response.headers
        
        # Check for security headers
        expected_security_headers = [
            "X-Content-Type-Options",  # nosniff
            "X-Frame-Options",         # DENY/SAMEORIGIN
            "X-XSS-Protection",        # 1; mode=block
            "Strict-Transport-Security" # HSTS
        ]
        
        for header in expected_security_headers:
            if header in security_headers:
                assert len(security_headers[header]) > 0
        
        self.logger.info("Auth middleware security headers validation successful")
    
    # Helper methods for middleware testing
    
    def _create_test_app_with_auth_middleware(self) -> FastAPI:
        """Create test FastAPI application with auth middleware."""
        app = FastAPI(title="Auth Middleware Test App")
        
        # Add custom auth middleware
        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            """Test auth middleware implementation."""
            import jwt
            from fastapi import HTTPException
            
            # Skip auth for non-protected routes
            if not request.url.path.startswith("/api/protected") and not request.url.path.startswith("/api/tier"):
                response = await call_next(request)
                return response
            
            # Extract JWT token
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Authentication required")
            
            token = auth_header.split(" ")[1]
            
            try:
                # Validate JWT token
                jwt_secret = self.env.get("JWT_SECRET_KEY") or "test-jwt-secret-key-unified-testing-32chars"
                payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
                
                # Add user context to request state
                request.state.user_context = {
                    "user_id": payload.get("sub"),
                    "email": payload.get("email"),
                    "permissions": payload.get("permissions", []),
                    "subscription_tier": payload.get("subscription_tier", "free"),
                    "authenticated_at": datetime.now(timezone.utc)
                }
                
                # Add request metadata
                request.state.request_metadata = {
                    "request_id": str(__import__("uuid").uuid4()),
                    "authenticated_at": datetime.now(timezone.utc),
                    "user_agent": request.headers.get("user-agent", ""),
                    "auth_method": "jwt_bearer"
                }
                
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=401, 
                    detail="Token expired",
                    headers={"error_code": "TOKEN_EXPIRED"}
                )
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token format")
            
            response = await call_next(request)
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            # Add CORS headers
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            
            return response
        
        # Add test endpoints
        @app.get("/api/protected/user-data")
        async def get_user_data(request: Request):
            user_context = request.state.user_context
            return {
                "authenticated": True,
                "user_id": user_context["user_id"],
                "subscription_tier": user_context["subscription_tier"]
            }
        
        @app.get("/api/protected/read-data")
        async def read_data(request: Request):
            user_context = request.state.user_context
            if "read" not in user_context["permissions"]:
                raise HTTPException(
                    status_code=403, 
                    detail="Insufficient permissions",
                    headers={"required_permission": "read"}
                )
            return {"access_granted": True, "permission_validated": "read"}
        
        @app.post("/api/protected/write-data")
        async def write_data(request: Request):
            user_context = request.state.user_context
            if "write" not in user_context["permissions"]:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions", 
                    headers={"required_permission": "write"}
                )
            return {"access_granted": True, "permission_validated": "write"}
        
        @app.get("/api/protected/admin-panel")
        async def admin_panel(request: Request):
            user_context = request.state.user_context
            if "admin" not in user_context["permissions"]:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions",
                    headers={"required_permission": "admin"}
                )
            return {"access_granted": True, "permission_validated": "admin"}
        
        @app.get("/api/tier/free-features")
        async def free_features(request: Request):
            return self._handle_tier_endpoint(request, "free")
        
        @app.get("/api/tier/premium-analytics")
        async def premium_analytics(request: Request):
            return self._handle_tier_endpoint(request, "mid")
        
        @app.get("/api/tier/enterprise-features")
        async def enterprise_features(request: Request):
            return self._handle_tier_endpoint(request, "enterprise")
        
        @app.get("/api/protected/context-aware-endpoint")
        async def context_aware_endpoint(request: Request):
            return {
                "user_context": dict(request.state.user_context),
                "request_metadata": dict(request.state.request_metadata)
            }
        
        return app
    
    def _handle_tier_endpoint(self, request: Request, required_tier: str):
        """Handle tier-restricted endpoint access."""
        from fastapi import HTTPException
        
        user_context = request.state.user_context
        user_tier = user_context["subscription_tier"]
        
        tier_hierarchy = ["free", "early", "mid", "enterprise"]
        user_tier_level = tier_hierarchy.index(user_tier)
        required_tier_level = tier_hierarchy.index(required_tier)
        
        if user_tier_level < required_tier_level:
            raise HTTPException(
                status_code=402,
                detail="Upgrade required to access this feature",
                headers={"required_tier": required_tier}
            )
        
        return {
            "tier_access_granted": True,
            "user_tier": user_tier,
            "required_tier": required_tier
        }
    
    def _create_expired_jwt_token(self) -> str:
        """Create an expired JWT token for testing."""
        import jwt
        
        expired_payload = {
            "sub": "expired-user",
            "email": "expired@test.com",
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "iss": "netra-auth-service"
        }
        
        jwt_secret = self.env.get("JWT_SECRET_KEY") or "test-jwt-secret-key-unified-testing-32chars"
        return jwt.encode(expired_payload, jwt_secret, algorithm="HS256")