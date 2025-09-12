"""
AgentClassRegistry: Infrastructure-only agent class registration.

CRITICAL: This is an infrastructure-layer component that stores ONLY agent classes
(not instances) and is immutable after startup. It serves as the SSOT for available
agent types that can be instantiated when needed.

Business Value: Provides a centralized, thread-safe registry of agent classes that:
- Prevents runtime modifications that could break system stability
- Enables dynamic agent instantiation with type safety
- Supports dependency injection and testing with predictable behavior
- Follows CLAUDE.md's Single Source of Truth (SSOT) principle

Architecture: Immutable after initialization, thread-safe for concurrent reads.
"""

import threading
from typing import Any, Dict, Optional, Type, List, Set, TYPE_CHECKING
from dataclasses import dataclass
from abc import ABC

if TYPE_CHECKING:
    from netra_backend.app.agents.base_agent import BaseAgent

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass(frozen=True)
class AgentClassInfo:
    """Immutable information about a registered agent class."""
    
    name: str
    agent_class: Type['BaseAgent']
    description: str
    version: str
    dependencies: tuple  # Tuple for immutability
    metadata: Dict[str, Any]  # Frozen during registration
    
    def __post_init__(self) -> None:
        """Validate agent class info after initialization."""
        # Import BaseAgent lazily for validation
        from netra_backend.app.agents.base_agent import BaseAgent
        if not issubclass(self.agent_class, BaseAgent):
            raise ValueError(f"Agent class {self.agent_class.__name__} must inherit from BaseAgent")
        
        if not self.name or not self.name.strip():
            raise ValueError("Agent name cannot be empty")
            
        if not isinstance(self.dependencies, tuple):
            # Convert to tuple for immutability
            object.__setattr__(self, 'dependencies', tuple(self.dependencies))


class AgentClassRegistry:
    """
    Immutable infrastructure-only registry for agent classes.
    
    CRITICAL REQUIREMENTS SATISFIED:
    1.  PASS:  Stores ONLY agent classes (not instances)  
    2.  PASS:  Immutable after startup (no modifications after _freeze())
    3.  PASS:  Located in netra_backend/app/agents/supervisor/agent_class_registry.py
    4.  PASS:  NO per-user state (no WebSocket bridges, no database sessions)
    5.  PASS:  Provides method to get agent classes by name
    6.  PASS:  Thread-safe for concurrent reads
    
    Design Principles:
    - Single responsibility: Only manages agent class registration
    - Immutable after initialization: Prevents runtime corruption
    - Thread-safe: Uses RLock for registration, no locking needed for reads after freeze
    - Type-safe: Comprehensive type hints and validation
    - SSOT: Central source of truth for all available agent types
    
    Usage Pattern:
    ```python
    # At startup (once)
    registry = AgentClassRegistry()
    registry.register('triage', TriageSubAgent, 'Handles request triage')
    registry.register('data', DataSubAgent, 'Processes data operations')
    registry.freeze()  # Makes registry immutable
    
    # During runtime (many times, thread-safe)
    agent_class = registry.get_agent_class('triage')
    if agent_class:
        agent_instance = agent_class(llm_manager, tool_dispatcher)
    ```
    """
    
    def __init__(self) -> None:
        """Initialize empty registry."""
        # Thread-safe registration during startup phase
        self._lock = threading.RLock()
        
        # Core registry data - immutable after freeze
        self._agent_classes: Dict[str, AgentClassInfo] = {}
        
        # State management
        self._frozen = False
        self._registration_count = 0
        
        # Metadata for diagnostics
        self._creation_time = None
        self._freeze_time = None
        
        logger.info("AgentClassRegistry initialized")
    
    def register(self, 
                 name: str, 
                 agent_class: Type['BaseAgent'], 
                 description: str = "",
                 version: str = "1.0.0",
                 dependencies: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register an agent class (STARTUP ONLY).
        
        Args:
            name: Unique identifier for the agent class
            agent_class: The agent class type (must inherit from BaseAgent)
            description: Human-readable description
            version: Version string for the agent class
            dependencies: List of required dependencies
            metadata: Additional metadata about the agent class
            
        Raises:
            RuntimeError: If registry is already frozen
            ValueError: If name is already registered or invalid
            TypeError: If agent_class doesn't inherit from BaseAgent
        """
        if self._frozen:
            raise RuntimeError(
                "Cannot register agent classes after registry is frozen. "
                "All agent classes must be registered during startup phase."
            )
        
        with self._lock:
            # Re-check frozen state after acquiring lock
            if self._frozen:
                raise RuntimeError("Registry was frozen while waiting for lock")
            
            # Validate input parameters
            self._validate_registration_params(name, agent_class, description)
            
            # Check for duplicate registration
            if name in self._agent_classes:
                existing_class = self._agent_classes[name].agent_class
                if existing_class != agent_class:
                    raise ValueError(
                        f"Agent name '{name}' already registered with different class "
                        f"(existing: {existing_class.__name__}, new: {agent_class.__name__})"
                    )
                else:
                    logger.warning(f"Agent class '{name}' already registered with same class, skipping")
                    return
            
            # Create immutable agent class info
            agent_info = AgentClassInfo(
                name=name,
                agent_class=agent_class,
                description=description,
                version=version,
                dependencies=tuple(dependencies or []),
                metadata=dict(metadata or {})  # Create copy for immutability
            )
            
            # Register the agent class
            self._agent_classes[name] = agent_info
            self._registration_count += 1
            
            logger.info(
                f"Registered agent class '{name}' -> {agent_class.__name__} "
                f"(version: {version})"
            )
    
    def freeze(self) -> None:
        """
        Freeze the registry to make it immutable (STARTUP COMPLETION).
        
        After calling this method, no further registrations are allowed.
        The registry becomes thread-safe for concurrent reads without locking.
        """
        if self._frozen:
            logger.warning("Registry is already frozen")
            return
        
        with self._lock:
            # Final validation before freezing
            if not self._agent_classes:
                logger.warning("Freezing registry with no registered agent classes")
            
            self._frozen = True
            import time
            self._freeze_time = time.time()
            
            logger.info(
                f"AgentClassRegistry frozen with {self._registration_count} agent classes: "
                f"{list(self._agent_classes.keys())}"
            )
    
    def get_agent_class(self, name: str) -> Optional[Type['BaseAgent']]:
        """
        Get agent class by name (RUNTIME - THREAD-SAFE).
        
        Args:
            name: Name of the agent class to retrieve
            
        Returns:
            Agent class if found, None otherwise
        """
        agent_info = self._agent_classes.get(name)
        return agent_info.agent_class if agent_info else None
    
    def get_agent_info(self, name: str) -> Optional[AgentClassInfo]:
        """
        Get complete agent class information by name (RUNTIME - THREAD-SAFE).
        
        Args:
            name: Name of the agent class
            
        Returns:
            AgentClassInfo if found, None otherwise
        """
        return self._agent_classes.get(name)
    
    def list_agent_names(self) -> List[str]:
        """
        List all registered agent names (RUNTIME - THREAD-SAFE).
        
        Returns:
            List of agent names sorted alphabetically
        """
        return sorted(self._agent_classes.keys())
    
    def get_all_agent_classes(self) -> Dict[str, Type['BaseAgent']]:
        """
        Get all registered agent classes (RUNTIME - THREAD-SAFE).
        
        Returns:
            Dictionary mapping names to agent classes
        """
        return {
            name: info.agent_class 
            for name, info in self._agent_classes.items()
        }
    
    def has_agent_class(self, name: str) -> bool:
        """
        Check if agent class is registered (RUNTIME - THREAD-SAFE).
        
        Args:
            name: Name to check
            
        Returns:
            True if agent class exists, False otherwise
        """
        return name in self._agent_classes
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics and health information (RUNTIME - THREAD-SAFE).
        
        Returns:
            Dictionary with registry statistics
        """
        return {
            "total_agent_classes": len(self._agent_classes),
            "frozen": self._frozen,
            "agent_names": self.list_agent_names(),
            "registration_count": self._registration_count,
            "creation_time": self._creation_time,
            "freeze_time": self._freeze_time,
            "health_status": "healthy" if self._frozen and self._agent_classes else "unhealthy"
        }
    
    def validate_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate that all declared dependencies are available (RUNTIME - THREAD-SAFE).
        
        Returns:
            Dictionary with any missing dependencies per agent
        """
        missing_deps = {}
        registered_names = set(self._agent_classes.keys())
        
        for name, info in self._agent_classes.items():
            missing = []
            for dep in info.dependencies:
                if dep not in registered_names:
                    missing.append(dep)
            
            if missing:
                missing_deps[name] = missing
        
        return missing_deps
    
    def get_agents_by_dependency(self, dependency: str) -> List[str]:
        """
        Get all agents that depend on a specific dependency (RUNTIME - THREAD-SAFE).
        
        Args:
            dependency: Name of dependency to search for
            
        Returns:
            List of agent names that depend on the given dependency
        """
        dependent_agents = []
        for name, info in self._agent_classes.items():
            if dependency in info.dependencies:
                dependent_agents.append(name)
        
        return sorted(dependent_agents)
    
    # === Private Helper Methods ===
    
    def _validate_registration_params(self, name: str, agent_class: Type, description: str) -> None:
        """Validate registration parameters."""
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Agent name must be a non-empty string")
        
        if not isinstance(agent_class, type):
            raise TypeError(f"agent_class must be a class type, got {type(agent_class)}")
        
        # Import BaseAgent lazily for validation
        from netra_backend.app.agents.base_agent import BaseAgent
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(
                f"Agent class {agent_class.__name__} must inherit from BaseAgent"
            )
        
        if not isinstance(description, str):
            raise TypeError("Description must be a string")
    
    def is_frozen(self) -> bool:
        """Check if registry is frozen (RUNTIME - THREAD-SAFE)."""
        return self._frozen
    
    def __len__(self) -> int:
        """Get number of registered agent classes."""
        return len(self._agent_classes)
    
    def __contains__(self, name: str) -> bool:
        """Check if agent name is registered (supports 'in' operator)."""
        return self.has_agent_class(name)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        status = "frozen" if self._frozen else "mutable"
        return (
            f"AgentClassRegistry({len(self._agent_classes)} classes, {status}): "
            f"{list(self._agent_classes.keys())}"
        )


# === SSOT Global Registry Instance ===

_global_agent_class_registry: Optional[AgentClassRegistry] = None
_registry_lock = threading.Lock()


def get_agent_class_registry() -> AgentClassRegistry:
    """
    Get the global agent class registry instance (SSOT pattern).
    
    Returns:
        The singleton AgentClassRegistry instance
    """
    global _global_agent_class_registry
    
    if _global_agent_class_registry is None:
        with _registry_lock:
            # Double-checked locking pattern
            if _global_agent_class_registry is None:
                _global_agent_class_registry = AgentClassRegistry()
                logger.info("Created global AgentClassRegistry instance")
    
    return _global_agent_class_registry


def create_test_registry() -> AgentClassRegistry:
    """
    Create a separate registry for testing (bypasses global singleton).
    
    Returns:
        New AgentClassRegistry instance for testing
    """
    return AgentClassRegistry()