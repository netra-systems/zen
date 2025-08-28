"""Fixtures Tests - Split from test_usage_metering_billing.py

BVJ: Protects $100K-$200K MRR through accurate consumption tracking
Segment: ALL tiers - revenue protection critical  
Business Goal: Ensure 100% billing accuracy and prevent revenue leakage
Value Impact: Real-time usage tracking for API calls, agent execution, tokens, storage, bandwidth
Strategic Impact: Foundation for consumption-based pricing and overage billing

Tests comprehensive usage metering pipeline:
- Real-time usage capture across all service boundaries  
- ClickHouse integration for high-volume metrics storage
- Billing calculation accuracy with performance fee model
- Overage handling and usage alerts
- Multi-tenant usage isolation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.db.clickhouse_init import create_workload_events_table_if_missing
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from netra_backend.app.schemas.user_plan import PlanTier, PlanUsageSummary, UsageRecord
from netra_backend.app.services.cost_calculator import (
    BudgetManager,
    CostCalculatorService,
    CostTier,
)
from netra_backend.app.services.metrics.agent_metrics import AgentMetricsCollector

class RealTimeUsageTracker:
    """Mock class for testing."""
    def __init__(self, clickhouse_client, cost_calculator):
        self.clickhouse_client = clickhouse_client
        self.cost_calculator = cost_calculator

class BillingCalculationEngine:
    """Mock class for testing."""
    def __init__(self, clickhouse_client):
        self.clickhouse_client = clickhouse_client

@pytest.fixture
def usage_tracker(metering_core):
    """Initialize real-time usage tracker."""
    return RealTimeUsageTracker(metering_core.clickhouse_client, metering_core.cost_calculator)

@pytest.fixture
def billing_engine(metering_core):
    """Initialize billing calculation engine."""
    return BillingCalculationEngine(metering_core.clickhouse_client)
