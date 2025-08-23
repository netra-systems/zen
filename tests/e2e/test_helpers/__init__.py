"""
E2E Test Helpers Package

Shared utilities and base classes for end-to-end testing.
"""

from tests.e2e.test_helpers.performance_base import (
    ThroughputMetrics,
    LatencyMeasurement,
    LoadTestResults,
    ThroughputAnalyzer,
    HighVolumeWebSocketServer,
    HighVolumeThroughputClient,
    HIGH_VOLUME_CONFIG
)

__all__ = [
    'create_real_services_manager',
    'websocket_test_context',
    'stress_test_connections',
    'setup_test_path',
    'ThroughputMetrics',
    'LatencyMeasurement', 
    'LoadTestResults',
    'ThroughputAnalyzer',
    'HighVolumeWebSocketServer',
    'HighVolumeThroughputClient',
    'HIGH_VOLUME_CONFIG'
]

from pathlib import Path
import sys

def setup_test_path():
    """Setup test path for e2e tests."""
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root

def stress_test_connections():
    """Placeholder for stress test connections."""
    pass

def websocket_test_context():
    """Placeholder for websocket test context."""
    pass

def create_real_services_manager():
    """Placeholder for real services manager."""
    pass

