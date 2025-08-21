"""Constants and configuration for demo service."""

from typing import Any, Dict

# Industry-specific optimization factors
INDUSTRY_FACTORS: Dict[str, Dict[str, Any]] = {
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
        "typical_scenarios": ["quality_control", "predictive_maintenance", "supply_chain"],
        "key_metrics": ["defect_rate", "uptime", "production_efficiency"]
    },
    "media": {
        "cost_reduction": 0.42,
        "latency_improvement": 0.70,
        "throughput_increase": 2.8,
        "accuracy_boost": 0.09,
        "typical_scenarios": ["content_generation", "personalization", "ad_targeting"],
        "key_metrics": ["engagement_rate", "content_quality", "revenue_per_user"]
    }
}

# Workload templates for different scenarios
WORKLOAD_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "fraud_detection": {
        "model_size": "large",
        "batch_size": 1000,
        "latency_target": 100,
        "throughput_requirement": 10000,
        "accuracy_threshold": 0.95
    },
    "recommendation_engine": {
        "model_size": "medium",
        "batch_size": 50,
        "latency_target": 50,
        "throughput_requirement": 50000,
        "accuracy_threshold": 0.85
    },
    "diagnostic_ai": {
        "model_size": "extra_large",
        "batch_size": 1,
        "latency_target": 500,
        "throughput_requirement": 1000,
        "accuracy_threshold": 0.98
    },
    "quality_control": {
        "model_size": "medium",
        "batch_size": 100,
        "latency_target": 200,
        "throughput_requirement": 5000,
        "accuracy_threshold": 0.99
    },
    "content_generation": {
        "model_size": "large",
        "batch_size": 10,
        "latency_target": 1000,
        "throughput_requirement": 2000,
        "accuracy_threshold": 0.90
    }
}

# Demo session configuration
DEMO_SESSION_TTL = 3600  # 1 hour in seconds
MAX_DEMO_SESSIONS = 100
DEMO_DATA_REFRESH_INTERVAL = 300  # 5 minutes