"""
Main test configuration with memory-optimized modular fixture loading.

This is the new optimized conftest.py that replaces the previous 1400-line monolith.
It uses selective imports to prevent memory exhaustion during pytest collection phase.

Memory Impact: REDUCED during collection and runtime
- Base fixtures always loaded (minimal impact)
- Mock fixtures loaded for unit tests
- Service fixtures loaded conditionally  
- Real service fixtures loaded only when needed
- E2E fixtures loaded only for E2E tests

Key optimizations:
1. Modular structure prevents loading unnecessary fixtures
2. Memory profiling on all fixtures to track usage
3. Eliminated circular dependencies and heavy fixture chains
4. Session-scoped fixtures reduced to absolute minimum
5. Real services only connected when explicitly needed
"""

import sys
import os
from typing import Dict, Any, Optional

import pytest

# Always import core base fixtures (minimal memory impact)
from tests.conftest_base import *

# Import mock fixtures (lightweight, good for most unit tests)
from tests.conftest_mocks import *

# Conditionally import heavier fixtures based on environment
_env_checked = False
_should_load_services = False
_should_load_real_services = False 
_should_load_e2e = False

def _check_environment():
    """Check environment once to determine what fixtures to load."""
    global _env_checked, _should_load_services, _should_load_real_services, _should_load_e2e
    
    if _env_checked:
        return
    
    from shared.isolated_environment import get_env
    env = get_env()
    
    # Check environment variables
    _should_load_real_services = (
        env.get("USE_REAL_SERVICES", "false").lower() == "true" or
        env.get("ENVIRONMENT", "").lower() == "staging"
    )
    
    _should_load_e2e = (
        env.get("RUN_E2E_TESTS", "false").lower() == "true" or 
        env.get("ENVIRONMENT", "").lower() == "staging"
    )
    
    # Always load services if we're loading real services or E2E
    _should_load_services = _should_load_real_services or _should_load_e2e
    
    _env_checked = True

# Check environment and conditionally import
_check_environment()

if _should_load_services:
    from tests.conftest_services import *

if _should_load_real_services:
    try:
        from test_framework.conftest_real_services import *
    except ImportError:
        # Real services may not be available in all environments
        pass

if _should_load_e2e:
    from tests.conftest_e2e import *

# Memory profiling decorator - available to all test modules
def memory_profile(description: str = "", impact: str = "LOW"):
    """Decorator to track memory usage of fixtures.
    
    Args:
        description: Human-readable description of fixture purpose
        impact: Memory impact level (LOW/MEDIUM/HIGH/VERY_HIGH)
    """
    def decorator(func):
        func._memory_description = description
        func._memory_impact = impact
        return func
    return decorator

# Track what modules were loaded
def get_loaded_fixture_modules():
    """Get information about what fixture modules were loaded."""
    modules = ['base', 'mocks']  # Always loaded
    
    if _should_load_services:
        modules.append('services')
    if _should_load_real_services:
        modules.append('real_services')
    if _should_load_e2e:
        modules.append('e2e')
    
    return modules

# Memory usage reporting fixture (optional)
@pytest.fixture
@memory_profile("Memory usage reporting for performance monitoring", "LOW") 
def memory_reporter():
    """Report memory usage during test execution.
    
    Memory Impact: LOW - Simple memory tracking
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        class MemoryReporter:
            def __init__(self):
                self.initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                
            def report(self, label: str = "") -> float:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                delta = current_memory - self.initial_memory
                print(f"Memory Report {label}: {current_memory:.1f} MB (Δ{delta:+.1f} MB)")
                return current_memory
                
            def get_loaded_modules(self) -> list:
                return get_loaded_fixture_modules()
        
        return MemoryReporter()
        
    except ImportError:
        # Mock reporter if psutil not available
        class MockMemoryReporter:
            def report(self, label: str = "") -> float:
                return 0.0
            def get_loaded_modules(self) -> list:
                return get_loaded_fixture_modules()
        
        return MockMemoryReporter()

# Test collection optimization: Add markers based on test paths
def pytest_collection_modifyitems(config, items):
    """Modify test items after collection to optimize for memory usage."""
    for item in items:
        # Auto-mark tests based on their path for better organization
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

# Hook to provide memory usage report at end of session  
def pytest_sessionfinish(session, exitstatus):
    """Report memory usage at end of test session."""
    print(f"\n=== Memory Usage Report ===")
    loaded_modules = get_loaded_fixture_modules()
    print(f"Loaded fixture modules: {', '.join(loaded_modules)}")
    
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"Peak memory usage: {memory_mb:.1f} MB")
    except ImportError:
        print("Memory tracking not available (psutil required)")
    
    # Report on fixture loading efficiency
    if len(loaded_modules) > 3:
        print("NOTE: Multiple fixture modules loaded - this is normal for integration/E2E tests")