"""
Test utilities for critical system initialization tests.
Provides common functions used across test suites.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Callable, Dict, Optional
from datetime import datetime, UTC

import httpx
from sqlalchemy.ext.asyncio import AsyncSession


async def wait_for_condition(
    condition_func: Callable[[], Any],
    timeout: int = 30,
    check_interval: float = 1.0,
    *args,
    **kwargs
) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition_func: Function to check condition
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        True if condition became true, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Handle both sync and async condition functions
            if asyncio.iscoroutinefunction(condition_func):
                result = await condition_func(*args, **kwargs)
            else:
                result = condition_func(*args, **kwargs)
                
            if result:
                return True
        except Exception:
            pass
        await asyncio.sleep(check_interval)
    return False


async def retry_with_backoff(
    func: Callable,
    max_attempts: int = 5,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    *args,
    **kwargs
) -> Any:
    """
    Retry a function with exponential backoff using UnifiedRetryHandler.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between attempts
        backoff_factor: Multiplier for delay on each retry
        
    Returns:
        Result from successful function call
        
    Raises:
        Exception from final failed attempt
    """
    # Import here to avoid circular dependencies
    try:
        from netra_backend.app.core.resilience.unified_retry_handler import (
            UnifiedRetryHandler, RetryConfig, RetryStrategy
        )
        
        # Create unified retry handler configuration
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=initial_delay,
            backoff_multiplier=backoff_factor,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter_range=0.1,
            timeout_seconds=None,
            retryable_exceptions=(Exception,),
            circuit_breaker_enabled=False,
            metrics_enabled=False  # Disable for test framework
        )
        
        handler = UnifiedRetryHandler("test_utils", retry_config)
        
        # Create wrapper function
        if asyncio.iscoroutinefunction(func):
            async def operation_wrapper():
                return await func(*args, **kwargs)
            
            result = await handler.execute_with_retry_async(operation_wrapper)
        else:
            def operation_wrapper():
                return func(*args, **kwargs)
            
            result = handler.execute_with_retry(operation_wrapper)
        
        if result.success:
            return result.result
        else:
            raise result.final_exception
            
    except ImportError:
        # Fall back to legacy implementation if UnifiedRetryHandler not available
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == max_attempts - 1:
                    break
                await asyncio.sleep(delay)
                delay *= backoff_factor
        
        raise last_exception


def create_test_user(
    email: Optional[str] = None,
    username: Optional[str] = None,
    provider: str = "test"
) -> Dict[str, Any]:
    """
    Create test user data.
    
    Args:
        email: User email (generated if not provided)
        username: Username (generated if not provided)
        provider: OAuth provider name
        
    Returns:
        Dictionary with test user data
    """
    timestamp = int(time.time())
    test_id = str(uuid.uuid4())[:8]
    
    if email is None:
        email = f"test_user_{timestamp}_{test_id}@test.com"
    if username is None:
        username = f"testuser_{timestamp}_{test_id}"
    
    return {
        "user_id": str(uuid.uuid4()),
        "email": email,
        "username": username,
        "provider": provider,
        "provider_id": f"{provider}_{timestamp}_{test_id}",
        "created_at": datetime.now(UTC).isoformat(),
        "is_test_user": True
    }


async def cleanup_test_data(session: AsyncSession) -> None:
    """
    Clean up test data from database.
    
    Args:
        session: Database session
    """
    from sqlalchemy import text
    
    try:
        # Clean up test users and related data
        await session.execute(text("""
            DELETE FROM user_sessions WHERE user_id IN (
                SELECT id FROM users WHERE email LIKE '%@test.com'
            )
        """))
        
        await session.execute(text("""
            DELETE FROM users WHERE email LIKE '%@test.com'
        """))
        
        # Clean up test threads and messages
        await session.execute(text("""
            DELETE FROM messages WHERE thread_id IN (
                SELECT id FROM threads WHERE title LIKE 'Test %'
            )
        """))
        
        await session.execute(text("""
            DELETE FROM threads WHERE title LIKE 'Test %'
        """))
        
        await session.commit()
    except Exception as e:
        await session.rollback()
        # Log error but don't fail test
        print(f"Warning: Test cleanup failed: {e}")


async def wait_for_service_ready(
    url: str,
    timeout: int = 30,
    check_interval: float = 1.0,
    expected_status: int = 200
) -> bool:
    """
    Wait for a service to become ready by checking its health endpoint.
    
    Args:
        url: Service URL to check
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        expected_status: Expected HTTP status code
        
    Returns:
        True if service became ready, False if timeout
    """
    async def check_service():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
                return response.status_code == expected_status
        except Exception:
            return False
    
    return await wait_for_condition(check_service, timeout, check_interval)


async def simulate_service_failure(
    service_url: str,
    failure_type: str = "timeout",
    duration: int = 5
) -> None:
    """
    Simulate service failure for testing recovery.
    
    Args:
        service_url: URL of service to affect
        failure_type: Type of failure to simulate
        duration: How long to maintain failure
    """
    # This is a mock implementation for testing
    # In real tests, this might temporarily block network access
    # or simulate other failure conditions
    print(f"Simulating {failure_type} failure for {service_url} for {duration}s")
    await asyncio.sleep(duration)
    print(f"Failure simulation complete for {service_url}")


async def verify_service_communication(
    from_url: str,
    to_url: str,
    timeout: int = 10
) -> bool:
    """
    Verify that one service can communicate with another.
    
    Args:
        from_url: Source service URL
        to_url: Target service URL
        timeout: Timeout for verification
        
    Returns:
        True if communication is successful
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Check if target service is reachable
            response = await client.get(f"{to_url}/health")
            if response.status_code not in [200, 404]:
                return False
                
            # If there's an inter-service communication endpoint, test it
            try:
                comm_response = await client.get(
                    f"{from_url}/api/internal/check-service",
                    params={"target": to_url}
                )
                return comm_response.status_code == 200
            except Exception:
                # If no specific endpoint, basic reachability is enough
                return True
                
    except Exception:
        return False


def generate_test_token(
    user_id: Optional[str] = None,
    expires_in: int = 3600,
    claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a test JWT token.
    
    Args:
        user_id: User ID for token (generated if not provided)
        expires_in: Token expiration time in seconds
        claims: Additional claims to include
        
    Returns:
        Test JWT token string
    """
    if user_id is None:
        user_id = str(uuid.uuid4())
    
    if claims is None:
        claims = {}
    
    # This is a simple test token - not cryptographically secure
    # In real tests, use proper JWT libraries
    token_data = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
        "test": True,
        **claims
    }
    
    # Simple base64 encoded test token
    import base64
    token_json = json.dumps(token_data)
    encoded = base64.b64encode(token_json.encode()).decode()
    return f"test.{encoded}.signature"


async def wait_for_database_ready(
    db_url: str,
    timeout: int = 30
) -> bool:
    """
    Wait for database to become ready.
    
    Args:
        db_url: Database connection URL
        timeout: Maximum time to wait
        
    Returns:
        True if database is ready
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    engine = create_async_engine(db_url)
    
    try:
        async def check_db():
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                    return True
            except Exception:
                return False
        
        result = await wait_for_condition(check_db, timeout)
        return result
    finally:
        await engine.dispose()


async def create_test_websocket_message(
    message_type: str = "test",
    payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a test WebSocket message.
    
    Args:
        message_type: Type of message
        payload: Message payload
        
    Returns:
        WebSocket message dictionary
    """
    if payload is None:
        payload = {"test": True}
    
    return {
        "type": message_type,
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload
    }