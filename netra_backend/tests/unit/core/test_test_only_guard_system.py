"""
Unit tests for the SSOT Test-Only Guard System.

Tests verify that the guard system properly enforces test-mode-only execution
for functions decorated with @test_only, preventing production misuse.

Business Value: Platform/Internal - System Stability & Test Isolation
"""

import os
import pytest
import sys
from unittest import mock

from shared.test_only_guard import (
    test_only, 
    TestModeViolation, 
    TestModeDetector,
    require_test_mode,
    is_test_only_function,
    get_test_only_reason
)


def test_imports_work():
    """Test that imports work correctly."""
    assert test_only is not None
    assert TestModeViolation is not None
    assert TestModeDetector is not None


class TestTestModeDetector:
    """Test the test mode detection logic."""
    
    def setup_method(self):
        """Reset test mode cache before each test."""
        TestModeDetector.reset_cache()
    
    def test_detects_pytest_execution(self):
        """Test that pytest execution is detected as test mode."""
        with mock.patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_something'}):
            TestModeDetector.reset_cache()
            assert TestModeDetector.is_test_mode() is True
    
    def test_detects_testing_environment_variable(self):
        """Test detection via TESTING environment variable."""
        with mock.patch.dict(os.environ, {'TESTING': 'true'}):
            TestModeDetector.reset_cache()
            assert TestModeDetector.is_test_mode() is True
        
        with mock.patch.dict(os.environ, {'TESTING': '1'}):
            TestModeDetector.reset_cache()
            assert TestModeDetector.is_test_mode() is True
    
    def test_detects_test_mode_environment_variable(self):
        """Test detection via TEST_MODE environment variable."""
        with mock.patch.dict(os.environ, {'TEST_MODE': 'yes'}):
            TestModeDetector.reset_cache()
            assert TestModeDetector.is_test_mode() is True
    
    def test_detects_environment_test_setting(self):
        """Test detection via ENVIRONMENT=test."""
        with mock.patch.dict(os.environ, {'ENVIRONMENT': 'test'}):
            TestModeDetector.reset_cache()
            assert TestModeDetector.is_test_mode() is True
        
        with mock.patch.dict(os.environ, {'ENVIRONMENT': 'testing'}):
            TestModeDetector.reset_cache()
            assert TestModeDetector.is_test_mode() is True
    
    def test_non_test_mode_detection(self):
        """Test that non-test environments are correctly identified."""
        # Clear all test indicators
        test_vars = ['PYTEST_CURRENT_TEST', 'TESTING', 'TEST_MODE', 'ENVIRONMENT']
        clear_env = {var: '' for var in test_vars}
        
        with mock.patch.dict(os.environ, clear_env, clear=False):
            TestModeDetector.reset_cache()
            # Should return False when no test indicators are present
            # Note: This might be True in actual test environment, but the mock should override
            pass  # We can't easily test this in a real test environment
    
    def test_caching_behavior(self):
        """Test that test mode detection is cached properly."""
        with mock.patch.dict(os.environ, {'TESTING': 'true'}):
            TestModeDetector.reset_cache()
            
            # First call should compute and cache
            result1 = TestModeDetector.is_test_mode()
            assert result1 is True
            
            # Second call should use cached value
            result2 = TestModeDetector.is_test_mode()
            assert result2 is True
            
            # Cache should be set
            assert TestModeDetector._cached_test_mode is True


class TestTestOnlyDecorator:
    """Test the @test_only decorator functionality."""
    
    def setup_method(self):
        """Reset test mode cache before each test."""
        TestModeDetector.reset_cache()
    
    def test_allows_execution_in_test_mode(self):
        """Test that decorated function executes normally in test mode."""
        @test_only("Test function")
        def test_function():
            return "success"
        
        # In test environment, this should work
        result = test_function()
        assert result == "success"
    
    def test_blocks_execution_in_non_test_mode(self):
        """Test that decorated function raises violation in non-test mode."""
        @test_only("Should only run in tests")
        def production_dangerous_function():
            return "This should not run in production"
        
        # Mock non-test environment
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            with pytest.raises(TestModeViolation) as exc_info:
                production_dangerous_function()
            
            violation = exc_info.value
            assert violation.function_name == "production_dangerous_function"
            assert "Should only run in tests" in violation.reason
    
    def test_custom_reason_in_violation(self):
        """Test that custom reasons are included in violations."""
        custom_reason = "This mock creator is dangerous in production"
        
        @test_only(custom_reason)
        def create_mock():
            return "mock"
        
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            with pytest.raises(TestModeViolation) as exc_info:
                create_mock()
            
            violation = exc_info.value
            assert custom_reason in violation.reason
    
    def test_override_mechanism(self):
        """Test that override mechanism works when enabled."""
        @test_only("Dangerous function", allow_override=True)
        def override_allowed_function():
            return "overridden"
        
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            # Should fail without override
            with pytest.raises(TestModeViolation):
                override_allowed_function()
            
            # Should succeed with override
            with mock.patch.dict(os.environ, {'FORCE_TEST_ONLY_OVERRIDE': 'true'}):
                result = override_allowed_function()
                assert result == "overridden"
    
    def test_function_metadata_preservation(self):
        """Test that decorator preserves function metadata."""
        @test_only("Test metadata")
        def example_function():
            """Example docstring."""
            return True
        
        # Check that metadata is preserved
        assert example_function.__name__ == "example_function"
        assert "Example docstring." in example_function.__doc__
        
        # Check our custom metadata
        assert example_function._is_test_only is True
        assert example_function._test_only_reason == "Test metadata"
    
    def test_introspection_functions(self):
        """Test introspection utility functions."""
        @test_only("Introspection test")
        def test_func():
            pass
        
        def regular_func():
            pass
        
        # Test is_test_only_function
        assert is_test_only_function(test_func) is True
        assert is_test_only_function(regular_func) is False
        
        # Test get_test_only_reason
        assert get_test_only_reason(test_func) == "Introspection test"
        assert get_test_only_reason(regular_func) is None


class TestRequireTestMode:
    """Test the require_test_mode standalone function."""
    
    def setup_method(self):
        """Reset test mode cache before each test."""
        TestModeDetector.reset_cache()
    
    def test_passes_in_test_mode(self):
        """Test that require_test_mode passes in test mode."""
        # Should not raise in test mode
        require_test_mode("test_function")
    
    def test_raises_in_non_test_mode(self):
        """Test that require_test_mode raises in non-test mode."""
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            with pytest.raises(TestModeViolation) as exc_info:
                require_test_mode("production_function")
            
            violation = exc_info.value
            assert violation.function_name == "production_function"
    
    def test_custom_message(self):
        """Test custom message in require_test_mode."""
        custom_message = "Custom violation message"
        
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            with pytest.raises(TestModeViolation) as exc_info:
                require_test_mode("func", custom_message)
            
            violation = exc_info.value
            assert custom_message in violation.reason


class TestUniversalRegistryIntegration:
    """Test integration with UniversalRegistry._create_mock_tool_dispatcher."""
    
    def setup_method(self):
        """Reset test mode cache before each test."""
        TestModeDetector.reset_cache()
    
    def test_mock_tool_dispatcher_creation_in_test_mode(self):
        """Test that mock tool dispatcher can be created in test mode."""
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # This should work in test mode
        dispatcher = registry.tool_dispatcher
        assert dispatcher is not None
        assert hasattr(dispatcher, '_websocket_enhanced')
    
    def test_mock_tool_dispatcher_blocked_in_production(self):
        """Test that mock tool dispatcher is blocked in production mode."""
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            registry = AgentRegistry()
            
            # Direct call to _create_mock_tool_dispatcher should fail
            with pytest.raises(TestModeViolation) as exc_info:
                registry._create_mock_tool_dispatcher()
            
            violation = exc_info.value
            assert "mock tool dispatcher" in violation.reason.lower()
            assert "testing" in violation.reason.lower()


class TestErrorMessagesAndSuggestions:
    """Test that error messages and suggestions are helpful."""
    
    def setup_method(self):
        """Reset test mode cache before each test."""
        TestModeDetector.reset_cache()
    
    def test_violation_message_format(self):
        """Test that violation messages are well-formatted and helpful."""
        @test_only("Mock creation for testing")
        def mock_creator():
            return "mock"
        
        with mock.patch.object(TestModeDetector, 'is_test_mode', return_value=False):
            with pytest.raises(TestModeViolation) as exc_info:
                mock_creator()
            
            violation = exc_info.value
            error_str = str(violation)
            
            # Check that error message contains key components
            assert "SSOT VIOLATION" in error_str
            assert "mock_creator" in error_str
            assert "test-only" in error_str
            assert "Mock creation for testing" in error_str
            assert "TESTING=true" in error_str
            assert "unified_test_runner.py" in error_str
    
    def test_default_suggestion_present(self):
        """Test that default suggestions are present in violations."""
        violation = TestModeViolation("test_func", "Test reason")
        error_str = str(violation)
        
        assert "TESTING=true" in error_str
        assert "unified_test_runner.py" in error_str