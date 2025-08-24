"""
Unified Agent Base Classes - Single source of truth for all agent inheritance.
Eliminates 174+ inconsistent agent base class import patterns.

This module provides the ONLY base classes that should be used for agent development
across the entire system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from datetime import datetime, UTC
from enum import Enum

from shared.logging import get_logger


class AgentState(Enum):
    """Standard agent state enumeration."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseAgent(ABC):
    """
    Unified base agent class that all agents must inherit from.
    
    This class replaces ALL existing base agent patterns and provides
    a consistent interface for agent development.
    """
    
    def __init__(
        self,
        name: str = "BaseAgent",
        description: str = "Base agent description",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize base agent with unified patterns.
        
        Args:
            name: Agent name for identification
            description: Agent description
            correlation_id: Optional correlation ID for tracing
            **kwargs: Additional agent-specific parameters
        """
        self.name = name
        self.description = description
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.state = AgentState.PENDING
        self.created_at = datetime.now(UTC)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.context: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        
        # Initialize unified logging
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Agent-specific initialization
        self._initialize(**kwargs)
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracing."""
        import uuid
        return f"agent-{uuid.uuid4().hex[:12]}"
    
    def _initialize(self, **kwargs) -> None:
        """
        Agent-specific initialization hook.
        
        Override this method to perform agent-specific setup
        without overriding __init__.
        """
        pass
    
    def start(self) -> None:
        """Start agent execution."""
        if self.state != AgentState.PENDING:
            raise ValueError(f"Agent {self.name} cannot start from state {self.state}")
        
        self.state = AgentState.RUNNING
        self.started_at = datetime.now(UTC)
        self.logger.info(f"Agent {self.name} starting execution", extra={
            "correlation_id": self.correlation_id,
            "agent_name": self.name
        })
        
        try:
            self.results = self.execute()
            self.state = AgentState.COMPLETED
            self.completed_at = datetime.now(UTC)
            self.logger.info(f"Agent {self.name} completed successfully", extra={
                "correlation_id": self.correlation_id,
                "agent_name": self.name,
                "duration_ms": self.get_execution_duration_ms()
            })
        except Exception as e:
            self.state = AgentState.FAILED
            self.completed_at = datetime.now(UTC)
            error_msg = str(e)
            self.errors.append(error_msg)
            self.logger.error(f"Agent {self.name} failed: {error_msg}", extra={
                "correlation_id": self.correlation_id,
                "agent_name": self.name,
                "duration_ms": self.get_execution_duration_ms()
            }, exc_info=True)
            raise
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Execute agent logic.
        
        This method must be implemented by all concrete agents.
        
        Returns:
            Dict containing agent execution results
        """
        pass
    
    def stop(self) -> None:
        """Stop agent execution."""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.CANCELLED
            self.completed_at = datetime.now(UTC)
            self.logger.info(f"Agent {self.name} cancelled", extra={
                "correlation_id": self.correlation_id,
                "agent_name": self.name
            })
    
    def get_execution_duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.get_execution_duration_ms(),
            "has_errors": len(self.errors) > 0,
            "error_count": len(self.errors)
        }


class LLMAgent(BaseAgent):
    """
    Base class for agents that interact with LLM providers.
    
    This class provides common LLM interaction patterns and should be
    used for all agents that need to call LLM APIs.
    """
    
    def _initialize(self, llm_manager=None, **kwargs):
        """Initialize LLM-specific functionality."""
        self.llm_manager = llm_manager
        self.llm_calls = []
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def _track_llm_call(self, provider: str, model: str, tokens: int, cost: float):
        """Track LLM API call for metrics."""
        call_info = {
            "provider": provider,
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "timestamp": datetime.now(UTC).isoformat()
        }
        self.llm_calls.append(call_info)
        self.total_tokens += tokens
        self.total_cost += cost
        
        self.logger.info(f"LLM call tracked", extra={
            "correlation_id": self.correlation_id,
            "agent_name": self.name,
            "provider": provider,
            "model": model,
            "tokens": tokens,
            "cost": cost
        })
    
    def get_status(self) -> Dict[str, Any]:
        """Get status including LLM metrics."""
        status = super().get_status()
        status.update({
            "llm_calls": len(self.llm_calls),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "has_llm_manager": self.llm_manager is not None
        })
        return status


class SubAgent(LLMAgent):
    """
    Base class for sub-agents in the Netra system.
    
    This class replaces BaseSubAgent and provides the standard
    interface for all sub-agent implementations.
    """
    
    def _initialize(self, parent_agent=None, **kwargs):
        """Initialize sub-agent specific functionality."""
        super()._initialize(**kwargs)
        self.parent_agent = parent_agent
        self.websocket_manager = None
        self.user_id = None
    
    def set_websocket_context(self, websocket_manager, user_id: str):
        """Set WebSocket context for communication."""
        self.websocket_manager = websocket_manager
        self.user_id = user_id
        self.logger.info(f"WebSocket context set for agent {self.name}", extra={
            "correlation_id": self.correlation_id,
            "agent_name": self.name,
            "user_id": user_id
        })
    
    async def send_websocket_message(self, message: Dict[str, Any]):
        """Send message via WebSocket if available."""
        if not self.websocket_manager or not self.user_id:
            self.logger.warning(f"No WebSocket context available for agent {self.name}")
            return
            
        try:
            await self.websocket_manager.send_to_user(self.user_id, message)
            self.logger.debug(f"WebSocket message sent", extra={
                "correlation_id": self.correlation_id,
                "agent_name": self.name,
                "user_id": self.user_id
            })
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket message: {e}", extra={
                "correlation_id": self.correlation_id,
                "agent_name": self.name,
                "user_id": self.user_id
            })


# Backward compatibility aliases
BaseSubAgent = SubAgent  # For existing code that uses BaseSubAgent


class AgentFactory:
    """Factory for creating standardized agent instances."""
    
    @staticmethod
    def create_agent(
        agent_class: type,
        name: str,
        description: str = "",
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent instance with standard configuration.
        
        Args:
            agent_class: Agent class to instantiate
            name: Agent name
            description: Agent description
            **kwargs: Additional arguments for the agent
            
        Returns:
            Configured agent instance
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class {agent_class} must inherit from BaseAgent")
        
        return agent_class(
            name=name,
            description=description,
            **kwargs
        )
    
    @staticmethod
    def create_llm_agent(
        agent_class: type,
        name: str,
        llm_manager,
        description: str = "",
        **kwargs
    ) -> LLMAgent:
        """
        Create an LLM agent with LLM manager.
        
        Args:
            agent_class: LLM Agent class to instantiate
            name: Agent name
            llm_manager: LLM manager instance
            description: Agent description
            **kwargs: Additional arguments for the agent
            
        Returns:
            Configured LLM agent instance
        """
        if not issubclass(agent_class, LLMAgent):
            raise ValueError(f"Agent class {agent_class} must inherit from LLMAgent")
        
        return agent_class(
            name=name,
            description=description,
            llm_manager=llm_manager,
            **kwargs
        )