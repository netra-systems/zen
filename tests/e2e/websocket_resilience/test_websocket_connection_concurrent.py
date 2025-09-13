"""
WebSocket Connection Concurrent Tests: Load and Performance

Concurrent connection tests focusing on performance under load,
multiple simultaneous expired token attempts, and system resilience.

Business Value: Ensures system stability under high load and prevents
performance degradation that could impact customer experience.
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
from websockets import ConnectionClosed, InvalidStatus

from netra_backend.app.logging_config import central_logger
from tests.e2e.websocket_resilience.websocket_recovery_fixtures import (
    SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient,
    TokenRefreshService, jwt_generator, audit_logger, token_refresh_service,
    expired_token, valid_token, near_expiry_token
)

logger = central_logger.get_logger(__name__)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_expired_token_connections(jwt_generator, audit_logger):
    """
    Test Case 1: Concurrent expired token connection attempts.
    
    Tests system performance and consistency under concurrent expired token
    connection attempts, validating resource protection and response consistency.
    """
    logger.info("Testing concurrent expired token connection attempts")
    
    concurrent_users = 10
    attempts_per_user = 2
    total_attempts = concurrent_users * attempts_per_user
    
    # Create expired tokens for concurrent testing
    expired_tokens = [
        jwt_generator.create_expired_token(f"concurrent_user_{i}", expired_minutes_ago=5)
        for i in range(concurrent_users)
    ]
    
    async def attempt_connection_with_expired_token(user_index: int) -> List[Dict]:
        """Simulate user making multiple attempts with expired token."""
        user_results = []
        token = expired_tokens[user_index]
        
        for attempt in range(attempts_per_user):
            client = SecureWebSocketTestClient(
                "ws://mock-server/ws",
                token,
                jwt_generator,
                audit_logger
            )
            
            headers = {
                "X-Forwarded-For": f"10.0.{user_index // 256}.{user_index % 256}",
                "User-Agent": f"ConcurrentClient/{user_index}.{attempt}",
                "X-User-Index": str(user_index),
                "X-Attempt": str(attempt)
            }
            
            start_time = time.time()
            success, result = await client.attempt_connection(headers)
            response_time = time.time() - start_time
            
            user_results.append({
                "user_index": user_index,
                "attempt": attempt,
                "success": success,
                "response_time": response_time,
                "result": result
            })
            
            await client.disconnect()
            
            # Brief delay between user's attempts
            await asyncio.sleep(0.05)
        
        return user_results
    
    # Execute concurrent attempts
    logger.info(f"Starting {concurrent_users} concurrent users with {attempts_per_user} attempts each")
    start_time = time.time()
    
    # Run all user attempts concurrently
    concurrent_tasks = [
        attempt_connection_with_expired_token(i) 
        for i in range(concurrent_users)
    ]
    
    all_results = await asyncio.gather(*concurrent_tasks)
    total_time = time.time() - start_time
    
    # Flatten results
    flat_results = [result for user_results in all_results for result in user_results]
    
    # Validate all attempts were rejected
    successful_attempts = [r for r in flat_results if r["success"]]
    failed_attempts = [r for r in flat_results if not r["success"]]
    
    assert len(successful_attempts) == 0, f"All expired token attempts should fail, got {len(successful_attempts)} successes"
    assert len(failed_attempts) == total_attempts, f"Expected {total_attempts} failures, got {len(failed_attempts)}"
    
    # Validate performance under concurrent load
    response_times = [r["response_time"] for r in flat_results]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    min_response_time = min(response_times)
    
    assert avg_response_time < 0.15, f"Average response time {avg_response_time:.3f}s too slow under concurrent load"
    assert max_response_time < 0.3, f"Max response time {max_response_time:.3f}s too slow under concurrent load"
    
    # Validate consistent performance (no major outliers)
    response_time_variance = max_response_time - min_response_time
    assert response_time_variance < 0.2, f"Response time variance {response_time_variance:.3f}s too high"
    
    throughput = total_attempts / total_time
    
    logger.info(f"[U+2713] Concurrent performance: {total_attempts} attempts in {total_time:.2f}s ({throughput:.1f} req/s)")
    logger.info(f"   Response times: avg {avg_response_time:.3f}s, max {max_response_time:.3f}s, variance {response_time_variance:.3f}s")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mixed_token_concurrent_connections(jwt_generator, audit_logger):
    """
    Test Case 2: Mixed valid and expired token concurrent connections.
    
    Tests system behavior under concurrent load with mix of valid and expired tokens,
    ensuring proper differentiation and consistent handling.
    """
    logger.info("Testing mixed valid and expired token concurrent connections")
    
    total_users = 15
    valid_token_ratio = 0.4  # 40% valid tokens, 60% expired
    valid_users = int(total_users * valid_token_ratio)
    expired_users = total_users - valid_users
    
    # Create mixed tokens
    test_tokens = []
    
    # Valid tokens
    for i in range(valid_users):
        user_id = f"valid_user_{i}"
        token = jwt_generator.create_valid_token(user_id)
        test_tokens.append({
            "user_id": user_id,
            "token": token,
            "expected_success": True,
            "token_type": "valid"
        })
    
    # Expired tokens
    for i in range(expired_users):
        user_id = f"expired_user_{i}"
        token = jwt_generator.create_expired_token(user_id, expired_minutes_ago=5)
        test_tokens.append({
            "user_id": user_id,
            "token": token,
            "expected_success": False,
            "token_type": "expired"
        })
    
    # Randomize order to simulate realistic mixed load
    import random
    random.shuffle(test_tokens)
    
    async def attempt_mixed_connection(token_info: Dict, index: int) -> Dict[str, Any]:
        """Attempt connection with either valid or expired token."""
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            token_info["token"],
            jwt_generator,
            audit_logger
        )
        
        headers = {
            "X-Forwarded-For": f"172.16.{index // 256}.{index % 256}",
            "User-Agent": f"MixedTestClient/{index}.0",
            "X-Token-Type": token_info["token_type"]
        }
        
        start_time = time.time()
        success, result = await client.attempt_connection(headers)
        response_time = time.time() - start_time
        
        await client.disconnect()
        
        return {
            "user_id": token_info["user_id"],
            "token_type": token_info["token_type"],
            "expected_success": token_info["expected_success"],
            "actual_success": success,
            "response_time": response_time,
            "result": result
        }
    
    # Execute mixed concurrent attempts
    logger.info(f"Starting {total_users} mixed connections ({valid_users} valid, {expired_users} expired)")
    mixed_start_time = time.time()
    
    mixed_tasks = [
        attempt_mixed_connection(token_info, i)
        for i, token_info in enumerate(test_tokens)
    ]
    
    mixed_results = await asyncio.gather(*mixed_tasks)
    mixed_total_time = time.time() - mixed_start_time
    
    # Validate correct differentiation
    correct_results = [r for r in mixed_results if r["actual_success"] == r["expected_success"]]
    incorrect_results = [r for r in mixed_results if r["actual_success"] != r["expected_success"]]
    
    accuracy_rate = len(correct_results) / len(mixed_results)
    assert accuracy_rate >= 0.98, f"Token validation accuracy {accuracy_rate:.2%} too low"
    assert len(incorrect_results) == 0, f"Found {len(incorrect_results)} incorrect validations"
    
    # Validate performance for both token types
    valid_results = [r for r in mixed_results if r["token_type"] == "valid"]
    expired_results = [r for r in mixed_results if r["token_type"] == "expired"]
    
    valid_times = [r["response_time"] for r in valid_results]
    expired_times = [r["response_time"] for r in expired_results]
    
    avg_valid_time = sum(valid_times) / len(valid_times) if valid_times else 0
    avg_expired_time = sum(expired_times) / len(expired_times) if expired_times else 0
    
    assert avg_valid_time < 0.1, f"Valid token processing {avg_valid_time:.3f}s too slow"
    assert avg_expired_time < 0.1, f"Expired token processing {avg_expired_time:.3f}s too slow"
    
    # Both should be fast, expired might be slightly faster due to immediate rejection
    assert abs(avg_valid_time - avg_expired_time) < 0.05, "Processing time difference too large"
    
    mixed_throughput = total_users / mixed_total_time
    
    logger.info(f"[U+2713] Mixed load: {total_users} connections in {mixed_total_time:.2f}s ({mixed_throughput:.1f} conn/s)")
    logger.info(f"   Accuracy: {accuracy_rate:.2%}, valid avg: {avg_valid_time:.3f}s, expired avg: {avg_expired_time:.3f}s")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_sustained_concurrent_load_stability(jwt_generator, audit_logger):
    """
    Test Case 3: Sustained concurrent load stability.
    
    Tests system stability under sustained concurrent load over time,
    ensuring no performance degradation or resource leaks.
    """
    logger.info("Testing sustained concurrent load stability")
    
    # Sustained load parameters
    load_duration_seconds = 10  # Run for 10 seconds
    connections_per_second = 5  # Moderate sustained rate
    batch_size = 3  # Connections per batch
    
    total_batches = (load_duration_seconds * connections_per_second) // batch_size
    sustained_results = []
    batch_times = []
    
    logger.info(f"Starting sustained load: {total_batches} batches over {load_duration_seconds}s")
    sustained_start = time.time()
    
    for batch_num in range(total_batches):
        batch_start = time.time()
        
        # Create batch of expired tokens
        batch_tokens = [
            jwt_generator.create_expired_token(f"sustained_user_{batch_num}_{i}", expired_minutes_ago=1)
            for i in range(batch_size)
        ]
        
        async def sustained_connection_attempt(batch_idx: int, token_idx: int) -> Dict[str, Any]:
            """Single sustained connection attempt."""
            token = batch_tokens[token_idx]
            client = SecureWebSocketTestClient(
                "ws://mock-server/ws",
                token,
                jwt_generator,
                audit_logger
            )
            
            headers = {
                "X-Forwarded-For": f"198.51.100.{(batch_idx * batch_size + token_idx) % 255}",
                "User-Agent": f"SustainedClient/{batch_idx}.{token_idx}",
                "X-Batch": str(batch_idx),
                "X-Token-Index": str(token_idx)
            }
            
            attempt_start = time.time()
            success, result = await client.attempt_connection(headers)
            attempt_time = time.time() - attempt_start
            
            await client.disconnect()
            
            return {
                "batch": batch_idx,
                "token_index": token_idx,
                "success": success,
                "response_time": attempt_time,
                "batch_time": batch_start
            }
        
        # Execute batch concurrently
        batch_tasks = [
            sustained_connection_attempt(batch_num, i)
            for i in range(batch_size)
        ]
        
        batch_results = await asyncio.gather(*batch_tasks)
        batch_time = time.time() - batch_start
        
        sustained_results.extend(batch_results)
        batch_times.append(batch_time)
        
        # Brief delay between batches to simulate sustained load
        await asyncio.sleep(0.2)
    
    sustained_total_time = time.time() - sustained_start
    
    # Validate sustained performance
    all_response_times = [r["response_time"] for r in sustained_results]
    avg_response_time = sum(all_response_times) / len(all_response_times)
    max_response_time = max(all_response_times)
    
    # Performance should remain consistent throughout sustained load
    assert avg_response_time < 0.1, f"Average response time {avg_response_time:.3f}s degraded under sustained load"
    assert max_response_time < 0.2, f"Max response time {max_response_time:.3f}s too high under sustained load"
    
    # Check for performance degradation over time
    first_half = sustained_results[:len(sustained_results)//2]
    second_half = sustained_results[len(sustained_results)//2:]
    
    first_half_avg = sum(r["response_time"] for r in first_half) / len(first_half)
    second_half_avg = sum(r["response_time"] for r in second_half) / len(second_half)
    
    performance_degradation = (second_half_avg - first_half_avg) / first_half_avg
    assert performance_degradation < 0.5, f"Performance degraded {performance_degradation:.1%} over time"
    
    # All attempts should fail (expired tokens)
    failed_attempts = [r for r in sustained_results if not r["success"]]
    assert len(failed_attempts) == len(sustained_results), "All sustained attempts should fail with expired tokens"
    
    # Validate batch consistency
    avg_batch_time = sum(batch_times) / len(batch_times)
    max_batch_time = max(batch_times)
    
    assert avg_batch_time < 0.5, f"Average batch time {avg_batch_time:.3f}s too slow"
    assert max_batch_time < 1.0, f"Max batch time {max_batch_time:.3f}s too slow"
    
    sustained_throughput = len(sustained_results) / sustained_total_time
    
    logger.info(f"[U+2713] Sustained load: {len(sustained_results)} attempts over {sustained_total_time:.1f}s ({sustained_throughput:.1f} req/s)")
    logger.info(f"   Performance: avg {avg_response_time:.3f}s, degradation {performance_degradation:.1%}")
    logger.info(f"   Batches: avg {avg_batch_time:.3f}s, max {max_batch_time:.3f}s")


if __name__ == "__main__":
    # Run concurrent connection tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto",
        "-k", "test_"  # Run all test functions
    ])
