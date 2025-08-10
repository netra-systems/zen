"""Agent Orchestrator

Manages agent execution with proper separation of concerns, error recovery, and circuit breakers.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from app.logging_config import central_logger
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState

logger = central_logger.get_logger(__name__)

class ExecutionStrategy(Enum):
    """Agent execution strategies"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class AgentExecutionContext:
    """Context for agent execution"""
    agent_name: str
    run_id: str
    user_id: str
    thread_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class CircuitBreaker:
    """Circuit breaker for agent failure handling"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    
    def record_success(self) -> None:
        """Record successful execution"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failures = 0
                self.half_open_calls = 0
                logger.info("Circuit breaker closed after successful half-open period")
    
    def record_failure(self) -> None:
        """Record failed execution"""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker opened after failure in half-open state")
        elif self.failures >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failures} failures")
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False
        
        return self.state == CircuitBreakerState.HALF_OPEN

class AgentOrchestrator:
    """Orchestrates agent execution with advanced patterns"""
    
    def __init__(self):
        self.agents: Dict[str, BaseSubAgent] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.execution_history: List[AgentExecutionContext] = []
        self.hooks: Dict[str, List[Callable]] = {
            "before_agent": [],
            "after_agent": [],
            "on_error": [],
            "on_retry": []
        }
    
    def register_agent(self, name: str, agent: BaseSubAgent) -> None:
        """Register an agent"""
        self.agents[name] = agent
        self.circuit_breakers[name] = CircuitBreaker()
        logger.info(f"Registered agent: {name}")
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """Register event hook"""
        if event in self.hooks:
            self.hooks[event].append(callback)
            logger.info(f"Registered hook for event: {event}")
    
    async def execute_sequential(self, 
                                state: DeepAgentState,
                                agent_names: List[str],
                                context: AgentExecutionContext) -> DeepAgentState:
        """Execute agents sequentially"""
        for agent_name in agent_names:
            if agent_name not in self.agents:
                raise ValueError(f"Agent {agent_name} not registered")
            
            await self._execute_agent(agent_name, state, context)
        
        return state
    
    async def execute_parallel(self,
                              state: DeepAgentState,
                              agent_names: List[str],
                              context: AgentExecutionContext) -> DeepAgentState:
        """Execute agents in parallel"""
        tasks = []
        for agent_name in agent_names:
            if agent_name not in self.agents:
                raise ValueError(f"Agent {agent_name} not registered")
            
            task = asyncio.create_task(
                self._execute_agent(agent_name, state.copy(), context)
            )
            tasks.append((agent_name, task))
        
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (agent_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_name} failed: {result}")
            else:
                self._merge_state(state, result)
        
        return state
    
    async def execute_pipeline(self,
                              state: DeepAgentState,
                              pipeline: List[Dict[str, Any]],
                              context: AgentExecutionContext) -> DeepAgentState:
        """Execute agents in a pipeline with conditions"""
        for stage in pipeline:
            agent_name = stage["agent"]
            condition = stage.get("condition")
            
            if condition and not await self._evaluate_condition(condition, state):
                logger.info(f"Skipping agent {agent_name} due to condition")
                continue
            
            await self._execute_agent(agent_name, state, context)
        
        return state
    
    async def _execute_agent(self,
                           agent_name: str,
                           state: DeepAgentState,
                           context: AgentExecutionContext) -> DeepAgentState:
        """Execute a single agent with error handling"""
        agent = self.agents[agent_name]
        circuit_breaker = self.circuit_breakers[agent_name]
        
        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for agent {agent_name}, skipping")
            return state
        
        exec_context = AgentExecutionContext(
            agent_name=agent_name,
            run_id=context.run_id,
            user_id=context.user_id,
            thread_id=context.thread_id
        )
        
        try:
            await self._run_hooks("before_agent", exec_context, state)
            
            logger.info(f"Executing agent: {agent_name}")
            await agent.execute(state, context.run_id, stream_updates=True)
            
            circuit_breaker.record_success()
            exec_context.completed_at = datetime.utcnow()
            exec_context.result = state
            
            await self._run_hooks("after_agent", exec_context, state)
            
            self.execution_history.append(exec_context)
            return state
            
        except Exception as e:
            circuit_breaker.record_failure()
            exec_context.error = str(e)
            
            logger.error(f"Agent {agent_name} failed: {e}")
            await self._run_hooks("on_error", exec_context, state)
            
            if exec_context.retry_count < exec_context.max_retries:
                exec_context.retry_count += 1
                await self._run_hooks("on_retry", exec_context, state)
                
                await asyncio.sleep(2 ** exec_context.retry_count)
                return await self._execute_agent(agent_name, state, context)
            
            self.execution_history.append(exec_context)
            raise
    
    async def _evaluate_condition(self, condition: Dict[str, Any], state: DeepAgentState) -> bool:
        """Evaluate execution condition"""
        condition_type = condition.get("type")
        
        if condition_type == "has_data":
            field = condition.get("field")
            return getattr(state, field) is not None
        
        elif condition_type == "custom":
            func = condition.get("function")
            return await func(state) if asyncio.iscoroutinefunction(func) else func(state)
        
        return True
    
    def _merge_state(self, target: DeepAgentState, source: DeepAgentState) -> None:
        """Merge state from parallel execution"""
        for field in source.__fields__:
            source_value = getattr(source, field)
            if source_value is not None:
                setattr(target, field, source_value)
    
    async def _run_hooks(self, event: str, context: AgentExecutionContext, state: DeepAgentState) -> None:
        """Run registered hooks"""
        for hook in self.hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context, state)
                else:
                    hook(context, state)
            except Exception as e:
                logger.error(f"Hook error for event {event}: {e}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        stats = {
            "total_executions": len(self.execution_history),
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "by_agent": {},
            "circuit_breakers": {}
        }
        
        for context in self.execution_history:
            if context.error:
                stats["failed"] += 1
            else:
                stats["successful"] += 1
            
            if context.retry_count > 0:
                stats["retried"] += 1
            
            agent_stats = stats["by_agent"].get(context.agent_name, {
                "executions": 0,
                "failures": 0,
                "avg_duration": 0
            })
            
            agent_stats["executions"] += 1
            if context.error:
                agent_stats["failures"] += 1
            
            if context.completed_at and context.started_at:
                duration = (context.completed_at - context.started_at).total_seconds()
                agent_stats["avg_duration"] = (
                    (agent_stats["avg_duration"] * (agent_stats["executions"] - 1) + duration) /
                    agent_stats["executions"]
                )
            
            stats["by_agent"][context.agent_name] = agent_stats
        
        for name, breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][name] = {
                "state": breaker.state.value,
                "failures": breaker.failures
            }
        
        return stats