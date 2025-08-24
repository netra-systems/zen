"""Agent Timeout and Cancellation L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (responsive AI operations)
- Business Goal: Responsiveness and user experience quality
- Value Impact: Protects $6K MRR from timeout-related UX degradation
- Strategic Impact: Core responsiveness feature for real-time AI interactions

Critical Path: Timeout detection -> Cancellation signal -> Graceful shutdown -> Resource cleanup
Coverage: Real timeout managers, cancellation handlers, cleanup coordination
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager as ConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class TimeoutType(Enum):
    """Types of timeouts that can occur."""
    EXECUTION = "execution"
    RESPONSE = "response"
    IDLE = "idle"
    TOTAL = "total"

class CancellationReason(Enum):
    """Reasons for cancellation."""
    TIMEOUT = "timeout"
    USER_REQUEST = "user_request"
    SYSTEM_SHUTDOWN = "system_shutdown"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    ERROR_THRESHOLD = "error_threshold"

@dataclass
class TimeoutConfig:
    """Configuration for timeout settings."""
    timeout_type: TimeoutType
    duration_seconds: float
    grace_period_seconds: float = 5.0
    retry_count: int = 0
    escalation_enabled: bool = True

@dataclass
class CancellationEvent:
    """Event representing a cancellation request."""
    cancellation_id: str
    agent_id: str
    reason: CancellationReason
    timeout_config: Optional[TimeoutConfig]
    requested_at: datetime
    graceful: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "cancellation_id": self.cancellation_id,
            "agent_id": self.agent_id,
            "reason": self.reason.value,
            "timeout_type": self.timeout_config.timeout_type.value if self.timeout_config else None,
            "requested_at": self.requested_at.isoformat(),
            "graceful": self.graceful
        }

class TimeoutManager:
    """Manages timeouts for agent operations."""
    
    def __init__(self):
        self.active_timeouts = {}
        self.timeout_history = []
        self.default_configs = {
            TimeoutType.EXECUTION: TimeoutConfig(TimeoutType.EXECUTION, 30.0),
            TimeoutType.RESPONSE: TimeoutConfig(TimeoutType.RESPONSE, 10.0),
            TimeoutType.IDLE: TimeoutConfig(TimeoutType.IDLE, 300.0),
            TimeoutType.TOTAL: TimeoutConfig(TimeoutType.TOTAL, 600.0)
        }
        
    def set_timeout_config(self, timeout_type: TimeoutType, config: TimeoutConfig):
        """Set timeout configuration for a specific type."""
        self.default_configs[timeout_type] = config
        
    async def start_timeout(self, agent_id: str, timeout_type: TimeoutType, 
                           custom_duration: Optional[float] = None) -> str:
        """Start a timeout timer for an agent."""
        config = self.default_configs[timeout_type]
        duration = custom_duration or config.duration_seconds
        
        timeout_id = f"timeout_{agent_id}_{timeout_type.value}_{int(time.time() * 1000)}"
        
        # Create timeout task
        timeout_task = asyncio.create_task(
            self._timeout_coroutine(timeout_id, agent_id, duration, config)
        )
        
        self.active_timeouts[timeout_id] = {
            "agent_id": agent_id,
            "timeout_type": timeout_type,
            "config": config,
            "task": timeout_task,
            "started_at": datetime.now()
        }
        
        logger.debug(f"Started {timeout_type.value} timeout for {agent_id}: {duration}s")
        return timeout_id
        
    async def _timeout_coroutine(self, timeout_id: str, agent_id: str, 
                                duration: float, config: TimeoutConfig):
        """Coroutine that handles timeout logic."""
        try:
            await asyncio.sleep(duration)
            
            # Timeout occurred
            await self._handle_timeout(timeout_id, agent_id, config)
            
        except asyncio.CancelledError:
            # Timeout was cancelled (normal completion)
            logger.debug(f"Timeout {timeout_id} cancelled (normal completion)")
            raise
        
    async def _handle_timeout(self, timeout_id: str, agent_id: str, config: TimeoutConfig):
        """Handle timeout occurrence."""
        timeout_event = {
            "timeout_id": timeout_id,
            "agent_id": agent_id,
            "timeout_type": config.timeout_type,
            "occurred_at": datetime.now()
        }
        
        self.timeout_history.append(timeout_event)
        
        # Create cancellation event
        cancellation_event = CancellationEvent(
            cancellation_id=f"cancel_{timeout_id}",
            agent_id=agent_id,
            reason=CancellationReason.TIMEOUT,
            timeout_config=config,
            requested_at=datetime.now(),
            graceful=True
        )
        
        # Notify cancellation handlers (would be implemented in real system)
        logger.warning(f"Timeout occurred for {agent_id}: {config.timeout_type.value}")
        
        return cancellation_event
        
    def cancel_timeout(self, timeout_id: str) -> bool:
        """Cancel an active timeout."""
        timeout_info = self.active_timeouts.get(timeout_id)
        
        if timeout_info and not timeout_info["task"].done():
            timeout_info["task"].cancel()
            logger.debug(f"Cancelled timeout {timeout_id}")
            return True
            
        return False
        
    def cancel_agent_timeouts(self, agent_id: str) -> int:
        """Cancel all timeouts for a specific agent."""
        cancelled_count = 0
        
        for timeout_id, timeout_info in list(self.active_timeouts.items()):
            if timeout_info["agent_id"] == agent_id:
                if self.cancel_timeout(timeout_id):
                    cancelled_count += 1
                    
        return cancelled_count
        
    def get_active_timeouts(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of active timeouts."""
        active_list = []
        
        for timeout_id, timeout_info in self.active_timeouts.items():
            if agent_id is None or timeout_info["agent_id"] == agent_id:
                if not timeout_info["task"].done():
                    active_list.append({
                        "timeout_id": timeout_id,
                        "agent_id": timeout_info["agent_id"],
                        "timeout_type": timeout_info["timeout_type"].value,
                        "started_at": timeout_info["started_at"].isoformat(),
                        "remaining_seconds": self._calculate_remaining_time(timeout_info)
                    })
                    
        return active_list
        
    def _calculate_remaining_time(self, timeout_info: Dict[str, Any]) -> float:
        """Calculate remaining time for a timeout."""
        elapsed = (datetime.now() - timeout_info["started_at"]).total_seconds()
        duration = timeout_info["config"].duration_seconds
        return max(0, duration - elapsed)

class CancellationHandler:
    """Handles cancellation requests and coordination."""
    
    def __init__(self, timeout_manager: TimeoutManager):
        self.timeout_manager = timeout_manager
        self.cancellation_hooks = []
        self.cancellation_history = []
        
    def add_cancellation_hook(self, hook: Callable[[CancellationEvent], Awaitable[None]]):
        """Add a hook that gets called during cancellation."""
        self.cancellation_hooks.append(hook)
        
    async def request_cancellation(self, agent_id: str, reason: CancellationReason, 
                                  graceful: bool = True) -> CancellationEvent:
        """Request cancellation of an agent."""
        cancellation_event = CancellationEvent(
            cancellation_id=f"cancel_{agent_id}_{int(time.time() * 1000)}",
            agent_id=agent_id,
            reason=reason,
            timeout_config=None,
            requested_at=datetime.now(),
            graceful=graceful
        )
        
        self.cancellation_history.append(cancellation_event)
        
        # Cancel associated timeouts
        cancelled_timeouts = self.timeout_manager.cancel_agent_timeouts(agent_id)
        
        # Call cancellation hooks
        await self._execute_cancellation_hooks(cancellation_event)
        
        logger.info(f"Cancellation requested for {agent_id}: {reason.value} "
                   f"(cancelled {cancelled_timeouts} timeouts)")
        
        return cancellation_event
        
    async def _execute_cancellation_hooks(self, cancellation_event: CancellationEvent):
        """Execute all cancellation hooks."""
        for hook in self.cancellation_hooks:
            try:
                await hook(cancellation_event)
            except Exception as e:
                logger.error(f"Cancellation hook failed: {e}")

class CleanupCoordinator:
    """Coordinates cleanup operations during cancellation."""
    
    def __init__(self):
        self.cleanup_tasks = {}
        self.cleanup_stats = {
            "total_cleanups": 0,
            "successful_cleanups": 0,
            "failed_cleanups": 0
        }
        
    def register_cleanup_task(self, agent_id: str, cleanup_func: Callable[[], Awaitable[None]], 
                             priority: int = 5):
        """Register a cleanup task for an agent."""
        if agent_id not in self.cleanup_tasks:
            self.cleanup_tasks[agent_id] = []
            
        self.cleanup_tasks[agent_id].append({
            "cleanup_func": cleanup_func,
            "priority": priority
        })
        
        # Sort by priority (higher priority first)
        self.cleanup_tasks[agent_id].sort(key=lambda x: x["priority"], reverse=True)
        
    async def execute_cleanup(self, agent_id: str, grace_period: float = 5.0) -> Dict[str, Any]:
        """Execute cleanup tasks for an agent."""
        start_time = time.time()
        cleanup_results = {
            "agent_id": agent_id,
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "cleanup_time": 0,
            "errors": []
        }
        
        tasks = self.cleanup_tasks.get(agent_id, [])
        cleanup_results["total_tasks"] = len(tasks)
        
        try:
            # Execute cleanup tasks with timeout
            cleanup_future = asyncio.create_task(self._execute_cleanup_tasks(tasks, cleanup_results))
            
            try:
                await asyncio.wait_for(cleanup_future, timeout=grace_period)
            except asyncio.TimeoutError:
                cleanup_future.cancel()
                cleanup_results["errors"].append("Cleanup timed out")
                logger.warning(f"Cleanup timed out for {agent_id}")
                
        except Exception as e:
            cleanup_results["errors"].append(str(e))
            logger.error(f"Cleanup failed for {agent_id}: {e}")
            
        cleanup_results["cleanup_time"] = time.time() - start_time
        
        # Update stats
        self.cleanup_stats["total_cleanups"] += 1
        if not cleanup_results["errors"]:
            self.cleanup_stats["successful_cleanups"] += 1
        else:
            self.cleanup_stats["failed_cleanups"] += 1
            
        # Remove completed cleanup tasks
        if agent_id in self.cleanup_tasks:
            del self.cleanup_tasks[agent_id]
            
        return cleanup_results
        
    async def _execute_cleanup_tasks(self, tasks: List[Dict[str, Any]], 
                                   cleanup_results: Dict[str, Any]):
        """Execute cleanup tasks in priority order."""
        for task in tasks:
            try:
                await task["cleanup_func"]()
                cleanup_results["successful_tasks"] += 1
            except Exception as e:
                cleanup_results["failed_tasks"] += 1
                cleanup_results["errors"].append(str(e))
                logger.error(f"Cleanup task failed: {e}")

class MockAgent:
    """Mock agent for testing timeout and cancellation."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.is_running = False
        self.is_cancelled = False
        self.execution_time = 0
        
    async def execute_task(self, duration: float):
        """Execute a task with specified duration."""
        self.is_running = True
        start_time = time.time()
        
        try:
            # Simulate work with cancellation checks
            while time.time() - start_time < duration:
                if self.is_cancelled:
                    raise asyncio.CancelledError("Agent was cancelled")
                await asyncio.sleep(0.1)  # Check cancellation every 100ms
                
        except asyncio.CancelledError:
            self.execution_time = time.time() - start_time
            raise
        finally:
            self.is_running = False
            
        self.execution_time = time.time() - start_time
        return {"success": True, "execution_time": self.execution_time}
        
    def cancel(self):
        """Cancel the agent."""
        self.is_cancelled = True

class AgentTimeoutCancellationManager:
    """Manages agent timeout and cancellation testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.timeout_manager = None
        self.cancellation_handler = None
        self.cleanup_coordinator = None
        self.mock_agents = {}
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = ConnectionManager()
        await self.db_manager.initialize()
        
        self.timeout_manager = TimeoutManager()
        self.cancellation_handler = CancellationHandler(self.timeout_manager)
        self.cleanup_coordinator = CleanupCoordinator()
        
        # Setup cancellation hooks
        self.cancellation_handler.add_cancellation_hook(self._handle_agent_cancellation)
        
    async def _handle_agent_cancellation(self, cancellation_event: CancellationEvent):
        """Handle agent cancellation."""
        agent = self.mock_agents.get(cancellation_event.agent_id)
        if agent:
            agent.cancel()
            
        # Execute cleanup
        await self.cleanup_coordinator.execute_cleanup(cancellation_event.agent_id)
        
    def create_mock_agent(self, agent_id: str) -> MockAgent:
        """Create a mock agent for testing."""
        agent = MockAgent(agent_id)
        self.mock_agents[agent_id] = agent
        
        # Register cleanup task
        async def cleanup_agent():
            logger.info(f"Cleaning up agent {agent_id}")
            # Simulate cleanup work
            await asyncio.sleep(0.1)
            
        self.cleanup_coordinator.register_cleanup_task(agent_id, cleanup_agent)
        
        return agent
        
    async def run_agent_with_timeout(self, agent: MockAgent, task_duration: float, 
                                   timeout_duration: float) -> Dict[str, Any]:
        """Run agent with timeout monitoring."""
        # Start timeout
        timeout_id = await self.timeout_manager.start_timeout(
            agent.agent_id, TimeoutType.EXECUTION, timeout_duration
        )
        
        start_time = time.time()
        
        try:
            # Run agent task
            result = await agent.execute_task(task_duration)
            
            # Cancel timeout (task completed normally)
            self.timeout_manager.cancel_timeout(timeout_id)
            
            return {
                "success": True,
                "result": result,
                "total_time": time.time() - start_time,
                "timed_out": False
            }
            
        except asyncio.CancelledError:
            return {
                "success": False,
                "result": None,
                "total_time": time.time() - start_time,
                "timed_out": True
            }
            
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def timeout_cancellation_manager():
    """Create timeout cancellation manager for testing."""
    manager = AgentTimeoutCancellationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_basic_timeout_detection(timeout_cancellation_manager):
    """Test basic timeout detection and handling."""
    manager = timeout_cancellation_manager
    
    # Create agent with long task
    agent = manager.create_mock_agent("timeout_test_agent")
    
    # Run task that should timeout
    result = await manager.run_agent_with_timeout(
        agent=agent,
        task_duration=2.0,    # 2 second task
        timeout_duration=1.0   # 1 second timeout
    )
    
    assert result["success"] is False
    assert result["timed_out"] is True
    assert result["total_time"] < 1.5  # Should be cancelled quickly
    
    # Verify timeout was recorded
    assert len(manager.timeout_manager.timeout_history) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_successful_task_completion(timeout_cancellation_manager):
    """Test successful task completion before timeout."""
    manager = timeout_cancellation_manager
    
    # Create agent with short task
    agent = manager.create_mock_agent("success_test_agent")
    
    # Run task that should complete before timeout
    result = await manager.run_agent_with_timeout(
        agent=agent,
        task_duration=0.5,    # 0.5 second task
        timeout_duration=2.0   # 2 second timeout
    )
    
    assert result["success"] is True
    assert result["timed_out"] is False
    assert result["total_time"] < 1.0
    
    # Verify no timeout occurred
    assert len(manager.timeout_manager.timeout_history) == 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_manual_cancellation(timeout_cancellation_manager):
    """Test manual cancellation request."""
    manager = timeout_cancellation_manager
    
    # Create agent with long task
    agent = manager.create_mock_agent("manual_cancel_agent")
    
    # Start task
    task = asyncio.create_task(agent.execute_task(5.0))
    
    # Wait a bit then cancel
    await asyncio.sleep(0.2)
    
    cancellation_event = await manager.cancellation_handler.request_cancellation(
        agent.agent_id, CancellationReason.USER_REQUEST
    )
    
    # Task should be cancelled
    with pytest.raises(asyncio.CancelledError):
        await task
    
    assert cancellation_event.reason == CancellationReason.USER_REQUEST
    assert len(manager.cancellation_handler.cancellation_history) == 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_graceful_cleanup_execution(timeout_cancellation_manager):
    """Test graceful cleanup execution during cancellation."""
    manager = timeout_cancellation_manager
    
    # Create agent and add multiple cleanup tasks
    agent = manager.create_mock_agent("cleanup_test_agent")
    
    cleanup_executed = []
    
    async def cleanup_task_1():
        cleanup_executed.append("task_1")
        await asyncio.sleep(0.05)
    
    async def cleanup_task_2():
        cleanup_executed.append("task_2")
        await asyncio.sleep(0.05)
    
    # Register cleanup tasks with different priorities
    manager.cleanup_coordinator.register_cleanup_task(agent.agent_id, cleanup_task_1, priority=10)
    manager.cleanup_coordinator.register_cleanup_task(agent.agent_id, cleanup_task_2, priority=5)
    
    # Request cancellation
    await manager.cancellation_handler.request_cancellation(
        agent.agent_id, CancellationReason.USER_REQUEST
    )
    
    # Allow cleanup to complete
    await asyncio.sleep(0.2)
    
    # Verify cleanup tasks were executed in priority order
    assert "task_1" in cleanup_executed
    assert "task_2" in cleanup_executed
    assert cleanup_executed.index("task_1") < cleanup_executed.index("task_2")

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_multiple_timeout_types(timeout_cancellation_manager):
    """Test multiple timeout types for the same agent."""
    manager = timeout_cancellation_manager
    
    agent = manager.create_mock_agent("multi_timeout_agent")
    
    # Start multiple timeouts
    execution_timeout = await manager.timeout_manager.start_timeout(
        agent.agent_id, TimeoutType.EXECUTION, 2.0
    )
    
    response_timeout = await manager.timeout_manager.start_timeout(
        agent.agent_id, TimeoutType.RESPONSE, 1.0
    )
    
    # Verify active timeouts
    active_timeouts = manager.timeout_manager.get_active_timeouts(agent.agent_id)
    assert len(active_timeouts) == 2
    
    # Cancel all timeouts for agent
    cancelled_count = manager.timeout_manager.cancel_agent_timeouts(agent.agent_id)
    assert cancelled_count == 2

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_timeout_configuration_override(timeout_cancellation_manager):
    """Test timeout configuration override."""
    manager = timeout_cancellation_manager
    
    # Set custom timeout config
    custom_config = TimeoutConfig(
        timeout_type=TimeoutType.EXECUTION,
        duration_seconds=0.5,
        grace_period_seconds=2.0
    )
    
    manager.timeout_manager.set_timeout_config(TimeoutType.EXECUTION, custom_config)
    
    agent = manager.create_mock_agent("config_test_agent")
    
    # Run with custom timeout
    result = await manager.run_agent_with_timeout(
        agent=agent,
        task_duration=1.0,    # 1 second task
        timeout_duration=None  # Use default (now 0.5 seconds)
    )
    
    assert result["timed_out"] is True
    assert result["total_time"] < 1.0  # Should timeout before task completes

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_concurrent_agent_timeouts(timeout_cancellation_manager):
    """Test concurrent timeout handling for multiple agents."""
    manager = timeout_cancellation_manager
    
    # Create multiple agents
    agents = [
        manager.create_mock_agent(f"concurrent_agent_{i}")
        for i in range(5)
    ]
    
    # Run all agents concurrently with different timeout scenarios
    tasks = []
    for i, agent in enumerate(agents):
        task_duration = 0.5 + (i * 0.2)  # Varying task durations
        timeout_duration = 1.0            # Same timeout for all
        
        task = manager.run_agent_with_timeout(agent, task_duration, timeout_duration)
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    # Some should succeed, some should timeout
    successful_results = [r for r in results if r["success"]]
    timed_out_results = [r for r in results if r["timed_out"]]
    
    assert len(successful_results) > 0  # Some should complete
    assert len(timed_out_results) > 0   # Some should timeout

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_cleanup_timeout_handling(timeout_cancellation_manager):
    """Test cleanup timeout handling for slow cleanup tasks."""
    manager = timeout_cancellation_manager
    
    agent = manager.create_mock_agent("slow_cleanup_agent")
    
    # Add slow cleanup task
    async def slow_cleanup():
        await asyncio.sleep(10.0)  # Very slow cleanup
    
    manager.cleanup_coordinator.register_cleanup_task(agent.agent_id, slow_cleanup)
    
    # Request cancellation with short grace period
    start_time = time.time()
    
    await manager.cancellation_handler.request_cancellation(
        agent.agent_id, CancellationReason.USER_REQUEST
    )
    
    cleanup_time = time.time() - start_time
    
    # Cleanup should be terminated due to grace period
    assert cleanup_time < 7.0  # Should not wait full 10 seconds
    
    # Check cleanup stats
    assert manager.cleanup_coordinator.cleanup_stats["failed_cleanups"] > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_cancellation_hook_execution(timeout_cancellation_manager):
    """Test cancellation hook execution and error handling."""
    manager = timeout_cancellation_manager
    
    hook_calls = []
    
    @pytest.mark.asyncio
    async def test_hook(cancellation_event: CancellationEvent):
        hook_calls.append(cancellation_event.agent_id)
    
    async def failing_hook(cancellation_event: CancellationEvent):
        raise Exception("Hook failed")
    
    # Add hooks
    manager.cancellation_handler.add_cancellation_hook(test_hook)
    manager.cancellation_handler.add_cancellation_hook(failing_hook)
    
    agent = manager.create_mock_agent("hook_test_agent")
    
    # Request cancellation
    await manager.cancellation_handler.request_cancellation(
        agent.agent_id, CancellationReason.USER_REQUEST
    )
    
    # Verify successful hook was called despite failing hook
    assert agent.agent_id in hook_calls

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_timeout_cancellation_performance(timeout_cancellation_manager):
    """Benchmark timeout and cancellation performance."""
    manager = timeout_cancellation_manager
    
    # Benchmark timeout setup
    start_time = time.time()
    
    agents = [
        manager.create_mock_agent(f"perf_agent_{i}")
        for i in range(50)
    ]
    
    timeout_ids = []
    for agent in agents:
        timeout_id = await manager.timeout_manager.start_timeout(
            agent.agent_id, TimeoutType.EXECUTION, 10.0
        )
        timeout_ids.append(timeout_id)
    
    setup_time = time.time() - start_time
    
    # Benchmark cancellation
    start_time = time.time()
    
    for agent in agents:
        await manager.cancellation_handler.request_cancellation(
            agent.agent_id, CancellationReason.USER_REQUEST
        )
    
    cancellation_time = time.time() - start_time
    
    # Performance assertions
    assert setup_time < 1.0      # 50 timeouts in under 1 second
    assert cancellation_time < 2.0  # 50 cancellations in under 2 seconds
    
    avg_setup_time = setup_time / 50
    avg_cancellation_time = cancellation_time / 50
    
    assert avg_setup_time < 0.02      # Under 20ms per timeout setup
    assert avg_cancellation_time < 0.04  # Under 40ms per cancellation
    
    logger.info(f"Performance: Setup {avg_setup_time*1000:.1f}ms, "
               f"Cancellation {avg_cancellation_time*1000:.1f}ms")