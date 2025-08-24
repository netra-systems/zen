"""
Staged Health Monitor Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 514-line monolith
"""

# Import all test classes from focused modules

import sys
from pathlib import Path

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