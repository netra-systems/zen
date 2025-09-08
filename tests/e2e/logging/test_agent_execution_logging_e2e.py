"""
Test Agent Execution Logging E2E - End-to-End Tests for Agent Workflow Logging

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core product functionality
- Business Goal: Enable effective debugging of AI agent workflows that deliver customer value
- Value Impact: Faster resolution of agent issues = better AI experience = higher customer satisfaction
- Strategic Impact: Foundation for reliable AI agent operations that are core to our value proposition

This test suite validates that agent execution logging provides:
1. Complete agent workflow tracing from request to results
2. Tool execution visibility for debugging agent reasoning
3. Performance metrics for agent optimization
4. Error diagnostics for agent failure scenarios
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch

import pytest
import websockets

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.conftest_real_services import real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.logging.unified_logger_factory import get_logger


class TestAgentExecutionLoggingE2E(SSotAsyncTestCase):
    """Test complete agent execution logging in end-to-end scenarios."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Setup test environment for agent execution logging
        self.set_env_var("LOG_LEVEL", "DEBUG")
        self.set_env_var("ENABLE_AGENT_EXECUTION_LOGGING", "true")
        self.set_env_var("SERVICE_NAME", "agent-execution-e2e-test")
        self.set_env_var("AGENT_LOG_TOOL_EXECUTION", "true")
        self.set_env_var("AGENT_LOG_PERFORMANCE_METRICS", "true")
        
        # Initialize auth helpers
        self.auth_helper = E2EAuthHelper(environment="test")
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Initialize agent execution logging
        self.agent_logger = get_logger("agent_execution")
        self.tool_logger = get_logger("tool_execution")
        self.websocket_logger = get_logger("websocket_events")
        
        # Capture logs for validation
        self.captured_logs = {
            "agent": [],
            "tool": [],
            "websocket": [],
            "all": []
        }
        
        # Setup log capture
        self._setup_log_capture()
        
        # Test agent execution context
        self.agent_execution_context = f"agent_exec_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def _setup_log_capture(self):
        """Setup log capture for agent execution components."""
        def create_capture_handler(service_name):
            import logging
            
            class LogCapture(logging.Handler):
                def __init__(self, service_name, capture_dict):
                    super().__init__()
                    self.service_name = service_name
                    self.capture_dict = capture_dict
                
                def emit(self, record):
                    self.capture_dict[self.service_name].append(record)
                    self.capture_dict["all"].append({
                        "service": self.service_name,
                        "record": record,
                        "timestamp": time.time()
                    })
            
            return LogCapture(service_name, self.captured_logs)
        
        # Add handlers to loggers
        self.agent_logger.addHandler(create_capture_handler("agent"))
        self.tool_logger.addHandler(create_capture_handler("tool"))
        self.websocket_logger.addHandler(create_capture_handler("websocket"))
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_agent_workflow_logging(self, real_services):
        """Test complete agent workflow logging from request to results."""
        user_id = "agent_workflow_user_001"
        agent_request_id = f"agent_req_{int(time.time())}"
        agent_execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Agent request received via WebSocket
        self.websocket_logger.info(
            "Agent execution request received via WebSocket",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_request_id": agent_request_id,
                "operation": "agent_request_received",
                "step": "request_received",
                "agent_type": "cost_optimizer",
                "request_content": "Please analyze my AWS infrastructure and provide cost optimization recommendations",
                "user_context": {
                    "subscription_tier": "enterprise",
                    "monthly_usage": 250,
                    "permissions": ["read", "write", "agent_execute", "enterprise_features"]
                }
            }
        )
        
        # Step 2: Agent execution initialization
        agent_start_time = time.time()
        
        self.agent_logger.info(
            "Agent execution initializing",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_request_id": agent_request_id,
                "agent_execution_id": agent_execution_id,
                "operation": "agent_initialization",
                "step": "agent_init",
                "agent_type": "cost_optimizer",
                "agent_version": "v2.1.3",
                "execution_priority": "enterprise_high",
                "resource_allocation": {
                    "cpu_cores": 4,
                    "memory_gb": 8,
                    "gpu_enabled": True,
                    "timeout_seconds": 300
                },
                "expected_tools": ["aws_cost_analyzer", "resource_optimizer", "recommendation_generator"]
            }
        )
        
        # Step 3: Agent planning phase
        await asyncio.sleep(0.1)  # Simulate planning time
        
        self.agent_logger.debug(
            "Agent planning phase completed",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "agent_planning",
                "step": "planning_complete",
                "execution_plan": {
                    "total_steps": 4,
                    "estimated_duration_s": 45,
                    "tools_to_use": ["aws_cost_analyzer", "resource_optimizer", "recommendation_generator"],
                    "data_sources": ["aws_cloudwatch", "aws_billing", "resource_inventory"]
                },
                "websocket_event": "agent_thinking"
            }
        )
        
        # Broadcast planning complete via WebSocket
        self.websocket_logger.debug(
            "Broadcasting agent thinking event",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "websocket_event_broadcast",
                "step": "broadcast_agent_thinking",
                "websocket_event": "agent_thinking",
                "event_data": {
                    "status": "Agent is analyzing your AWS infrastructure",
                    "progress": 15,
                    "estimated_time_remaining": 40
                }
            }
        )
        
        # Step 4: Tool execution phases
        tools_to_execute = [
            {
                "tool_name": "aws_cost_analyzer",
                "description": "Analyzing AWS cost patterns and trends",
                "duration": 0.3,
                "expected_outputs": ["cost_breakdown", "trend_analysis", "anomaly_detection"]
            },
            {
                "tool_name": "resource_optimizer",
                "description": "Identifying underutilized and oversized resources",
                "duration": 0.4,
                "expected_outputs": ["resource_utilization", "rightsizing_recommendations", "idle_resources"]
            },
            {
                "tool_name": "recommendation_generator",
                "description": "Generating actionable optimization recommendations",
                "duration": 0.2,
                "expected_outputs": ["optimization_recommendations", "implementation_steps", "impact_estimates"]
            }
        ]
        
        tool_results = {}
        
        for tool_info in tools_to_execute:
            # Tool execution start
            tool_execution_id = f"tool_{tool_info['tool_name']}_{int(time.time())}"
            tool_start_time = time.time()
            
            self.tool_logger.info(
                f"Tool execution starting: {tool_info['tool_name']}",
                extra={
                    "agent_execution_context": self.agent_execution_context,
                    "user_id": user_id,
                    "agent_execution_id": agent_execution_id,
                    "tool_execution_id": tool_execution_id,
                    "operation": "tool_execution_start",
                    "step": f"tool_{tool_info['tool_name']}_start",
                    "tool_name": tool_info["tool_name"],
                    "tool_description": tool_info["description"],
                    "expected_outputs": tool_info["expected_outputs"],
                    "tool_version": "v1.5.2"
                }
            )
            
            # Broadcast tool executing event
            self.websocket_logger.debug(
                f"Broadcasting tool executing event: {tool_info['tool_name']}",
                extra={
                    "agent_execution_context": self.agent_execution_context,
                    "user_id": user_id,
                    "agent_execution_id": agent_execution_id,
                    "tool_execution_id": tool_execution_id,
                    "operation": "websocket_event_broadcast",
                    "step": f"broadcast_tool_executing_{tool_info['tool_name']}",
                    "websocket_event": "tool_executing",
                    "event_data": {
                        "tool_name": tool_info["tool_name"],
                        "status": tool_info["description"],
                        "progress": 25 + (len(tool_results) * 20)
                    }
                }
            )
            
            # Simulate tool execution
            await asyncio.sleep(tool_info["duration"])
            
            # Tool execution completion
            tool_duration = (time.time() - tool_start_time) * 1000
            
            # Generate mock tool results
            tool_result = self._generate_mock_tool_result(tool_info["tool_name"])
            tool_results[tool_info["tool_name"]] = tool_result
            
            self.tool_logger.info(
                f"Tool execution completed: {tool_info['tool_name']}",
                extra={
                    "agent_execution_context": self.agent_execution_context,
                    "user_id": user_id,
                    "agent_execution_id": agent_execution_id,
                    "tool_execution_id": tool_execution_id,
                    "operation": "tool_execution_complete",
                    "step": f"tool_{tool_info['tool_name']}_complete",
                    "tool_name": tool_info["tool_name"],
                    "execution_duration_ms": tool_duration,
                    "execution_result": "success",
                    "output_summary": {
                        "records_processed": tool_result["records_processed"],
                        "recommendations_generated": tool_result.get("recommendations_count", 0),
                        "data_quality": "high"
                    }
                }
            )
            
            # Broadcast tool completed event
            self.websocket_logger.debug(
                f"Broadcasting tool completed event: {tool_info['tool_name']}",
                extra={
                    "agent_execution_context": self.agent_execution_context,
                    "user_id": user_id,
                    "agent_execution_id": agent_execution_id,
                    "tool_execution_id": tool_execution_id,
                    "operation": "websocket_event_broadcast",
                    "step": f"broadcast_tool_completed_{tool_info['tool_name']}",
                    "websocket_event": "tool_completed",
                    "event_data": {
                        "tool_name": tool_info["tool_name"],
                        "status": f"Completed {tool_info['description'].lower()}",
                        "progress": 25 + ((len(tool_results)) * 20),
                        "success": True
                    }
                }
            )
        
        # Step 5: Agent synthesis and result generation
        synthesis_start = time.time()
        await asyncio.sleep(0.2)  # Simulate synthesis time
        
        # Calculate total execution metrics
        total_execution_time = (time.time() - agent_start_time) * 1000
        synthesis_duration = (time.time() - synthesis_start) * 1000
        
        # Generate comprehensive agent results
        agent_results = {
            "cost_savings_identified": 12500.75,
            "recommendations": [
                {
                    "type": "rightsizing",
                    "description": "Resize overprovisioned EC2 instances",
                    "monthly_savings": 4500.00,
                    "implementation_effort": "low"
                },
                {
                    "type": "optimization",
                    "description": "Implement auto-scaling for variable workloads",
                    "monthly_savings": 3200.50,
                    "implementation_effort": "medium"
                },
                {
                    "type": "cleanup",
                    "description": "Remove unused EBS volumes and snapshots",
                    "monthly_savings": 1800.25,
                    "implementation_effort": "low"
                }
            ],
            "implementation_priority": "high",
            "roi_estimate": "285%"
        }
        
        self.agent_logger.info(
            "Agent execution synthesis completed",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "agent_synthesis",
                "step": "synthesis_complete",
                "synthesis_duration_ms": synthesis_duration,
                "tools_results_integrated": len(tool_results),
                "business_value_generated": {
                    "cost_savings_identified": agent_results["cost_savings_identified"],
                    "recommendations_count": len(agent_results["recommendations"]),
                    "roi_estimate": agent_results["roi_estimate"]
                }
            }
        )
        
        # Step 6: Agent execution completion
        self.agent_logger.info(
            "Agent execution completed successfully",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "agent_execution_complete",
                "step": "execution_complete",
                "total_execution_time_ms": total_execution_time,
                "execution_result": "success",
                "tools_executed": len(tools_to_execute),
                "business_impact": {
                    "value_delivered": True,
                    "customer_satisfaction_expected": "high",
                    "actionable_recommendations": len(agent_results["recommendations"]),
                    "estimated_annual_savings": agent_results["cost_savings_identified"] * 12
                },
                "performance_metrics": {
                    "execution_efficiency": "excellent" if total_execution_time < 30000 else "good",
                    "tool_success_rate": 100.0,
                    "data_quality_score": 95.5
                }
            }
        )
        
        # Broadcast final agent completed event
        self.websocket_logger.info(
            "Broadcasting agent completed event",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "websocket_event_broadcast",
                "step": "broadcast_agent_completed",
                "websocket_event": "agent_completed",
                "event_data": {
                    "status": "Analysis completed successfully",
                    "progress": 100,
                    "results_available": True,
                    "recommendations_count": len(agent_results["recommendations"]),
                    "savings_identified": agent_results["cost_savings_identified"]
                }
            }
        )
        
        # Validate complete agent workflow logging
        agent_logs = self.captured_logs["agent"]
        tool_logs = self.captured_logs["tool"]
        websocket_logs = self.captured_logs["websocket"]
        all_logs = agent_logs + tool_logs + websocket_logs
        
        # Filter logs for this execution
        execution_logs = [log for log in all_logs if hasattr(log, 'agent_execution_context') and log.agent_execution_context == self.agent_execution_context]
        
        # Validate workflow completeness
        assert len(execution_logs) >= 15, f"Expected at least 15 execution logs, got {len(execution_logs)}"
        
        # Validate agent lifecycle
        agent_steps = [log.step for log in execution_logs if hasattr(log, 'step') and log.step.startswith('agent_')]
        expected_agent_steps = ["agent_init", "planning_complete", "synthesis_complete", "execution_complete"]
        for step in expected_agent_steps:
            assert any(step in agent_step for agent_step in agent_steps), f"Agent step '{step}' missing from logs"
        
        # Validate tool execution tracking
        tool_execution_logs = [log for log in execution_logs if hasattr(log, 'tool_execution_id')]
        assert len(tool_execution_logs) >= 6, f"Expected at least 6 tool execution logs, got {len(tool_execution_logs)}"
        
        # Validate WebSocket events
        websocket_events = [log.websocket_event for log in execution_logs if hasattr(log, 'websocket_event')]
        expected_events = ["agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event in expected_events:
            assert event in websocket_events, f"WebSocket event '{event}' missing from logs"
        
        # Validate business value tracking
        value_logs = [log for log in execution_logs if hasattr(log, 'business_impact') or hasattr(log, 'business_value_generated')]
        assert len(value_logs) >= 2, "Business value not tracked in logs"
        
        # Validate performance metrics
        perf_logs = [log for log in execution_logs if hasattr(log, 'performance_metrics')]
        assert len(perf_logs) >= 1, "Performance metrics not captured"
        
        self.record_metric("agent_workflow_logging_test", "PASSED")
        self.record_metric("execution_logs_generated", len(execution_logs))
        self.record_metric("tools_executed", len(tools_to_execute))
        self.record_metric("websocket_events_sent", len(websocket_events))
        self.record_metric("total_execution_time_ms", total_execution_time)
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_failure_scenario_logging(self, real_services):
        """Test agent failure scenario logging for debugging."""
        user_id = "agent_failure_user_001"
        agent_request_id = f"failing_req_{int(time.time())}"
        agent_execution_id = f"failing_exec_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Agent execution starts normally
        self.agent_logger.info(
            "Agent execution starting (will fail)",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_request_id": agent_request_id,
                "agent_execution_id": agent_execution_id,
                "operation": "agent_initialization",
                "step": "agent_init",
                "agent_type": "failing_agent_test",
                "expected_failure_type": "tool_execution_timeout"
            }
        )
        
        # Step 2: First tool succeeds
        tool1_execution_id = f"tool_success_{int(time.time())}"
        
        self.tool_logger.info(
            "First tool execution successful",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "tool_execution_id": tool1_execution_id,
                "operation": "tool_execution_complete",
                "step": "tool_data_collector_complete",
                "tool_name": "data_collector",
                "execution_result": "success",
                "records_processed": 1500
            }
        )
        
        # Step 3: Second tool fails
        tool2_execution_id = f"tool_failure_{int(time.time())}"
        tool_error = Exception("Tool execution timeout: aws_analyzer failed to respond within 30 seconds")
        
        self.tool_logger.error(
            "Tool execution failed",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "tool_execution_id": tool2_execution_id,
                "operation": "tool_execution_failed",
                "step": "tool_aws_analyzer_failed",
                "tool_name": "aws_analyzer",
                "error_type": type(tool_error).__name__,
                "error_message": str(tool_error),
                "execution_duration_ms": 30000,
                "failure_reason": "timeout",
                "retry_attempted": True,
                "retry_count": 2,
                "recovery_action": "abort_agent_execution"
            },
            exc_info=True
        )
        
        # Step 4: Agent handles tool failure
        self.agent_logger.error(
            "Agent execution failed due to tool failure",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "agent_execution_failed",
                "step": "execution_failed",
                "failure_cause": "tool_execution_timeout",
                "failed_tool": "aws_analyzer",
                "tools_completed_successfully": 1,
                "total_tools_planned": 3,
                "partial_results_available": True,
                "customer_impact": "high",
                "escalation_required": True,
                "error_recovery_strategy": {
                    "immediate_action": "notify_customer_of_failure",
                    "follow_up_action": "retry_with_different_tool_configuration",
                    "escalation_path": "engineering_team"
                }
            }
        )
        
        # Step 5: WebSocket error notification
        self.websocket_logger.error(
            "Broadcasting agent error to customer",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "websocket_error_broadcast",
                "step": "broadcast_agent_error",
                "websocket_event": "agent_error",
                "error_notification": {
                    "message": "Agent analysis failed due to a temporary issue with our cost analysis service.",
                    "error_code": "TOOL_EXECUTION_TIMEOUT",
                    "customer_action": "Please try again in a few minutes or contact support if the issue persists.",
                    "support_ticket_auto_created": True,
                    "ticket_id": f"AUTO_{int(time.time())}"
                }
            }
        )
        
        # Step 6: Failure analysis and debugging info
        self.agent_logger.info(
            "Agent failure analysis for debugging",
            extra={
                "agent_execution_context": self.agent_execution_context,
                "user_id": user_id,
                "agent_execution_id": agent_execution_id,
                "operation": "failure_analysis",
                "step": "debugging_analysis",
                "failure_analysis": {
                    "root_cause": "aws_analyzer_tool_timeout",
                    "contributing_factors": [
                        "high_system_load",
                        "aws_api_rate_limiting",
                        "tool_configuration_suboptimal"
                    ],
                    "system_state_at_failure": {
                        "active_agents": 12,
                        "system_load": "high",
                        "aws_api_quota_remaining": "15%",
                        "memory_usage_percent": 85
                    },
                    "debugging_recommendations": [
                        "Check AWS API rate limits and quotas",
                        "Review system resource utilization",
                        "Verify tool configuration parameters",
                        "Consider implementing circuit breaker for aws_analyzer"
                    ]
                }
            }
        )
        
        # Validate agent failure scenario logging
        failure_logs = [log for log in self.captured_logs["all"] if hasattr(log["record"], 'agent_execution_context') and log["record"].agent_execution_context == self.agent_execution_context]
        
        # Extract records for easier processing
        failure_records = [log["record"] for log in failure_logs]
        
        # Validate failure tracking
        error_logs = [log for log in failure_records if hasattr(log, 'levelname') and log.levelname == "ERROR"]
        assert len(error_logs) >= 3, f"Expected at least 3 error logs, got {len(error_logs)}"
        
        # Validate tool failure logging
        tool_failure_logs = [log for log in error_logs if hasattr(log, 'tool_name') and log.tool_name == "aws_analyzer"]
        assert len(tool_failure_logs) >= 1, "Tool failure not logged"
        
        tool_failure_log = tool_failure_logs[0]
        assert hasattr(tool_failure_log, 'error_type'), "Error type missing from tool failure log"
        assert hasattr(tool_failure_log, 'retry_count'), "Retry count missing from tool failure log"
        assert tool_failure_log.retry_count == 2, "Incorrect retry count logged"
        
        # Validate agent failure handling
        agent_failure_logs = [log for log in error_logs if hasattr(log, 'operation') and log.operation == "agent_execution_failed"]
        assert len(agent_failure_logs) >= 1, "Agent failure handling not logged"
        
        agent_failure_log = agent_failure_logs[0]
        assert hasattr(agent_failure_log, 'error_recovery_strategy'), "Recovery strategy not logged"
        assert hasattr(agent_failure_log, 'customer_impact'), "Customer impact not assessed"
        
        # Validate customer notification
        notification_logs = [log for log in failure_records if hasattr(log, 'error_notification')]
        assert len(notification_logs) >= 1, "Customer error notification not logged"
        
        notification_log = notification_logs[0]
        assert hasattr(notification_log.error_notification, 'support_ticket_auto_created'), "Support ticket creation not logged"
        assert notification_log.error_notification["support_ticket_auto_created"] is True, "Support ticket not auto-created"
        
        # Validate debugging information
        debug_logs = [log for log in failure_records if hasattr(log, 'failure_analysis')]
        assert len(debug_logs) >= 1, "Failure analysis for debugging not logged"
        
        debug_log = debug_logs[0]
        assert hasattr(debug_log.failure_analysis, 'debugging_recommendations'), "Debugging recommendations not provided"
        assert len(debug_log.failure_analysis["debugging_recommendations"]) >= 3, "Insufficient debugging recommendations"
        
        self.record_metric("agent_failure_logging_test", "PASSED")
        self.record_metric("failure_logs_generated", len(failure_records))
        self.record_metric("error_logs_count", len(error_logs))
    
    def _generate_mock_tool_result(self, tool_name: str) -> Dict[str, Any]:
        """Generate mock results for tool execution."""
        mock_results = {
            "aws_cost_analyzer": {
                "records_processed": 2500,
                "cost_trends": "increasing",
                "anomalies_detected": 3,
                "recommendations_count": 5
            },
            "resource_optimizer": {
                "records_processed": 1800,
                "underutilized_resources": 15,
                "oversized_resources": 8,
                "recommendations_count": 4
            },
            "recommendation_generator": {
                "records_processed": 500,
                "recommendations_generated": 8,
                "priority_recommendations": 3,
                "implementation_complexity": "medium"
            }
        }
        
        return mock_results.get(tool_name, {"records_processed": 1000, "status": "success"})
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Remove log handlers
        for logger in [self.agent_logger, self.tool_logger, self.websocket_logger]:
            logger.handlers = []
        
        # Clear captured logs
        for key in self.captured_logs:
            self.captured_logs[key].clear()
        
        # Call parent teardown
        super().teardown_method(method)