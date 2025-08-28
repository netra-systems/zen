"""
Critical JWT Authentication Tests - Essential security validation

Tests core JWT token generation, validation, and cross-service consistency.
Critical for system security and user authentication.

Business Value Justification (BVJ):
- Segment: All tiers (security is universal requirement) 
- Business Goal: Prevent security breaches and ensure compliance
- Value Impact: Protects customer data and maintains system trust
- Revenue Impact: Security breaches could cost $100K+ and destroy user trust

Test Coverage:
- JWT token generation works
- Cross-service token validation
- Token expiry handling
- Basic authentication flow
"""

import pytest
import time
from typing import Dict, Any

from tests.e2e.config import TEST_CONFIG
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.enforce_real_services import E2EServiceValidator


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestCriticalJWTAuthentication:
    """Critical JWT authentication tests using real services"""
    
    def setup_method(self):
        """Setup with real authentication services"""
        self.services_manager = RealServicesManager()
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_jwt_token_generation_works(self):
        """Test JWT tokens can be generated successfully"""
        
        # Generate token via real auth service
        token_result = self.services_manager.generate_jwt_token()
        assert token_result['success'], f"JWT generation failed: {token_result.get('error')}"
        assert 'token' in token_result, "No token in response"
        assert token_result['token'], "Empty token generated"

    @pytest.mark.e2e  
    @pytest.mark.critical
    def test_jwt_token_validation_works(self):
        """Test JWT tokens can be validated successfully"""
        
        # Generate token
        token_result = self.services_manager.generate_jwt_token()
        assert token_result['success'], "Token generation failed"
        
        # Validate token
        validation_result = self.services_manager.validate_jwt_token(token_result['token'])
        assert validation_result['valid'], f"Token validation failed: {validation_result.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_cross_service_token_consistency(self):
        """Test tokens work consistently across all services"""
        
        # Generate token
        token_result = self.services_manager.generate_jwt_token()
        assert token_result['success'], "Token generation failed"
        token = token_result['token']
        
        # Test token works with backend service
        backend_test = self.services_manager.test_token_with_backend(token)
        assert backend_test['valid'], f"Token failed with backend: {backend_test.get('error')}"
        
        # Test token works with auth service
        auth_test = self.services_manager.test_token_with_auth_service(token)  
        assert auth_test['valid'], f"Token failed with auth service: {auth_test.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_expired_token_handling(self):
        """Test system properly handles expired tokens"""
        
        # Generate token with short expiry
        short_token_result = self.services_manager.generate_jwt_token(expiry_seconds=2)
        assert short_token_result['success'], "Short expiry token generation failed"
        
        # Wait for expiration
        time.sleep(3)
        
        # Test expired token is rejected
        validation_result = self.services_manager.validate_jwt_token(short_token_result['token'])
        assert not validation_result['valid'], "Expired token was incorrectly validated"
        assert 'expired' in validation_result.get('error', '').lower(), "No expiry error message"


# Initialize real services
E2EServiceValidator.enforce_real_services() 
class TestCriticalAuthenticationFlow:
    """Critical authentication flow tests"""
    
    def setup_method(self):
        """Setup"""
        self.services_manager = RealServicesManager()
        
    def teardown_method(self):
        """Cleanup"""  
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_complete_login_flow(self):
        """Test complete login flow works end-to-end"""
        
        # Start authentication process
        auth_start = self.services_manager.start_oauth_flow()
        assert auth_start['success'], f"OAuth start failed: {auth_start.get('error')}"
        
        # Complete authentication (simulate successful OAuth)
        auth_complete = self.services_manager.complete_oauth_flow(auth_start['flow_id'])
        assert auth_complete['success'], f"OAuth completion failed: {auth_complete.get('error')}"
        assert 'token' in auth_complete, "No token after successful auth"

    @pytest.mark.e2e
    @pytest.mark.critical  
    def test_websocket_authentication(self):
        """Test WebSocket authentication works with JWT tokens"""
        
        # Generate token
        token_result = self.services_manager.generate_jwt_token()
        assert token_result['success'], "Token generation failed"
        
        # Connect WebSocket with token
        ws_result = self.services_manager.connect_websocket_with_token(token_result['token'])
        assert ws_result['connected'], f"WebSocket auth failed: {ws_result.get('error')}"
        
        # Test authenticated WebSocket can send messages
        message_result = self.services_manager.send_websocket_message("test message")
        assert message_result['success'], f"Authenticated WebSocket messaging failed: {message_result.get('error')}"