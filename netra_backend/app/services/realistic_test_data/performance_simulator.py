"""Performance Simulator

This module simulates performance patterns including cascading failures and bottlenecks.
"""

import random
from datetime import datetime, timezone
from typing import Any, Dict, List

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
        scenario_config = self._get_scenario_config(scenario)
        failure_timeline = self._get_failure_timeline(scenario_config)
        current_time = datetime.now(timezone.utc)
        return self._generate_performance_data(
            base_metrics, scenario, scenario_config, failure_timeline, 
            current_time, duration_minutes
        )
    
    def _get_scenario_config(self, scenario: str) -> Dict[str, Any]:
        """Get scenario configuration with fallback"""
        return self.failure_scenarios.get(
            scenario,
            self.failure_scenarios["cascading_failure"]
        )
    
    def _get_failure_timeline(self, scenario_config: Dict[str, Any]) -> Dict[str, int]:
        """Get failure timeline points"""
        failure_start = random.randint(10, 20)
        recovery_start = failure_start + scenario_config["recovery_time_minutes"]
        return {"failure_start": failure_start, "recovery_start": recovery_start}
    
    def _generate_performance_data(
        self, base_metrics: Dict[str, float], scenario: str,
        scenario_config: Dict[str, Any], failure_timeline: Dict[str, int],
        current_time: datetime, duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Generate complete performance data for simulation"""
        performance_data = []
        for minute in range(duration_minutes):
            data_point = self._create_data_point(
                minute, base_metrics, scenario, scenario_config,
                failure_timeline, current_time
            )
            performance_data.append(data_point)
        return performance_data
    
    def _create_data_point(
        self, minute: int, base_metrics: Dict[str, float], scenario: str,
        scenario_config: Dict[str, Any], failure_timeline: Dict[str, int],
        current_time: datetime
    ) -> Dict[str, Any]:
        """Create single performance data point"""
        timestamp = self._calculate_timestamp(current_time, minute)
        degradation = self._calculate_degradation(
            minute, failure_timeline["failure_start"], 
            failure_timeline["recovery_start"], scenario_config
        )
        degraded_metrics = self._apply_degradation(
            base_metrics, degradation, scenario_config
        )
        return {
            "timestamp": timestamp.isoformat(),
            "minute": minute,
            "degradation_factor": degradation,
            "scenario": scenario,
            "metrics": degraded_metrics,
            "health_status": self._determine_health_status(degradation)
        }
    
    def _calculate_timestamp(self, current_time: datetime, minute: int) -> datetime:
        """Calculate timestamp for given minute offset"""
        return current_time.replace(
            minute=(current_time.minute + minute) % 60,
            hour=current_time.hour + (current_time.minute + minute) // 60
        )
    
    def _calculate_degradation(
        self,
        minute: int,
        failure_start: int,
        recovery_start: int,
        scenario_config: Dict[str, Any]
    ) -> float:
        """Calculate degradation factor based on failure timeline"""
        if minute < failure_start:
            return 0.0
        elif minute < recovery_start:
            return self._calculate_failure_degradation(
                minute, failure_start, scenario_config
            )
        else:
            return self._calculate_recovery_degradation(
                minute, recovery_start
            )
    
    def _calculate_failure_degradation(
        self, minute: int, failure_start: int, scenario_config: Dict[str, Any]
    ) -> float:
        """Calculate degradation during failure phase"""
        failure_duration = minute - failure_start
        max_degradation = 1.0
        progression_rate = scenario_config["progression_rate"]
        
        if scenario_config["trigger"] == "high_load":
            return min(max_degradation, 1 - np.exp(-progression_rate * failure_duration))
        elif scenario_config["trigger"] == "time_based":
            return min(max_degradation, progression_rate * failure_duration)
        else:
            return max_degradation * 0.8
    
    def _calculate_recovery_degradation(self, minute: int, recovery_start: int) -> float:
        """Calculate degradation during recovery phase"""
        recovery_duration = minute - recovery_start
        recovery_rate = 0.1
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
            degraded_metrics[metric_name] = self._apply_metric_degradation(
                metric_name, base_value, degradation, impact_multiplier
            )
        
        return self._add_realistic_noise(degraded_metrics)
    
    def _apply_metric_degradation(
        self, metric_name: str, base_value: float, 
        degradation: float, impact_multiplier: float
    ) -> float:
        """Apply degradation to specific metric type"""
        if metric_name in ["latency_ms", "response_time_ms", "p95_latency_ms"]:
            return base_value * (1 + degradation * impact_multiplier)
        elif metric_name in ["throughput_rps", "success_rate", "availability"]:
            return base_value * (1 - degradation * 0.8)
        elif metric_name in ["error_rate"]:
            return self._calculate_error_rate_degradation(
                base_value, degradation, impact_multiplier
            )
        elif metric_name in ["memory_mb", "cpu_percent"]:
            return base_value * (1 + degradation * 0.5)
        else:
            return base_value
    
    def _calculate_error_rate_degradation(
        self, base_value: float, degradation: float, impact_multiplier: float
    ) -> float:
        """Calculate error rate degradation with baseline handling"""
        baseline_error = base_value if base_value > 0 else 0.01
        return min(0.5, baseline_error * (1 + degradation * impact_multiplier))
    
    def _add_realistic_noise(self, degraded_metrics: Dict[str, float]) -> Dict[str, float]:
        """Add realistic noise to degraded metrics"""
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
        bottleneck_analysis = self._initialize_bottleneck_analysis()
        self._analyze_service_metrics(service_metrics, bottleneck_analysis)
        bottleneck_analysis["recommendations"] = self._generate_recommendations(
            bottleneck_analysis["identified_bottlenecks"]
        )
        bottleneck_analysis["impact_analysis"] = self._analyze_cascading_impact(
            service_metrics, bottleneck_analysis["identified_bottlenecks"]
        )
        return bottleneck_analysis
    
    def _initialize_bottleneck_analysis(self) -> Dict[str, Any]:
        """Initialize bottleneck analysis structure"""
        return {
            "identified_bottlenecks": [],
            "performance_scores": {},
            "recommendations": [],
            "impact_analysis": {}
        }
    
    def _analyze_service_metrics(
        self, service_metrics: Dict[str, Dict[str, float]], 
        bottleneck_analysis: Dict[str, Any]
    ) -> None:
        """Analyze each service's metrics for bottlenecks"""
        for service_name, metrics in service_metrics.items():
            performance_score = self._calculate_performance_score(metrics)
            bottleneck_analysis["performance_scores"][service_name] = performance_score
            
            if performance_score < 0.7:
                bottleneck_info = self._create_bottleneck_info(
                    service_name, metrics, performance_score
                )
                bottleneck_analysis["identified_bottlenecks"].append(bottleneck_info)
    
    def _create_bottleneck_info(
        self, service_name: str, metrics: Dict[str, float], 
        performance_score: float
    ) -> Dict[str, Any]:
        """Create bottleneck information structure"""
        return {
            "service": service_name,
            "severity": self._classify_severity(performance_score),
            "primary_issues": self._identify_primary_issues(metrics),
            "suggested_fixes": self._suggest_fixes(service_name, metrics)
        }
    
    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calculate normalized performance score for a service"""
        score = 1.0
        score -= self._calculate_latency_penalty(metrics)
        score -= self._calculate_error_penalty(metrics)
        score -= self._calculate_cpu_penalty(metrics)
        score -= self._calculate_memory_penalty(metrics)
        return max(0.0, min(1.0, score))
    
    def _calculate_latency_penalty(self, metrics: Dict[str, float]) -> float:
        """Calculate latency penalty component"""
        if "latency_ms" in metrics:
            return min(0.5, metrics["latency_ms"] / 1000)
        return 0.0
    
    def _calculate_error_penalty(self, metrics: Dict[str, float]) -> float:
        """Calculate error rate penalty component"""
        if "error_rate" in metrics:
            return min(0.3, metrics["error_rate"] * 10)
        return 0.0
    
    def _calculate_cpu_penalty(self, metrics: Dict[str, float]) -> float:
        """Calculate CPU usage penalty component"""
        if "cpu_percent" in metrics:
            return max(0, (metrics["cpu_percent"] - 80) / 100)
        return 0.0
    
    def _calculate_memory_penalty(self, metrics: Dict[str, float]) -> float:
        """Calculate memory usage penalty component"""
        if "memory_mb" in metrics:
            return max(0, (metrics["memory_mb"] - 3200) / 4000)
        return 0.0
    
    def _classify_severity(self, performance_score: float) -> str:
        """Classify bottleneck severity"""
        if performance_score > 0.8:
            return "low"
        elif performance_score > 0.6:
            return "medium"
        elif performance_score > 0.4:
            return "high"
        return "critical"
    
    def _identify_primary_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Identify primary performance issues from metrics"""
        issues = []
        issues.extend(self._check_latency_issues(metrics))
        issues.extend(self._check_error_issues(metrics))
        issues.extend(self._check_resource_issues(metrics))
        issues.extend(self._check_throughput_issues(metrics))
        return issues
    
    def _check_latency_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Check for latency-related issues"""
        if metrics.get("latency_ms", 0) > 500:
            return ["high_latency"]
        return []
    
    def _check_error_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Check for error-related issues"""
        if metrics.get("error_rate", 0) > 0.05:
            return ["high_error_rate"]
        return []
    
    def _check_resource_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Check for resource-related issues"""
        issues = []
        if metrics.get("cpu_percent", 0) > 80:
            issues.append("cpu_bottleneck")
        if metrics.get("memory_mb", 0) > 3200:
            issues.append("memory_pressure")
        return issues
    
    def _check_throughput_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Check for throughput-related issues"""
        if metrics.get("throughput_rps", float('inf')) < 10:
            return ["low_throughput"]
        return []
    
    def _suggest_fixes(self, service_name: str, metrics: Dict[str, float]) -> List[str]:
        """Suggest fixes based on identified issues"""
        fixes = []
        fixes.extend(self._get_cpu_fixes(metrics))
        fixes.extend(self._get_memory_fixes(metrics))
        fixes.extend(self._get_latency_fixes(metrics))
        fixes.extend(self._get_error_fixes(metrics))
        return fixes
    
    def _get_cpu_fixes(self, metrics: Dict[str, float]) -> List[str]:
        """Get CPU-related fixes"""
        if metrics.get("cpu_percent", 0) > 80:
            return [
                "Scale horizontally to reduce CPU load",
                "Optimize CPU-intensive operations"
            ]
        return []
    
    def _get_memory_fixes(self, metrics: Dict[str, float]) -> List[str]:
        """Get memory-related fixes"""
        if metrics.get("memory_mb", 0) > 3200:
            return [
                "Implement memory optimization",
                "Check for memory leaks"
            ]
        return []
    
    def _get_latency_fixes(self, metrics: Dict[str, float]) -> List[str]:
        """Get latency-related fixes"""
        if metrics.get("latency_ms", 0) <= 500:
            return []
        return [
            "Add caching layer",
            "Optimize database queries",
            "Review service dependencies"
        ]
    
    def _get_error_fixes(self, metrics: Dict[str, float]) -> List[str]:
        """Get error-related fixes"""
        if metrics.get("error_rate", 0) <= 0.05:
            return []
        return [
            "Improve error handling",
            "Add circuit breakers",
            "Review recent deployments"
        ]
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Generate overall system recommendations"""
        recommendations = []
        recommendations.extend(self._get_critical_recommendations(bottlenecks))
        recommendations.extend(self._get_cpu_cluster_recommendations(bottlenecks))
        recommendations.extend(self._get_memory_cluster_recommendations(bottlenecks))
        return recommendations
    
    def _get_critical_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Get critical bottleneck recommendations"""
        critical_bottlenecks = [b for b in bottlenecks if b["severity"] == "critical"]
        if critical_bottlenecks:
            return ["Address critical bottlenecks immediately"]
        return []
    
    def _get_cpu_cluster_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Get CPU cluster recommendations"""
        cpu_issues = [b for b in bottlenecks if "cpu_bottleneck" in b["primary_issues"]]
        if len(cpu_issues) > 1:
            return ["Consider cluster-wide CPU optimization"]
        return []
    
    def _get_memory_cluster_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Get memory cluster recommendations"""
        memory_issues = [b for b in bottlenecks if "memory_pressure" in b["primary_issues"]]
        if memory_issues:
            return ["Implement memory monitoring and alerting"]
        return []
    
    def _analyze_cascading_impact(
        self,
        service_metrics: Dict[str, Dict[str, float]],
        bottlenecks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze potential cascading impact of bottlenecks"""
        impact_analysis = self._initialize_impact_analysis()
        if not bottlenecks:
            return impact_analysis
        
        cascade_probability = self._calculate_cascade_probability(
            bottlenecks, len(service_metrics)
        )
        impact_analysis["cascade_probability"] = round(cascade_probability, 2)
        impact_analysis["risk_level"] = self._determine_risk_level(cascade_probability)
        impact_analysis["affected_services"] = self._identify_affected_services(
            service_metrics, bottlenecks
        )
        return impact_analysis
    
    def _initialize_impact_analysis(self) -> Dict[str, Any]:
        """Initialize impact analysis structure"""
        return {
            "risk_level": "low",
            "affected_services": [],
            "cascade_probability": 0.0
        }
    
    def _calculate_cascade_probability(
        self, bottlenecks: List[Dict[str, Any]], total_services: int
    ) -> float:
        """Calculate cascade probability from bottlenecks"""
        high_severity_count = sum(
            1 for b in bottlenecks if b["severity"] in ["high", "critical"]
        )
        return min(0.8, (high_severity_count / total_services) * 1.5)
    
    def _determine_risk_level(self, cascade_probability: float) -> str:
        """Determine risk level from cascade probability"""
        if cascade_probability > 0.6:
            return "high"
        elif cascade_probability > 0.3:
            return "medium"
        return "low"
    
    def _identify_affected_services(
        self, service_metrics: Dict[str, Dict[str, float]], 
        bottlenecks: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify potentially affected services"""
        bottleneck_services = {b["service"] for b in bottlenecks}
        all_services = set(service_metrics.keys())
        return list(all_services - bottleneck_services)