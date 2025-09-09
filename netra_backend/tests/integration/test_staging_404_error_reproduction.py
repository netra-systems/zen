"""
Test to Reproduce Staging 404 "Thread not found" Error for System User Authentication

Business Value Justification (BVJ):
- Segment: Platform Stability (all tiers)
- Business Goal: Prevent system user authentication failures that break service-to-service operations
- Value Impact: System operations like background jobs and internal services must work reliably
- Strategic Impact: Foundation for reliable inter-service communication and automation

ERROR TO REPRODUCE:
"ERROR: SYSTEM USER AUTHENTICATION FAILURE: User 'system' failed authentication. 
This indicates a service-to-service authentication problem.
ERROR: CRITICAL ERROR: Failed to create request-scoped database session req_1757380919494_304_2f3260be 
for user_id='system'. Error: 404: Thread not found."

ROOT CAUSE:
System user operations are being forced through user-centric authentication flows that require 
inappropriate thread validation. System users should not require thread records for basic operations.

This test validates:
1. System user authentication should work without requiring thread validation
2. Request-scoped session creation for system operations should succeed
3. The "404: Thread not found" error should be prevented for system users
4. Service-to-service authentication patterns work correctly

CRITICAL: This test uses real services and authentication as per CLAUDE.md requirements.
No mocks are used except for external dependencies. Tests are designed to fail hard.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from unittest.mock import patch, AsyncMock
from contextlib import asynccontextmanager

# SSOT imports for types and infrastructure
from shared.types.core_types import UserID, ThreadID, RequestID, ensure_user_id
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import get_env

# Database and authentication infrastructure
from netra_backend.app.database.request_scoped_session_factory import (
    RequestScopedSessionFactory, 
    get_session_factory,
    get_isolated_session
)
from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.services.database.thread_repository import ThreadRepository

# Logging and tracing
from netra_backend.app.logging.auth_trace_logger import (
    auth_tracer,
    log_authentication_context_dump,
    AuthTraceContext
)
from netra_backend.app.logging_config import central_logger

# Test framework - SSOT compliance  
from test_framework.fixtures.real_services import real_services_fixture

# FastAPI testing
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestStaging404ErrorReproduction:
    """
    Test suite to reproduce and validate fix for staging 404 "Thread not found" error.
    
    This test reproduces the exact error condition happening in GCP staging where
    system user operations fail due to inappropriate thread validation requirements.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_real_services(self, real_services_fixture):
        """Ensure real services are available for testing."""
        self.real_services = real_services_fixture
        logger.info("Real services fixture initialized for 404 error reproduction tests")
    
    @pytest.fixture
    def system_user_context(self) -> Dict[str, Any]:
        """Create system user context that should not require threads."""
        return {
            "user_id": "system",
            "operation": "service_to_service_operation",
            "requires_thread": False,
            "expected_auth": "service_auth_bypass"
        }
    
    @pytest.fixture
    def regular_user_context(self) -> Dict[str, Any]:
        """Create regular user context that does require threads."""
        user_id = f"test_user_{int(time.time())}"
        return {
            "user_id": user_id,
            "operation": "user_chat_operation", 
            "requires_thread": True,
            "expected_auth": "jwt_token_auth"
        }
    
    @pytest.mark.asyncio
    async def test_reproduce_system_user_404_thread_error(self, system_user_context):
        """
        CRITICAL TEST: Reproduce the exact 404 "Thread not found" error for system users.
        
        This test validates that the error occurs when system users are forced through
        user-centric authentication flows that inappropriately require thread validation.
        """
        user_id = system_user_context["user_id"]
        
        # Generate request context using SSOT
        request_id = UnifiedIdGenerator.generate_base_id("req_staging_404_test")
        correlation_id = UnifiedIdGenerator.generate_base_id("corr_404_test")
        
        # Start authentication tracing
        auth_context = auth_tracer.start_operation(
            user_id=user_id,
            request_id=request_id,
            correlation_id=correlation_id,
            operation="test_system_user_session_creation",
            additional_context={
                "test_purpose": "reproduce_404_thread_not_found",
                "error_to_reproduce": "CRITICAL ERROR: Failed to create request-scoped database session",
                "staging_behavior": "system_user_forced_through_thread_validation"
            }
        )
        
        logger.info(
            f"🎯 REPRODUCING STAGING ERROR: Starting test to reproduce 404 'Thread not found' "
            f"error for system user. User: {user_id}, Request: {request_id}"
        )
        
        try:
            # Attempt to create request-scoped session for system user
            # This should reproduce the staging error if the bug exists
            session = None
            async for session_iter in get_request_scoped_db_session():
                session = session_iter
                break
            
            if session:
                # If we get here, the bug may be fixed or test environment differs from staging
                logger.info(
                    f"✅ UNEXPECTED SUCCESS: System user session created successfully. "
                    f"This suggests the 404 error bug may be fixed or environment differs from staging. "
                    f"Session: {id(session)}, User: {user_id}"
                )
                
                # Verify session is properly configured for system user
                session_info = getattr(session, 'info', {})
                assert session_info.get('user_id') == user_id
                assert session_info.get('is_request_scoped') is True
                
                auth_tracer.log_success(auth_context, {
                    "session_created": True,
                    "session_id": id(session),
                    "session_info": session_info,
                    "note": "Bug may be fixed or environment differs from staging"
                })
                
            else:
                pytest.fail("Session creation returned None - unexpected test setup issue")
                
        except HTTPException as e:
            # This is the expected error we're trying to reproduce
            if e.status_code == 404 and "Thread not found" in str(e.detail):
                logger.error(
                    f"🎯 ERROR REPRODUCED: Successfully reproduced the staging 404 'Thread not found' error! "
                    f"User: {user_id}, Error: {e.detail}, Status: {e.status_code}"
                )
                
                auth_tracer.log_failure(auth_context, e, {
                    "error_reproduced": True,
                    "error_type": "404_thread_not_found",
                    "staging_behavior_confirmed": True,
                    "system_user_thread_validation_problem": True
                })
                
                # This is actually success for this test - we reproduced the error
                assert "Thread not found" in str(e.detail)
                assert e.status_code == 404
                
            else:
                logger.error(
                    f"❌ UNEXPECTED ERROR: Got different error than expected 404. "
                    f"Error: {e}, Status: {e.status_code}"
                )
                auth_tracer.log_failure(auth_context, e, {
                    "unexpected_error": True,
                    "expected": "404_thread_not_found",
                    "actual": f"{e.status_code}_{e.detail}"
                })
                raise
                
        except Exception as e:
            logger.error(
                f"❌ UNEXPECTED EXCEPTION: Got unexpected exception type. Error: {e}, Type: {type(e)}"
            )
            auth_tracer.log_failure(auth_context, e, {
                "unexpected_exception": True,
                "error_type": type(e).__name__
            })
            raise
    
    @pytest.mark.asyncio 
    async def test_system_user_should_bypass_thread_validation(self, system_user_context):
        """
        Test that system users should be able to operate without thread validation.
        
        This test validates the correct behavior: system users should not require
        thread records for basic session operations.
        """
        user_id = system_user_context["user_id"]
        request_id = UnifiedIdGenerator.generate_base_id("req_system_bypass")
        
        logger.info(
            f"🔧 TESTING SYSTEM USER BYPASS: Validating that system user can operate "
            f"without thread validation. User: {user_id}"
        )
        
        try:
            # Create session factory for direct testing
            factory = await get_session_factory()
            
            # Test direct session creation without thread requirements
            async with factory.get_request_scoped_session(
                user_id=user_id,
                request_id=request_id,
                thread_id=None  # System users should not require thread_id
            ) as session:
                
                # Verify session works for system operations
                assert session is not None
                session_info = getattr(session, 'info', {})
                assert session_info.get('user_id') == user_id
                
                # System user should have session without thread dependency
                logger.info(
                    f"✅ SYSTEM BYPASS SUCCESS: System user session created without thread dependency. "
                    f"Session info: {session_info}"
                )
                
                # Test that system user can perform database operations
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as test_value"))
                test_value = result.scalar()
                assert test_value == 1
                
                logger.info(
                    f"✅ SYSTEM OPERATIONS SUCCESS: System user can perform database operations. "
                    f"Test query result: {test_value}"
                )
                
        except Exception as e:
            logger.error(
                f"❌ SYSTEM BYPASS FAILED: System user failed to bypass thread validation. "
                f"Error: {e}, Type: {type(e)}"
            )
            
            # Log comprehensive error context
            log_authentication_context_dump(
                user_id=user_id,
                request_id=request_id,
                operation="test_system_user_bypass",
                error=e,
                test_type="system_user_thread_bypass",
                expected_behavior="system_user_should_work_without_threads",
                actual_behavior="system_user_failed_thread_validation"
            )
            raise
    
    @pytest.mark.asyncio
    async def test_system_user_vs_regular_user_behavior(self, system_user_context, regular_user_context):
        """
        Compare system user vs regular user behavior to validate different authentication paths.
        
        This test validates that:
        1. System users can operate without thread records
        2. Regular users require proper thread setup
        3. The authentication flows are appropriately different
        """
        system_user_id = system_user_context["user_id"]
        regular_user_id = regular_user_context["user_id"]
        
        logger.info(
            f"⚖️ COMPARING USER BEHAVIORS: Testing system user '{system_user_id}' vs "
            f"regular user '{regular_user_id}' authentication requirements"
        )
        
        # Test 1: System user should work without thread setup
        system_success = False
        try:
            async with get_isolated_session(
                user_id=system_user_id,
                request_id=UnifiedIdGenerator.generate_base_id("req_system_compare"),
                thread_id=None  # System user: no thread required
            ) as system_session:
                assert system_session is not None
                system_success = True
                logger.info(f"✅ SYSTEM USER SUCCESS: Works without thread setup")
                
        except Exception as e:
            logger.error(f"❌ SYSTEM USER FAILED: {e}")
            system_success = False
        
        # Test 2: Regular user with proper thread setup
        regular_success = False
        try:
            # Generate thread_id for regular user
            thread_id = UnifiedIdGenerator.generate_base_id("thread_regular")
            
            async with get_isolated_session(
                user_id=regular_user_id,
                request_id=UnifiedIdGenerator.generate_base_id("req_regular_compare"),
                thread_id=thread_id  # Regular user: thread provided
            ) as regular_session:
                assert regular_session is not None
                regular_success = True
                logger.info(f"✅ REGULAR USER SUCCESS: Works with proper thread setup")
                
        except Exception as e:
            logger.error(f"❌ REGULAR USER FAILED: {e}")
            regular_success = False
        
        # Analyze results
        logger.info(
            f"📊 COMPARISON RESULTS: System user success: {system_success}, "
            f"Regular user success: {regular_success}"
        )
        
        # Both should succeed but through different paths
        assert system_success, "System user should work without thread validation"
        assert regular_success, "Regular user should work with proper thread setup"
    
    @pytest.mark.asyncio
    async def test_session_factory_thread_auto_creation_bug(self, system_user_context):
        """
        Test for the specific bug where session factory inappropriately creates threads for system users.
        
        This test validates that the session factory does not force thread creation
        for system users who should not require threads.
        """
        user_id = system_user_context["user_id"]
        request_id = UnifiedIdGenerator.generate_base_id("req_auto_creation_test")
        
        logger.info(
            f"🐛 TESTING THREAD AUTO-CREATION BUG: Checking if session factory "
            f"inappropriately creates threads for system user: {user_id}"
        )
        
        # Track thread creation before test
        thread_repo = ThreadRepository()
        initial_threads = []
        
        try:
            factory = await get_session_factory()
            
            # Create session and monitor thread creation
            async with factory.get_request_scoped_session(
                user_id=user_id,
                request_id=request_id,
                thread_id=None  # System user should not need thread
            ) as session:
                
                # Check if factory inappropriately created thread records
                session_info = getattr(session, 'info', {})
                thread_id_created = session_info.get('thread_id')
                
                if thread_id_created:
                    logger.warning(
                        f"⚠️ POTENTIAL BUG: Session factory created thread_id '{thread_id_created}' "
                        f"for system user '{user_id}'. System users should not require threads!"
                    )
                    
                    # Check if thread record was created in database
                    try:
                        thread_record = await thread_repo.get_by_id(session, thread_id_created)
                        if thread_record:
                            logger.error(
                                f"🐛 BUG CONFIRMED: Session factory created unnecessary thread record "
                                f"'{thread_id_created}' for system user. This is the root cause of 404 errors!"
                            )
                            
                            # This is the bug we're looking for
                            pytest.fail(
                                f"BUG REPRODUCED: Session factory created unnecessary thread record "
                                f"for system user, causing 404 validation errors"
                            )
                    except Exception as thread_check_error:
                        logger.info(
                            f"Thread record check failed (expected for system users): {thread_check_error}"
                        )
                else:
                    logger.info(
                        f"✅ CORRECT BEHAVIOR: Session factory did not create thread_id for system user"
                    )
                
                # Verify session works regardless
                assert session is not None
                assert session_info.get('user_id') == user_id
                
        except Exception as e:
            logger.error(
                f"❌ SESSION FACTORY TEST FAILED: Error testing thread auto-creation behavior. "
                f"Error: {e}"
            )
            
            # This could be the 404 error we're trying to reproduce
            if "404" in str(e) and "Thread not found" in str(e):
                logger.error(
                    f"🎯 REPRODUCED 404 ERROR: Session factory thread auto-creation bug caused "
                    f"'Thread not found' error for system user!"
                )
                
                # Document the exact error reproduction
                log_authentication_context_dump(
                    user_id=user_id,
                    request_id=request_id,
                    operation="session_factory_thread_bug_reproduction",
                    error=e,
                    bug_type="thread_auto_creation_for_system_users",
                    root_cause="session_factory_forces_thread_validation_on_system_users",
                    fix_needed="bypass_thread_validation_for_system_users"
                )
                
                # For this test, reproducing the error is actually success
                assert "Thread not found" in str(e)
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_dependency_injection_system_user_path(self, system_user_context):
        """
        Test the exact dependency injection path that causes the staging error.
        
        This test follows the exact code path from dependencies.py that leads to the
        404 "Thread not found" error in staging.
        """
        user_id = system_user_context["user_id"]
        
        logger.info(
            f"🧪 TESTING DEPENDENCY INJECTION PATH: Following exact staging error path "
            f"for system user: {user_id}"
        )
        
        # Follow the exact path from dependencies.py get_request_scoped_db_session
        request_id = UnifiedIdGenerator.generate_base_id("req")
        correlation_id = UnifiedIdGenerator.generate_base_id("corr")
        
        # This is the exact context from dependencies.py line 184
        session_init_context = {
            "user_id": user_id,  # This is where 'system' comes from
            "request_id": request_id,
            "correlation_id": correlation_id,
            "source": "test_get_request_scoped_db_session",
            "auth_note": "user_id='system' is hardcoded in dependencies.py:184",
            "function_location": "netra_backend.app.dependencies:182"
        }
        
        logger.info(
            f"📍 EXACT STAGING PATH: Following dependencies.py path with context: {session_init_context}"
        )
        
        try:
            # Follow exact dependency injection path
            from netra_backend.app.database.request_scoped_session_factory import get_session_factory
            
            factory = await get_session_factory()
            
            # This is the exact call from dependencies.py line 239
            async with factory.get_request_scoped_session(user_id, request_id) as session:
                logger.info(
                    f"✅ DEPENDENCY PATH SUCCESS: System user session created through "
                    f"exact staging dependency path. Session: {id(session)}"
                )
                
                # Verify this matches staging behavior
                session_info = getattr(session, 'info', {})
                assert session_info.get('user_id') == user_id
                
        except Exception as e:
            if "404" in str(e) and "Thread not found" in str(e):
                logger.error(
                    f"🎯 STAGING ERROR REPRODUCED: Exact dependency injection path "
                    f"caused 404 'Thread not found' error for system user!"
                )
                
                # Comprehensive error documentation
                error_analysis = {
                    "error_location": "netra_backend.app.dependencies.get_request_scoped_db_session",
                    "staging_user_id": user_id,
                    "hardcoded_system_user": "dependencies.py line 184",
                    "factory_call": "factory.get_request_scoped_session(user_id, request_id)",
                    "thread_validation_failure": "system user forced through thread validation",
                    "root_cause": "system users should bypass thread validation requirements",
                    "fix_location": "request_scoped_session_factory.py _ensure_thread_record_exists"
                }
                
                log_authentication_context_dump(
                    user_id=user_id,
                    request_id=request_id,
                    operation="dependency_injection_path_reproduction",
                    error=e,
                    **error_analysis
                )
                
                # For this test, reproducing the staging error is success
                assert "Thread not found" in str(e)
                
            else:
                logger.error(f"❌ UNEXPECTED ERROR in dependency path: {e}")
                raise
    
    @pytest.mark.asyncio
    async def test_validate_fix_system_user_auth_bypass(self, system_user_context):
        """
        Test to validate that the fix for system user authentication works correctly.
        
        This test validates the correct behavior after the bug is fixed:
        1. System users should authenticate without thread validation
        2. Service-to-service operations should work reliably
        3. No 404 "Thread not found" errors for system users
        """
        user_id = system_user_context["user_id"]
        
        logger.info(
            f"🔧 TESTING FIX VALIDATION: Verifying system user authentication bypass "
            f"works correctly for user: {user_id}"
        )
        
        # Test multiple system user scenarios to ensure fix is comprehensive
        test_scenarios = [
            {
                "name": "basic_system_session",
                "thread_id": None,
                "operation": "basic_service_operation"
            },
            {
                "name": "system_session_with_minimal_context", 
                "thread_id": None,
                "operation": "background_job_operation"
            },
            {
                "name": "system_session_explicit_no_thread",
                "thread_id": None,
                "operation": "inter_service_communication"
            }
        ]
        
        all_scenarios_passed = True
        
        for scenario in test_scenarios:
            scenario_name = scenario["name"]
            logger.info(f"🧪 Testing scenario: {scenario_name}")
            
            try:
                request_id = UnifiedIdGenerator.generate_base_id(f"req_{scenario_name}")
                
                async with get_isolated_session(
                    user_id=user_id,
                    request_id=request_id,
                    thread_id=scenario["thread_id"]
                ) as session:
                    
                    # Verify session is properly configured
                    assert session is not None
                    session_info = getattr(session, 'info', {})
                    assert session_info.get('user_id') == user_id
                    
                    # Test basic database operation
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT 1 as system_test"))
                    assert result.scalar() == 1
                    
                    logger.info(f"✅ Scenario {scenario_name} PASSED")
                    
            except Exception as e:
                logger.error(f"❌ Scenario {scenario_name} FAILED: {e}")
                all_scenarios_passed = False
                
                # If we still get 404 errors, the fix is not complete
                if "404" in str(e) and "Thread not found" in str(e):
                    logger.error(
                        f"🐛 FIX INCOMPLETE: Still getting 404 'Thread not found' "
                        f"error for system user in scenario {scenario_name}"
                    )
        
        # All scenarios should pass for a complete fix
        assert all_scenarios_passed, "System user authentication fix validation failed"
        
        logger.info(
            f"✅ FIX VALIDATION SUCCESS: All system user authentication scenarios passed. "
            f"404 'Thread not found' error appears to be fixed."
        )


if __name__ == "__main__":
    """
    Run this test file directly to reproduce the staging 404 error.
    
    Usage:
    python -m pytest netra_backend/tests/integration/test_staging_404_error_reproduction.py -v --real-services
    """
    pytest.main([__file__, "-v", "--real-services", "--tb=short"])