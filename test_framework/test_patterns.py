"""
Test patterns for L3/L4 integration tests.

This module provides base test classes for integration testing with common
patterns and utilities that L3 and L4 tests need.
"""

import asyncio
import json
import uuid
import aiohttp
import pytest
from typing import Dict, Any, Optional, List
from datetime import datetime
import os


class BaseIntegrationTest:
    """Base class for integration tests with common utilities."""
    
    def __init__(self):
        self._setup_backend_url()
        self._test_users: List[Dict[str, Any]] = []
        self._test_threads: List[str] = []
        
    def _setup_backend_url(self):
        """Setup backend URL based on environment."""
        # Check for staging environment
        if os.getenv("ENVIRONMENT") == "staging":
            self.backend_url = os.getenv("STAGING_API_URL", "https://api.staging.netrasystems.ai")
        elif os.getenv("DEV_MODE") == "true":
            self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
        else:
            # Default test environment
            self.backend_url = "http://localhost:8001"
    
    async def create_test_user(self, email: str, tier: str = "free") -> Dict[str, Any]:
        """Create a test user for integration testing."""
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "username": email.split("@")[0],
            "tier": tier,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True
        }
        
        # Store for cleanup
        self._test_users.append(user_data)
        
        # In real implementation, this would create user via API
        # For now, return mock user data that tests can use
        return user_data
    
    async def get_auth_token(self, user_data: Dict[str, Any]) -> str:
        """Get authentication token for a user."""
        # In real implementation, this would call auth service
        # For now, return a mock JWT-like token
        import time
        import jwt
        
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "tier": user_data["tier"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour expiry
            "iss": "netra-test-auth",
            "aud": "netra-api"
        }
        
        # Use test secret
        secret = os.getenv("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars")
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        return token
    
    async def create_test_thread(self, token: str, title: str = "Test Thread") -> str:
        """Create a test thread and return its ID."""
        async with aiohttp.ClientSession() as session:
            thread_data = {"title": title}
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads",
                json=thread_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                if resp.status == 201:
                    thread = await resp.json()
                    thread_id = thread["id"]
                    self._test_threads.append(thread_id)
                    return thread_id
                else:
                    raise Exception(f"Failed to create thread: {resp.status}")
    
    async def cleanup_test_resources(self):
        """Cleanup test resources created during testing."""
        # In real implementation, this would clean up users, threads, etc.
        # For now, just clear the tracking lists
        self._test_users.clear()
        self._test_threads.clear()


class L3IntegrationTest(BaseIntegrationTest):
    """
    L3 Integration Test base class.
    
    L3 tests focus on:
    - Service-to-service integration
    - API endpoint testing
    - Database operations
    - Real service interactions (but with test data)
    - Error handling and recovery
    """
    
    def __init__(self):
        super().__init__()
        self.test_level = "L3"
        self.timeout = 300  # 5 minutes default timeout for L3 tests
    
    async def setup_method(self):
        """Setup method called before each test method."""
        # Override in subclasses for specific setup
        pass
    
    async def teardown_method(self):
        """Teardown method called after each test method."""
        await self.cleanup_test_resources()
    
    async def wait_for_processing(self, check_func, max_attempts: int = 10, 
                                delay: float = 1.0) -> Any:
        """
        Wait for asynchronous processing to complete.
        
        Args:
            check_func: Async function that returns result when ready
            max_attempts: Maximum number of attempts
            delay: Delay between attempts in seconds
            
        Returns:
            Result from check_func when successful
            
        Raises:
            TimeoutError: If max_attempts reached without success
        """
        for attempt in range(max_attempts):
            try:
                result = await check_func()
                if result:
                    return result
            except Exception:
                pass
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
        
        raise TimeoutError(f"Operation did not complete within {max_attempts} attempts")
    
    async def verify_api_response(self, response, expected_status: int = 200,
                                required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Verify API response meets expectations.
        
        Args:
            response: aiohttp response object
            expected_status: Expected HTTP status code
            required_fields: List of required fields in response JSON
            
        Returns:
            Parsed JSON response
            
        Raises:
            AssertionError: If response doesn't meet expectations
        """
        assert response.status == expected_status, f"Expected status {expected_status}, got {response.status}"
        
        try:
            data = await response.json()
        except Exception as e:
            raise AssertionError(f"Failed to parse JSON response: {e}")
        
        if required_fields:
            for field in required_fields:
                assert field in data, f"Required field '{field}' missing from response"
        
        return data
    
    async def send_message_and_wait(self, token: str, thread_id: str, 
                                  message_content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message to a thread and wait for processing.
        
        Args:
            token: Authentication token
            thread_id: Thread ID to send message to
            message_content: Message content
            **kwargs: Additional message parameters
            
        Returns:
            Final message state after processing
        """
        async with aiohttp.ClientSession() as session:
            # Send message
            message_data = {
                "content": message_content,
                **kwargs
            }
            
            async with session.post(
                f"{self.backend_url}/api/v1/threads/{thread_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 201, f"Failed to send message: {resp.status}"
                message = await resp.json()
                message_id = message["id"]
            
            # Wait for processing
            async def check_message_status():
                async with session.get(
                    f"{self.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    if resp.status == 200:
                        msg = await resp.json()
                        if msg["status"] in ["completed", "error", "timeout"]:
                            return msg
                return None
            
            return await self.wait_for_processing(check_message_status)


class L4IntegrationTest(BaseIntegrationTest):
    """
    L4 Integration Test base class.
    
    L4 tests focus on:
    - End-to-end user workflows
    - Cross-service integration
    - Production-like scenarios
    - Performance validation
    - Real environment testing (staging)
    - Business critical path validation
    """
    
    def __init__(self):
        super().__init__()
        self.test_level = "L4"
        self.timeout = 600  # 10 minutes default timeout for L4 tests
        self._session_metrics = {
            "start_time": None,
            "operations": [],
            "errors": [],
            "performance_metrics": {}
        }
    
    async def setup_method(self):
        """Setup method called before each test method."""
        self._session_metrics["start_time"] = datetime.utcnow()
        # Override in subclasses for specific setup
        pass
    
    async def teardown_method(self):
        """Teardown method called after each test method."""
        await self.cleanup_test_resources()
        await self._log_session_metrics()
    
    async def _log_session_metrics(self):
        """Log session metrics for L4 test analysis."""
        if self._session_metrics["start_time"]:
            duration = datetime.utcnow() - self._session_metrics["start_time"]
            print(f"L4 Test Session Duration: {duration.total_seconds():.2f}s")
            print(f"Operations Performed: {len(self._session_metrics['operations'])}")
            if self._session_metrics["errors"]:
                print(f"Errors Encountered: {len(self._session_metrics['errors'])}")
    
    def track_operation(self, operation_name: str, **kwargs):
        """Track an operation for metrics collection."""
        self._session_metrics["operations"].append({
            "name": operation_name,
            "timestamp": datetime.utcnow().isoformat(),
            "details": kwargs
        })
    
    def track_error(self, error: Exception, context: str = ""):
        """Track an error for metrics collection."""
        self._session_metrics["errors"].append({
            "error": str(error),
            "type": type(error).__name__,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def execute_user_workflow(self, workflow_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a complete user workflow with tracking.
        
        Args:
            workflow_steps: List of workflow steps to execute
            
        Returns:
            Workflow execution results
        """
        results = {
            "success": True,
            "steps": [],
            "total_duration": 0,
            "errors": []
        }
        
        workflow_start = datetime.utcnow()
        
        for i, step in enumerate(workflow_steps):
            step_start = datetime.utcnow()
            step_name = step.get("name", f"step_{i}")
            
            try:
                self.track_operation(f"workflow_step_{step_name}", step=step)
                
                # Execute step - this would be customized per workflow
                step_result = await self._execute_workflow_step(step)
                
                step_duration = (datetime.utcnow() - step_start).total_seconds()
                
                results["steps"].append({
                    "name": step_name,
                    "success": True,
                    "duration": step_duration,
                    "result": step_result
                })
                
            except Exception as e:
                self.track_error(e, f"workflow_step_{step_name}")
                step_duration = (datetime.utcnow() - step_start).total_seconds()
                
                results["steps"].append({
                    "name": step_name,
                    "success": False,
                    "duration": step_duration,
                    "error": str(e)
                })
                
                results["errors"].append(str(e))
                results["success"] = False
        
        results["total_duration"] = (datetime.utcnow() - workflow_start).total_seconds()
        return results
    
    async def _execute_workflow_step(self, step: Dict[str, Any]) -> Any:
        """
        Execute a single workflow step.
        
        This is a basic implementation - subclasses should override for specific workflows.
        """
        step_type = step.get("type", "unknown")
        
        if step_type == "create_user":
            return await self.create_test_user(step["email"], step.get("tier", "free"))
        elif step_type == "get_token":
            return await self.get_auth_token(step["user"])
        elif step_type == "create_thread":
            return await self.create_test_thread(step["token"], step.get("title", "Test Thread"))
        else:
            raise NotImplementedError(f"Workflow step type '{step_type}' not implemented")
    
    async def validate_performance_sla(self, operation_name: str, max_duration: float,
                                     actual_duration: float) -> bool:
        """
        Validate that operation meets performance SLA.
        
        Args:
            operation_name: Name of the operation
            max_duration: Maximum allowed duration in seconds
            actual_duration: Actual duration in seconds
            
        Returns:
            True if SLA is met, False otherwise
        """
        meets_sla = actual_duration <= max_duration
        
        self._session_metrics["performance_metrics"][operation_name] = {
            "max_duration": max_duration,
            "actual_duration": actual_duration,
            "meets_sla": meets_sla,
            "overhead_percent": ((actual_duration - max_duration) / max_duration * 100) if not meets_sla else 0
        }
        
        return meets_sla
    
    async def test_concurrent_operations(self, operations: List[Any], max_concurrent: int = 5) -> Dict[str, Any]:
        """
        Test concurrent operations for L4 performance validation.
        
        Args:
            operations: List of async operations to run concurrently
            max_concurrent: Maximum number of concurrent operations
            
        Returns:
            Concurrent execution results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(operation):
            async with semaphore:
                start_time = datetime.utcnow()
                try:
                    result = await operation
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    return {"success": True, "result": result, "duration": duration}
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    return {"success": False, "error": str(e), "duration": duration}
        
        results = await asyncio.gather(*[run_with_semaphore(op) for op in operations])
        
        successful = sum(1 for r in results if r["success"])
        total_duration = max(r["duration"] for r in results)
        avg_duration = sum(r["duration"] for r in results) / len(results)
        
        return {
            "total_operations": len(operations),
            "successful_operations": successful,
            "success_rate": successful / len(operations),
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "results": results
        }


# Pytest fixtures for L3/L4 tests
@pytest.fixture
async def l3_test_base():
    """Fixture providing L3 integration test base."""
    test_instance = L3IntegrationTest()
    await test_instance.setup_method()
    yield test_instance
    await test_instance.teardown_method()


@pytest.fixture  
async def l4_test_base():
    """Fixture providing L4 integration test base."""
    test_instance = L4IntegrationTest()
    await test_instance.setup_method()
    yield test_instance
    await test_instance.teardown_method()


# Utility functions for test patterns
def require_environment(env_name: str):
    """Decorator to skip tests if required environment is not available."""
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            if os.getenv("ENVIRONMENT") != env_name:
                pytest.skip(f"Test requires {env_name} environment")
            return test_func(*args, **kwargs)
        return wrapper
    return decorator


def require_real_services():
    """Decorator to skip tests if real services are not available."""
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            if os.getenv("ENABLE_REAL_LLM_TESTING") != "true":
                pytest.skip("Test requires real services (ENABLE_REAL_LLM_TESTING=true)")
            return test_func(*args, **kwargs)
        return wrapper
    return decorator


def timeout_test(seconds: int):
    """Decorator to set timeout for individual test methods."""
    def decorator(test_func):
        @pytest.mark.timeout(seconds)
        def wrapper(*args, **kwargs):
            return test_func(*args, **kwargs)
        return wrapper
    return decorator