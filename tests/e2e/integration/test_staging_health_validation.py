#!/usr/bin/env python3
"""
Staging Health Validation Tests

Business Value: Ensures staging environment is fully functional and ready for development/testing.
Validates all critical staging services and integration points.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import pytest


logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """Container for service health status."""
    name: str
    url: str
    accessible: bool = False
    status_code: Optional[int] = None
    health_data: Optional[Dict] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


class StagingHealthValidator:
    """Validates staging environment health and functionality."""
    
    STAGING_SERVICES = {
        'backend': 'https://api.staging.netrasystems.ai',
        'auth': 'https://auth.staging.netrasystems.ai',
        'frontend': 'https://app.staging.netrasystems.ai'
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[ServiceHealth] = []
        
    async def setup(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
    async def teardown(self):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
            
    async def validate_all_services(self) -> List[ServiceHealth]:
        """Validate all staging services."""
        validation_tasks = [
            self._validate_service(name, url)
            for name, url in self.STAGING_SERVICES.items()
        ]
        
        self.results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Handle any exceptions from gather
        processed_results = []
        for i, result in enumerate(self.results):
            if isinstance(result, Exception):
                service_name = list(self.STAGING_SERVICES.keys())[i]
                service_url = list(self.STAGING_SERVICES.values())[i]
                processed_results.append(ServiceHealth(
                    name=service_name,
                    url=service_url,
                    accessible=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
                
        self.results = processed_results
        return self.results
        
    async def _validate_service(self, name: str, url: str) -> ServiceHealth:
        """Validate individual service health."""
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Validating {name} at {url}")
            
            # Basic connectivity test
            async with self.session.get(url) as resp:
                response_time = (time.time() - start_time) * 1000
                health = ServiceHealth(
                    name=name,
                    url=url,
                    accessible=True,
                    status_code=resp.status,
                    response_time_ms=response_time
                )
                
                # Service-specific health checks
                if name == 'backend':
                    health = await self._validate_backend_health(health)
                elif name == 'auth':
                    health = await self._validate_auth_health(health)
                elif name == 'frontend':
                    health = await self._validate_frontend_health(health)
                    
                return health
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Service {name} validation failed: {e}")
            return ServiceHealth(
                name=name,
                url=url,
                accessible=False,
                error=str(e),
                response_time_ms=response_time
            )
            
    async def _validate_backend_health(self, health: ServiceHealth) -> ServiceHealth:
        """Validate backend-specific health endpoints."""
        try:
            # Test /health endpoint
            async with self.session.get(f"{health.url}/health") as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    health.health_data = health_data
                    logger.info(f"Backend health: {health_data.get('status', 'unknown')}")
                else:
                    health.error = f"Health endpoint returned {resp.status}"
                    
        except Exception as e:
            health.error = f"Health check failed: {e}"
            
        return health
        
    async def _validate_auth_health(self, health: ServiceHealth) -> ServiceHealth:
        """Validate auth service-specific endpoints."""
        try:
            # Test /health/ready endpoint
            async with self.session.get(f"{health.url}/health/ready") as resp:
                if resp.status == 200:
                    health.health_data = {"ready": True}
                    logger.info("Auth service is ready")
                else:
                    health.error = f"Ready endpoint returned {resp.status}"
                    
        except Exception as e:
            health.error = f"Ready check failed: {e}"
            
        return health
        
    async def _validate_frontend_health(self, health: ServiceHealth) -> ServiceHealth:
        """Validate frontend-specific functionality."""
        try:
            # For frontend, just check basic response
            if health.status_code == 200:
                health.health_data = {"status": "accessible"}
                logger.info("Frontend is accessible")
            else:
                health.error = f"Frontend returned {health.status_code}"
                
        except Exception as e:
            health.error = f"Frontend check failed: {e}"
            
        return health
        
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        total_services = len(self.results)
        accessible_services = len([r for r in self.results if r.accessible])
        
        summary = {
            "total_services": total_services,
            "accessible_services": accessible_services,
            "failed_services": total_services - accessible_services,
            "success_rate": accessible_services / total_services if total_services > 0 else 0,
            "overall_status": "healthy" if accessible_services == total_services else "degraded",
            "services": []
        }
        
        for result in self.results:
            service_info = {
                "name": result.name,
                "url": result.url,
                "status": "healthy" if result.accessible else "failed",
                "status_code": result.status_code,
                "response_time_ms": result.response_time_ms,
                "error": result.error
            }
            
            if result.health_data:
                service_info["health_data"] = result.health_data
                
            summary["services"].append(service_info)
            
        return summary


@pytest.mark.asyncio
async def test_staging_service_health():
    """Test staging services are healthy and accessible."""
    validator = StagingHealthValidator()
    await validator.setup()
    
    try:
        results = await validator.validate_all_services()
        summary = validator.get_health_summary()
        
        logger.info(f"Staging validation results: {json.dumps(summary, indent=2)}")
        
        # Assert all services are accessible
        assert summary["accessible_services"] == summary["total_services"], \
            f"Not all services accessible: {summary['failed_services']} failed"
            
        # Assert each service individually
        for result in results:
            assert result.accessible, f"Service {result.name} not accessible: {result.error}"
            assert result.status_code == 200, f"Service {result.name} returned {result.status_code}"
            
        # Assert response times are reasonable (under 10 seconds)
        for result in results:
            if result.response_time_ms:
                assert result.response_time_ms < 10000, \
                    f"Service {result.name} response time too slow: {result.response_time_ms}ms"
                    
        logger.info("✅ All staging services validated successfully")
        
    finally:
        await validator.teardown()


@pytest.mark.asyncio
async def test_staging_backend_endpoints():
    """Test backend-specific endpoints."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        backend_url = StagingHealthValidator.STAGING_SERVICES['backend']
        
        # Test health endpoint
        async with session.get(f"{backend_url}/health") as resp:
            assert resp.status == 200, f"Health endpoint failed: {resp.status}"
            health_data = await resp.json()
            assert health_data.get("status") == "healthy", \
                f"Backend not healthy: {health_data}"
                
        # Test API accessibility (without auth)
        async with session.get(f"{backend_url}/api") as resp:
            # Should get 404 for base API, but not connection error
            assert resp.status in [200, 404, 422], \
                f"API endpoint inaccessible: {resp.status}"
                
        logger.info("✅ Backend endpoints validated successfully")


@pytest.mark.asyncio 
async def test_staging_auth_endpoints():
    """Test auth service-specific endpoints."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        auth_url = StagingHealthValidator.STAGING_SERVICES['auth']
        
        # Test ready endpoint
        async with session.get(f"{auth_url}/health/ready") as resp:
            assert resp.status == 200, f"Ready endpoint failed: {resp.status}"
            
        # Test health endpoint (if available)
        async with session.get(f"{auth_url}/health") as resp:
            assert resp.status in [200, 404], f"Health endpoint error: {resp.status}"
            
        logger.info("✅ Auth service endpoints validated successfully")


@pytest.mark.asyncio
async def test_staging_cors_configuration():
    """Test CORS configuration in staging."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        backend_url = StagingHealthValidator.STAGING_SERVICES['backend']
        
        # Test CORS preflight
        headers = {
            'Origin': 'https://app.staging.netrasystems.ai',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type,Authorization'
        }
        
        async with session.options(f"{backend_url}/api/threads", headers=headers) as resp:
            # Should not fail with CORS error
            assert resp.status in [200, 204, 404], f"CORS preflight failed: {resp.status}"
            
            # Check CORS headers if present
            cors_origin = resp.headers.get('Access-Control-Allow-Origin')
            if cors_origin:
                assert cors_origin in ['*', 'https://app.staging.netrasystems.ai'], \
                    f"Invalid CORS origin: {cors_origin}"
                    
        logger.info("✅ CORS configuration validated successfully")


@pytest.mark.asyncio
async def test_staging_performance_baseline():
    """Test staging performance meets baseline requirements."""
    validator = StagingHealthValidator()
    await validator.setup()
    
    try:
        results = await validator.validate_all_services()
        
        # Check response times
        for result in results:
            if result.response_time_ms:
                # Staging should respond within 5 seconds for basic requests
                assert result.response_time_ms < 5000, \
                    f"Service {result.name} too slow: {result.response_time_ms}ms"
                    
                logger.info(f"Service {result.name} response time: {result.response_time_ms:.1f}ms")
                
        logger.info("✅ Staging performance baseline validated")
        
    finally:
        await validator.teardown()


if __name__ == "__main__":
    # Allow running directly for manual testing
    async def main():
        print("=== STAGING HEALTH VALIDATION ===")
        
        validator = StagingHealthValidator()
        await validator.setup()
        
        try:
            results = await validator.validate_all_services()
            summary = validator.get_health_summary()
            
            print(json.dumps(summary, indent=2))
            
            if summary["overall_status"] == "healthy":
                print("\n✅ ALL STAGING SERVICES ARE HEALTHY")
                return 0
            else:
                print(f"\n❌ STAGING ISSUES DETECTED: {summary['failed_services']} service(s) failed")
                return 1
                
        except Exception as e:
            print(f"\n❌ VALIDATION FAILED: {e}")
            return 1
            
        finally:
            await validator.teardown()
            
    exit_code = asyncio.run(main())
    sys.exit(exit_code)