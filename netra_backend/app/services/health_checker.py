"""Health Checker compatibility module

This module provides compatibility for code expecting health_checker import.
All actual functionality is in health_check_service.py.
"""

# Import everything from the actual health check service
from netra_backend.app.services.health_check_service import *

# Provide alias for the main class
from netra_backend.app.services.health_check_service import HealthCheckService as HealthChecker