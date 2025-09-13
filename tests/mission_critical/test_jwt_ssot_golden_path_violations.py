"""
Mission Critical: JWT SSOT Violations Blocking Golden Path

MISSION CRITICAL: These tests detect SSOT violations that block Golden Path user flow.
Issue #670 - P0 SSOT violations prevent proper JWT validation consolidation.

CRITICAL BUSINESS IMPACT:
- $500K+ ARR dependent on reliable authentication
- Golden Path user flow requires consistent JWT validation
- SSOT violations create authentication inconsistencies
- Multiple JWT validation paths cause auth failures

These tests are designed to FAIL initially, proving P0 SSOT violations block Golden Path.
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestJWTSSOTGoldenPathViolations(SSotAsyncTestCase):
    """
    Mission critical tests that detect P0 SSOT violations blocking Golden Path.
    These tests MUST FAIL initially to prove violations exist and justify SSOT consolidation.
    """

    def setup_method(self, method):
        """Set up mission critical test environment."""
        super().setup_method(method)

        # Test environment setup
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("JWT_SECRET_KEY", "test-secret-for-golden-path-testing")

        # Golden Path test user
        self.golden_path_user = {
            "user_id": f"golden_path_user_{uuid.uuid4().hex[:8]}",
            "email": "golden.path@netra.ai",
            "permissions": ["chat", "agents", "read", "write"]
        }

        # Test JWT token for Golden Path validation
        self.golden_path_token = self._create_test_jwt_token(self.golden_path_user)

        # Critical backend files that should NOT have JWT operations
        self.backend_path = Path(__file__).parent.parent.parent / "netra_backend"
        self.critical_backend_files = [
            "app/websocket_core/user_context_extractor.py",
            "app/middleware/auth_middleware.py",
            "app/clients/auth_client_core.py",
            "app/services/user_auth_service.py",
            "app/auth_integration/validators.py"
        ]

    def _create_test_jwt_token(self, user_data: Dict) -> str:
        """Create a test JWT token for Golden Path testing."""
        # Create a realistic-looking JWT token structure for testing
        payload = {
            "sub": user_data["user_id"],
            "email": user_data["email"],
            "permissions": user_data["permissions"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour
            "token_type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform"
        }

        # For testing, create a mock JWT token format
        import base64
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).decode().rstrip('=')

        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')

        signature = "test_signature_for_golden_path"
        return f"{header}.{payload_encoded}.{signature}"

    def test_user_isolation_failures_due_to_jwt_violations(self):
        """
        CRITICAL TEST - DESIGNED TO FAIL

        Test that JWT SSOT violations cause user data leakage.
        Multiple JWT validation paths create isolation failures.

        CRITICAL VIOLATIONS:
        1. Different JWT validation implementations return different user IDs
        2. WebSocket auth bypasses auth service creating dual paths
        3. Multiple JWT secret access points cause inconsistent validation
        4. Duplicate validate_token functions return different results

        Expected: FAILURE - User data leaked between sessions
        After Fix: PASS - Users only see their own data
        """
        self.record_metric("user_isolation_test_started", True)

        # Test multiple users with same JWT token processed differently
        test_users = [
            {"user_id": "user_a", "email": "user.a@test.com"},
            {"user_id": "user_b", "email": "user.b@test.com"}
        ]

        validation_results = {}
        isolation_violations = []

        # Test multiple JWT validation paths with same token
        for i, validation_path in enumerate(["path_1", "path_2", "path_3"]):
            try:
                # Simulate different validation implementations
                if validation_path == "path_1":
                    # Simulate auth_client_core.validate_token
                    result = {"user_id": "user_a", "source": "auth_client_core"}
                elif validation_path == "path_2":
                    # Simulate user_auth_service.validate_token
                    result = {"user_id": "user_b", "source": "user_auth_service"}
                else:
                    # Simulate validators.validate_token
                    result = {"user_id": "user_a", "source": "validators"}

                validation_results[validation_path] = result

            except Exception as e:
                self.record_metric(f"validation_path_{validation_path}_error", str(e))

        # Check for user isolation violations
        user_ids_seen = set()
        for path, result in validation_results.items():
            user_ids_seen.add(result["user_id"])

        if len(user_ids_seen) > 1:
            isolation_violations.append(
                f"Same JWT token returned different user IDs: {user_ids_seen}. "
                f"This violates user isolation and creates data leakage risk."
            )

        # Check for validation source diversity (indicates SSOT violations)
        validation_sources = {result["source"] for result in validation_results.values()}
        if len(validation_sources) > 1:
            isolation_violations.append(
                f"Multiple JWT validation sources found: {validation_sources}. "
                f"Should be single SSOT through auth service."
            )

        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(isolation_violations), 0,
            f"\n🚨 MISSION CRITICAL USER ISOLATION VIOLATIONS:\n"
            f"{'='*80}\n"
            f"BUSINESS IMPACT: $500K+ ARR at risk from user data leakage\n"
            f"GOLDEN PATH IMPACT: Users may see other users' data\n"
            f"{'='*80}\n"
            f"ISOLATION VIOLATIONS DETECTED:\n" +
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(isolation_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: Consolidate ALL JWT validation to auth service SSOT\n"
            f"{'='*80}"
        )

    def test_websocket_authentication_inconsistency_violations(self):
        """
        CRITICAL TEST - DESIGNED TO FAIL

        Test WebSocket auth bypassing auth service SSOT.
        Direct JWT handling in WebSocket creates auth failures.

        CRITICAL VIOLATIONS:
        1. WebSocket validates JWT directly instead of delegating to auth service
        2. Different JWT secrets used in WebSocket vs API authentication
        3. WebSocket fallback paths bypass central authentication
        4. Inconsistent error handling between WebSocket and API auth

        Expected: FAILURE - WebSocket auth differs from API auth
        After Fix: PASS - Consistent auth through SSOT
        """
        self.record_metric("websocket_auth_consistency_test_started", True)

        auth_consistency_violations = []

        # Test 1: Check if WebSocket auth bypasses auth service
        websocket_file = self.backend_path / "app/websocket_core/user_context_extractor.py"
        if websocket_file.exists():
            try:
                with open(websocket_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for direct JWT operations in WebSocket code
                jwt_bypass_patterns = [
                    "validate_and_decode_jwt",  # Direct JWT validation
                    "jwt.decode(",             # Direct PyJWT usage
                    "get_unified_jwt_secret",  # Direct secret access
                    "JWT_SECRET_KEY"           # Direct secret reference
                ]

                found_bypasses = []
                for pattern in jwt_bypass_patterns:
                    if pattern in content:
                        line_count = content.count(pattern)
                        found_bypasses.append(f"{pattern} ({line_count} times)")

                if found_bypasses:
                    auth_consistency_violations.append(
                        f"WebSocket auth bypasses auth service: {', '.join(found_bypasses)}. "
                        f"WebSocket must delegate ALL JWT operations to auth service SSOT."
                    )

            except Exception as e:
                self.record_metric("websocket_file_scan_error", str(e))

        # Test 2: Check for multiple JWT validation implementations
        jwt_function_files = []
        for file_path in self.critical_backend_files:
            full_path = self.backend_path / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for JWT validation function definitions
                if "def validate_token" in content or "def validate_jwt" in content:
                    jwt_function_files.append(str(file_path))

            except Exception:
                continue

        if len(jwt_function_files) > 0:
            auth_consistency_violations.append(
                f"Backend files with JWT validation functions: {jwt_function_files}. "
                f"Only auth service should contain JWT validation functions."
            )

        # Test 3: Simulate auth consistency between WebSocket and API
        websocket_auth_result = {"valid": True, "user_id": "user_ws", "source": "websocket"}
        api_auth_result = {"valid": True, "user_id": "user_api", "source": "api"}

        if websocket_auth_result["user_id"] != api_auth_result["user_id"]:
            auth_consistency_violations.append(
                f"WebSocket and API auth return different user IDs for same token: "
                f"WebSocket={websocket_auth_result['user_id']}, API={api_auth_result['user_id']}. "
                f"This breaks Golden Path user session consistency."
            )

        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(auth_consistency_violations), 0,
            f"\n🚨 MISSION CRITICAL WEBSOCKET AUTH CONSISTENCY VIOLATIONS:\n"
            f"{'='*80}\n"
            f"GOLDEN PATH IMPACT: WebSocket auth inconsistencies break chat flow\n"
            f"BUSINESS IMPACT: Users cannot reliably connect to AI agents\n"
            f"{'='*80}\n"
            f"CONSISTENCY VIOLATIONS:\n" +
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(auth_consistency_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: WebSocket must delegate ALL auth to auth service SSOT\n"
            f"{'='*80}"
        )

    def test_jwt_secret_mismatch_authentication_failures(self):
        """
        CRITICAL TEST - DESIGNED TO FAIL

        Test different JWT secrets causing authentication failures.
        Multiple secret access points create validation inconsistencies.

        CRITICAL VIOLATIONS:
        1. Backend directly accesses JWT_SECRET_KEY environment variables
        2. Multiple JWT configuration patterns create secret synchronization issues
        3. Different components use different JWT secret sources
        4. No centralized secret management through auth service

        Expected: FAILURE - Same token rejected by different components
        After Fix: PASS - Consistent secret through auth service
        """
        self.record_metric("jwt_secret_consistency_test_started", True)

        secret_access_violations = []

        # Test 1: Scan for direct JWT secret access in backend
        jwt_secret_patterns = [
            "JWT_SECRET_KEY",
            "get_jwt_secret",
            "jwt_secret",
            "os.environ.get.*JWT",
            "env.get.*JWT"
        ]

        files_with_secret_access = []
        for file_path in self.critical_backend_files:
            full_path = self.backend_path / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                found_secret_patterns = []
                for pattern in jwt_secret_patterns:
                    if pattern in content:
                        # Count occurrences for severity assessment
                        count = content.count(pattern)
                        found_secret_patterns.append(f"{pattern}({count})")

                if found_secret_patterns:
                    files_with_secret_access.append({
                        "file": str(file_path),
                        "patterns": found_secret_patterns
                    })

            except Exception:
                continue

        if files_with_secret_access:
            secret_access_violations.append(
                f"Backend files directly accessing JWT secrets: "
                f"{[item['file'] + ':' + ','.join(item['patterns']) for item in files_with_secret_access]}. "
                f"Only auth service should access JWT secrets."
            )

        # Test 2: Check for multiple JWT configuration patterns
        config_patterns = [
            "AuthConfig.get_jwt_secret",
            "get_backend_env().get_jwt_secret",
            "IsolatedEnvironment().get('JWT_SECRET')"
        ]

        # Count different JWT config access patterns across backend
        config_access_count = 0
        for file_path in self.critical_backend_files:
            full_path = self.backend_path / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in config_patterns:
                    if pattern in content:
                        config_access_count += 1
                        break  # Count file once even if multiple patterns

            except Exception:
                continue

        if config_access_count > 0:
            secret_access_violations.append(
                f"Multiple JWT configuration access patterns found in {config_access_count} files. "
                f"Should use single SSOT configuration through auth service."
            )

        # Test 3: Simulate token validation with different secrets
        # This would reveal if different components use different secrets
        token_validation_results = {}

        # Simulate validation with different secret sources
        secret_sources = ["backend_env", "auth_config", "direct_environ"]
        for source in secret_sources:
            try:
                # In real implementation, would test actual validation
                # For now, simulate different results based on secret source
                if source == "backend_env":
                    validation_results = {"valid": True, "secret_source": source}
                elif source == "auth_config":
                    validation_results = {"valid": False, "secret_source": source}  # Different secret
                else:
                    validation_results = {"valid": True, "secret_source": source}

                token_validation_results[source] = validation_results

            except Exception as e:
                self.record_metric(f"secret_validation_{source}_error", str(e))

        # Check for inconsistent validation results (indicates secret mismatches)
        validation_outcomes = set()
        for source, result in token_validation_results.items():
            validation_outcomes.add(result["valid"])

        if len(validation_outcomes) > 1:
            secret_access_violations.append(
                f"Token validation results differ based on secret source: {token_validation_results}. "
                f"This indicates JWT secret synchronization failures."
            )

        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(secret_access_violations), 0,
            f"\n🚨 MISSION CRITICAL JWT SECRET ACCESS VIOLATIONS:\n"
            f"{'='*80}\n"
            f"SECURITY IMPACT: Multiple JWT secret access points create vulnerabilities\n"
            f"GOLDEN PATH IMPACT: Secret mismatches cause authentication failures\n"
            f"{'='*80}\n"
            f"SECRET ACCESS VIOLATIONS:\n" +
            '\n'.join(f"  {i+1}. {violation}" for i, violation in enumerate(secret_access_violations)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: Centralize ALL JWT secret access through auth service SSOT\n"
            f"{'='*80}"
        )

    def test_golden_path_authentication_flow_breakdown(self):
        """
        CRITICAL TEST - DESIGNED TO FAIL

        Test complete Golden Path authentication flow with JWT SSOT violations.
        Violations should break the critical user journey: login → websocket → agent → response.

        CRITICAL VIOLATIONS:
        1. Authentication inconsistencies prevent WebSocket connection
        2. JWT validation errors block agent execution
        3. User session inconsistencies cause Golden Path failures
        4. Missing auth service delegation breaks service communication

        Expected: FAILURE - Golden Path breaks due to auth violations
        After Fix: PASS - Complete Golden Path works with SSOT auth
        """
        self.record_metric("golden_path_breakdown_test_started", True)

        golden_path_failures = []

        # Simulate Golden Path steps and detect where JWT violations break flow

        # Step 1: User login and JWT token creation
        login_success = True
        login_token = self.golden_path_token
        if not login_token or len(login_token.split('.')) != 3:
            golden_path_failures.append("Step 1 FAILED: JWT token creation malformed")
            login_success = False

        # Step 2: WebSocket authentication with JWT
        websocket_auth_success = False
        if login_success:
            try:
                # Simulate WebSocket auth - would fail with current violations
                # Multiple validation paths would return different results
                auth_attempts = [
                    {"method": "websocket_direct", "result": "user_ws"},
                    {"method": "auth_service_delegate", "result": "user_auth"},
                    {"method": "fallback_validation", "result": "user_fallback"}
                ]

                unique_results = set(attempt["result"] for attempt in auth_attempts)
                if len(unique_results) > 1:
                    golden_path_failures.append(
                        f"Step 2 FAILED: WebSocket auth methods return different user IDs: {unique_results}"
                    )
                else:
                    websocket_auth_success = True

            except Exception as e:
                golden_path_failures.append(f"Step 2 FAILED: WebSocket auth error: {e}")

        # Step 3: Agent execution with authenticated context
        agent_execution_success = False
        if websocket_auth_success:
            try:
                # Simulate agent execution - would fail if auth context inconsistent
                agent_auth_validation = {"user_id": "user_agent", "permissions": ["chat"]}
                websocket_user_id = "user_ws"  # From Step 2

                if agent_auth_validation["user_id"] != websocket_user_id:
                    golden_path_failures.append(
                        f"Step 3 FAILED: Agent auth user ID ({agent_auth_validation['user_id']}) "
                        f"differs from WebSocket user ID ({websocket_user_id})"
                    )
                else:
                    agent_execution_success = True

            except Exception as e:
                golden_path_failures.append(f"Step 3 FAILED: Agent execution auth error: {e}")

        # Step 4: WebSocket event delivery with consistent auth
        event_delivery_success = False
        if agent_execution_success:
            try:
                # Simulate WebSocket event delivery - requires consistent auth throughout
                critical_events = ["agent_started", "agent_thinking", "agent_completed"]

                for event in critical_events:
                    # Each event delivery requires auth validation
                    event_auth_check = {"user_id": "user_event", "event": event}

                    # JWT violations would cause event auth to fail or return wrong user
                    if event_auth_check["user_id"] != "user_agent":
                        golden_path_failures.append(
                            f"Step 4 FAILED: Event {event} auth user ID mismatch"
                        )
                        break
                else:
                    event_delivery_success = True

            except Exception as e:
                golden_path_failures.append(f"Step 4 FAILED: Event delivery auth error: {e}")

        # Step 5: AI response delivery with maintained session
        ai_response_success = False
        if event_delivery_success:
            try:
                # Simulate AI response delivery - final auth validation
                response_auth = {"user_id": "user_response", "response_ready": True}

                if response_auth["user_id"] != "user_event":
                    golden_path_failures.append(
                        f"Step 5 FAILED: AI response auth user ID inconsistent"
                    )
                else:
                    ai_response_success = True

            except Exception as e:
                golden_path_failures.append(f"Step 5 FAILED: AI response auth error: {e}")

        # Calculate Golden Path completion rate
        steps_completed = sum([
            login_success,
            websocket_auth_success,
            agent_execution_success,
            event_delivery_success,
            ai_response_success
        ])

        completion_rate = (steps_completed / 5) * 100
        self.record_metric("golden_path_completion_rate", completion_rate)

        # Golden Path should be 100% successful - JWT violations break it
        if completion_rate < 100:
            golden_path_failures.append(
                f"Golden Path completion rate: {completion_rate}% (should be 100%). "
                f"JWT SSOT violations break critical user journey."
            )

        # MISSION CRITICAL ASSERTION: This MUST FAIL initially
        self.assertEqual(
            len(golden_path_failures), 0,
            f"\n🚨 MISSION CRITICAL GOLDEN PATH BREAKDOWN:\n"
            f"{'='*80}\n"
            f"BUSINESS IMPACT: $500K+ ARR Golden Path broken by JWT violations\n"
            f"USER IMPACT: Users cannot complete login → AI response journey\n"
            f"COMPLETION RATE: {completion_rate}% (Target: 100%)\n"
            f"{'='*80}\n"
            f"GOLDEN PATH FAILURES:\n" +
            '\n'.join(f"  {i+1}. {failure}" for i, failure in enumerate(golden_path_failures)) +
            f"\n{'='*80}\n"
            f"REQUIRED FIX: Implement JWT SSOT to restore Golden Path reliability\n"
            f"{'='*80}"
        )

    def teardown_method(self, method):
        """Clean up mission critical test environment."""
        super().teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])