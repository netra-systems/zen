"""
Integration tests to reproduce auth service circuit breaker timeout issues (Issue #395).

REPRODUCTION TARGET: Circuit breaker timeout interactions with 0.5s staging timeouts.
These tests SHOULD FAIL initially to demonstrate how circuit breaker and timeout configurations interact.

Key Circuit Breaker Issues to Reproduce:
1. Circuit breaker opening due to repeated 0.5s timeout failures
2. 3.0s call timeout vs 0.5s health check timeout mismatch
3. Circuit breaker preventing auth recovery after timeout fixes
4. Cascading auth failures due to circuit breaker state
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.clients.circuit_breaker import CircuitBreakerOpen, CircuitBreakerHalfOpen
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestAuthCircuitBreakerTimeout(SSotAsyncTestCase):
    """
    Integration tests to reproduce circuit breaker and timeout configuration issues.
    
    These tests simulate how the circuit breaker interacts with aggressive timeout
    configuration to create cascading auth service failures.
    """
    
    async def asyncSetUp(self):
        """Set up test environment with staging configuration and circuit breaker."""
        await super().asyncSetUp()
        
        # Mock staging environment to trigger aggressive timeouts
        self.mock_env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.mock_env_patcher.start()
        self.mock_env.return_value.get.return_value = "staging"
        
        self.auth_client = AuthServiceClient()
        
        # Access circuit breaker configuration
        self.circuit_breaker = self.auth_client.circuit_breaker
        self.original_config = {
            "failure_threshold": self.circuit_breaker.failure_threshold,
            "success_threshold": self.circuit_breaker.success_threshold, 
            "timeout": self.circuit_breaker.timeout,
            "call_timeout": self.circuit_breaker.call_timeout
        }
    
    async def asyncTearDown(self):
        """Clean up test environment and reset circuit breaker."""
        # Reset circuit breaker state
        if hasattr(self.circuit_breaker, '_state'):
            self.circuit_breaker._state = "closed"
        if hasattr(self.circuit_breaker, '_failure_count'):
            self.circuit_breaker._failure_count = 0
            
        self.mock_env_patcher.stop()
        if self.auth_client._client:
            await self.auth_client._client.aclose()
        await super().asyncTearDown()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_from_timeout_failures(self):
        """
        REPRODUCTION TEST: Circuit breaker opens due to repeated 0.5s timeout failures.
        
        This test reproduces how the 0.5s staging timeout causes repeated failures
        that trigger the circuit breaker to open, blocking further auth attempts.
        
        EXPECTED RESULT: Should FAIL as circuit breaker opens due to timeouts.
        """
        
        failure_count = 0
        
        async def mock_timeout_failures(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            
            # Simulate staging timeout failures
            await asyncio.sleep(0.1)  # Brief processing  
            raise asyncio.TimeoutError(f"Staging timeout failure #{failure_count} (0.5s exceeded)")
        
        with patch.object(self.auth_client, '_validate_token_remote') as mock_validate:
            mock_validate.side_effect = mock_timeout_failures
            
            # Test multiple auth attempts to trigger circuit breaker
            circuit_breaker_opened = False
            attempts = []
            
            for attempt in range(5):  # More than failure threshold (3)
                try:
                    start_time = time.time()
                    result = await self.auth_client.validate_token(f"test_token_{attempt}")
                    duration = time.time() - start_time
                    
                    attempts.append({
                        "attempt": attempt + 1,
                        "duration": duration,
                        "result": "success" if result and result.get("valid") else "failure",
                        "exception": None
                    })
                    
                except CircuitBreakerOpen:
                    duration = time.time() - start_time
                    circuit_breaker_opened = True
                    attempts.append({
                        "attempt": attempt + 1, 
                        "duration": duration,
                        "result": "circuit_breaker_open",
                        "exception": "CircuitBreakerOpen"
                    })
                    
                except Exception as e:
                    duration = time.time() - start_time
                    attempts.append({
                        "attempt": attempt + 1,
                        "duration": duration, 
                        "result": "exception",
                        "exception": type(e).__name__
                    })
            
            print(f"\nCircuit Breaker Test Results:")
            for attempt in attempts:
                print(f"  Attempt {attempt['attempt']}: {attempt['result']} "
                      f"({attempt['duration']:.3f}s) {attempt['exception'] or ''}")
            
            # REPRODUCTION ASSERTION: Circuit breaker should open due to timeouts
            self.assertTrue(circuit_breaker_opened,
                          f"Expected circuit breaker to OPEN due to repeated timeout failures, "
                          f"but it remained closed after {len(attempts)} attempts")
            
            # Verify timeout failures led to circuit breaker opening
            timeout_failures = [a for a in attempts if "timeout" in str(a.get("exception", "")).lower()]
            circuit_breaker_blocks = [a for a in attempts if a["result"] == "circuit_breaker_open"]
            
            self.assertGreaterEqual(len(timeout_failures), 2,
                                   f"Expected multiple timeout failures, got {len(timeout_failures)}")
            self.assertGreater(len(circuit_breaker_blocks), 0,
                              f"Expected circuit breaker blocks, got {len(circuit_breaker_blocks)}")

    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout_configuration_mismatch(self):
        """
        REPRODUCTION TEST: Circuit breaker timeout vs staging timeout mismatch.
        
        This test reproduces the configuration issue where:
        - Circuit breaker call_timeout = 3.0s
        - Staging health check timeout = 0.5s
        - This mismatch causes inconsistent timeout behavior
        
        EXPECTED RESULT: Should demonstrate timeout configuration conflicts.
        """
        
        print(f"\nTesting timeout configuration mismatch:")
        print(f"  Circuit breaker call_timeout: {self.original_config['call_timeout']}s")
        print(f"  Staging health check timeout: 0.5s")
        print(f"  Configuration mismatch ratio: {self.original_config['call_timeout'] / 0.5:.1f}x")
        
        # Mock auth service response that takes 1.5s (between 0.5s and 3.0s)
        async def mock_intermediate_timeout(*args, **kwargs):
            await asyncio.sleep(1.5)  # Between health check (0.5s) and call timeout (3.0s)
            return {
                "valid": True,
                "user_id": "test_user",
                "email": "test@example.com"
            }
        
        timeout_results = {
            "health_check_results": [],
            "validation_results": [],
            "configuration_conflicts": []
        }
        
        # Test 1: Health check with 0.5s timeout
        print(f"  Testing health check with 0.5s timeout...")
        for i in range(3):
            try:
                start = time.time()
                # Health check uses hardcoded 0.5s timeout for staging
                connectivity = await self.auth_client._check_auth_service_connectivity()
                duration = time.time() - start
                
                timeout_results["health_check_results"].append({
                    "attempt": i + 1,
                    "duration": duration,
                    "result": "success" if connectivity else "failure"
                })
                
            except asyncio.TimeoutError:
                duration = time.time() - start
                timeout_results["health_check_results"].append({
                    "attempt": i + 1,
                    "duration": duration,
                    "result": "timeout"
                })
                
                # This demonstrates the 0.5s timeout is too aggressive
                if duration < 0.6:  # Timed out before 1.5s service response
                    timeout_results["configuration_conflicts"].append(
                        f"health_check_timeout_{i+1}_too_aggressive"
                    )
        
        # Test 2: Circuit breaker call with 3.0s timeout
        print(f"  Testing circuit breaker call with 3.0s timeout...")
        
        with patch.object(self.auth_client, '_validate_token_remote') as mock_validate:
            mock_validate.side_effect = mock_intermediate_timeout
            
            for i in range(3):
                try:
                    start = time.time()
                    # This goes through circuit breaker with 3.0s call_timeout
                    result = await self.auth_client.validate_token(f"test_token_{i}")
                    duration = time.time() - start
                    
                    timeout_results["validation_results"].append({
                        "attempt": i + 1,
                        "duration": duration,
                        "result": "success" if result and result.get("valid") else "failure"
                    })
                    
                    # 1.5s response should succeed with 3.0s circuit breaker timeout
                    if duration > 1.4 and duration < 1.8:  # Around 1.5s
                        timeout_results["configuration_conflicts"].append(
                            f"circuit_breaker_succeeds_where_health_check_fails_{i+1}"
                        )
                        
                except asyncio.TimeoutError:
                    duration = time.time() - start
                    timeout_results["validation_results"].append({
                        "attempt": i + 1,
                        "duration": duration,
                        "result": "timeout"
                    })
        
        # Analyze configuration mismatch
        health_timeouts = [r for r in timeout_results["health_check_results"] if r["result"] == "timeout"]
        validation_successes = [r for r in timeout_results["validation_results"] if r["result"] == "success"]
        
        print(f"\n  Results:")
        print(f"    Health check timeouts: {len(health_timeouts)}/3")
        print(f"    Validation successes: {len(validation_successes)}/3")
        print(f"    Configuration conflicts: {len(timeout_results['configuration_conflicts'])}")
        
        # REPRODUCTION ASSERTION: Configuration mismatch causes inconsistent behavior
        if len(health_timeouts) > 0 and len(validation_successes) > 0:
            self.fail(f"Configuration Mismatch REPRODUCED: Health checks fail with 0.5s timeout "
                     f"({len(health_timeouts)} failures) while circuit breaker succeeds with 3.0s timeout "
                     f"({len(validation_successes)} successes). This inconsistency causes auth reliability issues.")
        
        # At minimum, show the configuration mismatch exists
        self.assertGreater(self.original_config['call_timeout'], 0.5 * 2,
                          f"Circuit breaker timeout ({self.original_config['call_timeout']}s) should be "
                          f"much higher than health check timeout (0.5s), indicating configuration mismatch")

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_auth_recovery(self):
        """
        REPRODUCTION TEST: Circuit breaker prevents auth recovery after timeout fixes.
        
        This test simulates how circuit breaker opening due to timeout issues
        prevents auth service from recovering even after timeout configuration is fixed.
        
        EXPECTED RESULT: Should show circuit breaker blocking recovery.
        """
        
        recovery_test = {
            "initial_failures": [],
            "circuit_breaker_state": "closed", 
            "recovery_attempts": [],
            "final_state": None
        }
        
        # Phase 1: Cause circuit breaker to open with timeout failures
        print(f"Phase 1: Causing circuit breaker to open...")
        
        async def mock_initial_timeouts(*args, **kwargs):
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError("Initial staging timeout causing circuit breaker to open")
        
        with patch.object(self.auth_client, '_validate_token_remote') as mock_validate:
            mock_validate.side_effect = mock_initial_timeouts
            
            # Attempt auth until circuit breaker opens
            for attempt in range(5):
                try:
                    result = await self.auth_client.validate_token(f"initial_token_{attempt}")
                    recovery_test["initial_failures"].append(f"attempt_{attempt}_unexpected_success")
                    
                except CircuitBreakerOpen:
                    recovery_test["initial_failures"].append(f"attempt_{attempt}_circuit_breaker_open")
                    recovery_test["circuit_breaker_state"] = "open"
                    print(f"  Circuit breaker opened after {attempt + 1} attempts")
                    break
                    
                except Exception as e:
                    recovery_test["initial_failures"].append(f"attempt_{attempt}_{type(e).__name__}")
        
        # Verify circuit breaker is open
        self.assertEqual(recovery_test["circuit_breaker_state"], "open",
                        f"Expected circuit breaker to open, got state: {recovery_test['circuit_breaker_state']}")
        
        # Phase 2: Simulate "fixed" auth service (now responds quickly)
        print(f"Phase 2: Testing recovery with 'fixed' auth service...")
        
        async def mock_fixed_auth_service(*args, **kwargs):
            await asyncio.sleep(0.1)  # Fast, healthy response
            return {
                "valid": True,
                "user_id": "recovered_user",
                "email": "recovery@test.com"
            }
        
        with patch.object(self.auth_client, '_validate_token_remote') as mock_validate:
            mock_validate.side_effect = mock_fixed_auth_service
            
            # Attempt auth recovery - circuit breaker should block these
            for attempt in range(3):
                try:
                    start = time.time()
                    result = await self.auth_client.validate_token(f"recovery_token_{attempt}")
                    duration = time.time() - start
                    
                    success = result and result.get("valid", False)
                    recovery_test["recovery_attempts"].append({
                        "attempt": attempt + 1,
                        "duration": duration,
                        "result": "success" if success else "failure",
                        "user_id": result.get("user_id") if result else None
                    })
                    
                except CircuitBreakerOpen:
                    duration = time.time() - start
                    recovery_test["recovery_attempts"].append({
                        "attempt": attempt + 1,
                        "duration": duration,
                        "result": "circuit_breaker_blocked",
                        "user_id": None
                    })
                    
                except Exception as e:
                    duration = time.time() - start
                    recovery_test["recovery_attempts"].append({
                        "attempt": attempt + 1,
                        "duration": duration,
                        "result": f"error_{type(e).__name__}",
                        "user_id": None
                    })
        
        # Analyze recovery results
        blocked_attempts = [a for a in recovery_test["recovery_attempts"] if "circuit_breaker_blocked" in a["result"]]
        successful_attempts = [a for a in recovery_test["recovery_attempts"] if a["result"] == "success"]
        
        recovery_test["final_state"] = {
            "blocked_by_circuit_breaker": len(blocked_attempts),
            "successful_recoveries": len(successful_attempts),
            "total_attempts": len(recovery_test["recovery_attempts"])
        }
        
        print(f"\n  Recovery Results:")
        print(f"    Blocked by circuit breaker: {len(blocked_attempts)}")
        print(f"    Successful recoveries: {len(successful_attempts)}")
        print(f"    Total recovery attempts: {len(recovery_test['recovery_attempts'])}")
        
        for attempt in recovery_test["recovery_attempts"]:
            print(f"    Recovery {attempt['attempt']}: {attempt['result']} ({attempt['duration']:.3f}s)")
        
        # REPRODUCTION ASSERTION: Circuit breaker prevents recovery
        self.assertGreater(len(blocked_attempts), 0,
                          f"Expected circuit breaker to BLOCK recovery attempts, "
                          f"but {len(successful_attempts)} attempts succeeded")
        
        # Circuit breaker should block most/all recovery attempts  
        if len(blocked_attempts) >= len(successful_attempts):
            self.fail(f"Circuit Breaker Recovery BLOCKED: {len(blocked_attempts)} recovery attempts "
                     f"blocked by circuit breaker vs {len(successful_attempts)} successful. "
                     f"Circuit breaker prevents auth service recovery even after timeout fixes.")

    @pytest.mark.asyncio
    async def test_cascading_auth_failures_circuit_breaker_timeout(self):
        """
        REPRODUCTION TEST: Cascading auth failures due to circuit breaker and timeout interaction.
        
        This test reproduces the complete cascade:
        1. 0.5s timeouts cause auth failures
        2. Circuit breaker opens after 3 failures  
        3. All subsequent auth blocked for 10s
        4. WebSocket/chat/user flows completely broken
        
        EXPECTED RESULT: Should demonstrate complete auth system failure cascade.
        """
        
        cascade_timeline = {
            "timeout_phase": [],
            "circuit_breaker_phase": [],
            "system_impact_phase": [],
            "cascade_duration": None,
            "business_impact": []
        }
        
        start_time = time.time()
        
        # Phase 1: Timeout failures (0.5s staging timeout)
        print(f"Phase 1: Timeout failure cascade...")
        
        async def mock_staging_timeouts(*args, **kwargs):
            await asyncio.sleep(0.6)  # Above 0.5s staging timeout
            raise asyncio.TimeoutError("Staging 0.5s timeout exceeded")
        
        with patch.object(self.auth_client, '_check_auth_service_connectivity') as mock_connectivity:
            mock_connectivity.side_effect = mock_staging_timeouts
            
            # Generate timeout failures until circuit breaker opens
            for failure in range(4):  # One more than circuit breaker threshold
                try:
                    failure_start = time.time()
                    result = await self.auth_client.validate_token(f"cascade_token_{failure}")
                    duration = time.time() - failure_start
                    
                    cascade_timeline["timeout_phase"].append({
                        "failure": failure + 1,
                        "duration": duration,
                        "result": "unexpected_success",
                        "timestamp": time.time() - start_time
                    })
                    
                except asyncio.TimeoutError:
                    duration = time.time() - failure_start
                    cascade_timeline["timeout_phase"].append({
                        "failure": failure + 1,
                        "duration": duration,
                        "result": "timeout",
                        "timestamp": time.time() - start_time
                    })
                    
                except CircuitBreakerOpen:
                    duration = time.time() - failure_start
                    cascade_timeline["circuit_breaker_phase"].append({
                        "attempt": failure + 1,
                        "duration": duration,
                        "result": "circuit_breaker_open",
                        "timestamp": time.time() - start_time
                    })
                    print(f"  Circuit breaker opened after {failure + 1} timeout failures")
                    break
                    
                except Exception as e:
                    duration = time.time() - failure_start
                    cascade_timeline["timeout_phase"].append({
                        "failure": failure + 1,
                        "duration": duration,
                        "result": f"error_{type(e).__name__}",
                        "timestamp": time.time() - start_time
                    })
        
        # Phase 2: Circuit breaker blocking phase (should last ~10s)
        print(f"Phase 2: Circuit breaker blocking cascade...")
        
        # Test multiple auth operations that would be blocked
        blocked_operations = [
            "user_login",
            "websocket_handshake", 
            "chat_authentication",
            "agent_execution_auth",
            "api_request_auth"
        ]
        
        for operation in blocked_operations:
            try:
                operation_start = time.time()
                result = await self.auth_client.validate_token(f"{operation}_token")
                duration = time.time() - operation_start
                
                cascade_timeline["circuit_breaker_phase"].append({
                    "operation": operation,
                    "duration": duration,
                    "result": "unexpected_success",
                    "timestamp": time.time() - start_time
                })
                
            except CircuitBreakerOpen:
                duration = time.time() - operation_start
                cascade_timeline["circuit_breaker_phase"].append({
                    "operation": operation,
                    "duration": duration,
                    "result": "circuit_breaker_blocked",
                    "timestamp": time.time() - start_time
                })
                
                # Map to business impact
                if operation == "user_login":
                    cascade_timeline["business_impact"].append("user_login_blocked")
                elif operation == "websocket_handshake":
                    cascade_timeline["business_impact"].append("websocket_connections_blocked")
                elif operation == "chat_authentication":
                    cascade_timeline["business_impact"].append("chat_functionality_blocked")
                elif operation == "agent_execution_auth":
                    cascade_timeline["business_impact"].append("agent_system_blocked")
                    
            except Exception as e:
                duration = time.time() - operation_start
                cascade_timeline["circuit_breaker_phase"].append({
                    "operation": operation,
                    "duration": duration,
                    "result": f"error_{type(e).__name__}",
                    "timestamp": time.time() - start_time
                })
        
        cascade_timeline["cascade_duration"] = time.time() - start_time
        
        # Analyze cascade impact
        timeout_failures = len([p for p in cascade_timeline["timeout_phase"] if p["result"] == "timeout"])
        circuit_breaker_blocks = len([p for p in cascade_timeline["circuit_breaker_phase"] if "blocked" in p["result"]])
        business_systems_affected = len(cascade_timeline["business_impact"])
        
        print(f"\n🚨 Cascading Failure Analysis:")
        print(f"   Timeout failures: {timeout_failures}")
        print(f"   Circuit breaker blocks: {circuit_breaker_blocks}")
        print(f"   Business systems affected: {business_systems_affected}")
        print(f"   Total cascade duration: {cascade_timeline['cascade_duration']:.3f}s")
        print(f"   Business impact: {cascade_timeline['business_impact']}")
        
        # REPRODUCTION ASSERTION: Complete system cascade failure
        self.assertGreaterEqual(timeout_failures, 2,
                               f"Expected multiple timeout failures to trigger cascade, got {timeout_failures}")
        
        self.assertGreater(circuit_breaker_blocks, 0,
                          f"Expected circuit breaker to block operations after timeouts, got {circuit_breaker_blocks}")
        
        self.assertGreaterEqual(business_systems_affected, 3,
                               f"Expected multiple business systems affected, got {business_systems_affected}")
        
        # Critical business impact assertion
        critical_systems = ["user_login_blocked", "chat_functionality_blocked", "websocket_connections_blocked"]
        critical_affected = [impact for impact in cascade_timeline["business_impact"] if impact in critical_systems]
        
        if len(critical_affected) >= 2:
            self.fail(f"CASCADING FAILURE REPRODUCED: Timeout -> Circuit Breaker cascade blocks "
                     f"{len(critical_affected)} critical business systems: {critical_affected}. "
                     f"This represents complete auth system failure affecting $500K+ ARR user workflows.")

    @pytest.mark.asyncio
    async def test_circuit_breaker_configuration_analysis(self):
        """
        INTEGRATION TEST: Analysis of circuit breaker configuration for timeout compatibility.
        
        This test analyzes the current circuit breaker configuration and identifies
        how it interacts with staging timeout settings to cause issues.
        
        EXPECTED RESULT: Should reveal configuration incompatibilities.
        """
        
        # Analyze current configuration
        config_analysis = {
            "circuit_breaker_config": self.original_config,
            "staging_timeouts": {
                "health_check": 0.5,
                "httpx_connect": 1.0,
                "httpx_read": 2.0,
                "httpx_write": 1.0,
                "httpx_pool": 2.0
            },
            "compatibility_issues": [],
            "recommendations": []
        }
        
        # Get actual staging timeouts  
        staging_timeouts = self.auth_client._get_environment_specific_timeouts()
        config_analysis["staging_timeouts"].update({
            "httpx_connect": staging_timeouts.connect,
            "httpx_read": staging_timeouts.read,
            "httpx_write": staging_timeouts.write,  
            "httpx_pool": staging_timeouts.pool,
            "httpx_total": (staging_timeouts.connect + staging_timeouts.read + 
                           staging_timeouts.write + staging_timeouts.pool)
        })
        
        print(f"\n🔧 Circuit Breaker Configuration Analysis:")
        print(f"Circuit Breaker Settings:")
        for key, value in config_analysis["circuit_breaker_config"].items():
            print(f"  {key}: {value}")
            
        print(f"\nStaging Timeout Settings:")
        for key, value in config_analysis["staging_timeouts"].items():
            print(f"  {key}: {value}")
        
        # Identify compatibility issues
        
        # Issue 1: Circuit breaker call_timeout vs health check timeout
        if config_analysis["circuit_breaker_config"]["call_timeout"] > config_analysis["staging_timeouts"]["health_check"] * 5:
            config_analysis["compatibility_issues"].append({
                "issue": "circuit_breaker_health_check_timeout_mismatch",
                "description": f"Circuit breaker call_timeout ({config_analysis['circuit_breaker_config']['call_timeout']}s) "
                              f"is {config_analysis['circuit_breaker_config']['call_timeout'] / config_analysis['staging_timeouts']['health_check']:.1f}x "
                              f"larger than health check timeout ({config_analysis['staging_timeouts']['health_check']}s)",
                "impact": "Health checks timeout before circuit breaker call timeout, causing inconsistent behavior"
            })
            
        # Issue 2: Circuit breaker timeout vs httpx total timeout
        if config_analysis["circuit_breaker_config"]["timeout"] < config_analysis["staging_timeouts"]["httpx_total"]:
            config_analysis["compatibility_issues"].append({
                "issue": "circuit_breaker_recovery_too_fast",
                "description": f"Circuit breaker recovery timeout ({config_analysis['circuit_breaker_config']['timeout']}s) "
                              f"is shorter than total HTTP timeout ({config_analysis['staging_timeouts']['httpx_total']}s)",
                "impact": "Circuit breaker may attempt recovery before HTTP timeouts are resolved"
            })
            
        # Issue 3: Failure threshold too low for staging timeout sensitivity
        if config_analysis["circuit_breaker_config"]["failure_threshold"] <= 3:
            config_analysis["compatibility_issues"].append({
                "issue": "failure_threshold_too_sensitive",
                "description": f"Failure threshold ({config_analysis['circuit_breaker_config']['failure_threshold']}) "
                              f"is too low for aggressive {config_analysis['staging_timeouts']['health_check']}s staging timeouts",
                "impact": "Circuit breaker opens too quickly due to natural staging timeout variations"
            })
        
        print(f"\n⚠️  Configuration Compatibility Issues Found: {len(config_analysis['compatibility_issues'])}")
        for issue in config_analysis["compatibility_issues"]:
            print(f"\n  Issue: {issue['issue']}")
            print(f"  Description: {issue['description']}")
            print(f"  Impact: {issue['impact']}")
        
        # Generate recommendations
        if len(config_analysis["compatibility_issues"]) > 0:
            config_analysis["recommendations"].extend([
                "Increase health check timeout from 0.5s to 2.0s for staging environment",
                "Align circuit breaker call_timeout with maximum expected auth service response time",
                "Increase failure_threshold to 5-7 for staging to accommodate network variability",
                "Set circuit breaker recovery timeout to 2x total HTTP timeout for proper recovery"
            ])
            
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(config_analysis["recommendations"], 1):
            print(f"  {i}. {rec}")
        
        # INTEGRATION ASSERTIONS: Configuration compatibility issues
        self.assertGreater(len(config_analysis["compatibility_issues"]), 0,
                          f"Expected to find circuit breaker timeout compatibility issues, "
                          f"but configuration appears compatible. This might indicate the "
                          f"timeout issue has been resolved.")
        
        # Specific assertions for known issues
        health_check_mismatch = any("health_check_timeout_mismatch" in issue["issue"] 
                                   for issue in config_analysis["compatibility_issues"])
        
        if health_check_mismatch:
            self.fail(f"Circuit Breaker Configuration INCOMPATIBILITY: Health check timeout "
                     f"({config_analysis['staging_timeouts']['health_check']}s) vs circuit breaker "
                     f"call timeout ({config_analysis['circuit_breaker_config']['call_timeout']}s) "
                     f"mismatch causes inconsistent auth behavior in staging environment.")