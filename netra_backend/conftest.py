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
from tests.conftest import *  # noqa: F401, F403