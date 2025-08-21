"""
Startup Checks Module

Comprehensive startup check system split into focused components.
Each module handles specific check categories under 450-line limit.
"""

from netra_backend.app.services.apex_optimizer_agent.models import StartupCheckResult
from netra_backend.app.startup_checks.checker import StartupChecker
from netra_backend.app.startup_checks.utils import run_startup_checks
from netra_backend.app.startup_checks.environment_checks import EnvironmentChecker
from netra_backend.app.startup_checks.database_checks import DatabaseChecker

__all__ = [
    "StartupCheckResult",
    "StartupChecker",
    "run_startup_checks",
    "EnvironmentChecker",
    "DatabaseChecker"
]