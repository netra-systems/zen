"""Quality Monitoring Service Tests - Main Entry Point

This file serves as the main entry point for quality monitoring tests.
The actual tests have been split into focused modules for better maintainability.
"""

# Import all test modules to ensure they are discovered by pytest

# Add project root to path

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from netra_backend.tests.services.test_quality_monitoring_basic import *
from netra_backend.tests.services.test_quality_monitoring_metrics import *
from netra_backend.tests.services.test_quality_monitoring_alerts import *
from netra_backend.tests.services.test_quality_monitoring_integration import *

# Add project root to path
