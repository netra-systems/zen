"""Utilities Tests - Split from test_concurrent_user_auth_load.py

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise
- Business Goal: Scalability & Performance
- Value Impact: Validates system handles enterprise-level concurrent load
- Revenue Impact: Protects $45K Enterprise segment revenue

Tests 100+ concurrent login attempts, response times under load,
token collision prevention, and rate limiting mechanisms.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Optional, Any, Tuple
import httpx
from dataclasses import dataclass
from collections import defaultdict
import statistics
from app.core.configuration.database import DatabaseConfig
from test_framework.real_service_helper import RealServiceHelper
from test_framework.mock_utils import mock_justified
import redis.asyncio as redis

    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.service_helper = RealServiceHelper()
        self.results: List[AuthenticationResult] = []
        self.rate_limit_hits = 0
        self.backpressure_events = 0

    def calculate_metrics(self, results: List[AuthenticationResult]) -> Dict[str, Any]:
        """Calculate performance metrics from results."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        response_times = [r.response_time for r in results]
        
        metrics = {
            "total_attempts": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "p50_response_time": statistics.median(response_times) if response_times else 0,
            "p95_response_time": self._calculate_percentile(response_times, 95) if response_times else 0,
            "p99_response_time": self._calculate_percentile(response_times, 99) if response_times else 0,
            "rate_limit_hits": self.rate_limit_hits,
            "backpressure_events": self.backpressure_events,
            "retry_attempts": sum(r.retry_count for r in results)
        }
        
        return metrics

    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def validate_no_token_collisions(self, results: List[AuthenticationResult]) -> bool:
        """Validate that all generated tokens are unique."""
        tokens = [r.token for r in results if r.token]
        unique_tokens = set(tokens)
        return len(tokens) == len(unique_tokens)
