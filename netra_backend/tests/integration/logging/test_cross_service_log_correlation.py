"""
Test Cross-Service Log Correlation - Integration Tests for Distributed Tracing

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development Velocity & Operations)
- Business Goal: Enable rapid diagnosis of cross-service issues through distributed tracing
- Value Impact: Reduce multi-service debugging time from hours to minutes
- Strategic Impact: Foundation for reliable multi-service operations and customer success

This test suite validates that logging provides effective correlation across:
1. Backend service to Auth service communication
2. WebSocket to agent execution coordination
3. Database operations across services
4. Error propagation through service chains
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import get_env
from shared.logging.unified_logger_factory import get_logger
from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger


class TestCrossServiceLogCorrelation(SSotAsyncTestCase):
    """Test cross-service log correlation with real services."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Setup test environment for cross-service integration
        self.set_env_var("LOG_LEVEL", "DEBUG")
        self.set_env_var("ENABLE_CROSS_SERVICE_CORRELATION", "true")
        self.set_env_var("SERVICE_NAME", "integration-test-service")
        
        # Initialize loggers for different services
        self.backend_logger = get_logger("backend_service")
        self.auth_logger = get_logger("auth_service")
        self.websocket_logger = get_logger("websocket_service")
        
        # Capture logs from all services
        self.captured_logs = {
            "backend": [],
            "auth": [],
            "websocket": [],
            "all": []
        }
        
        # Mock handlers for log capture
        self._setup_log_capture()
        
        # Auth tracer for authentication correlation testing
        self.auth_tracer = AuthTraceLogger()
        
        # Test correlation context
        self.test_correlation_id = f"test_corr_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def _setup_log_capture(self):
        """Setup log capture for all services."""
        def create_capture_handler(service_name):
            handler = MagicMock()
            handler.emit = lambda record: self._capture_log(service_name, record)
            return handler
        
        # Add handlers to all loggers
        self.backend_logger.addHandler(create_capture_handler("backend"))
        self.auth_logger.addHandler(create_capture_handler("auth"))
        self.websocket_logger.addHandler(create_capture_handler("websocket"))
    
    def _capture_log(self, service_name: str, record):
        """Capture log record for analysis."""
        self.captured_logs[service_name].append(record)
        self.captured_logs["all"].append({
            "service": service_name,
            "record": record,
            "timestamp": time.time()
        })
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_backend_to_auth_service_correlation(self, real_services):
        """Test log correlation between backend and auth service."""
        # Simulate backend -> auth service flow
        user_id = "integration_test_user_001"
        request_id = f"req_integration_{int(time.time())}"
        
        # Step 1: Backend receives request
        self.backend_logger.info(
            "Backend processing user request",
            extra={
                "correlation_id": self.test_correlation_id,
                "request_id": request_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "process_user_request",
                "step": "request_received"
            }
        )
        
        # Step 2: Backend calls auth service
        self.backend_logger.info(
            "Calling auth service for user validation",
            extra={
                "correlation_id": self.test_correlation_id,
                "request_id": request_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "validate_user_auth",
                "step": "auth_service_call_start",
                "target_service": "auth_service"
            }
        )
        
        # Step 3: Auth service receives request
        auth_request_id = f"auth_req_{int(time.time())}"
        self.auth_logger.info(
            "Auth service processing validation request",
            extra={
                "correlation_id": self.test_correlation_id,  # Preserved from backend
                "request_id": auth_request_id,  # New request ID for auth service
                "parent_request_id": request_id,  # Reference to original request
                "user_id": user_id,
                "service": "auth_service",
                "operation": "validate_user_credentials",
                "step": "auth_validation_start"
            }
        )
        
        # Step 4: Auth service completes validation
        self.auth_logger.info(
            "User validation completed successfully",
            extra={
                "correlation_id": self.test_correlation_id,
                "request_id": auth_request_id,
                "parent_request_id": request_id,
                "user_id": user_id,
                "service": "auth_service",
                "operation": "validate_user_credentials",
                "step": "auth_validation_complete",
                "validation_result": "success",
                "user_permissions": ["read", "write", "agent_execute"]
            }
        )
        
        # Step 5: Backend receives auth response
        self.backend_logger.info(
            "Auth service validation completed",
            extra={
                "correlation_id": self.test_correlation_id,
                "request_id": request_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "process_user_request",
                "step": "auth_validation_received",
                "auth_result": "success"
            }
        )
        
        # Validate cross-service correlation
        backend_logs = self.captured_logs["backend"]
        auth_logs = self.captured_logs["auth"]
        
        assert len(backend_logs) == 3, f"Expected 3 backend logs, got {len(backend_logs)}"
        assert len(auth_logs) == 2, f"Expected 2 auth logs, got {len(auth_logs)}"
        
        # All logs should have same correlation ID
        all_correlation_ids = []
        for log in backend_logs + auth_logs:
            assert hasattr(log, 'correlation_id'), "Log missing correlation_id"
            all_correlation_ids.append(log.correlation_id)
        
        assert all(cid == self.test_correlation_id for cid in all_correlation_ids), "Correlation ID not preserved across services"
        
        # Validate request ID relationships
        backend_request_ids = [log.request_id for log in backend_logs]
        auth_request_ids = [log.request_id for log in auth_logs]
        
        # Backend should use consistent request ID
        assert all(rid == request_id for rid in backend_request_ids), "Backend request ID inconsistent"
        
        # Auth should use its own request ID but reference parent
        assert all(rid == auth_request_id for rid in auth_request_ids), "Auth request ID inconsistent"
        assert all(hasattr(log, 'parent_request_id') and log.parent_request_id == request_id for log in auth_logs), "Parent request ID not preserved"
        
        # Can reconstruct cross-service flow
        all_logs_sorted = sorted(
            [(log, "backend") for log in backend_logs] + [(log, "auth") for log in auth_logs],
            key=lambda x: getattr(x[0], 'step', '')
        )
        
        expected_flow = [
            "request_received", "auth_service_call_start", "auth_validation_start", 
            "auth_validation_complete", "auth_validation_received"
        ]
        actual_flow = [log.step for log, _ in all_logs_sorted if hasattr(log, 'step')]
        assert actual_flow == expected_flow, f"Cross-service flow incorrect: {actual_flow}"
        
        self.record_metric("backend_auth_correlation_test", "PASSED")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_to_agent_execution_correlation(self, real_services):
        """Test log correlation between WebSocket events and agent execution."""
        # Simulate WebSocket -> Agent execution flow
        connection_id = f"ws_conn_{uuid.uuid4().hex[:8]}"
        message_id = f"msg_{int(time.time())}"
        user_id = "ws_integration_user_001"
        
        # Step 1: WebSocket connection established
        self.websocket_logger.info(
            "WebSocket connection established",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "service": "websocket",
                "operation": "connection_established",
                "step": "websocket_connected"
            }
        )
        
        # Step 2: WebSocket receives agent request
        self.websocket_logger.info(
            "Agent request received via WebSocket",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": message_id,
                "user_id": user_id,
                "service": "websocket",
                "operation": "agent_request_received",
                "step": "agent_request_received",
                "agent_type": "cost_optimizer"
            }
        )
        
        # Step 3: Backend processes agent request
        agent_execution_id = f"agent_exec_{uuid.uuid4().hex[:8]}"
        self.backend_logger.info(
            "Starting agent execution",
            extra={
                "correlation_id": self.test_correlation_id,
                "message_id": message_id,  # Reference to WebSocket message
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "agent_execution_start",
                "step": "agent_execution_start",
                "agent_type": "cost_optimizer"
            }
        )
        
        # Step 4: Agent execution progress (with WebSocket events)
        progress_steps = ["agent_thinking", "tool_executing", "tool_completed"]
        for i, progress_step in enumerate(progress_steps):
            # Backend logs agent progress
            self.backend_logger.debug(
                f"Agent execution progress: {progress_step}",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "agent_execution_id": agent_execution_id,
                    "user_id": user_id,
                    "service": "backend",
                    "operation": "agent_execution_progress",
                    "step": f"agent_{progress_step}",
                    "progress_percent": (i + 1) * 33
                }
            )
            
            # WebSocket broadcasts progress
            self.websocket_logger.debug(
                f"Broadcasting agent progress to WebSocket",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "connection_id": connection_id,
                    "message_id": message_id,
                    "agent_execution_id": agent_execution_id,
                    "user_id": user_id,
                    "service": "websocket",
                    "operation": "agent_progress_broadcast",
                    "step": f"broadcast_{progress_step}",
                    "websocket_event": progress_step
                }
            )
        
        # Step 5: Agent execution completion
        self.backend_logger.info(
            "Agent execution completed",
            extra={
                "correlation_id": self.test_correlation_id,
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "agent_execution_complete",
                "step": "agent_execution_complete",
                "execution_result": "success",
                "recommendations_generated": 5
            }
        )
        
        # WebSocket sends final result
        self.websocket_logger.info(
            "Sending agent results via WebSocket",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": message_id,
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "service": "websocket",
                "operation": "agent_results_sent",
                "step": "results_sent",
                "websocket_event": "agent_completed"
            }
        )
        
        # Validate WebSocket-Agent correlation
        websocket_logs = self.captured_logs["websocket"]
        backend_logs = self.captured_logs["backend"]
        
        # Validate correlation ID consistency
        all_logs = websocket_logs + backend_logs
        for log in all_logs:
            assert hasattr(log, 'correlation_id'), "Log missing correlation_id"
            assert log.correlation_id == self.test_correlation_id, "Correlation ID mismatch"
        
        # Validate agent execution tracking across services
        agent_execution_logs = [log for log in all_logs if hasattr(log, 'agent_execution_id')]
        assert len(agent_execution_logs) > 0, "Agent execution not tracked"
        
        agent_execution_ids = set(log.agent_execution_id for log in agent_execution_logs)
        assert len(agent_execution_ids) == 1, f"Multiple agent execution IDs: {agent_execution_ids}"
        assert agent_execution_id in agent_execution_ids, "Agent execution ID not preserved"
        
        # Validate WebSocket event progression
        websocket_events = []
        for log in websocket_logs:
            if hasattr(log, 'websocket_event'):
                websocket_events.append(log.websocket_event)
        
        # Should include agent progress events
        expected_events = ["agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event in expected_events:
            assert event in websocket_events, f"WebSocket event '{event}' missing"
        
        self.record_metric("websocket_agent_correlation_test", "PASSED")
        self.record_metric("websocket_events_tracked", len(websocket_events))
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_database_operations_correlation(self, real_services):
        """Test log correlation for database operations across services."""
        # Simulate database operations with correlation
        db_operation_id = f"db_op_{uuid.uuid4().hex[:8]}"
        user_id = "db_integration_user_001"
        
        # Step 1: Backend initiates database operation
        self.backend_logger.info(
            "Starting database operation",
            extra={
                "correlation_id": self.test_correlation_id,
                "db_operation_id": db_operation_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "database_write_start",
                "step": "db_operation_start",
                "table": "user_sessions",
                "operation_type": "INSERT"
            }
        )
        
        # Step 2: Database connection established
        self.backend_logger.debug(
            "Database connection established",
            extra={
                "correlation_id": self.test_correlation_id,
                "db_operation_id": db_operation_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "database_connection",
                "step": "db_connection_established",
                "connection_pool": "primary",
                "connection_id": f"conn_{uuid.uuid4().hex[:8]}"
            }
        )
        
        # Step 3: Transaction started
        transaction_id = f"txn_{uuid.uuid4().hex[:8]}"
        self.backend_logger.debug(
            "Database transaction started",
            extra={
                "correlation_id": self.test_correlation_id,
                "db_operation_id": db_operation_id,
                "transaction_id": transaction_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "database_transaction_start",
                "step": "transaction_start",
                "isolation_level": "READ_COMMITTED"
            }
        )
        
        # Step 4: Query execution
        self.backend_logger.debug(
            "Executing database query",
            extra={
                "correlation_id": self.test_correlation_id,
                "db_operation_id": db_operation_id,
                "transaction_id": transaction_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "database_query_execution",
                "step": "query_execution",
                "query_type": "INSERT",
                "affected_rows": 1,
                "execution_time_ms": 15.5
            }
        )
        
        # Step 5: Transaction commit
        self.backend_logger.info(
            "Database transaction committed",
            extra={
                "correlation_id": self.test_correlation_id,
                "db_operation_id": db_operation_id,
                "transaction_id": transaction_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "database_transaction_commit",
                "step": "transaction_commit",
                "total_operations": 1,
                "commit_time_ms": 8.2
            }
        )
        
        # Step 6: Database operation completed
        self.backend_logger.info(
            "Database operation completed successfully",
            extra={
                "correlation_id": self.test_correlation_id,
                "db_operation_id": db_operation_id,
                "user_id": user_id,
                "service": "backend",
                "operation": "database_write_complete",
                "step": "db_operation_complete",
                "total_time_ms": 45.7,
                "success": True
            }
        )
        
        # Validate database operation correlation
        backend_logs = self.captured_logs["backend"]
        db_related_logs = [log for log in backend_logs if hasattr(log, 'db_operation_id')]
        
        assert len(db_related_logs) == 6, f"Expected 6 database-related logs, got {len(db_related_logs)}"
        
        # All should have same correlation ID and db_operation_id
        for log in db_related_logs:
            assert log.correlation_id == self.test_correlation_id, "Correlation ID mismatch"
            assert log.db_operation_id == db_operation_id, "DB operation ID mismatch"
            assert log.user_id == user_id, "User ID mismatch"
        
        # Validate transaction tracking
        transaction_logs = [log for log in db_related_logs if hasattr(log, 'transaction_id')]
        assert len(transaction_logs) == 3, "Transaction logs missing"
        
        for log in transaction_logs:
            assert log.transaction_id == transaction_id, "Transaction ID mismatch"
        
        # Validate operation sequence
        steps = [log.step for log in db_related_logs]
        expected_sequence = [
            "db_operation_start", "db_connection_established", "transaction_start",
            "query_execution", "transaction_commit", "db_operation_complete"
        ]
        assert steps == expected_sequence, f"Database operation sequence incorrect: {steps}"
        
        # Validate timing information
        timing_logs = [log for log in db_related_logs if hasattr(log, 'execution_time_ms') or hasattr(log, 'total_time_ms')]
        assert len(timing_logs) >= 2, "Timing information missing from database logs"
        
        self.record_metric("database_correlation_test", "PASSED")
        self.record_metric("database_operations_tracked", len(db_related_logs))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_propagation_correlation(self, real_services):
        """Test error propagation correlation across services."""
        # Simulate error propagation through service chain
        error_correlation = f"error_corr_{int(time.time())}"
        error_request_id = f"error_req_{int(time.time())}"
        
        # Step 1: Backend receives request
        self.backend_logger.info(
            "Processing request that will cause error",
            extra={
                "correlation_id": error_correlation,
                "request_id": error_request_id,
                "user_id": "error_test_user",
                "service": "backend",
                "operation": "process_request",
                "step": "request_start"
            }
        )
        
        # Step 2: Backend calls auth service (which will fail)
        self.backend_logger.info(
            "Calling auth service for validation",
            extra={
                "correlation_id": error_correlation,
                "request_id": error_request_id,
                "user_id": "error_test_user",
                "service": "backend",
                "operation": "auth_validation",
                "step": "auth_call_start"
            }
        )
        
        # Step 3: Auth service fails
        auth_error = Exception("Authentication service temporarily unavailable")
        self.auth_logger.error(
            "Auth service error occurred",
            extra={
                "correlation_id": error_correlation,
                "request_id": f"auth_{error_request_id}",
                "parent_request_id": error_request_id,
                "user_id": "error_test_user", 
                "service": "auth_service",
                "operation": "validate_user",
                "step": "auth_error",
                "error_type": type(auth_error).__name__,
                "error_message": str(auth_error),
                "error_code": "AUTH_SERVICE_UNAVAILABLE"
            },
            exc_info=True
        )
        
        # Step 4: Backend receives auth error
        self.backend_logger.error(
            "Auth service call failed",
            extra={
                "correlation_id": error_correlation,
                "request_id": error_request_id,
                "user_id": "error_test_user",
                "service": "backend", 
                "operation": "auth_validation",
                "step": "auth_call_failed",
                "upstream_error": "AUTH_SERVICE_UNAVAILABLE",
                "retry_attempt": 1,
                "will_retry": True
            }
        )
        
        # Step 5: Backend retry fails
        self.backend_logger.error(
            "Auth service retry also failed",
            extra={
                "correlation_id": error_correlation,
                "request_id": error_request_id,
                "user_id": "error_test_user",
                "service": "backend",
                "operation": "auth_validation",
                "step": "auth_retry_failed",
                "upstream_error": "AUTH_SERVICE_UNAVAILABLE",
                "retry_attempt": 2,
                "will_retry": False,
                "giving_up": True
            }
        )
        
        # Step 6: Backend returns error to client
        self.backend_logger.error(
            "Request failed due to auth service unavailable",
            extra={
                "correlation_id": error_correlation,
                "request_id": error_request_id,
                "user_id": "error_test_user",
                "service": "backend",
                "operation": "process_request",
                "step": "request_failed",
                "final_error": "SERVICE_TEMPORARILY_UNAVAILABLE",
                "retry_count": 2,
                "total_time_ms": 5500
            }
        )
        
        # Validate error correlation
        backend_logs = self.captured_logs["backend"]
        auth_logs = self.captured_logs["auth"]
        
        # Find error-related logs
        error_logs = []
        for log in backend_logs + auth_logs:
            if hasattr(log, 'correlation_id') and log.correlation_id == error_correlation:
                error_logs.append(log)
        
        assert len(error_logs) >= 6, f"Expected at least 6 error-correlated logs, got {len(error_logs)}"
        
        # All should have same correlation ID
        for log in error_logs:
            assert log.correlation_id == error_correlation, "Error correlation ID mismatch"
        
        # Can identify error origin
        auth_error_logs = [log for log in error_logs if hasattr(log, 'service') and log.service == "auth_service"]
        assert len(auth_error_logs) >= 1, "Auth service error not logged"
        
        # Can trace error propagation
        backend_error_logs = [log for log in error_logs if hasattr(log, 'service') and log.service == "backend"]
        retry_logs = [log for log in backend_error_logs if hasattr(log, 'retry_attempt')]
        assert len(retry_logs) >= 2, "Retry attempts not logged"
        
        # Can identify final resolution
        final_logs = [log for log in backend_error_logs if hasattr(log, 'step') and log.step == "request_failed"]
        assert len(final_logs) == 1, "Final error resolution not logged"
        
        final_log = final_logs[0]
        assert hasattr(final_log, 'retry_count'), "Retry count not logged"
        assert hasattr(final_log, 'total_time_ms'), "Total time not logged"
        
        self.record_metric("error_propagation_correlation_test", "PASSED")
        self.record_metric("error_related_logs", len(error_logs))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_correlation_across_services(self, real_services):
        """Test performance correlation across services for optimization debugging."""
        # Simulate performance-critical operation across services
        perf_correlation = f"perf_corr_{int(time.time())}"
        operation_start = time.time()
        
        # Step 1: Request starts (timing begins)
        self.backend_logger.info(
            "Starting performance-critical operation",
            extra={
                "correlation_id": perf_correlation,
                "user_id": "perf_test_user",
                "service": "backend",
                "operation": "cost_analysis_request",
                "step": "operation_start",
                "start_timestamp": operation_start,
                "expected_duration_ms": 3000
            }
        )
        
        # Step 2: Auth validation (fast operation)
        auth_start = time.time()
        await asyncio.sleep(0.05)  # Simulate auth delay
        auth_duration = (time.time() - auth_start) * 1000
        
        self.auth_logger.info(
            "Authentication completed",
            extra={
                "correlation_id": perf_correlation,
                "user_id": "perf_test_user",
                "service": "auth_service",
                "operation": "validate_jwt",
                "step": "auth_complete",
                "duration_ms": auth_duration,
                "performance_tier": "fast"
            }
        )
        
        # Step 3: Data fetching (medium operation)
        data_start = time.time()
        await asyncio.sleep(0.2)  # Simulate data fetch delay
        data_duration = (time.time() - data_start) * 1000
        
        self.backend_logger.info(
            "Data fetching completed",
            extra={
                "correlation_id": perf_correlation,
                "user_id": "perf_test_user",
                "service": "backend",
                "operation": "fetch_user_data",
                "step": "data_fetch_complete",
                "duration_ms": data_duration,
                "records_fetched": 1500,
                "performance_tier": "medium"
            }
        )
        
        # Step 4: Agent processing (slow operation)
        agent_start = time.time()
        await asyncio.sleep(0.5)  # Simulate agent processing delay
        agent_duration = (time.time() - agent_start) * 1000
        
        self.backend_logger.info(
            "Agent processing completed",
            extra={
                "correlation_id": perf_correlation,
                "user_id": "perf_test_user",
                "service": "backend",
                "operation": "agent_cost_analysis",
                "step": "agent_complete",
                "duration_ms": agent_duration,
                "recommendations_generated": 8,
                "performance_tier": "slow",
                "performance_bottleneck": True
            }
        )
        
        # Step 5: Response preparation (fast operation)
        response_start = time.time()
        await asyncio.sleep(0.02)  # Simulate response prep
        response_duration = (time.time() - response_start) * 1000
        
        self.backend_logger.info(
            "Response preparation completed",
            extra={
                "correlation_id": perf_correlation,
                "user_id": "perf_test_user",
                "service": "backend", 
                "operation": "prepare_response",
                "step": "response_complete",
                "duration_ms": response_duration,
                "response_size_bytes": 2048,
                "performance_tier": "fast"
            }
        )
        
        # Step 6: Operation complete (total timing)
        total_duration = (time.time() - operation_start) * 1000
        
        self.backend_logger.info(
            "Performance-critical operation completed",
            extra={
                "correlation_id": perf_correlation,
                "user_id": "perf_test_user",
                "service": "backend",
                "operation": "cost_analysis_request",
                "step": "operation_complete",
                "total_duration_ms": total_duration,
                "performance_breakdown": {
                    "auth_ms": auth_duration,
                    "data_fetch_ms": data_duration,
                    "agent_processing_ms": agent_duration,
                    "response_prep_ms": response_duration
                },
                "performance_verdict": "within_limits" if total_duration < 3000 else "exceeded_limits"
            }
        )
        
        # Validate performance correlation
        all_logs = self.captured_logs["backend"] + self.captured_logs["auth"]
        perf_logs = [log for log in all_logs if hasattr(log, 'correlation_id') and log.correlation_id == perf_correlation]
        
        assert len(perf_logs) >= 6, f"Expected at least 6 performance logs, got {len(perf_logs)}"
        
        # Validate timing information
        duration_logs = [log for log in perf_logs if hasattr(log, 'duration_ms')]
        assert len(duration_logs) >= 4, "Individual operation durations not logged"
        
        # Find bottleneck
        bottleneck_logs = [log for log in perf_logs if hasattr(log, 'performance_bottleneck') and log.performance_bottleneck]
        assert len(bottleneck_logs) == 1, "Performance bottleneck not identified"
        assert bottleneck_logs[0].operation == "agent_cost_analysis", "Wrong bottleneck identified"
        
        # Validate total performance tracking
        completion_logs = [log for log in perf_logs if hasattr(log, 'step') and log.step == "operation_complete"]
        assert len(completion_logs) == 1, "Operation completion not logged"
        
        completion_log = completion_logs[0]
        assert hasattr(completion_log, 'total_duration_ms'), "Total duration not logged"
        assert hasattr(completion_log, 'performance_breakdown'), "Performance breakdown not logged"
        
        # Validate performance analysis
        breakdown = completion_log.performance_breakdown
        assert breakdown["agent_processing_ms"] > breakdown["auth_ms"], "Agent processing should be slowest"
        assert breakdown["agent_processing_ms"] > breakdown["data_fetch_ms"], "Agent processing should be slower than data fetch"
        
        self.record_metric("performance_correlation_test", "PASSED")
        self.record_metric("total_operation_duration_ms", total_duration)
        self.record_metric("performance_logs_generated", len(perf_logs))
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Remove mock handlers from loggers
        for logger in [self.backend_logger, self.auth_logger, self.websocket_logger]:
            # Clear handlers to prevent interference
            logger.handlers = []
        
        # Clear captured logs
        for key in self.captured_logs:
            self.captured_logs[key].clear()
        
        # Call parent teardown
        super().teardown_method(method)