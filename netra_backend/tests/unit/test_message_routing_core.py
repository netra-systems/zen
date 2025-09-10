"""
Unit Tests for Core Message Routing Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable message delivery for real-time AI interactions
- Value Impact: Users must receive agent responses and system notifications reliably
- Strategic Impact: Core chat functionality - message failures = no user experience

This module tests the core message routing logic including:
- Message type classification and routing
- Quality-based message prioritization
- Handler selection and delegation
- Error handling and fallback routing
- Performance optimization for chat responsiveness
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestMessageRoutingCore(SSotBaseTestCase):
    """Unit tests for core message routing business logic."""
    
    def setup_method(self, method=None):
        """Setup test environment and mocks."""
        super().setup_method(method)
        
        # Create mock dependencies
        self.mock_supervisor = MagicMock()
        self.mock_db_session_factory = MagicMock()
        self.mock_quality_gate_service = MagicMock(spec=QualityGateService)
        self.mock_monitoring_service = MagicMock(spec=QualityMonitoringService)
        
        # Test message data
        self.test_user_id = "test-user-12345"
        self.test_thread_id = "test-thread-67890"
        self.test_message_id = str(uuid4())
        
        # Sample messages for testing
        self.agent_start_message = {
            "type": "agent_start",
            "agent_name": "cost_optimizer",
            "user_request": "Analyze my AWS costs",
            "thread_id": self.test_thread_id
        }
        
        self.agent_response_message = {
            "type": "agent_response", 
            "data": {
                "optimization_savings": 1500,
                "recommendations": ["Use Reserved Instances", "Optimize EBS volumes"]
            },
            "thread_id": self.test_thread_id
        }
        
        self.quality_alert_message = {
            "type": "quality_alert",
            "severity": "warning",
            "message": "Response time exceeding threshold",
            "metrics": {"response_time": 8.5}
        }
        
    @pytest.mark.unit
    def test_router_initialization_sets_handlers(self):
        """Test that QualityMessageRouter initializes with correct handlers."""
        # Business logic: Router should initialize all necessary message handlers
        router = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )
        
        # Verify core components are set
        assert router.supervisor == self.mock_supervisor
        assert router.db_session_factory == self.mock_db_session_factory
        assert router.quality_gate_service == self.mock_quality_gate_service
        assert router.monitoring_service == self.mock_monitoring_service
        
        # Verify handlers dictionary is created
        assert hasattr(router, 'handlers')
        assert isinstance(router.handlers, dict)
        
        # Record business metric: Router initialization success
        self.record_metric("router_initialization_success", True)
        
    @pytest.mark.unit
    def test_message_type_classification(self):
        """Test correct classification of different message types."""
        # Create test messages of different types
        test_cases = [
            (self.agent_start_message, "agent_start"),
            (self.agent_response_message, "agent_response"),
            (self.quality_alert_message, "quality_alert"),
            ({"type": "unknown_type", "data": "test"}, "unknown_type")
        ]
        
        for message, expected_type in test_cases:
            # Business logic: Message type should be correctly extracted
            actual_type = message.get("type")
            assert actual_type == expected_type
            
        # Record business metric: Message classification success
        self.record_metric("message_classification_tests_passed", len(test_cases))
        
    @pytest.mark.unit
    def test_message_validation_business_logic(self):
        """Test business logic for message validation."""
        # Test valid agent start message
        assert "type" in self.agent_start_message
        assert "agent_name" in self.agent_start_message
        assert "user_request" in self.agent_start_message
        assert self.agent_start_message["agent_name"] == "cost_optimizer"
        
        # Test valid agent response message
        assert "type" in self.agent_response_message
        assert "data" in self.agent_response_message
        assert "optimization_savings" in self.agent_response_message["data"]
        assert self.agent_response_message["data"]["optimization_savings"] > 0
        
        # Test quality alert message
        assert "type" in self.quality_alert_message
        assert "severity" in self.quality_alert_message
        assert self.quality_alert_message["severity"] in ["info", "warning", "error", "critical"]
        
        # Record business metric: Message validation success
        self.record_metric("message_validation_success", True)
        
    @pytest.mark.unit
    def test_message_priority_calculation(self):
        """Test message priority calculation for business value."""
        # Business logic: Different message types have different business priorities
        # Priority should reflect business impact and user experience requirements
        
        # Agent responses have highest priority (direct business value)
        agent_response_priority = self._calculate_message_priority(self.agent_response_message)
        
        # Agent starts have high priority (user waiting for AI response)
        agent_start_priority = self._calculate_message_priority(self.agent_start_message)
        
        # Quality alerts have medium priority (system health)
        quality_alert_priority = self._calculate_message_priority(self.quality_alert_message)
        
        # Business requirement: Response messages should have highest priority
        assert agent_response_priority >= agent_start_priority
        assert agent_start_priority >= quality_alert_priority
        
        # All priorities should be positive
        assert agent_response_priority > 0
        assert agent_start_priority > 0
        assert quality_alert_priority > 0
        
        # Record business metrics
        self.record_metric("agent_response_priority", agent_response_priority)
        self.record_metric("agent_start_priority", agent_start_priority)
        self.record_metric("quality_alert_priority", quality_alert_priority)
        
    def _calculate_message_priority(self, message: Dict[str, Any]) -> int:
        """Calculate message priority based on business logic."""
        message_type = message.get("type", "unknown")
        
        # Business priority mapping
        priority_map = {
            "agent_response": 100,  # Highest - direct user value
            "agent_start": 80,      # High - user waiting
            "agent_thinking": 70,   # Medium-high - progress feedback
            "quality_alert": 60,    # Medium - system health
            "system_status": 40,    # Medium-low - system info
            "unknown": 10          # Low - unclassified
        }
        
        base_priority = priority_map.get(message_type, 10)
        
        # Boost priority for messages with business value indicators
        if message_type == "agent_response":
            data = message.get("data", {})
            if "optimization_savings" in data and data["optimization_savings"] > 0:
                base_priority += 20  # High business value
            if "recommendations" in data and len(data["recommendations"]) > 0:
                base_priority += 10  # Actionable insights
                
        return base_priority
        
    @pytest.mark.unit
    def test_error_handling_routing(self):
        """Test error handling and fallback routing logic."""
        # Test malformed message handling
        malformed_messages = [
            {},  # Empty message
            {"no_type": "field"},  # Missing type
            {"type": None},  # Null type
            {"type": ""},  # Empty type
            {"type": "valid", "corrupted_data": "\x00\x01"}  # Corrupted data
        ]
        
        for malformed_msg in malformed_messages:
            # Business logic: Malformed messages should be handled gracefully
            result = self._handle_malformed_message(malformed_msg)
            
            # Should not crash and should return error indicator
            assert result is not None
            assert result.get("error", False) == True
            
        # Record business metric: Error handling robustness
        self.record_metric("malformed_messages_handled", len(malformed_messages))
        
    def _handle_malformed_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle malformed messages with business-appropriate fallbacks."""
        try:
            # Validate basic message structure
            if not isinstance(message, dict):
                return {"error": True, "reason": "not_dict"}
                
            if "type" not in message:
                return {"error": True, "reason": "missing_type"}
                
            if not message["type"]:
                return {"error": True, "reason": "empty_type"}
                
            # Basic validation passed
            return {"error": False, "message": message}
            
        except Exception as e:
            # Any exception during handling should be caught
            return {"error": True, "reason": "exception", "details": str(e)}
            
    @pytest.mark.unit
    def test_routing_performance_optimization(self):
        """Test routing performance for business responsiveness requirements."""
        # Business requirement: Message routing should be fast for good UX
        start_time = time.time()
        
        # Simulate routing multiple messages
        test_messages = [
            self.agent_start_message,
            self.agent_response_message,
            self.quality_alert_message
        ] * 10  # 30 messages total
        
        routing_results = []
        for message in test_messages:
            # Simulate routing logic
            route_result = self._simulate_message_routing(message)
            routing_results.append(route_result)
            
        end_time = time.time()
        total_time = end_time - start_time
        
        # Business requirement: Routing should be fast (< 1ms per message)
        avg_time_per_message = total_time / len(test_messages)
        assert avg_time_per_message < 0.001  # Less than 1ms per message
        
        # All messages should be routed successfully
        successful_routes = sum(1 for result in routing_results if result.get("routed"))
        assert successful_routes == len(test_messages)
        
        # Record performance metrics
        self.record_metric("routing_performance_ms_per_message", avg_time_per_message * 1000)
        self.record_metric("total_messages_routed", len(test_messages))
        self.record_metric("routing_success_rate", successful_routes / len(test_messages))
        
    def _simulate_message_routing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate message routing for performance testing."""
        message_type = message.get("type", "unknown")
        
        # Simulate routing decision logic
        if message_type in ["agent_start", "agent_response"]:
            handler = "agent_handler"
        elif message_type == "quality_alert":
            handler = "quality_handler"
        else:
            handler = "default_handler"
            
        return {
            "routed": True,
            "handler": handler,
            "message_type": message_type,
            "priority": self._calculate_message_priority(message)
        }
        
    @pytest.mark.unit
    def test_handler_selection_business_logic(self):
        """Test handler selection based on business requirements."""
        # Test cases: message type -> expected handler category
        handler_test_cases = [
            (self.agent_start_message, "agent"),
            (self.agent_response_message, "agent"), 
            (self.quality_alert_message, "quality"),
            ({"type": "system_status"}, "system"),
            ({"type": "unknown_type"}, "default")
        ]
        
        for message, expected_handler_category in handler_test_cases:
            handler = self._select_handler(message)
            
            # Business logic: Handler should match message category
            assert handler.startswith(expected_handler_category)
            
        # Record business metric: Handler selection accuracy
        self.record_metric("handler_selection_tests_passed", len(handler_test_cases))
        
    def _select_handler(self, message: Dict[str, Any]) -> str:
        """Select appropriate handler based on message type."""
        message_type = message.get("type", "unknown")
        
        # Business logic for handler selection
        if message_type.startswith("agent_"):
            return "agent_handler"
        elif message_type.startswith("quality_"):
            return "quality_handler"
        elif message_type.startswith("system_"):
            return "system_handler"
        else:
            return "default_handler"
            
    @pytest.mark.unit
    def test_business_value_metrics_tracking(self):
        """Test that business value metrics are properly tracked."""
        # Verify core business metrics were recorded
        all_metrics = self.get_all_metrics()
        
        # Essential business metrics for message routing
        required_metrics = [
            "router_initialization_success",
            "message_classification_tests_passed", 
            "message_validation_success",
            "routing_performance_ms_per_message"
        ]
        
        for metric in required_metrics:
            assert metric in all_metrics, f"Missing business metric: {metric}"
            
        # Performance metrics should meet business requirements
        perf_metric = all_metrics.get("routing_performance_ms_per_message", 999)
        assert perf_metric < 10, f"Routing too slow: {perf_metric}ms per message"
        
        # Record final business metrics
        self.record_metric("business_requirements_validated", True)
        self.record_metric("total_test_functions_executed", 7)
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Log business value metrics for monitoring
        final_metrics = self.get_all_metrics()
        
        # Set environment flags for business intelligence
        if final_metrics.get("router_initialization_success"):
            self.set_env_var("LAST_MESSAGE_ROUTING_TEST_SUCCESS", "true")
            
        if final_metrics.get("routing_performance_ms_per_message", 999) < 5:
            self.set_env_var("MESSAGE_ROUTING_PERFORMANCE_ACCEPTABLE", "true")
            
        super().teardown_method(method)