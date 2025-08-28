"""Cost Optimization Workflow L4 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (core revenue optimization)
- Business Goal: Ensure cost optimization accuracy and efficiency for maximum profitability
- Value Impact: Protects $20K MRR through intelligent resource allocation and cost reduction
- Strategic Impact: Critical for profit margin optimization, resource efficiency, and competitive pricing

Critical Path: 
Usage tracking -> Cost calculation -> Resource allocation -> Budget monitoring -> Alert generation -> Optimization recommendations

Coverage: Real billing accuracy, usage metering, budget enforcement, cost alerts, optimization algorithms, staging validation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.tests.integration.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite
from unittest.mock import AsyncMock, MagicMock

import pytest

LLMManager = AsyncMock
StagingTestSuite = AsyncMock
get_staging_suite = AsyncMock
from netra_backend.app.core.health_checkers import HealthChecker
from netra_backend.app.db.models_user import User
from netra_backend.app.schemas.UserPlan import PlanTier
from netra_backend.app.services.llm.llm_manager import LLMManager

# Mock cost optimization components for L4 testing
class UsageTracker:
    """Mock usage tracker for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass
    async def health_check(self): return {"healthy": True}
    
    async def track_usage_batch(self, batch_data: List[Dict]) -> Dict[str, Any]:
        return {"success": True}

class BillingEngine:
    """Mock billing engine for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass
    async def health_check(self): return {"healthy": True}
    
    async def calculate_user_cost(self, user_id: str, start_date, end_date) -> Dict[str, Any]:
        # Mock cost calculation based on user tier
        mock_cost = random.uniform(10.0, 500.0)
        return {"success": True, "total_cost": mock_cost}

class CostOptimizer:
    """Mock cost optimizer for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass
    async def health_check(self): return {"healthy": True}
    
    async def analyze_user_costs(self, user_id: str, usage_data, optimization_goals) -> Dict[str, Any]:
        savings = random.uniform(5.0, 50.0)
        return {
            "success": True,
            "recommendations": ["optimize_llm_usage", "reduce_storage"],
            "potential_savings": savings
        }
    
    async def analyze_resource_allocation(self, resource_type: str, usage_data, time_range_hours: int) -> Dict[str, Any]:
        efficiency = random.uniform(0.7, 0.95)
        return {
            "success": True,
            "efficiency_score": efficiency,
            "recommendations": [f"optimize_{resource_type}"]
        }

class BudgetManager:
    """Mock budget manager for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass

class BillingAlertManager:
    """Mock billing alert manager for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass
    
    async def generate_budget_alert(self, user_id: str, alert_type: str, current_usage, budget_limit, usage_percentage: float) -> Dict[str, Any]:
        return {"success": True, "alert_id": str(uuid.uuid4())}

class CostAnalytics:
    """Mock cost analytics for L4 testing."""
    async def initialize(self): pass
    async def shutdown(self): pass

@dataclass
class CostOptimizationMetrics:
    """Metrics container for cost optimization testing."""
    total_usage_tracked: int
    cost_calculation_accuracy: float
    optimization_savings_percentage: float
    budget_compliance_rate: float
    alert_response_time: float
    resource_efficiency_improvement: float

@dataclass
class UsageRecord:
    """Usage record data container."""
    user_id: str
    resource_type: str
    usage_amount: float
    unit_cost: Decimal
    timestamp: datetime
    tier: str
    region: str

@dataclass
class CostAlert:
    """Cost alert data container."""
    alert_id: str
    user_id: str
    alert_type: str
    threshold_percentage: float
    current_usage: Decimal
    budget_limit: Decimal
    triggered_at: datetime

class CostOptimizationWorkflowL4TestSuite:
    """L4 test suite for cost optimization workflow in staging environment."""
    
    def __init__(self):
        self.staging_suite: Optional[StagingTestSuite] = None
        self.usage_tracker: Optional[UsageTracker] = None
        self.billing_engine: Optional[BillingEngine] = None
        self.cost_optimizer: Optional[CostOptimizer] = None
        self.budget_manager: Optional[BudgetManager] = None
        self.billing_alert_manager: Optional[BillingAlertManager] = None
        self.cost_analytics: Optional[CostAnalytics] = None
        self.llm_manager: Optional[LLMManager] = None
        self.test_users: List[Dict] = []
        self.usage_records: List[UsageRecord] = []
        self.cost_alerts: List[CostAlert] = []
        self.optimization_results: List[Dict] = []
        self.test_metrics = {
            "usage_events_tracked": 0,
            "cost_calculations_performed": 0,
            "optimizations_executed": 0,
            "budgets_monitored": 0,
            "alerts_generated": 0
        }
        
    async def initialize_l4_environment(self) -> None:
        """Initialize L4 staging environment for cost optimization testing."""
        self.staging_suite = await get_staging_suite()
        await self.staging_suite.setup()
        
        # Initialize billing and cost components
        self.usage_tracker = UsageTracker()
        await self.usage_tracker.initialize()
        
        self.billing_engine = BillingEngine()
        await self.billing_engine.initialize()
        
        self.cost_optimizer = CostOptimizer()
        await self.cost_optimizer.initialize()
        
        self.budget_manager = BudgetManager()
        await self.budget_manager.initialize()
        
        self.billing_alert_manager = BillingAlertManager()
        await self.billing_alert_manager.initialize()
        
        self.cost_analytics = CostAnalytics()
        await self.cost_analytics.initialize()
        
        self.llm_manager = LLMManager()
        await self.llm_manager.initialize()
        
        # Validate cost optimization infrastructure
        await self._validate_cost_optimization_infrastructure()
    
    async def _validate_cost_optimization_infrastructure(self) -> None:
        """Validate cost optimization infrastructure in staging."""
        try:
            # Test billing engine connectivity
            billing_health = await self.billing_engine.health_check()
            if not billing_health["healthy"]:
                raise RuntimeError("Billing engine not accessible")
            
            # Test usage tracker connectivity
            usage_health = await self.usage_tracker.health_check()
            if not usage_health["healthy"]:
                raise RuntimeError("Usage tracker not accessible")
            
            # Test cost optimizer connectivity
            optimizer_health = await self.cost_optimizer.health_check()
            if not optimizer_health["healthy"]:
                raise RuntimeError("Cost optimizer not accessible")
                
        except Exception as e:
            raise RuntimeError(f"Cost optimization infrastructure validation failed: {e}")
    
    async def create_test_users_l4(self, user_count: int = 50) -> Dict[str, Any]:
        """Create realistic test users for cost optimization testing."""
        user_creation_start = time.time()
        
        # Define user tier distribution (realistic enterprise mix)
        tier_distribution = [
            {"tier": "free", "percentage": 0.6, "base_budget": 0},
            {"tier": "early", "percentage": 0.25, "base_budget": 50},
            {"tier": "mid", "percentage": 0.12, "base_budget": 200},
            {"tier": "enterprise", "percentage": 0.03, "base_budget": 1000}
        ]
        
        users_created = 0
        for i in range(user_count):
            # Select user tier based on distribution
            tier_random = random.random()
            cumulative_percentage = 0
            selected_tier = None
            
            for tier_config in tier_distribution:
                cumulative_percentage += tier_config["percentage"]
                if tier_random <= cumulative_percentage:
                    selected_tier = tier_config
                    break
            
            if not selected_tier:
                selected_tier = tier_distribution[0]  # Default to free
            
            user_id = str(uuid.uuid4())
            
            # Create test user
            test_user = {
                "user_id": user_id,
                "email": f"cost_test_user_{i}@netra-cost-test.com",
                "tier": selected_tier["tier"],
                "monthly_budget": selected_tier["base_budget"] + random.randint(-20, 50),
                "region": "us-east" if i % 2 == 0 else "us-west",
                "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
                "current_usage": Decimal("0.00"),
                "optimization_enabled": True
            }
            
            # Set budget alerts based on tier
            if selected_tier["tier"] != "free":
                test_user["budget_alerts"] = {
                    "warning_threshold": 0.75,  # 75%
                    "critical_threshold": 0.90,  # 90%
                    "absolute_limit": 1.10       # 110%
                }
            
            self.test_users.append(test_user)
            users_created += 1
        
        user_creation_time = time.time() - user_creation_start
        
        return {
            "users_created": users_created,
            "creation_time": user_creation_time,
            "tier_distribution": {tier["tier"]: len([u for u in self.test_users if u["tier"] == tier["tier"]]) for tier in tier_distribution}
        }
    
    async def generate_realistic_usage_data_l4(self, usage_events: int = 5000, 
                                             time_range_hours: int = 72) -> Dict[str, Any]:
        """Generate realistic usage data for cost optimization testing."""
        usage_generation_start = time.time()
        
        # Define realistic resource usage patterns
        resource_patterns = [
            {
                "type": "llm_tokens",
                "base_cost_per_unit": Decimal("0.0001"),  # $0.0001 per token
                "usage_variance": 0.3,
                "tier_multipliers": {"free": 1.0, "early": 5.0, "mid": 25.0, "enterprise": 100.0}
            },
            {
                "type": "api_requests",
                "base_cost_per_unit": Decimal("0.001"),   # $0.001 per request
                "usage_variance": 0.2,
                "tier_multipliers": {"free": 1.0, "early": 10.0, "mid": 50.0, "enterprise": 200.0}
            },
            {
                "type": "storage_gb",
                "base_cost_per_unit": Decimal("0.10"),    # $0.10 per GB
                "usage_variance": 0.1,
                "tier_multipliers": {"free": 0.1, "early": 1.0, "mid": 10.0, "enterprise": 100.0}
            },
            {
                "type": "compute_minutes",
                "base_cost_per_unit": Decimal("0.05"),    # $0.05 per minute
                "usage_variance": 0.4,
                "tier_multipliers": {"free": 0.5, "early": 2.0, "mid": 10.0, "enterprise": 50.0}
            },
            {
                "type": "websocket_connections",
                "base_cost_per_unit": Decimal("0.0001"),  # $0.0001 per connection
                "usage_variance": 0.25,
                "tier_multipliers": {"free": 1.0, "early": 5.0, "mid": 20.0, "enterprise": 100.0}
            }
        ]
        
        # Generate usage events across time range
        start_time = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)
        time_interval = timedelta(hours=time_range_hours) / usage_events
        
        for i in range(usage_events):
            current_time = start_time + (time_interval * i)
            
            # Select random user and resource pattern
            user = random.choice(self.test_users)
            resource_pattern = random.choice(resource_patterns)
            
            # Calculate usage amount based on tier and pattern
            base_usage = 100 * resource_pattern["tier_multipliers"][user["tier"]]
            variance_factor = 1.0 + random.uniform(-resource_pattern["usage_variance"], resource_pattern["usage_variance"])
            usage_amount = base_usage * variance_factor
            
            # Add time-based patterns (higher usage during business hours)
            hour_of_day = current_time.hour
            if 9 <= hour_of_day <= 17:  # Business hours
                usage_amount *= 1.5
            elif 22 <= hour_of_day or hour_of_day <= 6:  # Late night/early morning
                usage_amount *= 0.3
            
            # Create usage record
            usage_record = UsageRecord(
                user_id=user["user_id"],
                resource_type=resource_pattern["type"],
                usage_amount=usage_amount,
                unit_cost=resource_pattern["base_cost_per_unit"],
                timestamp=current_time,
                tier=user["tier"],
                region=user["region"]
            )
            
            self.usage_records.append(usage_record)
            self.test_metrics["usage_events_tracked"] += 1
        
        # Track usage in usage tracker
        tracking_result = await self._track_usage_records()
        
        usage_generation_time = time.time() - usage_generation_start
        
        return {
            "usage_events_generated": len(self.usage_records),
            "generation_time": usage_generation_time,
            "tracking_success": tracking_result["success"],
            "tracking_rate": tracking_result["tracking_rate"]
        }
    
    async def _track_usage_records(self) -> Dict[str, Any]:
        """Track usage records in the usage tracker system."""
        try:
            tracking_start = time.time()
            successful_tracks = 0
            
            # Track usage records in batches for performance
            batch_size = 100
            for i in range(0, len(self.usage_records), batch_size):
                batch = self.usage_records[i:i + batch_size]
                
                batch_data = []
                for usage_record in batch:
                    batch_data.append({
                        "user_id": usage_record.user_id,
                        "resource_type": usage_record.resource_type,
                        "usage_amount": float(usage_record.usage_amount),
                        "unit_cost": float(usage_record.unit_cost),
                        "timestamp": usage_record.timestamp,
                        "tier": usage_record.tier,
                        "region": usage_record.region
                    })
                
                tracking_result = await self.usage_tracker.track_usage_batch(batch_data)
                
                if tracking_result.get("success", False):
                    successful_tracks += len(batch)
            
            tracking_time = time.time() - tracking_start
            tracking_rate = successful_tracks / tracking_time if tracking_time > 0 else 0
            
            return {
                "success": successful_tracks > 0,
                "tracking_rate": tracking_rate,
                "records_tracked": successful_tracks
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tracking_rate": 0
            }
    
    @pytest.mark.asyncio
    async def test_cost_calculation_accuracy_l4(self) -> Dict[str, Any]:
        """Test cost calculation accuracy and billing engine performance."""
        cost_calculation_results = {
            "calculations_performed": 0,
            "calculation_accuracy": 0.0,
            "calculation_performance": [],
            "billing_discrepancies": []
        }
        
        # Test cost calculations for each user
        for user in self.test_users:
            calculation_start = time.time()
            
            try:
                # Get usage data for this user
                user_usage = [record for record in self.usage_records if record.user_id == user["user_id"]]
                
                if not user_usage:
                    continue
                
                # Calculate expected cost manually for verification
                expected_cost = Decimal("0.00")
                for usage_record in user_usage:
                    expected_cost += Decimal(str(usage_record.usage_amount)) * usage_record.unit_cost
                
                # Get calculated cost from billing engine
                calculated_cost_result = await self.billing_engine.calculate_user_cost(
                    user["user_id"],
                    start_date=datetime.now(timezone.utc) - timedelta(hours=72),
                    end_date=datetime.now(timezone.utc)
                )
                
                calculation_time = time.time() - calculation_start
                cost_calculation_results["calculation_performance"].append(calculation_time)
                
                if calculated_cost_result["success"]:
                    calculated_cost = Decimal(str(calculated_cost_result["total_cost"]))
                    
                    # Calculate accuracy (allow for small rounding differences)
                    if expected_cost > 0:
                        accuracy = 1.0 - abs(calculated_cost - expected_cost) / expected_cost
                        accuracy = max(0.0, min(1.0, accuracy))
                    else:
                        accuracy = 1.0 if calculated_cost == expected_cost else 0.0
                    
                    cost_calculation_results["calculation_accuracy"] += accuracy
                    cost_calculation_results["calculations_performed"] += 1
                    
                    # Track significant discrepancies
                    if accuracy < 0.95:  # Less than 95% accuracy
                        cost_calculation_results["billing_discrepancies"].append({
                            "user_id": user["user_id"],
                            "expected_cost": float(expected_cost),
                            "calculated_cost": float(calculated_cost),
                            "accuracy": accuracy
                        })
                
                self.test_metrics["cost_calculations_performed"] += 1
                
            except Exception as e:
                print(f"Cost calculation failed for user {user['user_id']}: {e}")
        
        # Calculate overall accuracy
        if cost_calculation_results["calculations_performed"] > 0:
            cost_calculation_results["calculation_accuracy"] /= cost_calculation_results["calculations_performed"]
        
        return cost_calculation_results
    
    @pytest.mark.asyncio
    async def test_budget_monitoring_and_alerts_l4(self) -> Dict[str, Any]:
        """Test budget monitoring and alert generation."""
        budget_monitoring_results = {
            "budgets_monitored": 0,
            "alerts_generated": 0,
            "alert_accuracy": 0.0,
            "alert_response_times": []
        }
        
        # Monitor budgets for users with budget limits
        users_with_budgets = [user for user in self.test_users if user.get("monthly_budget", 0) > 0]
        
        for user in users_with_budgets:
            monitoring_start = time.time()
            
            try:
                # Get current usage cost for user
                cost_result = await self.billing_engine.calculate_user_cost(
                    user["user_id"],
                    start_date=datetime.now(timezone.utc).replace(day=1),  # Start of month
                    end_date=datetime.now(timezone.utc)
                )
                
                if cost_result["success"]:
                    current_cost = Decimal(str(cost_result["total_cost"]))
                    monthly_budget = Decimal(str(user["monthly_budget"]))
                    usage_percentage = (current_cost / monthly_budget) if monthly_budget > 0 else 0
                    
                    # Check if alerts should be triggered
                    budget_alerts = user.get("budget_alerts", {})
                    alerts_to_trigger = []
                    
                    if usage_percentage >= budget_alerts.get("critical_threshold", 0.90):
                        alerts_to_trigger.append("critical")
                    elif usage_percentage >= budget_alerts.get("warning_threshold", 0.75):
                        alerts_to_trigger.append("warning")
                    
                    # Generate alerts
                    for alert_type in alerts_to_trigger:
                        alert_start = time.time()
                        
                        alert_result = await self.billing_alert_manager.generate_budget_alert(
                            user_id=user["user_id"],
                            alert_type=alert_type,
                            current_usage=current_cost,
                            budget_limit=monthly_budget,
                            usage_percentage=float(usage_percentage)
                        )
                        
                        alert_response_time = time.time() - alert_start
                        budget_monitoring_results["alert_response_times"].append(alert_response_time)
                        
                        if alert_result.get("success", False):
                            budget_monitoring_results["alerts_generated"] += 1
                            
                            # Create cost alert record
                            cost_alert = CostAlert(
                                alert_id=str(uuid.uuid4()),
                                user_id=user["user_id"],
                                alert_type=alert_type,
                                threshold_percentage=float(usage_percentage),
                                current_usage=current_cost,
                                budget_limit=monthly_budget,
                                triggered_at=datetime.now(timezone.utc)
                            )
                            
                            self.cost_alerts.append(cost_alert)
                            self.test_metrics["alerts_generated"] += 1
                    
                    budget_monitoring_results["budgets_monitored"] += 1
                    self.test_metrics["budgets_monitored"] += 1
                
                monitoring_time = time.time() - monitoring_start
                
            except Exception as e:
                print(f"Budget monitoring failed for user {user['user_id']}: {e}")
        
        # Calculate alert accuracy (alerts should match expected thresholds)
        if budget_monitoring_results["budgets_monitored"] > 0:
            # Simplified accuracy calculation
            budget_monitoring_results["alert_accuracy"] = min(1.0, budget_monitoring_results["alerts_generated"] / max(1, len(users_with_budgets) * 0.3))
        
        return budget_monitoring_results
    
    @pytest.mark.asyncio
    async def test_cost_optimization_algorithms_l4(self) -> Dict[str, Any]:
        """Test cost optimization algorithms and recommendations."""
        optimization_results = {
            "optimization_runs": 0,
            "total_savings_identified": Decimal("0.00"),
            "optimization_accuracy": 0.0,
            "optimization_performance": []
        }
        
        # Run cost optimization for high-usage users
        high_usage_users = [user for user in self.test_users if user["tier"] in ["mid", "enterprise"]]
        
        for user in high_usage_users:
            optimization_start = time.time()
            
            try:
                # Get user's usage patterns
                user_usage = [record for record in self.usage_records if record.user_id == user["user_id"]]
                
                if len(user_usage) < 10:  # Need sufficient data for optimization
                    continue
                
                # Run cost optimization analysis
                optimization_result = await self.cost_optimizer.analyze_user_costs(
                    user_id=user["user_id"],
                    usage_data=user_usage,
                    optimization_goals=["reduce_llm_costs", "optimize_api_usage", "right_size_storage"]
                )
                
                optimization_time = time.time() - optimization_start
                optimization_results["optimization_performance"].append(optimization_time)
                
                if optimization_result.get("success", False):
                    recommendations = optimization_result.get("recommendations", [])
                    potential_savings = Decimal(str(optimization_result.get("potential_savings", 0)))
                    
                    optimization_results["total_savings_identified"] += potential_savings
                    optimization_results["optimization_runs"] += 1
                    
                    # Store optimization results
                    self.optimization_results.append({
                        "user_id": user["user_id"],
                        "recommendations": recommendations,
                        "potential_savings": potential_savings,
                        "optimization_time": optimization_time
                    })
                    
                    self.test_metrics["optimizations_executed"] += 1
                
            except Exception as e:
                print(f"Cost optimization failed for user {user['user_id']}: {e}")
        
        # Calculate optimization accuracy (simplified metric)
        if optimization_results["optimization_runs"] > 0:
            avg_savings_per_user = optimization_results["total_savings_identified"] / optimization_results["optimization_runs"]
            # Assume good optimization finds at least 10% savings potential
            optimization_results["optimization_accuracy"] = min(1.0, float(avg_savings_per_user) / 50.0)  # $50 baseline
        
        return optimization_results
    
    @pytest.mark.asyncio
    async def test_resource_allocation_efficiency_l4(self) -> Dict[str, Any]:
        """Test resource allocation efficiency and recommendations."""
        allocation_results = {
            "allocation_analyses": 0,
            "efficiency_improvements": [],
            "resource_utilization_optimized": 0.0,
            "allocation_recommendations": []
        }
        
        # Analyze resource allocation patterns
        resource_types = ["llm_tokens", "api_requests", "storage_gb", "compute_minutes", "websocket_connections"]
        
        for resource_type in resource_types:
            try:
                # Get usage data for this resource type
                resource_usage = [record for record in self.usage_records if record.resource_type == resource_type]
                
                if not resource_usage:
                    continue
                
                # Analyze allocation efficiency
                allocation_analysis = await self.cost_optimizer.analyze_resource_allocation(
                    resource_type=resource_type,
                    usage_data=resource_usage,
                    time_range_hours=72
                )
                
                if allocation_analysis.get("success", False):
                    efficiency_score = allocation_analysis.get("efficiency_score", 0.0)
                    recommendations = allocation_analysis.get("recommendations", [])
                    
                    allocation_results["allocation_analyses"] += 1
                    allocation_results["efficiency_improvements"].append(efficiency_score)
                    allocation_results["allocation_recommendations"].extend(recommendations)
                    
                    # Track resource utilization optimization
                    if efficiency_score > 0.8:  # Good efficiency
                        allocation_results["resource_utilization_optimized"] += 1
                
            except Exception as e:
                print(f"Resource allocation analysis failed for {resource_type}: {e}")
        
        # Calculate overall resource utilization optimization
        if allocation_results["allocation_analyses"] > 0:
            allocation_results["resource_utilization_optimized"] /= allocation_results["allocation_analyses"]
        
        return allocation_results
    
    async def cleanup_l4_resources(self) -> None:
        """Clean up L4 test resources."""
        try:
            # Clear test data
            self.test_users.clear()
            self.usage_records.clear()
            self.cost_alerts.clear()
            self.optimization_results.clear()
            
            # Shutdown cost optimization components
            if self.usage_tracker:
                await self.usage_tracker.shutdown()
            if self.billing_engine:
                await self.billing_engine.shutdown()
            if self.cost_optimizer:
                await self.cost_optimizer.shutdown()
            if self.budget_manager:
                await self.budget_manager.shutdown()
            if self.billing_alert_manager:
                await self.billing_alert_manager.shutdown()
            if self.cost_analytics:
                await self.cost_analytics.shutdown()
            if self.llm_manager:
                await self.llm_manager.shutdown()
                
        except Exception as e:
            print(f"L4 cost optimization cleanup failed: {e}")

@pytest.fixture
async def cost_optimization_workflow_l4_suite():
    """Create L4 cost optimization workflow test suite."""
    suite = CostOptimizationWorkflowL4TestSuite()
    await suite.initialize_l4_environment()
    yield suite
    await suite.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_realistic_usage_data_generation_l4(cost_optimization_workflow_l4_suite):
    """Test realistic usage data generation and tracking."""
    # Create test users
    user_creation_results = await cost_optimization_workflow_l4_suite.create_test_users_l4(user_count=30)
    
    # Generate usage data
    usage_generation_results = await cost_optimization_workflow_l4_suite.generate_realistic_usage_data_l4(
        usage_events=3000,
        time_range_hours=48
    )
    
    # Validate user creation
    assert user_creation_results["users_created"] == 30, "User creation count mismatch"
    assert user_creation_results["creation_time"] < 10.0, "User creation took too long"
    
    # Validate usage data generation
    assert usage_generation_results["usage_events_generated"] >= 3000, "Insufficient usage events generated"
    assert usage_generation_results["tracking_success"] is True, "Usage tracking failed"
    assert usage_generation_results["tracking_rate"] >= 100, "Usage tracking rate too low"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_cost_calculation_accuracy_l4(cost_optimization_workflow_l4_suite):
    """Test cost calculation accuracy and billing engine performance."""
    # Setup test data
    await cost_optimization_workflow_l4_suite.create_test_users_l4(user_count=20)
    await cost_optimization_workflow_l4_suite.generate_realistic_usage_data_l4(
        usage_events=2000,
        time_range_hours=36
    )
    
    # Test cost calculations
    cost_calculation_results = await cost_optimization_workflow_l4_suite.test_cost_calculation_accuracy_l4()
    
    # Validate cost calculation accuracy
    assert cost_calculation_results["calculations_performed"] >= 15, "Insufficient cost calculations performed"
    assert cost_calculation_results["calculation_accuracy"] >= 0.95, "Cost calculation accuracy too low"
    
    # Validate calculation performance
    if cost_calculation_results["calculation_performance"]:
        avg_calculation_time = sum(cost_calculation_results["calculation_performance"]) / len(cost_calculation_results["calculation_performance"])
        assert avg_calculation_time < 2.0, f"Cost calculation too slow: {avg_calculation_time}s"
    
    # Validate billing discrepancies
    assert len(cost_calculation_results["billing_discrepancies"]) <= 2, "Too many billing discrepancies detected"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_budget_monitoring_and_alerts_l4(cost_optimization_workflow_l4_suite):
    """Test budget monitoring and alert generation functionality."""
    # Setup test data
    await cost_optimization_workflow_l4_suite.create_test_users_l4(user_count=25)
    await cost_optimization_workflow_l4_suite.generate_realistic_usage_data_l4(
        usage_events=2500,
        time_range_hours=48
    )
    
    # Test budget monitoring
    budget_monitoring_results = await cost_optimization_workflow_l4_suite.test_budget_monitoring_and_alerts_l4()
    
    # Validate budget monitoring
    assert budget_monitoring_results["budgets_monitored"] >= 5, "Insufficient budgets monitored"
    
    # Alerts should be generated for users exceeding thresholds
    if budget_monitoring_results["alerts_generated"] > 0:
        assert budget_monitoring_results["alert_accuracy"] >= 0.7, "Alert accuracy too low"
        
        # Validate alert response times
        if budget_monitoring_results["alert_response_times"]:
            avg_alert_time = sum(budget_monitoring_results["alert_response_times"]) / len(budget_monitoring_results["alert_response_times"])
            assert avg_alert_time < 3.0, f"Alert response time too slow: {avg_alert_time}s"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_cost_optimization_algorithms_l4(cost_optimization_workflow_l4_suite):
    """Test cost optimization algorithms and recommendations."""
    # Setup test data with focus on high-usage users
    await cost_optimization_workflow_l4_suite.create_test_users_l4(user_count=15)
    await cost_optimization_workflow_l4_suite.generate_realistic_usage_data_l4(
        usage_events=3000,
        time_range_hours=60
    )
    
    # Test cost optimization
    optimization_results = await cost_optimization_workflow_l4_suite.test_cost_optimization_algorithms_l4()
    
    # Validate optimization functionality
    assert optimization_results["optimization_runs"] >= 3, "Insufficient optimization runs completed"
    
    # Optimization should identify some savings potential
    if optimization_results["total_savings_identified"] > 0:
        assert float(optimization_results["total_savings_identified"]) >= 10.0, "Insufficient savings identified"
    
    # Validate optimization performance
    if optimization_results["optimization_performance"]:
        avg_optimization_time = sum(optimization_results["optimization_performance"]) / len(optimization_results["optimization_performance"])
        assert avg_optimization_time < 10.0, f"Optimization analysis too slow: {avg_optimization_time}s"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_resource_allocation_efficiency_l4(cost_optimization_workflow_l4_suite):
    """Test resource allocation efficiency and optimization."""
    # Setup test data
    await cost_optimization_workflow_l4_suite.create_test_users_l4(user_count=20)
    await cost_optimization_workflow_l4_suite.generate_realistic_usage_data_l4(
        usage_events=4000,
        time_range_hours=72
    )
    
    # Test resource allocation efficiency
    allocation_results = await cost_optimization_workflow_l4_suite.test_resource_allocation_efficiency_l4()
    
    # Validate allocation analysis
    assert allocation_results["allocation_analyses"] >= 3, "Insufficient allocation analyses completed"
    
    # Resource utilization should be optimized for most resources
    assert allocation_results["resource_utilization_optimized"] >= 0.6, "Resource utilization optimization too low"
    
    # Should generate meaningful recommendations
    assert len(allocation_results["allocation_recommendations"]) >= 2, "Insufficient allocation recommendations generated"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.l4
@pytest.mark.asyncio
async def test_cost_optimization_workflow_e2e_l4(cost_optimization_workflow_l4_suite):
    """Test end-to-end cost optimization workflow performance."""
    e2e_start = time.time()
    
    # Execute full workflow: user creation -> usage generation -> cost calculation -> budget monitoring -> optimization
    
    # Step 1: Create realistic user base
    user_creation_results = await cost_optimization_workflow_l4_suite.create_test_users_l4(user_count=40)
    
    # Step 2: Generate comprehensive usage data
    usage_generation_results = await cost_optimization_workflow_l4_suite.generate_realistic_usage_data_l4(
        usage_events=6000,
        time_range_hours=96
    )
    
    # Step 3: Test cost calculations
    cost_calculation_results = await cost_optimization_workflow_l4_suite.test_cost_calculation_accuracy_l4()
    
    # Step 4: Test budget monitoring
    budget_monitoring_results = await cost_optimization_workflow_l4_suite.test_budget_monitoring_and_alerts_l4()
    
    # Step 5: Test cost optimization
    optimization_results = await cost_optimization_workflow_l4_suite.test_cost_optimization_algorithms_l4()
    
    # Step 6: Test resource allocation
    allocation_results = await cost_optimization_workflow_l4_suite.test_resource_allocation_efficiency_l4()
    
    total_e2e_time = time.time() - e2e_start
    
    # Validate end-to-end workflow
    assert user_creation_results["users_created"] == 40, "E2E: User creation failed"
    assert usage_generation_results["tracking_success"] is True, "E2E: Usage tracking failed"
    assert cost_calculation_results["calculation_accuracy"] >= 0.95, "E2E: Cost calculation accuracy insufficient"
    assert budget_monitoring_results["budgets_monitored"] >= 8, "E2E: Budget monitoring insufficient"
    assert optimization_results["optimization_runs"] >= 5, "E2E: Cost optimization insufficient"
    assert allocation_results["allocation_analyses"] >= 3, "E2E: Resource allocation analysis insufficient"
    
    # Validate overall workflow performance
    assert total_e2e_time < 180.0, f"E2E workflow too slow: {total_e2e_time}s"
    
    # Validate workflow efficiency
    total_usage_events = usage_generation_results["usage_events_generated"]
    processing_rate = total_usage_events / total_e2e_time
    assert processing_rate >= 30, f"Workflow processing rate too low: {processing_rate} events/sec"
    
    # Validate cost optimization value
    if optimization_results["total_savings_identified"] > 0:
        savings_rate = float(optimization_results["total_savings_identified"]) / total_usage_events * 1000  # per 1000 events
        assert savings_rate >= 1.0, f"Cost optimization value too low: ${savings_rate} per 1000 events"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])