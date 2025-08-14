"""Metrics generation for demo service."""

import random
import numpy as np
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional
from app.services.demo.demo_constants import INDUSTRY_FACTORS, WORKLOAD_TEMPLATES

class DemoMetricsGenerator:
    """Generates realistic metrics for demo scenarios."""
    
    @staticmethod
    def generate_performance_metrics(industry: str, scenario: str) -> Dict[str, Any]:
        """Generate performance metrics for demo."""
        factors = INDUSTRY_FACTORS.get(industry, INDUSTRY_FACTORS["ecommerce"])
        template = WORKLOAD_TEMPLATES.get(scenario, WORKLOAD_TEMPLATES["recommendation_engine"])
        
        base_cost = random.uniform(1000, 5000)
        base_latency = template["latency_target"]
        
        return {
            "current": {
                "cost_per_hour": base_cost,
                "avg_latency_ms": base_latency,
                "throughput_rps": template["throughput_requirement"] * 0.7,
                "accuracy": template["accuracy_threshold"] * 0.95,
                "error_rate": random.uniform(0.02, 0.05)
            },
            "optimized": {
                "cost_per_hour": base_cost * (1 - factors["cost_reduction"]),
                "avg_latency_ms": base_latency * (1 - factors["latency_improvement"]),
                "throughput_rps": template["throughput_requirement"] * factors["throughput_increase"],
                "accuracy": min(0.99, template["accuracy_threshold"] + factors["accuracy_boost"]),
                "error_rate": random.uniform(0.001, 0.01)
            },
            "improvement_percentage": {
                "cost": factors["cost_reduction"] * 100,
                "latency": factors["latency_improvement"] * 100,
                "throughput": (factors["throughput_increase"] - 1) * 100,
                "accuracy": factors["accuracy_boost"] * 100
            }
        }
    
    @staticmethod
    def generate_time_series_data(hours: int = 24) -> List[Dict[str, Any]]:
        """Generate time series data for visualization."""
        data = []
        base_time = datetime.now(UTC) - timedelta(hours=hours)
        
        for i in range(hours * 4):  # 15-minute intervals
            timestamp = base_time + timedelta(minutes=i * 15)
            hour_of_day = timestamp.hour
            
            # Simulate daily patterns
            load_factor = DemoMetricsGenerator._get_load_factor(hour_of_day)
            
            data.append({
                "timestamp": timestamp.isoformat(),
                "requests": int(1000 * load_factor + random.uniform(-100, 100)),
                "latency": 50 + (20 * load_factor) + random.uniform(-5, 5),
                "errors": max(0, int(10 * load_factor + random.uniform(-2, 2))),
                "cpu_usage": min(100, 30 + (40 * load_factor) + random.uniform(-5, 5)),
                "memory_usage": min(100, 40 + (30 * load_factor) + random.uniform(-3, 3))
            })
        
        return data
    
    @staticmethod
    def _get_load_factor(hour: int) -> float:
        """Calculate load factor based on hour of day."""
        if 9 <= hour <= 17:  # Business hours
            return 0.8 + random.uniform(0, 0.2)
        elif 6 <= hour < 9 or 17 < hour <= 20:  # Peak hours
            return 0.6 + random.uniform(0, 0.2)
        else:  # Off hours
            return 0.3 + random.uniform(0, 0.1)
    
    @staticmethod
    def generate_cost_breakdown(total_cost: float) -> Dict[str, float]:
        """Generate cost breakdown by component."""
        breakdown = {
            "compute": total_cost * 0.45,
            "memory": total_cost * 0.20,
            "storage": total_cost * 0.15,
            "network": total_cost * 0.10,
            "licensing": total_cost * 0.10
        }
        return breakdown
    
    @staticmethod
    def generate_optimization_recommendations(industry: str) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = [
            {
                "priority": "high",
                "type": "model_optimization",
                "title": "Model Quantization",
                "description": "Apply INT8 quantization to reduce model size by 75%",
                "estimated_impact": {
                    "cost_reduction": "30%",
                    "latency_improvement": "40%"
                }
            },
            {
                "priority": "high",
                "type": "infrastructure",
                "title": "GPU Instance Optimization",
                "description": "Switch to latest generation GPUs for better price/performance",
                "estimated_impact": {
                    "cost_reduction": "25%",
                    "throughput_increase": "2x"
                }
            },
            {
                "priority": "medium",
                "type": "batching",
                "title": "Dynamic Batching",
                "description": "Implement dynamic batching to improve throughput",
                "estimated_impact": {
                    "throughput_increase": "3x",
                    "latency_improvement": "20%"
                }
            }
        ]
        
        # Add industry-specific recommendations
        if industry == "financial":
            recommendations.append({
                "priority": "high",
                "type": "compliance",
                "title": "Regulatory Compliance Optimization",
                "description": "Optimize model serving for financial regulations",
                "estimated_impact": {
                    "compliance_score": "+15%",
                    "audit_time_reduction": "50%"
                }
            })
        
        return recommendations