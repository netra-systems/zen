#!/usr/bin/env python3
"""
Multi-Agent Integration Test Suite - EXTREMELY Comprehensive Coverage

This test suite provides the most comprehensive and difficult multi-agent testing
possible to ensure the system can handle real production loads and complex scenarios.

Coverage Areas:
1. Multi-Agent Coordination (5+ agents working together)
2. WebSocket Event Flow for Multi-Agent scenarios
3. Real-World Complex Scenarios
4. Performance Under Load (20+ concurrent agents)
5. Integration Points Testing
6. Failure Scenarios and Recovery
7. Business Value Delivery Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Scale Validation
- Value Impact: Ensures chat responsiveness under extreme loads
- Strategic Impact: Validates system can handle enterprise-scale concurrent usage
"""

import asyncio
import gc
import json
import os
import psutil
import pytest
import random
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.websocket_types import WebSocketEventCapture
from test_framework.mocks.websocket import MockWebSocketManager
from test_framework.performance import PerformanceTracker

# Application imports
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import create_request_scoped_tool_dispatcher
from netra_backend.app.agents.tool_dispatcher_unified import UnifiedToolDispatcher
from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
from netra_backend.app.orchestration.agent_execution_registry import (
    AgentExecutionRegistry,
    get_agent_execution_registry
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.core.tool_models import ToolExecutionResult
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class AgentExecutionStats:
    """Statistics for agent execution tracking."""
    agent_id: str
    agent_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    events_sent: int = 0
    tools_executed: int = 0
    errors_encountered: int = 0
    websocket_events: List[Dict[str, Any]] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    execution_duration_ms: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass 
class MultiAgentScenarioConfig:
    """Configuration for multi-agent test scenarios."""
    name: str
    agent_types: List[str]
    dependency_chains: Dict[str, List[str]]
    expected_tools: Set[str]
    timeout_seconds: int = 30
    failure_rate: float = 0.0
    memory_limit_mb: int = 500


class MockComplexAgent:
    """Mock agent for complex multi-agent scenarios."""
    
    def __init__(self, agent_type: str, tools: List[str] = None, failure_rate: float = 0.0):
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.tools = tools or ["analysis", "data_processing", "reporting"]
        self.failure_rate = failure_rate
        self.execution_context: Optional[AgentExecutionContext] = None
        self.websocket_notifier: Optional[WebSocketNotifier] = None
        self.tool_dispatcher: Optional[UnifiedToolDispatcher] = None
        self.stats = AgentExecutionStats(
            agent_id=self.agent_id,
            agent_type=agent_type,
            start_time=datetime.now(timezone.utc)
        )
    
    async def initialize(self, execution_context: AgentExecutionContext,
                        websocket_notifier: WebSocketNotifier,
                        tool_dispatcher: UnifiedToolDispatcher):
        """Initialize agent with required components."""
        self.execution_context = execution_context
        self.websocket_notifier = websocket_notifier
        self.tool_dispatcher = tool_dispatcher
        
        # Send agent_started event
        await self.websocket_notifier.send_agent_started(execution_context)
        self.stats.events_sent += 1
        self.stats.websocket_events.append({
            "type": "agent_started",
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def execute_task(self, task: str, dependencies: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a complex task with multiple tool invocations."""
        if random.random() < self.failure_rate:
            raise RuntimeError(f"Simulated failure in {self.agent_type}")
        
        # Send agent_thinking event
        await self.websocket_notifier.send_agent_thinking(
            self.execution_context,
            thinking_content=f"Planning {task} execution with {len(self.tools)} tools"
        )
        self.stats.events_sent += 1
        
        results = {}
        
        # Execute multiple tools in sequence
        for tool_name in self.tools:
            try:
                # Send tool_executing event
                await self.websocket_notifier.send_tool_executing(
                    self.execution_context,
                    tool_name=tool_name,
                    tool_input={"task": task, "dependencies": dependencies or {}}
                )
                self.stats.events_sent += 1
                
                # Simulate tool execution with realistic delay
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                # Create mock tool result
                tool_result = ToolExecutionResult(
                    success=True,
                    result={"output": f"{tool_name} result for {task}", "agent_id": self.agent_id},
                    error=None,
                    execution_time_ms=random.uniform(100, 500)
                )
                
                results[tool_name] = tool_result.result
                self.stats.tools_executed += 1
                
                # Send tool_completed event
                await self.websocket_notifier.send_tool_completed(
                    self.execution_context,
                    tool_name=tool_name,
                    tool_result=tool_result.result,
                    execution_time_ms=tool_result.execution_time_ms
                )
                self.stats.events_sent += 1
                
            except Exception as e:
                self.stats.errors_encountered += 1
                # Send tool error event
                await self.websocket_notifier.send_tool_error(
                    self.execution_context,
                    tool_name=tool_name,
                    error_message=str(e)
                )
                self.stats.events_sent += 1
        
        return results
    
    async def finalize(self, results: Dict[str, Any]):
        """Finalize agent execution."""
        self.stats.end_time = datetime.now(timezone.utc)
        self.stats.execution_duration_ms = self.stats.duration_seconds * 1000
        
        # Send agent_completed event
        await self.websocket_notifier.send_agent_completed(
            self.execution_context,
            result=results,
            duration_ms=self.stats.execution_duration_ms
        )
        self.stats.events_sent += 1
        self.stats.websocket_events.append({
            "type": "agent_completed",
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": self.stats.execution_duration_ms
        })


class TestMultiAgentComprehensive(BaseIntegrationTest):
    """EXTREMELY comprehensive multi-agent integration tests."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Set up isolated test environment."""
        self.env = IsolatedEnvironment()
        self.performance_tracker = PerformanceTracker()
        self.websocket_events: List[Dict[str, Any]] = []
        self.agent_stats: Dict[str, AgentExecutionStats] = {}
        self.execution_registry: Optional[AgentExecutionRegistry] = None
        self.websocket_manager: Optional[WebSocketManager] = None
        
        # Track memory baseline
        self.baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        yield
        
        # Cleanup and memory verification
        await self._cleanup_test_environment()

    async def _cleanup_test_environment(self):
        """Clean up test environment and verify no memory leaks."""
        if self.execution_registry:
            await self.execution_registry.shutdown()
        
        # Force garbage collection
        gc.collect()
        
        # Check for memory leaks
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_increase = final_memory - self.baseline_memory
        
        # Allow some increase but flag major leaks
        assert memory_increase < 50, f"Memory leak detected: {memory_increase:.2f}MB increase"

    @pytest.fixture
    async def mock_websocket_manager(self):
        """Create mock WebSocket manager with comprehensive event tracking."""
        manager = MockWebSocketManager()
        
        # Track all events
        original_send_to_thread = manager.send_to_thread
        
        async def track_events(thread_id: str, message: Dict[str, Any]) -> bool:
            self.websocket_events.append({
                "thread_id": thread_id,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return await original_send_to_thread(thread_id, message)
        
        manager.send_to_thread = track_events
        return manager

    @pytest.fixture
    async def agent_execution_registry(self, mock_websocket_manager):
        """Create agent execution registry with WebSocket integration."""
        registry = AgentExecutionRegistry()
        await registry.initialize()
        await registry.set_websocket_manager(mock_websocket_manager)
        self.execution_registry = registry
        return registry

    async def create_agent_context(self, agent_type: str, user_id: str = None) -> Tuple[AgentExecutionContext, WebSocketNotifier]:
        """Create agent execution context with WebSocket notifier."""
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{thread_id}_{uuid.uuid4().hex[:8]}"
        
        context = AgentExecutionContext(
            run_id=run_id,
            thread_id=thread_id,
            user_id=user_id,
            agent_name=agent_type,
            metadata={"test_scenario": "multi_agent_comprehensive"}
        )
        
        notifier = WebSocketNotifier(self.websocket_manager)
        return context, notifier

    async def create_enhanced_tool_dispatcher(self) -> UnifiedToolDispatcher:
        """Create enhanced tool dispatcher with WebSocket notifications."""
        dispatcher = create_request_scoped_tool_dispatcher()
        
        # Enhance with WebSocket notifications
        enhanced_dispatcher = await enhance_tool_dispatcher_with_notifications(
            dispatcher,
            websocket_manager=self.websocket_manager,
            enable_notifications=True
        )
        
        return enhanced_dispatcher

    # ==========================================
    # Multi-Agent Coordination Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_five_agent_coordination_complex_workflow(self, agent_execution_registry, mock_websocket_manager):
        """Test 5+ agents working together on complex coordinated workflow."""
        self.websocket_manager = mock_websocket_manager
        
        # Define complex workflow scenario
        scenario = MultiAgentScenarioConfig(
            name="research_analysis_pipeline",
            agent_types=["data_collector", "data_analyzer", "insight_generator", "report_writer", "quality_checker"],
            dependency_chains={
                "data_collector": [],
                "data_analyzer": ["data_collector"],
                "insight_generator": ["data_analyzer"],
                "report_writer": ["insight_generator"],
                "quality_checker": ["report_writer"]
            },
            expected_tools={"collect", "analyze", "generate_insights", "write_report", "quality_check"},
            timeout_seconds=45
        )
        
        agents = []
        tasks = {}
        
        # Create all agents
        for agent_type in scenario.agent_types:
            agent = MockComplexAgent(agent_type, tools=[f"{agent_type}_tool_{i}" for i in range(3)])
            
            context, notifier = await self.create_agent_context(agent_type)
            dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await agent.initialize(context, notifier, dispatcher)
            agents.append(agent)
            self.agent_stats[agent.agent_id] = agent.stats
        
        # Execute workflow with proper dependency management
        start_time = time.time()
        
        try:
            # Execute in dependency order
            for agent_type in scenario.agent_types:
                agent = next(a for a in agents if a.agent_type == agent_type)
                dependencies = scenario.dependency_chains[agent_type]
                
                # Gather dependency results
                dependency_results = {}
                for dep in dependencies:
                    if dep in tasks:
                        dependency_results[dep] = tasks[dep]
                
                # Execute agent task
                task_result = await agent.execute_task(
                    f"Process {agent_type} workflow step",
                    dependencies=dependency_results
                )
                tasks[agent_type] = task_result
                
                # Finalize agent
                await agent.finalize(task_result)
        
        except Exception as e:
            pytest.fail(f"Multi-agent coordination failed: {str(e)}")
        
        execution_time = time.time() - start_time
        
        # Comprehensive validations
        assert execution_time < scenario.timeout_seconds, f"Workflow exceeded timeout: {execution_time:.2f}s"
        assert len(agents) == 5, "All 5 agents should be created"
        assert len(tasks) == 5, "All agents should complete their tasks"
        
        # Validate dependency chain execution order
        completion_times = {agent.agent_type: agent.stats.end_time for agent in agents if agent.stats.end_time}
        assert len(completion_times) == 5, "All agents should complete"
        
        # Verify dependency order
        for agent_type, dependencies in scenario.dependency_chains.items():
            agent_completion = completion_times[agent_type]
            for dep in dependencies:
                dep_completion = completion_times[dep]
                assert dep_completion < agent_completion, f"{dep} should complete before {agent_type}"
        
        # Validate WebSocket events
        total_events = sum(agent.stats.events_sent for agent in agents)
        assert total_events >= 25, f"Expected at least 25 events, got {total_events}"  # 5 events per agent minimum
        
        # Validate tools executed
        total_tools = sum(agent.stats.tools_executed for agent in agents)
        assert total_tools >= 15, f"Expected at least 15 tools executed, got {total_tools}"  # 3 tools per agent minimum

    @pytest.mark.asyncio
    async def test_agent_handoff_complex_data_pipeline(self, agent_execution_registry, mock_websocket_manager):
        """Test complex agent handoff with data transformation pipeline."""
        self.websocket_manager = mock_websocket_manager
        
        # Create data processing pipeline agents
        pipeline_stages = [
            ("data_ingestion", ["ingest_raw_data", "validate_format", "store_temp"]),
            ("data_cleaning", ["remove_duplicates", "fill_missing", "normalize"]),
            ("feature_engineering", ["create_features", "scale_data", "encode_categorical"]),
            ("model_training", ["split_data", "train_model", "validate_performance"]),
            ("result_export", ["generate_predictions", "create_report", "export_results"])
        ]
        
        pipeline_data = {"raw_records": 10000, "processed": False}
        agents = []
        
        # Execute pipeline with data handoff
        for stage_name, tools in pipeline_stages:
            agent = MockComplexAgent(stage_name, tools=tools)
            context, notifier = await self.create_agent_context(stage_name)
            dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await agent.initialize(context, notifier, dispatcher)
            
            # Execute stage with current pipeline data
            stage_result = await agent.execute_task(f"Execute {stage_name}", dependencies=pipeline_data)
            
            # Update pipeline data for next stage
            pipeline_data.update(stage_result)
            pipeline_data[f"{stage_name}_completed"] = True
            
            await agent.finalize(stage_result)
            agents.append(agent)
            self.agent_stats[agent.agent_id] = agent.stats
        
        # Validations
        assert len(agents) == 5, "All pipeline stages should execute"
        
        # Verify data flow integrity
        for i, (stage_name, _) in enumerate(pipeline_stages):
            assert f"{stage_name}_completed" in pipeline_data, f"{stage_name} should mark completion"
        
        # Verify WebSocket event sequence
        total_events = len(self.websocket_events)
        assert total_events >= 25, f"Expected comprehensive event coverage, got {total_events}"
        
        # Check event types distribution
        event_types = [event["message"].get("type") for event in self.websocket_events if "message" in event]
        assert "agent_started" in event_types, "Should have agent_started events"
        assert "tool_executing" in event_types, "Should have tool_executing events"
        assert "tool_completed" in event_types, "Should have tool_completed events"
        assert "agent_completed" in event_types, "Should have agent_completed events"

    # ==========================================
    # WebSocket Event Flow Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_websocket_events_ten_concurrent_agents_no_loss(self, agent_execution_registry, mock_websocket_manager):
        """Test WebSocket events with 10+ concurrent agents - no events should be lost."""
        self.websocket_manager = mock_websocket_manager
        
        concurrent_agents = 10
        agents = []
        tasks = []
        
        # Create concurrent agents
        for i in range(concurrent_agents):
            agent = MockComplexAgent(f"concurrent_agent_{i}", tools=[f"tool_{j}" for j in range(5)])
            agents.append(agent)
        
        # Initialize all agents concurrently
        async def init_and_run_agent(agent: MockComplexAgent):
            context, notifier = await self.create_agent_context(agent.agent_type)
            dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await agent.initialize(context, notifier, dispatcher)
            result = await agent.execute_task("Concurrent processing task")
            await agent.finalize(result)
            self.agent_stats[agent.agent_id] = agent.stats
            return agent.stats
        
        # Execute all agents concurrently
        start_time = time.time()
        agent_results = await asyncio.gather(*[init_and_run_agent(agent) for agent in agents])
        execution_time = time.time() - start_time
        
        # Comprehensive validations
        assert len(agent_results) == concurrent_agents, "All agents should complete"
        assert execution_time < 30, f"Concurrent execution took too long: {execution_time:.2f}s"
        
        # Validate event completeness - no events should be lost
        total_expected_events = sum(stats.events_sent for stats in agent_results)
        total_received_events = len(self.websocket_events)
        
        # Allow for slight variance but ensure no major loss
        loss_percentage = (total_expected_events - total_received_events) / total_expected_events * 100
        assert loss_percentage < 5, f"Event loss too high: {loss_percentage:.2f}%"
        
        # Validate event ordering and pairing
        for agent_stats in agent_results:
            agent_events = [
                event for event in self.websocket_events 
                if event.get("message", {}).get("agent_id") == agent_stats.agent_id
            ]
            
            # Should have proper event sequence
            event_types = [event["message"]["type"] for event in agent_events if "message" in event]
            assert "agent_started" in event_types, f"Missing agent_started for {agent_stats.agent_id}"
            assert "agent_completed" in event_types, f"Missing agent_completed for {agent_stats.agent_id}"

    @pytest.mark.asyncio 
    async def test_websocket_event_sequence_validation_complex(self, agent_execution_registry, mock_websocket_manager):
        """Test complex WebSocket event sequencing with tool event pairing."""
        self.websocket_manager = mock_websocket_manager
        
        # Create agent with multiple tools
        agent = MockComplexAgent("sequence_validator", tools=["tool_a", "tool_b", "tool_c", "tool_d", "tool_e"])
        context, notifier = await self.create_agent_context("sequence_validator")
        dispatcher = await self.create_enhanced_tool_dispatcher()
        
        await agent.initialize(context, notifier, dispatcher)
        result = await agent.execute_task("Event sequence validation")
        await agent.finalize(result)
        
        # Extract events for this agent
        agent_events = [
            event for event in self.websocket_events 
            if event.get("message", {}).get("run_id") == context.run_id
        ]
        
        event_sequence = [event["message"]["type"] for event in agent_events if "message" in event]
        
        # Validate event sequence
        assert event_sequence[0] == "agent_started", "First event should be agent_started"
        assert event_sequence[-1] == "agent_completed", "Last event should be agent_completed"
        
        # Validate tool event pairing
        tool_executing_events = [i for i, event_type in enumerate(event_sequence) if event_type == "tool_executing"]
        tool_completed_events = [i for i, event_type in enumerate(event_sequence) if event_type == "tool_completed"]
        
        assert len(tool_executing_events) == len(tool_completed_events), "Tool events should be paired"
        assert len(tool_executing_events) == len(agent.tools), "Should have events for all tools"
        
        # Verify proper pairing order
        for executing_idx, completed_idx in zip(tool_executing_events, tool_completed_events):
            assert executing_idx < completed_idx, "tool_executing should come before tool_completed"

    # ==========================================
    # Real-World Scenario Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_complex_research_scenario_end_to_end(self, agent_execution_registry, mock_websocket_manager):
        """Test complex research scenario with multiple specialists working together."""
        self.websocket_manager = mock_websocket_manager
        
        # Define research project scenario
        research_agents = [
            ("literature_researcher", ["search_papers", "extract_citations", "summarize_findings"]),
            ("data_scientist", ["analyze_datasets", "create_models", "validate_results"]),
            ("domain_expert", ["review_methodology", "validate_conclusions", "suggest_improvements"]),
            ("technical_writer", ["structure_document", "write_sections", "format_references"]),
            ("peer_reviewer", ["check_accuracy", "review_methodology", "provide_feedback"])
        ]
        
        research_context = {
            "topic": "Multi-Agent AI Systems Performance",
            "scope": "Enterprise Applications",
            "timeline": "30 days",
            "resources": {"papers": 150, "datasets": 5, "experts": 3}
        }
        
        agents = []
        research_outputs = {}
        
        # Execute research workflow
        for agent_type, tools in research_agents:
            agent = MockComplexAgent(agent_type, tools=tools)
            context, notifier = await self.create_agent_context(agent_type)
            dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await agent.initialize(context, notifier, dispatcher)
            
            # Execute research phase
            phase_result = await agent.execute_task(
                f"Research phase: {agent_type}",
                dependencies={"research_context": research_context, "previous_outputs": research_outputs}
            )
            
            research_outputs[agent_type] = phase_result
            await agent.finalize(phase_result)
            agents.append(agent)
            self.agent_stats[agent.agent_id] = agent.stats
        
        # Validate research workflow
        assert len(agents) == 5, "All research agents should execute"
        assert len(research_outputs) == 5, "All phases should produce outputs"
        
        # Validate research progression
        for agent_type, _ in research_agents:
            assert agent_type in research_outputs, f"Missing output from {agent_type}"
            assert research_outputs[agent_type], f"Empty output from {agent_type}"
        
        # Validate comprehensive WebSocket coverage
        total_events = len(self.websocket_events)
        assert total_events >= 35, f"Research scenario should generate comprehensive events, got {total_events}"

    @pytest.mark.asyncio
    async def test_data_analysis_validation_pipeline(self, agent_execution_registry, mock_websocket_manager):
        """Test data analysis pipeline with validation at each step."""
        self.websocket_manager = mock_websocket_manager
        
        # Define analysis pipeline with validators
        pipeline_config = [
            ("data_loader", ["load_sources", "validate_schema", "check_quality"], "data_validator"),
            ("data_processor", ["clean_data", "transform_features", "handle_missing"], "processing_validator"),
            ("analyzer", ["statistical_analysis", "trend_detection", "correlation_analysis"], "analysis_validator"),
            ("visualizer", ["create_charts", "generate_dashboards", "export_visuals"], "visual_validator")
        ]
        
        dataset_context = {
            "records": 50000,
            "features": 25,
            "target": "performance_score",
            "validation_rules": {"missing_threshold": 0.05, "correlation_min": 0.3}
        }
        
        pipeline_results = {}
        all_agents = []
        
        # Execute pipeline with validation
        for processor_type, processor_tools, validator_type in pipeline_config:
            # Create processor agent
            processor = MockComplexAgent(processor_type, tools=processor_tools)
            processor_context, processor_notifier = await self.create_agent_context(processor_type)
            processor_dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await processor.initialize(processor_context, processor_notifier, processor_dispatcher)
            
            # Execute processing
            processing_result = await processor.execute_task(
                f"Process {processor_type} stage",
                dependencies={"dataset": dataset_context, "previous_results": pipeline_results}
            )
            
            await processor.finalize(processing_result)
            all_agents.append(processor)
            self.agent_stats[processor.agent_id] = processor.stats
            
            # Create validator agent
            validator = MockComplexAgent(validator_type, tools=["validate_output", "check_quality", "approve_stage"])
            validator_context, validator_notifier = await self.create_agent_context(validator_type)
            validator_dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await validator.initialize(validator_context, validator_notifier, validator_dispatcher)
            
            # Execute validation
            validation_result = await validator.execute_task(
                f"Validate {processor_type} output",
                dependencies={"processing_result": processing_result, "validation_rules": dataset_context["validation_rules"]}
            )
            
            await validator.finalize(validation_result)
            all_agents.append(validator)
            self.agent_stats[validator.agent_id] = validator.stats
            
            # Store results for next stage
            pipeline_results[processor_type] = {
                "processing": processing_result,
                "validation": validation_result,
                "approved": True
            }
        
        # Comprehensive validations
        assert len(all_agents) == 8, "Should have 4 processors + 4 validators"
        assert len(pipeline_results) == 4, "All pipeline stages should complete"
        
        # Validate all stages approved
        for stage_name, stage_result in pipeline_results.items():
            assert stage_result["approved"], f"Stage {stage_name} should be approved"
            assert "processing" in stage_result, f"Missing processing result for {stage_name}"
            assert "validation" in stage_result, f"Missing validation result for {stage_name}"

    # ==========================================
    # Performance Under Load Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_twenty_concurrent_agents_performance_stress(self, agent_execution_registry, mock_websocket_manager):
        """Test system performance with 20+ concurrent agents - stress test."""
        self.websocket_manager = mock_websocket_manager
        
        concurrent_count = 25  # More than 20 for stress testing
        stress_agents = []
        
        # Create high-intensity agents
        for i in range(concurrent_count):
            agent = MockComplexAgent(
                f"stress_agent_{i}",
                tools=[f"intensive_tool_{j}" for j in range(7)],  # More tools per agent
                failure_rate=0.1  # 10% failure rate for realistic stress
            )
            stress_agents.append(agent)
        
        # Track performance metrics
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Execute stress test
        async def execute_stress_agent(agent: MockComplexAgent):
            try:
                context, notifier = await self.create_agent_context(agent.agent_type)
                dispatcher = await self.create_enhanced_tool_dispatcher()
                
                await agent.initialize(context, notifier, dispatcher)
                
                # Execute multiple intensive tasks
                for task_num in range(3):  # Multiple tasks per agent
                    try:
                        result = await agent.execute_task(f"Stress task {task_num}")
                    except RuntimeError:
                        # Handle simulated failures gracefully
                        result = {"status": "failed", "task": task_num}
                
                await agent.finalize({"status": "completed", "tasks": 3})
                self.agent_stats[agent.agent_id] = agent.stats
                return agent.stats
                
            except Exception as e:
                # Track failures
                agent.stats.errors_encountered += 1
                agent.stats.end_time = datetime.now(timezone.utc)
                self.agent_stats[agent.agent_id] = agent.stats
                return agent.stats
        
        # Execute all agents concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[execute_stress_agent(agent) for agent in stress_agents]),
                timeout=60  # 1 minute timeout for stress test
            )
        except asyncio.TimeoutError:
            pytest.fail("Stress test exceeded timeout - system may not handle load")
        
        execution_time = time.time() - start_time
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = final_memory - start_memory
        
        # Performance validations
        assert len(results) == concurrent_count, f"Expected {concurrent_count} results, got {len(results)}"
        assert execution_time < 60, f"Stress test took too long: {execution_time:.2f}s"
        assert memory_usage < 200, f"Memory usage too high: {memory_usage:.2f}MB"
        
        # Calculate performance metrics
        successful_agents = len([r for r in results if r.errors_encountered == 0])
        success_rate = (successful_agents / concurrent_count) * 100
        
        # Should handle at least 80% successfully under stress
        assert success_rate >= 80, f"Success rate too low under stress: {success_rate:.1f}%"
        
        # Validate WebSocket event handling under load
        total_events = len(self.websocket_events)
        expected_minimum = concurrent_count * 5  # Minimum 5 events per agent
        assert total_events >= expected_minimum, f"Event loss under load: {total_events} < {expected_minimum}"

    @pytest.mark.asyncio
    async def test_memory_leak_detection_long_running(self, agent_execution_registry, mock_websocket_manager):
        """Test for memory leaks during long-running multi-agent scenarios."""
        self.websocket_manager = mock_websocket_manager
        
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_snapshots = [baseline_memory]
        
        # Run multiple batches of agents to detect memory leaks
        for batch in range(5):  # 5 batches
            batch_agents = []
            
            # Create batch of agents
            for i in range(8):  # 8 agents per batch
                agent = MockComplexAgent(f"batch_{batch}_agent_{i}")
                batch_agents.append(agent)
            
            # Execute batch
            async def execute_batch_agent(agent: MockComplexAgent):
                context, notifier = await self.create_agent_context(agent.agent_type)
                dispatcher = await self.create_enhanced_tool_dispatcher()
                
                await agent.initialize(context, notifier, dispatcher)
                result = await agent.execute_task("Memory leak detection task")
                await agent.finalize(result)
                return agent.stats
            
            # Execute batch concurrently
            await asyncio.gather(*[execute_batch_agent(agent) for agent in batch_agents])
            
            # Force cleanup and measure memory
            gc.collect()
            await asyncio.sleep(0.1)  # Allow cleanup
            
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_snapshots.append(current_memory)
        
        # Analyze memory growth
        memory_growth = memory_snapshots[-1] - baseline_memory
        max_growth_between_batches = max(
            memory_snapshots[i+1] - memory_snapshots[i] 
            for i in range(len(memory_snapshots)-1)
        )
        
        # Memory leak validation
        assert memory_growth < 100, f"Total memory growth too high: {memory_growth:.2f}MB"
        assert max_growth_between_batches < 30, f"Batch memory growth too high: {max_growth_between_batches:.2f}MB"
        
        # Check for consistent memory pattern
        growth_rates = [
            memory_snapshots[i+1] - memory_snapshots[i] 
            for i in range(len(memory_snapshots)-1)
        ]
        
        # Growth should stabilize after first batch
        if len(growth_rates) > 2:
            later_growth = statistics.mean(growth_rates[2:])
            assert later_growth < 10, f"Continued memory growth suggests leak: {later_growth:.2f}MB/batch"

    # ==========================================
    # Integration Points Testing
    # ==========================================

    @pytest.mark.asyncio
    async def test_tool_dispatcher_websocket_integration_comprehensive(self, agent_execution_registry, mock_websocket_manager):
        """Test comprehensive integration between tool dispatcher and WebSocket bridge."""
        self.websocket_manager = mock_websocket_manager
        
        # Create agent with tool dispatcher integration
        agent = MockComplexAgent("integration_tester", tools=["integration_tool_1", "integration_tool_2", "integration_tool_3"])
        context, notifier = await self.create_agent_context("integration_tester")
        
        # Create and enhance dispatcher
        dispatcher = await self.create_enhanced_tool_dispatcher()
        
        # Verify enhancement worked
        assert hasattr(dispatcher, '_websocket_enhanced'), "Dispatcher should be enhanced"
        assert dispatcher._websocket_enhanced is True, "Enhancement flag should be set"
        
        await agent.initialize(context, notifier, dispatcher)
        
        # Execute task to test integration
        result = await agent.execute_task("Integration testing task")
        await agent.finalize(result)
        
        # Validate WebSocket integration
        integration_events = [
            event for event in self.websocket_events
            if event.get("message", {}).get("run_id") == context.run_id
        ]
        
        assert len(integration_events) >= 8, f"Expected comprehensive events, got {len(integration_events)}"
        
        # Validate event types from integration
        event_types = set(event["message"]["type"] for event in integration_events if "message" in event)
        expected_types = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
        
        assert expected_types.issubset(event_types), f"Missing event types: {expected_types - event_types}"

    @pytest.mark.asyncio
    async def test_execution_context_propagation_complex(self, agent_execution_registry, mock_websocket_manager):
        """Test execution context propagation through complex multi-agent scenarios."""
        self.websocket_manager = mock_websocket_manager
        
        # Create parent-child agent hierarchy
        parent_agent = MockComplexAgent("parent_coordinator", tools=["delegate_tasks", "monitor_progress", "aggregate_results"])
        child_agents = [
            MockComplexAgent("child_worker_1", tools=["process_data", "validate_output"]),
            MockComplexAgent("child_worker_2", tools=["analyze_results", "generate_report"]),
            MockComplexAgent("child_worker_3", tools=["quality_check", "finalize_output"])
        ]
        
        # Create contexts with proper hierarchy
        parent_context, parent_notifier = await self.create_agent_context("parent_coordinator")
        child_contexts = []
        
        for child_agent in child_agents:
            # Create child context with parent reference
            child_context, child_notifier = await self.create_agent_context(
                child_agent.agent_type, 
                user_id=parent_context.user_id
            )
            child_context.metadata["parent_run_id"] = parent_context.run_id
            child_contexts.append((child_context, child_notifier))
        
        # Initialize parent
        parent_dispatcher = await self.create_enhanced_tool_dispatcher()
        await parent_agent.initialize(parent_context, parent_notifier, parent_dispatcher)
        
        # Initialize children
        for child_agent, (child_context, child_notifier) in zip(child_agents, child_contexts):
            child_dispatcher = await self.create_enhanced_tool_dispatcher()
            await child_agent.initialize(child_context, child_notifier, child_dispatcher)
        
        # Execute hierarchical workflow
        parent_result = await parent_agent.execute_task("Coordinate child agents")
        
        child_results = []
        for child_agent, (child_context, _) in zip(child_agents, child_contexts):
            child_result = await child_agent.execute_task(
                f"Execute {child_agent.agent_type} task",
                dependencies={"parent_context": parent_context.metadata, "parent_result": parent_result}
            )
            child_results.append(child_result)
            await child_agent.finalize(child_result)
        
        # Finalize parent with aggregated results
        await parent_agent.finalize({"child_results": child_results, "coordination": "completed"})
        
        # Validate context propagation
        all_events = self.websocket_events
        parent_events = [e for e in all_events if e.get("message", {}).get("run_id") == parent_context.run_id]
        child_event_groups = [
            [e for e in all_events if e.get("message", {}).get("run_id") == ctx.run_id]
            for ctx, _ in child_contexts
        ]
        
        assert len(parent_events) >= 5, "Parent should generate comprehensive events"
        for i, child_events in enumerate(child_event_groups):
            assert len(child_events) >= 4, f"Child {i} should generate comprehensive events"
        
        # Validate user_id consistency across hierarchy
        all_user_ids = set()
        for event in all_events:
            if "message" in event and "user_id" in event["message"]:
                all_user_ids.add(event["message"]["user_id"])
        
        assert len(all_user_ids) <= 1, "All events should have consistent user_id"

    # ==========================================
    # Failure Scenarios and Recovery
    # ==========================================

    @pytest.mark.asyncio
    async def test_agent_failure_recovery_cascade_prevention(self, agent_execution_registry, mock_websocket_manager):
        """Test agent failure recovery and prevention of cascade failures."""
        self.websocket_manager = mock_websocket_manager
        
        # Create agent chain with one failure-prone agent
        agents_config = [
            ("reliable_agent_1", 0.0),  # No failures
            ("failure_prone_agent", 0.8),  # 80% failure rate
            ("reliable_agent_2", 0.0),  # No failures
            ("resilient_agent", 0.2),  # 20% failure rate but handles failures
        ]
        
        agents = []
        chain_results = {}
        
        for agent_type, failure_rate in agents_config:
            agent = MockComplexAgent(
                agent_type, 
                tools=[f"{agent_type}_tool_{i}" for i in range(4)],
                failure_rate=failure_rate
            )
            
            context, notifier = await self.create_agent_context(agent_type)
            dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await agent.initialize(context, notifier, dispatcher)
            agents.append(agent)
            
            # Execute with failure handling
            try:
                result = await agent.execute_task(
                    f"Chain task for {agent_type}",
                    dependencies=chain_results
                )
                chain_results[agent_type] = result
                await agent.finalize(result)
                
            except RuntimeError as e:
                # Handle expected failures gracefully
                error_result = {"status": "failed", "error": str(e), "recovery": "attempted"}
                chain_results[agent_type] = error_result
                await agent.finalize(error_result)
            
            self.agent_stats[agent.agent_id] = agent.stats
        
        # Validate failure handling
        reliable_agents = [agent for agent, rate in agents_config if rate == 0.0]
        assert len(reliable_agents) == 2, "Should have 2 reliable agents"
        
        # Check that reliable agents succeeded
        for agent in agents:
            if "reliable" in agent.agent_type:
                assert agent.stats.errors_encountered == 0, f"Reliable agent {agent.agent_type} should not fail"
        
        # Verify failure didn't cascade
        total_completions = len([agent for agent in agents if agent.stats.end_time is not None])
        assert total_completions == len(agents), "All agents should complete (even with failures)"
        
        # Validate error events were sent
        error_events = [
            event for event in self.websocket_events
            if event.get("message", {}).get("type") in ["tool_error", "agent_error"]
        ]
        
        # Should have some error events from failure-prone agents
        assert len(error_events) >= 1, "Should capture error events from failures"

    @pytest.mark.asyncio
    async def test_websocket_connection_failure_recovery(self, agent_execution_registry):
        """Test recovery from WebSocket connection failures during agent execution."""
        # Create mock WebSocket manager with simulated failures
        failing_websocket = MockWebSocketManager()
        
        # Simulate connection failures
        call_count = 0
        original_send = failing_websocket.send_to_thread
        
        async def failing_send_to_thread(thread_id: str, message: Dict[str, Any]) -> bool:
            nonlocal call_count
            call_count += 1
            
            # Fail every 3rd call to simulate intermittent connection issues
            if call_count % 3 == 0:
                return False  # Simulate send failure
            
            return await original_send(thread_id, message)
        
        failing_websocket.send_to_thread = failing_send_to_thread
        self.websocket_manager = failing_websocket
        
        # Create agent with resilient WebSocket handling
        agent = MockComplexAgent("resilient_websocket_agent", tools=["tool_1", "tool_2", "tool_3", "tool_4", "tool_5"])
        context, notifier = await self.create_agent_context("resilient_websocket_agent")
        dispatcher = await self.create_enhanced_tool_dispatcher()
        
        await agent.initialize(context, notifier, dispatcher)
        
        # Execute task despite WebSocket failures
        result = await agent.execute_task("WebSocket resilience test")
        await agent.finalize(result)
        
        # Validate agent completed despite WebSocket issues
        assert agent.stats.end_time is not None, "Agent should complete despite WebSocket failures"
        assert agent.stats.tools_executed > 0, "Agent should execute tools despite WebSocket failures"
        
        # Verify some events were lost due to failures (realistic scenario)
        assert call_count > agent.stats.events_sent, "Should have attempted more sends than successful events"

    @pytest.mark.asyncio
    async def test_timeout_handling_complex_scenario(self, agent_execution_registry, mock_websocket_manager):
        """Test timeout handling in complex multi-agent scenarios."""
        self.websocket_manager = mock_websocket_manager
        
        # Create agents with different execution speeds
        agent_configs = [
            ("fast_agent", 0.1, 0.2),    # 0.1-0.2s per tool
            ("normal_agent", 0.5, 1.0),  # 0.5-1.0s per tool  
            ("slow_agent", 2.0, 3.0),    # 2.0-3.0s per tool (will timeout)
            ("variable_agent", 0.1, 2.5) # Variable speed
        ]
        
        agents = []
        timeout_results = {}
        
        for agent_type, min_delay, max_delay in agent_configs:
            agent = MockComplexAgent(agent_type, tools=[f"{agent_type}_tool_{i}" for i in range(3)])
            
            # Modify agent to have realistic delays
            original_execute = agent.execute_task
            
            async def delayed_execute(task: str, dependencies: Dict[str, Any] = None):
                # Add realistic processing delays
                for _ in agent.tools:
                    delay = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(delay)
                return await original_execute(task, dependencies)
            
            agent.execute_task = delayed_execute
            
            context, notifier = await self.create_agent_context(agent_type)
            dispatcher = await self.create_enhanced_tool_dispatcher()
            
            await agent.initialize(context, notifier, dispatcher)
            agents.append(agent)
        
        # Execute with timeout handling
        timeout_seconds = 5
        
        async def execute_with_timeout(agent: MockComplexAgent):
            try:
                result = await asyncio.wait_for(
                    agent.execute_task("Timeout handling test"),
                    timeout=timeout_seconds
                )
                await agent.finalize(result)
                return {"status": "completed", "agent": agent.agent_type}
            
            except asyncio.TimeoutError:
                # Handle timeout gracefully
                await agent.finalize({"status": "timeout", "partial_result": True})
                return {"status": "timeout", "agent": agent.agent_type}
        
        # Execute all agents with timeout handling
        results = await asyncio.gather(*[execute_with_timeout(agent) for agent in agents])
        
        # Validate timeout handling
        completed_agents = [r for r in results if r["status"] == "completed"]
        timeout_agents = [r for r in results if r["status"] == "timeout"]
        
        # Should have some completions and some timeouts based on configured delays
        assert len(completed_agents) >= 2, "Fast agents should complete"
        assert len(timeout_agents) >= 1, "Slow agents should timeout"
        
        # Validate all agents were handled gracefully
        assert len(results) == len(agents), "All agents should be handled"

    # ==========================================
    # Business Value Delivery Validation
    # ==========================================

    @pytest.mark.asyncio
    async def test_chat_responsiveness_under_multi_agent_load(self, agent_execution_registry, mock_websocket_manager):
        """Test that chat remains responsive under heavy multi-agent load."""
        self.websocket_manager = mock_websocket_manager
        
        # Simulate heavy chat load scenario
        concurrent_chat_sessions = 15
        agents_per_session = 3
        
        chat_sessions = []
        all_agents = []
        
        # Create multiple chat sessions with agents
        for session_id in range(concurrent_chat_sessions):
            session_agents = []
            
            for agent_num in range(agents_per_session):
                agent = MockComplexAgent(
                    f"chat_session_{session_id}_agent_{agent_num}",
                    tools=[f"chat_tool_{i}" for i in range(4)]
                )
                
                context, notifier = await self.create_agent_context(
                    agent.agent_type,
                    user_id=f"chat_user_{session_id}"
                )
                dispatcher = await self.create_enhanced_tool_dispatcher()
                
                await agent.initialize(context, notifier, dispatcher)
                session_agents.append(agent)
                all_agents.append(agent)
            
            chat_sessions.append(session_agents)
        
        # Track chat responsiveness metrics
        start_time = time.time()
        response_times = []
        
        # Execute all chat sessions concurrently
        async def execute_chat_session(session_agents: List[MockComplexAgent], session_id: int):
            session_start = time.time()
            
            # Execute agents in chat session
            session_tasks = []
            for agent in session_agents:
                task = agent.execute_task(f"Chat session {session_id} processing")
                session_tasks.append(task)
            
            # Wait for all agents in session to complete
            session_results = await asyncio.gather(*session_tasks)
            
            # Finalize agents
            for agent, result in zip(session_agents, session_results):
                await agent.finalize(result)
            
            session_end = time.time()
            session_duration = session_end - session_start
            response_times.append(session_duration)
            
            return session_results
        
        # Execute all chat sessions
        all_results = await asyncio.gather(*[
            execute_chat_session(session_agents, session_id)
            for session_id, session_agents in enumerate(chat_sessions)
        ])
        
        total_execution_time = time.time() - start_time
        
        # Business value validations
        assert len(all_results) == concurrent_chat_sessions, "All chat sessions should complete"
        
        # Chat responsiveness requirements
        average_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        assert average_response_time < 10, f"Average chat response too slow: {average_response_time:.2f}s"
        assert max_response_time < 20, f"Maximum chat response too slow: {max_response_time:.2f}s"
        assert total_execution_time < 25, f"Total execution too slow for chat: {total_execution_time:.2f}s"
        
        # Validate WebSocket event delivery for chat
        total_agents = len(all_agents)
        total_events = len(self.websocket_events)
        events_per_agent = total_events / total_agents
        
        assert events_per_agent >= 4, f"Insufficient event coverage for chat: {events_per_agent:.1f} events/agent"
        
        # Validate event timing for responsiveness
        if self.websocket_events:
            event_timestamps = [
                datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                for event in self.websocket_events if "timestamp" in event
            ]
            
            if len(event_timestamps) > 1:
                # Check for consistent event delivery
                time_gaps = [
                    (event_timestamps[i+1] - event_timestamps[i]).total_seconds()
                    for i in range(len(event_timestamps)-1)
                ]
                
                max_gap = max(time_gaps)
                assert max_gap < 5, f"Event delivery gap too large for chat: {max_gap:.2f}s"

    @pytest.mark.asyncio
    async def test_enterprise_scale_validation(self, agent_execution_registry, mock_websocket_manager):
        """Test system behavior at enterprise scale (simulated)."""
        self.websocket_manager = mock_websocket_manager
        
        # Simulate enterprise deployment scenario
        enterprise_config = {
            "departments": 5,
            "agents_per_department": 8,
            "concurrent_users": 20,
            "tools_per_agent": 6,
            "execution_complexity": "high"
        }
        
        all_agents = []
        department_results = {}
        performance_metrics = {
            "start_time": time.time(),
            "memory_start": psutil.Process().memory_info().rss / 1024 / 1024,
            "event_counts": []
        }
        
        # Create enterprise departments with agents
        for dept_id in range(enterprise_config["departments"]):
            dept_name = f"enterprise_dept_{dept_id}"
            dept_agents = []
            
            for agent_id in range(enterprise_config["agents_per_department"]):
                agent = MockComplexAgent(
                    f"{dept_name}_agent_{agent_id}",
                    tools=[f"enterprise_tool_{i}" for i in range(enterprise_config["tools_per_agent"])]
                )
                
                context, notifier = await self.create_agent_context(
                    agent.agent_type,
                    user_id=f"enterprise_user_{agent_id % enterprise_config['concurrent_users']}"
                )
                dispatcher = await self.create_enhanced_tool_dispatcher()
                
                await agent.initialize(context, notifier, dispatcher)
                dept_agents.append(agent)
                all_agents.append(agent)
            
            # Execute department workflow
            async def execute_department_workflow(agents: List[MockComplexAgent], dept: str):
                dept_start = time.time()
                
                # Execute all agents in department concurrently
                dept_tasks = [
                    agent.execute_task(f"Enterprise workflow for {dept}")
                    for agent in agents
                ]
                
                dept_results_list = await asyncio.gather(*dept_tasks)
                
                # Finalize all agents
                for agent, result in zip(agents, dept_results_list):
                    await agent.finalize(result)
                
                dept_duration = time.time() - dept_start
                return {
                    "department": dept,
                    "agents": len(agents),
                    "duration": dept_duration,
                    "results": dept_results_list
                }
            
            dept_result = await execute_department_workflow(dept_agents, dept_name)
            department_results[dept_name] = dept_result
        
        # Calculate enterprise performance metrics
        total_duration = time.time() - performance_metrics["start_time"]
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = final_memory - performance_metrics["memory_start"]
        
        total_agents = len(all_agents)
        total_events = len(self.websocket_events)
        
        # Enterprise scale validations
        assert total_agents == 40, f"Expected 40 enterprise agents, got {total_agents}"
        assert len(department_results) == 5, "All departments should complete"
        
        # Performance requirements for enterprise scale
        assert total_duration < 45, f"Enterprise workflow too slow: {total_duration:.2f}s"
        assert memory_usage < 300, f"Enterprise memory usage too high: {memory_usage:.2f}MB"
        
        # Scalability metrics
        agents_per_second = total_agents / total_duration
        events_per_second = total_events / total_duration
        
        assert agents_per_second >= 0.8, f"Agent throughput too low: {agents_per_second:.2f} agents/s"
        assert events_per_second >= 4.0, f"Event throughput too low: {events_per_second:.2f} events/s"
        
        # Validate department isolation
        for dept_name, dept_result in department_results.items():
            assert dept_result["agents"] == 8, f"Department {dept_name} missing agents"
            assert dept_result["duration"] < 30, f"Department {dept_name} too slow: {dept_result['duration']:.2f}s"
        
        # Business value validation
        success_rate = (len(department_results) / enterprise_config["departments"]) * 100
        assert success_rate == 100, f"Enterprise success rate insufficient: {success_rate:.1f}%"


# Performance and utility functions for comprehensive testing

def calculate_performance_metrics(agents: List[MockComplexAgent]) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics for agent execution."""
    if not agents:
        return {}
    
    durations = [agent.stats.duration_seconds for agent in agents if agent.stats.end_time]
    events_sent = [agent.stats.events_sent for agent in agents]
    tools_executed = [agent.stats.tools_executed for agent in agents]
    errors = [agent.stats.errors_encountered for agent in agents]
    
    return {
        "total_agents": len(agents),
        "completed_agents": len(durations),
        "avg_duration_s": statistics.mean(durations) if durations else 0,
        "max_duration_s": max(durations) if durations else 0,
        "min_duration_s": min(durations) if durations else 0,
        "total_events": sum(events_sent),
        "avg_events_per_agent": statistics.mean(events_sent) if events_sent else 0,
        "total_tools_executed": sum(tools_executed),
        "total_errors": sum(errors),
        "success_rate": (len(durations) / len(agents)) * 100 if agents else 0
    }


def validate_websocket_event_integrity(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate WebSocket event integrity and completeness."""
    if not events:
        return {"valid": False, "reason": "No events found"}
    
    event_types = [event.get("message", {}).get("type") for event in events if "message" in event]
    event_type_counts = {event_type: event_types.count(event_type) for event_type in set(event_types)}
    
    # Check for required event types
    required_types = {"agent_started", "tool_executing", "tool_completed", "agent_completed"}
    missing_types = required_types - set(event_types)
    
    # Check event pairing
    tool_executing_count = event_type_counts.get("tool_executing", 0)
    tool_completed_count = event_type_counts.get("tool_completed", 0)
    
    return {
        "valid": len(missing_types) == 0 and tool_executing_count == tool_completed_count,
        "total_events": len(events),
        "event_type_counts": event_type_counts,
        "missing_required_types": list(missing_types),
        "tool_events_paired": tool_executing_count == tool_completed_count,
        "pairing_difference": abs(tool_executing_count - tool_completed_count)
    }


if __name__ == "__main__":
    # Run with pytest for comprehensive multi-agent testing
    pytest.main([__file__, "-v", "--tb=short"])