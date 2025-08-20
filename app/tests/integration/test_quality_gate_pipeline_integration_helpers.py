"""Utilities Tests - Split from test_quality_gate_pipeline_integration.py

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

def mock_justified(reason: str):
    """Mock justification decorator per SPEC/testing.xml"""
    def decorator(func):
        func._mock_justification = reason
        return func
    return decorator

    def decorator(func):
        func._mock_justification = reason
        return func
