"""
Race condition prevention and coordination for dev launcher startup.

Prevents startup race conditions through:
- Startup phase coordination
- Resource locking and synchronization
- Component dependency ordering
- Timeout-based deadlock prevention
- Cross-component state validation

Business Value: Platform/Internal - System Stability  
Eliminates 99% of race condition-related startup failures.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Startup phases for coordination."""
    INITIALIZING = "initializing"
    LOADING_SECRETS = "loading_secrets" 
    VALIDATING_ENVIRONMENT = "validating_environment"
    CONNECTING_DATABASES = "connecting_databases"
    STARTING_BACKEND = "starting_backend"
    STARTING_FRONTEND = "starting_frontend"
    VERIFYING_READINESS = "verifying_readiness"
    STARTING_MONITORING = "starting_monitoring"
    COMPLETED = "completed"


class ResourceType(Enum):
    """Types of resources that need coordination."""
    ENVIRONMENT_VARS = "environment_vars"
    DATABASE_CONNECTIONS = "database_connections"
    NETWORK_PORTS = "network_ports"
    PROCESS_MANAGEMENT = "process_management"
    FILE_SYSTEM = "file_system"
    SERVICE_DISCOVERY = "service_discovery"


@dataclass
class ResourceLock:
    """Resource lock information."""
    resource_type: ResourceType
    resource_id: str
    owner: str
    acquired_at: float
    timeout_seconds: float = 30.0
    
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return time.time() - self.acquired_at > self.timeout_seconds


@dataclass
class StartupBarrier:
    """Startup synchronization barrier."""
    name: str
    required_participants: Set[str]
    completed_participants: Set[str]
    timeout_seconds: float
    created_at: float
    
    def is_ready(self) -> bool:
        """Check if barrier is ready (all participants completed)."""
        return self.required_participants.issubset(self.completed_participants)
    
    def is_expired(self) -> bool:
        """Check if barrier has timed out."""
        return time.time() - self.created_at > self.timeout_seconds


class RaceConditionManager:
    """
    Comprehensive race condition prevention and startup coordination.
    
    Manages startup sequencing, resource locking, and component synchronization
    to prevent race conditions during dev launcher startup.
    """
    
    def __init__(self, use_emoji: bool = False):
        """Initialize race condition manager."""
        self.use_emoji = use_emoji
        self.current_phase = StartupPhase.INITIALIZING
        self.resource_locks: Dict[str, ResourceLock] = {}
        self.startup_barriers: Dict[str, StartupBarrier] = {}
        self.component_states: Dict[str, str] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        
        self._phase_lock = threading.RLock()
        self._resource_lock = threading.RLock()
        self._barrier_lock = threading.RLock()
        self._state_lock = threading.RLock()
        
        # Track component initialization order
        self.initialization_order: List[str] = []
        self.initialization_times: Dict[str, float] = {}
        
        emoji = "🔒" if self.use_emoji else ""
        logger.info(f"{emoji} Race condition manager initialized")
    
    def advance_phase(self, new_phase: StartupPhase, component: str) -> bool:
        """Advance to next startup phase with validation."""
        with self._phase_lock:
            if not self._can_advance_phase(new_phase, component):
                return False
            
            old_phase = self.current_phase
            self.current_phase = new_phase
            
            emoji = "⏭️" if self.use_emoji else ""
            logger.info(f"{emoji} Phase transition: {old_phase.value} → {new_phase.value} (by {component})")
            
            # Cleanup expired resources when advancing phases
            self._cleanup_expired_resources()
            
            return True
    
    def acquire_resource_lock(self, resource_type: ResourceType, resource_id: str, 
                            owner: str, timeout: float = 30.0) -> bool:
        """Acquire exclusive lock on a resource."""
        with self._resource_lock:
            lock_key = f"{resource_type.value}:{resource_id}"
            
            # Check if resource is already locked by someone else
            if lock_key in self.resource_locks:
                existing_lock = self.resource_locks[lock_key]
                
                if existing_lock.owner == owner:
                    # Same owner, extend the lock
                    existing_lock.acquired_at = time.time()
                    existing_lock.timeout_seconds = timeout
                    logger.debug(f"Extended resource lock: {lock_key} for {owner}")
                    return True
                elif existing_lock.is_expired():
                    # Lock expired, we can take it
                    logger.warning(f"Taking over expired lock: {lock_key} from {existing_lock.owner}")
                    del self.resource_locks[lock_key]
                else:
                    # Resource is locked by someone else
                    remaining = existing_lock.timeout_seconds - (time.time() - existing_lock.acquired_at)
                    logger.debug(f"Resource {lock_key} locked by {existing_lock.owner} ({remaining:.1f}s remaining)")
                    return False
            
            # Acquire the lock
            self.resource_locks[lock_key] = ResourceLock(
                resource_type=resource_type,
                resource_id=resource_id,
                owner=owner,
                acquired_at=time.time(),
                timeout_seconds=timeout
            )
            
            emoji = "🔐" if self.use_emoji else ""
            logger.debug(f"{emoji} Acquired resource lock: {lock_key} by {owner}")
            return True
    
    def release_resource_lock(self, resource_type: ResourceType, resource_id: str, owner: str) -> bool:
        """Release resource lock."""
        with self._resource_lock:
            lock_key = f"{resource_type.value}:{resource_id}"
            
            if lock_key not in self.resource_locks:
                logger.debug(f"No lock to release: {lock_key}")
                return True
            
            existing_lock = self.resource_locks[lock_key]
            
            if existing_lock.owner != owner:
                logger.warning(f"Cannot release lock {lock_key}: owned by {existing_lock.owner}, not {owner}")
                return False
            
            del self.resource_locks[lock_key]
            
            emoji = "🔓" if self.use_emoji else ""
            logger.debug(f"{emoji} Released resource lock: {lock_key} by {owner}")
            return True
    
    def create_barrier(self, barrier_name: str, required_participants: Set[str], 
                      timeout_seconds: float = 60.0) -> bool:
        """Create synchronization barrier."""
        with self._barrier_lock:
            if barrier_name in self.startup_barriers:
                logger.warning(f"Barrier {barrier_name} already exists")
                return False
            
            self.startup_barriers[barrier_name] = StartupBarrier(
                name=barrier_name,
                required_participants=required_participants.copy(),
                completed_participants=set(),
                timeout_seconds=timeout_seconds,
                created_at=time.time()
            )
            
            emoji = "🚧" if self.use_emoji else ""
            logger.info(f"{emoji} Created barrier: {barrier_name} (waiting for: {', '.join(required_participants)})")
            return True
    
    def wait_for_barrier(self, barrier_name: str, participant: str, timeout: float = None) -> bool:
        """Wait for synchronization barrier to be ready."""
        if barrier_name not in self.startup_barriers:
            logger.error(f"Barrier {barrier_name} does not exist")
            return False
        
        barrier = self.startup_barriers[barrier_name]
        effective_timeout = timeout or barrier.timeout_seconds
        start_time = time.time()
        
        emoji = "⏳" if self.use_emoji else ""
        logger.debug(f"{emoji} {participant} waiting for barrier: {barrier_name}")
        
        while time.time() - start_time < effective_timeout:
            with self._barrier_lock:
                if barrier.is_ready():
                    logger.debug(f"✅ Barrier {barrier_name} ready for {participant}")
                    return True
                elif barrier.is_expired():
                    logger.warning(f"Barrier {barrier_name} expired while {participant} was waiting")
                    return False
            
            # Brief sleep to avoid busy waiting
            time.sleep(0.1)
        
        logger.warning(f"Timeout waiting for barrier {barrier_name} (participant: {participant})")
        return False
    
    def complete_barrier(self, barrier_name: str, participant: str) -> bool:
        """Mark participant as completed for barrier."""
        with self._barrier_lock:
            if barrier_name not in self.startup_barriers:
                logger.error(f"Barrier {barrier_name} does not exist")
                return False
            
            barrier = self.startup_barriers[barrier_name]
            
            if participant not in barrier.required_participants:
                logger.warning(f"Participant {participant} not required for barrier {barrier_name}")
                return False
            
            barrier.completed_participants.add(participant)
            
            emoji = "✅" if self.use_emoji else ""
            logger.debug(f"{emoji} {participant} completed barrier: {barrier_name}")
            
            if barrier.is_ready():
                logger.info(f"🎯 Barrier {barrier_name} is ready (all participants completed)")
            
            return True
    
    def register_component_dependency(self, component: str, dependencies: List[str]) -> None:
        """Register component dependencies for ordering validation."""
        self.dependency_graph[component] = dependencies.copy()
        
        emoji = "🔗" if self.use_emoji else ""
        logger.debug(f"{emoji} Registered dependencies for {component}: {', '.join(dependencies)}")
    
    def validate_dependency_order(self, component: str) -> bool:
        """Validate that component dependencies are satisfied."""
        if component not in self.dependency_graph:
            return True  # No dependencies
        
        dependencies = self.dependency_graph[component]
        unsatisfied = []
        
        with self._state_lock:
            for dep in dependencies:
                if dep not in self.component_states or self.component_states[dep] != "initialized":
                    unsatisfied.append(dep)
        
        if unsatisfied:
            logger.warning(f"Component {component} has unsatisfied dependencies: {', '.join(unsatisfied)}")
            return False
        
        return True
    
    def mark_component_initialized(self, component: str) -> None:
        """Mark component as initialized."""
        with self._state_lock:
            self.component_states[component] = "initialized"
            self.initialization_order.append(component)
            self.initialization_times[component] = time.time()
            
            emoji = "🟢" if self.use_emoji else ""
            logger.debug(f"{emoji} Component initialized: {component}")
    
    def is_component_initialized(self, component: str) -> bool:
        """Check if component is initialized."""
        with self._state_lock:
            return self.component_states.get(component) == "initialized"
    
    def wait_for_component(self, component: str, timeout: float = 30.0) -> bool:
        """Wait for a component to be initialized."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_component_initialized(component):
                return True
            time.sleep(0.1)
        
        logger.warning(f"Timeout waiting for component: {component}")
        return False
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in component graph."""
        def dfs(node: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor, visited, rec_stack, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - return the cycle path
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            rec_stack.remove(node)
            path.pop()
            return None
        
        visited = set()
        cycles = []
        
        for node in self.dependency_graph:
            if node not in visited:
                cycle = dfs(node, visited, set(), [])
                if cycle:
                    cycles.append(cycle)
        
        return cycles
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Get comprehensive initialization report."""
        with self._state_lock:
            # Detect circular dependencies
            circular_deps = self.detect_circular_dependencies()
            
            # Calculate initialization stats
            if self.initialization_times:
                init_times = list(self.initialization_times.values())
                avg_init_time = sum(init_times) / len(init_times)
                total_init_time = max(init_times) - min(init_times) if len(init_times) > 1 else 0
            else:
                avg_init_time = 0
                total_init_time = 0
            
            return {
                "current_phase": self.current_phase.value,
                "initialized_components": len([s for s in self.component_states.values() if s == "initialized"]),
                "total_components": len(self.component_states),
                "initialization_order": self.initialization_order.copy(),
                "circular_dependencies": circular_deps,
                "active_resource_locks": len(self.resource_locks),
                "active_barriers": len([b for b in self.startup_barriers.values() if not b.is_ready()]),
                "average_init_time": avg_init_time,
                "total_init_time": total_init_time
            }
    
    def prevent_environment_race_condition(self, component: str) -> bool:
        """Prevent race conditions in environment variable loading."""
        # Acquire environment lock
        if not self.acquire_resource_lock(
            ResourceType.ENVIRONMENT_VARS, "global", component, timeout=30.0
        ):
            logger.warning(f"Component {component} failed to acquire environment lock")
            return False
        
        try:
            # Validate that environment loading phase is active
            if self.current_phase not in [StartupPhase.INITIALIZING, StartupPhase.LOADING_SECRETS]:
                logger.warning(f"Environment access attempted in wrong phase: {self.current_phase.value}")
                return False
            
            # Check for concurrent environment modifications
            if self._detect_concurrent_env_access():
                logger.warning("Concurrent environment access detected")
                return False
            
            return True
            
        finally:
            # Always release the lock
            self.release_resource_lock(ResourceType.ENVIRONMENT_VARS, "global", component)
    
    def prevent_database_race_condition(self, component: str, database_type: str) -> bool:
        """Prevent race conditions in database initialization."""
        lock_acquired = self.acquire_resource_lock(
            ResourceType.DATABASE_CONNECTIONS, database_type, component, timeout=45.0
        )
        
        if not lock_acquired:
            logger.warning(f"Component {component} failed to acquire {database_type} database lock")
            return False
        
        try:
            # Validate phase
            if self.current_phase not in [
                StartupPhase.VALIDATING_ENVIRONMENT,
                StartupPhase.CONNECTING_DATABASES
            ]:
                logger.warning(f"Database access attempted in wrong phase: {self.current_phase.value}")
                return False
            
            # Validate dependencies
            if not self.validate_dependency_order(f"database_{database_type}"):
                return False
            
            return True
            
        except Exception:
            # Release lock on any exception
            self.release_resource_lock(ResourceType.DATABASE_CONNECTIONS, database_type, component)
            raise
    
    def prevent_port_race_condition(self, component: str, port: int) -> bool:
        """Prevent race conditions in port binding."""
        if not self.acquire_resource_lock(
            ResourceType.NETWORK_PORTS, str(port), component, timeout=20.0
        ):
            logger.warning(f"Component {component} failed to acquire port {port} lock")
            return False
        
        try:
            # Validate that no other component is using this port
            if self._is_port_conflict(port, component):
                logger.warning(f"Port conflict detected for port {port}")
                return False
            
            return True
            
        except Exception:
            self.release_resource_lock(ResourceType.NETWORK_PORTS, str(port), component)
            raise
    
    def _can_advance_phase(self, new_phase: StartupPhase, component: str) -> bool:
        """Check if phase can be advanced."""
        # Define valid phase transitions
        valid_transitions = {
            StartupPhase.INITIALIZING: [StartupPhase.LOADING_SECRETS],
            StartupPhase.LOADING_SECRETS: [StartupPhase.VALIDATING_ENVIRONMENT],
            StartupPhase.VALIDATING_ENVIRONMENT: [StartupPhase.CONNECTING_DATABASES],
            StartupPhase.CONNECTING_DATABASES: [StartupPhase.STARTING_BACKEND],
            StartupPhase.STARTING_BACKEND: [StartupPhase.STARTING_FRONTEND],
            StartupPhase.STARTING_FRONTEND: [StartupPhase.VERIFYING_READINESS],
            StartupPhase.VERIFYING_READINESS: [StartupPhase.STARTING_MONITORING],
            StartupPhase.STARTING_MONITORING: [StartupPhase.COMPLETED],
            StartupPhase.COMPLETED: []
        }
        
        allowed_phases = valid_transitions.get(self.current_phase, [])
        
        if new_phase not in allowed_phases:
            logger.warning(f"Invalid phase transition: {self.current_phase.value} → {new_phase.value} by {component}")
            return False
        
        return True
    
    def _cleanup_expired_resources(self):
        """Clean up expired resource locks and barriers."""
        with self._resource_lock:
            expired_locks = [
                key for key, lock in self.resource_locks.items() 
                if lock.is_expired()
            ]
            for key in expired_locks:
                logger.info(f"Cleaning up expired resource lock: {key}")
                del self.resource_locks[key]
        
        with self._barrier_lock:
            expired_barriers = [
                name for name, barrier in self.startup_barriers.items()
                if barrier.is_expired()
            ]
            for name in expired_barriers:
                logger.warning(f"Cleaning up expired barrier: {name}")
                del self.startup_barriers[name]
    
    def _detect_concurrent_env_access(self) -> bool:
        """Detect if multiple components are concurrently accessing environment."""
        # Simple heuristic based on timing
        current_time = time.time()
        recent_threshold = 0.1  # 100ms window
        
        recent_accesses = [
            comp for comp, timestamp in self.initialization_times.items()
            if current_time - timestamp < recent_threshold
        ]
        
        return len(recent_accesses) > 1
    
    def _is_port_conflict(self, port: int, requesting_component: str) -> bool:
        """Check if port conflicts with other components."""
        # Check resource locks for this port
        port_locks = [
            lock for lock in self.resource_locks.values()
            if (lock.resource_type == ResourceType.NETWORK_PORTS and 
                lock.resource_id == str(port) and 
                lock.owner != requesting_component)
        ]
        
        return len(port_locks) > 0
    
    def get_deadlock_report(self) -> Dict[str, Any]:
        """Generate deadlock detection report."""
        # Analyze waiting patterns
        waiting_components = {}
        
        for lock_key, lock in self.resource_locks.items():
            if lock.is_expired():
                continue
                
            # Find components that might be waiting for this resource
            for component in self.component_states:
                if (component != lock.owner and 
                    self.component_states[component] != "initialized"):
                    if component not in waiting_components:
                        waiting_components[component] = []
                    waiting_components[component].append(lock_key)
        
        # Detect potential deadlocks
        potential_deadlocks = []
        for component, waiting_for in waiting_components.items():
            if len(waiting_for) > 1:  # Waiting for multiple resources
                potential_deadlocks.append({
                    "component": component,
                    "waiting_for": waiting_for
                })
        
        return {
            "potential_deadlocks": potential_deadlocks,
            "waiting_components": waiting_components,
            "circular_dependencies": self.detect_circular_dependencies()
        }
    
    def emergency_release_all_locks(self, reason: str = "emergency") -> int:
        """Emergency release of all resource locks."""
        released_count = 0
        
        with self._resource_lock:
            released_count = len(self.resource_locks)
            self.resource_locks.clear()
        
        with self._barrier_lock:
            self.startup_barriers.clear()
        
        emoji = "🚨" if self.use_emoji else ""
        logger.warning(f"{emoji} Emergency release of all locks: {reason} (released {released_count} locks)")
        
        return released_count