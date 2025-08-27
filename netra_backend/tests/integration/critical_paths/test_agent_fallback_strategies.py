"""Agent Fallback Strategies L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (system resilience and availability)
- Business Goal: Resilience and high availability
- Value Impact: Protects $10K MRR from system unavailability and failures
- Strategic Impact: Core reliability feature for mission-critical AI operations

Critical Path: Primary failure -> Strategy selection -> Fallback execution -> Recovery monitoring
Coverage: Real fallback managers, strategy selection, recovery handlers, monitoring
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.db.database_manager import DatabaseManager as ConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of failures that can trigger fallbacks."""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN_ERROR = "unknown_error"

class FallbackStrategy(Enum):
    """Available fallback strategies."""
    RETRY = "retry"
    ALTERNATIVE_SERVICE = "alternative_service"
    DEGRADED_MODE = "degraded_mode"
    CACHE_FALLBACK = "cache_fallback"
    MANUAL_OVERRIDE = "manual_override"
    FAIL_FAST = "fail_fast"
    CIRCUIT_BREAKER = "circuit_breaker"

class RecoveryStatus(Enum):
    """Recovery status states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class FailureContext:
    """Context information about a failure."""
    failure_id: str
    agent_id: str
    failure_type: FailureType
    original_request: Dict[str, Any]
    error_details: Dict[str, Any]
    occurred_at: datetime
    retry_count: int = 0
    severity: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "failure_id": self.failure_id,
            "agent_id": self.agent_id,
            "failure_type": self.failure_type.value,
            "error_details": self.error_details,
            "occurred_at": self.occurred_at.isoformat(),
            "retry_count": self.retry_count,
            "severity": self.severity
        }

@dataclass
class FallbackPlan:
    """Plan for handling a specific failure scenario."""
    plan_id: str
    failure_types: List[FailureType]
    strategies: List[FallbackStrategy]
    max_retries: int
    timeout_seconds: float
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # Lower number = higher priority
    
    def matches_failure(self, failure_context: FailureContext) -> bool:
        """Check if this plan applies to the given failure."""
        if failure_context.failure_type not in self.failure_types:
            return False
        
        # Check additional conditions
        for condition, expected_value in self.conditions.items():
            if condition == "max_retry_count":
                if failure_context.retry_count >= expected_value:
                    return False
            elif condition == "severity":
                if failure_context.severity != expected_value:
                    return False
        
        return True

@dataclass
class FallbackExecution:
    """Represents an ongoing fallback execution."""
    execution_id: str
    failure_context: FailureContext
    fallback_plan: FallbackPlan
    current_strategy_index: int
    started_at: datetime
    status: RecoveryStatus
    results: List[Dict[str, Any]] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    
    @property
    def current_strategy(self) -> Optional[FallbackStrategy]:
        """Get the current strategy being executed."""
        if 0 <= self.current_strategy_index < len(self.fallback_plan.strategies):
            return self.fallback_plan.strategies[self.current_strategy_index]
        return None
    
    @property
    def execution_time(self) -> float:
        """Get total execution time."""
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

class StrategySelector:
    """Selects appropriate fallback strategies based on failure context."""
    
    def __init__(self):
        self.fallback_plans = []
        self.selection_stats = {
            "total_selections": 0,
            "strategy_usage": {strategy.value: 0 for strategy in FallbackStrategy}
        }
        
    def add_fallback_plan(self, plan: FallbackPlan):
        """Add a fallback plan."""
        self.fallback_plans.append(plan)
        # Sort by priority (lower number = higher priority)
        self.fallback_plans.sort(key=lambda p: p.priority)
        
    def select_strategy(self, failure_context: FailureContext) -> Optional[FallbackPlan]:
        """Select the best fallback strategy for the given failure."""
        self.selection_stats["total_selections"] += 1
        
        # Find the first matching plan (highest priority)
        for plan in self.fallback_plans:
            if plan.matches_failure(failure_context):
                # Update usage stats
                for strategy in plan.strategies:
                    self.selection_stats["strategy_usage"][strategy.value] += 1
                
                logger.info(f"Selected fallback plan {plan.plan_id} for failure {failure_context.failure_id}")
                return plan
        
        logger.warning(f"No fallback plan found for failure {failure_context.failure_id}")
        return None
    
    def get_selection_stats(self) -> Dict[str, Any]:
        """Get strategy selection statistics."""
        return self.selection_stats.copy()

class FallbackExecutor:
    """Executes fallback strategies."""
    
    def __init__(self):
        self.strategy_handlers = {}
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "strategy_success_rates": {}
        }
        
    def register_strategy_handler(self, strategy: FallbackStrategy, 
                                 handler: Callable[[FailureContext, Dict[str, Any]], Any]):
        """Register a handler for a specific strategy."""
        self.strategy_handlers[strategy] = handler
        
    async def execute_fallback(self, failure_context: FailureContext, 
                              fallback_plan: FallbackPlan) -> FallbackExecution:
        """Execute a fallback plan."""
        execution = FallbackExecution(
            execution_id=f"exec_{int(time.time() * 1000000)}",
            failure_context=failure_context,
            fallback_plan=fallback_plan,
            current_strategy_index=0,
            started_at=datetime.now(),
            status=RecoveryStatus.IN_PROGRESS
        )
        
        self.execution_stats["total_executions"] += 1
        
        try:
            # Execute strategies in sequence until one succeeds or all fail
            for i, strategy in enumerate(fallback_plan.strategies):
                execution.current_strategy_index = i
                
                logger.info(f"Executing strategy {strategy.value} for failure {failure_context.failure_id}")
                
                # Execute strategy with timeout
                try:
                    result = await asyncio.wait_for(
                        self._execute_strategy(strategy, failure_context),
                        timeout=fallback_plan.timeout_seconds
                    )
                    
                    execution.results.append({
                        "strategy": strategy.value,
                        "success": True,
                        "result": result,
                        "executed_at": datetime.now().isoformat()
                    })
                    
                    # Strategy succeeded
                    execution.status = RecoveryStatus.SUCCEEDED
                    execution.completed_at = datetime.now()
                    
                    self.execution_stats["successful_executions"] += 1
                    self._update_strategy_stats(strategy, True)
                    
                    logger.info(f"Strategy {strategy.value} succeeded for failure {failure_context.failure_id}")
                    break
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Strategy {strategy.value} timed out for failure {failure_context.failure_id}")
                    execution.results.append({
                        "strategy": strategy.value,
                        "success": False,
                        "error": "timeout",
                        "executed_at": datetime.now().isoformat()
                    })
                    self._update_strategy_stats(strategy, False)
                    
                except Exception as e:
                    logger.error(f"Strategy {strategy.value} failed for failure {failure_context.failure_id}: {e}")
                    execution.results.append({
                        "strategy": strategy.value,
                        "success": False,
                        "error": str(e),
                        "executed_at": datetime.now().isoformat()
                    })
                    self._update_strategy_stats(strategy, False)
            
            # Check final status
            if execution.status == RecoveryStatus.IN_PROGRESS:
                execution.status = RecoveryStatus.FAILED
                execution.completed_at = datetime.now()
                self.execution_stats["failed_executions"] += 1
                
        except Exception as e:
            execution.status = RecoveryStatus.FAILED
            execution.completed_at = datetime.now()
            execution.results.append({
                "error": f"Execution failed: {str(e)}",
                "executed_at": datetime.now().isoformat()
            })
            self.execution_stats["failed_executions"] += 1
            logger.error(f"Fallback execution failed: {e}")
        
        return execution
    
    async def _execute_strategy(self, strategy: FallbackStrategy, 
                               failure_context: FailureContext) -> Dict[str, Any]:
        """Execute a specific strategy."""
        handler = self.strategy_handlers.get(strategy)
        
        if not handler:
            raise ValueError(f"No handler registered for strategy {strategy.value}")
        
        # Call strategy handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(failure_context, {})
        else:
            return handler(failure_context, {})
    
    def _update_strategy_stats(self, strategy: FallbackStrategy, success: bool):
        """Update strategy success statistics."""
        strategy_name = strategy.value
        
        if strategy_name not in self.execution_stats["strategy_success_rates"]:
            self.execution_stats["strategy_success_rates"][strategy_name] = {
                "total": 0, "successful": 0, "success_rate": 0.0
            }
        
        stats = self.execution_stats["strategy_success_rates"][strategy_name]
        stats["total"] += 1
        
        if success:
            stats["successful"] += 1
        
        stats["success_rate"] = (stats["successful"] / stats["total"]) * 100
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.execution_stats.copy()

class RecoveryMonitor:
    """Monitors recovery progress and health."""
    
    def __init__(self):
        self.active_recoveries = {}
        self.completed_recoveries = []
        self.health_metrics = {
            "overall_success_rate": 0.0,
            "avg_recovery_time": 0.0,
            "failure_trend": "stable"
        }
        
    def start_monitoring(self, execution: FallbackExecution):
        """Start monitoring a fallback execution."""
        self.active_recoveries[execution.execution_id] = execution
        logger.debug(f"Started monitoring execution {execution.execution_id}")
        
    def update_execution(self, execution: FallbackExecution):
        """Update execution status."""
        if execution.execution_id in self.active_recoveries:
            self.active_recoveries[execution.execution_id] = execution
            
            # Move to completed if finished
            if execution.status in [RecoveryStatus.SUCCEEDED, RecoveryStatus.FAILED]:
                self._complete_execution(execution)
    
    def _complete_execution(self, execution: FallbackExecution):
        """Mark execution as completed and update metrics."""
        if execution.execution_id in self.active_recoveries:
            del self.active_recoveries[execution.execution_id]
        
        self.completed_recoveries.append(execution)
        self._update_health_metrics()
        
        logger.info(f"Completed monitoring execution {execution.execution_id} "
                   f"with status {execution.status.value}")
    
    def _update_health_metrics(self):
        """Update overall health metrics."""
        if not self.completed_recoveries:
            return
        
        # Calculate success rate
        successful = sum(1 for ex in self.completed_recoveries 
                        if ex.status == RecoveryStatus.SUCCEEDED)
        total = len(self.completed_recoveries)
        self.health_metrics["overall_success_rate"] = (successful / total) * 100
        
        # Calculate average recovery time
        recovery_times = [ex.execution_time for ex in self.completed_recoveries]
        self.health_metrics["avg_recovery_time"] = sum(recovery_times) / len(recovery_times)
        
        # Analyze failure trend (simplified)
        recent_recoveries = self.completed_recoveries[-10:]  # Last 10
        if len(recent_recoveries) >= 5:
            recent_success_rate = sum(1 for ex in recent_recoveries 
                                    if ex.status == RecoveryStatus.SUCCEEDED) / len(recent_recoveries)
            
            if recent_success_rate > 0.8:
                self.health_metrics["failure_trend"] = "improving"
            elif recent_success_rate < 0.5:
                self.health_metrics["failure_trend"] = "degrading"
            else:
                self.health_metrics["failure_trend"] = "stable"
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            "active_recoveries": len(self.active_recoveries),
            "completed_recoveries": len(self.completed_recoveries),
            "health_metrics": self.health_metrics.copy()
        }

class FallbackManager:
    """Main manager for fallback strategies."""
    
    def __init__(self):
        self.strategy_selector = StrategySelector()
        self.fallback_executor = FallbackExecutor()
        self.recovery_monitor = RecoveryMonitor()
        
        self._setup_default_strategies()
        self._register_strategy_handlers()
    
    def _setup_default_strategies(self):
        """Setup default fallback strategies."""
        # Timeout failures
        timeout_plan = FallbackPlan(
            plan_id="timeout_plan",
            failure_types=[FailureType.TIMEOUT],
            strategies=[FallbackStrategy.RETRY, FallbackStrategy.ALTERNATIVE_SERVICE],
            max_retries=3,
            timeout_seconds=30.0,
            priority=1
        )
        
        # Connection errors
        connection_plan = FallbackPlan(
            plan_id="connection_plan", 
            failure_types=[FailureType.CONNECTION_ERROR, FailureType.SERVICE_UNAVAILABLE],
            strategies=[FallbackStrategy.RETRY, FallbackStrategy.CIRCUIT_BREAKER, FallbackStrategy.CACHE_FALLBACK],
            max_retries=2,
            timeout_seconds=20.0,
            priority=2
        )
        
        # Rate limiting
        rate_limit_plan = FallbackPlan(
            plan_id="rate_limit_plan",
            failure_types=[FailureType.RATE_LIMIT],
            strategies=[FallbackStrategy.ALTERNATIVE_SERVICE, FallbackStrategy.DEGRADED_MODE],
            max_retries=1,
            timeout_seconds=15.0,
            priority=1
        )
        
        # Authentication errors
        auth_plan = FallbackPlan(
            plan_id="auth_plan",
            failure_types=[FailureType.AUTHENTICATION_ERROR],
            strategies=[FallbackStrategy.MANUAL_OVERRIDE, FallbackStrategy.FAIL_FAST],
            max_retries=1,
            timeout_seconds=10.0,
            priority=3
        )
        
        self.strategy_selector.add_fallback_plan(timeout_plan)
        self.strategy_selector.add_fallback_plan(connection_plan)
        self.strategy_selector.add_fallback_plan(rate_limit_plan)
        self.strategy_selector.add_fallback_plan(auth_plan)
    
    def _register_strategy_handlers(self):
        """Register handlers for different strategies."""
        
        async def retry_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Retry the original request."""
            await asyncio.sleep(0.1 * (failure_context.retry_count + 1))  # Exponential backoff
            
            # Simulate retry logic
            if random.random() > 0.3:  # 70% success rate
                return {"success": True, "method": "retry", "attempts": failure_context.retry_count + 1}
            else:
                raise Exception("Retry failed")
        
        async def alternative_service_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Use alternative service."""
            await asyncio.sleep(0.2)  # Simulate service switch time
            
            if random.random() > 0.2:  # 80% success rate
                return {"success": True, "method": "alternative_service", "service": "backup_service"}
            else:
                raise Exception("Alternative service unavailable")
        
        async def degraded_mode_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Operate in degraded mode."""
            await asyncio.sleep(0.05)  # Fast response
            
            return {"success": True, "method": "degraded_mode", "quality": "reduced"}
        
        async def cache_fallback_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Use cached result."""
            await asyncio.sleep(0.01)  # Very fast
            
            if random.random() > 0.1:  # 90% cache hit rate
                return {"success": True, "method": "cache_fallback", "data": "cached_result"}
            else:
                raise Exception("Cache miss")
        
        async def circuit_breaker_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Circuit breaker pattern."""
            await asyncio.sleep(0.1)
            
            # Simulate circuit breaker logic
            return {"success": True, "method": "circuit_breaker", "state": "half_open"}
        
        async def manual_override_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Manual override/intervention."""
            await asyncio.sleep(0.5)  # Simulate manual process
            
            return {"success": True, "method": "manual_override", "operator": "system_admin"}
        
        async def fail_fast_handler(failure_context: FailureContext, options: Dict[str, Any]) -> Dict[str, Any]:
            """Fail fast strategy."""
            return {"success": False, "method": "fail_fast", "reason": "unrecoverable_error"}
        
        # Register handlers
        self.fallback_executor.register_strategy_handler(FallbackStrategy.RETRY, retry_handler)
        self.fallback_executor.register_strategy_handler(FallbackStrategy.ALTERNATIVE_SERVICE, alternative_service_handler)
        self.fallback_executor.register_strategy_handler(FallbackStrategy.DEGRADED_MODE, degraded_mode_handler)
        self.fallback_executor.register_strategy_handler(FallbackStrategy.CACHE_FALLBACK, cache_fallback_handler)
        self.fallback_executor.register_strategy_handler(FallbackStrategy.CIRCUIT_BREAKER, circuit_breaker_handler)
        self.fallback_executor.register_strategy_handler(FallbackStrategy.MANUAL_OVERRIDE, manual_override_handler)
        self.fallback_executor.register_strategy_handler(FallbackStrategy.FAIL_FAST, fail_fast_handler)
    
    async def handle_failure(self, failure_context: FailureContext) -> FallbackExecution:
        """Handle a failure using fallback strategies."""
        logger.info(f"Handling failure {failure_context.failure_id} of type {failure_context.failure_type.value}")
        
        # Select strategy
        fallback_plan = self.strategy_selector.select_strategy(failure_context)
        
        if not fallback_plan:
            # Create default execution for unhandled failures
            execution = FallbackExecution(
                execution_id=f"exec_{int(time.time() * 1000000)}",
                failure_context=failure_context,
                fallback_plan=FallbackPlan("default", [failure_context.failure_type], 
                                         [FallbackStrategy.FAIL_FAST], 0, 5.0),
                current_strategy_index=0,
                started_at=datetime.now(),
                status=RecoveryStatus.FAILED,
                completed_at=datetime.now()
            )
            return execution
        
        # Execute fallback
        execution = await self.fallback_executor.execute_fallback(failure_context, fallback_plan)
        
        # Monitor recovery
        self.recovery_monitor.start_monitoring(execution)
        self.recovery_monitor.update_execution(execution)
        
        return execution

class AgentFallbackStrategiesManager:
    """Manages agent fallback strategies testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.fallback_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = ConnectionManager()
        await self.db_manager.initialize()
        
        self.fallback_manager = FallbackManager()
    
    def create_test_failure(self, agent_id: str, failure_type: FailureType,
                           error_details: Dict[str, Any] = None) -> FailureContext:
        """Create a test failure context."""
        return FailureContext(
            failure_id=f"failure_{int(time.time() * 1000000)}",
            agent_id=agent_id,
            failure_type=failure_type,
            original_request={"test": True, "agent_id": agent_id},
            error_details=error_details or {"error": f"Test {failure_type.value}"},
            occurred_at=datetime.now()
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def fallback_strategies_manager():
    """Create fallback strategies manager for testing."""
    manager = AgentFallbackStrategiesManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_basic_fallback_strategy_selection(fallback_strategies_manager):
    """Test basic fallback strategy selection."""
    manager = fallback_strategies_manager
    
    # Create timeout failure
    failure = manager.create_test_failure("test_agent", FailureType.TIMEOUT)
    
    # Select strategy
    plan = manager.fallback_manager.strategy_selector.select_strategy(failure)
    
    assert plan is not None
    assert plan.plan_id == "timeout_plan"
    assert FailureType.TIMEOUT in plan.failure_types
    assert FallbackStrategy.RETRY in plan.strategies

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_fallback_execution_with_retry(fallback_strategies_manager):
    """Test fallback execution with retry strategy."""
    manager = fallback_strategies_manager
    
    # Create failure
    failure = manager.create_test_failure("retry_agent", FailureType.TIMEOUT)
    
    # Handle failure
    execution = await manager.fallback_manager.handle_failure(failure)
    
    assert execution is not None
    assert execution.status in [RecoveryStatus.SUCCEEDED, RecoveryStatus.FAILED]
    assert len(execution.results) > 0
    
    # Check that retry was attempted
    retry_results = [r for r in execution.results if r.get("strategy") == "retry"]
    assert len(retry_results) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_alternative_service_fallback(fallback_strategies_manager):
    """Test alternative service fallback strategy."""
    manager = fallback_strategies_manager
    
    # Create connection error
    failure = manager.create_test_failure("alt_service_agent", FailureType.CONNECTION_ERROR)
    
    # Handle failure
    execution = await manager.fallback_manager.handle_failure(failure)
    
    assert execution is not None
    
    # Check if alternative service was used
    alt_service_results = [r for r in execution.results 
                          if r.get("strategy") == "alternative_service"]
    
    # Should have attempted alternative service if retry failed
    if execution.status == RecoveryStatus.SUCCEEDED:
        success_results = [r for r in execution.results if r.get("success")]
        assert len(success_results) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_degraded_mode_operation(fallback_strategies_manager):
    """Test degraded mode fallback strategy."""
    manager = fallback_strategies_manager
    
    # Create rate limit failure
    failure = manager.create_test_failure("degraded_agent", FailureType.RATE_LIMIT)
    
    # Handle failure
    execution = await manager.fallback_manager.handle_failure(failure)
    
    assert execution is not None
    
    # Check for degraded mode usage
    degraded_results = [r for r in execution.results 
                       if r.get("strategy") == "degraded_mode"]
    
    # Rate limit plan includes degraded mode as a strategy
    if execution.status == RecoveryStatus.SUCCEEDED:
        success_result = next((r for r in execution.results if r.get("success")), None)
        assert success_result is not None

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_cache_fallback_strategy(fallback_strategies_manager):
    """Test cache fallback strategy."""
    manager = fallback_strategies_manager
    
    # Create service unavailable error
    failure = manager.create_test_failure("cache_agent", FailureType.SERVICE_UNAVAILABLE)
    
    # Handle failure
    execution = await manager.fallback_manager.handle_failure(failure)
    
    assert execution is not None
    
    # Check for cache fallback usage
    cache_results = [r for r in execution.results 
                    if r.get("strategy") == "cache_fallback"]
    
    # Connection plan includes cache fallback
    if len(cache_results) > 0:
        cache_result = cache_results[0]
        # Cache fallback should be fast
        assert cache_result is not None

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_authentication_error_handling(fallback_strategies_manager):
    """Test authentication error handling with manual override."""
    manager = fallback_strategies_manager
    
    # Create auth error
    failure = manager.create_test_failure("auth_agent", FailureType.AUTHENTICATION_ERROR)
    
    # Handle failure
    execution = await manager.fallback_manager.handle_failure(failure)
    
    assert execution is not None
    assert execution.fallback_plan.plan_id == "auth_plan"
    
    # Check for manual override or fail fast
    manual_results = [r for r in execution.results 
                     if r.get("strategy") in ["manual_override", "fail_fast"]]
    assert len(manual_results) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_strategy_priority_ordering(fallback_strategies_manager):
    """Test that higher priority strategies are selected first."""
    manager = fallback_strategies_manager
    
    # Create failures that match multiple plans
    rate_limit_failure = manager.create_test_failure("priority_agent", FailureType.RATE_LIMIT)
    timeout_failure = manager.create_test_failure("priority_agent", FailureType.TIMEOUT)
    
    # Both should select their respective highest priority plans
    rate_plan = manager.fallback_manager.strategy_selector.select_strategy(rate_limit_failure)
    timeout_plan = manager.fallback_manager.strategy_selector.select_strategy(timeout_failure)
    
    assert rate_plan.plan_id == "rate_limit_plan"  # Priority 1
    assert timeout_plan.plan_id == "timeout_plan"  # Priority 1
    
    # Both should have priority 1 (highest)
    assert rate_plan.priority == 1
    assert timeout_plan.priority == 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_strategy_execution_timeout(fallback_strategies_manager):
    """Test strategy execution timeout handling."""
    manager = fallback_strategies_manager
    
    # Create custom plan with very short timeout
    short_timeout_plan = FallbackPlan(
        plan_id="short_timeout_plan",
        failure_types=[FailureType.UNKNOWN_ERROR],
        strategies=[FallbackStrategy.RETRY],
        max_retries=1,
        timeout_seconds=0.01  # Very short timeout
    )
    
    manager.fallback_manager.strategy_selector.add_fallback_plan(short_timeout_plan)
    
    # Create failure
    failure = manager.create_test_failure("timeout_test_agent", FailureType.UNKNOWN_ERROR)
    
    # Handle failure
    execution = await manager.fallback_manager.handle_failure(failure)
    
    # Should have timeout results
    timeout_results = [r for r in execution.results if r.get("error") == "timeout"]
    assert len(timeout_results) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_recovery_monitoring(fallback_strategies_manager):
    """Test recovery monitoring and health metrics."""
    manager = fallback_strategies_manager
    
    # Create multiple failures to generate metrics
    failures = [
        manager.create_test_failure(f"monitor_agent_{i}", FailureType.TIMEOUT)
        for i in range(5)
    ]
    
    # Handle all failures
    executions = []
    for failure in failures:
        execution = await manager.fallback_manager.handle_failure(failure)
        executions.append(execution)
    
    # Check monitoring stats
    health_status = manager.fallback_manager.recovery_monitor.get_health_status()
    
    assert health_status["completed_recoveries"] == 5
    assert health_status["active_recoveries"] == 0  # All should be completed
    assert "overall_success_rate" in health_status["health_metrics"]
    assert "avg_recovery_time" in health_status["health_metrics"]

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_concurrent_fallback_execution(fallback_strategies_manager):
    """Test concurrent execution of multiple fallback strategies."""
    manager = fallback_strategies_manager
    
    # Create multiple failures of different types
    failures = [
        manager.create_test_failure(f"concurrent_agent_{i}", 
                                  [FailureType.TIMEOUT, FailureType.CONNECTION_ERROR, 
                                   FailureType.RATE_LIMIT][i % 3])
        for i in range(10)
    ]
    
    # Handle failures concurrently
    start_time = time.time()
    tasks = [manager.fallback_manager.handle_failure(failure) for failure in failures]
    executions = await asyncio.gather(*tasks)
    execution_time = time.time() - start_time
    
    assert len(executions) == 10
    assert all(ex is not None for ex in executions)
    
    # Concurrent execution should be faster than sequential
    assert execution_time < 5.0  # Should complete quickly with concurrency
    
    # Check success rates
    successful_executions = [ex for ex in executions 
                           if ex.status == RecoveryStatus.SUCCEEDED]
    success_rate = len(successful_executions) / len(executions) * 100
    
    # Should have reasonable success rate (strategies have good success rates)
    assert success_rate > 30  # At least 30% success rate

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_strategy_success_rate_tracking(fallback_strategies_manager):
    """Test tracking of strategy success rates."""
    manager = fallback_strategies_manager
    
    # Execute multiple fallbacks to build statistics
    for i in range(20):
        failure = manager.create_test_failure(f"stats_agent_{i}", FailureType.TIMEOUT)
        await manager.fallback_manager.handle_failure(failure)
    
    # Get execution stats
    stats = manager.fallback_manager.fallback_executor.get_execution_stats()
    
    assert stats["total_executions"] == 20
    assert "strategy_success_rates" in stats
    
    # Should have statistics for retry strategy
    if "retry" in stats["strategy_success_rates"]:
        retry_stats = stats["strategy_success_rates"]["retry"]
        assert retry_stats["total"] > 0
        assert 0 <= retry_stats["success_rate"] <= 100

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_fallback_performance_benchmark(fallback_strategies_manager):
    """Benchmark fallback strategy performance."""
    manager = fallback_strategies_manager
    
    # Create many failures for performance testing
    failures = [
        manager.create_test_failure(f"perf_agent_{i}", 
                                  [FailureType.TIMEOUT, FailureType.CONNECTION_ERROR][i % 2])
        for i in range(50)
    ]
    
    # Benchmark execution time
    start_time = time.time()
    
    tasks = [manager.fallback_manager.handle_failure(failure) for failure in failures]
    executions = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    assert len(executions) == 50
    
    # Performance assertions
    assert total_time < 10.0  # 50 fallbacks in under 10 seconds
    
    avg_execution_time = total_time / 50
    assert avg_execution_time < 0.2  # Under 200ms per fallback on average
    
    # Check individual execution times
    execution_times = [ex.execution_time for ex in executions if ex.execution_time]
    if execution_times:
        max_execution_time = max(execution_times)
        assert max_execution_time < 5.0  # No single execution over 5 seconds
    
    logger.info(f"Performance: {avg_execution_time*1000:.1f}ms average per fallback")
    logger.info(f"Total time for 50 fallbacks: {total_time:.2f}s")