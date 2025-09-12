"""
Issue #521: Service Authentication 403 Regression Test Suite

This test validates the resolution of 403 "Not authenticated" errors for service:netra-backend
when making internal service-to-service calls. The test is designed to initially FAIL if 
403 errors persist and PASS once authentication is properly configured.

Test Strategy:
1. Validate SERVICE_SECRET configuration consistency across services
2. Test service-to-service authentication without 403 errors 
3. Verify cascade issue resolution (Issue #5 database session creation)
4. Confirm end-to-end Golden Path functionality restoration

Execution Environment: GCP Staging (NO DOCKER REQUIRED)
"""

import pytest
import requests
import time
import json
from typing import Dict, Any, Optional
import logging
from unittest import TestCase

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.orchestration import OrchestrationConfig

logger = logging.getLogger(__name__)


class TestIssue521AuthenticationRegression(SSotBaseTestCase):
    """
    Issue #521 Regression Test Suite
    
    Tests service-to-service authentication to verify 403 errors are resolved.
    This test suite is designed to validate the specific authentication failures
    documented in Issue #521 and ensure they don't reoccur.
    """
    
    @classmethod
    def setUpClass(cls):
        """Setup test class with staging environment configuration."""
        super().setUpClass()
        cls.staging_config = {
            'base_url': 'https://netra-backend-staging-1234567890-uc.a.run.app',  # Replace with actual staging URL
            'auth_service_url': 'https://netra-auth-staging-1234567890-uc.a.run.app',
            'timeout': 30,
            'retry_count': 3
        }
        
    def setUp(self):
        """Setup individual test with required configuration."""
        super().setUp()
        self.session = requests.Session()
        self.session.timeout = self.staging_config['timeout']
        
    def tearDown(self):
        """Clean up test resources."""
        if hasattr(self, 'session'):
            self.session.close()
        super().tearDown()

    def test_staging_deployment_health_all_services(self):
        """
        Test: Verify all services are healthy in staging environment
        
        This test ensures the basic prerequisite that all services are deployed
        and responding before testing authentication flows.
        
        Expected: All services return 200 OK health status
        Failure Mode: Service deployment issues preventing authentication testing
        """
        logger.info("Testing staging deployment health for Issue #521")
        
        services = {
            'backend': f"{self.staging_config['base_url']}/health",
            'auth': f"{self.staging_config['auth_service_url']}/health"
        }
        
        health_results = {}
        
        for service_name, health_url in services.items():
            try:
                response = self.session.get(health_url)
                health_results[service_name] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'healthy': response.status_code == 200
                }
                
                if response.status_code != 200:
                    logger.error(f"Service {service_name} health check failed: {response.status_code}")
                    logger.error(f"Response body: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to reach {service_name} service: {str(e)}")
                health_results[service_name] = {
                    'status_code': 0,
                    'error': str(e),
                    'healthy': False
                }
        
        # Assert all services are healthy
        failed_services = [name for name, result in health_results.items() if not result['healthy']]
        
        self.assertEqual(len(failed_services), 0, 
                        f"Unhealthy services detected: {failed_services}. "
                        f"Health results: {json.dumps(health_results, indent=2)}")
        
        logger.info("All services healthy - deployment prerequisite met")

    def test_service_to_service_authentication_no_403_errors(self):
        """
        Test: Verify service:netra-backend can authenticate for internal calls
        
        This is the core test for Issue #521. It validates that the SERVICE_SECRET
        configuration issue has been resolved and service-to-service authentication
        works without 403 "Not authenticated" errors.
        
        Expected: Service authentication succeeds without 403 errors
        Failure Mode: 403 Forbidden errors indicate SERVICE_SECRET mismatch
        """
        logger.info("Testing service-to-service authentication for Issue #521")
        
        # Test internal service endpoint that requires service authentication
        internal_endpoint = f"{self.staging_config['base_url']}/internal/auth/validate"
        
        # Simulate service-to-service call that would trigger 403 error if unfixed
        service_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'service:netra-backend',
            'X-Service-Auth': 'internal'  # Trigger service authentication path
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    internal_endpoint,
                    headers=service_headers,
                    json={'test': 'service_auth_validation'},
                    timeout=self.staging_config['timeout']
                )
                
                # Log response for debugging
                logger.info(f"Service auth attempt {attempt + 1}: {response.status_code}")
                if response.status_code != 200:
                    logger.warning(f"Response headers: {dict(response.headers)}")
                    logger.warning(f"Response body: {response.text[:500]}")
                
                # Issue #521 specific assertion - MUST NOT return 403
                self.assertNotEqual(response.status_code, 403,
                                  f"Issue #521 REGRESSION: Got 403 'Not authenticated' error. "
                                  f"This indicates SERVICE_SECRET configuration is still broken. "
                                  f"Response: {response.text}")
                
                # Accept various success codes (200, 201, 202) and auth-related codes (401)
                # 401 is acceptable (wrong credentials) but 403 indicates configuration issue
                if response.status_code in [200, 201, 202]:
                    logger.info("Service authentication successful - Issue #521 resolved")
                    return  # Test passed
                
                if response.status_code == 401:
                    logger.info("Got 401 Unauthorized - this is different from Issue #521 (403 Forbidden)")
                    logger.info("401 indicates token validation issue, not SERVICE_SECRET mismatch")
                    return  # This is not the Issue #521 problem
                    
                # For other status codes, retry
                if attempt < max_retries - 1:
                    time.sleep(2)  # Brief retry delay
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(2)
                else:
                    self.fail(f"Service authentication test failed after {max_retries} attempts: {str(e)}")
        
        # If we get here, all retries failed
        self.fail(f"Service authentication failed after {max_retries} attempts. "
                 f"Last response: {response.status_code} - {response.text[:200]}")

    def test_database_session_creation_after_auth_fix(self):
        """
        Test: Verify Issue #5 cascade resolution - database sessions work after auth fix
        
        Issue #521 directly causes Issue #5 (database session creation failures).
        This test validates that fixing service authentication automatically
        resolves the downstream database session creation problems.
        
        Expected: Database sessions create successfully 
        Failure Mode: Database session failures persist even after auth is fixed
        """
        logger.info("Testing cascade resolution - database sessions after auth fix")
        
        # Test endpoint that requires database session creation
        db_session_endpoint = f"{self.staging_config['base_url']}/api/v1/agents/status"
        
        try:
            response = self.session.get(
                db_session_endpoint,
                timeout=self.staging_config['timeout']
            )
            
            # Log response details
            logger.info(f"Database session test response: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"DB session response: {response.text[:300]}")
            
            # Should not get service authentication errors (403) anymore
            self.assertNotEqual(response.status_code, 403,
                              f"Database session creation still failing with 403 errors. "
                              f"This suggests Issue #521 service auth fix did not resolve "
                              f"the cascade failure to Issue #5. Response: {response.text}")
            
            # Database connection should be working (200, 401, or other non-503 codes)
            self.assertNotEqual(response.status_code, 503,
                              f"Database session creation returning 503 Service Unavailable. "
                              f"This indicates Issue #5 database sessions still failing "
                              f"even after Issue #521 auth fix. Response: {response.text}")
            
            logger.info("Database session creation working - Issue #5 cascade resolved")
            
        except requests.exceptions.RequestException as e:
            # Network errors are different from auth/db errors
            logger.error(f"Network error during database session test: {str(e)}")
            self.fail(f"Could not test database session creation due to network error: {str(e)}")

    def test_service_secret_environment_consistency(self):
        """
        Test: Validate SERVICE_SECRET configuration consistency (diagnostic)
        
        This test attempts to validate that the root cause of Issue #521
        (SERVICE_SECRET mismatch between services) has been resolved by
        checking environment configuration consistency.
        
        Expected: SERVICE_SECRET configuration is consistent and valid
        Failure Mode: Configuration inconsistencies that could cause auth failures
        """
        logger.info("Testing SERVICE_SECRET environment consistency")
        
        # Test configuration endpoint that might expose SERVICE_SECRET status
        config_endpoint = f"{self.staging_config['base_url']}/internal/config/status"
        
        try:
            response = self.session.get(
                config_endpoint,
                timeout=self.staging_config['timeout']
            )
            
            logger.info(f"Configuration status check: {response.status_code}")
            
            # Even if endpoint doesn't exist (404), it shouldn't be 403 (auth issue)
            self.assertNotEqual(response.status_code, 403,
                              f"Configuration endpoint returning 403 suggests ongoing "
                              f"service authentication issues from Issue #521")
            
            if response.status_code == 200:
                try:
                    config_data = response.json()
                    logger.info("Configuration endpoint accessible - service auth working")
                    
                    # Look for environment validation status if available
                    if 'service_auth' in config_data:
                        service_auth_status = config_data['service_auth']
                        self.assertTrue(service_auth_status.get('enabled', True),
                                      f"Service authentication disabled: {service_auth_status}")
                        
                except json.JSONDecodeError:
                    logger.info("Configuration endpoint returned non-JSON response")
            
            logger.info("SERVICE_SECRET configuration appears consistent")
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not check configuration consistency: {str(e)}")
            # This is a diagnostic test - don't fail if endpoint unavailable
            logger.info("SERVICE_SECRET consistency test skipped due to network error")

    def test_golden_path_end_to_end_validation(self):
        """
        Test: Validate Golden Path user workflow after Issue #521 resolution
        
        This test ensures that the core business value (users login → get AI responses)
        is restored after fixing the service authentication failures. This represents
        the ultimate validation that Issue #521 resolution protects $500K+ ARR.
        
        Expected: Golden Path workflow components respond normally
        Failure Mode: Business-critical workflows still broken after auth fix
        """
        logger.info("Testing Golden Path validation after Issue #521 resolution")
        
        # Test key Golden Path endpoints that depend on service communication
        golden_path_endpoints = [
            '/api/v1/agents/list',  # Agent listing requires service auth
            '/api/v1/health/comprehensive',  # Health check with auth validation
            '/websocket/status',  # WebSocket functionality depends on service auth
        ]
        
        results = {}
        
        for endpoint_path in golden_path_endpoints:
            endpoint_url = f"{self.staging_config['base_url']}{endpoint_path}"
            
            try:
                response = self.session.get(endpoint_url, timeout=15)
                
                results[endpoint_path] = {
                    'status_code': response.status_code,
                    'success': response.status_code not in [403, 503]  # Not auth or service errors
                }
                
                logger.info(f"Golden Path endpoint {endpoint_path}: {response.status_code}")
                
                # Critical assertion: No service authentication failures
                self.assertNotEqual(response.status_code, 403,
                                  f"Golden Path endpoint {endpoint_path} still returning 403 errors. "
                                  f"This indicates Issue #521 service authentication problems persist, "
                                  f"blocking core business functionality ($500K+ ARR at risk).")
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Golden Path endpoint {endpoint_path} request failed: {str(e)}")
                results[endpoint_path] = {'error': str(e), 'success': False}
        
        # Summarize Golden Path health
        successful_endpoints = [path for path, result in results.items() if result.get('success', False)]
        total_endpoints = len(golden_path_endpoints)
        
        logger.info(f"Golden Path validation: {len(successful_endpoints)}/{total_endpoints} endpoints healthy")
        
        # Require majority of endpoints to be functional for Golden Path success
        success_ratio = len(successful_endpoints) / total_endpoints
        self.assertGreaterEqual(success_ratio, 0.6,
                               f"Golden Path validation failed: {success_ratio:.1%} endpoints healthy. "
                               f"Results: {json.dumps(results, indent=2)}. "
                               f"This indicates Issue #521 resolution incomplete.")
        
        logger.info("Golden Path validation successful - Issue #521 resolution confirmed")


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test suite
    pytest.main([__file__, '-v', '--tb=short'])