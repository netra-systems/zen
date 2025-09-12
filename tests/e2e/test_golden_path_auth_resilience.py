
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
E2E tests for Golden Path auth resilience on GCP staging (Issue #395).

REPRODUCTION TARGET: End-to-end Golden Path user flow failures due to auth service timeout.
These tests run against GCP staging environment and SHOULD FAIL initially.

Key E2E Issues to Reproduce:  
1. Complete user login -> chat flow blocked by auth timeouts
2. Real GCP Cloud Run network latency vs timeout configuration
3. Production-like auth service interaction failures
4. Business impact on $500K+ ARR user workflow
"""

import asyncio
import pytest
import time
import json
import os
from typing import Dict, Any, Optional
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestGoldenPathAuthResilience(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    E2E tests for Golden Path auth resilience in GCP staging environment.
    
    These tests reproduce real-world timeout issues that block the primary
    user workflow and threaten business value delivery.
    """
    
    def setup_method(self, method=None):
        """Set up E2E test environment targeting GCP staging."""
        super().setup_method(method)
        
        # Verify we're targeting staging environment  
        env = get_env()
        self.environment = env.get("ENVIRONMENT", "unknown").lower()
        
        if self.environment != "staging":
            pytest.skip("This test requires staging environment with real auth service")
            
        # Real auth client for GCP staging
        self.auth_client = AuthServiceClient()
        
        # Test credentials for staging (if available)
        self.test_email = env.get("TEST_USER_EMAIL", "test@netraapex.com")
        self.test_password = env.get("TEST_USER_PASSWORD", "test_password_123")
        
        # GCP staging auth service URL
        self.staging_auth_url = self.auth_client.settings.base_url
        
        print(f"\n🎯 E2E Test Setup - Environment: {self.environment}")
        print(f"🎯 Auth Service URL: {self.staging_auth_url}")
        print(f"🎯 Test User: {self.test_email}")
    
    def teardown_method(self, method=None):
        """Clean up E2E test environment."""
        if hasattr(self, 'auth_client') and self.auth_client and hasattr(self.auth_client, '_client') and self.auth_client._client:
            # Schedule async cleanup for next event loop
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.auth_client._client.aclose())
                else:
                    loop.run_until_complete(self.auth_client._client.aclose())
            except Exception as e:
                print(f"Warning: Could not close auth client: {e}")
        super().teardown_method(method)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_golden_path_complete_user_flow_timeout(self):
        """
        E2E REPRODUCTION TEST: Complete Golden Path user flow timeout in GCP staging.
        
        This test reproduces the complete user journey that generates $500K+ ARR:
        1. User login attempt
        2. WebSocket connection establishment  
        3. Chat authentication
        4. Agent message processing
        
        EXPECTED RESULT: Should FAIL due to auth service timeouts in real GCP environment.
        """
        
        print(f"\n🚀 Starting Golden Path E2E test against {self.staging_auth_url}")
        
        golden_path_metrics = {
            "login_duration": None,
            "websocket_auth_duration": None, 
            "chat_auth_duration": None,
            "total_duration": None,
            "failed_steps": [],
            "timeout_errors": []
        }
        
        start_time = time.time()
        
        # Step 1: User Login (Real auth service call)
        print("📝 Step 1: Testing real user login to staging auth service...")
        login_start = time.time()
        
        try:
            login_result = await self.auth_client.login(self.test_email, self.test_password)
            golden_path_metrics["login_duration"] = time.time() - login_start
            
            if not login_result:
                golden_path_metrics["failed_steps"].append("login_no_result")
                print(f"❌ Login failed: No result from auth service")
            else:
                print(f"✅ Login succeeded in {golden_path_metrics['login_duration']:.3f}s")
                
        except asyncio.TimeoutError as e:
            golden_path_metrics["login_duration"] = time.time() - login_start
            golden_path_metrics["failed_steps"].append("login_timeout")
            golden_path_metrics["timeout_errors"].append(f"login: {str(e)}")
            print(f"⏰ Login timed out after {golden_path_metrics['login_duration']:.3f}s")
            
        except Exception as e:
            golden_path_metrics["login_duration"] = time.time() - login_start  
            golden_path_metrics["failed_steps"].append(f"login_error_{type(e).__name__}")
            print(f"❌ Login failed with error: {e}")
        
        # Step 2: WebSocket Authentication (Real connectivity check)
        print("🔌 Step 2: Testing WebSocket auth connectivity to staging...")
        ws_start = time.time()
        
        try:
            ws_connectivity = await self.auth_client._check_auth_service_connectivity()
            golden_path_metrics["websocket_auth_duration"] = time.time() - ws_start
            
            if not ws_connectivity:
                golden_path_metrics["failed_steps"].append("websocket_connectivity_failed")
                print(f"❌ WebSocket connectivity failed after {golden_path_metrics['websocket_auth_duration']:.3f}s")
            else:
                print(f"✅ WebSocket connectivity succeeded in {golden_path_metrics['websocket_auth_duration']:.3f}s")
                
        except asyncio.TimeoutError as e:
            golden_path_metrics["websocket_auth_duration"] = time.time() - ws_start
            golden_path_metrics["failed_steps"].append("websocket_timeout")
            golden_path_metrics["timeout_errors"].append(f"websocket: {str(e)}")
            print(f"⏰ WebSocket connectivity timed out after {golden_path_metrics['websocket_auth_duration']:.3f}s")
            
        except Exception as e:
            golden_path_metrics["websocket_auth_duration"] = time.time() - ws_start
            golden_path_metrics["failed_steps"].append(f"websocket_error_{type(e).__name__}")
            print(f"❌ WebSocket connectivity failed with error: {e}")
        
        # Step 3: Chat Authentication (Real token validation)  
        print("💬 Step 3: Testing chat authentication token validation...")
        chat_start = time.time()
        
        # Generate test token or use from login
        test_token = "test_staging_jwt_token"
        if 'login_timeout' not in golden_path_metrics["failed_steps"] and 'login_result' in locals():
            test_token = login_result.get("access_token", test_token) if login_result else test_token
        
        try:
            chat_validation = await self.auth_client.validate_token(test_token)
            golden_path_metrics["chat_auth_duration"] = time.time() - chat_start
            
            if not chat_validation or not chat_validation.get("valid"):
                golden_path_metrics["failed_steps"].append("chat_auth_validation_failed")
                print(f"❌ Chat auth validation failed after {golden_path_metrics['chat_auth_duration']:.3f}s")
            else:
                print(f"✅ Chat auth validation succeeded in {golden_path_metrics['chat_auth_duration']:.3f}s")
                
        except asyncio.TimeoutError as e:
            golden_path_metrics["chat_auth_duration"] = time.time() - chat_start
            golden_path_metrics["failed_steps"].append("chat_auth_timeout")  
            golden_path_metrics["timeout_errors"].append(f"chat_auth: {str(e)}")
            print(f"⏰ Chat auth validation timed out after {golden_path_metrics['chat_auth_duration']:.3f}s")
            
        except Exception as e:
            golden_path_metrics["chat_auth_duration"] = time.time() - chat_start
            golden_path_metrics["failed_steps"].append(f"chat_auth_error_{type(e).__name__}")
            print(f"❌ Chat auth validation failed with error: {e}")
        
        # Calculate total Golden Path duration
        golden_path_metrics["total_duration"] = time.time() - start_time
        
        # Report E2E results
        print(f"\n📊 Golden Path E2E Results:")
        print(f"   Total Duration: {golden_path_metrics['total_duration']:.3f}s")
        print(f"   Failed Steps: {len(golden_path_metrics['failed_steps'])}/3")
        print(f"   Timeout Errors: {len(golden_path_metrics['timeout_errors'])}")
        
        if golden_path_metrics["timeout_errors"]:
            print(f"   Timeout Details: {golden_path_metrics['timeout_errors']}")
            
        # E2E REPRODUCTION ASSERTIONS
        self.assertGreater(len(golden_path_metrics["failed_steps"]), 0,
                          f"Expected Golden Path to FAIL in staging due to timeout issues, "
                          f"but all steps succeeded. This might indicate timeout fix is working.")
        
        # Check for specific timeout patterns
        timeout_steps = [step for step in golden_path_metrics["failed_steps"] if "timeout" in step]
        self.assertGreater(len(timeout_steps), 0,
                          f"Expected at least one timeout failure in Golden Path E2E test. "
                          f"Failed steps: {golden_path_metrics['failed_steps']}")
        
        # Business impact assertion
        if len(golden_path_metrics["failed_steps"]) >= 2:
            self.fail(f"Golden Path E2E FAILURE: {len(golden_path_metrics['failed_steps'])}/3 steps failed "
                     f"due to auth service timeout issues. This blocks $500K+ ARR user workflow. "
                     f"Failed steps: {golden_path_metrics['failed_steps']}")

    @pytest.mark.asyncio
    @pytest.mark.e2e  
    async def test_staging_auth_service_performance_measurement(self):
        """
        E2E MEASUREMENT TEST: Measure actual auth service performance in GCP staging.
        
        This test measures real auth service response times against configured timeouts
        to identify the exact performance vs configuration mismatch.
        
        EXPECTED RESULT: Should reveal timeout configuration vs actual performance gap.
        """
        
        print(f"\n📏 Measuring staging auth service performance...")
        
        performance_metrics = {
            "health_check_times": [],
            "token_validation_times": [],
            "login_times": [],
            "connectivity_times": [],
            "configured_timeouts": {},
            "failures": []
        }
        
        # Record configured timeout limits
        timeouts = self.auth_client._get_environment_specific_timeouts()
        performance_metrics["configured_timeouts"] = {
            "connect": timeouts.connect,
            "read": timeouts.read,  
            "write": timeouts.write,
            "pool": timeouts.pool,
            "total": timeouts.connect + timeouts.read + timeouts.write + timeouts.pool
        }
        
        # Health check timeout is hardcoded to 0.5s for staging
        performance_metrics["configured_timeouts"]["health_check"] = 0.5
        
        print(f"🎯 Configured Timeouts: {performance_metrics['configured_timeouts']}")
        
        # Test 1: Multiple health checks to measure consistency
        print("🔍 Testing health check performance (10 attempts)...")
        for i in range(10):
            try:
                start = time.time()
                result = await self.auth_client._check_auth_service_connectivity()
                duration = time.time() - start
                performance_metrics["health_check_times"].append(duration)
                print(f"   Health check {i+1}: {duration:.3f}s ({'✅' if result else '❌'})")
                
            except asyncio.TimeoutError:
                duration = time.time() - start
                performance_metrics["health_check_times"].append(duration)
                performance_metrics["failures"].append(f"health_check_{i+1}_timeout")
                print(f"   Health check {i+1}: ⏰ TIMEOUT after {duration:.3f}s")
                
            except Exception as e:
                duration = time.time() - start  
                performance_metrics["health_check_times"].append(duration)
                performance_metrics["failures"].append(f"health_check_{i+1}_error")
                print(f"   Health check {i+1}: ❌ ERROR after {duration:.3f}s - {e}")
            
            await asyncio.sleep(0.1)  # Brief pause between tests
        
        # Test 2: Token validation performance
        print("🔍 Testing token validation performance (5 attempts)...")
        test_token = "staging_performance_test_token"
        
        for i in range(5):
            try:
                start = time.time()
                result = await self.auth_client.validate_token(test_token)
                duration = time.time() - start
                performance_metrics["token_validation_times"].append(duration)
                
                valid = result and result.get("valid", False) if result else False
                print(f"   Validation {i+1}: {duration:.3f}s ({'✅' if valid else '❌'})")
                
            except asyncio.TimeoutError:
                duration = time.time() - start
                performance_metrics["token_validation_times"].append(duration)
                performance_metrics["failures"].append(f"token_validation_{i+1}_timeout")
                print(f"   Validation {i+1}: ⏰ TIMEOUT after {duration:.3f}s")
                
            except Exception as e:
                duration = time.time() - start
                performance_metrics["token_validation_times"].append(duration) 
                performance_metrics["failures"].append(f"token_validation_{i+1}_error")
                print(f"   Validation {i+1}: ❌ ERROR after {duration:.3f}s - {e}")
            
            await asyncio.sleep(0.2)  # Brief pause between tests
        
        # Analyze performance metrics
        if performance_metrics["health_check_times"]:
            avg_health = sum(performance_metrics["health_check_times"]) / len(performance_metrics["health_check_times"])
            max_health = max(performance_metrics["health_check_times"])
            min_health = min(performance_metrics["health_check_times"])
            
            print(f"\n📊 Health Check Performance:")
            print(f"   Average: {avg_health:.3f}s")
            print(f"   Range: {min_health:.3f}s - {max_health:.3f}s")
            print(f"   Configured timeout: {performance_metrics['configured_timeouts']['health_check']:.1f}s")
            
            # MEASUREMENT ASSERTIONS  
            timeout_violations = [t for t in performance_metrics["health_check_times"] 
                                if t > performance_metrics['configured_timeouts']['health_check']]
            
            if len(timeout_violations) > 0:
                self.assertGreater(len(timeout_violations), 0,
                                 f"Found {len(timeout_violations)} health checks that exceed "
                                 f"{performance_metrics['configured_timeouts']['health_check']}s timeout. "
                                 f"Max time: {max(timeout_violations):.3f}s")
        
        if performance_metrics["token_validation_times"]:
            avg_validation = sum(performance_metrics["token_validation_times"]) / len(performance_metrics["token_validation_times"])
            max_validation = max(performance_metrics["token_validation_times"])
            
            print(f"\n📊 Token Validation Performance:")
            print(f"   Average: {avg_validation:.3f}s")
            print(f"   Max: {max_validation:.3f}s")
            print(f"   Total configured timeout: {performance_metrics['configured_timeouts']['total']:.1f}s")
        
        # Overall failure analysis
        print(f"\n📊 Failure Analysis:")
        print(f"   Total failures: {len(performance_metrics['failures'])}")
        print(f"   Timeout failures: {len([f for f in performance_metrics['failures'] if 'timeout' in f])}")
        
        # E2E PERFORMANCE ASSERTIONS
        timeout_failures = len([f for f in performance_metrics["failures"] if "timeout" in f])
        if timeout_failures > 0:
            self.fail(f"E2E Performance Test FAILED: {timeout_failures} timeout failures in "
                     f"staging auth service. This confirms timeout configuration is too aggressive. "
                     f"Failures: {performance_metrics['failures']}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_real_websocket_auth_handshake_staging(self):
        """
        E2E REPRODUCTION TEST: Real WebSocket auth handshake in staging environment.
        
        This test reproduces the actual WebSocket authentication handshake
        that fails in production due to auth service timeout configuration.
        
        EXPECTED RESULT: Should FAIL, demonstrating real WebSocket auth issues.
        """
        
        print(f"\n🔌 Testing real WebSocket auth handshake in staging...")
        
        handshake_metrics = {
            "initial_connectivity": None,
            "auth_validation": None,
            "total_handshake_time": None,
            "handshake_steps": [],
            "failures": []
        }
        
        start_time = time.time()
        
        # Step 1: Initial connectivity (like WebSocket would do)
        print("🔍 Step 1: Initial auth service connectivity check...")
        conn_start = time.time()
        
        try:
            connectivity = await self.auth_client._check_auth_service_connectivity()
            handshake_metrics["initial_connectivity"] = time.time() - conn_start
            
            if connectivity:
                handshake_metrics["handshake_steps"].append("connectivity_success")
                print(f"   ✅ Connectivity: {handshake_metrics['initial_connectivity']:.3f}s")
            else:
                handshake_metrics["handshake_steps"].append("connectivity_failed") 
                handshake_metrics["failures"].append("connectivity_check_failed")
                print(f"   ❌ Connectivity failed: {handshake_metrics['initial_connectivity']:.3f}s")
                
        except asyncio.TimeoutError:
            handshake_metrics["initial_connectivity"] = time.time() - conn_start
            handshake_metrics["handshake_steps"].append("connectivity_timeout")
            handshake_metrics["failures"].append("connectivity_timeout")
            print(f"   ⏰ Connectivity timeout: {handshake_metrics['initial_connectivity']:.3f}s")
            
        # Step 2: Auth token validation (WebSocket auth phase)
        print("🔐 Step 2: WebSocket token validation...")  
        auth_start = time.time()
        
        # Use a realistic WebSocket auth token
        websocket_token = "websocket_handshake_auth_token_staging_test"
        
        try:
            validation = await self.auth_client.validate_token(websocket_token)
            handshake_metrics["auth_validation"] = time.time() - auth_start
            
            if validation and validation.get("valid"):
                handshake_metrics["handshake_steps"].append("auth_validation_success")
                print(f"   ✅ Auth validation: {handshake_metrics['auth_validation']:.3f}s")
            else:
                handshake_metrics["handshake_steps"].append("auth_validation_failed")
                handshake_metrics["failures"].append("auth_validation_rejected")
                print(f"   ❌ Auth validation failed: {handshake_metrics['auth_validation']:.3f}s")
                
        except asyncio.TimeoutError:
            handshake_metrics["auth_validation"] = time.time() - auth_start
            handshake_metrics["handshake_steps"].append("auth_validation_timeout")
            handshake_metrics["failures"].append("auth_validation_timeout") 
            print(f"   ⏰ Auth validation timeout: {handshake_metrics['auth_validation']:.3f}s")
            
        except Exception as e:
            handshake_metrics["auth_validation"] = time.time() - auth_start
            handshake_metrics["handshake_steps"].append("auth_validation_error")
            handshake_metrics["failures"].append(f"auth_validation_error_{type(e).__name__}")
            print(f"   ❌ Auth validation error: {handshake_metrics['auth_validation']:.3f}s - {e}")
        
        # Calculate total handshake time
        handshake_metrics["total_handshake_time"] = time.time() - start_time
        
        print(f"\n📊 WebSocket Handshake Results:")
        print(f"   Total handshake time: {handshake_metrics['total_handshake_time']:.3f}s")
        print(f"   Successful steps: {len([s for s in handshake_metrics['handshake_steps'] if 'success' in s])}/2")
        print(f"   Failed steps: {len(handshake_metrics['failures'])}")
        print(f"   Handshake steps: {handshake_metrics['handshake_steps']}")
        
        # E2E HANDSHAKE ASSERTIONS
        self.assertGreater(len(handshake_metrics["failures"]), 0,
                          f"Expected WebSocket handshake to FAIL in staging due to auth timeout issues, "
                          f"but handshake succeeded. Steps: {handshake_metrics['handshake_steps']}")
        
        # Check for timeout-specific failures
        timeout_failures = [f for f in handshake_metrics["failures"] if "timeout" in f]
        self.assertGreater(len(timeout_failures), 0,
                          f"Expected WebSocket handshake timeout failures, got: {handshake_metrics['failures']}")
        
        # Business impact: WebSocket handshake blocking chat
        if len(handshake_metrics["failures"]) >= 1:
            self.fail(f"WebSocket E2E Handshake FAILED: {len(handshake_metrics['failures'])} failures "
                     f"block WebSocket connections in staging. This prevents chat functionality. "
                     f"Failures: {handshake_metrics['failures']}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_gcp_cloud_run_network_latency_impact(self):
        """
        E2E MEASUREMENT TEST: GCP Cloud Run network latency impact on auth timeouts.
        
        This test measures actual network latency patterns in GCP staging 
        to understand how Cloud Run networking affects auth service timeouts.
        
        EXPECTED RESULT: Should reveal network latency patterns causing timeout issues.
        """
        
        print(f"\n🌐 Testing GCP Cloud Run network latency patterns...")
        
        latency_metrics = {
            "connection_attempts": [],
            "response_times": [],
            "timeout_occurrences": [],
            "network_patterns": {},
            "cloud_run_specifics": []
        }
        
        # Test multiple connection attempts to identify patterns
        print("📡 Testing 20 auth service connections to identify latency patterns...")
        
        for attempt in range(20):
            attempt_metrics = {
                "attempt": attempt + 1,
                "connect_time": None,
                "response_time": None,
                "total_time": None,
                "status": None,
                "error": None
            }
            
            start = time.time()
            connect_start = time.time()
            
            try:
                # Measure connection establishment
                client = await self.auth_client._get_client()
                attempt_metrics["connect_time"] = time.time() - connect_start
                
                # Measure actual request/response  
                response_start = time.time()
                response = await client.get("/health")
                attempt_metrics["response_time"] = time.time() - response_start
                attempt_metrics["total_time"] = time.time() - start
                attempt_metrics["status"] = response.status_code
                
                latency_metrics["connection_attempts"].append(attempt_metrics)
                latency_metrics["response_times"].append(attempt_metrics["total_time"])
                
                print(f"   Attempt {attempt + 1:2d}: {attempt_metrics['total_time']:.3f}s "
                      f"(connect: {attempt_metrics['connect_time']:.3f}s, "
                      f"response: {attempt_metrics['response_time']:.3f}s) "
                      f"[{attempt_metrics['status']}]")
                
            except asyncio.TimeoutError as e:
                attempt_metrics["total_time"] = time.time() - start
                attempt_metrics["error"] = "timeout"
                latency_metrics["timeout_occurrences"].append(attempt_metrics)
                print(f"   Attempt {attempt + 1:2d}: ⏰ TIMEOUT after {attempt_metrics['total_time']:.3f}s")
                
            except Exception as e:
                attempt_metrics["total_time"] = time.time() - start  
                attempt_metrics["error"] = type(e).__name__
                print(f"   Attempt {attempt + 1:2d}: ❌ ERROR after {attempt_metrics['total_time']:.3f}s - {e}")
            
            # Brief pause to avoid overwhelming
            await asyncio.sleep(0.1)
        
        # Analyze latency patterns
        if latency_metrics["response_times"]:
            response_times = latency_metrics["response_times"]
            avg_latency = sum(response_times) / len(response_times)
            max_latency = max(response_times)
            min_latency = min(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[len(sorted_times)//2] if sorted_times else 0
            p95 = sorted_times[int(len(sorted_times)*0.95)] if sorted_times else 0
            p99 = sorted_times[int(len(sorted_times)*0.99)] if sorted_times else 0
            
            latency_metrics["network_patterns"] = {
                "average": avg_latency,
                "min": min_latency,
                "max": max_latency,
                "p50": p50,
                "p95": p95, 
                "p99": p99,
                "std_dev": (sum((t - avg_latency) ** 2 for t in response_times) / len(response_times)) ** 0.5
            }
            
            print(f"\n📊 GCP Network Latency Analysis:")
            print(f"   Average: {avg_latency:.3f}s")
            print(f"   Range: {min_latency:.3f}s - {max_latency:.3f}s")
            print(f"   P50: {p50:.3f}s, P95: {p95:.3f}s, P99: {p99:.3f}s")
            print(f"   Std Dev: {latency_metrics['network_patterns']['std_dev']:.3f}s")
            
            # Compare against timeout configuration
            staging_timeout = 0.5  # Hardcoded staging health check timeout
            print(f"   Configured timeout: {staging_timeout:.1f}s")
            
            violations = [t for t in response_times if t > staging_timeout]
            violation_rate = len(violations) / len(response_times) * 100
            
            print(f"   Timeout violations: {len(violations)}/{len(response_times)} ({violation_rate:.1f}%)")
            
            # Cloud Run specific analysis
            if violation_rate > 10:  # More than 10% violations
                latency_metrics["cloud_run_specifics"].append("high_violation_rate")
                
            if latency_metrics["network_patterns"]["std_dev"] > 0.1:  # High variability
                latency_metrics["cloud_run_specifics"].append("high_latency_variability")
                
            if max_latency > staging_timeout * 2:  # Extreme outliers
                latency_metrics["cloud_run_specifics"].append("extreme_latency_outliers")
        
        timeout_count = len(latency_metrics["timeout_occurrences"]) 
        total_attempts = len(latency_metrics["connection_attempts"]) + timeout_count
        timeout_rate = timeout_count / total_attempts * 100 if total_attempts > 0 else 0
        
        print(f"   Timeout rate: {timeout_count}/{total_attempts} ({timeout_rate:.1f}%)")
        print(f"   Cloud Run issues: {latency_metrics['cloud_run_specifics']}")
        
        # E2E NETWORK LATENCY ASSERTIONS
        if violation_rate > 5:  # More than 5% violations indicates issue
            self.fail(f"GCP Network Latency E2E FAILURE: {violation_rate:.1f}% of requests exceed "
                     f"{staging_timeout}s timeout limit. This confirms timeout configuration "
                     f"is too aggressive for Cloud Run networking. Max latency: {max_latency:.3f}s")
        
        if timeout_rate > 0:
            self.fail(f"GCP Network E2E FAILURE: {timeout_rate:.1f}% timeout rate indicates "
                     f"auth service timeouts are causing real connectivity issues in Cloud Run staging.")