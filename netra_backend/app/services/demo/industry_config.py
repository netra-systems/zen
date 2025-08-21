"""Industry-specific configuration for demo service."""

from typing import Any, Dict

INDUSTRY_FACTORS = {
    "financial": {
        "cost_reduction": 0.45,
        "latency_improvement": 0.60,
        "throughput_increase": 2.5,
        "accuracy_boost": 0.08,
        "typical_scenarios": ["fraud_detection", "risk_assessment", "trading_algorithms"],
        "key_metrics": ["transaction_volume", "detection_accuracy", "processing_time"]
    },
    "healthcare": {
        "cost_reduction": 0.40,
        "latency_improvement": 0.55,
        "throughput_increase": 2.0,
        "accuracy_boost": 0.12,
        "typical_scenarios": ["diagnostic_ai", "patient_triage", "drug_discovery"],
        "key_metrics": ["diagnostic_accuracy", "patient_throughput", "compliance_score"]
    },
    "ecommerce": {
        "cost_reduction": 0.50,
        "latency_improvement": 0.65,
        "throughput_increase": 3.0,
        "accuracy_boost": 0.10,
        "typical_scenarios": ["recommendation_engine", "search_optimization", "inventory_prediction"],
        "key_metrics": ["conversion_rate", "cart_value", "search_relevance"]
    },
    "manufacturing": {
        "cost_reduction": 0.35,
        "latency_improvement": 0.50,
        "throughput_increase": 1.8,
        "accuracy_boost": 0.15,
        "typical_scenarios": ["predictive_maintenance", "quality_control", "supply_chain"],
        "key_metrics": ["downtime_reduction", "defect_rate", "efficiency_score"]
    },
    "technology": {
        "cost_reduction": 0.55,
        "latency_improvement": 0.70,
        "throughput_increase": 3.5,
        "accuracy_boost": 0.09,
        "typical_scenarios": ["code_generation", "bug_detection", "system_optimization"],
        "key_metrics": ["deployment_frequency", "bug_resolution_time", "system_uptime"]
    }
}

def get_industry_factors(industry: str) -> Dict[str, Any]:
    """Get industry-specific factors."""
    return INDUSTRY_FACTORS.get(
        industry.lower(), 
        INDUSTRY_FACTORS["technology"]
    )