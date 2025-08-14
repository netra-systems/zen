"""Quality Monitoring Service Tests - Main Entry Point

This file serves as the main entry point for quality monitoring tests.
The actual tests have been split into focused modules for better maintainability.
"""

# Import all test modules to ensure they are discovered by pytest
from app.tests.services.test_quality_monitoring_basic import *
from app.tests.services.test_quality_monitoring_metrics import *
from app.tests.services.test_quality_monitoring_alerts import *
from app.tests.services.test_quality_monitoring_integration import *