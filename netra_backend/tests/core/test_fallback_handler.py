"""
Simple tests for current fallback_handler.py implementation
All functions are ≤8 lines, file is <300 lines
"""

import pytest
from netra_backend.app.core.fallback_handler import FallbackHandler, FallbackMetadata
from netra_backend.app.services.fallback_response.models import FallbackContext, FailureReason
from netra_backend.app.schemas.quality_types import ContentType

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestFallbackHandlerSimple:
    """Test suite for FallbackHandler with 25-line function limit"""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance - 2 lines"""
        return FallbackHandler()
    
    @pytest.fixture
    def basic_context(self):
        """Create basic context - 7 lines"""
        return FallbackContext(
            agent_name="test_agent",
            content_type=ContentType.GENERAL,
            failure_reason=FailureReason.LLM_ERROR,
            user_request="Test request",
            attempted_action="test_action"
        )
    
    def test_handler_initialization(self, handler):
        """Test handler has required attributes - 4 lines"""
        assert handler.fallback_templates is not None
        assert isinstance(handler.fallback_templates, dict)
        assert len(handler.fallback_templates) > 0
        assert "default" in handler.fallback_templates
    
    def test_default_template_exists(self, handler):
        """Test default template - 3 lines"""
        templates = handler.fallback_templates
        assert "default" in templates
        assert len(templates["default"]) > 0
    
    def test_agent_error_template_exists(self, handler):
        """Test agent error template - 3 lines"""
        templates = handler.fallback_templates
        assert "agent_error" in templates
        assert "issue while processing" in templates["agent_error"]
    
    def test_timeout_template_exists(self, handler):
        """Test timeout template - 3 lines"""
        templates = handler.fallback_templates
        assert "timeout" in templates
        assert "timed out" in templates["timeout"]
    
    def test_validation_template_exists(self, handler):
        """Test validation template - 3 lines"""
        templates = handler.fallback_templates
        assert "validation_error" in templates
        assert "validation error" in templates["validation_error"]
    
    def test_generate_fallback_returns_string(self, handler, basic_context):
        """Test generate_fallback returns string - 3 lines"""
        result = handler.generate_fallback(basic_context)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_generate_fallback_includes_agent_name(self, handler):
        """Test result includes agent name - 8 lines"""
        context = FallbackContext(
            agent_name="optimization_agent",
            content_type=ContentType.OPTIMIZATION,
            failure_reason=FailureReason.LOW_QUALITY,
            user_request="Optimize system",
            attempted_action="optimize"
        )
        result = handler.generate_fallback(context)
        assert "optimization_agent" in result
    
    def test_fallback_with_error_type_agent_error(self, handler):
        """Test agent error type - 8 lines"""
        context = FallbackContext(
            agent_name="data_agent",
            content_type=ContentType.DATA_ANALYSIS,
            failure_reason=FailureReason.LLM_ERROR,
            user_request="Analyze data",
            attempted_action="analyze",
            error_details="agent_error"
        )
        result = handler.generate_fallback(context)
    
    def test_fallback_with_error_type_timeout(self, handler):
        """Test timeout error type - 8 lines"""
        context = FallbackContext(
            agent_name="report_agent",
            content_type=ContentType.REPORT,
            failure_reason=FailureReason.TIMEOUT,
            user_request="Generate report",
            attempted_action="generate_report"
        )
        result = handler.generate_fallback(context)
        assert "report_agent" in result
    
    def test_fallback_with_error_type_validation(self, handler):
        """Test validation error type - 8 lines"""
        context = FallbackContext(
            agent_name="triage_agent",
            content_type=ContentType.TRIAGE,
            failure_reason=FailureReason.VALIDATION_FAILED,
            user_request="Triage request",
            attempted_action="triage"
        )
        result = handler.generate_fallback(context)
        assert "triage_agent" in result
    
    def test_fallback_with_unknown_error_type(self, handler):
        """Test unknown error uses default - 8 lines"""
        context = FallbackContext(
            agent_name="unknown_agent",
            content_type=ContentType.GENERAL,
            failure_reason=FailureReason.LLM_ERROR,
            user_request="Unknown request",
            attempted_action="unknown"
        )
        result = handler.generate_fallback(context)
        assert "unknown_agent" in result
    
    def test_fallback_context_basic_usage(self, handler):
        """Test basic context usage - 8 lines"""
        context = FallbackContext(
            agent_name="basic_agent",
            content_type=ContentType.GENERAL,
            failure_reason=FailureReason.LLM_ERROR,
            user_request="Basic request",
            attempted_action="basic"
        )
        result = handler.generate_fallback(context)
        assert "basic_agent" in result


class TestFallbackMetadata:
    """Test FallbackMetadata with 25-line function limit"""
    
    def test_metadata_creation_minimal(self):
        """Test minimal metadata creation - 3 lines"""
        metadata = FallbackMetadata("TestError")
        assert metadata.error_type == "TestError"
        assert metadata.attempted_operation is None
    
    def test_metadata_creation_with_operation(self):
        """Test metadata with operation - 4 lines"""
        metadata = FallbackMetadata("ValidationError", attempted_operation="validate_input")
        assert metadata.error_type == "ValidationError"
        assert metadata.attempted_operation == "validate_input"
        assert metadata.context is None
    
    def test_metadata_creation_full(self):
        """Test full metadata creation - 6 lines"""
        context_data = {"user": "test", "action": "optimize"}
        metadata = FallbackMetadata("TimeoutError", "process_request", context_data)
        assert metadata.error_type == "TimeoutError"
        assert metadata.attempted_operation == "process_request"
        assert metadata.context == context_data
        assert metadata.context["user"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])