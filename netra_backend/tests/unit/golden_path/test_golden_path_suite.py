"""
Golden Path Unit Test Suite Runner

Comprehensive test suite runner for all golden path unit tests.
This module validates that the golden path unit tests follow SSOT patterns
and provide comprehensive business logic coverage.

Business Value:
- Ensures golden path unit tests cover all critical business scenarios
- Validates test suite completeness for business logic validation
- Provides unified entry point for golden path unit test execution
- Validates test patterns follow SSOT and business requirements
"""

import pytest
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import importlib.util


def get_golden_path_test_modules() -> List[str]:
    """Get all golden path test modules for validation."""
    golden_path_dir = Path(__file__).parent
    test_modules = []
    
    for test_file in golden_path_dir.glob("test_*.py"):
        if test_file.name != "test_golden_path_suite.py":  # Exclude this file
            module_name = test_file.stem
            test_modules.append(module_name)
    
    return test_modules


def validate_test_module_structure(module_name: str) -> Dict[str, Any]:
    """Validate that a test module follows golden path business requirements."""
    validation_results = {
        "module": module_name,
        "has_golden_path_marker": False,
        "has_unit_marker": False,
        "has_business_logic_tests": False,
        "test_classes": [],
        "test_methods": [],
        "business_value_documented": False
    }
    
    try:
        # Import the module
        golden_path_dir = Path(__file__).parent
        module_path = golden_path_dir / f"{module_name}.py"
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check module docstring for business value documentation
        if hasattr(module, '__doc__') and module.__doc__:
            docstring = module.__doc__.lower()
            validation_results["business_value_documented"] = (
                "business value" in docstring or 
                "business logic" in docstring or
                "business rules" in docstring
            )
        
        # Inspect module contents
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check for test classes
            if (isinstance(attr, type) and 
                attr_name.startswith('Test') and 
                hasattr(attr, '__module__') and 
                attr.__module__ == module_name):
                
                validation_results["test_classes"].append(attr_name)
                
                # Check class for pytest markers
                if hasattr(attr, 'pytestmark'):
                    markers = [mark.name for mark in attr.pytestmark]
                    if 'golden_path' in markers:
                        validation_results["has_golden_path_marker"] = True
                    if 'unit' in markers:
                        validation_results["has_unit_marker"] = True
                
                # Check for test methods
                for method_name in dir(attr):
                    if method_name.startswith('test_'):
                        validation_results["test_methods"].append(f"{attr_name}.{method_name}")
                        
                        # Check for business logic indicators in method names
                        if any(keyword in method_name.lower() for keyword in [
                            'business', 'logic', 'rule', 'requirement', 'value', 'workflow'
                        ]):
                            validation_results["has_business_logic_tests"] = True
    
    except Exception as e:
        validation_results["error"] = str(e)
    
    return validation_results


@pytest.mark.unit
@pytest.mark.golden_path
class TestGoldenPathTestSuiteValidation:
    """Validate that the golden path test suite meets business requirements."""
    
    def test_all_golden_path_modules_present(self):
        """Test that all required golden path test modules are present."""
        expected_modules = [
            "test_auth_flows_business_logic",
            "test_websocket_management_business_logic", 
            "test_agent_execution_workflow_business_logic",
            "test_data_validation_transformation_business_logic",
            "test_error_handling_business_logic"
        ]
        
        actual_modules = get_golden_path_test_modules()
        
        # Business Rule: All core golden path test modules must be present
        for expected_module in expected_modules:
            assert expected_module in actual_modules, \
                f"Required golden path test module missing: {expected_module}"
        
        # Business Rule: Test suite should have comprehensive coverage
        assert len(actual_modules) >= len(expected_modules), \
            f"Golden path test suite should have at least {len(expected_modules)} modules"
    
    def test_test_modules_follow_business_patterns(self):
        """Test that all test modules follow business logic patterns."""
        test_modules = get_golden_path_test_modules()
        
        for module_name in test_modules:
            if module_name == "test_golden_path_suite":
                continue  # Skip this validation module
                
            validation = validate_test_module_structure(module_name)
            
            # Business Rule: All test modules must be properly marked
            assert validation["has_golden_path_marker"], \
                f"Module {module_name} must have @pytest.mark.golden_path marker"
            assert validation["has_unit_marker"], \
                f"Module {module_name} must have @pytest.mark.unit marker"
            
            # Business Rule: All modules must have business value documentation
            assert validation["business_value_documented"], \
                f"Module {module_name} must document business value in docstring"
            
            # Business Rule: All modules must have business logic tests
            assert validation["has_business_logic_tests"], \
                f"Module {module_name} must include business logic test methods"
            
            # Business Rule: All modules must have test classes
            assert len(validation["test_classes"]) > 0, \
                f"Module {module_name} must have test classes"
            
            # Business Rule: All modules must have test methods
            assert len(validation["test_methods"]) > 0, \
                f"Module {module_name} must have test methods"
    
    def test_business_coverage_completeness(self):
        """Test that business logic coverage is complete across test modules."""
        test_modules = get_golden_path_test_modules()
        
        # Business Rule: Test suite must cover all critical business areas
        required_business_areas = [
            "authentication", "auth", "user",           # User authentication
            "websocket", "connection", "notification",  # WebSocket communication  
            "agent", "workflow", "execution",           # Agent execution
            "data", "validation", "transformation",     # Data processing
            "error", "handling", "recovery"             # Error handling
        ]
        
        all_test_content = ""
        for module_name in test_modules:
            if module_name == "test_golden_path_suite":
                continue
                
            golden_path_dir = Path(__file__).parent
            module_path = golden_path_dir / f"{module_name}.py"
            
            if module_path.exists():
                with open(module_path, 'r', encoding='utf-8') as f:
                    all_test_content += f.read().lower()
        
        # Check coverage of each business area
        covered_areas = []
        for area in required_business_areas:
            if area in all_test_content:
                covered_areas.append(area)
        
        # Business Rule: Must cover at least 80% of business areas
        coverage_ratio = len(covered_areas) / len(required_business_areas)
        assert coverage_ratio >= 0.8, \
            f"Business area coverage is {coverage_ratio:.1%}, must be at least 80%. Missing: {set(required_business_areas) - set(covered_areas)}"
    
    def test_test_naming_conventions_business_clarity(self):
        """Test that test naming follows business clarity conventions."""
        test_modules = get_golden_path_test_modules()
        
        for module_name in test_modules:
            if module_name == "test_golden_path_suite":
                continue
                
            validation = validate_test_module_structure(module_name)
            
            # Business Rule: Test method names should indicate business purpose
            business_indicators = [
                'business', 'rule', 'requirement', 'logic', 'workflow', 
                'value', 'continuity', 'security', 'validation', 'flow'
            ]
            
            business_named_tests = []
            for test_method in validation["test_methods"]:
                method_name = test_method.lower()
                if any(indicator in method_name for indicator in business_indicators):
                    business_named_tests.append(test_method)
            
            # Business Rule: At least 50% of tests should have business-focused names
            if len(validation["test_methods"]) > 0:
                business_naming_ratio = len(business_named_tests) / len(validation["test_methods"])
                assert business_naming_ratio >= 0.5, \
                    f"Module {module_name} should have at least 50% business-focused test names, got {business_naming_ratio:.1%}"
    
    def test_mock_usage_appropriate_for_unit_tests(self):
        """Test that mocking is used appropriately for unit test isolation."""
        test_modules = get_golden_path_test_modules()
        
        for module_name in test_modules:
            if module_name == "test_golden_path_suite":
                continue
                
            golden_path_dir = Path(__file__).parent
            module_path = golden_path_dir / f"{module_name}.py"
            
            if module_path.exists():
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Business Rule: Unit tests should use mocks for external dependencies
                has_mock_imports = any(mock_import in content for mock_import in [
                    "from unittest.mock import", "import unittest.mock", "@patch", "Mock", "AsyncMock"
                ])
                
                assert has_mock_imports, \
                    f"Module {module_name} should use mocks for external dependencies in unit tests"
                
                # Business Rule: Should not connect to real external services
                forbidden_real_services = [
                    "requests.get", "requests.post", "aiohttp.ClientSession(",
                    "websockets.connect", "asyncpg.connect", "redis.Redis("
                ]
                
                for forbidden in forbidden_real_services:
                    assert forbidden not in content, \
                        f"Module {module_name} should not connect to real services, found: {forbidden}"


def run_golden_path_unit_tests():
    """Run all golden path unit tests with appropriate configuration."""
    golden_path_dir = Path(__file__).parent
    
    # Configure pytest for golden path unit tests
    pytest_args = [
        str(golden_path_dir),  # Run tests in golden path directory
        "-v",                   # Verbose output
        "-m", "golden_path",    # Only golden path tests
        "--tb=short",          # Shorter traceback format
        "-x",                  # Stop on first failure for fast feedback
        "--disable-warnings"   # Reduce noise
    ]
    
    print("🚀 Running Golden Path Unit Test Suite...")
    print(f"📁 Test Directory: {golden_path_dir}")
    print("🎯 Target: Business logic validation without external dependencies")
    print("=" * 80)
    
    # Run the tests
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("✅ All Golden Path Unit Tests Passed!")
        print("💼 Business logic validation complete - ready for integration testing")
    else:
        print("❌ Some Golden Path Unit Tests Failed")
        print("🔍 Check the output above for business logic issues")
    
    return exit_code


if __name__ == "__main__":
    """Run golden path unit tests when executed directly."""
    sys.exit(run_golden_path_unit_tests())