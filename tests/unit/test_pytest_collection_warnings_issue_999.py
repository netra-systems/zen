"""
Issue #999 Reproduction Test: Pytest Collection Warnings for Test Classes with __init__

This test reproduces the specific pytest collection warning:
"cannot collect test class 'TestWebSocketConnection' because it has a __init__ constructor"

Created: 2025-09-14
Purpose: Validate pytest collection warnings and establish baseline for remediation
Test Plan: Phase 1 - Reproduction and Validation
"""

import pytest
import unittest
from unittest.mock import Mock, patch


@pytest.mark.unit
class TestWebSocketConnection:
    """
    INTENTIONAL ISSUE: This class has __init__ constructor which causes pytest collection warning.

    This reproduces the exact warning pattern found in the codebase:
    "cannot collect test class 'TestWebSocketConnection' because it has a __init__ constructor"
    """

    def __init__(self, websocket_url="ws://test"):
        """
        This __init__ method causes pytest collection warnings.

        pytest expects test classes to be instantiable without arguments,
        but this constructor requires parameters.
        """
        self.websocket_url = websocket_url
        self.connection = Mock()
        self.is_connected = False

    def test_connection_initialization(self):
        """Test websocket connection initialization - should not be collected by pytest"""
        assert self.websocket_url is not None
        assert self.connection is not None
        assert self.is_connected is False

    def test_connection_status(self):
        """Test connection status checking - should not be collected by pytest"""
        self.is_connected = True
        assert self.is_connected is True


@pytest.mark.unit
class TestDatabaseConnection:
    """
    INTENTIONAL ISSUE: Another test class with __init__ constructor.

    This creates additional pytest collection warnings to demonstrate
    the scope of the issue across different test scenarios.
    """

    def __init__(self, db_url="sqlite:///test.db", timeout=30):
        """
        Another problematic __init__ method that causes pytest warnings.
        """
        self.db_url = db_url
        self.timeout = timeout
        self.connection = None

    def test_database_connection(self):
        """Test database connection - should not be collected by pytest"""
        assert self.db_url is not None
        assert self.timeout > 0

    def test_connection_timeout(self):
        """Test connection timeout - should not be collected by pytest"""
        assert self.timeout == 30


@pytest.mark.unit
class TestProperTestClass:
    """
    CORRECT PATTERN: Test class without __init__ constructor.

    This class should be properly collected by pytest without warnings.
    This demonstrates the correct pattern that should be used.
    """

    def setup_method(self):
        """Proper setup method instead of __init__"""
        self.test_value = "initialized"
        self.mock_service = Mock()

    def test_proper_initialization(self):
        """This test should be properly collected by pytest"""
        assert hasattr(self, 'test_value')
        assert self.test_value == "initialized"

    def test_mock_service_available(self):
        """This test should be properly collected by pytest"""
        assert self.mock_service is not None


@pytest.mark.unit
class TestUnittestStyleClass(unittest.TestCase):
    """
    UNITTEST STYLE: Using unittest.TestCase base class.

    This should be collected properly by pytest as unittest.TestCase
    handles initialization differently.
    """

    def setUp(self):
        """Standard unittest setUp method"""
        self.service_mock = Mock()
        self.test_data = {"key": "value"}

    def test_unittest_style_setup(self):
        """Test unittest style setup"""
        self.assertIsNotNone(self.service_mock)
        self.assertEqual(self.test_data["key"], "value")

    def test_unittest_assertions(self):
        """Test unittest style assertions"""
        self.assertTrue(True)
        self.assertFalse(False)


# Test functions (not classes) - these should always be collected properly
@pytest.mark.unit
def test_standalone_function():
    """Standalone test function - should be collected without issues"""
    assert True


@pytest.mark.unit
def test_another_standalone_function():
    """Another standalone test function - should be collected without issues"""
    mock_data = {"test": True}
    assert mock_data["test"] is True


# Reproduction validation functions
def validate_collection_warnings():
    """
    Helper function to validate that pytest collection warnings are generated.

    This function can be called externally to confirm the reproduction test
    generates the expected warnings.
    """
    import subprocess
    import os

    # Get the path to this test file
    test_file = __file__

    # Run pytest with collection-only to capture warnings
    try:
        result = subprocess.run([
            'pytest', '--collect-only', '-v', test_file
        ], capture_output=True, text=True, timeout=30)

        # Check for the specific warning pattern
        warning_found = False
        if "cannot collect test class" in result.stdout or "cannot collect test class" in result.stderr:
            warning_found = True

        return {
            'warnings_reproduced': warning_found,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'warnings_reproduced': False,
            'error': 'Timeout during pytest collection'
        }
    except Exception as e:
        return {
            'warnings_reproduced': False,
            'error': str(e)
        }


if __name__ == "__main__":
    """
    When run directly, this script validates the reproduction.
    """
    print("=" * 60)
    print("Issue #999 Pytest Collection Warnings Reproduction Test")
    print("=" * 60)

    # Validate collection warnings
    result = validate_collection_warnings()

    if result['warnings_reproduced']:
        print("✅ SUCCESS: Pytest collection warnings successfully reproduced")
        print("\nThis confirms Issue #999 is present in this test file.")
        print("Expected warnings should include:")
        print("- cannot collect test class 'TestWebSocketConnection' because it has a __init__ constructor")
        print("- cannot collect test class 'TestDatabaseConnection' because it has a __init__ constructor")
    else:
        print("❌ WARNING: Pytest collection warnings not detected")
        print("This may indicate the issue is not properly reproduced.")

    print("\n" + "=" * 60)
    print("Test Plan Phase 1 Validation Complete")
    print("=" * 60)