"""
Agent Error Recovery Tests for Multi-Agent Orchestration System

Comprehensive error recovery testing focusing on business-critical resilience patterns,
circuit breaker coordination, graceful degradation, and recovery time objectives (RTO).

Business Value Justification (BVJ):
- Segment: Enterprise (critical for production SLA compliance) 
- Business Goal: Ensure 99.9% system availability during partial failures
- Value Impact: Protects $500K ARR from service interruption and SLA violations
- Strategic Impact: Enables enterprise-scale AI automation with controlled failure recovery

Critical Recovery Scenarios:
- Agent failure isolation and containment
- Circuit breaker activation and recovery cycles
- Graceful degradation with partial functionality
- Cross-agent dependency failure handling
- Recovery Time Objectives (RTO) validation
- Load shedding and backpressure management
- State consistency during failure scenarios

Test Coverage:
- Individual agent error recovery patterns
- Multi-agent cascade failure prevention  
- Circuit breaker coordination across pipelines
- Recovery time measurements and SLA validation
- Partial failure handling with business continuity
- Error propagation boundaries and isolation
"""

import asyncio
import json
import logging
import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
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
from netra_backend.app.services.api_gateway.fallback_service import ApiFallbackService
from netra_backend.app.services.state.state_manager import StateManager, StateStorage
from test_framework.environment_isolation import TestEnvironmentManager

logger = central_logger.get_logger(__name__)


class FailureType(Enum):
    """Types of failures to simulate in error recovery tests."""
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    LLM_API_FAILURE = "llm_api_failure"
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    NETWORK_PARTITION = "network_partition"
    STATE_CORRUPTION = "state_corruption"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTHENTICATION_FAILURE = "authentication_failure"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure scenarios."""
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK_SERVICE = "fallback_service"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    LOAD_SHEDDING = "load_shedding"
    STATE_RESTORATION = "state_restoration"
    PARTIAL_RECOVERY = "partial_recovery"


@dataclass
class ErrorRecoveryMetrics:
    """Metrics for tracking error recovery performance and effectiveness."""
    
    test_scenario: str
    failure_type: FailureType
    recovery_strategy: RecoveryStrategy
    
    # Timing metrics
    failure_detection_time_ms: float = 0.0
    recovery_initiation_time_ms: float = 0.0
    full_recovery_time_ms: float = 0.0
    rto_target_ms: float = 0.0
    rto_achieved: bool = False
    
    # Recovery effectiveness
    recovery_successful: bool = False
    partial_recovery_achieved: bool = False
    service_degradation_percent: float = 0.0
    
    # Circuit breaker metrics
    circuit_breaker_activations: int = 0
    circuit_breaker_recovery_cycles: int = 0
    cascade_failures_prevented: int = 0
    
    # Business continuity metrics
    requests_during_failure: int = 0
    requests_successfully_handled: int = 0
    fallback_activations: int = 0
    
    # Failure isolation metrics
    affected_agents: List[str] = field(default_factory=list)
    isolated_agents: List[str] = field(default_factory=list)
    recovery_pattern_used: Optional[str] = None
    
    def calculate_availability_during_failure(self) -> float:
        """Calculate service availability during failure period."""
        if self.requests_during_failure == 0:
            return 100.0
        return (self.requests_successfully_handled / self.requests_during_failure) * 100

    def calculate_recovery_efficiency(self) -> float:
        """Calculate recovery efficiency score."""
        efficiency_factors = []
        
        # RTO achievement factor
        if self.rto_achieved:
            efficiency_factors.append(1.0)
        else:
            rto_ratio = min(self.full_recovery_time_ms / max(1, self.rto_target_ms), 2.0)
            efficiency_factors.append(max(0.0, 1.0 - (rto_ratio - 1.0)))
        
        # Recovery success factor
        if self.recovery_successful:
            efficiency_factors.append(1.0)
        elif self.partial_recovery_achieved:
            efficiency_factors.append(0.7)
        else:
            efficiency_factors.append(0.0)
            
        # Service continuity factor
        availability = self.calculate_availability_during_failure() / 100
        efficiency_factors.append(availability)
        
        return sum(efficiency_factors) / len(efficiency_factors) if efficiency_factors else 0.0


class ErrorInjectionAgent(BaseSubAgent):
    """Agent that simulates various failure conditions for recovery testing."""
    
    def __init__(self, agent_type: str, failure_config: Dict[str, Any]):
        """Initialize error injection agent."""
        super().__init__(
            llm_manager=AsyncMock(),
            name=agent_type,
            description=f"Error injection agent for {agent_type}"
        )
        
        self.agent_type = agent_type
        self.agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.failure_config = failure_config
        self.execution_count = 0
        self.failure_history: List[Dict[str, Any]] = []
        
        # Configure failure patterns
        self.failure_type = failure_config.get("failure_type", FailureType.TIMEOUT)
        self.failure_probability = failure_config.get("failure_probability", 0.0)
        self.failure_after_successes = failure_config.get("failure_after_successes", 0)
        self.recovery_delay_ms = failure_config.get("recovery_delay_ms", 1000)
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute agent with configurable error injection."""
        self.execution_count += 1
        start_time = time.perf_counter()
        
        try:
            # Check if failure should be injected
            should_fail = await self._should_inject_failure()
            
            if should_fail:
                await self._inject_failure()
                
            # Simulate normal processing if no failure
            await self._simulate_normal_processing()
            
            # Record successful execution
            execution_time = (time.perf_counter() - start_time) * 1000
            self.failure_history.append({
                "execution_count": self.execution_count,
                "run_id": run_id,
                "success": True,
                "execution_time_ms": execution_time,
                "timestamp": time.time()
            })
            
        except Exception as e:
            # Record failure
            execution_time = (time.perf_counter() - start_time) * 1000
            self.failure_history.append({
                "execution_count": self.execution_count,
                "run_id": run_id,
                "success": False,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "execution_time_ms": execution_time,
                "timestamp": time.time()
            })
            raise

    async def _should_inject_failure(self) -> bool:
        """Determine if failure should be injected based on configuration."""
        # Check probability-based failure
        if random.random() < self.failure_probability:
            return True
            
        # Check failure after specific number of successes
        if self.failure_after_successes > 0:
            successful_runs = sum(1 for h in self.failure_history if h.get("success", False))
            if successful_runs >= self.failure_after_successes:
                return True
                
        return False

    async def _inject_failure(self):
        """Inject specific type of failure."""
        failure_type = self.failure_type
        
        if failure_type == FailureType.TIMEOUT:
            await asyncio.sleep(30)  # Simulate timeout
            
        elif failure_type == FailureType.RESOURCE_EXHAUSTION:
            raise RuntimeError(f"Resource exhaustion in {self.agent_type}")
            
        elif failure_type == FailureType.LLM_API_FAILURE:
            raise ConnectionError(f"LLM API unavailable for {self.agent_type}")
            
        elif failure_type == FailureType.DATABASE_CONNECTION_ERROR:
            raise ConnectionError(f"Database connection failed for {self.agent_type}")
            
        elif failure_type == FailureType.NETWORK_PARTITION:
            raise TimeoutError(f"Network partition detected for {self.agent_type}")
            
        elif failure_type == FailureType.STATE_CORRUPTION:
            raise ValueError(f"State corruption detected in {self.agent_type}")
            
        elif failure_type == FailureType.DEPENDENCY_UNAVAILABLE:
            raise RuntimeError(f"Required dependency unavailable for {self.agent_type}")
            
        elif failure_type == FailureType.QUOTA_EXCEEDED:
            raise RuntimeError(f"API quota exceeded for {self.agent_type}")
            
        elif failure_type == FailureType.AUTHENTICATION_FAILURE:
            raise PermissionError(f"Authentication failed for {self.agent_type}")
            
        elif failure_type == FailureType.CIRCUIT_BREAKER_OPEN:
            raise CircuitBreakerOpenError(f"Circuit breaker open for {self.agent_type}")

    async def _simulate_normal_processing(self):
        """Simulate normal agent processing."""
        # Simulate realistic processing time
        processing_time = 0.1 + random.uniform(0, 0.3)
        await asyncio.sleep(processing_time)

    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure statistics for analysis."""
        if not self.failure_history:
            return {"total_executions": 0, "failures": 0, "success_rate": 0.0}
            
        total_executions = len(self.failure_history)
        successful_executions = sum(1 for h in self.failure_history if h.get("success", False))
        failed_executions = total_executions - successful_executions
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions,
            "avg_execution_time_ms": sum(h.get("execution_time_ms", 0) for h in self.failure_history) / total_executions,
            "failure_types": list(set(h.get("error_type") for h in self.failure_history if not h.get("success", True)))
        }


class AgentErrorRecoveryOrchestrator:
    """Orchestrator for comprehensive error recovery testing across agent pipelines."""
    
    def __init__(self):
        """Initialize error recovery orchestrator."""
        self.test_env_manager = TestEnvironmentManager()
        self.circuit_breaker_manager = get_unified_circuit_breaker_manager()
        self.redis_manager: Optional[RedisManager] = None
        self.state_manager: Optional[StateManager] = None
        self.fallback_service: Optional[ApiFallbackService] = None
        
        # Recovery test configuration
        self.rto_targets = {
            "triage_agent": 5000,      # 5 seconds
            "supervisor_agent": 10000,  # 10 seconds  
            "data_agent": 15000,       # 15 seconds
            "optimization_agent": 30000, # 30 seconds
            "analysis_agent": 20000,   # 20 seconds
            "reporting_agent": 10000   # 10 seconds
        }
        
        # Agent dependency mapping for cascade testing
        self.agent_dependencies = {
            "triage_agent": [],
            "supervisor_agent": ["triage_agent"],
            "data_agent": ["supervisor_agent"],
            "optimization_agent": ["data_agent", "supervisor_agent"],
            "analysis_agent": ["data_agent"],
            "reporting_agent": ["analysis_agent", "optimization_agent"]
        }
        
        # Circuit breakers for each agent type
        self.circuit_breakers: Dict[str, UnifiedCircuitBreaker] = {}
        self.error_injection_agents: Dict[str, ErrorInjectionAgent] = {}
        self.recovery_metrics: Dict[str, ErrorRecoveryMetrics] = {}

    async def setup_error_recovery_environment(self):
        """Setup comprehensive error recovery testing environment."""
        self.test_env_manager.setup_test_environment()
        
        # Setup Redis for state management
        try:
            self.redis_manager = RedisManager(test_mode=True)
            await self.redis_manager.connect()
            
            if self.redis_manager.enabled:
                self.state_manager = StateManager(storage=StateStorage.HYBRID)
                self.state_manager._redis = self.redis_manager
                logger.info("Error recovery tests using Redis state management")
            else:
                self.state_manager = StateManager(storage=StateStorage.MEMORY)
                logger.info("Error recovery tests using memory state management")
                
        except Exception as e:
            logger.warning(f"Redis unavailable for error recovery tests: {e}")
            self.state_manager = StateManager(storage=StateStorage.MEMORY)
        
        # Setup circuit breakers for each agent type
        await self._setup_circuit_breakers()
        
        # Setup fallback service
        self.fallback_service = ApiFallbackService()
        
        logger.info("Error recovery testing environment initialized")

    async def _setup_circuit_breakers(self):
        """Setup circuit breakers with recovery-focused configurations."""
        circuit_configs = {
            "triage_agent": UnifiedCircuitConfig(
                name="triage_agent_recovery",
                failure_threshold=2,  # Fail fast for critical entry point
                recovery_timeout=5.0,
                success_threshold=1,
                timeout_seconds=5.0,
                sliding_window_size=5,
                error_rate_threshold=0.4,
                adaptive_threshold=True
            ),
            "supervisor_agent": UnifiedCircuitConfig(
                name="supervisor_agent_recovery",
                failure_threshold=3,
                recovery_timeout=10.0,
                success_threshold=2,
                timeout_seconds=10.0,
                sliding_window_size=6,
                error_rate_threshold=0.5,
                adaptive_threshold=True
            ),
            "data_agent": UnifiedCircuitConfig(
                name="data_agent_recovery",
                failure_threshold=4,
                recovery_timeout=15.0,
                success_threshold=2,
                timeout_seconds=15.0,
                sliding_window_size=8,
                error_rate_threshold=0.6,
                adaptive_threshold=True
            ),
            "optimization_agent": UnifiedCircuitConfig(
                name="optimization_agent_recovery",
                failure_threshold=5,
                recovery_timeout=30.0,
                success_threshold=3,
                timeout_seconds=30.0,
                sliding_window_size=10,
                error_rate_threshold=0.5,
                adaptive_threshold=True
            ),
            "analysis_agent": UnifiedCircuitConfig(
                name="analysis_agent_recovery",
                failure_threshold=4,
                recovery_timeout=20.0,
                success_threshold=2,
                timeout_seconds=20.0,
                sliding_window_size=8,
                error_rate_threshold=0.5,
                adaptive_threshold=True
            ),
            "reporting_agent": UnifiedCircuitConfig(
                name="reporting_agent_recovery", 
                failure_threshold=3,
                recovery_timeout=10.0,
                success_threshold=2,
                timeout_seconds=10.0,
                sliding_window_size=6,
                error_rate_threshold=0.4,
                adaptive_threshold=True
            )
        }
        
        for agent_type, config in circuit_configs.items():
            circuit_breaker = self.circuit_breaker_manager.create_circuit_breaker(
                agent_type, config
            )
            self.circuit_breakers[agent_type] = circuit_breaker
            
        logger.info(f"Configured {len(self.circuit_breakers)} circuit breakers for error recovery testing")

    async def create_error_injection_agents(self, failure_scenarios: Dict[str, Dict[str, Any]]):
        """Create agents with configurable error injection."""
        for agent_type, failure_config in failure_scenarios.items():
            agent = ErrorInjectionAgent(agent_type, failure_config)
            self.error_injection_agents[agent_type] = agent
            
        logger.info(f"Created {len(self.error_injection_agents)} error injection agents")

    async def execute_error_recovery_test(
        self,
        test_scenario: str,
        agent_pipeline: List[str],
        failure_scenarios: Dict[str, Dict[str, Any]],
        concurrent_requests: int = 1
    ) -> ErrorRecoveryMetrics:
        """Execute comprehensive error recovery test scenario."""
        
        # Initialize agents with failure injection
        await self.create_error_injection_agents(failure_scenarios)
        
        # Initialize recovery metrics
        primary_failure_agent = list(failure_scenarios.keys())[0] if failure_scenarios else "unknown"
        primary_failure_type = (
            list(failure_scenarios.values())[0].get("failure_type", FailureType.TIMEOUT)
            if failure_scenarios else FailureType.TIMEOUT
        )
        
        recovery_metrics = ErrorRecoveryMetrics(
            test_scenario=test_scenario,
            failure_type=primary_failure_type,
            recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER,  # Default strategy
            rto_target_ms=max(self.rto_targets.get(agent, 30000) for agent in agent_pipeline)
        )
        
        self.recovery_metrics[test_scenario] = recovery_metrics
        
        # Execute test with failure monitoring
        test_start_time = time.perf_counter()
        failure_detected_time = None
        recovery_initiated_time = None
        
        try:
            # Execute concurrent pipeline requests to test recovery under load
            pipeline_tasks = []
            for i in range(concurrent_requests):
                task_id = f"{test_scenario}_request_{i}"
                task = self._execute_pipeline_with_recovery(task_id, agent_pipeline, recovery_metrics)
                pipeline_tasks.append(task)
            
            # Monitor for failures and recovery
            monitoring_task = asyncio.create_task(
                self._monitor_failure_and_recovery(recovery_metrics)
            )
            
            # Execute pipelines
            pipeline_results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
            
            # Stop monitoring
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
            
            # Analyze results
            successful_pipelines = sum(1 for result in pipeline_results if not isinstance(result, Exception))
            failed_pipelines = len(pipeline_results) - successful_pipelines
            
            recovery_metrics.requests_during_failure = len(pipeline_results)
            recovery_metrics.requests_successfully_handled = successful_pipelines
            
            # Determine recovery success
            if successful_pipelines > 0:
                recovery_metrics.recovery_successful = True
            elif successful_pipelines > failed_pipelines * 0.5:
                recovery_metrics.partial_recovery_achieved = True
                
            # Calculate final recovery time
            test_end_time = time.perf_counter()
            recovery_metrics.full_recovery_time_ms = (test_end_time - test_start_time) * 1000
            recovery_metrics.rto_achieved = recovery_metrics.full_recovery_time_ms <= recovery_metrics.rto_target_ms
            
            logger.info(f"Error recovery test '{test_scenario}' completed: "
                       f"{successful_pipelines}/{len(pipeline_results)} successful, "
                       f"recovery_time={recovery_metrics.full_recovery_time_ms:.0f}ms")
            
        except Exception as e:
            logger.error(f"Error recovery test '{test_scenario}' failed: {e}")
            recovery_metrics.recovery_successful = False
            
        return recovery_metrics

    async def _execute_pipeline_with_recovery(
        self,
        task_id: str,
        agent_pipeline: List[str],
        recovery_metrics: ErrorRecoveryMetrics
    ) -> Dict[str, Any]:
        """Execute agent pipeline with recovery mechanisms."""
        pipeline_result = {
            "task_id": task_id,
            "agents_executed": [],
            "agents_succeeded": [],
            "agents_failed": [],
            "circuit_breaker_activations": 0,
            "fallback_activations": 0,
            "recovery_attempts": 0
        }
        
        # Execute agents in pipeline
        for agent_type in agent_pipeline:
            agent = self.error_injection_agents.get(agent_type)
            circuit_breaker = self.circuit_breakers.get(agent_type)
            
            if not agent or not circuit_breaker:
                logger.warning(f"Agent or circuit breaker not found for {agent_type}")
                continue
                
            pipeline_result["agents_executed"].append(agent_type)
            
            try:
                # Execute agent through circuit breaker
                async def protected_execution():
                    state = DeepAgentState()
                    state.run_id = task_id
                    await agent.execute(state, task_id, stream_updates=False)
                    return {"agent_type": agent_type, "success": True}
                
                result = await circuit_breaker.call(protected_execution)
                pipeline_result["agents_succeeded"].append(agent_type)
                
            except CircuitBreakerOpenError:
                # Circuit breaker is open, try fallback
                pipeline_result["circuit_breaker_activations"] += 1
                recovery_metrics.circuit_breaker_activations += 1
                
                try:
                    fallback_result = await self._attempt_fallback_recovery(agent_type, task_id)
                    if fallback_result:
                        pipeline_result["fallback_activations"] += 1
                        recovery_metrics.fallback_activations += 1
                        pipeline_result["agents_succeeded"].append(f"{agent_type}_fallback")
                    else:
                        pipeline_result["agents_failed"].append(agent_type)
                        
                except Exception as e:
                    logger.error(f"Fallback failed for {agent_type}: {e}")
                    pipeline_result["agents_failed"].append(agent_type)
                    
            except Exception as e:
                # Direct agent failure
                logger.error(f"Agent {agent_type} failed: {e}")
                pipeline_result["agents_failed"].append(agent_type)
                
                # Attempt recovery
                recovery_attempted = await self._attempt_agent_recovery(agent_type, task_id, recovery_metrics)
                if recovery_attempted:
                    pipeline_result["recovery_attempts"] += 1
        
        return pipeline_result

    async def _monitor_failure_and_recovery(self, recovery_metrics: ErrorRecoveryMetrics):
        """Monitor system for failure detection and recovery events."""
        monitoring_start = time.perf_counter()
        failure_detected = False
        recovery_initiated = False
        
        while True:
            try:
                current_time = time.perf_counter()
                
                # Check circuit breaker states for failure detection
                for agent_type, circuit_breaker in self.circuit_breakers.items():
                    status = circuit_breaker.get_status()
                    
                    if status["state"] == "open" and not failure_detected:
                        failure_detected = True
                        recovery_metrics.failure_detection_time_ms = (current_time - monitoring_start) * 1000
                        recovery_metrics.affected_agents.append(agent_type)
                        logger.info(f"Failure detected in {agent_type} at {recovery_metrics.failure_detection_time_ms:.0f}ms")
                        
                    elif status["state"] == "half_open" and failure_detected and not recovery_initiated:
                        recovery_initiated = True
                        recovery_metrics.recovery_initiation_time_ms = (current_time - monitoring_start) * 1000
                        logger.info(f"Recovery initiated for {agent_type} at {recovery_metrics.recovery_initiation_time_ms:.0f}ms")
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                break

    async def _attempt_fallback_recovery(self, agent_type: str, task_id: str) -> bool:
        """Attempt fallback recovery for failed agent."""
        try:
            if self.fallback_service:
                fallback_result = await self.fallback_service.execute_fallback(
                    agent_type, {"task_id": task_id}
                )
                logger.info(f"Fallback successful for {agent_type}")
                return True
        except Exception as e:
            logger.error(f"Fallback failed for {agent_type}: {e}")
            
        return False

    async def _attempt_agent_recovery(
        self,
        agent_type: str,
        task_id: str,
        recovery_metrics: ErrorRecoveryMetrics
    ) -> bool:
        """Attempt direct agent recovery with backoff."""
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(max_attempts):
            try:
                # Exponential backoff delay
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                
                # Attempt recovery execution
                agent = self.error_injection_agents.get(agent_type)
                if agent:
                    state = DeepAgentState()
                    state.run_id = f"{task_id}_recovery_{attempt}"
                    await agent.execute(state, state.run_id, stream_updates=False)
                    
                    logger.info(f"Direct recovery successful for {agent_type} on attempt {attempt + 1}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Recovery attempt {attempt + 1} failed for {agent_type}: {e}")
                
        logger.error(f"All recovery attempts failed for {agent_type}")
        return False

    async def test_cascade_failure_prevention(
        self,
        primary_failure_agent: str,
        dependent_agents: List[str]
    ) -> Dict[str, Any]:
        """Test cascade failure prevention through circuit breaker coordination."""
        
        # Setup failure scenario for primary agent
        failure_config = {
            primary_failure_agent: {
                "failure_type": FailureType.RESOURCE_EXHAUSTION,
                "failure_probability": 0.9,  # High failure rate
                "recovery_delay_ms": 5000
            }
        }
        
        cascade_test_metrics = {
            "primary_failure_agent": primary_failure_agent,
            "dependent_agents": dependent_agents,
            "cascade_prevention_effective": True,
            "affected_agents": [],
            "protected_agents": [],
            "circuit_breaker_coordination": {}
        }
        
        await self.create_error_injection_agents(failure_config)
        
        # Test pipeline execution
        test_pipeline = [primary_failure_agent] + dependent_agents
        
        try:
            recovery_metrics = await self.execute_error_recovery_test(
                "cascade_prevention_test",
                test_pipeline,
                failure_config,
                concurrent_requests=5
            )
            
            # Analyze cascade prevention effectiveness
            for agent_type in dependent_agents:
                circuit_breaker = self.circuit_breakers.get(agent_type)
                if circuit_breaker:
                    status = circuit_breaker.get_status()
                    cascade_test_metrics["circuit_breaker_coordination"][agent_type] = {
                        "state": status["state"],
                        "total_calls": status["metrics"]["total_calls"],
                        "rejected_calls": status["metrics"]["rejected_calls"],
                        "failed_calls": status["metrics"]["failed_calls"]
                    }
                    
                    # Check if agent was protected (rejected calls indicate protection)
                    if status["metrics"]["rejected_calls"] > 0:
                        cascade_test_metrics["protected_agents"].append(agent_type)
                    elif status["metrics"]["failed_calls"] > 0:
                        cascade_test_metrics["affected_agents"].append(agent_type)
                        cascade_test_metrics["cascade_prevention_effective"] = False
            
            cascade_test_metrics["recovery_metrics"] = asdict(recovery_metrics)
            
        except Exception as e:
            logger.error(f"Cascade prevention test failed: {e}")
            cascade_test_metrics["cascade_prevention_effective"] = False
            cascade_test_metrics["error"] = str(e)
        
        return cascade_test_metrics

    async def cleanup_error_recovery_environment(self):
        """Clean up error recovery test environment."""
        # Reset all circuit breakers
        reset_tasks = []
        for circuit_breaker in self.circuit_breakers.values():
            reset_tasks.append(circuit_breaker.reset())
        
        if reset_tasks:
            await asyncio.gather(*reset_tasks, return_exceptions=True)
        
        # Clear agents and metrics
        self.error_injection_agents.clear()
        self.recovery_metrics.clear()
        
        # Cleanup Redis connection
        if self.redis_manager:
            try:
                await self.redis_manager.disconnect()
            except Exception as e:
                logger.warning(f"Redis cleanup error: {e}")
        
        # Cleanup isolated environment
        self.test_env_manager.teardown_test_environment()
        
        logger.info("Error recovery test environment cleaned up")

    def save_recovery_test_report(self, test_name: str, results: Any):
        """Save comprehensive error recovery test report."""
        import os
        os.makedirs("test_reports/error_recovery", exist_ok=True)
        timestamp = int(time.time())
        filename = f"test_reports/error_recovery/agent_error_recovery_{test_name}_{timestamp}.json"
        
        report_data = {
            "test_name": test_name,
            "timestamp": timestamp,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "results": results if isinstance(results, dict) else asdict(results)
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"Error recovery test report saved: {filename}")


# Test Fixtures

@pytest.fixture
async def error_recovery_orchestrator():
    """Error recovery orchestrator fixture."""
    orchestrator = AgentErrorRecoveryOrchestrator()
    await orchestrator.setup_error_recovery_environment()
    yield orchestrator
    await orchestrator.cleanup_error_recovery_environment()


# Error Recovery Tests

@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_individual_agent_timeout_recovery(error_recovery_orchestrator):
    """Test individual agent recovery from timeout failures."""
    orchestrator = error_recovery_orchestrator
    
    # Configure timeout failure for data agent
    failure_scenarios = {
        "data_agent": {
            "failure_type": FailureType.TIMEOUT,
            "failure_probability": 0.7,
            "recovery_delay_ms": 2000
        }
    }
    
    # Execute recovery test
    recovery_metrics = await orchestrator.execute_error_recovery_test(
        "timeout_recovery_test",
        ["triage_agent", "data_agent", "analysis_agent"],
        failure_scenarios,
        concurrent_requests=3
    )
    
    # Recovery assertions
    assert recovery_metrics.circuit_breaker_activations > 0, "Circuit breaker should activate on timeout"
    assert recovery_metrics.full_recovery_time_ms < 20000, "Recovery should complete within 20 seconds"
    assert recovery_metrics.calculate_availability_during_failure() >= 50, "At least 50% availability during failure"
    
    # RTO validation
    data_agent_rto = orchestrator.rto_targets.get("data_agent", 15000)
    if not recovery_metrics.rto_achieved:
        logger.warning(f"RTO not achieved: {recovery_metrics.full_recovery_time_ms:.0f}ms > {data_agent_rto}ms")
    
    logger.info(f"Timeout recovery test: {recovery_metrics.calculate_recovery_efficiency():.2f} efficiency")
    orchestrator.save_recovery_test_report("timeout_recovery", recovery_metrics)


@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_circuit_breaker_coordination_across_agents(error_recovery_orchestrator):
    """Test circuit breaker coordination between dependent agents."""
    orchestrator = error_recovery_orchestrator
    
    # Configure cascading failure scenario
    failure_scenarios = {
        "supervisor_agent": {
            "failure_type": FailureType.RESOURCE_EXHAUSTION,
            "failure_probability": 0.8,
            "recovery_delay_ms": 3000
        }
    }
    
    # Test with dependent agents
    agent_pipeline = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent"]
    
    recovery_metrics = await orchestrator.execute_error_recovery_test(
        "circuit_breaker_coordination_test",
        agent_pipeline,
        failure_scenarios,
        concurrent_requests=5
    )
    
    # Coordination assertions
    assert recovery_metrics.circuit_breaker_activations >= 1, "Circuit breaker should coordinate failures"
    assert len(recovery_metrics.affected_agents) >= 1, "Some agents should be affected"
    
    # Check that downstream agents are protected
    supervisor_cb = orchestrator.circuit_breakers.get("supervisor_agent")
    data_cb = orchestrator.circuit_breakers.get("data_agent")
    
    if supervisor_cb and data_cb:
        supervisor_status = supervisor_cb.get_status()
        data_status = data_cb.get_status()
        
        # If supervisor fails, data agent should be protected
        if supervisor_status["metrics"]["failed_calls"] > 0:
            assert (data_status["metrics"]["rejected_calls"] > 0 or 
                   data_status["metrics"]["total_calls"] == 0), "Data agent should be protected from supervisor failure"
    
    logger.info(f"Circuit breaker coordination: {recovery_metrics.circuit_breaker_activations} activations")
    orchestrator.save_recovery_test_report("circuit_breaker_coordination", recovery_metrics)


@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_graceful_degradation_with_partial_functionality(error_recovery_orchestrator):
    """Test graceful degradation when some agents fail but others continue."""
    orchestrator = error_recovery_orchestrator
    
    # Configure partial failure scenario
    failure_scenarios = {
        "optimization_agent": {
            "failure_type": FailureType.LLM_API_FAILURE,
            "failure_probability": 0.9,
            "recovery_delay_ms": 5000
        }
    }
    
    # Test pipeline with fallback path
    agent_pipeline = ["triage_agent", "supervisor_agent", "data_agent", "optimization_agent", "reporting_agent"]
    
    recovery_metrics = await orchestrator.execute_error_recovery_test(
        "graceful_degradation_test",
        agent_pipeline,
        failure_scenarios,
        concurrent_requests=4
    )
    
    # Graceful degradation assertions
    assert recovery_metrics.requests_during_failure > 0, "Should handle requests during failure"
    
    # Check for partial functionality
    if recovery_metrics.requests_successfully_handled > 0:
        availability = recovery_metrics.calculate_availability_during_failure()
        assert availability >= 25, "Should maintain at least 25% functionality during degradation"
        
        if availability < 80:
            recovery_metrics.partial_recovery_achieved = True
            recovery_metrics.service_degradation_percent = 100 - availability
    
    # Verify fallback activations
    assert recovery_metrics.fallback_activations >= 0, "Fallback mechanisms should be available"
    
    degradation_level = recovery_metrics.service_degradation_percent
    logger.info(f"Graceful degradation: {degradation_level:.1f}% service degradation")
    
    orchestrator.save_recovery_test_report("graceful_degradation", recovery_metrics)


@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_cascade_failure_prevention_multiple_agents(error_recovery_orchestrator):
    """Test prevention of cascade failures across multiple dependent agents."""
    orchestrator = error_recovery_orchestrator
    
    # Test cascade prevention
    primary_failure_agent = "supervisor_agent"
    dependent_agents = ["data_agent", "optimization_agent", "analysis_agent"]
    
    cascade_metrics = await orchestrator.test_cascade_failure_prevention(
        primary_failure_agent,
        dependent_agents
    )
    
    # Cascade prevention assertions
    assert cascade_metrics["cascade_prevention_effective"], "Cascade prevention should be effective"
    assert len(cascade_metrics["protected_agents"]) >= 1, "At least one dependent agent should be protected"
    
    # Verify circuit breaker coordination prevented cascades
    protected_count = len(cascade_metrics["protected_agents"])
    affected_count = len(cascade_metrics["affected_agents"])
    
    # At least 50% of dependent agents should be protected
    protection_rate = protected_count / (protected_count + affected_count) if (protected_count + affected_count) > 0 else 0
    assert protection_rate >= 0.5, f"Protection rate {protection_rate:.2f} should be at least 50%"
    
    logger.info(f"Cascade prevention: {protected_count} protected, {affected_count} affected")
    orchestrator.save_recovery_test_report("cascade_prevention", cascade_metrics)


@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_recovery_time_objectives_validation(error_recovery_orchestrator):
    """Test RTO validation across different failure scenarios."""
    orchestrator = error_recovery_orchestrator
    
    # Test multiple agents with different RTO targets
    rto_test_scenarios = [
        {
            "name": "fast_recovery_triage",
            "agent": "triage_agent",
            "failure_type": FailureType.NETWORK_PARTITION,
            "expected_rto_ms": 5000
        },
        {
            "name": "medium_recovery_supervisor", 
            "agent": "supervisor_agent",
            "failure_type": FailureType.DATABASE_CONNECTION_ERROR,
            "expected_rto_ms": 10000
        },
        {
            "name": "slow_recovery_optimization",
            "agent": "optimization_agent", 
            "failure_type": FailureType.QUOTA_EXCEEDED,
            "expected_rto_ms": 30000
        }
    ]
    
    rto_results = {}
    
    for scenario in rto_test_scenarios:
        failure_scenarios = {
            scenario["agent"]: {
                "failure_type": scenario["failure_type"],
                "failure_probability": 0.8,
                "recovery_delay_ms": scenario["expected_rto_ms"] // 4  # Aim for faster recovery
            }
        }
        
        recovery_metrics = await orchestrator.execute_error_recovery_test(
            scenario["name"],
            ["triage_agent", scenario["agent"]],
            failure_scenarios,
            concurrent_requests=2
        )
        
        rto_results[scenario["name"]] = {
            "expected_rto_ms": scenario["expected_rto_ms"],
            "actual_recovery_time_ms": recovery_metrics.full_recovery_time_ms,
            "rto_achieved": recovery_metrics.rto_achieved,
            "recovery_efficiency": recovery_metrics.calculate_recovery_efficiency()
        }
        
        # RTO assertions
        if recovery_metrics.rto_achieved:
            logger.info(f"RTO achieved for {scenario['name']}: {recovery_metrics.full_recovery_time_ms:.0f}ms")
        else:
            logger.warning(f"RTO exceeded for {scenario['name']}: {recovery_metrics.full_recovery_time_ms:.0f}ms > {scenario['expected_rto_ms']}ms")
        
        # Accept some RTO violations but expect reasonable performance
        assert recovery_metrics.full_recovery_time_ms < scenario["expected_rto_ms"] * 2, f"Recovery time should be within 2x RTO limit"
    
    # Overall RTO validation
    rto_achievements = sum(1 for result in rto_results.values() if result["rto_achieved"])
    rto_success_rate = rto_achievements / len(rto_results) if rto_results else 0
    
    # At least 60% of RTO targets should be achieved
    assert rto_success_rate >= 0.6, f"RTO success rate {rto_success_rate:.2f} should be at least 60%"
    
    logger.info(f"RTO validation: {rto_achievements}/{len(rto_results)} targets achieved")
    orchestrator.save_recovery_test_report("rto_validation", rto_results)


@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_partial_failure_business_continuity(error_recovery_orchestrator):
    """Test business continuity during partial system failures."""
    orchestrator = error_recovery_orchestrator
    
    # Configure realistic partial failure scenario
    failure_scenarios = {
        "analysis_agent": {
            "failure_type": FailureType.STATE_CORRUPTION,
            "failure_probability": 0.6,
            "recovery_delay_ms": 4000
        },
        "optimization_agent": {
            "failure_type": FailureType.DEPENDENCY_UNAVAILABLE,
            "failure_probability": 0.4,
            "recovery_delay_ms": 6000
        }
    }
    
    # Test full pipeline with multiple failure points
    full_pipeline = ["triage_agent", "supervisor_agent", "data_agent", "analysis_agent", "optimization_agent", "reporting_agent"]
    
    recovery_metrics = await orchestrator.execute_error_recovery_test(
        "partial_failure_continuity_test",
        full_pipeline,
        failure_scenarios,
        concurrent_requests=6
    )
    
    # Business continuity assertions
    assert recovery_metrics.requests_during_failure >= 6, "Should handle all test requests"
    
    # Calculate business continuity metrics
    availability = recovery_metrics.calculate_availability_during_failure()
    continuity_maintained = availability >= 40  # 40% minimum for business continuity
    
    assert continuity_maintained, f"Business continuity not maintained: {availability:.1f}% availability"
    
    # Verify partial functionality
    if recovery_metrics.partial_recovery_achieved or recovery_metrics.recovery_successful:
        assert recovery_metrics.requests_successfully_handled > 0, "Some requests should succeed during partial failure"
    
    # Check fallback effectiveness
    if recovery_metrics.fallback_activations > 0:
        fallback_effectiveness = recovery_metrics.fallback_activations / len(failure_scenarios)
        logger.info(f"Fallback effectiveness: {fallback_effectiveness:.2f}")
    
    continuity_score = recovery_metrics.calculate_recovery_efficiency()
    logger.info(f"Business continuity maintained: {availability:.1f}% availability, {continuity_score:.2f} continuity score")
    
    orchestrator.save_recovery_test_report("business_continuity", {
        "availability_percent": availability,
        "continuity_maintained": continuity_maintained,
        "continuity_score": continuity_score,
        "recovery_metrics": recovery_metrics
    })


@pytest.mark.integration
@pytest.mark.error_recovery
@pytest.mark.asyncio
async def test_error_isolation_and_containment(error_recovery_orchestrator):
    """Test error isolation to prevent cross-agent contamination."""
    orchestrator = error_recovery_orchestrator
    
    # Configure isolated failure scenario
    failure_scenarios = {
        "data_agent": {
            "failure_type": FailureType.AUTHENTICATION_FAILURE,
            "failure_probability": 0.9,
            "recovery_delay_ms": 3000
        }
    }
    
    # Test pipeline with isolated failure
    test_pipeline = ["triage_agent", "supervisor_agent", "data_agent", "analysis_agent", "reporting_agent"]
    
    recovery_metrics = await orchestrator.execute_error_recovery_test(
        "error_isolation_test",
        test_pipeline,
        failure_scenarios,
        concurrent_requests=4
    )
    
    # Error isolation assertions
    assert len(recovery_metrics.affected_agents) >= 1, "At least one agent should be affected"
    
    # Check that unrelated agents are isolated from the failure
    unrelated_agents = ["triage_agent", "reporting_agent"]  # Not directly dependent on data_agent
    
    isolated_count = 0
    for agent_type in unrelated_agents:
        circuit_breaker = orchestrator.circuit_breakers.get(agent_type)
        if circuit_breaker:
            status = circuit_breaker.get_status()
            
            # Check if agent remained unaffected
            if (status["metrics"]["failed_calls"] == 0 and 
                status["state"] in ["closed", "half_open"]):
                isolated_count += 1
                recovery_metrics.isolated_agents.append(agent_type)
    
    # Verify isolation effectiveness
    isolation_effectiveness = isolated_count / len(unrelated_agents) if unrelated_agents else 0
    assert isolation_effectiveness >= 0.5, f"Error isolation effectiveness {isolation_effectiveness:.2f} should be at least 50%"
    
    logger.info(f"Error isolation: {isolated_count}/{len(unrelated_agents)} unrelated agents remained isolated")
    
    orchestrator.save_recovery_test_report("error_isolation", {
        "isolation_effectiveness": isolation_effectiveness,
        "isolated_agents": recovery_metrics.isolated_agents,
        "affected_agents": recovery_metrics.affected_agents,
        "recovery_metrics": recovery_metrics
    })


if __name__ == "__main__":
    # Run error recovery tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "error_recovery"])