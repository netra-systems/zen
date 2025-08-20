"""Utilities Tests - Split from test_staging_multi_service_startup_sequence.py

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability and Deployment Reliability
- Value Impact: Ensures proper service orchestration and dependency resolution in staging
- Revenue Impact: Prevents failed deployments that could delay releases and impact $2M+ ARR

Tests correct startup order (Auth → Backend → Frontend), health check cascade,
and service dependency resolution in staging environment.
"""

import asyncio
import pytest
from unittest.mock import patch, Mock, AsyncMock, call
from typing import Dict, List, Optional
import time
from test_framework.mock_utils import mock_justified

    def __init__(self, name: str, dependencies: List[str] = None, startup_time: float = 0.1):
        self.name = name
        self.dependencies = dependencies or []
        self.startup_time = startup_time
        self.started = False
        self.healthy = False
        self.startup_order = 0

    def stop(self):
        """Mock service stop."""
        self.started = False
        self.healthy = False

    def __init__(self):
        self.services: Dict[str, MockService] = {}
        self.startup_order: List[str] = []

    def register_service(self, service: MockService):
        """Register a service."""
        self.services[service.name] = service
