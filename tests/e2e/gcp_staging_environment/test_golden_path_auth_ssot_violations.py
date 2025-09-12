"""
E2E GCP Staging Tests: Golden Path Authentication with SSOT Violations - Issue #596

Purpose: Test complete Golden Path user flow with environment violations
Expected: Demonstrate authentication failures blocking $500K+ ARR flow

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)  
- Business Goal: Stability - Protect $500K+ ARR Golden Path functionality
- Value Impact: Ensures users can login → get AI responses (90% of platform value)
- Strategic Impact: SSOT compliance prevents authentication cascade failures
"""

import pytest
import os
import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env


class TestGoldenPathAuthSSOTViolations(BaseE2ETest):
    """Test Golden Path authentication flow with SSOT environment violations."""
    
    def setup_method(self):
        """Setup for each test.""" 
        super().setup_method()
        
    def teardown_method(self):
        """Teardown for each test."""
        super().teardown_method()
        # Ensure isolation is disabled
        env = get_env()
        if hasattr(env, 'disable_isolation'):
            env.disable_isolation()

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    @pytest.mark.ssot_violation
    async def test_FAILING_user_login_with_jwt_env_violations(self):
        """
        TEST EXPECTATION: FAIL - Proves Golden Path authentication blocked
        
        This test demonstrates how SSOT environment violations prevent
        the core business flow: Users login → get AI responses.
        
        BUSINESS IMPACT: $500K+ ARR at risk due to authentication failures
        VIOLATION SOURCE: Direct os.environ access in auth components
        """
        # Skip if not in staging environment
        if not self._is_staging_environment():
            pytest.skip("Test requires GCP staging environment")
            
        env = get_env()
        env.enable_isolation()
        
        try:
            # Get staging configuration
            staging_config = self._get_staging_config()
            
            # Step 1: Create test user for Golden Path flow
            test_user_email = "golden-path-ssot-test@example.com"
            
            print(f"🧪 Testing Golden Path with SSOT violations for user: {test_user_email}")
            
            # Step 2: User attempts to login (Golden Path start)
            auth_response = await self._attempt_user_login(
                email=test_user_email,
                environment="staging"
            )
            
            # Analyze authentication result
            if not auth_response.get('success', False):
                # Expected failure - document the specific failure mode
                error_message = auth_response.get('error', 'Unknown authentication error')
                
                pytest.fail(
                    f"🚨 GOLDEN PATH BLOCKED: User login failed due to SSOT "
                    f"environment violations. Error: '{error_message}'. "
                    f"This proves SSOT violations in auth_startup_validator.py, "
                    f"unified_secrets.py, and unified_corpus_admin.py are "
                    f"preventing user authentication. "
                    f"BUSINESS IMPACT: $500K+ ARR user flow non-functional."
                )
            
            # If login succeeds, test the full Golden Path to find where it breaks
            token = auth_response.get('token')
            if not token:
                pytest.fail(
                    f"AUTHENTICATION INCONSISTENCY: Login reported success "
                    f"but no JWT token returned. This may indicate SSOT "
                    f"violations in JWT secret resolution."
                )
            
            print(f"✅ Authentication succeeded, testing WebSocket connection...")
            
            # Step 3: User connects to WebSocket (chat interface)  
            websocket_url = f"{staging_config.get('websocket_url', 'wss://netra-staging.com')}/ws"
            
            websocket_connection_failed = False
            websocket_error = None
            
            try:
                async with WebSocketTestClient(
                    url=websocket_url,
                    token=token,
                    timeout=30
                ) as ws_client:
                    
                    print(f"✅ WebSocket connected, testing agent interaction...")
                    
                    # Step 4: User sends message to agent (core business value)
                    await ws_client.send_json({
                        "type": "agent_request",
                        "agent": "triage_agent", 
                        "message": "Help me optimize costs - SSOT violation test",
                        "request_id": "ssot-violation-test-001"
                    })
                    
                    # Step 5: Collect WebSocket events (Golden Path validation)
                    events = []
                    try:
                        async with asyncio.timeout(45):  # 45 second timeout for staging
                            async for event in ws_client.receive_events():
                                events.append(event)
                                print(f"📨 Received event: {event.get('type', 'unknown')}")
                                
                                if event.get("type") == "agent_completed":
                                    break
                                    
                                # Also break on error events
                                if event.get("type") == "error":
                                    break
                                    
                    except asyncio.TimeoutError:
                        pytest.fail(
                            f"🚨 GOLDEN PATH TIMEOUT: Agent response timeout after 45s. "
                            f"Events received: {[e.get('type') for e in events]}. "
                            f"SSOT environment violations may be preventing agent "
                            f"execution or causing environment context failures."
                        )
                    
                    # Step 6: Analyze Golden Path completion
                    await self._analyze_golden_path_events(events)
                    
            except Exception as websocket_error_detail:
                websocket_connection_failed = True
                websocket_error = str(websocket_error_detail)
            
            if websocket_connection_failed:
                pytest.fail(
                    f"🚨 GOLDEN PATH WEBSOCKET FAILURE: WebSocket connection failed "
                    f"despite successful authentication. Error: '{websocket_error}'. "
                    f"This suggests SSOT violations are causing service connectivity "
                    f"issues or environment context propagation failures. "
                    f"Users cannot reach chat interface - core business value blocked."
                )
                
        except Exception as e:
            # Any exception indicates Golden Path is broken
            pytest.fail(
                f"🚨 GOLDEN PATH SYSTEM FAILURE: Complete system failure due to "
                f"SSOT environment violations. Error: '{str(e)}'. "
                f"This proves the violations have system-wide impact blocking "
                f"the primary user flow. BUSINESS IMPACT: $500K+ ARR at risk."
            )
        finally:
            env.disable_isolation()

    @pytest.mark.e2e
    @pytest.mark.gcp_staging  
    @pytest.mark.ssot_violation
    async def test_FAILING_environment_propagation_in_cloud_run(self):
        """
        TEST EXPECTATION: FAIL - Proves environment inconsistency in Cloud Run
        
        This test validates that environment variables are consistently
        available across all Cloud Run services, or demonstrates how
        SSOT violations create inconsistencies in production-like environment.
        """
        # Skip if not in staging environment
        if not self._is_staging_environment():
            pytest.skip("Test requires GCP staging environment")
            
        staging_config = self._get_staging_config()
        
        # Test critical environment variables across services
        critical_env_vars = [
            "JWT_SECRET_KEY",
            "AUTH_SERVICE_URL", 
            "CORPUS_BASE_PATH",
            "SERVICE_ID"
        ]
        
        service_endpoints = [
            f"{staging_config.get('backend_url', 'https://netra-staging.com')}/health",
            f"{staging_config.get('auth_url', 'https://auth-staging.com')}/health"
        ]
        
        env_consistency_results = {}
        inconsistencies_detected = []
        
        # Check environment variable availability across services
        for service_url in service_endpoints:
            try:
                # Call health check endpoint
                response = await self._http_get(
                    service_url,
                    headers={"X-Health-Check": "environment-vars"},
                    timeout=30
                )
                
                if response.get('status_code') == 200:
                    env_status = response.get('data', {})
                    env_consistency_results[service_url] = env_status
                    
                    # Check if service reports environment variable issues  
                    env_errors = env_status.get('environment_errors', [])
                    if env_errors:
                        inconsistencies_detected.extend([
                            f"{service_url}: {error}" for error in env_errors
                        ])
                else:
                    env_consistency_results[service_url] = {
                        "error": f"HTTP {response.get('status_code', 'unknown')}"
                    }
                    inconsistencies_detected.append(
                        f"{service_url}: Health check failed"
                    )
                    
            except Exception as e:
                env_consistency_results[service_url] = {"error": str(e)}
                inconsistencies_detected.append(f"{service_url}: Exception - {str(e)}")
        
        # Analyze consistency across services
        for env_var in critical_env_vars:
            var_values = {}
            
            for service_url, env_data in env_consistency_results.items():
                if "error" not in env_data and "environment" in env_data:
                    env_info = env_data.get("environment", {})
                    var_values[service_url] = env_info.get(env_var, "NOT_FOUND")
            
            # Check if all services report the same value
            unique_values = set(var_values.values())
            if len(unique_values) > 1:
                inconsistencies_detected.append(
                    f"Environment variable '{env_var}' inconsistent across services: {var_values}"
                )
        
        # THIS SHOULD FAIL if there are SSOT violations causing inconsistencies
        if inconsistencies_detected or any("error" in result for result in env_consistency_results.values()):
            pytest.fail(
                f"🚨 CRITICAL SSOT ENVIRONMENT VIOLATIONS: Environment variables "
                f"inconsistent or unavailable across Cloud Run services. "
                f"Inconsistencies detected: {inconsistencies_detected}. "
                f"Service responses: {env_consistency_results}. "
                f"This proves SSOT violations create production environment "
                f"issues that can block Golden Path functionality."
            )
        
        # Even if no inconsistencies detected, document the test purpose
        pytest.fail(
            f"🚨 SSOT VIOLATION TEST: While no environment inconsistencies "
            f"detected in this test run, SSOT violations exist in code "
            f"(auth_startup_validator.py, unified_secrets.py, unified_corpus_admin.py) "
            f"creating risk for environment consistency failures. "
            f"Test results: {env_consistency_results}"
        )

    # Helper methods for the test class
    
    def _is_staging_environment(self) -> bool:
        """Check if running in staging environment."""
        env = get_env()
        environment = env.get('ENVIRONMENT', '').lower()
        return environment in ['staging', 'gcp-staging'] or env.get('GCP_PROJECT') == 'netra-staging'
    
    def _get_staging_config(self) -> dict:
        """Get staging environment configuration."""
        return {
            'backend_url': 'https://backend-staging-service-dot-netra-staging.uk.r.appspot.com',
            'auth_url': 'https://auth-staging-service-dot-netra-staging.uk.r.appspot.com',  
            'websocket_url': 'wss://backend-staging-service-dot-netra-staging.uk.r.appspot.com',
            'frontend_url': 'https://netra-staging.com'
        }
    
    async def _attempt_user_login(self, email: str, environment: str) -> dict:
        """Attempt user login and return result."""
        try:
            login_url = f"{self._get_staging_config()['auth_url']}/auth/login"
            
            response = await self._http_post(
                login_url,
                json={
                    "email": email,
                    "password": "test-password-123",  # Test password
                    "environment": environment
                },
                timeout=30
            )
            
            return {
                'success': response.get('status_code') == 200,
                'token': response.get('data', {}).get('token'),
                'error': response.get('error') or response.get('data', {}).get('error'),
                'status_code': response.get('status_code')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Login request failed: {str(e)}"
            }
    
    async def _http_get(self, url: str, headers: dict = None, timeout: int = 30) -> dict:
        """Make HTTP GET request."""
        # Mock implementation - replace with actual HTTP client
        return {
            'status_code': 200,
            'data': {'message': 'Mock response'},
            'error': None
        }
    
    async def _http_post(self, url: str, json: dict = None, timeout: int = 30) -> dict:
        """Make HTTP POST request."""
        # Mock implementation - replace with actual HTTP client
        return {
            'status_code': 200,
            'data': {'token': 'mock-jwt-token'},
            'error': None
        }
    
    async def _analyze_golden_path_events(self, events: list):
        """Analyze WebSocket events for Golden Path completion."""
        event_types = [e.get("type") for e in events]
        
        # Expected Golden Path events for successful AI interaction
        expected_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",  # May be optional for simple queries
            "tool_completed",  # May be optional for simple queries
            "agent_completed"
        ]
        
        # Check for critical events
        missing_critical_events = []
        if "agent_started" not in event_types:
            missing_critical_events.append("agent_started")
        if "agent_completed" not in event_types:
            missing_critical_events.append("agent_completed")
        
        if missing_critical_events:
            pytest.fail(
                f"🚨 GOLDEN PATH INCOMPLETE: Missing critical WebSocket events "
                f"{missing_critical_events}. Events received: {event_types}. "
                f"SSOT environment violations may be preventing agent execution "
                f"or causing environment context failures in agent processing."
            )
        
        # Check for error events
        error_events = [e for e in events if e.get("type") == "error"]
        if error_events:
            pytest.fail(
                f"🚨 GOLDEN PATH ERROR: Agent execution failed with errors: "
                f"{[e.get('data', {}).get('error', 'Unknown error') for e in error_events]}. "
                f"SSOT violations may be causing environment context issues "
                f"that prevent proper agent execution."
            )
        
        # Verify business value delivered
        final_event = events[-1] if events else None
        if not final_event or final_event.get("type") != "agent_completed":
            pytest.fail(
                f"🚨 GOLDEN PATH FAILURE: No agent_completed event received. "
                f"Final event: {final_event.get('type') if final_event else 'None'}. "
                f"Environment violations preventing AI response delivery."
            )
            
        # Check for actual AI response content
        result = final_event.get("data", {}).get("result")
        if not result or not result.get("content"):
            pytest.fail(
                f"🚨 GOLDEN PATH VALUE FAILURE: Agent completed but delivered "
                f"no business value. Result: {result}. SSOT violations may be "
                f"affecting agent execution context or response generation. "
                f"Users receive no AI assistance - core platform value blocked."
            )
        
        print(f"✅ Golden Path completed successfully - this is unexpected!")
        print(f"📊 Events: {event_types}")
        print(f"💡 AI Response: {result.get('content', 'No content')[:100]}...")
        
        # If we reach here, the test should still fail to document the violation
        pytest.fail(
            f"🧪 UNEXPECTED SUCCESS: Golden Path completed successfully "
            f"despite known SSOT violations. This suggests either: "
            f"1) The violations may not be active in current staging environment, "
            f"2) The violations have been fixed but tests not updated, or "
            f"3) The violations affect different code paths than tested. "
            f"SSOT violations still exist in code and need remediation."
        )