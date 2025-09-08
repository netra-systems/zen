"""Integration Tests: Agent WebSocket Events - MISSION CRITICAL for Chat Value

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure real-time chat notifications deliver substantive AI value
- Value Impact: WebSocket events ARE the user experience - without them chat is broken
- Strategic Impact: Core infrastructure for AI agent transparency and user engagement

This test suite validates the 5 MANDATORY WebSocket events for chat value:
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI working on solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights) 
5. agent_completed - User knows when valuable response is ready

CRITICAL: These events enable substantive chat interactions - they serve the business 
goal of delivering AI value to users. WITHOUT proper WebSocket events, the chat UI
appears broken and users cannot see AI progress.

Tests validate:
- Correct event sequence and timing
- Event data integrity and user isolation
- Multi-agent workflow event coordination
- WebSocket bridge integration patterns
- Error event handling and recovery
- Performance under concurrent load
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)

# MISSION CRITICAL: The 5 required WebSocket events for chat value
REQUIRED_WEBSOCKET_EVENTS = [
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
]


class ChatValueAgent(BaseAgent):
    """Agent that demonstrates the 5 critical WebSocket events for chat value."""
    
    def __init__(self, name: str, llm_manager: LLMManager, thinking_steps: int = 2, tool_count: int = 2):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Chat value {name} agent")
        self.thinking_steps = thinking_steps
        self.tool_count = tool_count
        self.execution_count = 0
        self.websocket_bridge = None
        self._run_id = None
        self.emitted_events = []
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for event emission."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent with all 5 critical WebSocket events."""
        self.execution_count += 1
        
        if not stream_updates or not self.websocket_bridge:
            logger.warning(f"⚠️ CRITICAL: {self.name} agent has no WebSocket bridge - chat value will be broken!")
            return {"success": False, "error": "No WebSocket bridge for chat updates"}
        
        # CRITICAL EVENT 1: agent_started - User sees agent began processing
        await self.websocket_bridge.notify_agent_started(
            run_id, self.name, {"context": "starting_analysis", "user_request": getattr(state, 'user_request', {})}
        )
        self.emitted_events.append("agent_started")
        
        # CRITICAL EVENT 2: agent_thinking - Show AI reasoning process
        for step in range(self.thinking_steps):
            reasoning = self._generate_thinking_content(step + 1)
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, reasoning, step_number=step + 1, 
                progress_percentage=int((step + 1) / self.thinking_steps * 50)  # First half of progress
            )
            self.emitted_events.append("agent_thinking")
            await asyncio.sleep(0.05)  # Realistic thinking delay
            
        # CRITICAL EVENTS 3 & 4: tool_executing and tool_completed - Show problem-solving
        for tool_num in range(self.tool_count):
            tool_name, tool_params = self._generate_tool_execution(tool_num + 1)
            
            # EVENT 3: tool_executing - Show tool is running
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, tool_name, tool_params
            )
            self.emitted_events.append("tool_executing")
            
            # Simulate tool processing
            await asyncio.sleep(0.08)
            
            # EVENT 4: tool_completed - Show tool results (actionable insights)
            tool_result = self._generate_tool_results(tool_name, tool_params)
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, tool_name, tool_result
            )
            self.emitted_events.append("tool_completed")
            
            # Update thinking after tool completion
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, f"Analyzing results from {tool_name}...", 
                step_number=self.thinking_steps + tool_num + 1,
                progress_percentage=int(50 + ((tool_num + 1) / self.tool_count * 40))  # Progress continues
            )
            self.emitted_events.append("agent_thinking")
            
        # Final analysis thinking
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Synthesizing final recommendations...", 
            step_number=self.thinking_steps + self.tool_count + 1,
            progress_percentage=95
        )
        self.emitted_events.append("agent_thinking")
        
        # Generate valuable agent result
        agent_result = self._generate_agent_output(state)
        
        # CRITICAL EVENT 5: agent_completed - User knows valuable response is ready
        await self.websocket_bridge.notify_agent_completed(
            run_id, self.name, agent_result, execution_time_ms=200
        )
        self.emitted_events.append("agent_completed")
        
        return agent_result
        
    def _generate_thinking_content(self, step: int) -> str:
        """Generate realistic thinking content for chat value."""
        thinking_patterns = {
            1: f"Analyzing {self.name} requirements and identifying key optimization opportunities...",
            2: f"Evaluating data patterns and determining best approach for {self.name} analysis...",
            3: f"Processing complex {self.name} algorithms to generate actionable insights...",
            4: f"Synthesizing {self.name} findings and preparing comprehensive recommendations..."
        }
        return thinking_patterns.get(step, f"Continuing {self.name} analysis (step {step})...")
        
    def _generate_tool_execution(self, tool_num: int) -> Tuple[str, Dict]:
        """Generate tool execution for demonstration."""
        tools = {
            1: (f"{self.name}_data_analyzer", {"data_source": "user_metrics", "analysis_type": "comprehensive"}),
            2: (f"{self.name}_optimizer", {"optimization_target": "cost_performance", "strategy": "advanced"}),
            3: (f"{self.name}_forecaster", {"forecast_horizon": "3_months", "confidence_interval": 95}),
            4: (f"{self.name}_reporter", {"format": "executive_summary", "include_charts": True})
        }
        return tools.get(tool_num, (f"{self.name}_tool_{tool_num}", {"param": f"value_{tool_num}"}))
        
    def _generate_tool_results(self, tool_name: str, params: Dict) -> Dict:
        """Generate realistic tool results."""
        if "analyzer" in tool_name:
            return {
                "analysis_complete": True,
                "insights_found": 5,
                "data_quality": "high",
                "key_findings": ["Pattern A identified", "Optimization opportunity B", "Risk factor C noted"]
            }
        elif "optimizer" in tool_name:
            return {
                "optimization_strategies": 3,
                "potential_savings": {"min": 12000, "max": 18000, "confidence": 0.85},
                "implementation_effort": "medium",
                "roi_timeline": "2-3 months"
            }
        elif "forecaster" in tool_name:
            return {
                "forecast_generated": True,
                "projected_metrics": {"growth": 15, "efficiency": 22, "cost_reduction": 12},
                "confidence_score": 0.89,
                "risk_factors": ["Market volatility", "Implementation delays"]
            }
        else:
            return {"tool_result": f"Completed {tool_name}", "success": True, "insights": ["Generic insight 1", "Generic insight 2"]}
            
    def _generate_agent_output(self, state: DeepAgentState) -> Dict[str, Any]:
        """Generate comprehensive agent output with business value."""
        return {
            "success": True,
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "business_value": {
                "primary_recommendations": [
                    f"{self.name} recommendation 1: Implement advanced optimization",
                    f"{self.name} recommendation 2: Enhance monitoring capabilities",
                    f"{self.name} recommendation 3: Establish feedback loops"
                ],
                "estimated_impact": {
                    "cost_savings": {"monthly": 8500, "annual": 102000},
                    "efficiency_gains": {"percentage": 25, "metric": "processing_time"},
                    "quality_improvements": {"accuracy": 15, "user_satisfaction": 22}
                },
                "implementation_plan": {
                    "phase1": "Quick wins (Week 1-2)",
                    "phase2": "Core improvements (Week 3-6)", 
                    "phase3": "Advanced optimization (Week 7-12)"
                }
            },
            "technical_analysis": {
                "data_processed": "2.3GB",
                "algorithms_applied": ["Machine Learning Model A", "Statistical Analysis B", "Pattern Recognition C"],
                "confidence_metrics": {"overall": 0.87, "recommendation_1": 0.92, "recommendation_2": 0.85}
            },
            "user_context": {
                "user_id": getattr(state, 'user_id', None),
                "request_processed": getattr(state, 'user_request', {}),
                "personalized_insights": f"Custom analysis for {self.name} based on user data"
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chat_value_delivered": True
        }


class WebSocketEventTracker:
    """Comprehensive WebSocket event tracking for validation."""
    
    def __init__(self):
        self.all_events = []
        self.events_by_user = {}
        self.events_by_run = {}
        self.events_by_type = {}
        self.event_sequences = {}
        
    async def create_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge with comprehensive event tracking."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.tracked_events = []
        
        async def track_event(event_type: str, data: Dict, **kwargs):
            """Track WebSocket event with full context."""
            timestamp = datetime.now(timezone.utc)
            event = {
                "event_type": event_type,
                "data": data,
                "user_id": user_context.user_id,
                "run_id": user_context.run_id,
                "timestamp": timestamp,
                "kwargs": kwargs,
                "sequence_number": len(self.all_events) + 1
            }
            
            # Store in multiple indexes for easy querying
            bridge.tracked_events.append(event)
            self.all_events.append(event)
            
            # Index by user
            if user_context.user_id not in self.events_by_user:
                self.events_by_user[user_context.user_id] = []
            self.events_by_user[user_context.user_id].append(event)
            
            # Index by run
            if user_context.run_id not in self.events_by_run:
                self.events_by_run[user_context.run_id] = []
            self.events_by_run[user_context.run_id].append(event)
            
            # Index by type
            if event_type not in self.events_by_type:
                self.events_by_type[event_type] = []
            self.events_by_type[event_type].append(event)
            
            # Track sequence for this run
            if user_context.run_id not in self.event_sequences:
                self.event_sequences[user_context.run_id] = []
            self.event_sequences[user_context.run_id].append(event_type)
            
            return True
            
        # Mock all WebSocket methods with tracking
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_event("agent_started", {"agent_name": agent_name, "context": context or {}}))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, reasoning, step_number=None, progress_percentage=None:
            track_event("agent_thinking", {"agent_name": agent_name, "reasoning": reasoning, "step_number": step_number, "progress_percentage": progress_percentage}))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, parameters:
            track_event("tool_executing", {"agent_name": agent_name, "tool_name": tool_name, "parameters": parameters}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            track_event("tool_completed", {"agent_name": agent_name, "tool_name": tool_name, "result": result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, execution_time_ms:
            track_event("agent_completed", {"agent_name": agent_name, "result": result, "execution_time_ms": execution_time_ms}))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, error_context=None:
            track_event("agent_error", {"agent_name": agent_name, "error": str(error), "error_context": error_context}))
        
        return bridge
        
    def validate_required_events(self, run_id: str) -> Dict[str, Any]:
        """Validate that all 5 required events were emitted for a run."""
        run_events = self.events_by_run.get(run_id, [])
        event_types = [event["event_type"] for event in run_events]
        
        validation_result = {
            "run_id": run_id,
            "total_events": len(run_events),
            "required_events_present": {},
            "missing_events": [],
            "extra_events": [],
            "event_sequence": event_types,
            "validation_passed": True
        }
        
        # Check for required events
        for required_event in REQUIRED_WEBSOCKET_EVENTS:
            present = required_event in event_types
            validation_result["required_events_present"][required_event] = present
            if not present:
                validation_result["missing_events"].append(required_event)
                validation_result["validation_passed"] = False
                
        # Identify extra events (beyond required)
        for event_type in set(event_types):
            if event_type not in REQUIRED_WEBSOCKET_EVENTS:
                validation_result["extra_events"].append(event_type)
                
        return validation_result
        
    def get_event_timing_analysis(self, run_id: str) -> Dict[str, Any]:
        """Analyze event timing and sequence for a run."""
        run_events = self.events_by_run.get(run_id, [])
        if not run_events:
            return {"error": "No events found for run"}
            
        start_time = run_events[0]["timestamp"]
        end_time = run_events[-1]["timestamp"]
        total_duration = (end_time - start_time).total_seconds()
        
        # Calculate inter-event timing
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
            "events_per_second": len(run_events) / total_duration if total_duration > 0 else 0
        }


class TestAgentWebSocketEventsIntegration(BaseIntegrationTest):
    """Integration tests for agent WebSocket events - MISSION CRITICAL for chat value."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        self.event_tracker = WebSocketEventTracker()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_manager.initialize = AsyncMock()
        return mock_manager
        
    @pytest.fixture
    async def chat_user_context(self):
        """Create user context for chat testing."""
        return UserExecutionContext(
            user_id=f"chat_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"chat_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"chat_run_{uuid.uuid4().hex[:8]}",
            request_id=f"chat_req_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Help me optimize my AI costs and improve performance", 
                "chat_session": True,
                "real_time_updates": True
            }
        )
        
    @pytest.fixture
    async def chat_value_agents(self, mock_llm_manager):
        """Create agents that demonstrate chat value through WebSocket events."""
        return {
            "triage": ChatValueAgent("triage", mock_llm_manager, thinking_steps=2, tool_count=1),
            "data_helper": ChatValueAgent("data_helper", mock_llm_manager, thinking_steps=3, tool_count=2),
            "optimization": ChatValueAgent("optimization", mock_llm_manager, thinking_steps=2, tool_count=2),
            "reporting": ChatValueAgent("reporting", mock_llm_manager, thinking_steps=1, tool_count=1)
        }
        
    @pytest.fixture
    async def chat_registry(self, chat_value_agents):
        """Create registry with chat value agents."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: chat_value_agents.get(name)
        registry.get_async = AsyncMock(side_effect=lambda name, context=None: chat_value_agents.get(name))
        registry.list_keys = lambda: list(chat_value_agents.keys())
        return registry

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_five_required_websocket_events_emitted(
        self, chat_user_context, chat_registry, chat_value_agents, mock_llm_manager
    ):
        """CRITICAL: Test all 5 required WebSocket events are emitted for chat value."""
        
        # Business Value: Without these 5 events, chat UI appears broken to users
        
        websocket_bridge = await self.event_tracker.create_bridge(chat_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=chat_registry,
            websocket_bridge=websocket_bridge,
            user_context=chat_user_context
        )
        
        # Execute triage agent (comprehensive event demonstration)
        context = AgentExecutionContext(
            user_id=chat_user_context.user_id,
            thread_id=chat_user_context.thread_id,
            run_id=chat_user_context.run_id,
            request_id=chat_user_context.request_id,
            agent_name="triage",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        state = DeepAgentState(
            user_request={"message": "Optimize my $45k monthly AI costs"},
            user_id=chat_user_context.user_id,
            chat_thread_id=chat_user_context.thread_id,
            run_id=chat_user_context.run_id,
            agent_input={"optimization_request": True}
        )
        
        # Execute with WebSocket events enabled
        start_time = time.time()
        result = await engine.execute_agent(context, chat_user_context)
        execution_time = time.time() - start_time
        
        # CRITICAL: Validate all 5 required events were emitted
        validation = self.event_tracker.validate_required_events(chat_user_context.run_id)
        
        assert validation["validation_passed"] is True, f"Missing required events: {validation['missing_events']}"
        assert len(validation["missing_events"]) == 0, f"Missing critical events: {validation['missing_events']}"
        
        # Validate each required event
        for required_event in REQUIRED_WEBSOCKET_EVENTS:
            assert validation["required_events_present"][required_event] is True, f"Missing {required_event} event"
            
        # Validate event sequence makes sense
        event_sequence = validation["event_sequence"]
        
        # agent_started should be first
        assert event_sequence[0] == "agent_started", "agent_started must be first event"
        
        # agent_completed should be last (excluding errors)
        completed_events = [e for e in event_sequence if e == "agent_completed"]
        assert len(completed_events) >= 1, "Must have agent_completed event"
        
        # Must have thinking events
        thinking_events = [e for e in event_sequence if e == "agent_thinking"]
        assert len(thinking_events) >= 2, "Must have multiple agent_thinking events"
        
        # Must have tool events
        tool_executing = [e for e in event_sequence if e == "tool_executing"]
        tool_completed = [e for e in event_sequence if e == "tool_completed"]
        assert len(tool_executing) >= 1, "Must have tool_executing events"
        assert len(tool_completed) >= 1, "Must have tool_completed events"
        assert len(tool_executing) == len(tool_completed), "Each tool_executing must have matching tool_completed"
        
        # Validate agent execution succeeded
        assert result.success is True
        assert result.agent_name == "triage"
        
        # Validate timing performance
        timing = self.event_tracker.get_event_timing_analysis(chat_user_context.run_id)
        assert timing["total_duration_seconds"] < 2.0, "Event sequence should complete quickly"
        assert timing["events_per_second"] >= 2, "Should have reasonable event frequency"
        
        logger.info(f"✅ All 5 required WebSocket events test passed - {validation['total_events']} events in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_data_integrity_and_user_isolation(
        self, chat_registry, chat_value_agents, mock_llm_manager
    ):
        """Test WebSocket events maintain data integrity and user isolation."""
        
        # Business Value: User isolation prevents data leakage in chat
        
        # Create two different users
        user1_context = UserExecutionContext(
            user_id="chat_user_1_isolation",
            thread_id="chat_thread_1",
            run_id="chat_run_1",
            request_id="chat_req_1",
            metadata={"secret_data": "user_1_confidential", "user_request": "User 1 optimization"}
        )
        
        user2_context = UserExecutionContext(
            user_id="chat_user_2_isolation", 
            thread_id="chat_thread_2",
            run_id="chat_run_2",
            request_id="chat_req_2",
            metadata={"secret_data": "user_2_confidential", "user_request": "User 2 analysis"}
        )
        
        # Create isolated WebSocket bridges
        bridge1 = await self.event_tracker.create_bridge(user1_context)
        bridge2 = await self.event_tracker.create_bridge(user2_context)
        
        # Create isolated execution engines
        engine1 = ExecutionEngine._init_from_factory(
            registry=chat_registry,
            websocket_bridge=bridge1,
            user_context=user1_context
        )
        
        engine2 = ExecutionEngine._init_from_factory(
            registry=chat_registry,
            websocket_bridge=bridge2,
            user_context=user2_context
        )
        
        # Execute agents for both users concurrently
        async def execute_for_user(user_context, engine, agent_name):
            context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name=agent_name,
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            state = DeepAgentState(
                user_request=user_context.metadata.get("user_request", {}),
                user_id=user_context.user_id,
                chat_thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                agent_input={"user_specific": user_context.metadata.get("secret_data")}
            )
            
            return await engine.execute_agent(context, user_context)
            
        # Execute concurrently
        results = await asyncio.gather(
            execute_for_user(user1_context, engine1, "data_helper"),
            execute_for_user(user2_context, engine2, "optimization"),
            return_exceptions=True
        )
        
        # Validate both succeeded
        assert len(results) == 2
        for result in results:
            assert not isinstance(result, Exception)
            assert result.success is True
            
        # Validate event isolation
        user1_events = self.event_tracker.events_by_user["chat_user_1_isolation"]
        user2_events = self.event_tracker.events_by_user["chat_user_2_isolation"]
        
        assert len(user1_events) > 0
        assert len(user2_events) > 0
        
        # Validate no cross-user contamination
        for event in user1_events:
            assert event["user_id"] == "chat_user_1_isolation"
            assert event["run_id"] == "chat_run_1"
            # Data should not contain user 2's secrets
            event_str = str(event["data"])
            assert "user_2_confidential" not in event_str
            
        for event in user2_events:
            assert event["user_id"] == "chat_user_2_isolation"
            assert event["run_id"] == "chat_run_2"
            # Data should not contain user 1's secrets
            event_str = str(event["data"])
            assert "user_1_confidential" not in event_str
            
        # Validate both users got required events
        user1_validation = self.event_tracker.validate_required_events("chat_run_1")
        user2_validation = self.event_tracker.validate_required_events("chat_run_2")
        
        assert user1_validation["validation_passed"] is True
        assert user2_validation["validation_passed"] is True
        
        logger.info("✅ WebSocket event data integrity and user isolation test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_agent_workflow_websocket_coordination(
        self, chat_user_context, chat_registry, chat_value_agents, mock_llm_manager
    ):
        """Test WebSocket events coordinate properly across multi-agent workflows."""
        
        # Business Value: Multi-agent workflows must show coordinated progress in chat
        
        websocket_bridge = await self.event_tracker.create_bridge(chat_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=chat_registry,
            websocket_bridge=websocket_bridge,
            user_context=chat_user_context
        )
        
        # Execute multi-agent workflow: triage → data_helper → optimization
        workflow_agents = ["triage", "data_helper", "optimization"]
        workflow_results = []
        
        # Shared state for workflow
        workflow_state = DeepAgentState(
            user_request={"message": "Complete workflow with coordinated events"},
            user_id=chat_user_context.user_id,
            chat_thread_id=chat_user_context.thread_id,
            run_id=chat_user_context.run_id,
            agent_input={"workflow": "multi_agent_coordination"}
        )
        
        # Execute workflow sequentially with event coordination
        for i, agent_name in enumerate(workflow_agents):
            context = AgentExecutionContext(
                user_id=chat_user_context.user_id,
                thread_id=chat_user_context.thread_id,
                run_id=f"{chat_user_context.run_id}_{agent_name}",  # Unique run per agent
                request_id=f"{chat_user_context.request_id}_{agent_name}",
                agent_name=agent_name,
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=i + 1
            )
            
            result = await engine.execute_agent(context, chat_user_context)
            workflow_results.append(result)
            
            # Store result in shared state for next agent
            if not workflow_state.metadata:
                workflow_state.metadata = {}
            workflow_state.metadata[f"{agent_name}_result"] = result.data
            
        # Validate workflow execution
        assert len(workflow_results) == 3
        for result in workflow_results:
            assert result.success is True
            
        # Validate WebSocket event coordination across workflow
        all_workflow_events = []
        for agent_name in workflow_agents:
            run_id = f"{chat_user_context.run_id}_{agent_name}"
            agent_events = self.event_tracker.events_by_run.get(run_id, [])
            all_workflow_events.extend(agent_events)
            
            # Each agent should have complete event sequence
            validation = self.event_tracker.validate_required_events(run_id)
            assert validation["validation_passed"] is True, f"Agent {agent_name} missing events: {validation['missing_events']}"
            
        # Validate workflow progression in events
        assert len(all_workflow_events) > 15  # Should have many events across 3 agents
        
        # Validate agent execution order through events
        started_events = [e for e in all_workflow_events if e["event_type"] == "agent_started"]
        assert len(started_events) == 3
        
        # Events should show proper workflow progression
        started_agents = [e["data"]["agent_name"] for e in started_events]
        assert started_agents == workflow_agents  # Should maintain order
        
        # Validate timing coordination
        workflow_start = min(e["timestamp"] for e in all_workflow_events)
        workflow_end = max(e["timestamp"] for e in all_workflow_events)
        workflow_duration = (workflow_end - workflow_start).total_seconds()
        
        assert workflow_duration < 5.0  # Should complete efficiently
        assert workflow_duration > 0.5  # Should take reasonable time for 3 agents
        
        logger.info(f"✅ Multi-agent workflow WebSocket coordination test passed - {len(all_workflow_events)} events")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_event_handling(
        self, chat_user_context, mock_llm_manager
    ):
        """Test WebSocket error events are properly emitted when agents fail."""
        
        # Business Value: Error events prevent chat UI from hanging on failures
        
        # Create failing agent
        class FailingChatAgent(BaseAgent):
            def __init__(self, llm_manager):
                super().__init__(llm_manager, "failing_agent", "Failing agent for error testing")
                self.websocket_bridge = None
                
            def set_websocket_bridge(self, bridge, run_id):
                self.websocket_bridge = bridge
                
            async def execute(self, state, run_id, stream_updates=True):
                if stream_updates and self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_started(run_id, "failing_agent")
                    await self.websocket_bridge.notify_agent_thinking(run_id, "failing_agent", "About to fail...")
                    
                # Simulate failure
                raise RuntimeError("Simulated agent failure for testing")
        
        failing_agent = FailingChatAgent(mock_llm_manager)
        
        # Create registry with failing agent
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: failing_agent if name == "failing_agent" else None
        registry.get_async = AsyncMock(return_value=failing_agent)
        
        websocket_bridge = await self.event_tracker.create_bridge(chat_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=chat_user_context
        )
        
        # Execute failing agent
        context = AgentExecutionContext(
            user_id=chat_user_context.user_id,
            thread_id=chat_user_context.thread_id,
            run_id=chat_user_context.run_id,
            request_id=chat_user_context.request_id,
            agent_name="failing_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        state = DeepAgentState(
            user_request={"message": "Test error handling"},
            user_id=chat_user_context.user_id,
            chat_thread_id=chat_user_context.thread_id,
            run_id=chat_user_context.run_id,
            agent_input={"test": "error_handling"}
        )
        
        # Execute (should fail gracefully with events)
        result = await engine.execute_agent(context, chat_user_context)
        
        # Validate failure was handled
        assert result.success is False
        assert "failure" in result.error.lower()
        
        # Validate error events were emitted
        run_events = self.event_tracker.events_by_run[chat_user_context.run_id]
        event_types = [e["event_type"] for e in run_events]
        
        # Should have start events
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types  
        
        # Should have error event
        assert "agent_error" in event_types
        
        # Validate error event content
        error_events = [e for e in run_events if e["event_type"] == "agent_error"]
        assert len(error_events) >= 1
        
        error_event = error_events[0]
        assert error_event["data"]["agent_name"] == "failing_agent"
        assert "failure" in error_event["data"]["error"].lower()
        
        logger.info("✅ WebSocket error event handling test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_performance_under_concurrent_load(
        self, chat_registry, chat_value_agents, mock_llm_manager
    ):
        """Test WebSocket event system performance under concurrent agent load."""
        
        # Business Value: System must handle multiple concurrent users with reliable events
        
        # Create multiple concurrent users
        concurrent_users = 5
        user_contexts = []
        websocket_bridges = []
        execution_engines = []
        
        for i in range(concurrent_users):
            context = UserExecutionContext(
                user_id=f"concurrent_chat_user_{i}",
                thread_id=f"concurrent_chat_thread_{i}",
                run_id=f"concurrent_chat_run_{i}",
                request_id=f"concurrent_chat_req_{i}",
                metadata={"user_index": i, "concurrent_test": True}
            )
            user_contexts.append(context)
            
            bridge = await self.event_tracker.create_bridge(context)
            websocket_bridges.append(bridge)
            
            engine = ExecutionEngine._init_from_factory(
                registry=chat_registry,
                websocket_bridge=bridge,
                user_context=context
            )
            execution_engines.append(engine)
            
        # Define concurrent execution task
        async def execute_concurrent_agent(user_index, context, engine):
            """Execute agent with full WebSocket events."""
            exec_context = AgentExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                request_id=context.request_id,
                agent_name="data_helper",  # Use comprehensive agent
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            state = DeepAgentState(
                user_request={"message": f"Concurrent user {user_index} request"},
                user_id=context.user_id,
                chat_thread_id=context.thread_id,
                run_id=context.run_id,
                agent_input={"concurrent_index": user_index}
            )
            
            start_time = time.time()
            result = await engine.execute_agent(exec_context, context)
            execution_time = time.time() - start_time
            
            return {
                "user_index": user_index,
                "user_id": context.user_id,
                "result": result,
                "execution_time": execution_time
            }
            
        # Execute all users concurrently
        start_time = time.time()
        tasks = []
        for i, (context, engine) in enumerate(zip(user_contexts, execution_engines)):
            task = execute_concurrent_agent(i, context, engine)
            tasks.append(task)
            
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate concurrent performance
        assert len(concurrent_results) == concurrent_users
        assert total_time < 3.0  # Should handle 5 users quickly
        
        # Validate all executions succeeded
        for result in concurrent_results:
            assert not isinstance(result, Exception), f"Concurrent execution failed: {result}"
            assert result["result"].success is True
            assert result["execution_time"] < 2.0  # Each user should complete quickly
            
        # Validate WebSocket event isolation
        for i, context in enumerate(user_contexts):
            user_events = self.event_tracker.events_by_user[context.user_id]
            assert len(user_events) > 0
            
            # Each user should have all required events
            validation = self.event_tracker.validate_required_events(context.run_id)
            assert validation["validation_passed"] is True, f"User {i} missing events: {validation['missing_events']}"
            
            # Events should only be for this user
            for event in user_events:
                assert event["user_id"] == context.user_id
                assert event["run_id"] == context.run_id
                
        # Validate overall event performance
        total_events = len(self.event_tracker.all_events)
        events_per_second = total_events / total_time
        
        assert total_events >= concurrent_users * 5  # At least 5 events per user
        assert events_per_second >= 10  # Reasonable event throughput
        
        logger.info(f"✅ WebSocket performance under concurrent load test passed - {concurrent_users} users, {total_events} events in {total_time:.3f}s")


if __name__ == "__main__":
    # Run specific test for development
    pytest.main([__file__, "-v", "-s"])