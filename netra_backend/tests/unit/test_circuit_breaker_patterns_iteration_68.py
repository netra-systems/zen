"""
Test Circuit Breaker Patterns - Iteration 68

Business Value Justification:
- Segment: Enterprise/Mid  
- Business Goal: System Resilience
- Value Impact: Prevents cascade failures and improves system stability
- Strategic Impact: Maintains service availability during partial failures
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta


class TestCircuitBreakerPatterns:
    """Test circuit breaker implementation patterns"""
    
    @pytest.mark.asyncio
    async def test_basic_circuit_breaker_states(self):
        """Test basic circuit breaker state transitions"""
        
        class CircuitBreaker:
            def __init__(self, failure_threshold=5, recovery_timeout=30, success_threshold=3):
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout  # seconds
                self.success_threshold = success_threshold
                self.failure_count = 0
                self.success_count = 0
                self.last_failure_time = None
                self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
                self.call_history = []
            
            async def call(self, func, *args, **kwargs):
                """Execute function call through circuit breaker"""
                call_start = time.time()
                
                # Check current state
                if self.state == "OPEN":
                    if self._should_attempt_reset():
                        self.state = "HALF_OPEN"
                        self.success_count = 0
                    else:
                        self.call_history.append({
                            "timestamp": call_start,
                            "state": "OPEN",
                            "result": "rejected",
                            "reason": "circuit_open"
                        })
                        raise Exception("Circuit breaker is OPEN")
                
                try:
                    result = await func(*args, **kwargs)
                    await self._on_success()
                    
                    self.call_history.append({
                        "timestamp": call_start,
                        "state": self.state,
                        "result": "success",
                        "duration": time.time() - call_start
                    })
                    
                    return result
                    
                except Exception as e:
                    await self._on_failure()
                    
                    self.call_history.append({
                        "timestamp": call_start,
                        "state": self.state,
                        "result": "failure",
                        "error": str(e),
                        "duration": time.time() - call_start
                    })
                    
                    raise
            
            def _should_attempt_reset(self):
                """Check if enough time has passed to attempt reset"""
                if self.last_failure_time is None:
                    return True
                return (time.time() - self.last_failure_time) >= self.recovery_timeout
            
            async def _on_success(self):
                """Handle successful call"""
                if self.state == "HALF_OPEN":
                    self.success_count += 1
                    if self.success_count >= self.success_threshold:
                        self.state = "CLOSED"
                        self.failure_count = 0
                        self.success_count = 0
                elif self.state == "CLOSED":
                    self.failure_count = 0  # Reset failure count on success
            
            async def _on_failure(self):
                """Handle failed call"""
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                elif self.state == "HALF_OPEN":
                    # Failed during recovery attempt, go back to OPEN
                    self.state = "OPEN"
                    self.success_count = 0
        
        # Test service that can fail
        failure_mode = False
        call_count = 0
        
        async def unreliable_service():
            """Service that fails based on failure_mode"""
            nonlocal call_count
            call_count += 1
            
            if failure_mode:
                raise Exception(f"Service failure {call_count}")
            
            return f"Success {call_count}"
        
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        # Phase 1: Normal operation (CLOSED state)
        result1 = await circuit_breaker.call(unreliable_service)
        assert result1 == "Success 1"
        assert circuit_breaker.state == "CLOSED"
        
        # Phase 2: Introduce failures to trip circuit breaker
        failure_mode = True
        failed_calls = 0
        
        for i in range(5):
            try:
                await circuit_breaker.call(unreliable_service)
            except Exception:
                failed_calls += 1
                
                if failed_calls >= 3:
                    # Should be OPEN after 3 failures
                    assert circuit_breaker.state == "OPEN"
                    break
        
        # Phase 3: Test OPEN state (calls should be rejected)
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await circuit_breaker.call(unreliable_service)
        
        # Phase 4: Wait for recovery timeout and test HALF_OPEN
        await asyncio.sleep(1.1)  # Wait longer than recovery timeout
        
        failure_mode = False  # Service is now working
        
        # First call after timeout should transition to HALF_OPEN
        result_after_recovery = await circuit_breaker.call(unreliable_service)
        assert circuit_breaker.state == "HALF_OPEN"
        
        # Make enough successful calls to close circuit
        for i in range(2):  # Need 3 total successes (already have 1)
            await circuit_breaker.call(unreliable_service)
        
        assert circuit_breaker.state == "CLOSED"
        
        # Verify call history tracking
        history = circuit_breaker.call_history
        assert len(history) > 5
        
        success_calls = [h for h in history if h["result"] == "success"]
        failure_calls = [h for h in history if h["result"] == "failure"] 
        rejected_calls = [h for h in history if h["result"] == "rejected"]
        
        assert len(success_calls) > 0
        assert len(failure_calls) > 0
        assert len(rejected_calls) > 0
    
    @pytest.mark.asyncio
    async def test_adaptive_circuit_breaker(self):
        """Test adaptive circuit breaker that adjusts thresholds"""
        
        class AdaptiveCircuitBreaker:
            def __init__(self):
                self.base_failure_threshold = 5
                self.current_failure_threshold = 5
                self.base_recovery_timeout = 30
                self.current_recovery_timeout = 30
                self.failure_rate_window = []  # Track recent failure rates
                self.performance_metrics = {
                    "avg_response_time": 0,
                    "error_rate": 0,
                    "throughput": 0
                }
                self.state = "CLOSED"
                self.failure_count = 0
                self.last_adaptation = time.time()
            
            async def call(self, func, *args, **kwargs):
                """Execute call with adaptive behavior"""
                call_start = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    call_duration = time.time() - call_start
                    await self._record_success(call_duration)
                    return result
                    
                except Exception as e:
                    call_duration = time.time() - call_start
                    await self._record_failure(call_duration)
                    
                    if self.failure_count >= self.current_failure_threshold:
                        self.state = "OPEN"
                    
                    raise
            
            async def _record_success(self, duration):
                """Record successful call and adapt parameters"""
                self.failure_count = max(0, self.failure_count - 1)  # Gradual recovery
                await self._update_performance_metrics(duration, success=True)
                await self._adapt_parameters()
            
            async def _record_failure(self, duration):
                """Record failed call and adapt parameters"""
                self.failure_count += 1
                await self._update_performance_metrics(duration, success=False)
                await self._adapt_parameters()
            
            async def _update_performance_metrics(self, duration, success=True):
                """Update performance metrics for adaptation"""
                current_time = time.time()
                
                # Update failure rate window (keep last 60 seconds)
                self.failure_rate_window = [
                    entry for entry in self.failure_rate_window
                    if current_time - entry["timestamp"] <= 60
                ]
                
                self.failure_rate_window.append({
                    "timestamp": current_time,
                    "success": success,
                    "duration": duration
                })
                
                # Calculate current metrics
                if self.failure_rate_window:
                    successes = sum(1 for e in self.failure_rate_window if e["success"])
                    total_calls = len(self.failure_rate_window)
                    durations = [e["duration"] for e in self.failure_rate_window]
                    
                    self.performance_metrics.update({
                        "avg_response_time": sum(durations) / len(durations),
                        "error_rate": (total_calls - successes) / total_calls,
                        "throughput": total_calls / min(60, current_time - self.failure_rate_window[0]["timestamp"])
                    })
            
            async def _adapt_parameters(self):
                """Adapt circuit breaker parameters based on performance"""
                current_time = time.time()
                
                # Only adapt every 30 seconds to avoid oscillation
                if current_time - self.last_adaptation < 30:
                    return
                
                error_rate = self.performance_metrics["error_rate"]
                avg_response_time = self.performance_metrics["avg_response_time"]
                
                # Adapt failure threshold based on error rate
                if error_rate > 0.2:  # High error rate
                    self.current_failure_threshold = max(2, self.base_failure_threshold - 2)
                elif error_rate < 0.05:  # Low error rate
                    self.current_failure_threshold = min(10, self.base_failure_threshold + 2)
                else:
                    self.current_failure_threshold = self.base_failure_threshold
                
                # Adapt recovery timeout based on response time
                if avg_response_time > 1.0:  # Slow responses
                    self.current_recovery_timeout = min(120, self.base_recovery_timeout * 2)
                elif avg_response_time < 0.1:  # Fast responses
                    self.current_recovery_timeout = max(10, self.base_recovery_timeout // 2)
                else:
                    self.current_recovery_timeout = self.base_recovery_timeout
                
                self.last_adaptation = current_time
        
        adaptive_cb = AdaptiveCircuitBreaker()
        
        # Simulate service with varying performance characteristics
        async def variable_service(response_time=0.05, should_fail=False):
            await asyncio.sleep(response_time)
            
            if should_fail:
                raise Exception("Service error")
            
            return "Success"
        
        # Phase 1: Fast, reliable service (should adapt to be more lenient)
        for i in range(20):
            await adaptive_cb.call(variable_service, response_time=0.02)
            await asyncio.sleep(0.1)
        
        initial_threshold = adaptive_cb.current_failure_threshold
        initial_timeout = adaptive_cb.current_recovery_timeout
        
        # Wait for adaptation window
        await asyncio.sleep(31)
        await adaptive_cb.call(variable_service, response_time=0.02)
        
        # Should have adapted to be more lenient (higher threshold, lower timeout)
        assert adaptive_cb.current_failure_threshold >= initial_threshold
        
        # Phase 2: Slow, unreliable service (should adapt to be more strict)
        for i in range(15):
            try:
                should_fail = i % 3 == 0  # 33% failure rate
                await adaptive_cb.call(variable_service, response_time=0.5, should_fail=should_fail)
            except Exception:
                pass
            await asyncio.sleep(0.1)
        
        # Wait for adaptation
        await asyncio.sleep(31)
        
        # Should have adapted to be more strict (lower threshold, higher timeout)
        adapted_threshold = adaptive_cb.current_failure_threshold
        adapted_timeout = adaptive_cb.current_recovery_timeout
        
        assert adapted_threshold < 5  # More strict than default
        assert adapted_timeout > 30   # Longer recovery time
        
        # Verify performance metrics are being tracked
        metrics = adaptive_cb.performance_metrics
        assert metrics["error_rate"] > 0.1    # Should reflect the 33% error rate
        assert metrics["avg_response_time"] > 0.3  # Should reflect slow responses
        assert metrics["throughput"] > 0      # Should calculate throughput
    
    def test_circuit_breaker_metrics_collection(self):
        """Test circuit breaker metrics and monitoring"""
        
        class MonitoredCircuitBreaker:
            def __init__(self):
                self.state = "CLOSED"
                self.metrics = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "rejected_calls": 0,
                    "state_transitions": [],
                    "response_times": []
                }
                self.failure_count = 0
                self.failure_threshold = 3
            
            def call(self, func, *args, **kwargs):
                """Synchronous call for testing"""
                call_start = time.time()
                self.metrics["total_calls"] += 1
                
                if self.state == "OPEN":
                    self.metrics["rejected_calls"] += 1
                    raise Exception("Circuit breaker is OPEN")
                
                try:
                    result = func(*args, **kwargs)
                    self.metrics["successful_calls"] += 1
                    self.failure_count = 0
                    
                    response_time = time.time() - call_start
                    self.metrics["response_times"].append(response_time)
                    
                    return result
                    
                except Exception as e:
                    self.metrics["failed_calls"] += 1
                    self.failure_count += 1
                    
                    if self.failure_count >= self.failure_threshold:
                        self._transition_state("OPEN")
                    
                    response_time = time.time() - call_start
                    self.metrics["response_times"].append(response_time)
                    
                    raise
            
            def _transition_state(self, new_state):
                """Transition to new state and record metrics"""
                old_state = self.state
                self.state = new_state
                
                self.metrics["state_transitions"].append({
                    "timestamp": time.time(),
                    "from_state": old_state,
                    "to_state": new_state,
                    "trigger": "failure_threshold" if new_state == "OPEN" else "manual"
                })
            
            def get_health_metrics(self):
                """Get circuit breaker health metrics"""
                if self.metrics["total_calls"] == 0:
                    return {"status": "no_data"}
                
                success_rate = self.metrics["successful_calls"] / self.metrics["total_calls"]
                avg_response_time = (
                    sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
                    if self.metrics["response_times"] else 0
                )
                
                return {
                    "state": self.state,
                    "success_rate": success_rate,
                    "error_rate": self.metrics["failed_calls"] / self.metrics["total_calls"],
                    "rejection_rate": self.metrics["rejected_calls"] / self.metrics["total_calls"],
                    "avg_response_time": avg_response_time,
                    "total_calls": self.metrics["total_calls"],
                    "state_transitions": len(self.metrics["state_transitions"]),
                    "current_failure_count": self.failure_count
                }
        
        cb = MonitoredCircuitBreaker()
        
        # Test successful calls
        def working_service():
            return "OK"
        
        for i in range(10):
            result = cb.call(working_service)
            assert result == "OK"
        
        metrics = cb.get_health_metrics()
        assert metrics["success_rate"] == 1.0
        assert metrics["error_rate"] == 0.0
        assert metrics["state"] == "CLOSED"
        assert metrics["total_calls"] == 10
        
        # Test failing service
        def failing_service():
            raise Exception("Service down")
        
        # Generate failures to trip circuit breaker
        failed_count = 0
        for i in range(5):
            try:
                cb.call(failing_service)
            except Exception:
                failed_count += 1
                if failed_count >= 3:
                    break
        
        # Test rejection after circuit opens
        rejection_count = 0
        for i in range(3):
            try:
                cb.call(working_service)
            except Exception as e:
                if "OPEN" in str(e):
                    rejection_count += 1
        
        final_metrics = cb.get_health_metrics()
        
        assert final_metrics["state"] == "OPEN"
        assert final_metrics["error_rate"] > 0
        assert final_metrics["rejection_rate"] > 0
        assert final_metrics["state_transitions"] > 0
        assert final_metrics["total_calls"] > 10