"""Legacy Execution Engine Adapter - SSOT Migration Support

This module provides adapters to wrap legacy execution engine implementations
and make them compatible with the consolidated execution engine interface.

Purpose:
- Enable zero-breaking-change migration from legacy to consolidated engines
- Provide backward compatibility during SSOT consolidation
- Maintain Golden Path functionality during transition
- Support gradual migration of 100+ execution engine usages

Business Value:
- Protects $500K+ ARR dependent on execution engine stability
- Enables safe SSOT consolidation without service disruption
- Reduces migration risk through incremental transition approach
"""

from __future__ import annotations

import asyncio
import warnings
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.execution_engine_interface import (
    IExecutionEngine,
    ExecutionEngineAdapter,
    ExecutionEngineCapabilities
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorExecutionEngineAdapter(ExecutionEngineAdapter, IExecutionEngine):
    """Adapter for SupervisorExecutionEngine to IExecutionEngine interface.
    
    This adapter wraps the legacy SupervisorExecutionEngine and provides
    the standard IExecutionEngine interface while maintaining all existing
    functionality and behavior.
    
    Migration Path:
    1. Wrap existing SupervisorExecutionEngine instances with this adapter
    2. Replace adapter usage with ConsolidatedExecutionEngine over time
    3. Remove adapter once all usages migrated
    """
    
    def __init__(self, supervisor_engine: Any):
        """Initialize adapter for SupervisorExecutionEngine.
        
        Args:
            supervisor_engine: Instance of SupervisorExecutionEngine to wrap
        """
        # Define capabilities of SupervisorExecutionEngine
        capabilities = ExecutionEngineCapabilities(
            supports_user_context=True,
            supports_pipelines=True,
            supports_websocket_events=True,
            supports_concurrent_users=True,
            supports_request_scoping=False,  # Legacy doesn't have request scoping
            max_concurrent_executions=10,
            execution_timeout_seconds=30.0,
            features=['user_isolation', 'websocket_events', 'pipeline_execution', 'timeout_handling']
        )
        
        super().__init__(supervisor_engine, capabilities)
        
        logger.info(f"Created SupervisorExecutionEngineAdapter wrapping {type(supervisor_engine).__name__}")
    
    async def execute_agent(
        self,
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> AgentExecutionResult:
        """Execute agent using wrapped SupervisorExecutionEngine.
        
        Args:
            context: Agent execution context
            user_context: Optional user context for isolation
            
        Returns:
            AgentExecutionResult from the wrapped engine
        """
        logger.debug(f"SupervisorAdapter executing agent: {context.agent_name}")
        
        try:
            # Use the adapter's method which handles initialization
            return await self.execute_agent_adapted(context, user_context)
        except Exception as e:
            logger.error(f"SupervisorAdapter execution failed for {context.agent_name}: {e}")
            # Return error result instead of raising to maintain interface contract
            return AgentExecutionResult(
                success=False,
                agent_name=context.agent_name,
                error=str(e),
                duration=0.0
            )
    
    async def execute_pipeline(
        self,
        steps: List[PipelineStep],
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> List[AgentExecutionResult]:
        """Execute pipeline using wrapped SupervisorExecutionEngine.
        
        Args:
            steps: Pipeline steps to execute
            context: Base execution context
            user_context: Optional user context for isolation
            
        Returns:
            List of AgentExecutionResult from pipeline execution
        """
        logger.debug(f"SupervisorAdapter executing pipeline with {len(steps)} steps")
        
        try:
            return await self.execute_pipeline_adapted(steps, context, user_context)
        except Exception as e:
            logger.error(f"SupervisorAdapter pipeline execution failed: {e}")
            # Return error results for all steps
            return [
                AgentExecutionResult(
                    success=False,
                    agent_name=step.agent_name,
                    error=f"Pipeline execution failed: {e}",
                    duration=0.0
                )
                for step in steps
            ]
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics from wrapped engine.
        
        Returns:
            Dictionary containing execution metrics and performance data
        """
        return await self.get_execution_stats_adapted()
    
    async def shutdown(self) -> None:
        """Shutdown the wrapped SupervisorExecutionEngine.
        
        Performs cleanup and resource release for the wrapped engine.
        """
        logger.info("Shutting down SupervisorExecutionEngineAdapter")
        await self.shutdown_adapted()
    
    def get_engine_type(self) -> str:
        """Get engine type identifier."""
        return f"SupervisorAdapter({type(self.wrapped_engine).__name__})"
    
    def has_user_context_support(self) -> bool:
        """Check if wrapped engine supports user context."""
        return self.capabilities.supports_user_context


class ConsolidatedExecutionEngineWrapper(IExecutionEngine):
    """Wrapper for ConsolidatedExecutionEngine to ensure interface compliance.
    
    This wrapper ensures the ConsolidatedExecutionEngine properly implements
    the IExecutionEngine interface and provides any missing methods.
    
    Note: ConsolidatedExecutionEngine should already implement the interface,
    this wrapper is for safety and interface guarantee during transition.
    """
    
    def __init__(self, consolidated_engine: Any):
        """Initialize wrapper for ConsolidatedExecutionEngine.
        
        Args:
            consolidated_engine: Instance of ConsolidatedExecutionEngine to wrap
        """
        self.consolidated_engine = consolidated_engine
        logger.info(f"Created ConsolidatedExecutionEngineWrapper wrapping {type(consolidated_engine).__name__}")
    
    async def execute_agent(
        self,
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> AgentExecutionResult:
        """Execute agent using ConsolidatedExecutionEngine.
        
        Args:
            context: Agent execution context
            user_context: Optional user context for isolation
            
        Returns:
            AgentExecutionResult from consolidated engine
        """
        # ConsolidatedExecutionEngine uses 'execute' method
        return await self.consolidated_engine.execute(
            context.agent_name,
            context,  # Pass full context as task
            user_context
        )
    
    async def execute_pipeline(
        self,
        steps: List[PipelineStep],
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> List[AgentExecutionResult]:
        """Execute pipeline using ConsolidatedExecutionEngine.
        
        ConsolidatedExecutionEngine doesn't have built-in pipeline support,
        so we execute steps sequentially.
        
        Args:
            steps: Pipeline steps to execute
            context: Base execution context
            user_context: Optional user context for isolation
            
        Returns:
            List of AgentExecutionResult from pipeline execution
        """
        results = []
        
        for step in steps:
            # Create context for this step
            step_context = AgentExecutionContext(
                run_id=context.run_id,
                thread_id=context.thread_id,
                user_id=context.user_id,
                agent_name=step.agent_name,
                prompt=context.prompt,
                user_input=context.user_input,
                metadata=step.metadata
            )
            
            # Execute step
            result = await self.execute_agent(step_context, user_context)
            results.append(result)
            
            # Stop on failure unless continue_on_error is set
            if not result.success and not step.metadata.get('continue_on_error', False):
                break
        
        return results
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics from ConsolidatedExecutionEngine.
        
        Returns:
            Dictionary containing execution metrics and performance data
        """
        if hasattr(self.consolidated_engine, 'get_metrics'):
            stats = self.consolidated_engine.get_metrics()
            # Add wrapper identification
            stats['wrapper_type'] = 'ConsolidatedExecutionEngineWrapper'
            return stats
        else:
            return {
                'engine_type': type(self.consolidated_engine).__name__,
                'wrapper_type': 'ConsolidatedExecutionEngineWrapper',
                'stats_available': False
            }
    
    async def shutdown(self) -> None:
        """Shutdown the ConsolidatedExecutionEngine.
        
        Performs cleanup and resource release.
        """
        logger.info("Shutting down ConsolidatedExecutionEngineWrapper")
        if hasattr(self.consolidated_engine, 'cleanup'):
            await self.consolidated_engine.cleanup()
    
    async def initialize(self) -> None:
        """Initialize the ConsolidatedExecutionEngine if needed."""
        if hasattr(self.consolidated_engine, 'initialize'):
            await self.consolidated_engine.initialize()
    
    def get_engine_type(self) -> str:
        """Get engine type identifier."""
        return f"ConsolidatedWrapper({type(self.consolidated_engine).__name__})"
    
    def has_user_context_support(self) -> bool:
        """ConsolidatedExecutionEngine supports user context."""
        return True


class ExecutionEngineFactory:
    """Unified factory for creating execution engines with proper adapters.
    
    This factory automatically wraps legacy engines with appropriate adapters
    and ensures all engines implement the IExecutionEngine interface.
    
    Migration Strategy:
    1. Factory detects engine type and applies appropriate adapter
    2. Gradually replace legacy engine creation with consolidated engine
    3. Remove adapters once migration is complete
    """
    
    @staticmethod
    def create_adapted_engine(engine: Any) -> IExecutionEngine:
        """Create an adapted execution engine from any engine implementation.
        
        Args:
            engine: Any execution engine implementation
            
        Returns:
            IExecutionEngine: Adapted engine implementing standard interface
            
        Raises:
            ValueError: If engine type is not supported
        """
        engine_type = type(engine).__name__
        engine_module = type(engine).__module__
        
        logger.info(f"Creating adapted engine for {engine_module}.{engine_type}")
        
        # Check if already implements interface
        if isinstance(engine, IExecutionEngine):
            logger.debug(f"Engine {engine_type} already implements IExecutionEngine")
            return engine
        
        # Detect legacy SupervisorExecutionEngine
        if 'supervisor.execution_engine' in engine_module and 'ExecutionEngine' in engine_type:
            logger.info(f"Adapting SupervisorExecutionEngine: {engine_type}")
            return SupervisorExecutionEngineAdapter(engine)
        
        # Detect ConsolidatedExecutionEngine
        if 'execution_engine_consolidated' in engine_module and 'ExecutionEngine' in engine_type:
            logger.info(f"Wrapping ConsolidatedExecutionEngine: {engine_type}")
            return ConsolidatedExecutionEngineWrapper(engine)
        
        # Unknown engine type - emit warning and try generic adapter
        warnings.warn(
            f"Unknown execution engine type: {engine_module}.{engine_type}. "
            f"Using generic adapter which may not work correctly. "
            f"Consider adding specific adapter implementation.",
            UserWarning,
            stacklevel=2
        )
        
        # Generic adapter as fallback
        return GenericExecutionEngineAdapter(engine)
    
    @classmethod
    def ensure_interface_compliance(cls, engine: Any) -> IExecutionEngine:
        """Ensure an execution engine complies with IExecutionEngine interface.
        
        Args:
            engine: Execution engine to check/adapt
            
        Returns:
            IExecutionEngine: Interface-compliant execution engine
        """
        if isinstance(engine, IExecutionEngine):
            return engine
        else:
            return cls.create_adapted_engine(engine)


class GenericExecutionEngineAdapter(ExecutionEngineAdapter, IExecutionEngine):
    """Generic adapter for unknown execution engine types.
    
    This adapter provides basic interface compliance for execution engines
    that don't have specific adapters. It makes best-effort attempts to
    delegate to the wrapped engine's methods.
    
    Warning: This is a fallback adapter and may not work correctly with
    all engine types. Specific adapters should be created for known engines.
    """
    
    def __init__(self, engine: Any):
        """Initialize generic adapter.
        
        Args:
            engine: Any execution engine to adapt
        """
        # Define minimal capabilities for unknown engines
        capabilities = ExecutionEngineCapabilities(
            supports_user_context=False,  # Conservative assumption
            supports_pipelines=False,     # Conservative assumption
            supports_websocket_events=False,  # Conservative assumption
            supports_concurrent_users=False,  # Conservative assumption
            supports_request_scoping=False,
            max_concurrent_executions=1,  # Conservative limit
            execution_timeout_seconds=30.0,
            features=[]
        )
        
        super().__init__(engine, capabilities)
        
        # Try to detect capabilities from wrapped engine
        self._detect_capabilities()
        
        logger.warning(
            f"Created GenericExecutionEngineAdapter for {type(engine).__name__}. "
            f"Consider creating a specific adapter for better compatibility."
        )
    
    def _detect_capabilities(self) -> None:
        """Attempt to detect capabilities of the wrapped engine."""
        # Check for common method names to infer capabilities
        if hasattr(self.wrapped_engine, 'execute_pipeline'):
            self.capabilities.supports_pipelines = True
            self.capabilities.features.append('pipeline_support_detected')
        
        if hasattr(self.wrapped_engine, 'user_context') or 'user' in str(type(self.wrapped_engine)).lower():
            self.capabilities.supports_user_context = True
            self.capabilities.features.append('user_context_support_detected')
        
        if hasattr(self.wrapped_engine, 'websocket') or 'websocket' in str(type(self.wrapped_engine)).lower():
            self.capabilities.supports_websocket_events = True
            self.capabilities.features.append('websocket_support_detected')
    
    async def execute_agent(
        self,
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> AgentExecutionResult:
        """Execute agent using generic adaptation."""
        logger.debug(f"GenericAdapter executing agent: {context.agent_name}")
        
        try:
            return await self.execute_agent_adapted(context, user_context)
        except Exception as e:
            logger.error(f"GenericAdapter execution failed for {context.agent_name}: {e}")
            return AgentExecutionResult(
                success=False,
                agent_name=context.agent_name,
                error=f"Generic adapter execution failed: {e}",
                duration=0.0
            )
    
    async def execute_pipeline(
        self,
        steps: List[PipelineStep],
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> List[AgentExecutionResult]:
        """Execute pipeline using generic adaptation."""
        logger.debug(f"GenericAdapter executing pipeline with {len(steps)} steps")
        
        try:
            return await self.execute_pipeline_adapted(steps, context, user_context)
        except Exception as e:
            logger.error(f"GenericAdapter pipeline execution failed: {e}")
            return [
                AgentExecutionResult(
                    success=False,
                    agent_name=step.agent_name,
                    error=f"Generic adapter pipeline failed: {e}",
                    duration=0.0
                )
                for step in steps
            ]
    
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics using generic adaptation."""
        return await self.get_execution_stats_adapted()
    
    async def shutdown(self) -> None:
        """Shutdown using generic adaptation."""
        logger.info("Shutting down GenericExecutionEngineAdapter")
        await self.shutdown_adapted()
    
    def get_engine_type(self) -> str:
        """Get engine type identifier."""
        return f"GenericAdapter({type(self.wrapped_engine).__name__})"
    
    def has_user_context_support(self) -> bool:
        """Check if wrapped engine supports user context."""
        return self.capabilities.supports_user_context


# Re-export main components
__all__ = [
    'SupervisorExecutionEngineAdapter',
    'ConsolidatedExecutionEngineWrapper',
    'ExecutionEngineFactory',
    'GenericExecutionEngineAdapter'
]