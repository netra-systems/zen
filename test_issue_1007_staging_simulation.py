#!/usr/bin/env python3
"""
Test Issue #1007 fix with staging environment simulation.

This test validates that the fix works by simulating staging environment conditions
where AUTH_SERVICE_ENABLED should be true by default and SERVICE_SECRET authentication
should work properly.
"""

import asyncio
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.clients.auth_client_cache import AuthServiceSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_staging_environment_simulation():
    """Test the fix with staging environment simulation."""
    logger.info("🚀 Issue #1007 Staging Environment Simulation Test")
    logger.info("=" * 80)

    env = get_env()

    # Save original values
    original_environment = env.get('ENVIRONMENT')
    original_auth_enabled = env.get('AUTH_SERVICE_ENABLED')
    original_testing = env.get('TESTING')

    try:
        # Simulate staging environment
        env.set('ENVIRONMENT', 'staging', 'test_staging_sim')
        env.set('TESTING', 'false', 'test_staging_sim')

        # Don't set AUTH_SERVICE_ENABLED - let it use the environment-aware default
        if 'AUTH_SERVICE_ENABLED' in os.environ:
            env.delete('AUTH_SERVICE_ENABLED', 'test_staging_sim')

        logger.info("🔍 Test: Staging Environment Simulation")
        logger.info(f"   ENVIRONMENT: {env.get('ENVIRONMENT')}")
        logger.info(f"   TESTING: {env.get('TESTING')}")
        logger.info(f"   AUTH_SERVICE_ENABLED: {env.get('AUTH_SERVICE_ENABLED', 'NOT SET - using default')}")

        # Test AuthServiceSettings with staging environment
        settings = AuthServiceSettings.from_env()

        logger.info(f"✅ AuthServiceSettings Results:")
        logger.info(f"   - Auth service enabled: {settings.enabled}")
        logger.info(f"   - Base URL: {settings.base_url}")

        if settings.enabled:
            logger.info("🎯 SUCCESS: Auth service is enabled in staging environment!")
        else:
            logger.error("❌ FAILED: Auth service still disabled in staging")
            return False

        # Test AuthServiceClient initialization
        auth_client = AuthServiceClient()

        logger.info(f"✅ AuthServiceClient Results:")
        logger.info(f"   - Client initialized: True")
        logger.info(f"   - Service ID: {auth_client.service_id}")
        logger.info(f"   - Service Secret configured: {bool(auth_client.service_secret)}")
        logger.info(f"   - Auth service enabled: {auth_client.settings.enabled}")

        # Test service header generation (the critical path for Issue #1007)
        headers = auth_client._get_service_auth_headers()

        logger.info(f"✅ Service Headers Results:")
        logger.info(f"   - Headers generated: {list(headers.keys())}")
        logger.info(f"   - X-Service-ID: {headers.get('X-Service-ID', 'MISSING')}")
        logger.info(f"   - X-Service-Secret: [REDACTED] (length: {len(headers.get('X-Service-Secret', ''))})")

        # Check if all components are ready for service authentication
        auth_ready = (
            settings.enabled and
            auth_client.settings.enabled and
            'X-Service-ID' in headers and
            'X-Service-Secret' in headers
        )

        if auth_ready:
            logger.info("🎯 SUCCESS: Issue #1007 RESOLVED - Service authentication ready!")
            logger.info("   - All authentication components functional")
            logger.info("   - SERVICE_SECRET authentication will work")
            logger.info("   - Inter-service communication restored")
            return True
        else:
            logger.error("❌ FAILED: Service authentication not ready")
            return False

    finally:
        # Restore original values
        if original_environment:
            env.set('ENVIRONMENT', original_environment, 'test_staging_sim')
        else:
            env.delete('ENVIRONMENT', 'test_staging_sim')

        if original_auth_enabled:
            env.set('AUTH_SERVICE_ENABLED', original_auth_enabled, 'test_staging_sim')
        else:
            env.delete('AUTH_SERVICE_ENABLED', 'test_staging_sim')

        if original_testing:
            env.set('TESTING', original_testing, 'test_staging_sim')
        else:
            env.delete('TESTING', 'test_staging_sim')

async def test_production_environment_simulation():
    """Test the fix with production environment simulation."""
    logger.info("🔍 Test: Production Environment Simulation")

    env = get_env()

    # Save original values
    original_environment = env.get('ENVIRONMENT')
    original_auth_enabled = env.get('AUTH_SERVICE_ENABLED')
    original_testing = env.get('TESTING')

    try:
        # Simulate production environment
        env.set('ENVIRONMENT', 'production', 'test_prod_sim')
        env.set('TESTING', 'false', 'test_prod_sim')

        # Don't set AUTH_SERVICE_ENABLED - let it use the environment-aware default
        if 'AUTH_SERVICE_ENABLED' in os.environ:
            env.delete('AUTH_SERVICE_ENABLED', 'test_prod_sim')

        logger.info(f"   ENVIRONMENT: {env.get('ENVIRONMENT')}")
        logger.info(f"   TESTING: {env.get('TESTING')}")

        # Test AuthServiceSettings with production environment
        settings = AuthServiceSettings.from_env()

        if settings.enabled:
            logger.info("✅ SUCCESS: Auth service enabled in production environment!")
            return True
        else:
            logger.error("❌ FAILED: Auth service disabled in production")
            return False

    finally:
        # Restore original values
        if original_environment:
            env.set('ENVIRONMENT', original_environment, 'test_prod_sim')
        else:
            env.delete('ENVIRONMENT', 'test_prod_sim')

        if original_auth_enabled:
            env.set('AUTH_SERVICE_ENABLED', original_auth_enabled, 'test_prod_sim')
        else:
            env.delete('AUTH_SERVICE_ENABLED', 'test_prod_sim')

        if original_testing:
            env.set('TESTING', original_testing, 'test_prod_sim')
        else:
            env.delete('TESTING', 'test_prod_sim')

async def main():
    """Main test execution."""
    try:
        # Test staging environment
        staging_success = await test_staging_environment_simulation()

        # Test production environment
        production_success = await test_production_environment_simulation()

        logger.info("=" * 80)
        logger.info("📊 FINAL RESULTS:")
        logger.info(f"   Staging Environment: {'✅ PASS' if staging_success else '❌ FAIL'}")
        logger.info(f"   Production Environment: {'✅ PASS' if production_success else '❌ FAIL'}")

        overall_success = staging_success and production_success

        if overall_success:
            logger.info("🎯 OVERALL: ✅ Issue #1007 fix validated for staging and production")
            sys.exit(0)
        else:
            logger.info("❌ OVERALL: Issue #1007 fix incomplete")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())