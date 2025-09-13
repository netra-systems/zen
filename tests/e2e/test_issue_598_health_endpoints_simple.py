"""
Simple test to reproduce Issue #598: Health endpoints returning 404 in GCP staging.

This test validates that health endpoints /health and /api/health are accessible
in GCP staging environment to diagnose the reported 404 errors.

Issue: https://github.com/netra-systems/netra-apex/issues/598
"""

import asyncio
import pytest
import httpx
from typing import Dict, Any
from datetime import datetime, timezone


class TestIssue598HealthEndpointsSimple:
    """
    Simple E2E test to reproduce and diagnose health endpoint 404 errors in staging.
    """

    @pytest.mark.asyncio
    async def test_health_endpoint_accessibility_staging(self):
        """
        CRITICAL TEST: Verify health endpoints are accessible in staging.
        
        This test directly reproduces the issue reported in #598 by attempting
        to access the health endpoints that are returning 404 errors.
        """
        staging_base_url = "https://netra-backend-staging-service-672236085899.us-central1.run.app"
        expected_health_endpoints = [
            "/health",
            "/api/health",
            "/health/ready", 
            "/health/live",
            "/health/startup"
        ]
        
        health_results = {}
        all_successful = True
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in expected_health_endpoints:
                url = f"{staging_base_url}{endpoint}"
                
                try:
                    response = await client.get(url)
                    health_results[endpoint] = {
                        "status_code": response.status_code,
                        "accessible": response.status_code in [200, 503],  # 503 is OK for health checks
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                        "url": url,
                        "user_agent": "test-client/1.0",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Try to parse response
                    try:
                        if response.headers.get("content-type", "").startswith("application/json"):
                            health_results[endpoint]["response_body"] = response.json()
                        else:
                            health_results[endpoint]["response_text"] = response.text[:200]  # First 200 chars
                    except Exception as parse_error:
                        health_results[endpoint]["parse_error"] = str(parse_error)
                    
                    # Check if this endpoint is returning 404 (the reported issue)
                    if response.status_code == 404:
                        all_successful = False
                        health_results[endpoint]["issue_598_confirmed"] = True
                        print(f"ISSUE #598 CONFIRMED: {endpoint} returned 404")
                    
                except httpx.TimeoutException:
                    health_results[endpoint] = {
                        "status_code": None,
                        "accessible": False,
                        "error": "timeout",
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    all_successful = False
                    
                except Exception as e:
                    health_results[endpoint] = {
                        "status_code": None,
                        "accessible": False,
                        "error": str(e),
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    all_successful = False

        # Log detailed results for analysis
        print("=== ISSUE #598 HEALTH ENDPOINT TEST RESULTS ===")
        for endpoint, result in health_results.items():
            print(f"{endpoint}: {result}")

        # Check for 404 errors specifically
        endpoints_with_404 = [
            endpoint for endpoint, result in health_results.items()
            if result.get("status_code") == 404
        ]
        
        if endpoints_with_404:
            print(f"ISSUE #598 REPRODUCED: These endpoints returned 404: {endpoints_with_404}")
            
            # Create detailed error message for debugging
            error_details = {
                "issue": "Health endpoints returning 404 in staging",
                "affected_endpoints": endpoints_with_404,
                "staging_url": staging_base_url,
                "test_timestamp": datetime.now(timezone.utc).isoformat(),
                "full_results": health_results
            }
            
            # This test should fail to highlight the issue
            pytest.fail(f"Issue #598 reproduced: {len(endpoints_with_404)} health endpoints returned 404. Details: {error_details}")

        # If no 404s, check if endpoints are properly responding
        successful_endpoints = [
            endpoint for endpoint, result in health_results.items()
            if result.get("accessible", False)
        ]
        
        assert len(successful_endpoints) > 0, f"No health endpoints were accessible. Results: {health_results}"
        
        # Log success
        print(f"SUCCESS: {len(successful_endpoints)} health endpoints accessible: {successful_endpoints}")

    @pytest.mark.asyncio
    async def test_curl_user_agent_compatibility(self):
        """
        Test health endpoints with curl user agent to match the reported issue pattern.
        
        The issue shows requests with User-Agent: curl/7.81.0 returning 404.
        """
        staging_base_url = "https://netra-backend-staging-service-672236085899.us-central1.run.app"
        curl_headers = {
            "User-Agent": "curl/7.81.0"
        }
        
        health_results = {}
        
        async with httpx.AsyncClient(timeout=30.0, headers=curl_headers) as client:
            for endpoint in ["/health", "/api/health"]:  # Main endpoints from issue
                url = f"{staging_base_url}{endpoint}"
                
                try:
                    response = await client.get(url)
                    health_results[endpoint] = {
                        "status_code": response.status_code,
                        "user_agent": "curl/7.81.0",
                        "accessible": response.status_code != 404,
                        "url": url
                    }
                    
                    if response.status_code == 404:
                        print(f"ISSUE #598: {endpoint} returned 404 with curl user agent")
                        
                except Exception as e:
                    health_results[endpoint] = {
                        "error": str(e),
                        "accessible": False,
                        "url": url
                    }

        # Check for 404 responses with curl user agent
        curl_404_endpoints = [
            endpoint for endpoint, result in health_results.items()
            if result.get("status_code") == 404
        ]
        
        if curl_404_endpoints:
            error_msg = f"Health endpoints returned 404 with curl user agent: {curl_404_endpoints}. This matches the exact pattern reported in Issue #598."
            print(error_msg)
            pytest.fail(error_msg)
        
        print(f"Curl compatibility test results: {health_results}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])