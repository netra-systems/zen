#!/usr/bin/env python3
"""
Test script to verify monitoring module imports are working correctly.
"""

def test_monitoring_imports():
    """Test all critical monitoring imports."""
    try:
        from netra_backend.app.monitoring import MetricsCollector, PerformanceMetric, CompactAlertManager
        from netra_backend.app.monitoring.alert_manager_compact import CompactAlertManager as DirectAlertManager
        from netra_backend.app.monitoring.performance_dashboard import PerformanceDashboard
        from netra_backend.app.monitoring.system_monitor import SystemPerformanceMonitor

        print('MONITORING IMPORT STATUS: SUCCESS')
        print('- MetricsCollector: Available')
        print('- PerformanceMetric: Available')
        print('- CompactAlertManager: Available')
        print('- DirectAlertManager: Available')
        print('- PerformanceDashboard: Available')
        print('- SystemPerformanceMonitor: Available')
        print('All critical monitoring components are operational')
        return True
    except Exception as e:
        print(f'MONITORING IMPORT ERROR: {e}')
        return False

if __name__ == "__main__":
    success = test_monitoring_imports()
    exit(0 if success else 1)