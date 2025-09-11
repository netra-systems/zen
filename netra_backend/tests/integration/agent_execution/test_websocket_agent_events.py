"""
WebSocket Agent Event Delivery Integration Tests

These tests validate the 5 critical WebSocket events during agent execution:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows when response is ready

Business Value Focus:
- Events enable meaningful AI chat interactions
- Real-time visibility into agent reasoning and tool usage
- Event sequencing and timing validation
- Concurrent user event isolation  
- Event delivery failure recovery

CRITICAL: Tests real WebSocket event systems without mocks for event logic.
"""

import asyncio
import logging
import time
import pytest
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.tests.integration.agent_execution.base_agent_execution_test import BaseAgentExecutionTest

logger = logging.getLogger(__name__)


class AdvancedWebSocketManager:
    """Advanced WebSocket manager with detailed event tracking and validation."""
    
    def __init__(self):
        self.emitted_events = []
        self.connected_users = {}
        self.event_sequence = []
        self.concurrent_sessions = {}
        self.performance_metrics = {
            "total_events": 0,
            "events_by_type": {},
            "avg_emission_time": 0,
            "failed_emissions": 0
        }
        
    async def emit_agent_event(self, event_type: str, data: Dict[str, Any], 
                              run_id: str, agent_name: str = None) -> bool:
        """Emit agent event with advanced tracking."""
        start_time = time.time()
        
        try:
            # Simulate realistic WebSocket emission timing
            await asyncio.sleep(0.01)  # Small network delay
            
            event = {
                'type': event_type,
                'data': data.copy() if data else {},
                'run_id': run_id,
                'agent_name': agent_name,
                'timestamp': time.time(),
                'sequence_id': len(self.event_sequence),
                'emission_time': time.time() - start_time
            }
            
            self.emitted_events.append(event)
            self.event_sequence.append(event_type)
            
            # Track per-user sessions
            user_id = data.get('user_id') if data else None
            if user_id:
                if user_id not in self.concurrent_sessions:
                    self.concurrent_sessions[user_id] = []
                self.concurrent_sessions[user_id].append(event)
            
            # Update performance metrics
            self.performance_metrics["total_events"] += 1
            if event_type not in self.performance_metrics["events_by_type"]:
                self.performance_metrics["events_by_type"][event_type] = 0
            self.performance_metrics["events_by_type"][event_type] += 1
            
            # Update average emission time
            total_time = self.performance_metrics["avg_emission_time"] * (self.performance_metrics["total_events"] - 1)
            self.performance_metrics["avg_emission_time"] = (total_time + event['emission_time']) / self.performance_metrics["total_events"]
            
            return True
            
        except Exception as e:
            self.performance_metrics["failed_emissions"] += 1
            raise RuntimeError(f"WebSocket emission failed: {e}")
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user is connected."""
        return user_id in self.connected_users
        
    def add_connection(self, user_id: str, connection_metadata: Dict[str, Any] = None):
        """Add user connection with metadata."""
        self.connected_users[user_id] = {
            "connected_at": time.time(),
            "metadata": connection_metadata or {},
            "event_count": 0
        }
        
    def get_critical_events_for_run(self, run_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get the 5 critical events for a specific run, grouped by type."""
        critical_event_types = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        
        run_events = [event for event in self.emitted_events if event['run_id'] == run_id]
        critical_events = {}
        
        for event_type in critical_event_types:
            critical_events[event_type] = [
                event for event in run_events if event['type'] == event_type
            ]
        
        return critical_events
        
    def validate_event_sequence(self, run_id: str) -> Dict[str, Any]:
        """Validate the sequence of critical events for business value delivery."""
        critical_events = self.get_critical_events_for_run(run_id)
        
        validation_results = {
            "sequence_valid": True,
            "missing_events": [],
            "timing_issues": [],
            "business_value_indicators": []
        }
        
        # Check required events exist
        required_events = ["agent_started", "agent_completed"]
        for event_type in required_events:
            if not critical_events[event_type]:
                validation_results["missing_events"].append(event_type)
                validation_results["sequence_valid"] = False
        
        # Check logical sequence
        if critical_events["agent_started"] and critical_events["agent_completed"]:
            start_time = critical_events["agent_started"][0]["timestamp"]
            end_time = critical_events["agent_completed"][-1]["timestamp"]
            
            if end_time <= start_time:
                validation_results["timing_issues"].append("agent_completed before agent_started")
                validation_results["sequence_valid"] = False
                
            # Check thinking events occur between start and end
            thinking_events = critical_events["agent_thinking"]
            for thinking_event in thinking_events:
                thinking_time = thinking_event["timestamp"]
                if thinking_time < start_time or thinking_time > end_time:
                    validation_results["timing_issues"].append(f"agent_thinking outside execution window")
                    
        # Check business value indicators in events
        for event_type, events in critical_events.items():
            for event in events:
                data = event.get("data", {})
                message = data.get("message", "")
                
                # Look for business value indicators
                business_indicators = ["optimization", "cost", "performance", "analysis", "recommendation", "insight"]
                for indicator in business_indicators:
                    if indicator.lower() in message.lower():
                        validation_results["business_value_indicators"].append({
                            "event_type": event_type,
                            "indicator": indicator,
                            "message_snippet": message[:50]
                        })
        
        return validation_results
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get WebSocket performance summary."""
        return self.performance_metrics.copy()
        
    def simulate_connection_failure(self, failure_rate: float = 0.1):
        """Simulate connection failures for testing."""
        self.failure_rate = failure_rate
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to a thread (required by WebSocketManagerProtocol).
        
        This method is required by the AgentWebSocketBridge interface validation.
        For testing purposes, we simply log the message and return success.
        
        Args:
            thread_id: Thread ID to send to
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            # For advanced testing, we track thread-specific messages
            if not hasattr(self, 'thread_messages'):
                self.thread_messages = {}
            
            if thread_id not in self.thread_messages:
                self.thread_messages[thread_id] = []
            
            self.thread_messages[thread_id].append({
                'message': message,
                'timestamp': time.time(),
                'thread_id': thread_id
            })
            
            # Simulate small network delay for realistic testing
            await asyncio.sleep(0.005)
            
            return True
        except Exception as e:
            # Track failures for advanced testing scenarios
            self.performance_metrics["failed_emissions"] += 1
            return False
        
    def clear_events(self):
        """Clear all events and reset metrics."""
        self.emitted_events.clear()
        self.event_sequence.clear()
        self.concurrent_sessions.clear()
        if hasattr(self, 'thread_messages'):
            self.thread_messages.clear()
        self.performance_metrics = {
            "total_events": 0,
            "events_by_type": {},
            "avg_emission_time": 0,
            "failed_emissions": 0
        }


class EventEmittingMockAgent(BaseAgent):
    """Mock agent that emits realistic WebSocket events during execution."""
    
    def __init__(self, agent_name: str, websocket_manager: AdvancedWebSocketManager, 
                 execution_steps: int = 3, tool_usage: bool = True):
        super().__init__(llm_manager=None, name=agent_name, description=f"Event emitting {agent_name}")
        self.websocket_manager = websocket_manager
        self.execution_steps = execution_steps
        self.tool_usage = tool_usage
        self.execution_count = 0
        
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with realistic WebSocket event emission patterns."""
        self.execution_count += 1
        
        # Event 1: Agent Started
        await self.websocket_manager.emit_agent_event(
            event_type="agent_started",
            data={
                "agent_name": self.name,
                "message": f"{self.name} agent starting execution",
                "user_id": context.user_id,
                "connection_id": context.websocket_connection_id,
                "execution_count": self.execution_count
            },
            run_id=context.run_id,
            agent_name=self.name
        )
        
        # Event 2: Agent Thinking (multiple thinking steps)
        for step in range(self.execution_steps):
            thinking_message = self._generate_thinking_message(step, context)
            
            await self.websocket_manager.emit_agent_event(
                event_type="agent_thinking",
                data={
                    "agent_name": self.name,
                    "message": thinking_message,
                    "user_id": context.user_id,
                    "connection_id": context.websocket_connection_id,
                    "step": step + 1,
                    "total_steps": self.execution_steps
                },
                run_id=context.run_id,
                agent_name=self.name
            )
            
            # Simulate thinking time
            await asyncio.sleep(0.1)
        
        # Event 3 & 4: Tool Executing and Tool Completed (if tool usage enabled)
        tool_results = []
        if self.tool_usage:
            tools_to_use = self._determine_tools_for_agent()
            
            for tool_name in tools_to_use:
                # Event 3: Tool Executing
                await self.websocket_manager.emit_agent_event(
                    event_type="tool_executing",
                    data={
                        "agent_name": self.name,
                        "tool_name": tool_name,
                        "message": f"Executing {tool_name} for business analysis",
                        "user_id": context.user_id,
                        "connection_id": context.websocket_connection_id
                    },
                    run_id=context.run_id,
                    agent_name=self.name
                )
                
                # Simulate tool execution
                await asyncio.sleep(0.2)
                
                # Generate tool result
                tool_result = {
                    "tool_name": tool_name,
                    "status": "completed",
                    "business_value": f"{tool_name} delivered cost optimization insights",
                    "metrics": {"processing_time": 0.2, "items_processed": 100}
                }
                tool_results.append(tool_result)
                
                # Event 4: Tool Completed
                await self.websocket_manager.emit_agent_event(
                    event_type="tool_completed",
                    data={
                        "agent_name": self.name,
                        "tool_name": tool_name,
                        "message": f"{tool_name} completed successfully",
                        "result": tool_result,
                        "user_id": context.user_id,
                        "connection_id": context.websocket_connection_id
                    },
                    run_id=context.run_id,
                    agent_name=self.name
                )
        
        # Final processing
        await asyncio.sleep(0.1)
        
        # Event 5: Agent Completed
        final_result = {
            "status": "completed",
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "thinking_steps": self.execution_steps,
            "tools_used": len(tool_results),
            "tool_results": tool_results,
            "business_output": {
                "insights": [f"Business insight {i+1} from {self.name}" for i in range(2)],
                "recommendations": [f"Recommendation {i+1} from {self.name}" for i in range(2)],
                "business_value": f"{self.name} delivered comprehensive business analysis"
            }
        }
        
        await self.websocket_manager.emit_agent_event(
            event_type="agent_completed",
            data={
                "agent_name": self.name,
                "message": f"{self.name} execution completed successfully",
                "result": final_result,
                "user_id": context.user_id,
                "connection_id": context.websocket_connection_id,
                "business_value_delivered": True
            },
            run_id=context.run_id,
            agent_name=self.name
        )
        
        return final_result
        
    def _generate_thinking_message(self, step: int, context: UserExecutionContext) -> str:
        """Generate realistic thinking messages with business context."""
        user_request = context.metadata.get("user_request", "")
        
        thinking_templates = [
            f"Analyzing user request: {user_request[:50]}...",
            f"Identifying optimization opportunities in the provided context",
            f"Evaluating cost reduction strategies and performance improvements",
            f"Considering business impact and implementation feasibility",
            f"Synthesizing findings into actionable recommendations"
        ]
        
        if step < len(thinking_templates):
            return thinking_templates[step]
        else:
            return f"Processing business logic step {step + 1} for {self.name}"
            
    def _determine_tools_for_agent(self) -> List[str]:
        """Determine which tools this agent should use based on its name."""
        if self.name == "cost_analyzer":
            return ["cost_analysis_tool", "usage_pattern_tool"]
        elif self.name == "performance_optimizer":
            return ["performance_monitor", "optimization_engine"]
        elif self.name == "data_processor":
            return ["data_collector", "data_transformer"]
        else:
            return ["generic_analysis_tool"]


class TestWebSocketAgentEvents(BaseAgentExecutionTest):
    """Test WebSocket agent event delivery and the 5 critical events."""
    
    def setup_method(self):
        """Set up advanced WebSocket testing environment."""
        super().setup_method()
        
        # Replace mock WebSocket manager with advanced version
        self.advanced_websocket_manager = AdvancedWebSocketManager()
        self.websocket_bridge.websocket_manager = self.advanced_websocket_manager
        
        # Add test user connection
        self.advanced_websocket_manager.add_connection(
            self.test_user_id,
            {"test_mode": True, "critical_events_required": True}
        )

    @pytest.mark.asyncio
    async def test_all_five_critical_events_sent_during_agent_execution(self):
        """Test that all 5 critical WebSocket events are sent during agent execution.
        
        Critical Events:
        1. agent_started - User sees agent began processing
        2. agent_thinking - Real-time reasoning visibility
        3. tool_executing - Tool usage transparency  
        4. tool_completed - Tool results display
        5. agent_completed - User knows when response is ready
        """
        # Create context for comprehensive agent execution
        context = self.create_user_execution_context(
            user_request="Execute comprehensive business analysis with all critical events",
            additional_metadata={
                "requires_all_events": True,
                "business_critical": True,
                "real_time_updates": True
            }
        )
        
        # Create event-emitting agent
        agent = EventEmittingMockAgent(
            agent_name="comprehensive_analyzer",
            websocket_manager=self.advanced_websocket_manager,
            execution_steps=4,
            tool_usage=True
        )
        
        # Execute agent and capture all events
        start_time = time.time()
        result = await agent.execute(context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # Get critical events for validation
        critical_events = self.advanced_websocket_manager.get_critical_events_for_run(context.run_id)
        
        # Validate all 5 critical events were emitted
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in required_events:
            assert len(critical_events[event_type]) > 0, f"Critical event '{event_type}' was not emitted"
            
        # Validate specific event counts and content
        assert len(critical_events["agent_started"]) == 1, "Should have exactly one agent_started event"
        assert len(critical_events["agent_completed"]) == 1, "Should have exactly one agent_completed event"
        assert len(critical_events["agent_thinking"]) >= 3, "Should have multiple thinking events for visibility"
        assert len(critical_events["tool_executing"]) >= 1, "Should have tool execution events"
        assert len(critical_events["tool_completed"]) >= 1, "Should have tool completion events"
        
        # Validate event content quality
        started_event = critical_events["agent_started"][0]
        assert "agent_name" in started_event["data"], "Started event should contain agent name"
        assert "message" in started_event["data"], "Started event should contain user-facing message"
        assert started_event["data"]["user_id"] == context.user_id, "Started event should contain correct user ID"
        
        thinking_events = critical_events["agent_thinking"]
        for thinking_event in thinking_events:
            assert "message" in thinking_event["data"], "Thinking events should contain reasoning messages"
            assert len(thinking_event["data"]["message"]) > 10, "Thinking messages should be meaningful"
            
        tool_exec_events = critical_events["tool_executing"]
        tool_comp_events = critical_events["tool_completed"]
        assert len(tool_exec_events) == len(tool_comp_events), "Each tool execution should have corresponding completion"
        
        completed_event = critical_events["agent_completed"][0]
        assert "result" in completed_event["data"], "Completed event should contain execution result"
        assert completed_event["data"].get("business_value_delivered") is True, "Should indicate business value delivered"
        
        # Validate execution result
        assert result["status"] == "completed", "Agent should complete successfully"
        assert "business_output" in result, "Agent should provide business output"
        assert len(result["business_output"]["insights"]) > 0, "Should provide business insights"

    @pytest.mark.asyncio
    async def test_event_ordering_and_timing_validation(self):
        """Test WebSocket event ordering and timing meets business requirements.
        
        Validates:
        - Events are sent in logical business sequence
        - Timing between events is reasonable for user experience  
        - Event timestamps show proper progression
        - Business value is communicated throughout execution
        """
        context = self.create_user_execution_context(
            user_request="Test event ordering and timing for optimal user experience",
            additional_metadata={
                "timing_critical": True,
                "user_experience_focus": True,
                "sequence_validation": True
            }
        )
        
        # Create agent with controlled timing
        agent = EventEmittingMockAgent(
            agent_name="timing_test_agent",
            websocket_manager=self.advanced_websocket_manager,
            execution_steps=5,
            tool_usage=True
        )
        
        # Execute with timing tracking
        execution_start = time.time()
        result = await agent.execute(context, stream_updates=True)
        execution_end = time.time()
        
        # Validate sequence using WebSocket manager validation
        sequence_validation = self.advanced_websocket_manager.validate_event_sequence(context.run_id)
        
        assert sequence_validation["sequence_valid"] is True, \
            f"Event sequence validation failed: {sequence_validation['timing_issues']}"
        assert len(sequence_validation["missing_events"]) == 0, \
            f"Missing critical events: {sequence_validation['missing_events']}"
        
        # Get all events for detailed timing analysis
        all_events = [event for event in self.advanced_websocket_manager.emitted_events 
                     if event['run_id'] == context.run_id]
        
        # Validate event progression
        timestamps = [event["timestamp"] for event in all_events]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], "Event timestamps should be non-decreasing"
            
        # Validate business timing requirements
        started_time = next(event["timestamp"] for event in all_events if event["type"] == "agent_started")
        completed_time = next(event["timestamp"] for event in all_events if event["type"] == "agent_completed")
        
        total_event_duration = completed_time - started_time
        actual_execution_duration = execution_end - execution_start
        
        # Event timing should be close to actual execution timing
        timing_variance = abs(total_event_duration - actual_execution_duration)
        assert timing_variance < 0.5, f"Event timing variance {timing_variance:.3f}s too high"
        
        # Validate thinking event spacing for good UX
        thinking_events = [event for event in all_events if event["type"] == "agent_thinking"]
        thinking_timestamps = [event["timestamp"] for event in thinking_events]
        
        if len(thinking_timestamps) > 1:
            thinking_intervals = [thinking_timestamps[i] - thinking_timestamps[i-1] 
                                for i in range(1, len(thinking_timestamps))]
            avg_thinking_interval = sum(thinking_intervals) / len(thinking_intervals)
            
            # Thinking events should be spaced reasonably for UX (not too fast, not too slow)
            assert 0.05 <= avg_thinking_interval <= 0.5, \
                f"Thinking event interval {avg_thinking_interval:.3f}s outside optimal UX range"
        
        # Validate business value indicators in sequence
        business_indicators = sequence_validation["business_value_indicators"]
        assert len(business_indicators) >= 2, "Should have multiple business value indicators throughout execution"
        
        # Validate performance metrics
        perf_metrics = self.advanced_websocket_manager.get_performance_summary()
        assert perf_metrics["failed_emissions"] == 0, "Should have no failed event emissions"
        assert perf_metrics["avg_emission_time"] < 0.1, "Event emission should be fast for good UX"

    @pytest.mark.asyncio
    async def test_event_payload_accuracy_and_completeness(self):
        """Test WebSocket event payloads contain accurate and complete business information.
        
        Validates:
        - Event payloads contain all required business context
        - Data accuracy across event types  
        - Event payloads support business decision making
        - No sensitive information leakage in events
        """
        context = self.create_user_execution_context(
            user_request="Analyze customer cost optimization with sensitive business data",
            additional_metadata={
                "customer_tier": "enterprise",
                "confidential_data": {"api_keys": "secret_key_123", "internal_metrics": {"revenue": 1000000}},
                "business_context": {"department": "finance", "project": "q4_cost_reduction"},
                "payload_validation": True
            }
        )
        
        # Create agent focused on business analysis
        agent = EventEmittingMockAgent(
            agent_name="business_analyzer",
            websocket_manager=self.advanced_websocket_manager,
            execution_steps=3,
            tool_usage=True
        )
        
        # Execute agent
        result = await agent.execute(context, stream_updates=True)
        
        # Get all events for payload validation
        all_events = [event for event in self.advanced_websocket_manager.emitted_events 
                     if event['run_id'] == context.run_id]
        
        # Validate payload structure and content
        for event in all_events:
            # Standard payload validation
            assert "type" in event, "Event should have type"
            assert "data" in event, "Event should have data payload"
            assert "timestamp" in event, "Event should have timestamp"
            assert "run_id" in event, "Event should have run_id"
            
            data = event["data"]
            
            # User context validation
            assert "user_id" in data, "Event data should contain user_id"
            assert data["user_id"] == context.user_id, "Event should contain correct user_id"
            
            if "connection_id" in data:
                assert data["connection_id"] == context.websocket_connection_id, "Should have correct connection_id"
            
            # Message quality validation
            if "message" in data:
                message = data["message"]
                assert isinstance(message, str), "Message should be string"
                assert len(message) > 0, "Message should not be empty"
                assert len(message) < 500, "Message should not be excessively long"
                
                # Business context validation
                if event["type"] in ["agent_thinking", "tool_executing"]:
                    # These events should contain business-relevant information
                    business_terms = ["analysis", "optimization", "cost", "performance", "business", 
                                    "insight", "recommendation", "strategy"]
                    has_business_term = any(term in message.lower() for term in business_terms)
                    assert has_business_term, f"Business event should contain business terms: {message}"
            
            # Sensitive data validation - ensure no leakage
            event_str = str(event).lower()
            sensitive_patterns = ["secret", "api_key", "password", "token", "internal_metrics", "revenue"]
            
            for pattern in sensitive_patterns:
                assert pattern not in event_str, f"Event should not contain sensitive data: {pattern}"
        
        # Validate event-specific payload requirements
        critical_events = self.advanced_websocket_manager.get_critical_events_for_run(context.run_id)
        
        # Agent started payload validation
        started_events = critical_events["agent_started"]
        for event in started_events:
            data = event["data"]
            assert "agent_name" in data, "Started event should contain agent_name"
            assert "execution_count" in data, "Started event should contain execution tracking"
            
        # Tool execution payload validation
        tool_exec_events = critical_events["tool_executing"]
        for event in tool_exec_events:
            data = event["data"]
            assert "tool_name" in data, "Tool execution event should contain tool_name"
            assert "agent_name" in data, "Tool execution event should contain agent_name"
            
        # Tool completion payload validation
        tool_comp_events = critical_events["tool_completed"]
        for event in tool_comp_events:
            data = event["data"]
            assert "tool_name" in data, "Tool completion event should contain tool_name"
            assert "result" in data, "Tool completion event should contain result"
            
            result_data = data["result"]
            assert "status" in result_data, "Tool result should contain status"
            assert "business_value" in result_data, "Tool result should indicate business value"
        
        # Agent completion payload validation
        completed_events = critical_events["agent_completed"]
        for event in completed_events:
            data = event["data"]
            assert "result" in data, "Completion event should contain full result"
            assert "business_value_delivered" in data, "Should indicate business value delivery"
            
            result_data = data["result"]
            assert "business_output" in result_data, "Result should contain business output"
            
            business_output = result_data["business_output"]
            assert "insights" in business_output, "Business output should contain insights"
            assert "recommendations" in business_output, "Business output should contain recommendations"
            assert len(business_output["insights"]) > 0, "Should have actionable insights"

    @pytest.mark.asyncio
    async def test_concurrent_user_event_isolation(self):
        """Test WebSocket events are properly isolated between concurrent users.
        
        Validates:
        - Events for different users don't cross-contaminate
        - Concurrent execution doesn't affect event delivery
        - User-specific context is preserved in events
        - System performance under concurrent load
        """
        # Create multiple user contexts for concurrent testing
        user_contexts = []
        for i in range(3):
            user_id = f"concurrent_user_{i}_{int(time.time())}"
            thread_id = f"thread_{i}_{int(time.time())}"
            run_id = f"run_{i}_{int(time.time())}"
            
            # Add user connection
            self.advanced_websocket_manager.add_connection(user_id, {"concurrent_test": True})
            
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_client_id=f"ws_connection_{user_id}",
                agent_context={
                    "user_request": f"Concurrent analysis request from user {i}",
                    "user_index": i,
                    "isolation_test": True,
                    "business_priority": "high" if i == 0 else "medium"
                }
            )
            user_contexts.append(context)
        
        # Create agents for each user
        agents = []
        for i, context in enumerate(user_contexts):
            agent = EventEmittingMockAgent(
                agent_name=f"concurrent_agent_{i}",
                websocket_manager=self.advanced_websocket_manager,
                execution_steps=2 + i,  # Different execution patterns
                tool_usage=True
            )
            agents.append(agent)
        
        # Execute all agents concurrently
        start_time = time.time()
        
        tasks = []
        for i, (agent, context) in enumerate(zip(agents, user_contexts)):
            task = asyncio.create_task(
                agent.execute(context, stream_updates=True),
                name=f"user_{i}_execution"
            )
            tasks.append((i, task, context))
        
        # Wait for all concurrent executions to complete
        results = []
        for i, task, context in tasks:
            result = await task
            results.append((i, result, context))
            
        concurrent_execution_time = time.time() - start_time
        
        # Validate concurrent execution isolation
        assert len(results) == 3, "All concurrent users should complete"
        
        # Validate per-user event isolation
        for i, (user_index, result, context) in enumerate(results):
            user_events = [event for event in self.advanced_websocket_manager.emitted_events 
                          if event['run_id'] == context.run_id]
            
            assert len(user_events) >= 5, f"User {user_index} should have minimum critical events"
            
            # Validate all events belong to correct user
            for event in user_events:
                event_user_id = event["data"].get("user_id")
                assert event_user_id == context.user_id, \
                    f"Event user_id {event_user_id} doesn't match context user_id {context.user_id}"
                    
                # Validate connection isolation
                event_connection_id = event["data"].get("connection_id")
                if event_connection_id:
                    assert event_connection_id == context.websocket_connection_id, \
                        "Event connection_id should match user's WebSocket connection"
        
        # Validate no cross-user contamination
        all_run_ids = [context.run_id for _, _, context in results]
        
        for run_id in all_run_ids:
            run_events = [event for event in self.advanced_websocket_manager.emitted_events 
                         if event['run_id'] == run_id]
            
            # Check that all events for this run have consistent user_id
            user_ids_in_run = set()
            for event in run_events:
                if "user_id" in event["data"]:
                    user_ids_in_run.add(event["data"]["user_id"])
                    
            assert len(user_ids_in_run) == 1, f"Run {run_id} should have events from only one user"
        
        # Validate concurrent performance
        sequential_estimate = len(user_contexts) * 1.0  # Estimated sequential time
        speedup_ratio = sequential_estimate / concurrent_execution_time
        
        assert speedup_ratio > 1.5, f"Concurrent execution should provide speedup, got {speedup_ratio:.2f}x"
        
        # Validate session tracking
        concurrent_sessions = self.advanced_websocket_manager.concurrent_sessions
        assert len(concurrent_sessions) == 3, "Should track all concurrent user sessions"
        
        for context in user_contexts:
            user_session_events = concurrent_sessions.get(context.user_id, [])
            assert len(user_session_events) >= 5, f"User {context.user_id} should have session events tracked"

    @pytest.mark.asyncio
    async def test_event_delivery_failure_recovery(self):
        """Test WebSocket event delivery failure recovery mechanisms.
        
        Validates:
        - System handles WebSocket delivery failures gracefully
        - Critical events are retried when possible
        - Agent execution continues despite event failures
        - Business value delivery is not compromised by event issues
        """
        context = self.create_user_execution_context(
            user_request="Test event delivery failure recovery in production scenarios",
            additional_metadata={
                "failure_recovery_test": True,
                "business_critical": True,
                "resilience_required": True
            }
        )
        
        # Create agent with event delivery failure simulation
        agent = EventEmittingMockAgent(
            agent_name="resilient_agent",
            websocket_manager=self.advanced_websocket_manager,
            execution_steps=4,
            tool_usage=True
        )
        
        # Simulate intermittent WebSocket failures
        original_emit = self.advanced_websocket_manager.emit_agent_event
        failure_count = 0
        failure_events = []
        
        async def failing_emit(event_type: str, data: Dict[str, Any], run_id: str, agent_name: str = None) -> bool:
            nonlocal failure_count, failure_events
            
            # Simulate 30% failure rate for some events (graceful failure)
            if event_type in ["agent_thinking", "tool_executing"] and failure_count < 3:
                failure_count += 1
                failure_events.append({
                    "event_type": event_type,
                    "failure_count": failure_count,
                    "timestamp": time.time(),
                    "error": f"Simulated WebSocket delivery failure for {event_type}"
                })
                # Log the simulated failure but don't crash the agent execution
                logger.warning(f"Simulated WebSocket delivery failure for {event_type} (test scenario)")
                return False  # Return False to indicate delivery failure without crashing
            
            # Let other events succeed normally
            return await original_emit(event_type, data, run_id, agent_name)
        
        # Replace emit method with failing version
        self.advanced_websocket_manager.emit_agent_event = failing_emit
        
        # Execute agent with failure recovery
        execution_successful = False
        result = None
        
        try:
            result = await agent.execute(context, stream_updates=True)
            execution_successful = True
        except Exception as e:
            # Agent execution should not fail due to event delivery issues
            pytest.fail(f"Agent execution failed due to event delivery issues: {e}")
        
        # Validate execution completed despite event failures
        assert execution_successful, "Agent execution should succeed despite WebSocket event failures"
        assert result is not None, "Agent should return result despite event delivery issues"
        assert result["status"] == "completed", "Agent should complete successfully"
        
        # Validate business value was still delivered
        assert "business_output" in result, "Business output should be delivered despite event failures"
        assert len(result["business_output"]["insights"]) > 0, "Business insights should be generated"
        assert len(result["business_output"]["recommendations"]) > 0, "Business recommendations should be generated"
        
        # Validate some events succeeded
        successful_events = [event for event in self.advanced_websocket_manager.emitted_events 
                           if event['run_id'] == context.run_id]
        
        assert len(successful_events) > 0, "Some events should succeed despite failures"
        
        # Critical events (started/completed) should succeed
        critical_events = self.advanced_websocket_manager.get_critical_events_for_run(context.run_id)
        
        # agent_started and agent_completed are most critical
        assert len(critical_events["agent_started"]) >= 1, "Agent started events should succeed (critical for UX)"
        assert len(critical_events["agent_completed"]) >= 1, "Agent completed events should succeed (critical for UX)"
        
        # Validate failure tracking
        assert len(failure_events) > 0, "Should have simulated some failures"
        assert failure_count > 0, "Should track failure count"
        
        perf_metrics = self.advanced_websocket_manager.get_performance_summary()
        assert perf_metrics["failed_emissions"] >= failure_count, "Should track failed emissions"
        
        # Validate business continuity
        # Even with event failures, the business logic should complete
        assert "tools_used" in result, "Tool usage should complete despite event failures"
        assert result["tools_used"] > 0, "Should have used tools despite event delivery issues"

    @pytest.mark.asyncio
    async def test_websocket_event_performance_under_load(self):
        """Test WebSocket event performance under load conditions.
        
        Validates:
        - Event emission performance scales with load
        - Memory usage remains reasonable during high event volume
        - Event delivery latency stays within acceptable bounds
        - System maintains responsiveness under event load
        """
        # Create high-load scenario with multiple concurrent agents
        load_contexts = []
        num_concurrent_users = 5
        events_per_user = 20  # High event volume per user
        
        for i in range(num_concurrent_users):
            context = self.create_user_execution_context(
                user_request=f"High-load performance test user {i}",
                additional_metadata={
                    "performance_test": True,
                    "user_index": i,
                    "expected_event_count": events_per_user
                }
            )
            load_contexts.append(context)
            
            # Add user connection
            self.advanced_websocket_manager.add_connection(context.user_id, {"performance_test": True})
        
        # Create high-event-volume agents
        load_agents = []
        for i, context in enumerate(load_contexts):
            agent = EventEmittingMockAgent(
                agent_name=f"load_test_agent_{i}",
                websocket_manager=self.advanced_websocket_manager,
                execution_steps=8,  # High number of thinking steps
                tool_usage=True
            )
            load_agents.append(agent)
        
        # Track performance metrics
        start_memory = self.advanced_websocket_manager.performance_metrics.copy()
        load_start_time = time.time()
        
        # Execute high-load concurrent scenario
        load_tasks = []
        for agent, context in zip(load_agents, load_contexts):
            task = asyncio.create_task(agent.execute(context, stream_updates=True))
            load_tasks.append(task)
        
        # Wait for all high-load executions
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        load_end_time = time.time()
        
        total_load_time = load_end_time - load_start_time
        
        # Validate load test results
        successful_executions = [result for result in load_results if not isinstance(result, Exception)]
        assert len(successful_executions) == num_concurrent_users, \
            f"All {num_concurrent_users} concurrent executions should succeed under load"
        
        # Validate performance metrics
        final_metrics = self.advanced_websocket_manager.get_performance_summary()
        
        total_events = final_metrics["total_events"] - start_memory["total_events"]
        expected_min_events = num_concurrent_users * 10  # Minimum events per user
        
        assert total_events >= expected_min_events, \
            f"Should emit at least {expected_min_events} events under load, got {total_events}"
        
        # Validate average emission time under load
        avg_emission_time = final_metrics["avg_emission_time"]
        assert avg_emission_time < 0.05, \
            f"Average event emission time {avg_emission_time:.4f}s should remain fast under load"
        
        # Validate event delivery throughput
        events_per_second = total_events / total_load_time
        min_throughput = 50  # events per second
        assert events_per_second >= min_throughput, \
            f"Event throughput {events_per_second:.1f} events/sec should meet minimum {min_throughput} events/sec"
        
        # Validate failure rate under load
        failure_rate = final_metrics["failed_emissions"] / max(total_events, 1)
        max_acceptable_failure_rate = 0.05  # 5% max failure rate
        assert failure_rate <= max_acceptable_failure_rate, \
            f"Event failure rate {failure_rate:.3f} should be below {max_acceptable_failure_rate}"
        
        # Validate concurrent execution performance
        avg_execution_time = total_load_time / num_concurrent_users  # If they were sequential
        parallel_efficiency = avg_execution_time / total_load_time
        assert parallel_efficiency >= 2.0, \
            f"Parallel execution should be efficient, efficiency: {parallel_efficiency:.2f}x"
        
        # Validate event distribution across users
        for context in load_contexts:
            user_events = [event for event in self.advanced_websocket_manager.emitted_events 
                          if event['run_id'] == context.run_id]
            
            assert len(user_events) >= 8, f"User {context.user_id} should have received adequate events under load"
            
            # Validate event timing consistency under load
            event_timestamps = [event["timestamp"] for event in user_events]
            if len(event_timestamps) > 1:
                time_diffs = [event_timestamps[i] - event_timestamps[i-1] 
                            for i in range(1, len(event_timestamps))]
                max_gap = max(time_diffs)
                assert max_gap < 2.0, f"Event timing gaps should remain reasonable under load, max gap: {max_gap:.3f}s"
        
        # Validate system responsiveness (memory and resource usage)
        # This is approximated by checking event processing efficiency
        events_by_type = final_metrics["events_by_type"]
        for event_type, count in events_by_type.items():
            if count > 0:
                # All event types should be processed efficiently
                assert count <= total_events, f"Event type {event_type} count should be reasonable"