"""
Tool Registry Performance Tests
Tests performance aspects of tool registry
"""

import pytest
import time
import threading
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock

from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.tests.test_tool_registry_registration_core import MockTool

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestToolRegistryPerformance:
    """Test performance aspects of tool registry"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return MagicMock()
    
    @pytest.fixture
    def tool_registry(self, mock_db_session):
        """Create tool registry for performance testing"""
        return ToolRegistry(mock_db_session)
    
    async def test_large_scale_tool_registration(self, tool_registry):
        """Test registration performance with large number of tools"""
        # Create many tools
        tools = []
        for i in range(1000):
            tool = MockTool(
                name=f"performance_tool_{i}",
                description=f"Performance test tool number {i}"
            )
            tools.append(("triage", tool))
        
        # Measure registration time
        start_time = time.time()
        
        for category, tool in tools:
            tool_registry.register_tool(category, tool)
        
        registration_time = time.time() - start_time
        
        # Should register 1000 tools in reasonable time (< 5 seconds)
        assert registration_time < 5.0
        
        # Verify all tools registered
        registered_tools = tool_registry.get_tools(["triage"])
        assert len(registered_tools) == 1000
    
    def test_tool_discovery_performance(self, tool_registry):
        """Test discovery performance with many tools"""
        # Register many tools across categories
        for category in ["triage", "data", "optimizations_core"]:
            for i in range(100):
                tool = MockTool(
                    name=f"{category}_tool_{i}",
                    description=f"Tool {i} for {category}"
                )
                tool_registry.register_tool(category, tool)
        
        # Measure discovery time
        start_time = time.time()
        
        # Multiple discovery operations
        for _ in range(10):
            _ = tool_registry.get_tools(["triage", "data"])
            _ = tool_registry.find_tools_by_pattern("*_tool_5*")
            _ = tool_registry.fuzzy_search("tool")
        
        discovery_time = time.time() - start_time
        
        # Should complete discovery operations in reasonable time
        assert discovery_time < 2.0
    
    def test_concurrent_tool_access(self, tool_registry):
        """Test concurrent access to tool registry"""
        # Register some tools
        for i in range(50):
            tool = MockTool(name=f"concurrent_tool_{i}", description=f"Tool {i}")
            tool_registry.register_tool("triage", tool)
        
        results = []
        errors = []
        
        def concurrent_access():
            try:
                for _ in range(10):
                    tools = tool_registry.get_tools(["triage"])
                    results.append(len(tools))
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=concurrent_access)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Assert no errors and consistent results
        assert len(errors) == 0
        assert len(results) == 100  # 10 threads * 10 operations
        assert all(result == 50 for result in results)  # Consistent tool count
    
    def test_memory_usage_with_large_registry(self, tool_registry):
        """Test memory usage with large tool registry"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Register many tools
        for i in range(1000):
            tool = MockTool(
                name=f"memory_test_tool_{i}",
                description=f"Memory test tool {i}" * 100  # Large description
            )
            tool_registry.register_tool("data", tool)
        
        # Get memory usage after registration
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024
    
    def test_tool_search_performance(self, tool_registry):
        """Test search performance with complex queries"""
        # Register tools with various metadata
        for i in range(500):
            tool = MockTool(
                name=f"search_tool_{i}",
                description=f"Tool for searching data type {i % 10}"
            )
            tool_registry.register_tool("data", tool)
            
            # Add metadata
            tool_registry.add_tool_tags("data", tool.name, [f"tag_{i % 5}", f"category_{i % 3}"])
        
        # Measure search performance
        start_time = time.time()
        
        # Complex search operations
        for _ in range(50):
            _ = tool_registry.find_tools_by_tag("tag_1")
            _ = tool_registry.find_tools_by_pattern("*_tool_*")
            _ = tool_registry.fuzzy_search("search")
        
        search_time = time.time() - start_time
        
        # Should complete complex searches in reasonable time
        assert search_time < 3.0
    
    def test_bulk_operations_performance(self, tool_registry):
        """Test performance of bulk operations"""
        # Create large number of tools
        tools_data = {}
        for category in ["triage", "data", "optimizations_core"]:
            tools_data[category] = [
                MockTool(name=f"{category}_bulk_{i}", description=f"Bulk tool {i}")
                for i in range(300)
            ]
        
        # Measure bulk registration time
        start_time = time.time()
        tool_registry.bulk_register_tools(tools_data)
        bulk_time = time.time() - start_time
        
        # Should complete bulk operations efficiently
        assert bulk_time < 2.0
        
        # Verify all tools registered
        all_tools = tool_registry.get_tools(["triage", "data", "optimizations_core"])
        assert len(all_tools) == 900
    
    def test_cache_performance(self, tool_registry):
        """Test performance with caching enabled"""
        # Enable caching
        tool_registry.enable_caching = True
        
        # Register tools
        for i in range(100):
            tool = MockTool(name=f"cache_tool_{i}", description=f"Cache test tool {i}")
            tool_registry.register_tool("triage", tool)
        
        # First access - should cache results
        start_time = time.time()
        tools1 = tool_registry.get_tools(["triage"])
        first_access_time = time.time() - start_time
        
        # Second access - should be faster due to caching
        start_time = time.time()
        tools2 = tool_registry.get_tools(["triage"])
        second_access_time = time.time() - start_time
        
        # Cached access should be faster
        assert second_access_time < first_access_time
        assert len(tools1) == len(tools2) == 100
    
    def test_stress_test_tool_operations(self, tool_registry):
        """Stress test with mixed operations"""
        # Setup phase
        for i in range(200):
            tool = MockTool(name=f"stress_tool_{i}", description=f"Stress test tool {i}")
            tool_registry.register_tool("data", tool)
        
        # Stress test with mixed operations
        start_time = time.time()
        
        for _ in range(100):
            # Mix of different operations
            _ = tool_registry.get_tools(["data"])
            _ = tool_registry.find_tools_by_pattern("stress_tool_*")
            tool_registry.record_tool_usage(f"stress_tool_{_ % 200}", "test_user")
            
            if _ % 10 == 0:
                # Occasional heavy operations
                _ = tool_registry.get_recently_used_tools("test_user")
                _ = tool_registry.get_popular_tools()
        
        stress_time = time.time() - start_time
        
        # Should handle stress test within reasonable time
        assert stress_time < 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])