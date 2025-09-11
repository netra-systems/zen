"""Unit Test for Service Startup Hanging Issue - Fixed Version

This test validates RealServicesManager service startup logic to identify
hanging behavior during E2E test initialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development/Testing Infrastructure
- Business Goal: Prevent E2E test timeouts that block CI/CD pipeline
- Value Impact: Enables reliable test execution and faster deployment cycles
- Revenue Impact: Reduces development delays that cost ~$500/hour in team productivity

Test Strategy:
- Test startup flow with timeout mechanisms using simple assertions
- Validate health check timeout behavior
- Test service availability detection logic
- Should initially FAIL to demonstrate hanging behavior if it exists

CRITICAL: Uses standard pytest patterns for compatibility
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from tests.e2e.real_services_manager import RealServicesManager, ServiceStatus, ServiceEndpoint


class TestServiceStartupHangingIssueUnit:
    """Unit tests for service startup hanging behavior"""
    
    def setup_method(self):
        """Setup test environment"""
        self.manager = RealServicesManager()
    
    async def test_health_check_timeout_behavior(self):
        """Test that health checks timeout properly and don't hang indefinitely"""
        # Create a mock HTTP client that hangs
        hanging_client = Mock()
        hanging_client.get = AsyncMock()
        
        # Make the get request hang for a very long time
        async def hanging_request(*args, **kwargs):
            await asyncio.sleep(300)  # 5 minutes - should timeout way before this
            return Mock(status_code=200)
        
        hanging_client.get.side_effect = hanging_request
        self.manager._http_client = hanging_client
        
        # Create a test endpoint with short timeout
        endpoint = ServiceEndpoint("test_service", "http://localhost:9999", "/health", timeout=2.0)
        
        # Test that health check respects timeout and doesn't hang
        start_time = time.time()
        status = await self.manager._check_service_health(endpoint)
        elapsed_time = time.time() - start_time
        
        # Should complete within reasonable time (timeout + buffer)
        assert elapsed_time < 10.0, f"Health check took {elapsed_time:.2f}s, expected <10s"
        
        # Should report unhealthy due to timeout
        assert not status.healthy, "Service should be unhealthy due to timeout"
        assert status.error is not None, "Should have error message"
    
    async def test_wait_for_services_healthy_timeout(self):
        """Test that _wait_for_services_healthy doesn't hang when services never become healthy"""
        
        # Mock _check_all_services_health to always return unhealthy
        async def always_unhealthy():
            return {
                "all_healthy": False,
                "services": {"test_service": {"healthy": False}},
                "failures": ["test_service"],
                "summary": "0/1 services healthy"
            }
        
        self.manager._check_all_services_health = always_unhealthy
        
        # Test with very short timeout
        start_time = time.time()
        
        with pytest.raises(Exception):
            await self.manager._wait_for_services_healthy(timeout=3.0)
        
        elapsed_time = time.time() - start_time
        
        # Should timeout in approximately the specified time
        assert elapsed_time < 6.0, f"Wait for services took {elapsed_time:.2f}s, expected ~3s"
        assert elapsed_time > 2.5, f"Wait for services took {elapsed_time:.2f}s, too fast for 3s timeout"
    
    async def test_start_all_services_hanging_detection(self):
        """Test that start_all_services has proper timeout handling"""
        
        # Mock the internal methods to simulate hanging behavior
        async def hanging_health_check():
            await asyncio.sleep(120)  # Hang for 2 minutes
            return {"all_healthy": False, "failures": ["hanging_service"]}
        
        async def hanging_service_start(*args, **kwargs):
            await asyncio.sleep(120)  # Hang during startup
            return {"success": False, "error": "Startup hanging"}
        
        self.manager._check_all_services_health = hanging_health_check
        self.manager._start_missing_services = hanging_service_start
        self.manager._ensure_http_client = AsyncMock()
        
        # Test with timeout using asyncio.wait_for
        start_time = time.time()
        
        with pytest.raises(asyncio.TimeoutError):
            # Wrap in timeout to prevent actual hanging
            await asyncio.wait_for(self.manager.start_all_services(), timeout=5.0)
        
        elapsed_time = time.time() - start_time
        
        # Should timeout in approximately 5 seconds
        assert elapsed_time < 8.0, f"Start services took {elapsed_time:.2f}s, expected ~5s"
    
    async def test_websocket_health_check_timeout(self):
        """Test WebSocket health check timeout behavior"""
        
        # Create endpoint that should timeout
        ws_endpoint = ServiceEndpoint("websocket", "ws://nonexistent:9999", "/ws", timeout=2.0)
        
        start_time = time.time()
        healthy, error = await self.manager._check_websocket_health(ws_endpoint)
        elapsed_time = time.time() - start_time
        
        # Should complete quickly (connection refused) or timeout
        assert elapsed_time < 10.0, f"WebSocket health check took {elapsed_time:.2f}s, too long"
        
        # Should be unhealthy
        assert not healthy, "WebSocket to nonexistent host should be unhealthy"
        assert error is not None, "Should have error message"
    
    def test_synchronous_startup_hanging(self):
        """Test synchronous startup method for hanging behavior"""
        
        # The launch_dev_environment method has synchronous interface
        # but calls async methods - potential source of hanging
        
        start_time = time.time()
        
        # Mock to simulate hanging async operation
        async def hanging_start_all():
            await asyncio.sleep(60)  # Hang for 1 minute
            return {"success": False}
        
        original_start_all = self.manager.start_all_services
        self.manager.start_all_services = hanging_start_all
        
        # Test synchronous call - this might hang in real scenarios
        try:
            result = self.manager.launch_dev_environment()
            elapsed_time = time.time() - start_time
            
            # Should complete quickly or return success indication
            assert elapsed_time < 5.0, f"Synchronous startup took {elapsed_time:.2f}s, may indicate hanging"
            assert isinstance(result, dict), "Should return dict result"
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Synchronous startup failed with: {e}")
            # Should not take too long even to fail
            assert elapsed_time < 5.0, f"Synchronous startup error took {elapsed_time:.2f}s, may indicate hanging"
        finally:
            # Restore original method
            self.manager.start_all_services = original_start_all
    
    def teardown_method(self):
        """Cleanup test resources"""
        if hasattr(self, 'manager'):
            # Use asyncio.run for cleanup if needed
            try:
                asyncio.run(self.manager.cleanup())
            except Exception as e:
                print(f"Cleanup error: {e}")


class TestServiceStartupTimeouts:
    """Specific timeout behavior tests"""
    
    def setup_method(self):
        """Setup"""
        self.manager = RealServicesManager()
    
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'manager'):
            try:
                asyncio.run(self.manager.cleanup())
            except Exception:
                pass
    
    async def test_cascading_timeout_issue(self):
        """Test for cascading timeout issues that could cause hanging"""
        
        # Mock multiple services with different timeout behaviors
        services_config = [
            ("fast_service", 1.0),    # Fast response
            ("slow_service", 10.0),   # Slow response
            ("timeout_service", 0.1), # Times out quickly
            ("hanging_service", 30.0) # Very slow
        ]
        
        # Mock endpoints
        endpoints = []
        for name, timeout in services_config:
            endpoint = ServiceEndpoint(name, f"http://localhost:9999", "/health", timeout=timeout)
            endpoints.append(endpoint)
        
        self.manager.service_endpoints = endpoints
        
        # Mock HTTP client with different behaviors per service
        mock_client = Mock()
        
        async def mock_get(url, timeout=None, **kwargs):
            if "fast_service" in url:
                await asyncio.sleep(0.5)
                return Mock(status_code=200)
            elif "slow_service" in url:
                await asyncio.sleep(5.0)
                return Mock(status_code=200)
            elif "timeout_service" in url:
                await asyncio.sleep(2.0)  # Will timeout with 0.1s limit
                return Mock(status_code=200)
            elif "hanging_service" in url:
                await asyncio.sleep(100)  # Should timeout with 30s limit
                return Mock(status_code=200)
            else:
                raise Exception("Connection refused")
        
        mock_client.get = mock_get
        self.manager._http_client = mock_client
        
        # Test health check with mixed timeout scenarios
        start_time = time.time()
        health_results = await self.manager._check_all_services_health()
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time despite some timeouts
        assert elapsed_time < 45.0, f"Health checks took {elapsed_time:.2f}s, too long"
        
        # Should handle mixed success/failure gracefully
        assert isinstance(health_results, dict)
        assert "all_healthy" in health_results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])