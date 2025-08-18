"""
Metrics export functionality supporting multiple formats
Exports corpus metrics in JSON, Prometheus, CSV, and InfluxDB formats
COMPATIBILITY WRAPPER - Main implementation moved to exporter_core.py
"""

# Re-export the main class for backward compatibility
from .exporter_core import MetricsExporter

__all__ = ['MetricsExporter']