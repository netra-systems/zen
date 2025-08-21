"""Execution interfaces - Single source of truth.

Consolidated execution strategies merging enum-based types with strategy pattern
implementations for agent pipelines and LLM fallback execution.
Follows 450-line limit and 25-line functions.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionStrategy(Enum):
    """Execution strategies for agent pipelines and LLM operations."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    CIRCUIT_FALLBACK = "circuit_fallback"
    RETRY_EXECUTION = "retry_execution"


@dataclass
class AgentExecutionContext:
    """Context for agent execution with comprehensive tracking."""
    run_id: str
    thread_id: str
    user_id: str
    agent_name: str
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentExecutionResult:
    """Result of agent execution with detailed tracking."""
    success: bool
    state: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineStep:
    """Represents a step in an execution pipeline."""
    agent_name: str
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    condition: Optional[callable] = None
    dependencies: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionStrategyHandler(ABC):
    """Abstract strategy handler for different execution approaches."""
    
    @abstractmethod
    async def execute(self) -> Any:
        """Execute the strategy."""
        pass


class CircuitFallbackStrategy(ExecutionStrategyHandler):
    """Strategy for circuit breaker fallback execution."""
    
    def __init__(self, handler: 'LLMFallbackHandler', fallback_type: str):
        """Initialize circuit fallback strategy."""
        self.handler = handler
        self.fallback_type = fallback_type
    
    async def execute(self) -> Any:
        """Execute circuit fallback strategy."""
        return self.handler._create_fallback_response(self.fallback_type)


class RetryExecutionStrategy(ExecutionStrategyHandler):
    """Strategy for retry execution with comprehensive fallback."""
    
    def __init__(self, handler: 'LLMFallbackHandler', llm_operation, 
                 operation_name: str, circuit_breaker, provider: str, fallback_type: str):
        """Initialize retry execution strategy."""
        self.handler = handler
        self.llm_operation = llm_operation
        self.operation_name = operation_name
        self.circuit_breaker = circuit_breaker
        self.provider = provider
        self.fallback_type = fallback_type
    
    async def execute(self) -> Any:
        """Execute retry strategy with fallback handling."""
        return await self.handler._execute_with_retry(
            self.llm_operation, self.operation_name, self.circuit_breaker,
            self.provider, self.fallback_type
        )


class SequentialExecutionStrategy(ExecutionStrategyHandler):
    """Strategy for sequential execution of pipeline steps."""
    
    def __init__(self, steps: List[PipelineStep], context: AgentExecutionContext):
        """Initialize sequential execution strategy."""
        self.steps = steps
        self.context = context
        self.results: List[AgentExecutionResult] = []
    
    async def execute(self) -> List[AgentExecutionResult]:
        """Execute steps sequentially."""
        for step in self.steps:
            result = await self._execute_step(step)
            self.results.append(result)
            if not result.success and not self._should_continue_on_failure(step):
                break
        return self.results
    
    async def _execute_step(self, step: PipelineStep) -> AgentExecutionResult:
        """Execute a single pipeline step."""
        start_time = datetime.now()
        try:
            # Simplified step execution
            logger.info(f"Executing step: {step.agent_name}")
            await asyncio.sleep(0.1)  # Simulate execution
            duration = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(success=True, duration=duration)
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(success=False, error=str(e), duration=duration)
    
    def _should_continue_on_failure(self, step: PipelineStep) -> bool:
        """Determine if execution should continue after step failure."""
        return step.metadata.get('continue_on_failure', False)


class ParallelExecutionStrategy(ExecutionStrategyHandler):
    """Strategy for parallel execution of pipeline steps."""
    
    def __init__(self, steps: List[PipelineStep], context: AgentExecutionContext):
        """Initialize parallel execution strategy."""
        self.steps = steps
        self.context = context
    
    async def execute(self) -> List[AgentExecutionResult]:
        """Execute steps in parallel."""
        tasks = [self._execute_step_async(step) for step in self.steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_parallel_results(results)
    
    async def _execute_step_async(self, step: PipelineStep) -> AgentExecutionResult:
        """Execute a single step asynchronously."""
        start_time = datetime.now()
        try:
            logger.info(f"Executing step in parallel: {step.agent_name}")
            await asyncio.sleep(0.1)  # Simulate execution
            duration = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(success=True, duration=duration)
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(success=False, error=str(e), duration=duration)
    
    def _process_parallel_results(self, results: List) -> List[AgentExecutionResult]:
        """Process results from parallel execution."""
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(AgentExecutionResult(success=False, error=str(result)))
            else:
                processed_results.append(result)
        return processed_results


class ConditionalExecutionStrategy(ExecutionStrategyHandler):
    """Strategy for conditional execution based on step conditions."""
    
    def __init__(self, steps: List[PipelineStep], context: AgentExecutionContext):
        """Initialize conditional execution strategy."""
        self.steps = steps
        self.context = context
        self.results: List[AgentExecutionResult] = []
    
    async def execute(self) -> List[AgentExecutionResult]:
        """Execute steps based on their conditions."""
        for step in self.steps:
            if self._should_execute_step(step):
                result = await self._execute_conditional_step(step)
                self.results.append(result)
            else:
                self.results.append(self._create_skipped_result(step))
        return self.results
    
    def _should_execute_step(self, step: PipelineStep) -> bool:
        """Check if step condition is met."""
        if not step.condition:
            return True
        
        try:
            return step.condition(self.context, self.results)
        except Exception as e:
            logger.error(f"Error evaluating condition for {step.agent_name}: {e}")
            return False
    
    async def _execute_conditional_step(self, step: PipelineStep) -> AgentExecutionResult:
        """Execute a conditional step."""
        start_time = datetime.now()
        try:
            logger.info(f"Executing conditional step: {step.agent_name}")
            await asyncio.sleep(0.1)  # Simulate execution
            duration = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(success=True, duration=duration)
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(success=False, error=str(e), duration=duration)
    
    def _create_skipped_result(self, step: PipelineStep) -> AgentExecutionResult:
        """Create result for skipped step."""
        return AgentExecutionResult(
            success=True, duration=0.0,
            metadata={'skipped': True, 'reason': 'condition_not_met'}
        )


class RetryExecutor:
    """Handles retry execution logic with circuit breaker integration."""
    
    def __init__(self, handler: 'LLMFallbackHandler'):
        """Initialize retry executor."""
        self.handler = handler
    
    async def execute_operation(self, llm_operation, circuit_breaker, provider: str):
        """Execute operation with timeout and circuit breaker recording."""
        result = await asyncio.wait_for(llm_operation(), timeout=self.handler.config.timeout)
        self.handler._record_success(circuit_breaker, provider)
        return result
    
    async def handle_operation_failure(self, error: Exception, attempt: int,
                                     operation_name: str, circuit_breaker):
        """Handle operation failure with logging and circuit breaker recording."""
        failure_type = self.handler._classify_error(error)
        self.handler._record_retry_attempt(attempt, failure_type, str(error))
        if self.handler.config.use_circuit_breaker:
            circuit_breaker.record_failure(failure_type)
    
    async def wait_before_retry(self, attempt: int, error: Exception, operation_name: str):
        """Wait before retry with exponential backoff."""
        failure_type = self.handler._classify_error(error)
        delay = self.handler._calculate_delay(attempt, failure_type)
        logger.warning(f"Operation {operation_name} failed (attempt {attempt}): {error}. Retrying in {delay:.2f}s")
        await asyncio.sleep(delay)


class ExecutionStrategyFactory:
    """Factory for creating execution strategy instances."""
    
    @staticmethod
    def create_strategy(strategy: ExecutionStrategy, steps: List[PipelineStep],
                       context: AgentExecutionContext, **kwargs) -> ExecutionStrategyHandler:
        """Create strategy instance based on type."""
        if strategy == ExecutionStrategy.SEQUENTIAL:
            return SequentialExecutionStrategy(steps, context)
        elif strategy == ExecutionStrategy.PARALLEL:
            return ParallelExecutionStrategy(steps, context)
        elif strategy == ExecutionStrategy.CONDITIONAL:
            return ConditionalExecutionStrategy(steps, context)
        elif strategy == ExecutionStrategy.CIRCUIT_FALLBACK:
            handler = kwargs.get('handler')
            fallback_type = kwargs.get('fallback_type', 'default')
            return CircuitFallbackStrategy(handler, fallback_type)
        elif strategy == ExecutionStrategy.RETRY_EXECUTION:
            return RetryExecutionStrategy(
                kwargs.get('handler'), kwargs.get('llm_operation'),
                kwargs.get('operation_name'), kwargs.get('circuit_breaker'),
                kwargs.get('provider'), kwargs.get('fallback_type')
            )
        else:
            raise ValueError(f"Unknown execution strategy: {strategy}")
    
    @staticmethod
    def get_available_strategies() -> List[ExecutionStrategy]:
        """Get list of available execution strategies."""
        return list(ExecutionStrategy)


class StructuredFallbackBuilder:
    """Builder pattern for creating structured fallbacks with schema validation."""
    
    def __init__(self, schema):
        """Initialize builder with schema."""
        self.schema = schema
        self.field_defaults = {}
    
    def build_field_defaults(self):
        """Build default values for schema fields."""
        for field_name, field_info in self.schema.model_fields.items():
            self._set_field_default(field_name, field_info)
        return self
    
    def build(self):
        """Build the structured fallback instance."""
        try:
            return self.schema(**self.field_defaults)
        except Exception as e:
            logger.error(f"Failed to create structured fallback for {self.schema.__name__}: {e}")
            return self._create_empty_fallback()
    
    def _set_field_default(self, field_name: str, field_info):
        """Set default value for a specific field."""
        if field_info.default is not None:
            self.field_defaults[field_name] = field_info.default
        else:
            self.field_defaults[field_name] = self._get_type_default(field_info.annotation)
    
    def _get_type_default(self, annotation):
        """Get default value based on type annotation."""
        # Simplified type default mapping
        type_defaults = {
            str: "", int: 0, float: 0.0, bool: False,
            list: [], dict: {}, tuple: ()
        }
        return type_defaults.get(annotation, None)
    
    def _create_empty_fallback(self):
        """Create empty fallback instance as last resort."""
        try:
            return self.schema()
        except Exception:
            raise ValueError(f"Cannot create fallback instance for {self.schema.__name__}")


class ExecutionPipelineManager:
    """Manages execution pipelines with strategy selection."""
    
    def __init__(self):
        """Initialize pipeline manager."""
        self.active_pipelines: Dict[str, Any] = {}
        self.strategy_factory = ExecutionStrategyFactory()
    
    async def execute_pipeline(self, pipeline_id: str, steps: List[PipelineStep],
                              strategy: ExecutionStrategy, context: AgentExecutionContext) -> List[AgentExecutionResult]:
        """Execute pipeline with specified strategy."""
        self.active_pipelines[pipeline_id] = {
            'steps': steps, 'strategy': strategy, 'context': context,
            'started_at': datetime.now()
        }
        
        try:
            strategy_handler = self.strategy_factory.create_strategy(strategy, steps, context)
            results = await strategy_handler.execute()
            self._cleanup_pipeline(pipeline_id)
            return results
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} execution failed: {e}")
            self._cleanup_pipeline(pipeline_id)
            raise
    
    def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Clean up completed pipeline."""
        self.active_pipelines.pop(pipeline_id, None)
    
    def get_active_pipeline_count(self) -> int:
        """Get count of active pipelines."""
        return len(self.active_pipelines)
    
    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific pipeline."""
        return self.active_pipelines.get(pipeline_id)