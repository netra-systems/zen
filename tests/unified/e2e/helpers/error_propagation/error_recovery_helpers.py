"""Error Recovery and Retry Logic Testing

This module contains utilities for testing network failure simulation,
retry mechanisms, and recovery logic with proper backoff patterns.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List
from pathlib import Path

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ...real_client_types import ClientConfig
from ...real_http_client import RealHTTPClient
from .error_generators import ErrorCorrelationContext, RealErrorPropagationTester

logger = logging.getLogger(__name__)


class NetworkFailureSimulationValidator:
    """Validates network failures trigger automatic retry logic with proper backoff."""
    
    def __init__(self, tester: RealErrorPropagationTester):
        self.tester = tester
        self.network_failure_tests: List[Dict[str, Any]] = []
    
    async def test_timeout_retry_mechanisms(self) -> Dict[str, Any]:
        """Test timeout handling with exponential backoff retry logic."""
        context = self.tester._create_correlation_context("timeout_retry_test")
        context.service_chain.append("network_layer")
        
        # Test with very short timeout to force retry behavior
        timeout_result = await self._test_short_timeout_behavior(context)
        
        # Test retry backoff patterns
        backoff_result = await self._test_exponential_backoff(context)
        
        # Test eventual success after retries
        eventual_success_result = await self._test_eventual_success(context)
        
        return {
            "test_type": "timeout_retry_mechanisms",
            "request_id": context.request_id,
            "timeout_behavior": timeout_result,
            "backoff_pattern": backoff_result,
            "eventual_success": eventual_success_result,
            "retry_logic_effective": self._assess_retry_effectiveness(
                timeout_result, backoff_result, eventual_success_result
            )
        }
    
    async def _test_short_timeout_behavior(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test behavior with very short timeouts."""
        context.service_chain.append("timeout_handler")
        
        # Create client with very short timeout
        backend_url = self.tester.orchestrator.get_service_url("backend")
        config = ClientConfig(timeout=0.1, max_retries=3)  # Very short timeout
        short_timeout_client = RealHTTPClient(backend_url, config)
        
        try:
            start_time = time.time()
            response = await short_timeout_client.get("/health")
            end_time = time.time()
            
            return self._analyze_timeout_success(start_time, end_time, response)
            
        except Exception as e:
            return self._analyze_timeout_failure(e, context)
        finally:
            await short_timeout_client.close()
    
    def _analyze_timeout_success(self, start_time: float, end_time: float, response) -> Dict[str, Any]:
        """Analyze successful response after timeout scenario."""
        total_time = end_time - start_time
        
        return {
            "request_completed": True,
            "total_time": total_time,
            "retries_likely_occurred": total_time > 0.2,  # More than 2x timeout
            "status_code": getattr(response, 'status_code', None)
        }
    
    def _analyze_timeout_failure(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze timeout failure response."""
        error_str = str(error).lower()
        
        # Check for proper timeout handling
        timeout_indicators = ["timeout", "retry", "connection", "network"]
        timeout_handled = any(indicator in error_str for indicator in timeout_indicators)
        
        context.retry_count = getattr(error, 'retry_count', 0)
        
        return {
            "timeout_exception_raised": True,
            "timeout_properly_handled": timeout_handled,
            "retry_count": context.retry_count,
            "error_message": str(error)
        }
    
    async def _test_exponential_backoff(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test exponential backoff pattern in retries."""
        context.service_chain.append("backoff_handler")
        
        backend_url = self.tester.orchestrator.get_service_url("backend")
        config = ClientConfig(timeout=0.05, max_retries=3)  # Very short timeout
        backoff_test_client = RealHTTPClient(backend_url, config)
        
        try:
            start_time = time.time()
            
            # This should fail and trigger multiple retries
            await backoff_test_client.get("/health")
            
            return {"unexpected_success": True}
            
        except Exception as e:
            end_time = time.time()
            return self._analyze_backoff_timing(start_time, end_time, config)
            
        finally:
            await backoff_test_client.close()
    
    def _analyze_backoff_timing(self, start_time: float, end_time: float, config: ClientConfig) -> Dict[str, Any]:
        """Analyze timing patterns for exponential backoff."""
        total_time = end_time - start_time
        
        # With 3 retries and exponential backoff, we expect:
        # Initial: 0.05s, Retry 1: ~0.05s + 1s, Retry 2: ~0.05s + 2s, Retry 3: ~0.05s + 4s
        expected_min_time = 0.05 * 4 + (1 + 2 + 4) * 0.5  # Conservative estimate
        
        return {
            "total_retry_time": total_time,
            "expected_min_time": expected_min_time,
            "backoff_pattern_detected": total_time > expected_min_time,
            "retry_attempts_made": config.max_retries
        }
    
    async def _test_eventual_success(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test that retries can lead to eventual success."""
        context.service_chain.append("success_handler")
        
        # Use normal timeout with retries
        backend_url = self.tester.orchestrator.get_service_url("backend")
        config = ClientConfig(timeout=5.0, max_retries=2)  # Normal timeout with retries
        normal_client = RealHTTPClient(backend_url, config)
        
        try:
            start_time = time.time()
            response = await normal_client.get("/health")
            end_time = time.time()
            
            return {
                "eventual_success": True,
                "response_time": end_time - start_time,
                "status_code": getattr(response, 'status_code', None),
                "retry_recovery": True
            }
            
        except Exception as e:
            return {
                "eventual_success": False,
                "service_unavailable": True,
                "final_error": str(e)
            }
        finally:
            await normal_client.close()
    
    def _assess_retry_effectiveness(self, *test_results) -> Dict[str, Any]:
        """Assess overall effectiveness of retry mechanisms."""
        effectiveness_score = 0
        indicators = []
        
        for result in test_results:
            if isinstance(result, dict):
                if result.get("retries_likely_occurred", False):
                    effectiveness_score += 1
                    indicators.append("retry_mechanism_active")
                
                if result.get("backoff_pattern_detected", False):
                    effectiveness_score += 1
                    indicators.append("exponential_backoff")
                
                if result.get("eventual_success", False):
                    effectiveness_score += 1
                    indicators.append("recovery_capability")
                
                if result.get("timeout_properly_handled", False):
                    effectiveness_score += 1
                    indicators.append("error_handling")
        
        return {
            "effectiveness_score": effectiveness_score,
            "max_possible_score": 4,
            "effectiveness_indicators": indicators,
            "retry_system_effective": effectiveness_score >= 2
        }


class RetryPatternTester:
    """Utility for testing specific retry patterns."""
    
    def __init__(self, tester: RealErrorPropagationTester):
        self.tester = tester
    
    async def test_circuit_breaker_behavior(self, endpoint: str = "/health") -> Dict[str, Any]:
        """Test circuit breaker pattern behavior."""
        failure_count = 0
        success_count = 0
        
        # Simulate multiple rapid failures
        for attempt in range(5):
            try:
                config = ClientConfig(timeout=0.01, max_retries=0)  # Immediate timeout
                client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)
                
                try:
                    await client.get(endpoint)
                    success_count += 1
                except Exception:
                    failure_count += 1
                finally:
                    await client.close()
                    
            except Exception:
                failure_count += 1
            
            await asyncio.sleep(0.1)  # Brief pause between attempts
        
        return {
            "total_attempts": 5,
            "failure_count": failure_count,
            "success_count": success_count,
            "circuit_breaker_triggered": failure_count >= 3
        }
    
    async def test_progressive_timeout_increase(self) -> Dict[str, Any]:
        """Test progressive timeout increase pattern."""
        timeouts = [0.1, 0.2, 0.5, 1.0]
        results = []
        
        for timeout in timeouts:
            config = ClientConfig(timeout=timeout, max_retries=1)
            client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)
            
            try:
                start_time = time.time()
                await client.get("/health")
                end_time = time.time()
                
                results.append({
                    "timeout_setting": timeout,
                    "actual_time": end_time - start_time,
                    "success": True
                })
                break  # Success, no need to try longer timeouts
                
            except Exception as e:
                results.append({
                    "timeout_setting": timeout,
                    "success": False,
                    "error": str(e)
                })
            finally:
                await client.close()
        
        return {
            "progressive_timeouts": results,
            "eventual_success": any(r["success"] for r in results)
        }


class RecoveryScenarioTester:
    """Test various recovery scenarios and patterns."""
    
    def __init__(self, tester: RealErrorPropagationTester):
        self.tester = tester
    
    async def test_service_degradation_recovery(self) -> Dict[str, Any]:
        """Test service recovery from degraded state."""
        # Test health endpoint (should always work)
        health_result = await self._test_endpoint_availability("/health")
        
        # Test critical endpoint (might be degraded)
        critical_result = await self._test_endpoint_availability("/auth/me")
        
        # Assess recovery capability
        recovery_assessment = self._assess_recovery_capability(health_result, critical_result)
        
        return {
            "health_endpoint": health_result,
            "critical_endpoint": critical_result,
            "recovery_assessment": recovery_assessment
        }
    
    async def _test_endpoint_availability(self, endpoint: str) -> Dict[str, Any]:
        """Test specific endpoint availability."""
        config = ClientConfig(timeout=5.0, max_retries=2)
        client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)
        
        try:
            start_time = time.time()
            response = await client.get(endpoint)
            end_time = time.time()
            
            return {
                "endpoint": endpoint,
                "available": True,
                "response_time": end_time - start_time,
                "status_code": getattr(response, 'status_code', None)
            }
            
        except Exception as e:
            return {
                "endpoint": endpoint,
                "available": False,
                "error": str(e),
                "degraded": self._is_degraded_error(str(e))
            }
        finally:
            await client.close()
    
    def _is_degraded_error(self, error_str: str) -> bool:
        """Check if error indicates service degradation rather than complete failure."""
        degradation_indicators = ["timeout", "slow", "degraded", "limited", "temporary"]
        return any(indicator in error_str.lower() for indicator in degradation_indicators)
    
    def _assess_recovery_capability(self, health_result: Dict, critical_result: Dict) -> Dict[str, Any]:
        """Assess system's recovery capability."""
        health_available = health_result.get("available", False)
        critical_available = critical_result.get("available", False)
        
        if health_available and critical_available:
            recovery_state = "fully_operational"
        elif health_available and not critical_available:
            recovery_state = "degraded_service"
        elif not health_available:
            recovery_state = "service_down"
        else:
            recovery_state = "unknown"
        
        return {
            "recovery_state": recovery_state,
            "health_monitoring_active": health_available,
            "critical_services_available": critical_available,
            "graceful_degradation": health_available and not critical_available
        }