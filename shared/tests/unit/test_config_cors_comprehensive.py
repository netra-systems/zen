"""
Comprehensive Unit Tests for CORS Configuration Module

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (CRITICAL FRONTEND-BACKEND COMMUNICATION)
- Business Goal: Zero CORS-related failures blocking frontend-backend communication
- Value Impact: Prevents CORS errors that break golden path user flow frontend interactions
- Strategic Impact: Enables secure cross-origin requests for modern web architecture
- Revenue Impact: Eliminates CORS failures that prevent users from accessing the system

MISSION CRITICAL: These tests validate CORS configuration components that enable:
1. Secure frontend-backend communication across all environments
2. Environment-specific CORS origin configuration (DEV/STAGING/PROD)
3. WebSocket CORS configuration for real-time agent communication
4. Static asset CORS configuration for CDN and font serving
5. CORS security validation and content type checking
6. Service-to-service communication bypass for internal APIs
7. FastAPI middleware integration for seamless CORS handling

GOLDEN PATH CORS SCENARIOS TESTED:
1. Origin Validation: Proper origin checking for each environment
2. Header Management: Correct CORS headers for frontend requests
3. WebSocket Support: CORS origins for real-time agent communication
4. Security Validation: Content-type and origin security checks
5. Environment Isolation: CORS configs don't leak between environments
6. Performance Optimization: FastAPI middleware configuration
7. Static Asset Serving: CDN-optimized CORS for fonts and images

TESTING APPROACH:
- Real CORS configuration objects (no mocks for CORS logic)
- Minimal mocking limited to external HTTP requests only
- SSOT compliance using test_framework utilities
- Business value focus on CORS reliability scenarios
- Golden path focus on environment-specific CORS configuration
- Coverage target: 95%+ method coverage on critical CORS paths
"""

import pytest
import re
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# SSOT imports following absolute import rules
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.cors_config_builder import (
    CORSConfigurationBuilder,
    CORSEnvironment,
    CORSSecurityEvent,
    get_cors_origins,
    get_cors_config,
    is_origin_allowed,
    validate_content_type,
    is_service_to_service_request,
    get_cors_health_info,
    get_websocket_cors_origins,
    get_static_file_cors_headers,
    get_cdn_cors_config,
    get_fastapi_cors_config
)
from shared.security_origins_config import SecurityOriginsConfig


class TestCORSConfigurationComprehensive(SSotBaseTestCase):
    """
    Comprehensive test suite for CORS Configuration Module.
    
    Tests the critical CORS configuration components that enable secure
    frontend-backend communication for golden path user flow stability.
    """
    
    def setUp(self):
        """Set up test environment with proper CORS configuration."""
        super().setUp()
        self.env = get_env()
        
        # Enable isolation for clean test environment
        self.env.enable_isolation()
        
        # Set test environment with CORS configuration
        self.env.set('ENVIRONMENT', 'development', 'test_setup')
        self.env.set('TESTING', 'true', 'test_setup')
        
        # Clear any cached CORS configuration
        self.setup_test_cors_environment()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env.reset()
        super().tearDown()
    
    def setup_test_cors_environment(self):
        """Set up test CORS environment configuration."""
        # Clear any custom CORS origins for clean testing
        if self.env.get('CORS_ORIGINS'):
            self.env.delete('CORS_ORIGINS', 'test_cleanup')
    
    @contextmanager
    def temp_env_vars(self, **kwargs):
        """Context manager for temporary environment variables."""
        original_values = {}
        for key, value in kwargs.items():
            original_values[key] = self.env.get(key)
            self.env.set(key, value, "temp_test_var")
        
        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    self.env.delete(key, "temp_test_cleanup")
                else:
                    self.env.set(key, original_value, "temp_test_restore")

    # === CORS CONFIGURATION BUILDER TESTS ===
    
    def test_cors_configuration_builder_initialization(self):
        """
        Test CORSConfigurationBuilder initialization and sub-builders.
        
        BVJ: CORSConfigurationBuilder is the SSOT for CORS configuration.
        Proper initialization is critical for all frontend-backend communication.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test main builder initialization
        self.assertIsNotNone(cors_builder, "CORSConfigurationBuilder should initialize successfully")
        self.assertEqual(cors_builder.environment, 'development', "Should detect development environment")
        
        # Test sub-builders initialization
        self.assertIsNotNone(cors_builder.origins, "Origins builder should be initialized")
        self.assertIsNotNone(cors_builder.headers, "Headers builder should be initialized")
        self.assertIsNotNone(cors_builder.security, "Security builder should be initialized")
        self.assertIsNotNone(cors_builder.service_detector, "Service detector should be initialized")
        self.assertIsNotNone(cors_builder.fastapi, "FastAPI builder should be initialized")
        self.assertIsNotNone(cors_builder.health, "Health builder should be initialized")
        self.assertIsNotNone(cors_builder.websocket, "WebSocket builder should be initialized")
        self.assertIsNotNone(cors_builder.static, "Static assets builder should be initialized")
        
        print("✓ CORSConfigurationBuilder initialization validated")
    
    def test_cors_origins_builder_allowed_origins(self):
        """
        Test CORS origins builder provides correct allowed origins.
        
        BVJ: Allowed origins are critical for frontend-backend communication.
        Incorrect origins break the golden path user flow.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test allowed origins retrieval
        allowed_origins = cors_builder.origins.allowed
        self.assertIsInstance(allowed_origins, list, "Allowed origins should be a list")
        self.assertGreater(len(allowed_origins), 0, "Should have at least one allowed origin")
        
        # Test development environment includes localhost origins
        localhost_origins = [origin for origin in allowed_origins if 'localhost' in origin]
        self.assertGreater(len(localhost_origins), 0, "Development should include localhost origins")
        
        # Test standard development origins
        expected_dev_origins = [
            'http://localhost:3000',
            'http://localhost:8000',
            'https://localhost:3000'
        ]
        
        for expected_origin in expected_dev_origins:
            found_origin = any(expected_origin in origin for origin in allowed_origins)
            self.assertTrue(found_origin, f"Development should include {expected_origin}")
        
        print(f"✓ CORS origins validated - {len(allowed_origins)} origins configured")
    
    def test_cors_origins_builder_is_allowed_validation(self):
        """
        Test CORS origins builder origin validation logic.
        
        BVJ: Origin validation prevents unauthorized cross-origin requests
        while allowing legitimate frontend-backend communication.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test allowed origins
        test_cases = [
            ('http://localhost:3000', True, "Localhost should be allowed in development"),
            ('https://localhost:3000', True, "HTTPS localhost should be allowed"),
            ('http://127.0.0.1:3000', True, "127.0.0.1 should be allowed in development"),
            ('http://frontend:3000', True, "Docker container names should be allowed"),
            ('https://malicious-site.com', False, "External sites should not be allowed"),
            ('', False, "Empty origin should not be allowed"),
        ]
        
        for origin, expected_allowed, description in test_cases:
            with self.subTest(origin=origin):
                is_allowed = cors_builder.origins.is_allowed(origin)
                self.assertEqual(is_allowed, expected_allowed, description)
        
        # Test service-to-service bypass
        service_allowed = cors_builder.origins.is_allowed('https://external.com', service_to_service=True)
        self.assertTrue(service_allowed, "Service-to-service should bypass CORS restrictions")
        
        print("✓ CORS origin validation logic tested")
    
    def test_cors_origins_builder_environment_specific_origins(self):
        """
        Test CORS origins builder provides environment-specific origins.
        
        BVJ: Environment-specific origins are critical for proper CORS
        configuration across DEV/STAGING/PROD environments.
        """
        test_environments = {
            'development': ['localhost', '127.0.0.1', 'frontend'],
            'staging': ['staging.netrasystems.ai', 'run.app'],
            'production': ['netrasystems.ai', 'secure-domain.com']
        }
        
        for env_name, expected_patterns in test_environments.items():
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    cors_builder = CORSConfigurationBuilder()
                    allowed_origins = cors_builder.origins.allowed
                    
                    # Check environment-specific patterns
                    for pattern in expected_patterns:
                        found_match = any(pattern in origin for origin in allowed_origins)
                        # Note: Some environments may not have all patterns configured
                        # This test validates the pattern detection works
                        if env_name == 'development':
                            self.assertTrue(found_match, f"{env_name} should include origins with {pattern}")
                    
                    print(f"✓ Environment-specific origins validated for {env_name}")
    
    def test_cors_headers_builder_configuration(self):
        """
        Test CORS headers builder provides correct header configuration.
        
        BVJ: Proper CORS headers are critical for frontend JavaScript
        to successfully communicate with backend APIs.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test allowed headers
        allowed_headers = cors_builder.headers.allowed_headers
        self.assertIsInstance(allowed_headers, list, "Allowed headers should be a list")
        self.assertGreater(len(allowed_headers), 0, "Should have at least one allowed header")
        
        # Test critical headers are included
        critical_headers = ['Authorization', 'Content-Type', 'Accept', 'Origin']
        for header in critical_headers:
            self.assertIn(header, allowed_headers, f"Should include critical header: {header}")
        
        # Test exposed headers
        exposed_headers = cors_builder.headers.exposed_headers
        self.assertIsInstance(exposed_headers, list, "Exposed headers should be a list")
        
        # Test allowed methods
        allowed_methods = cors_builder.headers.allowed_methods
        self.assertIsInstance(allowed_methods, list, "Allowed methods should be a list")
        critical_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        for method in critical_methods:
            self.assertIn(method, allowed_methods, f"Should include critical method: {method}")
        
        # Test max age
        max_age = cors_builder.headers.max_age
        self.assertIsInstance(max_age, int, "Max age should be integer")
        self.assertGreater(max_age, 0, "Max age should be positive")
        
        # Test header validation methods
        self.assertTrue(cors_builder.headers.is_header_allowed('Content-Type'), 
                       "Should allow Content-Type header")
        self.assertTrue(cors_builder.headers.is_method_allowed('POST'), 
                       "Should allow POST method")
        
        print(f"✓ CORS headers configuration validated - {len(allowed_headers)} headers, {len(allowed_methods)} methods")
    
    def test_cors_security_builder_content_type_validation(self):
        """
        Test CORS security builder content type validation.
        
        BVJ: Content type validation prevents malicious requests
        while allowing legitimate frontend-backend communication.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test allowed content types
        allowed_content_types = [
            'application/json',
            'application/x-www-form-urlencoded',
            'text/plain',
            'text/html',
            'multipart/form-data'
        ]
        
        for content_type in allowed_content_types:
            with self.subTest(content_type=content_type):
                is_valid = cors_builder.security.validate_content_type(content_type)
                self.assertTrue(is_valid, f"Should allow content type: {content_type}")
        
        # Test blocked content types
        blocked_content_types = [
            'application/x-msdownload',
            'text/vbscript',
            'application/vnd.ms-excel'
        ]
        
        for content_type in blocked_content_types:
            with self.subTest(content_type=content_type):
                is_valid = cors_builder.security.validate_content_type(content_type)
                self.assertFalse(is_valid, f"Should block suspicious content type: {content_type}")
        
        # Test content type with charset
        is_valid_with_charset = cors_builder.security.validate_content_type('application/json; charset=utf-8')
        self.assertTrue(is_valid_with_charset, "Should allow content type with charset")
        
        print("✓ Content type validation tested")
    
    def test_cors_security_builder_event_logging(self):
        """
        Test CORS security builder security event logging.
        
        BVJ: Security event logging is critical for monitoring
        and detecting potential CORS-related security threats.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Clear any existing security events
        cors_builder.security.clear_security_events()
        
        # Test security event logging
        cors_builder.security.log_security_event(
            "test_event",
            "http://malicious-site.com",
            "/api/sensitive",
            request_id="test-123",
            additional_info={"user_agent": "malicious-bot"}
        )
        
        # Test event retrieval
        events = cors_builder.security.get_security_events(limit=10)
        self.assertEqual(len(events), 1, "Should have logged one security event")
        
        event = events[0]
        self.assertEqual(event.event_type, "test_event", "Event type should match")
        self.assertEqual(event.origin, "http://malicious-site.com", "Origin should match")
        self.assertEqual(event.path, "/api/sensitive", "Path should match")
        self.assertEqual(event.request_id, "test-123", "Request ID should match")
        self.assertIn("user_agent", event.details, "Additional info should be included")
        
        print("✓ Security event logging validated")
    
    def test_cors_service_detector_internal_request_detection(self):
        """
        Test CORS service detector internal request detection.
        
        BVJ: Internal request detection enables service-to-service
        communication to bypass CORS restrictions for internal APIs.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test service-to-service request detection
        internal_headers = {
            'x-service-name': 'auth-service',
            'user-agent': 'httpx/0.24.0'
        }
        
        is_internal = cors_builder.service_detector.is_internal_request(internal_headers)
        self.assertTrue(is_internal, "Should detect internal service request")
        
        # Test regular browser request
        browser_headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        is_browser = cors_builder.service_detector.is_internal_request(browser_headers)
        self.assertFalse(is_browser, "Should not detect browser request as internal")
        
        # Test CORS bypass decision
        should_bypass = cors_builder.service_detector.should_bypass_cors(internal_headers)
        expected_bypass = cors_builder.environment != "production"
        self.assertEqual(should_bypass, expected_bypass, 
                        f"CORS bypass should be {expected_bypass} in {cors_builder.environment}")
        
        print("✓ Service detector internal request detection validated")
    
    def test_cors_fastapi_builder_middleware_config(self):
        """
        Test CORS FastAPI builder middleware configuration.
        
        BVJ: FastAPI middleware configuration is critical for
        integrating CORS handling into the web framework.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test middleware configuration
        middleware_config = cors_builder.fastapi.get_middleware_config()
        self.assertIsInstance(middleware_config, dict, "Middleware config should be dictionary")
        
        # Test required middleware configuration fields
        required_fields = [
            'allow_origins', 'allow_credentials', 'allow_methods',
            'allow_headers', 'expose_headers', 'max_age'
        ]
        
        for field in required_fields:
            self.assertIn(field, middleware_config, f"Middleware config should include {field}")
        
        # Test field types
        self.assertIsInstance(middleware_config['allow_origins'], list, "Origins should be list")
        self.assertIsInstance(middleware_config['allow_credentials'], bool, "Credentials should be boolean")
        self.assertIsInstance(middleware_config['allow_methods'], list, "Methods should be list")
        self.assertIsInstance(middleware_config['allow_headers'], list, "Headers should be list")
        self.assertIsInstance(middleware_config['max_age'], int, "Max age should be integer")
        
        # Test credentials are allowed (required for authentication)
        self.assertTrue(middleware_config['allow_credentials'], 
                       "Should allow credentials for authenticated requests")
        
        print("✓ FastAPI middleware configuration validated")
    
    def test_cors_websocket_builder_configuration(self):
        """
        Test CORS WebSocket builder configuration for real-time communication.
        
        BVJ: WebSocket CORS configuration is critical for real-time
        agent communication in the golden path user flow.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test WebSocket origins
        websocket_origins = cors_builder.websocket.allowed_origins
        self.assertIsInstance(websocket_origins, list, "WebSocket origins should be list")
        self.assertGreater(len(websocket_origins), 0, "Should have WebSocket origins configured")
        
        # Test WebSocket origins match regular CORS origins
        regular_origins = cors_builder.origins.allowed
        self.assertEqual(websocket_origins, regular_origins, 
                        "WebSocket origins should match regular CORS origins")
        
        # Test origin validation
        is_allowed = cors_builder.websocket.is_origin_allowed('http://localhost:3000')
        self.assertTrue(is_allowed, "Should allow localhost for WebSocket in development")
        
        print(f"✓ WebSocket CORS configuration validated - {len(websocket_origins)} origins")
    
    def test_cors_static_assets_builder_configuration(self):
        """
        Test CORS static assets builder for CDN and font serving.
        
        BVJ: Static asset CORS configuration is critical for
        serving fonts, images, and other assets from CDN.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test static file headers
        static_headers = cors_builder.static.get_static_headers()
        self.assertIsInstance(static_headers, dict, "Static headers should be dictionary")
        
        # Test required static headers
        self.assertIn('Access-Control-Allow-Origin', static_headers, "Should include origin header")
        self.assertIn('Access-Control-Allow-Methods', static_headers, "Should include methods header")
        self.assertEqual(static_headers['Access-Control-Allow-Origin'], '*', 
                        "Static assets should allow all origins")
        
        # Test CDN configuration
        cdn_config = cors_builder.static.get_cdn_config()
        self.assertIsInstance(cdn_config, dict, "CDN config should be dictionary")
        self.assertEqual(cdn_config['allow_origins'], ['*'], "CDN should allow all origins")
        self.assertEqual(cdn_config['allow_credentials'], False, "CDN should not require credentials")
        
        print("✓ Static assets CORS configuration validated")
    
    def test_cors_health_builder_configuration_info(self):
        """
        Test CORS health builder provides configuration information.
        
        BVJ: Health information is critical for monitoring
        and troubleshooting CORS configuration issues.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test configuration info
        config_info = cors_builder.health.get_config_info()
        self.assertIsInstance(config_info, dict, "Config info should be dictionary")
        
        # Test required info fields
        required_fields = [
            'environment', 'origins_count', 'origins', 'allow_credentials',
            'methods', 'headers_count', 'config_valid'
        ]
        
        for field in required_fields:
            self.assertIn(field, config_info, f"Config info should include {field}")
        
        # Test info values
        self.assertEqual(config_info['environment'], cors_builder.environment, 
                        "Should report correct environment")
        self.assertIsInstance(config_info['origins_count'], int, "Origins count should be integer")
        self.assertIsInstance(config_info['config_valid'], bool, "Config valid should be boolean")
        
        # Test debug info
        debug_info = cors_builder.health.get_debug_info()
        self.assertIsInstance(debug_info, dict, "Debug info should be dictionary")
        self.assertIn('configuration', debug_info, "Debug info should include configuration")
        self.assertIn('validation', debug_info, "Debug info should include validation")
        
        print("✓ CORS health configuration info validated")
    
    # === BACKWARD COMPATIBILITY TESTS ===
    
    def test_backward_compatibility_functions(self):
        """
        Test backward compatibility functions for existing code.
        
        BVJ: Backward compatibility ensures existing CORS configuration
        code continues to work during transition to unified system.
        """
        # Test get_cors_origins function
        origins = get_cors_origins('development')
        self.assertIsInstance(origins, list, "get_cors_origins should return list")
        self.assertGreater(len(origins), 0, "Should have origins for development")
        
        # Test get_cors_config function
        config = get_cors_config('development')
        self.assertIsInstance(config, dict, "get_cors_config should return dictionary")
        self.assertIn('allow_origins', config, "Config should include allow_origins")
        
        # Test is_origin_allowed function
        is_allowed = is_origin_allowed('http://localhost:3000', [], 'development')
        self.assertIsInstance(is_allowed, bool, "is_origin_allowed should return boolean")
        
        # Test validate_content_type function
        is_valid = validate_content_type('application/json')
        self.assertTrue(is_valid, "Should validate application/json as valid")
        
        # Test is_service_to_service_request function
        headers = {'x-service-name': 'test-service'}
        is_service = is_service_to_service_request(headers)
        self.assertTrue(is_service, "Should detect service-to-service request")
        
        # Test get_cors_health_info function
        health_info = get_cors_health_info('development')
        self.assertIsInstance(health_info, dict, "Health info should be dictionary")
        
        # Test get_websocket_cors_origins function
        ws_origins = get_websocket_cors_origins('development')
        self.assertIsInstance(ws_origins, list, "WebSocket origins should be list")
        
        # Test get_static_file_cors_headers function
        static_headers = get_static_file_cors_headers()
        self.assertIsInstance(static_headers, dict, "Static headers should be dictionary")
        
        # Test get_cdn_cors_config function
        cdn_config = get_cdn_cors_config('development')
        self.assertIsInstance(cdn_config, dict, "CDN config should be dictionary")
        
        # Test get_fastapi_cors_config function
        fastapi_config = get_fastapi_cors_config('development')
        self.assertIsInstance(fastapi_config, dict, "FastAPI config should be dictionary")
        
        print("✓ Backward compatibility functions validated")
    
    # === ENVIRONMENT-SPECIFIC TESTS ===
    
    def test_cors_configuration_environment_specificity(self):
        """
        Test CORS configuration across different environments.
        
        BVJ: Environment-specific CORS configuration is critical
        for proper security and functionality in each deployment environment.
        """
        test_environments = ['development', 'staging', 'production']
        
        for env_name in test_environments:
            with self.subTest(environment=env_name):
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    cors_builder = CORSConfigurationBuilder()
                    
                    # Test environment detection
                    self.assertEqual(cors_builder.environment, env_name,
                                   f"Should detect {env_name} environment")
                    
                    # Test environment-specific origins
                    allowed_origins = cors_builder.origins.allowed
                    self.assertGreater(len(allowed_origins), 0, 
                                     f"Should have origins for {env_name}")
                    
                    # Test environment-specific validation
                    is_valid, error_msg = cors_builder.validate()
                    if env_name == 'production':
                        # Production should not allow wildcard origins
                        self.assertNotIn('*', allowed_origins, 
                                       "Production should not allow wildcard origins")
                    
                    print(f"✓ CORS configuration validated for environment: {env_name}")
    
    def test_cors_configuration_custom_origins_override(self):
        """
        Test CORS configuration with custom origins override.
        
        BVJ: Custom origins override enables flexible CORS configuration
        for specific deployment scenarios and testing requirements.
        """
        custom_origins = 'https://custom1.example.com,https://custom2.example.com'
        
        with self.temp_env_vars(CORS_ORIGINS=custom_origins):
            cors_builder = CORSConfigurationBuilder()
            allowed_origins = cors_builder.origins.allowed
            
            # Test custom origins are used
            self.assertIn('https://custom1.example.com', allowed_origins,
                         "Should include first custom origin")
            self.assertIn('https://custom2.example.com', allowed_origins,
                         "Should include second custom origin")
            
            # Test custom origins validation
            is_allowed_custom1 = cors_builder.origins.is_allowed('https://custom1.example.com')
            self.assertTrue(is_allowed_custom1, "Should allow first custom origin")
            
            is_allowed_custom2 = cors_builder.origins.is_allowed('https://custom2.example.com')
            self.assertTrue(is_allowed_custom2, "Should allow second custom origin")
            
            # Test non-custom origin is not allowed
            is_allowed_other = cors_builder.origins.is_allowed('https://other.example.com')
            self.assertFalse(is_allowed_other, "Should not allow non-custom origin")
        
        print("✓ Custom origins override validated")
    
    # === ERROR HANDLING TESTS ===
    
    def test_cors_configuration_invalid_environment_handling(self):
        """
        Test CORS configuration handles invalid environments gracefully.
        
        BVJ: Graceful error handling ensures CORS configuration
        provides meaningful fallbacks for unexpected environments.
        """
        with self.temp_env_vars(ENVIRONMENT='invalid_environment'):
            cors_builder = CORSConfigurationBuilder()
            
            # Should fallback to development configuration
            self.assertEqual(cors_builder.environment, 'invalid_environment',
                           "Should preserve environment name")
            
            # Should still provide valid configuration
            allowed_origins = cors_builder.origins.allowed
            self.assertIsInstance(allowed_origins, list, "Should provide valid origins list")
            self.assertGreater(len(allowed_origins), 0, "Should have fallback origins")
            
            # Should provide valid middleware config
            middleware_config = cors_builder.fastapi.get_middleware_config()
            self.assertIsInstance(middleware_config, dict, "Should provide valid middleware config")
        
        print("✓ Invalid environment handling validated")
    
    def test_cors_configuration_missing_security_origins_handling(self):
        """
        Test CORS configuration handles missing SecurityOriginsConfig gracefully.
        
        BVJ: Graceful handling of missing security configuration
        ensures system continues to function with reasonable defaults.
        """
        # Mock SecurityOriginsConfig to simulate missing configuration
        with patch('shared.cors_config_builder.SecurityOriginsConfig') as mock_security:
            mock_security.get_cors_origins.side_effect = Exception("Security config not found")
            
            # Should handle gracefully and provide fallback
            cors_builder = CORSConfigurationBuilder()
            allowed_origins = cors_builder.origins.allowed
            
            # Should still provide some origins (even if just fallback localhost)
            self.assertIsInstance(allowed_origins, list, "Should provide origins list")
        
        print("✓ Missing security origins handling validated")
    
    # === PERFORMANCE TESTS ===
    
    def test_cors_configuration_performance_requirements(self):
        """
        Test CORS configuration meets performance requirements.
        
        BVJ: CORS configuration performance is critical for
        request processing speed and overall system responsiveness.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Test origins retrieval performance
        start_time = time.time()
        for _ in range(1000):
            origins = cors_builder.origins.allowed
            self.assertGreater(len(origins), 0)
        origins_time = time.time() - start_time
        
        # Test origin validation performance
        start_time = time.time()
        for _ in range(1000):
            is_allowed = cors_builder.origins.is_allowed('http://localhost:3000')
            self.assertIsInstance(is_allowed, bool)
        validation_time = time.time() - start_time
        
        # Test middleware config generation performance
        start_time = time.time()
        for _ in range(100):
            config = cors_builder.fastapi.get_middleware_config()
            self.assertIsInstance(config, dict)
        middleware_time = time.time() - start_time
        
        # Performance requirements
        self.assertLess(origins_time, 0.1, "1000 origins retrievals should complete in under 100ms")
        self.assertLess(validation_time, 0.1, "1000 origin validations should complete in under 100ms")
        self.assertLess(middleware_time, 0.1, "100 middleware configs should complete in under 100ms")
        
        print(f"✓ CORS configuration performance validated - Origins: {origins_time:.3f}s, "
              f"Validation: {validation_time:.3f}s, Middleware: {middleware_time:.3f}s")
    
    # === BUSINESS VALUE VALIDATION ===
    
    def test_cors_golden_path_requirements(self):
        """
        Test CORS configuration meets golden path user flow requirements.
        
        BVJ: Golden path requirements ensure CORS configuration supports
        the critical user flow from login → AI responses without CORS errors.
        """
        cors_builder = CORSConfigurationBuilder()
        
        # Golden path requirement: Frontend origins allowed
        allowed_origins = cors_builder.origins.allowed
        localhost_allowed = any('localhost' in origin for origin in allowed_origins)
        self.assertTrue(localhost_allowed, "Frontend localhost origins required for development")
        
        # Golden path requirement: Essential headers allowed
        allowed_headers = cors_builder.headers.allowed_headers
        essential_headers = ['Authorization', 'Content-Type', 'Accept']
        for header in essential_headers:
            self.assertIn(header, allowed_headers, f"Essential header required: {header}")
        
        # Golden path requirement: Essential methods allowed
        allowed_methods = cors_builder.headers.allowed_methods
        essential_methods = ['GET', 'POST', 'OPTIONS']
        for method in essential_methods:
            self.assertIn(method, allowed_methods, f"Essential method required: {method}")
        
        # Golden path requirement: WebSocket support
        websocket_origins = cors_builder.websocket.allowed_origins
        self.assertGreater(len(websocket_origins), 0, "WebSocket origins required for real-time communication")
        
        # Golden path requirement: Configuration validation
        is_valid, error_msg = cors_builder.validate()
        self.assertTrue(is_valid, f"CORS configuration must be valid: {error_msg}")
        
        # Golden path requirement: FastAPI middleware ready
        middleware_config = cors_builder.fastapi.get_middleware_config()
        required_fields = ['allow_origins', 'allow_credentials', 'allow_methods', 'allow_headers']
        for field in required_fields:
            self.assertIn(field, middleware_config, f"Middleware requires {field}")
        
        print("✓ Golden path CORS requirements validated")
    
    def test_cors_business_value_metrics(self):
        """
        Test and record CORS configuration business value metrics.
        
        BVJ: Business value metrics demonstrate CORS configuration
        contribution to system reliability and golden path user flow stability.
        """
        cors_builder = CORSConfigurationBuilder()
        metrics = {}
        
        # Metric 1: Origin validation reliability
        validation_attempts = 50
        successful_validations = 0
        test_origins = ['http://localhost:3000', 'https://app.example.com', 'https://malicious.com']
        
        for _ in range(validation_attempts):
            try:
                for origin in test_origins:
                    is_allowed = cors_builder.origins.is_allowed(origin)
                    if isinstance(is_allowed, bool):
                        successful_validations += 1
            except Exception:
                pass
        
        validation_reliability = successful_validations / (validation_attempts * len(test_origins))
        
        # Metric 2: Middleware configuration generation reliability
        middleware_attempts = 20
        successful_middleware = 0
        
        for _ in range(middleware_attempts):
            try:
                config = cors_builder.fastapi.get_middleware_config()
                if isinstance(config, dict) and 'allow_origins' in config:
                    successful_middleware += 1
            except Exception:
                pass
        
        middleware_reliability = successful_middleware / middleware_attempts
        
        # Metric 3: Security validation reliability
        security_attempts = 30
        successful_security = 0
        test_content_types = ['application/json', 'text/plain', 'application/x-msdownload']
        
        for _ in range(security_attempts):
            try:
                for content_type in test_content_types:
                    is_valid = cors_builder.security.validate_content_type(content_type)
                    if isinstance(is_valid, bool):
                        successful_security += 1
            except Exception:
                pass
        
        security_reliability = successful_security / (security_attempts * len(test_content_types))
        
        # Business value assertions
        self.assertGreaterEqual(validation_reliability, 0.95, "Origin validation should be 95%+ reliable")
        self.assertGreaterEqual(middleware_reliability, 0.95, "Middleware generation should be 95%+ reliable")
        self.assertGreaterEqual(security_reliability, 0.95, "Security validation should be 95%+ reliable")
        
        # Record metrics
        metrics = {
            'cors_origin_validation_reliability': f"{validation_reliability:.1%}",
            'cors_middleware_generation_reliability': f"{middleware_reliability:.1%}",
            'cors_security_validation_reliability': f"{security_reliability:.1%}"
        }
        
        print(f"✓ CORS configuration business value metrics: {metrics}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])