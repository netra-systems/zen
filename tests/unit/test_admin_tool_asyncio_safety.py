"""
Unit Tests for Admin Tool Validation Asyncio Safety

Tests to ensure admin tool validation doesn't have nested event loop issues.
"""
import asyncio
import sys
from pathlib import Path
import pytest
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestAdminToolAsyncioSafety:
    """Test admin tool validation for asyncio safety"""

    @pytest.mark.asyncio
    async def test_admin_tool_validation_no_nested_loops(self):
        """Test admin tool validation doesn't use nested asyncio.run()"""

        class AdminToolValidator:
            async def validate_tool_async(self, tool_config: dict) -> dict:
                """Async validation of tool configuration"""
                await asyncio.sleep(0)  # Simulate async operation

                # Validate required fields
                required = ["name", "type", "config"]
                for field in required:
                    if field not in tool_config:
                        await asyncio.sleep(0)
                        return {"valid": False, "error": f"Missing field: {field}"}

                return {"valid": True, "tool": tool_config}

            def validate_tool_sync(self, tool_config: dict) -> dict:
                """Pure sync validation for async context"""
                required = ["name", "type", "config"]
                for field in required:
                    if field not in tool_config:
                        return {"valid": False, "error": f"Missing field: {field}"}
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

        validator = AdminToolValidator()

        # Test valid configuration
        test_config = {
            "name": "gpt_tool",
            "type": "llm", 
            "config": {"model": "gpt-4"}
        }

        # Should work in async context
        result = validator.validate_tool(test_config)
        assert result["valid"] is True
        assert result["tool"]["name"] == "gpt_tool"

        # Test invalid configuration
        invalid_config = {
            "name": "bad_tool",
            "type": "llm"
            # Missing config
        }

        result = validator.validate_tool(invalid_config)
        assert result["valid"] is False
        assert "config" in result["error"]

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
                    await asyncio.sleep(0)
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
        results = await validator.validate_batch(test_tools)

        assert len(results) == 4
        assert results[0]["valid"] is True
        assert results[1]["valid"] is True
        assert results[2]["valid"] is False
        assert "Missing name" in results[2]["error"]
        assert results[3]["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])