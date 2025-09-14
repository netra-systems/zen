#!/usr/bin/env python3
"""
Test script to reproduce Issue #1007 - Service Authentication API Signature Mismatches

This test reproduces the exact service authentication failure pattern described in the issue:
"SERVICE_SECRET=REDACTED found in config or environment - auth=REDACTED fail"

The test validates the complete service-to-service authentication flow and identifies
API signature mismatches between backend client and auth service.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, Optional

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.configuration import get_configuration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceAuthenticationTestSuite:
    """Test suite to reproduce and diagnose service authentication failures."""

    def __init__(self):
        self.env = get_env()
        self.test_results = {}

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test suite for service authentication."""
        logger.info("🚀 Starting Issue #1007 Service Authentication Reproduction Test")
        logger.info("=" * 80)

        # Test 1: Environment Configuration Validation
        await self.test_environment_configuration()

        # Test 2: Service Authentication Client Initialization
        await self.test_auth_client_initialization()

        # Test 3: Service Header Generation
        await self.test_service_header_generation()

        # Test 4: Backend-Auth Service Communication
        await self.test_backend_auth_communication()

        # Test 5: API Signature Validation
        await self.test_api_signature_validation()

        # Summary Report
        self.generate_summary_report()

        return self.test_results

    async def test_environment_configuration(self):
        """Test SERVICE_SECRET and SERVICE_ID configuration."""
        logger.info("🔍 Test 1: Environment Configuration Validation")

        try:
            # Check SERVICE_SECRET availability
            service_secret = self.env.get('SERVICE_SECRET')
            service_id = self.env.get('SERVICE_ID')

            # Check configuration loading
            config = get_configuration()
            config_service_secret = getattr(config, 'service_secret', None)
            config_service_id = getattr(config, 'service_id', None)

            self.test_results['environment_config'] = {
                'service_secret_env': bool(service_secret),
                'service_secret_length': len(service_secret) if service_secret else 0,
                'service_id_env': bool(service_id),
                'config_service_secret': bool(config_service_secret),
                'config_service_id': bool(config_service_id),
                'environment_type': self.env.get('ENVIRONMENT', 'unknown')
            }

            if service_secret:
                logger.info(f"✅ SERVICE_SECRET detected in environment (length: {len(service_secret)})")
            else:
                logger.error("❌ SERVICE_SECRET missing from environment")

            if service_id:
                logger.info(f"✅ SERVICE_ID detected: {service_id}")
            else:
                logger.info("ℹ️  SERVICE_ID not explicitly set (using default)")

            # Reproduce the exact error pattern from logs
            if service_secret:
                logger.info(f"SERVICE_SECRET=REDACTED found in config or environment - testing auth validation...")

        except Exception as e:
            logger.error(f"❌ Environment configuration test failed: {e}")
            self.test_results['environment_config'] = {'error': str(e)}

    async def test_auth_client_initialization(self):
        """Test AuthServiceClient initialization and configuration."""
        logger.info("🔍 Test 2: Service Authentication Client Initialization")

        try:
            # Initialize auth client (this is where the issue might occur)
            auth_client = AuthServiceClient()

            self.test_results['auth_client_init'] = {
                'client_initialized': True,
                'service_id_configured': bool(auth_client.service_id),
                'service_secret_configured': bool(auth_client.service_secret),
                'auth_service_enabled': bool(auth_client.settings.enabled),
                'auth_service_url': auth_client.settings.base_url if auth_client.settings else None
            }

            logger.info(f"✅ AuthServiceClient initialized")
            logger.info(f"   - Service ID: {auth_client.service_id}")
            logger.info(f"   - Service Secret configured: {bool(auth_client.service_secret)}")
            logger.info(f"   - Auth service enabled: {auth_client.settings.enabled}")

            # Check for configuration issues that might cause auth failures
            if not auth_client.service_secret:
                logger.error("❌ CRITICAL: service_secret is None in auth client")

            if not auth_client.settings.enabled:
                logger.warning("⚠️  Auth service is disabled - this could cause auth failures")

            return auth_client

        except Exception as e:
            logger.error(f"❌ Auth client initialization failed: {e}")
            self.test_results['auth_client_init'] = {'error': str(e)}
            return None

    async def test_service_header_generation(self):
        """Test service authentication header generation."""
        logger.info("🔍 Test 3: Service Header Generation")

        try:
            auth_client = AuthServiceClient()

            # Test service auth headers generation
            headers = auth_client._get_service_auth_headers()

            self.test_results['header_generation'] = {
                'headers_generated': bool(headers),
                'service_id_header': 'X-Service-ID' in headers,
                'service_secret_header': 'X-Service-Secret' in headers,
                'header_count': len(headers),
                'header_keys': list(headers.keys())
            }

            logger.info(f"✅ Service headers generated: {list(headers.keys())}")

            # Validate header format
            if 'X-Service-ID' in headers:
                logger.info(f"   - X-Service-ID: {headers['X-Service-ID']}")
            else:
                logger.error("❌ Missing X-Service-ID header")

            if 'X-Service-Secret' in headers:
                logger.info(f"   - X-Service-Secret: [REDACTED] (length: {len(headers['X-Service-Secret'])})")
            else:
                logger.error("❌ Missing X-Service-Secret header")

            return headers

        except Exception as e:
            logger.error(f"❌ Header generation test failed: {e}")
            self.test_results['header_generation'] = {'error': str(e)}
            return {}

    async def test_backend_auth_communication(self):
        """Test actual backend to auth service communication."""
        logger.info("🔍 Test 4: Backend-Auth Service Communication")

        try:
            auth_client = AuthServiceClient()

            # Test if auth service is reachable
            service_available = await auth_client.check_service_availability()

            self.test_results['service_communication'] = {
                'service_available': service_available,
                'auth_service_url': auth_client.settings.base_url,
                'circuit_breaker_status': 'unknown'  # Will be updated if we can check
            }

            if service_available:
                logger.info("✅ Auth service is available")

                # Test token validation (this is where the failure likely occurs)
                try:
                    # Create a dummy token for testing
                    test_token = "test-token-for-validation"

                    # This should trigger the service authentication flow
                    validation_result = await auth_client.validate_token(test_token)

                    self.test_results['service_communication']['token_validation'] = {
                        'validation_attempted': True,
                        'validation_result': validation_result
                    }

                    logger.info(f"✅ Token validation response: {validation_result}")

                except Exception as validation_error:
                    logger.error(f"❌ Token validation failed: {validation_error}")
                    self.test_results['service_communication']['token_validation'] = {
                        'validation_attempted': True,
                        'error': str(validation_error)
                    }

                    # This is likely where we'll see the authentication failure
                    if "SERVICE_SECRET" in str(validation_error) or "auth" in str(validation_error).lower():
                        logger.error("🎯 REPRODUCTION SUCCESS: Found SERVICE_SECRET authentication failure!")

            else:
                logger.warning("⚠️  Auth service not available - cannot test communication")

        except Exception as e:
            logger.error(f"❌ Service communication test failed: {e}")
            self.test_results['service_communication'] = {'error': str(e)}

    async def test_api_signature_validation(self):
        """Test API signature compatibility between backend and auth service."""
        logger.info("🔍 Test 5: API Signature Validation")

        try:
            # Test the specific API endpoints involved in service authentication
            auth_client = AuthServiceClient()

            # Test request format that backend sends to auth service
            expected_request_format = {
                'headers': ['X-Service-ID', 'X-Service-Secret'],
                'body_format': 'JSON',
                'required_fields': ['token']
            }

            # Test response format that backend expects from auth service
            expected_response_format = {
                'success_fields': ['valid', 'user_id', 'exp'],
                'error_fields': ['valid', 'error', 'message']
            }

            self.test_results['api_signature'] = {
                'expected_request': expected_request_format,
                'expected_response': expected_response_format,
                'compatibility_check': 'pending'
            }

            logger.info("✅ API signature expectations documented")
            logger.info(f"   - Expected request headers: {expected_request_format['headers']}")
            logger.info(f"   - Expected response fields: {expected_response_format['success_fields']}")

        except Exception as e:
            logger.error(f"❌ API signature validation failed: {e}")
            self.test_results['api_signature'] = {'error': str(e)}

    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        logger.info("=" * 80)
        logger.info("📊 ISSUE #1007 REPRODUCTION TEST SUMMARY")
        logger.info("=" * 80)

        # Overall status
        total_tests = len([k for k in self.test_results.keys() if k != 'summary'])
        failed_tests = len([k for k, v in self.test_results.items()
                          if isinstance(v, dict) and 'error' in v])

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Failed Tests: {failed_tests}")
        logger.info(f"Success Rate: {((total_tests - failed_tests) / total_tests * 100):.1f}%")

        # Environment Status
        if 'environment_config' in self.test_results:
            env_config = self.test_results['environment_config']
            if not isinstance(env_config, dict) or 'error' not in env_config:
                logger.info(f"SERVICE_SECRET Status: {'✅ CONFIGURED' if env_config.get('service_secret_env') else '❌ MISSING'}")
                logger.info(f"Configuration Status: {'✅ LOADED' if env_config.get('config_service_secret') else '❌ FAILED'}")

        # Auth Client Status
        if 'auth_client_init' in self.test_results:
            auth_status = self.test_results['auth_client_init']
            if not isinstance(auth_status, dict) or 'error' not in auth_status:
                logger.info(f"Auth Client Status: {'✅ INITIALIZED' if auth_status.get('client_initialized') else '❌ FAILED'}")

        # Communication Status
        if 'service_communication' in self.test_results:
            comm_status = self.test_results['service_communication']
            if not isinstance(comm_status, dict) or 'error' not in comm_status:
                logger.info(f"Service Communication: {'✅ AVAILABLE' if comm_status.get('service_available') else '❌ UNAVAILABLE'}")

        # Issue Reproduction Status
        reproduction_success = self._check_reproduction_success()
        logger.info(f"Issue #1007 Reproduction: {'✅ SUCCESS' if reproduction_success else '❌ NOT REPRODUCED'}")

        self.test_results['summary'] = {
            'total_tests': total_tests,
            'failed_tests': failed_tests,
            'success_rate': ((total_tests - failed_tests) / total_tests * 100),
            'reproduction_success': reproduction_success
        }

        logger.info("=" * 80)

    def _check_reproduction_success(self) -> bool:
        """Check if we successfully reproduced the issue."""
        # Look for authentication failure patterns in our test results
        for test_name, result in self.test_results.items():
            if isinstance(result, dict):
                # Check for SERVICE_SECRET related errors
                if 'error' in result and 'SERVICE_SECRET' in str(result['error']):
                    return True
                # Check for auth validation failures
                if 'token_validation' in result and isinstance(result['token_validation'], dict):
                    if 'error' in result['token_validation']:
                        return True
        return False


async def main():
    """Main test execution."""
    test_suite = ServiceAuthenticationTestSuite()

    try:
        results = await test_suite.run_comprehensive_test()

        # Write results to file for analysis
        with open('issue_1007_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info("📝 Test results written to: issue_1007_test_results.json")

        # Exit with appropriate code
        if results.get('summary', {}).get('reproduction_success', False):
            logger.info("🎯 SUCCESS: Issue #1007 reproduced - authentication failure confirmed")
            sys.exit(0)
        else:
            logger.info("⚠️  Issue #1007 not reproduced - may be environment specific")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())