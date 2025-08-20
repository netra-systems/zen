"""Managers Tests - Split from test_staging_clickhouse_http_native_ports.py

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

    def __init__(self):
        self.connections = {}
        self.port_config = {
            "http": 8123,
            "native": 9000, 
            "https": 8443
        }
        self.query_log = []
        self.performance_metrics = {}

    def _build_connection_url(self, protocol: str, host: str, port: int) -> str:
        """Build connection URL for protocol and port."""
        if protocol == "http":
            return f"http://{host}:{port}"
        elif protocol == "https":
            return f"https://{host}:{port}"
        elif protocol == "native":
            return f"clickhouse://{host}:{port}"
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")

    def _update_performance_metrics(self, protocol: str, execution_time: float) -> None:
        """Update performance metrics for protocol."""
        if protocol not in self.performance_metrics:
            self.performance_metrics[protocol] = {
                "total_queries": 0,
                "total_time": 0.0,
                "avg_time": 0.0
            }
        
        metrics = self.performance_metrics[protocol]
        metrics["total_queries"] += 1
        metrics["total_time"] += execution_time
        metrics["avg_time"] = metrics["total_time"] / metrics["total_queries"]

    def validate_port_configuration(self) -> Dict[str, bool]:
        """Validate port configuration matches staging requirements."""
        return {
            "http_port_8123": self.port_config["http"] == 8123,
            "native_port_9000": self.port_config["native"] == 9000,
            "https_port_8443": self.port_config["https"] == 8443
        }

    def get_connection_summary(self) -> Dict[str, any]:
        """Get summary of all connections and metrics."""
        return {
            "total_connections": len(self.connections),
            "connections_by_protocol": {
                protocol: len([c for c in self.connections.values() if c["protocol"] == protocol])
                for protocol in self.port_config.keys()
            },
            "performance_metrics": self.performance_metrics,
            "total_queries": len(self.query_log)
        }
