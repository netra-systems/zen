"""
Integration tests for long-running agent streaming scenarios - Issue #341

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Complex analytical workflows
- Business Goal: System Reliability - Support extended agent processing
- Value Impact: Enables complex business analytics without timeout failures
- Revenue Impact: Unlocks $500K+ ARR from enterprise analytical use cases

CRITICAL ISSUE #341:
Current problem: 60s agent execution timeouts fail for complex analytical workflows
Target solution: 60s→300s timeout progression for extended processing
Test Strategy: Integration tests with simulated long-running agents (NO Docker)

REQUIREMENTS:
- NO Docker dependencies (integration tests without containers)
- Tests initially FAIL demonstrating current 60s timeout limitation
- Follow SSOT test patterns from test_framework  
- Simulate realistic long-running analytical workflows
- Test timeout coordination between WebSocket and agent execution
"""

import pytest
import asyncio
import time
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.timeout_configuration import (
    get_websocket_recv_timeout,
    get_agent_execution_timeout,
    get_timeout_config,
    reset_timeout_manager
)

# Mock agent execution components for integration testing
try:
    from netra_backend.app.agents.base_agent import BaseAgent, AgentState
    from netra_backend.app.core.agent_execution_tracker import ExecutionState
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    REAL_IMPORTS_AVAILABLE = True
except ImportError:
    # Handle gracefully for test isolation
    BaseAgent = Mock
    AgentState = Mock
    ExecutionState = Mock
    UserExecutionContext = Mock
    REAL_IMPORTS_AVAILABLE = False


@dataclass
class StreamingEvent:
    """Simulated streaming event for testing."""
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    processing_time: float = 0.0


class MockLongRunningAgent:
    """Mock agent that simulates long-running analytical processing."""
    
    def __init__(self, processing_duration: int = 120, streaming_interval: float = 5.0):
        """
        Initialize mock long-running agent.
        
        Args:
            processing_duration: Total processing time in seconds
            streaming_interval: Interval between streaming updates
        """
        self.processing_duration = processing_duration
        self.streaming_interval = streaming_interval
        self.events_sent = []
        self.is_running = False
        self.start_time = None
        
    async def run_analytical_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate long-running analytical workflow with streaming updates.
        
        This represents complex business scenarios like:
        - Financial analysis reports (4+ minutes)
        - Supply chain optimization (3+ minutes)  
        - Customer behavior analytics (5+ minutes)
        """
        self.is_running = True
        self.start_time = time.time()
        
        # Simulate phases of complex analytical workflow
        phases = [
            {"name": "Data Collection", "duration": self.processing_duration * 0.2},
            {"name": "Data Processing", "duration": self.processing_duration * 0.3},
            {"name": "Pattern Analysis", "duration": self.processing_duration * 0.3},
            {"name": "Report Generation", "duration": self.processing_duration * 0.2}
        ]
        
        results = {"phases_completed": [], "streaming_events": []}
        
        for phase in phases:
            phase_start = time.time()
            
            # Send streaming update at phase start
            event = StreamingEvent(
                event_type="phase_started",
                timestamp=time.time(),
                data={
                    "phase": phase["name"],
                    "expected_duration": phase["duration"],
                    "total_progress": len(results["phases_completed"]) / len(phases)
                }
            )
            self.events_sent.append(event)
            results["streaming_events"].append(event)
            
            # Simulate phase processing with periodic updates
            elapsed = 0
            while elapsed < phase["duration"]:
                # Wait for next streaming interval or until phase completes
                wait_time = min(self.streaming_interval, phase["duration"] - elapsed)
                await asyncio.sleep(wait_time)
                elapsed = time.time() - phase_start
                
                # Send progress update
                progress_event = StreamingEvent(
                    event_type="phase_progress", 
                    timestamp=time.time(),
                    data={
                        "phase": phase["name"],
                        "phase_progress": min(elapsed / phase["duration"], 1.0),
                        "total_progress": (len(results["phases_completed"]) + elapsed/phase["duration"]) / len(phases),
                        "elapsed_time": time.time() - self.start_time
                    }
                )
                self.events_sent.append(progress_event)
                results["streaming_events"].append(progress_event)
            
            # Mark phase completed
            results["phases_completed"].append({
                "name": phase["name"],
                "duration": time.time() - phase_start,
                "completed_at": time.time()
            })
        
        # Final completion event
        completion_event = StreamingEvent(
            event_type="workflow_completed",
            timestamp=time.time(),
            data={
                "total_duration": time.time() - self.start_time,
                "phases_completed": len(results["phases_completed"]),
                "events_sent": len(self.events_sent),
                "success": True
            },
            processing_time=time.time() - self.start_time
        )
        self.events_sent.append(completion_event)
        results["streaming_events"].append(completion_event)
        
        self.is_running = False
        return results


class TestLongRunningAgentStreaming(SSotAsyncTestCase):
    """Integration tests for long-running agent streaming scenarios."""
    
    def setup_method(self, method=None):
        """Setup each test with fresh state."""
        super().setup_method(method)
        reset_timeout_manager()
        self.record_metric("test_setup_completed", True)
        
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        reset_timeout_manager()
        super().teardown_method(method)
    
    @pytest.mark.asyncio
    async def test_current_timeout_blocks_financial_analysis_workflow(self):
        """
        Test that current timeouts block realistic financial analysis workflows.
        
        This test should INITIALLY FAIL, proving Issue #341 affects real business scenarios.
        Financial analysis typically requires 4+ minutes for complex multi-source data processing.
        """
        self.set_env_var("ENVIRONMENT", "staging")  # Test in staging environment
        
        # Financial analysis workflow requirements
        FINANCIAL_ANALYSIS_DURATION = 240  # 4 minutes for complex financial analysis
        STREAMING_INTERVAL = 10.0  # Updates every 10 seconds
        
        # Get current timeout configuration
        current_agent_timeout = get_agent_execution_timeout()
        current_websocket_timeout = get_websocket_recv_timeout()
        
        self.record_metric("current_agent_timeout", current_agent_timeout) 
        self.record_metric("current_websocket_timeout", current_websocket_timeout)
        self.record_metric("required_financial_analysis_duration", FINANCIAL_ANALYSIS_DURATION)
        
        # Create mock financial analysis agent
        financial_agent = MockLongRunningAgent(
            processing_duration=FINANCIAL_ANALYSIS_DURATION,
            streaming_interval=STREAMING_INTERVAL
        )
        
        # Test execution with current timeout constraints
        start_time = time.time()
        execution_failed = False
        timeout_error = None
        
        try:
            # Simulate agent execution with current timeout
            workflow_result = await self.run_with_timeout(
                financial_agent.run_analytical_workflow({
                    "analysis_type": "financial_analysis",
                    "data_sources": ["balance_sheet", "income_statement", "cash_flow", "market_data"],
                    "complexity": "high"
                }),
                timeout=current_agent_timeout  # Use current inadequate timeout
            )
            
            # If we get here without timeout, record success (unexpected initially)
            execution_time = time.time() - start_time
            self.record_metric("financial_analysis_execution_time", execution_time)
            self.record_metric("financial_analysis_events_sent", len(financial_agent.events_sent))
            
        except asyncio.TimeoutError as e:
            execution_failed = True
            timeout_error = str(e)
            execution_time = time.time() - start_time
            
            self.record_metric("financial_analysis_timeout_occurred", True)
            self.record_metric("financial_analysis_timeout_duration", execution_time)
            self.record_metric("financial_analysis_events_before_timeout", len(financial_agent.events_sent))
        
        # CRITICAL ASSERTION: Current timeout should be inadequate (initially FAIL)
        assert execution_failed, (
            f"Issue #341 VALIDATION FAILED: Financial analysis completed in {execution_time:.1f}s "
            f"within current {current_agent_timeout}s timeout. Expected timeout failure to prove issue exists. "
            f"Either current timeout is adequate (issue resolved) or test simulation too fast."
        )
        
        # Validate that timeout occurred before analysis completion
        assert execution_time < FINANCIAL_ANALYSIS_DURATION, (
            f"Timeout occurred at {execution_time:.1f}s, expected < {FINANCIAL_ANALYSIS_DURATION}s"
        )
        
        # Record business impact
        self.record_metric("business_scenario_blocked", "Financial Analysis Report")
        self.record_metric("timeout_constraint_confirmed", True)
    
    @pytest.mark.asyncio
    async def test_supply_chain_optimization_timeout_failure(self):
        """
        Test supply chain optimization workflow fails due to current timeout constraints.
        
        This test should INITIALLY FAIL, demonstrating Issue #341 impact on supply chain analytics.
        """
        self.set_env_var("ENVIRONMENT", "staging")
        
        # Supply chain optimization requirements
        SUPPLY_CHAIN_DURATION = 180  # 3 minutes for supply chain optimization
        STREAMING_INTERVAL = 8.0     # Updates every 8 seconds
        
        current_agent_timeout = get_agent_execution_timeout()
        
        # Create supply chain optimization agent
        supply_chain_agent = MockLongRunningAgent(
            processing_duration=SUPPLY_CHAIN_DURATION,
            streaming_interval=STREAMING_INTERVAL
        )
        
        start_time = time.time()
        execution_failed = False
        
        try:
            workflow_result = await self.run_with_timeout(
                supply_chain_agent.run_analytical_workflow({
                    "optimization_type": "supply_chain",
                    "variables": ["inventory", "demand", "shipping", "costs", "suppliers"],
                    "complexity": "medium-high",
                    "geographical_scope": "multi_region"
                }),
                timeout=current_agent_timeout
            )
            
            execution_time = time.time() - start_time
            self.record_metric("supply_chain_execution_time", execution_time)
            
        except asyncio.TimeoutError:
            execution_failed = True
            execution_time = time.time() - start_time
            self.record_metric("supply_chain_timeout_occurred", True)
            self.record_metric("supply_chain_timeout_duration", execution_time)
        
        # Should fail due to current timeout constraints (initially)
        assert execution_failed, (
            f"Supply chain optimization should timeout with current {current_agent_timeout}s limit. "
            f"Completed in {execution_time:.1f}s, proving Issue #341: "
            f"Current timeouts adequate (issue resolved) or test simulation too fast."
        )
        
        self.record_metric("business_scenario_blocked", "Supply Chain Optimization")
    
    @pytest.mark.asyncio
    async def test_customer_behavior_analytics_extreme_timeout(self):
        """
        Test customer behavior analytics with extreme processing requirements.
        
        This test should INITIALLY FAIL, proving Issue #341 for the most complex scenarios.
        """
        self.set_env_var("ENVIRONMENT", "staging")
        
        # Customer behavior analytics requirements (most demanding)
        CUSTOMER_ANALYTICS_DURATION = 300  # 5 minutes for deep customer behavior analysis
        STREAMING_INTERVAL = 15.0          # Updates every 15 seconds (large data processing)
        
        current_agent_timeout = get_agent_execution_timeout()
        current_websocket_timeout = get_websocket_recv_timeout()
        
        # Create customer analytics agent
        analytics_agent = MockLongRunningAgent(
            processing_duration=CUSTOMER_ANALYTICS_DURATION,
            streaming_interval=STREAMING_INTERVAL
        )
        
        start_time = time.time()
        execution_failed = False
        
        try:
            workflow_result = await self.run_with_timeout(
                analytics_agent.run_analytical_workflow({
                    "analytics_type": "customer_behavior",
                    "data_sources": ["transactions", "web_analytics", "social_media", "support_tickets"],
                    "ml_models": ["clustering", "prediction", "segmentation"],
                    "complexity": "very_high",
                    "data_volume": "very_large"
                }),
                timeout=current_agent_timeout
            )
            
            execution_time = time.time() - start_time
            self.record_metric("customer_analytics_execution_time", execution_time)
            
        except asyncio.TimeoutError:
            execution_failed = True
            execution_time = time.time() - start_time
            self.record_metric("customer_analytics_timeout_occurred", True)
            self.record_metric("customer_analytics_timeout_duration", execution_time)
        
        # Extreme scenario should definitely fail with current constraints
        assert execution_failed, (
            f"Customer behavior analytics (300s requirement) should timeout with current "
            f"{current_agent_timeout}s limit. This is the extreme test case for Issue #341. "
            f"If this passes ({execution_time:.1f}s), either issue is resolved or test inadequate."
        )
        
        self.record_metric("business_scenario_blocked", "Customer Behavior Analytics")
        self.record_metric("extreme_timeout_scenario_confirmed", True)
    
    @pytest.mark.asyncio
    async def test_streaming_event_coordination_under_timeout_pressure(self):
        """
        Test streaming event coordination when approaching timeout limits.
        
        This test validates streaming behavior near timeout boundaries.
        Should reveal coordination issues between WebSocket and agent timeouts.
        """
        self.set_env_var("ENVIRONMENT", "staging")
        
        current_agent_timeout = get_agent_execution_timeout()
        current_websocket_timeout = get_websocket_recv_timeout()
        
        # Test duration just under agent timeout to examine coordination
        TEST_DURATION = max(current_agent_timeout - 5, 10)  # 5s before timeout, minimum 10s
        STREAMING_INTERVAL = 2.0  # Frequent updates to test coordination
        
        streaming_agent = MockLongRunningAgent(
            processing_duration=TEST_DURATION,
            streaming_interval=STREAMING_INTERVAL
        )
        
        # Track streaming events during execution
        events_received = []
        coordination_issues = []
        
        async def monitor_streaming_events():
            """Monitor streaming events during execution."""
            while streaming_agent.is_running:
                await asyncio.sleep(0.5)  # Check every 500ms
                
                # Simulate WebSocket event coordination
                current_time = time.time()
                if streaming_agent.start_time:
                    elapsed = current_time - streaming_agent.start_time
                    
                    # Check for coordination issues
                    if elapsed > current_websocket_timeout * 0.8:  # 80% of WebSocket timeout
                        coordination_issues.append({
                            "type": "websocket_timeout_approaching",
                            "elapsed": elapsed,
                            "websocket_limit": current_websocket_timeout
                        })
                    
                    if elapsed > current_agent_timeout * 0.9:  # 90% of agent timeout
                        coordination_issues.append({
                            "type": "agent_timeout_approaching", 
                            "elapsed": elapsed,
                            "agent_limit": current_agent_timeout
                        })
                    
                    events_received.append({
                        "timestamp": current_time,
                        "elapsed": elapsed,
                        "events_sent": len(streaming_agent.events_sent)
                    })
        
        # Start monitoring task
        monitor_task = asyncio.create_task(monitor_streaming_events())
        
        start_time = time.time()
        execution_result = None
        execution_failed = False
        
        try:
            # Run with timeout coordination test
            workflow_task = asyncio.create_task(streaming_agent.run_analytical_workflow({
                "test_type": "timeout_coordination",
                "duration": TEST_DURATION,
                "streaming_interval": STREAMING_INTERVAL
            }))
            
            execution_result = await self.run_with_timeout(
                workflow_task,
                timeout=current_agent_timeout
            )
            
        except asyncio.TimeoutError:
            execution_failed = True
        finally:
            # Stop monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        execution_time = time.time() - start_time
        
        # Record coordination metrics
        self.record_metric("coordination_test_duration", execution_time)
        self.record_metric("coordination_events_received", len(events_received))
        self.record_metric("coordination_issues", len(coordination_issues))
        self.record_metric("streaming_events_sent", len(streaming_agent.events_sent))
        
        # Analyze coordination behavior
        if execution_failed:
            self.record_metric("coordination_timeout_occurred", True)
            # Timeout expected if test duration approaches limits
        else:
            self.record_metric("coordination_completed_successfully", True)
        
        # Validate streaming event flow
        assert len(streaming_agent.events_sent) > 0, "No streaming events sent during execution"
        
        # Record findings for Issue #341 analysis
        self.record_metric("websocket_agent_timeout_gap", current_websocket_timeout - current_agent_timeout)
        self.record_metric("coordination_pressure_detected", len(coordination_issues) > 0)
    
    @pytest.mark.asyncio
    async def test_concurrent_long_running_agents_timeout_isolation(self):
        """
        Test timeout isolation between concurrent long-running agents.
        
        This tests that timeout issues don't cascade between concurrent executions.
        """
        self.set_env_var("ENVIRONMENT", "staging")
        
        current_agent_timeout = get_agent_execution_timeout()
        
        # Create different duration agents to test isolation
        agent_configs = [
            {"name": "quick_analysis", "duration": 20, "interval": 2.0},
            {"name": "medium_analysis", "duration": 60, "interval": 5.0}, 
            {"name": "long_analysis", "duration": 120, "interval": 10.0}  # Should timeout
        ]
        
        agents = {}
        execution_tasks = {}
        results = {}
        
        # Start all agents concurrently
        start_time = time.time()
        
        for config in agent_configs:
            agent_name = config["name"]
            agent = MockLongRunningAgent(
                processing_duration=config["duration"],
                streaming_interval=config["interval"]
            )
            agents[agent_name] = agent
            
            # Start concurrent execution
            execution_tasks[agent_name] = asyncio.create_task(
                self._execute_with_timeout_tracking(agent, agent_name, current_agent_timeout)
            )
        
        # Wait for all tasks to complete (with timeout or success)
        for agent_name, task in execution_tasks.items():
            try:
                result = await task
                results[agent_name] = result
                self.record_metric(f"{agent_name}_execution_result", result["status"])
                
            except Exception as e:
                results[agent_name] = {"status": "error", "error": str(e)}
                self.record_metric(f"{agent_name}_execution_error", str(e))
        
        total_execution_time = time.time() - start_time
        
        # Record isolation metrics
        self.record_metric("concurrent_execution_time", total_execution_time)
        self.record_metric("concurrent_agents_tested", len(agent_configs))
        self.record_metric("concurrent_results", len(results))
        
        # Validate isolation (some agents should succeed, others timeout)
        successful_agents = [name for name, result in results.items() if result.get("status") == "success"]
        timeout_agents = [name for name, result in results.items() if result.get("status") == "timeout"]
        
        self.record_metric("successful_concurrent_agents", len(successful_agents))
        self.record_metric("timeout_concurrent_agents", len(timeout_agents))
        
        # Quick analysis should succeed, long analysis should timeout
        assert "quick_analysis" in successful_agents, "Quick analysis should succeed within timeout"
        
        # Long analysis should timeout with current constraints (Issue #341)
        assert "long_analysis" in timeout_agents, (
            f"Long analysis (120s) should timeout with current {current_agent_timeout}s limit. "
            f"Issue #341 validation: If this passes, timeout constraints may be adequate."
        )
        
        # Validate timeout isolation didn't affect other agents
        assert len(results) == len(agent_configs), "Timeout in one agent affected others"
    
    async def _execute_with_timeout_tracking(self, agent: MockLongRunningAgent, 
                                           agent_name: str, timeout: int) -> Dict[str, Any]:
        """
        Execute agent with timeout tracking for isolation testing.
        
        Args:
            agent: Mock agent to execute
            agent_name: Name for tracking
            timeout: Timeout limit in seconds
            
        Returns:
            Dict with execution results
        """
        start_time = time.time()
        
        try:
            workflow_result = await self.run_with_timeout(
                agent.run_analytical_workflow({
                    "agent_name": agent_name,
                    "isolation_test": True
                }),
                timeout=timeout
            )
            
            return {
                "status": "success",
                "execution_time": time.time() - start_time,
                "events_sent": len(agent.events_sent),
                "result": workflow_result
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "timeout", 
                "execution_time": time.time() - start_time,
                "events_sent": len(agent.events_sent),
                "timeout_limit": timeout
            }
        except Exception as e:
            return {
                "status": "error",
                "execution_time": time.time() - start_time, 
                "events_sent": len(agent.events_sent),
                "error": str(e)
            }
    
    @pytest.mark.asyncio
    async def test_streaming_timeout_progression_requirements(self):
        """
        Test streaming timeout progression requirements for Issue #341.
        
        This test validates the 60s→300s timeout progression need.
        Should INITIALLY FAIL to prove progression requirement.
        """
        self.set_env_var("ENVIRONMENT", "staging")
        
        # Define timeout progression requirements for Issue #341
        timeout_progression = [
            {"phase": "initial_response", "required_timeout": 60, "description": "Basic agent startup and initial response"},
            {"phase": "data_processing", "required_timeout": 120, "description": "Data collection and initial processing"},
            {"phase": "analysis_phase", "required_timeout": 180, "description": "Complex analysis and pattern detection"},
            {"phase": "report_generation", "required_timeout": 240, "description": "Report generation and formatting"},
            {"phase": "finalization", "required_timeout": 300, "description": "Final validation and delivery"}
        ]
        
        current_agent_timeout = get_agent_execution_timeout()
        current_websocket_timeout = get_websocket_recv_timeout()
        
        progression_gaps = []
        
        for phase in timeout_progression:
            required = phase["required_timeout"]
            phase_name = phase["phase"]
            
            # Check if current timeout supports this phase
            agent_gap = required - current_agent_timeout
            websocket_gap = required - current_websocket_timeout
            
            self.record_metric(f"{phase_name}_required_timeout", required)
            self.record_metric(f"{phase_name}_agent_gap", agent_gap)
            self.record_metric(f"{phase_name}_websocket_gap", websocket_gap)
            
            if agent_gap > 0 or websocket_gap > 0:
                progression_gaps.append({
                    "phase": phase_name,
                    "required": required,
                    "agent_gap": agent_gap,
                    "websocket_gap": websocket_gap,
                    "description": phase["description"]
                })
        
        # Record progression analysis
        self.record_metric("timeout_progression_phases", len(timeout_progression))
        self.record_metric("timeout_progression_gaps", len(progression_gaps))
        self.record_metric("current_agent_timeout", current_agent_timeout)
        self.record_metric("current_websocket_timeout", current_websocket_timeout)
        
        # CRITICAL ASSERTION: Should have progression gaps (initially FAIL)
        assert len(progression_gaps) == 0, (
            f"Issue #341 TIMEOUT PROGRESSION REQUIREMENT: "
            f"Current timeouts inadequate for {len(progression_gaps)}/{len(timeout_progression)} phases. "
            f"Agent timeout: {current_agent_timeout}s, WebSocket timeout: {current_websocket_timeout}s. "
            f"Gaps found in phases: {[g['phase'] for g in progression_gaps]}. "
            f"Maximum required: {max(p['required_timeout'] for p in timeout_progression)}s. "
            f"This proves Issue #341: Need 60s→300s timeout progression for enterprise workflows."
        )


class TestStreamingTimeoutRecovery(SSotAsyncTestCase):
    """Tests for streaming timeout recovery and graceful degradation."""
    
    def setup_method(self, method=None):
        """Setup each test with fresh state."""
        super().setup_method(method)
        reset_timeout_manager()
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        reset_timeout_manager()
        super().teardown_method(method)
    
    @pytest.mark.asyncio
    async def test_graceful_timeout_degradation_streaming_preservation(self):
        """
        Test graceful degradation when timeouts occur while preserving streaming events.
        
        This tests that streaming events are preserved even when timeout occurs.
        """
        self.set_env_var("ENVIRONMENT", "testing")  # Use shorter timeouts for testing
        
        current_timeout = get_agent_execution_timeout()
        
        # Create agent that will timeout but generates streaming events
        streaming_agent = MockLongRunningAgent(
            processing_duration=current_timeout + 10,  # Exceeds timeout by 10s
            streaming_interval=1.0  # Frequent events
        )
        
        events_captured = []
        
        try:
            # Monitor events during execution
            start_time = time.time()
            
            workflow_result = await self.run_with_timeout(
                streaming_agent.run_analytical_workflow({
                    "test_type": "graceful_degradation",
                    "preserve_events": True
                }),
                timeout=current_timeout
            )
            
            # Should not reach here due to timeout
            self.record_metric("unexpected_completion", True)
            
        except asyncio.TimeoutError:
            # Expected timeout - capture events generated before timeout
            events_captured = streaming_agent.events_sent.copy()
            execution_time = time.time() - start_time
            
            self.record_metric("graceful_timeout_occurred", True)
            self.record_metric("events_captured_before_timeout", len(events_captured))
            self.record_metric("timeout_execution_time", execution_time)
        
        # Validate graceful degradation
        assert len(events_captured) > 0, "No streaming events captured before timeout"
        
        # Events should show progression before timeout
        event_types = [event.event_type for event in events_captured]
        assert "phase_started" in event_types, "No phase start events captured"
        
        # Should have partial progress events
        progress_events = [e for e in events_captured if e.event_type == "phase_progress"]
        assert len(progress_events) > 0, "No progress events captured during graceful degradation"
        
        self.record_metric("graceful_degradation_validated", True)
        self.record_metric("partial_progress_preserved", len(progress_events))


if __name__ == "__main__":
    # Run integration tests to demonstrate Issue #341
    pytest.main([__file__, "-v", "-s", "--tb=short"])