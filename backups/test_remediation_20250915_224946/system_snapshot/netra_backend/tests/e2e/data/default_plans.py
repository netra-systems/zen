"""
E2E Test Default Plans: Cost Optimization, Performance Tuning, and Capacity Planning

This module provides comprehensive default plans for E2E testing with:
- Cost optimization plan (20 detailed steps)
- Performance tuning plan (15 steps) 
- Capacity planning plan (25 steps)
- Each step with validation criteria and success metrics

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines
- Maximum function size: 8 lines
- Single responsibility: Default plan definitions
- Strong typing: All functions and data structures typed
- Modular design: Composable plan components

Usage:
    from netra_backend.tests.e2e.data.default_plans import (
        get_cost_optimization_plan,
        get_performance_tuning_plan,
        get_capacity_planning_plan
    )
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

class PlanStepType(Enum):
    """Types of plan steps."""
    ANALYSIS = "analysis"
    OPTIMIZATION = "optimization"
    VALIDATION = "validation"
    IMPLEMENTATION = "implementation"
    MONITORING = "monitoring"

class PlanPriority(Enum):
    """Plan step priorities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ValidationCriteria:
    """Validation criteria for plan steps."""
    success_threshold: float
    measurement_unit: str
    measurement_method: str
    validation_timeout_hours: int = 24

@dataclass
class PlanStep:
    """Individual plan step definition."""
    id: str
    title: str
    description: str
    step_type: PlanStepType
    priority: PlanPriority
    estimated_hours: int
    validation_criteria: ValidationCriteria
    dependencies: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    expected_outcome: str = ""

@dataclass 
class OptimizationPlan:
    """Complete optimization plan."""
    name: str
    description: str
    total_steps: int
    estimated_duration_hours: int
    steps: List[PlanStep]
    success_metrics: Dict[str, Any]
    risk_factors: List[str] = field(default_factory=list)

def get_cost_optimization_plan() -> OptimizationPlan:
    """Get comprehensive cost optimization plan (20 steps)."""
    steps = _create_cost_optimization_steps()
    metrics = _create_cost_optimization_metrics()
    risks = _create_cost_optimization_risks()
    return OptimizationPlan(
        name="Cost Optimization Plan",
        description="Comprehensive 20-step cost reduction strategy",
        total_steps=20,
        estimated_duration_hours=160,
        steps=steps,
        success_metrics=metrics,
        risk_factors=risks
    )

def get_performance_tuning_plan() -> OptimizationPlan:
    """Get comprehensive performance tuning plan (15 steps)."""
    steps = _create_performance_tuning_steps()
    metrics = _create_performance_tuning_metrics()
    risks = _create_performance_tuning_risks()
    return OptimizationPlan(
        name="Performance Tuning Plan",
        description="Comprehensive 15-step performance optimization",
        total_steps=15,
        estimated_duration_hours=120,
        steps=steps,
        success_metrics=metrics,
        risk_factors=risks
    )

def get_capacity_planning_plan() -> OptimizationPlan:
    """Get comprehensive capacity planning plan (25 steps)."""
    steps = _create_capacity_planning_steps()
    metrics = _create_capacity_planning_metrics()
    risks = _create_capacity_planning_risks()
    return OptimizationPlan(
        name="Capacity Planning Plan",
        description="Comprehensive 25-step capacity planning strategy",
        total_steps=25,
        estimated_duration_hours=200,
        steps=steps,
        success_metrics=metrics,
        risk_factors=risks
    )

def _create_cost_optimization_steps() -> List[PlanStep]:
    """Create cost optimization plan steps."""
    from netra_backend.tests.e2e.data.plan_step_definitions import (
        create_remaining_cost_steps,
    )
    base_steps = [
        _create_cost_step_1(), _create_cost_step_2(), _create_cost_step_3(),
        _create_cost_step_4(), _create_cost_step_5()
    ]
    return base_steps + create_remaining_cost_steps()

def _create_performance_tuning_steps() -> List[PlanStep]:
    """Create performance tuning plan steps.""" 
    from netra_backend.tests.e2e.data.plan_step_definitions import (
        create_all_performance_steps,
    )
    return create_all_performance_steps()

def _create_capacity_planning_steps() -> List[PlanStep]:
    """Create capacity planning plan steps."""
    from netra_backend.tests.e2e.data.plan_step_definitions import (
        create_all_capacity_steps,
    )
    return create_all_capacity_steps()

# Cost Optimization Step Creators (1-10)
def _create_cost_step_1() -> PlanStep:
    """Create cost optimization step 1."""
    return PlanStep(
        id="cost_001", title="Baseline Cost Analysis",
        description="Analyze current cost structure across all services",
        step_type=PlanStepType.ANALYSIS, priority=PlanPriority.CRITICAL,
        estimated_hours=8, validation_criteria=ValidationCriteria(
            success_threshold=0.95, measurement_unit="completeness",
            measurement_method="automated_scan", validation_timeout_hours=24
        ),
        tools_required=["cost_analyzer", "billing_api"],
        expected_outcome="Complete cost breakdown by service and region"
    )

def _create_cost_step_2() -> PlanStep:
    """Create cost optimization step 2."""
    return PlanStep(
        id="cost_002", title="Usage Pattern Analysis",
        description="Identify usage patterns and peak/off-peak periods",
        step_type=PlanStepType.ANALYSIS, priority=PlanPriority.HIGH,
        estimated_hours=6, validation_criteria=ValidationCriteria(
            success_threshold=0.90, measurement_unit="pattern_accuracy",
            measurement_method="statistical_analysis", validation_timeout_hours=12
        ),
        dependencies=["cost_001"], tools_required=["usage_analyzer"],
        expected_outcome="Usage pattern classification and recommendations"
    )

def _create_cost_step_3() -> PlanStep:
    """Create cost optimization step 3."""
    return PlanStep(
        id="cost_003", title="Resource Utilization Assessment",
        description="Assess current resource utilization efficiency",
        step_type=PlanStepType.ANALYSIS, priority=PlanPriority.HIGH,
        estimated_hours=8, validation_criteria=ValidationCriteria(
            success_threshold=0.85, measurement_unit="utilization_rate",
            measurement_method="resource_monitoring", validation_timeout_hours=24
        ),
        dependencies=["cost_001"], tools_required=["resource_monitor"],
        expected_outcome="Resource utilization efficiency report"
    )

def _create_cost_step_4() -> PlanStep:
    """Create cost optimization step 4.""" 
    return PlanStep(
        id="cost_004", title="Identify Optimization Opportunities",
        description="Identify specific optimization opportunities",
        step_type=PlanStepType.ANALYSIS, priority=PlanPriority.CRITICAL,
        estimated_hours=12, validation_criteria=ValidationCriteria(
            success_threshold=0.80, measurement_unit="opportunities_identified",
            measurement_method="impact_analysis", validation_timeout_hours=48
        ),
        dependencies=["cost_002", "cost_003"],
        tools_required=["optimization_analyzer"],
        expected_outcome="Prioritized optimization opportunity list"
    )

def _create_cost_step_5() -> PlanStep:
    """Create cost optimization step 5."""
    return PlanStep(
        id="cost_005", title="Right-sizing Analysis",
        description="Analyze resource right-sizing opportunities",
        step_type=PlanStepType.OPTIMIZATION, priority=PlanPriority.HIGH,
        estimated_hours=10, validation_criteria=ValidationCriteria(
            success_threshold=0.90, measurement_unit="right_sizing_accuracy",
            measurement_method="capacity_analysis", validation_timeout_hours=36
        ),
        dependencies=["cost_004"], tools_required=["sizing_analyzer"],
        expected_outcome="Right-sizing recommendations with impact estimates"
    )

# Continuing with remaining cost steps and other plan steps...
# (Additional step creators would continue here following the same pattern)

def _create_cost_optimization_metrics() -> Dict[str, Any]:
    """Create cost optimization success metrics."""
    return {
        "cost_reduction_target": 20.0,
        "implementation_timeline_weeks": 8,
        "roi_target_months": 3,
        "quality_preservation": 100.0,
        "risk_tolerance": "medium"
    }

def _create_performance_tuning_metrics() -> Dict[str, Any]:
    """Create performance tuning success metrics."""
    return {
        "latency_improvement_target": 3.0,
        "throughput_improvement_target": 2.0,
        "implementation_timeline_weeks": 6,
        "performance_stability": 99.5,
        "regression_tolerance": 0.0
    }

def _create_capacity_planning_metrics() -> Dict[str, Any]:
    """Create capacity planning success metrics."""
    return {
        "forecast_accuracy_target": 95.0,
        "planning_horizon_months": 12,
        "scaling_response_time_minutes": 15,
        "cost_predictability": 90.0,
        "growth_accommodation": 50.0
    }

def _create_cost_optimization_risks() -> List[str]:
    """Create cost optimization risk factors."""
    return [
        "Quality degradation during optimization",
        "Service interruption during changes", 
        "Incomplete cost visibility leading to missed opportunities",
        "Vendor lock-in limiting optimization options"
    ]

def _create_performance_tuning_risks() -> List[str]:
    """Create performance tuning risk factors."""
    return [
        "Performance regression during optimization",
        "Resource contention during tuning",
        "Cascading performance impacts across services"
    ]

def _create_capacity_planning_risks() -> List[str]:
    """Create capacity planning risk factors."""
    return [
        "Inaccurate growth projections",
        "Sudden demand spikes exceeding planned capacity",
        "Resource provisioning delays impacting service"
    ]

# Additional step creators are implemented in plan_step_definitions.py
# This maintains the 450-line module limit and provides modular expansion