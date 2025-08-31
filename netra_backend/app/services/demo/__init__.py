"""Demo service module for handling enterprise demonstration functionality."""

from netra_backend.app.services.demo.analytics_tracker import AnalyticsTracker
from netra_backend.app.services.demo.demo_metrics_generator import DemoMetricsGenerator
from netra_backend.app.services.demo.demo_service import DemoService, get_demo_service
from netra_backend.app.services.demo.industry_config import INDUSTRY_FACTORS
from netra_backend.app.services.demo.report_generator import ReportGenerator
# Note: SessionManager now consolidated in Redis service
# from netra_backend.app.services.redis.session_manager import RedisSessionManager as SessionManager

__all__ = [
    "DemoService",
    "get_demo_service",
    "INDUSTRY_FACTORS",
    "DemoMetricsGenerator",
    "ReportGenerator",
    # "SessionManager",  # Now consolidated in Redis service
    "AnalyticsTracker"
]