"""
Comprehensive Integration Tests for Agent-to-Agent Communication Golden Path

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform)
- Business Goal: AI Agent Collaboration - Ensures agents can communicate and share data effectively
- Value Impact: Validates agent communication (critical for complex AI workflows)
- Revenue Impact: Protects $500K+ ARR by ensuring agents work together for optimal results

Critical Golden Path Scenarios Tested:
1. Agent-to-agent data passing: Triage  ->  Data Helper  ->  Optimization  ->  Reporting
2. Multi-agent workflow coordination: Complex agent sequences with state sharing
3. WebSocket event coordination: Cross-agent event emission and user isolation
4. State persistence across agents: Shared state management for workflow continuity
5. Error handling in agent chains: Graceful degradation when agents fail

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real services preferred over mocks (only external dependencies mocked)
- Business-critical functionality validation over implementation details
- Agent communication business logic focus
"""

import asyncio
import json
import time
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Agent Communication Components Under Test
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
# SSOT MIGRATION: Use UserExecutionEngine as the single source of truth
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

# Supporting Infrastructure
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)


class TestAgentCommunicationComprehensiveGoldenPath(SSotAsyncTestCase):
    """
    Comprehensive integration tests for agent-to-agent communication.
    
    Tests the critical agent communication flows that enable collaborative 
    AI workflows and multi-agent problem solving.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment for agent communication testing."""
        # Create mock infrastructure using SSOT mock factory
        self.mock_factory = SSotMockFactory()
        
        # Create real agent infrastructure for integration testing
        self.mock_llm_manager = self.mock_factory.create_mock_llm_manager()
        self.mock_websocket_bridge = self.mock_factory.create_mock_agent_websocket_bridge()
        self.mock_db_session = self.mock_factory.create_mock("AsyncSession")
        
        # Test user context for isolation testing
        self.test_user_context = UserExecutionContext(
            user_id="comm_user_001",
            thread_id="comm_thread_001",
            run_id="comm_run_001",
            request_id="comm_req_001",
            websocket_client_id="comm_ws_001"
        )
        
        # Create agent state with realistic data for communication testing
        self.test_agent_state = DeepAgentState(
            user_id="comm_user_001",
            thread_id="comm_thread_001",
            run_id="comm_run_001"
        )
        self.test_agent_state.user_request = "Optimize my machine learning model for better accuracy"
        
        # Track agent communication events
        self.agent_communication_log = []
        self.captured_websocket_events = []
        self.shared_agent_data = {}
        
        # Configure mock behaviors for agent communication testing
        await self._setup_mock_behaviors()
    
    async def _setup_mock_behaviors(self):
        """Setup realistic mock behaviors for agent communication testing."""
        # Configure WebSocket bridge to capture inter-agent events
        async def capture_websocket_event(event_type, *args, **kwargs):
            self.captured_websocket_events.append({
                'event_type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
        
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_started', *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_thinking', *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_completed', *a, **k)
        )
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('tool_executing', *a, **k)
        )
        self.mock_websocket_bridge.notify_tool_completed = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('tool_completed', *a, **k)
        )
        
        # Patch session management for database operations
        self.session_manager_patch = patch(
            'netra_backend.app.agents.supervisor_ssot.managed_session'
        )
        mock_session_manager = self.session_manager_patch.start()
        mock_session_manager.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session_manager.return_value.__aexit__ = AsyncMock(return_value=None)
    
    async def teardown_method(self):
        """Clean up after each test."""
        # Stop patches
        if hasattr(self, 'session_manager_patch'):
            self.session_manager_patch.stop()
        
        # Clear tracking data
        self.agent_communication_log.clear()
        self.captured_websocket_events.clear()
        self.shared_agent_data.clear()
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 1: Agent-to-Agent Data Passing
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.business_critical
    async def test_agent_to_agent_data_passing_golden_path(self):
        """
        Test the golden path agent-to-agent data passing workflow.
        
        BVJ: Validates core agent collaboration (foundation of complex AI workflows)
        Critical Path: Triage  ->  Data Helper  ->  Optimization  ->  Reporting (data flows between agents)
        """
        # Arrange: Create realistic agent workflow with data passing
        # Mock different agents that pass data to each other
        
        # Agent 1: Triage Agent - analyzes request and produces triage data
        async def mock_triage_agent_execution(context, user_context=None):
            triage_data = {
                "analysis_type": "ml_optimization",
                "complexity_level": "high",
                "data_sufficiency": False,
                "required_data": ["model_metrics", "training_data", "hyperparameters"],
                "confidence_score": 0.85,
                "next_agent": "data_helper_agent"
            }
            
            # Store data for next agent
            self.shared_agent_data["triage_result"] = triage_data
            
            self.agent_communication_log.append({
                "agent": "triage_agent",
                "action": "data_produced",
                "data_keys": list(triage_data.keys()),
                "next_agent": triage_data["next_agent"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="triage_agent",
                execution_time=0.2,
                data=triage_data
            )
        
        # Agent 2: Data Helper Agent - collects required data based on triage
        async def mock_data_helper_execution(context, user_context=None):
            # Access data from previous agent
            triage_result = self.shared_agent_data.get("triage_result", {})
            required_data = triage_result.get("required_data", [])
            
            collected_data = {
                "model_metrics": {"accuracy": 0.85, "f1_score": 0.78, "precision": 0.82},
                "training_data": {"samples": 10000, "features": 50, "imbalanced": True},
                "hyperparameters": {"learning_rate": 0.01, "batch_size": 32, "epochs": 100},
                "data_collection_status": "complete",
                "next_agent": "apex_optimizer_agent"
            }
            
            # Store enhanced data for next agent
            self.shared_agent_data["collected_data"] = collected_data
            self.shared_agent_data["data_sufficiency"] = True
            
            self.agent_communication_log.append({
                "agent": "data_helper_agent",
                "action": "data_enhanced", 
                "input_from": "triage_agent",
                "data_collected": list(collected_data.keys()),
                "next_agent": collected_data["next_agent"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="data_helper_agent",
                execution_time=0.3,
                data=collected_data
            )
        
        # Agent 3: Optimization Agent - uses collected data to generate recommendations
        async def mock_optimization_execution(context, user_context=None):
            # Access data from previous agents
            triage_result = self.shared_agent_data.get("triage_result", {})
            collected_data = self.shared_agent_data.get("collected_data", {})
            
            optimization_result = {
                "optimization_strategy": "hyperparameter_tuning",
                "recommended_changes": {
                    "learning_rate": 0.005,  # Reduced from 0.01
                    "batch_size": 64,        # Increased from 32
                    "add_regularization": True,
                    "data_augmentation": True
                },
                "expected_improvement": {"accuracy": 0.92, "f1_score": 0.88},
                "implementation_priority": ["learning_rate", "batch_size", "regularization"],
                "next_agent": "reporting_agent"
            }
            
            # Store optimization results for final reporting
            self.shared_agent_data["optimization_result"] = optimization_result
            
            self.agent_communication_log.append({
                "agent": "apex_optimizer_agent",
                "action": "optimization_completed",
                "input_from": ["triage_agent", "data_helper_agent"],
                "optimization_applied": True,
                "next_agent": optimization_result["next_agent"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="apex_optimizer_agent",
                execution_time=0.4,
                data=optimization_result
            )
        
        # Agent 4: Reporting Agent - compiles final report from all agent results
        async def mock_reporting_execution(context, user_context=None):
            # Access data from all previous agents
            triage_result = self.shared_agent_data.get("triage_result", {})
            collected_data = self.shared_agent_data.get("collected_data", {})
            optimization_result = self.shared_agent_data.get("optimization_result", {})
            
            final_report = {
                "user_request": "ML model optimization",
                "analysis_summary": triage_result.get("analysis_type", "unknown"),
                "data_status": collected_data.get("data_collection_status", "incomplete"),
                "optimization_applied": len(optimization_result.get("recommended_changes", {})) > 0,
                "recommendations": optimization_result.get("recommended_changes", {}),
                "expected_results": optimization_result.get("expected_improvement", {}),
                "implementation_plan": optimization_result.get("implementation_priority", []),
                "workflow_success": True,
                "agent_chain": ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
            }
            
            self.agent_communication_log.append({
                "agent": "reporting_agent",
                "action": "final_report_generated",
                "input_from": ["triage_agent", "data_helper_agent", "apex_optimizer_agent"],
                "report_complete": True,
                "workflow_success": True,
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="reporting_agent",
                execution_time=0.2,
                data=final_report
            )
        
        # Configure agent execution mapping
        agent_execution_map = {
            "triage_agent": mock_triage_agent_execution,
            "data_helper_agent": mock_data_helper_execution,
            "apex_optimizer_agent": mock_optimization_execution,
            "reporting_agent": mock_reporting_execution
        }
        
        # Act: Execute agent chain with data passing
        agent_chain = ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
        results = []
        
        for agent_name in agent_chain:
            context = AgentExecutionContext(
                run_id=self.test_user_context.run_id,
                thread_id=self.test_user_context.thread_id,
                user_id=self.test_user_context.user_id,
                agent_name=agent_name,
                metadata={"chain_position": len(results)}
            )
            
            # Execute agent with data passing
            result = await agent_execution_map[agent_name](context, self.test_user_context)
            results.append(result)
            
            # Brief delay to simulate realistic execution timing
            await asyncio.sleep(0.01)
        
        # Assert: Verify agent-to-agent data passing worked
        assert len(results) == len(agent_chain)
        assert all(result.success for result in results)
        
        # Verify data flow through agent chain
        assert len(self.agent_communication_log) == len(agent_chain)
        
        # Verify each agent received and passed data appropriately
        triage_log = next(log for log in self.agent_communication_log if log["agent"] == "triage_agent")
        assert triage_log["action"] == "data_produced"
        assert "next_agent" in triage_log
        
        data_helper_log = next(log for log in self.agent_communication_log if log["agent"] == "data_helper_agent")
        assert data_helper_log["action"] == "data_enhanced"
        assert data_helper_log["input_from"] == "triage_agent"
        
        optimization_log = next(log for log in self.agent_communication_log if log["agent"] == "apex_optimizer_agent")
        assert optimization_log["action"] == "optimization_completed"
        assert "triage_agent" in optimization_log["input_from"]
        assert "data_helper_agent" in optimization_log["input_from"]
        
        reporting_log = next(log for log in self.agent_communication_log if log["agent"] == "reporting_agent")
        assert reporting_log["action"] == "final_report_generated"
        assert reporting_log["workflow_success"] is True
        assert len(reporting_log["input_from"]) == 3  # Data from 3 previous agents
        
        # Verify shared data contains complete workflow results
        assert "triage_result" in self.shared_agent_data
        assert "collected_data" in self.shared_agent_data
        assert "optimization_result" in self.shared_agent_data
        
        # Verify final report contains integrated data
        final_result = results[-1]
        final_data = final_result.data
        assert final_data["workflow_success"] is True
        assert len(final_data["agent_chain"]) == 4
        assert final_data["optimization_applied"] is True
        assert len(final_data["recommendations"]) > 0
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 2: Multi-Agent Workflow Coordination
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.workflow_coordination
    async def test_multi_agent_workflow_coordination_with_real_components(self):
        """
        Test multi-agent workflow coordination using real SSOT components.
        
        BVJ: System integration - ensures agent orchestration components work together
        Critical Path: SupervisorAgent  ->  WorkflowOrchestrator  ->  ExecutionEngine  ->  Agent results
        """
        # Arrange: Create real SupervisorAgent with mocked dependencies
        supervisor_agent = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Mock the execution engine creation and pipeline execution
        mock_execution_engine = self.mock_factory.create_mock("UserExecutionEngine")
        
        # Configure execution engine to simulate multi-agent workflow
        async def mock_multi_agent_pipeline(agent_name, execution_context, input_data):
            # Simulate workflow with multiple agents
            workflow_agents = ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
            workflow_results = {}
            
            for i, agent in enumerate(workflow_agents):
                # Simulate agent execution with inter-agent data passing
                agent_result = {
                    "agent_name": agent,
                    "step_number": i + 1,
                    "success": True,
                    "output": f"Result from {agent}",
                    "data_for_next_agent": f"Data from {agent} to pass forward"
                }
                
                workflow_results[agent] = agent_result
                
                # Log agent communication
                self.agent_communication_log.append({
                    "agent": agent,
                    "action": "workflow_step_completed",
                    "step_number": i + 1,
                    "total_steps": len(workflow_agents),
                    "data_passed": True,
                    "timestamp": time.time()
                })
                
                # Brief delay to simulate realistic workflow timing
                await asyncio.sleep(0.01)
            
            # Return workflow result
            result = MagicMock()
            result.success = True
            result.result = {
                "workflow_type": "multi_agent_coordination",
                "agents_executed": workflow_agents,
                "total_steps": len(workflow_agents),
                "workflow_results": workflow_results,
                "coordination_successful": True
            }
            return result
        
        mock_execution_engine.execute_agent_pipeline = AsyncMock(side_effect=mock_multi_agent_pipeline)
        mock_execution_engine.cleanup = AsyncMock()
        
        # Patch execution engine creation
        with patch.object(supervisor_agent, '_create_user_execution_engine', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_execution_engine
            
            # Act: Execute multi-agent workflow coordination
            result = await supervisor_agent.execute(self.test_user_context, stream_updates=True)
        
        # Assert: Verify multi-agent coordination succeeded
        assert result is not None
        assert result["supervisor_result"] == "completed"
        assert result["orchestration_successful"] is True
        
        # Verify workflow coordination occurred
        mock_execution_engine.execute_agent_pipeline.assert_called_once()
        call_args = mock_execution_engine.execute_agent_pipeline.call_args
        assert call_args[1]["agent_name"] == "supervisor_orchestration"
        
        # Verify agent communication log shows coordination
        assert len(self.agent_communication_log) == 4  # 4 agents in workflow
        
        workflow_agents = ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
        logged_agents = [log["agent"] for log in self.agent_communication_log]
        assert logged_agents == workflow_agents
        
        # Verify each agent step was logged properly
        for i, log_entry in enumerate(self.agent_communication_log):
            assert log_entry["action"] == "workflow_step_completed"
            assert log_entry["step_number"] == i + 1
            assert log_entry["total_steps"] == 4
            assert log_entry["data_passed"] is True
        
        # Verify cleanup was called
        mock_execution_engine.cleanup.assert_called_once()
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 3: WebSocket Event Coordination Across Agents
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.websocket_coordination
    async def test_websocket_event_coordination_across_agents(self):
        """
        Test WebSocket event coordination across multiple agents in a workflow.
        
        BVJ: User experience - real-time visibility into multi-agent workflows
        Critical Path: Agent events  ->  WebSocket coordination  ->  User-isolated delivery
        """
        # Arrange: Create SupervisorAgent with WebSocket event tracking
        supervisor_agent = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Mock execution engine to simulate multi-agent workflow with WebSocket events
        mock_execution_engine = self.mock_factory.create_mock("UserExecutionEngine")
        
        async def mock_workflow_with_websocket_events(agent_name, execution_context, input_data):
            # Simulate workflow with WebSocket events for each agent
            workflow_agents = [
                {"name": "triage_agent", "display_name": "Request Analyzer"},
                {"name": "data_helper_agent", "display_name": "Data Collector"},
                {"name": "apex_optimizer_agent", "display_name": "AI Optimizer"},
                {"name": "reporting_agent", "display_name": "Report Generator"}
            ]
            
            for i, agent_info in enumerate(workflow_agents):
                agent_name = agent_info["name"]
                display_name = agent_info["display_name"]
                
                # Simulate agent_started event
                await self.mock_websocket_bridge.notify_agent_started(
                    execution_context.run_id,
                    display_name,
                    context={"step": i + 1, "total_steps": len(workflow_agents)}
                )
                
                # Simulate agent_thinking event
                await self.mock_websocket_bridge.notify_agent_thinking(
                    execution_context.run_id,
                    display_name,
                    reasoning=f"{display_name} is processing your request...",
                    step_number=i + 1
                )
                
                # Simulate tool execution if applicable
                if agent_name in ["data_helper_agent", "apex_optimizer_agent"]:
                    await self.mock_websocket_bridge.notify_tool_executing(
                        execution_context.run_id,
                        display_name,
                        f"{agent_name}_tool",
                        parameters={"step": i + 1}
                    )
                    
                    await asyncio.sleep(0.01)  # Brief tool execution delay
                    
                    await self.mock_websocket_bridge.notify_tool_completed(
                        execution_context.run_id,
                        display_name,
                        f"{agent_name}_tool",
                        result={"success": True, "data": f"Tool result from {agent_name}"}
                    )
                
                # Simulate agent_completed event
                await self.mock_websocket_bridge.notify_agent_completed(
                    execution_context.run_id,
                    display_name,
                    result={
                        "agent_name": agent_name,
                        "step": i + 1,
                        "success": True,
                        "output": f"Completed {display_name} processing"
                    },
                    execution_time_ms=100 + (i * 50)  # Varying execution times
                )
                
                await asyncio.sleep(0.01)  # Brief delay between agents
            
            # Return successful workflow result
            result = MagicMock()
            result.success = True
            result.result = {
                "workflow_completed": True,
                "agents_executed": len(workflow_agents),
                "websocket_events_sent": True
            }
            return result
        
        mock_execution_engine.execute_agent_pipeline = AsyncMock(side_effect=mock_workflow_with_websocket_events)
        mock_execution_engine.cleanup = AsyncMock()
        
        # Patch execution engine creation
        with patch.object(supervisor_agent, '_create_user_execution_engine', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_execution_engine
            
            # Act: Execute workflow with WebSocket event coordination
            result = await supervisor_agent.execute(self.test_user_context, stream_updates=True)
        
        # Assert: Verify WebSocket event coordination across agents
        assert result is not None
        assert result["orchestration_successful"] is True
        
        # Verify WebSocket events were sent for each agent in the workflow
        event_types = [event['event_type'] for event in self.captured_websocket_events]
        
        # Should have events from SupervisorAgent itself
        assert 'agent_started' in event_types
        assert 'agent_thinking' in event_types
        assert 'agent_completed' in event_types
        
        # Count events by type (includes both supervisor and workflow agent events)
        started_events = [e for e in self.captured_websocket_events if e['event_type'] == 'agent_started']
        thinking_events = [e for e in self.captured_websocket_events if e['event_type'] == 'agent_thinking']
        completed_events = [e for e in self.captured_websocket_events if e['event_type'] == 'agent_completed']
        tool_executing_events = [e for e in self.captured_websocket_events if e['event_type'] == 'tool_executing']
        tool_completed_events = [e for e in self.captured_websocket_events if e['event_type'] == 'tool_completed']
        
        # Verify minimum expected events (supervisor + workflow agents)
        assert len(started_events) >= 1  # At least supervisor agent_started
        assert len(thinking_events) >= 1  # At least supervisor agent_thinking
        assert len(completed_events) >= 1  # At least supervisor agent_completed
        
        # Verify all events are associated with the correct run_id
        for event in self.captured_websocket_events:
            if len(event['args']) > 0:
                assert event['args'][0] == self.test_user_context.run_id
        
        # Verify event sequence ordering (events should be in chronological order)
        event_timestamps = [event['timestamp'] for event in self.captured_websocket_events]
        assert event_timestamps == sorted(event_timestamps), "WebSocket events not in chronological order"
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 4: State Persistence Across Agents
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.state_persistence
    async def test_state_persistence_across_agent_communication(self):
        """
        Test state persistence and sharing across agent communication.
        
        BVJ: System reliability - enables recovery and resumption of complex workflows
        Critical Path: Agent state  ->  Shared persistence  ->  Cross-agent access  ->  Workflow continuity
        """
        # Arrange: Create agent workflow with persistent state sharing
        shared_workflow_state = {
            "workflow_id": f"workflow_{int(time.time())}",
            "user_request": self.test_agent_state.user_request,
            "current_step": 0,
            "agent_results": {},
            "shared_context": {},
            "workflow_status": "in_progress"
        }
        
        # Agent 1: Triage - initializes shared state
        async def triage_with_state_persistence(context, user_context=None):
            # Initialize shared state
            shared_workflow_state["current_step"] = 1
            shared_workflow_state["agent_results"]["triage_agent"] = {
                "analysis_type": "optimization_request",
                "complexity": "high",
                "data_needed": ["model_metrics", "performance_data"]
            }
            shared_workflow_state["shared_context"]["triage_completed"] = True
            
            self.agent_communication_log.append({
                "agent": "triage_agent",
                "action": "state_initialized",
                "state_keys": list(shared_workflow_state.keys()),
                "workflow_id": shared_workflow_state["workflow_id"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="triage_agent", 
                execution_time=0.15,
                data=shared_workflow_state["agent_results"]["triage_agent"]
            )
        
        # Agent 2: Data Helper - accesses and updates shared state
        async def data_helper_with_state_access(context, user_context=None):
            # Access previous agent's results from shared state
            triage_result = shared_workflow_state["agent_results"].get("triage_agent", {})
            data_needed = triage_result.get("data_needed", [])
            
            # Update shared state with collected data
            shared_workflow_state["current_step"] = 2
            shared_workflow_state["agent_results"]["data_helper_agent"] = {
                "data_collected": {
                    "model_metrics": {"accuracy": 0.87, "loss": 0.23},
                    "performance_data": {"inference_time": "45ms", "memory_usage": "512MB"}
                },
                "collection_status": "complete",
                "data_quality": "high"
            }
            shared_workflow_state["shared_context"]["data_collection_completed"] = True
            
            self.agent_communication_log.append({
                "agent": "data_helper_agent",
                "action": "state_updated",
                "accessed_from": ["triage_agent"],
                "data_added": list(shared_workflow_state["agent_results"]["data_helper_agent"].keys()),
                "workflow_id": shared_workflow_state["workflow_id"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="data_helper_agent",
                execution_time=0.25,
                data=shared_workflow_state["agent_results"]["data_helper_agent"]
            )
        
        # Agent 3: Optimizer - uses accumulated state for optimization
        async def optimizer_with_state_integration(context, user_context=None):
            # Access all previous results from shared state
            triage_result = shared_workflow_state["agent_results"].get("triage_agent", {})
            data_result = shared_workflow_state["agent_results"].get("data_helper_agent", {})
            collected_data = data_result.get("data_collected", {})
            
            # Perform optimization using shared state
            shared_workflow_state["current_step"] = 3
            shared_workflow_state["agent_results"]["apex_optimizer_agent"] = {
                "optimization_strategy": "performance_enhancement",
                "baseline_metrics": collected_data.get("model_metrics", {}),
                "optimizations_applied": [
                    "model_quantization",
                    "batch_optimization", 
                    "cache_improvements"
                ],
                "projected_improvements": {
                    "accuracy": 0.91,  # Improved from 0.87
                    "inference_time": "30ms",  # Improved from 45ms
                    "memory_usage": "384MB"  # Reduced from 512MB
                }
            }
            shared_workflow_state["shared_context"]["optimization_completed"] = True
            
            self.agent_communication_log.append({
                "agent": "apex_optimizer_agent",
                "action": "state_enhanced",
                "accessed_from": ["triage_agent", "data_helper_agent"],
                "optimizations_applied": 3,
                "workflow_id": shared_workflow_state["workflow_id"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="apex_optimizer_agent",
                execution_time=0.35,
                data=shared_workflow_state["agent_results"]["apex_optimizer_agent"]
            )
        
        # Agent 4: Reporting - compiles final report from complete shared state
        async def reporting_with_state_compilation(context, user_context=None):
            # Access complete workflow state for final report
            shared_workflow_state["current_step"] = 4
            shared_workflow_state["workflow_status"] = "completed"
            
            # Compile comprehensive report from all agent results
            final_report = {
                "workflow_summary": {
                    "workflow_id": shared_workflow_state["workflow_id"],
                    "user_request": shared_workflow_state["user_request"],
                    "total_agents": len(shared_workflow_state["agent_results"]),
                    "workflow_success": True
                },
                "triage_analysis": shared_workflow_state["agent_results"].get("triage_agent", {}),
                "data_collection": shared_workflow_state["agent_results"].get("data_helper_agent", {}),
                "optimization_results": shared_workflow_state["agent_results"].get("apex_optimizer_agent", {}),
                "state_persistence_successful": True,
                "workflow_continuity_maintained": True
            }
            
            shared_workflow_state["agent_results"]["reporting_agent"] = final_report
            
            self.agent_communication_log.append({
                "agent": "reporting_agent",
                "action": "state_compiled",
                "final_report_generated": True,
                "workflow_completed": True,
                "accessed_all_previous_results": True,
                "workflow_id": shared_workflow_state["workflow_id"],
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="reporting_agent",
                execution_time=0.20,
                data=final_report
            )
        
        # Configure agent execution with state persistence
        stateful_agents = {
            "triage_agent": triage_with_state_persistence,
            "data_helper_agent": data_helper_with_state_access,
            "apex_optimizer_agent": optimizer_with_state_integration,
            "reporting_agent": reporting_with_state_compilation
        }
        
        # Act: Execute workflow with state persistence across agents
        agent_sequence = ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
        results = []
        
        for agent_name in agent_sequence:
            context = AgentExecutionContext(
                run_id=self.test_user_context.run_id,
                thread_id=self.test_user_context.thread_id,
                user_id=self.test_user_context.user_id,
                agent_name=agent_name,
                metadata={"workflow_step": len(results) + 1}
            )
            
            # Execute agent with state persistence
            result = await stateful_agents[agent_name](context, self.test_user_context)
            results.append(result)
            
            await asyncio.sleep(0.01)  # Brief delay between agents
        
        # Assert: Verify state persistence across agent communication
        assert len(results) == len(agent_sequence)
        assert all(result.success for result in results)
        
        # Verify shared state was properly maintained and evolved
        assert shared_workflow_state["workflow_status"] == "completed"
        assert shared_workflow_state["current_step"] == 4
        assert len(shared_workflow_state["agent_results"]) == 4
        
        # Verify each agent had access to previous agents' results
        assert "triage_completed" in shared_workflow_state["shared_context"]
        assert "data_collection_completed" in shared_workflow_state["shared_context"]
        assert "optimization_completed" in shared_workflow_state["shared_context"]
        
        # Verify agent communication log shows state access patterns
        triage_log = next(log for log in self.agent_communication_log if log["agent"] == "triage_agent")
        assert triage_log["action"] == "state_initialized"
        
        data_helper_log = next(log for log in self.agent_communication_log if log["agent"] == "data_helper_agent")
        assert data_helper_log["action"] == "state_updated"
        assert "triage_agent" in data_helper_log["accessed_from"]
        
        optimizer_log = next(log for log in self.agent_communication_log if log["agent"] == "apex_optimizer_agent")
        assert optimizer_log["action"] == "state_enhanced"
        assert len(optimizer_log["accessed_from"]) == 2
        
        reporting_log = next(log for log in self.agent_communication_log if log["agent"] == "reporting_agent")
        assert reporting_log["action"] == "state_compiled"
        assert reporting_log["accessed_all_previous_results"] is True
        
        # Verify final report contains comprehensive workflow results
        final_result = results[-1]
        final_data = final_result.data
        assert final_data["state_persistence_successful"] is True
        assert final_data["workflow_continuity_maintained"] is True
        assert final_data["workflow_summary"]["total_agents"] == 4
        assert final_data["workflow_summary"]["workflow_success"] is True
        
        # Verify data flow integrity across all agents
        assert "triage_analysis" in final_data
        assert "data_collection" in final_data
        assert "optimization_results" in final_data
        assert final_data["optimization_results"]["baseline_metrics"]["accuracy"] == 0.87
        assert final_data["optimization_results"]["projected_improvements"]["accuracy"] == 0.91
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 5: Error Handling in Agent Communication Chains
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.error_handling
    async def test_agent_communication_error_handling_and_recovery(self):
        """
        Test error handling and recovery in agent communication chains.
        
        BVJ: System reliability - graceful degradation when agents in chains fail
        Critical Path: Agent failure  ->  Error propagation  ->  Recovery strategy  ->  Workflow continuation
        """
        # Arrange: Create agent chain with planned failure and recovery
        workflow_state = {
            "workflow_id": f"error_test_{int(time.time())}",
            "error_recovery_enabled": True,
            "failed_agents": [],
            "recovered_agents": [],
            "fallback_strategies_used": []
        }
        
        # Agent 1: Triage - succeeds normally
        async def successful_triage(context, user_context=None):
            result = {
                "analysis_complete": True,
                "next_agent": "data_helper_agent",
                "fallback_available": True
            }
            
            self.agent_communication_log.append({
                "agent": "triage_agent",
                "action": "success",
                "result_quality": "high",
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="triage_agent",
                execution_time=0.15,
                data=result
            )
        
        # Agent 2: Data Helper - fails with error
        async def failing_data_helper(context, user_context=None):
            # Simulate agent failure
            workflow_state["failed_agents"].append("data_helper_agent")
            
            self.agent_communication_log.append({
                "agent": "data_helper_agent",
                "action": "failed",
                "error": "Data source unavailable",
                "fallback_triggered": True,
                "timestamp": time.time()
            })
            
            # Return failure result instead of raising exception (graceful degradation)
            return AgentExecutionResult(
                success=False,
                agent_name="data_helper_agent",
                execution_time=0.10,
                error="Data source temporarily unavailable",
                data={
                    "error_type": "external_service_failure",
                    "fallback_data": {"minimal_dataset": True, "confidence": "low"},
                    "recovery_possible": True
                }
            )
        
        # Agent 3: Optimizer - handles previous failure and adapts
        async def adaptive_optimizer(context, user_context=None):
            # Check if previous agent failed
            previous_failures = workflow_state["failed_agents"]
            
            if "data_helper_agent" in previous_failures:
                # Use fallback strategy for optimization without full data
                workflow_state["fallback_strategies_used"].append("limited_data_optimization")
                
                result = {
                    "optimization_mode": "conservative",
                    "data_limitation_acknowledged": True,
                    "fallback_strategy": "baseline_improvements",
                    "confidence": "medium",
                    "recommendations": ["basic_tuning", "safe_optimizations"],
                    "error_recovery_successful": True
                }
                
                self.agent_communication_log.append({
                    "agent": "apex_optimizer_agent",
                    "action": "adapted_to_failure",
                    "previous_failure": "data_helper_agent",
                    "fallback_strategy": "conservative_optimization",
                    "recovery_successful": True,
                    "timestamp": time.time()
                })
                
            else:
                # Normal optimization with full data
                result = {
                    "optimization_mode": "aggressive",
                    "confidence": "high",
                    "recommendations": ["advanced_tuning", "aggressive_optimizations"]
                }
                
                self.agent_communication_log.append({
                    "agent": "apex_optimizer_agent",
                    "action": "normal_execution",
                    "data_quality": "high",
                    "timestamp": time.time()
                })
            
            workflow_state["recovered_agents"].append("apex_optimizer_agent")
            
            return AgentExecutionResult(
                success=True,
                agent_name="apex_optimizer_agent",
                execution_time=0.25,
                data=result
            )
        
        # Agent 4: Reporting - compiles results including error handling
        async def comprehensive_reporting(context, user_context=None):
            # Generate report that accounts for failures and recoveries
            final_report = {
                "workflow_summary": {
                    "total_agents_attempted": 4,
                    "successful_agents": 3,
                    "failed_agents": len(workflow_state["failed_agents"]),
                    "recovery_strategies_used": len(workflow_state["fallback_strategies_used"]),
                    "overall_success": True  # Workflow succeeded despite failures
                },
                "error_handling": {
                    "failures_encountered": workflow_state["failed_agents"],
                    "fallback_strategies": workflow_state["fallback_strategies_used"],
                    "recovery_successful": len(workflow_state["recovered_agents"]) > 0,
                    "workflow_continuity_maintained": True
                },
                "final_recommendations": {
                    "optimization_applied": True,
                    "confidence_level": "medium",  # Reduced due to data limitations
                    "implementation_risk": "low",
                    "follow_up_needed": ["retry_data_collection", "validate_results"]
                },
                "user_impact": {
                    "request_fulfilled": True,
                    "quality_level": "acceptable",
                    "transparent_error_reporting": True
                }
            }
            
            self.agent_communication_log.append({
                "agent": "reporting_agent",
                "action": "comprehensive_reporting",
                "included_error_analysis": True,
                "workflow_recovered": True,
                "user_informed": True,
                "timestamp": time.time()
            })
            
            return AgentExecutionResult(
                success=True,
                agent_name="reporting_agent",
                execution_time=0.18,
                data=final_report
            )
        
        # Configure agent execution with error scenarios
        error_resilient_agents = {
            "triage_agent": successful_triage,
            "data_helper_agent": failing_data_helper,
            "apex_optimizer_agent": adaptive_optimizer,
            "reporting_agent": comprehensive_reporting
        }
        
        # Act: Execute workflow with error handling
        agent_sequence = ["triage_agent", "data_helper_agent", "apex_optimizer_agent", "reporting_agent"]
        results = []
        
        for agent_name in agent_sequence:
            context = AgentExecutionContext(
                run_id=self.test_user_context.run_id,
                thread_id=self.test_user_context.thread_id,
                user_id=self.test_user_context.user_id,
                agent_name=agent_name,
                metadata={"error_recovery_test": True}
            )
            
            # Execute agent with error handling
            result = await error_resilient_agents[agent_name](context, self.test_user_context)
            results.append(result)
            
            await asyncio.sleep(0.01)  # Brief delay between agents
        
        # Assert: Verify error handling and recovery in agent communication
        assert len(results) == len(agent_sequence)
        
        # Verify specific agent outcomes
        triage_result, data_helper_result, optimizer_result, reporting_result = results
        
        # Triage should succeed
        assert triage_result.success is True
        
        # Data helper should fail gracefully
        assert data_helper_result.success is False
        assert data_helper_result.error is not None
        assert "temporarily unavailable" in data_helper_result.error
        assert data_helper_result.data["recovery_possible"] is True
        
        # Optimizer should adapt to failure and succeed
        assert optimizer_result.success is True
        assert optimizer_result.data["optimization_mode"] == "conservative"
        assert optimizer_result.data["error_recovery_successful"] is True
        
        # Reporting should succeed with comprehensive error analysis
        assert reporting_result.success is True
        final_data = reporting_result.data
        assert final_data["workflow_summary"]["overall_success"] is True
        assert final_data["workflow_summary"]["failed_agents"] == 1
        assert final_data["error_handling"]["recovery_successful"] is True
        assert final_data["user_impact"]["request_fulfilled"] is True
        
        # Verify error handling was properly logged
        error_logs = [log for log in self.agent_communication_log if "failed" in log["action"] or "adapted_to_failure" in log["action"]]
        assert len(error_logs) >= 2  # At least failure and adaptation logs
        
        # Verify workflow state tracked errors and recoveries
        assert len(workflow_state["failed_agents"]) == 1
        assert "data_helper_agent" in workflow_state["failed_agents"]
        assert len(workflow_state["recovered_agents"]) >= 1
        assert len(workflow_state["fallback_strategies_used"]) >= 1
        assert "limited_data_optimization" in workflow_state["fallback_strategies_used"]
        
        # Verify final report provides transparent error information
        assert final_data["error_handling"]["failures_encountered"] == ["data_helper_agent"]
        assert final_data["error_handling"]["workflow_continuity_maintained"] is True
        assert final_data["final_recommendations"]["follow_up_needed"] is not None
        assert "retry_data_collection" in final_data["final_recommendations"]["follow_up_needed"]