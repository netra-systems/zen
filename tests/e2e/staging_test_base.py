"""
Base class for staging environment tests.
Provides common functionality for all staging E2E tests.
"""

import asyncio
import pytest
import httpx
import websockets
import json
import time
import functools
from typing import Optional, Dict, Any, Callable
from tests.e2e.staging_test_config import get_staging_config, is_staging_available


def track_test_timing(test_func: Callable) -> Callable:
    """Decorator to track test execution time and fail on 0-second e2e tests.
    
    CRITICAL: All e2e tests that return in 0 seconds are automatic hard failures.
    This indicates tests are not actually executing or are being mocked.
    See reports/staging/STAGING_100_TESTS_REPORT.md
    """
    @functools.wraps(test_func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        test_name = test_func.__name__
        
        try:
            # Run the actual test
            result = await test_func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.perf_counter() - start_time
            
            # CRITICAL: Fail any e2e test that executes in under 0.01 seconds
            if execution_time < 0.01:
                pytest.fail(
                    f"\n{'='*60}\n"
                    f" ALERT:  E2E TEST FAILED: ZERO-SECOND EXECUTION\n"
                    f"{'='*60}\n"
                    f"Test: {test_name}\n"
                    f"Execution Time: {execution_time:.4f}s\n\n"
                    f"This test executed in effectively 0 seconds, indicating:\n"
                    f"  - Test is not actually running\n"
                    f"  - Test is being skipped/mocked\n"
                    f"  - Missing async/await handling\n"
                    f"  - Not connecting to real staging services\n\n"
                    f"ALL E2E TESTS MUST:\n"
                    f"  1. Connect to real staging services\n"
                    f"  2. Perform actual network I/O\n"
                    f"  3. Use proper authentication (JWT/OAuth)\n"
                    f"  4. Take measurable time to execute\n\n"
                    f"See STAGING_100_TESTS_REPORT.md for context\n"
                    f"{'='*60}"
                )
            
            # Warn if test is suspiciously fast (under 0.1 seconds)
            elif execution_time < 0.1:
                print(
                    f"\n WARNING: [U+FE0F]  WARNING: Test '{test_name}' executed in {execution_time:.3f}s\n"
                    f"   This is suspiciously fast for an e2e test connecting to staging.\n"
                    f"   Verify the test is actually performing real operations.\n"
                )
            
            # Log normal execution time
            else:
                print(f"[[U+2713]] Test '{test_name}' completed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            print(f"[[U+2717]] Test '{test_name}' failed after {execution_time:.2f}s: {e}")
            raise
    
    return wrapper


class StagingTestBase:
    """Base class for staging environment tests
    
    CRITICAL: All e2e tests MUST take measurable time to execute.
    Tests returning in 0 seconds are automatic hard failures.
    """
    
    @classmethod
    def setup_class(cls):
        """Setup for test class"""
        # CRITICAL FIX: Load staging environment variables for JWT authentication
        cls._load_staging_environment()
        
        cls.config = get_staging_config()
        cls.client = None
        cls.websocket = None
        
        # Check if staging is available and adapt behavior
        if not is_staging_available():
            import logging
            logging.warning("Staging environment is not available - tests will run with local/stub services")
            cls.use_stub_services = True
        else:
            cls.use_stub_services = False
    
    @classmethod
    def _load_staging_environment(cls):
        """Load staging environment variables from config/staging.env
        
        CRITICAL FIX: This ensures staging tests have access to JWT_SECRET_STAGING
        and other staging-specific configuration needed for proper authentication.
        """
        import os
        from pathlib import Path
        
        # Find config/staging.env file
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir
        while project_root.parent != project_root:
            staging_env_file = project_root / "config" / "staging.env"
            if staging_env_file.exists():
                break
            project_root = project_root.parent
        else:
            # Try one more time from current working directory
            project_root = Path.cwd()
            staging_env_file = project_root / "config" / "staging.env"
        
        if staging_env_file.exists():
            print(f"Loading staging environment from: {staging_env_file}")
            
            # Parse .env file manually (simple key=value format)
            with open(staging_env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Only set if not already in environment (don't override)
                        if key not in os.environ:
                            os.environ[key] = value
                            if key == "JWT_SECRET_STAGING":
                                print(f"Loaded JWT_SECRET_STAGING from config/staging.env")
            
            # Ensure ENVIRONMENT is set to staging
            os.environ["ENVIRONMENT"] = "staging"
            print(f"Set ENVIRONMENT=staging for staging tests")
            
        else:
            print(f"WARNING: config/staging.env not found at {staging_env_file}")
            print("Staging tests may fail due to missing environment variables")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after test class"""
        if cls.client:
            asyncio.run(cls.client.aclose())
        if cls.websocket:
            asyncio.run(cls.websocket.close())
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client for API calls"""
        if not self.client:
            self.client = httpx.AsyncClient(
                base_url=self.config.backend_url,
                timeout=self.config.timeout,
                headers=self.config.get_headers()
            )
        return self.client
    
    async def get_websocket_connection(self) -> websockets.ClientConnection:
        """Get WebSocket connection"""
        if not self.websocket:
            headers = self.config.get_websocket_headers()
            try:
                self.websocket = await websockets.connect(
                    self.config.websocket_url,
                    extra_headers=headers if headers else None
                )
            except Exception as e:
                if self.config.skip_websocket_auth:
                    import logging
                    logging.warning(f"WebSocket requires authentication: {e} - using stub connection")
                    # Create stub WebSocket for testing
                    class StubWebSocket:
                        async def send(self, message):
                            logging.info(f"[STUB] Would send WebSocket message: {message}")
                        async def recv(self):
                            return '{"type":"stub","message":"authentication not available"}'
                        async def close(self):
                            pass
                    self.websocket = StubWebSocket()
                else:
                    raise
        return self.websocket
    
    async def call_api(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: Optional[Dict[str, Any]] = None,
        include_auth: bool = False
    ) -> httpx.Response:
        """Call API endpoint"""
        client = await self.get_http_client()
        
        headers = self.config.get_headers(include_auth)
        
        if method == "GET":
            response = await client.get(endpoint, headers=headers)
        elif method == "POST":
            response = await client.post(endpoint, json=json_data, headers=headers)
        elif method == "PUT":
            response = await client.put(endpoint, json=json_data, headers=headers)
        elif method == "DELETE":
            response = await client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    
    async def send_websocket_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Send WebSocket message and wait for response"""
        ws = await self.get_websocket_connection()
        
        await ws.send(json.dumps(message))
        
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=self.config.timeout)
            return response
        except asyncio.TimeoutError:
            return None
    
    async def verify_health(self):
        """Verify backend health"""
        response = await self.call_api("/health")
        print(f"[DEBUG] Base health response status: {response.status_code}")
        print(f"[DEBUG] Base health response headers: {dict(response.headers)}")
        try:
            response_text = response.text
            print(f"[DEBUG] Base health response content: {response_text[:500]}")
        except:
            print("[DEBUG] Could not read response content")
        assert response.status_code == 200, f"Base health check failed with status {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy"
        return True
    
    async def verify_api_health(self):
        """Verify API health"""
        response = await self.call_api("/api/health")
        print(f"[DEBUG] API health response status: {response.status_code}")
        print(f"[DEBUG] API health response headers: {dict(response.headers)}")
        try:
            response_text = response.text
            print(f"[DEBUG] API health response content: {response_text[:500]}")
        except:
            print("[DEBUG] Could not read response content")
        assert response.status_code == 200, f"API health check failed with status {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy"
        return True
    
    def assert_websocket_event(self, event: str, event_type: str):
        """Assert WebSocket event structure"""
        try:
            data = json.loads(event)
            assert "type" in data, f"Missing 'type' field in event: {data}"
            assert data["type"] == event_type, f"Expected type '{event_type}', got '{data['type']}'"
            return data
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON in WebSocket event: {event}")
    
    async def wait_for_websocket_event(
        self,
        event_type: str,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Wait for specific WebSocket event type"""
        ws = await self.get_websocket_connection()
        timeout = timeout or self.config.timeout
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=1)
                data = json.loads(response)
                if data.get("type") == event_type:
                    return data
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
        
        return None


# Decorator to mark tests as staging tests
def staging_test(func):
    """Decorator to mark and configure staging tests"""
    @pytest.mark.staging
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not is_staging_available(),
        reason="Staging environment is not available"
    )
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper