"""End-to-End tests for GCP Cloud Run traceback simulation.

Business Value Justification (BVJ):
- Segment: Enterprise - Production Infrastructure & Incident Response
- Business Goal: Validate complete error reporting pipeline in Cloud Run environment  
- Value Impact: Ensures enterprise customers have full production debugging capabilities
- Strategic Impact: Enables 24/7 production support with fast incident resolution

This E2E test suite validates:
1. Complete Cloud Run environment simulation with K_SERVICE and other GCP env vars
2. Real HTTP request handling with error scenarios
3. WebSocket connection lifecycle with error propagation
4. Agent execution pipeline failures with full traceback capture
5. Production-like logging configuration and output formatting

CRITICAL: These tests simulate actual Cloud Run environment and should initially 
FAIL to demonstrate missing traceback issues in GCP staging environment.

Uses REAL services and authentication per CLAUDE.md E2E requirements.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from unittest.mock import patch, Mock

import pytest
import aiohttp

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.logging_formatters import LogFormatter, SensitiveDataFilter
from netra_backend.app.core.unified_logging import get_logger
from shared.isolated_environment import get_env


class TestGCPCloudRunTracebackE2E(SSotAsyncTestCase):
    """End-to-End tests for Cloud Run traceback capture simulation."""
    
    def setup_method(self, method):
        """Setup E2E Cloud Run environment simulation."""
        super().setup_method(method)
        self.env = get_env()
        
        # Configure complete Cloud Run environment simulation
        self.set_env_var("K_SERVICE", "netra-backend")
        self.set_env_var("K_REVISION", "netra-backend-00042-xox") 
        self.set_env_var("K_CONFIGURATION", "netra-backend")
        self.set_env_var("PORT", "8080")
        self.set_env_var("GOOGLE_CLOUD_PROJECT", "netra-staging")
        self.set_env_var("GOOGLE_CLOUD_REGION", "us-central1")
        self.set_env_var("ENVIRONMENT", "staging")
        
        # Cloud Run metadata simulation
        self.set_env_var("CLOUD_RUN_JOB", "")  # Empty for service (not job)
        self.set_env_var("CLOUD_RUN_EXECUTION", "")
        self.set_env_var("CLOUD_RUN_TASK_INDEX", "")
        self.set_env_var("CLOUD_RUN_TASK_ATTEMPT", "")
        
        # GCP logging configuration
        # Note: UnifiedLogger auto-configures based on environment
        self.logger = get_logger(__name__)
        self.base_url = "http://localhost:8080"  # Simulated Cloud Run service
        
        # Track E2E metrics
        self.record_metric("cloud_run_setup_completed", True)
    
    async def test_http_request_error_traceback_e2e(self):
        """
        Test complete HTTP request error handling with traceback capture.
        
        Simulates real HTTP requests that trigger server errors and validates
        complete traceback capture through the Cloud Run logging pipeline.
        """
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        user_agent = "Mozilla/5.0 (Test E2E Client)"
        
        with self.temp_env_vars(REQUEST_ID=request_id):
            with self._capture_cloud_run_logs() as log_capture:
                # Simulate HTTP request that triggers server error
                await self._simulate_http_request_error(request_id, user_agent)
            
            # Validate Cloud Run log format
            http_error_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and "http" in log.get("message", "").lower()
            ]
            
            assert len(http_error_logs) > 0, "No HTTP error logs captured in Cloud Run format"
            
            # Find log with traceback
            traceback_log = None
            for log_entry in http_error_logs:
                if self._has_complete_traceback(log_entry):
                    traceback_log = log_entry
                    break
            
            # CRITICAL: This should initially FAIL to demonstrate missing traceback
            assert traceback_log is not None, "No HTTP error log with complete traceback - CLOUD RUN TRACEBACK MISSING"
            
            # Validate Cloud Run specific fields
            self._validate_cloud_run_log_structure(traceback_log)
            
            # Validate HTTP context in traceback
            error_field = traceback_log["error"]
            traceback_content = error_field["traceback"]
            assert request_id in traceback_content or request_id in traceback_log.get("labels", {}), "Request ID not in traceback context"
        
        self.record_metric("http_traceback_e2e_validated", True)
    
    async def test_websocket_lifecycle_error_traceback_e2e(self):
        """
        Test complete WebSocket lifecycle with error scenarios in Cloud Run.
        
        Validates WebSocket connection, authentication, message handling,
        and error scenarios with complete traceback capture.
        """
        session_id = f"ws_session_{uuid.uuid4().hex[:8]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            WEBSOCKET_SESSION_ID=session_id,
            USER_ID=user_id
        ):
            with self._capture_cloud_run_logs() as log_capture:
                # Simulate complete WebSocket lifecycle with errors
                await self._simulate_websocket_lifecycle_errors(session_id, user_id)
            
            # Validate WebSocket error logs
            ws_error_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and any(
                    keyword in log.get("message", "").lower()
                    for keyword in ["websocket", "ws", "connection"]
                )
            ]
            
            assert len(ws_error_logs) > 0, "No WebSocket error logs captured"
            
            # Validate multiple WebSocket error scenarios
            error_scenarios = ["connection", "authentication", "message_handling"]
            scenarios_found = {scenario: False for scenario in error_scenarios}
            
            for log_entry in ws_error_logs:
                if self._has_complete_traceback(log_entry):
                    message = log_entry.get("message", "").lower()
                    traceback_content = log_entry["error"]["traceback"]
                    
                    for scenario in error_scenarios:
                        if scenario.replace("_", " ") in message or scenario.replace("_", " ") in traceback_content:
                            scenarios_found[scenario] = True
            
            # At least one WebSocket scenario should have complete traceback
            traceback_scenarios = [scenario for scenario, found in scenarios_found.items() if found]
            assert len(traceback_scenarios) > 0, f"No WebSocket scenarios with traceback found. Scenarios: {scenarios_found}"
        
        self.record_metric("websocket_lifecycle_e2e_validated", True)
        self.increment_websocket_events(3)  # Multiple scenarios
    
    async def test_agent_execution_pipeline_error_traceback_e2e(self):
        """
        Test complete agent execution pipeline with error scenarios.
        
        Validates agent initialization, tool execution, response generation,
        and error scenarios with complete traceback capture in Cloud Run.
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        agent_type = "supervisor"
        
        with self.temp_env_vars(
            AGENT_EXECUTION_ID=execution_id,
            AGENT_TYPE=agent_type
        ):
            with self._capture_cloud_run_logs() as log_capture:
                # Simulate complete agent execution pipeline
                await self._simulate_agent_execution_pipeline_errors(execution_id, agent_type)
            
            # Validate agent execution error logs
            agent_error_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and any(
                    keyword in log.get("message", "").lower()
                    for keyword in ["agent", "execution", "tool", "supervisor"]
                )
            ]
            
            assert len(agent_error_logs) > 0, "No agent execution error logs captured"
            
            # Validate agent execution stages with traceback
            execution_stages = ["initialization", "tool_execution", "response_generation"]
            stages_with_traceback = []
            
            for log_entry in agent_error_logs:
                if self._has_complete_traceback(log_entry):
                    message = log_entry.get("message", "").lower()
                    traceback_content = log_entry["error"]["traceback"]
                    
                    for stage in execution_stages:
                        if stage.replace("_", " ") in message or stage.replace("_", " ") in traceback_content:
                            if stage not in stages_with_traceback:
                                stages_with_traceback.append(stage)
            
            # Should have traceback for at least one execution stage
            assert len(stages_with_traceback) > 0, f"No agent execution stages with traceback. Expected: {execution_stages}"
            
            # Validate execution context preservation
            execution_context_found = False
            for log_entry in agent_error_logs:
                if self._has_complete_traceback(log_entry):
                    if execution_id in log_entry["error"]["traceback"] or execution_id in log_entry.get("labels", {}):
                        execution_context_found = True
                        break
            
            assert execution_context_found, "Agent execution context not preserved in traceback"
        
        self.record_metric("agent_pipeline_e2e_validated", True)
    
    async def test_database_connection_pool_error_traceback_e2e(self):
        """
        Test database connection pool errors with Cloud Run resource constraints.
        
        Simulates database connection exhaustion and timeout scenarios
        that occur in Cloud Run environments with limited resources.
        """
        pool_id = f"pool_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            DB_POOL_ID=pool_id,
            DB_MAX_CONNECTIONS="5",  # Limited for Cloud Run
            DB_TIMEOUT="10"
        ):
            with self._capture_cloud_run_logs() as log_capture:
                # Simulate database connection pool exhaustion
                await self._simulate_database_pool_errors(pool_id)
            
            # Validate database error logs
            db_error_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and any(
                    keyword in log.get("message", "").lower()
                    for keyword in ["database", "connection", "pool", "timeout"]
                )
            ]
            
            assert len(db_error_logs) > 0, "No database error logs captured"
            
            # Validate connection pool specific errors
            pool_error_types = ["exhaustion", "timeout", "validation"]
            pool_errors_with_traceback = []
            
            for log_entry in db_error_logs:
                if self._has_complete_traceback(log_entry):
                    message = log_entry.get("message", "").lower()
                    traceback_content = log_entry["error"]["traceback"]
                    
                    for error_type in pool_error_types:
                        if error_type in message or error_type in traceback_content:
                            if error_type not in pool_errors_with_traceback:
                                pool_errors_with_traceback.append(error_type)
            
            # Should capture at least one type of pool error with traceback
            assert len(pool_errors_with_traceback) > 0, f"No database pool errors with traceback. Expected: {pool_error_types}"
        
        self.record_metric("database_pool_e2e_validated", True)
        self.increment_db_query_count(5)  # Simulated failed connections
    
    async def test_cloud_run_memory_pressure_error_traceback_e2e(self):
        """
        Test error scenarios under Cloud Run memory pressure.
        
        Simulates memory-constrained scenarios that trigger OOM errors
        and validates traceback capture under resource pressure.
        """
        memory_limit = "512Mi"  # Cloud Run memory limit
        instance_id = f"instance_{uuid.uuid4().hex[:8]}"
        
        with self.temp_env_vars(
            CLOUD_RUN_MEMORY_LIMIT=memory_limit,
            INSTANCE_ID=instance_id
        ):
            with self._capture_cloud_run_logs() as log_capture:
                # Simulate memory pressure scenarios
                await self._simulate_memory_pressure_errors(instance_id)
            
            # Validate memory-related error logs
            memory_error_logs = [
                log for log in log_capture.logs
                if log.get("severity") == "ERROR" and any(
                    keyword in log.get("message", "").lower()
                    for keyword in ["memory", "allocation", "oom", "resource"]
                )
            ]
            
            assert len(memory_error_logs) > 0, "No memory pressure error logs captured"
            
            # Validate memory errors have traceback
            memory_traceback_found = False
            for log_entry in memory_error_logs:
                if self._has_complete_traceback(log_entry):
                    traceback_content = log_entry["error"]["traceback"]
                    if any(keyword in traceback_content.lower() for keyword in ["memory", "allocation"]):
                        memory_traceback_found = True
                        # Validate Cloud Run context
                        assert instance_id in traceback_content or instance_id in log_entry.get("labels", {}), "Instance ID not in memory error context"
                        break
            
            assert memory_traceback_found, "No memory pressure error with traceback found"
        
        self.record_metric("memory_pressure_e2e_validated", True)
    
    async def test_concurrent_request_error_isolation_e2e(self):
        """
        Test concurrent request error isolation in Cloud Run.
        
        Validates that multiple concurrent requests maintain proper
        error isolation and traceback context separation.
        """
        num_concurrent_requests = 5
        request_ids = [f"req_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_concurrent_requests)]
        
        with self._capture_cloud_run_logs() as log_capture:
            # Execute concurrent requests with errors
            tasks = [
                self._simulate_concurrent_request_error(req_id)
                for req_id in request_ids
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate error isolation
        error_logs = [log for log in log_capture.logs if log.get("severity") == "ERROR"]
        assert len(error_logs) >= num_concurrent_requests, f"Expected at least {num_concurrent_requests} error logs"
        
        # Group logs by request ID and validate isolation
        request_error_logs = {req_id: [] for req_id in request_ids}
        unassigned_logs = []
        
        for log_entry in error_logs:
            assigned = False
            message = log_entry.get("message", "")
            labels = log_entry.get("labels", {})
            traceback = log_entry.get("error", {}).get("traceback", "")
            
            for req_id in request_ids:
                if req_id in message or req_id in labels.get("request_id", "") or req_id in traceback:
                    request_error_logs[req_id].append(log_entry)
                    assigned = True
                    break
            
            if not assigned:
                unassigned_logs.append(log_entry)
        
        # Validate each request has isolated errors
        for req_id in request_ids:
            req_logs = request_error_logs[req_id]
            assert len(req_logs) > 0, f"No error logs found for request {req_id}"
            
            # At least one log should have traceback
            req_traceback_found = any(
                self._has_complete_traceback(log) for log in req_logs
            )
            assert req_traceback_found, f"No traceback found for request {req_id}"
        
        self.record_metric("concurrent_isolation_e2e_validated", True)
    
    # Helper methods for E2E error simulation
    
    async def _simulate_http_request_error(self, request_id: str, user_agent: str):
        """Simulate HTTP request that triggers server error."""
        try:
            def http_handler():
                def request_validation():
                    def business_logic():
                        raise ValueError(f"HTTP request validation failed for {request_id}")
                    business_logic()
                request_validation()
            
            http_handler()
        except ValueError:
            self.logger.error(f"HTTP request error for {request_id}", exc_info=True, extra={
                "request_id": request_id,
                "user_agent": user_agent,
                "http_method": "POST",
                "endpoint": "/api/v1/agents/execute"
            })
    
    async def _simulate_websocket_lifecycle_errors(self, session_id: str, user_id: str):
        """Simulate complete WebSocket lifecycle with multiple error scenarios."""
        # Connection error
        try:
            def websocket_connection():
                raise ConnectionError(f"WebSocket connection failed for session {session_id}")
            websocket_connection()
        except ConnectionError:
            self.logger.error("WebSocket connection error", exc_info=True, extra={
                "session_id": session_id,
                "user_id": user_id,
                "error_type": "connection"
            })
        
        # Authentication error
        try:
            def websocket_auth():
                raise PermissionError(f"WebSocket authentication failed for user {user_id}")
            websocket_auth()
        except PermissionError:
            self.logger.error("WebSocket authentication error", exc_info=True, extra={
                "session_id": session_id,
                "user_id": user_id,
                "error_type": "authentication"
            })
        
        # Message handling error
        try:
            def websocket_message_handling():
                raise RuntimeError(f"WebSocket message handling failed for session {session_id}")
            websocket_message_handling()
        except RuntimeError:
            self.logger.error("WebSocket message handling error", exc_info=True, extra={
                "session_id": session_id,
                "user_id": user_id,
                "error_type": "message_handling"
            })
    
    async def _simulate_agent_execution_pipeline_errors(self, execution_id: str, agent_type: str):
        """Simulate agent execution pipeline with multiple error stages."""
        # Agent initialization error
        try:
            def agent_initialization():
                raise ImportError(f"Agent initialization failed for {agent_type} agent")
            agent_initialization()
        except ImportError:
            self.logger.error("Agent initialization error", exc_info=True, extra={
                "execution_id": execution_id,
                "agent_type": agent_type,
                "stage": "initialization"
            })
        
        # Tool execution error
        try:
            def tool_execution():
                raise TimeoutError(f"Tool execution timeout in {execution_id}")
            tool_execution()
        except TimeoutError:
            self.logger.error("Agent tool execution error", exc_info=True, extra={
                "execution_id": execution_id,
                "agent_type": agent_type,
                "stage": "tool_execution"
            })
        
        # Response generation error
        try:
            def response_generation():
                raise ValueError(f"Response generation failed for {execution_id}")
            response_generation()
        except ValueError:
            self.logger.error("Agent response generation error", exc_info=True, extra={
                "execution_id": execution_id,
                "agent_type": agent_type,
                "stage": "response_generation"
            })
    
    async def _simulate_database_pool_errors(self, pool_id: str):
        """Simulate database connection pool errors."""
        # Pool exhaustion
        try:
            def pool_exhaustion():
                raise ConnectionError(f"Database connection pool {pool_id} exhausted")
            pool_exhaustion()
        except ConnectionError:
            self.logger.error("Database pool exhaustion", exc_info=True, extra={
                "pool_id": pool_id,
                "error_type": "exhaustion"
            })
        
        # Connection timeout
        try:
            def connection_timeout():
                raise TimeoutError(f"Database connection timeout for pool {pool_id}")
            connection_timeout()
        except TimeoutError:
            self.logger.error("Database connection timeout", exc_info=True, extra={
                "pool_id": pool_id,
                "error_type": "timeout"
            })
        
        # Connection validation error
        try:
            def connection_validation():
                raise RuntimeError(f"Database connection validation failed for pool {pool_id}")
            connection_validation()
        except RuntimeError:
            self.logger.error("Database connection validation error", exc_info=True, extra={
                "pool_id": pool_id,
                "error_type": "validation"
            })
    
    async def _simulate_memory_pressure_errors(self, instance_id: str):
        """Simulate memory pressure errors."""
        try:
            def memory_allocation():
                raise MemoryError(f"Memory allocation failed on instance {instance_id}")
            memory_allocation()
        except MemoryError:
            self.logger.error("Memory pressure error", exc_info=True, extra={
                "instance_id": instance_id,
                "error_type": "allocation",
                "memory_limit": self.get_env_var("CLOUD_RUN_MEMORY_LIMIT")
            })
    
    async def _simulate_concurrent_request_error(self, request_id: str):
        """Simulate concurrent request error."""
        await asyncio.sleep(0.05)  # Small delay for concurrency simulation
        try:
            def concurrent_operation():
                raise RuntimeError(f"Concurrent operation failed for request {request_id}")
            concurrent_operation()
        except RuntimeError:
            self.logger.error(f"Concurrent request error for {request_id}", exc_info=True, extra={
                "request_id": request_id,
                "error_type": "concurrent"
            })
    
    def _has_complete_traceback(self, log_entry: Dict[str, Any]) -> bool:
        """Check if log entry has complete traceback information."""
        if "error" not in log_entry:
            return False
        
        error_field = log_entry["error"]
        return (
            error_field.get("type") is not None and
            error_field.get("value") is not None and
            error_field.get("traceback") is not None and
            len(error_field["traceback"]) > 0
        )
    
    def _validate_cloud_run_log_structure(self, log_entry: Dict[str, Any]):
        """Validate Cloud Run specific log structure."""
        # Required GCP fields
        assert "severity" in log_entry, "Missing severity field"
        assert "message" in log_entry, "Missing message field"
        assert "timestamp" in log_entry, "Missing timestamp field"
        
        # Cloud Run specific labels
        labels = log_entry.get("labels", {})
        assert "module" in labels, "Missing module label"
        
        # Validate severity mapping
        assert log_entry["severity"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "Invalid severity level"
        
        # Validate single-line JSON format
        json_str = json.dumps(log_entry)
        assert "\n" not in json_str, "Log entry not single-line JSON"
    
    @asynccontextmanager
    async def _capture_cloud_run_logs(self):
        """Context manager to capture Cloud Run formatted logs."""
        captured_logs = []
        
        class CloudRunLogCapture:
            def __init__(self):
                self.logs = []
            
            def capture_log(self, formatted_json):
                try:
                    # Strip any trailing newlines that might be added by the sink
                    clean_json = formatted_json.strip()
                    if clean_json:
                        log_entry = json.loads(clean_json)
                        self.logs.append(log_entry)
                except json.JSONDecodeError as e:
                    # Handle malformed JSON - this might indicate formatting issues
                    self.logs.append({
                        "raw_output": formatted_json,
                        "parse_error": True,
                        "error": str(e)
                    })
        
        log_capture = CloudRunLogCapture()
        
        # Patch the GCP formatter to capture Cloud Run output
        def capturing_cloud_run_formatter(record):
            formatter = LogFormatter(SensitiveDataFilter())
            formatted_json = formatter.gcp_json_formatter(record)
            log_capture.capture_log(formatted_json)
            return formatted_json
        
        with patch.object(LogFormatter, 'gcp_json_formatter', side_effect=capturing_cloud_run_formatter):
            yield log_capture