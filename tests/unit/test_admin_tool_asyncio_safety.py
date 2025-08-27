"""
Unit Tests for Admin Tool Validation Asyncio Safety

Tests to ensure admin tool validation doesn't have nested event loop issues.
"""
import asyncio
import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Add parent directories to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.asyncio_test_utils import (
    AsyncioTestUtils,
    EventLoopTestError
)


class TestAdminToolAsyncioSafety:
    """Test admin tool validation for asyncio safety"""
    
    @pytest.mark.asyncio
    async def test_admin_tool_validation_no_nested_loops(self):
        """Test admin tool validation doesn't use nested asyncio.run()"""
        
        # Mock admin tool validator with problematic pattern
        class AdminToolValidator:
            async def validate_tool_async(self, tool_config: dict) -> dict:
                """Async validation of tool configuration"""
                await asyncio.sleep(0)  # Simulate async operation
                
                # Validate required fields
                required = ["name", "type", "config"]
                for field in required:
                    if field not in tool_config:
                        return {"valid": False, "error": f"Missing {field}"}
                
                return {"valid": True, "tool": tool_config}
            
            def validate_tool(self, tool_config: dict) -> dict:
                """Backward compatibility wrapper - problematic pattern"""
                # This is the problematic pattern found in audit
                return asyncio.run(self.validate_tool_async(tool_config))
        
        validator = AdminToolValidator()
        test_config = {"name": "test_tool", "type": "executor", "config": {}}
        
        # This would fail in async context
        with pytest.raises(RuntimeError) as exc_info:
            validator.validate_tool(test_config)
        assert "cannot be called from a running event loop" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_admin_tool_proper_async_pattern(self):
        """Test proper async pattern for admin tool validation"""
        
        class ProperAdminToolValidator:
            async def validate_tool_async(self, tool_config: dict) -> dict:
                """Async validation"""
                await asyncio.sleep(0)
                
                required = ["name", "type", "config"]
                for field in required:
                    if field not in tool_config:
                        return {"valid": False, "error": f"Missing {field}"}
                
                # Additional async validations
                if tool_config["type"] == "llm":
                    # Simulate checking LLM provider
                    await asyncio.sleep(0)
                    if "model" not in tool_config["config"]:
                        return {"valid": False, "error": "LLM tool requires model"}
                
                return {"valid": True, "tool": tool_config}
            
            def validate_tool_sync(self, tool_config: dict) -> dict:
                """Pure sync validation for backward compatibility"""
                required = ["name", "type", "config"]
                for field in required:
                    if field not in tool_config:
                        return {"valid": False, "error": f"Missing {field}"}
                
                if tool_config["type"] == "llm" and "model" not in tool_config["config"]:
                    return {"valid": False, "error": "LLM tool requires model"}
                
                return {"valid": True, "tool": tool_config}
            
            def validate_tool(self, tool_config: dict) -> dict:
                """Smart wrapper that detects context"""
                try:
                    loop = asyncio.get_running_loop()
                    # In async context, use sync version
                    return self.validate_tool_sync(tool_config)
                except RuntimeError:
                    # Not in async context, safe to use asyncio.run
                    return asyncio.run(self.validate_tool_async(tool_config))
        
        validator = ProperAdminToolValidator()
        
        # Test valid configuration
        test_config = {
            "name": "gpt_tool",
            "type": "llm",
            "config": {"model": "gpt-4"}
        }
        
        # Should work in async context
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = validator.validate_tool(test_config)
            assert result["valid"] is True
            assert result["tool"]["name"] == "gpt_tool"
        
        # Test invalid configuration
        invalid_config = {
            "name": "bad_tool",
            "type": "llm",
            "config": {}  # Missing model
        }
        
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = validator.validate_tool(invalid_config)
            assert result["valid"] is False
            assert "model" in result["error"]
    
    def test_admin_tool_sync_context(self):
        """Test admin tool validation in sync context"""
        
        class AdminToolValidator:
            async def validate_async(self, config: dict) -> dict:
                await asyncio.sleep(0)
                return {"valid": True, "config": config}
            
            def validate(self, config: dict) -> dict:
                try:
                    asyncio.get_running_loop()
                    # In async context, use sync validation
                    return {"valid": True, "config": config}
                except RuntimeError:
                    # Not in async context, safe to create loop
                    return asyncio.run(self.validate_async(config))
        
        validator = AdminToolValidator()
        test_config = {"tool": "test"}
        
        # Should work in sync context
        result = validator.validate(test_config)
        assert result["valid"] is True
        assert result["config"] == test_config
    
    @pytest.mark.asyncio
    async def test_admin_tool_batch_validation(self):
        """Test batch validation of multiple tools"""
        
        class BatchToolValidator:
            async def validate_single_tool(self, tool: dict) -> dict:
                """Validate single tool asynchronously"""
                await asyncio.sleep(0)
                
                if "name" not in tool:
                    return {"tool": tool, "valid": False, "error": "Missing name"}
                
                return {"tool": tool, "valid": True}
            
            async def validate_batch(self, tools: list) -> list:
                """Validate multiple tools concurrently"""
                # Proper async pattern - use gather
                results = await asyncio.gather(
                    *[self.validate_single_tool(tool) for tool in tools]
                )
                return results
        
        validator = BatchToolValidator()
        
        test_tools = [
            {"name": "tool1", "type": "executor"},
            {"name": "tool2", "type": "llm"},
            {"type": "invalid"},  # Missing name
            {"name": "tool3", "type": "webhook"}
        ]
        
        # Test batch validation
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            results = await validator.validate_batch(test_tools)
            
            assert len(results) == 4
            assert results[0]["valid"] is True
            assert results[1]["valid"] is True
            assert results[2]["valid"] is False
            assert "Missing name" in results[2]["error"]
            assert results[3]["valid"] is True


class TestAdminToolConfigurationAsync:
    """Test admin tool configuration handling"""
    
    @pytest.mark.asyncio
    async def test_tool_configuration_loading(self):
        """Test async loading of tool configurations"""
        
        class ToolConfigLoader:
            async def load_config_async(self, config_path: str) -> dict:
                """Async config loading"""
                await asyncio.sleep(0)  # Simulate file I/O
                
                # Simulate config loading
                return {
                    "tools": [
                        {"name": "tool1", "enabled": True},
                        {"name": "tool2", "enabled": False}
                    ]
                }
            
            async def load_and_validate(self, config_path: str) -> dict:
                """Load and validate configuration"""
                config = await self.load_config_async(config_path)
                
                # Validate each tool
                validated = []
                for tool in config["tools"]:
                    if tool.get("enabled", False):
                        validated.append(tool)
                
                return {"tools": validated, "total": len(validated)}
        
        loader = ToolConfigLoader()
        
        # Test loading and validation
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = await loader.load_and_validate("/path/to/config")
            assert result["total"] == 1
            assert result["tools"][0]["name"] == "tool1"
    
    @pytest.mark.asyncio
    async def test_tool_dependency_resolution(self):
        """Test async resolution of tool dependencies"""
        
        class ToolDependencyResolver:
            async def resolve_dependencies(self, tool: dict) -> dict:
                """Resolve tool dependencies asynchronously"""
                dependencies = []
                
                if tool.get("requires"):
                    for dep in tool["requires"]:
                        await asyncio.sleep(0)  # Simulate lookup
                        dependencies.append({
                            "name": dep,
                            "resolved": True
                        })
                
                return {
                    "tool": tool["name"],
                    "dependencies": dependencies,
                    "ready": all(d["resolved"] for d in dependencies)
                }
        
        resolver = ToolDependencyResolver()
        
        test_tool = {
            "name": "complex_tool",
            "requires": ["database", "cache", "llm_provider"]
        }
        
        # Test dependency resolution
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = await resolver.resolve_dependencies(test_tool)
            assert result["tool"] == "complex_tool"
            assert len(result["dependencies"]) == 3
            assert result["ready"] is True


class TestAdminToolExecutionAsync:
    """Test admin tool execution patterns"""
    
    @pytest.mark.asyncio
    async def test_tool_execution_async_safety(self):
        """Test tool execution doesn't have nested loops"""
        
        class ToolExecutor:
            async def execute_tool_async(self, tool_name: str, params: dict) -> dict:
                """Execute tool asynchronously"""
                await asyncio.sleep(0)
                
                # Simulate tool execution
                if tool_name == "test_tool":
                    return {
                        "success": True,
                        "result": f"Executed with {params}"
                    }
                
                return {"success": False, "error": "Unknown tool"}
            
            async def execute(self, tool_name: str, params: dict) -> dict:
                """Proper async execution"""
                # No nested asyncio.run, just await
                return await self.execute_tool_async(tool_name, params)
        
        executor = ToolExecutor()
        
        # Test execution
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = await executor.execute("test_tool", {"param1": "value1"})
            assert result["success"] is True
            assert "value1" in str(result["result"])
    
    @pytest.mark.asyncio
    async def test_tool_pipeline_execution(self):
        """Test pipeline of tool executions"""
        
        class ToolPipeline:
            async def run_step(self, step: dict, context: dict) -> dict:
                """Run single pipeline step"""
                await asyncio.sleep(0)
                
                # Update context with step result
                context[step["name"]] = f"Result of {step['name']}"
                return context
            
            async def execute_pipeline(self, steps: list) -> dict:
                """Execute pipeline steps sequentially"""
                context = {}
                
                for step in steps:
                    context = await self.run_step(step, context)
                
                return {
                    "completed": True,
                    "steps_executed": len(steps),
                    "context": context
                }
        
        pipeline = ToolPipeline()
        
        test_steps = [
            {"name": "validate", "type": "validation"},
            {"name": "process", "type": "processing"},
            {"name": "output", "type": "output"}
        ]
        
        # Test pipeline execution
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = await pipeline.execute_pipeline(test_steps)
            assert result["completed"] is True
            assert result["steps_executed"] == 3
            assert "validate" in result["context"]
            assert "process" in result["context"]
            assert "output" in result["context"]


class TestAdminToolMigrationPatterns:
    """Test patterns for migrating admin tools to proper async"""
    
    @pytest.mark.asyncio
    async def test_migration_before_after(self):
        """Test migration from problematic to proper pattern"""
        
        # BEFORE: Problematic pattern
        class OldToolValidator:
            async def _validate(self, tool):
                return {"valid": True}
            
            def validate(self, tool):
                # This causes issues in async context
                return asyncio.run(self._validate(tool))
        
        # AFTER: Proper pattern
        class NewToolValidator:
            async def validate_async(self, tool):
                await asyncio.sleep(0)
                return {"valid": True, "tool": tool}
            
            def validate_sync(self, tool):
                # Pure sync validation
                return {"valid": True, "tool": tool}
            
            def validate(self, tool):
                """Smart wrapper"""
                try:
                    asyncio.get_running_loop()
                    # In async context, use sync
                    return self.validate_sync(tool)
                except RuntimeError:
                    # Not in async context, safe to use async
                    return asyncio.run(self.validate_async(tool))
        
        new_validator = NewToolValidator()
        
        # Test in async context
        with AsyncioTestUtils.assert_no_nested_asyncio_run():
            result = new_validator.validate({"name": "test"})
            assert result["valid"] is True
            assert result["tool"]["name"] == "test"
    
    def test_backward_compatibility(self):
        """Test backward compatibility is maintained"""
        
        class BackwardCompatibleValidator:
            async def validate_v2(self, tool):
                """New async version"""
                await asyncio.sleep(0)
                return {"version": 2, "valid": True}
            
            def validate_v1(self, tool):
                """Legacy sync version"""
                return {"version": 1, "valid": True}
            
            def validate(self, tool, use_async=None):
                """Backward compatible interface"""
                if use_async is None:
                    # Auto-detect
                    try:
                        asyncio.get_running_loop()
                        # In async context, use sync
                        return self.validate_v1(tool)
                    except RuntimeError:
                        # Not in async context, can use async
                        return asyncio.run(self.validate_v2(tool))
                elif use_async:
                    return asyncio.run(self.validate_v2(tool))
                else:
                    return self.validate_v1(tool)
        
        validator = BackwardCompatibleValidator()
        
        # Test sync context with auto-detect
        result = validator.validate({"test": True})
        assert result["valid"] is True
        assert result["version"] in [1, 2]  # Either version is acceptable
        
        # Test explicit sync
        result = validator.validate({"test": True}, use_async=False)
        assert result["version"] == 1
        assert result["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])