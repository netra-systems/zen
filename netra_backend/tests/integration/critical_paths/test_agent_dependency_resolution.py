"""Agent Dependency Resolution L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (complex AI workflows)
- Business Goal: Reliable multi-agent orchestration
- Value Impact: Protects $7K MRR from dependency-related failures
- Strategic Impact: Enables sophisticated AI agent collaboration

Critical Path: Dependency declaration -> Resolution -> Injection -> Validation -> Execution
Coverage: Real dependency injection, circular detection, lazy loading
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Set, Type, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.db.database_manager import DatabaseManager as ConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class DependencyScope(Enum):
    """Dependency scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

class DependencyLifetime(Enum):
    """Dependency lifetimes."""
    APPLICATION = "application"
    SESSION = "session"
    REQUEST = "request"

@dataclass
class DependencyMetadata:
    """Metadata for a dependency."""
    name: str
    implementation_type: Type
    scope: DependencyScope
    lifetime: DependencyLifetime
    dependencies: List[str] = field(default_factory=list)
    optional: bool = False
    lazy: bool = False
    factory_method: Optional[str] = None
    configuration: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)

class DependencyProtocol(Protocol):
    """Protocol for dependency injection."""
    
    async def initialize(self) -> None:
        """Initialize the dependency."""
        ...
    
    async def cleanup(self) -> None:
        """Clean up the dependency."""
        ...

class DependencyProxy:
    """Lazy loading proxy for dependencies."""
    
    def __init__(self, dependency_name: str, resolver):
        self._dependency_name = dependency_name
        self._resolver = resolver
        self._instance = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the dependency is initialized."""
        if not self._initialized:
            self._instance = await self._resolver.resolve(self._dependency_name, force_eager=True)
            self._initialized = True
    
    def __getattr__(self, name):
        """Proxy attribute access."""
        if not self._initialized:
            asyncio.create_task(self._ensure_initialized())
        return getattr(self._instance, name)
    
    async def get_instance(self):
        """Get the actual instance."""
        await self._ensure_initialized()
        return self._instance

class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""
    
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle)}")

class DependencyResolutionError(Exception):
    """Raised when dependency resolution fails."""
    pass

class DependencyRegistry:
    """Registry for dependency metadata."""
    
    def __init__(self):
        self.dependencies: Dict[str, DependencyMetadata] = {}
        self.aliases: Dict[str, str] = {}
        
    def register(self, metadata: DependencyMetadata) -> None:
        """Register a dependency."""
        self.dependencies[metadata.name] = metadata
        
    def register_alias(self, alias: str, target: str) -> None:
        """Register an alias for a dependency."""
        self.aliases[alias] = target
        
    def get_canonical_name(self, name: str) -> str:
        """Get the canonical name for a dependency (resolves aliases)."""
        return self.aliases.get(name, name)
        
    def get_metadata(self, name: str) -> Optional[DependencyMetadata]:
        """Get dependency metadata."""
        # Resolve alias if present
        actual_name = self.get_canonical_name(name)
        return self.dependencies.get(actual_name)
        
    def get_all_dependencies(self) -> List[str]:
        """Get all registered dependency names."""
        return list(self.dependencies.keys())
        
    def has_dependency(self, name: str) -> bool:
        """Check if a dependency is registered."""
        actual_name = self.aliases.get(name, name)
        return actual_name in self.dependencies

class DependencyGraph:
    """Builds and analyzes dependency graphs."""
    
    def __init__(self, registry: DependencyRegistry):
        self.registry = registry
        self.graph: Dict[str, Set[str]] = {}
        
    def build_graph(self) -> None:
        """Build the dependency graph."""
        self.graph.clear()
        
        # Initialize all nodes
        for name in self.registry.dependencies.keys():
            self.graph[name] = set()
        
        # Add edges: if A depends on B, then B -> A (B comes before A)
        for name, metadata in self.registry.dependencies.items():
            for dep_name in metadata.dependencies:
                if dep_name in self.graph:
                    self.graph[dep_name].add(name)
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        visited = set()
        recursion_stack = set()
        cycles = []
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)
            
            for neighbor in self.graph.get(node, set()):
                if neighbor in recursion_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor, path.copy())
            
            recursion_stack.remove(node)
        
        for node in self.graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def topological_sort(self) -> List[str]:
        """Perform topological sort of dependencies."""
        if self.detect_cycles():
            raise CircularDependencyError(self.detect_cycles()[0])
        
        in_degree = {node: 0 for node in self.graph}
        
        # Calculate in-degrees
        for node in self.graph:
            for neighbor in self.graph[node]:
                if neighbor in in_degree:
                    in_degree[neighbor] += 1
        
        # Queue for nodes with no incoming edges
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.graph.get(node, set()):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result

class DependencyContainer:
    """Container for managing dependency instances."""
    
    def __init__(self):
        self.singletons: Dict[str, Any] = {}
        self.scoped_instances: Dict[str, Dict[str, Any]] = {}
        self.current_scope: Optional[str] = None
        
    def set_scope(self, scope_id: str) -> None:
        """Set the current scope."""
        self.current_scope = scope_id
        if scope_id not in self.scoped_instances:
            self.scoped_instances[scope_id] = {}
    
    def clear_scope(self, scope_id: str) -> None:
        """Clear a scope."""
        if scope_id in self.scoped_instances:
            del self.scoped_instances[scope_id]
    
    def store_instance(self, name: str, instance: Any, scope: DependencyScope) -> None:
        """Store an instance based on its scope."""
        if scope == DependencyScope.SINGLETON:
            self.singletons[name] = instance
        elif scope == DependencyScope.SCOPED and self.current_scope:
            self.scoped_instances[self.current_scope][name] = instance
        # TRANSIENT instances are not stored
    
    def get_instance(self, name: str, scope: DependencyScope) -> Optional[Any]:
        """Get an instance based on its scope."""
        if scope == DependencyScope.SINGLETON:
            return self.singletons.get(name)
        elif scope == DependencyScope.SCOPED and self.current_scope:
            return self.scoped_instances.get(self.current_scope, {}).get(name)
        # TRANSIENT instances are always created new
        return None

class DependencyResolver:
    """Resolves and injects dependencies."""
    
    def __init__(self, registry: DependencyRegistry):
        self.registry = registry
        self.container = DependencyContainer()
        self.graph = DependencyGraph(registry)
        self.resolving: Set[str] = set()  # Track currently resolving dependencies
        self._locks: Dict[str, asyncio.Lock] = {}  # Per-dependency locks
        
    async def resolve(self, name: str, context: Optional[Dict[str, Any]] = None, force_eager: bool = False) -> Any:
        """Resolve a dependency by name."""
        # Resolve alias to canonical name
        canonical_name = self.registry.get_canonical_name(name)
        
        metadata = self.registry.get_metadata(name)
        if not metadata:
            raise DependencyResolutionError(f"Dependency '{name}' not registered")
        
        # Check if instance already exists (use canonical name for storage)
        existing_instance = self.container.get_instance(canonical_name, metadata.scope)
        if existing_instance:
            return existing_instance
        
        # Handle lazy loading (unless forced to be eager)
        if metadata.lazy and not force_eager:
            return DependencyProxy(canonical_name, self)
        
        # Get or create lock for this dependency
        if canonical_name not in self._locks:
            self._locks[canonical_name] = asyncio.Lock()
        
        async with self._locks[canonical_name]:
            # Double-check if instance was created while waiting for lock
            existing_instance = self.container.get_instance(canonical_name, metadata.scope)
            if existing_instance:
                return existing_instance
            
            # Check for circular dependency
            if canonical_name in self.resolving:
                raise CircularDependencyError([canonical_name])
            
            # Resolve dependencies
            self.resolving.add(canonical_name)
            try:
                instance = await self._create_instance(metadata, context)
                self.container.store_instance(canonical_name, instance, metadata.scope)
                return instance
            finally:
                self.resolving.remove(canonical_name)
    
    async def _create_instance(self, metadata: DependencyMetadata, context: Optional[Dict[str, Any]]) -> Any:
        """Create an instance of a dependency."""
        # Resolve sub-dependencies first
        resolved_deps = {}
        for dep_name in metadata.dependencies:
            resolved_deps[dep_name] = await self.resolve(dep_name, context)
        
        # Create instance
        if metadata.factory_method:
            factory = getattr(metadata.implementation_type, metadata.factory_method)
            instance = factory(**resolved_deps, **metadata.configuration)
        else:
            instance = metadata.implementation_type(**resolved_deps, **metadata.configuration)
        
        # Initialize if it has an initialize method
        if hasattr(instance, 'initialize'):
            await instance.initialize()
        
        return instance
    
    async def resolve_all(self, names: List[str]) -> Dict[str, Any]:
        """Resolve multiple dependencies."""
        # Build dependency graph and sort
        self.graph.build_graph()
        sorted_names = self.graph.topological_sort()
        
        # Filter to only requested names and their dependencies
        required_deps = set()
        for name in names:
            required_deps.update(self._get_all_dependencies(name))
        
        # Resolve in dependency order
        resolved = {}
        for dep_name in sorted_names:
            if dep_name in required_deps:
                resolved[dep_name] = await self.resolve(dep_name)
        
        return {name: resolved[name] for name in names if name in resolved}
    
    def _get_all_dependencies(self, name: str) -> Set[str]:
        """Get all dependencies (recursive) for a given name."""
        result = {name}
        metadata = self.registry.get_metadata(name)
        
        if metadata:
            for dep in metadata.dependencies:
                result.update(self._get_all_dependencies(dep))
        
        return result
    
    async def cleanup_scope(self, scope_id: str) -> None:
        """Clean up a dependency scope."""
        if scope_id in self.container.scoped_instances:
            instances = self.container.scoped_instances[scope_id]
            
            # Cleanup instances in reverse dependency order
            for instance in reversed(list(instances.values())):
                if hasattr(instance, 'cleanup'):
                    await instance.cleanup()
            
            self.container.clear_scope(scope_id)

# Test service implementations
class MockDatabaseService:
    """Mock database service for testing."""
    
    def __init__(self, connection_string: str = "mock://localhost"):
        self.connection_string = connection_string
        self.is_connected = False
        
    async def initialize(self):
        """Initialize the database connection."""
        await asyncio.sleep(0.01)  # Simulate connection time
        self.is_connected = True
        logger.info(f"Database connected to {self.connection_string}")
    
    async def cleanup(self):
        """Clean up the database connection."""
        self.is_connected = False
        logger.info("Database connection closed")
    
    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a query."""
        if not self.is_connected:
            raise Exception("Database not connected")
        return [{"result": "mock_data"}]

class MockCacheService:
    """Mock cache service for testing."""
    
    def __init__(self, database_service: MockDatabaseService, redis_url: str = "redis://localhost"):
        self.database_service = database_service
        self.redis_url = redis_url
        self.cache = {}
        
    async def initialize(self):
        """Initialize the cache service."""
        await asyncio.sleep(0.01)
        logger.info(f"Cache service initialized with Redis at {self.redis_url}")
    
    async def cleanup(self):
        """Clean up the cache service."""
        self.cache.clear()
        logger.info("Cache service cleaned up")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self.cache.get(key)
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self.cache[key] = value

class MockAgentService:
    """Mock agent service for testing."""
    
    def __init__(self, database_service: MockDatabaseService, cache_service: MockCacheService, model_name: str = LLMModel.GEMINI_2_5_FLASH.value):
        self.database_service = database_service
        self.cache_service = cache_service
        self.model_name = model_name
        self.agent_id = f"agent_{int(time.time() * 1000)}"
        
    async def initialize(self):
        """Initialize the agent service."""
        await asyncio.sleep(0.01)
        logger.info(f"Agent service {self.agent_id} initialized with model {self.model_name}")
    
    async def cleanup(self):
        """Clean up the agent service."""
        logger.info(f"Agent service {self.agent_id} cleaned up")
    
    async def process_request(self, request: str) -> str:
        """Process a request."""
        # Use cache and database services
        cached_result = await self.cache_service.get(f"request:{request}")
        if cached_result:
            return cached_result
        
        # Query database
        db_results = await self.database_service.query(f"SELECT * FROM responses WHERE request = '{request}'")
        result = f"Processed: {request} with {self.model_name}"
        
        # Cache result
        await self.cache_service.set(f"request:{request}", result)
        return result

class DependencyManager:
    """Manages dependency resolution testing."""
    
    def __init__(self):
        self.registry = DependencyRegistry()
        self.resolver = DependencyResolver(self.registry)
        
    def setup_test_dependencies(self):
        """Set up test dependencies."""
        # Register database service
        db_metadata = DependencyMetadata(
            name="database_service",
            implementation_type=MockDatabaseService,
            scope=DependencyScope.SINGLETON,
            lifetime=DependencyLifetime.APPLICATION,
            configuration={"connection_string": "test://localhost:5432"}
        )
        self.registry.register(db_metadata)
        
        # Register cache service (depends on database)
        cache_metadata = DependencyMetadata(
            name="cache_service",
            implementation_type=MockCacheService,
            scope=DependencyScope.SINGLETON,
            lifetime=DependencyLifetime.APPLICATION,
            dependencies=["database_service"],
            configuration={"redis_url": "redis://test:6379"}
        )
        self.registry.register(cache_metadata)
        
        # Register agent service (depends on both)
        agent_metadata = DependencyMetadata(
            name="agent_service",
            implementation_type=MockAgentService,
            scope=DependencyScope.SCOPED,
            lifetime=DependencyLifetime.SESSION,
            dependencies=["database_service", "cache_service"],
            configuration={"model_name": "gpt-4-test"}
        )
        self.registry.register(agent_metadata)
        
        # Register lazy dependency
        lazy_agent_metadata = DependencyMetadata(
            name="lazy_agent_service",
            implementation_type=MockAgentService,
            scope=DependencyScope.TRANSIENT,
            lifetime=DependencyLifetime.REQUEST,
            dependencies=["database_service", "cache_service"],
            lazy=True,
            configuration={"model_name": LLMModel.GEMINI_2_5_FLASH.value}
        )
        self.registry.register(lazy_agent_metadata)
        
        # Register alias
        self.registry.register_alias("db", "database_service")
        self.registry.register_alias("cache", "cache_service")

@pytest.fixture
def dependency_manager():
    """Create dependency manager for testing."""
    manager = DependencyManager()
    manager.setup_test_dependencies()
    return manager

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_basic_dependency_registration(dependency_manager):
    """Test basic dependency registration."""
    manager = dependency_manager
    
    # Test dependency registration
    assert manager.registry.has_dependency("database_service")
    assert manager.registry.has_dependency("cache_service")
    assert manager.registry.has_dependency("agent_service")
    
    # Test metadata retrieval
    db_metadata = manager.registry.get_metadata("database_service")
    assert db_metadata is not None
    assert db_metadata.scope == DependencyScope.SINGLETON
    assert db_metadata.implementation_type == MockDatabaseService

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_simple_dependency_resolution(dependency_manager):
    """Test simple dependency resolution."""
    manager = dependency_manager
    
    # Resolve database service (no dependencies)
    db_service = await manager.resolver.resolve("database_service")
    
    assert isinstance(db_service, MockDatabaseService)
    assert db_service.is_connected is True
    assert db_service.connection_string == "test://localhost:5432"

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_dependency_chain_resolution(dependency_manager):
    """Test dependency chain resolution."""
    manager = dependency_manager
    
    # Resolve agent service (has chain of dependencies)
    manager.resolver.container.set_scope("test_scope")
    agent_service = await manager.resolver.resolve("agent_service")
    
    assert isinstance(agent_service, MockAgentService)
    assert isinstance(agent_service.database_service, MockDatabaseService)
    assert isinstance(agent_service.cache_service, MockCacheService)
    assert agent_service.model_name == "gpt-4-test"
    
    # Verify services are initialized
    assert agent_service.database_service.is_connected is True

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_singleton_scope_behavior(dependency_manager):
    """Test singleton scope behavior."""
    manager = dependency_manager
    
    # Resolve same dependency multiple times
    db_service1 = await manager.resolver.resolve("database_service")
    db_service2 = await manager.resolver.resolve("database_service")
    
    # Should be the same instance
    assert db_service1 is db_service2

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_scoped_dependency_behavior(dependency_manager):
    """Test scoped dependency behavior."""
    manager = dependency_manager
    
    # Test first scope
    manager.resolver.container.set_scope("scope1")
    agent1 = await manager.resolver.resolve("agent_service")
    agent1_again = await manager.resolver.resolve("agent_service")
    
    # Should be same instance within scope
    assert agent1 is agent1_again
    
    # Test second scope
    manager.resolver.container.set_scope("scope2")
    agent2 = await manager.resolver.resolve("agent_service")
    
    # Should be different instance in different scope
    assert agent1 is not agent2

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_dependency_aliases(dependency_manager):
    """Test dependency aliases."""
    manager = dependency_manager
    
    # Resolve using alias
    db_via_alias = await manager.resolver.resolve("db")
    db_direct = await manager.resolver.resolve("database_service")
    
    # Should resolve to same instance
    assert db_via_alias is db_direct

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_lazy_dependency_loading(dependency_manager):
    """Test lazy dependency loading."""
    manager = dependency_manager
    
    # Resolve lazy dependency
    lazy_agent = await manager.resolver.resolve("lazy_agent_service")
    
    # Should be a proxy, not the actual instance
    assert isinstance(lazy_agent, DependencyProxy)
    
    # Get actual instance
    actual_instance = await lazy_agent.get_instance()
    assert isinstance(actual_instance, MockAgentService)

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_circular_dependency_detection(dependency_manager):
    """Test circular dependency detection."""
    manager = dependency_manager
    
    # Create circular dependencies
    circular_a = DependencyMetadata(
        name="circular_a",
        implementation_type=MockDatabaseService,
        scope=DependencyScope.SINGLETON,
        lifetime=DependencyLifetime.APPLICATION,
        dependencies=["circular_b"]
    )
    
    circular_b = DependencyMetadata(
        name="circular_b",
        implementation_type=MockCacheService,
        scope=DependencyScope.SINGLETON,
        lifetime=DependencyLifetime.APPLICATION,
        dependencies=["circular_a"]
    )
    
    manager.registry.register(circular_a)
    manager.registry.register(circular_b)
    
    # Should detect circular dependency
    with pytest.raises(CircularDependencyError):
        await manager.resolver.resolve("circular_a")

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_dependency_graph_analysis(dependency_manager):
    """Test dependency graph analysis."""
    manager = dependency_manager
    
    # Build dependency graph
    manager.resolver.graph.build_graph()
    
    # Test cycle detection (should be none)
    cycles = manager.resolver.graph.detect_cycles()
    assert len(cycles) == 0
    
    # Test topological sort
    sorted_deps = manager.resolver.graph.topological_sort()
    
    # Database should come before cache, cache before agent
    db_index = sorted_deps.index("database_service")
    cache_index = sorted_deps.index("cache_service")
    agent_index = sorted_deps.index("agent_service")
    
    assert db_index < cache_index < agent_index

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_bulk_dependency_resolution(dependency_manager):
    """Test bulk dependency resolution."""
    manager = dependency_manager
    
    # Resolve multiple dependencies at once
    manager.resolver.container.set_scope("bulk_test")
    resolved = await manager.resolver.resolve_all(["agent_service", "cache_service"])
    
    assert "agent_service" in resolved
    assert "cache_service" in resolved
    assert isinstance(resolved["agent_service"], MockAgentService)
    assert isinstance(resolved["cache_service"], MockCacheService)

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_dependency_cleanup(dependency_manager):
    """Test dependency cleanup."""
    manager = dependency_manager
    
    # Create scoped dependencies
    scope_id = "cleanup_test"
    manager.resolver.container.set_scope(scope_id)
    agent_service = await manager.resolver.resolve("agent_service")
    
    # Verify service is created
    assert isinstance(agent_service, MockAgentService)
    
    # Cleanup scope
    await manager.resolver.cleanup_scope(scope_id)
    
    # Verify scope is cleared
    assert scope_id not in manager.resolver.container.scoped_instances

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_dependency_error_handling(dependency_manager):
    """Test dependency error handling."""
    manager = dependency_manager
    
    # Test resolving non-existent dependency
    with pytest.raises(DependencyResolutionError):
        await manager.resolver.resolve("non_existent_service")
    
    # Test resolving dependency with missing sub-dependency
    broken_metadata = DependencyMetadata(
        name="broken_service",
        implementation_type=MockAgentService,
        scope=DependencyScope.SINGLETON,
        lifetime=DependencyLifetime.APPLICATION,
        dependencies=["missing_dependency"]
    )
    manager.registry.register(broken_metadata)
    
    with pytest.raises(DependencyResolutionError):
        await manager.resolver.resolve("broken_service")

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_concurrent_dependency_resolution(dependency_manager):
    """Test concurrent dependency resolution."""
    manager = dependency_manager
    
    # Resolve same singleton concurrently
    tasks = [
        manager.resolver.resolve("database_service")
        for _ in range(10)
    ]
    
    services = await asyncio.gather(*tasks)
    
    # All should be the same instance
    first_service = services[0]
    assert all(service is first_service for service in services)

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_dependency_resolution_performance(dependency_manager):
    """Benchmark dependency resolution performance."""
    manager = dependency_manager
    
    # Warm up
    manager.resolver.container.set_scope("perf_test")
    await manager.resolver.resolve("agent_service")
    
    # Benchmark resolution
    start_time = time.time()
    
    tasks = []
    for i in range(100):
        if i % 10 == 0:  # New scope every 10 resolutions
            manager.resolver.container.set_scope(f"perf_scope_{i}")
        task = manager.resolver.resolve("agent_service")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    resolution_time = time.time() - start_time
    
    assert len(results) == 100
    assert all(isinstance(result, MockAgentService) for result in results)
    
    # Performance assertions
    assert resolution_time < 2.0  # 100 resolutions in under 2 seconds
    avg_resolution_time = resolution_time / 100
    assert avg_resolution_time < 0.02  # Average resolution under 20ms
    
    logger.info(f"Performance: {avg_resolution_time*1000:.1f}ms per dependency resolution")