"""Utilities Tests - Split from test_usage_metering_billing.py

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

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
from app.db.clickhouse import get_clickhouse_client
from app.db.clickhouse_init import create_workload_events_table_if_missing
from app.schemas.llm_base_types import LLMProvider, TokenUsage
from app.schemas.UserPlan import PlanTier, PlanUsageSummary, UsageRecord
from app.services.cost_calculator import (
    BudgetManager,
    CostCalculatorService,
    CostTier,
)
from app.services.metrics.agent_metrics import AgentMetricsCollector

# Add project root to path


class MeteringCoreHelper:
    """Helper class for metering core functionality."""
    
    def __init__(self):
        self.clickhouse_client = None
        self.cost_calculator = CostCalculatorService()
        self.metrics_collector = AgentMetricsCollector()
        self.budget_manager = BudgetManager(daily_budget=Decimal("1000.00"))
        self.test_org_id = f"test_org_{int(time.time())}"
        self.usage_buffer = []


class RealTimeUsageTracker:
    """Real-time usage tracker helper."""
    
    def __init__(self, clickhouse_client, cost_calculator: CostCalculatorService):
        self.clickhouse_client = clickhouse_client
        self.cost_calculator = cost_calculator

    def _calculate_api_cost(self, endpoint: str, plan_tier: PlanTier) -> int:
        """Calculate API call cost in cents."""
        base_cost = {"free": 1, "pro": 0, "enterprise": 0}[plan_tier.value]
        multiplier = {"admin": 5, "agent": 3, "data": 2}.get(endpoint.split('/')[1] if '/' in endpoint else "standard", 1)
        return base_cost * multiplier

    def _calculate_agent_cost(self, agent_type: str, execution_time_ms: int, plan_tier: PlanTier) -> int:
        """Calculate agent execution cost in cents."""
        seconds = execution_time_ms / 1000.0
        cost_per_second = {"free": 0.5, "pro": 0.2, "enterprise": 0.1}[plan_tier.value]
        agent_multiplier = {"optimization": 3, "data": 2, "triage": 1, "admin": 1.5}.get(agent_type, 1)
        return int(seconds * cost_per_second * agent_multiplier * 100)

    def _calculate_storage_cost(self, gb: float, plan_tier: PlanTier) -> int:
        """Calculate storage cost in cents per GB."""
        cost_per_gb = {"free": 10, "pro": 5, "enterprise": 2}[plan_tier.value]
        return int(gb * cost_per_gb)

    def _calculate_bandwidth_cost(self, gb: float, plan_tier: PlanTier) -> int:
        """Calculate bandwidth cost in cents per GB."""
        cost_per_gb = {"free": 15, "pro": 8, "enterprise": 3}[plan_tier.value]
        return int(gb * cost_per_gb)


class BillingCalculationEngine:
    """Billing calculation engine helper."""
    
    def __init__(self, clickhouse_client):
        self.clickhouse_client = clickhouse_client

    def _process_usage_aggregation(self, results) -> Dict[str, Any]:
        """Process usage aggregation results."""
        usage_by_type = {}
        total_cost_cents = 0
        total_events = 0
        
        for result in results:
            if isinstance(result, dict):
                resource_type = result.get('resource_type')
                quantity = result.get('total_quantity', 0)
                cost_cents = result.get('total_cost_cents', 0)
                events = result.get('total_events', 0)
            else:
                resource_type, quantity, cost_cents, events = result
                
            usage_by_type[resource_type] = {
                "quantity": float(quantity),
                "cost_cents": int(cost_cents),
                "events": int(events)
            }
            total_cost_cents += int(cost_cents)
            total_events += int(events)
            
        return {
            "usage_by_type": usage_by_type,
            "total_cost_cents": total_cost_cents,
            "total_events": total_events
        }

    def _get_performance_fee_rate(self, plan_tier: PlanTier) -> float:
        """Get performance fee rate by plan tier."""
        return {"free": 0.0, "pro": 0.15, "enterprise": 0.20}[plan_tier.value]

    def _generate_line_items(self, usage_summary: Dict[str, Any], performance_fee_cents: int, tax_cents: int) -> List[Dict[str, Any]]:
        """Generate detailed line items for bill."""
        line_items = []
        
        for resource_type, details in usage_summary.get("usage_by_type", {}).items():
            line_items.append({
                "description": f"{resource_type.replace('_', ' ').title()} Usage",
                "quantity": details["quantity"],
                "cost_cents": details["cost_cents"]
            })
            
        if performance_fee_cents > 0:
            line_items.append({
                "description": "Performance Optimization Fee",
                "quantity": 1,
                "cost_cents": performance_fee_cents
            })
            
        if tax_cents > 0:
            line_items.append({
                "description": "Tax",
                "quantity": 1,
                "cost_cents": tax_cents
            })
            
        return line_items

    def _get_plan_limits(self, plan_tier: PlanTier) -> Dict[str, float]:
        """Get plan usage limits."""
        limits = {
            "free": {
                "api_call": 1000,
                "agent_execution": 300,  # seconds
                "token_usage": 50000,
                "storage": 1.0,  # GB
                "bandwidth": 5.0  # GB
            },
            "pro": {
                "api_call": 50000,
                "agent_execution": 18000,  # seconds (5 hours)
                "token_usage": 5000000,
                "storage": 100.0,  # GB
                "bandwidth": 500.0  # GB
            },
            "enterprise": {
                "api_call": float('inf'),
                "agent_execution": float('inf'),
                "token_usage": float('inf'),
                "storage": float('inf'),
                "bandwidth": float('inf')
            }
        }
        return limits[plan_tier.value]
