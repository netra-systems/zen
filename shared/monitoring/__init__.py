"""Monitoring interfaces and base classes for component health monitoring.

Business Value: Provides standardized monitoring contracts enabling comprehensive
system health visibility and silent failure detection.
"""

from shared.monitoring.interfaces import MonitorableComponent, ComponentMonitor

__all__ = ["MonitorableComponent", "ComponentMonitor"]