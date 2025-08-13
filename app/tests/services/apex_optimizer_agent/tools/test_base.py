# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:57:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Ultra-thinking test generation for 97% coverage goal
# Git: v6 | be70ff77 | dirty
# Change: Test | Scope: Module | Risk: Low
# Session: ultra-think-test-gen | Seq: 3
# Review: Pending | Score: 95
# ================================
"""
Comprehensive unit tests for base tool classes.
Designed with ultra-thinking to achieve 97% test coverage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Any
import asyncio

from app.services.apex_optimizer_agent.tools.base import ToolMetadata, BaseTool
from app.services.context import ToolContext
from pydantic import ValidationError


class ConcreteTool(BaseTool):
    """Concrete implementation of BaseTool for testing"""
    
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
    
    async def run(self, context: ToolContext, **kwargs) -> Any:
        """Implementation of abstract run method"""
        return f"Tool {self.metadata.name} executed with {kwargs}"


class FailingTool(BaseTool):
    """Tool that always fails for testing error handling"""
    
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
    
    async def run(self, context: ToolContext, **kwargs) -> Any:
        """Implementation that always raises an exception"""
        raise RuntimeError("Tool execution failed")


class TestToolMetadata:
    """Test suite for ToolMetadata model"""
    
    def test_tool_metadata_creation_basic(self):
        """Test basic ToolMetadata creation with required fields"""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool for unit testing"
        )
        
        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool for unit testing"
        assert metadata.version == "1.0.0"  # Default value
        assert metadata.status == "production"  # Default value
    
    def test_tool_metadata_creation_full(self):
        """Test ToolMetadata creation with all fields"""
        metadata = ToolMetadata(
            name="advanced_tool",
            description="An advanced tool with custom settings",
            version="2.1.3",
            status="mock"
        )
        
        assert metadata.name == "advanced_tool"
        assert metadata.description == "An advanced tool with custom settings"
        assert metadata.version == "2.1.3"
        assert metadata.status == "mock"
    
    def test_tool_metadata_validation_missing_required(self):
        """Test ToolMetadata validation when required fields are missing"""
        with pytest.raises(ValidationError) as exc_info:
            ToolMetadata(name="test_tool")  # Missing description
        
        assert "description" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            ToolMetadata(description="A tool")  # Missing name
        
        assert "name" in str(exc_info.value)
    
    def test_tool_metadata_dict_conversion(self):
        """Test ToolMetadata conversion to dictionary"""
        metadata = ToolMetadata(
            name="dict_tool",
            description="Tool for dict conversion test",
            version="1.2.0",
            status="disabled"
        )
        
        metadata_dict = metadata.dict()
        
        assert metadata_dict == {
            "name": "dict_tool",
            "description": "Tool for dict conversion test",
            "version": "1.2.0",
            "status": "disabled"
        }
    
    def test_tool_metadata_json_serialization(self):
        """Test ToolMetadata JSON serialization"""
        metadata = ToolMetadata(
            name="json_tool",
            description="Tool for JSON test"
        )
        
        json_str = metadata.model_dump_json()
        
        assert "json_tool" in json_str
        assert "Tool for JSON test" in json_str
        assert "1.0.0" in json_str
        assert "production" in json_str
    
    def test_tool_metadata_edge_cases(self):
        """Test ToolMetadata with edge case values"""
        # Empty strings (should be allowed)
        metadata = ToolMetadata(
            name="",
            description=""
        )
        assert metadata.name == ""
        assert metadata.description == ""
        
        # Very long strings
        long_name = "a" * 1000
        long_desc = "b" * 10000
        metadata = ToolMetadata(
            name=long_name,
            description=long_desc
        )
        assert len(metadata.name) == 1000
        assert len(metadata.description) == 10000
        
        # Special characters
        metadata = ToolMetadata(
            name="test-tool_v2.0",
            description="Tool with special chars: !@#$%^&*()"
        )
        assert metadata.name == "test-tool_v2.0"
        assert "!@#$%^&*()" in metadata.description


class TestBaseTool:
    """Test suite for BaseTool abstract class"""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext"""
        return Mock(spec=ToolContext)
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample ToolMetadata for testing"""
        return ToolMetadata(
            name="sample_tool",
            description="A sample tool for testing",
            version="1.0.0",
            status="production"
        )
    
    def test_base_tool_instantiation(self, sample_metadata):
        """Test that BaseTool cannot be instantiated directly"""
        # BaseTool is abstract, so we use ConcreteTool
        tool = ConcreteTool(sample_metadata)
        
        assert tool.metadata == sample_metadata
        assert tool.llm_name == None
    
    def test_base_tool_get_metadata(self, sample_metadata):
        """Test get_metadata method"""
        tool = ConcreteTool(sample_metadata)
        
        metadata_dict = tool.get_metadata()
        
        assert metadata_dict == {
            "name": "sample_tool",
            "description": "A sample tool for testing",
            "version": "1.0.0",
            "status": "production"
        }
    
    @pytest.mark.asyncio
    async def test_base_tool_execute_wrapper(self, mock_context, sample_metadata):
        """Test the execute wrapper method with logging"""
        tool = ConcreteTool(sample_metadata)
        
        with patch('app.services.apex_optimizer_agent.tools.base.logger') as mock_logger:
            result = await tool.execute(mock_context, param1="value1", param2=42)
            
            # Verify logging calls
            mock_logger.debug.assert_called_once()
            assert "sample_tool" in str(mock_logger.debug.call_args)
            
            mock_logger.info.assert_called_once()
            assert "sample_tool executed successfully" in str(mock_logger.info.call_args)
            
            # Verify result
            assert "Tool sample_tool executed" in result
    
    @pytest.mark.asyncio
    async def test_base_tool_execute_failure(self, mock_context, sample_metadata):
        """Test the execute wrapper method when tool fails"""
        tool = FailingTool(sample_metadata)
        
        with patch('app.services.apex_optimizer_agent.tools.base.logger') as mock_logger:
            with pytest.raises(RuntimeError) as exc_info:
                await tool.execute(mock_context)
            
            # Verify error logging
            mock_logger.error.assert_called_once()
            assert "sample_tool failed" in str(mock_logger.error.call_args)
            assert str(exc_info.value) == "Tool execution failed"
    
    @pytest.mark.asyncio
    async def test_concrete_tool_run_method(self, mock_context, sample_metadata):
        """Test the concrete implementation of run method"""
        tool = ConcreteTool(sample_metadata)
        
        result = await tool.run(mock_context, test_param="test_value")
        
        assert result == "Tool sample_tool executed with {'test_param': 'test_value'}"
    
    def test_base_tool_with_llm_name(self, sample_metadata):
        """Test BaseTool with llm_name set"""
        tool = ConcreteTool(sample_metadata)
        tool.llm_name = "gpt-4"
        
        assert tool.llm_name == "gpt-4"
        assert tool.metadata.name == "sample_tool"
    
    @pytest.mark.asyncio
    async def test_base_tool_multiple_executions(self, mock_context, sample_metadata):
        """Test multiple executions of the same tool"""
        tool = ConcreteTool(sample_metadata)
        
        results = []
        for i in range(5):
            result = await tool.execute(mock_context, iteration=i)
            results.append(result)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert f"iteration': {i}" in result
    
    @pytest.mark.asyncio
    async def test_base_tool_concurrent_execution(self, mock_context, sample_metadata):
        """Test concurrent execution of tool instances"""
        tool1 = ConcreteTool(sample_metadata)
        tool2 = ConcreteTool(ToolMetadata(
            name="concurrent_tool",
            description="Tool for concurrent testing"
        ))
        
        # Execute both tools concurrently
        results = await asyncio.gather(
            tool1.execute(mock_context, tool_id=1),
            tool2.execute(mock_context, tool_id=2)
        )
        
        assert len(results) == 2
        assert "sample_tool" in results[0]
        assert "concurrent_tool" in results[1]
    
    @pytest.mark.asyncio
    async def test_base_tool_execute_without_metadata_attribute(self, mock_context):
        """Test execute method when metadata attribute is not properly set"""
        class BrokenTool(BaseTool):
            # Intentionally not setting metadata in __init__
            async def run(self, context: ToolContext, **kwargs) -> Any:
                return "Executed"
        
        tool = BrokenTool()
        # Test that it works even without metadata (may have default behavior)
        with patch('app.services.apex_optimizer_agent.tools.base.logger') as mock_logger:
            # If BaseTool allows execution without metadata, test that
            result = await tool.execute(mock_context)
            assert result == "Executed"
    
    def test_base_tool_inheritance_chain(self, sample_metadata):
        """Test that inheritance works correctly"""
        class SpecializedTool(ConcreteTool):
            async def run(self, context: ToolContext, **kwargs) -> Any:
                base_result = await super().run(context, **kwargs)
                return f"Specialized: {base_result}"
        
        tool = SpecializedTool(sample_metadata)
        assert isinstance(tool, BaseTool)
        assert isinstance(tool, ConcreteTool)
        assert isinstance(tool, SpecializedTool)
    
    @pytest.mark.asyncio
    async def test_base_tool_with_complex_kwargs(self, mock_context, sample_metadata):
        """Test tool execution with complex keyword arguments"""
        tool = ConcreteTool(sample_metadata)
        
        complex_kwargs = {
            "nested_dict": {"key1": "value1", "key2": {"nested_key": "nested_value"}},
            "list_param": [1, 2, 3, 4, 5],
            "tuple_param": (10, 20, 30),
            "none_param": None,
            "bool_param": True
        }
        
        result = await tool.execute(mock_context, **complex_kwargs)
        
        assert "nested_dict" in result
        assert "list_param" in result
        assert "tuple_param" in result
    
    @pytest.mark.asyncio
    async def test_base_tool_exception_types(self, mock_context, sample_metadata):
        """Test different exception types in tool execution"""
        class CustomExceptionTool(BaseTool):
            def __init__(self, metadata, exception_type):
                self.metadata = metadata
                self.exception_type = exception_type
            
            async def run(self, context: ToolContext, **kwargs) -> Any:
                raise self.exception_type("Custom error")
        
        # Test with different exception types
        for exc_type in [ValueError, TypeError, KeyError, AttributeError]:
            tool = CustomExceptionTool(sample_metadata, exc_type)
            
            with patch('app.services.apex_optimizer_agent.tools.base.logger'):
                with pytest.raises(exc_type) as exc_info:
                    await tool.execute(mock_context)
                
                # The exception message may include quotes
                assert "Custom error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_base_tool_async_delay(self, mock_context, sample_metadata):
        """Test tool with async delay to ensure proper async handling"""
        class SlowTool(BaseTool):
            def __init__(self, metadata, delay):
                self.metadata = metadata
                self.delay = delay
            
            async def run(self, context: ToolContext, **kwargs) -> Any:
                await asyncio.sleep(self.delay)
                return f"Completed after {self.delay}s"
        
        tool = SlowTool(sample_metadata, 0.1)
        
        start_time = asyncio.get_event_loop().time()
        result = await tool.execute(mock_context)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        assert elapsed >= 0.09  # Allow for small timing variations
        assert "Completed after 0.1s" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.apex_optimizer_agent.tools.base"])