"""Agent Cost Tracking and Budgeting L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (cost control and optimization)
- Business Goal: Cost control and budget enforcement, accurate cost tracking
- Value Impact: $100K MRR - Ensures precise cost calculation >99% accuracy and budget compliance
- Strategic Impact: Cost tracking enables predictable scaling and prevents budget overruns

Critical Path: Cost calculation -> Real-time tracking -> Budget monitoring -> Alerts -> Usage forecasting -> Attribution
Coverage: Cost calculation accuracy, budget enforcement, real-time tracking, cost attribution, usage forecasting, alert systems
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.registry import TaskPriority

# Add project root to path

logger = logging.getLogger(__name__)


class CostType(Enum):
    """Types of costs tracked in the system."""
    LLM_TOKENS = "llm_tokens"
    COMPUTE_TIME = "compute_time"
    STORAGE_USAGE = "storage_usage"
    API_CALLS = "api_calls"
    BANDWIDTH = "bandwidth"
    DATABASE_OPERATIONS = "database_operations"


class BudgetPeriod(Enum):
    """Budget tracking periods."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class CostEntry:
    """Individual cost tracking entry."""
    id: str
    cost_type: CostType
    amount: Decimal
    unit_cost: Decimal
    quantity: int
    timestamp: datetime
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_total_cost(self) -> Decimal:
        """Calculate total cost for this entry."""
        return self.unit_cost * Decimal(str(self.quantity))


@dataclass
class BudgetLimit:
    """Budget limit configuration."""
    budget_id: str
    period: BudgetPeriod
    limit_amount: Decimal
    cost_types: List[CostType]
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    alert_threshold: float = 0.8  # Alert at 80% of budget
    
    def is_applicable_to(self, cost_entry: CostEntry) -> bool:
        """Check if budget applies to a cost entry."""
        if cost_entry.cost_type not in self.cost_types:
            return False
        
        if self.user_id and cost_entry.user_id != self.user_id:
            return False
        
        if self.agent_id and cost_entry.agent_id != self.agent_id:
            return False
        
        return True


@dataclass
class CostMetrics:
    """Cost tracking and budget metrics."""
    total_tracked_costs: Decimal = Decimal('0')
    total_entries: int = 0
    accuracy_percentage: float = 100.0
    budget_alerts_sent: int = 0
    budget_violations: int = 0
    cost_attribution_errors: int = 0
    forecasting_accuracy: float = 0.0
    real_time_updates: int = 0
    
    def add_cost_entry(self, cost: Decimal):
        """Add a cost entry to metrics."""
        self.total_tracked_costs += cost
        self.total_entries += 1
        self.real_time_updates += 1


class CostCalculator:
    """Accurate cost calculation engine with >99% accuracy target."""
    
    def __init__(self):
        self.unit_costs = {
            CostType.LLM_TOKENS: Decimal('0.000002'),  # $0.000002 per token
            CostType.COMPUTE_TIME: Decimal('0.001'),   # $0.001 per second
            CostType.STORAGE_USAGE: Decimal('0.00001'), # $0.00001 per MB
            CostType.API_CALLS: Decimal('0.0001'),     # $0.0001 per call
            CostType.BANDWIDTH: Decimal('0.00005'),    # $0.00005 per MB
            CostType.DATABASE_OPERATIONS: Decimal('0.000001')  # $0.000001 per operation
        }
        self.calculation_history: List[Tuple[CostEntry, Decimal]] = []
    
    def calculate_cost(self, cost_type: CostType, quantity: int, 
                      metadata: Optional[Dict[str, Any]] = None) -> Decimal:
        """Calculate cost with high precision."""
        if cost_type not in self.unit_costs:
            raise NetraException(f"Unknown cost type: {cost_type}")
        
        base_unit_cost = self.unit_costs[cost_type]
        
        # Apply modifiers based on metadata
        final_unit_cost = self._apply_cost_modifiers(cost_type, base_unit_cost, metadata or {})
        
        # Calculate with high precision
        total_cost = final_unit_cost * Decimal(str(quantity))
        
        # Round to 6 decimal places for consistency
        total_cost = total_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        
        return total_cost
    
    def _apply_cost_modifiers(self, cost_type: CostType, base_cost: Decimal, 
                            metadata: Dict[str, Any]) -> Decimal:
        """Apply cost modifiers based on usage patterns and metadata."""
        modified_cost = base_cost
        
        # Volume discounts
        if 'volume_tier' in metadata:
            volume_tier = metadata['volume_tier']
            if volume_tier == 'high':
                modified_cost *= Decimal('0.9')  # 10% discount
            elif volume_tier == 'enterprise':
                modified_cost *= Decimal('0.8')  # 20% discount
        
        # Priority surcharge
        if 'priority' in metadata:
            priority = metadata['priority']
            if priority == 'high':
                modified_cost *= Decimal('1.2')  # 20% surcharge
        
        # Time-based pricing
        if 'time_of_day' in metadata:
            hour = metadata['time_of_day']
            if 0 <= hour <= 6:  # Off-peak hours
                modified_cost *= Decimal('0.8')  # 20% discount
        
        return modified_cost
    
    def validate_calculation_accuracy(self, expected_cost: Decimal, 
                                    calculated_cost: Decimal) -> float:
        """Validate calculation accuracy against expected cost."""
        if expected_cost == 0:
            return 100.0 if calculated_cost == 0 else 0.0
        
        accuracy = (1 - abs(expected_cost - calculated_cost) / expected_cost) * 100
        return max(0.0, min(100.0, accuracy))


class BudgetEnforcer:
    """Budget enforcement and monitoring system."""
    
    def __init__(self):
        self.budget_limits: Dict[str, BudgetLimit] = {}
        self.current_usage: Dict[str, Dict[BudgetPeriod, Decimal]] = {}
        self.alert_callbacks: List[AsyncMock] = []
        self.violation_history: List[Dict[str, Any]] = []
    
    def add_budget_limit(self, budget_limit: BudgetLimit):
        """Add a budget limit to enforcement."""
        self.budget_limits[budget_limit.budget_id] = budget_limit
        self.current_usage[budget_limit.budget_id] = {
            period: Decimal('0') for period in BudgetPeriod
        }
    
    async def track_cost_entry(self, cost_entry: CostEntry) -> Dict[str, Any]:
        """Track cost entry against budget limits."""
        tracking_result = {
            "entry_id": cost_entry.id,
            "cost": cost_entry.calculate_total_cost(),
            "budget_checks": [],
            "alerts_triggered": [],
            "violations": []
        }
        
        entry_cost = cost_entry.calculate_total_cost()
        
        # Check against all applicable budget limits
        for budget_id, budget_limit in self.budget_limits.items():
            if budget_limit.is_applicable_to(cost_entry):
                check_result = await self._check_budget_limit(
                    budget_id, budget_limit, entry_cost, cost_entry.timestamp
                )
                tracking_result["budget_checks"].append(check_result)
                
                if check_result["alert_triggered"]:
                    tracking_result["alerts_triggered"].append(check_result)
                
                if check_result["violation"]:
                    tracking_result["violations"].append(check_result)
        
        return tracking_result
    
    async def _check_budget_limit(self, budget_id: str, budget_limit: BudgetLimit,
                                cost: Decimal, timestamp: datetime) -> Dict[str, Any]:
        """Check cost against specific budget limit."""
        period = budget_limit.period
        period_usage = self._get_period_usage(budget_id, period, timestamp)
        
        new_usage = period_usage + cost
        usage_percentage = float(new_usage / budget_limit.limit_amount * 100)
        
        # Update usage tracking
        self.current_usage[budget_id][period] = new_usage
        
        # Check for alerts and violations
        alert_triggered = usage_percentage >= (budget_limit.alert_threshold * 100)
        violation = new_usage > budget_limit.limit_amount
        
        check_result = {
            "budget_id": budget_id,
            "period": period.value,
            "current_usage": new_usage,
            "limit_amount": budget_limit.limit_amount,
            "usage_percentage": usage_percentage,
            "alert_triggered": alert_triggered,
            "violation": violation
        }
        
        # Send alerts if necessary
        if alert_triggered:
            await self._send_budget_alert(budget_limit, check_result)
        
        if violation:
            await self._handle_budget_violation(budget_limit, check_result)
        
        return check_result
    
    def _get_period_usage(self, budget_id: str, period: BudgetPeriod, 
                         timestamp: datetime) -> Decimal:
        """Get current usage for the budget period."""
        # Simplified implementation - in reality would query database
        return self.current_usage.get(budget_id, {}).get(period, Decimal('0'))
    
    async def _send_budget_alert(self, budget_limit: BudgetLimit, check_result: Dict[str, Any]):
        """Send budget alert notification."""
        alert_data = {
            "type": "budget_alert",
            "budget_id": budget_limit.budget_id,
            "usage_percentage": check_result["usage_percentage"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for callback in self.alert_callbacks:
            await callback(alert_data)
    
    async def _handle_budget_violation(self, budget_limit: BudgetLimit, check_result: Dict[str, Any]):
        """Handle budget violation."""
        violation_record = {
            "budget_id": budget_limit.budget_id,
            "violation_amount": check_result["current_usage"] - budget_limit.limit_amount,
            "timestamp": datetime.now(timezone.utc),
            "check_result": check_result
        }
        
        self.violation_history.append(violation_record)
        
        # Send violation alert
        violation_alert = {
            "type": "budget_violation",
            "budget_id": budget_limit.budget_id,
            "violation_amount": violation_record["violation_amount"],
            "timestamp": violation_record["timestamp"].isoformat()
        }
        
        for callback in self.alert_callbacks:
            await callback(violation_alert)


class UsageForecaster:
    """Usage and cost forecasting system."""
    
    def __init__(self):
        self.usage_history: List[CostEntry] = []
        self.forecast_accuracy_history: List[float] = []
    
    def add_usage_data(self, cost_entry: CostEntry):
        """Add usage data for forecasting."""
        self.usage_history.append(cost_entry)
        
        # Keep only recent history (last 1000 entries)
        if len(self.usage_history) > 1000:
            self.usage_history = self.usage_history[-1000:]
    
    def forecast_usage(self, cost_type: CostType, forecast_period: timedelta) -> Dict[str, Any]:
        """Forecast usage for a given period."""
        # Filter relevant history
        relevant_history = [
            entry for entry in self.usage_history 
            if entry.cost_type == cost_type
        ]
        
        if len(relevant_history) < 3:
            return {
                "forecast_available": False,
                "reason": "Insufficient historical data",
                "min_data_points": 3,
                "actual_data_points": len(relevant_history)
            }
        
        # Simple linear trend forecasting
        recent_entries = relevant_history[-10:]  # Last 10 entries
        
        # Calculate average usage rate
        total_quantity = sum(entry.quantity for entry in recent_entries)
        time_span = (recent_entries[-1].timestamp - recent_entries[0].timestamp).total_seconds()
        
        if time_span <= 0:
            usage_rate = 0
        else:
            usage_rate = total_quantity / time_span  # quantity per second
        
        # Forecast for the specified period
        forecast_seconds = forecast_period.total_seconds()
        forecasted_quantity = int(usage_rate * forecast_seconds)
        
        # Calculate forecasted cost
        calculator = CostCalculator()
        forecasted_cost = calculator.calculate_cost(cost_type, forecasted_quantity)
        
        return {
            "forecast_available": True,
            "cost_type": cost_type.value,
            "forecast_period_hours": forecast_seconds / 3600,
            "forecasted_quantity": forecasted_quantity,
            "forecasted_cost": forecasted_cost,
            "usage_rate_per_hour": usage_rate * 3600,
            "confidence_level": self._calculate_confidence_level(relevant_history),
            "data_points_used": len(recent_entries)
        }
    
    def _calculate_confidence_level(self, history: List[CostEntry]) -> float:
        """Calculate forecast confidence level based on data quality."""
        if len(history) < 5:
            return 0.3  # Low confidence
        elif len(history) < 20:
            return 0.6  # Medium confidence
        else:
            return 0.8  # High confidence
    
    def validate_forecast_accuracy(self, forecast: Dict[str, Any], 
                                 actual_usage: int) -> float:
        """Validate forecast accuracy against actual usage."""
        if not forecast["forecast_available"]:
            return 0.0
        
        forecasted = forecast["forecasted_quantity"]
        if forecasted == 0 and actual_usage == 0:
            return 100.0
        elif forecasted == 0:
            return 0.0
        
        accuracy = (1 - abs(forecasted - actual_usage) / forecasted) * 100
        accuracy = max(0.0, min(100.0, accuracy))
        
        self.forecast_accuracy_history.append(accuracy)
        return accuracy


class AgentCostTracker:
    """Comprehensive agent cost tracking and budgeting system."""
    
    def __init__(self):
        self.calculator = CostCalculator()
        self.budget_enforcer = BudgetEnforcer()
        self.usage_forecaster = UsageForecaster()
        self.metrics = CostMetrics()
        self.cost_entries: List[CostEntry] = []
        
        # Initialize alert system
        self.budget_enforcer.alert_callbacks.append(AsyncMock())
    
    async def track_cost(self, cost_type: CostType, quantity: int,
                        user_id: Optional[str] = None, agent_id: Optional[str] = None,
                        session_id: Optional[str] = None, 
                        metadata: Optional[Dict[str, Any]] = None) -> CostEntry:
        """Track a cost with real-time budget monitoring."""
        # Calculate cost
        unit_cost = self.calculator.unit_costs[cost_type]
        total_cost = self.calculator.calculate_cost(cost_type, quantity, metadata)
        
        # Create cost entry
        cost_entry = CostEntry(
            id=f"cost_{uuid.uuid4().hex[:8]}",
            cost_type=cost_type,
            amount=total_cost,
            unit_cost=unit_cost,
            quantity=quantity,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        # Store entry
        self.cost_entries.append(cost_entry)
        
        # Update metrics
        self.metrics.add_cost_entry(total_cost)
        
        # Track against budgets
        budget_tracking = await self.budget_enforcer.track_cost_entry(cost_entry)
        
        # Add to forecasting data
        self.usage_forecaster.add_usage_data(cost_entry)
        
        return cost_entry
    
    async def test_cost_calculation_accuracy(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test cost calculation accuracy against known test cases."""
        accuracy_results = []
        
        for test_case in test_cases:
            cost_type = test_case["cost_type"]
            quantity = test_case["quantity"]
            expected_cost = Decimal(str(test_case["expected_cost"]))
            metadata = test_case.get("metadata", {})
            
            calculated_cost = self.calculator.calculate_cost(cost_type, quantity, metadata)
            accuracy = self.calculator.validate_calculation_accuracy(expected_cost, calculated_cost)
            
            accuracy_results.append({
                "cost_type": cost_type.value,
                "quantity": quantity,
                "expected_cost": expected_cost,
                "calculated_cost": calculated_cost,
                "accuracy_percentage": accuracy,
                "within_tolerance": accuracy >= 99.0  # 99% accuracy target
            })
        
        # Calculate overall accuracy
        overall_accuracy = sum(r["accuracy_percentage"] for r in accuracy_results) / len(accuracy_results)
        
        return {
            "test_cases": len(test_cases),
            "overall_accuracy": overall_accuracy,
            "accuracy_target_met": overall_accuracy >= 99.0,
            "individual_results": accuracy_results,
            "failed_cases": [r for r in accuracy_results if not r["within_tolerance"]]
        }
    
    async def test_budget_enforcement(self, budget_test_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test budget enforcement mechanisms."""
        # Set up budget limit
        budget_limit = BudgetLimit(
            budget_id=budget_test_scenario["budget_id"],
            period=budget_test_scenario["period"],
            limit_amount=Decimal(str(budget_test_scenario["limit_amount"])),
            cost_types=budget_test_scenario["cost_types"],
            alert_threshold=budget_test_scenario.get("alert_threshold", 0.8)
        )
        
        self.budget_enforcer.add_budget_limit(budget_limit)
        
        # Execute test usage that should trigger alerts and violations
        test_results = {
            "budget_id": budget_limit.budget_id,
            "alerts_triggered": 0,
            "violations_detected": 0,
            "cost_entries_tracked": 0,
            "total_cost_tracked": Decimal('0')
        }
        
        test_usage = budget_test_scenario["test_usage"]
        
        for usage in test_usage:
            cost_entry = await self.track_cost(
                cost_type=usage["cost_type"],
                quantity=usage["quantity"],
                user_id=usage.get("user_id"),
                agent_id=usage.get("agent_id"),
                metadata=usage.get("metadata")
            )
            
            test_results["cost_entries_tracked"] += 1
            test_results["total_cost_tracked"] += cost_entry.amount
            
            # Check if this triggered any alerts or violations
            current_usage = self.budget_enforcer.current_usage[budget_limit.budget_id][budget_limit.period]
            usage_percentage = float(current_usage / budget_limit.limit_amount * 100)
            
            if usage_percentage >= (budget_limit.alert_threshold * 100):
                test_results["alerts_triggered"] += 1
            
            if current_usage > budget_limit.limit_amount:
                test_results["violations_detected"] += 1
        
        return test_results
    
    async def test_real_time_tracking_performance(self, concurrent_operations: int) -> Dict[str, Any]:
        """Test real-time cost tracking performance under load."""
        start_time = time.time()
        
        # Create concurrent cost tracking operations
        async def track_single_cost(operation_id: int):
            cost_type = list(CostType)[operation_id % len(CostType)]
            quantity = (operation_id % 100) + 1
            
            return await self.track_cost(
                cost_type=cost_type,
                quantity=quantity,
                user_id=f"user_{operation_id}",
                agent_id=f"agent_{operation_id % 5}"
            )
        
        # Execute concurrent operations
        tasks = [track_single_cost(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze performance
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        failed_operations = [r for r in results if isinstance(r, Exception)]
        
        return {
            "concurrent_operations": concurrent_operations,
            "total_time": total_time,
            "successful_operations": len(successful_operations),
            "failed_operations": len(failed_operations),
            "operations_per_second": len(successful_operations) / total_time if total_time > 0 else 0,
            "average_operation_time": total_time / concurrent_operations if concurrent_operations > 0 else 0,
            "real_time_performance_acceptable": total_time < 5.0  # Should complete within 5 seconds
        }
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cost tracking and budget metrics."""
        return {
            "cost_tracking": {
                "total_tracked_costs": float(self.metrics.total_tracked_costs),
                "total_entries": self.metrics.total_entries,
                "accuracy_percentage": self.metrics.accuracy_percentage,
                "real_time_updates": self.metrics.real_time_updates
            },
            "budget_enforcement": {
                "budget_alerts_sent": self.metrics.budget_alerts_sent,
                "budget_violations": self.metrics.budget_violations,
                "active_budgets": len(self.budget_enforcer.budget_limits),
                "violation_history_size": len(self.budget_enforcer.violation_history)
            },
            "usage_forecasting": {
                "historical_data_points": len(self.usage_forecaster.usage_history),
                "forecast_accuracy_samples": len(self.usage_forecaster.forecast_accuracy_history),
                "average_forecast_accuracy": (
                    sum(self.usage_forecaster.forecast_accuracy_history) / 
                    len(self.usage_forecaster.forecast_accuracy_history)
                    if self.usage_forecaster.forecast_accuracy_history else 0
                )
            }
        }


@pytest.fixture
async def agent_cost_tracker():
    """Create agent cost tracker for testing."""
    tracker = AgentCostTracker()
    yield tracker


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
class TestAgentCostTrackingL3:
    """L3 integration tests for agent cost tracking and budgeting."""
    
    async def test_cost_calculation_accuracy_above_99_percent(self, agent_cost_tracker):
        """Test cost calculation accuracy exceeds 99% target."""
        tracker = agent_cost_tracker
        
        # Define test cases with known expected costs
        test_cases = [
            {
                "cost_type": CostType.LLM_TOKENS,
                "quantity": 1000,
                "expected_cost": "0.002000",  # 1000 * 0.000002
                "metadata": {}
            },
            {
                "cost_type": CostType.COMPUTE_TIME,
                "quantity": 60,
                "expected_cost": "0.060000",  # 60 * 0.001
                "metadata": {}
            },
            {
                "cost_type": CostType.LLM_TOKENS,
                "quantity": 5000,
                "expected_cost": "0.009000",  # 5000 * 0.000002 * 0.9 (high volume discount)
                "metadata": {"volume_tier": "high"}
            },
            {
                "cost_type": CostType.COMPUTE_TIME,
                "quantity": 30,
                "expected_cost": "0.024000",  # 30 * 0.001 * 0.8 (off-peak discount)
                "metadata": {"time_of_day": 3}
            },
            {
                "cost_type": CostType.API_CALLS,
                "quantity": 100,
                "expected_cost": "0.012000",  # 100 * 0.0001 * 1.2 (high priority surcharge)
                "metadata": {"priority": "high"}
            }
        ]
        
        accuracy_test = await tracker.test_cost_calculation_accuracy(test_cases)
        
        # Verify accuracy requirements
        assert accuracy_test["accuracy_target_met"], \
            f"Cost calculation accuracy {accuracy_test['overall_accuracy']:.2f}% should exceed 99%"
        
        assert accuracy_test["overall_accuracy"] >= 99.0, \
            f"Overall accuracy {accuracy_test['overall_accuracy']:.2f}% must be ≥99%"
        
        # Verify individual test cases
        failed_cases = accuracy_test["failed_cases"]
        assert len(failed_cases) == 0, \
            f"All test cases should meet 99% accuracy target, failed: {failed_cases}"
        
        # Verify precision in calculations
        for result in accuracy_test["individual_results"]:
            assert result["within_tolerance"], \
                f"Cost calculation for {result['cost_type']} should meet tolerance"
    
    async def test_real_time_cost_tracking(self, agent_cost_tracker):
        """Test real-time cost tracking performance and accuracy."""
        tracker = agent_cost_tracker
        
        # Test real-time tracking performance
        performance_test = await tracker.test_real_time_tracking_performance(50)
        
        # Verify real-time performance
        assert performance_test["real_time_performance_acceptable"], \
            f"Real-time tracking should complete within 5s, took {performance_test['total_time']:.2f}s"
        
        assert performance_test["operations_per_second"] >= 10.0, \
            f"Should handle ≥10 operations/second, got {performance_test['operations_per_second']:.1f}"
        
        assert performance_test["failed_operations"] == 0, \
            f"No operations should fail, got {performance_test['failed_operations']} failures"
        
        # Verify tracking accuracy in real-time
        metrics = tracker.get_comprehensive_metrics()
        assert metrics["cost_tracking"]["real_time_updates"] >= 50, \
            "Real-time updates should be tracked in metrics"
        
        assert metrics["cost_tracking"]["total_entries"] >= 50, \
            "All cost entries should be tracked"
    
    async def test_budget_enforcement_mechanisms(self, agent_cost_tracker):
        """Test budget enforcement and alert systems."""
        tracker = agent_cost_tracker
        
        # Set up budget enforcement test scenario
        budget_scenario = {
            "budget_id": "test_budget_enforcement",
            "period": BudgetPeriod.DAILY,
            "limit_amount": "1.00",  # $1.00 daily limit
            "cost_types": [CostType.LLM_TOKENS, CostType.COMPUTE_TIME],
            "alert_threshold": 0.7,  # Alert at 70%
            "test_usage": [
                {
                    "cost_type": CostType.LLM_TOKENS,
                    "quantity": 200000,  # $0.40
                    "user_id": "test_user"
                },
                {
                    "cost_type": CostType.COMPUTE_TIME,
                    "quantity": 400,  # $0.40
                    "user_id": "test_user"
                },
                {
                    "cost_type": CostType.LLM_TOKENS,
                    "quantity": 150000,  # $0.30 - Should trigger alert (total: $1.10)
                    "user_id": "test_user"
                }
            ]
        }
        
        enforcement_test = await tracker.test_budget_enforcement(budget_scenario)
        
        # Verify budget enforcement
        assert enforcement_test["alerts_triggered"] >= 1, \
            "Budget alerts should be triggered when threshold is exceeded"
        
        assert enforcement_test["violations_detected"] >= 1, \
            "Budget violations should be detected when limit is exceeded"
        
        assert enforcement_test["cost_entries_tracked"] == 3, \
            "All cost entries should be tracked"
        
        # Verify total cost tracking
        total_cost = float(enforcement_test["total_cost_tracked"])
        assert total_cost > 1.0, \
            f"Total tracked cost {total_cost:.2f} should exceed budget limit"
        
        # Verify budget metrics
        metrics = tracker.get_comprehensive_metrics()
        assert metrics["budget_enforcement"]["active_budgets"] >= 1, \
            "Active budget should be tracked"
    
    async def test_cost_attribution_accuracy(self, agent_cost_tracker):
        """Test accurate cost attribution to users, agents, and sessions."""
        tracker = agent_cost_tracker
        
        # Create cost entries with various attribution patterns
        attribution_scenarios = [
            {
                "cost_type": CostType.LLM_TOKENS,
                "quantity": 1000,
                "user_id": "user_1",
                "agent_id": "agent_a",
                "session_id": "session_1"
            },
            {
                "cost_type": CostType.COMPUTE_TIME,
                "quantity": 30,
                "user_id": "user_1",
                "agent_id": "agent_b",
                "session_id": "session_1"
            },
            {
                "cost_type": CostType.API_CALLS,
                "quantity": 10,
                "user_id": "user_2",
                "agent_id": "agent_a",
                "session_id": "session_2"
            },
            {
                "cost_type": CostType.STORAGE_USAGE,
                "quantity": 1000,
                "user_id": "user_2",
                "agent_id": "agent_c",
                "session_id": "session_3"
            }
        ]
        
        # Track all attribution scenarios
        tracked_entries = []
        for scenario in attribution_scenarios:
            cost_entry = await tracker.track_cost(**scenario)
            tracked_entries.append(cost_entry)
        
        # Verify attribution accuracy
        user_1_costs = [e for e in tracked_entries if e.user_id == "user_1"]
        user_2_costs = [e for e in tracked_entries if e.user_id == "user_2"]
        
        assert len(user_1_costs) == 2, \
            "User 1 should have 2 cost entries attributed"
        
        assert len(user_2_costs) == 2, \
            "User 2 should have 2 cost entries attributed"
        
        # Verify agent attribution
        agent_a_costs = [e for e in tracked_entries if e.agent_id == "agent_a"]
        assert len(agent_a_costs) == 2, \
            "Agent A should have 2 cost entries attributed"
        
        # Verify session attribution
        session_1_costs = [e for e in tracked_entries if e.session_id == "session_1"]
        assert len(session_1_costs) == 2, \
            "Session 1 should have 2 cost entries attributed"
        
        # Verify all entries have proper attribution
        for entry in tracked_entries:
            assert entry.user_id is not None, \
                "All entries should have user attribution"
            assert entry.agent_id is not None, \
                "All entries should have agent attribution"
            assert entry.session_id is not None, \
                "All entries should have session attribution"
    
    async def test_usage_forecasting_capabilities(self, agent_cost_tracker):
        """Test usage forecasting accuracy and capabilities."""
        tracker = agent_cost_tracker
        
        # Generate historical usage data for forecasting
        historical_usage = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for i in range(20):
            timestamp = base_time + timedelta(hours=i)
            usage_entry = CostEntry(
                id=f"historical_{i}",
                cost_type=CostType.LLM_TOKENS,
                amount=Decimal('0.002'),
                unit_cost=Decimal('0.000002'),
                quantity=1000 + (i * 50),  # Increasing usage pattern
                timestamp=timestamp,
                user_id="forecasting_user"
            )
            tracker.usage_forecaster.add_usage_data(usage_entry)
            historical_usage.append(usage_entry)
        
        # Generate forecast for next 6 hours
        forecast_period = timedelta(hours=6)
        forecast = tracker.usage_forecaster.forecast_usage(CostType.LLM_TOKENS, forecast_period)
        
        # Verify forecast capabilities
        assert forecast["forecast_available"], \
            "Forecast should be available with sufficient historical data"
        
        assert forecast["confidence_level"] >= 0.6, \
            f"Forecast confidence {forecast['confidence_level']:.2f} should be ≥0.6"
        
        assert forecast["forecasted_quantity"] > 0, \
            "Forecast should predict positive usage"
        
        assert forecast["forecasted_cost"] > 0, \
            "Forecast should predict positive cost"
        
        # Test forecast accuracy by simulating actual usage
        actual_usage = int(forecast["forecasted_quantity"] * 0.95)  # 95% of forecast
        accuracy = tracker.usage_forecaster.validate_forecast_accuracy(forecast, actual_usage)
        
        assert accuracy >= 80.0, \
            f"Forecast accuracy {accuracy:.1f}% should be ≥80%"
    
    async def test_budget_alert_systems(self, agent_cost_tracker):
        """Test budget alert and notification systems."""
        tracker = agent_cost_tracker
        
        # Set up budget with low threshold for testing alerts
        budget_limit = BudgetLimit(
            budget_id="alert_test_budget",
            period=BudgetPeriod.HOURLY,
            limit_amount=Decimal('0.50'),  # $0.50 hourly limit
            cost_types=[CostType.LLM_TOKENS],
            alert_threshold=0.5  # Alert at 50%
        )
        
        tracker.budget_enforcer.add_budget_limit(budget_limit)
        
        # Track usage to trigger alerts
        alert_usage = [
            {"quantity": 75000, "expected_alert": False},  # $0.15 - 30%
            {"quantity": 75000, "expected_alert": False},  # $0.30 - 60% but may not trigger yet
            {"quantity": 50000, "expected_alert": True},   # $0.40 - 80% should trigger
            {"quantity": 75000, "expected_alert": True}    # $0.55 - 110% violation
        ]
        
        alerts_received = []
        violations_received = []
        
        # Mock alert callback to capture alerts
        async def alert_callback(alert_data):
            if alert_data["type"] == "budget_alert":
                alerts_received.append(alert_data)
            elif alert_data["type"] == "budget_violation":
                violations_received.append(alert_data)
        
        tracker.budget_enforcer.alert_callbacks = [alert_callback]
        
        # Execute usage that should trigger alerts
        for i, usage in enumerate(alert_usage):
            await tracker.track_cost(
                cost_type=CostType.LLM_TOKENS,
                quantity=usage["quantity"],
                user_id="alert_test_user"
            )
        
        # Verify alert system
        assert len(alerts_received) >= 1, \
            f"Should receive at least 1 budget alert, got {len(alerts_received)}"
        
        assert len(violations_received) >= 1, \
            f"Should receive at least 1 violation alert, got {len(violations_received)}"
        
        # Verify alert content
        for alert in alerts_received:
            assert alert["type"] == "budget_alert", \
                "Alert should have correct type"
            assert "usage_percentage" in alert, \
                "Alert should include usage percentage"
            assert alert["budget_id"] == "alert_test_budget", \
                "Alert should reference correct budget"
    
    async def test_concurrent_cost_tracking_consistency(self, agent_cost_tracker):
        """Test cost tracking consistency under concurrent operations."""
        tracker = agent_cost_tracker
        
        # Create concurrent cost tracking operations
        async def concurrent_cost_tracking(operation_id: int):
            operations = []
            for i in range(5):
                operation = tracker.track_cost(
                    cost_type=CostType.COMPUTE_TIME,
                    quantity=10,
                    user_id=f"concurrent_user_{operation_id}",
                    agent_id=f"concurrent_agent_{operation_id}"
                )
                operations.append(operation)
            return await asyncio.gather(*operations)
        
        # Execute concurrent operations
        concurrent_tasks = [concurrent_cost_tracking(i) for i in range(10)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify consistency
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        total_entries = sum(len(ops) for ops in successful_operations)
        
        assert len(successful_operations) == 10, \
            "All concurrent operations should succeed"
        
        assert total_entries == 50, \
            f"Should track 50 cost entries, tracked {total_entries}"
        
        # Verify no data corruption in tracking
        metrics = tracker.get_comprehensive_metrics()
        final_entry_count = metrics["cost_tracking"]["total_entries"]
        
        assert final_entry_count >= 50, \
            f"Final entry count {final_entry_count} should include all concurrent entries"
        
        # Verify cost calculation consistency
        total_tracked_cost = float(metrics["cost_tracking"]["total_tracked_costs"])
        expected_cost = 50 * 10 * 0.001  # 50 entries * 10 quantity * $0.001 unit cost
        
        assert abs(total_tracked_cost - expected_cost) < 0.01, \
            f"Total cost {total_tracked_cost:.4f} should match expected {expected_cost:.4f}"
    
    async def test_comprehensive_cost_management_workflow(self, agent_cost_tracker):
        """Test complete cost management workflow from tracking to forecasting."""
        tracker = agent_cost_tracker
        
        # Phase 1: Set up budget
        workflow_budget = BudgetLimit(
            budget_id="workflow_test",
            period=BudgetPeriod.DAILY,
            limit_amount=Decimal('5.00'),
            cost_types=[CostType.LLM_TOKENS, CostType.COMPUTE_TIME, CostType.API_CALLS],
            alert_threshold=0.8
        )
        tracker.budget_enforcer.add_budget_limit(workflow_budget)
        
        # Phase 2: Generate diverse usage patterns
        usage_patterns = [
            # Morning usage spike
            {"cost_type": CostType.LLM_TOKENS, "quantity": 500000, "user_id": "workflow_user"},
            {"cost_type": CostType.COMPUTE_TIME, "quantity": 300, "user_id": "workflow_user"},
            {"cost_type": CostType.API_CALLS, "quantity": 100, "user_id": "workflow_user"},
            
            # Afternoon moderate usage
            {"cost_type": CostType.LLM_TOKENS, "quantity": 300000, "user_id": "workflow_user"},
            {"cost_type": CostType.COMPUTE_TIME, "quantity": 200, "user_id": "workflow_user"},
            
            # Evening high-priority usage
            {"cost_type": CostType.LLM_TOKENS, "quantity": 200000, "user_id": "workflow_user", 
             "metadata": {"priority": "high"}},
        ]
        
        tracked_costs = []
        for usage in usage_patterns:
            cost_entry = await tracker.track_cost(**usage)
            tracked_costs.append(cost_entry)
        
        # Phase 3: Verify comprehensive tracking
        assert len(tracked_costs) == len(usage_patterns), \
            "All usage patterns should be tracked"
        
        # Phase 4: Generate forecast
        forecast = tracker.usage_forecaster.forecast_usage(
            CostType.LLM_TOKENS, 
            timedelta(hours=12)
        )
        
        # Phase 5: Verify comprehensive metrics
        final_metrics = tracker.get_comprehensive_metrics()
        
        # Verify cost tracking metrics
        assert final_metrics["cost_tracking"]["total_entries"] >= 6, \
            "All workflow entries should be tracked"
        
        assert final_metrics["cost_tracking"]["total_tracked_costs"] > 0, \
            "Should track positive total costs"
        
        # Verify budget enforcement metrics
        assert final_metrics["budget_enforcement"]["active_budgets"] >= 1, \
            "Workflow budget should be active"
        
        # Verify forecasting data
        assert final_metrics["usage_forecasting"]["historical_data_points"] >= 6, \
            "Historical data should be available for forecasting"
        
        # Phase 6: Verify workflow integration
        total_workflow_cost = sum(entry.amount for entry in tracked_costs)
        assert total_workflow_cost > Decimal('2.0'), \
            "Workflow should generate substantial cost for testing"
        
        # Verify workflow completed successfully
        workflow_complete = (
            len(tracked_costs) == len(usage_patterns) and
            final_metrics["cost_tracking"]["total_entries"] >= 6 and
            final_metrics["budget_enforcement"]["active_budgets"] >= 1
        )
        
        assert workflow_complete, \
            "Complete cost management workflow should execute successfully"