"""Execution Engine Interface - SSOT Migration Support

This module provides the common interface for all execution engine implementations
to enable seamless migration from legacy implementations to the consolidated engine.

Business Value:
- Zero breaking changes during SSOT consolidation 
- Backward compatibility for existing integrations
- Gradual migration path for 100+ execution engine usages
- Protection of Golden Path user flows during transition

Architecture:
- Abstract interface defining required execution engine methods
- Common return types and execution context patterns
- Migration support for legacy execution engines
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class IExecutionEngine(ABC):
    """Interface for all execution engine implementations.
    
    This interface ensures consistent behavior across all execution engine
    implementations during the SSOT consolidation process.
    
    All execution engines (legacy and consolidated) must implement this interface
    to maintain compatibility and enable gradual migration.
    """
    
    @abstractmethod
    async def execute_agent(
        self,
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> AgentExecutionResult:
        """Execute a single agent with the given context.
        
        Args:
            context: Agent execution context containing agent name, task, and metadata
            user_context: Optional user context for isolation and personalization
            
        Returns:
            AgentExecutionResult: Results of the agent execution
            
        Raises:
            RuntimeError: If execution fails critically
            TimeoutError: If execution exceeds configured timeout
        """
        pass
    
    @abstractmethod
    async def execute_pipeline(
        self,
        steps: List[PipelineStep],
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> List[AgentExecutionResult]:
        """Execute a pipeline of agent steps.
        
        Args:
            steps: List of pipeline steps to execute
            context: Base execution context for the pipeline
            user_context: Optional user context for isolation
            
        Returns:
            List[AgentExecutionResult]: Results from each pipeline step
        """
        pass
    
    @abstractmethod
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution performance and health statistics.
        
        Returns:
            Dict containing execution metrics, performance data, and health status
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the execution engine and clean up resources.
        
        This method should:
        - Cancel any running executions gracefully
        - Release resources (connections, memory, handles)
        - Cleanup background tasks
        """
        pass
    
    # Optional interface methods with default implementations
    
    async def initialize(self) -> None:
        """Initialize the execution engine (optional).
        
        Default implementation is no-op. Engines can override if needed.
        """
        pass
    
    def get_engine_type(self) -> str:
        """Get the engine type identifier.
        
        Returns:
            String identifying the engine implementation type
        """
        return self.__class__.__name__
    
    def has_user_context_support(self) -> bool:
        """Check if engine supports UserExecutionContext.
        
        Returns:
            True if engine supports user context isolation, False otherwise
        """
        return True  # Default assumption for new engines
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the execution engine.
        
        Returns:
            Dict containing health status and diagnostic information
        """
        try:
            stats = await self.get_execution_stats()
            return {
                'status': 'healthy',
                'engine_type': self.get_engine_type(),
                'user_context_support': self.has_user_context_support(),
                'stats': stats
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'engine_type': self.get_engine_type(),
                'error': str(e)
            }


class ExecutionEngineCapabilities:
    """Capabilities descriptor for execution engines.
    
    Used to describe what features an execution engine implementation supports.
    Enables feature detection and compatibility checking during migration.
    """
    
    def __init__(
        self,
        supports_user_context: bool = True,
        supports_pipelines: bool = True,
        supports_websocket_events: bool = True,
        supports_concurrent_users: bool = True,
        supports_request_scoping: bool = False,
        max_concurrent_executions: int = 10,
        execution_timeout_seconds: float = 30.0,
        features: Optional[List[str]] = None
    ):
        """Initialize execution engine capabilities.
        
        Args:
            supports_user_context: Engine supports UserExecutionContext isolation
            supports_pipelines: Engine can execute multi-step pipelines
            supports_websocket_events: Engine emits WebSocket events
            supports_concurrent_users: Engine handles multiple users safely
            supports_request_scoping: Engine supports request-scoped execution
            max_concurrent_executions: Maximum concurrent executions supported
            execution_timeout_seconds: Default execution timeout
            features: Additional feature strings
        """
        self.supports_user_context = supports_user_context
        self.supports_pipelines = supports_pipelines
        self.supports_websocket_events = supports_websocket_events
        self.supports_concurrent_users = supports_concurrent_users
        self.supports_request_scoping = supports_request_scoping
        self.max_concurrent_executions = max_concurrent_executions
        self.execution_timeout_seconds = execution_timeout_seconds
        self.features = features or []
    
    def is_compatible_with(self, required_capabilities: 'ExecutionEngineCapabilities') -> bool:
        """Check if this engine's capabilities meet the requirements.
        
        Args:
            required_capabilities: Required capabilities to check against
            
        Returns:
            True if this engine meets all required capabilities
        """
        # Check basic capability flags
        if required_capabilities.supports_user_context and not self.supports_user_context:
            return False
        if required_capabilities.supports_pipelines and not self.supports_pipelines:
            return False
        if required_capabilities.supports_websocket_events and not self.supports_websocket_events:
            return False
        if required_capabilities.supports_concurrent_users and not self.supports_concurrent_users:
            return False
        if required_capabilities.supports_request_scoping and not self.supports_request_scoping:
            return False
        
        # Check performance requirements
        if self.max_concurrent_executions < required_capabilities.max_concurrent_executions:
            return False
        if self.execution_timeout_seconds < required_capabilities.execution_timeout_seconds:
            return False
        
        # Check required features
        for required_feature in required_capabilities.features:
            if required_feature not in self.features:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary representation."""
        return {
            'supports_user_context': self.supports_user_context,
            'supports_pipelines': self.supports_pipelines,
            'supports_websocket_events': self.supports_websocket_events,
            'supports_concurrent_users': self.supports_concurrent_users,
            'supports_request_scoping': self.supports_request_scoping,
            'max_concurrent_executions': self.max_concurrent_executions,
            'execution_timeout_seconds': self.execution_timeout_seconds,
            'features': self.features
        }


class ExecutionEngineAdapter:
    """Base adapter class for wrapping legacy execution engines.
    
    Provides common functionality for adapting legacy execution engines
    to the IExecutionEngine interface without breaking existing code.
    """
    
    def __init__(self, wrapped_engine: Any, capabilities: ExecutionEngineCapabilities):
        """Initialize the adapter.
        
        Args:
            wrapped_engine: The legacy execution engine to wrap
            capabilities: Capabilities of the wrapped engine
        """
        self.wrapped_engine = wrapped_engine
        self.capabilities = capabilities
        self._initialized = False
    
    async def ensure_initialized(self) -> None:
        """Ensure the wrapped engine is initialized."""
        if not self._initialized:
            if hasattr(self.wrapped_engine, 'initialize'):
                await self.wrapped_engine.initialize()
            self._initialized = True
    
    async def execute_agent_adapted(
        self,
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> AgentExecutionResult:
        """Adapter method for execute_agent - override in specific adapters."""
        await self.ensure_initialized()
        
        # Default implementation delegates to wrapped engine
        if hasattr(self.wrapped_engine, 'execute_agent'):
            return await self.wrapped_engine.execute_agent(context, user_context)
        elif hasattr(self.wrapped_engine, 'execute'):
            # Try alternate method names
            return await self.wrapped_engine.execute(context, user_context)
        else:
            raise NotImplementedError(
                f"Wrapped engine {type(self.wrapped_engine)} does not have execute_agent or execute method"
            )
    
    async def execute_pipeline_adapted(
        self,
        steps: List[PipelineStep],
        context: AgentExecutionContext,
        user_context: Optional['UserExecutionContext'] = None
    ) -> List[AgentExecutionResult]:
        """Adapter method for execute_pipeline - override in specific adapters."""
        await self.ensure_initialized()
        
        # Default implementation delegates to wrapped engine
        if hasattr(self.wrapped_engine, 'execute_pipeline'):
            return await self.wrapped_engine.execute_pipeline(steps, context, user_context)
        else:
            # Fallback: execute steps sequentially
            results = []
            for step in steps:
                step_context = AgentExecutionContext(
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    user_id=context.user_id,
                    agent_name=step.agent_name,
                    prompt=context.prompt,
                    user_input=context.user_input,
                    metadata=step.metadata
                )
                result = await self.execute_agent_adapted(step_context, user_context)
                results.append(result)
                
                # Stop on failure unless continue_on_error is set
                if not result.success and not step.metadata.get('continue_on_error', False):
                    break
            
            return results
    
    async def get_execution_stats_adapted(self) -> Dict[str, Any]:
        """Adapter method for get_execution_stats."""
        base_stats = {
            'engine_type': type(self.wrapped_engine).__name__,
            'adapter_type': type(self).__name__,
            'capabilities': self.capabilities.to_dict()
        }
        
        if hasattr(self.wrapped_engine, 'get_execution_stats'):
            wrapped_stats = await self.wrapped_engine.get_execution_stats()
            base_stats.update(wrapped_stats)
        elif hasattr(self.wrapped_engine, 'execution_stats'):
            # Try accessing stats directly
            base_stats['wrapped_stats'] = getattr(self.wrapped_engine, 'execution_stats')
        
        return base_stats
    
    async def shutdown_adapted(self) -> None:
        """Adapter method for shutdown."""
        if hasattr(self.wrapped_engine, 'shutdown'):
            await self.wrapped_engine.shutdown()
        elif hasattr(self.wrapped_engine, 'cleanup'):
            await self.wrapped_engine.cleanup()
        
        self._initialized = False


# Convenience type alias for execution engines
ExecutionEngineType = Union[IExecutionEngine, Any]  # Any for legacy engines during transition

# Re-export interface components
__all__ = [
    'IExecutionEngine',
    'ExecutionEngineCapabilities', 
    'ExecutionEngineAdapter',
    'ExecutionEngineType'
]