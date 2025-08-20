"""
Staged Health Monitor Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 514-line monolith
"""

# Import all test classes from focused modules
from app.tests.startup.test_health_monitor_core import (
    TestHealthStage,
    TestServiceConfig,
    TestHealthCheckResult,
    TestStageConfig,
    TestServiceState,
    TestStagedHealthMonitorInit
)
from app.tests.startup.test_health_monitor_lifecycle import (
    TestServiceRegistration,
    TestMonitoringLifecycle
)
from app.tests.startup.test_health_monitor_checks import (
    TestHealthChecks,
    TestCheckResultProcessing,
    TestStageProgression
)
from app.tests.startup.test_health_monitor_adaptive import (
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