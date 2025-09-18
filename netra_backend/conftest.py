"""
Root conftest for netra_backend - Sets up Python path for absolute imports.

This file ensures that absolute imports work correctly when running tests
from within the netra_backend directory, following the import management
architecture specification.
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path to enable absolute imports
# This allows "from netra_backend.app..." imports to work correctly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Also ensure test_framework is available
test_framework_path = project_root / "test_framework"
if str(test_framework_path) not in sys.path:
    sys.path.insert(0, str(test_framework_path))

# Import the test-specific configuration
# Ensure tests directory is in sys.path before loading tests/conftest.py
tests_path = project_root / "tests"
if str(tests_path) not in sys.path:
    sys.path.insert(0, str(tests_path))

# Use absolute path to avoid module resolution issues
tests_conftest_path = tests_path / "conftest.py"
if tests_conftest_path.exists():
    import importlib.util
    import importlib
    
    # First, ensure the tests package exists in sys.modules
    if 'tests' not in sys.modules:
        # Create a package module for tests
        tests_package = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location('tests', tests_path / '__init__.py')
        )
        tests_package.__path__ = [str(tests_path)]
        sys.modules['tests'] = tests_package
    
    # Now load tests.conftest with proper package context
    spec = importlib.util.spec_from_file_location("tests.conftest", tests_conftest_path)
    if spec and spec.loader:
        tests_conftest = importlib.util.module_from_spec(spec)
        # Set the package context properly
        tests_conftest.__package__ = 'tests'
        sys.modules['tests.conftest'] = tests_conftest
        spec.loader.exec_module(tests_conftest)
        # Import all public symbols from tests.conftest
        for name in dir(tests_conftest):
            if not name.startswith('_'):
                globals()[name] = getattr(tests_conftest, name)