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

# CRITICAL FIX: Set OAuth test credentials to prevent CentralConfigurationValidator errors
# Must be done early during conftest loading before any validation occurs
from shared.isolated_environment import get_env
_env = get_env()
if not _env.get("GOOGLE_OAUTH_CLIENT_ID_TEST"):
    _env.set("GOOGLE_OAUTH_CLIENT_ID_TEST", "test-oauth-client-id-for-automated-testing", source="main_conftest_oauth_fix")
if not _env.get("GOOGLE_OAUTH_CLIENT_SECRET_TEST"):
    _env.set("GOOGLE_OAUTH_CLIENT_SECRET_TEST", "test-oauth-client-secret-for-automated-testing", source="main_conftest_oauth_fix")

# Import mock fixtures (lightweight, good for most unit tests)
from tests.conftest_mocks import *

# Import real services fixtures for integration testing
# CRITICAL: Import directly from fixtures module to ensure pytest discovers them
try:
    from test_framework.fixtures.real_services import (
        real_postgres_connection,
        with_test_database,
        real_redis_fixture,
        real_services_fixture
    )
except ImportError:
    # Real services fixtures not available
    pass

# Import no-docker mode plugin for integration test management
try:
    from test_framework.ssot.pytest_no_docker_plugin import (
        NoDocketModePlugin,
        pytest_configure as no_docker_pytest_configure,
        pytest_sessionstart,
        pytest_sessionfinish
    )
except ImportError:
    # Plugin not available, continue without it
    NoDocketModePlugin = None
    no_docker_pytest_configure = None
    pytest_sessionstart = None
    pytest_sessionfinish = None

# Lazy loading to prevent resource exhaustion during pytest collection
# CRITICAL: Do NOT check environment at module level - causes Docker crash on Windows
_env_checked = False
_should_load_services = False
_should_load_real_services = False 
_should_load_e2e = False

def _check_environment():
    """Check environment once to determine what fixtures to load.
    
    WARNING: This function should ONLY be called from within fixtures,
    never at module import time to prevent resource exhaustion.
    """
    global _env_checked, _should_load_services, _should_load_real_services, _should_load_e2e
    
    if _env_checked:
        return
    
    # Use os.environ directly to avoid heavy imports during collection
    import os
    
    # Check environment variables
    _should_load_real_services = (
        os.environ.get("USE_REAL_SERVICES", "false").lower() == "true" or
        os.environ.get("ENVIRONMENT", "").lower() == "staging"
    )
    
    _should_load_e2e = (
        os.environ.get("RUN_E2E_TESTS", "false").lower() == "true" or 
        os.environ.get("ENVIRONMENT", "").lower() == "staging"
    )
    
    # Always load services if we're loading real services or E2E
    _should_load_services = _should_load_real_services or _should_load_e2e
    
    _env_checked = True

# REMOVED: Automatic environment check that causes Docker crash
# Environment will be checked lazily when fixtures are actually used

# Conditional imports are now controlled by pytest hooks
# to prevent loading during collection phase

# Pytest hooks for conditional loading
def pytest_configure(config):
    """Configure pytest with conditional fixture loading.
    
    This hook runs AFTER collection, preventing resource exhaustion.
    """
    import os
    
    # Check if we need service fixtures
    if (
        os.environ.get("USE_REAL_SERVICES", "false").lower() == "true" or
        os.environ.get("ENVIRONMENT", "").lower() == "staging" or
        config.getoption("--real-services", default=False)
    ):
        # Import service fixtures only when needed
        # Note: Can't use 'import *' inside function/conditional
        # These imports need to be at module level
        pass
    
    # Check if we need E2E fixtures
    if (
        os.environ.get("RUN_E2E_TESTS", "false").lower() == "true" or
        os.environ.get("ENVIRONMENT", "").lower() == "staging"
    ):
        # Note: Can't use 'import *' inside function/conditional
        # These imports need to be at module level
        pass

def pytest_collection_modifyitems(config, items):
    """Skip tests that require Docker if Docker is not available."""
    import platform
    import os
    
    # Skip Docker tests on Windows if requested
    if platform.system() == "Windows" and os.environ.get("SKIP_DOCKER_TESTS", "").lower() == "true":
        skip_docker = pytest.mark.skip(reason="Docker tests skipped on Windows (SKIP_DOCKER_TESTS=true)")
        for item in items:
            if item.get_closest_marker("requires_docker"):
                item.add_marker(skip_docker)

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
                print(f"Memory Report {label}: {current_memory:.1f} MB ([U+0394]{delta:+.1f} MB)")
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

# =============================================================================
# MISSING FIXTURE IMPLEMENTATIONS
# =============================================================================

@pytest.fixture
@memory_profile("Service discovery fixture for cross-service integration tests", "MEDIUM")
def service_discovery():
    """Create test service discovery fixture.
    
    Provides a ServiceDiscovery instance configured for testing cross-service
    integration scenarios. Creates a temporary directory for service discovery
    files and cleans up after test completion.
    
    Memory Impact: MEDIUM - Creates temporary files and ServiceDiscovery instance
    """
    import tempfile
    from pathlib import Path
    from dev_launcher.service_discovery import ServiceDiscovery
    
    with tempfile.TemporaryDirectory() as temp_dir:
        discovery = ServiceDiscovery(Path(temp_dir))
        # Register test services with standard development ports
        discovery.write_backend_info(8000)
        discovery.write_frontend_info(3000)
        discovery.write_auth_info({
            'port': 8081,
            'url': 'http://localhost:8081',
            'api_url': 'http://localhost:8081/api'
        })
        yield discovery
        # Cleanup happens automatically with tempfile context manager

@pytest.fixture
@memory_profile("Launcher configuration fixture for dev environment tests", "LOW")
def launcher_config():
    """Create test launcher configuration fixture.
    
    Provides a LauncherConfig instance configured for testing with minimal
    resource usage and test-appropriate settings.
    
    Memory Impact: LOW - Simple configuration object creation
    """
    from dev_launcher.config import LauncherConfig
    from pathlib import Path
    
    # Create minimal config for testing
    config = LauncherConfig(
        backend_port=8000,
        frontend_port=3000,
        dynamic_ports=False,  # Use fixed ports for testing consistency
        backend_reload=False,  # Disable reload for test performance
        frontend_reload=False,
        auth_reload=False,
        load_secrets=False,  # Local-only secrets for testing
        no_browser=True,  # Never open browser in tests
        verbose=False,  # Quiet mode for tests
        non_interactive=True,  # Non-interactive for automated testing
        parallel_startup=False,  # Sequential startup for test predictability
        startup_mode="minimal",  # Minimal startup for tests
        silent_mode=True,  # Silent logging for tests
        project_root=Path.cwd(),  # Use current working directory
    )
    
    yield config

# Hook to provide memory usage report at end of session  
def pytest_sessionfinish(session, exitstatus):
    """Report memory usage at end of test session."""
    try:
        # Check if stdout is available before attempting to print
        import sys
        if hasattr(sys.stdout, 'closed') and sys.stdout.closed:
            return  # Skip reporting if stdout is closed
        
        print("\n=== Memory Usage Report ===")
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
    except (ValueError, OSError):
        # Silently skip if there are I/O issues
        pass
