"""
Integration Tests for JWT SSOT Phase 1 APIs
Tests all new JWT validation, WebSocket auth, and service auth APIs
Ensures no breaking changes and golden path protection
"""
import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi.testclient import TestClient
from auth_service.main import app
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.migration.migration_support import migration_manager, MigrationFlag

class TestJWTValidationAPI:
    """Test JWT validation API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler fixture"""
        return JWTHandler()
    
    @pytest.fixture
    def valid_token(self, jwt_handler):
        """Valid test token fixture"""
        return jwt_handler.create_access_token("test-user", "test@example.com")
    
    @pytest.fixture
    def service_token(self, jwt_handler):
        """Valid service token fixture"""
        return jwt_handler.create_service_token("test-service", "Test Service")
    
    def test_jwt_validation_endpoint_basic(self, client, valid_token):
        """Test basic JWT validation endpoint"""
        response = client.post(
            "/api/v1/jwt/validate",
            json={
                "token": valid_token,
                "token_type": "access",
                "include_user_context": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["user_id"] == "test-user"
        assert data["email"] == "test@example.com"
        assert "validation_timestamp" in data
        assert "expires_at" in data
        assert "issued_at" in data
    
    def test_jwt_validation_invalid_token(self, client):
        """Test JWT validation with invalid token"""
        response = client.post(
            "/api/v1/jwt/validate",
            json={
                "token": "invalid.token.here",
                "token_type": "access"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert "error" in data
        assert data["error"] == "invalid_or_expired_token"
    
    def test_jwt_validation_consumption_mode(self, client, valid_token):
        """Test JWT validation with consumption mode (replay protection)"""
        response = client.post(
            "/api/v1/jwt/validate", 
            json={
                "token": valid_token,
                "token_type": "access",
                "validate_for_consumption": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["user_id"] == "test-user"
    
    def test_jwt_batch_validation(self, client, jwt_handler):
        """Test batch JWT validation endpoint"""
        # Create multiple tokens
        tokens = [
            jwt_handler.create_access_token(f"user-{i}", f"user{i}@example.com")
            for i in range(3)
        ]
        
        response = client.post(
            "/api/v1/jwt/validate-batch",
            json={
                "tokens": tokens,
                "token_type": "access",
                "include_user_context": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid_count"] == 3
        assert data["invalid_count"] == 0
        assert len(data["results"]) == 3
        
        for i, result in enumerate(data["results"]):
            assert result["valid"] is True
            assert result["user_id"] == f"user-{i}"
            assert result["token_index"] == i
    
    def test_jwt_user_id_extraction(self, client, valid_token):
        """Test JWT user ID extraction endpoint"""
        response = client.post(
            "/api/v1/jwt/extract-user-id",
            json={"token": valid_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["user_id"] == "test-user"
        assert "extraction_timestamp" in data
    
    def test_jwt_performance_stats(self, client):
        """Test JWT performance stats endpoint"""
        response = client.get("/api/v1/jwt/performance-stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "performance_stats" in data
        assert "service_info" in data
        assert data["service_info"]["environment"] == AuthConfig.get_environment()
    
    def test_jwt_blacklist_check(self, client, valid_token):
        """Test JWT blacklist check endpoint"""
        response = client.post(
            "/api/v1/jwt/check-blacklist",
            json={"token": valid_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["blacklisted"] is False
        assert "check_timestamp" in data
    
    def test_jwt_health_check(self, client):
        """Test JWT validation health endpoint"""
        response = client.get("/api/v1/jwt/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "jwt-validation"
        assert "validation_time_ms" in data
        assert "performance_stats" in data

class TestWebSocketAuthAPI:
    """Test WebSocket authentication API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler fixture"""
        return JWTHandler()
    
    @pytest.fixture
    def valid_token(self, jwt_handler):
        """Valid test token fixture"""
        return jwt_handler.create_access_token("ws-user", "ws@example.com")
    
    def test_websocket_auth_with_bearer_token(self, client, valid_token):
        """Test WebSocket authentication with Bearer token"""
        response = client.post(
            "/api/v1/auth/websocket/authenticate",
            json={
                "authorization_header": f"Bearer {valid_token}",
                "connection_id": "test-connection-1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["authenticated"] is True
        assert data["user_id"] == "ws-user"
        assert data["email"] == "ws@example.com"
        assert data["auth_method"] == "authorization_header"
        assert data["demo_user"] is False
        assert "execution_context" in data
        assert data["execution_context"]["user_id"] == "ws-user"
    
    def test_websocket_auth_with_subprotocol_token(self, client, valid_token):
        """Test WebSocket authentication with subprotocol token"""
        response = client.post(
            "/api/v1/auth/websocket/authenticate",
            json={
                "subprotocol_token": valid_token,
                "connection_id": "test-connection-2"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["authenticated"] is True
        assert data["user_id"] == "ws-user"
        assert data["auth_method"] == "subprotocol"
    
    def test_websocket_auth_demo_mode(self, client):
        """Test WebSocket authentication in demo mode"""
        # Enable demo mode
        environment = AuthConfig.get_environment()
        
        if environment in ["development", "test"]:
            response = client.post(
                "/api/v1/auth/websocket/authenticate",
                json={
                    "demo_mode": True,
                    "connection_id": "demo-connection"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["authenticated"] is True
            assert data["demo_user"] is True
            assert data["auth_method"] == "demo_mode"
            assert "execution_context" in data
            assert data["execution_context"]["demo_mode"] is True
        else:
            # Demo mode should be rejected in production
            response = client.post(
                "/api/v1/auth/websocket/authenticate",
                json={
                    "demo_mode": True,
                    "connection_id": "demo-connection"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["authenticated"] is False
            assert "demo_mode_not_allowed" in data["error"]
    
    def test_websocket_auth_no_token(self, client):
        """Test WebSocket authentication with no token provided"""
        response = client.post(
            "/api/v1/auth/websocket/authenticate",
            json={
                "connection_id": "no-token-connection"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["authenticated"] is False
        assert data["error"] == "no_authentication_provided"
    
    def test_websocket_token_extraction(self, client, valid_token):
        """Test WebSocket token extraction endpoint"""
        response = client.post(
            "/api/v1/auth/websocket/extract-token",
            json={
                "headers": {
                    "Authorization": f"Bearer {valid_token}",
                    "Sec-WebSocket-Protocol": "some-protocol"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["token_found"] is True
        assert data["token"] == valid_token
        assert data["source"] == "header"
        assert data["method"] == "authorization_bearer"
    
    def test_websocket_token_extraction_subprotocol(self, client, valid_token):
        """Test WebSocket token extraction from subprotocol"""
        response = client.post(
            "/api/v1/auth/websocket/extract-token",
            json={
                "headers": {
                    "Sec-WebSocket-Protocol": f"protocol1, {valid_token}, protocol2"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["token_found"] is True
        assert data["token"] == valid_token
        assert data["source"] == "subprotocol"
        assert data["method"] == "sec_websocket_protocol"
    
    def test_websocket_connection_validation(self, client, valid_token):
        """Test WebSocket connection validation endpoint"""
        response = client.post(
            "/api/v1/auth/websocket/validate-connection",
            json={
                "connection_id": "test-connection",
                "token": valid_token
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["connection_id"] == "test-connection"
        assert data["user_id"] == "ws-user"
    
    def test_websocket_context_refresh(self, client, jwt_handler):
        """Test WebSocket context refresh endpoint"""
        # Create new token for refresh
        new_token = jwt_handler.create_access_token("refreshed-user", "refreshed@example.com")
        
        response = client.post(
            "/api/v1/auth/websocket/refresh-context",
            json={
                "connection_id": "refresh-connection",
                "new_token": new_token
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["connection_id"] == "refresh-connection"
        assert data["user_id"] == "refreshed-user"
        assert "execution_context" in data
    
    def test_websocket_health_check(self, client):
        """Test WebSocket auth health endpoint"""
        response = client.get("/api/v1/auth/websocket/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "websocket-authentication"

class TestServiceAuthAPI:
    """Test service-to-service authentication API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    def test_service_authentication(self, client):
        """Test service authentication endpoint"""
        # Get service secret from environment
        from shared.isolated_environment import get_env
        service_secret = get_env().get("SERVICE_SECRET", "")
        
        if not service_secret:
            # Use development fallback
            environment = AuthConfig.get_environment()
            if environment in ["development", "test"]:
                service_secret = "dev-service-secret-not-for-production"
        
        if service_secret:
            response = client.post(
                "/api/v1/service/authenticate",
                json={
                    "service_id": "netra-backend",
                    "service_secret": service_secret,
                    "requested_permissions": ["jwt_validation"],
                    "token_duration_minutes": 60
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["authenticated"] is True
            assert data["service_id"] == "netra-backend"
            assert "service_token" in data
            assert "permissions" in data
            assert "jwt_validation" in data["permissions"]
        else:
            pytest.skip("SERVICE_SECRET not configured for testing")
    
    def test_service_authentication_invalid_secret(self, client):
        """Test service authentication with invalid secret"""
        response = client.post(
            "/api/v1/service/authenticate",
            json={
                "service_id": "netra-backend",
                "service_secret": "invalid-secret",
                "token_duration_minutes": 60
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["authenticated"] is False
        assert "invalid_service_secret" in data["error"]
    
    def test_service_authentication_unknown_service(self, client):
        """Test service authentication with unknown service ID"""
        response = client.post(
            "/api/v1/service/authenticate",
            json={
                "service_id": "unknown-service",
                "service_secret": "any-secret",
                "token_duration_minutes": 60
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["authenticated"] is False
        assert "unknown_service_id" in data["error"]
    
    def test_service_request_signing(self, client):
        """Test service request signing endpoint"""
        response = client.post(
            "/api/v1/service/sign-request",
            json={
                "service_id": "netra-backend",
                "request_method": "POST",
                "request_path": "/api/v1/jwt/validate",
                "request_body": '{"token": "test"}',
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            assert "signature" in data
            assert "timestamp" in data
            assert data["algorithm"] == "HMAC-SHA256"
            assert "headers" in data
            assert "X-Service-ID" in data["headers"]
            assert "X-Service-Signature" in data["headers"]
        else:
            # Skip if service secret not configured
            assert response.status_code == 400  # Unknown service ID
    
    def test_service_registry_access(self, client, jwt_handler):
        """Test service registry access endpoint"""
        # Create service token
        service_token = jwt_handler.create_service_token("netra-backend", "Test Service")
        
        response = client.get(
            "/api/v1/service/registry",
            headers={"Authorization": f"Bearer {service_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "services" in data
        assert "total_services" in data
        assert "requesting_service" in data
        
        # Check that netra-backend is in the registry
        assert "netra-backend" in data["services"]
        assert "permissions" in data["services"]["netra-backend"]
    
    def test_service_health_check(self, client):
        """Test service auth health endpoint"""
        response = client.get("/api/v1/service/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "service-authentication"
        assert "services_registered" in data
        assert data["services_registered"] > 0  # Should have at least netra-backend

class TestMigrationSupport:
    """Test migration support features"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    def test_migration_flags_enabled(self):
        """Test that migration flags are properly enabled"""
        # Check that critical flags are enabled
        assert migration_manager.is_flag_enabled(MigrationFlag.ENABLE_JWT_VALIDATION_API)
        assert migration_manager.is_flag_enabled(MigrationFlag.ENABLE_WEBSOCKET_AUTH_API)
        assert migration_manager.is_flag_enabled(MigrationFlag.ENABLE_SERVICE_AUTH_API)
    
    def test_migration_status(self):
        """Test migration status tracking"""
        status = migration_manager.get_migration_status()
        
        assert "current_phase" in status
        assert "enabled_flags" in status
        assert "api_status" in status
        
        # Check API status
        assert status["api_status"]["jwt_validation_api"] is True
        assert status["api_status"]["websocket_auth_api"] is True
        assert status["api_status"]["service_auth_api"] is True

class TestGoldenPathProtection:
    """Test that Golden Path functionality is preserved"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    def test_existing_auth_endpoints_still_work(self, client):
        """Test that existing auth endpoints are not broken"""
        # Test health endpoint
        response = client.get("/auth/health")
        assert response.status_code == 200
        
        # Test config endpoint
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        # Test status endpoint
        response = client.get("/auth/status")
        assert response.status_code == 200
    
    def test_existing_token_validation_still_works(self, client):
        """Test that existing token validation endpoint still works"""
        jwt_handler = JWTHandler()
        valid_token = jwt_handler.create_access_token("test-user", "test@example.com")
        
        response = client.post(
            "/auth/validate",
            json={"token": valid_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_id"] == "test-user"
    
    def test_dev_login_still_works(self, client):
        """Test that dev login endpoint still works"""
        environment = AuthConfig.get_environment()
        
        if environment in ["development", "test"]:
            response = client.post("/auth/dev/login")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"
    
    def test_performance_not_degraded(self, client):
        """Test that new APIs don't significantly degrade performance"""
        jwt_handler = JWTHandler()
        valid_token = jwt_handler.create_access_token("perf-test", "perf@example.com")
        
        # Time the new JWT validation API
        start_time = time.time()
        response = client.post(
            "/api/v1/jwt/validate",
            json={"token": valid_token, "token_type": "access"}
        )
        new_api_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        
        # Time the existing validation API
        start_time = time.time()
        response = client.post(
            "/auth/validate",
            json={"token": valid_token}
        )
        existing_api_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        
        # New API should not be significantly slower (allow 2x for overhead)
        assert new_api_time < existing_api_time * 2.0, f"New API too slow: {new_api_time}s vs {existing_api_time}s"

class TestBackwardCompatibility:
    """Test backward compatibility with existing systems"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    def test_all_existing_endpoints_accessible(self, client):
        """Test that all existing endpoints are still accessible"""
        # Health endpoints
        assert client.get("/health").status_code == 200
        assert client.get("/auth/health").status_code == 200
        
        # Config endpoints
        assert client.get("/auth/config").status_code == 200
        assert client.get("/auth/status").status_code == 200
        
        # OAuth endpoints (may fail if not configured, but should be accessible)
        response = client.get("/oauth/providers")
        assert response.status_code in [200, 503]  # 503 if OAuth not configured
    
    def test_response_formats_unchanged(self, client):
        """Test that existing response formats are unchanged"""
        # Test config endpoint response format
        response = client.get("/auth/config")
        assert response.status_code == 200
        data = response.json()
        
        # These fields should still exist
        assert "google_client_id" in data
        assert "oauth_enabled" in data
        assert "endpoints" in data
        assert "authorized_javascript_origins" in data
        
        # Test health endpoint response format
        response = client.get("/auth/health")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data
    
    def test_token_formats_unchanged(self, client):
        """Test that token formats are unchanged"""
        environment = AuthConfig.get_environment()
        
        if environment in ["development", "test"]:
            # Generate tokens using existing endpoint
            response = client.post("/auth/dev/login")
            assert response.status_code == 200
            data = response.json()
            
            access_token = data["access_token"]
            
            # Validate token using both old and new endpoints
            old_response = client.post("/auth/validate", json={"token": access_token})
            new_response = client.post("/api/v1/jwt/validate", json={"token": access_token})
            
            assert old_response.status_code == 200
            assert new_response.status_code == 200
            
            old_data = old_response.json()
            new_data = new_response.json()
            
            # Both should validate successfully
            assert old_data["valid"] is True
            assert new_data["valid"] is True
            
            # User ID should be the same
            assert old_data["user_id"] == new_data["user_id"]

# Performance and load testing
class TestAPIPerformance:
    """Test API performance and load handling"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler fixture"""
        return JWTHandler()
    
    def test_batch_validation_performance(self, client, jwt_handler):
        """Test batch validation performance"""
        # Create 10 tokens
        tokens = [
            jwt_handler.create_access_token(f"batch-user-{i}", f"batch{i}@example.com")
            for i in range(10)
        ]
        
        start_time = time.time()
        response = client.post(
            "/api/v1/jwt/validate-batch",
            json={"tokens": tokens, "token_type": "access"}
        )
        batch_time = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid_count"] == 10
        
        # Batch should be faster than individual validations
        start_time = time.time()
        for token in tokens:
            response = client.post(
                "/api/v1/jwt/validate",
                json={"token": token, "token_type": "access"}
            )
            assert response.status_code == 200
        individual_time = time.time() - start_time
        
        # Batch should be at least 2x faster
        assert batch_time < individual_time / 2.0, f"Batch not efficient: {batch_time}s vs {individual_time}s"
    
    def test_performance_stats_tracking(self, client, jwt_handler):
        """Test that performance stats are properly tracked"""
        # Make some API calls
        token = jwt_handler.create_access_token("stats-user", "stats@example.com")
        
        for _ in range(5):
            client.post("/api/v1/jwt/validate", json={"token": token})
        
        # Check performance stats
        response = client.get("/api/v1/jwt/performance-stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "performance_stats" in data
        stats = data["performance_stats"]
        
        # Should have recorded some requests
        assert stats["requests"]["total"] >= 5
        assert stats["requests"]["successful"] >= 5
        assert stats["cache"]["hit_rate"] >= 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])