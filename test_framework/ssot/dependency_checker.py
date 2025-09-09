"""
Test Dependency Checker - SSOT for Dependency Verification

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Test Infrastructure Reliability
- Value Impact: Prevents test failures due to missing dependencies
- Strategic Impact: Ensures consistent test environment setup across developers
- Revenue Impact: Prevents configuration test failures that could hide critical bugs

This module provides a single source of truth for verifying that all required
dependencies are available before test execution begins.

CRITICAL: This prevents the exact issue that caused all 20 configuration tests
to fail with ERROR status due to missing dependencies.
"""

import sys
from typing import List, Dict, Tuple, Optional


class DependencyCheckResult:
    """Result of dependency checking operation."""
    
    def __init__(self, success: bool, missing: List[str], available: List[str], errors: List[str]):
        self.success = success
        self.missing = missing
        self.available = available  
        self.errors = errors
    
    def __str__(self) -> str:
        if self.success:
            return f"✓ All dependencies available ({len(self.available)} dependencies)"
        else:
            return f"✗ Missing {len(self.missing)} dependencies: {', '.join(self.missing)}"


class TestDependencyChecker:
    """SSOT for test dependency verification.
    
    Provides comprehensive dependency checking for different test categories
    to prevent import failures during test execution.
    """
    
    # Core dependencies required by most tests
    CORE_DEPENDENCIES = [
        "pytest",
        "pydantic", 
        "loguru",
    ]
    
    # Dependencies required by configuration tests
    CONFIG_TEST_DEPENDENCIES = [
        "pytest",
        "pydantic",
        "loguru", 
        "sqlalchemy",
        "fastapi",
    ]
    
    # Dependencies required by integration tests  
    INTEGRATION_TEST_DEPENDENCIES = [
        "pytest",
        "pytest_asyncio",
        "pydantic",
        "loguru",
        "sqlalchemy", 
        "fastapi",
        "redis",
        "httpx",
        "websockets",
    ]
    
    # Dependencies required by E2E tests
    E2E_TEST_DEPENDENCIES = [
        "pytest",
        "pytest_asyncio", 
        "pydantic",
        "loguru",
        "sqlalchemy",
        "fastapi", 
        "redis",
        "httpx",
        "websockets",
        "openai",
        "anthropic",
    ]
    
    @classmethod
    def check_dependencies(cls, dependency_list: List[str]) -> DependencyCheckResult:
        """Check if all dependencies in the list are available.
        
        Args:
            dependency_list: List of dependency names to check
            
        Returns:
            DependencyCheckResult: Result of dependency checking
        """
        missing = []
        available = []
        errors = []
        
        for dep_name in dependency_list:
            try:
                __import__(dep_name)
                available.append(dep_name)
            except ImportError as e:
                missing.append(dep_name)
                errors.append(f"{dep_name}: {str(e)}")
            except Exception as e:
                missing.append(dep_name)
                errors.append(f"{dep_name}: Unexpected error - {str(e)}")
        
        success = len(missing) == 0
        return DependencyCheckResult(success, missing, available, errors)
    
    @classmethod  
    def check_core_dependencies(cls) -> DependencyCheckResult:
        """Check core dependencies required by most tests."""
        return cls.check_dependencies(cls.CORE_DEPENDENCIES)
    
    @classmethod
    def check_config_test_dependencies(cls) -> DependencyCheckResult:
        """Check dependencies required by configuration tests."""
        return cls.check_dependencies(cls.CONFIG_TEST_DEPENDENCIES)
    
    @classmethod
    def check_integration_test_dependencies(cls) -> DependencyCheckResult:
        """Check dependencies required by integration tests."""
        return cls.check_dependencies(cls.INTEGRATION_TEST_DEPENDENCIES)
    
    @classmethod
    def check_e2e_test_dependencies(cls) -> DependencyCheckResult:
        """Check dependencies required by E2E tests."""
        return cls.check_dependencies(cls.E2E_TEST_DEPENDENCIES)
    
    @classmethod
    def verify_test_environment(cls, test_category: str = "core") -> None:
        """Verify test environment has required dependencies.
        
        Args:
            test_category: Type of tests ("core", "config", "integration", "e2e")
            
        Raises:
            EnvironmentError: If required dependencies are missing
        """
        if test_category == "config":
            result = cls.check_config_test_dependencies()
        elif test_category == "integration":
            result = cls.check_integration_test_dependencies()  
        elif test_category == "e2e":
            result = cls.check_e2e_test_dependencies()
        else:
            result = cls.check_core_dependencies()
        
        if not result.success:
            error_msg = (
                f"Test environment missing required dependencies for {test_category} tests:\n"
                f"Missing: {', '.join(result.missing)}\n"
                f"Available: {', '.join(result.available)}\n\n"
                f"To fix this issue:\n"
                f"1. Activate virtual environment: source venv/bin/activate\n"
                f"2. Install dependencies: pip install -r requirements.txt\n"
                f"3. Or install missing only: pip install {' '.join(result.missing)}"
            )
            raise EnvironmentError(error_msg)
    
    @classmethod
    def get_installation_command(cls, missing_deps: List[str]) -> str:
        """Get pip install command for missing dependencies.
        
        Args:
            missing_deps: List of missing dependency names
            
        Returns:
            str: pip install command
        """
        if not missing_deps:
            return "# No missing dependencies"
        
        return f"pip install {' '.join(missing_deps)}"


# Convenience functions for backward compatibility
def verify_core_dependencies() -> None:
    """Verify core test dependencies are available."""
    TestDependencyChecker.verify_test_environment("core")


def verify_config_test_dependencies() -> None:
    """Verify configuration test dependencies are available."""
    TestDependencyChecker.verify_test_environment("config")


def verify_integration_test_dependencies() -> None:
    """Verify integration test dependencies are available.""" 
    TestDependencyChecker.verify_test_environment("integration")


def verify_e2e_test_dependencies() -> None:
    """Verify E2E test dependencies are available."""
    TestDependencyChecker.verify_test_environment("e2e")


# Legacy function name for backward compatibility
def verify_test_dependencies() -> None:
    """Legacy function - use verify_core_dependencies() instead."""
    verify_core_dependencies()


if __name__ == "__main__":
    """Command-line interface for dependency checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check test dependencies")
    parser.add_argument("--category", default="core", 
                       choices=["core", "config", "integration", "e2e"],
                       help="Test category to check dependencies for")
    parser.add_argument("--fix", action="store_true",
                       help="Show pip install command for missing dependencies")
    
    args = parser.parse_args()
    
    try:
        if args.category == "config":
            result = TestDependencyChecker.check_config_test_dependencies()
        elif args.category == "integration": 
            result = TestDependencyChecker.check_integration_test_dependencies()
        elif args.category == "e2e":
            result = TestDependencyChecker.check_e2e_test_dependencies()
        else:
            result = TestDependencyChecker.check_core_dependencies()
        
        print(f"Dependency Check for {args.category} tests:")
        print(f"Result: {result}")
        
        if result.missing and args.fix:
            print(f"\nTo fix missing dependencies:")
            print(TestDependencyChecker.get_installation_command(result.missing))
            print("Or install all: pip install -r requirements.txt")
        
        sys.exit(0 if result.success else 1)
        
    except Exception as e:
        print(f"Error during dependency check: {e}")
        sys.exit(1)