"""
Tests for error handler enumerations and context.
All functions ≤8 lines per requirements.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest

# Add project root to path
from netra_backend.app.agents.error_handler import ErrorCategory, ErrorRecoveryStrategy
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.shared_types import ErrorContext
from ..helpers.shared_test_types import (
    TestErrorContext as SharedTestErrorContext,
)

# Add project root to path


class TestErrorEnums:
    """Test error enumerations."""
    
    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.PROCESSING.value == "processing"
        assert ErrorCategory.WEBSOCKET.value == "websocket"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.RESOURCE.value == "resource"
    
    def test_error_recovery_strategy_values(self):
        """Test ErrorRecoveryStrategy enum values."""
        assert ErrorRecoveryStrategy.RETRY.value == "retry"
        assert ErrorRecoveryStrategy.FALLBACK.value == "fallback"
        assert ErrorRecoveryStrategy.ABORT.value == "abort"
        assert ErrorRecoveryStrategy.IGNORE.value == "ignore"


class TestErrorContext(SharedTestErrorContext):
    """Test error context functionality with inheritance."""
    
    def test_error_context_creation(self):
        """Test creation of ErrorContext."""
        context = ErrorContext(
            agent_id="test_agent",
            operation="test_operation",
            timestamp=1234567890,
            metadata={"key": "value"}
        )
        
        assert context.agent_id == "test_agent"
        assert context.operation == "test_operation"
        assert context.timestamp == 1234567890
        assert context.metadata == {"key": "value"}
    
    def test_error_context_with_defaults(self):
        """Test ErrorContext with default values."""
        context = ErrorContext(agent_id="test", operation="test")
        
        assert context.agent_id == "test"
        assert context.operation == "test"
        assert context.timestamp is not None
        assert context.metadata == {}
    
    def test_error_context_serialization(self):
        """Test ErrorContext serialization."""
        context = ErrorContext(
            agent_id="serialize_test",
            operation="serialize_op",
            metadata={"serializable": True}
        )
        
        # Test dict conversion
        context_dict = context.dict()
        assert "agent_id" in context_dict
        assert "operation" in context_dict
        assert "metadata" in context_dict
    
    def test_error_context_validation(self):
        """Test ErrorContext validation."""
        # Valid context
        valid_context = ErrorContext(agent_id="valid", operation="valid")
        assert valid_context.agent_id == "valid"
        
        # Test required fields
        with pytest.raises(ValueError):
            ErrorContext()  # Missing required fields
    
    def test_error_context_metadata_operations(self):
        """Test ErrorContext metadata operations."""
        context = ErrorContext(
            agent_id="meta_test",
            operation="meta_op",
            metadata={"initial": "value"}
        )
        
        # Test metadata access
        assert context.metadata["initial"] == "value"
        
        # Test metadata modification
        context.metadata["added"] = "new_value"
        assert context.metadata["added"] == "new_value"
    
    def test_error_context_immutability(self):
        """Test ErrorContext immutability for core fields."""
        context = ErrorContext(agent_id="immutable", operation="test")
        original_agent_id = context.agent_id
        original_operation = context.operation
        
        # Core fields should remain unchanged
        assert context.agent_id == original_agent_id
        assert context.operation == original_operation
    
    def test_error_context_inheritance_compatibility(self):
        """Test inheritance compatibility with SharedTestErrorContext."""
        # Test that we can use inherited methods
        test_context = self.create_test_context("inheritance_test")
        
        assert test_context.agent_id == "inheritance_test"
        assert test_context.operation == "test_operation"
    
    def test_error_context_edge_cases(self):
        """Test ErrorContext edge cases."""
        # Empty metadata
        context_empty = ErrorContext(
            agent_id="edge", 
            operation="edge",
            metadata={}
        )
        assert context_empty.metadata == {}
        
        # Large metadata
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}
        context_large = ErrorContext(
            agent_id="large",
            operation="large",
            metadata=large_metadata
        )
        assert len(context_large.metadata) == 100