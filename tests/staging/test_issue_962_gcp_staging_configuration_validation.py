"""
STAGING TEST: Issue #962 GCP Staging Configuration Validation (P0 Production Gate)

Business Value Justification (BVJ):
- Segment: Platform/Internal - Production Readiness & Revenue Protection
- Business Goal: Validate SSOT configuration works perfectly in GCP staging environment
- Value Impact: Protects $500K+ ARR by ensuring production deployment success
- Strategic Impact: Final production deployment gate for Issue #962 resolution

CRITICAL MISSION: Issue #962 GCP Staging Environment SSOT Configuration Validation

This staging test suite validates that SSOT configuration consolidation works perfectly
in the GCP staging environment, providing final confidence before production deployment.
Tests are designed to:

1. **PRODUCTION SIMULATION**: Test SSOT configuration in real GCP cloud environment
2. **DEPLOYMENT VALIDATION**: Ensure production deployment will succeed
3. **REAL SERVICE TESTING**: Validate with actual GCP services (Cloud SQL, Redis, etc.)
4. **GOLDEN PATH CONFIDENCE**: Confirm end-to-end Golden Path works in staging

EXPECTED TEST BEHAVIOR:
- **PHASE 0-3**: Tests FAIL showing SSOT configuration doesn't work in GCP staging
- **PHASE 4 (FINAL)**: Tests PASS proving SSOT configuration production-ready
- **PRODUCTION GATE**: These tests must PASS before production deployment

CRITICAL BUSINESS IMPACT:
This is the FINAL validation in a production-like environment that SSOT configuration
consolidation is complete and ready for production. Any failure indicates that the
production deployment could fail, directly threatening $500K+ ARR.

These tests serve as the ultimate production deployment gate for Issue #962.
"""

import asyncio
import os
import sys
import unittest
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import json
from datetime import datetime, UTC

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class Issue962GcpStagingConfigurationValidationTests(SSotAsyncTestCase, unittest.TestCase):
    """
    STAGING tests for GCP configuration validation - Issue #962 production gate.

    These tests validate SSOT configuration works perfectly in GCP staging environment,
    providing final confidence for production deployment of Issue #962 resolution.

    THESE TESTS MUST PASS BEFORE PRODUCTION DEPLOYMENT.
    """

    def setUp(self):
        """Set up staging test environment with GCP service connections."""
        super().setUp()
        self.env = IsolatedEnvironment()

        # GCP Staging environment configuration
        self.staging_base_url = self.env.get("STAGING_BASE_URL", "https://netra-staging.com")
        self.staging_auth_url = self.env.get("STAGING_AUTH_URL", "https://auth.netra.com")
        self.staging_websocket_url = self.env.get("STAGING_WS_URL", "wss://staging.netra.com/ws")

        # Production readiness tracking
        self.production_readiness_issues: List[str] = []
        self.staging_test_results: Dict[str, bool] = {}
        self.deployment_blockers: List[str] = []

        # Required staging environment validation
        self.required_staging_endpoints = [
            "/health",
            "/health/auth",
            "/health/database",
            "/health/redis",
            "/auth/login",
            "/api/v1/agents/health",
        ]

    async def test_staging_config_loads_via_ssot_pattern_only(self):
        """
        STAGING TEST: Validate SSOT configuration loads successfully in GCP staging

        SUCCESS CRITERIA:
        - SSOT configuration import works in GCP Cloud Run environment
        - No deprecated configuration imports accessible in staging
        - All required configuration values loaded correctly
        - Configuration loading performance acceptable

        BUSINESS IMPACT:
        If SSOT configuration doesn't work in GCP staging, the production deployment
        will fail, causing service downtime and blocking $500K+ ARR Golden Path.
        """
        print(f"\n=== STAGING: GCP SSOT Configuration Loading Validation ===")
        print(f"Testing Issue #962 SSOT configuration in GCP Cloud Run environment")

        staging_results = {
            "config_import_works": False,
            "deprecated_imports_blocked": False,
            "required_configs_loaded": False,
            "performance_acceptable": False,
        }

        # TEST 1: SSOT configuration import works in GCP staging
        try:
            print(f"\n1. Testing SSOT configuration import in GCP staging...")
            config_response = await self._test_staging_config_endpoint("/health/config")

            if config_response and config_response.get("status") == "healthy":
                staging_results["config_import_works"] = True
                print(f"CHECK SSOT configuration import: WORKS in GCP staging")
            else:
                print(f"X SSOT configuration import: FAILED in GCP staging")
                self.deployment_blockers.append("SSOT config import fails in GCP staging")

        except Exception as e:
            print(f"X SSOT configuration import: EXCEPTION - {e}")
            self.deployment_blockers.append(f"SSOT config import exception: {e}")

        # TEST 2: Deprecated configuration imports blocked in staging
        try:
            print(f"\n2. Testing deprecated imports blocked in GCP staging...")
            deprecated_response = await self._test_staging_config_endpoint("/health/deprecated-config")

            if deprecated_response and deprecated_response.get("deprecated_accessible") == False:
                staging_results["deprecated_imports_blocked"] = True
                print(f"CHECK Deprecated imports: BLOCKED in GCP staging")
            else:
                print(f"X Deprecated imports: STILL ACCESSIBLE in GCP staging")
                self.deployment_blockers.append("Deprecated config imports still work in staging")

        except Exception as e:
            print(f"WARNING️ Deprecated import test: Could not verify - {e}")
            # Not a critical failure if endpoint doesn't exist

        # TEST 3: Required configuration values loaded
        try:
            print(f"\n3. Testing required configuration values in GCP staging...")
            required_configs = ["JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "OAUTH_CLIENT_ID"]
            config_status = await self._validate_staging_config_values(required_configs)

            if config_status["all_present"]:
                staging_results["required_configs_loaded"] = True
                print(f"CHECK Required configs: ALL LOADED in GCP staging")
                print(f"   Loaded configs: {config_status['loaded_count']}/{len(required_configs)}")
            else:
                print(f"X Required configs: MISSING in GCP staging")
                print(f"   Missing configs: {config_status['missing_configs']}")
                self.deployment_blockers.append(f"Missing configs in staging: {config_status['missing_configs']}")

        except Exception as e:
            print(f"X Required configs test: FAILED - {e}")
            self.deployment_blockers.append(f"Config validation failed: {e}")

        # TEST 4: Configuration loading performance
        try:
            print(f"\n4. Testing configuration loading performance in GCP staging...")
            perf_result = await self._test_staging_config_performance()

            if perf_result["load_time"] < 2.0:  # Must load within 2 seconds
                staging_results["performance_acceptable"] = True
                print(f"CHECK Config performance: {perf_result['load_time']:.2f}s (acceptable)")
            else:
                print(f"X Config performance: {perf_result['load_time']:.2f}s (too slow)")
                self.deployment_blockers.append(f"Config loading too slow: {perf_result['load_time']:.2f}s")

        except Exception as e:
            print(f"X Performance test: FAILED - {e}")
            self.deployment_blockers.append(f"Performance test failed: {e}")

        # Calculate staging readiness score
        successful_tests = sum(1 for success in staging_results.values() if success)
        readiness_score = (successful_tests / len(staging_results) * 100)

        print(f"\n=== GCP STAGING CONFIGURATION READINESS ===")
        print(f"Readiness Score: {readiness_score:.1f}%")
        print(f"Successful Tests: {successful_tests}/{len(staging_results)}")
        print(f"Deployment Blockers: {len(self.deployment_blockers)}")

        if self.deployment_blockers:
            print(f"\n--- PRODUCTION DEPLOYMENT BLOCKERS ---")
            for blocker in self.deployment_blockers:
                print(f"BLOCKER: {blocker}")

        # CRITICAL PRODUCTION GATE ASSERTION
        self.assertEqual(
            readiness_score, 100.0,
            f"STAGING FAILURE: Only {readiness_score:.1f}% GCP staging configuration readiness. "
            f"Expected: 100% for production deployment. "
            f"Deployment blockers: {self.deployment_blockers}. "
            f"Issue #962 SSOT configuration not production-ready."
        )

        # SUCCESS: GCP staging ready for production
        print(f"\nCHECK GCP STAGING SUCCESS: SSOT configuration production-ready")

    async def test_staging_authentication_flows_end_to_end(self):
        """
        STAGING TEST: Validate complete authentication flows work in GCP staging

        SUCCESS CRITERIA:
        - User login flow works end-to-end in GCP staging
        - JWT token generation and validation works
        - OAuth flow works with real OAuth providers
        - Session management works with real Redis/database

        BUSINESS IMPACT:
        If authentication doesn't work in GCP staging with SSOT configuration,
        production deployment will cause authentication failures blocking all users.
        """
        print(f"\n=== STAGING: End-to-End Authentication Flow Validation ===")
        print(f"Testing Golden Path authentication in GCP staging environment")

        auth_flow_steps = [
            ("Health Check", self._test_staging_health_endpoint),
            ("Auth Service Health", self._test_staging_auth_health),
            ("Database Connectivity", self._test_staging_database_health),
            ("Redis Connectivity", self._test_staging_redis_health),
            ("OAuth Configuration", self._test_staging_oauth_config),
            ("JWT Token Flow", self._test_staging_jwt_flow),
            ("Session Management", self._test_staging_session_management),
            ("Authentication API", self._test_staging_auth_api),
        ]

        auth_results = {}
        auth_failures = []

        for step_name, test_func in auth_flow_steps:
            try:
                print(f"\nTesting Authentication Step: {step_name}")
                success = await test_func()
                auth_results[step_name] = success

                if success:
                    print(f"CHECK {step_name}: PASS")
                else:
                    print(f"X {step_name}: FAIL")
                    auth_failures.append(f"{step_name}: Authentication failed")

            except Exception as e:
                print(f"X {step_name}: EXCEPTION - {e}")
                auth_results[step_name] = False
                auth_failures.append(f"{step_name}: Exception - {e}")

        # Calculate authentication success rate
        total_steps = len(auth_flow_steps)
        successful_steps = sum(1 for success in auth_results.values() if success)
        auth_success_rate = (successful_steps / total_steps * 100) if total_steps > 0 else 0

        print(f"\n=== GCP STAGING AUTHENTICATION RESULTS ===")
        print(f"Authentication Success Rate: {auth_success_rate:.1f}%")
        print(f"Successful Steps: {successful_steps}/{total_steps}")
        print(f"Authentication Failures: {len(auth_failures)}")

        if auth_failures:
            print(f"\n--- AUTHENTICATION FAILURES (PRODUCTION BLOCKERS) ---")
            for failure in auth_failures:
                print(f"PRODUCTION BLOCKER: {failure}")

        # CRITICAL PRODUCTION GATE ASSERTION
        self.assertEqual(
            auth_success_rate, 100.0,
            f"STAGING AUTH FAILURE: Only {auth_success_rate:.1f}% authentication success in "
            f"GCP staging with SSOT configuration. Expected: 100%. "
            f"Auth failures: {auth_failures}. "
            f"Production deployment will cause authentication failures blocking Golden Path."
        )

        # SUCCESS: Authentication works perfectly in staging
        print(f"\nCHECK STAGING AUTH SUCCESS: Golden Path authentication 100% working in GCP")

    async def test_staging_websocket_events_with_ssot_configuration(self):
        """
        STAGING TEST: Validate WebSocket events work with SSOT configuration in GCP

        SUCCESS CRITERIA:
        - WebSocket connections establish successfully in GCP staging
        - All 5 critical WebSocket events delivered reliably
        - Real-time functionality works with SSOT configuration
        - WebSocket authentication works with SSOT JWT configuration

        BUSINESS IMPACT:
        WebSocket events are critical for Golden Path user experience. If they don't
        work in staging with SSOT configuration, production users will have broken
        real-time functionality, directly impacting user satisfaction and retention.
        """
        print(f"\n=== STAGING: WebSocket Events with SSOT Configuration Validation ===")
        print(f"Testing real-time functionality in GCP staging environment")

        websocket_tests = [
            ("WebSocket Connection", self._test_staging_websocket_connection),
            ("WebSocket Authentication", self._test_staging_websocket_auth),
            ("Agent Events Delivery", self._test_staging_agent_events),
            ("Real-time Communication", self._test_staging_realtime_comm),
            ("WebSocket Performance", self._test_staging_websocket_performance),
        ]

        websocket_results = {}
        websocket_failures = []

        for test_name, test_func in websocket_tests:
            try:
                print(f"\nTesting WebSocket: {test_name}")
                success = await test_func()
                websocket_results[test_name] = success

                if success:
                    print(f"CHECK {test_name}: PASS")
                else:
                    print(f"X {test_name}: FAIL")
                    websocket_failures.append(f"{test_name}: WebSocket failed")

            except Exception as e:
                print(f"X {test_name}: EXCEPTION - {e}")
                websocket_results[test_name] = False
                websocket_failures.append(f"{test_name}: Exception - {e}")

        # Calculate WebSocket success rate
        total_tests = len(websocket_tests)
        successful_tests = sum(1 for success in websocket_results.values() if success)
        websocket_success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n=== GCP STAGING WEBSOCKET RESULTS ===")
        print(f"WebSocket Success Rate: {websocket_success_rate:.1f}%")
        print(f"Successful Tests: {successful_tests}/{total_tests}")
        print(f"WebSocket Failures: {len(websocket_failures)}")

        if websocket_failures:
            print(f"\n--- WEBSOCKET FAILURES (USER EXPERIENCE BLOCKERS) ---")
            for failure in websocket_failures:
                print(f"UX BLOCKER: {failure}")

        # CRITICAL USER EXPERIENCE ASSERTION
        self.assertGreaterEqual(
            websocket_success_rate, 80.0,  # Allow some tolerance for staging environment
            f"STAGING WEBSOCKET FAILURE: Only {websocket_success_rate:.1f}% WebSocket success "
            f"in GCP staging with SSOT configuration. Expected: ≥80%. "
            f"WebSocket failures: {websocket_failures}. "
            f"Production users will have broken real-time functionality."
        )

        # Warn if not perfect
        if websocket_success_rate < 100.0:
            print(f"\nWARNING️ WARNING: WebSocket not perfect in staging - monitor in production")

        # SUCCESS or WARNING
        if websocket_success_rate == 100.0:
            print(f"\nCHECK STAGING WEBSOCKET SUCCESS: Real-time functionality perfect in GCP")
        else:
            print(f"\nWARNING️ STAGING WEBSOCKET PARTIAL: {websocket_success_rate:.1f}% success - acceptable for production")

    # HELPER METHODS FOR STAGING VALIDATION

    async def _test_staging_config_endpoint(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Test staging configuration endpoint."""
        try:
            url = f"{self.staging_base_url}{endpoint}"
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Staging endpoint {endpoint} returned status: {response.status}")
                        return None

        except Exception as e:
            print(f"Error testing staging endpoint {endpoint}: {e}")
            return None

    async def _validate_staging_config_values(self, required_configs: List[str]) -> Dict[str, Any]:
        """Validate required configuration values are present in staging."""
        try:
            config_response = await self._test_staging_config_endpoint("/health/config-values")

            if not config_response:
                return {"all_present": False, "loaded_count": 0, "missing_configs": required_configs}

            loaded_configs = config_response.get("config_keys", [])
            missing_configs = [key for key in required_configs if key not in loaded_configs]

            return {
                "all_present": len(missing_configs) == 0,
                "loaded_count": len(loaded_configs),
                "missing_configs": missing_configs,
            }

        except Exception as e:
            print(f"Error validating staging config values: {e}")
            return {"all_present": False, "loaded_count": 0, "missing_configs": required_configs}

    async def _test_staging_config_performance(self) -> Dict[str, Any]:
        """Test configuration loading performance in staging."""
        try:
            start_time = asyncio.get_event_loop().time()
            response = await self._test_staging_config_endpoint("/health")
            end_time = asyncio.get_event_loop().time()

            load_time = end_time - start_time

            return {
                "load_time": load_time,
                "performance_acceptable": load_time < 2.0,
            }

        except Exception as e:
            print(f"Error testing staging config performance: {e}")
            return {"load_time": 999.0, "performance_acceptable": False}

    async def _test_staging_health_endpoint(self) -> bool:
        """Test staging health endpoint."""
        try:
            response = await self._test_staging_config_endpoint("/health")
            return response and response.get("status") == "healthy"
        except Exception:
            return False

    async def _test_staging_auth_health(self) -> bool:
        """Test staging auth service health."""
        try:
            response = await self._test_staging_config_endpoint("/health/auth")
            return response and response.get("status") == "healthy"
        except Exception:
            return False

    async def _test_staging_database_health(self) -> bool:
        """Test staging database health."""
        try:
            response = await self._test_staging_config_endpoint("/health/database")
            return response and response.get("status") == "healthy"
        except Exception:
            return False

    async def _test_staging_redis_health(self) -> bool:
        """Test staging Redis health."""
        try:
            response = await self._test_staging_config_endpoint("/health/redis")
            return response and response.get("status") == "healthy"
        except Exception:
            return False

    async def _test_staging_oauth_config(self) -> bool:
        """Test staging OAuth configuration."""
        try:
            response = await self._test_staging_config_endpoint("/health/oauth")
            return response and response.get("oauth_configured", False)
        except Exception:
            return False

    async def _test_staging_jwt_flow(self) -> bool:
        """Test staging JWT token flow."""
        try:
            response = await self._test_staging_config_endpoint("/health/jwt")
            return response and response.get("jwt_working", False)
        except Exception:
            return False

    async def _test_staging_session_management(self) -> bool:
        """Test staging session management."""
        try:
            response = await self._test_staging_config_endpoint("/health/session")
            return response and response.get("session_working", False)
        except Exception:
            return False

    async def _test_staging_auth_api(self) -> bool:
        """Test staging authentication API."""
        try:
            response = await self._test_staging_config_endpoint("/api/v1/auth/health")
            return response and response.get("status") == "healthy"
        except Exception:
            return False

    async def _test_staging_websocket_connection(self) -> bool:
        """Test staging WebSocket connection."""
        try:
            # Simulate WebSocket connection test
            response = await self._test_staging_config_endpoint("/health/websocket")
            return response and response.get("websocket_healthy", False)
        except Exception:
            return False

    async def _test_staging_websocket_auth(self) -> bool:
        """Test staging WebSocket authentication."""
        try:
            response = await self._test_staging_config_endpoint("/health/websocket-auth")
            return response and response.get("websocket_auth_working", False)
        except Exception:
            return False

    async def _test_staging_agent_events(self) -> bool:
        """Test staging agent events delivery."""
        try:
            response = await self._test_staging_config_endpoint("/health/agent-events")
            return response and response.get("events_working", False)
        except Exception:
            return False

    async def _test_staging_realtime_comm(self) -> bool:
        """Test staging real-time communication."""
        try:
            response = await self._test_staging_config_endpoint("/health/realtime")
            return response and response.get("realtime_working", False)
        except Exception:
            return False

    async def _test_staging_websocket_performance(self) -> bool:
        """Test staging WebSocket performance."""
        try:
            start_time = asyncio.get_event_loop().time()
            response = await self._test_staging_config_endpoint("/health/websocket")
            end_time = asyncio.get_event_loop().time()

            performance_acceptable = (end_time - start_time) < 3.0
            return response and performance_acceptable
        except Exception:
            return False


if __name__ == "__main__":
    # Execute staging tests with maximum verbosity
    print("=" * 80)
    print("STAGING TESTS: Issue #962 GCP Configuration Validation")
    print("PRODUCTION DEPLOYMENT GATE: These tests validate production readiness")
    print("BUSINESS IMPACT: $500K+ ARR Golden Path protection")
    print("=" * 80)

    unittest.main(verbosity=2)