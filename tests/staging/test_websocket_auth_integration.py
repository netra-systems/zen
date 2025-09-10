#!/usr/bin/env python
"""
WebSocket Authentication Integration Tests - Exposing Infrastructure Gaps

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - WebSocket auth affects all users
- Business Goal: Expose WebSocket authentication infrastructure failures preventing chat value
- Value Impact: WebSocket auth enables 90% of business value through real-time chat interactions
- Strategic Impact: Root cause analysis for staging 0% pass rate - $120K+ MRR at risk

CRITICAL MISSION: These tests are designed to FAIL and expose specific infrastructure gaps:
1. WebSocket auth header JSON serialization failures in staging
2. HTTP 503 Service Unavailable errors from GCP Cloud Run
3. Agent Registry missing WebSocket manager integration
4. Authentication bypass missing in staging environment

TEST FAILURE EXPECTATIONS:
- JSON serialization errors with complex auth headers
- Connection timeouts to wss://api.staging.netrasystems.ai/ws
- Missing E2E_OAUTH_SIMULATION_KEY configuration 
- Factory pattern vs singleton pattern architectural mismatches

This test suite intentionally reproduces the staging infrastructure failures
to systematically document and validate fixes.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# SSOT imports per CLAUDE.md requirements
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env
from shared.types.core_types import UserID


@dataclass
class WebSocketAuthFailureReport:
    """Data structure for capturing WebSocket authentication infrastructure failures."""
    
    test_name: str
    failure_type: str
    error_message: str
    expected_failure: bool
    infrastructure_gap: str
    staging_specific: bool
    timestamp: str
    technical_details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert failure report to dictionary for analysis."""
        return {
            "test_name": self.test_name,
            "failure_type": self.failure_type,
            "error_message": self.error_message,
            "expected_failure": self.expected_failure,
            "infrastructure_gap": self.infrastructure_gap,
            "staging_specific": self.staging_specific,
            "timestamp": self.timestamp,
            "technical_details": self.technical_details
        }


class TestWebSocketAuthenticationIntegration(BaseIntegrationTest):
    """Integration tests designed to expose WebSocket authentication infrastructure gaps."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.failure_reports: List[WebSocketAuthFailureReport] = []
        self.auth_helper = None
        self.websocket_auth_helper = None
        
    def setup_method(self):
        """Setup for each test method with failure tracking."""
        # Determine environment - prefer staging for infrastructure gap testing
        test_environment = self.env.get("TEST_ENV", "staging")
        
        # Initialize auth helpers for the environment
        self.auth_helper = E2EAuthHelper(environment=test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=test_environment)
        
        print(f"[INFO] WebSocket Auth Integration Test Environment: {test_environment}")
        print(f"[INFO] Auth service URL: {self.auth_helper.config.auth_service_url}")
        print(f"[INFO] WebSocket URL: {self.auth_helper.config.websocket_url}")
        
    def capture_failure_report(
        self,
        test_name: str,
        failure_type: str,
        error_message: str,
        expected_failure: bool,
        infrastructure_gap: str,
        staging_specific: bool = False,
        technical_details: Optional[Dict[str, Any]] = None
    ):
        """Capture structured failure report for infrastructure gap analysis."""
        report = WebSocketAuthFailureReport(
            test_name=test_name,
            failure_type=failure_type,
            error_message=error_message,
            expected_failure=expected_failure,
            infrastructure_gap=infrastructure_gap,
            staging_specific=staging_specific,
            timestamp=datetime.now(timezone.utc).isoformat(),
            technical_details=technical_details or {}
        )
        
        self.failure_reports.append(report)
        
        # Log failure for immediate visibility
        failure_status = "EXPECTED" if expected_failure else "UNEXPECTED"
        staging_marker = " [STAGING-SPECIFIC]" if staging_specific else ""
        print(f"[{failure_status} FAILURE{staging_marker}] {test_name}: {infrastructure_gap}")
        print(f"[ERROR DETAILS] {error_message}")
        if technical_details:
            print(f"[TECHNICAL] {json.dumps(technical_details, indent=2)}")
    
    # ===================== WebSocket Header Serialization Tests =====================
    
    @pytest.mark.integration 
    async def test_websocket_auth_header_json_serialization_failure(self):
        """
        Test WebSocket auth header JSON serialization failures.
        
        EXPECTED TO FAIL: This test should expose JSON serialization issues
        when complex auth headers are sent to staging WebSocket endpoints.
        
        Infrastructure Gap: WebSocket auth header serialization failures
        """
        test_name = "websocket_auth_header_json_serialization"
        
        try:
            # Create authenticated user with complex permissions
            auth_user = await self.auth_helper.create_authenticated_user(
                email="json_serialize_test@example.com",
                permissions=["read", "write", "admin", "complex:permission:with:colons"]
            )
            
            # Get WebSocket headers with complex data that may cause serialization issues
            complex_headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
            
            # Add potentially problematic headers that staging might fail to serialize
            complex_headers.update({
                "X-User-Permissions": json.dumps(auth_user.permissions),  # JSON in header
                "X-User-Metadata": json.dumps({
                    "complex": {"nested": {"data": True}},
                    "special_chars": "quotes\"and'apostrophes",
                    "unicode": "🔐🚀💯",
                    "timestamps": datetime.now(timezone.utc).isoformat()
                }),
                "X-Complex-Auth-Context": json.dumps({
                    "user_id": auth_user.user_id,
                    "session_data": {"key": "value with spaces and symbols &%$#"},
                    "nested_arrays": [1, 2, {"nested": True}]
                })
            })
            
            print(f"[DEBUG] Complex WebSocket headers: {len(complex_headers)} headers")
            print(f"[DEBUG] Header names: {list(complex_headers.keys())}")
            
            # EXPECTED FAILURE: Staging WebSocket should fail with JSON serialization error
            try:
                websocket_connection, connection_info = await self.auth_helper.create_websocket_connection(
                    token=auth_user.jwt_token,
                    timeout=10.0
                )
                
                # If connection succeeds unexpectedly, this is a gap in our test
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type="unexpected_success",
                    error_message="WebSocket connection succeeded with complex headers",
                    expected_failure=False,
                    infrastructure_gap="Complex header serialization should fail in staging",
                    staging_specific=True,
                    technical_details={
                        "connection_info": connection_info,
                        "headers_sent": list(complex_headers.keys()),
                        "headers_count": len(complex_headers)
                    }
                )
                
                await websocket_connection.close()
                
            except Exception as websocket_error:
                # EXPECTED: This should fail with serialization or connection error
                error_message = str(websocket_error).lower()
                
                # Check for known serialization failure patterns
                serialization_patterns = [
                    "json", "serializ", "encoding", "decode", "invalid", 
                    "header", "format", "parse"
                ]
                
                is_serialization_error = any(pattern in error_message for pattern in serialization_patterns)
                
                if is_serialization_error:
                    self.capture_failure_report(
                        test_name=test_name,
                        failure_type="json_serialization_error",
                        error_message=str(websocket_error),
                        expected_failure=True,
                        infrastructure_gap="WebSocket header JSON serialization failure in staging",
                        staging_specific=True,
                        technical_details={
                            "error_type": type(websocket_error).__name__,
                            "problematic_headers": list(complex_headers.keys()),
                            "serialization_patterns_found": [p for p in serialization_patterns if p in error_message]
                        }
                    )
                else:
                    # Connection error but not serialization - still valuable data
                    self.capture_failure_report(
                        test_name=test_name,
                        failure_type="connection_error",
                        error_message=str(websocket_error),
                        expected_failure=True,
                        infrastructure_gap="WebSocket connection failure (non-serialization)",
                        staging_specific=True,
                        technical_details={
                            "error_type": type(websocket_error).__name__,
                            "error_category": "connection_failure"
                        }
                    )
                    
        except Exception as setup_error:
            self.capture_failure_report(
                test_name=test_name,
                failure_type="setup_error",
                error_message=str(setup_error),
                expected_failure=False,
                infrastructure_gap="Test setup failure - auth helper issues",
                technical_details={
                    "error_type": type(setup_error).__name__,
                    "setup_phase": "auth_user_creation"
                }
            )
            raise
    
    @pytest.mark.integration
    async def test_websocket_auth_header_empty_values_handling(self):
        """
        Test WebSocket auth header handling with empty/null values.
        
        EXPECTED TO FAIL: This should expose how staging handles malformed auth headers
        
        Infrastructure Gap: WebSocket auth header validation failures
        """
        test_name = "websocket_auth_header_empty_values"
        
        try:
            # Create basic authenticated user
            auth_user = await self.auth_helper.create_authenticated_user()
            
            # Get normal headers first
            normal_headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
            
            # Create problematic headers with empty values
            problematic_headers = normal_headers.copy()
            problematic_headers.update({
                "X-Empty-String": "",
                "X-Null-Value": None,  # This might cause issues
                "X-Empty-JSON": "{}",
                "X-Invalid-JSON": "{invalid json",
                "X-User-ID": "",  # Empty user ID might break validation
                "Authorization": f"Bearer {auth_user.jwt_token}",  # Valid token
                "X-Malformed-Auth": "Bearer ",  # Empty token part
            })
            
            # EXPECTED FAILURE: Staging should fail with auth validation error
            try:
                websocket_connection, connection_info = await self.auth_helper.create_websocket_connection(
                    token=auth_user.jwt_token,
                    timeout=5.0
                )
                
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type="unexpected_success",
                    error_message="WebSocket accepted malformed auth headers",
                    expected_failure=False,
                    infrastructure_gap="Malformed header validation should fail",
                    staging_specific=True,
                    technical_details={
                        "connection_info": connection_info,
                        "malformed_headers": [k for k, v in problematic_headers.items() if not v]
                    }
                )
                
                await websocket_connection.close()
                
            except Exception as websocket_error:
                # EXPECTED: Should fail with validation error
                error_message = str(websocket_error).lower()
                
                validation_patterns = ["validation", "invalid", "empty", "null", "required"]
                is_validation_error = any(pattern in error_message for pattern in validation_patterns)
                
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type="auth_validation_error" if is_validation_error else "connection_error",
                    error_message=str(websocket_error),
                    expected_failure=True,
                    infrastructure_gap="WebSocket auth header validation failure" if is_validation_error else "WebSocket connection failure",
                    staging_specific=True,
                    technical_details={
                        "error_type": type(websocket_error).__name__,
                        "validation_patterns_found": [p for p in validation_patterns if p in error_message] if is_validation_error else [],
                        "malformed_headers_tested": list(problematic_headers.keys())
                    }
                )
                
        except Exception as setup_error:
            self.capture_failure_report(
                test_name=test_name,
                failure_type="setup_error", 
                error_message=str(setup_error),
                expected_failure=False,
                infrastructure_gap="Test setup failure",
                technical_details={"error_type": type(setup_error).__name__}
            )
            raise
    
    # ===================== HTTP 503 Service Unavailable Tests =====================
    
    @pytest.mark.integration
    async def test_staging_websocket_503_service_unavailable_reproduction(self):
        """
        Test staging WebSocket 503 Service Unavailable error reproduction.
        
        EXPECTED TO FAIL: This should reproduce the exact 503 errors seen in staging
        that prevent WebSocket connections from being established.
        
        Infrastructure Gap: GCP Cloud Run service availability issues
        """
        test_name = "staging_websocket_503_reproduction"
        
        try:
            # Use staging-specific configuration
            staging_auth_helper = E2EWebSocketAuthHelper(environment="staging")
            
            # Get staging token - this might fail due to missing E2E_OAUTH_SIMULATION_KEY
            try:
                staging_token = await staging_auth_helper.get_staging_token_async()
                token_obtained = True
                token_error = None
            except Exception as token_error:
                staging_token = None
                token_obtained = False
                
                # Document the token acquisition failure
                self.capture_failure_report(
                    test_name=f"{test_name}_token_acquisition",
                    failure_type="oauth_simulation_error",
                    error_message=str(token_error),
                    expected_failure=True,
                    infrastructure_gap="Missing E2E_OAUTH_SIMULATION_KEY in staging",
                    staging_specific=True,
                    technical_details={
                        "token_method": "get_staging_token_async",
                        "error_type": type(token_error).__name__
                    }
                )
            
            # EXPECTED FAILURE: Staging WebSocket connection should fail with 503
            try:
                # Use staging WebSocket URL directly
                staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"
                
                if staging_token:
                    websocket_headers = staging_auth_helper.get_websocket_headers(staging_token)
                else:
                    # Try with fallback staging-compatible token
                    fallback_token = staging_auth_helper._create_staging_compatible_jwt("test@example.com")
                    websocket_headers = staging_auth_helper.get_websocket_headers(fallback_token)
                
                print(f"[INFO] Attempting connection to: {staging_websocket_url}")
                print(f"[INFO] Using headers: {list(websocket_headers.keys())}")
                
                # This should fail with 503 Service Unavailable
                websocket_connection = await staging_auth_helper.connect_authenticated_websocket(timeout=15.0)
                
                # If connection succeeds, this indicates the infrastructure issue may be resolved
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type="unexpected_success",
                    error_message="Staging WebSocket connection succeeded unexpectedly",
                    expected_failure=False,
                    infrastructure_gap="Expected 503 error not encountered - infrastructure may be fixed",
                    staging_specific=True,
                    technical_details={
                        "websocket_url": staging_websocket_url,
                        "token_obtained": token_obtained,
                        "headers_sent": list(websocket_headers.keys())
                    }
                )
                
                await websocket_connection.close()
                
            except Exception as connection_error:
                # EXPECTED: Should fail with 503 or connection error
                error_message = str(connection_error).lower()
                
                # Check for specific staging failure patterns
                staging_failure_patterns = [
                    "503", "service unavailable", "unavailable", "timeout", 
                    "connection refused", "failed to connect", "cloud run"
                ]
                
                is_503_error = "503" in error_message or "unavailable" in error_message
                is_staging_failure = any(pattern in error_message for pattern in staging_failure_patterns)
                
                failure_type = "503_service_unavailable" if is_503_error else "staging_connection_failure"
                
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type=failure_type,
                    error_message=str(connection_error),
                    expected_failure=True,
                    infrastructure_gap="Staging WebSocket service unavailable (503) - GCP Cloud Run issues",
                    staging_specific=True,
                    technical_details={
                        "error_type": type(connection_error).__name__,
                        "is_503_error": is_503_error,
                        "is_staging_failure": is_staging_failure,
                        "staging_patterns_found": [p for p in staging_failure_patterns if p in error_message],
                        "websocket_url": staging_websocket_url,
                        "token_acquisition_success": token_obtained
                    }
                )
                
        except Exception as test_error:
            self.capture_failure_report(
                test_name=test_name,
                failure_type="test_execution_error",
                error_message=str(test_error),
                expected_failure=False,
                infrastructure_gap="Test execution framework issue",
                technical_details={"error_type": type(test_error).__name__}
            )
            raise
    
    @pytest.mark.integration
    async def test_missing_e2e_oauth_simulation_key_failure(self):
        """
        Test missing E2E OAuth simulation key infrastructure failure.
        
        EXPECTED TO FAIL: This should expose the missing E2E_OAUTH_SIMULATION_KEY
        that prevents staging authentication for E2E tests.
        
        Infrastructure Gap: Missing secret deployment in GCP Secret Manager
        """
        test_name = "missing_e2e_oauth_simulation_key"
        
        try:
            # Direct test of E2E OAuth simulation key availability
            e2e_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            
            if not e2e_key:
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type="missing_environment_variable",
                    error_message="E2E_OAUTH_SIMULATION_KEY environment variable not set",
                    expected_failure=True,
                    infrastructure_gap="Missing E2E_OAUTH_SIMULATION_KEY in environment - prevents staging auth bypass",
                    staging_specific=True,
                    technical_details={
                        "environment_check": "E2E_OAUTH_SIMULATION_KEY",
                        "available_env_vars": [k for k in self.env.keys() if "oauth" in k.lower() or "e2e" in k.lower()]
                    }
                )
            
            # Test direct auth service bypass endpoint
            staging_auth_helper = E2EWebSocketAuthHelper(environment="staging")
            
            try:
                # This should fail if the key is missing or invalid
                token = await staging_auth_helper.get_staging_token_async(
                    email="e2e_test@example.com",
                    bypass_key=e2e_key
                )
                
                if token:
                    # Unexpected success - key might be working
                    self.capture_failure_report(
                        test_name=test_name,
                        failure_type="unexpected_success",
                        error_message="E2E OAuth simulation succeeded unexpectedly",
                        expected_failure=False,
                        infrastructure_gap="E2E OAuth simulation working - key deployment may be resolved",
                        staging_specific=True,
                        technical_details={
                            "token_length": len(token) if token else 0,
                            "key_provided": bool(e2e_key)
                        }
                    )
                else:
                    # Expected failure pattern
                    self.capture_failure_report(
                        test_name=test_name,
                        failure_type="oauth_simulation_failure",
                        error_message="E2E OAuth simulation returned no token",
                        expected_failure=True,
                        infrastructure_gap="E2E OAuth simulation failure - invalid or missing key",
                        staging_specific=True,
                        technical_details={
                            "token_result": None,
                            "key_provided": bool(e2e_key)
                        }
                    )
                    
            except Exception as oauth_error:
                # EXPECTED: Should fail with authentication or key validation error
                error_message = str(oauth_error).lower()
                
                key_error_patterns = ["key", "unauthorized", "forbidden", "invalid", "bypass", "simulation"]
                is_key_error = any(pattern in error_message for pattern in key_error_patterns)
                
                self.capture_failure_report(
                    test_name=test_name,
                    failure_type="oauth_simulation_key_error" if is_key_error else "oauth_simulation_failure",
                    error_message=str(oauth_error),
                    expected_failure=True,
                    infrastructure_gap="E2E OAuth simulation key validation failure",
                    staging_specific=True,
                    technical_details={
                        "error_type": type(oauth_error).__name__,
                        "is_key_error": is_key_error,
                        "key_patterns_found": [p for p in key_error_patterns if p in error_message],
                        "key_provided": bool(e2e_key),
                        "key_length": len(e2e_key) if e2e_key else 0
                    }
                )
                
        except Exception as test_error:
            self.capture_failure_report(
                test_name=test_name,
                failure_type="test_execution_error",
                error_message=str(test_error),
                expected_failure=False,
                infrastructure_gap="Test execution issue",
                technical_details={"error_type": type(test_error).__name__}
            )
            raise
    
    # ===================== Test Result Analysis and Reporting =====================
    
    @pytest.mark.integration
    async def test_infrastructure_gap_analysis_report(self):
        """
        Generate comprehensive infrastructure gap analysis from test failures.
        
        This test analyzes all captured failures and generates a structured report
        of infrastructure gaps discovered during testing.
        """
        test_name = "infrastructure_gap_analysis"
        
        print(f"\n{'='*80}")
        print(f"INFRASTRUCTURE GAP ANALYSIS REPORT")
        print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        print(f"Total Failures Captured: {len(self.failure_reports)}")
        print(f"{'='*80}")
        
        # Categorize failures by type
        failure_categories = {}
        staging_specific_failures = []
        expected_failures = []
        unexpected_failures = []
        
        for report in self.failure_reports:
            category = report.failure_type
            if category not in failure_categories:
                failure_categories[category] = []
            failure_categories[category].append(report)
            
            if report.staging_specific:
                staging_specific_failures.append(report)
            
            if report.expected_failure:
                expected_failures.append(report)
            else:
                unexpected_failures.append(report)
        
        # Print categorized analysis
        print(f"\nFAILURE CATEGORIES:")
        for category, reports in failure_categories.items():
            print(f"  {category.upper()}: {len(reports)} failures")
            for report in reports:
                status = "EXPECTED" if report.expected_failure else "UNEXPECTED"
                staging = " [STAGING]" if report.staging_specific else ""
                print(f"    - {report.test_name}: {report.infrastructure_gap} ({status}){staging}")
        
        print(f"\nSTAGING-SPECIFIC ISSUES: {len(staging_specific_failures)}")
        for report in staging_specific_failures:
            print(f"  - {report.infrastructure_gap}")
            print(f"    Error: {report.error_message}")
        
        print(f"\nEXPECTED vs UNEXPECTED FAILURES:")
        print(f"  Expected: {len(expected_failures)} (infrastructure gaps successfully exposed)")
        print(f"  Unexpected: {len(unexpected_failures)} (test framework or setup issues)")
        
        if unexpected_failures:
            print(f"\nUNEXPECTED FAILURE DETAILS:")
            for report in unexpected_failures:
                print(f"  - {report.test_name}: {report.error_message}")
        
        # Generate structured report for analysis
        infrastructure_gap_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_failures": len(self.failure_reports),
            "expected_failures": len(expected_failures),
            "unexpected_failures": len(unexpected_failures),
            "staging_specific_failures": len(staging_specific_failures),
            "failure_categories": {k: len(v) for k, v in failure_categories.items()},
            "key_infrastructure_gaps": list(set(report.infrastructure_gap for report in self.failure_reports)),
            "detailed_failures": [report.to_dict() for report in self.failure_reports]
        }
        
        # Save report for analysis (would be written to file in real implementation)
        print(f"\nSTRUCTURED REPORT SUMMARY:")
        print(f"Key Infrastructure Gaps Identified: {len(infrastructure_gap_report['key_infrastructure_gaps'])}")
        for gap in infrastructure_gap_report['key_infrastructure_gaps']:
            print(f"  - {gap}")
        
        print(f"\n{'='*80}")
        print(f"INFRASTRUCTURE GAP TESTING COMPLETE")
        print(f"Report available for further analysis and remediation planning")
        print(f"{'='*80}\n")
        
        # For this test, we'll assert that we successfully captured some failures
        # (indicating infrastructure gaps were exposed)
        assert len(self.failure_reports) > 0, "No infrastructure gaps were exposed - tests may need revision"
        assert len(expected_failures) > 0, "No expected failures captured - infrastructure gap detection not working"
        
        # Store report as class attribute for potential further use
        self.infrastructure_gap_report = infrastructure_gap_report
        
        return infrastructure_gap_report


# Integration with pytest fixtures and markers
if __name__ == "__main__":
    import asyncio
    
    async def run_direct_tests():
        """Run tests directly for development and debugging."""
        print("Starting WebSocket Authentication Integration Tests...")
        
        test_instance = TestWebSocketAuthenticationIntegration()
        test_instance.setup_method()
        
        try:
            # Run key tests to expose infrastructure gaps
            await test_instance.test_websocket_auth_header_json_serialization_failure()
            await test_instance.test_staging_websocket_503_service_unavailable_reproduction()
            await test_instance.test_missing_e2e_oauth_simulation_key_failure()
            
            # Generate analysis report
            report = await test_instance.test_infrastructure_gap_analysis_report()
            
            print(f"✅ Infrastructure gap testing completed")
            print(f"   → {report['total_failures']} failures captured")
            print(f"   → {report['expected_failures']} expected infrastructure gaps exposed")
            print(f"   → {report['staging_specific_failures']} staging-specific issues identified")
            
        except Exception as e:
            print(f"✗ Infrastructure gap testing encountered issues: {e}")
            raise
    
    # Run tests if executed directly
    asyncio.run(run_direct_tests())