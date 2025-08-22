"""
Staged Health Monitor Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 514-line monolith
"""

# Import all test classes from focused modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from netra_backend.tests.test_health_monitor_adaptive import (
    TestAdaptiveRules,
    TestHealthCheckFactories,
    TestServiceStatus,
)
from netra_backend.tests.test_health_monitor_checks import (
    TestCheckResultProcessing,
    TestHealthChecks,
    TestStageProgression,
)
from netra_backend.tests.test_health_monitor_core import (
    TestHealthCheckResult,
    # Add project root to path
    TestHealthStage,
    TestServiceConfig,
    TestServiceState,
    TestStageConfig,
    TestStagedHealthMonitorInit,
)
from netra_backend.tests.test_health_monitor_lifecycle import (
    TestMonitoringLifecycle,
    TestServiceRegistration,
)

# Re-export for backward compatibility
__all__ = [
    'TestHealthStage',
    'TestServiceConfig',
    'TestHealthCheckResult',
    'TestStageConfig',
    'TestServiceState',
    'TestStagedHealthMonitorInit',
    'TestServiceRegistration',
    'TestMonitoringLifecycle',
    'TestHealthChecks',
    'TestCheckResultProcessing',
    'TestStageProgression',
    'TestAdaptiveRules',
    'TestServiceStatus',
    'TestHealthCheckFactories'
]