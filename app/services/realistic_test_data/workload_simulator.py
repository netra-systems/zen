"""Workload Simulator

This module generates realistic workload patterns with seasonality and business logic.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import numpy as np


class WorkloadSimulator:
    """Simulates realistic workload patterns"""
    
    def __init__(self):
        """Initialize workload simulator"""
        self.workload_profiles = self._init_workload_profiles()
    
    def _init_workload_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Initialize workload profiles for different business types"""
        return {
            "ecommerce": {
                "base_rps": 100,
                "peak_multiplier": 5.0,
                "peak_hours": [19, 20, 21],  # Evening shopping
                "weekend_multiplier": 1.3,
                "seasonality": {
                    "black_friday": 8.0,
                    "holiday_season": 3.0,
                    "back_to_school": 2.0
                },
                "model_usage": {
                    "recommendation": 0.4,
                    "search": 0.3,
                    "customer_service": 0.2,
                    "content_generation": 0.1
                }
            },
            "fintech": {
                "base_rps": 50,
                "peak_multiplier": 3.0,
                "peak_hours": [9, 10, 11, 14, 15],  # Business hours
                "weekend_multiplier": 0.3,
                "seasonality": {
                    "tax_season": 4.0,
                    "end_of_quarter": 2.5,
                    "year_end": 3.0
                },
                "model_usage": {
                    "fraud_detection": 0.5,
                    "risk_assessment": 0.3,
                    "customer_service": 0.15,
                    "document_analysis": 0.05
                }
            },
            "healthcare": {
                "base_rps": 30,
                "peak_multiplier": 2.0,
                "peak_hours": [8, 9, 10, 14, 15, 16],
                "weekend_multiplier": 0.6,
                "seasonality": {
                    "flu_season": 2.5,
                    "pandemic_surge": 5.0,
                    "allergy_season": 1.8
                },
                "model_usage": {
                    "diagnosis_assistance": 0.4,
                    "medical_qa": 0.3,
                    "administrative": 0.2,
                    "research": 0.1
                }
            }
        }
    
    def generate_workload_simulation(
        self,
        workload_type: str = "ecommerce",
        duration_days: int = 7,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """
        Generate realistic workload simulation data
        
        Args:
            workload_type: Type of business workload to simulate
            duration_days: Duration of simulation in days
            include_seasonality: Whether to include seasonal variations
            
        Returns:
            Complete workload simulation data
        """
        profile = self.workload_profiles.get(workload_type, self.workload_profiles["ecommerce"])
        
        # Generate hourly traffic data
        traffic_data = self._generate_traffic_patterns(profile, duration_days, include_seasonality)
        
        # Generate model usage breakdown
        model_usage = self._generate_model_usage_data(profile, traffic_data)
        
        # Generate performance characteristics
        performance_data = self._generate_performance_data(traffic_data)
        
        # Generate cost estimates
        cost_data = self._generate_cost_estimates(model_usage, traffic_data)
        
        return {
            "workload_type": workload_type,
            "duration_days": duration_days,
            "total_requests": sum(hour["requests"] for hour in traffic_data),
            "peak_rps": max(hour["rps"] for hour in traffic_data),
            "average_rps": np.mean([hour["rps"] for hour in traffic_data]),
            "traffic_data": traffic_data,
            "model_usage": model_usage,
            "performance_data": performance_data,
            "cost_data": cost_data,
            "business_impact": self._calculate_business_impact(profile, traffic_data, cost_data)
        }
    
    def _generate_traffic_patterns(
        self,
        profile: Dict[str, Any],
        duration_days: int,
        include_seasonality: bool
    ) -> List[Dict[str, Any]]:
        """Generate realistic traffic patterns"""
        traffic_data = []
        start_time = datetime.now(timezone.utc) - timedelta(days=duration_days)
        
        for day in range(duration_days):
            is_weekend = (start_time + timedelta(days=day)).weekday() >= 5
            day_multiplier = profile["weekend_multiplier"] if is_weekend else 1.0
            
            for hour in range(24):
                current_time = start_time + timedelta(days=day, hours=hour)
                
                # Base traffic calculation
                base_rps = profile["base_rps"] * day_multiplier
                
                # Peak hour adjustments
                if hour in profile["peak_hours"]:
                    base_rps *= profile["peak_multiplier"]
                
                # Add realistic noise
                noise_factor = random.uniform(0.8, 1.2)
                current_rps = int(base_rps * noise_factor)
                
                # Seasonality adjustments
                if include_seasonality:
                    current_rps = self._apply_seasonality(current_rps, current_time, profile)
                
                # Generate additional metrics
                traffic_data.append({
                    "timestamp": current_time.isoformat(),
                    "hour_of_day": hour,
                    "day_of_week": current_time.weekday(),
                    "is_weekend": is_weekend,
                    "rps": current_rps,
                    "requests": current_rps * 3600,  # requests per hour
                    "latency_p50_ms": self._calculate_latency(current_rps, "p50"),
                    "latency_p95_ms": self._calculate_latency(current_rps, "p95"),
                    "error_rate": self._calculate_error_rate(current_rps)
                })
        
        return traffic_data
    
    def _apply_seasonality(
        self,
        base_rps: int,
        current_time: datetime,
        profile: Dict[str, Any]
    ) -> int:
        """Apply seasonal adjustments to traffic"""
        seasonality = profile.get("seasonality", {})
        
        # Simple seasonal patterns (would be more sophisticated in production)
        month = current_time.month
        day = current_time.day
        
        # Holiday season (November-December)
        if month in [11, 12]:
            return int(base_rps * seasonality.get("holiday_season", 1.0))
        
        # Back to school (August-September)
        elif month in [8, 9]:
            return int(base_rps * seasonality.get("back_to_school", 1.0))
        
        # Black Friday simulation (last Friday of November)
        elif month == 11 and current_time.weekday() == 4 and day >= 23:
            return int(base_rps * seasonality.get("black_friday", 1.0))
        
        return base_rps
    
    def _calculate_latency(self, rps: int, percentile: str) -> float:
        """Calculate latency based on load"""
        # Simulate latency increase under load
        base_latency = {"p50": 100, "p95": 250}[percentile]
        load_factor = max(1.0, rps / 100)  # Latency increases with load
        
        latency = base_latency * (1 + np.log(load_factor) * 0.3)
        # Add realistic variation
        return round(latency * random.uniform(0.8, 1.2), 1)
    
    def _calculate_error_rate(self, rps: int) -> float:
        """Calculate error rate based on load"""
        base_error_rate = 0.01  # 1% base error rate
        load_factor = max(1.0, rps / 100)
        
        # Error rate increases with load
        error_rate = base_error_rate * (1 + (load_factor - 1) * 0.1)
        return round(min(error_rate, 0.05), 4)  # Cap at 5%
    
    def _generate_model_usage_data(
        self,
        profile: Dict[str, Any],
        traffic_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate model usage breakdown"""
        model_usage_data = []
        total_requests = sum(hour["requests"] for hour in traffic_data)
        
        for model_type, percentage in profile["model_usage"].items():
            model_requests = int(total_requests * percentage)
            
            # Add realistic model characteristics
            if "recommendation" in model_type:
                avg_tokens = 200
                cost_per_1k = 0.02
            elif "search" in model_type:
                avg_tokens = 150
                cost_per_1k = 0.015
            elif "fraud_detection" in model_type:
                avg_tokens = 300
                cost_per_1k = 0.03
            else:
                avg_tokens = 250
                cost_per_1k = 0.025
            
            model_usage_data.append({
                "model_type": model_type,
                "requests": model_requests,
                "percentage": percentage,
                "avg_tokens_per_request": avg_tokens,
                "total_tokens": model_requests * avg_tokens,
                "cost_per_1k_tokens": cost_per_1k,
                "total_cost": (model_requests * avg_tokens / 1000) * cost_per_1k
            })
        
        return model_usage_data
    
    def _generate_performance_data(self, traffic_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate performance metrics summary"""
        latencies_p50 = [hour["latency_p50_ms"] for hour in traffic_data]
        latencies_p95 = [hour["latency_p95_ms"] for hour in traffic_data]
        error_rates = [hour["error_rate"] for hour in traffic_data]
        
        return {
            "avg_latency_p50_ms": round(np.mean(latencies_p50), 1),
            "avg_latency_p95_ms": round(np.mean(latencies_p95), 1),
            "max_latency_p50_ms": max(latencies_p50),
            "max_latency_p95_ms": max(latencies_p95),
            "avg_error_rate": round(np.mean(error_rates), 4),
            "max_error_rate": max(error_rates),
            "availability": round((1 - np.mean(error_rates)) * 100, 2)
        }
    
    def _generate_cost_estimates(
        self,
        model_usage: List[Dict[str, Any]],
        traffic_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate cost estimates"""
        total_cost = sum(model["total_cost"] for model in model_usage)
        total_tokens = sum(model["total_tokens"] for model in model_usage)
        
        # Infrastructure costs (simplified)
        peak_rps = max(hour["rps"] for hour in traffic_data)
        infrastructure_cost = peak_rps * 0.001 * 24 * len(traffic_data) / 24  # $0.001 per RPS per day
        
        return {
            "model_costs_usd": round(total_cost, 2),
            "infrastructure_costs_usd": round(infrastructure_cost, 2),
            "total_costs_usd": round(total_cost + infrastructure_cost, 2),
            "total_tokens": total_tokens,
            "cost_per_token_usd": round((total_cost / total_tokens) if total_tokens > 0 else 0, 8),
            "cost_per_request_usd": round(total_cost / sum(hour["requests"] for hour in traffic_data), 6)
        }
    
    def _calculate_business_impact(
        self,
        profile: Dict[str, Any],
        traffic_data: List[Dict[str, Any]],
        cost_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate business impact metrics"""
        total_requests = sum(hour["requests"] for hour in traffic_data)
        avg_error_rate = np.mean([hour["error_rate"] for hour in traffic_data])
        
        # Simplified business impact calculations
        successful_requests = int(total_requests * (1 - avg_error_rate))
        revenue_per_request = {"ecommerce": 0.05, "fintech": 0.10, "healthcare": 0.02}.get(
            profile.get("workload_type", "ecommerce"), 0.05
        )
        
        return {
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "estimated_revenue_usd": round(successful_requests * revenue_per_request, 2),
            "revenue_to_cost_ratio": round(
                (successful_requests * revenue_per_request) / cost_data["total_costs_usd"], 2
            ),
            "request_success_rate": round((1 - avg_error_rate) * 100, 2)
        }