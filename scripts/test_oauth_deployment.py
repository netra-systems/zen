#!/usr/bin/env python3
"""
Script to test OAuth flow after deployment.
Run this after deploying to staging to ensure OAuth is working correctly.
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.deployment.test_oauth_staging_flow import OAuthStagingTester


async def main():
    """Run OAuth deployment tests"""
    print("\n🔍 Running OAuth Deployment Tests...")
    
    # Check if we're in staging environment
    env = os.getenv('ENVIRONMENT', 'development')
    if env not in ['staging', 'production']:
        print(f"⚠️  Warning: Running in {env} environment")
        print("These tests are designed for staging/production")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted")
            return 1
    
    # Run the tests
    tester = OAuthStagingTester()
    success = await tester.run_all_tests()
    
    if not success:
        print("\n📋 Troubleshooting Guide:")
        print("-" * 40)
        print("1. Check auth service logs:")
        print("   gcloud run logs read auth-service --project=vps-ai-404804")
        print("\n2. Verify secrets are set:")
        print("   - GOOGLE_OAUTH_CLIENT_ID_STAGING")
        print("   - GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
        print("   - JWT_SECRET_KEY")
        print("\n3. Check OAuth console configuration:")
        print("   - Redirect URI: https://auth.staging.netrasystems.ai/auth/callback")
        print("   - JavaScript origins: https://app.staging.netrasystems.ai")
        print("\n4. Test auth service directly:")
        print("   curl https://auth.staging.netrasystems.ai/auth/health")
        print("   curl https://auth.staging.netrasystems.ai/auth/config")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)