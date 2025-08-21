"""Metrics generation for demo service."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List

import numpy as np

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.demo.industry_config import get_industry_factors

logger = central_logger.get_logger(__name__)

def calculate_savings(industry_data: Dict[str, Any]) -> float:
    """Calculate estimated annual savings."""
    base_savings = random.uniform(500000, 2000000)
    return base_savings * industry_data["cost_reduction"]

def generate_optimization_metrics(industry: str) -> Dict[str, Any]:
    """Generate optimization metrics based on industry."""
    industry_data = get_industry_factors(industry)
    return {
        "cost_reduction_percentage": industry_data["cost_reduction"] * 100,
        "latency_improvement_ms": random.uniform(50, 200) * industry_data["latency_improvement"],
        "throughput_increase_factor": industry_data["throughput_increase"],
        "accuracy_improvement_percentage": industry_data["accuracy_boost"] * 100,
        "estimated_annual_savings": calculate_savings(industry_data),
        "implementation_time_weeks": random.randint(2, 8),
        "confidence_score": random.uniform(0.85, 0.98)
    }

def generate_baseline_metrics(industry: str) -> Dict[str, Any]:
    """Generate baseline metrics for industry."""
    return {
        "avg_latency_ms": random.uniform(200, 500),
        "requests_per_second": random.randint(100, 1000),
        "error_rate": random.uniform(0.01, 0.05),
        "cost_per_1k_requests": random.uniform(5, 20),
        "model_accuracy": random.uniform(0.80, 0.90)
    }

def generate_optimized_metrics(industry: str) -> Dict[str, Any]:
    """Generate optimized metrics showing improvement."""
    baseline = generate_baseline_metrics(industry)
    factors = get_industry_factors(industry)
    return {
        "avg_latency_ms": baseline["avg_latency_ms"] * (1 - factors["latency_improvement"]),
        "requests_per_second": baseline["requests_per_second"] * factors["throughput_increase"],
        "error_rate": baseline["error_rate"] * 0.5,
        "cost_per_1k_requests": baseline["cost_per_1k_requests"] * (1 - factors["cost_reduction"]),
        "model_accuracy": min(0.99, baseline["model_accuracy"] + factors["accuracy_boost"])
    }

def generate_time_series_data(duration_hours: int) -> List[datetime]:
    """Generate timestamps for time series data."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=duration_hours)
    timestamps = []
    current = start_time
    while current <= end_time:
        timestamps.append(current)
        current += timedelta(minutes=15)
    return timestamps

def generate_synthetic_values(num_points: int) -> Dict[str, List[float]]:
    """Generate synthetic metric values."""
    baseline_latency = 250 + np.random.normal(0, 20, num_points)
    baseline_throughput = 500 + np.random.normal(0, 50, num_points)
    baseline_cost = 10 + np.random.normal(0, 1, num_points)
    improvement_curve = np.linspace(0, 1, num_points)
    return {
        "baseline_latency": (baseline_latency).tolist(),
        "optimized_latency": (baseline_latency * (1 - 0.6 * improvement_curve) + 
                             np.random.normal(0, 10, num_points)).tolist(),
        "baseline_throughput": (baseline_throughput).tolist(),
        "optimized_throughput": (baseline_throughput * (1 + 2 * improvement_curve) + 
                                np.random.normal(0, 30, num_points)).tolist(),
        "baseline_cost": (baseline_cost).tolist(),
        "optimized_cost": (baseline_cost * (1 - 0.45 * improvement_curve) + 
                          np.random.normal(0, 0.5, num_points)).tolist()
    }

async def generate_synthetic_metrics(scenario: str = "standard", 
                                   duration_hours: int = 24) -> Dict[str, Any]:
    """Generate synthetic performance metrics for demonstration."""
    try:
        timestamps = generate_time_series_data(duration_hours)
        num_points = len(timestamps)
        values = generate_synthetic_values(num_points)
        
        return {
            "latency_reduction": 60.0,
            "throughput_increase": 200.0,
            "cost_reduction": 45.0,
            "accuracy_improvement": 8.5,
            "timestamps": timestamps,
            "values": values
        }
    except Exception as e:
        logger.error(f"Synthetic metrics generation error: {str(e)}")
        raise

def calculate_roi_metrics(factors: Dict[str, Any], 
                         current_spend: float) -> Dict[str, Any]:
    """Calculate ROI metrics."""
    current_annual_cost = current_spend * 12
    optimized_annual_cost = current_annual_cost * (1 - factors["cost_reduction"])
    annual_savings = current_annual_cost - optimized_annual_cost
    implementation_cost = current_spend * 0.5
    roi_months = int(np.ceil(implementation_cost / (annual_savings / 12)))
    return {
        "current_annual_cost": current_annual_cost,
        "optimized_annual_cost": optimized_annual_cost,
        "annual_savings": annual_savings,
        "savings_percentage": (annual_savings / current_annual_cost) * 100,
        "roi_months": roi_months,
        "three_year_tco_reduction": annual_savings * 3 - implementation_cost
    }

async def calculate_roi(current_spend: float, request_volume: int,
                       average_latency: float, industry: str) -> Dict[str, Any]:
    """Calculate ROI for AI optimization."""
    try:
        factors = get_industry_factors(industry)
        roi_metrics = calculate_roi_metrics(factors, current_spend)
        performance_improvements = {
            "latency_reduction_percentage": factors["latency_improvement"] * 100,
            "throughput_increase_factor": factors["throughput_increase"],
            "accuracy_improvement_percentage": factors["accuracy_boost"] * 100,
            "error_rate_reduction_percentage": 50.0
        }
        roi_metrics["performance_improvements"] = performance_improvements
        return roi_metrics
    except Exception as e:
        logger.error(f"ROI calculation error: {str(e)}")
        raise