"""
WebSocket Performance Monitor Coverage Tests
Tests for monitoring coverage and partial failure scenarios.
Verifies 100% monitoring coverage despite individual check failures.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.websocket.performance_monitor_core import PerformanceMonitor
from netra_backend.app.websocket.performance_monitor_types import PerformanceThresholds

# Add project root to path


class TestMonitoringCoverage:
    """Test monitoring coverage and partial failure scenarios."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor for testing."""
        thresholds = PerformanceThresholds()
        return PerformanceMonitor(thresholds)
    
    async def test_all_checks_run_despite_individual_failures(self, monitor):
        """Test that all monitoring checks run even when some fail."""
        # Mock individual check methods to simulate failures
        with patch.object(monitor, '_check_response_time_threshold', 
                         side_effect=Exception("Response time check failed")) as mock_rt:
            with patch.object(monitor, '_check_memory_threshold', 
                             new_callable=AsyncMock) as mock_mem:
                with patch.object(monitor, '_check_error_rate_threshold',
                                 side_effect=Exception("Error rate check failed")) as mock_err:
                    with patch.object(monitor, '_check_throughput_threshold',
                                     new_callable=AsyncMock) as mock_tp:
                        with patch.object(monitor, '_check_cpu_threshold',
                                         new_callable=AsyncMock) as mock_cpu:
                            
                            # Run monitoring checks
                            await monitor._check_performance_thresholds()
                            
                            # Verify ALL checks were attempted
                            mock_rt.assert_called_once()
                            mock_mem.assert_called_once()
                            mock_err.assert_called_once()
                            mock_tp.assert_called_once()
                            mock_cpu.assert_called_once()
    
    async def test_coverage_metrics_track_failures(self, monitor):
        """Test that coverage metrics properly track check failures."""
        # Mock checks with mixed success/failure
        with patch.object(monitor, '_check_response_time_threshold', 
                         side_effect=Exception("Failed")):
            with patch.object(monitor, '_check_memory_threshold', 
                             new_callable=AsyncMock):
                with patch.object(monitor, '_check_error_rate_threshold',
                                 side_effect=Exception("Failed")):
                    with patch.object(monitor, '_check_throughput_threshold',
                                     new_callable=AsyncMock):
                        with patch.object(monitor, '_check_cpu_threshold',
                                         new_callable=AsyncMock):
                            
                            # Run checks multiple times
                            for _ in range(3):
                                await monitor._check_performance_thresholds()
                            
                            # Verify coverage metrics
                            coverage = monitor.monitoring_coverage
                            assert coverage["total_checks"] == 15  # 5 checks * 3 runs
                            assert coverage["successful_checks"] == 9  # 3 successful checks * 3 runs
                            assert coverage["failed_checks"] == 6   # 2 failed checks * 3 runs
    
    async def test_monitoring_coverage_summary(self, monitor):
        """Test monitoring coverage summary calculation."""
        # Simulate some checks
        monitor.monitoring_coverage["total_checks"] = 10
        monitor.monitoring_coverage["successful_checks"] = 8
        monitor.monitoring_coverage["failed_checks"] = 2
        
        # Get coverage summary
        summary = monitor._get_monitoring_coverage_summary()
        
        # Verify coverage percentage
        assert summary["coverage_percentage"] == 80.0
        assert "recent_failures" in summary
    
    async def test_check_result_recording(self, monitor):
        """Test that check results are properly recorded."""
        # Record success and failure
        monitor._record_check_success("test_check")
        await monitor._handle_check_failure("failed_check", Exception("Test error"))
        
        # Verify results are recorded
        results = list(monitor.monitoring_coverage["check_results"])
        assert len(results) == 2
        
        # Check success result
        success_result = next(r for r in results if r["success"])
        assert success_result["check_name"] == "test_check"
        assert success_result["error"] is None
        
        # Check failure result
        failure_result = next(r for r in results if not r["success"])
        assert failure_result["check_name"] == "failed_check"
        assert "Test error" in failure_result["error"]
    
    async def test_fifty_percent_failure_scenario(self, monitor):
        """Test 100% monitoring coverage with 50% check failures."""
        # Setup scenario with alternating failures
        check_calls = []
        
        async def failing_check():
            check_calls.append("failed")
            raise Exception("Simulated failure")
        
        async def passing_check():
            check_calls.append("passed")
        
        # Mock checks to alternate between pass/fail
        with patch.object(monitor, '_check_response_time_threshold', 
                         side_effect=failing_check):
            with patch.object(monitor, '_check_memory_threshold', 
                             side_effect=passing_check):
                with patch.object(monitor, '_check_error_rate_threshold',
                                 side_effect=failing_check):
                    with patch.object(monitor, '_check_throughput_threshold',
                                     side_effect=passing_check):
                        with patch.object(monitor, '_check_cpu_threshold',
                                         side_effect=failing_check):
                            
                            # Run monitoring cycle
                            await monitor._check_performance_thresholds()
                            
                            # Verify all 5 checks were called (100% coverage)
                            assert len(check_calls) == 5
                            
                            # Verify 50% failure rate
                            failed_count = check_calls.count("failed")
                            passed_count = check_calls.count("passed")
                            assert failed_count == 3  # 3 out of 5 failed
                            assert passed_count == 2  # 2 out of 5 passed
                            
                            # Verify coverage metrics
                            coverage = monitor.monitoring_coverage
                            assert coverage["total_checks"] == 5
                            assert coverage["successful_checks"] == 2
                            assert coverage["failed_checks"] == 3
    
    async def test_performance_summary_includes_coverage(self, monitor):
        """Test that performance summary includes monitoring coverage."""
        # Run some checks to populate coverage data
        await monitor._check_performance_thresholds()
        
        # Get performance summary
        summary = monitor.get_current_performance_summary()
        
        # Verify coverage is included
        assert "monitoring_coverage" in summary
        coverage = summary["monitoring_coverage"]
        assert "coverage_percentage" in coverage
        assert "recent_failures" in coverage
    
    async def test_exception_handling_preserves_results(self, monitor):
        """Test that exceptions in check processing don't lose results."""
        results_captured = []
        
        async def capture_results(check_names, results):
            results_captured.extend(results)
            # Simulate original method behavior
            for check_name, result in zip(check_names, results):
                if isinstance(result, Exception):
                    await monitor._handle_check_failure(check_name, result)
                else:
                    monitor._record_check_success(check_name)
        
        # Mock result handling to capture what gets processed
        with patch.object(monitor, '_handle_check_results', 
                         side_effect=capture_results):
            with patch.object(monitor, '_check_response_time_threshold', 
                             side_effect=Exception("Test failure")):
                with patch.object(monitor, '_check_memory_threshold', 
                                 new_callable=AsyncMock):
                    with patch.object(monitor, '_check_error_rate_threshold',
                                     new_callable=AsyncMock):
                        with patch.object(monitor, '_check_throughput_threshold',
                                         new_callable=AsyncMock):
                            with patch.object(monitor, '_check_cpu_threshold',
                                             new_callable=AsyncMock):
                                
                                # Run checks
                                await monitor._check_performance_thresholds()
                                
                                # Verify all 5 results were captured
                                assert len(results_captured) == 5
                                
                                # Verify one exception and four successful results
                                exceptions = [r for r in results_captured if isinstance(r, Exception)]
                                successes = [r for r in results_captured if not isinstance(r, Exception)]
                                assert len(exceptions) == 1
                                assert len(successes) == 4
    
    async def test_recent_failure_counting(self, monitor):
        """Test recent failure counting for coverage metrics."""
        # Add some old failures (outside 5-minute window)
        old_timestamp = (datetime.now(timezone.utc)).replace(
            minute=datetime.now(timezone.utc).minute - 10
        ).isoformat()
        
        monitor.monitoring_coverage["check_results"].append({
            "timestamp": old_timestamp,
            "check_name": "old_check",
            "success": False,
            "error": "Old failure"
        })
        
        # Add recent failure
        recent_timestamp = datetime.now(timezone.utc).isoformat()
        monitor.monitoring_coverage["check_results"].append({
            "timestamp": recent_timestamp,
            "check_name": "recent_check",
            "success": False,
            "error": "Recent failure"
        })
        
        # Count should only include recent failures
        recent_count = monitor._count_recent_failures()
        assert recent_count == 1
    
    async def test_reset_coverage_metrics(self, monitor):
        """Test that coverage metrics are properly reset."""
        # Populate some coverage data
        monitor.monitoring_coverage["total_checks"] = 10
        monitor.monitoring_coverage["successful_checks"] = 8
        monitor.monitoring_coverage["failed_checks"] = 2
        
        # Reset metrics
        monitor.reset_metrics()
        
        # Verify coverage is reset
        coverage = monitor.monitoring_coverage
        assert coverage["total_checks"] == 0
        assert coverage["successful_checks"] == 0
        assert coverage["failed_checks"] == 0
        assert len(coverage["check_results"]) == 0


class TestMonitoringReliabilityPatterns:
    """Test compliance with WebSocket reliability patterns."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor for testing."""
        return PerformanceMonitor()
    
    async def test_fail_fast_monitoring_pattern_compliance(self, monitor):
        """Test compliance with fail_fast_monitoring pattern from spec."""
        # Mock all checks to fail
        failure_exception = Exception("Simulated failure")
        
        with patch.object(monitor, '_check_response_time_threshold', 
                         side_effect=failure_exception):
            with patch.object(monitor, '_check_memory_threshold', 
                             side_effect=failure_exception):
                with patch.object(monitor, '_check_error_rate_threshold',
                                 side_effect=failure_exception):
                    with patch.object(monitor, '_check_throughput_threshold',
                                     side_effect=failure_exception):
                        with patch.object(monitor, '_check_cpu_threshold',
                                         side_effect=failure_exception):
                            
                            # Should not raise exception despite all failures
                            await monitor._check_performance_thresholds()
                            
                            # All failures should be recorded
                            coverage = monitor.monitoring_coverage
                            assert coverage["failed_checks"] == 5
                            assert coverage["successful_checks"] == 0
                            assert coverage["total_checks"] == 5
    
    async def test_independent_check_execution(self, monitor):
        """Test that monitoring checks are truly independent."""
        call_order = []
        
        async def slow_check(name):
            call_order.append(f"{name}_start")
            await asyncio.sleep(0.1)  # Simulate slow check
            call_order.append(f"{name}_end")
        
        # Mock checks with different execution times
        with patch.object(monitor, '_check_response_time_threshold', 
                         side_effect=lambda: slow_check("response")):
            with patch.object(monitor, '_check_memory_threshold', 
                             side_effect=lambda: slow_check("memory")):
                with patch.object(monitor, '_check_error_rate_threshold',
                                 side_effect=lambda: slow_check("error")):
                    with patch.object(monitor, '_check_throughput_threshold',
                                     side_effect=lambda: slow_check("throughput")):
                        with patch.object(monitor, '_check_cpu_threshold',
                                         side_effect=lambda: slow_check("cpu")):
                            
                            start_time = asyncio.get_event_loop().time()
                            await monitor._check_performance_thresholds()
                            end_time = asyncio.get_event_loop().time()
                            
                            # Should complete in ~0.1s (parallel) not ~0.5s (sequential)
                            execution_time = end_time - start_time
                            assert execution_time < 0.2  # Allow some overhead
                            
                            # All checks should start before any end (parallel execution)
                            start_calls = [c for c in call_order if c.endswith("_start")]
                            assert len(start_calls) == 5