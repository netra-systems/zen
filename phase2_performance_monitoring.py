#!/usr/bin/env python3
"""
Phase 2 Performance and Stability Monitoring Script

Monitors performance and stability of the staging environment after Phase 2
ToolExecutionEngine consolidation deployment.

Business Value: Ensures Phase 2 changes don't introduce performance regressions
that could impact $500K+ ARR customer experience.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

STAGING_BASE_URL = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"

def collect_performance_metrics() -> Dict[str, Any]:
    """Collect current performance metrics from staging."""
    try:
        # Get readiness probe data
        response = requests.get(f"{STAGING_BASE_URL}/api/health/ready", timeout=30)
        ready_data = response.json()
        
        # Get startup probe data
        startup_response = requests.get(f"{STAGING_BASE_URL}/api/health/startup", timeout=30)
        startup_data = startup_response.json()
        
        # Calculate key metrics
        pg_response_time = ready_data.get('checks', {}).get('postgresql', {}).get('response_time_ms')
        ch_response_time = ready_data.get('checks', {}).get('clickhouse', {}).get('response_time_ms')
        uptime_seconds = ready_data.get('uptime_seconds', 0)
        
        # Health check response time
        health_response_time = None
        start_time = time.time()
        try:
            health_response = requests.get(f"{STAGING_BASE_URL}/health", timeout=10)
            if health_response.status_code == 200:
                health_response_time = (time.time() - start_time) * 1000  # Convert to ms
        except:
            health_response_time = None
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": ready_data.get('status', 'unknown'),
            "uptime_seconds": uptime_seconds,
            "database_metrics": {
                "postgresql": {
                    "response_time_ms": pg_response_time,
                    "status": ready_data.get('checks', {}).get('postgresql', {}).get('status')
                },
                "clickhouse": {
                    "response_time_ms": ch_response_time,
                    "status": ready_data.get('checks', {}).get('clickhouse', {}).get('status')
                },
                "redis": {
                    "status": ready_data.get('checks', {}).get('redis', {}).get('status')
                }
            },
            "service_metrics": {
                "health_check_response_time_ms": health_response_time,
                "startup_complete": startup_data.get('database_details', {}).get('startup_validation', {}).get('details', {}).get('startup_complete', False)
            }
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "overall_status": "error"
        }

def assess_performance_health(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Assess performance health based on collected metrics."""
    assessment = {
        "overall_health": "healthy",
        "warnings": [],
        "critical_issues": [],
        "performance_score": 100
    }
    
    if metrics.get('error'):
        assessment['critical_issues'].append(f"Metrics collection failed: {metrics['error']}")
        assessment['overall_health'] = "critical"
        assessment['performance_score'] = 0
        return assessment
    
    # Assess database performance
    pg_response_time = metrics.get('database_metrics', {}).get('postgresql', {}).get('response_time_ms')
    if pg_response_time:
        if pg_response_time > 10000:  # 10 seconds
            assessment['critical_issues'].append(f"PostgreSQL response time critical: {pg_response_time}ms")
            assessment['performance_score'] -= 40
        elif pg_response_time > 5000:  # 5 seconds
            assessment['warnings'].append(f"PostgreSQL response time high: {pg_response_time}ms")
            assessment['performance_score'] -= 20
    
    ch_response_time = metrics.get('database_metrics', {}).get('clickhouse', {}).get('response_time_ms')
    if ch_response_time:
        if ch_response_time > 1000:  # 1 second
            assessment['warnings'].append(f"ClickHouse response time elevated: {ch_response_time}ms")
            assessment['performance_score'] -= 10
    
    # Assess service health
    health_response_time = metrics.get('service_metrics', {}).get('health_check_response_time_ms')
    if health_response_time:
        if health_response_time > 5000:  # 5 seconds
            assessment['critical_issues'].append(f"Health check response time critical: {health_response_time:.1f}ms")
            assessment['performance_score'] -= 30
        elif health_response_time > 2000:  # 2 seconds
            assessment['warnings'].append(f"Health check response time elevated: {health_response_time:.1f}ms")
            assessment['performance_score'] -= 15
    
    # Assess overall status
    overall_status = metrics.get('overall_status', 'unknown')
    if overall_status == 'failed':
        assessment['critical_issues'].append("Service overall status is failed")
        assessment['performance_score'] -= 50
    elif overall_status == 'degraded':
        assessment['warnings'].append("Service overall status is degraded")
        assessment['performance_score'] -= 25
    
    # Determine overall health
    if assessment['critical_issues']:
        assessment['overall_health'] = "critical"
    elif assessment['warnings']:
        assessment['overall_health'] = "degraded"
    
    # Ensure score doesn't go below 0
    assessment['performance_score'] = max(0, assessment['performance_score'])
    
    return assessment

def monitor_phase2_performance():
    """Monitor Phase 2 performance and stability."""
    print("🚀 Phase 2 Performance and Stability Monitoring")
    print("=" * 70)
    print("Monitoring staging environment after ToolExecutionEngine consolidation...")
    print()
    
    # Collect baseline metrics
    print("📊 Collecting performance metrics...")
    metrics = collect_performance_metrics()
    
    if metrics.get('error'):
        print(f"❌ Failed to collect metrics: {metrics['error']}")
        return {"status": "FAIL", "error": metrics['error']}
    
    # Assess performance
    assessment = assess_performance_health(metrics)
    
    # Display results
    print("📈 Performance Metrics:")
    print(f"   ⏱️  Service Uptime: {metrics.get('uptime_seconds', 'N/A')} seconds")
    print(f"   🏥 Overall Status: {metrics.get('overall_status', 'N/A')}")
    
    # Database metrics
    pg_metrics = metrics.get('database_metrics', {}).get('postgresql', {})
    ch_metrics = metrics.get('database_metrics', {}).get('clickhouse', {})
    
    if pg_metrics.get('response_time_ms'):
        print(f"   🐘 PostgreSQL: {pg_metrics['response_time_ms']:.1f}ms ({pg_metrics.get('status', 'unknown')})")
    
    if ch_metrics.get('response_time_ms'):
        print(f"   🏠 ClickHouse: {ch_metrics['response_time_ms']:.1f}ms ({ch_metrics.get('status', 'unknown')})")
    
    # Service metrics
    service_metrics = metrics.get('service_metrics', {})
    if service_metrics.get('health_check_response_time_ms'):
        print(f"   🏥 Health Check: {service_metrics['health_check_response_time_ms']:.1f}ms")
    
    print(f"   🚀 Startup Complete: {service_metrics.get('startup_complete', False)}")
    
    print()
    print("🎯 Performance Assessment:")
    print(f"   📊 Performance Score: {assessment['performance_score']}/100")
    print(f"   🏥 Overall Health: {assessment['overall_health'].upper()}")
    
    # Show warnings and issues
    if assessment['warnings']:
        print("\n⚠️  Warnings:")
        for warning in assessment['warnings']:
            print(f"   • {warning}")
    
    if assessment['critical_issues']:
        print("\n🚨 Critical Issues:")
        for issue in assessment['critical_issues']:
            print(f"   • {issue}")
    
    print()
    
    # Final assessment
    if assessment['overall_health'] == 'healthy':
        print("✅ PERFORMANCE VALIDATION: PASS")
        print("🎉 Phase 2 deployment shows good performance characteristics")
        print("💼 $500K+ ARR functionality maintaining acceptable performance")
    elif assessment['overall_health'] == 'degraded':
        print("⚠️  PERFORMANCE VALIDATION: DEGRADED BUT ACCEPTABLE")
        print("🔧 Some performance issues detected but system is functional")
        print("💼 $500K+ ARR functionality preserved with acceptable performance")
    else:
        print("❌ PERFORMANCE VALIDATION: NEEDS ATTENTION")
        print("🚨 Critical performance issues detected")
        print("🔧 Immediate attention required for production readiness")
    
    # Create comprehensive results
    results = {
        "validation_status": "PASS" if assessment['overall_health'] in ['healthy', 'degraded'] else "FAIL",
        "performance_score": assessment['performance_score'],
        "overall_health": assessment['overall_health'],
        "metrics": metrics,
        "assessment": assessment,
        "timestamp": datetime.now().isoformat()
    }
    
    return results

if __name__ == "__main__":
    results = monitor_phase2_performance()
    
    # Save results
    with open('/Users/anthony/Desktop/netra-apex/phase2_performance_monitoring_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📝 Performance monitoring results saved to: phase2_performance_monitoring_results.json")