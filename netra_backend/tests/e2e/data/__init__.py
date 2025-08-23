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
    from netra_backend.tests.e2e.data import (
        ProductionMirrorGenerator,
        get_cost_optimization_plan,
        EdgeCaseGenerator,
        TemporalPatternGenerator
    )
"""

from netra_backend.tests.e2e.data.default_plans import (
    OptimizationPlan,
    PlanStep,
    ValidationCriteria,
    get_capacity_planning_plan,
    get_cost_optimization_plan,
    get_performance_tuning_plan,
)
# NOTE: edge_cases_temporal module not found - commenting out for now
# from netra_backend.tests.edge_cases_temporal import (
#     EdgeCase,
#     EdgeCaseCategory,
#     EdgeCaseGenerator,
#     ErrorConditionSimulator,
# )
from netra_backend.tests.e2e.data.seeded_data_generator import (
    DatasetConfig,
    DomainSpecificGenerator,
    ProductionMirrorGenerator,
    StressTestGenerator,
)
from netra_backend.tests.e2e.data.temporal_patterns import (
    BurstPatternGenerator,
    GrowthPatternGenerator,
    SeasonalPatternGenerator,
    TemporalPattern,
    TemporalPatternGenerator,
    TemporalPatternType,
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
    
    # Edge cases - commented out due to missing module
    # "EdgeCaseGenerator",
    # "ErrorConditionSimulator",
    # "EdgeCase",
    # "EdgeCaseCategory",
    
    # Temporal patterns
    "TemporalPatternGenerator",
    "SeasonalPatternGenerator",
    "BurstPatternGenerator", 
    "GrowthPatternGenerator",
    "TemporalPattern",
    "TemporalPatternType"
]