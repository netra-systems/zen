"""
Staged Health Monitor Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 514-line monolith
"""

# Import all test classes from focused modules
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.startup.test_health_monitor_core import (

# Add project root to path
    TestHealthStage,
    TestServiceConfig,
    TestHealthCheckResult,
    TestStageConfig,
    TestServiceState,
    TestStagedHealthMonitorInit
)
from netra_backend.tests.startup.test_health_monitor_lifecycle import (
    TestServiceRegistration,
    TestMonitoringLifecycle
)
from netra_backend.tests.startup.test_health_monitor_checks import (
    TestHealthChecks,
    TestCheckResultProcessing,
    TestStageProgression
)
from netra_backend.tests.startup.test_health_monitor_adaptive import (
    TestAdaptiveRules,
    TestServiceStatus,
    TestHealthCheckFactories
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