"""
E2E Test Data Module

This module provides comprehensive test data generation for E2E testing:
- Seeded data generation (production-mirror, stress-test, domain-specific)
- Test scenarios (9 example prompts with validation criteria)
- Default optimization plans (cost, performance, capacity)
- Edge cases and temporal patterns
- Error injection scenarios

ARCHITECTURAL COMPLIANCE:
- Modular design with 450-line file limits
- Strong typing throughout
- Single responsibility per module
- Composable generators

Usage:
    from app.tests.e2e.data import (
        ProductionMirrorGenerator,
        get_cost_optimization_plan,
        EdgeCaseGenerator,
        TemporalPatternGenerator
    )
"""

from .seeded_data_generator import (
    ProductionMirrorGenerator,
    StressTestGenerator,
    DomainSpecificGenerator,
    DatasetConfig
)

from .default_plans import (
    get_cost_optimization_plan,
    get_performance_tuning_plan,
    get_capacity_planning_plan,
    OptimizationPlan,
    PlanStep,
    ValidationCriteria
)

from .edge_cases_temporal import (
    EdgeCaseGenerator,
    ErrorConditionSimulator,
    EdgeCase,
    EdgeCaseCategory
)

from .temporal_patterns import (
    TemporalPatternGenerator,
    SeasonalPatternGenerator,
    BurstPatternGenerator,
    GrowthPatternGenerator,
    TemporalPattern,
    TemporalPatternType
)

__all__ = [
    # Data generators
    "ProductionMirrorGenerator",
    "StressTestGenerator", 
    "DomainSpecificGenerator",
    "DatasetConfig",
    
    # Plans
    "get_cost_optimization_plan",
    "get_performance_tuning_plan",
    "get_capacity_planning_plan",
    "OptimizationPlan",
    "PlanStep",
    "ValidationCriteria",
    
    # Edge cases
    "EdgeCaseGenerator",
    "ErrorConditionSimulator",
    "EdgeCase",
    "EdgeCaseCategory",
    
    # Temporal patterns
    "TemporalPatternGenerator",
    "SeasonalPatternGenerator",
    "BurstPatternGenerator", 
    "GrowthPatternGenerator",
    "TemporalPattern",
    "TemporalPatternType"
]