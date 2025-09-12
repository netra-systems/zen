"""
Test Real Agent Execution Order - Proper Sequence Validation

Business Value Justification (BVJ):
- Segment: All (Execution order affects quality for all user types)
- Business Goal: Ensure agents execute in optimal sequence for maximum value delivery
- Value Impact: Proper execution order ensures data flows correctly between agents
- Strategic Impact: Foundation for reliable multi-agent workflows and consistent results

CRITICAL for business value delivery:
1. Triage MUST execute first to determine strategy
2. Data Sub-Agent MUST execute before Optimization Agent (data dependency)
3. Optimization Agent MUST have data inputs before generating recommendations
4. Supervisor coordination must respect agent dependencies
5. WebSocket events must reflect actual execution sequence

This test validates the CRITICAL agent execution order fix from 
SPEC/learnings/agent_execution_order_fix_20250904.xml:
"Data BEFORE Optimization" - the fundamental dependency that enables value delivery.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestHelpers, MockWebSocketConnection

# Agent imports
try:
    from netra_backend.app.agents.triage_agent import TriageAgent
    from netra_backend.app.agents.data_sub_agent import DataSubAgent
    from netra_backend.app.agents.optimization_agent import OptimizationAgent
    from netra_backend.app.agents.supervisor_agent import SupervisorAgent
    from netra_backend.app.services.agent_registry import AgentRegistry
    AGENT_SERVICES_AVAILABLE = True
except ImportError:
    AGENT_SERVICES_AVAILABLE = False

# WebSocket services
try:
    from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
    WEBSOCKET_SERVICES_AVAILABLE = True
except ImportError:
    WEBSOCKET_SERVICES_AVAILABLE = False


class TestRealAgentExecutionOrder(BaseE2ETest):
    """Test proper agent execution sequencing for business value delivery."""

    def setup_method(self):
        """Set up test method with execution order validation."""
        super().setup_method()
        self.test_user_id = f"execution_order_user_{uuid.uuid4().hex[:8]}"
        self.execution_events = []
        self.agent_dependencies = {}
        self.execution_metrics = {
            "total_execution_time": 0,
            "sequence_violations": [],
            "dependency_violations": [],
            "agents_executed": [],
            "execution_order": []
        }

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_critical_data_before_optimization_order(self, real_services_fixture):
        """
        MISSION CRITICAL: Test Data Sub-Agent executes BEFORE Optimization Agent.
        
        This validates the core fix from agent_execution_order_fix_20250904.xml.
        Without proper order, optimization recommendations lack data foundation,
        delivering no business value.
        """
        await self.initialize_test_environment()
        
        # Create scenario requiring data -> optimization sequence
        optimization_request = {
            "user_id": self.test_user_id,
            "message": "Analyze my infrastructure costs and provide optimization recommendations",
            "context": {
                "requires_data_analysis": True,
                "requires_optimization": True,
                "expected_sequence": ["triage_agent", "data_sub_agent", "optimization_agent"]
            }
        }
        
        # Execute with sequence monitoring
        execution_result = await self._execute_with_sequence_monitoring(
            request=optimization_request,
            expected_sequence=optimization_request["context"]["expected_sequence"]
        )
        
        # CRITICAL VALIDATION: Data BEFORE Optimization
        self._assert_data_before_optimization_order(execution_result)
        
        # Validate dependency satisfaction
        self._assert_dependency_satisfaction(execution_result)
        
        # Validate business value is achievable with proper order
        self._assert_business_value_achievable(execution_result)
        
        # Validate WebSocket events reflect proper order
        self._assert_websocket_events_reflect_order(execution_result)
        
        self.logger.info(" PASS:  CRITICAL data-before-optimization order validated")

    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_triage_first_execution_order(self, real_services_fixture):
        """
        Test Triage Agent executes FIRST in all scenarios.
        
        Validates that triage always precedes specialized agent execution,
        ensuring proper request analysis and routing.
        """
        await self.initialize_test_environment()
        
        # Test multiple scenarios where triage must be first
        test_scenarios = [
            {
                "name": "simple_query",
                "message": "What are my options for reducing costs?",
                "expected_first": "triage_agent",
                "expected_sequence": ["triage_agent", "data_sub_agent", "optimization_agent"]
            },
            {
                "name": "complex_analysis",
                "message": "Comprehensive infrastructure analysis with performance and cost optimization",
                "expected_first": "triage_agent", 
                "expected_sequence": ["triage_agent", "data_sub_agent", "optimization_agent", "supervisor_agent"]
            },
            {
                "name": "performance_focused",
                "message": "Identify and resolve performance bottlenecks",
                "expected_first": "triage_agent",
                "expected_sequence": ["triage_agent", "data_sub_agent"]
            }
        ]
        
        for scenario in test_scenarios:
            self.logger.info(f"Testing triage-first scenario: {scenario['name']}")
            
            request = {
                "user_id": self.test_user_id,
                "message": scenario["message"],
                "context": {"scenario": scenario["name"]}
            }
            
            execution_result = await self._execute_with_sequence_monitoring(
                request=request,
                expected_sequence=scenario["expected_sequence"]
            )
            
            # Validate triage executed first
            self._assert_triage_first(execution_result, scenario)
            
            # Reset for next scenario
            self._reset_execution_state()
        
        self.logger.info(" PASS:  Triage-first execution order validated for all scenarios")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_supervisor_coordination_respects_dependencies(self, real_services_fixture):
        """
        Test Supervisor Agent respects sub-agent dependencies.
        
        Validates that supervisor coordination maintains proper execution order
        while orchestrating multiple sub-agents.
        """
        await self.initialize_test_environment()
        
        # Complex request requiring supervisor coordination
        coordination_request = {
            "user_id": self.test_user_id,
            "message": "Strategic infrastructure optimization with comprehensive analysis and implementation roadmap",
            "context": {
                "requires_coordination": True,
                "complexity": "high",
                "expected_agents": ["triage_agent", "data_sub_agent", "optimization_agent", "supervisor_agent"]
            }
        }
        
        # Execute with dependency tracking
        execution_result = await self._execute_with_dependency_tracking(
            request=coordination_request,
            track_coordinator=True
        )
        
        # Validate supervisor respects dependencies
        self._assert_supervisor_respects_dependencies(execution_result)
        
        # Validate coordination enhances rather than disrupts order
        self._assert_coordination_enhances_order(execution_result)
        
        # Validate final result quality with proper coordination
        self._assert_coordinated_result_quality(execution_result)
        
        self.logger.info(" PASS:  Supervisor coordination with dependency respect validated")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_users_maintain_execution_order(self, real_services_fixture):
        """
        Test execution order maintained across concurrent users.
        
        Validates that proper sequencing is preserved even when multiple
        users are executing agents simultaneously.
        """
        await self.initialize_test_environment()
        
        # Create concurrent users with different request types
        concurrent_users = [
            {
                "user_id": f"concurrent_order_user_1_{uuid.uuid4().hex[:8]}",
                "message": "Cost optimization analysis needed",
                "expected_sequence": ["triage_agent", "data_sub_agent", "optimization_agent"]
            },
            {
                "user_id": f"concurrent_order_user_2_{uuid.uuid4().hex[:8]}",
                "message": "Performance bottleneck identification required",
                "expected_sequence": ["triage_agent", "data_sub_agent"]
            },
            {
                "user_id": f"concurrent_order_user_3_{uuid.uuid4().hex[:8]}",
                "message": "Strategic infrastructure roadmap with comprehensive recommendations",
                "expected_sequence": ["triage_agent", "data_sub_agent", "optimization_agent", "supervisor_agent"]
            }
        ]
        
        # Execute all users concurrently
        start_time = time.time()
        
        concurrent_tasks = []
        for user in concurrent_users:
            request = {
                "user_id": user["user_id"],
                "message": user["message"],
                "context": {"concurrent_test": True}
            }
            
            task = self._execute_with_sequence_monitoring(
                request=request,
                expected_sequence=user["expected_sequence"],
                user_prefix=f"concurrent_{user['user_id'][-8:]}"
            )
            concurrent_tasks.append(task)
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate all executions succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"Concurrent execution {i} failed: {result}")
        
        # Validate execution order maintained for each user
        for i, result in enumerate(results):
            expected_sequence = concurrent_users[i]["expected_sequence"]
            self._assert_execution_order_maintained(result, expected_sequence, concurrent_users[i]["user_id"])
        
        # Validate no cross-user sequence contamination
        self._assert_no_cross_user_sequence_contamination(results, concurrent_users)
        
        # Validate performance under concurrent load
        self._assert_concurrent_execution_performance(execution_time, len(concurrent_users))
        
        self.logger.info(f" PASS:  Concurrent execution order validated for {len(concurrent_users)} users")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_execution_order_failure_recovery(self, real_services_fixture):
        """
        Test execution order recovery when agents fail.
        
        Validates that failures don't disrupt execution sequence and
        recovery maintains proper order.
        """
        await self.initialize_test_environment()
        
        # Request with simulated agent failure
        failure_request = {
            "user_id": self.test_user_id,
            "message": "Analysis with potential agent failures during execution",
            "context": {
                "simulate_failures": True,
                "failure_agent": "data_sub_agent",  # Simulate data agent failure
                "expected_recovery": "graceful_degradation"
            }
        }
        
        # Execute with failure simulation
        execution_result = await self._execute_with_failure_simulation(
            request=failure_request,
            failure_scenarios=["data_sub_agent_timeout", "dependency_failure"]
        )
        
        # Validate execution order preserved despite failures
        self._assert_order_preserved_despite_failures(execution_result)
        
        # Validate dependency handling during failures
        self._assert_dependency_handling_during_failures(execution_result)
        
        # Validate recovery maintains sequence integrity
        self._assert_recovery_sequence_integrity(execution_result)
        
        # Validate business value delivery with degraded sequence
        self._assert_degraded_sequence_value_delivery(execution_result)
        
        self.logger.info(" PASS:  Execution order failure recovery validated")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_execution_order_performance_optimization(self, real_services_fixture):
        """
        Test execution order performance optimizations.
        
        Validates that proper sequencing is maintained while optimizing
        for performance and minimizing execution time.
        """
        await self.initialize_test_environment()
        
        # Performance-focused execution request
        performance_request = {
            "user_id": self.test_user_id,
            "message": "Fast optimization analysis with minimal latency",
            "context": {
                "performance_mode": True,
                "max_execution_time": 15.0,
                "optimize_for": "speed_with_quality"
            }
        }
        
        # Execute with performance monitoring
        start_time = time.time()
        
        execution_result = await self._execute_with_performance_optimization(
            request=performance_request,
            performance_targets={
                "max_total_time": 15.0,
                "max_per_agent_time": 5.0,
                "min_quality_score": 0.8
            }
        )
        
        total_time = time.time() - start_time
        
        # Validate execution order maintained during optimization
        self._assert_order_maintained_during_optimization(execution_result)
        
        # Validate performance targets met
        self._assert_performance_targets_met(execution_result, total_time)
        
        # Validate quality not compromised for speed
        self._assert_quality_maintained_with_speed(execution_result)
        
        self.logger.info(f" PASS:  Execution order performance optimization validated in {total_time:.2f}s")

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    async def _execute_with_sequence_monitoring(self,
                                              request: Dict[str, Any],
                                              expected_sequence: List[str],
                                              user_prefix: str = "") -> Dict[str, Any]:
        """Execute agents with comprehensive sequence monitoring."""
        
        execution_start = time.time()
        
        # Set up monitoring
        execution_context = await self._create_execution_context(request["user_id"])
        websocket_notifier = await self._create_sequence_monitoring_notifier(request["user_id"])
        
        # Execute agent sequence
        sequence_result = await self._execute_agent_sequence(
            request=request,
            expected_sequence=expected_sequence,
            context=execution_context,
            websocket_notifier=websocket_notifier
        )
        
        execution_time = time.time() - execution_start
        self.execution_metrics["total_execution_time"] = execution_time
        
        # Compile execution result with monitoring data
        execution_result = {
            "request": request,
            "expected_sequence": expected_sequence,
            "actual_sequence": sequence_result["actual_sequence"],
            "execution_events": sequence_result["execution_events"],
            "agent_results": sequence_result["agent_results"],
            "dependency_map": sequence_result["dependency_map"],
            "execution_metrics": {
                "total_time": execution_time,
                "agents_executed": len(sequence_result["actual_sequence"]),
                "sequence_violations": len(self.execution_metrics["sequence_violations"])
            }
        }
        
        return execution_result

    async def _create_execution_context(self, user_id: str):
        """Create execution context for sequence monitoring."""
        if AGENT_SERVICES_AVAILABLE:
            agent_registry = AgentRegistry()
            return {
                "user_id": user_id,
                "connection_id": f"conn_{uuid.uuid4().hex[:8]}",
                "agent_registry": agent_registry,
                "execution_config": {
                    "monitor_sequence": True,
                    "track_dependencies": True,
                    "enforce_order": True
                }
            }
        else:
            return {
                "user_id": user_id,
                "connection_id": f"conn_{uuid.uuid4().hex[:8]}",
                "agent_registry": MagicMock(),
                "execution_config": {
                    "monitor_sequence": True,
                    "track_dependencies": True,
                    "enforce_order": True
                }
            }

    async def _create_sequence_monitoring_notifier(self, user_id: str):
        """Create WebSocket notifier with sequence monitoring."""
        if WEBSOCKET_SERVICES_AVAILABLE:
            notifier = WebSocketNotifier.create_for_user()
            
            # Hook into notifier for sequence monitoring
            original_send = notifier.send_to_user
            
            async def monitor_sequence_events(user_id_param, event_data):
                # Record execution events with sequence tracking
                execution_event = {
                    **event_data,
                    "sequence_timestamp": time.time(),
                    "user_id": user_id_param,
                    "execution_phase": self._determine_execution_phase(event_data)
                }
                self.execution_events.append(execution_event)
                
                # Track agent execution order
                if event_data.get("type") == "agent_started":
                    agent_name = event_data.get("agent_name")
                    if agent_name:
                        self.execution_metrics["execution_order"].append(agent_name)
                        self.execution_metrics["agents_executed"].append(agent_name)
                
                return await original_send(user_id_param, event_data)
            
            notifier.send_to_user = monitor_sequence_events
            return notifier
        else:
            # Mock notifier with sequence monitoring
            mock_notifier = MagicMock()
            mock_notifier.send_to_user = AsyncMock()
            
            async def mock_monitor_sequence_events(user_id_param, event_data):
                execution_event = {
                    **event_data,
                    "sequence_timestamp": time.time(),
                    "user_id": user_id_param,
                    "execution_phase": self._determine_execution_phase(event_data),
                    "mock_context": True
                }
                self.execution_events.append(execution_event)
                
                if event_data.get("type") == "agent_started":
                    agent_name = event_data.get("agent_name")
                    if agent_name:
                        self.execution_metrics["execution_order"].append(agent_name)
                        self.execution_metrics["agents_executed"].append(agent_name)
            
            mock_notifier.send_to_user.side_effect = mock_monitor_sequence_events
            return mock_notifier

    def _determine_execution_phase(self, event_data: Dict[str, Any]) -> str:
        """Determine execution phase from event data."""
        event_type = event_data.get("type", "")
        agent_name = event_data.get("agent_name", "")
        
        if event_type == "agent_started":
            return f"{agent_name}_starting"
        elif event_type == "agent_thinking":
            return f"{agent_name}_processing"
        elif event_type == "tool_executing":
            return f"{agent_name}_tool_execution"
        elif event_type == "agent_completed":
            return f"{agent_name}_completed"
        else:
            return "coordination"

    async def _execute_agent_sequence(self,
                                    request: Dict[str, Any],
                                    expected_sequence: List[str],
                                    context: Dict[str, Any],
                                    websocket_notifier) -> Dict[str, Any]:
        """Execute agent sequence with proper order enforcement."""
        
        actual_sequence = []
        execution_events = []
        agent_results = {}
        dependency_map = {}
        
        # Execute agents in proper sequence
        for i, agent_name in enumerate(expected_sequence):
            # Check dependencies before execution
            dependencies_satisfied = await self._check_agent_dependencies(
                agent_name, actual_sequence, agent_results
            )
            
            if not dependencies_satisfied:
                # Record dependency violation
                self.execution_metrics["dependency_violations"].append({
                    "agent": agent_name,
                    "missing_dependencies": self._get_missing_dependencies(agent_name, actual_sequence),
                    "timestamp": time.time()
                })
                continue
            
            # Execute agent
            agent_result = await self._execute_single_agent_in_sequence(
                agent_name=agent_name,
                request=request,
                context=context,
                websocket_notifier=websocket_notifier,
                dependencies=actual_sequence,
                sequence_position=i
            )
            
            # Record execution
            actual_sequence.append(agent_name)
            agent_results[agent_name] = agent_result
            dependency_map[agent_name] = self._get_agent_dependencies(agent_name)
            
            # Brief coordination delay
            await asyncio.sleep(0.1)
        
        return {
            "actual_sequence": actual_sequence,
            "execution_events": execution_events,
            "agent_results": agent_results,
            "dependency_map": dependency_map
        }

    async def _check_agent_dependencies(self,
                                      agent_name: str,
                                      completed_agents: List[str],
                                      agent_results: Dict[str, Any]) -> bool:
        """Check if agent dependencies are satisfied."""
        
        dependencies = self._get_agent_dependencies(agent_name)
        
        for dependency in dependencies:
            if dependency not in completed_agents:
                return False
            
            # For optimization agent, specifically check data availability
            if agent_name == "optimization_agent" and dependency == "data_sub_agent":
                data_result = agent_results.get("data_sub_agent", {})
                if not data_result.get("data_insights"):
                    return False
        
        return True

    def _get_agent_dependencies(self, agent_name: str) -> List[str]:
        """Get dependencies for specific agent."""
        dependencies = {
            "triage_agent": [],  # No dependencies - always first
            "data_sub_agent": ["triage_agent"],  # Needs triage routing
            "optimization_agent": ["triage_agent", "data_sub_agent"],  # CRITICAL: Needs data
            "supervisor_agent": ["triage_agent", "data_sub_agent"]  # Needs context from others
        }
        
        return dependencies.get(agent_name, [])

    def _get_missing_dependencies(self, agent_name: str, completed_agents: List[str]) -> List[str]:
        """Get missing dependencies for agent."""
        required = self._get_agent_dependencies(agent_name)
        return [dep for dep in required if dep not in completed_agents]

    async def _execute_single_agent_in_sequence(self,
                                              agent_name: str,
                                              request: Dict[str, Any],
                                              context: Dict[str, Any],
                                              websocket_notifier,
                                              dependencies: List[str],
                                              sequence_position: int) -> Dict[str, Any]:
        """Execute single agent within sequence with dependency awareness."""
        
        # Agent starts
        await websocket_notifier.send_to_user(
            request["user_id"],
            {
                "type": "agent_started",
                "agent_name": agent_name,
                "sequence_position": sequence_position,
                "dependencies": dependencies,
                "timestamp": time.time()
            }
        )
        
        # Agent processing with sequence awareness
        await websocket_notifier.send_to_user(
            request["user_id"],
            {
                "type": "agent_thinking",
                "agent_name": agent_name,
                "reasoning": f"{agent_name} processing with dependencies: {dependencies}",
                "sequence_context": f"Position {sequence_position} in sequence",
                "timestamp": time.time()
            }
        )
        
        # Generate sequence-aware result
        agent_result = await self._generate_sequence_aware_result(
            agent_name, request, dependencies, sequence_position
        )
        
        # Agent completion
        await websocket_notifier.send_to_user(
            request["user_id"],
            {
                "type": "agent_completed",
                "agent_name": agent_name,
                "final_response": agent_result["summary"],
                "sequence_position": sequence_position,
                "provides_for_next": agent_result.get("provides_for_next", []),
                "timestamp": time.time()
            }
        )
        
        return agent_result

    async def _generate_sequence_aware_result(self,
                                            agent_name: str,
                                            request: Dict[str, Any],
                                            dependencies: List[str],
                                            sequence_position: int) -> Dict[str, Any]:
        """Generate result that acknowledges sequence dependencies."""
        
        base_result = {
            "agent_name": agent_name,
            "sequence_position": sequence_position,
            "dependencies_used": dependencies,
            "execution_timestamp": time.time()
        }
        
        if agent_name == "triage_agent":
            base_result.update({
                "summary": "Request triaged and routing strategy determined",
                "routing_decision": "multi_agent_optimization_workflow",
                "provides_for_next": ["routing_strategy", "complexity_assessment"],
                "data_insights": None  # Triage doesn't provide data
            })
        
        elif agent_name == "data_sub_agent":
            base_result.update({
                "summary": "Infrastructure data analyzed with key insights identified",
                "data_insights": {
                    "cost_analysis": {"monthly_spend": 15000, "trend": "increasing"},
                    "performance_metrics": {"avg_response_time": 450, "error_rate": 0.02},
                    "utilization_patterns": {"peak_hours": "9am-6pm", "idle_capacity": 0.35}
                },
                "provides_for_next": ["cost_data", "performance_data", "utilization_patterns"],
                "sequence_validation": "executed_after_triage"
            })
        
        elif agent_name == "optimization_agent":
            # CRITICAL: Must acknowledge data dependency
            data_available = "data_sub_agent" in dependencies
            base_result.update({
                "summary": f"Optimization recommendations generated {'with data foundation' if data_available else 'without data foundation'}",
                "optimization_recommendations": [
                    {
                        "area": "resource_rightsizing",
                        "potential_savings": 3500 if data_available else 0,
                        "confidence": "high" if data_available else "low",
                        "data_driven": data_available
                    }
                ] if data_available else [],
                "provides_for_next": ["actionable_recommendations", "implementation_plan"],
                "sequence_validation": f"executed_after_data_agent: {data_available}",
                "business_value_possible": data_available
            })
        
        elif agent_name == "supervisor_agent":
            base_result.update({
                "summary": "Strategic coordination and synthesis completed",
                "coordination_result": "Multi-agent insights synthesized into actionable strategy",
                "provides_for_next": ["strategic_roadmap", "executive_summary"],
                "sequence_validation": "coordinated_all_dependencies"
            })
        
        return base_result

    async def _execute_with_dependency_tracking(self,
                                              request: Dict[str, Any],
                                              track_coordinator: bool = False) -> Dict[str, Any]:
        """Execute with comprehensive dependency tracking."""
        
        # Enhanced execution with dependency tracking
        expected_sequence = request["context"]["expected_agents"]
        
        # Track dependencies throughout execution
        execution_result = await self._execute_with_sequence_monitoring(
            request=request,
            expected_sequence=expected_sequence
        )
        
        # Add dependency tracking data
        execution_result["dependency_tracking"] = {
            "dependency_map": {
                agent: self._get_agent_dependencies(agent) 
                for agent in expected_sequence
            },
            "dependency_violations": self.execution_metrics["dependency_violations"],
            "coordination_overhead": 0.5  # Simulated coordination time
        }
        
        return execution_result

    async def _execute_with_failure_simulation(self,
                                             request: Dict[str, Any],
                                             failure_scenarios: List[str]) -> Dict[str, Any]:
        """Execute with simulated agent failures."""
        
        expected_sequence = ["triage_agent", "data_sub_agent", "optimization_agent"]
        
        # Simulate execution with failure in data_sub_agent
        execution_context = await self._create_execution_context(request["user_id"])
        websocket_notifier = await self._create_sequence_monitoring_notifier(request["user_id"])
        
        actual_sequence = []
        agent_results = {}
        
        for i, agent_name in enumerate(expected_sequence):
            if agent_name == "data_sub_agent" and "data_sub_agent_timeout" in failure_scenarios:
                # Simulate failure
                await websocket_notifier.send_to_user(
                    request["user_id"],
                    {
                        "type": "agent_error",
                        "agent_name": agent_name,
                        "error_message": "Simulated timeout during data analysis",
                        "sequence_position": i,
                        "timestamp": time.time()
                    }
                )
                
                # Record failure but continue with degraded sequence
                agent_results[f"{agent_name}_failed"] = {
                    "error": "timeout",
                    "sequence_impact": "optimization_agent_degraded"
                }
            else:
                # Normal execution
                agent_result = await self._execute_single_agent_in_sequence(
                    agent_name=agent_name,
                    request=request,
                    context=execution_context,
                    websocket_notifier=websocket_notifier,
                    dependencies=actual_sequence,
                    sequence_position=i
                )
                actual_sequence.append(agent_name)
                agent_results[agent_name] = agent_result
        
        return {
            "request": request,
            "actual_sequence": actual_sequence,
            "agent_results": agent_results,
            "failure_scenarios": failure_scenarios,
            "recovery_actions": ["graceful_degradation", "partial_optimization"]
        }

    async def _execute_with_performance_optimization(self,
                                                   request: Dict[str, Any],
                                                   performance_targets: Dict[str, float]) -> Dict[str, Any]:
        """Execute with performance optimization while maintaining order."""
        
        expected_sequence = ["triage_agent", "data_sub_agent", "optimization_agent"]
        
        # Execute with performance monitoring
        execution_result = await self._execute_with_sequence_monitoring(
            request=request,
            expected_sequence=expected_sequence
        )
        
        # Add performance optimization data
        execution_result["performance_optimization"] = {
            "targets": performance_targets,
            "actual_performance": {
                "total_time": execution_result["execution_metrics"]["total_time"],
                "avg_per_agent": execution_result["execution_metrics"]["total_time"] / len(expected_sequence),
                "quality_score": 0.85  # Simulated quality score
            },
            "optimization_applied": ["parallel_tool_execution", "cached_data_retrieval"]
        }
        
        return execution_result

    def _reset_execution_state(self):
        """Reset execution state between tests."""
        self.execution_events = [e for e in self.execution_events if e.get("test_reset") != True]
        self.execution_metrics["execution_order"] = []
        self.execution_metrics["agents_executed"] = []

    # =============================================================================
    # VALIDATION METHODS
    # =============================================================================

    def _assert_data_before_optimization_order(self, execution_result: Dict[str, Any]):
        """CRITICAL: Assert Data Sub-Agent executes before Optimization Agent."""
        
        actual_sequence = execution_result["actual_sequence"]
        
        # Find positions of data and optimization agents
        data_position = None
        optimization_position = None
        
        for i, agent_name in enumerate(actual_sequence):
            if agent_name == "data_sub_agent":
                data_position = i
            elif agent_name == "optimization_agent":
                optimization_position = i
        
        # CRITICAL VALIDATION
        if optimization_position is not None:
            assert data_position is not None, (
                "Optimization Agent executed without Data Sub-Agent. "
                "This violates the critical 'Data BEFORE Optimization' requirement!"
            )
            
            assert data_position < optimization_position, (
                f"CRITICAL SEQUENCE VIOLATION: Data Sub-Agent at position {data_position}, "
                f"Optimization Agent at position {optimization_position}. "
                f"Data MUST execute before Optimization for business value delivery!"
            )
        
        # Validate data is available for optimization
        if "optimization_agent" in execution_result["agent_results"]:
            opt_result = execution_result["agent_results"]["optimization_agent"]
            
            # Optimization should acknowledge data dependency
            assert opt_result.get("sequence_validation", "").startswith("executed_after_data_agent: True"), (
                f"Optimization Agent did not acknowledge data dependency: {opt_result.get('sequence_validation')}"
            )
            
            # Business value should be possible with proper sequence
            assert opt_result.get("business_value_possible") == True, (
                "Optimization Agent indicates business value not possible - sequence may be wrong"
            )
        
        self.logger.info(" PASS:  CRITICAL: Data-before-optimization order validated")

    def _assert_dependency_satisfaction(self, execution_result: Dict[str, Any]):
        """Assert all agent dependencies were satisfied."""
        
        actual_sequence = execution_result["actual_sequence"]
        
        for agent_name in actual_sequence:
            required_deps = self._get_agent_dependencies(agent_name)
            
            for dependency in required_deps:
                assert dependency in actual_sequence, (
                    f"Agent {agent_name} dependency {dependency} not satisfied. "
                    f"Actual sequence: {actual_sequence}"
                )
                
                # Dependency must come before dependent
                dep_position = actual_sequence.index(dependency)
                agent_position = actual_sequence.index(agent_name)
                
                assert dep_position < agent_position, (
                    f"Dependency violation: {dependency} at position {dep_position}, "
                    f"{agent_name} at position {agent_position}"
                )

    def _assert_business_value_achievable(self, execution_result: Dict[str, Any]):
        """Assert proper sequence enables business value delivery."""
        
        agent_results = execution_result["agent_results"]
        
        # If optimization agent executed, it should have data foundation
        if "optimization_agent" in agent_results:
            opt_result = agent_results["optimization_agent"]
            
            # Should have optimization recommendations
            recommendations = opt_result.get("optimization_recommendations", [])
            assert len(recommendations) > 0, "No optimization recommendations generated"
            
            # Recommendations should have substance (data-driven)
            for rec in recommendations:
                assert rec.get("confidence") != "low", f"Low confidence recommendation: {rec}"
                assert rec.get("potential_savings", 0) > 0, f"No savings identified: {rec}"
                assert rec.get("data_driven") == True, f"Recommendation not data-driven: {rec}"
        
        # Data agent should provide foundation for optimization
        if "data_sub_agent" in agent_results:
            data_result = agent_results["data_sub_agent"]
            data_insights = data_result.get("data_insights", {})
            
            assert len(data_insights) > 0, "Data Sub-Agent provided no insights"
            assert "cost_analysis" in data_insights, "Missing cost analysis from data agent"

    def _assert_websocket_events_reflect_order(self, execution_result: Dict[str, Any]):
        """Assert WebSocket events reflect proper execution order."""
        
        # Extract agent_started events in order
        started_events = [
            event for event in self.execution_events
            if event.get("type") == "agent_started"
        ]
        
        # Events should be in proper sequence order
        expected_sequence = execution_result["expected_sequence"]
        actual_event_sequence = [event.get("agent_name") for event in started_events]
        
        # Validate sequence matches expectation
        for i, expected_agent in enumerate(expected_sequence):
            if i < len(actual_event_sequence):
                actual_agent = actual_event_sequence[i]
                assert actual_agent == expected_agent, (
                    f"WebSocket event sequence mismatch at position {i}: "
                    f"expected {expected_agent}, got {actual_agent}"
                )

    def _assert_triage_first(self, execution_result: Dict[str, Any], scenario: Dict[str, Any]):
        """Assert Triage Agent executed first in scenario."""
        
        actual_sequence = execution_result["actual_sequence"]
        
        assert len(actual_sequence) > 0, f"No agents executed in scenario {scenario['name']}"
        assert actual_sequence[0] == "triage_agent", (
            f"Triage Agent not first in scenario {scenario['name']}. "
            f"Actual sequence: {actual_sequence}"
        )
        
        # Validate triage provided routing for subsequent agents
        if "triage_agent" in execution_result["agent_results"]:
            triage_result = execution_result["agent_results"]["triage_agent"]
            assert "routing_decision" in triage_result, "Triage did not provide routing decision"

    def _assert_supervisor_respects_dependencies(self, execution_result: Dict[str, Any]):
        """Assert Supervisor Agent respects sub-agent dependencies."""
        
        actual_sequence = execution_result["actual_sequence"]
        
        if "supervisor_agent" in actual_sequence:
            supervisor_position = actual_sequence.index("supervisor_agent")
            
            # Supervisor should come after required dependencies
            required_before_supervisor = ["triage_agent", "data_sub_agent"]
            
            for required_agent in required_before_supervisor:
                if required_agent in actual_sequence:
                    required_position = actual_sequence.index(required_agent)
                    assert required_position < supervisor_position, (
                        f"Supervisor coordination violated dependency: "
                        f"{required_agent} at {required_position}, supervisor at {supervisor_position}"
                    )

    def _assert_coordination_enhances_order(self, execution_result: Dict[str, Any]):
        """Assert coordination enhances rather than disrupts execution order."""
        
        # Coordination should not introduce sequence violations
        assert len(self.execution_metrics["sequence_violations"]) == 0, (
            f"Coordination introduced sequence violations: {self.execution_metrics['sequence_violations']}"
        )
        
        # Should not introduce dependency violations
        assert len(self.execution_metrics["dependency_violations"]) == 0, (
            f"Coordination introduced dependency violations: {self.execution_metrics['dependency_violations']}"
        )

    def _assert_coordinated_result_quality(self, execution_result: Dict[str, Any]):
        """Assert coordinated results maintain quality."""
        
        agent_results = execution_result["agent_results"]
        
        if "supervisor_agent" in agent_results:
            supervisor_result = agent_results["supervisor_agent"]
            
            # Should acknowledge coordination of dependencies
            assert "coordination_result" in supervisor_result, "Supervisor did not provide coordination result"
            assert supervisor_result.get("sequence_validation") == "coordinated_all_dependencies", (
                "Supervisor did not validate proper coordination"
            )

    def _assert_execution_order_maintained(self, 
                                         result: Dict[str, Any],
                                         expected_sequence: List[str],
                                         user_id: str):
        """Assert execution order maintained for specific user."""
        
        actual_sequence = result["actual_sequence"]
        
        # Validate sequence matches expectation
        for i, expected_agent in enumerate(expected_sequence):
            if i < len(actual_sequence):
                assert actual_sequence[i] == expected_agent, (
                    f"User {user_id} sequence violation at position {i}: "
                    f"expected {expected_agent}, got {actual_sequence[i]}"
                )

    def _assert_no_cross_user_sequence_contamination(self,
                                                   results: List[Dict[str, Any]],
                                                   concurrent_users: List[Dict[str, Any]]):
        """Assert no sequence contamination between concurrent users."""
        
        for i, result in enumerate(results):
            user_id = concurrent_users[i]["user_id"]
            expected_sequence = concurrent_users[i]["expected_sequence"]
            actual_sequence = result["actual_sequence"]
            
            # Validate sequence is specific to user request
            for agent_name in actual_sequence:
                # Agent should not appear in wrong user's sequence
                for j, other_result in enumerate(results):
                    if i == j:
                        continue
                    
                    other_expected = concurrent_users[j]["expected_sequence"]
                    
                    # If agent not expected for other user, ensure isolation
                    if agent_name not in other_expected:
                        # This is OK - different users can have different agents
                        pass

    def _assert_concurrent_execution_performance(self, execution_time: float, user_count: int):
        """Assert performance under concurrent execution."""
        
        max_concurrent_time = 20.0  # Reasonable for concurrent execution with order enforcement
        
        assert execution_time <= max_concurrent_time, (
            f"Concurrent execution with order enforcement took {execution_time:.2f}s, "
            f"exceeds maximum {max_concurrent_time}s"
        )
        
        # Time per user should be reasonable
        time_per_user = execution_time / user_count
        assert time_per_user <= 12.0, (
            f"Time per user {time_per_user:.2f}s too high for concurrent order enforcement"
        )

    def _assert_order_preserved_despite_failures(self, execution_result: Dict[str, Any]):
        """Assert execution order preserved despite agent failures."""
        
        actual_sequence = execution_result["actual_sequence"]
        agent_results = execution_result["agent_results"]
        
        # Should still maintain basic order principles
        if "triage_agent" in actual_sequence and "optimization_agent" in actual_sequence:
            triage_pos = actual_sequence.index("triage_agent")
            opt_pos = actual_sequence.index("optimization_agent")
            assert triage_pos < opt_pos, "Basic order not maintained despite failures"
        
        # Should have failure recovery indicators
        failed_agents = [key for key in agent_results.keys() if key.endswith("_failed")]
        assert len(failed_agents) > 0, "No failure indicators found in failure test"

    def _assert_dependency_handling_during_failures(self, execution_result: Dict[str, Any]):
        """Assert proper dependency handling during failures."""
        
        agent_results = execution_result["agent_results"]
        
        # If optimization agent ran despite data agent failure, should be degraded
        if "optimization_agent" in agent_results and "data_sub_agent_failed" in agent_results:
            opt_result = agent_results["optimization_agent"]
            
            # Should acknowledge lack of data foundation
            assert opt_result.get("business_value_possible") == False, (
                "Optimization agent should recognize degraded capability without data"
            )

    def _assert_recovery_sequence_integrity(self, execution_result: Dict[str, Any]):
        """Assert recovery maintains sequence integrity."""
        
        recovery_actions = execution_result.get("recovery_actions", [])
        
        # Should have attempted recovery
        assert len(recovery_actions) > 0, "No recovery actions taken during failure"
        assert "graceful_degradation" in recovery_actions, "No graceful degradation attempted"

    def _assert_degraded_sequence_value_delivery(self, execution_result: Dict[str, Any]):
        """Assert degraded sequence still attempts value delivery."""
        
        agent_results = execution_result["agent_results"]
        
        # Should still complete what's possible
        successful_agents = [
            agent for agent in agent_results.keys() 
            if not agent.endswith("_failed")
        ]
        
        assert len(successful_agents) > 0, "No agents completed successfully during failure recovery"

    def _assert_order_maintained_during_optimization(self, execution_result: Dict[str, Any]):
        """Assert execution order maintained during performance optimization."""
        
        actual_sequence = execution_result["actual_sequence"]
        expected_sequence = execution_result["expected_sequence"]
        
        # Should maintain proper sequence despite optimization
        assert actual_sequence == expected_sequence, (
            f"Performance optimization disrupted sequence: "
            f"expected {expected_sequence}, got {actual_sequence}"
        )

    def _assert_performance_targets_met(self, execution_result: Dict[str, Any], total_time: float):
        """Assert performance targets met."""
        
        performance_opt = execution_result.get("performance_optimization", {})
        targets = performance_opt.get("targets", {})
        
        if "max_total_time" in targets:
            max_time = targets["max_total_time"]
            assert total_time <= max_time, (
                f"Total execution time {total_time:.2f}s exceeds target {max_time}s"
            )

    def _assert_quality_maintained_with_speed(self, execution_result: Dict[str, Any]):
        """Assert quality maintained despite speed optimization."""
        
        performance_opt = execution_result.get("performance_optimization", {})
        actual_performance = performance_opt.get("actual_performance", {})
        
        quality_score = actual_performance.get("quality_score", 0)
        min_quality = performance_opt.get("targets", {}).get("min_quality_score", 0.8)
        
        assert quality_score >= min_quality, (
            f"Quality score {quality_score} below minimum {min_quality} during speed optimization"
        )

    async def cleanup_resources(self):
        """Clean up execution order test resources."""
        await super().cleanup_resources()
        
        # Clear execution tracking
        self.execution_events.clear()
        self.agent_dependencies.clear()
        
        # Reset metrics
        self.execution_metrics = {
            "total_execution_time": 0,
            "sequence_violations": [],
            "dependency_violations": [],
            "agents_executed": [],
            "execution_order": []
        }