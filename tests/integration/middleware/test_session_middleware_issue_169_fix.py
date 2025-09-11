"""
Integration tests for Issue #169: SessionMiddleware Authentication Infrastructure Fix

These tests validate the 3-phase remediation plan implementation:
- Phase 1: Emergency defensive session access patterns
- Phase 2: SECRET_KEY configuration and middleware order fixes
- Phase 3: Consolidated secret management SSOT

Business Impact: Validates $500K+ ARR authentication flow reliability
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
from netra_backend.app.core.session_utils import (
    SessionAvailabilityDetector,
    SafeSessionAccessor,
    get_safe_session_data,
    is_session_available
)
from netra_backend.app.core.unified_secret_manager import (
    UnifiedSecretManager,
    SecretType,
    SecretSource,
    get_session_secret,
    validate_all_secrets
)
from netra_backend.app.core.middleware_setup import (
    setup_middleware,
    _validate_and_get_secret_key,
    _validate_session_middleware_installation
)


class TestSessionMiddlewareIssue169Fix:
    """Test suite for SessionMiddleware authentication infrastructure fixes."""
    
    def setup_method(self):
        """Set up test environment."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mock_env_vars = {
            'ENVIRONMENT': 'testing',
            'SECRET_KEY': 'test-secret-key-32-chars-minimum-required-for-starlette-testing',
            'GCP_PROJECT_ID': 'test-project'
        }
    
    def test_phase1_defensive_session_access_patterns(self):
        """Test Phase 1: Emergency defensive session access in GCP auth middleware."""
        # Create a FastAPI app without SessionMiddleware to test defensive patterns
        app = FastAPI()
        middleware = GCPAuthContextMiddleware(app)
        
        # Mock request with no session attribute
        mock_request = Mock(spec=Request)
        mock_request.headers = {'Authorization': 'Bearer test-token'}
        mock_request.cookies = {'user_id': 'test-user-123'}
        mock_request.state = Mock()
        mock_request.state.user_id = 'state-user-456'
        
        # Test safe session extraction
        session_data = middleware._safe_extract_session_data(mock_request)
        
        # Should successfully extract from fallback sources without crashing
        assert isinstance(session_data, dict)
        assert 'user_id' in session_data  # Should get from cookies or state
        
        self.logger.info("✅ Phase 1: Defensive session access patterns working")
    
    def test_phase1_session_availability_detector(self):
        """Test Phase 1: Session availability detection utility."""
        detector = SessionAvailabilityDetector()
        
        # Test environment-based detection
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'testing',
                'SECRET_KEY': 'test-secret-32-chars-minimum-required'
            }.get(key, default)
            
            availability = detector._detect_session_environment()
            assert availability is True
        
        # Test with missing SECRET_KEY
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'staging',
                'SECRET_KEY': 'short'  # Too short
            }.get(key, default)
            
            availability = detector._detect_session_environment()
            assert availability is False
        
        self.logger.info("✅ Phase 1: Session availability detection working")
    
    def test_phase1_safe_session_accessor(self):
        """Test Phase 1: Safe session accessor with fallback strategies."""
        accessor = SafeSessionAccessor()
        
        # Mock request with multiple data sources
        mock_request = Mock(spec=Request)
        mock_request.cookies = {
            'session_id': 'cookie-session-123',
            'user_id': 'cookie-user-456'
        }
        mock_request.state = Mock()
        mock_request.state.user_email = 'state@example.com'
        mock_request.headers = {'X-Session-ID': 'header-session-789'}
        
        # Mock session middleware unavailable
        with patch.object(accessor.detector, 'is_session_middleware_available', return_value=False):
            session_data = accessor.get_session_data(mock_request)
        
        # Should combine data from multiple fallback sources
        assert 'session_id' in session_data
        assert 'user_id' in session_data
        assert 'user_email' in session_data
        
        self.logger.info("✅ Phase 1: Safe session accessor fallbacks working")
    
    @patch('shared.isolated_environment.get_env')
    def test_phase2_secret_key_configuration_fix(self, mock_env):
        """Test Phase 2: SECRET_KEY configuration and GCP integration fixes."""
        # Mock environment manager
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default=None: self.mock_env_vars.get(key, default)
        mock_env.return_value = mock_env_manager
        
        # Mock environment object
        mock_environment = Mock()
        mock_environment.value = 'testing'
        
        # Mock config with invalid secret
        mock_config = Mock()
        mock_config.secret_key = 'short'  # Too short, should trigger fallback
        
        # Test the enhanced secret validation
        secret_key = _validate_and_get_secret_key(mock_config, mock_environment)
        
        # Should get a valid secret (from environment or fallback)
        assert len(secret_key) >= 32
        assert secret_key is not None
        
        self.logger.info("✅ Phase 2: SECRET_KEY configuration fixes working")
    
    def test_phase2_middleware_registration_order(self):
        """Test Phase 2: Middleware registration order fixes."""
        app = FastAPI()
        
        # Mock all middleware setup functions to track call order
        setup_calls = []
        
        def mock_session_setup(app_instance):
            setup_calls.append('session')
            # Actually add SessionMiddleware for validation
            app_instance.add_middleware(
                SessionMiddleware,
                secret_key='test-secret-key-32-chars-minimum-required-for-validation'
            )
        
        def mock_gcp_setup(app_instance):
            setup_calls.append('gcp_auth')
        
        def mock_cors_setup(app_instance):
            setup_calls.append('cors')
        
        def mock_auth_setup(app_instance):
            setup_calls.append('auth')
        
        # Patch middleware setup functions
        with patch('netra_backend.app.core.middleware_setup.setup_session_middleware', mock_session_setup), \
             patch('netra_backend.app.core.middleware_setup.setup_gcp_auth_context_middleware', mock_gcp_setup), \
             patch('netra_backend.app.core.middleware_setup.setup_cors_middleware', mock_cors_setup), \
             patch('netra_backend.app.core.middleware_setup.setup_auth_middleware', mock_auth_setup), \
             patch('netra_backend.app.core.middleware_setup.setup_gcp_websocket_readiness_middleware'), \
             patch('netra_backend.app.core.middleware_setup.create_cors_redirect_middleware', return_value=lambda req, call_next: None):
            
            setup_middleware(app)
        
        # Verify correct order: session first, then gcp_auth, then cors, then auth
        expected_order = ['session', 'gcp_auth', 'cors', 'auth']
        assert setup_calls == expected_order
        
        self.logger.info("✅ Phase 2: Middleware registration order fixed")
    
    def test_phase2_session_middleware_validation(self):
        """Test Phase 2: SessionMiddleware installation validation."""
        # Test with SessionMiddleware properly installed
        app = FastAPI()
        app.add_middleware(
            SessionMiddleware,
            secret_key='test-secret-key-32-chars-minimum-required-for-validation'
        )
        
        # Validation should pass without raising exceptions
        try:
            _validate_session_middleware_installation(app)
            validation_passed = True
        except Exception as e:
            validation_passed = False
            self.logger.error(f"Validation failed: {e}")
        
        assert validation_passed
        
        self.logger.info("✅ Phase 2: SessionMiddleware validation working")
    
    def test_phase3_unified_secret_manager(self):
        """Test Phase 3: Consolidated secret management SSOT."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': self.mock_env_vars.get(key, default)
            mock_env.return_value = mock_env_manager
            
            manager = UnifiedSecretManager('testing')
            
            # Test session secret loading
            secret_info = manager.get_session_secret()
            assert secret_info is not None
            assert len(secret_info.value) >= 32
            assert secret_info.source in [SecretSource.ENVIRONMENT_VARIABLE, SecretSource.DEVELOPMENT_FALLBACK]
            
            # Test secret validation
            validation_report = manager.validate_all_secrets()
            assert validation_report['overall_status'] in ['success', 'error']
            assert 'SECRET_KEY' in validation_report['secrets']
            
        self.logger.info("✅ Phase 3: Unified secret manager SSOT working")
    
    def test_phase3_secret_manager_fallback_strategies(self):
        """Test Phase 3: Secret manager fallback strategies."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            # Test environment with no secrets
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'testing'
                # No SECRET_KEY
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            manager = UnifiedSecretManager('testing')
            
            # Should still get a secret via development fallback
            secret_info = manager.get_session_secret()
            assert secret_info is not None
            assert secret_info.source == SecretSource.DEVELOPMENT_FALLBACK
            assert secret_info.is_fallback is True
            
        self.logger.info("✅ Phase 3: Secret manager fallback strategies working")
    
    @patch('shared.isolated_environment.get_env')
    def test_phase3_gcp_secret_manager_integration(self, mock_env):
        """Test Phase 3: GCP Secret Manager integration."""
        # Mock environment for staging
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'test-project'
        }.get(key, default)
        mock_env.return_value = mock_env_manager
        
        manager = UnifiedSecretManager('staging')
        
        # Mock GCP Secret Manager success
        with patch.object(manager, '_load_via_direct_gcp', return_value='gcp-secret-32-chars-minimum-required-for-testing'):
            secret_info = manager.get_session_secret()
            assert secret_info.source == SecretSource.GCP_SECRET_MANAGER
            assert len(secret_info.value) >= 32
        
        self.logger.info("✅ Phase 3: GCP Secret Manager integration working")
    
    def test_end_to_end_session_middleware_fix(self):
        """Test end-to-end SessionMiddleware functionality after fixes."""
        # Create a test app with our fixed middleware setup
        app = FastAPI()
        
        @app.get("/test-session")
        async def test_session_endpoint(request: Request):
            """Test endpoint that uses session functionality."""
            try:
                # Test safe session access using our defensive patterns
                session_data = get_safe_session_data(request)
                
                # Test session availability detection
                session_available = is_session_available(request)
                
                return JSONResponse({
                    "session_data": session_data,
                    "session_available": session_available,
                    "status": "success"
                })
            except Exception as e:
                return JSONResponse({
                    "error": str(e),
                    "status": "error"
                }, status_code=500)
        
        # Add SessionMiddleware manually for testing
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': self.mock_env_vars.get(key, default)
            mock_env.return_value = mock_env_manager
            
            # Get secret using our unified manager
            secret_info = get_session_secret('testing')
            app.add_middleware(SessionMiddleware, secret_key=secret_info.value)
        
        # Test the endpoint
        client = TestClient(app)
        response = client.get("/test-session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "session_data" in data
        
        self.logger.info("✅ End-to-end SessionMiddleware functionality working")
    
    def test_regression_sessionmiddleware_not_installed_error(self):
        """Test regression: Ensure we handle 'SessionMiddleware must be installed' error."""
        # Create app without SessionMiddleware
        app = FastAPI()
        
        @app.get("/test-no-session")
        async def test_no_session_endpoint(request: Request):
            """Test endpoint accessing session when middleware not installed."""
            # This should NOT crash with our defensive patterns
            middleware = GCPAuthContextMiddleware(app)
            session_data = middleware._safe_extract_session_data(request)
            return JSONResponse({"session_data": session_data})
        
        client = TestClient(app)
        response = client.get("/test-no-session")
        
        # Should succeed (not crash) even without SessionMiddleware
        assert response.status_code == 200
        data = response.json()
        assert "session_data" in data
        
        self.logger.info("✅ Regression test: No SessionMiddleware crash handled")


class TestIssue169BusinessImpactValidation:
    """Validate business impact of Issue #169 fixes."""
    
    def test_authentication_flow_continuity(self):
        """Test that authentication flow maintains $500K+ ARR business continuity."""
        # Test scenarios that would have failed before the fix
        scenarios = [
            {
                'name': 'Missing SECRET_KEY',
                'env_vars': {'ENVIRONMENT': 'staging'},  # No SECRET_KEY
                'should_have_fallback': True
            },
            {
                'name': 'Invalid SECRET_KEY',
                'env_vars': {'ENVIRONMENT': 'staging', 'SECRET_KEY': 'short'},
                'should_have_fallback': True
            },
            {
                'name': 'GCP Secret Manager unavailable',
                'env_vars': {'ENVIRONMENT': 'staging', 'GCP_PROJECT_ID': 'unavailable-project'},
                'should_have_fallback': True
            }
        ]
        
        for scenario in scenarios:
            with patch('shared.isolated_environment.get_env') as mock_env, \
                 patch('netra_backend.app.core.unified_secret_manager.get_env') as mock_env2:
                
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': scenario['env_vars'].get(key, default)
                mock_env.return_value = mock_env_manager
                mock_env2.return_value = mock_env_manager
                
                # Clear any cached instances to ensure clean test
                from netra_backend.app.core.unified_secret_manager import _unified_secret_manager
                global _unified_secret_manager
                _unified_secret_manager = None
                
                # Should not crash and should provide some form of secret
                try:
                    secret_info = get_session_secret(scenario['env_vars'].get('ENVIRONMENT', 'staging'))
                    assert secret_info is not None
                    assert len(secret_info.value) >= 32
                    
                    if scenario['should_have_fallback']:
                        # For scenarios that should have fallbacks, verify they are fallback/generated
                        # unless we got a real secret from environment
                        has_real_secret = 'SECRET_KEY' in scenario['env_vars'] and len(scenario['env_vars']['SECRET_KEY']) >= 32
                        if not has_real_secret:
                            assert secret_info.is_fallback or secret_info.is_generated, \
                                f"Expected fallback/generated secret for {scenario['name']}, got {secret_info.source}"
                    
                    print(f"✅ Business continuity maintained for: {scenario['name']} (source: {secret_info.source.value})")
                    
                except Exception as e:
                    pytest.fail(f"Business continuity broken for {scenario['name']}: {e}")
    
    def test_enterprise_compliance_requirements(self):
        """Test that fixes maintain enterprise compliance requirements."""
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_manager = Mock()
            mock_env_manager.get.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'production',
                'SECRET_KEY': 'production-secret-key-32-chars-minimum-required-for-enterprise-compliance'
            }.get(key, default)
            mock_env.return_value = mock_env_manager
            
            # Production should never use fallback secrets
            manager = UnifiedSecretManager('production')
            secret_info = manager.get_session_secret()
            
            assert secret_info is not None
            assert not secret_info.is_fallback  # Production must use real secrets
            assert not secret_info.is_generated  # No generated secrets in production
            
            print("✅ Enterprise compliance requirements maintained")


if __name__ == '__main__':
    # Run tests with detailed output
    pytest.main([__file__, '-v', '--tb=short'])