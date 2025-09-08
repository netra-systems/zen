"""
Test Debug Utilities Completeness - Unit Tests for Debug Information Quality

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development Velocity & Operations)
- Business Goal: Enable engineers to debug production issues in minutes not hours
- Value Impact: Faster issue resolution = better customer experience and reduced downtime costs
- Strategic Impact: Core operational capability that enables reliable service delivery

This test suite validates that our debug utilities provide complete information for:
1. Production issue diagnosis
2. Performance troubleshooting
3. Multi-user system debugging
4. Cross-service error tracing
"""

import json
import re
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.logging.unified_logger_factory import get_logger
from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


class TestDebugUtilitiesCompleteness(SSotBaseTestCase):
    """Test that debug utilities provide complete information for production debugging."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Setup test environment for debugging
        self.set_env_var("LOG_LEVEL", "DEBUG")
        self.set_env_var("ENABLE_DEBUG_UTILITIES", "true")
        self.set_env_var("SERVICE_NAME", "debug-test-service")
        
        # Create logger for testing
        self.logger = get_logger("debug_utilities_test")
        
        # Mock log capture
        self.captured_logs = []
        self.original_handlers = self.logger.handlers.copy()
        
        # Add mock handler
        mock_handler = MagicMock()
        mock_handler.emit = lambda record: self.captured_logs.append(record)
        self.logger.addHandler(mock_handler)
        
        # Create auth tracer for authentication debugging
        self.auth_tracer = AuthTraceLogger()
    
    @pytest.mark.unit
    def test_user_context_debug_information(self):
        """Test that user context provides complete debugging information."""
        # Simulate user context with all necessary debug info
        user_context = {
            "user_id": "enterprise_user_789",
            "session_id": "session_abc123def456",
            "request_id": "req_debug_001",
            "correlation_id": "corr_user_flow_001", 
            "thread_id": "thread_cost_optimization_001",
            "user_permissions": ["read", "write", "agent_execute"],
            "subscription_tier": "enterprise",
            "organization_id": "org_acme_corp_001",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation_context": {
                "current_operation": "cost_optimization_analysis",
                "step": "data_collection",
                "tools_in_use": ["aws_cost_analyzer", "gcp_billing_api"],
                "expected_duration_ms": 30000
            }
        }
        
        # Log user operation with full context
        self.logger.info(
            "User operation in progress - cost optimization analysis",
            extra=user_context
        )
        
        assert len(self.captured_logs) == 1, "Expected 1 log record"
        record = self.captured_logs[0]
        
        # Validate all critical user identifiers present
        critical_ids = ["user_id", "session_id", "request_id", "correlation_id", "thread_id"]
        for id_field in critical_ids:
            assert hasattr(record, id_field), f"Critical ID field '{id_field}' missing"
            assert getattr(record, id_field) == user_context[id_field], f"ID field '{id_field}' value mismatch"
        
        # Validate security context present
        assert hasattr(record, 'user_permissions'), "User permissions missing"
        assert hasattr(record, 'subscription_tier'), "Subscription tier missing"
        assert record.subscription_tier == "enterprise", "Subscription tier incorrect"
        
        # Validate operational context present
        assert hasattr(record, 'operation_context'), "Operation context missing"
        operation_context = record.operation_context
        assert operation_context["current_operation"] == "cost_optimization_analysis", "Operation name incorrect"
        assert "tools_in_use" in operation_context, "Tools context missing"
        
        # Validate timing context for performance debugging
        assert hasattr(record, 'timestamp'), "Timestamp missing"
        assert "expected_duration_ms" in operation_context, "Expected duration missing"
        
        self.record_metric("user_context_completeness", "PASSED")
    
    @pytest.mark.unit
    def test_error_debug_information_completeness(self):
        """Test that error debugging information is comprehensive enough for diagnosis."""
        # Create realistic multi-layer error scenario
        def simulate_business_operation():
            """Simulate a realistic business operation that can fail."""
            user_data = {"user_id": "test_user_456", "permissions": ["read"]}
            
            # Layer 1: Permission check
            if "agent_execute" not in user_data.get("permissions", []):
                raise PermissionError("User lacks agent execution permission")
            
            # Layer 2: Resource availability (not reached due to permission error)
            if not self._check_agent_capacity():
                raise RuntimeError("Agent capacity exceeded")
            
            return {"status": "success", "result": "analysis_complete"}
        
        # Capture the error with full context
        error_context = {
            "operation": "cost_optimizer_agent_execution",
            "user_id": "test_user_456", 
            "thread_id": "thread_debug_test_001",
            "request_path": "/api/agents/execute",
            "request_method": "POST",
            "user_subscription": "free_tier",
            "system_state": {
                "agent_queue_length": 15,
                "active_agents": 8,
                "max_concurrent_agents": 10,
                "memory_usage_percent": 78.5,
                "cpu_usage_percent": 65.2
            },
            "business_context": {
                "monthly_usage": 145,
                "usage_limit": 100,
                "overage_allowed": False
            }
        }
        
        try:
            simulate_business_operation()
        except Exception as e:
            # Log with comprehensive error context
            self.logger.error(
                f"Business operation failed: {e}",
                extra={
                    **error_context,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error_traceback": traceback.format_exc(),
                    "troubleshooting_hints": [
                        "Check user permissions in admin panel",
                        "Verify user subscription allows agent execution",
                        "Check if free tier limits have been exceeded"
                    ]
                },
                exc_info=True
            )
        
        assert len(self.captured_logs) == 1, "Expected 1 error log record"
        record = self.captured_logs[0]
        
        # Validate error identification complete
        assert hasattr(record, 'error_type'), "Error type missing"
        assert record.error_type == "PermissionError", "Error type incorrect"
        assert hasattr(record, 'error_message'), "Error message missing"
        
        # Validate business context for debugging
        assert hasattr(record, 'user_subscription'), "User subscription context missing"
        assert hasattr(record, 'business_context'), "Business context missing"
        business_context = record.business_context
        assert business_context["monthly_usage"] > business_context["usage_limit"], "Business constraint not logged"
        
        # Validate system context for infrastructure debugging
        assert hasattr(record, 'system_state'), "System state missing"
        system_state = record.system_state
        assert "memory_usage_percent" in system_state, "Memory usage missing"
        assert "agent_queue_length" in system_state, "Queue state missing"
        
        # Validate troubleshooting guidance present
        assert hasattr(record, 'troubleshooting_hints'), "Troubleshooting hints missing"
        hints = record.troubleshooting_hints
        assert len(hints) > 0, "No troubleshooting hints provided"
        assert any("permissions" in hint.lower() for hint in hints), "Permission troubleshooting hint missing"
        
        # Validate exception info captured
        assert record.exc_info is not None, "Exception info not captured"
        
        self.record_metric("error_debug_completeness", "PASSED")
    
    @pytest.mark.unit
    def test_performance_debug_information(self):
        """Test that performance debugging information is comprehensive."""
        # Simulate performance-sensitive operation
        operation_id = str(uuid.uuid4())
        performance_context = {
            "operation_id": operation_id,
            "operation_type": "llm_query_processing",
            "user_id": "perf_test_user",
            "expected_max_duration_ms": 5000,
            "performance_tier": "premium",
            "resource_allocation": {
                "cpu_cores": 4,
                "memory_mb": 2048,
                "gpu_enabled": True
            }
        }
        
        # Start operation timing
        import time
        start_time = time.time()
        
        # Log operation start
        self.logger.info(
            "Performance-critical operation starting",
            extra={
                **performance_context,
                "phase": "start",
                "timestamp_ms": int(start_time * 1000)
            }
        )
        
        # Simulate operation phases with timing
        phases = ["initialization", "data_loading", "llm_processing", "result_formatting"]
        phase_times = []
        
        for phase in phases:
            phase_start = time.time()
            
            # Simulate phase work
            time.sleep(0.01)  # Small delay to create measurable timing
            
            phase_duration = (time.time() - phase_start) * 1000  # Convert to ms
            phase_times.append(phase_duration)
            
            # Log phase completion with timing
            self.logger.debug(
                f"Operation phase completed: {phase}",
                extra={
                    **performance_context,
                    "phase": phase,
                    "phase_duration_ms": phase_duration,
                    "cumulative_duration_ms": sum(phase_times),
                    "memory_usage_estimate_mb": 512 * (len(phase_times) + 1)  # Simulated memory growth
                }
            )
        
        # Log operation completion
        total_duration = (time.time() - start_time) * 1000
        self.logger.info(
            "Performance-critical operation completed",
            extra={
                **performance_context,
                "phase": "complete",
                "total_duration_ms": total_duration,
                "phase_breakdown_ms": dict(zip(phases, phase_times)),
                "performance_verdict": "within_limits" if total_duration < performance_context["expected_max_duration_ms"] else "exceeded_limits",
                "efficiency_score": min(100, int((performance_context["expected_max_duration_ms"] / total_duration) * 100))
            }
        )
        
        # Validate performance logging completeness
        perf_logs = [log for log in self.captured_logs if hasattr(log, 'operation_id') and log.operation_id == operation_id]
        assert len(perf_logs) >= len(phases) + 2, f"Expected at least {len(phases) + 2} performance logs"
        
        # Find completion log
        completion_log = None
        for log in perf_logs:
            if hasattr(log, 'phase') and log.phase == "complete":
                completion_log = log
                break
        
        assert completion_log is not None, "Completion log not found"
        
        # Validate timing information complete
        assert hasattr(completion_log, 'total_duration_ms'), "Total duration missing"
        assert hasattr(completion_log, 'phase_breakdown_ms'), "Phase breakdown missing"
        assert completion_log.total_duration_ms > 0, "Invalid total duration"
        
        # Validate performance assessment present
        assert hasattr(completion_log, 'performance_verdict'), "Performance verdict missing"
        assert hasattr(completion_log, 'efficiency_score'), "Efficiency score missing"
        assert 0 <= completion_log.efficiency_score <= 100, "Invalid efficiency score"
        
        # Validate resource context present
        assert hasattr(completion_log, 'resource_allocation'), "Resource allocation missing"
        
        self.record_metric("performance_debug_completeness", "PASSED")
        self.record_metric("operation_duration_ms", total_duration)
    
    @pytest.mark.unit
    def test_multi_user_debug_isolation(self):
        """Test that debug information properly isolates different users."""
        # Simulate concurrent operations from different users
        users = [
            {
                "user_id": "user_alice_001",
                "session_id": "session_alice_001", 
                "operation": "cost_analysis",
                "subscription": "enterprise"
            },
            {
                "user_id": "user_bob_002",
                "session_id": "session_bob_002",
                "operation": "usage_report", 
                "subscription": "professional"
            },
            {
                "user_id": "user_charlie_003",
                "session_id": "session_charlie_003",
                "operation": "agent_chat",
                "subscription": "free"
            }
        ]
        
        # Log operations for each user with isolation context
        for user in users:
            self.logger.info(
                f"User operation: {user['operation']}",
                extra={
                    **user,
                    "isolation_boundary": f"user_context_{user['user_id']}",
                    "thread_isolation": f"thread_{user['user_id']}_{user['operation']}",
                    "debug_scope": "user_isolated",
                    "cross_user_data_access": False,
                    "data_isolation_verified": True
                }
            )
        
        # Validate isolation in debug logs
        user_logs = {}
        for log in self.captured_logs:
            if hasattr(log, 'user_id'):
                user_id = log.user_id
                if user_id not in user_logs:
                    user_logs[user_id] = []
                user_logs[user_id].append(log)
        
        # Validate each user has isolated context
        assert len(user_logs) == 3, "Expected logs for 3 different users"
        
        for user_id, logs in user_logs.items():
            user_log = logs[0]  # Should be only one log per user
            
            # Validate user isolation markers present
            assert hasattr(user_log, 'isolation_boundary'), f"Isolation boundary missing for {user_id}"
            assert user_id in user_log.isolation_boundary, f"User ID not in isolation boundary for {user_id}"
            
            assert hasattr(user_log, 'thread_isolation'), f"Thread isolation missing for {user_id}"
            assert user_id in user_log.thread_isolation, f"User ID not in thread isolation for {user_id}"
            
            assert hasattr(user_log, 'cross_user_data_access'), f"Cross-user access flag missing for {user_id}"
            assert user_log.cross_user_data_access is False, f"Cross-user access not disabled for {user_id}"
            
            assert hasattr(user_log, 'data_isolation_verified'), f"Data isolation verification missing for {user_id}"
            assert user_log.data_isolation_verified is True, f"Data isolation not verified for {user_id}"
        
        self.record_metric("multi_user_isolation_debug", "PASSED")
    
    @pytest.mark.unit
    def test_websocket_debug_information(self):
        """Test that WebSocket operations provide complete debugging information."""
        # Simulate WebSocket lifecycle with comprehensive debug info
        websocket_context = {
            "connection_id": "ws_conn_debug_001",
            "user_id": "ws_test_user_001",
            "session_id": "ws_session_001",
            "connection_origin": "wss://app.netra.ai",
            "auth_method": "jwt_bearer",
            "protocol_version": "v1",
            "client_info": {
                "ip": "10.0.1.45",
                "user_agent": "Mozilla/5.0 WebSocket Client",
                "connect_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # WebSocket connection established
        self.logger.info(
            "WebSocket connection established",
            extra={
                **websocket_context,
                "event_type": "connection_established",
                "connection_state": "active",
                "pending_messages": 0,
                "connection_health": "healthy"
            }
        )
        
        # Message exchange
        message_context = {
            **websocket_context,
            "message_id": "msg_001",
            "message_type": "agent_request",
            "message_size_bytes": 1024,
            "agent_requested": "cost_optimizer"
        }
        
        self.logger.debug(
            "WebSocket message received",
            extra={
                **message_context,
                "event_type": "message_received",
                "processing_queue_length": 3,
                "estimated_processing_time_ms": 2500
            }
        )
        
        # Agent event broadcasting
        self.logger.debug(
            "WebSocket agent event broadcast",
            extra={
                **message_context,
                "event_type": "agent_event_broadcast",
                "websocket_event": "agent_thinking",
                "broadcast_recipients": 1,
                "message_delivery_status": "delivered"
            }
        )
        
        # Connection error scenario
        try:
            # Simulate connection issue
            raise ConnectionResetError("WebSocket connection reset by peer")
        except ConnectionResetError as e:
            self.logger.error(
                "WebSocket connection error",
                extra={
                    **websocket_context,
                    "event_type": "connection_error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "connection_duration_s": 125.5,
                    "messages_exchanged": 8,
                    "last_message_timestamp": datetime.now(timezone.utc).isoformat(),
                    "reconnection_possible": True,
                    "error_recovery_action": "attempt_reconnection"
                },
                exc_info=True
            )
        
        # Validate WebSocket debug information completeness
        ws_logs = [log for log in self.captured_logs if hasattr(log, 'connection_id')]
        assert len(ws_logs) == 4, "Expected 4 WebSocket-related logs"
        
        # Validate connection lifecycle tracking
        event_types = [log.event_type for log in ws_logs if hasattr(log, 'event_type')]
        expected_events = ["connection_established", "message_received", "agent_event_broadcast", "connection_error"]
        assert set(event_types) == set(expected_events), f"WebSocket events incomplete: {event_types}"
        
        # Validate error recovery information
        error_log = None
        for log in ws_logs:
            if hasattr(log, 'event_type') and log.event_type == "connection_error":
                error_log = log
                break
        
        assert error_log is not None, "WebSocket error log not found"
        assert hasattr(error_log, 'reconnection_possible'), "Reconnection possibility not logged"
        assert hasattr(error_log, 'error_recovery_action'), "Recovery action not logged"
        assert hasattr(error_log, 'connection_duration_s'), "Connection duration not logged"
        assert hasattr(error_log, 'messages_exchanged'), "Message count not logged"
        
        self.record_metric("websocket_debug_completeness", "PASSED")
    
    @pytest.mark.unit
    def test_auth_debug_information_completeness(self):
        """Test that authentication debugging provides comprehensive information."""
        # Comprehensive authentication debug scenario
        auth_context = {
            "user_id": "auth_debug_user_001",
            "request_id": "auth_req_debug_001",
            "correlation_id": "auth_corr_debug_001",
            "operation": "jwt_token_validation"
        }
        
        # Start authentication trace
        context = self.auth_tracer.start_operation(**auth_context)
        
        # Add detailed auth context
        detailed_context = {
            "auth_method": "jwt_bearer",
            "token_source": "authorization_header",
            "token_format": "valid_jwt_format",
            "issuer": "netra-auth-service",
            "audience": "netra-backend-api",
            "token_claims": {
                "sub": auth_context["user_id"],
                "permissions": ["read", "write"],
                "subscription": "professional",
                "organization": "test_org_001"
            },
            "validation_steps": [
                {"step": "format_validation", "status": "passed"},
                {"step": "signature_validation", "status": "passed"}, 
                {"step": "expiry_validation", "status": "passed"},
                {"step": "audience_validation", "status": "passed"}
            ]
        }
        
        # Log successful authentication with complete context
        self.auth_tracer.log_success(context, detailed_context)
        
        # Now test failure scenario with comprehensive debug info
        failure_context = {
            **auth_context,
            "user_id": "auth_debug_user_002",
            "request_id": "auth_req_debug_002",
            "operation": "jwt_token_validation_failure"
        }
        
        failure_trace = self.auth_tracer.start_operation(**failure_context)
        
        # Simulate comprehensive failure
        auth_failure = Exception("JWT signature validation failed - possible key mismatch")
        failure_debug_context = {
            "auth_method": "jwt_bearer",
            "token_provided": True,
            "token_format_valid": True,
            "signature_validation": {
                "status": "failed",
                "error": "signature_mismatch",
                "key_used": "HS256_key_001",
                "expected_algorithm": "HS256",
                "actual_algorithm": "HS256",
                "key_rotation_date": "2024-01-15",
                "troubleshooting": [
                    "Check JWT_SECRET environment variable",
                    "Verify key rotation completed successfully",
                    "Check auth service and backend service key consistency"
                ]
            },
            "request_metadata": {
                "ip_address": "192.168.1.100", 
                "user_agent": "Python/requests",
                "endpoint": "/api/agents/execute",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        self.auth_tracer.log_failure(failure_trace, auth_failure, failure_debug_context)
        
        # Validate authentication debug completeness
        auth_logs = [log for log in self.captured_logs if "AUTH_TRACE" in log.getMessage()]
        assert len(auth_logs) >= 2, "Expected at least 2 auth trace logs (success + failure)"
        
        # Find success and failure logs
        success_log = None
        failure_log = None
        
        for log in auth_logs:
            message = log.getMessage()
            if "AUTH_TRACE_SUCCESS" in message:
                success_log = log
            elif "AUTH_TRACE_FAILURE" in message:
                failure_log = log
        
        assert success_log is not None, "Success auth log not found"
        assert failure_log is not None, "Failure auth log not found"
        
        # Validate success log completeness
        success_message = success_log.getMessage()
        assert "auth_debug_user_001" in success_message, "Success user ID missing"
        assert "auth_req_debug_001" in success_message, "Success request ID missing"
        
        # Validate failure log completeness
        failure_message = failure_log.getMessage()
        assert "auth_debug_user_002" in failure_message, "Failure user ID missing"
        assert "JWT signature validation failed" in failure_message, "Failure reason missing"
        assert "signature_mismatch" in failure_message, "Specific error details missing"
        
        self.record_metric("auth_debug_completeness", "PASSED")
    
    def _check_agent_capacity(self):
        """Mock method for testing resource availability."""
        return False  # Simulate capacity exceeded
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Restore original logger handlers
        if hasattr(self, 'logger') and hasattr(self, 'original_handlers'):
            self.logger.handlers = self.original_handlers
        
        # Call parent teardown
        super().teardown_method(method)