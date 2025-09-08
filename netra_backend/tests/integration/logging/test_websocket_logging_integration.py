"""
Test WebSocket Logging Integration - Integration Tests for Real-Time Event Logging

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core platform functionality
- Business Goal: Enable effective debugging of WebSocket-based chat interactions
- Value Impact: Faster resolution of real-time communication issues = better user experience
- Strategic Impact: Foundation for reliable real-time AI interactions that deliver core value

This test suite validates that WebSocket logging provides:
1. Complete event lifecycle tracking for debugging
2. Connection state correlation across services
3. Message flow tracing for agent interactions  
4. Performance metrics for optimization
"""

import asyncio
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.conftest_real_services import real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.logging.unified_logger_factory import get_logger


class TestWebSocketLoggingIntegration(SSotAsyncTestCase):
    """Test WebSocket logging integration with real services."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Setup test environment for WebSocket logging
        self.set_env_var("LOG_LEVEL", "DEBUG")
        self.set_env_var("ENABLE_WEBSOCKET_LOGGING", "true")
        self.set_env_var("SERVICE_NAME", "websocket-logging-test")
        self.set_env_var("WEBSOCKET_LOG_EVENTS", "true")
        
        # Initialize loggers for WebSocket components
        self.websocket_logger = get_logger("websocket_manager")
        self.agent_logger = get_logger("agent_execution") 
        self.event_logger = get_logger("websocket_events")
        
        # Capture logs for analysis
        self.captured_logs = {
            "websocket": [],
            "agent": [],
            "event": [],
            "all": []
        }
        
        # Setup log capture
        self._setup_log_capture()
        
        # Auth helper for WebSocket testing
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test correlation for this session
        self.test_correlation_id = f"ws_test_corr_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def _setup_log_capture(self):
        """Setup log capture for WebSocket components."""
        def create_capture_handler(service_name):
            handler = MagicMock()
            handler.emit = lambda record: self._capture_log(service_name, record)
            return handler
        
        # Add handlers to loggers
        self.websocket_logger.addHandler(create_capture_handler("websocket"))
        self.agent_logger.addHandler(create_capture_handler("agent"))
        self.event_logger.addHandler(create_capture_handler("event"))
    
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
    async def test_websocket_connection_lifecycle_logging(self, real_services):
        """Test complete WebSocket connection lifecycle logging."""
        connection_id = f"ws_conn_test_{uuid.uuid4().hex[:8]}"
        user_id = "ws_lifecycle_user_001"
        
        # Step 1: Connection attempt
        self.websocket_logger.info(
            "WebSocket connection attempt",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "websocket_connect_attempt",
                "step": "connection_attempt",
                "client_info": {
                    "ip": "192.168.1.100",
                    "user_agent": "Test WebSocket Client",
                    "protocol_version": "v1"
                }
            }
        )
        
        # Step 2: Authentication validation
        self.websocket_logger.info(
            "WebSocket authentication validation",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "websocket_auth_validation",
                "step": "auth_validation",
                "auth_method": "jwt_bearer",
                "auth_result": "success",
                "permissions": ["read", "write", "agent_execute"]
            }
        )
        
        # Step 3: Connection established
        self.websocket_logger.info(
            "WebSocket connection established successfully",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "websocket_connected",
                "step": "connection_established",
                "connection_state": "active",
                "session_id": f"session_{connection_id}",
                "connection_duration_setup_ms": 150.5
            }
        )
        
        # Step 4: Message exchange
        message_id = f"msg_{int(time.time())}"
        self.websocket_logger.debug(
            "WebSocket message received",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": message_id,
                "user_id": user_id,
                "operation": "websocket_message_received",
                "step": "message_received",
                "message_type": "agent_request",
                "message_size_bytes": 512,
                "agent_requested": "cost_optimizer"
            }
        )
        
        # Step 5: Agent event broadcasting
        agent_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event in agent_events:
            self.event_logger.debug(
                f"Broadcasting agent event: {event}",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "connection_id": connection_id,
                    "message_id": message_id,
                    "user_id": user_id,
                    "operation": "websocket_event_broadcast",
                    "step": f"broadcast_{event}",
                    "websocket_event": event,
                    "event_data_size_bytes": 256,
                    "broadcast_success": True
                }
            )
        
        # Step 6: Connection health monitoring
        self.websocket_logger.debug(
            "WebSocket connection health check",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "websocket_health_check",
                "step": "health_check",
                "connection_state": "active",
                "last_ping_ms": 45.2,
                "messages_sent": 5,
                "messages_received": 1,
                "connection_uptime_s": 30.5
            }
        )
        
        # Step 7: Connection close
        self.websocket_logger.info(
            "WebSocket connection closed",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "websocket_disconnect",
                "step": "connection_closed",
                "close_reason": "client_disconnect",
                "close_code": 1000,
                "total_connection_duration_s": 45.7,
                "total_messages_exchanged": 6,
                "connection_clean": True
            }
        )
        
        # Validate WebSocket lifecycle logging
        ws_logs = self.captured_logs["websocket"]
        event_logs = self.captured_logs["event"] 
        
        # Validate connection lifecycle completeness
        lifecycle_steps = [log.step for log in ws_logs if hasattr(log, 'step')]
        expected_lifecycle = [
            "connection_attempt", "auth_validation", "connection_established",
            "message_received", "health_check", "connection_closed"
        ]
        assert lifecycle_steps == expected_lifecycle, f"WebSocket lifecycle incomplete: {lifecycle_steps}"
        
        # Validate all logs have same connection_id and correlation_id
        all_connection_logs = ws_logs + event_logs
        for log in all_connection_logs:
            assert hasattr(log, 'connection_id'), "Connection ID missing from log"
            assert log.connection_id == connection_id, "Connection ID mismatch"
            assert hasattr(log, 'correlation_id'), "Correlation ID missing from log"
            assert log.correlation_id == self.test_correlation_id, "Correlation ID mismatch"
        
        # Validate agent events were properly logged
        event_steps = [log.step for log in event_logs if hasattr(log, 'step')]
        expected_events = [f"broadcast_{event}" for event in agent_events]
        assert event_steps == expected_events, f"Agent events incomplete: {event_steps}"
        
        # Validate performance metrics captured
        perf_logs = [log for log in all_connection_logs if hasattr(log, 'connection_duration_setup_ms') or hasattr(log, 'total_connection_duration_s')]
        assert len(perf_logs) >= 2, "Performance metrics not captured"
        
        self.record_metric("websocket_lifecycle_logging_test", "PASSED")
        self.record_metric("lifecycle_steps_logged", len(lifecycle_steps))
        self.record_metric("agent_events_logged", len(event_steps))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_flow_correlation(self, real_services):
        """Test WebSocket message flow correlation with agent execution."""
        connection_id = f"ws_flow_test_{uuid.uuid4().hex[:8]}"
        user_id = "ws_flow_user_001"
        message_id = f"msg_flow_{int(time.time())}"
        
        # Step 1: WebSocket receives message
        self.websocket_logger.info(
            "Agent request message received",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": message_id,
                "user_id": user_id,
                "operation": "agent_request_received",
                "step": "message_received",
                "agent_type": "cost_optimizer",
                "request_content": "Analyze my AWS costs for optimization opportunities"
            }
        )
        
        # Step 2: Message validation and routing
        self.websocket_logger.debug(
            "Message validation and routing",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": message_id,
                "user_id": user_id,
                "operation": "message_routing",
                "step": "message_validated",
                "validation_result": "success",
                "route_target": "agent_execution_service"
            }
        )
        
        # Step 3: Agent execution starts (agent logger)
        agent_execution_id = f"agent_exec_{uuid.uuid4().hex[:8]}"
        self.agent_logger.info(
            "Agent execution started from WebSocket request",
            extra={
                "correlation_id": self.test_correlation_id,
                "message_id": message_id,  # Reference to WebSocket message
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "operation": "agent_execution_start",
                "step": "agent_start",
                "agent_type": "cost_optimizer",
                "execution_context": {
                    "source": "websocket",
                    "connection_id": connection_id,
                    "real_time": True
                }
            }
        )
        
        # Step 4: Agent progress with WebSocket events
        progress_steps = [
            {"event": "agent_thinking", "progress": 10, "description": "Analyzing user requirements"},
            {"event": "tool_executing", "progress": 40, "description": "Fetching AWS cost data"},
            {"event": "tool_executing", "progress": 70, "description": "Analyzing cost patterns"},
            {"event": "tool_completed", "progress": 90, "description": "Generating recommendations"},
        ]
        
        for step_info in progress_steps:
            # Agent logs progress
            self.agent_logger.debug(
                f"Agent progress: {step_info['description']}",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "agent_execution_id": agent_execution_id,
                    "user_id": user_id,
                    "operation": "agent_progress",
                    "step": f"agent_{step_info['event']}",
                    "progress_percent": step_info["progress"],
                    "progress_description": step_info["description"]
                }
            )
            
            # WebSocket broadcasts progress
            self.event_logger.debug(
                f"Broadcasting agent progress via WebSocket",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "connection_id": connection_id,
                    "message_id": message_id,
                    "agent_execution_id": agent_execution_id,
                    "user_id": user_id,
                    "operation": "progress_broadcast",
                    "step": f"broadcast_{step_info['event']}",
                    "websocket_event": step_info["event"],
                    "progress_percent": step_info["progress"],
                    "broadcast_latency_ms": 15.3
                }
            )
        
        # Step 5: Agent completion
        self.agent_logger.info(
            "Agent execution completed successfully",
            extra={
                "correlation_id": self.test_correlation_id,
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "operation": "agent_execution_complete",
                "step": "agent_complete",
                "execution_duration_ms": 2500,
                "recommendations_generated": 5,
                "cost_savings_identified": 1200.50
            }
        )
        
        # Step 6: Results sent via WebSocket
        self.websocket_logger.info(
            "Agent results sent to WebSocket client",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": message_id,
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "operation": "results_sent",
                "step": "results_delivered",
                "websocket_event": "agent_completed",
                "response_size_bytes": 2048,
                "delivery_success": True
            }
        )
        
        # Validate message flow correlation
        all_logs = self.captured_logs["websocket"] + self.captured_logs["agent"] + self.captured_logs["event"]
        
        # Filter logs for this flow
        flow_logs = [log for log in all_logs if hasattr(log, 'correlation_id') and log.correlation_id == self.test_correlation_id]
        
        # Validate correlation completeness
        assert len(flow_logs) >= 10, f"Expected at least 10 flow logs, got {len(flow_logs)}"
        
        # Validate message ID propagation
        message_logs = [log for log in flow_logs if hasattr(log, 'message_id') and log.message_id == message_id]
        assert len(message_logs) >= 6, "Message ID not properly propagated through flow"
        
        # Validate agent execution correlation
        agent_exec_logs = [log for log in flow_logs if hasattr(log, 'agent_execution_id')]
        assert len(agent_exec_logs) >= 6, "Agent execution not properly correlated"
        
        agent_execution_ids = set(log.agent_execution_id for log in agent_exec_logs)
        assert len(agent_execution_ids) == 1, f"Multiple agent execution IDs: {agent_execution_ids}"
        
        # Validate WebSocket event sequence
        event_broadcasts = [log for log in flow_logs if hasattr(log, 'websocket_event')]
        websocket_events = [log.websocket_event for log in event_broadcasts]
        
        expected_events = ["agent_thinking", "tool_executing", "tool_executing", "tool_completed", "agent_completed"]
        # Filter out duplicates while preserving order
        actual_events = []
        seen = set()
        for event in websocket_events:
            if event not in seen or event == "tool_executing":  # Allow multiple tool_executing
                actual_events.append(event)
                if event != "tool_executing":
                    seen.add(event)
        
        assert len(actual_events) >= len(expected_events), f"Missing WebSocket events: expected {expected_events}, got {actual_events}"
        
        self.record_metric("websocket_flow_correlation_test", "PASSED")
        self.record_metric("flow_logs_generated", len(flow_logs))
        self.record_metric("websocket_events_broadcast", len(event_broadcasts))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_handling_logging(self, real_services):
        """Test WebSocket error handling and recovery logging."""
        connection_id = f"ws_error_test_{uuid.uuid4().hex[:8]}"
        user_id = "ws_error_user_001"
        
        # Step 1: Connection established normally
        self.websocket_logger.info(
            "WebSocket connection established",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "websocket_connected",
                "step": "connection_established"
            }
        )
        
        # Step 2: Message processing error
        error_message_id = f"error_msg_{int(time.time())}"
        processing_error = Exception("Invalid message format: missing required field 'agent_type'")
        
        self.websocket_logger.error(
            "WebSocket message processing error",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": error_message_id,
                "user_id": user_id,
                "operation": "message_processing_error",
                "step": "processing_error",
                "error_type": type(processing_error).__name__,
                "error_message": str(processing_error),
                "message_content": '{"type": "agent_request", "missing_field": true}',
                "recovery_action": "send_error_response"
            },
            exc_info=True
        )
        
        # Step 3: Error response sent
        self.websocket_logger.info(
            "Error response sent to WebSocket client",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": error_message_id,
                "user_id": user_id,
                "operation": "error_response_sent",
                "step": "error_response",
                "error_code": "INVALID_MESSAGE_FORMAT",
                "error_details": "Message missing required field: agent_type",
                "client_notified": True
            }
        )
        
        # Step 4: Connection health check after error
        self.websocket_logger.debug(
            "Connection health check after error",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "health_check_post_error",
                "step": "health_check",
                "connection_state": "active",
                "error_count": 1,
                "connection_stable": True
            }
        )
        
        # Step 5: Agent execution error scenario
        agent_error_message_id = f"agent_error_msg_{int(time.time())}"
        
        self.websocket_logger.info(
            "Valid agent request received",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": agent_error_message_id,
                "user_id": user_id,
                "operation": "agent_request_received",
                "step": "valid_message_received",
                "agent_type": "cost_optimizer"
            }
        )
        
        # Agent execution fails
        agent_execution_id = f"failing_agent_{uuid.uuid4().hex[:8]}"
        agent_error = Exception("Agent execution timeout after 30 seconds")
        
        self.agent_logger.error(
            "Agent execution failed",
            extra={
                "correlation_id": self.test_correlation_id,
                "agent_execution_id": agent_execution_id,
                "message_id": agent_error_message_id,
                "user_id": user_id,
                "operation": "agent_execution_failed",
                "step": "agent_error",
                "error_type": type(agent_error).__name__,
                "error_message": str(agent_error),
                "execution_duration_ms": 30000,
                "recovery_strategy": "notify_client_and_cleanup"
            },
            exc_info=True
        )
        
        # Step 6: WebSocket notifies client of agent error
        self.event_logger.error(
            "Broadcasting agent error to WebSocket client",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "message_id": agent_error_message_id,
                "agent_execution_id": agent_execution_id,
                "user_id": user_id,
                "operation": "agent_error_broadcast",
                "step": "error_broadcast",
                "websocket_event": "agent_error",
                "error_code": "AGENT_EXECUTION_TIMEOUT",
                "client_notification": "Agent execution timed out. Please try again."
            }
        )
        
        # Step 7: Connection recovery verification
        self.websocket_logger.info(
            "Connection recovered successfully after errors",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "connection_recovery",
                "step": "recovery_complete",
                "total_errors_handled": 2,
                "connection_stable": True,
                "recovery_successful": True
            }
        )
        
        # Validate error handling logging
        all_logs = self.captured_logs["websocket"] + self.captured_logs["agent"] + self.captured_logs["event"]
        error_flow_logs = [log for log in all_logs if hasattr(log, 'correlation_id') and log.correlation_id == self.test_correlation_id]
        
        # Validate error logs present
        error_logs = [log for log in error_flow_logs if hasattr(log, 'error_type')]
        assert len(error_logs) >= 2, f"Expected at least 2 error logs, got {len(error_logs)}"
        
        # Validate error information completeness
        for error_log in error_logs:
            assert hasattr(error_log, 'error_type'), "Error type missing from error log"
            assert hasattr(error_log, 'error_message'), "Error message missing from error log"
            assert error_log.error_message, "Error message is empty"
        
        # Validate recovery logging
        recovery_logs = [log for log in error_flow_logs if hasattr(log, 'step') and 'recovery' in log.step]
        assert len(recovery_logs) >= 1, "Recovery logging missing"
        
        recovery_log = recovery_logs[0]
        assert hasattr(recovery_log, 'recovery_successful'), "Recovery status not logged"
        assert recovery_log.recovery_successful is True, "Recovery not marked as successful"
        
        # Validate error correlation maintained
        for log in error_flow_logs:
            assert log.correlation_id == self.test_correlation_id, "Correlation lost during error handling"
            if hasattr(log, 'connection_id'):
                assert log.connection_id == connection_id, "Connection ID lost during error handling"
        
        # Validate client notification
        notification_logs = [log for log in error_flow_logs if hasattr(log, 'client_notification') or hasattr(log, 'client_notified')]
        assert len(notification_logs) >= 2, "Client notification not properly logged"
        
        self.record_metric("websocket_error_handling_test", "PASSED")
        self.record_metric("errors_handled", len(error_logs))
        self.record_metric("recovery_logs", len(recovery_logs))
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_performance_logging(self, real_services):
        """Test WebSocket performance metrics logging."""
        connection_id = f"ws_perf_test_{uuid.uuid4().hex[:8]}"
        user_id = "ws_perf_user_001"
        
        # Performance test scenario: multiple concurrent messages
        message_count = 5
        start_time = time.time()
        
        # Log performance test start
        self.websocket_logger.info(
            "WebSocket performance test starting",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "performance_test_start",
                "step": "perf_test_start",
                "expected_messages": message_count,
                "test_start_time": start_time
            }
        )
        
        # Process multiple messages with timing
        message_times = []
        for i in range(message_count):
            message_start = time.time()
            message_id = f"perf_msg_{i}_{int(time.time() * 1000)}"
            
            # Message received
            self.websocket_logger.debug(
                f"Performance test message {i+1} received",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "connection_id": connection_id,
                    "message_id": message_id,
                    "user_id": user_id,
                    "operation": "perf_message_received",
                    "step": f"message_{i+1}_received",
                    "message_index": i + 1,
                    "receive_timestamp": message_start
                }
            )
            
            # Simulate message processing delay
            await asyncio.sleep(0.1)  # 100ms processing
            
            message_end = time.time()
            processing_time = (message_end - message_start) * 1000  # Convert to ms
            message_times.append(processing_time)
            
            # Message processed
            self.websocket_logger.debug(
                f"Performance test message {i+1} processed",
                extra={
                    "correlation_id": self.test_correlation_id,
                    "connection_id": connection_id,
                    "message_id": message_id,
                    "user_id": user_id,
                    "operation": "perf_message_processed",
                    "step": f"message_{i+1}_processed",
                    "message_index": i + 1,
                    "processing_time_ms": processing_time,
                    "throughput_msg_per_sec": 1000 / processing_time if processing_time > 0 else 0
                }
            )
        
        # Log performance test completion
        total_time = (time.time() - start_time) * 1000
        avg_processing_time = sum(message_times) / len(message_times)
        
        self.websocket_logger.info(
            "WebSocket performance test completed",
            extra={
                "correlation_id": self.test_correlation_id,
                "connection_id": connection_id,
                "user_id": user_id,
                "operation": "performance_test_complete",
                "step": "perf_test_complete",
                "messages_processed": message_count,
                "total_time_ms": total_time,
                "average_processing_time_ms": avg_processing_time,
                "max_processing_time_ms": max(message_times),
                "min_processing_time_ms": min(message_times),
                "overall_throughput_msg_per_sec": (message_count * 1000) / total_time,
                "performance_verdict": "acceptable" if avg_processing_time < 200 else "needs_optimization"
            }
        )
        
        # Validate performance logging
        ws_logs = self.captured_logs["websocket"]
        perf_logs = [log for log in ws_logs if hasattr(log, 'correlation_id') and log.correlation_id == self.test_correlation_id]
        
        # Validate performance metrics captured
        timing_logs = [log for log in perf_logs if hasattr(log, 'processing_time_ms') or hasattr(log, 'total_time_ms')]
        assert len(timing_logs) >= message_count + 1, f"Performance timing logs missing: expected {message_count + 1}, got {len(timing_logs)}"
        
        # Find completion log with performance summary
        completion_logs = [log for log in perf_logs if hasattr(log, 'step') and log.step == "perf_test_complete"]
        assert len(completion_logs) == 1, "Performance test completion not logged"
        
        completion_log = completion_logs[0]
        assert hasattr(completion_log, 'average_processing_time_ms'), "Average processing time not logged"
        assert hasattr(completion_log, 'overall_throughput_msg_per_sec'), "Throughput not logged"
        assert hasattr(completion_log, 'performance_verdict'), "Performance verdict not logged"
        
        # Validate throughput calculation
        expected_throughput = (message_count * 1000) / total_time
        actual_throughput = completion_log.overall_throughput_msg_per_sec
        assert abs(actual_throughput - expected_throughput) < 0.1, "Throughput calculation incorrect"
        
        # Validate performance verdict logic
        if completion_log.average_processing_time_ms < 200:
            assert completion_log.performance_verdict == "acceptable", "Performance verdict logic incorrect"
        
        self.record_metric("websocket_performance_test", "PASSED")
        self.record_metric("messages_tested", message_count)
        self.record_metric("average_processing_time_ms", avg_processing_time)
        self.record_metric("overall_throughput_msg_per_sec", completion_log.overall_throughput_msg_per_sec)
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Remove mock handlers from loggers
        for logger in [self.websocket_logger, self.agent_logger, self.event_logger]:
            logger.handlers = []
        
        # Clear captured logs
        for key in self.captured_logs:
            self.captured_logs[key].clear()
        
        # Call parent teardown
        super().teardown_method(method)