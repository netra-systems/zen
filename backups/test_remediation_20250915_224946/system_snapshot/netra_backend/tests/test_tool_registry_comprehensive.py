"""
Comprehensive test runner for UnifiedToolRegistry

Demonstrates that the registry works correctly with the new get_tool_categories method.
"""

import asyncio
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Fix Unicode encoding for Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from netra_backend.app.services.unified_tool_registry import (
    UnifiedToolRegistry,
    UnifiedTool,
    ToolExecutionResult
)


async def test_registry_functionality():
    """Test all registry functionality"""
    print("\n=== Testing UnifiedToolRegistry ===\n")
    
    # Create registry
    registry = UnifiedToolRegistry()
    print("[U+2713] Registry created")
    
    # Test empty registry
    assert registry.get_tool_categories() == []
    print("[U+2713] Empty registry returns empty categories")
    
    # Create test tools
    tool1 = UnifiedTool(
        id="analyzer",
        name="Data Analyzer",
        description="Analyzes data patterns",
        category="analysis",
        version="1.0.0"
    )
    
    tool2 = UnifiedTool(
        id="optimizer",
        name="Cost Optimizer",
        description="Optimizes costs",
        category="optimization",
        version="1.0.0"
    )
    
    tool3 = UnifiedTool(
        id="reporter",
        name="Report Generator",
        description="Generates reports",
        category="analysis",
        version="1.0.0"
    )
    
    # Register tools
    registry.register_tool(tool1)
    registry.register_tool(tool2)
    registry.register_tool(tool3)
    print("[U+2713] Tools registered successfully")
    
    # Test get_tool
    retrieved = registry.get_tool("analyzer")
    assert retrieved == tool1
    print("[U+2713] Tool retrieval works")
    
    # Test list_tools
    all_tools = registry.list_tools()
    assert len(all_tools) == 3
    print(f"[U+2713] List tools returns {len(all_tools)} tools")
    
    # Test category filter
    analysis_tools = registry.list_tools(category="analysis")
    assert len(analysis_tools) == 2
    print(f"[U+2713] Category filter works (found {len(analysis_tools)} analysis tools)")
    
    # Test get_tool_categories
    categories = registry.get_tool_categories()
    assert len(categories) == 2
    print(f"[U+2713] get_tool_categories returns {len(categories)} categories")
    
    # Verify category counts
    for cat in categories:
        if cat["name"] == "analysis":
            assert cat["count"] == 2
            print(f"  - Analysis category has {cat['count']} tools")
        elif cat["name"] == "optimization":
            assert cat["count"] == 1
            print(f"  - Optimization category has {cat['count']} tool")
    
    # Test tool execution without handler
    result = await registry.execute_tool("analyzer", {}, {})
    assert result.success is False
    assert "No handler" in result.error
    print("[U+2713] Tool execution without handler fails gracefully")
    
    # Test with handler
    async def test_handler(params, context):
        return {"status": "success", "result": params.get("input", "no input")}
    
    registry._tool_handlers["analyzer"] = test_handler
    
    result = await registry.execute_tool(
        "analyzer",
        {"input": "test data"},
        {"user": "tester"}
    )
    assert result.success is True
    assert result.result["status"] == "success"
    print("[U+2713] Tool execution with handler succeeds")
    
    # Test permissions
    has_perm = registry.check_permission("analyzer", "user123", "execute")
    assert has_perm is True
    print("[U+2713] Permission checking works")
    
    # Test clear
    registry.clear()
    assert len(registry._tools) == 0
    assert len(registry._tool_handlers) == 0
    assert registry.get_tool_categories() == []
    print("[U+2713] Registry clear works")
    
    print("\n=== All tests passed! ===\n")


async def test_error_scenarios():
    """Test error handling scenarios"""
    print("\n=== Testing Error Scenarios ===\n")
    
    registry = UnifiedToolRegistry()
    
    # Test tool without category attribute
    class MockTool:
        def __init__(self):
            self.id = "mock_tool"
            self.name = "Mock Tool"
            # No category attribute
    
    mock_tool = MockTool()
    registry._tools["mock_tool"] = mock_tool
    
    categories = registry.get_tool_categories()
    assert len(categories) == 1
    assert categories[0]["name"] == "default"
    print("[U+2713] Tools without category default to 'default' category")
    
    # Test non-existent tool execution
    result = await registry.execute_tool("non_existent", {}, {})
    assert result.success is False
    assert "not found" in result.error
    print("[U+2713] Non-existent tool execution fails with proper error")
    
    # Test handler exception
    async def failing_handler(params, context):
        raise ValueError("Intentional error")
    
    registry._tools["failing"] = UnifiedTool(
        id="failing",
        name="Failing Tool",
        description="",
        category="test",
        version="1.0.0"
    )
    registry._tool_handlers["failing"] = failing_handler
    
    result = await registry.execute_tool("failing", {}, {})
    assert result.success is False
    assert "Intentional error" in result.error
    print("[U+2713] Handler exceptions are caught and returned as errors")
    
    print("\n=== Error handling tests passed! ===\n")


async def main():
    """Run all tests"""
    try:
        await test_registry_functionality()
        await test_error_scenarios()
        
        print("\n" + "="*50)
        print(" PASS:  ALL TESTS PASSED SUCCESSFULLY!")
        print("="*50 + "\n")
        
        print("Summary:")
        print("- UnifiedToolRegistry.get_tool_categories() works correctly")
        print("- Category counting and grouping functions properly")
        print("- Tools without category attribute default to 'default'")
        print("- All error scenarios are handled gracefully")
        print("- The fix for the missing method has been successful")
        
    except Exception as e:
        print(f"\n FAIL:  Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())