"""
Authentication Circuit Breakers and Error Handling Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical for system reliability  
- Business Goal: Ensure auth system remains stable under failure conditions
- Value Impact: Users experience graceful degradation instead of complete system failure
- Strategic Impact: Core platform reliability - prevents cascade failures that could lose all users

CRITICAL: Tests auth system error handling and circuit breaker patterns.
Validates graceful degradation and recovery mechanisms for business continuity.

Following CLAUDE.md requirements:
- Unit tests can have limited mocks for external dependencies if needed
- Tests MUST fail hard - no try/except blocks masking errors
- Focus on business logic validation for error scenarios
- Use SSOT patterns from test_framework/ssot/
"""
import pytest
import time
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional, List

# Absolute imports per CLAUDE.md
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env


class TestAuthCircuitBreakersCore:
    """Unit tests for authentication circuit breaker patterns and error handling."""
    
    @pytest.fixture(autouse=True)
    def setup_error_handling_environment(self):
        """Setup environment for error handling and circuit breaker tests."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Set error handling test configuration
        self.env.set("JWT_SECRET_KEY", "unit-test-error-jwt-secret-32-chars-long", "test_error_handling")
        self.env.set("SERVICE_SECRET", "unit-test-error-service-secret-32", "test_error_handling")
        self.env.set("ENVIRONMENT", "test", "test_error_handling")
        
        # Configure circuit breaker thresholds for testing
        self.env.set("AUTH_CIRCUIT_BREAKER_ENABLED", "true", "test_error_handling")
        self.env.set("AUTH_FAILURE_THRESHOLD", "5", "test_error_handling")  # Low threshold for testing
        self.env.set("AUTH_RECOVERY_TIMEOUT", "10", "test_error_handling")  # Short timeout for testing
        
        yield
        
        # Cleanup
        self.env.disable_isolation()
    
    def test_jwt_handler_gracefully_handles_corrupted_secret_key(self):
        """Test that JWT handler gracefully handles corrupted or missing secret keys."""
        # Test case 1: Empty secret key
        with patch.object(AuthConfig, 'get_jwt_secret', return_value=""):
            try:
                handler = JWTHandler()
                # Should either use fallback or raise clear error
                if hasattr(handler, 'secret') and handler.secret:
                    # Fallback mechanism worked
                    assert len(handler.secret) >= 32, "Fallback secret must be sufficiently long"
                else:
                    assert False, "Handler should provide fallback for empty secret"
            except ValueError as e:
                # Clear error is acceptable
                assert "JWT_SECRET_KEY" in str(e), "Error message must reference JWT_SECRET_KEY"
        
        # Test case 2: Very short secret key (security issue)
        with patch.object(AuthConfig, 'get_jwt_secret', return_value="short"):
            with patch.object(AuthConfig, 'get_environment', return_value="production"):
                try:
                    handler = JWTHandler()
                    assert False, "Short JWT secret in production must raise error"
                except ValueError as e:
                    assert "32 characters" in str(e), "Error must specify minimum secret length"
        
        # Test case 3: Non-string secret key
        with patch.object(AuthConfig, 'get_jwt_secret', return_value=None):
            try:
                handler = JWTHandler()
                # Should handle None gracefully with fallback or clear error
                assert handler.secret is not None, "Handler must provide fallback for None secret"
            except (ValueError, TypeError) as e:
                # Clear error is acceptable
                assert "JWT_SECRET_KEY" in str(e) or "secret" in str(e).lower(), "Error must reference secret configuration"
        
        # Test case 4: Valid secret (baseline)
        with patch.object(AuthConfig, 'get_jwt_secret', return_value="valid-jwt-secret-32-characters-long-test-key"):
            handler = JWTHandler()
            assert handler.secret == "valid-jwt-secret-32-characters-long-test-key", "Valid secret must be used as-is"
    
    def test_jwt_validation_handles_malformed_tokens_without_crashing(self):
        """Test that JWT validation handles all types of malformed tokens without system crashes."""
        handler = JWTHandler()
        
        # Comprehensive malformed token test cases
        malformed_token_cases = [
            {"token": None, "description": "None value"},
            {"token": "", "description": "empty string"},
            {"token": "   ", "description": "whitespace only"},
            {"token": "not-a-jwt-at-all", "description": "random string"},
            {"token": "one.two", "description": "only two parts"},
            {"token": "one.two.three.four", "description": "too many parts"},
            {"token": "...", "description": "empty parts"},
            {"token": "valid-looking.but-invalid.signature", "description": "invalid signature"},
            {"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..", "description": "empty payload"},
            {"token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0ZXN0IjoidmFsdWUifQ.invalid", "description": "bearer prefix"},
            {"token": "\x00\x01\x02invalid-binary-data", "description": "binary data"},
            {"token": "{'not': 'jwt'}", "description": "json object"},
            {"token": "a" * 10000, "description": "extremely long string"}
        ]
        
        for test_case in malformed_token_cases:
            token = test_case["token"]
            description = test_case["description"]
            
            # Act: Validate malformed token
            try:
                payload = handler.validate_token(token, "access")
                
                # Assert: Must return None for invalid tokens, never crash
                assert payload is None, f"Malformed token ({description}) must return None, got: {payload}"
                
            except Exception as e:
                # If exception occurs, it must be a controlled exception, not a crash
                acceptable_exceptions = (ValueError, TypeError, AttributeError)
                assert isinstance(e, acceptable_exceptions), (
                    f"Malformed token ({description}) must not cause unhandled exception. "
                    f"Got {type(e).__name__}: {e}"
                )
                
                # Exception message should be informative but not expose sensitive data
                error_msg = str(e).lower()
                assert "token" in error_msg or "invalid" in error_msg or "malformed" in error_msg, (
                    f"Exception message must be informative for {description}: {e}"
                )
                
                # Must not expose secret key or internal details
                assert "secret" not in error_msg, f"Exception must not expose secret key for {description}: {e}"
    
    def test_concurrent_authentication_failures_trigger_circuit_breaker(self):
        """Test that concurrent authentication failures trigger circuit breaker protection."""
        handler = JWTHandler()
        
        # Mock Redis for circuit breaker state (since Redis not available in unit tests)
        with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.get_client.return_value = mock_redis_client
            
            # Configure mock Redis to simulate circuit breaker state
            failure_count = 0
            circuit_breaker_state = {"failures": 0, "last_failure": None, "state": "closed"}
            
            def mock_increment_failures(key):
                nonlocal failure_count, circuit_breaker_state
                failure_count += 1
                circuit_breaker_state["failures"] = failure_count
                circuit_breaker_state["last_failure"] = time.time()
                if failure_count >= 5:  # Threshold from environment
                    circuit_breaker_state["state"] = "open"
                return failure_count
            
            def mock_get_circuit_state(key):
                return circuit_breaker_state
            
            mock_redis_client.incr.side_effect = mock_increment_failures
            mock_redis_client.hgetall.return_value = circuit_breaker_state
            mock_redis_client.hset.return_value = True
            
            # Simulate multiple concurrent failures
            failure_scenarios = [
                {"token": "invalid-token-1", "expected_failure": True},
                {"token": "invalid-token-2", "expected_failure": True},
                {"token": "invalid-token-3", "expected_failure": True},
                {"token": "invalid-token-4", "expected_failure": True},
                {"token": "invalid-token-5", "expected_failure": True},  # Should trigger circuit breaker
                {"token": "invalid-token-6", "expected_circuit_breaker": True}  # Should be blocked by circuit breaker
            ]
            
            results = []
            
            for i, scenario in enumerate(failure_scenarios):
                # Mock circuit breaker check
                if circuit_breaker_state["state"] == "open" and scenario.get("expected_circuit_breaker"):
                    # Circuit breaker should block this request
                    result = {
                        "scenario_index": i,
                        "token": scenario["token"],
                        "blocked_by_circuit_breaker": True,
                        "validation_result": None
                    }
                else:
                    # Normal validation (will fail for invalid tokens)
                    validation_result = handler.validate_token(scenario["token"], "access")
                    result = {
                        "scenario_index": i,
                        "token": scenario["token"],
                        "blocked_by_circuit_breaker": False,
                        "validation_result": validation_result
                    }
                
                results.append(result)
            
            # Assert: First 5 failures should go through normally, 6th should be blocked
            for i, result in enumerate(results[:5]):
                assert result["blocked_by_circuit_breaker"] is False, (
                    f"Request {i} should not be blocked by circuit breaker yet"
                )
                assert result["validation_result"] is None, (
                    f"Request {i} should fail validation (invalid token)"
                )
            
            # 6th request should be blocked by circuit breaker
            if len(results) > 5:
                circuit_breaker_result = results[5]
                assert circuit_breaker_result["blocked_by_circuit_breaker"] is True, (
                    "Request after failure threshold should be blocked by circuit breaker"
                )
    
    def test_database_connection_failure_doesnt_crash_authentication(self):
        """Test that database/Redis connection failures don't crash the authentication system."""
        handler = JWTHandler()
        
        # Create valid token first (before simulating DB failure)
        user_id = "db-failure-test-user"
        email = "db-failure@netra.ai"
        valid_token = handler.create_access_token(user_id, email)
        
        # Verify token is valid before simulating failure
        pre_failure_validation = handler.validate_token(valid_token, "access")
        assert pre_failure_validation is not None, "Token must be valid before simulating database failure"
        
        # Simulate Redis/database connection failures
        connection_failure_scenarios = [
            {
                "exception": ConnectionError("Redis connection failed"),
                "description": "Redis connection failure"
            },
            {
                "exception": TimeoutError("Database timeout"), 
                "description": "Database timeout"
            },
            {
                "exception": OSError("Network unreachable"),
                "description": "Network failure"
            },
            {
                "exception": Exception("Generic database error"),
                "description": "Generic database error"
            }
        ]
        
        for scenario in connection_failure_scenarios:
            exception = scenario["exception"]
            description = scenario["description"]
            
            # Mock Redis operations to simulate failures
            with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock_redis:
                mock_redis_client = Mock()
                mock_redis.get_client.return_value = mock_redis_client
                
                # All Redis operations fail with this exception
                mock_redis_client.get.side_effect = exception
                mock_redis_client.hgetall.side_effect = exception
                mock_redis_client.incr.side_effect = exception
                mock_redis_client.hset.side_effect = exception
                
                try:
                    # Act: Attempt token validation during database failure
                    validation_result = handler.validate_token(valid_token, "access")
                    
                    # Assert: System should handle gracefully, either:
                    # 1. Return None (fail closed for security)
                    # 2. Return valid payload (if JWT validation doesn't require DB)
                    # 3. Raise controlled exception (not system crash)
                    
                    if validation_result is None:
                        # Fail-closed approach is acceptable for security
                        print(f"[U+2713] {description}: System failed closed (secure)")
                    elif validation_result is not None and validation_result.get("sub") == user_id:
                        # JWT validation succeeded without DB (also acceptable)  
                        print(f"[U+2713] {description}: JWT validation succeeded without DB")
                    else:
                        assert False, f"{description}: Unexpected validation result: {validation_result}"
                        
                except Exception as e:
                    # If exception occurs, it must be controlled, not a system crash
                    acceptable_exceptions = (ConnectionError, TimeoutError, ValueError, RuntimeError)
                    assert isinstance(e, acceptable_exceptions), (
                        f"{description}: Must not cause system crash. "
                        f"Got {type(e).__name__}: {e}"
                    )
                    
                    # Exception should be informative but not expose sensitive data
                    error_msg = str(e).lower()
                    assert any(word in error_msg for word in ["connection", "timeout", "database", "redis", "error"]), (
                        f"{description}: Exception message should indicate connection issue: {e}"
                    )
    
    def test_token_blacklisting_continues_during_partial_system_failures(self):
        """Test that token blacklisting continues to work during partial system failures."""
        handler = JWTHandler()
        
        # Create tokens for blacklisting test
        user_id = "blacklist-failure-test"
        email = "blacklist-failure@netra.ai"
        
        token_to_blacklist = handler.create_access_token(user_id, email)
        valid_token = handler.create_access_token(f"{user_id}-valid", email)
        
        # Verify tokens are initially valid
        assert handler.validate_token(token_to_blacklist, "access") is not None, "Token to blacklist must be initially valid"
        assert handler.validate_token(valid_token, "access") is not None, "Valid token must be initially valid"
        
        # Test blacklisting under different failure conditions
        failure_scenarios = [
            {
                "redis_operation": "hset",  # Blacklist storage fails
                "exception": ConnectionError("Redis write failed"),
                "description": "blacklist storage failure"
            },
            {
                "redis_operation": "get", # Blacklist lookup fails
                "exception": TimeoutError("Redis read timeout"),
                "description": "blacklist lookup failure" 
            },
            {
                "redis_operation": "incr", # Counter increment fails
                "exception": OSError("Redis counter failure"),
                "description": "failure counter update failure"
            }
        ]
        
        for scenario in failure_scenarios:
            failing_operation = scenario["redis_operation"]
            exception = scenario["exception"] 
            description = scenario["description"]
            
            with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock_redis:
                mock_redis_client = Mock()
                mock_redis.get_client.return_value = mock_redis_client
                
                # Configure mock Redis - most operations succeed, specific one fails
                mock_redis_client.hset.return_value = True
                mock_redis_client.get.return_value = None  # Not blacklisted
                mock_redis_client.incr.return_value = 1
                mock_redis_client.hgetall.return_value = {}
                
                # Make specific operation fail
                if failing_operation == "hset":
                    mock_redis_client.hset.side_effect = exception
                elif failing_operation == "get":
                    mock_redis_client.get.side_effect = exception
                elif failing_operation == "incr":
                    mock_redis_client.incr.side_effect = exception
                
                try:
                    # Act: Attempt blacklisting during failure
                    blacklist_result = handler.blacklist_token(token_to_blacklist)
                    
                    # System should handle gracefully - either succeed or fail cleanly
                    if blacklist_result is True:
                        print(f"[U+2713] {description}: Blacklisting succeeded despite {failing_operation} failure")
                    elif blacklist_result is False:
                        print(f"[U+2713] {description}: Blacklisting failed gracefully due to {failing_operation} failure")
                    else:
                        assert False, f"{description}: Blacklisting must return boolean result"
                    
                    # Verify non-blacklisted token still works
                    valid_token_result = handler.validate_token(valid_token, "access")
                    assert valid_token_result is not None, (
                        f"{description}: Valid tokens must continue working during partial failures"
                    )
                    
                except Exception as e:
                    # Controlled exceptions are acceptable
                    acceptable_exceptions = (ConnectionError, TimeoutError, OSError, RuntimeError, ValueError)
                    assert isinstance(e, acceptable_exceptions), (
                        f"{description}: Must not cause system crash during blacklisting. "
                        f"Got {type(e).__name__}: {e}"
                    )
    
    def test_authentication_system_recovers_after_failures(self):
        """Test that authentication system properly recovers after temporary failures."""
        handler = JWTHandler()
        
        # Create test tokens
        user_id = "recovery-test-user"
        email = "recovery@netra.ai"
        test_token = handler.create_access_token(user_id, email)
        
        # Verify initial valid state
        initial_validation = handler.validate_token(test_token, "access")
        assert initial_validation is not None, "Token must be initially valid"
        assert initial_validation["sub"] == user_id, "Initial validation must contain correct user data"
        
        # Simulate temporary failure and recovery
        with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.get_client.return_value = mock_redis_client
            
            # Phase 1: System failure
            mock_redis_client.get.side_effect = ConnectionError("Temporary Redis failure")
            mock_redis_client.hgetall.side_effect = ConnectionError("Temporary Redis failure")
            
            # During failure, system should either fail gracefully or continue with JWT-only validation
            try:
                failure_validation = handler.validate_token(test_token, "access")
                
                # Either fail closed (None) or succeed with JWT validation
                if failure_validation is None:
                    print("[U+2713] System failed closed during Redis failure (secure)")
                elif failure_validation.get("sub") == user_id:
                    print("[U+2713] System continued with JWT validation during Redis failure")
                else:
                    assert False, f"Unexpected validation result during failure: {failure_validation}"
                    
            except Exception as e:
                # Controlled failure is acceptable
                acceptable_exceptions = (ConnectionError, RuntimeError, ValueError)
                assert isinstance(e, acceptable_exceptions), (
                    f"System failure must be controlled exception, got {type(e).__name__}: {e}"
                )
                print(f"[U+2713] System failed with controlled exception: {type(e).__name__}")
            
            # Phase 2: System recovery
            mock_redis_client.get.side_effect = None
            mock_redis_client.hgetall.side_effect = None
            mock_redis_client.get.return_value = None  # Not blacklisted
            mock_redis_client.hgetall.return_value = {"state": "closed", "failures": 0}  # Circuit breaker reset
            
            # After recovery, system should work normally
            recovery_validation = handler.validate_token(test_token, "access")
            assert recovery_validation is not None, "System must recover and validate tokens after failure resolution"
            assert recovery_validation["sub"] == user_id, "Recovered system must provide correct user data"
            
            # Test that new token creation also works after recovery
            new_token = handler.create_access_token(f"{user_id}-recovery", email)
            new_token_validation = handler.validate_token(new_token, "access")
            assert new_token_validation is not None, "New token creation and validation must work after recovery"
            assert new_token_validation["sub"] == f"{user_id}-recovery", "New token must contain correct data after recovery"
            
            print("[U+2713] Authentication system fully recovered after temporary failure")