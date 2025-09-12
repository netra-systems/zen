"""
Issue #586: Service Availability Audit Test
==========================================

This test audits service availability to identify missing or failed services
that could be causing 503 errors and WebSocket connection failures.

Execution: Python-only (no Docker dependency)
Target: All key staging services
Focus: Service discovery, health checks, and dependency validation
"""

import asyncio
import httpx
import pytest
import time
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Try different import patterns for IsolatedEnvironment
try:
    from shared.isolated_environment import IsolatedEnvironment
except ImportError:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
        from isolated_environment import IsolatedEnvironment
    except ImportError:
        # Fallback - create a minimal stub for IsolatedEnvironment
        class IsolatedEnvironment:
            def __init__(self):
                pass


class ServiceAvailabilityAuditTest:
    """Audit service availability to identify missing or failed services."""
    
    def __init__(self):
        """Initialize test with staging environment configuration."""
        self.env = IsolatedEnvironment()
        self.staging_base_url = "https://api.staging.netrasystems.ai"
        self.test_results = []
        self.service_issues = []
        
        # Define critical service endpoints to audit
        self.critical_services = {
            "backend_health": "/health",
            "backend_ready": "/health/ready", 
            "backend_live": "/health/live",
            "api_status": "/api/v1/health",
            "auth_health": "/api/v1/auth/health",
            "agents_status": "/api/v1/agents",
            "websocket_endpoint": "/api/v1/websocket",
            "cors_preflight": "/api/v1/health"  # For CORS testing
        }
        
        # Define expected service dependencies
        self.service_dependencies = {
            "database": ["PostgreSQL", "Redis", "ClickHouse"],
            "external_apis": ["OpenAI", "Anthropic"],
            "infrastructure": ["Load Balancer", "Cloud Run", "VPC"]
        }
        
    async def test_critical_service_availability(self) -> Dict[str, Any]:
        """
        EXPECTED TO FIND ISSUES: Audit all critical services for availability.
        
        This test is designed to identify missing or failed services
        that could be causing Issue #586.
        """
        print("\n🔍 AUDITING: Critical Service Availability")
        print("=" * 60)
        
        test_result = {
            "test_name": "critical_service_availability_audit",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "purpose": "Audit critical services for Issue #586 root cause",
            "services_checked": 0,
            "services_healthy": 0,
            "services_failed": 0,
            "failed_services": [],
            "evidence": {}
        }
        
        service_results = {}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service_name, endpoint in self.critical_services.items():
                test_result["services_checked"] += 1
                start_time = time.time()
                
                try:
                    print(f"Checking {service_name}: {self.staging_base_url}{endpoint}")
                    
                    if service_name == "cors_preflight":
                        # Test CORS preflight for WebSocket setup
                        response = await client.options(
                            f"{self.staging_base_url}{endpoint}",
                            headers={
                                "Origin": "https://staging.netrasystems.ai",
                                "Access-Control-Request-Method": "GET",
                                "Access-Control-Request-Headers": "Authorization"
                            }
                        )
                    else:
                        response = await client.get(f"{self.staging_base_url}{endpoint}")
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    service_result = {
                        "status_code": response.status_code,
                        "response_time_ms": round(response_time, 2),
                        "headers": dict(response.headers),
                        "content_length": len(response.content),
                        "healthy": response.status_code < 500
                    }
                    
                    if response.status_code < 500:
                        test_result["services_healthy"] += 1
                        print(f"  ✅ HEALTHY: {response.status_code} ({response_time:.1f}ms)")
                    else:
                        test_result["services_failed"] += 1
                        test_result["failed_services"].append(service_name)
                        service_result["error"] = f"HTTP {response.status_code}"
                        print(f"  ❌ FAILED: {response.status_code} ({response_time:.1f}ms)")
                        self.service_issues.append(f"{service_name}_http_{response.status_code}")
                        
                    service_results[service_name] = service_result
                    
                except httpx.TimeoutException:
                    test_result["services_failed"] += 1
                    test_result["failed_services"].append(service_name)
                    service_result = {
                        "status_code": None,
                        "error": "Timeout",
                        "healthy": False
                    }
                    service_results[service_name] = service_result
                    print(f"  ❌ TIMEOUT: {service_name}")
                    self.service_issues.append(f"{service_name}_timeout")
                    
                except httpx.ConnectError as e:
                    test_result["services_failed"] += 1
                    test_result["failed_services"].append(service_name)
                    service_result = {
                        "status_code": None,
                        "error": f"Connection failed: {str(e)}",
                        "healthy": False
                    }
                    service_results[service_name] = service_result
                    print(f"  ❌ CONNECTION ERROR: {service_name} - {str(e)}")
                    self.service_issues.append(f"{service_name}_connection_error")
                    
                except Exception as e:
                    test_result["services_failed"] += 1
                    test_result["failed_services"].append(service_name)
                    service_result = {
                        "status_code": None,
                        "error": f"Unexpected error: {str(e)}",
                        "healthy": False
                    }
                    service_results[service_name] = service_result
                    print(f"  ❌ ERROR: {service_name} - {str(e)}")
                    self.service_issues.append(f"{service_name}_unexpected_error")
                    
                await asyncio.sleep(0.1)  # Brief delay between requests
        
        # Calculate service health percentage
        health_percentage = (test_result["services_healthy"] / test_result["services_checked"]) * 100
        test_result.update({
            "service_health_percentage": round(health_percentage, 1),
            "service_results": service_results,
            "overall_assessment": "HEALTHY" if health_percentage >= 80 else "DEGRADED" if health_percentage >= 60 else "CRITICAL"
        })
        
        print(f"\n📊 SERVICE AVAILABILITY SUMMARY:")
        print(f"Total Services Checked: {test_result['services_checked']}")
        print(f"Healthy Services: {test_result['services_healthy']}")
        print(f"Failed Services: {test_result['services_failed']}")
        print(f"Health Percentage: {health_percentage:.1f}%")
        print(f"Overall Assessment: {test_result['overall_assessment']}")
        
        if test_result["failed_services"]:
            print(f"Failed Services: {', '.join(test_result['failed_services'])}")
        
        self.test_results.append(test_result)
        return test_result
    
    async def test_service_dependency_health(self) -> Dict[str, Any]:
        """
        EXPECTED TO FIND ISSUES: Audit service dependencies for missing components.
        """
        print("\n🔍 AUDITING: Service Dependencies")
        print("=" * 60)
        
        test_result = {
            "test_name": "service_dependency_health_audit",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "purpose": "Check for missing service dependencies",
            "dependency_categories": len(self.service_dependencies),
            "total_dependencies": sum(len(deps) for deps in self.service_dependencies.values()),
            "healthy_dependencies": 0,
            "failed_dependencies": 0,
            "missing_dependencies": [],
            "evidence": {}
        }
        
        # Test backend health with detailed dependency information
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                health_response = await client.get(f"{self.staging_base_url}/health?details=true")
                
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    print(f"Backend Health Response: {health_data}")
                    
                    # Analyze health response for dependency information
                    if "dependencies" in health_data:
                        dependencies = health_data["dependencies"]
                        for category, expected_deps in self.service_dependencies.items():
                            for dep in expected_deps:
                                dep_key = dep.lower().replace(" ", "_")
                                if dep_key in dependencies:
                                    status = dependencies[dep_key]
                                    if isinstance(status, dict) and status.get("healthy", False):
                                        test_result["healthy_dependencies"] += 1
                                        print(f"  ✅ {dep}: {status}")
                                    else:
                                        test_result["failed_dependencies"] += 1
                                        test_result["missing_dependencies"].append(dep)
                                        print(f"  ❌ {dep}: {status}")
                                        self.service_issues.append(f"dependency_{dep_key}_failed")
                                else:
                                    test_result["failed_dependencies"] += 1
                                    test_result["missing_dependencies"].append(dep)
                                    print(f"  ⚠️  {dep}: Not reported in health check")
                                    self.service_issues.append(f"dependency_{dep_key}_missing")
                    else:
                        print("  ⚠️  No dependency information in health response")
                        # Assume all dependencies are missing
                        for category, deps in self.service_dependencies.items():
                            for dep in deps:
                                test_result["failed_dependencies"] += 1
                                test_result["missing_dependencies"].append(dep)
                                self.service_issues.append(f"dependency_{dep.lower()}_not_reported")
                else:
                    print(f"  ❌ Health endpoint returned {health_response.status_code}")
                    # Mark all dependencies as unknown
                    test_result["failed_dependencies"] = test_result["total_dependencies"]
                    test_result["missing_dependencies"] = [dep for deps in self.service_dependencies.values() for dep in deps]
                    
        except Exception as e:
            print(f"  ❌ Failed to check dependencies: {str(e)}")
            test_result["failed_dependencies"] = test_result["total_dependencies"]
            test_result["missing_dependencies"] = [dep for deps in self.service_dependencies.values() for dep in deps]
            self.service_issues.append("dependency_check_failed")
        
        # Calculate dependency health
        dependency_health = (test_result["healthy_dependencies"] / test_result["total_dependencies"]) * 100 if test_result["total_dependencies"] > 0 else 0
        test_result["dependency_health_percentage"] = round(dependency_health, 1)
        
        print(f"\n📊 DEPENDENCY HEALTH SUMMARY:")
        print(f"Total Dependencies: {test_result['total_dependencies']}")
        print(f"Healthy Dependencies: {test_result['healthy_dependencies']}")
        print(f"Failed Dependencies: {test_result['failed_dependencies']}")
        print(f"Dependency Health: {dependency_health:.1f}%")
        
        if test_result["missing_dependencies"]:
            print(f"Missing/Failed Dependencies: {', '.join(test_result['missing_dependencies'])}")
        
        self.test_results.append(test_result)
        return test_result
    
    async def test_load_balancer_configuration(self) -> Dict[str, Any]:
        """
        EXPECTED TO FIND ISSUES: Test load balancer and routing configuration.
        """
        print("\n🔍 AUDITING: Load Balancer Configuration")
        print("=" * 60)
        
        test_result = {
            "test_name": "load_balancer_configuration_audit",
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "purpose": "Check load balancer routing and health",
            "routing_tests": 0,
            "routing_successful": 0,
            "routing_failed": 0,
            "configuration_issues": [],
            "evidence": {}
        }
        
        # Test different routing scenarios
        routing_tests = [
            {"path": "/health", "expected_status": 200, "name": "Basic Health"},
            {"path": "/api/v1/health", "expected_status": 200, "name": "API Health"},
            {"path": "/api/v1/websocket", "expected_status": [200, 405], "name": "WebSocket Routing"},  # 405 = Method Not Allowed for GET on WebSocket
            {"path": "/nonexistent", "expected_status": 404, "name": "404 Handling"},
            {"path": "/api/v1/agents", "expected_status": [200, 401, 403], "name": "Protected Route"}  # Auth required
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for test in routing_tests:
                test_result["routing_tests"] += 1
                
                try:
                    print(f"Testing routing: {test['name']} -> {test['path']}")
                    response = await client.get(f"{self.staging_base_url}{test['path']}")
                    
                    expected_statuses = test['expected_status'] if isinstance(test['expected_status'], list) else [test['expected_status']]
                    
                    if response.status_code in expected_statuses:
                        test_result["routing_successful"] += 1
                        print(f"  ✅ {test['name']}: {response.status_code} (expected)")
                    else:
                        test_result["routing_failed"] += 1
                        test_result["configuration_issues"].append(f"{test['name']}: got {response.status_code}, expected {expected_statuses}")
                        print(f"  ❌ {test['name']}: {response.status_code} (expected {expected_statuses})")
                        self.service_issues.append(f"routing_{test['name'].lower().replace(' ', '_')}_failed")
                    
                    # Check for load balancer headers
                    lb_headers = ["x-cloud-trace-context", "server", "via"]
                    lb_header_count = sum(1 for header in lb_headers if header in response.headers)
                    
                    if lb_header_count >= 2:
                        print(f"    ✅ Load balancer headers detected: {lb_header_count}/{len(lb_headers)}")
                    else:
                        print(f"    ⚠️  Few load balancer headers: {lb_header_count}/{len(lb_headers)}")
                        if "load_balancer_headers_missing" not in self.service_issues:
                            self.service_issues.append("load_balancer_headers_missing")
                    
                except Exception as e:
                    test_result["routing_failed"] += 1
                    test_result["configuration_issues"].append(f"{test['name']}: {str(e)}")
                    print(f"  ❌ {test['name']}: ERROR - {str(e)}")
                    self.service_issues.append(f"routing_{test['name'].lower().replace(' ', '_')}_error")
        
        # Calculate routing health
        routing_health = (test_result["routing_successful"] / test_result["routing_tests"]) * 100 if test_result["routing_tests"] > 0 else 0
        test_result["routing_health_percentage"] = round(routing_health, 1)
        
        print(f"\n📊 LOAD BALANCER HEALTH SUMMARY:")
        print(f"Routing Tests: {test_result['routing_tests']}")
        print(f"Successful Routes: {test_result['routing_successful']}")
        print(f"Failed Routes: {test_result['routing_failed']}")
        print(f"Routing Health: {routing_health:.1f}%")
        
        if test_result["configuration_issues"]:
            print(f"Configuration Issues:")
            for issue in test_result["configuration_issues"]:
                print(f"  - {issue}")
        
        self.test_results.append(test_result)
        return test_result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all service availability audit tests."""
        print("🚨 ISSUE #586: SERVICE AVAILABILITY AUDIT")
        print("=" * 70)
        print("Purpose: Audit all services for availability and health issues")
        print("Expected: Identify missing/failed services causing 503/WebSocket errors")
        print("=" * 70)
        
        audit_start_time = time.time()
        
        # Run all audit tests
        results = await asyncio.gather(
            self.test_critical_service_availability(),
            self.test_service_dependency_health(),
            self.test_load_balancer_configuration(),
            return_exceptions=True
        )
        
        audit_duration = time.time() - audit_start_time
        
        # Analyze overall audit results
        total_issues = len(set(self.service_issues))
        
        summary = {
            "issue_number": 586,
            "audit_purpose": "Service availability audit for Issue #586",
            "total_audit_categories": len(results),
            "audit_duration_seconds": round(audit_duration, 2),
            "total_service_issues": total_issues,
            "service_issues_found": list(set(self.service_issues)),
            "detailed_results": results,
            "overall_service_health": "HEALTHY" if total_issues == 0 else "DEGRADED" if total_issues < 5 else "CRITICAL",
            "audit_conclusions": {
                "service_availability": "GOOD" if total_issues < 3 else "POOR",
                "likely_cause_of_503": "Service dependencies" if any("dependency" in issue for issue in self.service_issues) else "Load balancer" if any("routing" in issue for issue in self.service_issues) else "Unknown",
                "recommended_action": "Fix service dependencies" if any("dependency" in issue for issue in self.service_issues) else "Check load balancer config" if any("routing" in issue for issue in self.service_issues) else "Continue investigation"
            }
        }
        
        print(f"\n📊 COMPREHENSIVE SERVICE AUDIT SUMMARY")
        print("=" * 50)
        print(f"Audit Duration: {audit_duration:.2f}s")
        print(f"Service Issues Found: {total_issues}")
        print(f"Overall Service Health: {summary['overall_service_health']}")
        print(f"Service Availability: {summary['audit_conclusions']['service_availability']}")
        print(f"Likely 503 Cause: {summary['audit_conclusions']['likely_cause_of_503']}")
        print(f"Recommended Action: {summary['audit_conclusions']['recommended_action']}")
        
        if self.service_issues:
            print(f"\nDetected Issues:")
            for issue in sorted(set(self.service_issues)):
                print(f"  - {issue}")
        
        return summary


@pytest.mark.asyncio
async def test_issue_586_service_availability_audit():
    """
    Issue #586 service availability audit to identify root causes.
    
    This test audits all critical services to identify what might be
    causing 503 errors and WebSocket connection failures.
    """
    auditor = ServiceAvailabilityAuditTest()
    results = await auditor.run_all_tests()
    
    # This test doesn't assert failure - it's purely investigative
    # The goal is to gather comprehensive service health data
    
    print(f"\n✅ Service availability audit completed!")
    print(f"Found {results['total_service_issues']} service issues to investigate")
    
    return results


if __name__ == "__main__":
    """Run the audit directly for debugging."""
    async def main():
        print("Running Issue #586 Service Availability Audit")
        auditor = ServiceAvailabilityAuditTest()
        results = await auditor.run_all_tests()
        
        print(f"\n🎯 AUDIT RESULT:")
        if results["total_service_issues"] > 0:
            print(f"🔍 Found {results['total_service_issues']} service issues that may be causing Issue #586")
            print(f"Service health: {results['overall_service_health']}")
            print(f"Issues: {', '.join(results['service_issues_found'])}")
        else:
            print(f"✅ All services appear healthy - Issue #586 may be resolved")
            
        return results
    
    results = asyncio.run(main())