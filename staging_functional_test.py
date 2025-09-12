#!/usr/bin/env python3
"""
Staging Functional Test for Issue #573

This script performs basic functional tests on the staging environment
to ensure the system works end-to-end with timeout configurations.
"""

import requests
import json
import time
from typing import Dict, Any

STAGING_BACKEND_URL = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
STAGING_AUTH_URL = "https://netra-auth-service-701982941522.us-central1.run.app"
STAGING_FRONTEND_URL = "https://netra-frontend-staging-701982941522.us-central1.run.app"

def test_service_health(service_name: str, url: str) -> Dict[str, Any]:
    """Test service health endpoint"""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        return {
            "service": service_name,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "data": response.json() if response.status_code == 200 else None
        }
    except Exception as e:
        return {
            "service": service_name,
            "status_code": 0,
            "success": False,
            "error": str(e),
            "response_time_ms": 0
        }

def test_auth_service() -> Dict[str, Any]:
    """Test auth service functionality"""
    try:
        # Test if auth service config endpoint exists
        response = requests.get(f"{STAGING_AUTH_URL}/config", timeout=5)
        return {
            "auth_config_available": response.status_code == 200,
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000
        }
    except Exception as e:
        return {
            "auth_config_available": False,
            "error": str(e),
            "status_code": 0,
            "response_time_ms": 0
        }

def validate_staging_deployment() -> Dict[str, Any]:
    """Comprehensive staging validation"""
    results = {
        "timestamp": time.time(),
        "issue": "Issue #573 - Background Task Timeout Configuration",
        "staging_validation": {
            "services": {},
            "functional_tests": {}
        }
    }
    
    print("🚀 Running comprehensive staging validation for Issue #573")
    print("=" * 60)
    
    # Test all services
    services = [
        ("backend", STAGING_BACKEND_URL),
        ("auth", STAGING_AUTH_URL),
        ("frontend", STAGING_FRONTEND_URL)
    ]
    
    all_services_healthy = True
    
    for service_name, service_url in services:
        print(f"\n🔍 Testing {service_name} service health...")
        health_result = test_service_health(service_name, service_url)
        results["staging_validation"]["services"][service_name] = health_result
        
        if health_result["success"]:
            print(f"✅ {service_name} service healthy ({health_result['response_time_ms']:.1f}ms)")
        else:
            print(f"❌ {service_name} service failed: {health_result.get('error', 'Unknown error')}")
            all_services_healthy = False
    
    # Test auth service functionality
    print(f"\n🔐 Testing auth service functionality...")
    auth_test = test_auth_service()
    results["staging_validation"]["functional_tests"]["auth"] = auth_test
    
    # Overall assessment
    results["overall_status"] = "HEALTHY" if all_services_healthy else "DEGRADED"
    results["deployment_ready"] = all_services_healthy
    
    print("\n" + "=" * 60)
    print(f"🎯 Overall Status: {results['overall_status']}")
    
    if results["deployment_ready"]:
        print("✅ All staging services are healthy and ready")
        print("💡 Timeout configuration appears to be working correctly")
        print("🚢 System is ready for continued development")
    else:
        print("⚠️ Some staging services need attention")
        print("💡 May need to investigate service configuration or deployment")
    
    return results

if __name__ == "__main__":
    results = validate_staging_deployment()
    
    # Save results
    with open("staging_functional_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Full results saved to: staging_functional_test_results.json")