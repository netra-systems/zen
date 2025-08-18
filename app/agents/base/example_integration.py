"""Example Agent Integration with Base Execution Interface

Shows how to refactor existing agents to use the standardized execution system.
This example demonstrates integration patterns for the TriageSubAgent.

Business Value: Template for updating 40+ agents to use standardized patterns.
"""

from typing import Dict, Any, Optional
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.redis_manager import RedisManager
from app.core.reliability import CircuitBreakerConfig, RetryConfig

# Import the new base execution system
from app.agents.base import (
    BaseExecutionInterface, BaseExecutionEngine, ExecutionMonitor,
    ReliabilityManager, ExecutionContext, ExecutionResult
)
from app.agents.base.errors import ValidationError, ExternalServiceError


class ModernTriageSubAgent(BaseExecutionInterface):
    """Example of TriageSubAgent refactored to use base execution interface.
    
    Demonstrates how to:
    - Implement standardized execution patterns
    - Use centralized error handling
    - Integrate monitoring and reliability
    - Maintain backward compatibility
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 redis_manager: Optional[RedisManager] = None):
        super().__init__("TriageSubAgent")
        self._init_core_components(llm_manager, tool_dispatcher, redis_manager)
        self._init_execution_system()
        
    def _init_core_components(self, llm_manager: LLMManager, 
                            tool_dispatcher: ToolDispatcher,
                            redis_manager: Optional[RedisManager]) -> None:
        """Initialize core agent components."""
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager
        self.cache_ttl = 3600
        
    def _init_execution_system(self) -> None:
        """Initialize standardized execution system."""
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        self._setup_execution_components(circuit_config, retry_config)
        
    def _create_circuit_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=30.0, name="TriageSubAgent"
        )
        
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0)
        
    def _setup_execution_components(self, circuit_config: CircuitBreakerConfig, 
                                   retry_config: RetryConfig) -> None:
        """Setup execution system components."""
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.monitor = ExecutionMonitor()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
    
    # Implement the abstract methods from BaseExecutionInterface
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate triage execution preconditions."""
        # Check if we have a user request to triage
        if not context.state.user_request:
            return False
        
        # Validate request format
        if len(context.state.user_request.strip()) < 3:
            raise ValidationError("User request too short for triage")
        
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute triage-specific core logic."""
        user_request = context.state.user_request
        await self.send_status_update(context, "analyzing", "Analyzing user request...")
        
        cached_result = await self._try_cache_retrieval(context, user_request)
        if cached_result:
            return cached_result
            
        return await self._perform_full_triage(context, user_request)
        
    async def _try_cache_retrieval(self, context: ExecutionContext, 
                                  user_request: str) -> Optional[Dict[str, Any]]:
        """Try to retrieve cached triage result."""
        cached_result = await self._check_triage_cache(user_request)
        if cached_result:
            await self.send_status_update(context, "cached", "Using cached triage result")
            return cached_result
        return None
        
    async def _perform_full_triage(self, context: ExecutionContext, 
                                  user_request: str) -> Dict[str, Any]:
        """Perform full triage analysis."""
        await self.send_status_update(context, "processing", "Processing with LLM...")
        triage_result = await self._perform_llm_triage(user_request)
        await self._cache_triage_result(user_request, triage_result)
        enriched_result = await self._enrich_triage_result(triage_result, context)
        await self.send_status_update(context, "completed", "Triage analysis complete")
        return enriched_result
    
    # New standardized execute method using the base execution engine
    
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> None:
        """Execute triage with standardized execution engine."""
        context = self._create_execution_context(state, run_id, stream_updates)
        result = await self.execution_engine.execute(self, context)
        self._set_execution_result(state, result)
        
    def _create_execution_context(self, state: DeepAgentState, run_id: str,
                                 stream_updates: bool) -> ExecutionContext:
        """Create execution context for triage."""
        context_params = self._get_context_params(state, run_id, stream_updates)
        return ExecutionContext(**context_params)
        
    def _get_context_params(self, state: DeepAgentState, run_id: str, 
                           stream_updates: bool) -> Dict[str, Any]:
        """Get execution context parameters."""
        return {
            'run_id': run_id, 'agent_name': self.agent_name, 'state': state, 'stream_updates': stream_updates,
            'thread_id': getattr(state, 'chat_thread_id', None), 'user_id': getattr(state, 'user_id', None)
        }
        
    def _set_execution_result(self, state: DeepAgentState, 
                             result: ExecutionResult) -> None:
        """Set execution result in agent state."""
        if result.success:
            state.triage_result = result.result
        else:
            state.triage_result = self._create_failure_result(result)
            
    def _create_failure_result(self, result: ExecutionResult) -> Dict[str, Any]:
        """Create failure result dictionary."""
        return {
            "status": "failed",
            "error": result.error,
            "fallback_used": result.fallback_used
        }
    
    # Private implementation methods
    
    async def _check_triage_cache(self, user_request: str) -> Optional[Dict[str, Any]]:
        """Check cache for existing triage result."""
        if not self.redis_manager:
            return None
        
        try:
            cache_key = f"triage:{hash(user_request)}"
            cached_data = await self.redis_manager.get(cache_key)
            return cached_data if cached_data else None
        except Exception:
            # Cache failure shouldn't break execution
            return None
    
    async def _perform_llm_triage(self, user_request: str) -> Dict[str, Any]:
        """Perform LLM-based triage analysis."""
        try:
            prompt = self._build_triage_prompt(user_request)
            llm_response = await self.llm_manager.ask_llm(prompt, "default")
            return self._parse_llm_response(llm_response)
        except Exception as e:
            raise ExternalServiceError(f"LLM triage failed: {str(e)}")
    
    def _build_triage_prompt(self, user_request: str) -> str:
        """Build enhanced triage prompt."""
        template = self._get_triage_prompt_template()
        return template.format(user_request=user_request)
        
    def _get_triage_prompt_template(self) -> str:
        """Get triage prompt template."""
        return ("Analyze this user request and categorize it:\n\nRequest: {user_request}\n\n"
                "Provide a JSON response with:\n- category: The primary category\n"
                "- confidence: Confidence score (0-1)\n- suggested_tools: Array of recommended tools\n"
                "- reasoning: Brief explanation")
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse and validate LLM response."""
        import json
        result = json.loads(llm_response)
        self._validate_llm_result_fields(result)
        return result
            
    def _validate_llm_result_fields(self, result: Dict[str, Any]) -> None:
        """Validate required fields in LLM result."""
        required_fields = ["category", "confidence", "suggested_tools"]
        for field in required_fields:
            if field not in result:
                raise ValidationError(f"Missing required field: {field}")
    
    async def _cache_triage_result(self, user_request: str, 
                                 result: Dict[str, Any]) -> None:
        """Cache triage result for future use."""
        if not self.redis_manager:
            return
        
        try:
            cache_key = f"triage:{hash(user_request)}"
            await self.redis_manager.set(cache_key, result, ex=self.cache_ttl)
        except Exception:
            # Cache failure shouldn't break execution
            pass
    
    async def _enrich_triage_result(self, triage_result: Dict[str, Any],
                                  context: ExecutionContext) -> Dict[str, Any]:
        """Enrich triage result with metadata."""
        triage_result["metadata"] = {
            "run_id": context.run_id,
            "agent_name": context.agent_name,
            "timestamp": context.start_time,
            "retry_count": context.retry_count
        }
        
        return triage_result
    
    # Health and monitoring methods
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive agent health status."""
        base_status = self._get_base_health_info()
        component_status = self._get_component_health_info()
        return {**base_status, **component_status}
        
    def _get_base_health_info(self) -> Dict[str, Any]:
        """Get base agent health information."""
        return {
            "agent_name": self.agent_name,
            "cache_available": self.redis_manager is not None
        }
        
    def _get_component_health_info(self) -> Dict[str, Any]:
        """Get component health information."""
        return {
            "execution_engine": self.execution_engine.get_health_status(),
            "reliability": self.reliability_manager.get_health_status(),
            "monitor": self.monitor.get_health_status()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return self.monitor.get_agent_performance_stats(self.agent_name)
    
    # Backward compatibility methods
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Backward compatibility method."""
        context = ExecutionContext(run_id=run_id, agent_name=self.agent_name, state=state)
        return await self.validate_preconditions(context)
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution."""
        # Any cleanup logic can be added here
        pass


# Factory function for creating modernized agents
def create_modern_agent(agent_class, *args, **kwargs):
    """Factory function to create agents with standardized execution."""
    _validate_agent_class(agent_class)
    return _instantiate_agent(agent_class, *args, **kwargs)
    
def _validate_agent_class(agent_class) -> None:
    """Validate agent class inheritance."""
    if not issubclass(agent_class, BaseExecutionInterface):
        raise ValueError(f"Agent class {agent_class.__name__} must inherit from BaseExecutionInterface")
        
def _instantiate_agent(agent_class, *args, **kwargs):
    """Instantiate agent with error handling."""
    try:
        return agent_class(*args, **kwargs)
    except Exception as e:
        raise ValueError(f"Failed to create modern agent: {str(e)}")


# Migration helper functions
def migrate_agent_to_base_interface(legacy_agent_class):
    """Helper to migrate legacy agents to use base interface."""
    from typing import Type, get_type_hints
    
    if issubclass(legacy_agent_class, BaseExecutionInterface):
        return legacy_agent_class
    _validate_legacy_agent(legacy_agent_class)
    return _create_migrated_agent_wrapper(legacy_agent_class)
    
def _validate_legacy_agent(legacy_agent_class) -> None:
    """Validate legacy agent has required methods."""
    if not hasattr(legacy_agent_class, 'execute'):
        raise ValueError(f"Legacy agent {legacy_agent_class.__name__} must have execute method")
        
def _create_migrated_agent_wrapper(legacy_agent_class):
    """Create wrapper class for legacy agent."""
    return _build_migrated_agent_class(legacy_agent_class)
    
def _build_migrated_agent_class(legacy_agent_class):
    """Build the migrated agent class definition."""
    return type('MigratedAgent', (BaseExecutionInterface,), {
        '__init__': lambda self, *a, **kw: (super(type(self), self).__init__(legacy_agent_class.__name__), setattr(self, 'legacy_agent', legacy_agent_class(*a, **kw)))[1],
        'validate_preconditions': lambda self, ctx: _check_legacy_preconditions(self.legacy_agent, ctx),
        'execute_core_logic': lambda self, ctx: _execute_legacy_logic(self.legacy_agent, ctx, legacy_agent_class)
    })
    
async def _check_legacy_preconditions(legacy_agent, context: ExecutionContext) -> bool:
    """Check preconditions for legacy agent."""
    if hasattr(legacy_agent, 'check_entry_conditions'):
        return await legacy_agent.check_entry_conditions(context.state, context.run_id)
    return True
    
async def _execute_legacy_logic(legacy_agent, context: ExecutionContext, 
                               legacy_class) -> Dict[str, Any]:
    """Execute legacy agent logic."""
    await legacy_agent.execute(context.state, context.run_id, context.stream_updates)
    return {"migrated": True, "agent": legacy_class.__name__}


class AgentMigrationGuide:
    """Migration guide for updating existing agents.
    
    Step-by-step process:
    1. Inherit from BaseExecutionInterface instead of BaseSubAgent
    2. Implement validate_preconditions() and execute_core_logic()
    3. Initialize execution system in __init__
    4. Update execute() method to use execution engine
    5. Add health and monitoring methods
    6. Maintain backward compatibility methods
    """
    
    @staticmethod
    def get_migration_checklist() -> Dict[str, str]:
        """Get migration checklist for agents."""
        return {
            **_get_inheritance_steps(),
            **_get_implementation_steps(),
            **_get_validation_steps()
        }
    
    @staticmethod
    def get_performance_benefits() -> Dict[str, str]:
        """Get expected performance benefits from migration."""
        return {
            **_get_reliability_benefits(),
            **_get_system_benefits()
        }

        
def _get_inheritance_steps() -> Dict[str, str]:
    """Get inheritance migration steps."""
    return {
        "inherit_base_interface": "Change inheritance to BaseExecutionInterface",
        "implement_abstract_methods": "Implement validate_preconditions() and execute_core_logic()"
    }
    
def _get_implementation_steps() -> Dict[str, str]:
    """Get implementation migration steps."""
    return {
        "init_execution_system": "Initialize reliability manager, monitor, and execution engine",
        "update_execute_method": "Use execution engine for execute() method",
        "add_health_methods": "Add get_health_status() and get_performance_metrics()"
    }
    
def _get_validation_steps() -> Dict[str, str]:
    """Get validation migration steps."""
    return {
        "maintain_compatibility": "Keep existing public methods for backward compatibility",
        "test_integration": "Run comprehensive tests to validate integration"
    }

def _get_reliability_benefits() -> Dict[str, str]:
    """Get reliability performance benefits."""
    return {
        "error_handling": "Structured error handling with fallback strategies",
        "monitoring": "Comprehensive performance and health monitoring",
        "reliability": "Circuit breaker and retry patterns for resilience"
    }
    
def _get_system_benefits() -> Dict[str, str]:
    """Get system performance benefits."""
    return {
        "consistency": "Standardized execution patterns across all agents",
        "maintainability": "Centralized improvements benefit all agents",
        "scalability": "Better resource management and rate limiting"
    }