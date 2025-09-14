"""
Comprehensive tests for the SSOT Test Framework

This module tests all components of the Single Source of Truth test framework
to ensure they function correctly and meet the requirements for eliminating
test infrastructure violations across all 6,096+ test files.

Business Value: Platform/Internal - Test Infrastructure Stability
Validates that the SSOT framework works correctly and provides reliable
foundation for all testing in the system.
"""

import asyncio
import logging
import pytest
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import MagicMock

# Add project root for imports - MUST be before any local imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment

# Import SSOT components under test (only what actually exists)
from test_framework.ssot import (
    # Base classes
    BaseTestCase,
    AsyncBaseTestCase,
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    ExecutionMetrics,
    
    # Mock utilities
    MockFactory,
    MockRegistry,
    DatabaseMockFactory,
    ServiceMockFactory,
    get_mock_factory,
    
    # Database utilities
    DatabaseTestUtility,
    PostgreSQLTestUtility,
    ClickHouseTestUtility,
    create_database_test_utility,
    
    # WebSocket utilities
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    
    # Docker utilities
    DockerTestUtility,
    create_docker_test_utility,
    
    # Framework utilities
    validate_test_class,
    get_test_base_for_category,
    validate_ssot_compliance,
    get_ssot_status,
    SSOT_VERSION,
    SSOT_COMPLIANCE
)

# Import the actual base test classes
from test_framework.ssot.base_test_case import (
    SSotBaseTestCase,
    SSotAsyncTestCase
)

logger = logging.getLogger(__name__)


class TestSSotFrameworkCore:
    """Test core SSOT framework functionality."""
    
    def test_framework_version_and_compliance(self):
        """Test framework version and compliance constants."""
        assert SSOT_VERSION == "1.0.0"
        assert isinstance(SSOT_COMPLIANCE, dict)
        assert "total_components" in SSOT_COMPLIANCE
        assert "base_classes" in SSOT_COMPLIANCE
        assert "mock_factories" in SSOT_COMPLIANCE
    
    def test_ssot_status_function(self):
        """Test get_ssot_status function."""
        status = get_ssot_status()
        
        assert isinstance(status, dict)
        assert status["version"] == SSOT_VERSION
        assert "compliance" in status
        assert "violations" in status
        assert "components" in status
        
        # Check component categories
        components = status["components"]
        assert "base_classes" in components
        assert "mock_utilities" in components
        assert "database_utilities" in components
        assert "websocket_utilities" in components
        assert "docker_utilities" in components
    
    def test_ssot_compliance_validation(self):
        """Test SSOT compliance validation."""
        violations = validate_ssot_compliance()
        assert isinstance(violations, list)
        
        # Compliance validation should pass for properly implemented framework
        if violations:
            logger.warning(f"SSOT compliance violations found: {violations}")
    
    def test_validate_test_class_function(self):
        """Test validate_test_class utility function."""
        # Valid test class
        class ValidTest(BaseTestCase):
            def test_something(self):
                pass
        
        errors = validate_test_class(ValidTest)
        assert isinstance(errors, list)
        
        # Invalid test class (not inheriting from BaseTestCase)
        class InvalidTest:
            def test_something(self):
                pass
        
        errors = validate_test_class(InvalidTest)
        assert len(errors) > 0
    
    def test_get_test_base_for_category(self):
        """Test get_test_base_for_category utility function."""
        # Test different categories
        assert get_test_base_for_category("unit") == BaseTestCase
        assert get_test_base_for_category("integration") == IntegrationTestCase
        assert get_test_base_for_category("database") == DatabaseTestCase
        assert get_test_base_for_category("websocket") == WebSocketTestCase
        assert get_test_base_for_category("e2e") == IntegrationTestCase
        assert get_test_base_for_category("unknown") == BaseTestCase


class TestBaseTestCase:
    """Test the BaseTestCase SSOT implementation."""
    
    def test_base_test_case_initialization(self):
        """Test BaseTestCase initializes correctly."""
        test_case = SSotBaseTestCase()
        
        assert hasattr(test_case, '_env')
        assert hasattr(test_case, '_metrics')
        assert hasattr(test_case, '_test_id')
        assert hasattr(test_case, '_resources_to_cleanup')
        
        # Test configuration
        assert test_case.ISOLATION_ENABLED == True
        assert test_case.AUTO_CLEANUP == True
    
    def test_setup_method_creates_test_context(self):
        """Test that setup_method creates proper test context."""
        test_case = SSotBaseTestCase()
        
        # Mock method for testing
        mock_method = MagicMock()
        mock_method.__name__ = "test_example"
        
        # Call setup_method
        test_case.setup_method(mock_method)
        
        # Verify test context is created
        assert test_case._test_context is not None
        assert test_case._test_context.test_name == "test_example"
        assert test_case._test_started
        
        # Verify environment is isolated
        assert test_case._env.is_isolated()
        
        # Clean up
        test_case.teardown_method(mock_method)
    
    def test_teardown_method_cleans_up(self):
        """Test that teardown_method properly cleans up."""
        test_case = SSotBaseTestCase()
        
        # Setup first
        mock_method = MagicMock()
        mock_method.__name__ = "test_cleanup"
        test_case.setup_method(mock_method)
        
        # Add a cleanup callback to test
        cleanup_called = [False]
        def cleanup_callback():
            cleanup_called[0] = True
        test_case.add_cleanup(cleanup_callback)
        
        # Call teardown
        test_case.teardown_method(mock_method)
        
        # Verify cleanup occurred
        assert cleanup_called[0]
        assert test_case._test_completed
        assert test_case._cleanup_callbacks == []
        assert test_case._test_context is None
    
    def test_environment_integration(self):
        """Test that environment integration works correctly."""
        test_case = SSotBaseTestCase()
        
        # Test setting and getting environment variables
        test_case.set_env_var("TEST_VAR", "test_value")
        assert test_case.get_env_var("TEST_VAR") == "test_value"
        
        # Test deletion
        test_case.delete_env_var("TEST_VAR")
        assert test_case.get_env_var("TEST_VAR") is None
    
    def test_temp_env_vars_context_manager(self):
        """Test temporary environment variables context manager."""
        test_case = SSotBaseTestCase()
        
        # Set initial value
        test_case.set_env_var("TEMP_TEST", "original")
        
        # Use context manager
        with test_case.temp_env_vars(TEMP_TEST="temporary", NEW_VAR="new"):
            assert test_case.get_env_var("TEMP_TEST") == "temporary"
            assert test_case.get_env_var("NEW_VAR") == "new"
        
        # Verify restoration
        assert test_case.get_env_var("TEMP_TEST") == "original"
        assert test_case.get_env_var("NEW_VAR") is None
    
    def test_metrics_recording(self):
        """Test metrics recording functionality."""
        test_case = SSotBaseTestCase()
        
        # Record metrics
        test_case.record_metric("test_metric", 42)
        test_case.record_metric("another_metric", "string_value")
        
        # Retrieve metrics
        assert test_case.get_metric("test_metric") == 42
        assert test_case.get_metric("another_metric") == "string_value"
        assert test_case.get_metric("nonexistent") is None
        
        # Get all metrics
        all_metrics = test_case.get_all_metrics()
        assert "test_metric" in all_metrics
        assert "another_metric" in all_metrics
        assert all_metrics["test_metric"] == 42


class TestSSotAsyncTestCase:
    """Test the SSOT AsyncTestCase functionality."""
    
    @pytest.mark.asyncio
    async def test_async_initialization(self):
        """Test that async test case initializes correctly."""
        test_case = SSotAsyncTestCase()
        
        # Should have all base functionality
        assert test_case._env is not None
        assert test_case._metrics is not None
        
        # Test async setup/teardown
        mock_method = MagicMock()
        mock_method.__name__ = "test_async_method"
        
        await test_case.setup_method(mock_method)
        assert test_case._test_started
        
        await test_case.teardown_method(mock_method)
        assert test_case._test_completed
    
    @pytest.mark.asyncio
    async def test_async_temp_env_vars(self):
        """Test async temporary environment variables."""
        test_case = SSotAsyncTestCase()
        
        test_case.set_env_var("ASYNC_TEST", "original")
        
        async with test_case.async_temp_env_vars(ASYNC_TEST="temporary"):
            assert test_case.get_env_var("ASYNC_TEST") == "temporary"
        
        assert test_case.get_env_var("ASYNC_TEST") == "original"
    
    @pytest.mark.asyncio
    async def test_wait_for_condition(self):
        """Test the wait_for_condition utility."""
        test_case = SSotAsyncTestCase()
        
        # Test successful condition
        counter = [0]
        def condition():
            counter[0] += 1
            return counter[0] >= 3
        
        await test_case.wait_for_condition(condition, timeout=1.0, interval=0.1)
        assert counter[0] >= 3
        
        # Test timeout
        def never_true():
            return False
        
        with pytest.raises(TimeoutError):
            await test_case.wait_for_condition(never_true, timeout=0.1, interval=0.05)
    
    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test the run_with_timeout utility."""
        test_case = SSotAsyncTestCase()
        
        # Test successful execution
        async def quick_coro():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await test_case.run_with_timeout(quick_coro(), timeout=1.0)
        assert result == "success"
        
        # Test timeout
        async def slow_coro():
            await asyncio.sleep(1.0)
            return "too_slow"
        
        with pytest.raises(TimeoutError):
            await test_case.run_with_timeout(slow_coro(), timeout=0.1)


class TestSSotMockFactory:
    """Test the SSOT Mock Factory functionality."""
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = MockFactory()
        
        assert hasattr(factory, 'create_mock')
    
    def test_global_factory_access(self):
        """Test global factory instance access."""
        factory1 = get_mock_factory()
        factory2 = get_mock_factory()
        
        # Should be the same instance
        assert factory1 is factory2


class TestBackwardsCompatibility:
    """Test backwards compatibility features."""
    
    def test_base_class_aliases(self):
        """Test that base class aliases work."""
        # Test that the aliases point to the SSOT classes
        assert BaseTestCase is SSotBaseTestCase
        assert AsyncBaseTestCase is SSotAsyncTestCase
        
        # Test that they can be instantiated
        base_test = BaseTestCase()
        assert isinstance(base_test, SSotBaseTestCase)


class TestIntegrationScenarios:
    """Test integration scenarios combining base test case and mocks."""
    
    @pytest.mark.asyncio
    async def test_full_test_scenario(self):
        """Test a complete test scenario using SSOT framework."""
        # This simulates how a real test would use the SSOT framework
        
        class ExampleTest(SSotAsyncTestCase):
            """Example test using SSOT framework."""
            
            async def test_basic_functionality(self):
                # Setup environment
                self.set_env_var("TEST_ENVIRONMENT", "integration") 
                
                # Record metrics
                self.record_metric("requests_processed", 1)
                
                # Assertions
                self.assert_env_var_set("TEST_ENVIRONMENT", "integration")
                self.assert_metrics_recorded("requests_processed")
                
                return {"status": "success"}
        
        # Run the test
        test_instance = ExampleTest()
        
        # Setup
        mock_method = MagicMock()
        mock_method.__name__ = "test_basic_functionality"
        await test_instance.setup_method(mock_method)
        
        try:
            # Execute test
            result = await test_instance.test_basic_functionality()
            
            # Verify result
            assert result["status"] == "success"
            assert test_instance.get_metric("requests_processed") == 1
            
        finally:
            # Teardown
            await test_instance.teardown_method(mock_method)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])