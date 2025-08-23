"""
Tool Registry Validation Tests
Tests tool validation functionality
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import sys
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from langchain_core.tools import BaseTool

from netra_backend.app.core.exceptions_base import NetraException

from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.tests.services.test_tool_registry_registration_core import MockTool

class TestToolRegistryValidation:
    """Test tool validation functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return MagicMock()
    
    @pytest.fixture
    def validator_registry(self, mock_db_session):
        """Registry with validation enabled"""
        registry = ToolRegistry(mock_db_session)
        registry.enable_validation = True
        return registry
    
    def test_tool_interface_validation(self, validator_registry):
        """Test tool interface validation"""
        # Valid tool
        valid_tool = MockTool(name="valid_tool", description="Valid tool description")
        assert validator_registry.validate_tool_interface(valid_tool) == True
        
        # Invalid tool - missing required methods
        invalid_tool = MagicMock()
        invalid_tool.name = "invalid_tool"
        invalid_tool.description = "Invalid tool"
        del invalid_tool._run  # Remove required method
        
        assert validator_registry.validate_tool_interface(invalid_tool) == False
    
    def test_tool_metadata_validation(self, validator_registry):
        """Test tool metadata validation"""
        # Valid metadata
        valid_metadata = {
            "version": "1.0.0",
            "author": "test_author",
            "tags": ["test", "validation"],
            "created_at": datetime.now(UTC).isoformat(),
            "dependencies": ["langchain"]
        }
        
        assert validator_registry.validate_metadata(valid_metadata) == True
        
        # Invalid metadata - missing required fields
        invalid_metadata = {
            "tags": ["test"]
            # Missing required fields
        }
        
        assert validator_registry.validate_metadata(invalid_metadata) == False
    
    def test_tool_security_validation(self, validator_registry):
        """Test tool security validation"""
        # Safe tool
        safe_tool = MockTool(name="safe_tool", description="Safe tool")
        assert validator_registry.validate_tool_security(safe_tool) == True
        
        # Potentially unsafe tool
        class UnsafeTool(BaseTool):
            name: str = "unsafe_tool"
            description: str = "Tool with file system access"
            
            def _run(self, query: str) -> str:
                import os
                return os.listdir("/")  # File system access
        
        unsafe_tool = UnsafeTool()
        
        # Should fail security validation if strict mode enabled
        validator_registry.strict_security = True
        assert validator_registry.validate_tool_security(unsafe_tool) == False
    
    def test_tool_performance_validation(self, validator_registry):
        """Test tool performance validation"""
        # Setup performance thresholds
        validator_registry.performance_thresholds = {
            "max_execution_time": 5.0,  # seconds
            "max_memory_usage": 100 * 1024 * 1024,  # 100MB
            "max_cpu_usage": 80  # 80%
        }
        
        # Fast tool
        fast_tool = MockTool(name="fast_tool", description="Fast executing tool")
        
        # Mock performance measurement
        with patch.object(validator_registry, 'measure_tool_performance') as mock_measure:
            mock_measure.return_value = {
                "execution_time": 0.5,
                "memory_usage": 10 * 1024 * 1024,  # 10MB
                "cpu_usage": 30
            }
            
            assert validator_registry.validate_tool_performance(fast_tool) == True
        
        # Slow tool
        with patch.object(validator_registry, 'measure_tool_performance') as mock_measure:
            mock_measure.return_value = {
                "execution_time": 10.0,  # Exceeds threshold
                "memory_usage": 50 * 1024 * 1024,
                "cpu_usage": 40
            }
            
            assert validator_registry.validate_tool_performance(fast_tool) == False
    
    def test_tool_compatibility_validation(self, validator_registry):
        """Test tool compatibility validation"""
        # Setup compatibility matrix
        compatibility_matrix = {
            "triage": {
                "compatible_with": ["data", "reporting"],
                "incompatible_with": ["optimizations_core"]
            }
        }
        
        validator_registry.set_compatibility_matrix(compatibility_matrix)
        
        # Compatible tools
        assert validator_registry.validate_compatibility("triage", "data") == True
        assert validator_registry.validate_compatibility("triage", "reporting") == True
        
        # Incompatible tools
        assert validator_registry.validate_compatibility("triage", "optimizations_core") == False
    
    def test_tool_dependency_validation(self, validator_registry):
        """Test tool dependency validation"""
        # Tool with valid dependencies
        tool_with_deps = MockTool(name="dependent_tool", description="Tool with dependencies")
        dependencies = ["numpy", "pandas", "sklearn"]
        
        # Mock dependency check
        with patch.object(validator_registry, 'check_dependencies') as mock_check:
            mock_check.return_value = {"numpy": True, "pandas": True, "sklearn": False}
            
            validation_result = validator_registry.validate_dependencies(tool_with_deps, dependencies)
            
            assert validation_result["valid"] == False
            assert "sklearn" in validation_result["missing_dependencies"]
    
    def test_tool_version_compatibility_validation(self, validator_registry):
        """Test tool version compatibility validation"""
        # Setup version requirements
        version_requirements = {
            "min_python": "3.8",
            "max_python": "3.11",
            "langchain": ">=0.1.0,<1.0.0"
        }
        
        # Mock system version
        with patch('sys.version_info', (3, 9, 0)):
            with patch.object(validator_registry, 'get_package_version') as mock_version:
                mock_version.return_value = "0.5.0"  # langchain version
                
                assert validator_registry.validate_version_compatibility(version_requirements) == True
        
        # Incompatible Python version
        with patch('sys.version_info', (3, 12, 0)):  # Too new
            assert validator_registry.validate_version_compatibility(version_requirements) == False
    
    def test_tool_input_schema_validation(self, validator_registry):
        """Test tool input schema validation"""
        # Tool with schema
        tool = MockTool(name="schema_tool", description="Tool with schema")
        tool.args_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1}
            },
            "required": ["query"]
        }
        
        # Valid input
        valid_input = {"query": "test query", "limit": 10}
        assert validator_registry.validate_tool_input(tool, valid_input) == True
        
        # Invalid input - missing required field
        invalid_input = {"limit": 10}
        assert validator_registry.validate_tool_input(tool, invalid_input) == False
    
    def test_tool_output_validation(self, validator_registry):
        """Test tool output validation"""
        tool = MockTool(name="output_tool", description="Tool with output validation")
        
        # Valid output
        valid_output = "Valid tool output"
        assert validator_registry.validate_tool_output(tool, valid_output) == True
        
        # Invalid output - None
        invalid_output = None
        assert validator_registry.validate_tool_output(tool, invalid_output) == False
    
    def test_bulk_validation(self, validator_registry):
        """Test bulk validation of multiple tools"""
        tools = [
            MockTool(name="tool1", description="First tool"),
            MockTool(name="tool2", description="Second tool"),
            MockTool(name="tool3", description="Third tool")
        ]
        
        results = validator_registry.bulk_validate_tools(tools)
        
        assert len(results) == 3
        assert all(result["valid"] for result in results)
    
    def test_validation_error_reporting(self, validator_registry):
        """Test detailed validation error reporting"""
        # Create invalid tool
        invalid_tool = MagicMock()
        invalid_tool.name = ""  # Invalid name
        invalid_tool.description = "Valid description"
        
        with pytest.raises(NetraException) as exc_info:
            validator_registry.register_tool("data", invalid_tool)
        
        error_msg = str(exc_info.value)
        assert "validation" in error_msg.lower()
        assert "name" in error_msg.lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])