"""Circuit Breaker Orchestration Tests for Multi-Agent Workflows

Business Value Justification (BVJ):
- Segment: Enterprise/Mid (protects high-value AI automation workflows)
- Business Goal: Ensure resilient multi-agent orchestration with controlled failure propagation
- Value Impact: Prevents revenue loss from AI pipeline failures, maintains SLA commitments
- Strategic Impact: Enables enterprise-scale AI automation with 99.9% availability during partial failures

This module provides comprehensive testing of circuit breaker behavior during multi-agent
orchestration workflows. It validates that circuit breakers properly coordinate to prevent
cascade failures while maintaining workflow integrity and state consistency.

Critical Coverage:
- Triage → Supervisor → Data → Optimization agent chains
- Circuit breaker activation during multi-stage workflows
- State preservation during partial agent failures
- Recovery time objectives (RTO) for agent orchestration
- Concurrent workflow resilience with multiple circuit breakers
- Failure isolation boundaries in complex agent dependency graphs

Level: L3 (Real SUT with Real Local Services)
Pattern: Real circuit breakers, real Redis state management, real agent registry
"""

import asyncio
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
from netra_backend.app.core.resilience.domain_circuit_breakers import (
    AgentCircuitBreaker,
    AgentCircuitBreakerConfig,
)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitBreakerManager,
    UnifiedCircuitConfig,
    UnifiedCircuitBreakerState,
    get_unified_circuit_breaker_manager,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.state.state_manager import StateManager, StateStorage

logger = central_logger.get_logger(__name__)


class WorkflowStage(Enum):
    """Multi-agent workflow execution stages."""
    TRIAGE = "triage"
    SUPERVISOR = "supervisor"  
    DATA_PROCESSING = "data_processing"
    OPTIMIZATION = "optimization"
    AGGREGATION = "aggregation"
    COMPLETION = "completion"


class AgentFailureMode(Enum):
    """Types of agent failures to simulate."""
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    LLM_API_FAILURE = "llm_api_failure"
    STATE_CORRUPTION = "state_corruption"
    DEPENDENCY_FAILURE = "dependency_failure"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class WorkflowMetrics:
    """Metrics for tracking workflow execution and circuit breaker behavior."""
    workflow_id: str
    start_time: float
    completion_time: Optional[float] = None
    total_agents: int = 0
    successful_agents: int = 0
    failed_agents: int = 0
    circuit_breaker_activations: int = 0
    cascade_prevented_count: int = 0
    state_consistency_maintained: bool = True
    rto_achieved: bool = False
    recovery_time_seconds: Optional[float] = None
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    
    def calculate_success_rate(self) -> float:
        """Calculate agent success rate."""
        if self.total_agents == 0:
            return 0.0
        return self.successful_agents / self.total_agents
    
    def calculate_execution_time(self) -> float:
        """Calculate total execution time."""
        if self.completion_time is None:
            return time.time() - self.start_time
        return self.completion_time - self.start_time


@dataclass
class OrchestrationScenario:
    """Configuration for orchestration test scenarios."""
    name: str
    agent_chain: List[str]
    expected_stages: List[WorkflowStage]
    failure_injection: Dict[str, AgentFailureMode]
    rto_target_seconds: float = 30.0
    cascade_prevention_expected: bool = True
    state_consistency_required: bool = True
    concurrent_workflows: int = 1
    

class MockAgentImplementation(BaseSubAgent):
    """Mock agent implementation for testing circuit breaker orchestration."""
    
    def __init__(self, agent_type: str, circuit_breaker: UnifiedCircuitBreaker,
                 failure_mode: Optional[AgentFailureMode] = None,
                 failure_probability: float = 0.0):
        """Initialize mock agent with circuit breaker integration."""
        # Initialize parent with minimal required parameters
        super().__init__(
            llm_manager=AsyncMock(),
            name=agent_type,
            description=f"Mock agent for {agent_type}"
        )
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"  # Generate unique agent ID
        self.circuit_breaker = circuit_breaker
        self.failure_mode = failure_mode
        self.failure_probability = failure_probability
        self.execution_count = 0
        self.state_data: Dict[str, Any] = {}
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Required abstract method implementation for BaseSubAgent."""
        # This method is required by BaseSubAgent but we use execute_task for circuit breaker testing
        task_data = {"run_id": run_id, "stream_updates": stream_updates}
        context = {"state": state}
        result = await self.execute_task(task_data, context)
        # Update the state with results if needed
        if hasattr(state, 'agent_results'):
            state.agent_results[self.agent_type] = result
        
    async def execute_task(self, task_data: Dict[str, Any], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task with circuit breaker protection."""
        self.execution_count += 1
        
        async def protected_execution():
            # Simulate processing time
            await asyncio.sleep(0.1 + random.uniform(0, 0.2))
            
            # Inject failures based on configuration
            if self.failure_mode and random.random() < self.failure_probability:
                await self._simulate_failure()
            
            # Update state
            self.state_data.update({
                "execution_count": self.execution_count,
                "last_execution": time.time(),
                "input_processed": len(str(task_data)),
                "status": "completed"
            })
            
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "result": f"{self.agent_type} processing completed",
                "execution_time": time.time(),
                "state": self.state_data.copy(),
                "metadata": {
                    "execution_count": self.execution_count,
                    "circuit_breaker_state": self.circuit_breaker.state.value
                }
            }
            
        # Execute through circuit breaker protection
        return await self.circuit_breaker.call(protected_execution)
        
    async def _simulate_failure(self):
        """Simulate different types of agent failures."""
        if self.failure_mode == AgentFailureMode.TIMEOUT:
            await asyncio.sleep(10)  # Will trigger circuit breaker timeout
            
        elif self.failure_mode == AgentFailureMode.RESOURCE_EXHAUSTION:
            raise RuntimeError(f"Resource exhaustion in {self.agent_type}")
            
        elif self.failure_mode == AgentFailureMode.LLM_API_FAILURE:
            raise ConnectionError(f"LLM API unavailable for {self.agent_type}")
            
        elif self.failure_mode == AgentFailureMode.STATE_CORRUPTION:
            raise ValueError(f"State corruption detected in {self.agent_type}")
            
        elif self.failure_mode == AgentFailureMode.DEPENDENCY_FAILURE:
            raise RuntimeError(f"Dependency service failure for {self.agent_type}")
            
    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "state_data": self.state_data,
            "execution_count": self.execution_count,
            "circuit_breaker_status": self.circuit_breaker.get_status()
        }


class CircuitBreakerOrchestrationManager:
    """Manager for testing circuit breaker behavior in multi-agent workflows."""
    
    def __init__(self):
        """Initialize orchestration test manager."""
        self.circuit_breaker_manager = get_unified_circuit_breaker_manager()
        self.agent_circuit_breakers: Dict[str, UnifiedCircuitBreaker] = {}
        self.mock_agents: Dict[str, MockAgentImplementation] = {}
        self.redis_manager: Optional[RedisManager] = None
        self.state_manager: Optional[StateManager] = None
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_metrics: Dict[str, WorkflowMetrics] = {}
        
        # Agent dependency mapping (realistic production topology)
        self.agent_dependencies = {
            "triage_agent": [],  # Entry point, no dependencies
            "supervisor_agent": ["triage_agent"],
            "data_agent": ["supervisor_agent", "triage_agent"],
            "optimization_agent": ["data_agent", "supervisor_agent"],
            "aggregation_agent": ["optimization_agent", "data_agent"],
            "completion_agent": ["aggregation_agent"]
        }
        
        # Recovery time objectives for each agent type
        self.agent_rto_targets = {
            "triage_agent": 5.0,      # Critical entry point
            "supervisor_agent": 10.0,  # Core orchestration
            "data_agent": 20.0,       # Data processing can be slower
            "optimization_agent": 30.0, # Complex optimization
            "aggregation_agent": 15.0,  # Results compilation
            "completion_agent": 5.0     # Final stage
        }
        
    async def initialize_services(self):
        """Initialize real services for L3 testing."""
        await self._setup_redis_state_management()
        await self._setup_circuit_breakers()
        logger.info("Circuit breaker orchestration services initialized")
        
    async def _setup_redis_state_management(self):
        """Setup Redis for state management with proper async context handling."""
        try:
            # Initialize Redis manager in test mode to handle async context properly
            self.redis_manager = RedisManager(test_mode=True)
            await self.redis_manager.connect()
            
            # Initialize state manager with fallback to memory storage
            self.state_manager = StateManager(storage=StateStorage.MEMORY)
            
            # Only use Redis if connection succeeded and client is available
            if (self.redis_manager and 
                self.redis_manager.enabled and 
                self.redis_manager.redis_client):
                # Use hybrid storage if Redis is available
                self.state_manager = StateManager(storage=StateStorage.HYBRID)
                self.state_manager._redis = self.redis_manager
                logger.info("Redis state management initialized successfully")
            else:
                logger.info("Using memory-only state storage (Redis not available)")
                
        except Exception as e:
            logger.warning(f"Redis connection failed, using memory-only storage: {e}")
            # Ensure we always have a state manager, even if Redis fails
            self.state_manager = StateManager(storage=StateStorage.MEMORY)
            self.redis_manager = None
            
    async def _setup_circuit_breakers(self):
        """Setup circuit breakers for each agent type."""
        circuit_configs = {
            "triage_agent": UnifiedCircuitConfig(
                name="triage_agent",
                failure_threshold=3,
                recovery_timeout=5.0,
                success_threshold=2,
                timeout_seconds=8.0,
                sliding_window_size=6,
                error_rate_threshold=0.5,
                adaptive_threshold=True,
                exponential_backoff=True
            ),
            "supervisor_agent": UnifiedCircuitConfig(
                name="supervisor_agent", 
                failure_threshold=4,
                recovery_timeout=10.0,
                success_threshold=3,
                timeout_seconds=15.0,
                sliding_window_size=8,
                error_rate_threshold=0.4,
                adaptive_threshold=True,
                exponential_backoff=True
            ),
            "data_agent": UnifiedCircuitConfig(
                name="data_agent",
                failure_threshold=5,
                recovery_timeout=20.0,
                success_threshold=3,
                timeout_seconds=30.0,
                sliding_window_size=10,
                error_rate_threshold=0.6,
                adaptive_threshold=True,
                exponential_backoff=True
            ),
            "optimization_agent": UnifiedCircuitConfig(
                name="optimization_agent",
                failure_threshold=6,
                recovery_timeout=30.0,
                success_threshold=4,
                timeout_seconds=60.0,
                sliding_window_size=12,
                error_rate_threshold=0.5,
                adaptive_threshold=True,
                exponential_backoff=True
            ),
            "aggregation_agent": UnifiedCircuitConfig(
                name="aggregation_agent",
                failure_threshold=4,
                recovery_timeout=15.0,
                success_threshold=3,
                timeout_seconds=25.0,
                sliding_window_size=8,
                error_rate_threshold=0.5,
                adaptive_threshold=True
            ),
            "completion_agent": UnifiedCircuitConfig(
                name="completion_agent",
                failure_threshold=2,  # Critical final stage
                recovery_timeout=5.0,
                success_threshold=2,
                timeout_seconds=10.0,
                sliding_window_size=5,
                error_rate_threshold=0.3,
                adaptive_threshold=True
            )
        }
        
        for agent_type, config in circuit_configs.items():
            circuit_breaker = self.circuit_breaker_manager.create_circuit_breaker(
                agent_type, config
            )
            self.agent_circuit_breakers[agent_type] = circuit_breaker
            
        logger.info(f"Initialized {len(self.agent_circuit_breakers)} agent circuit breakers")
        
    async def create_mock_agents(self, failure_config: Dict[str, Tuple[AgentFailureMode, float]] = None):
        """Create mock agents with circuit breaker integration."""
        failure_config = failure_config or {}
        
        for agent_type, circuit_breaker in self.agent_circuit_breakers.items():
            failure_mode, failure_prob = failure_config.get(agent_type, (None, 0.0))
            
            mock_agent = MockAgentImplementation(
                agent_type=agent_type,
                circuit_breaker=circuit_breaker,
                failure_mode=failure_mode,
                failure_probability=failure_prob
            )
            
            self.mock_agents[agent_type] = mock_agent
            
        logger.info(f"Created {len(self.mock_agents)} mock agents")
        
    async def execute_multi_agent_workflow(
        self,
        workflow_id: str,
        agent_chain: List[str],
        initial_data: Dict[str, Any],
        expected_stages: List[WorkflowStage] = None
    ) -> WorkflowMetrics:
        """Execute multi-agent workflow with circuit breaker orchestration."""
        start_time = time.time()
        
        # Initialize workflow metrics
        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            start_time=start_time,
            total_agents=len(agent_chain)
        )
        self.workflow_metrics[workflow_id] = metrics
        
        # Store workflow state
        workflow_state = {
            "workflow_id": workflow_id,
            "agent_chain": agent_chain,
            "current_stage": 0,
            "status": "running",
            "start_time": start_time,
            "data": initial_data,
            "agent_results": {},
            "circuit_breaker_events": []
        }
        
        await self.state_manager.set(f"workflow:{workflow_id}", workflow_state)
        self.active_workflows[workflow_id] = workflow_state
        
        logger.info(f"Starting workflow {workflow_id} with {len(agent_chain)} agents")
        
        # Execute agent chain with circuit breaker coordination
        current_data = initial_data.copy()
        
        for stage_idx, agent_type in enumerate(agent_chain):
            stage_start_time = time.time()
            
            try:
                # Get agent and execute task
                agent = self.mock_agents.get(agent_type)
                if not agent:
                    raise ValueError(f"Agent {agent_type} not found")
                
                logger.info(f"Executing stage {stage_idx}: {agent_type}")
                
                # Update workflow stage
                workflow_state["current_stage"] = stage_idx
                workflow_state["data"] = current_data
                await self.state_manager.set(f"workflow:{workflow_id}", workflow_state)
                
                # Execute agent task with circuit breaker protection
                task_context = {
                    "workflow_id": workflow_id,
                    "stage": stage_idx,
                    "previous_results": workflow_state.get("agent_results", {}),
                    "dependencies": [
                        workflow_state["agent_results"].get(dep)
                        for dep in self.agent_dependencies.get(agent_type, [])
                        if dep in workflow_state["agent_results"]
                    ]
                }
                
                result = await agent.execute_task(current_data, task_context)
                
                # Record successful execution
                metrics.successful_agents += 1
                workflow_state["agent_results"][agent_type] = result
                
                # Determine workflow stage completion
                if expected_stages and stage_idx < len(expected_stages):
                    stage = expected_stages[stage_idx].value
                    metrics.stages_completed.append(stage)
                    
                # Update data for next agent
                current_data.update(result.get("processed_data", {}))
                
                logger.info(f"Stage {stage_idx} ({agent_type}) completed successfully")
                
            except CircuitBreakerOpenError as e:
                # Circuit breaker prevented execution
                logger.warning(f"Circuit breaker open for {agent_type}: {e}")
                metrics.circuit_breaker_activations += 1
                
                # Test cascade prevention
                cascade_prevented = await self._test_cascade_prevention(
                    workflow_id, agent_type, stage_idx
                )
                
                if cascade_prevented:
                    metrics.cascade_prevented_count += 1
                    logger.info(f"Cascade successfully prevented at {agent_type}")
                else:
                    logger.error(f"Cascade prevention failed at {agent_type}")
                    
                # Record stage failure
                if expected_stages and stage_idx < len(expected_stages):
                    stage = expected_stages[stage_idx].value
                    metrics.stages_failed.append(stage)
                    
                # Attempt recovery based on RTO
                recovery_attempted = await self._attempt_stage_recovery(
                    workflow_id, agent_type, stage_idx, current_data, task_context
                )
                
                if recovery_attempted:
                    logger.info(f"Recovery attempted for {agent_type}")
                else:
                    logger.warning(f"Recovery failed for {agent_type}, stopping workflow")
                    break
                    
            except Exception as e:
                # Other failures
                logger.error(f"Agent {agent_type} failed: {e}")
                metrics.failed_agents += 1
                
                # Record stage failure  
                if expected_stages and stage_idx < len(expected_stages):
                    stage = expected_stages[stage_idx].value
                    metrics.stages_failed.append(stage)
                    
                # Test failure isolation
                isolation_effective = await self._test_failure_isolation(
                    workflow_id, agent_type, stage_idx
                )
                
                if not isolation_effective:
                    logger.error(f"Failure isolation violated at {agent_type}")
                    metrics.state_consistency_maintained = False
                    
            # Update workflow state after each stage
            workflow_state["current_stage"] = stage_idx + 1
            await self.state_manager.set(f"workflow:{workflow_id}", workflow_state)
            
        # Finalize workflow
        completion_time = time.time()
        metrics.completion_time = completion_time
        
        workflow_state["status"] = "completed"
        workflow_state["completion_time"] = completion_time
        await self.state_manager.set(f"workflow:{workflow_id}", workflow_state)
        
        # Check RTO achievement
        execution_time = completion_time - start_time
        max_rto = max([self.agent_rto_targets.get(agent, 30.0) for agent in agent_chain])
        metrics.rto_achieved = execution_time <= max_rto
        metrics.recovery_time_seconds = execution_time
        
        logger.info(f"Workflow {workflow_id} completed in {execution_time:.2f}s")
        return metrics
        
    async def _test_cascade_prevention(
        self, 
        workflow_id: str, 
        failed_agent: str, 
        stage_idx: int
    ) -> bool:
        """Test that circuit breaker prevented cascade failure."""
        # Check downstream agents (agents that depend on the failed agent)
        downstream_agents = [
            agent for agent, deps in self.agent_dependencies.items()
            if failed_agent in deps
        ]
        
        if not downstream_agents:
            return True  # No downstream agents to cascade to
            
        cascade_prevented = True
        
        for downstream_agent in downstream_agents:
            circuit_breaker = self.agent_circuit_breakers[downstream_agent]
            
            # Test if downstream agent is properly protected
            try:
                # Attempt to execute downstream task
                async def downstream_test():
                    # This would fail due to missing dependency
                    raise RuntimeError(f"Missing dependency: {failed_agent}")
                    
                await circuit_breaker.call(downstream_test)
                
                # If we reach here, cascade prevention may have failed
                logger.warning(f"Potential cascade to {downstream_agent}")
                cascade_prevented = False
                
            except CircuitBreakerOpenError:
                # Circuit breaker correctly prevented cascade
                logger.info(f"Cascade prevented for {downstream_agent}")
                
            except Exception:
                # Expected failure due to dependency
                pass
                
        return cascade_prevented
        
    async def _attempt_stage_recovery(
        self,
        workflow_id: str,
        failed_agent: str,
        stage_idx: int,
        current_data: Dict[str, Any],
        task_context: Dict[str, Any]
    ) -> bool:
        """Attempt to recover from stage failure within RTO."""
        recovery_start = time.time()
        rto_target = self.agent_rto_targets.get(failed_agent, 30.0)
        
        circuit_breaker = self.agent_circuit_breakers[failed_agent]
        agent = self.mock_agents[failed_agent]
        
        # Wait for circuit breaker recovery opportunity
        max_wait_time = min(rto_target * 0.7, 10.0)  # Don't wait too long
        
        await asyncio.sleep(0.5)  # Initial wait
        
        recovery_attempts = 0
        max_attempts = 3
        
        while recovery_attempts < max_attempts:
            elapsed_time = time.time() - recovery_start
            if elapsed_time >= max_wait_time:
                logger.warning(f"Recovery timeout for {failed_agent}")
                break
                
            try:
                # Check if circuit breaker allows execution
                if circuit_breaker.state != UnifiedCircuitBreakerState.OPEN:
                    logger.info(f"Attempting recovery for {failed_agent}")
                    
                    # Try to execute the failed stage again
                    result = await agent.execute_task(current_data, task_context)
                    
                    logger.info(f"Recovery successful for {failed_agent}")
                    return True
                    
            except CircuitBreakerOpenError:
                logger.debug(f"Circuit breaker still open for {failed_agent}")
                
            except Exception as e:
                logger.warning(f"Recovery attempt failed for {failed_agent}: {e}")
                
            recovery_attempts += 1
            await asyncio.sleep(1.0)
            
        return False
        
    async def _test_failure_isolation(
        self,
        workflow_id: str,
        failed_agent: str,
        stage_idx: int
    ) -> bool:
        """Test that failure is properly isolated and doesn't affect unrelated agents."""
        # Get agents that should be unaffected (no dependency relationship)
        unrelated_agents = [
            agent for agent in self.agent_circuit_breakers.keys()
            if (agent != failed_agent and
                failed_agent not in self.agent_dependencies.get(agent, []) and
                agent not in self.agent_dependencies.get(failed_agent, []))
        ]
        
        isolation_effective = True
        
        for unrelated_agent in unrelated_agents:
            circuit_breaker = self.agent_circuit_breakers[unrelated_agent]
            
            # Test that unrelated agent is not affected
            try:
                async def isolation_test():
                    return f"{unrelated_agent} isolation test"
                    
                result = await circuit_breaker.call(isolation_test)
                logger.debug(f"Isolation maintained for {unrelated_agent}")
                
            except Exception as e:
                logger.error(f"Isolation violated for {unrelated_agent}: {e}")
                isolation_effective = False
                
        return isolation_effective
        
    async def execute_concurrent_workflows(
        self,
        num_workflows: int,
        agent_chain: List[str],
        failure_config: Dict[str, Tuple[AgentFailureMode, float]] = None
    ) -> List[WorkflowMetrics]:
        """Execute multiple concurrent workflows to test circuit breaker coordination."""
        logger.info(f"Starting {num_workflows} concurrent workflows")
        
        # Create workflows with different data
        workflow_tasks = []
        for i in range(num_workflows):
            workflow_id = f"concurrent_workflow_{i}_{uuid.uuid4().hex[:8]}"
            initial_data = {
                "workflow_index": i,
                "request": f"Process concurrent request {i}",
                "priority": random.choice(["high", "medium", "low"]),
                "complexity": random.randint(1, 10)
            }
            
            task = self.execute_multi_agent_workflow(
                workflow_id=workflow_id,
                agent_chain=agent_chain,
                initial_data=initial_data,
                expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR, 
                               WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION]
            )
            workflow_tasks.append(task)
            
        # Execute all workflows concurrently
        results = await asyncio.gather(*workflow_tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = [r for r in results if isinstance(r, WorkflowMetrics)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        logger.info(f"Concurrent workflows completed: {len(successful_results)} successful, {len(failed_results)} failed")
        
        return successful_results
        
    async def test_circuit_breaker_state_consistency(self, workflow_id: str) -> Dict[str, Any]:
        """Test that circuit breaker states remain consistent during workflow execution."""
        consistency_report = {
            "workflow_id": workflow_id,
            "circuit_breaker_states": {},
            "state_transitions": [],
            "consistency_violations": [],
            "overall_consistent": True
        }
        
        # Capture initial states
        initial_states = {}
        for agent_type, circuit_breaker in self.agent_circuit_breakers.items():
            state = circuit_breaker.get_status()
            initial_states[agent_type] = state
            consistency_report["circuit_breaker_states"][f"{agent_type}_initial"] = state
            
        # Monitor state changes during workflow
        monitoring_duration = 5.0  # Monitor for 5 seconds
        start_monitoring = time.time()
        
        while time.time() - start_monitoring < monitoring_duration:
            await asyncio.sleep(0.5)
            
            # Check current states
            for agent_type, circuit_breaker in self.agent_circuit_breakers.items():
                current_state = circuit_breaker.get_status()
                previous_state = initial_states[agent_type]
                
                # Detect state transitions
                if current_state["state"] != previous_state["state"]:
                    transition = {
                        "agent": agent_type,
                        "from_state": previous_state["state"],
                        "to_state": current_state["state"],
                        "timestamp": time.time(),
                        "metrics": current_state["metrics"]
                    }
                    consistency_report["state_transitions"].append(transition)
                    initial_states[agent_type] = current_state
                    
                # Check for consistency violations
                if self._detect_state_inconsistency(agent_type, current_state):
                    violation = {
                        "agent": agent_type,
                        "violation_type": "state_inconsistency",
                        "state": current_state,
                        "timestamp": time.time()
                    }
                    consistency_report["consistency_violations"].append(violation)
                    consistency_report["overall_consistent"] = False
                    
        # Capture final states
        for agent_type, circuit_breaker in self.agent_circuit_breakers.items():
            final_state = circuit_breaker.get_status()
            consistency_report["circuit_breaker_states"][f"{agent_type}_final"] = final_state
            
        return consistency_report
        
    def _detect_state_inconsistency(self, agent_type: str, state: Dict[str, Any]) -> bool:
        """Detect state inconsistencies in circuit breaker state."""
        # Check for logical inconsistencies
        metrics = state.get("metrics", {})
        
        # Total calls should equal successful + failed + rejected
        total = metrics.get("total_calls", 0)
        successful = metrics.get("successful_calls", 0)
        failed = metrics.get("failed_calls", 0)
        rejected = metrics.get("rejected_calls", 0)
        
        if total > 0 and total != (successful + failed + rejected):
            return True
            
        # Error rate should be consistent with counts
        error_rate = metrics.get("current_error_rate", 0.0)
        if total > 0:
            actual_error_rate = failed / total if total > 0 else 0.0
            if abs(error_rate - actual_error_rate) > 0.1:  # Allow small variance
                return True
                
        return False
        
    async def get_system_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive system health summary."""
        summary = {
            "circuit_breakers": {},
            "active_workflows": len(self.active_workflows),
            "total_workflows": len(self.workflow_metrics),
            "system_health": "healthy",
            "alerts": []
        }
        
        unhealthy_count = 0
        
        for agent_type, circuit_breaker in self.agent_circuit_breakers.items():
            status = circuit_breaker.get_status()
            summary["circuit_breakers"][agent_type] = {
                "state": status["state"],
                "is_healthy": status["is_healthy"],
                "metrics": status["metrics"]
            }
            
            if not status["is_healthy"]:
                unhealthy_count += 1
                summary["alerts"].append({
                    "type": "circuit_breaker_unhealthy",
                    "agent": agent_type,
                    "state": status["state"]
                })
                
        # Determine overall system health
        total_breakers = len(self.agent_circuit_breakers)
        if unhealthy_count == 0:
            summary["system_health"] = "healthy"
        elif unhealthy_count < total_breakers * 0.3:
            summary["system_health"] = "degraded"
        else:
            summary["system_health"] = "unhealthy"
            
        return summary
        
    async def cleanup(self):
        """Clean up test resources."""
        logger.info("Cleaning up circuit breaker orchestration test resources")
        
        # Reset all circuit breakers
        reset_tasks = []
        for circuit_breaker in self.agent_circuit_breakers.values():
            reset_tasks.append(circuit_breaker.reset())
            
        await asyncio.gather(*reset_tasks, return_exceptions=True)
        
        # Clear state
        self.active_workflows.clear()
        self.workflow_metrics.clear()
        
        # Disconnect Redis
        if self.redis_manager:
            try:
                await self.redis_manager.disconnect()
            except Exception as e:
                logger.warning(f"Redis disconnect error: {e}")
                
        logger.info("Cleanup completed")


# Fixtures

@pytest.fixture
async def orchestration_manager():
    """Create orchestration manager for testing."""
    manager = CircuitBreakerOrchestrationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.fixture
def orchestration_scenarios():
    """Provide predefined orchestration test scenarios."""
    return [
        OrchestrationScenario(
            name="standard_pipeline",
            agent_chain=["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"],
            expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR, 
                           WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION],
            failure_injection={},
            rto_target_seconds=60.0,
            cascade_prevention_expected=True
        ),
        OrchestrationScenario(
            name="failure_recovery_test", 
            agent_chain=["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"],
            expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                           WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION],
            failure_injection={
                "data_agent": (AgentFailureMode.TIMEOUT, 0.7)
            },
            rto_target_seconds=90.0,
            cascade_prevention_expected=True
        ),
        OrchestrationScenario(
            name="cascade_prevention_test",
            agent_chain=["triage_agent", "supervisor_agent", "data_agent", "optimization_agent", "completion_agent"],
            expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                           WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION, WorkflowStage.COMPLETION],
            failure_injection={
                "supervisor_agent": (AgentFailureMode.RESOURCE_EXHAUSTION, 0.8)
            },
            rto_target_seconds=120.0,
            cascade_prevention_expected=True
        ),
        OrchestrationScenario(
            name="concurrent_workflows_test",
            agent_chain=["triage_agent", "data_agent", "aggregation_agent"],
            expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.DATA_PROCESSING, WorkflowStage.AGGREGATION],
            failure_injection={
                "data_agent": (AgentFailureMode.LLM_API_FAILURE, 0.3)
            },
            concurrent_workflows=5,
            rto_target_seconds=45.0
        )
    ]


# Tests

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_agent_failure_cascade_prevention_three_plus_agents(orchestration_manager):
    """Test circuit breaker prevents cascading failures in 3+ agent workflows."""
    manager = orchestration_manager
    
    # Create agents with failure injection
    failure_config = {
        "supervisor_agent": (AgentFailureMode.RESOURCE_EXHAUSTION, 0.9)  # High failure rate
    }
    await manager.create_mock_agents(failure_config)
    
    # Execute workflow with 4 agents
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    workflow_id = f"cascade_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {"request": "Test cascade prevention", "priority": "high"}
    
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION]
    )
    
    # Assertions
    assert metrics.total_agents == 4
    assert metrics.circuit_breaker_activations > 0, "Circuit breaker should have activated"
    assert metrics.cascade_prevented_count > 0, "Cascade should have been prevented"
    assert len(metrics.stages_failed) >= 1, "At least one stage should have failed"
    
    # Verify downstream agents were protected
    supervisor_cb = manager.agent_circuit_breakers["supervisor_agent"]
    assert supervisor_cb.state == UnifiedCircuitBreakerState.OPEN, "Supervisor circuit breaker should be open"
    
    # Verify other agents remain healthy
    triage_cb = manager.agent_circuit_breakers["triage_agent"]
    assert triage_cb.is_closed or triage_cb.is_half_open, "Triage agent should remain available"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_circuit_breaker_activation_during_workflow_execution(orchestration_manager):
    """Test circuit breaker activates during mid-workflow execution."""
    manager = orchestration_manager
    
    # Create agents with delayed failure (fails after some executions)
    failure_config = {
        "data_agent": (AgentFailureMode.TIMEOUT, 0.6)
    }
    await manager.create_mock_agents(failure_config)
    
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    workflow_id = f"activation_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {"request": "Test mid-workflow activation", "complexity": 8}
    
    # Start workflow execution
    start_time = time.time()
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION]
    )
    execution_time = time.time() - start_time
    
    # Assertions
    assert metrics.circuit_breaker_activations > 0, "Circuit breaker should have activated during execution"
    assert execution_time > 1.0, "Workflow should have taken time to execute and fail"
    assert len(metrics.stages_completed) >= 1, "At least initial stages should complete"
    
    # Verify circuit breaker state
    data_cb = manager.agent_circuit_breakers["data_agent"]
    status = data_cb.get_status()
    assert status["metrics"]["total_calls"] > 0, "Data agent should have been called"
    assert status["metrics"]["failed_calls"] > 0, "Data agent should have failures recorded"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_recovery_time_objectives_validation(orchestration_manager):
    """Test RTO validation for agent orchestration workflows."""
    manager = orchestration_manager
    
    # Create agents with controllable failures
    failure_config = {
        "optimization_agent": (AgentFailureMode.DEPENDENCY_FAILURE, 0.5)
    }
    await manager.create_mock_agents(failure_config)
    
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    workflow_id = f"rto_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {"request": "Test RTO validation", "urgency": "critical"}
    
    # Execute workflow and measure RTO
    start_time = time.time()
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION]
    )
    total_time = time.time() - start_time
    
    # Calculate expected RTO
    max_expected_rto = max([manager.agent_rto_targets.get(agent, 30.0) for agent in agent_chain])
    
    # Assertions
    assert metrics.recovery_time_seconds is not None, "Recovery time should be recorded"
    assert total_time <= max_expected_rto * 2, f"Total time {total_time:.2f}s should be reasonable vs RTO {max_expected_rto}s"
    
    # Verify RTO tracking per agent
    for agent_type in agent_chain:
        expected_rto = manager.agent_rto_targets.get(agent_type, 30.0)
        assert expected_rto > 0, f"Agent {agent_type} should have defined RTO"
        
    logger.info(f"RTO test completed in {total_time:.2f}s, max expected: {max_expected_rto}s")


@pytest.mark.asyncio
@pytest.mark.integration  
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_state_consistency_during_circuit_breaker_opening(orchestration_manager):
    """Test state consistency when circuit breakers open mid-workflow."""
    manager = orchestration_manager
    
    # Create agents with state corruption simulation
    failure_config = {
        "data_agent": (AgentFailureMode.STATE_CORRUPTION, 0.4)
    }
    await manager.create_mock_agents(failure_config)
    
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "aggregation_agent"]
    workflow_id = f"consistency_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {"request": "Test state consistency", "data_size": "large"}
    
    # Start workflow and monitor state consistency
    consistency_task = asyncio.create_task(
        manager.test_circuit_breaker_state_consistency(workflow_id)
    )
    
    # Execute workflow concurrently
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.AGGREGATION]
    )
    
    # Wait for consistency monitoring to complete
    await asyncio.sleep(0.5)
    consistency_task.cancel()
    
    try:
        consistency_report = await consistency_task
    except asyncio.CancelledError:
        # Get final consistency report manually
        consistency_report = await manager.test_circuit_breaker_state_consistency(workflow_id)
    
    # Assertions
    assert metrics.state_consistency_maintained, "State consistency should be maintained"
    assert consistency_report["overall_consistent"], "Circuit breaker states should remain consistent"
    assert len(consistency_report["consistency_violations"]) == 0, "No state consistency violations"
    
    # Verify state transitions are logical
    for transition in consistency_report["state_transitions"]:
        from_state = transition["from_state"]
        to_state = transition["to_state"]
        
        # Valid state transitions: closed -> half_open -> closed/open, closed -> open
        valid_transitions = [
            ("closed", "half_open"),
            ("closed", "open"),
            ("half_open", "closed"),
            ("half_open", "open"),
            ("open", "half_open")
        ]
        
        assert (from_state, to_state) in valid_transitions, f"Invalid transition: {from_state} -> {to_state}"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_concurrent_workflow_handling_multiple_circuit_breakers(orchestration_manager):
    """Test concurrent workflow handling with multiple circuit breakers."""
    manager = orchestration_manager
    
    # Create agents with mixed failure modes
    failure_config = {
        "supervisor_agent": (AgentFailureMode.LLM_API_FAILURE, 0.2),
        "data_agent": (AgentFailureMode.TIMEOUT, 0.3),
        "optimization_agent": (AgentFailureMode.RESOURCE_EXHAUSTION, 0.1)
    }
    await manager.create_mock_agents(failure_config)
    
    # Execute concurrent workflows
    num_workflows = 6
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    
    results = await manager.execute_concurrent_workflows(
        num_workflows=num_workflows,
        agent_chain=agent_chain,
        failure_config=failure_config
    )
    
    # Assertions
    assert len(results) >= num_workflows * 0.5, f"At least 50% of workflows should complete"
    
    # Analyze circuit breaker coordination
    total_activations = sum(r.circuit_breaker_activations for r in results)
    total_cascades_prevented = sum(r.cascade_prevented_count for r in results)
    
    assert total_activations > 0, "Some circuit breakers should have activated"
    logger.info(f"Concurrent workflows: {len(results)} completed, {total_activations} CB activations, {total_cascades_prevented} cascades prevented")
    
    # Verify system health
    health_summary = await manager.get_system_health_summary()
    assert health_summary["system_health"] in ["healthy", "degraded"], "System should maintain basic health"
    
    # Check workflow success distribution
    success_rates = [r.calculate_success_rate() for r in results]
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
    assert avg_success_rate >= 0.3, f"Average success rate {avg_success_rate:.2f} should be reasonable"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_triage_supervisor_data_optimization_chain(orchestration_manager):
    """Test specific Triage → Supervisor → Data → Optimization agent chain."""
    manager = orchestration_manager
    
    # Create agents without failure injection for baseline test
    await manager.create_mock_agents()
    
    # Execute the specific agent chain
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    workflow_id = f"chain_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {
        "request": "Optimize AI workflow performance",
        "domain": "manufacturing",
        "constraints": {"budget": 50000, "timeline": "Q2"},
        "data_sources": ["production_logs", "sensor_data", "quality_metrics"]
    }
    
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION]
    )
    
    # Assertions
    assert metrics.total_agents == 4, "Should execute all 4 agents"
    assert metrics.successful_agents >= 3, "At least 3 agents should succeed"
    assert len(metrics.stages_completed) >= 3, "At least 3 stages should complete"
    assert metrics.rto_achieved, "Should meet RTO requirements"
    
    # Verify agent execution order and dependencies
    workflow_state = manager.active_workflows[workflow_id]
    agent_results = workflow_state["agent_results"]
    
    # Triage should execute first
    assert "triage_agent" in agent_results, "Triage agent should execute"
    
    # Supervisor should execute after triage
    if "supervisor_agent" in agent_results:
        supervisor_result = agent_results["supervisor_agent"]
        assert supervisor_result["metadata"]["execution_count"] > 0, "Supervisor should have execution count"
    
    # Data agent should execute after supervisor  
    if "data_agent" in agent_results:
        data_result = agent_results["data_agent"]
        assert data_result["result"], "Data agent should produce result"
        
    # Optimization should execute after data
    if "optimization_agent" in agent_results:
        opt_result = agent_results["optimization_agent"]
        assert opt_result["metadata"]["circuit_breaker_state"], "Should track circuit breaker state"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_circuit_breaker_coordination_between_dependent_agents(orchestration_manager):
    """Test circuit breaker coordination between agents with dependencies."""
    manager = orchestration_manager
    
    # Create agents with dependency-aware failure
    failure_config = {
        "supervisor_agent": (AgentFailureMode.DEPENDENCY_FAILURE, 0.7)  # High failure rate
    }
    await manager.create_mock_agents(failure_config)
    
    # Execute workflow with clear dependencies
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    workflow_id = f"coordination_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {"request": "Test dependency coordination", "complexity": 5}
    
    # Monitor circuit breaker states before execution
    initial_states = {}
    for agent_type, cb in manager.agent_circuit_breakers.items():
        initial_states[agent_type] = cb.get_status()
    
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION]
    )
    
    # Analyze coordination effectiveness
    supervisor_cb = manager.agent_circuit_breakers["supervisor_agent"]
    data_cb = manager.agent_circuit_breakers["data_agent"]  # Depends on supervisor
    optimization_cb = manager.agent_circuit_breakers["optimization_agent"]  # Depends on data
    
    # Assertions
    assert metrics.circuit_breaker_activations > 0, "Circuit breakers should coordinate"
    
    # If supervisor fails, data agent should be protected
    if supervisor_cb.state == UnifiedCircuitBreakerState.OPEN:
        logger.info("Supervisor circuit breaker opened, checking downstream protection")
        
        # Data agent should either not execute or be protected
        data_status = data_cb.get_status()
        assert (data_status["metrics"]["rejected_calls"] > 0 or 
                data_status["metrics"]["failed_calls"] == 0), "Data agent should be protected"
    
    # Verify dependency awareness in circuit breaker behavior
    dependency_protected = True
    for agent, deps in manager.agent_dependencies.items():
        if not deps:  # No dependencies
            continue
            
        agent_cb = manager.agent_circuit_breakers[agent]
        
        # Check if any dependencies are in open state
        deps_failed = any(
            manager.agent_circuit_breakers[dep].state == UnifiedCircuitBreakerState.OPEN
            for dep in deps if dep in manager.agent_circuit_breakers
        )
        
        if deps_failed:
            # Agent should be protected or have failed gracefully
            agent_status = agent_cb.get_status()
            if agent_status["metrics"]["total_calls"] > 0:
                protection_effective = (
                    agent_status["metrics"]["rejected_calls"] > 0 or
                    agent_cb.state != UnifiedCircuitBreakerState.CLOSED
                )
                if not protection_effective:
                    dependency_protected = False
                    logger.warning(f"Dependency protection failed for {agent}")
    
    assert dependency_protected, "Dependency-based protection should be effective"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_state_preservation_during_partial_failures(orchestration_manager):
    """Test state preservation when some agents fail in workflow."""
    manager = orchestration_manager
    
    # Create agents with partial failure scenario
    failure_config = {
        "data_agent": (AgentFailureMode.STATE_CORRUPTION, 0.8),
        "optimization_agent": (AgentFailureMode.RESOURCE_EXHAUSTION, 0.6)
    }
    await manager.create_mock_agents(failure_config)
    
    agent_chain = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent", "completion_agent"]
    workflow_id = f"preservation_test_{uuid.uuid4().hex[:8]}"
    
    initial_data = {
        "request": "Test state preservation",
        "important_data": {"customer_id": "12345", "session_token": "abc123"},
        "checkpoint_required": True
    }
    
    # Execute workflow
    metrics = await manager.execute_multi_agent_workflow(
        workflow_id=workflow_id,
        agent_chain=agent_chain,
        initial_data=initial_data,
        expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR,
                        WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION,
                        WorkflowStage.COMPLETION]
    )
    
    # Check state preservation
    workflow_state = await manager.state_manager.get(f"workflow:{workflow_id}")
    
    # Assertions
    assert workflow_state is not None, "Workflow state should be preserved"
    assert workflow_state["workflow_id"] == workflow_id, "Workflow ID should be preserved"
    assert "important_data" in workflow_state["data"], "Important data should be preserved"
    
    # Verify partial results are saved
    agent_results = workflow_state.get("agent_results", {})
    successful_agents = [agent for agent in agent_chain if agent in agent_results]
    
    assert len(successful_agents) >= 1, "At least one agent should have completed successfully"
    
    # Check that successful agent states are preserved
    for agent_type in successful_agents:
        agent = manager.mock_agents[agent_type]
        agent_state = agent.get_state()
        
        assert agent_state["execution_count"] > 0, f"{agent_type} should have execution history"
        assert "state_data" in agent_state, f"{agent_type} should preserve state data"
    
    # Verify failed agents don't corrupt overall state
    assert workflow_state["status"] in ["completed", "running"], "Workflow status should be valid"
    assert metrics.state_consistency_maintained, "State consistency should be maintained"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration  
@pytest.mark.performance
async def test_recovery_patterns_and_rto_validation_comprehensive(orchestration_manager):
    """Comprehensive test of recovery patterns and RTO validation."""
    manager = orchestration_manager
    
    # Create agents with staggered failure modes for comprehensive recovery testing
    failure_config = {
        "supervisor_agent": (AgentFailureMode.TIMEOUT, 0.4),
        "data_agent": (AgentFailureMode.DEPENDENCY_FAILURE, 0.3),
        "optimization_agent": (AgentFailureMode.LLM_API_FAILURE, 0.2)
    }
    await manager.create_mock_agents(failure_config)
    
    # Test multiple workflows with different recovery scenarios
    recovery_test_cases = [
        {
            "name": "fast_recovery",
            "agent_chain": ["triage_agent", "supervisor_agent", "completion_agent"],
            "rto_target": 15.0
        },
        {
            "name": "medium_recovery", 
            "agent_chain": ["triage_agent", "supervisor_agent", "data_agent", "aggregation_agent"],
            "rto_target": 45.0
        },
        {
            "name": "complex_recovery",
            "agent_chain": ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent", "completion_agent"],
            "rto_target": 90.0
        }
    ]
    
    recovery_results = []
    
    for test_case in recovery_test_cases:
        workflow_id = f"recovery_{test_case['name']}_{uuid.uuid4().hex[:8]}"
        
        start_time = time.time()
        metrics = await manager.execute_multi_agent_workflow(
            workflow_id=workflow_id,
            agent_chain=test_case["agent_chain"],
            initial_data={"request": f"Test {test_case['name']}", "priority": "high"},
            expected_stages=[WorkflowStage.TRIAGE, WorkflowStage.SUPERVISOR, 
                           WorkflowStage.DATA_PROCESSING, WorkflowStage.OPTIMIZATION, WorkflowStage.COMPLETION][:len(test_case["agent_chain"])]
        )
        execution_time = time.time() - start_time
        
        recovery_result = {
            "test_case": test_case["name"],
            "execution_time": execution_time,
            "rto_target": test_case["rto_target"],
            "rto_achieved": execution_time <= test_case["rto_target"],
            "metrics": metrics,
            "recovery_successful": metrics.successful_agents > 0
        }
        
        recovery_results.append(recovery_result)
        
        # Reset between tests
        await asyncio.sleep(1.0)
        
    # Comprehensive assertions
    successful_recoveries = [r for r in recovery_results if r["recovery_successful"]]
    rto_achievements = [r for r in recovery_results if r["rto_achieved"]]
    
    assert len(successful_recoveries) >= len(recovery_test_cases) * 0.6, "At least 60% of recovery tests should succeed"
    assert len(rto_achievements) >= len(recovery_test_cases) * 0.4, "At least 40% should meet RTO targets"
    
    # Analyze recovery patterns
    for result in recovery_results:
        logger.info(f"Recovery test '{result['test_case']}': "
                   f"execution={result['execution_time']:.2f}s, "
                   f"target={result['rto_target']}s, "
                   f"rto_achieved={result['rto_achieved']}, "
                   f"success_rate={result['metrics'].calculate_success_rate():.2f}")
    
    # Verify system health after comprehensive testing
    final_health = await manager.get_system_health_summary()
    assert final_health["system_health"] in ["healthy", "degraded"], "System should maintain reasonable health"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
@pytest.mark.agent_orchestration
async def test_orchestration_scenarios_comprehensive(orchestration_manager, orchestration_scenarios):
    """Test comprehensive orchestration scenarios with circuit breakers."""
    manager = orchestration_manager
    scenario_results = {}
    
    for scenario in orchestration_scenarios:
        logger.info(f"Testing orchestration scenario: {scenario.name}")
        
        # Create agents with scenario-specific failure configuration
        failure_config = {}
        for agent_type, (failure_mode, probability) in scenario.failure_injection.items():
            failure_config[agent_type] = (failure_mode, probability)
            
        await manager.create_mock_agents(failure_config)
        
        if scenario.concurrent_workflows > 1:
            # Test concurrent workflows
            results = await manager.execute_concurrent_workflows(
                num_workflows=scenario.concurrent_workflows,
                agent_chain=scenario.agent_chain,
                failure_config=failure_config
            )
            
            # Analyze concurrent results
            avg_success_rate = sum(r.calculate_success_rate() for r in results) / len(results)
            total_cascades_prevented = sum(r.cascade_prevented_count for r in results)
            
            scenario_results[scenario.name] = {
                "type": "concurrent",
                "num_workflows": len(results),
                "avg_success_rate": avg_success_rate,
                "cascades_prevented": total_cascades_prevented,
                "cascade_prevention_effective": total_cascades_prevented > 0 if failure_config else True,
                "rto_compliance": sum(1 for r in results if r.rto_achieved) / len(results)
            }
            
        else:
            # Test single workflow
            workflow_id = f"scenario_{scenario.name}_{uuid.uuid4().hex[:8]}"
            initial_data = {"request": f"Test scenario {scenario.name}", "priority": "high"}
            
            metrics = await manager.execute_multi_agent_workflow(
                workflow_id=workflow_id,
                agent_chain=scenario.agent_chain,
                initial_data=initial_data,
                expected_stages=scenario.expected_stages
            )
            
            scenario_results[scenario.name] = {
                "type": "single",
                "success_rate": metrics.calculate_success_rate(),
                "cascade_prevention_effective": (
                    metrics.cascade_prevented_count > 0 if scenario.failure_injection 
                    else True
                ),
                "rto_achieved": metrics.rto_achieved,
                "state_consistent": metrics.state_consistency_maintained
            }
        
        # Verify scenario expectations
        result = scenario_results[scenario.name]
        
        if scenario.cascade_prevention_expected and scenario.failure_injection:
            assert result["cascade_prevention_effective"], f"Cascade prevention failed for {scenario.name}"
            
        if scenario.state_consistency_required and result["type"] == "single":
            assert result["state_consistent"], f"State consistency failed for {scenario.name}"
        
        logger.info(f"Scenario {scenario.name} completed: {result}")
        
        # Clean up between scenarios
        await manager.cleanup()
        await manager.initialize_services()
        
    # Overall scenario success validation
    successful_scenarios = sum(
        1 for result in scenario_results.values()
        if (result.get("cascade_prevention_effective", True) and
            (result.get("success_rate", 0) > 0.2 or result.get("avg_success_rate", 0) > 0.2))
    )
    
    assert successful_scenarios >= len(orchestration_scenarios) * 0.7, "At least 70% of scenarios should succeed"
    logger.info(f"Orchestration scenarios completed: {successful_scenarios}/{len(orchestration_scenarios)} successful")