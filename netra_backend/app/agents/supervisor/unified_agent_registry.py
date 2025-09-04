"""
UnifiedAgentRegistry: SSOT for all agent registration and discovery.

This unified registry combines the best aspects of agent_registry.py and 
agent_class_registry.py while eliminating duplications and singleton patterns.

Business Value: Critical for reliable agent execution and proper isolation
BVJ: Platform/Internal | Stability | Enables 100% reliable agent orchestration
"""

import threading
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING
from dataclasses import dataclass, field
from abc import ABC
import time
import asyncio

if TYPE_CHECKING:
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.reliability.unified_reliability_manager import (
    get_reliability_manager,
    create_agent_reliability_manager
)

logger = central_logger.get_logger(__name__)


@dataclass(frozen=True)
class AgentMetadata:
    """Immutable metadata about a registered agent type."""
    name: str
    agent_class: Type['BaseAgent']
    description: str
    version: str = "1.0"
    dependencies: tuple = field(default_factory=tuple)
    execution_order: int = 100  # Lower numbers execute first
    category: str = "general"  # triage, data, optimization, action, reporting
    
    def __post_init__(self) -> None:
        """Validate agent metadata after initialization."""
        from netra_backend.app.agents.base_agent import BaseAgent
        if not issubclass(self.agent_class, BaseAgent):
            raise ValueError(f"Agent class {self.agent_class.__name__} must inherit from BaseAgent")
        if not self.name or not self.name.strip():
            raise ValueError("Agent name cannot be empty")


class UnifiedAgentRegistry:
    """
    SSOT for all agent registration and discovery.
    
    Combines the best of both registries:
    - Infrastructure-level class storage (from agent_class_registry)
    - Instance creation and management (from agent_registry)
    - Proper execution order enforcement
    - Thread-safe operations
    - No singleton patterns
    
    Critical Features:
    1. Stores agent classes with metadata
    2. Creates instances per-request (no singletons)
    3. Enforces execution order (Data before Optimization)
    4. Thread-safe for concurrent operations
    5. Supports dynamic discovery
    """
    
    def __init__(self):
        """Initialize unified registry."""
        self._lock = threading.RLock()
        
        # Core registry data - agent classes with metadata
        self._agent_metadata: Dict[str, AgentMetadata] = {}
        
        # Execution order enforcement
        self._execution_order = {
            'triage': 10,
            'goals_triage': 15,
            'data': 20,  # MUST come before optimization
            'synthetic_data': 25,
            'optimization': 30,  # MUST come after data
            'optimizations': 30,  # Alias
            'actions': 40,
            'reporting': 50,
            'summary': 60,
        }
        
        # State management
        self._frozen = False
        self._registration_count = 0
        
        # Cache for agent discovery
        self._discovery_cache: Optional[List[str]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl = 60.0  # Cache for 60 seconds
        
        logger.info("UnifiedAgentRegistry initialized")
    
    def register_agent_class(
        self,
        agent_type: str,
        agent_class: Type['BaseAgent'],
        description: str = "",
        category: Optional[str] = None,
        execution_order: Optional[int] = None
    ) -> None:
        """
        Register an agent class for discovery.
        
        Args:
            agent_type: Unique identifier for the agent type
            agent_class: The agent class (must inherit from BaseAgent)
            description: Human-readable description
            category: Agent category for grouping
            execution_order: Override default execution order
        """
        with self._lock:
            if self._frozen:
                raise RuntimeError("Registry is frozen and cannot be modified")
            
            # Determine execution order
            if execution_order is None:
                # Try to infer from agent type
                for key, order in self._execution_order.items():
                    if key in agent_type.lower():
                        execution_order = order
                        break
                else:
                    execution_order = 100  # Default
            
            # Determine category if not provided
            if category is None:
                for cat in ['triage', 'data', 'optimization', 'actions', 'reporting']:
                    if cat in agent_type.lower():
                        category = cat
                        break
                else:
                    category = 'general'
            
            # Create metadata
            metadata = AgentMetadata(
                name=agent_type,
                agent_class=agent_class,
                description=description or f"{agent_class.__name__} agent",
                execution_order=execution_order,
                category=category,
                dependencies=tuple()
            )
            
            # Register
            if agent_type in self._agent_metadata:
                logger.warning(f"Overwriting existing agent registration: {agent_type}")
            
            self._agent_metadata[agent_type] = metadata
            self._registration_count += 1
            
            # Invalidate discovery cache
            self._discovery_cache = None
            
            logger.info(
                f"Registered agent: {agent_type} "
                f"(class={agent_class.__name__}, order={execution_order}, category={category})"
            )
    
    def get_agent_class(self, agent_type: str) -> Optional[Type['BaseAgent']]:
        """
        Get an agent class by type.
        
        Args:
            agent_type: The agent type identifier
            
        Returns:
            The agent class or None if not found
        """
        metadata = self._agent_metadata.get(agent_type)
        return metadata.agent_class if metadata else None
    
    def get_agent_metadata(self, agent_type: str) -> Optional[AgentMetadata]:
        """
        Get complete metadata for an agent type.
        
        Args:
            agent_type: The agent type identifier
            
        Returns:
            The agent metadata or None if not found
        """
        return self._agent_metadata.get(agent_type)
    
    def create_agent_instance(
        self,
        agent_type: str,
        llm_manager: 'LLMManager',
        tool_dispatcher: 'ToolDispatcher',
        context: Optional['UserExecutionContext'] = None,
        **kwargs
    ) -> Optional['BaseAgent']:
        """
        Create a new agent instance (not cached/singleton).
        
        Args:
            agent_type: The agent type to instantiate
            llm_manager: LLM manager for the agent
            tool_dispatcher: Tool dispatcher for the agent
            context: Optional user execution context
            **kwargs: Additional arguments for agent construction
            
        Returns:
            New agent instance or None if type not found
        """
        agent_class = self.get_agent_class(agent_type)
        if not agent_class:
            logger.error(f"Agent type not found: {agent_type}")
            return None
        
        try:
            # Create new instance (no caching/singleton)
            agent = agent_class(
                llm_manager=llm_manager,
                tool_dispatcher=tool_dispatcher,
                **kwargs
            )
            
            # If context provided, set it
            if context and hasattr(agent, 'set_context'):
                agent.set_context(context)
            
            logger.debug(f"Created new {agent_type} instance")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create {agent_type} instance: {e}")
            return None
    
    def discover_agents(self, force_refresh: bool = False) -> List[str]:
        """
        Discover all available agent types.
        
        Args:
            force_refresh: Force cache refresh
            
        Returns:
            List of registered agent types sorted by execution order
        """
        # Check cache
        if not force_refresh and self._discovery_cache is not None:
            if time.time() - self._cache_timestamp < self._cache_ttl:
                return self._discovery_cache
        
        # Build discovery list sorted by execution order
        agents = sorted(
            self._agent_metadata.values(),
            key=lambda m: (m.execution_order, m.name)
        )
        
        self._discovery_cache = [agent.name for agent in agents]
        self._cache_timestamp = time.time()
        
        return self._discovery_cache
    
    def get_agents_by_category(self, category: str) -> List[str]:
        """
        Get all agents in a specific category.
        
        Args:
            category: The category to filter by
            
        Returns:
            List of agent types in the category
        """
        return [
            name for name, metadata in self._agent_metadata.items()
            if metadata.category == category
        ]
    
    def get_execution_order(self) -> List[str]:
        """
        Get the proper execution order for all agents.
        
        Critical: Ensures Data agents run before Optimization agents.
        
        Returns:
            Ordered list of agent types
        """
        agents = sorted(
            self._agent_metadata.items(),
            key=lambda x: (x[1].execution_order, x[0])
        )
        return [name for name, _ in agents]
    
    def validate_execution_order(self, agent_sequence: List[str]) -> bool:
        """
        Validate that an agent sequence follows proper execution order.
        
        Critical: Ensures Data comes before Optimization.
        
        Args:
            agent_sequence: Proposed sequence of agent types
            
        Returns:
            True if order is valid, False otherwise
        """
        # Check Data before Optimization rule
        data_index = -1
        optimization_index = -1
        
        for i, agent_type in enumerate(agent_sequence):
            if 'data' in agent_type.lower() and 'synthetic' not in agent_type.lower():
                data_index = i
            elif 'optimization' in agent_type.lower():
                optimization_index = i
        
        # If both present, data must come first
        if data_index >= 0 and optimization_index >= 0:
            if data_index > optimization_index:
                logger.error(
                    f"Invalid execution order: Data agent at {data_index} "
                    f"comes after Optimization at {optimization_index}"
                )
                return False
        
        return True
    
    def freeze(self) -> None:
        """
        Make the registry immutable after initialization.
        
        This prevents runtime modifications that could break stability.
        """
        with self._lock:
            self._frozen = True
            logger.info(
                f"Registry frozen with {self._registration_count} agents: "
                f"{', '.join(self.discover_agents())}"
            )
    
    def is_frozen(self) -> bool:
        """Check if registry is frozen."""
        return self._frozen
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry stats
        """
        return {
            'total_agents': len(self._agent_metadata),
            'categories': list(set(m.category for m in self._agent_metadata.values())),
            'frozen': self._frozen,
            'agents': self.discover_agents(),
            'execution_order': self.get_execution_order(),
        }
    
    def register_default_agents(self) -> None:
        """
        Register all default agent types.
        
        This method imports and registers all standard agents.
        """
        try:
            # Import all agent classes
            from netra_backend.app.agents.data_sub_agent import DataSubAgent
            from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
            from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
            from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
            from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
            from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
            from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
            
            # Register in proper order
            self.register_agent_class('triage', TriageSubAgent, 'Initial request triage')
            self.register_agent_class('goals_triage', GoalsTriageSubAgent, 'Goals assessment')
            self.register_agent_class('data', DataSubAgent, 'Data analysis and metrics')
            self.register_agent_class('synthetic_data', SyntheticDataSubAgent, 'Synthetic data generation')
            self.register_agent_class('optimizations', OptimizationsCoreSubAgent, 'Optimization strategies')
            self.register_agent_class('actions', ActionsToMeetGoalsSubAgent, 'Action planning')
            self.register_agent_class('reporting', ReportingSubAgent, 'Report generation')
            
            logger.info(f"Registered {self._registration_count} default agents")
            
        except ImportError as e:
            logger.error(f"Failed to import agent classes: {e}")
            raise


# Global singleton instance (created once at module load)
_global_registry: Optional[UnifiedAgentRegistry] = None
_registry_lock = threading.Lock()


def get_unified_agent_registry() -> UnifiedAgentRegistry:
    """
    Get the global unified agent registry instance.
    
    Returns:
        The global registry instance
    """
    global _global_registry
    
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = UnifiedAgentRegistry()
                _global_registry.register_default_agents()
                _global_registry.freeze()
    
    return _global_registry