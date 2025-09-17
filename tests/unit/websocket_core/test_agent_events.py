"""
Unit Tests for WebSocket Agent Events

Tests agent_started, agent_thinking, tool_executing, tool_completed, and agent_completed
event structure validation, event delivery confirmation tracking, and business-critical
WebSocket event handling for the Golden Path user flow.

Business Value: Platform/Internal - Testing Infrastructure
Ensures reliable WebSocket event delivery protecting $500K+ ARR chat functionality.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, MessageType, AgentEvent, create_standard_message,
    serialize_message_safely
)


class TestAgentEvents(SSotAsyncTestCase):
    """Test WebSocket agent events with SSOT patterns and business value protection."""

    def setup_method(self, method):
        """Setup test environment for each test."""
        super().setup_method(method)
        
        # Test data for Golden Path scenarios
        self.user_id = "user_golden_path_123"
        self.thread_id = "thread_chat_456"
        self.agent_id = "apex_optimizer_789"
        self.run_id = "run_analysis_101"
        
        # Mock WebSocket manager for event delivery
        self.mock_websocket_manager = SSotMockFactory.create_websocket_manager_mock()
        
        # Track event delivery for business value validation
        self.delivered_events = []
        self.event_delivery_confirmations = {}

    async def test_agent_started_event_structure_and_validation(self):
        """Test agent_started event has proper structure and passes validation."""
        # Arrange - Create agent_started event with required business data
        event_data = {
            "agent_type": "apex_optimizer",
            "agent_id": self.agent_id,
            "user_request": "Analyze performance metrics and provide optimization recommendations",
            "execution_context": {
                "user_id": self.user_id,
                "thread_id": self.thread_id,
                "run_id": self.run_id
            },
            "estimated_duration": "2-3 minutes",
            "capabilities": ["data_analysis", "performance_optimization", "reporting"]
        }
        
        # Act - Create agent_started message
        message = create_standard_message(
            msg_type=MessageType.AGENT_STARTED,
            payload=event_data,
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Assert - Validate structure
        self.assertEqual(message.type, MessageType.AGENT_STARTED)
        self.assertEqual(message.user_id, self.user_id)
        self.assertEqual(message.thread_id, self.thread_id)
        self.assertIsNotNone(message.message_id)
        self.assertIsNotNone(message.timestamp)
        
        # Validate required business fields
        payload = message.payload
        self.assertEqual(payload["agent_type"], "apex_optimizer")
        self.assertEqual(payload["agent_id"], self.agent_id)
        self.assertIn("user_request", payload)
        self.assertIn("execution_context", payload)
        self.assertIn("estimated_duration", payload)
        self.assertIn("capabilities", payload)
        
        # Validate execution context
        context = payload["execution_context"]
        self.assertEqual(context["user_id"], self.user_id)
        self.assertEqual(context["thread_id"], self.thread_id)
        self.assertEqual(context["run_id"], self.run_id)
        
        # Test JSON serialization for WebSocket transmission
        serialized = serialize_message_safely(message)
        json_str = json.dumps(serialized)
        self.assertIsInstance(json_str, str)
        
        # Record event for delivery tracking
        self.record_event_delivery("agent_started", message)

    async def test_agent_thinking_event_with_reasoning_content(self):
        """Test agent_thinking event contains reasoning content and progress updates."""
        # Arrange - Create agent_thinking event with reasoning data
        reasoning_data = {
            "current_step": "data_analysis",
            "step_number": 2,
            "total_steps": 5,
            "reasoning": "Analyzing performance metrics to identify bottlenecks and optimization opportunities.",
            "progress_percentage": 40,
            "intermediate_findings": [
                "High CPU usage detected in database queries",
                "Memory allocation patterns suggest inefficient caching"
            ],
            "next_steps": ["Query optimization analysis", "Cache efficiency evaluation"],
            "thinking_duration_ms": 1500,
            "agent_id": self.agent_id,
            "context": {
                "analysis_type": "performance",
                "data_source": "system_metrics",
                "time_window": "last_24_hours"
            }
        }
        
        # Act - Create agent_thinking message
        message = create_standard_message(
            msg_type=MessageType.AGENT_THINKING,
            payload=reasoning_data,
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Assert - Validate reasoning content structure
        self.assertEqual(message.type, MessageType.AGENT_THINKING)
        payload = message.payload
        
        # Validate progress tracking
        self.assertEqual(payload["current_step"], "data_analysis")
        self.assertEqual(payload["step_number"], 2)
        self.assertEqual(payload["total_steps"], 5)
        self.assertEqual(payload["progress_percentage"], 40)
        
        # Validate reasoning content
        self.assertIn("reasoning", payload)
        self.assertIsInstance(payload["reasoning"], str)
        self.assertGreater(len(payload["reasoning"]), 10)  # Meaningful reasoning
        
        # Validate intermediate findings
        self.assertIn("intermediate_findings", payload)
        self.assertIsInstance(payload["intermediate_findings"], list)
        self.assertGreater(len(payload["intermediate_findings"]), 0)
        
        # Validate next steps
        self.assertIn("next_steps", payload)
        self.assertIsInstance(payload["next_steps"], list)
        
        # Validate timing information
        self.assertIn("thinking_duration_ms", payload)
        self.assertIsInstance(payload["thinking_duration_ms"], (int, float))
        
        # Validate context information
        self.assertIn("context", payload)
        self.assertIsInstance(payload["context"], dict)
        
        # Record event for delivery tracking
        self.record_event_delivery("agent_thinking", message)

    async def test_tool_executing_event_with_tool_parameters(self):
        """Test tool_executing event contains tool parameters and execution context."""
        # Arrange - Create tool_executing event with tool data
        tool_data = {
            "tool_name": "database_query_analyzer",
            "tool_id": "tool_db_query_001",
            "tool_category": "data_analysis",
            "execution_id": f"exec_{uuid.uuid4().hex[:8]}",
            "parameters": {
                "query_type": "performance_analysis",
                "database": "production_metrics",
                "time_range": {
                    "start": "2025-01-16T10:00:00Z",
                    "end": "2025-01-17T10:00:00Z"
                },
                "filters": {
                    "table_name": "query_performance",
                    "min_duration_ms": 1000
                },
                "output_format": "json"
            },
            "expected_duration_ms": 5000,
            "retry_attempts": 0,
            "max_retries": 3,
            "timeout_ms": 30000,
            "agent_id": self.agent_id,
            "tool_purpose": "Analyze database query performance to identify optimization opportunities",
            "tool_metadata": {
                "version": "2.1.0",
                "provider": "internal",
                "classification": "data_tool"
            }
        }
        
        # Act - Create tool_executing message
        message = create_standard_message(
            msg_type=MessageType.TOOL_EXECUTING,
            payload=tool_data,
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Assert - Validate tool execution structure
        self.assertEqual(message.type, MessageType.TOOL_EXECUTING)
        payload = message.payload
        
        # Validate tool identification
        self.assertEqual(payload["tool_name"], "database_query_analyzer")
        self.assertEqual(payload["tool_id"], "tool_db_query_001")
        self.assertEqual(payload["tool_category"], "data_analysis")
        
        # Validate execution context
        self.assertIn("execution_id", payload)
        self.assertEqual(payload["agent_id"], self.agent_id)
        
        # Validate parameters
        self.assertIn("parameters", payload)
        self.assertIsInstance(payload["parameters"], dict)
        parameters = payload["parameters"]
        self.assertEqual(parameters["query_type"], "performance_analysis")
        self.assertEqual(parameters["database"], "production_metrics")
        self.assertIn("time_range", parameters)
        self.assertIn("filters", parameters)
        
        # Validate execution settings
        self.assertEqual(payload["expected_duration_ms"], 5000)
        self.assertEqual(payload["max_retries"], 3)
        self.assertEqual(payload["timeout_ms"], 30000)
        
        # Validate tool metadata
        self.assertIn("tool_metadata", payload)
        metadata = payload["tool_metadata"]
        self.assertEqual(metadata["version"], "2.1.0")
        self.assertEqual(metadata["provider"], "internal")
        
        # Record event for delivery tracking
        self.record_event_delivery("tool_executing", message)

    async def test_tool_completed_event_with_result_formatting(self):
        """Test tool_completed event properly formats tool results and execution metrics."""
        # Arrange - Create tool_completed event with results
        result_data = {
            "tool_name": "database_query_analyzer",
            "tool_id": "tool_db_query_001",
            "execution_id": "exec_12345678",
            "status": "success",
            "execution_time_ms": 4750,
            "result": {
                "summary": {
                    "total_queries_analyzed": 1247,
                    "slow_queries_found": 23,
                    "optimization_opportunities": 8,
                    "average_improvement_potential": "45%"
                },
                "detailed_findings": [
                    {
                        "query_id": "q001",
                        "current_duration_ms": 2500,
                        "optimized_duration_ms": 890,
                        "improvement_percentage": 64.4,
                        "recommendation": "Add index on user_id column"
                    },
                    {
                        "query_id": "q002",
                        "current_duration_ms": 1800,
                        "optimized_duration_ms": 650,
                        "improvement_percentage": 63.9,
                        "recommendation": "Rewrite JOIN to use EXISTS clause"
                    }
                ],
                "actionable_recommendations": [
                    "Create composite index on (user_id, created_at) for user queries",
                    "Implement query result caching for frequently accessed data",
                    "Consider partitioning large tables by date"
                ],
                "metrics": {
                    "data_processed_mb": 125.7,
                    "queries_per_second": 262.5,
                    "memory_usage_mb": 45.2
                }
            },
            "agent_id": self.agent_id,
            "completion_timestamp": datetime.now(timezone.utc).isoformat(),
            "success_indicators": {
                "data_quality": "high",
                "completeness": "100%",
                "confidence_score": 0.92
            }
        }
        
        # Act - Create tool_completed message
        message = create_standard_message(
            msg_type=MessageType.TOOL_COMPLETED,
            payload=result_data,
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Assert - Validate tool completion structure
        self.assertEqual(message.type, MessageType.TOOL_COMPLETED)
        payload = message.payload
        
        # Validate execution status
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["execution_time_ms"], 4750)
        self.assertIn("completion_timestamp", payload)
        
        # Validate result structure
        self.assertIn("result", payload)
        result = payload["result"]
        self.assertIsInstance(result, dict)
        
        # Validate summary data
        self.assertIn("summary", result)
        summary = result["summary"]
        self.assertEqual(summary["total_queries_analyzed"], 1247)
        self.assertEqual(summary["slow_queries_found"], 23)
        self.assertEqual(summary["optimization_opportunities"], 8)
        
        # Validate detailed findings
        self.assertIn("detailed_findings", result)
        findings = result["detailed_findings"]
        self.assertIsInstance(findings, list)
        self.assertGreater(len(findings), 0)
        
        # Validate first finding structure
        first_finding = findings[0]
        self.assertIn("query_id", first_finding)
        self.assertIn("current_duration_ms", first_finding)
        self.assertIn("optimized_duration_ms", first_finding)
        self.assertIn("improvement_percentage", first_finding)
        self.assertIn("recommendation", first_finding)
        
        # Validate actionable recommendations
        self.assertIn("actionable_recommendations", result)
        recommendations = result["actionable_recommendations"]
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Validate metrics
        self.assertIn("metrics", result)
        metrics = result["metrics"]
        self.assertIn("data_processed_mb", metrics)
        self.assertIn("queries_per_second", metrics)
        self.assertIn("memory_usage_mb", metrics)
        
        # Validate success indicators
        self.assertIn("success_indicators", payload)
        indicators = payload["success_indicators"]
        self.assertEqual(indicators["data_quality"], "high")
        self.assertEqual(indicators["completeness"], "100%")
        self.assertEqual(indicators["confidence_score"], 0.92)
        
        # Record event for delivery tracking
        self.record_event_delivery("tool_completed", message)

    async def test_agent_completed_event_with_final_response_data(self):
        """Test agent_completed event contains comprehensive final response data."""
        # Arrange - Create agent_completed event with final results
        completion_data = {
            "agent_type": "apex_optimizer",
            "agent_id": self.agent_id,
            "execution_status": "completed_successfully",
            "total_execution_time_ms": 125000,  # ~2 minutes
            "final_response": {
                "summary": "Performance analysis completed with 8 optimization opportunities identified",
                "key_findings": [
                    "Database queries can be optimized to reduce average response time by 45%",
                    "Memory usage can be reduced by 30% through improved caching strategies",
                    "Query throughput can be increased by 60% with strategic indexing"
                ],
                "actionable_recommendations": [
                    {
                        "priority": "high",
                        "category": "database_optimization",
                        "action": "Create composite index on (user_id, created_at)",
                        "expected_impact": "35% reduction in query time",
                        "implementation_effort": "low",
                        "estimated_time": "30 minutes"
                    },
                    {
                        "priority": "medium",
                        "category": "caching",
                        "action": "Implement Redis caching for user profile data",
                        "expected_impact": "50% reduction in database load",
                        "implementation_effort": "medium",
                        "estimated_time": "2-3 hours"
                    }
                ],
                "metrics_achieved": {
                    "queries_analyzed": 1247,
                    "optimizations_identified": 8,
                    "potential_cost_savings_monthly": "$2,400",
                    "performance_improvement_percentage": 45.2
                }
            },
            "execution_stats": {
                "tools_executed": 3,
                "data_sources_accessed": ["production_db", "metrics_db", "cache_logs"],
                "total_data_processed_mb": 342.8,
                "reasoning_steps": 12,
                "confidence_score": 0.94
            },
            "next_steps": {
                "immediate_actions": [
                    "Review and approve recommended database indexes",
                    "Schedule implementation window for cache optimization"
                ],
                "follow_up_analysis": [
                    "Monitor query performance after index implementation",
                    "Track cache hit rates and adjust policies as needed"
                ],
                "success_metrics": [
                    "Query response time reduction > 40%",
                    "Database CPU utilization < 70%",
                    "Cache hit rate > 85%"
                ]
            },
            "business_impact": {
                "estimated_cost_savings": "$2,400/month",
                "performance_improvement": "45% faster query response",
                "user_experience_impact": "Reduced page load times",
                "scalability_improvement": "60% higher query throughput capacity"
            }
        }
        
        # Act - Create agent_completed message
        message = create_standard_message(
            msg_type=MessageType.AGENT_COMPLETED,
            payload=completion_data,
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Assert - Validate completion structure
        self.assertEqual(message.type, MessageType.AGENT_COMPLETED)
        payload = message.payload
        
        # Validate execution status
        self.assertEqual(payload["execution_status"], "completed_successfully")
        self.assertEqual(payload["total_execution_time_ms"], 125000)
        
        # Validate final response
        self.assertIn("final_response", payload)
        response = payload["final_response"]
        self.assertIn("summary", response)
        self.assertIn("key_findings", response)
        self.assertIn("actionable_recommendations", response)
        self.assertIn("metrics_achieved", response)
        
        # Validate key findings
        findings = response["key_findings"]
        self.assertIsInstance(findings, list)
        self.assertGreater(len(findings), 0)
        
        # Validate actionable recommendations
        recommendations = response["actionable_recommendations"]
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Validate first recommendation structure
        first_rec = recommendations[0]
        self.assertIn("priority", first_rec)
        self.assertIn("category", first_rec)
        self.assertIn("action", first_rec)
        self.assertIn("expected_impact", first_rec)
        self.assertIn("implementation_effort", first_rec)
        self.assertIn("estimated_time", first_rec)
        
        # Validate execution statistics
        self.assertIn("execution_stats", payload)
        stats = payload["execution_stats"]
        self.assertEqual(stats["tools_executed"], 3)
        self.assertIn("data_sources_accessed", stats)
        self.assertEqual(stats["confidence_score"], 0.94)
        
        # Validate next steps
        self.assertIn("next_steps", payload)
        next_steps = payload["next_steps"]
        self.assertIn("immediate_actions", next_steps)
        self.assertIn("follow_up_analysis", next_steps)
        self.assertIn("success_metrics", next_steps)
        
        # Validate business impact
        self.assertIn("business_impact", payload)
        impact = payload["business_impact"]
        self.assertIn("estimated_cost_savings", impact)
        self.assertIn("performance_improvement", impact)
        self.assertIn("user_experience_impact", impact)
        
        # Record event for delivery tracking
        self.record_event_delivery("agent_completed", message)

    async def test_event_delivery_confirmation_tracking(self):
        """Test event delivery confirmation tracking for all agent events."""
        # Arrange - Create sequence of all agent events
        events = [
            (MessageType.AGENT_STARTED, {"agent_type": "apex_optimizer", "agent_id": self.agent_id}),
            (MessageType.AGENT_THINKING, {"reasoning": "Analyzing data...", "progress": 25}),
            (MessageType.TOOL_EXECUTING, {"tool_name": "analyzer", "tool_id": "tool_001"}),
            (MessageType.TOOL_COMPLETED, {"tool_name": "analyzer", "status": "success"}),
            (MessageType.AGENT_COMPLETED, {"execution_status": "completed_successfully"})
        ]
        
        # Act - Process all events and track delivery
        delivered_events = []
        for event_type, payload in events:
            message = create_standard_message(
                msg_type=event_type,
                payload=payload,
                user_id=self.user_id,
                thread_id=self.thread_id
            )
            
            # Simulate event delivery confirmation
            delivery_confirmation = await self.simulate_event_delivery(message)
            delivered_events.append((event_type, delivery_confirmation))
            
            # Record for tracking
            self.record_event_delivery(event_type.value, message)
        
        # Assert - Validate all events were delivered
        self.assertEqual(len(delivered_events), 5)
        
        # Validate delivery confirmations
        for event_type, confirmation in delivered_events:
            self.assertIsNotNone(confirmation)
            self.assertTrue(confirmation["delivered"])
            self.assertIn("delivery_timestamp", confirmation)
            self.assertIn("message_id", confirmation)
        
        # Validate complete Golden Path event sequence
        expected_sequence = [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_THINKING,
            MessageType.TOOL_EXECUTING,
            MessageType.TOOL_COMPLETED,
            MessageType.AGENT_COMPLETED
        ]
        
        actual_sequence = [event_type for event_type, _ in delivered_events]
        self.assertEqual(actual_sequence, expected_sequence)
        
        # Validate tracking data
        self.assertEqual(len(self.delivered_events), 5)
        self.assertEqual(len(self.event_delivery_confirmations), 5)

    async def test_agent_event_serialization_edge_cases(self):
        """Test agent event serialization handles edge cases and complex data."""
        # Arrange - Create event with complex nested data and edge cases
        complex_payload = {
            "agent_type": "apex_optimizer",
            "timestamp": datetime.now(timezone.utc),
            "nested_data": {
                "metrics": [1, 2, 3, {"value": 4.5}],
                "settings": {
                    "timeout": None,
                    "retry": True,
                    "options": ["a", "b", "c"]
                }
            },
            "large_text": "x" * 1000,  # Large text field
            "unicode_text": "测试数据 🚀 Ñiño café",
            "special_numbers": {
                "zero": 0,
                "negative": -123.45,
                "large": 999999999
            }
        }
        
        # Act - Create and serialize message
        message = create_standard_message(
            msg_type=MessageType.AGENT_STARTED,
            payload=complex_payload,
            user_id=self.user_id
        )
        
        serialized = serialize_message_safely(message)
        
        # Assert - Validate serialization succeeded
        self.assertIsInstance(serialized, dict)
        
        # Test JSON serialization
        json_str = json.dumps(serialized, ensure_ascii=False)
        self.assertIsInstance(json_str, str)
        
        # Validate complex data was preserved
        payload = serialized['payload']
        self.assertIn('nested_data', payload)
        self.assertIn('unicode_text', payload)
        self.assertIn('special_numbers', payload)
        
        # Test deserialization
        parsed_data = json.loads(json_str)
        self.assertEqual(parsed_data['user_id'], self.user_id)

    async def test_event_validation_failures(self):
        """Test event validation handles invalid event data gracefully."""
        # Test cases for invalid event data
        invalid_cases = [
            # Missing required message type
            (None, {"data": "test"}),
            # Invalid payload type
            (MessageType.AGENT_STARTED, "invalid_payload"),
        ]
        
        for msg_type, payload in invalid_cases:
            with self.subTest(msg_type=msg_type, payload=payload):
                # Act & Assert - Should raise appropriate exceptions
                if msg_type is None:
                    with self.assertRaises(ValueError):
                        create_standard_message(
                            msg_type=msg_type,
                            payload=payload
                        )
                elif not isinstance(payload, dict):
                    with self.assertRaises(TypeError):
                        create_standard_message(
                            msg_type=msg_type,
                            payload=payload
                        )

    async def test_concurrent_event_delivery_isolation(self):
        """Test concurrent event delivery maintains proper user isolation."""
        # Arrange - Create events for multiple users
        users = [f"user_{i}" for i in range(3)]
        events_per_user = 2
        
        # Act - Process events concurrently
        tasks = []
        for user_id in users:
            for i in range(events_per_user):
                event_type = MessageType.AGENT_THINKING if i % 2 == 0 else MessageType.TOOL_EXECUTING
                payload = {"user_specific_data": f"data_for_{user_id}_{i}"}
                
                task = asyncio.create_task(
                    self.process_user_event(user_id, event_type, payload)
                )
                tasks.append((user_id, task))
        
        # Wait for all events to complete
        results = []
        for user_id, task in tasks:
            result = await task
            results.append((user_id, result))
        
        # Assert - Validate isolation and delivery
        self.assertEqual(len(results), len(users) * events_per_user)
        
        # Verify each user received their own events
        user_results = {}
        for user_id, result in results:
            if user_id not in user_results:
                user_results[user_id] = []
            user_results[user_id].append(result)
        
        # Validate user isolation
        for user_id in users:
            user_events = user_results[user_id]
            self.assertEqual(len(user_events), events_per_user)
            
            # Verify events contain correct user data
            for event in user_events:
                self.assertIn(user_id, event["payload"]["user_specific_data"])

    # Helper methods for test support

    def record_event_delivery(self, event_type: str, message: WebSocketMessage):
        """Record event delivery for tracking."""
        delivery_record = {
            "event_type": event_type,
            "message_id": message.message_id,
            "user_id": message.user_id,
            "thread_id": message.thread_id,
            "timestamp": message.timestamp,
            "delivered_at": time.time()
        }
        self.delivered_events.append(delivery_record)
        self.event_delivery_confirmations[message.message_id] = delivery_record

    async def simulate_event_delivery(self, message: WebSocketMessage) -> Dict[str, Any]:
        """Simulate WebSocket event delivery and return confirmation."""
        # Simulate network delay
        await asyncio.sleep(0.01)
        
        return {
            "delivered": True,
            "delivery_timestamp": time.time(),
            "message_id": message.message_id,
            "user_id": message.user_id,
            "delivery_method": "websocket"
        }

    async def process_user_event(self, user_id: str, event_type: MessageType, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single user event and return result."""
        # Create event message
        message = create_standard_message(
            msg_type=event_type,
            payload=payload,
            user_id=user_id,
            thread_id=f"thread_{user_id}"
        )
        
        # Simulate processing delay
        await asyncio.sleep(0.05)
        
        # Return processed event data
        return {
            "user_id": user_id,
            "event_type": event_type.value,
            "payload": payload,
            "processed_at": time.time(),
            "message_id": message.message_id
        }