"""
Issue #586: Backend Service 503 Error Reproduction Test
======================================================

This test reproduces the backend service 503 errors without requiring Docker.
Designed to fail and demonstrate the service health issues.

Execution: Python-only (no Docker dependency)
Target: GCP Staging Backend Service
Focus: Health endpoint failures and service unavailability
"""

import asyncio
import httpx
import pytest
import time
import sys
import os
from typing import Dict, Any, Optional
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


class BackendService503ReproductionTest:
    """Test backend service health to reproduce 503 errors."""
    
    def __init__(self):
        """Initialize test with staging environment configuration."""
        self.env = IsolatedEnvironment()
        self.staging_backend_url = "https://api.staging.netrasystems.ai"
        self.test_results = []
        self.error_patterns = []
        
    async def test_backend_health_endpoint_503_error(self) -> Dict[str, Any]:
        """
        EXPECTED TO FAIL: Test backend health endpoint to reproduce 503 error.
        
        This test is designed to demonstrate the backend service unavailability
        issue described in Issue #586.
        """
        print("\n🔍 TESTING: Backend Health Endpoint (Expected 503 Error)")
        print("=" * 60)
        
        test_result = {
            "test_name": "backend_health_endpoint_503_error",
            "timestamp": datetime.utcnow().isoformat(),
            "expected_failure": True,
            "purpose": "Reproduce Issue #586 backend service 503 error",
            "success": False,
            "status_code": None,
            "error_message": None,
            "response_time_ms": None,
            "evidence": {}
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_url = f"{self.staging_backend_url}/health"
                print(f"Testing health endpoint: {health_url}")
                
                response = await client.get(health_url)
                response_time = (time.time() - start_time) * 1000
                
                test_result.update({
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2),
                    "response_headers": dict(response.headers),
                    "response_text": response.text[:500] if response.text else ""
                })
                
                print(f"Status Code: {response.status_code}")
                print(f"Response Time: {response_time:.2f}ms")
                print(f"Headers: {dict(response.headers)}")
                
                if response.status_code == 503:
                    print("✅ EXPECTED FAILURE REPRODUCED: Backend service returned 503")
                    test_result.update({
                        "success": True,  # Success at reproducing the issue
                        "error_message": "Backend service unavailable (503)",
                        "evidence": {
                            "issue_reproduced": True,
                            "error_type": "service_unavailable",
                            "backend_down": True
                        }
                    })
                    self.error_patterns.append("backend_service_503")
                    
                elif response.status_code == 200:
                    print("❌ UNEXPECTED SUCCESS: Backend service is healthy")
                    test_result.update({
                        "success": False,  # Failed to reproduce the issue
                        "error_message": "Service unexpectedly healthy",
                        "evidence": {
                            "issue_reproduced": False,
                            "service_operational": True,
                            "response_data": response.text[:200]
                        }
                    })
                    
                else:
                    print(f"⚠️  UNEXPECTED STATUS: Received {response.status_code}")
                    test_result.update({
                        "success": True if response.status_code >= 500 else False,
                        "error_message": f"Unexpected status code: {response.status_code}",
                        "evidence": {
                            "issue_reproduced": response.status_code >= 500,
                            "unexpected_status": True,
                            "status_code": response.status_code
                        }
                    })
                    
        except httpx.TimeoutException as e:
            print(f"✅ EXPECTED FAILURE: Backend service timeout")
            test_result.update({
                "success": True,  # Success at reproducing connection issues
                "error_message": f"Backend service timeout: {str(e)}",
                "evidence": {
                    "issue_reproduced": True,
                    "error_type": "connection_timeout",
                    "backend_unreachable": True
                }
            })
            self.error_patterns.append("backend_timeout")
            
        except httpx.ConnectError as e:
            print(f"✅ EXPECTED FAILURE: Backend service connection error")
            test_result.update({
                "success": True,  # Success at reproducing connection issues
                "error_message": f"Backend connection failed: {str(e)}",
                "evidence": {
                    "issue_reproduced": True,
                    "error_type": "connection_error", 
                    "backend_unreachable": True
                }
            })
            self.error_patterns.append("backend_connection_error")
            
        except Exception as e:
            print(f"⚠️  UNEXPECTED ERROR: {str(e)}")
            test_result.update({
                "success": False,
                "error_message": f"Unexpected error: {str(e)}",
                "evidence": {
                    "issue_reproduced": False,
                    "unexpected_error": True,
                    "error_details": str(e)
                }
            })
            
        self.test_results.append(test_result)
        return test_result
    
    async def test_backend_readiness_probe_failure(self) -> Dict[str, Any]:
        """
        EXPECTED TO FAIL: Test backend readiness probe to demonstrate service issues.
        """
        print("\n🔍 TESTING: Backend Readiness Probe (Expected Failure)")
        print("=" * 60)
        
        test_result = {
            "test_name": "backend_readiness_probe_failure",
            "timestamp": datetime.utcnow().isoformat(),
            "expected_failure": True,
            "purpose": "Demonstrate backend service readiness issues",
            "success": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                readiness_url = f"{self.staging_backend_url}/health/ready"
                print(f"Testing readiness endpoint: {readiness_url}")
                
                response = await client.get(readiness_url)
                test_result["status_code"] = response.status_code
                
                if response.status_code == 503:
                    print("✅ EXPECTED FAILURE: Backend not ready (503)")
                    test_result.update({
                        "success": True,
                        "error_message": "Backend service not ready",
                        "evidence": {"readiness_failed": True, "backend_not_ready": True}
                    })
                    self.error_patterns.append("backend_not_ready")
                    
                elif response.status_code == 200:
                    print("❌ UNEXPECTED: Backend reports ready")
                    test_result.update({
                        "success": False,
                        "error_message": "Backend unexpectedly ready"
                    })
                    
        except Exception as e:
            print(f"✅ EXPECTED ERROR: Connection failure - {str(e)}")
            test_result.update({
                "success": True,
                "error_message": f"Connection failed: {str(e)}",
                "evidence": {"connection_failed": True}
            })
            self.error_patterns.append("backend_connection_failure")
            
        self.test_results.append(test_result)
        return test_result
    
    async def test_backend_liveness_probe_failure(self) -> Dict[str, Any]:
        """
        EXPECTED TO FAIL: Test backend liveness probe to show service death.
        """
        print("\n🔍 TESTING: Backend Liveness Probe (Expected Failure)")
        print("=" * 60)
        
        test_result = {
            "test_name": "backend_liveness_probe_failure", 
            "timestamp": datetime.utcnow().isoformat(),
            "expected_failure": True,
            "purpose": "Demonstrate backend service liveness issues",
            "success": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:  # Shorter timeout for liveness
                liveness_url = f"{self.staging_backend_url}/health/live"
                print(f"Testing liveness endpoint: {liveness_url}")
                
                response = await client.get(liveness_url)
                test_result["status_code"] = response.status_code
                
                if response.status_code == 503:
                    print("✅ EXPECTED FAILURE: Backend not alive (503)")
                    test_result.update({
                        "success": True,
                        "error_message": "Backend service not alive",
                        "evidence": {"liveness_failed": True, "backend_dead": True}
                    })
                    self.error_patterns.append("backend_not_alive")
                    
        except Exception as e:
            print(f"✅ EXPECTED ERROR: Liveness check failed - {str(e)}")
            test_result.update({
                "success": True,
                "error_message": f"Liveness check failed: {str(e)}",
                "evidence": {"liveness_check_failed": True}
            })
            self.error_patterns.append("backend_liveness_failure")
            
        self.test_results.append(test_result)
        return test_result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all backend service reproduction tests."""
        print("🚨 ISSUE #586: BACKEND SERVICE 503 ERROR REPRODUCTION")
        print("=" * 70)
        print("Purpose: Reproduce backend service health issues")
        print("Expected: Tests should FAIL to demonstrate the problem")
        print("=" * 70)
        
        test_suite_start = time.time()
        
        # Run all reproduction tests
        results = await asyncio.gather(
            self.test_backend_health_endpoint_503_error(),
            self.test_backend_readiness_probe_failure(),
            self.test_backend_liveness_probe_failure(),
            return_exceptions=True
        )
        
        test_suite_duration = time.time() - test_suite_start
        
        # Analyze results
        successful_reproductions = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        total_tests = len(results)
        
        summary = {
            "issue_number": 586,
            "test_purpose": "Reproduce backend service 503 errors",
            "total_tests": total_tests,
            "successful_reproductions": successful_reproductions,
            "reproduction_rate": successful_reproductions / total_tests if total_tests > 0 else 0,
            "test_duration_seconds": round(test_suite_duration, 2),
            "error_patterns_found": list(set(self.error_patterns)),
            "detailed_results": results,
            "conclusions": {
                "issue_reproduced": successful_reproductions > 0,
                "backend_service_health": "FAILING" if successful_reproductions > 0 else "HEALTHY",
                "recommended_action": "Fix backend service deployment" if successful_reproductions > 0 else "Investigate false positive"
            }
        }
        
        print(f"\n📊 TEST SUITE SUMMARY")
        print("=" * 30)
        print(f"Total Tests: {total_tests}")
        print(f"Issue Reproductions: {successful_reproductions}")
        print(f"Reproduction Rate: {summary['reproduction_rate']:.1%}")
        print(f"Duration: {test_suite_duration:.2f}s")
        print(f"Error Patterns: {', '.join(self.error_patterns)}")
        print(f"Backend Status: {summary['conclusions']['backend_service_health']}")
        print(f"Recommended Action: {summary['conclusions']['recommended_action']}")
        
        return summary


@pytest.mark.asyncio
async def test_issue_586_backend_service_503_reproduction():
    """
    Issue #586 reproduction test that should FAIL to demonstrate the problem.
    
    This test is designed to reproduce backend service 503 errors.
    SUCCESS = Successfully reproducing the 503 error
    FAILURE = Backend service is unexpectedly healthy
    """
    tester = BackendService503ReproductionTest()
    results = await tester.run_all_tests()
    
    # Assert that we successfully reproduced the issue
    assert results["successful_reproductions"] > 0, (
        f"Failed to reproduce Issue #586 backend service errors. "
        f"Got {results['successful_reproductions']} reproductions out of {results['total_tests']} tests. "
        f"Backend service appears to be healthy."
    )
    
    # Assert that we found expected error patterns
    assert len(results["error_patterns_found"]) > 0, (
        "No error patterns detected. Issue #586 may be resolved or test needs adjustment."
    )
    
    print(f"\n✅ Successfully reproduced Issue #586 backend service problems!")
    return results


if __name__ == "__main__":
    """Run the test directly for debugging."""
    async def main():
        print("Running Issue #586 Backend Service 503 Reproduction Test")
        tester = BackendService503ReproductionTest()
        results = await tester.run_all_tests()
        
        print(f"\n🎯 FINAL RESULT:")
        if results["successful_reproductions"] > 0:
            print(f"✅ Issue #586 REPRODUCED: Found {results['successful_reproductions']} backend service failures")
            print(f"Error patterns: {', '.join(results['error_patterns_found'])}")
        else:
            print(f"❌ Issue #586 NOT REPRODUCED: Backend service appears healthy")
            
        return results
    
    results = asyncio.run(main())