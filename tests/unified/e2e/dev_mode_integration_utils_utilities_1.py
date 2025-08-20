"""Utilities_1 Tests - Split from dev_mode_integration_utils.py

BVJ (Business Value Justification):
- Segment: Platform/Internal | Goal: Development Velocity | Impact: Test Infrastructure
- Value Impact: Accelerates test development and reduces test maintenance overhead
- Strategic Impact: Enables comprehensive testing with reusable components
- Risk Mitigation: Centralizes common test patterns to reduce bugs and inconsistencies

Utilities:
✅ CORS validation helpers
✅ User journey simulation utilities
✅ Performance metrics collection
✅ Service coordination monitors
✅ Resource usage tracking
✅ WebSocket connection testing
✅ Error scenario simulation
✅ Test data management
"""

import asyncio
import httpx
import websockets
import json
import time
import uuid
import os
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from enum import Enum
from abc import ABC, abstractmethod

def create_test_data_factory() -> Dict[str, Callable]:
    """Create factory functions for generating test data."""
    
    def create_test_user():
        """Create test user data."""
        user_id = str(uuid.uuid4())
        return {
            "id": user_id,
            "email": f"test_user_{user_id[:8]}@example.com",
            "name": f"Test User {user_id[:8]}",
            "created_at": time.time()
        }
    
    def create_test_message():
        """Create test message data."""
        return {
            "id": str(uuid.uuid4()),
            "content": "Hello, can you help me optimize my AI workload?",
            "type": "user_message",
            "timestamp": time.time()
        }
    
    def create_test_thread():
        """Create test thread data."""
        return {
            "id": str(uuid.uuid4()),
            "title": "AI Optimization Discussion",
            "created_at": time.time(),
            "message_count": 0
        }
    
    return {
        "user": create_test_user,
        "message": create_test_message,
        "thread": create_test_thread
    }

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.requests_made == 0:
            return 0.0
        return self.requests_successful / self.requests_made

    def finalize(self):
        """Finalize metrics calculation."""
        if self.end_time == 0.0:
            self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    def __init__(self):
        self.metrics = TestMetrics()
        self.response_times: List[float] = []
        self._start_time = time.time()

    def start_request(self) -> float:
        """Start timing a request."""
        return time.time()

    def end_request(self, start_time: float, success: bool = True):
        """End timing a request and update metrics."""
        response_time = time.time() - start_time
        self.response_times.append(response_time)
        
        self.metrics.requests_made += 1
        
        if success:
            self.metrics.requests_successful += 1
        else:
            self.metrics.requests_failed += 1
        
        # Update response time statistics
        if response_time > self.metrics.max_response_time:
            self.metrics.max_response_time = response_time
        
        if response_time < self.metrics.min_response_time:
            self.metrics.min_response_time = response_time
        
        # Calculate running average
        if self.response_times:
            self.metrics.avg_response_time = sum(self.response_times) / len(self.response_times)

    def add_error(self, error: str):
        """Add an error to the metrics."""
        self.metrics.errors.append(error)

    def get_metrics(self) -> TestMetrics:
        """Get current metrics."""
        self.metrics.finalize()
        return self.metrics

    def validate_cors_headers(headers: Dict[str, str], origin: str) -> Dict[str, bool]:
        """Validate CORS headers in a response."""
        return {
            "has_allow_origin": "access-control-allow-origin" in headers,
            "origin_matches": headers.get("access-control-allow-origin") in [origin, "*"],
            "allows_credentials": headers.get("access-control-allow-credentials") == "true",
            "has_allow_methods": "access-control-allow-methods" in headers,
            "has_allow_headers": "access-control-allow-headers" in headers,
            "has_expose_headers": "access-control-expose-headers" in headers,
            "has_max_age": "access-control-max-age" in headers
        }

    def create_cors_preflight_headers(origin: str, method: str = "POST", 
                                    headers: str = "Content-Type,Authorization") -> Dict[str, str]:
        """Create headers for CORS preflight request."""
        return {
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers
        }

    def __init__(self, url: str, timeout: float = 10.0):
        self.url = url
        self.timeout = timeout
        self.connection: Optional[websockets.WebSocketServerProtocol] = None
        self.messages_received: List[Dict[str, Any]] = []
        self.connection_time: float = 0.0

    def __init__(self, base_url: str, auth_url: str):
        self.base_url = base_url
        self.auth_url = auth_url
        self.user_id = str(uuid.uuid4())
        self.email = f"test_user_{self.user_id[:8]}@example.com"
        self.access_token: Optional[str] = None
        self.session_data: Dict[str, Any] = {}
        self.performance_monitor = PerformanceMonitor()

    def __init__(self, services: Dict[str, str]):
        """Initialize with service name -> URL mapping."""
        self.services = services
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}
        
        for service_name in services:
            self.health_history[service_name] = []

    def get_service_availability(self, service_name: str, 
                               time_window_minutes: int = 60) -> float:
        """Calculate service availability over time window."""
        if service_name not in self.health_history:
            return 0.0
        
        history = self.health_history[service_name]
        if not history:
            return 0.0
        
        # Filter to time window
        cutoff_time = time.time() - (time_window_minutes * 60)
        recent_checks = [check for check in history if check["timestamp"] >= cutoff_time]
        
        if not recent_checks:
            return 0.0
        
        healthy_checks = sum(1 for check in recent_checks if check["healthy"])
        return healthy_checks / len(recent_checks)

    def create_test_user():
        """Create test user data."""
        user_id = str(uuid.uuid4())
        return {
            "id": user_id,
            "email": f"test_user_{user_id[:8]}@example.com",
            "name": f"Test User {user_id[:8]}",
            "created_at": time.time()
        }
