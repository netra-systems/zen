"""
Zen Telemetry Module

Comprehensive telemetry and observability solution for Zen orchestrator.
Provides OpenTelemetry integration with Google Cloud Trace, secure secret management,
and privacy-first data collection.

Core Features:
- OpenTelemetry integration with Google Cloud Trace
- zen_secrets integration for secure credential management
- Opt-out mechanism via ZEN_TELEMETRY_DISABLED environment variable
- Data sanitization and PII filtering
- Performance monitoring with minimal overhead
- Compliance with privacy standards

Usage:
    from zen.telemetry import TelemetryManager, traced

    # Auto-initialized via zen.__init__.py
    telemetry = TelemetryManager()

    # Instrument functions
    @traced("operation_name")
    def my_function():
        pass
"""

__version__ = "1.0.0"
__author__ = "Netra Systems"

from .manager import TelemetryManager
from .config import TelemetryConfig
try:
    from .instrumentation import traced, instrument_class, trace_performance
except ImportError as e:
    # Create no-op decorators if instrumentation fails to import
    def traced(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def instrument_class(*args, **kwargs):
        def decorator(cls):
            return cls
        return decorator
    def trace_performance(*args, **kwargs):
        class NoOpContext:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return NoOpContext()
from .sanitization import DataSanitizer

# Global instance - initialized in zen.__init__.py
telemetry = TelemetryManager()
telemetry_manager = telemetry  # Alias for compatibility

# Check if OpenTelemetry is available
try:
    import opentelemetry
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

# Convenience functions
def disable_telemetry():
    """
    Disable telemetry for this session

    This is a convenience function that disables telemetry programmatically.
    Equivalent to setting ZEN_TELEMETRY_DISABLED=true environment variable.

    Example:
        from zen.telemetry import disable_telemetry
        disable_telemetry()  # Telemetry now disabled
    """
    telemetry_manager.disable()


def enable_telemetry():
    """
    Enable telemetry for this session

    This is a convenience function that enables telemetry programmatically.
    Equivalent to removing ZEN_TELEMETRY_DISABLED environment variable.

    Example:
        from zen.telemetry import enable_telemetry
        enable_telemetry()  # Telemetry now enabled
    """
    telemetry_manager.enable()


def is_telemetry_enabled() -> bool:
    """
    Check if telemetry is currently enabled

    Returns:
        bool: True if telemetry is enabled, False otherwise

    Example:
        from zen.telemetry import is_telemetry_enabled
        if is_telemetry_enabled():
            print("Telemetry is active")
    """
    return telemetry_manager.is_enabled()


def health_check():
    """
    Perform a health check of the telemetry system

    Returns:
        dict: Health status information including enabled status, configuration, and diagnostics

    Example:
        from zen.telemetry import health_check
        status = health_check()
        print(f"Telemetry status: {status['status']}")
    """
    try:
        manager = telemetry_manager

        status = {
            "status": "healthy" if manager.is_enabled() else "disabled",
            "enabled": manager.is_enabled(),
            "opentelemetry_available": OPENTELEMETRY_AVAILABLE,
            "config": {
                "sample_rate": manager.get_config().sample_rate,
                "level": manager.get_config().level,
                "service_name": manager.get_config().service_name,
            }
        }

        if manager.is_enabled():
            status["details"] = {
                "tracer_available": manager.tracer is not None,
                "gcp_project": manager.get_config().get_gcp_project(),
            }

        return status

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "enabled": False
        }


__all__ = [
    "TelemetryManager",
    "TelemetryConfig",
    "traced",
    "instrument_class",
    "trace_performance",
    "DataSanitizer",
    "telemetry",
    "telemetry_manager",
    "disable_telemetry",
    "enable_telemetry",
    "is_telemetry_enabled",
    "health_check"
]