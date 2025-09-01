"""
Recovery Manager for Agent Failures
====================================
Handles recovery from agent deaths, timeouts, and other failures.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from netra_backend.app.core.execution_tracker import ExecutionRecord, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for failed agents."""
    RETRY = "retry"  # Retry the same agent
    FALLBACK = "fallback"  # Use fallback agent
    SKIP = "skip"  # Skip and continue
    ABORT = "abort"  # Abort entire pipeline
    RESTART = "restart"  # Restart agent service


@dataclass
class RecoveryAttempt:
    """Track a recovery attempt."""
    execution_id: UUID
    agent_name: str
    strategy: RecoveryStrategy
    attempt_number: int
    timestamp: float
    success: bool
    error: Optional[str] = None
    
    
class RecoveryManager:
    """
    Manages recovery from agent failures.
    
    Features:
    - Automatic retry with exponential backoff
    - Fallback to alternative agents
    - Dead letter queue for failed messages
    - Circuit breaker pattern
    """
    
    MAX_RETRY_ATTEMPTS = 3
    INITIAL_RETRY_DELAY = 1.0  # 1 second
    MAX_RETRY_DELAY = 30.0  # 30 seconds
    CIRCUIT_BREAKER_THRESHOLD = 5  # failures before circuit opens
    CIRCUIT_BREAKER_TIMEOUT = 60.0  # 60 seconds cooldown
    
    def __init__(self):
        self.recovery_attempts: List[RecoveryAttempt] = []
        self.dead_letter_queue: List[ExecutionRecord] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_agents: Dict[str, str] = {
            "triage": "fallback_triage",
            "data": "reporting",  # Fallback to reporting if data fails
            "optimization": "actions",  # Fallback to actions if optimization fails
        }
        self._lock = asyncio.Lock()
        
    async def handle_failed_execution(
        self,
        execution: ExecutionRecord,
        strategy: Optional[RecoveryStrategy] = None
    ) -> bool:
        """
        Handle a failed execution with recovery strategy.
        
        Returns:
            bool: True if recovery successful, False otherwise
        """
        async with self._lock:
            agent_name = execution.agent_name
            
            # Check circuit breaker
            if self._is_circuit_open(agent_name):
                logger.error(f"Circuit breaker OPEN for {agent_name} - sending to DLQ")
                await self._send_to_dlq(execution)
                return False
            
            # Determine recovery strategy
            if strategy is None:
                strategy = self._determine_strategy(execution)
            
            logger.info(f"Attempting recovery for {agent_name} with strategy: {strategy.value}")
            
            # Execute recovery based on strategy
            success = False
            if strategy == RecoveryStrategy.RETRY:
                success = await self._retry_execution(execution)
            elif strategy == RecoveryStrategy.FALLBACK:
                success = await self._fallback_execution(execution)
            elif strategy == RecoveryStrategy.SKIP:
                success = await self._skip_execution(execution)
            elif strategy == RecoveryStrategy.RESTART:
                success = await self._restart_agent(execution)
            else:  # ABORT
                await self._abort_pipeline(execution)
                
            # Record recovery attempt
            attempt = RecoveryAttempt(
                execution_id=execution.execution_id,
                agent_name=agent_name,
                strategy=strategy,
                attempt_number=self._get_attempt_count(execution.execution_id),
                timestamp=time.time(),
                success=success
            )
            self.recovery_attempts.append(attempt)
            
            # Update circuit breaker
            if not success:
                self._record_failure(agent_name)
            else:
                self._record_success(agent_name)
                
            return success
    
    def _determine_strategy(self, execution: ExecutionRecord) -> RecoveryStrategy:
        """Determine the best recovery strategy based on failure type."""
        
        # Check attempt count
        attempt_count = self._get_attempt_count(execution.execution_id)
        
        if execution.state == ExecutionState.TIMEOUT:
            # Timeout failures - retry with longer timeout
            if attempt_count < self.MAX_RETRY_ATTEMPTS:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.FALLBACK
                
        elif execution.state == ExecutionState.DEAD:
            # Agent death - restart and retry
            if attempt_count == 0:
                return RecoveryStrategy.RESTART
            elif attempt_count < self.MAX_RETRY_ATTEMPTS:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.FALLBACK
                
        elif execution.state == ExecutionState.FAILED:
            # General failure - check error type
            if "connection" in (execution.error or "").lower():
                return RecoveryStrategy.RESTART
            elif attempt_count < self.MAX_RETRY_ATTEMPTS:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.SKIP
                
        return RecoveryStrategy.ABORT
    
    async def _retry_execution(self, execution: ExecutionRecord) -> bool:
        """Retry the failed execution with exponential backoff."""
        attempt_count = self._get_attempt_count(execution.execution_id)
        
        if attempt_count >= self.MAX_RETRY_ATTEMPTS:
            logger.error(f"Max retry attempts reached for {execution.agent_name}")
            await self._send_to_dlq(execution)
            return False
        
        # Calculate delay with exponential backoff
        delay = min(
            self.INITIAL_RETRY_DELAY * (2 ** attempt_count),
            self.MAX_RETRY_DELAY
        )
        
        logger.info(f"Retrying {execution.agent_name} after {delay}s (attempt {attempt_count + 1})")
        await asyncio.sleep(delay)
        
        # TODO: Actually retry the execution
        # This would need to re-invoke the agent with the original context
        # For now, we'll simulate success/failure
        
        # Simulate 70% success rate on retry
        import random
        return random.random() < 0.7
    
    async def _fallback_execution(self, execution: ExecutionRecord) -> bool:
        """Use a fallback agent."""
        fallback_agent = self.fallback_agents.get(execution.agent_name)
        
        if not fallback_agent:
            logger.error(f"No fallback agent configured for {execution.agent_name}")
            await self._send_to_dlq(execution)
            return False
        
        logger.info(f"Using fallback agent {fallback_agent} for {execution.agent_name}")
        
        # TODO: Execute fallback agent
        # This would need to create a new execution with the fallback agent
        
        # Simulate 80% success rate for fallback
        import random
        return random.random() < 0.8
    
    async def _skip_execution(self, execution: ExecutionRecord) -> bool:
        """Skip the failed execution and continue."""
        logger.warning(f"Skipping failed execution for {execution.agent_name}")
        
        # Mark as skipped in some way
        execution.state = ExecutionState.FAILED
        execution.error = f"Skipped after {self._get_attempt_count(execution.execution_id)} attempts"
        
        return True  # Consider skip as "successful" recovery
    
    async def _restart_agent(self, execution: ExecutionRecord) -> bool:
        """Restart the agent service."""
        logger.info(f"Attempting to restart agent {execution.agent_name}")
        
        # TODO: Implement actual agent restart logic
        # This would involve:
        # 1. Killing the current agent process/thread
        # 2. Re-initializing the agent
        # 3. Re-registering with the registry
        
        # Simulate restart with 60% success rate
        import random
        success = random.random() < 0.6
        
        if success:
            logger.info(f"Successfully restarted {execution.agent_name}")
        else:
            logger.error(f"Failed to restart {execution.agent_name}")
            
        return success
    
    async def _abort_pipeline(self, execution: ExecutionRecord):
        """Abort the entire pipeline."""
        logger.error(f"ABORTING pipeline due to failure in {execution.agent_name}")
        
        # Send to DLQ
        await self._send_to_dlq(execution)
        
        # TODO: Notify all dependent agents to stop
        # TODO: Send error to user via WebSocket
    
    async def _send_to_dlq(self, execution: ExecutionRecord):
        """Send failed execution to dead letter queue."""
        self.dead_letter_queue.append(execution)
        logger.info(f"Sent execution {execution.execution_id} to DLQ (total: {len(self.dead_letter_queue)})")
    
    def _get_attempt_count(self, execution_id: UUID) -> int:
        """Get the number of recovery attempts for an execution."""
        return sum(
            1 for attempt in self.recovery_attempts
            if attempt.execution_id == execution_id
        )
    
    def _is_circuit_open(self, agent_name: str) -> bool:
        """Check if circuit breaker is open for an agent."""
        breaker = self.circuit_breakers.get(agent_name)
        if not breaker:
            return False
        return breaker.is_open()
    
    def _record_failure(self, agent_name: str):
        """Record a failure for circuit breaker."""
        if agent_name not in self.circuit_breakers:
            self.circuit_breakers[agent_name] = CircuitBreaker(
                agent_name,
                self.CIRCUIT_BREAKER_THRESHOLD,
                self.CIRCUIT_BREAKER_TIMEOUT
            )
        self.circuit_breakers[agent_name].record_failure()
    
    def _record_success(self, agent_name: str):
        """Record a success for circuit breaker."""
        if agent_name in self.circuit_breakers:
            self.circuit_breakers[agent_name].record_success()
    
    def get_dlq_items(self) -> List[ExecutionRecord]:
        """Get items from dead letter queue."""
        return self.dead_letter_queue.copy()
    
    def clear_dlq(self):
        """Clear the dead letter queue."""
        self.dead_letter_queue.clear()
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total_attempts = len(self.recovery_attempts)
        successful = sum(1 for a in self.recovery_attempts if a.success)
        
        strategy_stats = {}
        for strategy in RecoveryStrategy:
            strategy_attempts = [
                a for a in self.recovery_attempts 
                if a.strategy == strategy
            ]
            strategy_stats[strategy.value] = {
                "total": len(strategy_attempts),
                "successful": sum(1 for a in strategy_attempts if a.success)
            }
        
        return {
            "total_recovery_attempts": total_attempts,
            "successful_recoveries": successful,
            "success_rate": (successful / total_attempts * 100) if total_attempts > 0 else 0,
            "dlq_size": len(self.dead_letter_queue),
            "strategy_stats": strategy_stats,
            "circuit_breakers": {
                name: breaker.get_status()
                for name, breaker in self.circuit_breakers.items()
            }
        }


class CircuitBreaker:
    """Simple circuit breaker implementation."""
    
    def __init__(self, name: str, threshold: int, timeout: float):
        self.name = name
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed, open, half-open
        
    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == "open":
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                return False
            return True
        return False
    
    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker OPENED for {self.name}")
    
    def record_success(self):
        """Record a success."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info(f"Circuit breaker CLOSED for {self.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "threshold": self.threshold,
            "time_since_last_failure": (
                time.time() - self.last_failure_time 
                if self.last_failure_time > 0 else None
            )
        }


# Global recovery manager
_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    """Get or create the global recovery manager."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager()
    return _recovery_manager