"""Fixtures Tests - Split from test_staging_clickhouse_http_native_ports.py

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability and Analytics Reliability
- Value Impact: Ensures correct ClickHouse port configuration preventing analytics failures
- Strategic Impact: Prevents $500K+ analytics pipeline failures due to configuration errors

Tests correct port configuration (HTTP:8123, Native:9000, HTTPS:8443),
connection mode selection, query execution, data consistency, and performance
across different connection types in staging environment.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from test_framework.mock_utils import mock_justified

def clickhouse_manager():
    """Create ClickHouse connection manager."""
    return ClickHouseConnectionManager()
