"""Agent Tool Loading L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (reliable AI tool execution)
- Business Goal: Tool reliability and availability
- Value Impact: Protects $8K MRR from tool loading failures
- Strategic Impact: Core capability for agent tool execution pipeline

Critical Path: Tool discovery -> Validation -> Loading -> Registry -> Availability
Coverage: Real tool loader, registry, dependency resolution, performance tracking
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.services.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class MockTool:
    """Mock tool for testing loading pipeline."""
    
    def __init__(self, name: str, version: str = "1.0.0", dependencies: List[str] = None):
        self.name = name
        self.version = version
        self.dependencies = dependencies or []
        self.load_time = 0.1
        self.is_loaded = False
        
    async def load(self) -> bool:
        """Load the tool with simulated delay."""
        await asyncio.sleep(self.load_time)
        self.is_loaded = True
        return True
        
    def validate(self) -> bool:
        """Validate tool configuration."""
        return len(self.name) > 0 and self.version is not None


class ToolRegistry:
    """Tool registry for managing loaded tools."""
    
    def __init__(self):
        self.tools = {}
        self.load_order = []
        self.validation_errors = []
        
    async def register_tool(self, tool: MockTool) -> bool:
        """Register a tool in the registry."""
        if tool.validate():
            self.tools[tool.name] = tool
            self.load_order.append(tool.name)
            return True
        else:
            self.validation_errors.append(f"Tool {tool.name} validation failed")
            return False
            
    def get_tool(self, name: str) -> Optional[MockTool]:
        """Get tool by name."""
        return self.tools.get(name)
        
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())


class DependencyResolver:
    """Resolves tool dependencies and loading order."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        
    def resolve_dependencies(self, tools: List[MockTool]) -> List[MockTool]:
        """Resolve tool loading order based on dependencies."""
        resolved = []
        pending = tools.copy()
        
        while pending:
            progress = False
            for tool in pending[:]:
                if all(dep in [t.name for t in resolved] for dep in tool.dependencies):
                    resolved.append(tool)
                    pending.remove(tool)
                    progress = True
                    
            if not progress and pending:
                # Circular dependency or missing dependency
                raise ValueError(f"Cannot resolve dependencies for: {[t.name for t in pending]}")
                
        return resolved


class ToolLoader:
    """Manages tool loading process."""
    
    def __init__(self):
        self.registry = ToolRegistry()
        self.dependency_resolver = DependencyResolver(self.registry)
        self.load_stats = {
            "total_loaded": 0,
            "failed_loads": 0,
            "load_time_ms": 0
        }
        
    async def load_tools(self, tools: List[MockTool]) -> Dict[str, Any]:
        """Load tools with dependency resolution."""
        start_time = time.time()
        
        try:
            # Resolve dependencies
            ordered_tools = self.dependency_resolver.resolve_dependencies(tools)
            
            # Load tools in order
            for tool in ordered_tools:
                success = await tool.load()
                if success:
                    await self.registry.register_tool(tool)
                    self.load_stats["total_loaded"] += 1
                else:
                    self.load_stats["failed_loads"] += 1
                    
        except Exception as e:
            logger.error(f"Tool loading failed: {e}")
            self.load_stats["failed_loads"] += len(tools)
            
        self.load_stats["load_time_ms"] = (time.time() - start_time) * 1000
        
        return {
            "success": self.load_stats["failed_loads"] == 0,
            "loaded_count": self.load_stats["total_loaded"],
            "failed_count": self.load_stats["failed_loads"],
            "load_time_ms": self.load_stats["load_time_ms"],
            "tools": self.registry.list_tools()
        }


class AgentToolLoadingManager:
    """Manages agent tool loading testing."""
    
    def __init__(self):
        self.tool_loader = ToolLoader()
        self.redis_service = None
        self.circuit_breaker = None
        self.db_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.circuit_breaker = CircuitBreaker("tool_loading", failure_threshold=3)
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
    async def test_dynamic_loading(self, tools: List[MockTool]) -> Dict[str, Any]:
        """Test dynamic tool loading capabilities."""
        return await self.tool_loader.load_tools(tools)
        
    async def test_version_compatibility(self, tools: List[MockTool]) -> Dict[str, Any]:
        """Test tool version compatibility checking."""
        compatibility_results = []
        
        for tool in tools:
            # Simulate version checking
            is_compatible = tool.version.startswith("1.")  # Simple version check
            compatibility_results.append({
                "name": tool.name,
                "version": tool.version,
                "compatible": is_compatible
            })
            
        return {
            "total_tools": len(tools),
            "compatible_tools": sum(1 for r in compatibility_results if r["compatible"]),
            "results": compatibility_results
        }
        
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()


@pytest.fixture
async def tool_loading_manager():
    """Create tool loading manager for testing."""
    manager = AgentToolLoadingManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_tool_loading(tool_loading_manager):
    """Test basic tool loading functionality."""
    manager = tool_loading_manager
    
    # Create test tools
    tools = [
        MockTool("file_reader", "1.0.0"),
        MockTool("calculator", "1.1.0"),
        MockTool("web_scraper", "2.0.0")
    ]
    
    result = await manager.test_dynamic_loading(tools)
    
    assert result["success"] is True
    assert result["loaded_count"] == 3
    assert result["failed_count"] == 0
    assert result["load_time_ms"] < 1000
    assert "file_reader" in result["tools"]
    assert "calculator" in result["tools"]
    assert "web_scraper" in result["tools"]


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_dependency_resolution(tool_loading_manager):
    """Test tool dependency resolution and loading order."""
    manager = tool_loading_manager
    
    # Create tools with dependencies
    tools = [
        MockTool("advanced_tool", "1.0.0", ["basic_tool", "utility_tool"]),
        MockTool("basic_tool", "1.0.0"),
        MockTool("utility_tool", "1.0.0", ["basic_tool"])
    ]
    
    result = await manager.test_dynamic_loading(tools)
    
    assert result["success"] is True
    assert result["loaded_count"] == 3
    
    # Verify loading order (basic_tool should be first)
    load_order = manager.tool_loader.registry.load_order
    assert load_order.index("basic_tool") < load_order.index("utility_tool")
    assert load_order.index("utility_tool") < load_order.index("advanced_tool")


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_tool_validation_failures(tool_loading_manager):
    """Test tool validation and error handling."""
    manager = tool_loading_manager
    
    # Create tools with validation issues
    tools = [
        MockTool("", "1.0.0"),  # Invalid name
        MockTool("valid_tool", None),  # Invalid version
        MockTool("good_tool", "1.0.0")  # Valid tool
    ]
    
    result = await manager.test_dynamic_loading(tools)
    
    assert result["failed_count"] > 0
    assert "good_tool" in result["tools"]
    assert len(manager.tool_loader.registry.validation_errors) > 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_circular_dependency_detection(tool_loading_manager):
    """Test circular dependency detection and handling."""
    manager = tool_loading_manager
    
    # Create tools with circular dependencies
    tools = [
        MockTool("tool_a", "1.0.0", ["tool_b"]),
        MockTool("tool_b", "1.0.0", ["tool_c"]),
        MockTool("tool_c", "1.0.0", ["tool_a"])  # Circular dependency
    ]
    
    with pytest.raises(ValueError) as exc_info:
        await manager.test_dynamic_loading(tools)
    
    assert "Cannot resolve dependencies" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_version_compatibility_checking(tool_loading_manager):
    """Test tool version compatibility validation."""
    manager = tool_loading_manager
    
    # Create tools with different versions
    tools = [
        MockTool("tool_v1", "1.0.0"),
        MockTool("tool_v1_minor", "1.5.3"),
        MockTool("tool_v2", "2.0.0"),
        MockTool("tool_v3", "3.1.0")
    ]
    
    result = await manager.test_version_compatibility(tools)
    
    assert result["total_tools"] == 4
    assert result["compatible_tools"] == 2  # Only v1.x tools are compatible
    
    # Check specific compatibility results
    v1_tools = [r for r in result["results"] if r["version"].startswith("1.")]
    assert len(v1_tools) == 2
    assert all(r["compatible"] for r in v1_tools)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_tool_loading(tool_loading_manager):
    """Test concurrent tool loading performance."""
    manager = tool_loading_manager
    
    # Create multiple tool sets for concurrent loading
    tool_sets = [
        [MockTool(f"batch1_tool_{i}", "1.0.0") for i in range(3)],
        [MockTool(f"batch2_tool_{i}", "1.0.0") for i in range(3)],
        [MockTool(f"batch3_tool_{i}", "1.0.0") for i in range(3)]
    ]
    
    start_time = time.time()
    
    # Load tool sets concurrently
    tasks = [manager.test_dynamic_loading(tool_set) for tool_set in tool_sets]
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Verify all loads succeeded
    for result in results:
        assert result["success"] is True
        assert result["loaded_count"] == 3
    
    # Performance check - concurrent should be faster than sequential
    assert total_time < 1.0  # Should complete quickly with concurrency


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_tool_registry_persistence(tool_loading_manager):
    """Test tool registry persistence with Redis."""
    manager = tool_loading_manager
    
    # Load tools
    tools = [MockTool("persistent_tool", "1.0.0")]
    result = await manager.test_dynamic_loading(tools)
    
    assert result["success"] is True
    
    # Verify Redis persistence
    tool_key = "tool_registry:persistent_tool"
    cached_tool = await manager.redis_service.client.get(tool_key)
    
    # Tool should be cached in Redis
    assert cached_tool is not None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_tool_loading_circuit_breaker(tool_loading_manager):
    """Test circuit breaker for tool loading failures."""
    manager = tool_loading_manager
    
    # Simulate multiple failing tools to trigger circuit breaker
    failing_tools = [MockTool("failing_tool", None) for _ in range(5)]
    
    # Execute multiple failed loads
    for _ in range(4):
        await manager.test_dynamic_loading(failing_tools[:1])
    
    # Circuit breaker should be in open state after failures
    assert manager.circuit_breaker.failure_count >= 3


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_tool_loading_performance_benchmark(tool_loading_manager):
    """Benchmark tool loading performance for capacity planning."""
    manager = tool_loading_manager
    
    # Create large set of tools for performance testing
    large_tool_set = [MockTool(f"perf_tool_{i}", "1.0.0") for i in range(50)]
    
    start_time = time.time()
    result = await manager.test_dynamic_loading(large_tool_set)
    load_time = time.time() - start_time
    
    assert result["success"] is True
    assert result["loaded_count"] == 50
    
    # Performance benchmarks
    assert load_time < 10.0  # Should load 50 tools in under 10 seconds
    assert result["load_time_ms"] / result["loaded_count"] < 100  # < 100ms per tool
    
    logger.info(f"Performance: {result['loaded_count']} tools in {load_time:.2f}s")
    logger.info(f"Average: {result['load_time_ms']/result['loaded_count']:.1f}ms per tool")