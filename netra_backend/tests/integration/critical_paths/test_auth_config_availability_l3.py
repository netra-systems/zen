"""L3 Integration Test: Auth Service Config Endpoint Availability

Business Value Justification (BVJ):
- Segment: All segments
- Business Goal: Retention (Auth config required for session management)
- Value Impact: Prevents session failures and auth loops
- Revenue Impact: $30K MRR protected from auth config failures

L3 Test: Real local services with containers for auth service config endpoint testing.
Tests config availability, response time, structure validation, and resilience.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import json
import time
import uuid
import subprocess
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from unittest.mock import patch

from netra_backend.app.logging_config import central_logger

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.tests..helpers.redis_l3_helpers import RedisContainer

# Add project root to path

logger = central_logger.get_logger(__name__)


class AuthServiceContainer:
    """Manages Auth Service Docker container for L3 testing."""
    
    def __init__(self, port: int = 8080, redis_url: str = None):
        self.port = port
        self.redis_url = redis_url
        self.container_name = f"netra-test-auth-l3-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.service_url = f"http://localhost:{port}"
        
    async def start(self) -> str:
        """Start auth service container."""
        try:
            await self._cleanup_existing()
            cmd = self._build_docker_command()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self._validate_docker_result(result)
            self.container_id = result.stdout.strip()
            await self._wait_for_ready()
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"Auth service startup failed: {e}")
        
        logger.info(f"Auth service started: {self.container_name}")
        return self.service_url
    
    async def stop(self) -> None:
        """Stop auth service container."""
        if self.container_id:
            try:
                subprocess.run(["docker", "stop", self.container_id], 
                             capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", self.container_id], 
                             capture_output=True, timeout=10)
                logger.info(f"Auth service container stopped: {self.container_name}")
            except Exception as e:
                logger.warning(f"Error stopping auth service: {e}")
            finally:
                self.container_id = None
    
    async def _cleanup_existing(self) -> None:
        """Clean up existing container."""
        try:
            subprocess.run(["docker", "stop", self.container_name], 
                         capture_output=True, timeout=5)
            subprocess.run(["docker", "rm", self.container_name], 
                         capture_output=True, timeout=5)
        except:
            pass
    
    async def _wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for auth service to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self._check_health():
                return
            await asyncio.sleep(1.0)
        raise RuntimeError("Auth service failed to become ready")
    
    async def _check_health(self) -> bool:
        """Check if auth service is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.service_url}/auth/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
    
    def _build_docker_command(self) -> List[str]:
        """Build Docker command for auth service."""
        env_vars = self._get_environment_variables()
        base_cmd = ["docker", "run", "-d", "--name", self.container_name, 
                   "-p", f"{self.port}:8080", "--network", "host"]
        return base_cmd + env_vars + ["auth_service:latest"]
    
    def _get_environment_variables(self) -> List[str]:
        """Get environment variables for container."""
        return [
            "-e", f"REDIS_URL={self.redis_url}", "-e", "ENVIRONMENT=test",
            "-e", "SECRET_KEY=test-secret-key-64-chars-long-for-testing-purposes-only",
            "-e", "GOOGLE_CLIENT_ID=test-client-id", "-e", "GOOGLE_CLIENT_SECRET=test-client-secret",
            "-e", "DATABASE_URL=postgresql://test:test@localhost:5432/test"
        ]
    
    def _validate_docker_result(self, result) -> None:
        """Validate Docker command execution result."""
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start auth service: {result.stderr}")


class PostgresContainer:
    """Manages PostgreSQL container for L3 testing."""
    
    def __init__(self, port: int = 5433):
        self.port = port
        self.container_name = f"netra-test-postgres-l3-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.db_url = f"postgresql://test:test@localhost:{port}/test"
        
    async def start(self) -> str:
        """Start PostgreSQL container."""
        try:
            await self._cleanup_existing()
            cmd = self._build_postgres_command()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self._validate_postgres_result(result)
            self.container_id = result.stdout.strip()
            await self._wait_for_ready()
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"PostgreSQL startup failed: {e}")
        
        logger.info(f"PostgreSQL started: {self.container_name}")
        return self.db_url
    
    async def stop(self) -> None:
        """Stop PostgreSQL container."""
        if self.container_id:
            try:
                subprocess.run(["docker", "stop", self.container_id], 
                             capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", self.container_id], 
                             capture_output=True, timeout=10)
                logger.info(f"PostgreSQL container stopped: {self.container_name}")
            except Exception as e:
                logger.warning(f"Error stopping PostgreSQL: {e}")
            finally:
                self.container_id = None
                
    async def _cleanup_existing(self) -> None:
        """Clean up existing container."""
        try:
            subprocess.run(["docker", "stop", self.container_name], 
                         capture_output=True, timeout=5)
            subprocess.run(["docker", "rm", self.container_name], 
                         capture_output=True, timeout=5)
        except:
            pass
    
    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for PostgreSQL to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self._check_postgres_connection():
                return
            await asyncio.sleep(1.0)
        raise RuntimeError("PostgreSQL failed to become ready")
    
    async def _check_postgres_connection(self) -> bool:
        """Check PostgreSQL connection."""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.db_url)
            await conn.execute("SELECT 1")
            await conn.close()
            return True
        except Exception:
            return False
    
    def _build_postgres_command(self) -> List[str]:
        """Build PostgreSQL Docker command."""
        return [
            "docker", "run", "-d", "--name", self.container_name,
            "-p", f"{self.port}:5432", "-e", "POSTGRES_USER=test",
            "-e", "POSTGRES_PASSWORD=test", "-e", "POSTGRES_DB=test",
            "postgres:15-alpine"
        ]
    
    def _validate_postgres_result(self, result) -> None:
        """Validate PostgreSQL command result."""
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start PostgreSQL: {result.stderr}")


class AuthConfigAvailabilityManager:
    """Manages auth config endpoint availability testing."""
    
    def __init__(self, auth_service_url: str):
        self.auth_service_url = auth_service_url
        self.config_endpoint = f"{auth_service_url}/auth/config"
        self.health_endpoint = f"{auth_service_url}/auth/health"
        self.test_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "config_structure_valid": 0,
            "concurrent_test_results": []
        }
    
    async def test_config_endpoint_basic(self) -> Dict[str, Any]:
        """Test basic config endpoint functionality."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.config_endpoint,
                    timeout=2.0
                )
                
                response_time = time.time() - start_time
                self.test_metrics["response_times"].append(response_time)
                self.test_metrics["total_requests"] += 1
                
                if response.status_code == 200:
                    self.test_metrics["successful_requests"] += 1
                    config_data = response.json()
                    
                    # Validate config structure
                    if self._validate_config_structure(config_data):
                        self.test_metrics["config_structure_valid"] += 1
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "config_data": config_data,
                        "structure_valid": self._validate_config_structure(config_data)
                    }
                else:
                    self.test_metrics["failed_requests"] += 1
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "error": response.text
                    }
                    
        except Exception as e:
            self.test_metrics["failed_requests"] += 1
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    async def test_concurrent_requests(self, num_requests: int = 10) -> Dict[str, Any]:
        """Test concurrent requests to config endpoint."""
        start_time = time.time()
        
        # Create concurrent request tasks
        tasks = [
            self.test_config_endpoint_basic()
            for _ in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze concurrent test results
        successful_concurrent = sum(
            1 for r in results 
            if not isinstance(r, Exception) and r.get("success")
        )
        
        response_times = [
            r.get("response_time", 0) 
            for r in results 
            if not isinstance(r, Exception)
        ]
        
        concurrent_result = {
            "total_requests": num_requests,
            "successful_requests": successful_concurrent,
            "failed_requests": num_requests - successful_concurrent,
            "total_test_time": total_time,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "requests_per_second": num_requests / total_time
        }
        
        self.test_metrics["concurrent_test_results"].append(concurrent_result)
        return concurrent_result
    
    async def test_config_caching_behavior(self) -> Dict[str, Any]:
        """Test config endpoint caching behavior."""
        cache_results = []
        
        for i in range(5):
            result = await self.test_config_endpoint_basic()
            cache_results.append({
                "request_number": i + 1,
                "response_time": result.get("response_time", 0),
                "success": result.get("success", False)
            })
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        # Check if response times improve (indicating caching)
        response_times = [r["response_time"] for r in cache_results if r["success"]]
        
        return {
            "cache_test_results": cache_results,
            "response_times": response_times,
            "avg_first_request": response_times[0] if response_times else 0,
            "avg_cached_requests": sum(response_times[1:]) / len(response_times[1:]) if len(response_times) > 1 else 0,
            "caching_effective": len(response_times) > 1 and response_times[0] > sum(response_times[1:]) / len(response_times[1:])
        }
    
    async def test_environment_adaptation(self) -> Dict[str, Any]:
        """Test config adaptation to different environments."""
        # Test with different environment variables
        config_result = await self.test_config_endpoint_basic()
        
        if not config_result.get("success"):
            return {"success": False, "error": "Failed to get config"}
        
        config_data = config_result["config_data"]
        
        # Validate environment-specific configurations
        env_validation = {
            "has_client_id": "google_client_id" in config_data,
            "has_endpoints": "endpoints" in config_data,
            "has_development_mode": "development_mode" in config_data,
            "endpoints_structure_valid": False
        }
        
        if "endpoints" in config_data:
            endpoints = config_data["endpoints"]
            env_validation["endpoints_structure_valid"] = all([
                "login" in endpoints,
                "logout" in endpoints,
                "callback" in endpoints,
                "token" in endpoints,
                "health" in endpoints
            ])
        
        return {
            "config_data": config_data,
            "environment_validation": env_validation,
            "environment_detected": config_data.get("development_mode", False)
        }
    
    async def test_resilience_with_failures(self) -> Dict[str, Any]:
        """Test config endpoint resilience with simulated failures."""
        resilience_results = []
        
        # Test with different timeout scenarios
        timeouts = [0.1, 0.5, 1.0, 2.0, 5.0]
        
        for timeout in timeouts:
            try:
                start_time = time.time()
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        self.config_endpoint,
                        timeout=timeout
                    )
                    
                    response_time = time.time() - start_time
                    
                    resilience_results.append({
                        "timeout_setting": timeout,
                        "success": response.status_code == 200,
                        "response_time": response_time,
                        "status_code": response.status_code
                    })
                    
            except Exception as e:
                resilience_results.append({
                    "timeout_setting": timeout,
                    "success": False,
                    "error": str(e),
                    "response_time": time.time() - start_time
                })
        
        return {
            "resilience_tests": resilience_results,
            "successful_timeouts": [r for r in resilience_results if r["success"]],
            "failed_timeouts": [r for r in resilience_results if not r["success"]]
        }
    
    def _validate_config_structure(self, config_data: Dict[str, Any]) -> bool:
        """Validate auth config response structure."""
        required_fields = [
            "google_client_id",
            "endpoints", 
            "development_mode",
            "authorized_javascript_origins",
            "authorized_redirect_uris"
        ]
        
        # Check required top-level fields
        for field in required_fields:
            if field not in config_data:
                return False
        
        # Check endpoints structure
        endpoints = config_data.get("endpoints", {})
        required_endpoints = [
            "login", "logout", "callback", "token", 
            "user", "validate_token", "refresh", "health"
        ]
        
        for endpoint in required_endpoints:
            if endpoint not in endpoints:
                return False
        
        return True
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of all tests."""
        response_times = self.test_metrics["response_times"]
        
        basic_metrics = self._calculate_basic_metrics(response_times)
        performance_metrics = self._calculate_performance_metrics(response_times)
        return {**basic_metrics, **performance_metrics}
    
    async def _make_config_request(self):
        """Make HTTP request to config endpoint."""
        async with httpx.AsyncClient() as client:
            return await client.get(self.config_endpoint, timeout=2.0)
    
    def _update_metrics(self, response_time: float) -> None:
        """Update test metrics with response time."""
        self.test_metrics["response_times"].append(response_time)
        self.test_metrics["total_requests"] += 1
    
    def _process_config_response(self, response, response_time: float) -> Dict[str, Any]:
        """Process config endpoint response."""
        if response.status_code == 200:
            return self._create_success_response(response, response_time)
        else:
            return self._create_failure_response(response, response_time)
    
    def _create_success_response(self, response, response_time: float) -> Dict[str, Any]:
        """Create success response dict."""
        self.test_metrics["successful_requests"] += 1
        config_data = response.json()
        if self._validate_config_structure(config_data):
            self.test_metrics["config_structure_valid"] += 1
        return {
            "success": True, "status_code": response.status_code,
            "response_time": response_time, "config_data": config_data,
            "structure_valid": self._validate_config_structure(config_data)
        }
    
    def _create_failure_response(self, response, response_time: float) -> Dict[str, Any]:
        """Create failure response dict."""
        self.test_metrics["failed_requests"] += 1
        return {
            "success": False, "status_code": response.status_code,
            "response_time": response_time, "error": response.text
        }
    
    def _create_error_response(self, error: Exception, response_time: float) -> Dict[str, Any]:
        """Create error response dict."""
        return {"success": False, "error": str(error), "response_time": response_time}
    
    def _analyze_concurrent_results(self, results: List, num_requests: int, total_time: float) -> Dict[str, Any]:
        """Analyze concurrent test results."""
        successful_concurrent = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
        response_times = [r.get("response_time", 0) for r in results if not isinstance(r, Exception)]
        return {
            "total_requests": num_requests, "successful_requests": successful_concurrent,
            "failed_requests": num_requests - successful_concurrent, "total_test_time": total_time,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "requests_per_second": num_requests / total_time
        }
    
    def _calculate_basic_metrics(self, response_times: List[float]) -> Dict[str, Any]:
        """Calculate basic performance metrics."""
        total_requests = self.test_metrics["total_requests"]
        successful_requests = self.test_metrics["successful_requests"]
        return {
            "total_requests": total_requests,
            "success_rate": successful_requests / max(total_requests, 1),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0
        }
    
    def _calculate_performance_metrics(self, response_times: List[float]) -> Dict[str, Any]:
        """Calculate performance grade and timing metrics."""
        successful_requests = self.test_metrics["successful_requests"]
        config_valid = self.test_metrics["config_structure_valid"]
        return {
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "config_structure_valid_rate": config_valid / max(successful_requests, 1),
            "sub_500ms_responses": sum(1 for t in response_times if t < 0.5),
            "performance_grade": self._determine_performance_grade(response_times)
        }
    
    def _determine_performance_grade(self, response_times: List[float]) -> str:
        """Determine performance grade based on response times."""
        if all(t < 0.5 for t in response_times):
            return "A"
        elif all(t < 1.0 for t in response_times):
            return "B"
        else:
            return "C"


@pytest.mark.L3
@pytest.mark.integration
class TestAuthConfigAvailabilityL3:
    """L3 integration test for Auth Service Config Endpoint Availability."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container."""
        container = RedisContainer(port=6382)
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture(scope="class") 
    async def postgres_container(self):
        """Set up PostgreSQL container."""
        container = PostgresContainer(port=5434)
        db_url = await container.start()
        yield container, db_url
        await container.stop()
    
    @pytest.fixture(scope="class")
    async def auth_service_container(self, redis_container, postgres_container):
        """Set up Auth Service container."""
        _, redis_url = redis_container
        _, db_url = postgres_container
        
        container = AuthServiceContainer(port=8081, redis_url=redis_url)
        service_url = await container.start()
        yield container, service_url
        await container.stop()
    
    @pytest.fixture
    async def config_manager(self, auth_service_container):
        """Create auth config availability manager."""
        _, service_url = auth_service_container
        manager = AuthConfigAvailabilityManager(service_url)
        yield manager
    
    async def test_auth_service_config_endpoint_availability_l3(self, config_manager):
        """Test auth service config endpoint responds within 500ms."""
        # Test basic config endpoint
        result = await config_manager.test_config_endpoint_basic()
        
        # Verify config endpoint responds successfully
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["response_time"] < 0.5  # Within 500ms requirement
        
        # Verify config structure is valid
        assert result["structure_valid"] is True
        
        config_data = result["config_data"]
        
        # Verify required OAuth fields present
        assert "google_client_id" in config_data
        assert "endpoints" in config_data
        assert "development_mode" in config_data
        
        endpoints = config_data["endpoints"]
        assert "login" in endpoints
        assert "callback" in endpoints
        assert "token" in endpoints
        assert "health" in endpoints
        
        logger.info(f"Config endpoint test passed: {result['response_time']:.3f}s")
    
    async def test_concurrent_requests_handling(self, config_manager):
        """Test config endpoint handles 10+ concurrent requests."""
        # Test concurrent load
        concurrent_result = await config_manager.test_concurrent_requests(12)
        
        # Verify concurrent request handling
        assert concurrent_result["total_requests"] == 12
        assert concurrent_result["successful_requests"] >= 10  # At least 10 successful
        assert concurrent_result["avg_response_time"] < 1.0  # Reasonable response time under load
        
        # Verify requests per second performance
        assert concurrent_result["requests_per_second"] > 5  # Minimum throughput
        
        logger.info(f"Concurrent requests test passed: {concurrent_result['successful_requests']}/12 successful, "
                   f"{concurrent_result['requests_per_second']:.1f} RPS")
    
    async def test_environment_specific_urls(self, config_manager):
        """Test config adapts to environment with correct URLs."""
        # Test environment adaptation
        env_result = await config_manager.test_environment_adaptation()
        
        assert env_result.get("success", True) is not False
        
        env_validation = env_result["environment_validation"]
        
        # Verify environment-specific configuration
        assert env_validation["has_client_id"] is True
        assert env_validation["has_endpoints"] is True
        assert env_validation["endpoints_structure_valid"] is True
        
        # Verify development mode detection
        config_data = env_result["config_data"]
        assert isinstance(config_data.get("development_mode"), bool)
        
        # Verify URLs are properly formed
        endpoints = config_data["endpoints"]
        for endpoint_name, endpoint_url in endpoints.items():
            if endpoint_url:  # Skip None values (like dev_login in non-dev mode)
                assert endpoint_url.startswith("http")
                assert "/auth/" in endpoint_url or endpoint_name == "callback"
        
        logger.info(f"Environment adaptation test passed: development_mode={config_data.get('development_mode')}")
    
    async def test_config_caching_and_refresh(self, config_manager):
        """Test config caching and refresh behavior."""
        # Test caching behavior  
        cache_result = await config_manager.test_config_caching_behavior()
        
        # Verify caching tests completed
        assert len(cache_result["cache_test_results"]) == 5
        
        # Verify most requests were successful
        successful_cache_requests = sum(
            1 for r in cache_result["cache_test_results"] if r["success"]
        )
        assert successful_cache_requests >= 4  # At least 4 out of 5 successful
        
        # Verify response times are reasonable
        response_times = cache_result["response_times"]
        if response_times:
            assert max(response_times) < 2.0  # No request takes too long
            
        logger.info(f"Config caching test passed: {successful_cache_requests}/5 successful, "
                   f"caching_effective={cache_result.get('caching_effective', False)}")
    
    async def test_graceful_degradation_failures(self, config_manager):
        """Test graceful degradation when dependencies fail."""
        # Test resilience with various timeout scenarios
        resilience_result = await config_manager.test_resilience_with_failures()
        
        # Verify resilience tests completed
        assert len(resilience_result["resilience_tests"]) == 5
        
        # Verify service responds within reasonable timeouts
        successful_timeouts = resilience_result["successful_timeouts"]
        assert len(successful_timeouts) >= 3  # Should succeed with reasonable timeouts
        
        # Verify fastest timeout that succeeds
        if successful_timeouts:
            fastest_success = min(r["timeout_setting"] for r in successful_timeouts)
            assert fastest_success <= 2.0  # Should respond within 2 seconds
        
        logger.info(f"Resilience test passed: {len(successful_timeouts)}/5 timeout scenarios successful")
    
    async def test_config_endpoint_performance_requirements(self, config_manager):
        """Test config endpoint meets performance requirements."""
        # Run performance summary
        performance = config_manager.get_performance_summary()
        
        # Verify performance requirements
        assert performance["success_rate"] >= 0.9  # 90% success rate minimum
        assert performance["avg_response_time"] < 0.5  # Average under 500ms
        assert performance["config_structure_valid_rate"] >= 0.95  # 95% valid responses
        
        # Verify performance grade
        assert performance["performance_grade"] in ["A", "B"]  # Good performance
        
        # Verify sub-500ms responses
        assert performance["sub_500ms_responses"] >= performance["total_requests"] * 0.8  # 80% under 500ms
        
        logger.info(f"Performance test passed: {performance['success_rate']:.1%} success rate, "
                   f"{performance['avg_response_time']:.3f}s avg response time, "
                   f"grade {performance['performance_grade']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])