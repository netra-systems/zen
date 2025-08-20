"""Fixtures Tests - Split from test_quality_gate_pipeline_integration.py

Business Value Justification (BVJ):
- Segment: Enterprise ($15K MRR protection)
- Business Goal: Quality Assurance for AI Response Standards
- Value Impact: Protects enterprise customers from AI response quality degradation
- Revenue Impact: Prevents churn from poor AI quality, ensures enterprise SLA compliance
"""

import asyncio
import pytest
import os
from typing import Dict, List, Any, Tuple
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, UTC
import json
from app.services.quality_gate.quality_gate_core import QualityGateService
from app.services.quality_gate.quality_gate_models import (
from app.tests.helpers.quality_gate_helpers import create_redis_mock, create_quality_service
from app.logging_config import central_logger

    def redis_manager(self):
        """Create mocked Redis manager for integration testing"""
        redis_mock = create_redis_mock()
        # Add additional async methods needed for integration
        redis_mock.get_redis = MagicMock()
        redis_mock.get_redis.return_value.keys = AsyncMock(return_value=[b"quality_metrics:test_key"])
        redis_mock.cleanup = AsyncMock()
        return redis_mock

    def quality_service(self, redis_manager):
        """Create quality service with mocked Redis integration"""
        service = QualityGateService(redis_manager=redis_manager)
        return service
