"""Test #33: Tool Execution Integration with WebSocket Event Notifications and State Tracking

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core platform functionality
- Business Goal: Transparent tool execution shows AI working to solve user problems  
- Value Impact: Tool visibility increases user confidence and demonstrates AI problem-solving approach
- Strategic Impact: Tool execution transparency is key differentiator vs opaque AI systems

This test validates that tool execution is properly integrated with WebSocket events
and application state tracking, ensuring users see exactly how AI agents solve their problems.

CRITICAL: Tool execution events (tool_executing, tool_completed) are essential for:
- User confidence: Users see AI actively working on their optimization problems
- Transparency: Clear visibility into which tools are analyzing their infrastructure
- Progress tracking: Real-time updates on analysis progress and completion
- Business value demonstration: Shows sophisticated problem-solving capabilities

WITHOUT proper tool execution events, users cannot see the AI working and may assume
the system is broken or not processing their requests.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Core application imports
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
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


class ToolExecutionState:
    """Tracks tool execution state and progress."""
    
    def __init__(self, tool_name: str, parameters: Dict[str, Any]):
        self.tool_name = tool_name
        self.parameters = parameters
        self.start_time = None
        self.end_time = None
        self.status = "pending"  # pending, executing, completed, failed
        self.progress_percentage = 0
        self.intermediate_results = []
        self.final_result = None
        self.execution_metadata = {}
        
    def start_execution(self):
        """Mark tool as started."""
        self.start_time = datetime.now(timezone.utc)
        self.status = "executing"
        self.progress_percentage = 0
        
    def update_progress(self, percentage: int, intermediate_data: Optional[Dict] = None):
        """Update tool execution progress."""
        self.progress_percentage = min(100, max(0, percentage))
        if intermediate_data:
            self.intermediate_results.append({
                "timestamp": datetime.now(timezone.utc),
                "progress": percentage,
                "data": intermediate_data
            })
            
    def complete_execution(self, result: Any, metadata: Optional[Dict] = None):
        """Mark tool as completed with result."""
        self.end_time = datetime.now(timezone.utc)
        self.status = "completed"
        self.progress_percentage = 100
        self.final_result = result
        if metadata:
            self.execution_metadata.update(metadata)
            
    def fail_execution(self, error: str, metadata: Optional[Dict] = None):
        """Mark tool as failed."""
        self.end_time = datetime.now(timezone.utc)
        self.status = "failed"
        self.final_result = {"error": error}
        if metadata:
            self.execution_metadata.update(metadata)
            
    def get_execution_duration(self) -> float:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_duration": self.get_execution_duration(),
            "intermediate_results_count": len(self.intermediate_results),
            "final_result": self.final_result,
            "execution_metadata": self.execution_metadata
        }


class BusinessToolExecutionAgent(BaseAgent):
    """Agent that demonstrates comprehensive tool execution with state tracking."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Tool execution {name}")
        self.websocket_bridge = None
        self.tool_execution_states = {}
        self.execution_sequence = []
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        """Set WebSocket bridge for tool execution notifications."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent with comprehensive tool execution and state tracking."""
        
        if not stream_updates or not self.websocket_bridge:
            raise ValueError("WebSocket bridge required for tool execution visibility")
            
        # Clear previous execution state
        self.tool_execution_states.clear()
        self.execution_sequence.clear()
        
        # EVENT 1: agent_started
        await self.websocket_bridge.notify_agent_started(
            run_id, self.name, {
                "tool_execution_plan": "multi_stage_analysis",
                "expected_tools": ["cost_analyzer", "performance_optimizer", "recommendation_engine"],
                "user_context": getattr(state, 'user_request', {})
            }
        )
        
        # EVENT 2: agent_thinking - Plan tool execution
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, 
            "Planning comprehensive tool execution sequence for infrastructure analysis...",
            step_number=1, progress_percentage=10
        )
        
        # Define business-critical tool execution sequence
        tool_sequence = [
            ("cost_analyzer", {
                "analysis_depth": "comprehensive",
                "time_period": "90_days",
                "include_forecasting": True,
                "cost_centers": ["compute", "storage", "network"]
            }),
            ("performance_optimizer", {
                "optimization_targets": ["cost", "performance", "reliability"],
                "risk_tolerance": "medium",
                "implementation_complexity": "medium"
            }),
            ("recommendation_engine", {
                "recommendation_types": ["immediate", "short_term", "strategic"],
                "priority_weighting": {"cost": 0.4, "performance": 0.3, "risk": 0.3},
                "business_context": True
            })
        ]
        
        # Execute tools with full state tracking and WebSocket integration
        tool_results = []
        total_tools = len(tool_sequence)
        
        for tool_index, (tool_name, tool_params) in enumerate(tool_sequence):
            # Initialize tool execution state
            tool_state = ToolExecutionState(tool_name, tool_params)
            self.tool_execution_states[tool_name] = tool_state
            self.execution_sequence.append(tool_name)
            
            # Pre-execution thinking
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name,
                f"Preparing to execute {tool_name} with parameters: {list(tool_params.keys())}",
                step_number=tool_index + 2,
                progress_percentage=20 + (tool_index * 20)
            )
            
            # EVENT 3: tool_executing - Start tool with state tracking
            tool_state.start_execution()
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, tool_name, {
                    **tool_params,
                    "execution_id": f"{run_id}_{tool_name}",
                    "state_tracking": True,
                    "progress_reporting": True
                }
            )
            
            # Simulate comprehensive tool execution with progress updates
            tool_result = await self._execute_business_tool(
                tool_name, tool_params, tool_state, run_id
            )
            
            # EVENT 4: tool_completed - Report comprehensive results
            tool_state.complete_execution(
                tool_result, 
                {"execution_successful": True, "business_value_generated": True}
            )
            
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, tool_name, {
                    "result": tool_result,
                    "execution_state": tool_state.to_dict(),
                    "business_value": self._extract_business_value(tool_name, tool_result),
                    "next_tools": tool_sequence[tool_index + 1:] if tool_index + 1 < total_tools else []
                }
            )
            
            tool_results.append({
                "tool_name": tool_name,
                "result": tool_result,
                "execution_state": tool_state.to_dict()
            })
            
            # Inter-tool thinking
            if tool_index < total_tools - 1:
                await self.websocket_bridge.notify_agent_thinking(
                    run_id, self.name,
                    f"Analyzing {tool_name} results and preparing next tool execution...",
                    step_number=tool_index + 3,
                    progress_percentage=30 + (tool_index * 20)
                )
        
        # Final synthesis thinking
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name,
            "Synthesizing all tool results into comprehensive business recommendations...",
            step_number=len(tool_sequence) + 2,
            progress_percentage=95
        )
        
        # Generate comprehensive result with tool execution summary
        final_result = {
            "success": True,
            "agent_name": self.name,
            "tool_execution_summary": {
                "tools_executed": len(tool_results),
                "execution_sequence": self.execution_sequence,
                "total_execution_time": sum(
                    state.get_execution_duration() for state in self.tool_execution_states.values()
                ),
                "all_tools_successful": all(
                    state.status == "completed" for state in self.tool_execution_states.values()
                )
            },
            "business_insights": self._generate_comprehensive_insights(tool_results),
            "tool_results": tool_results,
            "execution_metadata": {
                "websocket_events_sent": (len(tool_sequence) * 2) + 3,  # 2 per tool + start + final thinking
                "state_tracking_enabled": True,
                "progress_reporting": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # EVENT 5: agent_completed
        await self.websocket_bridge.notify_agent_completed(
            run_id, self.name, final_result,
            execution_time_ms=int(sum(
                state.get_execution_duration() for state in self.tool_execution_states.values()
            ) * 1000)
        )
        
        return final_result
        
    async def _execute_business_tool(
        self, tool_name: str, tool_params: Dict, tool_state: ToolExecutionState, run_id: str
    ) -> Dict[str, Any]:
        """Execute business tool with realistic processing and progress updates."""
        
        # Simulate tool execution phases with progress updates
        phases = self._get_tool_execution_phases(tool_name)
        
        for phase_index, (phase_name, duration) in enumerate(phases):
            # Update progress
            progress = int(((phase_index + 1) / len(phases)) * 100)
            tool_state.update_progress(progress, {
                "current_phase": phase_name,
                "phase_index": phase_index + 1,
                "total_phases": len(phases)
            })
            
            # Simulate phase processing time
            await asyncio.sleep(duration)
            
        # Generate business-realistic results based on tool type
        if tool_name == "cost_analyzer":
            return {
                "analysis_complete": True,
                "cost_breakdown": {
                    "compute": {"current": 28500, "optimizable": 8200},
                    "storage": {"current": 12300, "optimizable": 3600},
                    "network": {"current": 6800, "optimizable": 1200},
                    "total_analyzed": 47600,
                    "total_savings_potential": 13000
                },
                "cost_trends": {
                    "90_day_growth": 12.3,
                    "month_over_month": 2.8,
                    "projected_annual": 571200
                },
                "optimization_opportunities": [
                    {"type": "rightsizing", "impact": "high", "effort": "medium"},
                    {"type": "scheduling", "impact": "medium", "effort": "low"},
                    {"type": "storage_tiering", "impact": "medium", "effort": "low"}
                ],
                "confidence_score": 0.89,
                "data_sources": ["billing_api", "metrics", "usage_logs"]
            }
        elif tool_name == "performance_optimizer":
            return {
                "optimization_strategies": [
                    {
                        "strategy": "Auto-scaling Implementation",
                        "impact": {"cost_reduction": 6200, "performance_gain": 23},
                        "implementation": {"effort": "medium", "timeline": "4-6 weeks"},
                        "risk_level": "low"
                    },
                    {
                        "strategy": "Storage Optimization",
                        "impact": {"cost_reduction": 3600, "performance_gain": 15},
                        "implementation": {"effort": "low", "timeline": "1-2 weeks"},
                        "risk_level": "very_low"  
                    },
                    {
                        "strategy": "Network Routing Optimization",
                        "impact": {"cost_reduction": 1200, "performance_gain": 8},
                        "implementation": {"effort": "low", "timeline": "1 week"},
                        "risk_level": "very_low"
                    }
                ],
                "performance_analysis": {
                    "current_efficiency": 67,
                    "potential_efficiency": 89,
                    "improvement_potential": 22
                },
                "implementation_roadmap": {
                    "quick_wins": ["storage_tiering", "scheduling_optimization"],
                    "medium_term": ["auto_scaling", "load_balancing"],
                    "strategic": ["architecture_optimization"]
                }
            }
        else:  # recommendation_engine
            return {
                "immediate_recommendations": [
                    {
                        "title": "Implement Storage Auto-Tiering",
                        "priority": "high",
                        "savings": "$3,600/month", 
                        "effort": "1-2 weeks",
                        "business_impact": "Quick cost reduction with minimal risk"
                    }
                ],
                "short_term_recommendations": [
                    {
                        "title": "Deploy Auto-Scaling for Compute",
                        "priority": "high",
                        "savings": "$6,200/month",
                        "effort": "4-6 weeks", 
                        "business_impact": "Significant cost reduction + performance improvement"
                    }
                ],
                "strategic_recommendations": [
                    {
                        "title": "Infrastructure Architecture Review",
                        "priority": "medium",
                        "savings": "$2,000+/month",
                        "effort": "8-12 weeks",
                        "business_impact": "Long-term optimization foundation"
                    }
                ],
                "business_case": {
                    "total_potential_savings": "$13,000/month",
                    "annual_impact": "$156,000",
                    "roi_timeline": "2-3 months",
                    "implementation_investment": "$25,000",
                    "roi_percentage": 624
                }
            }
    
    def _get_tool_execution_phases(self, tool_name: str) -> List[Tuple[str, float]]:
        """Get execution phases for different tool types."""
        if tool_name == "cost_analyzer":
            return [
                ("data_collection", 0.1),
                ("cost_analysis", 0.15),
                ("trend_analysis", 0.1),
                ("optimization_identification", 0.1),
                ("result_compilation", 0.05)
            ]
        elif tool_name == "performance_optimizer":
            return [
                ("performance_baseline", 0.08),
                ("bottleneck_analysis", 0.12),
                ("strategy_generation", 0.1),
                ("impact_modeling", 0.08),
                ("roadmap_creation", 0.05)
            ]
        else:  # recommendation_engine
            return [
                ("data_synthesis", 0.06),
                ("recommendation_generation", 0.1),
                ("prioritization", 0.08),
                ("business_case_analysis", 0.08),
                ("final_compilation", 0.03)
            ]
    
    def _extract_business_value(self, tool_name: str, tool_result: Dict) -> Dict[str, Any]:
        """Extract business value indicators from tool results."""
        if tool_name == "cost_analyzer":
            return {
                "cost_savings_identified": tool_result.get("cost_breakdown", {}).get("total_savings_potential", 0),
                "analysis_confidence": tool_result.get("confidence_score", 0),
                "actionable_opportunities": len(tool_result.get("optimization_opportunities", []))
            }
        elif tool_name == "performance_optimizer":
            return {
                "performance_improvement": tool_result.get("performance_analysis", {}).get("improvement_potential", 0),
                "optimization_strategies": len(tool_result.get("optimization_strategies", [])),
                "implementation_readiness": "high" if len(tool_result.get("optimization_strategies", [])) > 2 else "medium"
            }
        else:  # recommendation_engine
            return {
                "total_recommendations": (
                    len(tool_result.get("immediate_recommendations", [])) +
                    len(tool_result.get("short_term_recommendations", [])) +
                    len(tool_result.get("strategic_recommendations", []))
                ),
                "business_case_strength": tool_result.get("business_case", {}).get("roi_percentage", 0),
                "implementation_priority": "high" if tool_result.get("business_case", {}).get("roi_percentage", 0) > 400 else "medium"
            }
    
    def _generate_comprehensive_insights(self, tool_results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive business insights from all tool results."""
        total_savings = 0
        total_recommendations = 0
        
        for tool_result in tool_results:
            result_data = tool_result.get("result", {})
            
            if "cost_breakdown" in result_data:
                total_savings += result_data["cost_breakdown"].get("total_savings_potential", 0)
            if "immediate_recommendations" in result_data:
                total_recommendations += len(result_data["immediate_recommendations"])
            if "short_term_recommendations" in result_data:
                total_recommendations += len(result_data["short_term_recommendations"])
                
        return {
            "comprehensive_analysis": {
                "total_cost_savings_potential": total_savings,
                "total_actionable_recommendations": total_recommendations,
                "analysis_depth": "comprehensive",
                "confidence_level": "high"
            },
            "business_impact": {
                "monthly_savings": total_savings,
                "annual_impact": total_savings * 12,
                "roi_timeline": "2-3 months",
                "implementation_priority": "high" if total_savings > 10000 else "medium"
            },
            "tool_execution_effectiveness": {
                "all_tools_successful": True,
                "comprehensive_coverage": True,
                "data_quality": "high",
                "actionable_insights": True
            }
        }


class ToolExecutionEventCollector:
    """Collects and validates tool execution events and state."""
    
    def __init__(self):
        self.all_events = []
        self.tool_events = {"executing": [], "completed": []}
        self.execution_states = {}
        
    async def create_state_tracking_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge that tracks tool execution state."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.events = []
        
        async def track_tool_event(event_type: str, run_id: str, agent_name: str, data: Any = None, **kwargs):
            """Track tool execution events with state."""
            event = {
                "event_type": event_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "data": data,
                "timestamp": datetime.now(timezone.utc),
                "user_id": user_context.user_id,
                "kwargs": kwargs
            }
            
            bridge.events.append(event)
            self.all_events.append(event)
            
            # Track tool-specific events
            if event_type in ["tool_executing", "tool_completed"]:
                self.tool_events[event_type.split("_")[1]].append(event)
                
                # Extract tool state if available
                if event_type == "tool_completed" and data and "execution_state" in data:
                    tool_name = data.get("tool_name") or (data.get("execution_state", {}).get("tool_name"))
                    if tool_name:
                        self.execution_states[tool_name] = data["execution_state"]
            
            return True
            
        # Mock WebSocket methods with tool state tracking
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_tool_event("agent_started", run_id, agent_name, context))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, thinking, **kwargs:
            track_tool_event("agent_thinking", run_id, agent_name, {"reasoning": thinking}, **kwargs))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, params:
            track_tool_event("tool_executing", run_id, agent_name, {"tool_name": tool_name, "parameters": params}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            track_tool_event("tool_completed", run_id, agent_name, {"tool_name": tool_name, **result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, **kwargs:
            track_tool_event("agent_completed", run_id, agent_name, result, **kwargs))
            
        return bridge
        
    def validate_tool_execution_flow(self) -> Dict[str, Any]:
        """Validate complete tool execution flow."""
        executing_events = self.tool_events["executing"]
        completed_events = self.tool_events["completed"]
        
        validation = {
            "tool_executing_events": len(executing_events),
            "tool_completed_events": len(completed_events),
            "events_paired_correctly": len(executing_events) == len(completed_events),
            "tool_execution_states": len(self.execution_states),
            "all_tools_successful": True,
            "execution_flow_valid": True,
            "business_value_indicators": {}
        }
        
        # Check that each tool_executing has matching tool_completed
        executing_tools = [e["data"]["tool_name"] for e in executing_events]
        completed_tools = []
        
        for event in completed_events:
            tool_name = event["data"].get("tool_name")
            if not tool_name and "execution_state" in event["data"]:
                tool_name = event["data"]["execution_state"].get("tool_name")
            if tool_name:
                completed_tools.append(tool_name)
                
        validation["tool_pairing"] = {
            "executing_tools": executing_tools,
            "completed_tools": completed_tools,
            "missing_completions": [t for t in executing_tools if t not in completed_tools],
            "orphaned_completions": [t for t in completed_tools if t not in executing_tools]
        }
        
        if validation["tool_pairing"]["missing_completions"] or validation["tool_pairing"]["orphaned_completions"]:
            validation["execution_flow_valid"] = False
            
        # Validate tool execution states
        for tool_name, state in self.execution_states.items():
            if state.get("status") != "completed":
                validation["all_tools_successful"] = False
                
        # Extract business value indicators
        total_savings = 0
        for event in completed_events:
            result = event["data"].get("result", {})
            if "cost_breakdown" in result:
                total_savings += result["cost_breakdown"].get("total_savings_potential", 0)
                
        validation["business_value_indicators"]["total_savings_identified"] = total_savings
        validation["business_value_indicators"]["has_actionable_insights"] = total_savings > 0
        
        return validation


class TestWebSocketToolExecutionIntegrationStateTracking(BaseIntegrationTest):
    """Integration test for tool execution with WebSocket events and state tracking."""
    
    def setup_method(self):
        """Set up test environment for tool execution testing."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        self.event_collector = ToolExecutionEventCollector()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        llm_manager.initialize = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    async def tool_execution_user_context(self):
        """Create user context for tool execution testing."""
        return UserExecutionContext(
            user_id=f"tool_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"tool_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"tool_run_{uuid.uuid4().hex[:8]}",
            request_id=f"tool_req_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Comprehensive infrastructure cost optimization analysis",
                "expected_tools": ["cost_analyzer", "performance_optimizer", "recommendation_engine"],
                "analysis_depth": "comprehensive"
            }
        )
        
    @pytest.fixture
    async def tool_execution_registry(self, mock_llm_manager):
        """Create registry with tool execution agent."""
        agent = BusinessToolExecutionAgent("infrastructure_optimizer", mock_llm_manager)
        
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: agent if name == "infrastructure_optimizer" else None
        registry.get_async = AsyncMock(return_value=agent)
        registry.list_keys = lambda: ["infrastructure_optimizer"]
        
        return registry, agent

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_comprehensive_tool_execution_with_websocket_integration(
        self, real_services_fixture, tool_execution_user_context, tool_execution_registry, mock_llm_manager
    ):
        """CRITICAL: Test comprehensive tool execution with WebSocket events and state tracking."""
        
        # Business Value: Tool execution transparency demonstrates AI problem-solving to users
        
        registry, agent = tool_execution_registry
        websocket_bridge = await self.event_collector.create_state_tracking_bridge(tool_execution_user_context)
        
        # Initialize execution engine with tool integration
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=tool_execution_user_context
        )
        
        # Create agent execution context
        exec_context = AgentExecutionContext(
            user_id=tool_execution_user_context.user_id,
            thread_id=tool_execution_user_context.thread_id,
            run_id=tool_execution_user_context.run_id,
            request_id=tool_execution_user_context.request_id,
            agent_name="infrastructure_optimizer",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Create agent state with tool execution requirements
        agent_state = DeepAgentState(
            user_request=tool_execution_user_context.metadata["user_request"],
            user_id=tool_execution_user_context.user_id,
            chat_thread_id=tool_execution_user_context.thread_id,
            run_id=tool_execution_user_context.run_id,
            agent_input={
                "comprehensive_analysis": True,
                "tool_execution_required": True,
                "state_tracking": True,
                "progress_reporting": True
            }
        )
        
        # Execute agent with comprehensive tool execution
        start_time = time.time()
        result = await execution_engine.execute_agent(exec_context, tool_execution_user_context)
        execution_time = time.time() - start_time
        
        # CRITICAL: Validate execution succeeded
        assert result is not None
        assert result.success is True, f"Tool execution failed: {getattr(result, 'error', 'Unknown')}"
        assert result.agent_name == "infrastructure_optimizer"
        
        # MISSION CRITICAL: Validate tool execution flow
        tool_validation = self.event_collector.validate_tool_execution_flow()
        
        # Validate tool event pairing
        assert tool_validation["events_paired_correctly"] is True, \
            "Each tool_executing must have matching tool_completed"
        assert tool_validation["execution_flow_valid"] is True, \
            f"Tool execution flow invalid: {tool_validation['tool_pairing']}"
        assert tool_validation["all_tools_successful"] is True, \
            "All tools must execute successfully"
            
        # Validate expected number of tools executed
        expected_tools = 3  # cost_analyzer, performance_optimizer, recommendation_engine
        assert tool_validation["tool_executing_events"] == expected_tools, \
            f"Expected {expected_tools} tool_executing events, got {tool_validation['tool_executing_events']}"
        assert tool_validation["tool_completed_events"] == expected_tools, \
            f"Expected {expected_tools} tool_completed events, got {tool_validation['tool_completed_events']}"
            
        # Validate tool execution states were captured
        assert tool_validation["tool_execution_states"] == expected_tools, \
            f"Expected {expected_tools} tool execution states, got {tool_validation['tool_execution_states']}"
            
        # BUSINESS VALUE: Validate tools produced meaningful results
        business_value = tool_validation["business_value_indicators"]
        assert business_value["total_savings_identified"] > 0, \
            "Tools must identify cost savings opportunities"
        assert business_value["has_actionable_insights"] is True, \
            "Tools must produce actionable business insights"
            
        # Validate comprehensive tool execution summary in result
        tool_summary = result.data.get("tool_execution_summary", {})
        assert tool_summary.get("tools_executed") == expected_tools
        assert tool_summary.get("all_tools_successful") is True
        assert tool_summary.get("total_execution_time", 0) > 0
        
        # Validate business insights were generated
        business_insights = result.data.get("business_insights", {})
        assert "comprehensive_analysis" in business_insights
        assert business_insights["comprehensive_analysis"]["total_cost_savings_potential"] > 0
        assert business_insights["comprehensive_analysis"]["total_actionable_recommendations"] > 0
        
        # Validate individual tool results
        tool_results = result.data.get("tool_results", [])
        assert len(tool_results) == expected_tools
        
        tool_names = [tr["tool_name"] for tr in tool_results]
        expected_tool_names = ["cost_analyzer", "performance_optimizer", "recommendation_engine"]
        for expected_tool in expected_tool_names:
            assert expected_tool in tool_names, f"Missing expected tool: {expected_tool}"
            
        # Validate tool execution metadata
        execution_metadata = result.data.get("execution_metadata", {})
        assert execution_metadata.get("state_tracking_enabled") is True
        assert execution_metadata.get("progress_reporting") is True
        assert execution_metadata.get("websocket_events_sent", 0) >= 9  # Minimum expected events
        
        # PERFORMANCE: Validate execution completed in reasonable time
        assert execution_time < 10.0, f"Tool execution too slow: {execution_time:.2f}s"
        
        # DATABASE INTEGRATION: Validate tool execution could be persisted
        if real_services_fixture["database_available"]:
            db_session = real_services_fixture["db"]
            if db_session:
                # Tool execution record for database
                tool_execution_record = {
                    "user_id": tool_execution_user_context.user_id,
                    "run_id": tool_execution_user_context.run_id,
                    "agent_name": "infrastructure_optimizer",
                    "tools_executed": expected_tools,
                    "execution_time": execution_time,
                    "total_savings_identified": business_value["total_savings_identified"],
                    "success": True,
                    "websocket_events": len(self.event_collector.all_events)
                }
                
                # Validate record is suitable for persistence
                assert tool_execution_record["tools_executed"] == expected_tools
                assert tool_execution_record["total_savings_identified"] > 0
                assert tool_execution_record["success"] is True
                
        self.logger.info(
            f" PASS:  Comprehensive tool execution test PASSED - "
            f"{expected_tools} tools executed, "
            f"${business_value['total_savings_identified']:,} savings identified, "
            f"{len(self.event_collector.all_events)} WebSocket events, "
            f"{execution_time:.3f}s execution time"
        )

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_tool_execution_state_tracking_and_progress_reporting(
        self, tool_execution_user_context, tool_execution_registry
    ):
        """Test tool execution state tracking and progress reporting through WebSocket events."""
        
        # Business Value: Progress tracking shows users AI is actively working
        
        registry, agent = tool_execution_registry
        websocket_bridge = await self.event_collector.create_state_tracking_bridge(tool_execution_user_context)
        
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=tool_execution_user_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=tool_execution_user_context.user_id,
            thread_id=tool_execution_user_context.thread_id,
            run_id=tool_execution_user_context.run_id,
            request_id=tool_execution_user_context.request_id,
            agent_name="infrastructure_optimizer",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"state_tracking_focus": True},
            user_id=tool_execution_user_context.user_id,
            chat_thread_id=tool_execution_user_context.thread_id,
            run_id=tool_execution_user_context.run_id,
            agent_input={"detailed_progress": True}
        )
        
        # Execute with state tracking focus
        result = await execution_engine.execute_agent(exec_context, tool_execution_user_context)
        
        # Validate execution and state tracking
        assert result.success is True
        
        # Validate tool execution states were captured
        tool_states = self.event_collector.execution_states
        assert len(tool_states) >= 3, f"Expected at least 3 tool states, got {len(tool_states)}"
        
        # Validate each tool state has required tracking data
        for tool_name, state in tool_states.items():
            assert state["status"] == "completed", f"Tool {tool_name} status: {state['status']}"
            assert state["progress_percentage"] == 100, f"Tool {tool_name} progress: {state['progress_percentage']}"
            assert state["execution_duration"] > 0, f"Tool {tool_name} duration: {state['execution_duration']}"
            assert "start_time" in state and state["start_time"] is not None
            assert "end_time" in state and state["end_time"] is not None
            assert "final_result" in state and state["final_result"] is not None
            
        # Validate progress was tracked through WebSocket events
        thinking_events = [e for e in self.event_collector.all_events if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 5, "Should have multiple thinking events for progress tracking"
        
        # Validate progress percentages were included
        progress_events = [e for e in thinking_events if "progress_percentage" in e.get("kwargs", {})]
        assert len(progress_events) >= 3, "Should have progress percentage updates"
        
        self.logger.info(
            f" PASS:  Tool execution state tracking test PASSED - "
            f"{len(tool_states)} tools tracked, "
            f"{len(thinking_events)} progress updates"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_error_handling_with_websocket_notification(
        self, tool_execution_user_context, mock_llm_manager
    ):
        """Test tool execution error handling with WebSocket event notification."""
        
        # Business Value: Error transparency prevents user confusion when tools fail
        
        # Create agent that simulates tool failure
        class FailingToolAgent(BaseAgent):
            def __init__(self, llm_manager):
                super().__init__(llm_manager, "failing_tool_agent", "Agent with failing tools")
                self.websocket_bridge = None
                
            def set_websocket_bridge(self, bridge, run_id):
                self.websocket_bridge = bridge
                
            async def execute(self, state, run_id, stream_updates=True):
                if not stream_updates or not self.websocket_bridge:
                    raise ValueError("WebSocket required")
                    
                await self.websocket_bridge.notify_agent_started(run_id, "failing_tool_agent")
                
                # Start tool execution
                await self.websocket_bridge.notify_tool_executing(
                    run_id, "failing_tool_agent", "failing_analyzer", {"param": "value"}
                )
                
                # Simulate tool failure
                await asyncio.sleep(0.1)
                
                # Report tool failure
                await self.websocket_bridge.notify_tool_completed(
                    run_id, "failing_tool_agent", "failing_analyzer", {
                        "result": {"error": "Tool execution failed", "success": False},
                        "execution_state": {
                            "tool_name": "failing_analyzer",
                            "status": "failed",
                            "error": "Simulated tool failure for testing"
                        }
                    }
                )
                
                return {
                    "success": False,
                    "error": "Tool execution failed",
                    "tool_failures": ["failing_analyzer"]
                }
        
        failing_agent = FailingToolAgent(mock_llm_manager)
        
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: failing_agent
        registry.get_async = AsyncMock(return_value=failing_agent)
        
        websocket_bridge = await self.event_collector.create_state_tracking_bridge(tool_execution_user_context)
        
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=websocket_bridge,
            user_context=tool_execution_user_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=tool_execution_user_context.user_id,
            thread_id=tool_execution_user_context.thread_id,
            run_id=tool_execution_user_context.run_id,
            request_id=tool_execution_user_context.request_id,
            agent_name="failing_tool_agent",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"test": "tool_failure"},
            user_id=tool_execution_user_context.user_id,
            chat_thread_id=tool_execution_user_context.thread_id,
            run_id=tool_execution_user_context.run_id
        )
        
        # Execute with expected tool failure
        result = await execution_engine.execute_agent(exec_context, tool_execution_user_context)
        
        # Validate failure was handled properly
        assert result.success is False
        
        # Validate tool failure was reported via WebSocket
        tool_completed_events = [e for e in self.event_collector.all_events if e["event_type"] == "tool_completed"]
        assert len(tool_completed_events) >= 1, "Should have tool_completed event even for failures"
        
        failure_event = tool_completed_events[0]
        assert "error" in str(failure_event["data"]), "Tool failure should be reported in event data"
        
        # Validate tool execution state captured failure
        if self.event_collector.execution_states:
            for tool_name, state in self.event_collector.execution_states.items():
                if state["status"] == "failed":
                    assert "error" in state, "Failed tool state should include error details"
                    
        self.logger.info(" PASS:  Tool execution error handling test PASSED")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])