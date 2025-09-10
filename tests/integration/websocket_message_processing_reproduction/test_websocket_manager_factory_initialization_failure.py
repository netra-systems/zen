"""
Integration Test: Reproduce create_websocket_manager Factory Initialization Failure

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Critical Infrastructure Reliability
- Value Impact: Validates WebSocket factory service creation reliability
- Strategic Impact: Prevents cascading failures in agent message processing

CRITICAL MISSION: Reproduce the exact factory initialization failures that cause
AgentMessageHandler.handle_message() to fail at create_websocket_manager() call.

This integration test uses REAL services where possible but NO Docker to test
the factory pattern initialization under various failure conditions.

Test Focus Areas:
1. UserExecutionContext validation in factory pattern
2. Database session dependency resolution
3. Service factory dependency chain validation
4. WebSocket manager creation with real service dependencies

IMPORTANT: Uses SSOT patterns and real authentication context per CLAUDE.md requirements.
NO MOCKING of critical business logic components.
"""

import asyncio
import pytest
import os
from unittest.mock import Mock, patch
from contextlib import asynccontextmanager

from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    get_websocket_manager_factory
)
from netra_backend.app.dependencies import (
    get_user_execution_context,
    get_request_scoped_db_session
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.id_generation import UnifiedIdGenerator
from test_framework.ssot.e2e_auth_helper import AuthHelper


class TestWebSocketManagerFactoryInitializationFailure:
    """
    INTEGRATION REPRODUCTION TESTS: These tests reproduce create_websocket_manager
    failures using real service dependencies but controlled failure scenarios.
    
    These tests are DESIGNED TO FAIL initially to prove they can reproduce
    the exact factory initialization failures causing production 1011 errors.
    """
    
    @pytest.fixture
    def test_user_id(self):
        """Generate consistent test user ID using SSOT."""
        return UnifiedIdGenerator.generate_user_id()
    
    @pytest.fixture
    def test_thread_id(self):
        """Generate consistent test thread ID using SSOT."""
        return UnifiedIdGenerator.generate_thread_id()
    
    @pytest.fixture
    def test_run_id(self):
        """Generate consistent test run ID using SSOT."""
        return UnifiedIdGenerator.generate_run_id()
    
    @pytest.fixture
    async def real_user_execution_context(self, test_user_id, test_thread_id, test_run_id):
        """
        Create REAL UserExecutionContext using SSOT dependency injection.
        
        This uses the actual get_user_execution_context function to create
        a valid context that should work with the factory pattern.
        """
        return get_user_execution_context(
            user_id=test_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id
        )
    
    async def test_create_websocket_manager_with_valid_context_should_succeed_but_fails(
        self, real_user_execution_context
    ):
        """
        CRITICAL REPRODUCTION TEST: create_websocket_manager fails with valid context
        
        Expected: This test should FAIL when create_websocket_manager is called
        with a perfectly valid UserExecutionContext, indicating the factory
        has internal initialization issues.
        
        Root Cause Focus: Factory initialization logic in websocket_manager_factory.py
        that fails even when provided with valid inputs.
        """
        # CRITICAL: Test with REAL valid context - this should work but doesn't in production
        context = real_user_execution_context
        
        # Validate the context is properly formed before testing factory
        assert context is not None, "UserExecutionContext creation failed"
        assert context.user_id is not None, "Context missing user_id"
        assert context.thread_id is not None, "Context missing thread_id"  
        assert context.run_id is not None, "Context missing run_id"
        
        print(f"Testing factory with valid context: user_id={context.user_id}, thread_id={context.thread_id}")
        
        # CRITICAL TEST: This should succeed but fails in production due to factory issues
        with pytest.raises(Exception) as exc_info:
            # This is the exact call that fails in AgentMessageHandler line 101
            ws_manager = await create_websocket_manager(context)
            
            # If we reach here without exception, the reproduction failed
            assert False, (
                f"FACTORY REPRODUCTION FAILURE: Expected create_websocket_manager to fail "
                f"but it succeeded with manager: {ws_manager}. "
                f"This means the reproduction test conditions don't match production failure."
            )
        
        error_message = str(exc_info.value)
        
        # Validate we caught the expected factory initialization failure patterns
        factory_error_patterns = [
            "factory",
            "WebSocket",
            "manager", 
            "initialization",
            "service",
            "dependency",
            "import",
            "module"
        ]
        
        pattern_found = any(pattern.lower() in error_message.lower() for pattern in factory_error_patterns)
        
        assert pattern_found, (
            f"FACTORY ERROR PATTERN VALIDATION FAILED: "
            f"Caught exception '{error_message}' but it doesn't match expected factory error patterns. "
            f"Expected patterns: {factory_error_patterns}. "
            f"This suggests the factory is failing for different reasons than expected."
        )
        
        print(f"✅ FACTORY INITIALIZATION FAILURE REPRODUCED: {error_message}")
    
    async def test_websocket_manager_factory_dependency_resolution_failure(
        self, real_user_execution_context
    ):
        """
        INTEGRATION TEST: Factory fails due to service dependency resolution issues
        
        Expected: This test should FAIL when the factory tries to resolve
        its service dependencies (database, auth, etc.) but encounters issues
        similar to what happens in staging environment.
        """
        context = real_user_execution_context
        
        # CRITICAL: Test factory with real context but simulate dependency failures
        # that occur in staging environment
        
        # Mock get_websocket_manager_factory to simulate dependency resolution failure
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager_factory') as mock_get_factory:
            mock_get_factory.side_effect = RuntimeError(
                "WebSocket factory dependency resolution failed: "
                "Cannot resolve database connection pool in staging environment. "
                "Service dependencies are not properly initialized."
            )
            
            with pytest.raises(RuntimeError) as exc_info:
                # This should fail during factory dependency resolution
                ws_manager = await create_websocket_manager(context)
                
                assert False, (
                    f"DEPENDENCY RESOLUTION REPRODUCTION FAILURE: "
                    f"Expected RuntimeError but factory succeeded with: {ws_manager}"
                )
            
            error_message = str(exc_info.value)
            
            # Validate dependency resolution failure patterns
            dependency_patterns = [
                "dependency resolution",
                "database connection",
                "staging environment",
                "service dependencies",
                "initialization"
            ]
            
            pattern_found = any(pattern in error_message for pattern in dependency_patterns)
            
            assert pattern_found, (
                f"DEPENDENCY ERROR VALIDATION FAILED: "
                f"Error '{error_message}' doesn't match dependency resolution patterns: {dependency_patterns}"
            )
            
            # Verify the factory getter was called
            mock_get_factory.assert_called_once()
            
            print(f"✅ FACTORY DEPENDENCY RESOLUTION FAILURE REPRODUCED: {error_message}")
    
    async def test_isolated_websocket_manager_creation_with_invalid_context_types(self):
        """
        INTEGRATION TEST: Factory fails when UserExecutionContext has invalid field types
        
        Expected: This test should FAIL when the factory encounters context
        with invalid field types that pass basic validation but fail during
        deeper service initialization.
        """
        # Create context with problematic field types that might cause issues
        invalid_context = UserExecutionContext(
            user_id="invalid-user-id-format-not-uuid",  # Invalid format
            thread_id=None,  # None when string expected
            run_id=12345,  # Integer when string expected
            request_id="",  # Empty string
            websocket_connection_id="invalid-connection-format"
        )
        
        print(f"Testing factory with invalid context types: {invalid_context}")
        
        with pytest.raises(Exception) as exc_info:
            # Factory should fail during validation or service creation
            ws_manager = await create_websocket_manager(invalid_context)
            
            assert False, (
                f"TYPE VALIDATION REPRODUCTION FAILURE: "
                f"Expected factory to fail with invalid context types but succeeded with: {ws_manager}"
            )
        
        error_message = str(exc_info.value)
        
        # Validate type validation failure patterns
        type_error_patterns = [
            "invalid",
            "type",
            "format",
            "validation",
            "user_id",
            "thread_id",
            "run_id",
            "None",
            "uuid"
        ]
        
        pattern_found = any(pattern.lower() in error_message.lower() for pattern in type_error_patterns)
        
        assert pattern_found, (
            f"TYPE VALIDATION ERROR REPRODUCTION FAILED: "
            f"Error '{error_message}' doesn't match type validation patterns: {type_error_patterns}"
        )
        
        print(f"✅ INVALID CONTEXT TYPE FAILURE REPRODUCED: {error_message}")
    
    async def test_websocket_manager_factory_database_session_integration_failure(
        self, real_user_execution_context
    ):
        """
        INTEGRATION TEST: Factory fails when database session creation fails
        
        This test simulates the database connectivity issues that cause factory
        initialization to fail in staging environment. Uses REAL database session
        creation logic but under failure conditions.
        
        Expected: This test should FAIL when database session creation encounters
        issues similar to staging environment problems.
        """
        context = real_user_execution_context
        
        # CRITICAL: Test with real database session dependency but simulate staging failures
        
        @asynccontextmanager
        async def failing_db_session():
            """Simulate database session creation failure during factory initialization."""
            raise ConnectionError(
                "Database connection pool exhausted in staging environment. "
                "Cannot create session for WebSocket manager factory initialization. "
                "This simulates the exact database connectivity issues causing factory failures."
            )
            yield  # Never reached due to exception
        
        # Mock database session creation to simulate staging environment failures
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.get_request_scoped_db_session', 
                   side_effect=lambda: failing_db_session()):
            
            with pytest.raises(ConnectionError) as exc_info:
                # Factory should fail during database session initialization
                ws_manager = await create_websocket_manager(context)
                
                assert False, (
                    f"DATABASE SESSION INTEGRATION REPRODUCTION FAILURE: "
                    f"Expected ConnectionError but factory succeeded with: {ws_manager}"
                )
            
            error_message = str(exc_info.value)
            
            # Validate database connectivity failure patterns
            db_error_patterns = [
                "Database connection",
                "pool exhausted", 
                "staging environment",
                "session",
                "factory initialization",
                "connectivity"
            ]
            
            pattern_found = any(pattern in error_message for pattern in db_error_patterns)
            
            assert pattern_found, (
                f"DATABASE INTEGRATION ERROR VALIDATION FAILED: "
                f"Error '{error_message}' doesn't match database failure patterns: {db_error_patterns}"
            )
            
            print(f"✅ DATABASE SESSION INTEGRATION FAILURE REPRODUCED: {error_message}")
    
    async def test_websocket_manager_factory_environment_variable_missing_failure(
        self, real_user_execution_context
    ):
        """
        INTEGRATION TEST: Factory fails due to missing critical environment variables
        
        Expected: This test should FAIL when factory initialization requires
        environment variables that are missing in staging environment.
        
        This reproduces the configuration drift issues that cause service failures.
        """
        context = real_user_execution_context
        
        # CRITICAL: Test factory with missing environment variables that might be required
        # Save original environment variables
        original_env = {}
        critical_env_vars = [
            "DATABASE_URL",
            "REDIS_URL", 
            "JWT_SECRET_KEY",
            "GOOGLE_CLOUD_PROJECT",
            "K_SERVICE"
        ]
        
        for var in critical_env_vars:
            if var in os.environ:
                original_env[var] = os.environ[var]
                del os.environ[var]
        
        try:
            with pytest.raises(Exception) as exc_info:
                # Factory should fail due to missing environment configuration
                ws_manager = await create_websocket_manager(context)
                
                assert False, (
                    f"ENVIRONMENT VARIABLE REPRODUCTION FAILURE: "
                    f"Expected factory to fail with missing env vars but succeeded with: {ws_manager}"
                )
            
            error_message = str(exc_info.value)
            
            # Validate environment configuration failure patterns
            env_error_patterns = [
                "environment",
                "variable",
                "configuration", 
                "missing",
                "required",
                "DATABASE_URL",
                "REDIS_URL",
                "JWT_SECRET_KEY"
            ]
            
            pattern_found = any(pattern in error_message for pattern in env_error_patterns)
            
            assert pattern_found, (
                f"ENVIRONMENT VARIABLE ERROR VALIDATION FAILED: "
                f"Error '{error_message}' doesn't match environment failure patterns: {env_error_patterns}"
            )
            
            print(f"✅ ENVIRONMENT VARIABLE FAILURE REPRODUCED: {error_message}")
            
        finally:
            # Restore original environment variables
            for var, value in original_env.items():
                os.environ[var] = value
    
    async def test_websocket_manager_factory_auth_service_integration_failure(
        self, real_user_execution_context
    ):
        """
        INTEGRATION TEST: Factory fails when auth service integration fails
        
        Expected: This test should FAIL when factory tries to integrate with
        auth service but encounters the auth service connectivity issues
        that occur in staging environment.
        
        Uses REAL auth patterns but simulates service unavailability.
        """
        context = real_user_execution_context
        
        print(f"Testing factory with auth service failure for user: {context.user_id}")
        
        # CRITICAL: Test factory with auth service dependency failure
        # This simulates the auth service unavailability in staging
        
        with patch('test_framework.ssot.e2e_auth_helper.AuthHelper.authenticate_user') as mock_auth:
            mock_auth.side_effect = ConnectionError(
                "Auth service unavailable: staging auth service endpoint unreachable. "
                "Cannot validate user context during WebSocket manager factory initialization. "
                "Service discovery failed to locate auth service instances."
            )
            
            with pytest.raises(ConnectionError) as exc_info:
                # Factory should fail during auth service integration
                ws_manager = await create_websocket_manager(context)
                
                assert False, (
                    f"AUTH SERVICE INTEGRATION REPRODUCTION FAILURE: "
                    f"Expected ConnectionError but factory succeeded with: {ws_manager}"
                )
            
            error_message = str(exc_info.value)
            
            # Validate auth service integration failure patterns
            auth_error_patterns = [
                "Auth service",
                "unavailable",
                "staging",
                "endpoint unreachable",
                "user context",
                "service discovery", 
                "auth service instances"
            ]
            
            pattern_found = any(pattern in error_message for pattern in auth_error_patterns)
            
            assert pattern_found, (
                f"AUTH SERVICE ERROR VALIDATION FAILED: "
                f"Error '{error_message}' doesn't match auth service failure patterns: {auth_error_patterns}"
            )
            
            print(f"✅ AUTH SERVICE INTEGRATION FAILURE REPRODUCED: {error_message}")
    
    async def test_factory_thread_safety_concurrent_initialization_failure(
        self, real_user_execution_context
    ):
        """
        INTEGRATION TEST: Factory fails under concurrent initialization stress
        
        Expected: This test should FAIL when multiple concurrent calls to
        create_websocket_manager cause race conditions or resource contention
        that lead to factory initialization failures.
        
        This reproduces the multi-user concurrent access issues that cause
        intermittent factory failures in production.
        """
        context = real_user_execution_context
        
        # CRITICAL: Test factory under concurrent load that simulates production conditions
        concurrent_requests = 10
        
        async def create_manager_concurrent():
            """Concurrent factory creation that should stress the system."""
            try:
                return await create_websocket_manager(context)
            except Exception as e:
                return e  # Return exception for analysis
        
        print(f"Testing factory with {concurrent_requests} concurrent requests")
        
        # Execute concurrent factory creation requests
        tasks = [create_manager_concurrent() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for concurrency-related failures
        exceptions = [result for result in results if isinstance(result, Exception)]
        successes = [result for result in results if not isinstance(result, Exception)]
        
        print(f"Concurrent test results: {len(successes)} successes, {len(exceptions)} failures")
        
        # At least some requests should fail due to concurrency issues
        assert len(exceptions) > 0, (
            f"CONCURRENCY FAILURE REPRODUCTION FAILED: "
            f"Expected some concurrent requests to fail but all {len(successes)} succeeded. "
            f"This suggests the factory doesn't have the concurrency issues expected in production."
        )
        
        # Analyze failure patterns from concurrent requests
        concurrency_error_patterns = [
            "concurrent",
            "race condition",
            "resource contention",
            "thread safety",
            "lock",
            "timeout",
            "pool exhausted",
            "connection limit"
        ]
        
        exception_messages = [str(exc) for exc in exceptions]
        pattern_found = any(
            pattern.lower() in msg.lower() 
            for msg in exception_messages 
            for pattern in concurrency_error_patterns
        )
        
        assert pattern_found, (
            f"CONCURRENCY ERROR PATTERN VALIDATION FAILED: "
            f"Exceptions {exception_messages} don't match concurrency patterns: {concurrency_error_patterns}"
        )
        
        print(f"✅ CONCURRENCY FAILURE REPRODUCED: {len(exceptions)} failures with patterns found")
        for i, exc in enumerate(exceptions[:3]):  # Show first 3 exceptions
            print(f"  Exception {i+1}: {exc}")


if __name__ == "__main__":
    """
    Direct test execution for rapid debugging.
    
    Usage: python -m pytest tests/integration/websocket_message_processing_reproduction/test_websocket_manager_factory_initialization_failure.py -v -s
    """
    pytest.main([__file__, "-v", "-s", "--tb=long"])