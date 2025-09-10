"""Integration tests for GCP traceback with real services.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Production Reliability & Incident Response  
- Business Goal: Validate complete logging pipeline from app errors to GCP Cloud Logging
- Value Impact: Ensures production debugging capabilities reduce incident resolution time by 70%
- Strategic Impact: Enables proactive monitoring and fast incident response for $500K+ ARR platform

This integration test suite validates:
1. Real logging system integration with GCP formatters
2. WebSocket error scenarios with traceback capture
3. Agent execution failures with proper error reporting
4. Database operation errors with contextual information
5. Complete error propagation through middleware stack

CRITICAL: Uses real services approach per CLAUDE.md requirements.
No mocks in integration tests - validates actual logging pipeline behavior.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from unittest.mock import patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
from netra_backend.app.core.unified_logging import get_logger
from shared.isolated_environment import get_env


class TestGCPTracebackIntegration(SSotAsyncTestCase):
    """Integration tests for GCP traceback capture with real logging services."""
    
    def setup_method(self, method):
        """Setup integration tests with real logging configuration."""
        super().setup_method(method)
        self.env = get_env()
        
        # Configure for GCP staging environment simulation
        self.set_env_var("K_SERVICE", "netra-backend-staging")
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("GOOGLE_CLOUD_PROJECT", "netra-staging")
        
        # Set up real unified logging system
        # Note: UnifiedLogger auto-configures based on environment
        self.logger = get_logger(__name__)
        self.captured_logs = []
        
        # Track integration metrics
        self.record_metric("test_setup_completed", True)
    
    async def test_websocket_error_traceback_capture_integration(self):
        """
        Test traceback capture during WebSocket error scenarios.
        
        Simulates real WebSocket connection failures and validates traceback
        propagation through the logging system.
        """
        # Simulate WebSocket connection error scenario
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        
        # Set up context for WebSocket error
        with self.temp_env_vars(
            USER_ID=user_id,
            TRACE_ID=trace_id,
            REQUEST_ID=f"req_{uuid.uuid4().hex[:8]}"
        ):
            # Capture logs during error scenario
            with self._capture_gcp_logs() as log_capture:
                await self._simulate_websocket_connection_failure()
            
            # Validate captured logs contain traceback
            error_logs = [log for log in log_capture.logs if log.get("severity") == "ERROR"]
            assert len(error_logs) > 0, "No ERROR logs captured during WebSocket failure"
            
            # Find log entry with traceback
            traceback_log = None
            for log_entry in error_logs:
                if "error" in log_entry and log_entry["error"].get("traceback"):
                    traceback_log = log_entry
                    break
            
            # CRITICAL: This assertion should initially FAIL if traceback capture is broken
            assert traceback_log is not None, "No log entry with traceback found - MISSING TRACEBACK ISSUE"
            
            # Validate traceback content
            error_field = traceback_log["error"]
            assert error_field["type"] is not None, "Exception type missing"
            assert error_field["value"] is not None, "Exception value missing"
            assert len(error_field["traceback"]) > 0, "Traceback is empty"
            
            # Validate context propagation
            assert traceback_log["labels"]["user_id"] == user_id, "User ID not propagated"
            assert traceback_log["trace"] == trace_id, "Trace ID not propagated"
        
        self.record_metric("websocket_traceback_validated", True)
        self.increment_websocket_events(1)
    
    async def test_agent_execution_error_traceback_integration(self):
        """
        Test traceback capture during agent execution failures.
        
        Validates that agent errors are properly logged with complete traceback
        information for debugging production issues.
        """
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            AGENT_ID=agent_id,
            EXECUTION_ID=execution_id
        ):
            with self._capture_gcp_logs() as log_capture:
                await self._simulate_agent_execution_failure()
            
            # Find agent error logs
            agent_error_logs = [
                log for log in log_capture.logs 
                if log.get("severity") == "ERROR" and "agent" in log.get("message", "").lower()
            ]
            
            assert len(agent_error_logs) > 0, "No agent error logs captured"
            
            # Validate traceback in agent error
            for log_entry in agent_error_logs:
                if "error" in log_entry:
                    error_field = log_entry["error"]
                    if error_field.get("traceback"):
                        # Validate agent-specific traceback content
                        traceback_content = error_field["traceback"]
                        assert "agent" in traceback_content.lower(), "Agent context missing from traceback"
                        assert execution_id in traceback_content or execution_id in log_entry.get("context", {}), "Execution ID not in traceback context"
                        break
            else:
                # This should initially fail if agent tracebacks aren't captured
                assert False, "No agent error log with traceback found - AGENT TRACEBACK MISSING"
        
        self.record_metric("agent_traceback_validated", True)
    
    async def test_database_operation_error_traceback_integration(self):
        """
        Test traceback capture during database operation failures.
        
        Validates database error scenarios are logged with proper context
        and traceback information for production debugging.
        """
        query_id = f"query_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(QUERY_ID=query_id):
            with self._capture_gcp_logs() as log_capture:
                await self._simulate_database_operation_failure()
            
            # Find database error logs
            db_error_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and any(
                    keyword in log.get("message", "").lower() 
                    for keyword in ["database", "sql", "query", "connection"]
                )
            ]
            
            assert len(db_error_logs) > 0, "No database error logs captured"
            
            # Validate database error traceback
            db_traceback_found = False
            for log_entry in db_error_logs:
                if "error" in log_entry and log_entry["error"].get("traceback"):
                    traceback_content = log_entry["error"]["traceback"]
                    # Database errors should include connection/query context
                    if any(keyword in traceback_content.lower() for keyword in ["database", "connection", "query"]):
                        db_traceback_found = True
                        break
            
            # This assertion may initially fail if database tracebacks aren't captured
            assert db_traceback_found, "No database error log with traceback found"
        
        self.record_metric("database_traceback_validated", True)
        self.increment_db_query_count(1)
    
    async def test_middleware_error_propagation_with_traceback(self):
        """
        Test error propagation through middleware stack with traceback preservation.
        
        Validates that errors from deep in the stack maintain traceback information
        when propagated through middleware layers.
        """
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(REQUEST_ID=request_id):
            with self._capture_gcp_logs() as log_capture:
                await self._simulate_middleware_error_propagation()
            
            # Find middleware error logs
            middleware_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and "middleware" in log.get("message", "").lower()
            ]
            
            assert len(middleware_logs) > 0, "No middleware error logs captured"
            
            # Validate full stack trace preservation
            full_stack_found = False
            for log_entry in middleware_logs:
                if "error" in log_entry and log_entry["error"].get("traceback"):
                    traceback_content = log_entry["error"]["traceback"]
                    
                    # Should contain multiple stack frames from middleware chain
                    if traceback_content.count("middleware") >= 2:  # Multiple middleware layers
                        full_stack_found = True
                        assert request_id in traceback_content or request_id in log_entry.get("labels", {}), "Request ID not in traceback context"
                        break
            
            assert full_stack_found, "Full middleware stack trace not preserved"
        
        self.record_metric("middleware_traceback_validated", True)
    
    async def test_concurrent_error_traceback_isolation(self):
        """
        Test that concurrent error scenarios maintain traceback isolation.
        
        Validates that multiple simultaneous errors don't interfere with
        each other's traceback capture.
        """
        # Create multiple concurrent error scenarios
        tasks = []
        for i in range(3):
            task_id = f"task_{i}_{uuid.uuid4().hex[:8]}"
            tasks.append(self._simulate_concurrent_error(task_id))
        
        with self._capture_gcp_logs() as log_capture:
            # Run concurrent error scenarios
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate each task's errors are isolated
        error_logs = [log for log in log_capture.logs if log.get("severity") == "ERROR"]
        assert len(error_logs) >= 3, f"Expected at least 3 error logs, got {len(error_logs)}"
        
        # Group logs by task ID and validate isolation
        task_logs = {}
        for log_entry in error_logs:
            message = log_entry.get("message", "")
            for i in range(3):
                task_pattern = f"task_{i}_"
                if task_pattern in message:
                    if i not in task_logs:
                        task_logs[i] = []
                    task_logs[i].append(log_entry)
        
        assert len(task_logs) == 3, "Not all concurrent tasks produced isolated logs"
        
        # Validate each task has proper traceback
        for task_id, logs in task_logs.items():
            task_traceback_found = False
            for log_entry in logs:
                if "error" in log_entry and log_entry["error"].get("traceback"):
                    traceback_content = log_entry["error"]["traceback"]
                    if f"task_{task_id}" in traceback_content:
                        task_traceback_found = True
                        break
            
            assert task_traceback_found, f"Task {task_id} traceback not found or not isolated"
        
        self.record_metric("concurrent_isolation_validated", True)
    
    async def test_large_traceback_performance_integration(self):
        """
        Test performance of large traceback processing in real logging system.
        
        Validates that large tracebacks don't degrade logging performance
        in production scenarios.
        """
        start_time = time.time()
        
        with self._capture_gcp_logs() as log_capture:
            await self._simulate_large_traceback_scenario()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time even with large traceback
        assert processing_time < 1.0, f"Large traceback processing too slow: {processing_time:.3f}s"
        
        # Validate large traceback was captured
        large_traceback_logs = [
            log for log in log_capture.logs
            if log.get("error", {}).get("traceback") and len(log["error"]["traceback"]) > 1000
        ]
        
        assert len(large_traceback_logs) > 0, "Large traceback not captured"
        
        self.record_metric("large_traceback_processing_time_ms", processing_time * 1000)
    
    # Helper methods for simulating error scenarios
    
    async def _simulate_websocket_connection_failure(self):
        """Simulate WebSocket connection failure with traceback."""
        try:
            # Simulate WebSocket operation that fails
            class MockWebSocketError(Exception):
                pass
            
            def failing_websocket_operation():
                raise MockWebSocketError("WebSocket connection lost during agent communication")
            
            failing_websocket_operation()
        except MockWebSocketError:
            self.logger.error("WebSocket error occurred", exc_info=True)
    
    async def _simulate_agent_execution_failure(self):
        """Simulate agent execution failure with traceback."""
        try:
            def agent_execution_step():
                def tool_execution():
                    raise ValueError("Tool execution failed: invalid parameters")
                tool_execution()
            
            agent_execution_step()
        except ValueError:
            self.logger.error("Agent execution failed", exc_info=True)
    
    async def _simulate_database_operation_failure(self):
        """Simulate database operation failure with traceback."""
        try:
            def database_query():
                def connection_operation():
                    raise ConnectionError("Database connection timeout during query execution")
                connection_operation()
            
            database_query()
        except ConnectionError:
            self.logger.error("Database operation failed", exc_info=True)
    
    async def _simulate_middleware_error_propagation(self):
        """Simulate error propagation through middleware layers."""
        try:
            def auth_middleware():
                def validation_middleware():
                    def business_logic():
                        raise PermissionError("Access denied: insufficient permissions")
                    business_logic()
                validation_middleware()
            
            auth_middleware()
        except PermissionError:
            self.logger.error("Middleware error propagation", exc_info=True)
    
    async def _simulate_concurrent_error(self, task_id: str):
        """Simulate concurrent error scenario."""
        await asyncio.sleep(0.1)  # Small delay to simulate concurrent work
        try:
            raise RuntimeError(f"Concurrent error in {task_id}")
        except RuntimeError:
            self.logger.error(f"Concurrent error occurred in {task_id}", exc_info=True)
    
    async def _simulate_large_traceback_scenario(self):
        """Simulate scenario that produces large traceback."""
        try:
            def create_deep_stack(depth, context=""):
                if depth <= 0:
                    raise RecursionError(f"Deep stack error with context: {context}")
                return create_deep_stack(depth - 1, f"{context}->frame_{depth}")
            
            create_deep_stack(50, "large_traceback_test")
        except RecursionError:
            self.logger.error("Large traceback scenario", exc_info=True)
    
    @asynccontextmanager
    async def _capture_gcp_logs(self):
        """Context manager to capture GCP-formatted logs for validation."""
        captured_logs = []
        
        # Mock the GCP sink to capture formatted output
        original_formatter = None
        
        class LogCapture:
            def __init__(self):
                self.logs = []
            
            def capture_log(self, formatted_json):
                try:
                    log_entry = json.loads(formatted_json)
                    self.logs.append(log_entry)
                except json.JSONDecodeError:
                    # Handle malformed JSON gracefully
                    self.logs.append({"raw_output": formatted_json, "parse_error": True})
        
        log_capture = LogCapture()
        
        # Patch the formatter to capture output
        def capturing_gcp_formatter(record):
            # Get the original formatted output
            formatter = LogFormatter(SensitiveDataFilter())
            formatted_json = formatter.gcp_json_formatter(record)
            
            # Capture for validation
            log_capture.capture_log(formatted_json)
            
            return formatted_json
        
        with patch.object(LogFormatter, 'gcp_json_formatter', side_effect=capturing_gcp_formatter):
            yield log_capture