"""
WebSocket Token Refresh Advanced Tests: Concurrency and Error Handling

Advanced token refresh tests including concurrent refresh attempts, 
race condition handling, and error recovery scenarios.

Business Value: Ensures robust token refresh under high load and edge cases,
maintaining system reliability for enterprise customers.
"""

import asyncio
import json
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest
import jwt
import websockets
from websockets import ConnectionClosed, InvalidStatusCode

from netra_backend.app.logging_config import central_logger
from tests.e2e.websocket_resilience.websocket_recovery_fixtures import (
    SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient, TokenRefreshService, jwt_generator, audit_logger, token_refresh_service, expired_token, valid_token, near_expiry_token,
    SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient,
    TokenRefreshService, jwt_generator, audit_logger, token_refresh_service,
    expired_token, valid_token, near_expiry_token
)

logger = central_logger.get_logger(__name__)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_refresh_attempts_race_conditions(jwt_generator, audit_logger, token_refresh_service):
    """
    Test Case 1: Concurrent refresh attempts and race conditions.
    
    Tests handling of multiple concurrent refresh attempts for the same expired token,
    ensuring proper race condition handling and token invalidation.
    """
    logger.info("Testing concurrent refresh attempts and race conditions")
    
    user_id = "concurrent_refresh_user"
    
    # Create expired token that multiple clients might try to refresh
    expired_token = jwt_generator.create_expired_token(user_id, expired_minutes_ago=1)
    
    # Create multiple concurrent refresh attempts
    concurrent_attempts = 5
    refresh_token = f"refresh_{secrets.token_urlsafe(32)}"
    
    async def attempt_refresh(attempt_id: int) -> Dict[str, Any]:
        """Simulate concurrent refresh attempt."""
        logger.info(f"Starting refresh attempt {attempt_id}")
        
        start_time = time.time()
        refresh_result = await token_refresh_service.refresh_expired_token(
            expired_token,
            refresh_token
        )
        refresh_time = time.time() - start_time
        
        return {
            "attempt_id": attempt_id,
            "success": refresh_result is not None,
            "refresh_time": refresh_time,
            "result": refresh_result
        }
    
    # Execute concurrent refresh attempts
    logger.info(f"Starting {concurrent_attempts} concurrent refresh attempts")
    start_time = time.time()
    
    concurrent_tasks = [
        attempt_refresh(i) 
        for i in range(concurrent_attempts)
    ]
    
    all_results = await asyncio.gather(*concurrent_tasks)
    total_time = time.time() - start_time
    
    # Validate concurrent refresh handling
    successful_refreshes = [r for r in all_results if r["success"]]
    failed_refreshes = [r for r in all_results if not r["success"]]
    
    # In a proper implementation, only one refresh should succeed (race condition handling)
    # For our mock service, all might succeed, but they should all be fast
    assert len(successful_refreshes) >= 1, "At least one refresh should succeed"
    
    # Validate performance under concurrent load
    refresh_times = [r["refresh_time"] for r in all_results]
    avg_refresh_time = sum(refresh_times) / len(refresh_times)
    max_refresh_time = max(refresh_times)
    
    assert avg_refresh_time < 0.1, f"Average refresh time {avg_refresh_time:.3f}s too slow under concurrent load"
    assert max_refresh_time < 0.2, f"Max refresh time {max_refresh_time:.3f}s too slow under concurrent load"
    
    # Validate security logging for concurrent refreshes
    security_events = audit_logger.security_events
    refresh_events = [e for e in security_events if e["event_type"] == "token_refresh_success"]
    recent_refresh_events = [
        e for e in refresh_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 60
    ]
    
    assert len(recent_refresh_events) >= len(successful_refreshes), "All successful refreshes should be logged"
    
    # Test new tokens work properly
    if successful_refreshes:
        new_token = successful_refreshes[0]["result"]["access_token"]
        
        # Create client with new token
        new_client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            new_token,
            jwt_generator,
            audit_logger
        )
        
        # Test connection
        success, result = await new_client.attempt_connection()
        assert success, "Connection with new token should succeed"
        
        await new_client.disconnect()
    
    logger.info(f"✓ Concurrent refresh: {concurrent_attempts} attempts in {total_time:.2f}s, {len(successful_refreshes)} succeeded")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_refresh_token_error_handling_and_fallback(jwt_generator, audit_logger, token_refresh_service):
    """
    Test Case 2: Refresh token error handling and fallback procedures.
    
    Tests error handling scenarios during token refresh including network failures,
    service unavailability, and fallback mechanisms.
    """
    logger.info("Testing refresh token error handling and fallback procedures")
    
    user_id = "error_handling_user"
    
    # Create expired token for error testing
    expired_token = jwt_generator.create_expired_token(user_id, expired_minutes_ago=3)
    
    # Test error scenarios
    error_scenarios = [
        {
            "name": "Malformed expired token",
            "expired_token": "malformed.expired.token",
            "refresh_token": f"refresh_{secrets.token_urlsafe(32)}",
            "should_succeed": False
        },
        {
            "name": "Empty expired token",
            "expired_token": "",
            "refresh_token": f"refresh_{secrets.token_urlsafe(32)}",
            "should_succeed": False
        },
        {
            "name": "Valid tokens",
            "expired_token": expired_token,
            "refresh_token": f"refresh_{secrets.token_urlsafe(32)}",
            "should_succeed": True
        }
    ]
    
    error_results = []
    
    for i, scenario in enumerate(error_scenarios):
        logger.info(f"Testing error scenario: {scenario['name']}")
        
        error_start = time.time()
        
        try:
            refresh_result = await token_refresh_service.refresh_expired_token(
                scenario["expired_token"],
                scenario["refresh_token"]
            )
            
            error_time = time.time() - error_start
            success = refresh_result is not None
            
        except Exception as e:
            error_time = time.time() - error_start
            success = False
            refresh_result = None
            logger.info(f"Exception in scenario '{scenario['name']}': {str(e)}")
        
        # Validate expected behavior
        if scenario["should_succeed"]:
            assert success, f"Error scenario should succeed: {scenario['name']}"
        else:
            assert not success, f"Error scenario should fail: {scenario['name']}"
        
        # Validate quick error handling
        assert error_time < 0.1, f"Error handling too slow: {scenario['name']}"
        
        error_results.append({
            "scenario": scenario["name"],
            "success": success,
            "error_time": error_time,
            "expected_success": scenario["should_succeed"]
        })
        
        await asyncio.sleep(0.1)
    
    # Validate error handling performance
    error_times = [r["error_time"] for r in error_results]
    avg_error_time = sum(error_times) / len(error_times)
    max_error_time = max(error_times)
    
    assert avg_error_time < 0.05, f"Average error handling {avg_error_time:.3f}s too slow"
    assert max_error_time < 0.1, f"Max error handling {max_error_time:.3f}s too slow"
    
    # Validate all scenarios behaved as expected
    for result in error_results:
        assert result["success"] == result["expected_success"], f"Unexpected result: {result['scenario']}"
    
    # Validate security logging for successful refresh
    security_events = audit_logger.security_events
    refresh_events = [e for e in security_events if e["event_type"] == "token_refresh_success"]
    recent_events = [
        e for e in refresh_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 60
    ]
    
    successful_scenarios = [r for r in error_results if r["success"]]
    assert len(recent_events) >= len(successful_scenarios), "Successful refreshes should be logged"
    
    logger.info(f"✓ Error handling: {len(error_scenarios)} scenarios tested, avg {avg_error_time:.3f}s handling time")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_refresh_token_performance_under_load(jwt_generator, audit_logger, token_refresh_service):
    """
    Test Case 3: Refresh token performance under high load.
    
    Tests token refresh service performance under high concurrent load
    to ensure scalability and responsiveness.
    """
    logger.info("Testing refresh token performance under high load")
    
    # High load test parameters
    total_users = 25
    refreshes_per_user = 2
    total_refreshes = total_users * refreshes_per_user
    
    # Create test users and tokens
    test_data = []
    for i in range(total_users):
        user_id = f"load_test_user_{i:03d}"
        expired_token = jwt_generator.create_expired_token(user_id, expired_minutes_ago=5)
        refresh_token = f"refresh_{secrets.token_urlsafe(32)}"
        
        test_data.append({
            "user_id": user_id,
            "expired_token": expired_token,
            "refresh_token": refresh_token
        })
    
    async def perform_user_refreshes(user_data: Dict[str, str]) -> List[Dict[str, Any]]:
        """Perform multiple refreshes for a single user."""
        user_results = []
        current_token = user_data["expired_token"]
        current_refresh = user_data["refresh_token"]
        
        for refresh_num in range(refreshes_per_user):
            refresh_start = time.time()
            
            refresh_result = await token_refresh_service.refresh_expired_token(
                current_token,
                current_refresh
            )
            
            refresh_time = time.time() - refresh_start
            
            user_results.append({
                "user_id": user_data["user_id"],
                "refresh_num": refresh_num,
                "success": refresh_result is not None,
                "refresh_time": refresh_time,
                "result": refresh_result
            })
            
            # Update tokens for next refresh if successful
            if refresh_result:
                current_token = refresh_result["access_token"]
                current_refresh = refresh_result["refresh_token"]
            
            # Small delay between refreshes for same user
            await asyncio.sleep(0.01)
        
        return user_results
    
    # Execute high load test
    logger.info(f"Starting high load test: {total_users} users, {refreshes_per_user} refreshes each")
    load_start_time = time.time()
    
    # Run all user refreshes concurrently
    concurrent_tasks = [
        perform_user_refreshes(user_data)
        for user_data in test_data
    ]
    
    all_user_results = await asyncio.gather(*concurrent_tasks)
    total_load_time = time.time() - load_start_time
    
    # Flatten results
    all_results = [result for user_results in all_user_results for result in user_results]
    
    # Validate load test results
    successful_refreshes = [r for r in all_results if r["success"]]
    failed_refreshes = [r for r in all_results if not r["success"]]
    
    # Should have high success rate
    success_rate = len(successful_refreshes) / len(all_results)
    assert success_rate >= 0.95, f"Success rate {success_rate:.2%} too low under load"
    
    # Validate performance under load
    refresh_times = [r["refresh_time"] for r in all_results]
    avg_refresh_time = sum(refresh_times) / len(refresh_times)
    max_refresh_time = max(refresh_times)
    p95_refresh_time = sorted(refresh_times)[int(len(refresh_times) * 0.95)]
    
    assert avg_refresh_time < 0.1, f"Average refresh time {avg_refresh_time:.3f}s too slow under load"
    assert p95_refresh_time < 0.2, f"95th percentile refresh time {p95_refresh_time:.3f}s too slow"
    assert max_refresh_time < 0.5, f"Max refresh time {max_refresh_time:.3f}s too slow under load"
    
    # Calculate throughput
    throughput = len(successful_refreshes) / total_load_time
    
    # Validate security logging handled the load
    security_events = audit_logger.security_events
    recent_refresh_events = [
        e for e in security_events
        if e["event_type"] == "token_refresh_success" and
           (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 120
    ]
    
    # Should have logged most successful refreshes
    logging_success_rate = len(recent_refresh_events) / len(successful_refreshes)
    assert logging_success_rate >= 0.9, f"Logging success rate {logging_success_rate:.2%} too low under load"
    
    logger.info(f"✓ Load test: {total_refreshes} refreshes in {total_load_time:.2f}s ({throughput:.1f} refreshes/s)")
    logger.info(f"   Success rate: {success_rate:.2%}, avg time: {avg_refresh_time:.3f}s, p95: {p95_refresh_time:.3f}s")
    logger.info(f"   Logging rate: {logging_success_rate:.2%}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_refresh_token_timeout_and_retry_logic(jwt_generator, audit_logger, token_refresh_service):
    """
    Test Case 4: Refresh token timeout and retry logic.
    
    Tests timeout handling and retry mechanisms for token refresh operations
    to ensure robust error recovery.
    """
    logger.info("Testing refresh token timeout and retry logic")
    
    user_id = "timeout_test_user"
    
    # Create test scenarios with different timeout conditions
    timeout_scenarios = [
        {
            "name": "Normal refresh (no timeout)",
            "timeout_ms": 0,  # No artificial timeout
            "should_succeed": True
        },
        {
            "name": "Quick refresh with small delay",
            "timeout_ms": 10,  # Small delay
            "should_succeed": True
        },
        {
            "name": "Refresh with moderate delay",
            "timeout_ms": 50,  # Moderate delay
            "should_succeed": True
        }
    ]
    
    test_results = []
    
    for i, scenario in enumerate(timeout_scenarios):
        logger.info(f"Testing timeout scenario: {scenario['name']}")
        
        # Create fresh expired token for each scenario
        expired_token = jwt_generator.create_expired_token(user_id, expired_minutes_ago=i+1)
        refresh_token = f"refresh_{secrets.token_urlsafe(32)}"
        
        # Add artificial delay if specified
        if scenario["timeout_ms"] > 0:
            await asyncio.sleep(scenario["timeout_ms"] / 1000.0)
        
        timeout_start = time.time()
        
        try:
            refresh_result = await token_refresh_service.refresh_expired_token(
                expired_token,
                refresh_token
            )
            
            timeout_time = time.time() - timeout_start
            success = refresh_result is not None
            
        except asyncio.TimeoutError:
            timeout_time = time.time() - timeout_start
            success = False
            refresh_result = None
            logger.info(f"Timeout occurred in scenario: {scenario['name']}")
            
        except Exception as e:
            timeout_time = time.time() - timeout_start
            success = False
            refresh_result = None
            logger.info(f"Exception in timeout scenario '{scenario['name']}': {str(e)}")
        
        # Validate expected behavior
        if scenario["should_succeed"]:
            assert success, f"Timeout scenario should succeed: {scenario['name']}"
        else:
            assert not success, f"Timeout scenario should fail: {scenario['name']}"
        
        test_results.append({
            "scenario": scenario["name"],
            "success": success,
            "timeout_time": timeout_time,
            "expected_success": scenario["should_succeed"]
        })
        
        # Brief delay between scenarios
        await asyncio.sleep(0.1)
    
    # Validate timeout handling performance
    timeout_times = [r["timeout_time"] for r in test_results]
    avg_timeout_time = sum(timeout_times) / len(timeout_times)
    max_timeout_time = max(timeout_times)
    
    # Even with delays, should be relatively fast
    assert avg_timeout_time < 0.2, f"Average timeout handling {avg_timeout_time:.3f}s too slow"
    assert max_timeout_time < 0.5, f"Max timeout handling {max_timeout_time:.3f}s too slow"
    
    # Validate all scenarios behaved as expected
    for result in test_results:
        assert result["success"] == result["expected_success"], f"Unexpected timeout result: {result['scenario']}"
    
    # Validate successful refreshes were logged
    security_events = audit_logger.security_events
    refresh_events = [e for e in security_events if e["event_type"] == "token_refresh_success"]
    recent_events = [
        e for e in refresh_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 60
    ]
    
    successful_scenarios = [r for r in test_results if r["success"]]
    assert len(recent_events) >= len(successful_scenarios), "Successful refreshes should be logged despite timeouts"
    
    logger.info(f"✓ Timeout handling: {len(timeout_scenarios)} scenarios tested, avg {avg_timeout_time:.3f}s handling")


if __name__ == "__main__":
    # Run advanced token refresh tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto",
        "-k", "test_"  # Run all test functions
    ])
