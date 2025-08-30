"""Business Logic Validation Test Suite

This package contains comprehensive tests for validating agent business logic outcomes,
not just technical execution. Focus is on ensuring agents make correct business decisions
that drive value for customers.

Test Coverage Areas:
--------------------
1. Triage Decision Logic (test_triage_decisions.py)
   - Data sufficiency assessment
   - Workflow path selection
   - Priority classification

2. Optimization Value (test_optimization_value.py)
   - ROI validation
   - Recommendation quality
   - Implementation feasibility

3. Adaptive Workflow Flows (test_adaptive_workflow_flows.py)
   - End-to-end flow validation
   - Agent handoff testing
   - Context accumulation

4. Data Helper Clarity (test_data_helper_clarity.py)
   - Request clarity and actionability
   - User experience validation
   - Progressive data collection

Business Value Justification (BVJ):
-----------------------------------
Segment: Enterprise, Mid
Business Goal: Quality Assurance, Risk Reduction
Value Impact: Ensures agent outputs create measurable business value ($10K-100K+ per customer)
Strategic Impact: Validates core value proposition of AI optimization platform
"""

from typing import List

# Test module imports for easy access
__all__: List[str] = [
    "TestTriageDecisionLogic",
    "TestOptimizationOutputQuality", 
    "TestAdaptiveWorkflowFlows",
    "TestDataHelperClarity"
]

# Test configuration
TEST_CATEGORIES = {
    "business_logic": {
        "priority": "CRITICAL",
        "coverage_target": 0.80,
        "test_files": [
            "test_triage_decisions.py",
            "test_optimization_value.py",
            "test_adaptive_workflow_flows.py",
            "test_data_helper_clarity.py"
        ]
    }
}

# Business scenario validation requirements
BUSINESS_SCENARIOS = {
    "cost_optimization": {
        "min_savings": 1000,  # Minimum monthly savings in USD
        "confidence_threshold": 0.70,
        "required_metrics": ["monthly_spend", "usage_volume", "model_distribution"]
    },
    "performance_optimization": {
        "min_latency_reduction": 0.20,  # 20% minimum improvement
        "required_metrics": ["p50_latency", "p95_latency", "request_volume"]
    },
    "multi_objective": {
        "requires_tradeoff_analysis": True,
        "min_objectives": 2,
        "required_metrics": ["current_state", "constraints", "priorities"]
    }
}

# Agent output quality thresholds
QUALITY_THRESHOLDS = {
    "triage": {
        "decision_accuracy": 0.95,
        "workflow_selection_accuracy": 0.90,
        "context_preservation": 1.0
    },
    "optimization": {
        "recommendation_specificity": 0.85,
        "roi_accuracy": 0.75,
        "implementation_feasibility": 0.90
    },
    "data_helper": {
        "question_clarity": 0.90,
        "user_abandonment_rate": 0.05,
        "data_collection_success": 0.80
    },
    "reporting": {
        "completeness": 0.95,
        "value_demonstration": 0.90,
        "actionability": 0.85
    }
}