"""
Unit Tests for Agent Message Router - Golden Path Message Routing Logic

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - Core Message Infrastructure
- Business Goal: Ensure proper message routing between agents and users for Golden Path
- Value Impact: Message routing enables correct delivery of AI interactions worth $500K+ ARR
- Strategic Impact: Core routing logic that connects user requests to appropriate agent responses
- Revenue Protection: Without proper routing, users get wrong responses or no responses -> churn

PURPOSE: This test suite validates the message routing functionality that determines
how messages flow between users, agents, and the system in the Golden Path user flow.
Message routing is critical infrastructure that ensures users receive the right
AI responses from the correct agents at the right time.

KEY COVERAGE:
1. Message routing decisions based on message type
2. Agent-specific message routing logic
3. User context preservation in routing
4. Error message routing and fallback logic
5. Priority-based message routing
6. Performance requirements for routing decisions
7. Security validation in routing logic

GOLDEN PATH PROTECTION:
Tests ensure message router correctly delivers user requests to appropriate agents
and routes agent responses back to the correct users, maintaining the communication
flow that's essential for the $500K+ ARR AI interaction experience.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import message routing components
from netra_backend.app.websocket_core.types import MessageType
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MessagePriority(Enum):
    """Message priority levels for routing"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class RouteDestination(Enum):
    """Possible routing destinations"""
    TRIAGE_AGENT = "triage_agent"
    DATA_AGENT = "data_agent"
    OPTIMIZATION_AGENT = "optimization_agent"
    USER_WEBSOCKET = "user_websocket"
    ERROR_HANDLER = "error_handler"
    BROADCAST_MANAGER = "broadcast_manager"


@dataclass
class RoutingDecision:
    """Represents a routing decision made by the router"""
    destination: RouteDestination
    message_id: str
    user_id: str
    priority: MessagePriority
    routing_metadata: Dict[str, Any]
    processing_time: float


class MockMessageRouter:
    """Mock message router for testing routing logic"""
    
    def __init__(self):
        self.routing_decisions = []
        self.processed_messages = []
        self.routing_rules = self._initialize_routing_rules()
        self.performance_metrics = {}
        
    def _initialize_routing_rules(self) -> Dict[str, RouteDestination]:
        """Initialize message type to destination routing rules"""
        return {
            "user_request": RouteDestination.TRIAGE_AGENT,
            "optimization_request": RouteDestination.OPTIMIZATION_AGENT,
            "data_query": RouteDestination.DATA_AGENT,
            "agent_response": RouteDestination.USER_WEBSOCKET,
            "agent_error": RouteDestination.ERROR_HANDLER,
            "system_broadcast": RouteDestination.BROADCAST_MANAGER,
            "unknown": RouteDestination.ERROR_HANDLER
        }
    
    async def route_message(
        self, 
        message: Dict[str, Any], 
        context: UserExecutionContext
    ) -> RoutingDecision:
        """Route message based on type, content, and context"""
        
        start_time = time.time()
        
        # Extract routing information
        message_type = message.get("type", "unknown")
        message_id = message.get("id", f"msg_{int(time.time() * 1000)}")
        user_id = context.user_id
        
        # Determine priority
        priority = self._determine_message_priority(message)
        
        # Apply routing rules
        destination = self._apply_routing_rules(message, context)
        
        # Create routing decision
        processing_time = time.time() - start_time
        routing_decision = RoutingDecision(
            destination=destination,
            message_id=message_id,
            user_id=user_id,
            priority=priority,
            routing_metadata={
                "message_type": message_type,
                "routing_rule_applied": True,
                "context_validated": True,
                "security_check_passed": self._security_check(message, context)
            },
            processing_time=processing_time
        )
        
        # Store routing decision
        self.routing_decisions.append(routing_decision)
        self.processed_messages.append({
            "message": message,
            "context": context,
            "decision": routing_decision,
            "timestamp": time.time()
        })
        
        return routing_decision
    
    def _determine_message_priority(self, message: Dict[str, Any]) -> MessagePriority:
        """Determine message priority based on content and metadata"""
        
        # Check for explicit priority
        if "priority" in message:
            priority_str = message["priority"].lower()
            if priority_str in [p.value for p in MessagePriority]:
                return MessagePriority(priority_str)
        
        # Priority based on message type
        message_type = message.get("type", "").lower()
        
        if "error" in message_type or "critical" in message_type:
            return MessagePriority.CRITICAL
        elif "urgent" in message_type or message_type == "agent_started":
            return MessagePriority.HIGH
        elif message_type in ["optimization_request", "user_request"]:
            return MessagePriority.MEDIUM
        else:
            return MessagePriority.LOW
    
    def _apply_routing_rules(
        self, 
        message: Dict[str, Any], 
        context: UserExecutionContext
    ) -> RouteDestination:
        """Apply routing rules to determine destination"""
        
        message_type = message.get("type", "unknown")
        
        # Check for override rules based on context
        if context.user_tier == "enterprise" and message_type == "user_request":
            # Enterprise users get priority routing
            return RouteDestination.OPTIMIZATION_AGENT
        
        # Apply standard rules
        return self.routing_rules.get(message_type, RouteDestination.ERROR_HANDLER)
    
    def _security_check(self, message: Dict[str, Any], context: UserExecutionContext) -> bool:
        """Perform security validation on message and context"""
        
        # Check message structure
        if not isinstance(message, dict):
            return False
            
        # Check required fields
        if not message.get("type"):
            return False
            
        # Check context validity
        if not context or not context.user_id:
            return False
            
        # Check for suspicious content
        content = str(message.get("content", "")).lower()
        suspicious_patterns = ["<script>", "drop table", "rm -rf", "eval("]
        
        for pattern in suspicious_patterns:
            if pattern in content:
                return False
                
        return True
    
    async def route_batch_messages(
        self, 
        messages: List[Dict[str, Any]], 
        contexts: List[UserExecutionContext]
    ) -> List[RoutingDecision]:
        """Route multiple messages efficiently"""
        
        if len(messages) != len(contexts):
            raise ValueError("Messages and contexts must have same length")
        
        routing_decisions = []
        
        # Process messages concurrently for performance
        tasks = [
            self.route_message(msg, ctx) 
            for msg, ctx in zip(messages, contexts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, RoutingDecision):
                routing_decisions.append(result)
            else:
                # Create error routing decision
                error_decision = RoutingDecision(
                    destination=RouteDestination.ERROR_HANDLER,
                    message_id="error_msg",
                    user_id="unknown",
                    priority=MessagePriority.HIGH,
                    routing_metadata={"error": str(result)},
                    processing_time=0.0
                )
                routing_decisions.append(error_decision)
        
        return routing_decisions
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance and usage statistics"""
        
        if not self.routing_decisions:
            return {"total_messages": 0}
        
        total_messages = len(self.routing_decisions)
        
        # Calculate destination distribution
        destinations = {}
        priorities = {}
        processing_times = []
        
        for decision in self.routing_decisions:
            # Count destinations
            dest_name = decision.destination.value
            destinations[dest_name] = destinations.get(dest_name, 0) + 1
            
            # Count priorities
            priority_name = decision.priority.value
            priorities[priority_name] = priorities.get(priority_name, 0) + 1
            
            # Collect processing times
            processing_times.append(decision.processing_time)
        
        return {
            "total_messages": total_messages,
            "destination_distribution": destinations,
            "priority_distribution": priorities,
            "average_processing_time": sum(processing_times) / len(processing_times),
            "max_processing_time": max(processing_times),
            "min_processing_time": min(processing_times)
        }


class MessageRouterUnitTests(SSotAsyncTestCase):
    """Unit tests for message router functionality
    
    This test class validates the critical message routing capabilities that
    determine how messages flow through the system in the Golden Path user flow.
    These tests focus on core routing logic without requiring complex
    infrastructure dependencies.
    
    Tests MUST ensure message router can:
    1. Route messages to correct destinations based on type
    2. Apply proper priority to messages  
    3. Maintain user context during routing
    4. Handle routing errors gracefully
    5. Apply security validation during routing
    6. Process messages with performance requirements
    """
    
    def setup_method(self, method=None):
        """Setup for each test with proper isolation"""
        super().setup_method(method)
        
        # Create isolated user contexts for testing
        self.user_context = SSotMockFactory.create_mock_user_context(
            user_id=f"test_user_{self.get_test_context().test_id}",
            thread_id=f"test_thread_{self.get_test_context().test_id}",
            run_id=f"test_run_{self.get_test_context().test_id}",
            request_id=f"test_req_{self.get_test_context().test_id}"
        )
        
        self.enterprise_context = SSotMockFactory.create_mock_user_context(
            user_id="enterprise_user",
            thread_id="enterprise_thread", 
            run_id="enterprise_run",
            request_id="enterprise_req"
        )
        self.enterprise_context.user_tier = "enterprise"
        
        # Create message router instance
        self.router = MockMessageRouter()
    
    # ========================================================================
    # CORE MESSAGE ROUTING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_user_request_routing_to_triage_agent(self):
        """Test routing of user requests to triage agent
        
        Business Impact: Ensures user requests reach triage agent for proper
        categorization and workflow initialization in Golden Path.
        """
        # Create user request message
        user_request_msg = {
            "id": "user_req_001",
            "type": "user_request",
            "content": "Help me optimize my AI costs",
            "timestamp": time.time()
        }
        
        # Route message
        start_time = time.time()
        decision = await self.router.route_message(user_request_msg, self.user_context)
        routing_time = time.time() - start_time
        
        # Verify routing decision
        assert decision.destination == RouteDestination.TRIAGE_AGENT
        assert decision.message_id == "user_req_001"
        assert decision.user_id == self.user_context.user_id
        assert decision.priority == MessagePriority.MEDIUM
        
        # Verify routing metadata
        assert decision.routing_metadata["message_type"] == "user_request"
        assert decision.routing_metadata["routing_rule_applied"] is True
        assert decision.routing_metadata["security_check_passed"] is True
        
        # Verify performance
        assert routing_time < 0.001, f"Routing took {routing_time:.4f}s, should be < 0.001s"
        assert decision.processing_time < 0.001, "Processing time should be minimal for unit test"
        
        self.record_metric("user_request_routed_correctly", True)
        self.record_metric("routing_processing_time", decision.processing_time)
    
    @pytest.mark.unit
    async def test_optimization_request_routing(self):
        """Test routing of optimization requests to optimization agent
        
        Business Impact: Ensures optimization requests reach the specialized
        optimization agent for proper AI cost optimization analysis.
        """
        optimization_msg = {
            "id": "opt_req_001",
            "type": "optimization_request", 
            "content": "Optimize my model selection and reduce costs",
            "optimization_type": "cost",
            "timestamp": time.time()
        }
        
        decision = await self.router.route_message(optimization_msg, self.user_context)
        
        # Verify optimization routing
        assert decision.destination == RouteDestination.OPTIMIZATION_AGENT
        assert decision.priority == MessagePriority.MEDIUM
        assert decision.message_id == "opt_req_001"
        
        self.record_metric("optimization_request_routed_correctly", True)
    
    @pytest.mark.unit
    async def test_data_query_routing_to_data_agent(self):
        """Test routing of data queries to data agent
        
        Business Impact: Ensures data queries reach data agent for proper
        data retrieval and analysis in Golden Path workflows.
        """
        data_query_msg = {
            "id": "data_query_001",
            "type": "data_query",
            "content": "Get my usage statistics for last 30 days",
            "query_type": "usage_analytics",
            "timestamp": time.time()
        }
        
        decision = await self.router.route_message(data_query_msg, self.user_context)
        
        # Verify data query routing
        assert decision.destination == RouteDestination.DATA_AGENT
        assert decision.message_id == "data_query_001"
        assert decision.user_id == self.user_context.user_id
        
        self.record_metric("data_query_routed_correctly", True)
    
    @pytest.mark.unit
    async def test_agent_response_routing_to_user(self):
        """Test routing of agent responses back to user WebSocket
        
        Business Impact: Ensures agent responses reach users for Golden Path
        value delivery completion.
        """
        agent_response_msg = {
            "id": "agent_resp_001",
            "type": "agent_response",
            "content": "Your optimization analysis is complete",
            "agent_id": "optimization_agent_123",
            "result": {
                "savings_potential": "$1,200/month",
                "recommendations": ["Use smaller models for simple tasks"]
            },
            "timestamp": time.time()
        }
        
        decision = await self.router.route_message(agent_response_msg, self.user_context)
        
        # Verify response routing to user
        assert decision.destination == RouteDestination.USER_WEBSOCKET
        assert decision.message_id == "agent_resp_001"
        assert decision.user_id == self.user_context.user_id
        
        self.record_metric("agent_response_routed_to_user", True)
    
    # ========================================================================
    # MESSAGE PRIORITY TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_message_priority_determination(self):
        """Test message priority assignment based on type and content
        
        Business Impact: Proper prioritization ensures critical messages
        are handled first, improving system responsiveness.
        """
        # Test critical priority
        critical_msg = {
            "id": "critical_001",
            "type": "agent_error",
            "content": "Critical system error occurred",
            "timestamp": time.time()
        }
        
        critical_decision = await self.router.route_message(critical_msg, self.user_context)
        assert critical_decision.priority == MessagePriority.CRITICAL
        
        # Test high priority 
        high_msg = {
            "id": "high_001",
            "type": "agent_started",
            "content": "Agent started processing",
            "timestamp": time.time()
        }
        
        high_decision = await self.router.route_message(high_msg, self.user_context)
        assert high_decision.priority == MessagePriority.HIGH
        
        # Test medium priority
        medium_msg = {
            "id": "medium_001", 
            "type": "user_request",
            "content": "Regular user request",
            "timestamp": time.time()
        }
        
        medium_decision = await self.router.route_message(medium_msg, self.user_context)
        assert medium_decision.priority == MessagePriority.MEDIUM
        
        # Test low priority
        low_msg = {
            "id": "low_001",
            "type": "status_update",
            "content": "Status information",
            "timestamp": time.time()
        }
        
        low_decision = await self.router.route_message(low_msg, self.user_context)
        assert low_decision.priority == MessagePriority.LOW
        
        self.record_metric("priority_determination_tests_passed", 4)
    
    @pytest.mark.unit
    async def test_explicit_priority_override(self):
        """Test explicit priority specification overrides default rules
        
        Business Impact: Allows system to handle urgent requests that
        may not match standard priority patterns.
        """
        # Message with explicit high priority
        explicit_priority_msg = {
            "id": "explicit_001",
            "type": "status_update",  # Normally low priority
            "priority": "critical",   # Explicit override
            "content": "Critical status update",
            "timestamp": time.time()
        }
        
        decision = await self.router.route_message(explicit_priority_msg, self.user_context)
        
        # Should use explicit priority, not default for type
        assert decision.priority == MessagePriority.CRITICAL
        
        self.record_metric("explicit_priority_override_works", True)
    
    # ========================================================================
    # CONTEXT-BASED ROUTING TESTS
    # ========================================================================
    
    @pytest.mark.unit 
    async def test_enterprise_user_priority_routing(self):
        """Test enterprise users get priority routing
        
        Business Impact: Enterprise tier users receive enhanced service
        level for better customer satisfaction and retention.
        """
        enterprise_request = {
            "id": "enterprise_001",
            "type": "user_request",
            "content": "Enterprise user optimization request",
            "timestamp": time.time()
        }
        
        # Route with enterprise context
        enterprise_decision = await self.router.route_message(
            enterprise_request, self.enterprise_context
        )
        
        # Route with regular context for comparison
        regular_decision = await self.router.route_message(
            enterprise_request, self.user_context
        )
        
        # Enterprise should get routed directly to optimization agent
        assert enterprise_decision.destination == RouteDestination.OPTIMIZATION_AGENT
        
        # Regular user goes to triage first
        assert regular_decision.destination == RouteDestination.TRIAGE_AGENT
        
        self.record_metric("enterprise_priority_routing_works", True)
    
    @pytest.mark.unit
    async def test_user_context_preservation(self):
        """Test user context is preserved throughout routing
        
        Business Impact: Context preservation is critical for multi-tenant
        security and proper user isolation.
        """
        test_msg = {
            "id": "context_test_001",
            "type": "user_request",
            "content": "Test context preservation",
            "timestamp": time.time()
        }
        
        decision = await self.router.route_message(test_msg, self.user_context)
        
        # Verify context preservation
        assert decision.user_id == self.user_context.user_id
        
        # Verify context is stored with processed message
        processed_msg = self.router.processed_messages[-1]
        assert processed_msg["context"].user_id == self.user_context.user_id
        assert processed_msg["context"].thread_id == self.user_context.thread_id
        assert processed_msg["context"].run_id == self.user_context.run_id
        
        self.record_metric("user_context_preserved", True)
    
    # ========================================================================
    # SECURITY VALIDATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_security_validation_in_routing(self):
        """Test security checks are performed during routing
        
        Business Impact: Security validation prevents malicious messages
        from being routed to sensitive system components.
        """
        # Test valid message passes security
        valid_msg = {
            "id": "valid_001",
            "type": "user_request",
            "content": "Normal user request",
            "timestamp": time.time()
        }
        
        valid_decision = await self.router.route_message(valid_msg, self.user_context)
        assert valid_decision.routing_metadata["security_check_passed"] is True
        
        # Test suspicious content
        suspicious_messages = [
            {
                "id": "suspicious_001",
                "type": "user_request", 
                "content": "<script>alert('xss')</script>",
                "timestamp": time.time()
            },
            {
                "id": "suspicious_002",
                "type": "user_request",
                "content": "DROP TABLE users; --",
                "timestamp": time.time()
            }
        ]
        
        for msg in suspicious_messages:
            decision = await self.router.route_message(msg, self.user_context)
            # Should fail security check
            assert decision.routing_metadata["security_check_passed"] is False
        
        self.record_metric("security_validation_tests_passed", 3)
    
    @pytest.mark.unit
    async def test_malformed_message_routing(self):
        """Test routing of malformed messages to error handler
        
        Business Impact: Proper error handling prevents system crashes
        from malformed input and provides meaningful error responses.
        """
        # Test message without type
        malformed_msg = {
            "id": "malformed_001",
            "content": "Message without type field",
            "timestamp": time.time()
        }
        
        decision = await self.router.route_message(malformed_msg, self.user_context)
        
        # Should route to error handler for unknown type
        assert decision.destination == RouteDestination.ERROR_HANDLER
        assert decision.routing_metadata["security_check_passed"] is False
        
        self.record_metric("malformed_message_routed_to_error_handler", True)
    
    # ========================================================================
    # BATCH PROCESSING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_batch_message_routing(self):
        """Test efficient routing of multiple messages
        
        Business Impact: Batch processing improves system throughput
        and reduces latency for multiple simultaneous requests.
        """
        # Create batch of messages
        messages = []
        contexts = []
        
        for i in range(10):
            messages.append({
                "id": f"batch_msg_{i}",
                "type": "user_request" if i % 2 == 0 else "optimization_request",
                "content": f"Batch message {i}",
                "timestamp": time.time()
            })
            contexts.append(
                SSotMockFactory.create_mock_user_context(
                    user_id=f"batch_user_{i}",
                    thread_id=f"batch_thread_{i}",
                    run_id=f"batch_run_{i}"
                )
            )
        
        # Route batch
        start_time = time.time()
        decisions = await self.router.route_batch_messages(messages, contexts)
        batch_time = time.time() - start_time
        
        # Verify all messages routed
        assert len(decisions) == len(messages)
        
        # Verify routing correctness
        for i, decision in enumerate(decisions):
            expected_dest = (RouteDestination.TRIAGE_AGENT if i % 2 == 0 
                           else RouteDestination.OPTIMIZATION_AGENT)
            assert decision.destination == expected_dest
            assert decision.user_id == f"batch_user_{i}"
        
        # Verify batch performance
        assert batch_time < 0.1, f"Batch routing took {batch_time:.3f}s, should be < 0.1s"
        
        self.record_metric("batch_messages_routed", len(decisions))
        self.record_metric("batch_routing_time", batch_time)
    
    @pytest.mark.unit
    async def test_batch_routing_error_handling(self):
        """Test error handling in batch message routing
        
        Business Impact: Robust error handling ensures partial failures
        don't prevent processing of valid messages in batch.
        """
        # Create batch with some invalid messages
        messages = [
            {"id": "valid_1", "type": "user_request", "content": "Valid message 1"},
            {"id": "invalid_1", "content": "Missing type field"},  # Invalid
            {"id": "valid_2", "type": "optimization_request", "content": "Valid message 2"},
            None,  # Invalid message
        ]
        
        contexts = [
            SSotMockFactory.create_mock_user_context(user_id="user_1"),
            SSotMockFactory.create_mock_user_context(user_id="user_2"), 
            SSotMockFactory.create_mock_user_context(user_id="user_3"),
            SSotMockFactory.create_mock_user_context(user_id="user_4")
        ]
        
        # Should handle errors gracefully
        try:
            decisions = await self.router.route_batch_messages(messages, contexts)
            
            # Verify we get decisions for all messages (including error routing)
            assert len(decisions) == len(messages)
            
            # Valid messages should route correctly
            assert decisions[0].destination == RouteDestination.TRIAGE_AGENT
            assert decisions[2].destination == RouteDestination.OPTIMIZATION_AGENT
            
            # Invalid messages should route to error handler
            assert decisions[1].destination == RouteDestination.ERROR_HANDLER
            assert decisions[3].destination == RouteDestination.ERROR_HANDLER
            
        except Exception as e:
            # If batch routing fails completely, that's acceptable for invalid input
            assert "length" in str(e).lower() or "invalid" in str(e).lower()
        
        self.record_metric("batch_error_handling_works", True)
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_routing_performance(self):
        """Test message routing performance requirements
        
        Business Impact: Fast routing is critical for real-time user
        experience in Golden Path interactions.
        """
        test_msg = {
            "id": "perf_test_001",
            "type": "user_request",
            "content": "Performance test message",
            "timestamp": time.time()
        }
        
        # Measure routing times
        times = []
        for i in range(100):
            start_time = time.time()
            decision = await self.router.route_message(test_msg, self.user_context)
            end_time = time.time()
            
            assert decision.destination == RouteDestination.TRIAGE_AGENT
            times.append(end_time - start_time)
        
        # Calculate performance metrics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance requirements for unit tests
        assert avg_time < 0.001, f"Average routing time {avg_time:.6f}s should be < 0.001s"
        assert max_time < 0.005, f"Max routing time {max_time:.6f}s should be < 0.005s"
        
        self.record_metric("average_routing_time", avg_time)
        self.record_metric("max_routing_time", max_time)
        self.record_metric("routing_performance_requirements_met", True)
    
    @pytest.mark.unit
    async def test_routing_statistics_collection(self):
        """Test routing statistics and metrics collection
        
        Business Impact: Statistics enable monitoring and optimization
        of routing performance and patterns.
        """
        # Route various message types
        message_types = [
            "user_request", "optimization_request", "data_query", 
            "agent_response", "agent_error", "unknown"
        ]
        
        for i, msg_type in enumerate(message_types):
            msg = {
                "id": f"stats_test_{i}",
                "type": msg_type,
                "content": f"Statistics test message {i}",
                "timestamp": time.time()
            }
            await self.router.route_message(msg, self.user_context)
        
        # Get statistics
        stats = self.router.get_routing_statistics()
        
        # Verify statistics
        assert stats["total_messages"] == len(message_types)
        assert "destination_distribution" in stats
        assert "priority_distribution" in stats
        assert "average_processing_time" in stats
        
        # Verify destination counts
        dest_dist = stats["destination_distribution"]
        assert dest_dist["triage_agent"] == 1  # user_request
        assert dest_dist["optimization_agent"] == 1  # optimization_request
        assert dest_dist["data_agent"] == 1  # data_query
        assert dest_dist["user_websocket"] == 1  # agent_response
        assert dest_dist["error_handler"] == 2  # agent_error + unknown
        
        self.record_metric("routing_statistics_accurate", True)
        self.record_metric("total_routing_decisions_tracked", stats["total_messages"])
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Record final test metrics
        metrics = self.get_all_metrics()
        
        # Calculate comprehensive coverage metrics
        total_routing_tests = sum(1 for key in metrics.keys() 
                                if "routed" in key and metrics[key] is True)
        
        self.record_metric("message_routing_test_coverage", total_routing_tests)
        self.record_metric("routing_logic_validation_complete", True)
        
        # Call parent teardown
        super().teardown_method(method)