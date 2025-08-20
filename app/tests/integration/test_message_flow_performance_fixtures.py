"""Fixtures Tests - Split from test_message_flow_performance.py"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone
from app.tests.integration.test_unified_message_flow import MessageFlowTracker
from app.logging_config import central_logger
import tracemalloc

def perf_tracker():
    """Create performance metrics tracker."""
    return PerformanceMetricsTracker()
