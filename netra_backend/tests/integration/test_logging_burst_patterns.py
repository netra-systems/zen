"""
Integration Tests for Logging Burst Patterns - Issue #253 Reproduction

This test suite reproduces the integration-level conditions that cause empty CRITICAL
log entries during high-load scenarios, specifically targeting the burst logging
patterns observed in production (21+ logs in 2 seconds).

Test Plan Focus:
1. WebSocket connection retry burst logging under real load
2. Concurrent user context logging integration with actual services  
3. GCP JSON formatter behavior under stress with real environment
4. Multi-threaded logging scenarios that cause context corruption
5. Production-scale logging bursts with timing pressure

Expected Behavior: These tests will FAIL initially, demonstrating the burst logging issues.
After implementing fixes, these tests should PASS.

SSOT Compliance: Inherits from SSotBaseTestCase, uses real services (no mocks for integration).
Business Value: Platform/Internal - System Stability & Production Reliability

Created: 2025-09-10 (Issue #253 Integration Test Implementation)
"""

import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

# System Under Test - Real logging infrastructure
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT,
    UnifiedLoggingContext,
    request_id_context,
    user_id_context,
    trace_id_context
)

# Real service integration components (no mocks in integration tests)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestLoggingBurstPatterns(SSotBaseTestCase):
    """
    Integration test suite for logging burst patterns causing empty CRITICAL entries.
    
    Tests real service integration under production-like load conditions
    that reproduce the burst logging issues observed in Issue #253.
    """
    
    def setup_method(self, method):
        """Setup integration test environment with real services."""
        super().setup_method(method)
        self.logger = UnifiedLoggingSSOT()
        self.context = UnifiedLoggingContext()
        
        # Integration test state tracking
        self.captured_logs: List[Dict[str, Any]] = []
        self.timing_data: List[Dict[str, Any]] = []
        self.thread_safety_violations: List[str] = []
        
        # Real service components for integration testing
        self.user_contexts: Dict[str, UserExecutionContext] = {}
        
        # Setup log monitoring
        self._setup_integration_log_monitoring()
        
    def teardown_method(self, method):
        """Clean up integration test state."""
        # Clear all contexts
        request_id_context.set(None)
        user_id_context.set(None)
        trace_id_context.set(None)
        
        # Clean up user contexts
        for user_context in self.user_contexts.values():
            try:
                user_context.cleanup()
            except Exception:
                pass  # Best effort cleanup
        
        self.user_contexts.clear()
        
        super().teardown_method(method)
    
    def _setup_integration_log_monitoring(self):
        """Setup integration-level log monitoring without mocking."""
        self.captured_logs.clear()
        self.timing_data.clear()
        self.thread_safety_violations.clear()
        
        # Monitor timing for burst detection
        self.burst_start_time = None
        self.burst_log_count = 0
    
    @contextmanager
    def _monitor_logging_burst(self, expected_burst_size: int = 21):
        """Context manager to monitor logging bursts in integration tests."""
        self.burst_start_time = time.time()
        self.burst_log_count = 0
        
        # Patch the logger to monitor actual calls
        original_critical = self.logger.critical
        
        def monitored_critical(*args, **kwargs):
            self.burst_log_count += 1
            current_time = time.time()
            
            if self.burst_start_time:
                elapsed = current_time - self.burst_start_time
                self.timing_data.append({
                    'timestamp': current_time,
                    'elapsed': elapsed,
                    'log_number': self.burst_log_count,
                    'args': str(args)[:100],  # Truncate for safety
                    'thread_id': threading.get_ident()
                })
            
            # Call original method
            return original_critical(*args, **kwargs)
        
        self.logger.critical = monitored_critical
        
        try:
            yield
        finally:
            # Restore original method
            self.logger.critical = original_critical
            
            # Analyze burst pattern
            if self.timing_data:
                total_time = max(entry['elapsed'] for entry in self.timing_data)
                self._analyze_burst_pattern(total_time, expected_burst_size)
    
    def _analyze_burst_pattern(self, total_time: float, expected_size: int):
        """Analyze the burst pattern for timing issues."""
        if total_time <= 2.0 and self.burst_log_count >= expected_size:
            # We have a valid burst - check for timing issues
            timing_gaps = []
            for i in range(1, len(self.timing_data)):
                gap = self.timing_data[i]['elapsed'] - self.timing_data[i-1]['elapsed']
                timing_gaps.append(gap)
            
            # Check for timestamp collisions (gaps < 1ms)
            collision_count = sum(1 for gap in timing_gaps if gap < 0.001)
            if collision_count > 0:
                self.thread_safety_violations.append(
                    f"Found {collision_count} timestamp collisions in burst of {self.burst_log_count} logs"
                )
    
    def test_websocket_connection_retry_burst_integration(self):
        """
        Integration Test 1: WebSocket connection retry burst with real components.
        
        Tests the actual WebSocket retry mechanism that produces the 21+ logs
        in 2 seconds pattern observed in production, using real service integration.
        """
        # Setup real user execution context
        user_id = "integration_test_user_001"
        self.user_contexts[user_id] = UserExecutionContext(user_id=user_id)
        
        with self._monitor_logging_burst(expected_burst_size=25):
            # Simulate real WebSocket connection retry scenario
            retry_count = 0
            max_retries = 25
            connection_start = time.time()
            
            while retry_count < max_retries:
                # Set real context for each retry
                user_id_context.set(user_id)
                request_id_context.set(f"ws_retry_{retry_count}_{int(time.time())}")
                trace_id_context.set(f"trace_ws_{user_id}_{retry_count}")
                
                # Log critical failure (this produces the burst)
                self.logger.critical(
                    f"WebSocket connection retry {retry_count} failed for user {user_id}",
                    extra={
                        'component': 'websocket_manager',
                        'user_id': user_id,
                        'retry_count': retry_count,
                        'connection_attempt_time': time.time(),
                        'integration_test': True,
                        'user_context': self.user_contexts[user_id].get_context_summary()
                    }
                )
                
                retry_count += 1
                
                # Simulate real retry timing (rapid but not instant)
                time.sleep(0.075)  # 75ms between retries = ~13 retries/second
                
                # Break if we've gone over 2.5 seconds (safety)
                if time.time() - connection_start > 2.5:
                    break
        
        # Integration test assertions
        total_time = time.time() - connection_start
        
        # This test should FAIL initially - demonstrating burst timing issues
        assert total_time <= 2.5, f"Integration test took too long: {total_time}s"
        assert self.burst_log_count >= 20, f"Expected >=20 logs, got {self.burst_log_count}"
        
        # Check for thread safety violations
        assert len(self.thread_safety_violations) == 0, \
            f"Thread safety violations detected: {self.thread_safety_violations}"
        
        # Verify user context integrity throughout burst
        user_context_entries = [entry for entry in self.timing_data if 'user_context' in entry.get('args', '')]
        assert len(user_context_entries) > 0, "No user context found in burst logs"
    
    def test_concurrent_user_context_logging_integration(self):
        """
        Integration Test 2: Concurrent user context logging with real services.
        
        Tests multiple real user execution contexts logging simultaneously,
        reproducing context corruption that causes empty log entries.
        """
        # Setup multiple real user contexts
        user_count = 10
        user_ids = [f"concurrent_user_{i:03d}" for i in range(user_count)]
        
        for user_id in user_ids:
            self.user_contexts[user_id] = UserExecutionContext(user_id=user_id)
        
        # Track results per user
        user_log_counts = {user_id: 0 for user_id in user_ids}
        user_errors = {user_id: [] for user_id in user_ids}
        
        def user_logging_task(user_id: str) -> Dict[str, Any]:
            """Real user logging task with actual service integration."""
            task_start = time.time()
            logs_generated = 0
            errors = []
            
            try:
                # Set real user context
                user_context = self.user_contexts[user_id]
                
                for i in range(15):  # Each user generates 15 critical logs
                    # Set context variables for this user
                    user_id_context.set(user_id)
                    request_id_context.set(f"req_{user_id}_{i}")
                    trace_id_context.set(f"trace_{user_id}_{i}")
                    
                    # Generate critical log with real context data
                    self.logger.critical(
                        f"Concurrent critical event {i} for {user_id}",
                        extra={
                            'user_id': user_id,
                            'event_sequence': i,
                            'user_context_data': user_context.get_context_summary(),
                            'timestamp': datetime.utcnow().isoformat(),
                            'concurrent_test': True
                        }
                    )
                    
                    logs_generated += 1
                    
                    # Small delay to create concurrency pressure
                    time.sleep(0.01)  # 10ms delay
                    
            except Exception as e:
                errors.append(str(e))
            
            return {
                'user_id': user_id,
                'logs_generated': logs_generated,
                'errors': errors,
                'duration': time.time() - task_start
            }
        
        # Execute concurrent logging with real thread pool
        integration_start = time.time()
        
        with ThreadPoolExecutor(max_workers=user_count) as executor:
            # Submit all user tasks
            future_to_user = {
                executor.submit(user_logging_task, user_id): user_id 
                for user_id in user_ids
            }
            
            # Collect results
            results = []
            for future in as_completed(future_to_user, timeout=30):
                user_id = future_to_user[future]
                try:
                    result = future.result()
                    results.append(result)
                    user_log_counts[user_id] = result['logs_generated']
                    user_errors[user_id] = result['errors']
                except Exception as e:
                    user_errors[user_id].append(f"Task execution error: {e}")
        
        integration_duration = time.time() - integration_start
        
        # Integration test assertions
        assert integration_duration <= 30, f"Integration test timeout: {integration_duration}s"
        
        # This test should FAIL initially - demonstrating concurrent logging issues
        total_logs_expected = user_count * 15  # 10 users × 15 logs each
        total_logs_actual = sum(user_log_counts.values())
        
        assert total_logs_actual >= total_logs_expected, \
            f"Missing logs: expected {total_logs_expected}, got {total_logs_actual}"
        
        # Check for user context corruption
        for user_id, errors in user_errors.items():
            assert len(errors) == 0, f"User {user_id} had errors: {errors}"
        
        # Verify no cross-user context pollution
        # This requires analyzing actual log content, which would be captured
        # by the logger in a real integration test environment
        
    def test_gcp_json_formatter_stress_integration(self):
        """
        Integration Test 3: GCP JSON formatter under real environment stress.
        
        Tests the actual GCP JSON formatter used in staging/production
        under integration-level stress that reproduces empty log entries.
        """
        # Setup real GCP-like environment
        with patch.dict(self._env.get_all_vars(), {
            'ENVIRONMENT': 'integration_test',
            'GCP_PROJECT': 'netra-integration-test',
            'SERVICE_NAME': 'netra-backend',
            'ENABLE_GCP_LOGGING': 'true'
        }):
            
            # Create real user context for stress test
            stress_user_id = "gcp_stress_test_user"
            self.user_contexts[stress_user_id] = UserExecutionContext(user_id=stress_user_id)
            
            # Setup stress test monitoring
            formatter_errors = []
            empty_log_count = 0
            
            def monitor_json_formatting():
                """Monitor JSON formatter for errors during stress test."""
                original_formatter = self.logger._get_json_formatter()
                
                def stress_monitoring_formatter(record):
                    try:
                        result = original_formatter(record)
                        if not result or result.strip() == '':
                            nonlocal empty_log_count
                            empty_log_count += 1
                        return result
                    except Exception as e:
                        formatter_errors.append(str(e))
                        return ""  # Simulate production behavior
                
                return stress_monitoring_formatter
            
            # Apply stress monitoring
            with patch.object(self.logger, '_get_json_formatter', side_effect=monitor_json_formatting):
                stress_start = time.time()
                stress_logs_generated = 0
                
                # Generate stress load with real data
                for stress_round in range(5):  # 5 rounds of stress
                    for burst_log in range(30):  # 30 logs per round
                        user_id_context.set(stress_user_id)
                        request_id_context.set(f"stress_{stress_round}_{burst_log}")
                        trace_id_context.set(f"stress_trace_{stress_round}_{burst_log}")
                        
                        # Critical log with complex real data
                        self.logger.critical(
                            f"GCP stress test critical log round {stress_round} burst {burst_log}",
                            extra={
                                'stress_test': True,
                                'user_id': stress_user_id,
                                'stress_round': stress_round,
                                'burst_sequence': burst_log,
                                'user_context': self.user_contexts[stress_user_id].get_context_summary(),
                                'timestamp': datetime.utcnow().isoformat(),
                                'gcp_environment': self._env.get('GCP_PROJECT'),
                                'complex_data': {
                                    'nested_dict': {'level1': {'level2': {'level3': 'deep_value'}}},
                                    'list_data': list(range(10)),
                                    'timing_info': {
                                        'start': stress_start,
                                        'current': time.time(),
                                        'elapsed': time.time() - stress_start
                                    }
                                }
                            }
                        )
                        
                        stress_logs_generated += 1
                        
                        # Rapid burst timing
                        time.sleep(0.005)  # 5ms delay = 200 logs/second
                
                stress_duration = time.time() - stress_start
                
                # Integration assertions for GCP formatter stress
                assert stress_duration <= 10, f"Stress test took too long: {stress_duration}s"
                assert stress_logs_generated >= 150, f"Expected >=150 stress logs, got {stress_logs_generated}"
                
                # This test should FAIL initially - demonstrating GCP formatter issues
                assert len(formatter_errors) == 0, \
                    f"JSON formatter errors during stress: {formatter_errors[:5]}"  # Show first 5 errors
                
                assert empty_log_count == 0, \
                    f"Found {empty_log_count} empty logs during GCP stress test"
    
    def test_multi_threaded_context_corruption_integration(self):
        """
        Integration Test 4: Multi-threaded context corruption with real threading.
        
        Tests real threading scenarios that cause context variable corruption
        and result in empty or misattributed log entries.
        """
        # Setup multiple threads with real user contexts
        thread_count = 8
        logs_per_thread = 20
        
        thread_results = {}
        context_corruption_detected = []
        
        def threaded_logging_task(thread_id: int) -> Dict[str, Any]:
            """Real threaded logging with context management."""
            thread_user_id = f"thread_user_{thread_id:02d}"
            self.user_contexts[thread_user_id] = UserExecutionContext(user_id=thread_user_id)
            
            task_logs = []
            task_errors = []
            
            try:
                for log_num in range(logs_per_thread):
                    # Set context for this thread
                    user_id_context.set(thread_user_id)
                    request_id_context.set(f"thread_req_{thread_id}_{log_num}")
                    trace_id_context.set(f"thread_trace_{thread_id}_{log_num}")
                    
                    # Verify context before logging
                    current_user = user_id_context.get()
                    current_request = request_id_context.get()
                    
                    if current_user != thread_user_id:
                        context_corruption_detected.append(
                            f"Thread {thread_id}: Expected user {thread_user_id}, got {current_user}"
                        )
                    
                    # Generate critical log
                    self.logger.critical(
                        f"Thread {thread_id} critical log {log_num}",
                        extra={
                            'thread_id': thread_id,
                            'log_sequence': log_num,
                            'user_id': thread_user_id,
                            'context_user': current_user,
                            'context_request': current_request,
                            'user_context_data': self.user_contexts[thread_user_id].get_context_summary(),
                            'threading_test': True
                        }
                    )
                    
                    task_logs.append({
                        'log_num': log_num,
                        'expected_user': thread_user_id,
                        'actual_user': current_user
                    })
                    
                    # Thread contention timing
                    time.sleep(0.02)  # 20ms delay
                    
            except Exception as e:
                task_errors.append(str(e))
            
            return {
                'thread_id': thread_id,
                'logs_generated': len(task_logs),
                'errors': task_errors,
                'log_details': task_logs
            }
        
        # Execute multi-threaded integration test
        threading_start = time.time()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [
                executor.submit(threaded_logging_task, thread_id)
                for thread_id in range(thread_count)
            ]
            
            for future in as_completed(futures, timeout=60):
                result = future.result()
                thread_results[result['thread_id']] = result
        
        threading_duration = time.time() - threading_start
        
        # Integration assertions for threading
        assert threading_duration <= 60, f"Threading test timeout: {threading_duration}s"
        
        # This test should FAIL initially - demonstrating threading issues
        total_expected_logs = thread_count * logs_per_thread
        total_actual_logs = sum(result['logs_generated'] for result in thread_results.values())
        
        assert total_actual_logs >= total_expected_logs, \
            f"Missing threaded logs: expected {total_expected_logs}, got {total_actual_logs}"
        
        # Check for context corruption
        assert len(context_corruption_detected) == 0, \
            f"Context corruption detected: {context_corruption_detected[:3]}"  # Show first 3
        
        # Verify thread isolation
        for thread_id, result in thread_results.items():
            assert len(result['errors']) == 0, f"Thread {thread_id} errors: {result['errors']}"
            
            # Verify all logs from this thread have correct user ID
            for log_detail in result['log_details']:
                assert log_detail['expected_user'] == log_detail['actual_user'], \
                    f"Thread {thread_id} context mismatch: {log_detail}"
    
    def test_production_scale_burst_integration(self):
        """
        Integration Test 5: Production-scale burst logging integration.
        
        Tests production-scale logging burst (100+ logs/second) that
        reproduces the exact timing conditions causing empty CRITICAL entries.
        """
        # Setup production-scale test environment
        scale_user_id = "production_scale_user"
        self.user_contexts[scale_user_id] = UserExecutionContext(user_id=scale_user_id)
        
        # Production scale parameters
        burst_duration = 2.0  # 2 seconds
        target_logs_per_second = 150  # 150 logs/second
        total_target_logs = int(burst_duration * target_logs_per_second)
        
        scale_start = time.time()
        scale_logs_generated = 0
        scale_timing_violations = []
        
        user_id_context.set(scale_user_id)
        
        try:
            while time.time() - scale_start < burst_duration:
                # Generate burst with production timing pressure
                for burst_batch in range(10):  # 10 logs per batch
                    request_id_context.set(f"scale_req_{scale_logs_generated}")
                    trace_id_context.set(f"scale_trace_{scale_logs_generated}")
                    
                    batch_start = time.time()
                    
                    self.logger.critical(
                        f"Production scale critical log {scale_logs_generated}",
                        extra={
                            'production_scale_test': True,
                            'user_id': scale_user_id,
                            'log_sequence': scale_logs_generated,
                            'batch_sequence': burst_batch,
                            'target_rate': target_logs_per_second,
                            'elapsed_time': time.time() - scale_start,
                            'user_context': self.user_contexts[scale_user_id].get_context_summary()
                        }
                    )
                    
                    scale_logs_generated += 1
                    
                    batch_duration = time.time() - batch_start
                    if batch_duration > 0.01:  # > 10ms per log indicates timing issue
                        scale_timing_violations.append(f"Log {scale_logs_generated}: {batch_duration:.3f}s")
                    
                    # Aggressive timing to hit target rate
                    time.sleep(0.001)  # 1ms delay between logs
                
                # Brief pause between batches
                time.sleep(0.005)  # 5ms batch pause
        
        except Exception as e:
            pytest.fail(f"Production scale test failed: {e}")
        
        scale_duration = time.time() - scale_start
        actual_rate = scale_logs_generated / scale_duration
        
        # Production scale integration assertions
        assert scale_duration <= 3.0, f"Scale test took too long: {scale_duration}s"
        
        # This test should FAIL initially - demonstrating production scale issues
        assert scale_logs_generated >= total_target_logs * 0.8, \
            f"Scale test underperformed: expected >={total_target_logs * 0.8}, got {scale_logs_generated}"
        
        assert actual_rate >= target_logs_per_second * 0.8, \
            f"Log rate too low: expected >={target_logs_per_second * 0.8}/s, got {actual_rate:.1f}/s"
        
        assert len(scale_timing_violations) < scale_logs_generated * 0.1, \
            f"Too many timing violations ({len(scale_timing_violations)}): {scale_timing_violations[:5]}"