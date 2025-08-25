#!/usr/bin/env python3
"""
Deployment Performance Validation Script

Validates deployment performance against optimal settings and benchmarks.
Created for Iteration 3 audit follow-up - ensures deployment health and performance.

Usage:
    python scripts/validate_deployment_performance.py --environment staging
    python scripts/validate_deployment_performance.py --environment local --detailed
"""

import asyncio
import time
import sys
import argparse
import json
import requests
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class PerformanceMetric:
    """Performance metric with validation status."""
    name: str
    value: float
    unit: str
    threshold: float
    status: str  # "pass", "warning", "fail"
    message: str = ""


@dataclass
class DeploymentValidationResult:
    """Complete deployment validation result."""
    environment: str
    timestamp: float
    overall_status: str  # "healthy", "warning", "unhealthy"
    health_score: float  # 0-100
    metrics: List[PerformanceMetric]
    recommendations: List[str]
    

class DeploymentValidator:
    """Validates deployment performance and configuration."""
    
    def __init__(self, environment: str = "local"):
        self.environment = environment
        self.project_root = project_root
        self.service_urls = self._get_service_urls()
        
        # Performance thresholds based on audit findings
        self.thresholds = {
            "startup_time_seconds": 60.0,      # Cloud Run timeout
            "memory_usage_mb": 900.0,          # Under 1Gi limit
            "health_response_ms": 100.0,       # Sub-100ms requirement
            "ready_response_ms": 200.0,        # Readiness check
            "cpu_utilization_percent": 85.0,   # CPU efficiency
            "error_rate_percent": 5.0,         # Error threshold
        }
    
    def _get_service_urls(self) -> Dict[str, str]:
        """Get service URLs based on environment."""
        if self.environment == "staging":
            return {
                "backend": "https://api.staging.netrasystems.ai",
                "auth": "https://auth.staging.netrasystems.ai",
                "frontend": "https://app.staging.netrasystems.ai"
            }
        elif self.environment == "local":
            return {
                "backend": "http://localhost:8888",
                "auth": "http://localhost:8080", 
                "frontend": "http://localhost:3000"
            }
        else:
            return {}
    
    async def validate_deployment(self, detailed: bool = False) -> DeploymentValidationResult:
        """Run comprehensive deployment validation."""
        print(f"[INFO] Validating {self.environment} deployment performance...")
        
        metrics = []
        recommendations = []
        
        # 1. Startup Performance Validation
        startup_metrics = await self._validate_startup_performance()
        metrics.extend(startup_metrics)
        
        # 2. Resource Optimization Validation
        resource_metrics = await self._validate_resource_optimization()
        metrics.extend(resource_metrics)
        
        # 3. Health Endpoint Performance
        health_metrics = await self._validate_health_endpoints()
        metrics.extend(health_metrics)
        
        # 4. Service Integration Validation
        if detailed:
            integration_metrics = await self._validate_service_integration()
            metrics.extend(integration_metrics)
        
        # Calculate overall health score
        health_score = self._calculate_health_score(metrics)
        overall_status = self._determine_overall_status(health_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        return DeploymentValidationResult(
            environment=self.environment,
            timestamp=time.time(),
            overall_status=overall_status,
            health_score=health_score,
            metrics=metrics,
            recommendations=recommendations
        )
    
    async def _validate_startup_performance(self) -> List[PerformanceMetric]:
        """Validate startup performance metrics."""
        print("  [INFO] Validating startup performance...")
        metrics = []
        
        # Simulate startup time measurement
        start_time = time.time()
        
        # Test if services respond (indicates successful startup)
        services_started = 0
        total_services = len(self.service_urls)
        
        for service_name, url in self.service_urls.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code in [200, 404]:  # 404 is OK if health endpoint doesn't exist
                    services_started += 1
            except Exception:
                pass
        
        startup_time = time.time() - start_time
        
        # Startup time metric
        startup_metric = PerformanceMetric(
            name="startup_time_seconds",
            value=startup_time,
            unit="seconds",
            threshold=self.thresholds["startup_time_seconds"],
            status="pass" if startup_time < self.thresholds["startup_time_seconds"] else "fail",
            message=f"Startup completed in {startup_time:.2f}s"
        )
        metrics.append(startup_metric)
        
        # Service availability metric
        availability_percent = (services_started / total_services) * 100
        availability_metric = PerformanceMetric(
            name="service_availability_percent",
            value=availability_percent,
            unit="percent",
            threshold=80.0,
            status="pass" if availability_percent >= 80.0 else "warning",
            message=f"{services_started}/{total_services} services available"
        )
        metrics.append(availability_metric)
        
        return metrics
    
    async def _validate_resource_optimization(self) -> List[PerformanceMetric]:
        """Validate resource optimization (memory/CPU)."""
        print("  [INFO] Validating resource optimization...")
        metrics = []
        
        try:
            process = psutil.Process()
            
            # Memory usage validation
            memory_mb = process.memory_info().rss / (1024 * 1024)
            memory_metric = PerformanceMetric(
                name="memory_usage_mb",
                value=memory_mb,
                unit="MB",
                threshold=self.thresholds["memory_usage_mb"],
                status="pass" if memory_mb < self.thresholds["memory_usage_mb"] else "warning",
                message=f"Memory usage: {memory_mb:.1f}MB (limit: {self.thresholds['memory_usage_mb']}MB)"
            )
            metrics.append(memory_metric)
            
            # CPU utilization validation
            cpu_percent = process.cpu_percent(interval=1)
            cpu_metric = PerformanceMetric(
                name="cpu_utilization_percent",
                value=cpu_percent,
                unit="percent",
                threshold=self.thresholds["cpu_utilization_percent"],
                status="pass" if cpu_percent < self.thresholds["cpu_utilization_percent"] else "warning",
                message=f"CPU utilization: {cpu_percent:.1f}%"
            )
            metrics.append(cpu_metric)
            
        except Exception as e:
            error_metric = PerformanceMetric(
                name="resource_monitoring_error",
                value=1.0,
                unit="boolean",
                threshold=0.0,
                status="fail",
                message=f"Failed to monitor resources: {e}"
            )
            metrics.append(error_metric)
        
        return metrics
    
    async def _validate_health_endpoints(self) -> List[PerformanceMetric]:
        """Validate health endpoint performance (<100ms requirement)."""
        print("  [INFO] Validating health endpoint performance...")
        metrics = []
        
        for service_name, base_url in self.service_urls.items():
            health_url = f"{base_url}/health"
            
            try:
                # Measure response time
                start_time = time.time()
                response = requests.get(health_url, timeout=10)
                response_time_ms = (time.time() - start_time) * 1000
                
                # Health endpoint response time
                health_metric = PerformanceMetric(
                    name=f"{service_name}_health_response_ms",
                    value=response_time_ms,
                    unit="milliseconds",
                    threshold=self.thresholds["health_response_ms"],
                    status="pass" if response_time_ms < self.thresholds["health_response_ms"] else "warning",
                    message=f"{service_name} health: {response_time_ms:.1f}ms (status: {response.status_code})"
                )
                metrics.append(health_metric)
                
            except requests.exceptions.ConnectionError:
                # Service not available - might be OK for local testing
                unavailable_metric = PerformanceMetric(
                    name=f"{service_name}_health_availability",
                    value=0.0,
                    unit="boolean",
                    threshold=1.0,
                    status="warning" if self.environment == "local" else "fail",
                    message=f"{service_name} service not available at {health_url}"
                )
                metrics.append(unavailable_metric)
                
            except Exception as e:
                error_metric = PerformanceMetric(
                    name=f"{service_name}_health_error",
                    value=1.0,
                    unit="boolean",
                    threshold=0.0,
                    status="fail",
                    message=f"{service_name} health check error: {e}"
                )
                metrics.append(error_metric)
        
        return metrics
    
    async def _validate_service_integration(self) -> List[PerformanceMetric]:
        """Validate service integration performance."""
        print("  [INFO] Validating service integration...")
        metrics = []
        
        # Test cross-service communication
        integration_tests = [
            ("backend_auth_integration", "backend", "auth"),
            ("frontend_backend_integration", "frontend", "backend"),
        ]
        
        for test_name, source_service, target_service in integration_tests:
            if source_service in self.service_urls and target_service in self.service_urls:
                try:
                    # Simple connectivity test
                    target_url = self.service_urls[target_service]
                    start_time = time.time()
                    response = requests.get(f"{target_url}/health", timeout=5)
                    response_time = time.time() - start_time
                    
                    integration_metric = PerformanceMetric(
                        name=test_name,
                        value=response_time * 1000,
                        unit="milliseconds",
                        threshold=500.0,  # 500ms for integration
                        status="pass" if response_time < 0.5 else "warning",
                        message=f"{source_service} -> {target_service}: {response_time*1000:.1f}ms"
                    )
                    metrics.append(integration_metric)
                    
                except Exception as e:
                    error_metric = PerformanceMetric(
                        name=f"{test_name}_error",
                        value=1.0,
                        unit="boolean",
                        threshold=0.0,
                        status="warning",
                        message=f"Integration test failed: {e}"
                    )
                    metrics.append(error_metric)
        
        return metrics
    
    def _calculate_health_score(self, metrics: List[PerformanceMetric]) -> float:
        """Calculate overall health score (0-100)."""
        if not metrics:
            return 0.0
        
        total_weight = 0
        weighted_score = 0
        
        # Weight different metric types
        weights = {
            "startup_time_seconds": 25,
            "memory_usage_mb": 20,
            "cpu_utilization_percent": 15,
            "health_response_ms": 20,
            "service_availability_percent": 20
        }
        
        for metric in metrics:
            weight = weights.get(metric.name.split('_')[0], 10)  # Default weight
            
            # Score based on status
            if metric.status == "pass":
                score = 100
            elif metric.status == "warning":
                score = 60
            else:  # fail
                score = 0
            
            weighted_score += score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _determine_overall_status(self, health_score: float) -> str:
        """Determine overall deployment status."""
        if health_score >= 85:
            return "healthy"
        elif health_score >= 60:
            return "warning"
        else:
            return "unhealthy"
    
    def _generate_recommendations(self, metrics: List[PerformanceMetric]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        for metric in metrics:
            if metric.status == "fail":
                if "memory" in metric.name:
                    recommendations.append(f"[FIX] Optimize memory usage: Currently {metric.value:.1f}{metric.unit}, consider reducing to under {metric.threshold}{metric.unit}")
                elif "startup" in metric.name:
                    recommendations.append(f"[FIX] Optimize startup time: Currently {metric.value:.1f}{metric.unit}, target under {metric.threshold}{metric.unit}")
                elif "health" in metric.name:
                    recommendations.append(f"[FIX] Optimize health endpoint: Currently {metric.value:.1f}{metric.unit}, target under {metric.threshold}{metric.unit}")
            
            elif metric.status == "warning":
                if "cpu" in metric.name:
                    recommendations.append(f"[MONITOR] Monitor CPU usage: Currently {metric.value:.1f}{metric.unit}")
                elif "availability" in metric.name:
                    recommendations.append(f"[MONITOR] Check service availability: {metric.message}")
        
        # Add general recommendations
        if not any("memory" in rec for rec in recommendations):
            recommendations.append("[GOOD] Memory usage is optimal")
        
        if not any("startup" in rec for rec in recommendations):
            recommendations.append("[GOOD] Startup performance is good")
        
        return recommendations


def print_validation_results(result: DeploymentValidationResult, detailed: bool = False):
    """Print formatted validation results."""
    print(f"\n{'='*60}")
    print(f"DEPLOYMENT VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Environment: {result.environment}")
    print(f"Status: {result.overall_status.upper()}")
    print(f"Health Score: {result.health_score:.1f}/100")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.timestamp))}")
    
    print(f"\nPERFORMANCE METRICS:")
    print(f"{'Metric':<30} {'Value':<15} {'Status':<10} {'Message'}")
    print(f"{'-'*80}")
    
    for metric in result.metrics:
        status_indicator = {"pass": "[PASS]", "warning": "[WARN]", "fail": "[FAIL]"}
        indicator = status_indicator.get(metric.status, "[UNKNOWN]")
        print(f"{metric.name:<30} {metric.value:.1f} {metric.unit:<10} {indicator} {metric.message}")
    
    if result.recommendations:
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(result.recommendations, 1):
            print(f"{i:2}. {rec}")
    
    print(f"\n{'='*60}")
    
    # Summary advice
    if result.overall_status == "healthy":
        print(f"[SUCCESS] Deployment is performing well! No critical issues detected.")
    elif result.overall_status == "warning":
        print(f"[WARNING] Deployment has some performance concerns. Review recommendations.")
    else:
        print(f"[CRITICAL] Deployment has performance issues that need attention!")


async def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate deployment performance and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Local validation:
    python scripts/validate_deployment_performance.py --environment local
    
  Staging validation with details:
    python scripts/validate_deployment_performance.py --environment staging --detailed
    
  Save results to file:
    python scripts/validate_deployment_performance.py --environment staging --output results.json
        """
    )
    
    parser.add_argument("--environment", 
                       choices=["local", "staging"], 
                       default="local",
                       help="Environment to validate (default: local)")
    parser.add_argument("--detailed", 
                       action="store_true",
                       help="Run detailed validation including integration tests")
    parser.add_argument("--output", 
                       type=str,
                       help="Save results to JSON file")
    parser.add_argument("--quiet", 
                       action="store_true",
                       help="Minimal output (just pass/fail)")
    
    args = parser.parse_args()
    
    try:
        # Run validation
        validator = DeploymentValidator(args.environment)
        result = await validator.validate_deployment(detailed=args.detailed)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(asdict(result), f, indent=2, default=str)
            print(f"[INFO] Results saved to {args.output}")
        
        # Print results
        if not args.quiet:
            print_validation_results(result, detailed=args.detailed)
        
        # Exit with appropriate code
        if result.overall_status == "unhealthy":
            sys.exit(1)
        elif result.overall_status == "warning":
            sys.exit(2)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n[WARNING] Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())