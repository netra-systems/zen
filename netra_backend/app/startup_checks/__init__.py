"""
Startup Checks Module

Comprehensive startup check system split into focused components.
Each module handles specific check categories under 450-line limit.
"""

from netra_backend.app.startup_checks.checker import StartupChecker
from netra_backend.app.startup_checks.database_checks import DatabaseChecker
from netra_backend.app.startup_checks.environment_checks import EnvironmentChecker
from netra_backend.app.startup_checks.models import StartupCheckResult
from netra_backend.app.startup_checks.utils import run_startup_checks

# Backward compatibility alias
startup_checks = run_startup_checks

__all__ = [
    "StartupCheckResult",
    "StartupChecker", 
    "run_startup_checks",
    "startup_checks",
    "EnvironmentChecker",
    "DatabaseChecker"
]