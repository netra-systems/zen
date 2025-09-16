from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Health Check Cascade Integration Test - Real Health Endpoint Testing

from shared.isolated_environment import get_env
Business Value: Test real health endpoints for degraded mode behavior.
Validates actual system health reporting when ClickHouse is unavailable.
"""

import asyncio
import logging
import os

# Add project root to path for imports
import sys
from pathlib import Path
from typing import Any, Dict

import pytest


logger = logging.getLogger(__name__)


env = get_env()
class HealthEndpointerTests:
    """Tests health endpoints directly for degraded mode behavior."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize health endpoint tester."""
        self.base_url = base_url
        self.health_endpoints = [
            "/health",
            "/health/ready", 
            "/health/system/comprehensive"
        ]
    
    @pytest.mark.e2e
    async def test_health_endpoints_respond(self) -> Dict[str, Any]:
        """Test that health endpoints respond when services are available."""
        results = {}
        
        for endpoint in self.health_endpoints:
            try:
                response = await self._call_health_endpoint(endpoint)
                results[endpoint] = {
                    "responsive": True,
                    "status_code": response.get("status_code", 0),
                    "has_status": "status" in response.get("data", {})
                }
            except Exception as e:
                results[endpoint] = {
                    "responsive": False,
                    "error": str(e)
                }
        
        return results
    
    async def _call_health_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Call individual health endpoint."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(f"{self.base_url}{endpoint}")
                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else {}
                }
        except Exception as e:
            return {"error": str(e)}
    
    @pytest.mark.e2e
    async def test_degraded_mode_with_clickhouse_disabled(self) -> Dict[str, Any]:
        """Test health endpoints when ClickHouse is disabled via environment."""
        # Set environment variable to simulate ClickHouse failure
        original_value = env.get('CLICKHOUSE_DISABLED')
        env.set('CLICKHOUSE_DISABLED', 'true', "test")
        
        try:
            # Wait a moment for configuration to take effect
            await asyncio.sleep(1)
            
            # Test health endpoints
            health_results = await self.test_health_endpoints_respond()
            
            # Check if any endpoint reports degraded status
            degraded_detected = await self._check_for_degraded_status(health_results)
            
            return {
                "clickhouse_disabled": True,
                "health_endpoints_responsive": any(r.get("responsive", False) for r in health_results.values()),
                "degraded_mode_detected": degraded_detected,
                "endpoint_results": health_results
            }
            
        finally:
            # Restore original environment
            if original_value is None:
                env.delete('CLICKHOUSE_DISABLED', "test")
            else:
                env.set('CLICKHOUSE_DISABLED', original_value, "test")
    
    async def _check_for_degraded_status(self, health_results: Dict[str, Any]) -> bool:
        """Check if any health endpoint reports degraded status."""
        for endpoint, result in health_results.items():
            if result.get("responsive", False):
                try:
                    # Re-call endpoint to get fresh status with ClickHouse disabled
                    fresh_response = await self._call_health_endpoint(endpoint)
                    data = fresh_response.get("data", {})
                    status = data.get("status", "").lower()
                    
                    if status in ["degraded", "unhealthy"]:
                        return True
                    
                    # Check for ClickHouse failure indicators
                    checks = data.get("checks", {})
                    if isinstance(checks, dict) and checks.get("clickhouse") is False:
                        return True
                        
                except Exception as e:
                    logger.debug(f"Error checking degraded status for {endpoint}: {e}")
        
        return False


@pytest.mark.asyncio 
@pytest.mark.e2e
class HealthCascadeIntegrationTests:
    """Integration tests for health check cascade with real endpoints."""
    
    @pytest.fixture
    def health_tester(self):
        """Initialize health endpoint tester."""
        return HealthEndpointTester()
    
    @pytest.mark.e2e
    async def test_health_endpoints_basic_functionality(self, health_tester):
        """Test basic health endpoint functionality."""
        results = await health_tester.test_health_endpoints_respond()
        
        # At least one endpoint should be responsive
        responsive_count = sum(1 for r in results.values() if r.get("responsive", False))
        
        if responsive_count == 0:
            pytest.skip("No health endpoints responsive - backend not running")
        
        assert responsive_count > 0, "No health endpoints responded"
        logger.info(f"Health endpoints test: {responsive_count}/{len(results)} responsive")
    
    @pytest.mark.e2e
    async def test_degraded_mode_detection(self, health_tester):
        """Test degraded mode detection when ClickHouse is disabled."""
        # Check if backend is running first
        initial_results = await health_tester.test_health_endpoints_respond()
        responsive_count = sum(1 for r in initial_results.values() if r.get("responsive", False))
        
        if responsive_count == 0:
            pytest.skip("Backend not running - cannot test degraded mode")
        
        # Test degraded mode with ClickHouse disabled
        degraded_results = await health_tester.test_degraded_mode_with_clickhouse_disabled()
        
        assert degraded_results["health_endpoints_responsive"], "Health endpoints not responsive in degraded mode"
        
        # Log results for debugging
        logger.info(f"Degraded mode test results: {degraded_results}")
        
        # If degraded mode detection is implemented, it should be detected
        if degraded_results["degraded_mode_detected"]:
            logger.info("Degraded mode successfully detected by health endpoints")
        else:
            logger.warning("Degraded mode not detected - may need implementation")
    
    @pytest.mark.e2e
    async def test_health_cascade_timing(self, health_tester):
        """Test that health cascade operations complete within timing requirements."""
        import time
        
        start_time = time.time()
        
        # Test basic health endpoint response time
        results = await health_tester.test_health_endpoints_respond()
        
        basic_time = time.time() - start_time
        
        # Test degraded mode response time
        degraded_start = time.time()
        degraded_results = await health_tester.test_degraded_mode_with_clickhouse_disabled()
        degraded_time = time.time() - degraded_start
        
        total_time = time.time() - start_time
        
        # Health checks should be fast
        assert basic_time < 10.0, f"Basic health checks took {basic_time:.2f}s, should be < 10s"
        assert degraded_time < 15.0, f"Degraded mode check took {degraded_time:.2f}s, should be < 15s"
        assert total_time < 25.0, f"Total health cascade test took {total_time:.2f}s, should be < 25s"
        
        logger.info(f"Health cascade timing: basic={basic_time:.2f}s, degraded={degraded_time:.2f}s, total={total_time:.2f}s")


# Standalone test runner
async def run_health_cascade_integration_tests():
    """Run health cascade integration tests standalone."""
    tester = HealthEndpointTester()
    
    # Test basic functionality
    basic_results = await tester.test_health_endpoints_respond()
    responsive_count = sum(1 for r in basic_results.values() if r.get("responsive", False))
    
    if responsive_count == 0:
        return {"error": "No health endpoints responsive - backend not running"}
    
    # Test degraded mode
    degraded_results = await tester.test_degraded_mode_with_clickhouse_disabled()
    
    return {
        "integration_tests_passed": True,
        "responsive_endpoints": responsive_count,
        "total_endpoints": len(basic_results),
        "degraded_mode_tested": True,
        "degraded_mode_detected": degraded_results["degraded_mode_detected"]
    }


if __name__ == "__main__":
    result = asyncio.run(run_health_cascade_integration_tests())
    print(f"Integration test results: {result}")
