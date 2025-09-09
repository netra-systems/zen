"""
Test JWT Handler Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Secure token-based authentication for multi-user platform
- Value Impact: Protects user sessions and enables secure multi-tenant operations
- Strategic Impact: Core security foundation for $120K+ MRR protection

CRITICAL COMPLIANCE:
- Tests business logic only, no external dependencies
- Validates security patterns that protect revenue-generating users
- Ensures JWT secrets are properly validated across environments
- Tests token lifecycle management for user retention
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from test_framework.mock_factory import MockFactory


class TestJWTHandlerBusinessLogic:
    """Test JWT handler core business logic without external dependencies."""
    
    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler with test configuration."""
        with patch.object(AuthConfig, 'get_jwt_secret', return_value='test-secret-' + 'x' * 32):
            with patch.object(AuthConfig, 'get_environment', return_value='test'):
                with patch.object(AuthConfig, 'get_service_secret', return_value='service-secret-' + 'x' * 16):
                    with patch.object(AuthConfig, 'get_service_id', return_value='test-service'):
                        handler = JWTHandler()
                        handler._initialize_blacklist_from_redis = Mock()  # Skip Redis in unit test
                        return handler
    
    @pytest.mark.unit
    def test_create_access_token_with_user_data(self, jwt_handler):
        """Test access token creation with complete user data."""
        # Given: User authentication data
        user_id = str(uuid.uuid4())
        email = "premium@enterprise.com"
        permissions = ["read_data", "write_analysis", "execute_agents"]
        
        # When: Creating access token
        token = jwt_handler.create_access_token(
            user_id=user_id,
            email=email,
            permissions=permissions
        )
        
        # Then: Token should be valid and contain expected data
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        
        # Verify token can be decoded
        decoded = jwt_handler.verify_access_token(token)
        assert decoded is not None
        assert decoded['sub'] == user_id
        assert decoded['email'] == email
        assert decoded['permissions'] == permissions
        assert decoded['token_type'] == 'access'
    
    @pytest.mark.unit
    def test_refresh_token_lifecycle_management(self, jwt_handler):
        """Test refresh token creation and validation for user retention."""
        # Given: Enterprise user needing long-term session
        user_id = str(uuid.uuid4())
        email = "enterprise@customer.com"
        
        # When: Creating refresh token for extended sessions
        refresh_token = jwt_handler.create_refresh_token(user_id, email)
        
        # Then: Refresh token should have extended expiry for user retention
        assert refresh_token is not None
        decoded = jwt_handler.verify_refresh_token(refresh_token)
        assert decoded['sub'] == user_id
        assert decoded['token_type'] == 'refresh'
        
        # Should have longer expiry than access tokens
        exp_time = datetime.fromtimestamp(decoded['exp'], timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now
        assert time_diff.days >= 7  # Refresh tokens should last at least a week
    
    @pytest.mark.unit
    def test_service_token_inter_service_authentication(self, jwt_handler):
        """Test service token creation for secure inter-service communication."""
        # Given: Backend service needs to authenticate with auth service
        service_name = "netra-backend"
        service_id = "backend-001"
        
        # When: Creating service token for microservice authentication
        service_token = jwt_handler.create_service_token(
            service_name=service_name,
            service_id=service_id
        )
        
        # Then: Service token should enable secure service-to-service calls
        assert service_token is not None
        decoded = jwt_handler.verify_service_token(service_token)
        assert decoded['service_name'] == service_name
        assert decoded['service_id'] == service_id
        assert decoded['token_type'] == 'service'
        
        # Service tokens should have appropriate expiry for service operations
        exp_time = datetime.fromtimestamp(decoded['exp'], timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now
        assert time_diff.total_seconds() >= 3600  # At least 1 hour for service operations
    
    @pytest.mark.unit
    def test_token_blacklist_security_enforcement(self, jwt_handler):
        """Test token blacklisting for immediate security enforcement."""
        # Given: User with valid access token
        user_id = str(uuid.uuid4())
        email = "security@test.com"
        token = jwt_handler.create_access_token(user_id, email)
        
        # Initially token should be valid
        assert jwt_handler.verify_access_token(token) is not None
        
        # When: Security incident requires immediate token invalidation
        jwt_handler.blacklist_token(token)
        
        # Then: Token should be immediately invalid
        assert jwt_handler.verify_access_token(token) is None
        
        # And: Token should remain blacklisted
        assert jwt_handler._is_token_blacklisted(token) is True
    
    @pytest.mark.unit
    def test_user_session_invalidation_security_boundary(self, jwt_handler):
        """Test complete user session invalidation for security boundaries."""
        # Given: User with multiple tokens (access + refresh)
        user_id = str(uuid.uuid4())
        email = "multiuser@enterprise.com"
        
        access_token = jwt_handler.create_access_token(user_id, email)
        refresh_token = jwt_handler.create_refresh_token(user_id, email)
        
        # Both tokens should be valid initially
        assert jwt_handler.verify_access_token(access_token) is not None
        assert jwt_handler.verify_refresh_token(refresh_token) is not None
        
        # When: Security requires invalidating all user sessions
        jwt_handler.invalidate_user_sessions(user_id)
        
        # Then: All user tokens should be invalidated
        assert jwt_handler.verify_access_token(access_token) is None
        assert jwt_handler.verify_refresh_token(refresh_token) is None
        
        # And: User should be in blacklist
        assert jwt_handler._is_user_blacklisted(user_id) is True
    
    @pytest.mark.unit
    def test_jwt_secret_validation_production_safety(self):
        """Test JWT secret validation enforces production security standards."""
        # When: Testing production environment secret validation
        with patch.object(AuthConfig, 'get_environment', return_value='production'):
            
            # Then: Should reject empty secrets in production
            with patch.object(AuthConfig, 'get_jwt_secret', return_value=''):
                with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set in production"):
                    JWTHandler()
            
            # Then: Should reject short secrets in production
            with patch.object(AuthConfig, 'get_jwt_secret', return_value='short'):
                with pytest.raises(ValueError, match="must be at least 32 characters"):
                    JWTHandler()
            
            # Then: Should accept proper secrets in production
            with patch.object(AuthConfig, 'get_jwt_secret', return_value='production-secret-' + 'x' * 32):
                with patch.object(AuthConfig, 'get_service_secret', return_value='service-secret'):
                    with patch.object(AuthConfig, 'get_service_id', return_value='prod-service'):
                        handler = JWTHandler()
                        handler._initialize_blacklist_from_redis = Mock()
                        assert handler.secret.startswith('production-secret-')
    
    @pytest.mark.unit
    def test_token_expiry_business_logic_validation(self, jwt_handler):
        """Test token expiry logic protects against expired token attacks."""
        # Given: Token with custom expiry
        user_id = str(uuid.uuid4())
        email = "expiry@test.com"
        
        # Mock short expiry for testing
        with patch.object(jwt_handler, 'access_expiry', 0):  # Expire immediately
            token = jwt_handler.create_access_token(user_id, email)
            
            # When: Token expires due to time passage
            import time
            time.sleep(1)  # Wait for expiry
            
            # Then: Expired token should be rejected
            result = jwt_handler.verify_access_token(token)
            assert result is None  # Should be None for expired tokens
    
    @pytest.mark.unit  
    def test_permission_based_authorization_business_logic(self, jwt_handler):
        """Test permission-based authorization logic for multi-tenant security."""
        # Given: Users with different permission levels
        basic_user_id = str(uuid.uuid4())
        premium_user_id = str(uuid.uuid4())
        enterprise_user_id = str(uuid.uuid4())
        
        # When: Creating tokens with different permission sets
        basic_token = jwt_handler.create_access_token(
            basic_user_id, "basic@test.com", ["read_basic"]
        )
        premium_token = jwt_handler.create_access_token(
            premium_user_id, "premium@test.com", ["read_basic", "read_premium", "write_data"]
        )
        enterprise_token = jwt_handler.create_access_token(
            enterprise_user_id, "enterprise@test.com", 
            ["read_basic", "read_premium", "write_data", "execute_agents", "admin_access"]
        )
        
        # Then: Each token should contain appropriate permissions for business tier
        basic_decoded = jwt_handler.verify_access_token(basic_token)
        assert len(basic_decoded['permissions']) == 1
        assert "read_basic" in basic_decoded['permissions']
        
        premium_decoded = jwt_handler.verify_access_token(premium_token)
        assert len(premium_decoded['permissions']) == 3
        assert "write_data" in premium_decoded['permissions']
        
        enterprise_decoded = jwt_handler.verify_access_token(enterprise_token)
        assert len(enterprise_decoded['permissions']) == 5
        assert "admin_access" in enterprise_decoded['permissions']
        assert "execute_agents" in enterprise_decoded['permissions']