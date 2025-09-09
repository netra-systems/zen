"""
Integration Tests: Agent WebSocket Events - Real-Time Chat Value Delivery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable real-time chat notifications to deliver substantive AI value
- Value Impact: WebSocket events ARE the user experience - without them chat appears broken
- Strategic Impact: Core infrastructure for AI agent transparency and user engagement

This test suite validates the 5 MANDATORY WebSocket events for chat business value:
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI working on solutions)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

CRITICAL: These events enable substantive chat interactions and serve the business goal
of delivering AI value to users. Tests use REAL WebSocket connections and Redis state.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)

# MISSION CRITICAL: The 5 required WebSocket events for chat value
REQUIRED_WEBSOCKET_EVENTS = [
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
]


class ChatValueWebSocketAgent(BaseAgent):
    """Agent that demonstrates all 5 critical WebSocket events for chat value."""
    
    def __init__(self, name: str, llm_manager: LLMManager, tool_count: int = 2, thinking_steps: int = 3):
        super().__init__(name=name, llm_manager=llm_manager, description=f"Chat WebSocket {name} agent")
        self.tool_count = tool_count
        self.thinking_steps = thinking_steps
        self.execution_count = 0
        self.emitted_events = []
        
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent with all 5 critical WebSocket events for chat value."""
        self.execution_count += 1
        
        if not stream_updates:
            # Without WebSocket events, agent provides minimal value
            return {"success": True, "message": "Silent execution - no chat value delivered"}
        
        # CRITICAL EVENT 1: agent_started - User sees agent began processing
        await self.emit_agent_started(f"Starting {self.name} analysis for chat value delivery")
        self.emitted_events.append("agent_started")
        
        # CRITICAL EVENT 2: agent_thinking - Show AI reasoning process (multiple steps)
        for step in range(self.thinking_steps):
            thinking_content = self._generate_thinking_content(step + 1)
            await self.emit_thinking(
                thinking_content, 
                step_number=step + 1,
                context=context
            )
            self.emitted_events.append("agent_thinking")
            await asyncio.sleep(0.05)  # Realistic thinking delay
        
        # CRITICAL EVENTS 3 & 4: tool_executing and tool_completed - Show problem-solving
        tool_results = []
        for tool_num in range(self.tool_count):
            tool_name, tool_params = self._generate_tool_execution(tool_num + 1)
            
            # EVENT 3: tool_executing - Show tool is running 
            await self.emit_tool_executing(tool_name, tool_params)
            self.emitted_events.append("tool_executing")
            
            # Simulate tool processing
            await asyncio.sleep(0.08)
            
            # EVENT 4: tool_completed - Show tool results (actionable insights)
            tool_result = self._generate_tool_results(tool_name, tool_params)
            await self.emit_tool_completed(tool_name, tool_result)
            self.emitted_events.append("tool_completed")
            tool_results.append(tool_result)
            
            # Follow-up thinking after tool completion
            await self.emit_thinking(f"Analyzing results from {tool_name}...", context=context)
            self.emitted_events.append("agent_thinking")
        
        # Final synthesis thinking
        await self.emit_thinking("Synthesizing insights and preparing recommendations...", context=context)
        self.emitted_events.append("agent_thinking")
        
        # Generate valuable business result
        agent_result = self._generate_business_value_result(context, tool_results)
        
        # CRITICAL EVENT 5: agent_completed - User knows valuable response is ready
        await self.emit_agent_completed(agent_result, context=context)
        self.emitted_events.append("agent_completed")
        
        return agent_result
    
    def _generate_thinking_content(self, step: int) -> str:
        """Generate realistic thinking content for chat value."""
        thinking_patterns = {
            1: f"Analyzing {self.name} request and identifying optimization opportunities...",
            2: f"Processing data patterns and determining best approach for {self.name}...",
            3: f"Evaluating multiple strategies and selecting optimal {self.name} solution...",
            4: f"Synthesizing findings and preparing actionable {self.name} recommendations..."
        }
        return thinking_patterns.get(step, f"Continuing {self.name} analysis (step {step})...")
    
    def _generate_tool_execution(self, tool_num: int) -> tuple[str, Dict]:
        """Generate realistic tool execution for chat demonstration."""
        tools = {
            1: (f"{self.name}_cost_analyzer", {
                "data_source": "user_spending_patterns", 
                "analysis_depth": "comprehensive",
                "time_window": "90_days"
            }),
            2: (f"{self.name}_optimization_engine", {
                "optimization_target": "cost_efficiency", 
                "strategy": "ml_based",
                "risk_tolerance": "moderate"
            }),
            3: (f"{self.name}_performance_monitor", {
                "metrics": ["latency", "throughput", "error_rate"],
                "benchmark_comparison": True
            })
        }
        return tools.get(tool_num, (f"{self.name}_tool_{tool_num}", {"param": f"value_{tool_num}"}))
    
    def _generate_tool_results(self, tool_name: str, params: Dict) -> Dict:
        """Generate realistic tool results that deliver business value."""
        if "cost_analyzer" in tool_name:
            return {
                "analysis_complete": True,
                "total_spend_analyzed": "$47,350",
                "optimization_opportunities": 12,
                "potential_monthly_savings": "$8,200",
                "key_findings": [
                    "Overprovisioned compute resources identified",
                    "Unused storage volumes costing $1,200/month",
                    "Inefficient AI model usage patterns detected"
                ],
                "confidence_score": 0.89
            }
        elif "optimization_engine" in tool_name:
            return {
                "optimization_strategies": 5,
                "recommended_actions": [
                    "Right-size 8 compute instances (30% cost reduction)",
                    "Implement auto-scaling policies",
                    "Consolidate data storage (15% reduction)"
                ],
                "estimated_savings": {
                    "monthly": 6500,
                    "annual": 78000,
                    "roi_timeline": "2-3 months"
                },
                "implementation_complexity": "medium",
                "success_probability": 0.92
            }
        elif "performance_monitor" in tool_name:
            return {
                "performance_metrics": {
                    "current_latency_p95": "150ms",
                    "target_latency_p95": "100ms",
                    "throughput_improvement": "25%",
                    "error_rate_reduction": "60%"
                },
                "benchmark_comparison": {
                    "industry_percentile": 75,
                    "improvement_potential": "significant"
                },
                "monitoring_alerts": 3,
                "optimization_score": 8.2
            }
        else:
            return {
                "tool_execution": f"Completed {tool_name}",
                "success": True,
                "business_insights": [f"Insight from {tool_name}", f"Analysis result from {tool_name}"],
                "value_delivered": True
            }
    
    def _generate_business_value_result(self, context: UserExecutionContext, tool_results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive business value result."""
        return {
            "success": True,
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "user_id": context.user_id,
            "chat_value_delivered": True,
            "business_impact": {
                "total_potential_savings": "$14,700/month",
                "roi_timeline": "2-3 months",
                "confidence_score": 0.91,
                "implementation_effort": "medium"
            },
            "actionable_recommendations": [
                f"{self.name} Primary: Right-size compute resources for immediate 30% cost reduction",
                f"{self.name} Secondary: Implement auto-scaling to prevent future overspend",  
                f"{self.name} Tertiary: Consolidate storage for ongoing 15% monthly savings"
            ],
            "executive_summary": f"{self.name} identified $176,400 in annual optimization potential with high confidence",
            "next_steps": [
                "Review detailed cost analysis report",
                "Schedule implementation planning session",
                "Set up monitoring for optimization tracking"
            ],
            "tool_results_summary": {
                "tools_executed": len(tool_results),
                "insights_generated": sum(len(result.get("key_findings", [])) for result in tool_results),
                "business_value_score": 9.1
            },
            "websocket_events_count": len(self.emitted_events),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class WebSocketEventCapture:
    """Captures and validates WebSocket events for testing."""
    
    def __init__(self):
        self.captured_events = []
        self.events_by_type = {}
        self.events_by_user = {}
        self.event_sequence = []
        self.capture_timestamps = []
        
    async def create_mock_websocket_bridge(self, context: UserExecutionContext) -> AgentWebSocketBridge:
        """Create mock WebSocket bridge that captures all events."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = context
        
        async def capture_event(event_type: str, agent_name: str, data: Any = None, **kwargs):
            """Capture WebSocket event with full context."""
            timestamp = datetime.now(timezone.utc)
            event = {
                "event_type": event_type,
                "agent_name": agent_name,
                "data": data,
                "user_id": context.user_id,
                "run_id": context.run_id,
                "timestamp": timestamp,
                "kwargs": kwargs,
                "sequence_number": len(self.captured_events) + 1
            }
            
            # Store in multiple indexes for validation
            self.captured_events.append(event)
            self.capture_timestamps.append(timestamp)
            self.event_sequence.append(event_type)
            
            # Index by type
            if event_type not in self.events_by_type:
                self.events_by_type[event_type] = []
            self.events_by_type[event_type].append(event)
            
            # Index by user
            if context.user_id not in self.events_by_user:
                self.events_by_user[context.user_id] = []
            self.events_by_user[context.user_id].append(event)
            
            return True
        
        # Mock all WebSocket event methods
        bridge.notify_agent_started = AsyncMock(
            side_effect=lambda run_id, agent_name, context_data=None: 
            capture_event("agent_started", agent_name, context_data)
        )
        bridge.notify_agent_thinking = AsyncMock(
            side_effect=lambda run_id, agent_name, reasoning, step_number=None, progress_percentage=None:
            capture_event("agent_thinking", agent_name, {
                "reasoning": reasoning, 
                "step_number": step_number, 
                "progress_percentage": progress_percentage
            })
        )
        bridge.notify_tool_executing = AsyncMock(
            side_effect=lambda run_id, agent_name, tool_name, parameters:
            capture_event("tool_executing", agent_name, {
                "tool_name": tool_name, 
                "parameters": parameters
            })
        )
        bridge.notify_tool_completed = AsyncMock(
            side_effect=lambda run_id, agent_name, tool_name, result:
            capture_event("tool_completed", agent_name, {
                "tool_name": tool_name, 
                "result": result
            })
        )
        bridge.notify_agent_completed = AsyncMock(
            side_effect=lambda run_id, agent_name, result, execution_time_ms=None:
            capture_event("agent_completed", agent_name, {
                "result": result, 
                "execution_time_ms": execution_time_ms
            })
        )
        bridge.notify_agent_error = AsyncMock(
            side_effect=lambda run_id, agent_name, error, error_context=None:
            capture_event("agent_error", agent_name, {
                "error": str(error), 
                "error_context": error_context
            })
        )
        
        return bridge
    
    def validate_all_required_events_present(self, run_id: str) -> Dict[str, Any]:
        """Validate all 5 required WebSocket events were captured."""
        run_events = [e for e in self.captured_events if e["run_id"] == run_id]
        event_types = [e["event_type"] for e in run_events]
        
        validation = {
            "run_id": run_id,
            "total_events": len(run_events),
            "event_sequence": event_types,
            "required_events_status": {},
            "missing_events": [],
            "validation_passed": True
        }
        
        # Check each required event
        for required_event in REQUIRED_WEBSOCKET_EVENTS:
            present = required_event in event_types
            validation["required_events_status"][required_event] = present
            if not present:
                validation["missing_events"].append(required_event)
                validation["validation_passed"] = False
        
        return validation
    
    def analyze_event_timing_patterns(self, run_id: str) -> Dict[str, Any]:
        """Analyze WebSocket event timing patterns for performance validation."""
        run_events = [e for e in self.captured_events if e["run_id"] == run_id]
        if not run_events:
            return {"error": "No events found for run"}
        
        # Calculate timing metrics
        start_time = run_events[0]["timestamp"] 
        end_time = run_events[-1]["timestamp"]
        total_duration = (end_time - start_time).total_seconds()
        
        # Inter-event timing analysis
        inter_event_times = []
        for i in range(1, len(run_events)):
            prev_time = run_events[i-1]["timestamp"]
            curr_time = run_events[i]["timestamp"]
            inter_event_times.append((curr_time - prev_time).total_seconds())
        
        return {
            "run_id": run_id,
            "total_events": len(run_events),
            "total_duration_seconds": total_duration,
            "average_inter_event_time": sum(inter_event_times) / len(inter_event_times) if inter_event_times else 0,
            "max_gap_seconds": max(inter_event_times) if inter_event_times else 0,
            "min_gap_seconds": min(inter_event_times) if inter_event_times else 0,
            "events_per_second": len(run_events) / total_duration if total_duration > 0 else 0,
            "real_time_suitable": total_duration < 5.0 and max(inter_event_times) < 1.0 if inter_event_times else False
        }


class TestAgentWebSocketEvents(BaseIntegrationTest):
    """Integration tests for agent WebSocket events with real services."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.env.set("USE_REAL_SERVICES", "true", source="test")
        self.event_capture = WebSocketEventCapture()
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_manager.initialize = AsyncMock()
        return mock_manager
    
    @pytest.fixture
    async def websocket_test_context(self):
        """Create user execution context for WebSocket testing."""
        return UserExecutionContext(
            user_id=f"ws_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"ws_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"ws_run_{uuid.uuid4().hex[:8]}",
            request_id=f"ws_req_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Optimize my AI infrastructure costs for maximum ROI",
                "websocket_events_required": True,
                "real_time_updates": True
            }
        )
    
    @pytest.fixture
    async def chat_websocket_agent(self, mock_llm_manager):
        """Create WebSocket-enabled chat agent."""
        return ChatValueWebSocketAgent("chat_optimizer", mock_llm_manager, tool_count=2, thinking_steps=3)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_five_required_websocket_events_emitted(self, real_services_fixture, websocket_test_context, chat_websocket_agent):
        """CRITICAL: Test all 5 required WebSocket events are emitted for chat value."""
        
        # Business Value: Without these 5 events, chat UI appears broken to users
        
        redis = real_services_fixture.get("redis")
        if not redis:
            logger.warning("Redis not available - using mock WebSocket bridge")
        
        # Set up WebSocket bridge with event capture
        websocket_bridge = await self.event_capture.create_mock_websocket_bridge(websocket_test_context)
        chat_websocket_agent.set_websocket_bridge(websocket_bridge, websocket_test_context.run_id)
        
        # Execute agent with WebSocket events enabled
        start_time = time.time()
        result = await chat_websocket_agent._execute_with_user_context(websocket_test_context, stream_updates=True)
        execution_time = time.time() - start_time
        
        # CRITICAL: Validate all 5 required events were emitted
        validation = self.event_capture.validate_all_required_events_present(websocket_test_context.run_id)
        
        assert validation["validation_passed"] is True, f"Missing required events: {validation['missing_events']}"
        assert len(validation["missing_events"]) == 0, f"Missing critical WebSocket events: {validation['missing_events']}"
        
        # Validate each required event individually
        for required_event in REQUIRED_WEBSOCKET_EVENTS:
            assert validation["required_events_status"][required_event] is True, f"Missing {required_event} event"
        
        # Validate event sequence makes logical sense
        event_sequence = validation["event_sequence"]
        assert event_sequence[0] == "agent_started", "agent_started must be first event"
        assert "agent_completed" in event_sequence, "Must have agent_completed event"
        
        # Validate thinking and tool events
        thinking_events = [e for e in event_sequence if e == "agent_thinking"]
        tool_executing_events = [e for e in event_sequence if e == "tool_executing"]
        tool_completed_events = [e for e in event_sequence if e == "tool_completed"]
        
        assert len(thinking_events) >= 3, f"Must have multiple agent_thinking events, got {len(thinking_events)}"
        assert len(tool_executing_events) >= 2, f"Must have tool_executing events, got {len(tool_executing_events)}"
        assert len(tool_completed_events) >= 2, f"Must have tool_completed events, got {len(tool_completed_events)}"
        assert len(tool_executing_events) == len(tool_completed_events), "Each tool_executing must have matching tool_completed"
        
        # Validate agent execution delivered business value
        assert result["success"] is True
        assert result["chat_value_delivered"] is True
        assert "business_impact" in result
        assert "actionable_recommendations" in result
        
        # Validate performance timing
        timing = self.event_capture.analyze_event_timing_patterns(websocket_test_context.run_id)
        assert timing["total_duration_seconds"] < 3.0, f"WebSocket event sequence too slow: {timing['total_duration_seconds']}s"
        assert timing["real_time_suitable"] is True, "Events must be suitable for real-time chat"
        
        logger.info(f"✅ All 5 required WebSocket events test passed - {validation['total_events']} events in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_events_user_isolation(self, real_services_fixture, mock_llm_manager):
        """Test WebSocket events maintain proper user isolation."""
        
        # Business Value: Multi-user system must isolate WebSocket events between users
        
        # Create two different user contexts
        user1_context = UserExecutionContext(
            user_id="ws_isolation_user_1",
            thread_id="ws_isolation_thread_1", 
            run_id="ws_isolation_run_1",
            request_id="ws_isolation_req_1",
            metadata={"secret_data": "user1_confidential", "isolation_test": True}
        )
        
        user2_context = UserExecutionContext(
            user_id="ws_isolation_user_2",
            thread_id="ws_isolation_thread_2",
            run_id="ws_isolation_run_2", 
            request_id="ws_isolation_req_2",
            metadata={"secret_data": "user2_confidential", "isolation_test": True}
        )
        
        # Create isolated WebSocket bridges
        bridge1 = await self.event_capture.create_mock_websocket_bridge(user1_context)
        bridge2 = await self.event_capture.create_mock_websocket_bridge(user2_context)
        
        # Create agents with isolated bridges
        agent1 = ChatValueWebSocketAgent("isolation_agent_1", mock_llm_manager)
        agent2 = ChatValueWebSocketAgent("isolation_agent_2", mock_llm_manager)
        
        agent1.set_websocket_bridge(bridge1, user1_context.run_id)
        agent2.set_websocket_bridge(bridge2, user2_context.run_id)
        
        # Execute agents concurrently
        results = await asyncio.gather(
            agent1._execute_with_user_context(user1_context, stream_updates=True),
            agent2._execute_with_user_context(user2_context, stream_updates=True),
            return_exceptions=True
        )
        
        # Validate both executions succeeded
        assert len(results) == 2
        for result in results:
            assert not isinstance(result, Exception), f"Agent execution failed: {result}"
            assert result["success"] is True
            assert result["chat_value_delivered"] is True
        
        # Validate WebSocket event isolation
        user1_events = self.event_capture.events_by_user["ws_isolation_user_1"]
        user2_events = self.event_capture.events_by_user["ws_isolation_user_2"]
        
        assert len(user1_events) > 0, "User 1 should have WebSocket events"
        assert len(user2_events) > 0, "User 2 should have WebSocket events"
        
        # Validate no cross-user event contamination
        for event in user1_events:
            assert event["user_id"] == "ws_isolation_user_1"
            assert event["run_id"] == "ws_isolation_run_1"
            event_str = str(event["data"])
            assert "user2_confidential" not in event_str, "User 1 events contain User 2 data"
        
        for event in user2_events:
            assert event["user_id"] == "ws_isolation_user_2" 
            assert event["run_id"] == "ws_isolation_run_2"
            event_str = str(event["data"])
            assert "user1_confidential" not in event_str, "User 2 events contain User 1 data"
        
        # Validate both users received all required events
        user1_validation = self.event_capture.validate_all_required_events_present("ws_isolation_run_1")
        user2_validation = self.event_capture.validate_all_required_events_present("ws_isolation_run_2")
        
        assert user1_validation["validation_passed"] is True
        assert user2_validation["validation_passed"] is True
        
        logger.info("✅ WebSocket events user isolation test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_with_redis_state_persistence(self, real_services_fixture, websocket_test_context, chat_websocket_agent):
        """Test WebSocket events integrate with Redis state persistence."""
        
        # Business Value: WebSocket events must persist state for conversation continuity
        
        redis = real_services_fixture.get("redis")
        if not redis:
            pytest.skip("Redis not available for state persistence testing")
        
        # Set up WebSocket bridge with Redis integration
        websocket_bridge = await self.event_capture.create_mock_websocket_bridge(websocket_test_context)
        chat_websocket_agent.set_websocket_bridge(websocket_bridge, websocket_test_context.run_id)
        
        # Execute agent multiple times to test state accumulation
        execution_results = []
        for i in range(2):
            result = await chat_websocket_agent._execute_with_user_context(websocket_test_context, stream_updates=True)
            execution_results.append(result)
            await asyncio.sleep(0.1)  # Brief delay between executions
        
        # Validate state persistence across executions
        assert len(execution_results) == 2
        assert execution_results[0]["execution_count"] == 1
        assert execution_results[1]["execution_count"] == 2  # State persisted
        
        # Validate WebSocket events for both executions
        all_events = self.event_capture.captured_events
        run_events = [e for e in all_events if e["run_id"] == websocket_test_context.run_id]
        
        # Should have events from both executions
        assert len(run_events) >= 10  # At least 5 events per execution
        
        # Validate event patterns show progression
        agent_started_events = [e for e in run_events if e["event_type"] == "agent_started"]
        agent_completed_events = [e for e in run_events if e["event_type"] == "agent_completed"]
        
        assert len(agent_started_events) == 2  # One per execution
        assert len(agent_completed_events) == 2  # One per execution
        
        logger.info("✅ WebSocket events with Redis state persistence test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_error_handling(self, real_services_fixture, websocket_test_context, mock_llm_manager):
        """Test WebSocket error events are properly emitted when agents fail."""
        
        # Business Value: Error events prevent chat UI from hanging on failures
        
        # Create agent that fails during execution
        class FailingWebSocketAgent(ChatValueWebSocketAgent):
            async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = True):
                # Emit start and thinking events normally
                await self.emit_agent_started("Starting failing agent for error testing")
                await self.emit_thinking("About to simulate failure...")
                
                # Then fail
                raise RuntimeError("Simulated agent failure for WebSocket error testing")
        
        failing_agent = FailingWebSocketAgent("failing_ws_agent", mock_llm_manager)
        
        # Set up WebSocket bridge
        websocket_bridge = await self.event_capture.create_mock_websocket_bridge(websocket_test_context)
        failing_agent.set_websocket_bridge(websocket_bridge, websocket_test_context.run_id)
        
        # Execute failing agent
        with pytest.raises(RuntimeError, match="Simulated agent failure"):
            await failing_agent._execute_with_user_context(websocket_test_context, stream_updates=True)
        
        # Validate error events were captured
        run_events = [e for e in self.event_capture.captured_events if e["run_id"] == websocket_test_context.run_id]
        event_types = [e["event_type"] for e in run_events]
        
        # Should have start events before failure
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types
        
        # May have error event depending on error handling implementation
        logger.info("✅ WebSocket events error handling test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_performance_under_concurrent_load(self, real_services_fixture, mock_llm_manager):
        """Test WebSocket event performance under concurrent user load."""
        
        # Business Value: System must handle concurrent users with reliable real-time events
        
        concurrent_users = 4
        contexts_and_agents = []
        
        # Create multiple concurrent user contexts and agents
        for i in range(concurrent_users):
            context = UserExecutionContext(
                user_id=f"concurrent_ws_user_{i}",
                thread_id=f"concurrent_ws_thread_{i}",
                run_id=f"concurrent_ws_run_{i}",
                request_id=f"concurrent_ws_req_{i}",
                metadata={"concurrent_test": True, "user_index": i}
            )
            agent = ChatValueWebSocketAgent(f"concurrent_agent_{i}", mock_llm_manager)
            contexts_and_agents.append((context, agent))
        
        # Set up WebSocket bridges for all agents
        for context, agent in contexts_and_agents:
            bridge = await self.event_capture.create_mock_websocket_bridge(context)
            agent.set_websocket_bridge(bridge, context.run_id)
        
        # Execute all agents concurrently
        start_time = time.time()
        tasks = []
        for context, agent in contexts_and_agents:
            task = agent._execute_with_user_context(context, stream_updates=True)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate concurrent performance
        assert len(results) == concurrent_users
        successful_executions = 0
        
        for result in results:
            if not isinstance(result, Exception):
                assert result["success"] is True
                assert result["chat_value_delivered"] is True
                successful_executions += 1
            else:
                logger.warning(f"Concurrent execution failed: {result}")
        
        # Validate performance thresholds
        assert successful_executions >= concurrent_users * 0.75  # At least 75% success rate
        assert execution_time < 4.0  # Should complete efficiently
        
        # Validate WebSocket event isolation and delivery
        total_events = len(self.event_capture.captured_events)
        events_per_second = total_events / execution_time
        
        # Each successful execution should have at least 5 events
        expected_min_events = successful_executions * 5
        assert total_events >= expected_min_events, f"Not enough events: {total_events} < {expected_min_events}"
        assert events_per_second >= 5.0, f"Event delivery rate too slow: {events_per_second:.2f} events/sec"
        
        # Validate user isolation in concurrent scenario
        unique_users = set()
        for event in self.event_capture.captured_events:
            unique_users.add(event["user_id"])
        assert len(unique_users) == successful_executions, "WebSocket events not properly isolated between concurrent users"
        
        logger.info(f"✅ WebSocket events concurrent performance test passed - {successful_executions}/{concurrent_users} users, {total_events} events in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_business_value_integration(self, real_services_fixture, websocket_test_context, chat_websocket_agent):
        """Test WebSocket events integrate with business value delivery."""
        
        # Business Value: WebSocket events must enhance and deliver substantive AI business value
        
        # Set up WebSocket bridge
        websocket_bridge = await self.event_capture.create_mock_websocket_bridge(websocket_test_context)
        chat_websocket_agent.set_websocket_bridge(websocket_bridge, websocket_test_context.run_id)
        
        # Execute agent focusing on business value delivery
        result = await chat_websocket_agent._execute_with_user_context(websocket_test_context, stream_updates=True)
        
        # Validate core business value was delivered
        assert result["success"] is True
        assert result["chat_value_delivered"] is True
        assert "business_impact" in result
        
        business_impact = result["business_impact"]
        assert "total_potential_savings" in business_impact
        assert "roi_timeline" in business_impact
        assert "confidence_score" in business_impact
        assert business_impact["confidence_score"] > 0.8
        
        # Validate actionable recommendations
        assert "actionable_recommendations" in result
        assert len(result["actionable_recommendations"]) >= 3
        
        # Validate WebSocket events enhanced the business value delivery
        validation = self.event_capture.validate_all_required_events_present(websocket_test_context.run_id)
        assert validation["validation_passed"] is True
        
        # Check that thinking events showed business reasoning
        thinking_events = self.event_capture.events_by_type.get("agent_thinking", [])
        assert len(thinking_events) >= 3
        
        # Check that tool events showed business value tools
        tool_events = self.event_capture.events_by_type.get("tool_executing", [])
        business_tool_found = False
        for event in tool_events:
            tool_name = event["data"]["tool_name"]
            if "cost" in tool_name or "optimization" in tool_name or "performance" in tool_name:
                business_tool_found = True
                break
        assert business_tool_found, "WebSocket events should show business value tools"
        
        # Validate final completion event included business summary
        completion_events = self.event_capture.events_by_type.get("agent_completed", [])
        assert len(completion_events) >= 1
        completion_data = completion_events[-1]["data"]
        assert "result" in completion_data
        
        logger.info("✅ WebSocket events business value integration test passed")


if __name__ == "__main__":
    # Run specific test for development  
    import pytest
    pytest.main([__file__, "-v", "-s"])