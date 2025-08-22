"""Quality Monitoring Service Tests - Main Entry Point

This file serves as the main entry point for quality monitoring tests.
The actual tests have been split into focused modules for better maintainability.
"""

# Import all test modules to ensure they are discovered by pytest

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from netra_backend.tests.test_quality_monitoring_alerts import *
from netra_backend.tests.test_quality_monitoring_basic import *
from netra_backend.tests.test_quality_monitoring_integration import *
from netra_backend.tests.test_quality_monitoring_metrics import *

# Add project root to path
