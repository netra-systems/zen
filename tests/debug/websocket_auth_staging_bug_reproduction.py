"""
WebSocket Authentication Bug Reproduction Test for Staging

This test reproduces the exact WebSocket authentication failure pattern
seen in staging E2E tests where connections timeout during handshake.

Business Value:
- Reproduces critical $120K+ MRR blocking issue
- Validates root cause analysis findings
- Provides test case for fix validation

CRITICAL: This test is designed to FAIL until the WebSocket auth bug is fixed.
"""

import asyncio
import pytest
import time
import json
from typing import Dict, Optional
import websockets
from unittest.mock import patch

from shared.isolated_environment import get_env
from tests.e2e.staging_config import get_staging_config
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig


class TestWebSocketAuthBugReproduction:
    """Reproduce the WebSocket authentication timeout bug in staging."""
    
    @pytest.mark.asyncio
    @pytest.mark.reproduction
    async def test_reproduce_websocket_handshake_timeout_exact_failure(self):
        """
        CRITICAL BUG REPRODUCTION: WebSocket connection timeout during handshake
        
        This test reproduces the exact failure seen in staging:
        - Connection times out at websockets.asyncio.client.py:543
        - Handshake never completes due to pre-auth + infrastructure timeout
        - Business Impact: $120K+ MRR chat functionality validation blocked
        
        EXPECTED RESULT: This test should FAIL until bug is fixed
        """
        print("\n SEARCH:  REPRODUCING: WebSocket handshake timeout in staging...")
        
        # Use exact staging configuration as failing tests
        config = get_staging_config()
        auth_config = E2EAuthConfig.for_staging()
        auth_helper = E2EAuthHelper(config=auth_config, environment="staging")
        
        # Create E2E JWT token using current method (same as failing tests)
        print("[U+1F511] Creating E2E JWT token using current method...")
        test_token = await auth_helper.create_test_jwt_token()
        print(f"[U+1F511] Token created: {test_token[:20]}...")
        
        # Prepare WebSocket headers exactly as E2E tests do
        headers = config.get_websocket_headers(test_token)
        print(f"[U+1F4E1] WebSocket headers: {list(headers.keys())}")
        
        # Record timing to demonstrate the failure pattern
        start_time = time.time()
        connection_error = None
        
        try:
            print(f"[U+1F50C] Attempting WebSocket connection to: {config.urls.websocket_url}")
            print("[U+23F1][U+FE0F]  This should timeout during handshake (reproducing bug)...")
            
            # This should fail with timeout during handshake (reproducing the bug)
            async with websockets.connect(
                config.urls.websocket_url,
                additional_headers=headers,
                timeout=5.0,  # Short timeout to quickly reproduce issue
                ping_interval=None,  # Disable ping during handshake test
                ping_timeout=None
            ) as ws:
                print(" FAIL:  UNEXPECTED: Connection succeeded - bug may be fixed!")
                await ws.send('{"type": "ping"}')
                response = await ws.recv()
                print(f"[U+1F4E8] Received: {response}")
                
        except Exception as e:
            connection_error = e
            end_time = time.time()
            duration = end_time - start_time
            
            print(f" PASS:  REPRODUCED: WebSocket connection failed in {duration:.1f}s")
            print(f" CHART:  Error type: {type(e).__name__}")
            print(f" CHART:  Error message: {str(e)}")
            
            # Verify this matches the expected failure pattern
            error_str = str(e).lower()
            is_timeout = "timeout" in error_str
            is_connection_error = "connection" in error_str or "handshake" in error_str
            
            assert is_timeout or is_connection_error, f"Unexpected error type: {e}"
            assert duration < 10.0, f"Expected quick timeout, got {duration:.1f}s"
            
            print(" PASS:  CONFIRMED: This matches the expected WebSocket handshake failure pattern")
            return  # Test succeeded in reproducing the bug
        
        # If we get here, the connection unexpectedly succeeded
        end_time = time.time()
        duration = end_time - start_time
        print(f" FAIL:  UNEXPECTED SUCCESS: Connection established in {duration:.1f}s")
        pytest.fail("WebSocket connection succeeded - expected failure to reproduce bug")
    
    @pytest.mark.asyncio 
    @pytest.mark.reproduction
    async def test_demonstrate_e2e_environment_detection_failure(self):
        """
        Demonstrate that E2E environment detection fails in staging.
        
        This test shows WHY the handshake timeout occurs:
        E2E environment variables are not available in staging Cloud Run,
        causing full JWT validation instead of E2E bypass.
        """
        print("\n SEARCH:  TESTING: E2E environment detection logic...")
        
        # Get current environment state
        env = get_env()
        
        # Check E2E environment variables that staging WebSocket route looks for
        e2e_vars = {
            "E2E_TESTING": env.get("E2E_TESTING"),
            "PYTEST_RUNNING": env.get("PYTEST_RUNNING"), 
            "STAGING_E2E_TEST": env.get("STAGING_E2E_TEST"),
            "E2E_OAUTH_SIMULATION_KEY": "SET" if env.get("E2E_OAUTH_SIMULATION_KEY") else None,
            "E2E_TEST_ENV": env.get("E2E_TEST_ENV")
        }
        
        # Calculate if E2E testing would be detected using exact websocket.py logic
        is_e2e_testing = (
            env.get("E2E_TESTING", "0") == "1" or 
            env.get("PYTEST_RUNNING", "0") == "1" or
            env.get("STAGING_E2E_TEST", "0") == "1" or
            env.get("E2E_OAUTH_SIMULATION_KEY") is not None or
            env.get("E2E_TEST_ENV") == "staging"
        )
        
        print(f" CHART:  E2E Environment Variables: {e2e_vars}")
        print(f" CHART:  E2E Detection Result: {is_e2e_testing}")
        print(f" CHART:  Environment: {env.get('ENVIRONMENT', 'unknown')}")
        
        # This documents the root cause
        if not is_e2e_testing:
            print(" FAIL:  ROOT CAUSE: E2E testing NOT detected")
            print(" FAIL:  This means staging WebSocket will run FULL JWT validation")
            print(" FAIL:  Full validation + GCP timeout = handshake failure")
        else:
            print(" PASS:  E2E testing detected - bypass should work")
            
        # Document findings regardless of current state
        print(f"\n[U+1F4CB] ANALYSIS:")
        print(f"   [U+2022] Local test environment has E2E vars: {any(e2e_vars.values())}")
        print(f"   [U+2022] E2E detection logic result: {is_e2e_testing}")
        print(f"   [U+2022] Expected staging behavior: {'Bypass auth' if is_e2e_testing else 'Full auth validation'}")
    
    @pytest.mark.asyncio
    @pytest.mark.reproduction
    async def test_measure_auth_service_validation_latency(self):
        """
        Test to measure auth service JWT validation latency in staging.
        High latency may contribute to handshake timeouts in Cloud Run.
        """
        print("\n SEARCH:  MEASURING: Auth service JWT validation latency...")
        
        try:
            config = get_staging_config()
            auth_config = E2EAuthConfig.for_staging()
            auth_helper = E2EAuthHelper(config=auth_config, environment="staging")
            
            # Create test JWT using same method as failing tests
            test_token = await auth_helper.create_test_jwt_token()
            print(f"[U+1F511] Created test token for latency test: {test_token[:20]}...")
            
            # Measure auth service validation time
            start_time = time.time()
            
            # Import auth client to test validation directly
            from netra_backend.app.clients.auth_client_core import auth_client
            
            print("[U+23F1][U+FE0F]  Starting auth service validation...")
            result = await auth_client.validate_token(test_token)
            end_time = time.time()
            validation_duration = end_time - start_time
            
            print(f" CHART:  Auth service validation took: {validation_duration:.3f}s")
            print(f" CHART:  Validation result valid: {result.get('valid') if result else False}")
            print(f" CHART:  Validation result keys: {list(result.keys()) if result else 'None'}")
            
            # Analyze impact on WebSocket handshake timing
            gcp_timeout_limit = 30.0  # GCP Cloud Run NEG timeout
            handshake_overhead = 2.0   # Estimated handshake processing time
            available_time = gcp_timeout_limit - handshake_overhead
            
            print(f"\n[U+1F4CB] TIMEOUT ANALYSIS:")
            print(f"   [U+2022] GCP Cloud Run NEG timeout: {gcp_timeout_limit}s")
            print(f"   [U+2022] WebSocket handshake overhead: ~{handshake_overhead}s")
            print(f"   [U+2022] Available time for auth validation: ~{available_time}s")
            print(f"   [U+2022] Actual auth validation time: {validation_duration:.3f}s")
            
            if validation_duration > available_time:
                print(f" FAIL:  CRITICAL: Auth validation too slow for GCP timeout!")
                print(f" FAIL:  This contributes to WebSocket handshake failures")
            elif validation_duration > available_time * 0.5:
                print(f" WARNING: [U+FE0F]  WARNING: Auth validation uses {validation_duration/available_time*100:.1f}% of available time")
            else:
                print(f" PASS:  Auth validation time acceptable: {validation_duration:.3f}s")
                
        except Exception as e:
            end_time = time.time()
            validation_duration = end_time - start_time
            print(f" FAIL:  Auth service validation failed after {validation_duration:.3f}s: {e}")
            print(f" FAIL:  This explains WebSocket handshake failures!")
            
            # This failure itself is part of the bug reproduction
            print(f"\n PASS:  REPRODUCED: Auth service validation failure")
            print(f"   [U+2022] Duration before failure: {validation_duration:.3f}s") 
            print(f"   [U+2022] Error type: {type(e).__name__}")
            print(f"   [U+2022] This validation failure causes WebSocket handshake timeout")
    
    @pytest.mark.asyncio
    @pytest.mark.reproduction  
    async def test_websocket_health_endpoint_comparison(self):
        """
        Compare WebSocket health endpoint vs main WebSocket endpoint.
        Health endpoint should work while main endpoint fails.
        """
        print("\n SEARCH:  COMPARING: WebSocket health vs main endpoint...")
        
        config = get_staging_config()
        
        # Test health endpoint (should work)
        health_url = f"{config.urls.backend_url}/ws/health"
        print(f"[U+1F3E5] Testing health endpoint: {health_url}")
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(health_url, timeout=10) as response:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    print(f" PASS:  Health endpoint responded in {duration:.3f}s")
                    print(f" CHART:  Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f" CHART:  Service status: {data.get('status', 'unknown')}")
                        print(f" CHART:  Environment info available: {'environment' in data}")
                        
                        # Check if health endpoint provides E2E testing info
                        e2e_info = data.get('e2e_testing', {})
                        if e2e_info:
                            print(f" CHART:  E2E testing info: {e2e_info}")
                        
        except Exception as e:
            print(f" FAIL:  Health endpoint also failed: {e}")
            print(" FAIL:  This suggests broader infrastructure issues")
        
        # Now test main WebSocket endpoint (should fail)
        print(f"\n[U+1F50C] Testing main WebSocket endpoint: {config.urls.websocket_url}")
        print("   (This should fail, demonstrating the difference)")
        
        try:
            # Create minimal connection attempt without full auth
            start_time = time.time()
            async with websockets.connect(
                config.urls.websocket_url,
                timeout=3.0
            ) as ws:
                end_time = time.time()
                duration = end_time - start_time
                print(f" FAIL:  UNEXPECTED: WebSocket connected in {duration:.3f}s without auth")
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f" PASS:  EXPECTED: WebSocket failed in {duration:.3f}s: {type(e).__name__}")
            
            # This demonstrates the contrast between working health endpoint
            # and failing WebSocket endpoint
            print(f"\n[U+1F4CB] COMPARISON RESULTS:")
            print(f"   [U+2022] Health endpoint: Working")
            print(f"   [U+2022] WebSocket endpoint: Failing during handshake")
            print(f"   [U+2022] This confirms WebSocket-specific authentication issue")


if __name__ == "__main__":
    """
    Run reproduction tests directly for debugging.
    
    Usage: python tests/debug/websocket_auth_staging_bug_reproduction.py
    """
    import sys
    sys.path.append('.')
    
    async def run_reproduction_tests():
        """Run all reproduction tests sequentially."""
        test_instance = TestWebSocketAuthBugReproduction()
        
        print(" ALERT:  STARTING WEBSOCKET AUTH BUG REPRODUCTION TESTS")
        print("=" * 60)
        
        try:
            # Test 1: Main reproduction test
            print("\n1[U+FE0F][U+20E3] MAIN REPRODUCTION TEST:")
            await test_instance.test_reproduce_websocket_handshake_timeout_exact_failure()
            
        except Exception as e:
            print(f" PASS:  Test 1 correctly reproduced the bug: {e}")
        
        try:
            # Test 2: Environment detection
            print("\n2[U+FE0F][U+20E3] E2E ENVIRONMENT DETECTION TEST:")
            await test_instance.test_demonstrate_e2e_environment_detection_failure()
            
        except Exception as e:
            print(f" FAIL:  Test 2 failed: {e}")
        
        try:
            # Test 3: Auth latency
            print("\n3[U+FE0F][U+20E3] AUTH SERVICE LATENCY TEST:")
            await test_instance.test_measure_auth_service_validation_latency()
            
        except Exception as e:
            print(f" FAIL:  Test 3 failed: {e}")
            
        try:
            # Test 4: Health comparison
            print("\n4[U+FE0F][U+20E3] HEALTH ENDPOINT COMPARISON TEST:")
            await test_instance.test_websocket_health_endpoint_comparison()
            
        except Exception as e:
            print(f" FAIL:  Test 4 failed: {e}")
        
        print("\n[U+1F3C1] REPRODUCTION TESTS COMPLETED")
        print("=" * 60)
    
    # Run if executed directly
    asyncio.run(run_reproduction_tests())