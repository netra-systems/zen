"""Performance Simulator

This module simulates performance patterns including cascading failures and bottlenecks.
"""

import random
from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np


class PerformanceSimulator:
    """Simulates realistic performance patterns and failures"""
    
    def __init__(self):
        """Initialize performance simulator"""
        self.failure_scenarios = self._init_failure_scenarios()
    
    def _init_failure_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Initialize realistic failure scenarios"""
        return {
            "cascading_failure": {
                "trigger": "high_load",
                "progression_rate": 0.1,  # 10% per minute
                "recovery_time_minutes": 15,
                "impact_multiplier": 3.0,
                "affected_services": ["api", "database", "cache"]
            },
            "memory_leak": {
                "trigger": "time_based",
                "progression_rate": 0.05,  # 5% degradation per hour
                "recovery_time_minutes": 30,
                "impact_multiplier": 2.0,
                "affected_services": ["worker", "scheduler"]
            },
            "database_deadlock": {
                "trigger": "concurrent_writes",
                "progression_rate": 0.2,  # Sudden spike
                "recovery_time_minutes": 5,
                "impact_multiplier": 5.0,
                "affected_services": ["database"]
            },
            "network_partition": {
                "trigger": "random",
                "progression_rate": 0.3,  # Immediate impact
                "recovery_time_minutes": 10,
                "impact_multiplier": 10.0,
                "affected_services": ["api", "external_services"]
            }
        }
    
    def simulate_performance_degradation(
        self,
        base_metrics: Dict[str, float],
        scenario: str = "cascading_failure",
        duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Simulate performance degradation over time
        
        Args:
            base_metrics: Baseline performance metrics
            scenario: Type of failure scenario
            duration_minutes: Duration of simulation
            
        Returns:
            List of performance data points over time
        """
        scenario_config = self.failure_scenarios.get(
            scenario,
            self.failure_scenarios["cascading_failure"]
        )
        
        performance_data = []
        current_time = datetime.now(timezone.utc)
        
        # Determine failure start point
        failure_start = random.randint(10, 20)  # Start failure 10-20 minutes in
        recovery_start = failure_start + scenario_config["recovery_time_minutes"]
        
        for minute in range(duration_minutes):
            timestamp = current_time.replace(
                minute=(current_time.minute + minute) % 60,
                hour=current_time.hour + (current_time.minute + minute) // 60
            )
            
            # Calculate degradation factor based on time and scenario
            degradation = self._calculate_degradation(
                minute, failure_start, recovery_start, scenario_config
            )
            
            # Apply degradation to metrics
            degraded_metrics = self._apply_degradation(base_metrics, degradation, scenario_config)
            
            performance_data.append({
                "timestamp": timestamp.isoformat(),
                "minute": minute,
                "degradation_factor": degradation,
                "scenario": scenario,
                "metrics": degraded_metrics,
                "health_status": self._determine_health_status(degradation)
            })
        
        return performance_data
    
    def _calculate_degradation(
        self,
        minute: int,
        failure_start: int,
        recovery_start: int,
        scenario_config: Dict[str, Any]
    ) -> float:
        """Calculate degradation factor based on failure timeline"""
        if minute < failure_start:
            # Normal operation
            return 0.0
        
        elif minute < recovery_start:
            # Failure progression
            failure_duration = minute - failure_start
            max_degradation = 1.0
            progression_rate = scenario_config["progression_rate"]
            
            # Different progression patterns
            if scenario_config["trigger"] == "high_load":
                # Exponential degradation
                return min(max_degradation, 1 - np.exp(-progression_rate * failure_duration))
            elif scenario_config["trigger"] == "time_based":
                # Linear degradation
                return min(max_degradation, progression_rate * failure_duration)
            else:
                # Sudden degradation
                return max_degradation * 0.8  # Immediate 80% degradation
        
        else:
            # Recovery phase
            recovery_duration = minute - recovery_start
            recovery_rate = 0.1  # 10% recovery per minute
            
            # Exponential recovery
            remaining_degradation = 1.0 * np.exp(-recovery_rate * recovery_duration)
            return max(0.0, remaining_degradation)
    
    def _apply_degradation(
        self,
        base_metrics: Dict[str, float],
        degradation: float,
        scenario_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """Apply degradation to base metrics"""
        degraded_metrics = {}
        impact_multiplier = scenario_config["impact_multiplier"]
        
        for metric_name, base_value in base_metrics.items():
            if metric_name in ["latency_ms", "response_time_ms", "p95_latency_ms"]:
                # Latency increases with degradation
                degraded_metrics[metric_name] = base_value * (1 + degradation * impact_multiplier)
            
            elif metric_name in ["throughput_rps", "success_rate", "availability"]:
                # Throughput/success decreases with degradation
                degraded_metrics[metric_name] = base_value * (1 - degradation * 0.8)
            
            elif metric_name in ["error_rate"]:
                # Error rate increases with degradation
                baseline_error = base_value if base_value > 0 else 0.01
                degraded_metrics[metric_name] = min(0.5, baseline_error * (1 + degradation * impact_multiplier))
            
            elif metric_name in ["memory_mb", "cpu_percent"]:
                # Resource usage may increase
                degraded_metrics[metric_name] = base_value * (1 + degradation * 0.5)
            
            else:
                # Default: no change
                degraded_metrics[metric_name] = base_value
        
        # Add noise for realism
        for metric_name in degraded_metrics:
            noise_factor = random.uniform(0.95, 1.05)
            degraded_metrics[metric_name] *= noise_factor
        
        return degraded_metrics
    
    def _determine_health_status(self, degradation: float) -> str:
        """Determine system health status based on degradation"""
        if degradation < 0.1:
            return "healthy"
        elif degradation < 0.3:
            return "warning"
        elif degradation < 0.7:
            return "critical"
        else:
            return "failing"
    
    def simulate_bottleneck_analysis(
        self,
        service_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Simulate bottleneck analysis across services
        
        Args:
            service_metrics: Metrics for different services
            
        Returns:
            Bottleneck analysis results
        """
        bottleneck_analysis = {
            "identified_bottlenecks": [],
            "performance_scores": {},
            "recommendations": [],
            "impact_analysis": {}
        }
        
        # Analyze each service for bottlenecks
        for service_name, metrics in service_metrics.items():
            performance_score = self._calculate_performance_score(metrics)
            bottleneck_analysis["performance_scores"][service_name] = performance_score
            
            if performance_score < 0.7:
                bottleneck_info = {
                    "service": service_name,
                    "severity": self._classify_severity(performance_score),
                    "primary_issues": self._identify_primary_issues(metrics),
                    "suggested_fixes": self._suggest_fixes(service_name, metrics)
                }
                bottleneck_analysis["identified_bottlenecks"].append(bottleneck_info)
        
        # Generate overall recommendations
        bottleneck_analysis["recommendations"] = self._generate_recommendations(
            bottleneck_analysis["identified_bottlenecks"]
        )
        
        # Impact analysis
        bottleneck_analysis["impact_analysis"] = self._analyze_cascading_impact(
            service_metrics,
            bottleneck_analysis["identified_bottlenecks"]
        )
        
        return bottleneck_analysis
    
    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calculate normalized performance score for a service"""
        score = 1.0
        
        # Latency impact (lower is better)
        if "latency_ms" in metrics:
            latency_penalty = min(0.5, metrics["latency_ms"] / 1000)  # Penalty up to 0.5
            score -= latency_penalty
        
        # Error rate impact (lower is better)
        if "error_rate" in metrics:
            error_penalty = min(0.3, metrics["error_rate"] * 10)  # Penalty up to 0.3
            score -= error_penalty
        
        # CPU usage impact (too high is bad)
        if "cpu_percent" in metrics:
            cpu_penalty = max(0, (metrics["cpu_percent"] - 80) / 100)  # Penalty after 80%
            score -= cpu_penalty
        
        # Memory usage impact
        if "memory_mb" in metrics:
            # Assume 4GB = 4000MB is the limit
            memory_penalty = max(0, (metrics["memory_mb"] - 3200) / 4000)  # Penalty after 80%
            score -= memory_penalty
        
        return max(0.0, min(1.0, score))
    
    def _classify_severity(self, performance_score: float) -> str:
        """Classify bottleneck severity"""
        if performance_score > 0.8:
            return "low"
        elif performance_score > 0.6:
            return "medium"
        elif performance_score > 0.4:
            return "high"
        else:
            return "critical"
    
    def _identify_primary_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Identify primary performance issues from metrics"""
        issues = []
        
        if metrics.get("latency_ms", 0) > 500:
            issues.append("high_latency")
        
        if metrics.get("error_rate", 0) > 0.05:
            issues.append("high_error_rate")
        
        if metrics.get("cpu_percent", 0) > 80:
            issues.append("cpu_bottleneck")
        
        if metrics.get("memory_mb", 0) > 3200:
            issues.append("memory_pressure")
        
        if metrics.get("throughput_rps", float('inf')) < 10:
            issues.append("low_throughput")
        
        return issues
    
    def _suggest_fixes(self, service_name: str, metrics: Dict[str, float]) -> List[str]:
        """Suggest fixes based on identified issues"""
        fixes = []
        
        if metrics.get("cpu_percent", 0) > 80:
            fixes.append("Scale horizontally to reduce CPU load")
            fixes.append("Optimize CPU-intensive operations")
        
        if metrics.get("memory_mb", 0) > 3200:
            fixes.append("Implement memory optimization")
            fixes.append("Check for memory leaks")
        
        if metrics.get("latency_ms", 0) > 500:
            fixes.append("Add caching layer")
            fixes.append("Optimize database queries")
            fixes.append("Review service dependencies")
        
        if metrics.get("error_rate", 0) > 0.05:
            fixes.append("Improve error handling")
            fixes.append("Add circuit breakers")
            fixes.append("Review recent deployments")
        
        return fixes
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Generate overall system recommendations"""
        recommendations = []
        
        critical_bottlenecks = [b for b in bottlenecks if b["severity"] == "critical"]
        if critical_bottlenecks:
            recommendations.append("Address critical bottlenecks immediately")
        
        cpu_issues = [b for b in bottlenecks if "cpu_bottleneck" in b["primary_issues"]]
        if len(cpu_issues) > 1:
            recommendations.append("Consider cluster-wide CPU optimization")
        
        memory_issues = [b for b in bottlenecks if "memory_pressure" in b["primary_issues"]]
        if memory_issues:
            recommendations.append("Implement memory monitoring and alerting")
        
        return recommendations
    
    def _analyze_cascading_impact(
        self,
        service_metrics: Dict[str, Dict[str, float]],
        bottlenecks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze potential cascading impact of bottlenecks"""
        impact_analysis = {
            "risk_level": "low",
            "affected_services": [],
            "cascade_probability": 0.0
        }
        
        if not bottlenecks:
            return impact_analysis
        
        # Calculate cascade probability based on bottleneck severity
        high_severity_count = sum(1 for b in bottlenecks if b["severity"] in ["high", "critical"])
        total_services = len(service_metrics)
        
        cascade_probability = min(0.8, (high_severity_count / total_services) * 1.5)
        impact_analysis["cascade_probability"] = round(cascade_probability, 2)
        
        if cascade_probability > 0.6:
            impact_analysis["risk_level"] = "high"
        elif cascade_probability > 0.3:
            impact_analysis["risk_level"] = "medium"
        
        # Identify potentially affected services
        bottleneck_services = {b["service"] for b in bottlenecks}
        all_services = set(service_metrics.keys())
        impact_analysis["affected_services"] = list(all_services - bottleneck_services)
        
        return impact_analysis