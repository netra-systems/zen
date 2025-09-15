#!/usr/bin/env python3
"""
WebSocket Subprotocol Negotiation Fixes Validation Script

This script validates the fixes applied to resolve WebSocket subprotocol
negotiation failures in staging GCP environment.

Usage:
    python validate_websocket_subprotocol_fixes.py
"""

import asyncio
import json
import sys
from typing import Dict, List, Optional
import httpx
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_subprotocol_negotiation():
    """Test the subprotocol negotiation logic with fixed formats."""
    print("\n=== Testing WebSocket Subprotocol Negotiation ===")

    try:
        from netra_backend.app.websocket_core.unified_jwt_protocol_handler import negotiate_websocket_subprotocol

        # Test cases that should work in staging after the fixes
        test_cases = [
            # Case 1: Single jwt-auth protocol
            (['jwt-auth'], 'jwt-auth'),

            # Case 2: E2E testing with jwt-auth
            (['e2e-testing', 'jwt-auth'], 'e2e-testing'),

            # Case 3: JWT token protocol (new format)
            (['jwt.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'], 'jwt.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'),

            # Case 4: Mixed protocols with token
            (['jwt-auth', 'jwt.test_token_123'], 'jwt.test_token_123'),

            # Case 5: E2E testing only
            (['e2e-testing'], 'e2e-testing'),
        ]

        all_passed = True
        for i, (client_protocols, expected) in enumerate(test_cases, 1):
            try:
                result = negotiate_websocket_subprotocol(client_protocols)
                if result == expected:
                    print(f"✅ Test {i}: {client_protocols} -> {result} (PASS)")
                else:
                    print(f"❌ Test {i}: {client_protocols} -> {result}, expected {expected} (FAIL)")
                    all_passed = False
            except Exception as e:
                print(f"❌ Test {i}: {client_protocols} -> ERROR: {e} (FAIL)")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"❌ Failed to import subprotocol negotiation: {e}")
        return False


async def test_staging_config_updates():
    """Test the staging configuration updates."""
    print("\n=== Testing Staging Configuration Updates ===")

    try:
        from tests.e2e.staging_test_config import StagingConfig, get_staging_config

        config = get_staging_config()

        # Check auth URL update
        expected_auth_url = "https://auth.staging.netrasystems.ai"
        if config.auth_url == expected_auth_url:
            print(f"✅ Auth URL updated correctly: {config.auth_url}")
        else:
            print(f"❌ Auth URL not updated: {config.auth_url}, expected {expected_auth_url}")
            return False

        # Test JWT token creation
        print("Testing JWT token creation for staging...")
        token = config.create_test_jwt_token()

        if token:
            print(f"✅ JWT token created successfully (length: {len(token)})")
        else:
            print("❌ JWT token creation failed")
            return False

        # Test WebSocket headers generation
        print("Testing WebSocket headers generation...")
        headers = config.get_websocket_headers(token)

        # Check for critical headers
        required_headers = ["Authorization", "sec-websocket-protocol", "X-Test-Type", "X-E2E-Test"]
        missing_headers = []
        for header in required_headers:
            if header not in headers:
                missing_headers.append(header)

        if not missing_headers:
            print(f"✅ All required headers present: {list(headers.keys())}")
        else:
            print(f"❌ Missing required headers: {missing_headers}")
            return False

        # Check subprotocol format (should NOT contain comma-separated values)
        subprotocol = headers.get("sec-websocket-protocol", "")
        if subprotocol and "e2e-testing, jwt-auth" not in subprotocol:
            print(f"✅ Subprotocol format is correct: {subprotocol}")
        else:
            print(f"❌ Subprotocol format still incorrect: {subprotocol}")
            return False

        return True

    except Exception as e:
        print(f"❌ Failed to test staging config: {e}")
        return False


async def test_auth_service_connectivity():
    """Test connectivity to the updated auth service."""
    print("\n=== Testing Auth Service Connectivity ===")

    auth_urls = [
        "https://auth.staging.netrasystems.ai/health",
        "https://auth.staging.netrasystems.ai",
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in auth_urls:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✅ Auth service accessible: {url} -> HTTP {response.status_code}")
                    return True
                else:
                    print(f"⚠️  Auth service responded but not OK: {url} -> HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ Auth service connection failed: {url} -> {e}")

    print("❌ Auth service not accessible at any tested URL")
    return False


async def test_websocket_url_format():
    """Test WebSocket URL format for staging."""
    print("\n=== Testing WebSocket URL Format ===")

    try:
        from tests.e2e.staging_test_config import StagingConfig

        config = StagingConfig()
        websocket_url = config.websocket_url

        expected_format = "wss://api.staging.netrasystems.ai/api/v1/websocket"
        if websocket_url == expected_format:
            print(f"✅ WebSocket URL format correct: {websocket_url}")
            return True
        else:
            print(f"❌ WebSocket URL format incorrect: {websocket_url}, expected {expected_format}")
            return False

    except Exception as e:
        print(f"❌ Failed to test WebSocket URL: {e}")
        return False


async def run_validation_tests():
    """Run all validation tests."""
    print("🚀 Starting WebSocket Subprotocol Fixes Validation")
    print("=" * 60)

    test_results = []

    # Test 1: Subprotocol negotiation logic
    result1 = await test_subprotocol_negotiation()
    test_results.append(("Subprotocol Negotiation", result1))

    # Test 2: Staging config updates
    result2 = await test_staging_config_updates()
    test_results.append(("Staging Configuration", result2))

    # Test 3: Auth service connectivity
    result3 = await test_auth_service_connectivity()
    test_results.append(("Auth Service Connectivity", result3))

    # Test 4: WebSocket URL format
    result4 = await test_websocket_url_format()
    test_results.append(("WebSocket URL Format", result4))

    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL VALIDATION TESTS PASSED! 🎉")
        print("The WebSocket subprotocol fixes are ready for deployment.")
        return True
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("Please address the failing tests before deployment.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_validation_tests())
    sys.exit(0 if success else 1)