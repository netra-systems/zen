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
        ecommerce = self._create_ecommerce_profile()
        fintech = self._create_fintech_profile()
        healthcare = self._create_healthcare_profile()
        return {"ecommerce": ecommerce, "fintech": fintech, "healthcare": healthcare}
    
    def _create_ecommerce_profile(self) -> Dict[str, Any]:
        """Create ecommerce workload profile."""
        seasonality = {"black_friday": 8.0, "holiday_season": 3.0, "back_to_school": 2.0}
        model_usage = {"recommendation": 0.4, "search": 0.3, "customer_service": 0.2, "content_generation": 0.1}
        return {"base_rps": 100, "peak_multiplier": 5.0, "peak_hours": [19, 20, 21], "weekend_multiplier": 1.3, "seasonality": seasonality, "model_usage": model_usage}
    
    def _create_fintech_profile(self) -> Dict[str, Any]:
        """Create fintech workload profile."""
        seasonality = {"tax_season": 4.0, "end_of_quarter": 2.5, "year_end": 3.0}
        model_usage = {"fraud_detection": 0.5, "risk_assessment": 0.3, "customer_service": 0.15, "document_analysis": 0.05}
        return {"base_rps": 50, "peak_multiplier": 3.0, "peak_hours": [9, 10, 11, 14, 15], "weekend_multiplier": 0.3, "seasonality": seasonality, "model_usage": model_usage}
    
    def _create_healthcare_profile(self) -> Dict[str, Any]:
        """Create healthcare workload profile."""
        seasonality = {"flu_season": 2.5, "pandemic_surge": 5.0, "allergy_season": 1.8}
        model_usage = {"diagnosis_assistance": 0.4, "medical_qa": 0.3, "administrative": 0.2, "research": 0.1}
        return {"base_rps": 30, "peak_multiplier": 2.0, "peak_hours": [8, 9, 10, 14, 15, 16], "weekend_multiplier": 0.6, "seasonality": seasonality, "model_usage": model_usage}
    
    def generate_workload_simulation(
        self,
        workload_type: str = "ecommerce",
        duration_days: int = 7,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """Generate realistic workload simulation data."""
        profile = self.workload_profiles.get(workload_type, self.workload_profiles["ecommerce"])
        return self._generate_simulation_components(profile, workload_type, duration_days, include_seasonality)
    
    def _generate_simulation_components(
        self, profile: Dict[str, Any], workload_type: str, 
        duration_days: int, include_seasonality: bool
    ) -> Dict[str, Any]:
        """Generate all simulation data components."""
        traffic_data = self._generate_traffic_patterns(profile, duration_days, include_seasonality)
        model_usage = self._generate_model_usage_data(profile, traffic_data)
        performance_data = self._generate_performance_data(traffic_data)
        cost_data = self._generate_cost_estimates(model_usage, traffic_data)
        return self._build_simulation_result(workload_type, duration_days, traffic_data, model_usage, performance_data, cost_data, profile)
    
    def _build_simulation_result(
        self, workload_type: str, duration_days: int, traffic_data: List[Dict[str, Any]],
        model_usage: List[Dict[str, Any]], performance_data: Dict[str, Any], 
        cost_data: Dict[str, Any], profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build final simulation result dictionary."""
        return {"workload_type": workload_type, "duration_days": duration_days, "total_requests": sum(hour["requests"] for hour in traffic_data), "peak_rps": max(hour["rps"] for hour in traffic_data), "average_rps": np.mean([hour["rps"] for hour in traffic_data]), "traffic_data": traffic_data, "model_usage": model_usage, "performance_data": performance_data, "cost_data": cost_data, "business_impact": self._calculate_business_impact(profile, traffic_data, cost_data)}
    
    def _generate_traffic_patterns(
        self,
        profile: Dict[str, Any],
        duration_days: int,
        include_seasonality: bool
    ) -> List[Dict[str, Any]]:
        """Generate realistic traffic patterns"""
        traffic_data = []
        start_time = datetime.now(timezone.utc) - timedelta(days=duration_days)
        self._generate_daily_traffic_patterns(traffic_data, profile, duration_days, start_time, include_seasonality)
        return traffic_data
    
    def _generate_daily_traffic_patterns(
        self, traffic_data: List[Dict[str, Any]], profile: Dict[str, Any], 
        duration_days: int, start_time: datetime, include_seasonality: bool
    ) -> None:
        """Generate traffic patterns for all days."""
        for day in range(duration_days):
            is_weekend = (start_time + timedelta(days=day)).weekday() >= 5
            day_multiplier = profile["weekend_multiplier"] if is_weekend else 1.0
            self._generate_hourly_traffic_patterns(traffic_data, profile, day, start_time, day_multiplier, is_weekend, include_seasonality)
    
    def _generate_hourly_traffic_patterns(
        self, traffic_data: List[Dict[str, Any]], profile: Dict[str, Any], day: int,
        start_time: datetime, day_multiplier: float, is_weekend: bool, include_seasonality: bool
    ) -> None:
        """Generate traffic patterns for all hours in a day."""
        for hour in range(24):
            current_time = start_time + timedelta(days=day, hours=hour)
            current_rps = self._calculate_hourly_rps(profile, hour, day_multiplier, current_time, include_seasonality)
            hour_data = self._build_hour_traffic_data(current_time, hour, is_weekend, current_rps)
            traffic_data.append(hour_data)
    
    def _calculate_hourly_rps(
        self, profile: Dict[str, Any], hour: int, day_multiplier: float, 
        current_time: datetime, include_seasonality: bool
    ) -> int:
        """Calculate RPS for specific hour."""
        base_rps = profile["base_rps"] * day_multiplier
        if hour in profile["peak_hours"]:
            base_rps *= profile["peak_multiplier"]
        noise_factor = random.uniform(0.8, 1.2)
        current_rps = int(base_rps * noise_factor)
        if include_seasonality:
            current_rps = self._apply_seasonality(current_rps, current_time, profile)
        return current_rps
    
    def _build_hour_traffic_data(self, current_time: datetime, hour: int, is_weekend: bool, current_rps: int) -> Dict[str, Any]:
        """Build traffic data for single hour."""
        return {"timestamp": current_time.isoformat(), "hour_of_day": hour, "day_of_week": current_time.weekday(), "is_weekend": is_weekend, "rps": current_rps, "requests": current_rps * 3600, "latency_p50_ms": self._calculate_latency(current_rps, "p50"), "latency_p95_ms": self._calculate_latency(current_rps, "p95"), "error_rate": self._calculate_error_rate(current_rps)}
    
    def _apply_seasonality(
        self,
        base_rps: int,
        current_time: datetime,
        profile: Dict[str, Any]
    ) -> int:
        """Apply seasonal adjustments to traffic"""
        seasonality = profile.get("seasonality", {})
        month, day, weekday = current_time.month, current_time.day, current_time.weekday()
        multiplier = self._get_seasonal_multiplier(month, day, weekday, seasonality)
        return int(base_rps * multiplier)
    
    def _get_seasonal_multiplier(
        self, month: int, day: int, weekday: int, seasonality: Dict[str, float]
    ) -> float:
        """Get seasonal multiplier for given date."""
        if month in [11, 12]:
            return seasonality.get("holiday_season", 1.0)
        elif month in [8, 9]:
            return seasonality.get("back_to_school", 1.0)
        elif month == 11 and weekday == 4 and day >= 23:
            return seasonality.get("black_friday", 1.0)
        return 1.0
    
    def _calculate_latency(self, rps: int, percentile: str) -> float:
        """Calculate latency based on load"""
        base_latency = {"p50": 100, "p95": 250}[percentile]
        load_factor = max(1.0, rps / 100)
        latency = base_latency * (1 + np.log(load_factor) * 0.3)
        return round(latency * random.uniform(0.8, 1.2), 1)
    
    def _calculate_error_rate(self, rps: int) -> float:
        """Calculate error rate based on load"""
        base_error_rate = 0.01
        load_factor = max(1.0, rps / 100)
        error_rate = base_error_rate * (1 + (load_factor - 1) * 0.1)
        return round(min(error_rate, 0.05), 4)
    
    def _generate_model_usage_data(
        self,
        profile: Dict[str, Any],
        traffic_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate model usage breakdown"""
        model_usage_data = []
        total_requests = sum(hour["requests"] for hour in traffic_data)
        self._populate_model_usage_data(model_usage_data, profile, total_requests)
        return model_usage_data
    
    def _populate_model_usage_data(
        self, model_usage_data: List[Dict[str, Any]], 
        profile: Dict[str, Any], total_requests: int
    ) -> None:
        """Populate model usage data for all model types."""
        for model_type, percentage in profile["model_usage"].items():
            model_requests = int(total_requests * percentage)
            avg_tokens, cost_per_1k = self._get_model_characteristics(model_type)
            usage_entry = self._build_model_usage_entry(model_type, percentage, model_requests, avg_tokens, cost_per_1k)
            model_usage_data.append(usage_entry)
    
    def _get_model_characteristics(self, model_type: str) -> tuple[int, float]:
        """Get token count and cost characteristics for model type."""
        if "recommendation" in model_type:
            return 200, 0.02
        elif "search" in model_type:
            return 150, 0.015
        elif "fraud_detection" in model_type:
            return 300, 0.03
        else:
            return 250, 0.025
    
    def _build_model_usage_entry(
        self, model_type: str, percentage: float, model_requests: int, 
        avg_tokens: int, cost_per_1k: float
    ) -> Dict[str, Any]:
        """Build single model usage entry."""
        total_tokens = model_requests * avg_tokens
        return {"model_type": model_type, "requests": model_requests, "percentage": percentage, "avg_tokens_per_request": avg_tokens, "total_tokens": total_tokens, "cost_per_1k_tokens": cost_per_1k, "total_cost": (total_tokens / 1000) * cost_per_1k}
    
    def _generate_performance_data(self, traffic_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate performance metrics summary"""
        latencies_p50 = [hour["latency_p50_ms"] for hour in traffic_data]
        latencies_p95 = [hour["latency_p95_ms"] for hour in traffic_data]
        error_rates = [hour["error_rate"] for hour in traffic_data]
        return self._build_performance_metrics(latencies_p50, latencies_p95, error_rates)
    
    def _build_performance_metrics(
        self, latencies_p50: List[float], latencies_p95: List[float], error_rates: List[float]
    ) -> Dict[str, Any]:
        """Build performance metrics dictionary."""
        return {"avg_latency_p50_ms": round(np.mean(latencies_p50), 1), "avg_latency_p95_ms": round(np.mean(latencies_p95), 1), "max_latency_p50_ms": max(latencies_p50), "max_latency_p95_ms": max(latencies_p95), "avg_error_rate": round(np.mean(error_rates), 4), "max_error_rate": max(error_rates), "availability": round((1 - np.mean(error_rates)) * 100, 2)}
    
    def _generate_cost_estimates(
        self,
        model_usage: List[Dict[str, Any]],
        traffic_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate cost estimates"""
        total_cost = sum(model["total_cost"] for model in model_usage)
        total_tokens = sum(model["total_tokens"] for model in model_usage)
        infrastructure_cost = self._calculate_infrastructure_cost(traffic_data)
        total_requests = sum(hour["requests"] for hour in traffic_data)
        return self._build_cost_estimates_result(total_cost, infrastructure_cost, total_tokens, total_requests)
    
    def _calculate_infrastructure_cost(self, traffic_data: List[Dict[str, Any]]) -> float:
        """Calculate infrastructure cost based on peak RPS."""
        peak_rps = max(hour["rps"] for hour in traffic_data)
        return peak_rps * 0.001 * 24 * len(traffic_data) / 24  # $0.001 per RPS per day
    
    def _build_cost_estimates_result(
        self, total_cost: float, infrastructure_cost: float, 
        total_tokens: int, total_requests: int
    ) -> Dict[str, Any]:
        """Build cost estimates result dictionary."""
        return {"model_costs_usd": round(total_cost, 2), "infrastructure_costs_usd": round(infrastructure_cost, 2), "total_costs_usd": round(total_cost + infrastructure_cost, 2), "total_tokens": total_tokens, "cost_per_token_usd": round((total_cost / total_tokens) if total_tokens > 0 else 0, 8), "cost_per_request_usd": round(total_cost / total_requests, 6)}
    
    def _calculate_business_impact(
        self,
        profile: Dict[str, Any],
        traffic_data: List[Dict[str, Any]],
        cost_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate business impact metrics"""
        total_requests = sum(hour["requests"] for hour in traffic_data)
        avg_error_rate = np.mean([hour["error_rate"] for hour in traffic_data])
        successful_requests = int(total_requests * (1 - avg_error_rate))
        revenue_per_request = self._get_revenue_per_request(profile)
        return self._build_business_impact_result(successful_requests, total_requests, revenue_per_request, cost_data, avg_error_rate)
    
    def _get_revenue_per_request(self, profile: Dict[str, Any]) -> float:
        """Get revenue per request based on workload type."""
        revenue_map = {"ecommerce": 0.05, "fintech": 0.10, "healthcare": 0.02}
        return revenue_map.get(profile.get("workload_type", "ecommerce"), 0.05)
    
    def _build_business_impact_result(
        self, successful_requests: int, total_requests: int, revenue_per_request: float,
        cost_data: Dict[str, Any], avg_error_rate: float
    ) -> Dict[str, Any]:
        """Build business impact result dictionary."""
        estimated_revenue = successful_requests * revenue_per_request
        return {"successful_requests": successful_requests, "failed_requests": total_requests - successful_requests, "estimated_revenue_usd": round(estimated_revenue, 2), "revenue_to_cost_ratio": round(estimated_revenue / cost_data["total_costs_usd"], 2), "request_success_rate": round((1 - avg_error_rate) * 100, 2)}