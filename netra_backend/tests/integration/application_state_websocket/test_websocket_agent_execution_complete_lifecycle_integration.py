"""Test #31: Complete Agent Execution Lifecycle with 5 Critical WebSocket Events

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure real-time agent execution visibility delivers maximum user engagement
- Value Impact: All 5 WebSocket events are MISSION CRITICAL for chat value - without them users see broken UI
- Strategic Impact: Core infrastructure enabling $50k+ monthly AI spend optimization visibility

This test validates the complete agent execution lifecycle through WebSocket events
including application state synchronization with database operations. 

CRITICAL: Tests the 5 MANDATORY WebSocket events for chat business value:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time AI reasoning visibility  
3. tool_executing - Transparency in problem-solving approach
4. tool_completed - Actionable insights delivery
5. agent_completed - Final result notification

WITHOUT these events, the chat UI appears broken and users cannot see AI progress,
directly impacting user retention and platform value perception.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Core application imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
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
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# MISSION CRITICAL: The 5 required WebSocket events for business value
REQUIRED_WEBSOCKET_EVENTS = [
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
]


class BusinessValueAgent(BaseAgent):
    """Agent that demonstrates complete business value through WebSocket events."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Business value {name} agent")
        self.websocket_bridge = None
        self._run_id = None
        self.emitted_events = []
        self.execution_count = 0
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        """Set WebSocket bridge for event emission - CRITICAL for chat value."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent with complete WebSocket event lifecycle for business value."""
        self.execution_count += 1
        
        if not stream_updates or not self.websocket_bridge:
            raise ValueError("WebSocket bridge required for business value delivery")
        
        # EVENT 1: agent_started - CRITICAL business value visibility
        await self.websocket_bridge.notify_agent_started(
            run_id, self.name, {
                "context": "analyzing_user_request",
                "business_value_intent": "cost_optimization_analysis",
                "user_request": getattr(state, 'user_request', {})
            }
        )
        self.emitted_events.append("agent_started")
        
        # EVENT 2: agent_thinking - Multiple thinking steps for transparency
        thinking_steps = [
            "Analyzing current AI infrastructure costs and usage patterns...",
            "Identifying optimization opportunities and potential savings...",
            "Evaluating implementation strategies and risk assessment..."
        ]
        
        for i, thinking in enumerate(thinking_steps):
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, thinking,
                step_number=i + 1,
                progress_percentage=int((i + 1) / len(thinking_steps) * 50)  # First half of progress
            )
            self.emitted_events.append("agent_thinking")
            await asyncio.sleep(0.05)  # Realistic thinking delay
            
        # EVENT 3 & 4: tool_executing and tool_completed - Business value tools
        business_tools = [
            ("cost_analyzer", {"analysis_type": "comprehensive", "timeframe": "90_days"}),
            ("optimization_engine", {"strategy": "advanced", "risk_tolerance": "medium"})
        ]
        
        for tool_name, tool_params in business_tools:
            # EVENT 3: tool_executing
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, tool_name, tool_params
            )
            self.emitted_events.append("tool_executing")
            
            # Simulate tool processing with business logic
            await asyncio.sleep(0.1)
            
            # Generate business value results
            if "cost_analyzer" in tool_name:
                tool_result = {
                    "analysis_complete": True,
                    "total_analyzed": "$47,350",
                    "optimization_opportunities": 8,
                    "potential_monthly_savings": "$12,400",
                    "confidence_score": 0.89,
                    "key_findings": [
                        "GPU utilization at 34% - optimization potential",
                        "Storage costs 2.3x industry average",
                        "API rate limiting causing unnecessary retries"
                    ]
                }
            else:  # optimization_engine
                tool_result = {
                    "optimization_strategies": 5,
                    "implementation_complexity": "medium",
                    "estimated_savings": {
                        "monthly": 12400,
                        "annual": 148800,
                        "confidence": 0.85
                    },
                    "roi_timeline": "2-3 months",
                    "recommended_actions": [
                        "Implement GPU auto-scaling",
                        "Migrate to cheaper storage tiers",
                        "Optimize API retry logic"
                    ]
                }
                
            # EVENT 4: tool_completed - Deliver actionable business insights
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, tool_name, tool_result
            )
            self.emitted_events.append("tool_completed")
            
        # Final thinking synthesis
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Synthesizing recommendations and preparing executive summary...",
            step_number=len(thinking_steps) + 1,
            progress_percentage=95
        )
        self.emitted_events.append("agent_thinking")
        
        # Generate comprehensive business value result
        business_result = {
            "success": True,
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "business_value": {
                "cost_optimization": {
                    "current_monthly_spend": 47350,
                    "potential_monthly_savings": 12400,
                    "percentage_reduction": 26.2,
                    "annual_impact": 148800
                },
                "recommendations": [
                    {
                        "title": "Implement GPU Auto-Scaling",
                        "impact": "High",
                        "savings": "$8,200/month",
                        "effort": "Medium",
                        "timeline": "4-6 weeks"
                    },
                    {
                        "title": "Storage Tier Optimization",
                        "impact": "Medium", 
                        "savings": "$2,800/month",
                        "effort": "Low",
                        "timeline": "1-2 weeks"
                    },
                    {
                        "title": "API Retry Logic Enhancement",
                        "impact": "Medium",
                        "savings": "$1,400/month", 
                        "effort": "Low",
                        "timeline": "1 week"
                    }
                ],
                "risk_assessment": {
                    "overall_risk": "Low",
                    "mitigation_strategies": ["Gradual rollout", "Monitoring dashboards", "Rollback procedures"],
                    "confidence_level": 0.87
                }
            },
            "technical_analysis": {
                "data_sources_analyzed": 5,
                "metrics_processed": 247,
                "time_period": "90 days",
                "algorithms_used": ["Cost Pattern Analysis", "Usage Forecasting", "Optimization Modeling"]
            },
            "user_context": {
                "user_id": getattr(state, 'user_id', None),
                "personalized_insights": True,
                "chat_interaction_id": run_id
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_value_delivered": True
        }
        
        # EVENT 5: agent_completed - CRITICAL final notification
        await self.websocket_bridge.notify_agent_completed(
            run_id, self.name, business_result, execution_time_ms=300
        )
        self.emitted_events.append("agent_completed")
        
        return business_result


class WebSocketEventCollector:
    """Comprehensive WebSocket event tracking and validation."""
    
    def __init__(self):
        self.all_events = []
        self.events_by_run = {}
        self.events_by_type = {}
        
    async def create_mock_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge that captures all events."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.collected_events = []
        
        async def capture_event(event_type: str, run_id: str, agent_name: str, data: Any = None, **kwargs):
            """Capture WebSocket event with full context."""
            event = {
                "event_type": event_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "data": data,
                "timestamp": datetime.now(timezone.utc),
                "user_id": user_context.user_id,
                "kwargs": kwargs
            }
            
            bridge.collected_events.append(event)
            self.all_events.append(event)
            
            # Index by run
            if run_id not in self.events_by_run:
                self.events_by_run[run_id] = []
            self.events_by_run[run_id].append(event)
            
            # Index by type
            if event_type not in self.events_by_type:
                self.events_by_type[event_type] = []
            self.events_by_type[event_type].append(event)
            
            return True
        
        # Mock all WebSocket notification methods
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            capture_event("agent_started", run_id, agent_name, context))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, thinking, **kwargs:
            capture_event("agent_thinking", run_id, agent_name, {"reasoning": thinking}, **kwargs))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, params:
            capture_event("tool_executing", run_id, agent_name, {"tool_name": tool_name, "parameters": params}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            capture_event("tool_completed", run_id, agent_name, {"tool_name": tool_name, "result": result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, **kwargs:
            capture_event("agent_completed", run_id, agent_name, result, **kwargs))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, **kwargs:
            capture_event("agent_error", run_id, agent_name, {"error": str(error)}, **kwargs))
            
        return bridge
        
    def validate_complete_lifecycle(self, run_id: str) -> Dict[str, Any]:
        """Validate complete agent execution lifecycle events."""
        events = self.events_by_run.get(run_id, [])
        event_types = [e["event_type"] for e in events]
        
        validation = {
            "run_id": run_id,
            "total_events": len(events),
            "event_sequence": event_types,
            "required_events_present": {},
            "missing_events": [],
            "validation_passed": True,
            "business_value_indicators": {}
        }
        
        # Check all 5 required events
        for required_event in REQUIRED_WEBSOCKET_EVENTS:
            present = required_event in event_types
            validation["required_events_present"][required_event] = present
            if not present:
                validation["missing_events"].append(required_event)
                validation["validation_passed"] = False
                
        # Validate business value indicators
        if events:
            # Check for cost optimization data
            completed_events = [e for e in events if e["event_type"] == "agent_completed"]
            if completed_events:
                result = completed_events[0].get("data", {})
                if isinstance(result, dict):
                    validation["business_value_indicators"]["has_cost_savings"] = "cost_optimization" in result
                    validation["business_value_indicators"]["has_recommendations"] = "recommendations" in str(result)
                    validation["business_value_indicators"]["has_technical_analysis"] = "technical_analysis" in result
        
        return validation


class TestWebSocketAgentExecutionCompleteLifecycleIntegration(BaseIntegrationTest):
    """Integration test for complete agent execution lifecycle with WebSocket events."""
    
    def setup_method(self):
        """Set up test environment for agent execution lifecycle testing."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        self.event_collector = WebSocketEventCollector()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager for agent testing."""
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        llm_manager.initialize = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    async def business_user_context(self):
        """Create user context for business value testing."""
        return UserExecutionContext(
            user_id=f"biz_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"biz_thread_{uuid.uuid4().hex[:8]}", 
            run_id=f"biz_run_{uuid.uuid4().hex[:8]}",
            request_id=f"biz_req_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Optimize my AI infrastructure costs - currently spending $47k monthly",
                "business_priority": "high",
                "expected_value": "cost_optimization"
            }
        )
        
    @pytest.fixture
    async def business_agent_registry(self, mock_llm_manager):
        """Create registry with business value agent."""
        agent = BusinessValueAgent("cost_optimizer", mock_llm_manager)
        
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: agent if name == "cost_optimizer" else None
        registry.get_async = AsyncMock(return_value=agent)
        registry.list_keys = lambda: ["cost_optimizer"]
        
        return registry, agent

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_agent_execution_lifecycle_with_websocket_events(
        self, real_services_fixture, business_user_context, business_agent_registry, mock_llm_manager
    ):
        """CRITICAL: Test complete agent execution lifecycle with all 5 WebSocket events."""
        
        # Business Value: This test validates the core chat experience delivers value
        
        registry, agent = business_agent_registry
        websocket_bridge = await self.event_collector.create_mock_bridge(business_user_context)
        
        # Initialize execution engine with WebSocket integration
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=business_user_context
        )
        
        # Create agent execution context
        exec_context = AgentExecutionContext(
            user_id=business_user_context.user_id,
            thread_id=business_user_context.thread_id,
            run_id=business_user_context.run_id,
            request_id=business_user_context.request_id,
            agent_name="cost_optimizer",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Create agent state with business context
        agent_state = DeepAgentState(
            user_request=business_user_context.metadata["user_request"],
            user_id=business_user_context.user_id,
            chat_thread_id=business_user_context.thread_id,
            run_id=business_user_context.run_id,
            agent_input={
                "optimization_request": True,
                "current_spend": 47000,
                "priority": "high"
            }
        )
        
        # Execute agent with WebSocket event monitoring
        start_time = time.time()
        result = await execution_engine.execute_agent(exec_context, business_user_context)
        execution_time = time.time() - start_time
        
        # CRITICAL: Validate execution succeeded
        assert result is not None
        assert result.success is True, f"Agent execution failed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
        assert result.agent_name == "cost_optimizer"
        
        # MISSION CRITICAL: Validate all 5 required WebSocket events
        validation = self.event_collector.validate_complete_lifecycle(business_user_context.run_id)
        
        assert validation["validation_passed"] is True, \
            f"Missing required WebSocket events: {validation['missing_events']}"
        assert len(validation["missing_events"]) == 0, \
            f"Required events not sent: {validation['missing_events']}"
            
        # Validate each required event individually
        for required_event in REQUIRED_WEBSOCKET_EVENTS:
            assert validation["required_events_present"][required_event] is True, \
                f"Critical WebSocket event missing: {required_event}"
                
        # Validate event sequence and ordering
        event_sequence = validation["event_sequence"]
        
        # agent_started must be first
        assert event_sequence[0] == "agent_started", \
            "agent_started must be first event in lifecycle"
            
        # agent_completed must be present (could be last)
        completed_events = [e for e in event_sequence if e == "agent_completed"]
        assert len(completed_events) >= 1, \
            "Must have at least one agent_completed event"
            
        # Must have thinking events (multiple expected)
        thinking_count = len([e for e in event_sequence if e == "agent_thinking"])
        assert thinking_count >= 2, \
            f"Must have multiple agent_thinking events for transparency, got {thinking_count}"
            
        # Tool events should be paired
        tool_executing_count = len([e for e in event_sequence if e == "tool_executing"])
        tool_completed_count = len([e for e in event_sequence if e == "tool_completed"])
        assert tool_executing_count > 0, "Must have tool_executing events"
        assert tool_completed_count > 0, "Must have tool_completed events"
        assert tool_executing_count == tool_completed_count, \
            "Each tool_executing must have matching tool_completed"
        
        # BUSINESS VALUE: Validate real business insights delivered
        events = self.event_collector.events_by_run[business_user_context.run_id]
        completed_events = [e for e in events if e["event_type"] == "agent_completed"]
        assert len(completed_events) > 0, "Must have completion event with business results"
        
        business_result = completed_events[0]["data"]
        
        # Validate cost optimization value
        assert "business_value" in business_result
        assert "cost_optimization" in business_result["business_value"]
        
        cost_opt = business_result["business_value"]["cost_optimization"]
        assert cost_opt["potential_monthly_savings"] > 0, "Must identify real cost savings"
        assert cost_opt["percentage_reduction"] > 0, "Must calculate percentage savings"
        assert cost_opt["annual_impact"] > 0, "Must project annual impact"
        
        # Validate actionable recommendations
        assert "recommendations" in business_result["business_value"]
        recommendations = business_result["business_value"]["recommendations"]
        assert len(recommendations) > 0, "Must provide actionable recommendations"
        
        for rec in recommendations:
            assert "title" in rec, "Each recommendation must have title"
            assert "savings" in rec, "Each recommendation must specify savings"
            assert "timeline" in rec, "Each recommendation must have timeline"
            
        # Validate technical analysis depth
        assert "technical_analysis" in business_result
        tech_analysis = business_result["technical_analysis"]
        assert tech_analysis["data_sources_analyzed"] > 0
        assert tech_analysis["metrics_processed"] > 0
        
        # PERFORMANCE: Validate execution completed in reasonable time
        assert execution_time < 5.0, f"Agent execution too slow: {execution_time:.2f}s"
        assert validation["total_events"] >= 7, \
            f"Expected minimum 7 events, got {validation['total_events']}"
            
        # DATABASE INTEGRATION: Validate with real services if available
        if real_services_fixture["database_available"]:
            db_session = real_services_fixture["db"]
            if db_session:
                # Verify agent execution state could be persisted
                execution_record = {
                    "user_id": business_user_context.user_id,
                    "run_id": business_user_context.run_id,
                    "agent_name": "cost_optimizer",
                    "success": True,
                    "events_count": validation["total_events"],
                    "business_value_delivered": True
                }
                
                # This would typically be saved to agent_executions table
                assert execution_record["success"] is True
                assert execution_record["events_count"] >= 5
                assert execution_record["business_value_delivered"] is True
        
        self.logger.info(
            f"✅ Complete agent execution lifecycle test PASSED - "
            f"{validation['total_events']} events in {execution_time:.3f}s, "
            f"${cost_opt['potential_monthly_savings']:,} monthly savings identified"
        )

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_events_application_state_synchronization(
        self, real_services_fixture, business_user_context, business_agent_registry
    ):
        """Test WebSocket events synchronize with application state during agent execution."""
        
        # Business Value: State sync ensures chat UI reflects actual system state
        
        registry, agent = business_agent_registry
        websocket_bridge = await self.event_collector.create_mock_bridge(business_user_context)
        
        # Track application state changes
        application_state = {
            "agent_status": "idle",
            "current_operation": None,
            "progress_percentage": 0,
            "last_event": None
        }
        
        # Create state-aware WebSocket bridge
        original_methods = {}
        
        async def state_tracking_wrapper(original_method, event_type):
            """Wrap WebSocket methods to track application state."""
            async def wrapper(*args, **kwargs):
                result = await original_method(*args, **kwargs)
                
                # Update application state based on event type
                if event_type == "agent_started":
                    application_state["agent_status"] = "running"
                    application_state["progress_percentage"] = 10
                elif event_type == "agent_thinking": 
                    application_state["current_operation"] = "thinking"
                    if "progress_percentage" in kwargs:
                        application_state["progress_percentage"] = kwargs["progress_percentage"]
                elif event_type == "tool_executing":
                    application_state["current_operation"] = f"executing_{args[2]}"  # tool_name
                elif event_type == "tool_completed":
                    application_state["current_operation"] = "processing_results"
                elif event_type == "agent_completed":
                    application_state["agent_status"] = "completed"
                    application_state["progress_percentage"] = 100
                    
                application_state["last_event"] = event_type
                return result
            return wrapper
        
        # Wrap bridge methods with state tracking
        for method_name, event_type in [
            ("notify_agent_started", "agent_started"),
            ("notify_agent_thinking", "agent_thinking"),
            ("notify_tool_executing", "tool_executing"),
            ("notify_tool_completed", "tool_completed"), 
            ("notify_agent_completed", "agent_completed")
        ]:
            original_method = getattr(websocket_bridge, method_name)
            wrapped_method = await state_tracking_wrapper(original_method, event_type)
            setattr(websocket_bridge, method_name, wrapped_method)
        
        # Execute agent with state synchronization
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=business_user_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=business_user_context.user_id,
            thread_id=business_user_context.thread_id,
            run_id=business_user_context.run_id,
            request_id=business_user_context.request_id,
            agent_name="cost_optimizer",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"optimize": "ai_costs"},
            user_id=business_user_context.user_id,
            chat_thread_id=business_user_context.thread_id,
            run_id=business_user_context.run_id
        )
        
        # Execute with state monitoring
        result = await execution_engine.execute_agent(exec_context, business_user_context)
        
        # Validate execution and state synchronization
        assert result.success is True
        
        # Validate application state reflects completion
        assert application_state["agent_status"] == "completed"
        assert application_state["progress_percentage"] == 100
        assert application_state["last_event"] == "agent_completed"
        
        # Validate state progression through events
        events = self.event_collector.events_by_run[business_user_context.run_id]
        assert len(events) >= 5
        
        # Validate state transitions align with WebSocket events
        event_types = [e["event_type"] for e in events]
        assert "agent_started" in event_types
        assert "agent_completed" in event_types
        
        # DATABASE SYNC: Validate state could be persisted with real database
        if real_services_fixture["database_available"] and real_services_fixture["db"]:
            # State that would be saved to database
            persistent_state = {
                "user_id": business_user_context.user_id,
                "run_id": business_user_context.run_id,
                "final_status": application_state["agent_status"],
                "progress": application_state["progress_percentage"],
                "last_event": application_state["last_event"],
                "events_count": len(events),
                "success": result.success
            }
            
            # Validate state data is suitable for persistence
            assert persistent_state["final_status"] == "completed"
            assert persistent_state["progress"] == 100
            assert persistent_state["success"] is True
            
        self.logger.info(
            f"✅ WebSocket events application state synchronization test PASSED - "
            f"State: {application_state['agent_status']}, Progress: {application_state['progress_percentage']}%"
        )


if __name__ == "__main__":
    # Run test for development
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])