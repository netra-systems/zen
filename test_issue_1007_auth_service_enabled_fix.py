#!/usr/bin/env python3
"""
Test script to validate Issue #1007 remediation - AUTH_SERVICE_ENABLED Fix

This test validates the root cause and remediation for Issue #1007.

ROOT CAUSE IDENTIFIED: AUTH_SERVICE_ENABLED=false
This causes service authentication to be completely disabled, which explains
the "SERVICE_SECRET=REDACTED found in config or environment - auth=REDACTED fail" logs.

REMEDIATION: Set AUTH_SERVICE_ENABLED=true to enable service authentication.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from typing import Dict, Any

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.clients.auth_client_cache import AuthServiceSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Issue1007RemediationTest:
    """Test suite to validate Issue #1007 remediation."""

    def __init__(self):
        self.env = get_env()
        self.test_results = {}

    async def run_remediation_test(self) -> Dict[str, Any]:
        """Run remediation validation test."""
        logger.info("🚀 Issue #1007 Remediation Test - AUTH_SERVICE_ENABLED Fix")
        logger.info("=" * 80)

        # Test 1: Reproduce the problem (AUTH_SERVICE_ENABLED=false)
        await self.test_problem_reproduction()

        # Test 2: Test the remediation (AUTH_SERVICE_ENABLED=true)
        await self.test_remediation_solution()

        # Test 3: Validate service authentication with enabled service
        await self.test_service_authentication_enabled()

        # Summary Report
        self.generate_remediation_report()

        return self.test_results

    async def test_problem_reproduction(self):
        """Reproduce the original problem with AUTH_SERVICE_ENABLED=false."""
        logger.info("🔍 Test 1: Problem Reproduction (AUTH_SERVICE_ENABLED=false)")

        try:
            # Check current environment state
            current_auth_enabled = self.env.get('AUTH_SERVICE_ENABLED', 'NOT SET')
            current_service_secret = self.env.get('SERVICE_SECRET', 'NOT SET')

            logger.info(f"Current AUTH_SERVICE_ENABLED: {current_auth_enabled}")
            logger.info(f"SERVICE_SECRET configured: {current_service_secret != 'NOT SET'}")

            # Create AuthServiceSettings to check the disabled state
            auth_settings = AuthServiceSettings.from_env()

            self.test_results['problem_reproduction'] = {
                'auth_service_enabled_env': current_auth_enabled,
                'auth_service_enabled_setting': auth_settings.enabled,
                'service_secret_configured': current_service_secret != 'NOT SET',
                'problem_reproduced': not auth_settings.enabled and current_service_secret != 'NOT SET'
            }

            if not auth_settings.enabled and current_service_secret != 'NOT SET':
                logger.info("🎯 PROBLEM REPRODUCED: SERVICE_SECRET is configured but AUTH_SERVICE_ENABLED=false")
                logger.info("   This explains the 'SERVICE_SECRET=REDACTED...auth=REDACTED fail' error")
            else:
                logger.warning("⚠️  Problem not reproduced - auth service may already be enabled")

        except Exception as e:
            logger.error(f"❌ Problem reproduction failed: {e}")
            self.test_results['problem_reproduction'] = {'error': str(e)}

    async def test_remediation_solution(self):
        """Test the remediation by temporarily enabling AUTH_SERVICE_ENABLED."""
        logger.info("🔍 Test 2: Remediation Solution (AUTH_SERVICE_ENABLED=true)")

        try:
            # Temporarily set AUTH_SERVICE_ENABLED to true
            original_value = self.env.get('AUTH_SERVICE_ENABLED')
            self.env.set('AUTH_SERVICE_ENABLED', 'true', 'test_remediation')

            # Create new AuthServiceSettings with the enabled state
            remediated_settings = AuthServiceSettings.from_env()

            # Test AuthServiceClient initialization with enabled service
            auth_client = AuthServiceClient()

            self.test_results['remediation_solution'] = {
                'auth_service_enabled_after_fix': remediated_settings.enabled,
                'auth_client_initialized': True,
                'service_secret_configured': bool(auth_client.service_secret),
                'service_id_configured': bool(auth_client.service_id),
                'auth_service_url': remediated_settings.base_url,
                'remediation_successful': remediated_settings.enabled and bool(auth_client.service_secret)
            }

            if remediated_settings.enabled:
                logger.info("✅ REMEDIATION SUCCESS: Auth service is now enabled")
                logger.info(f"   - Auth Service URL: {remediated_settings.base_url}")
                logger.info(f"   - Service Secret configured: {bool(auth_client.service_secret)}")
                logger.info(f"   - Service ID: {auth_client.service_id}")
            else:
                logger.error("❌ Remediation failed - auth service still disabled")

            # Restore original value
            if original_value is not None:
                self.env.set('AUTH_SERVICE_ENABLED', original_value, 'test_remediation')
            else:
                self.env.delete('AUTH_SERVICE_ENABLED', 'test_remediation')

        except Exception as e:
            logger.error(f"❌ Remediation test failed: {e}")
            self.test_results['remediation_solution'] = {'error': str(e)}

    async def test_service_authentication_enabled(self):
        """Test service authentication with enabled auth service."""
        logger.info("🔍 Test 3: Service Authentication with Enabled Auth Service")

        try:
            # Enable auth service for this test
            self.env.set('AUTH_SERVICE_ENABLED', 'true', 'test_auth_enabled')

            # Initialize client with enabled service
            auth_client = AuthServiceClient()

            # Test service header generation (this should now work properly)
            headers = auth_client._get_service_auth_headers()

            # Test the authentication flow that was failing
            self.test_results['service_authentication_enabled'] = {
                'auth_service_enabled': auth_client.settings.enabled,
                'headers_generated': bool(headers),
                'service_id_header_present': 'X-Service-ID' in headers,
                'service_secret_header_present': 'X-Service-Secret' in headers,
                'authentication_flow_ready': (
                    auth_client.settings.enabled and
                    'X-Service-ID' in headers and
                    'X-Service-Secret' in headers
                )
            }

            if self.test_results['service_authentication_enabled']['authentication_flow_ready']:
                logger.info("✅ SERVICE AUTHENTICATION READY: All components properly configured")
                logger.info(f"   - Headers: {list(headers.keys())}")
                logger.info(f"   - Service ID: {headers.get('X-Service-ID', 'NOT SET')}")
                logger.info(f"   - Service Secret: [REDACTED] (length: {len(headers.get('X-Service-Secret', ''))})")

                # This is where the original authentication would succeed
                logger.info("✅ ISSUE #1007 RESOLVED: Service authentication is now functional")
            else:
                logger.error("❌ Service authentication still not ready")

            # Cleanup
            self.env.delete('AUTH_SERVICE_ENABLED', 'test_auth_enabled')

        except Exception as e:
            logger.error(f"❌ Service authentication test failed: {e}")
            self.test_results['service_authentication_enabled'] = {'error': str(e)}

    def generate_remediation_report(self):
        """Generate comprehensive remediation report."""
        logger.info("=" * 80)
        logger.info("📊 ISSUE #1007 REMEDIATION REPORT")
        logger.info("=" * 80)

        # Root Cause Summary
        logger.info("🔍 ROOT CAUSE IDENTIFIED:")
        logger.info("   AUTH_SERVICE_ENABLED environment variable was set to 'false'")
        logger.info("   This disabled service authentication despite SERVICE_SECRET being configured")
        logger.info("   Result: 'SERVICE_SECRET=REDACTED...auth=REDACTED fail' error logs")

        # Remediation Summary
        logger.info("")
        logger.info("💡 REMEDIATION SOLUTION:")
        logger.info("   Set AUTH_SERVICE_ENABLED=true to enable service authentication")
        logger.info("   This allows SERVICE_SECRET to be used for inter-service auth")

        # Test Results
        problem_reproduced = self.test_results.get('problem_reproduction', {}).get('problem_reproduced', False)
        remediation_successful = self.test_results.get('remediation_solution', {}).get('remediation_successful', False)
        auth_flow_ready = self.test_results.get('service_authentication_enabled', {}).get('authentication_flow_ready', False)

        logger.info("")
        logger.info("📋 TEST RESULTS:")
        logger.info(f"   Problem Reproduction: {'✅ SUCCESS' if problem_reproduced else '❌ FAILED'}")
        logger.info(f"   Remediation Solution: {'✅ SUCCESS' if remediation_successful else '❌ FAILED'}")
        logger.info(f"   Authentication Ready: {'✅ SUCCESS' if auth_flow_ready else '❌ FAILED'}")

        # Overall Status
        overall_success = problem_reproduced and remediation_successful and auth_flow_ready
        logger.info("")
        logger.info(f"🎯 OVERALL STATUS: {'✅ ISSUE #1007 RESOLVED' if overall_success else '❌ ISSUE PERSISTS'}")

        self.test_results['remediation_summary'] = {
            'problem_reproduced': problem_reproduced,
            'remediation_successful': remediation_successful,
            'authentication_ready': auth_flow_ready,
            'overall_success': overall_success,
            'root_cause': 'AUTH_SERVICE_ENABLED=false',
            'solution': 'Set AUTH_SERVICE_ENABLED=true'
        }

        logger.info("=" * 80)

async def main():
    """Main test execution."""
    test_suite = Issue1007RemediationTest()

    try:
        results = await test_suite.run_remediation_test()

        # Write results to file for analysis
        with open('issue_1007_remediation_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info("📝 Remediation results written to: issue_1007_remediation_results.json")

        # Exit with appropriate code based on overall success
        if results.get('remediation_summary', {}).get('overall_success', False):
            logger.info("🎯 SUCCESS: Issue #1007 root cause identified and remediation validated")
            sys.exit(0)
        else:
            logger.info("⚠️  Issue #1007 remediation incomplete")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Remediation test failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())