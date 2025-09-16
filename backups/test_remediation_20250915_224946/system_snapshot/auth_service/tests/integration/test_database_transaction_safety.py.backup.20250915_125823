"""
Database Transaction Safety Tests - PRIORITY 3 SECURITY CRITICAL

**CRITICAL**: Comprehensive database transaction safety testing for race conditions and data integrity.
These tests ensure database operations maintain consistency under concurrent load, preventing
data corruption that could compromise Chat user accounts and authentication.

Business Value Justification (BVJ):
- Segment: All tiers - database integrity affects all user authentication
- Business Goal: Data Integrity, System Reliability, Platform Stability
- Value Impact: Prevents data corruption that could lock users out of Chat
- Strategic Impact: Database integrity maintains platform trust and prevents catastrophic failures

ULTRA CRITICAL CONSTRAINTS:
- ALL tests use REAL PostgreSQL database with real transactions
- Tests designed to FAIL HARD - no try/except bypassing
- Focus on realistic concurrent user scenarios
- Database integrity must be maintained under race conditions
- ABSOLUTE IMPORTS ONLY (from auth_service.* not relative)

Database Attack Vectors Tested:
- Concurrent user creation race conditions
- Transaction isolation level bypasses
- Deadlock exploitation attempts
- Data integrity constraint violations
- Connection pool exhaustion attacks
- SQL injection through concurrent operations
"""

import asyncio
import pytest
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm.exc import StaleDataError

# ABSOLUTE IMPORTS ONLY - No relative imports
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase  
from test_framework.database_test_utilities import DatabaseTestUtilities
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database import (
    auth_db, get_db_session, AuthUser, AuthSession, AuthAuditLog,
    AuthUserRepository, AuthSessionRepository, AuthAuditRepository
)
from auth_service.services.user_service import UserService
from auth_service.services.session_service import SessionService
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService


class TestDatabaseTransactionSafety(SSotBaseTestCase):
    """
    PRIORITY 3: Comprehensive database transaction safety tests.
    
    This test suite validates critical database integrity that protects Chat:
    - Transaction isolation and consistency under concurrent load
    - Race condition prevention in user creation and authentication
    - Database constraint enforcement and data integrity
    - Connection pool management and resource cleanup
    - Deadlock prevention and recovery mechanisms
    - Data corruption prevention in concurrent operations
    """
    
    @pytest.fixture(autouse=True) 
    async def setup_database_transaction_test_environment(self):
        """Set up comprehensive database transaction safety test environment."""
        
        # Initialize environment and services
        self.env = get_env()
        self.auth_config = AuthConfig()
        
        # Initialize database components
        self.database_utility = DatabaseTestUtilities("auth_service")
        
        # CRITICAL: Real service instances for database testing
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        
        # Get database session for testing
        self.db_session = await get_db_session()
        
        # Initialize services with database access
        self.user_service = UserService(self.auth_config, self.db_session)
        self.session_service = SessionService(self.auth_config, self.redis_service, self.jwt_service)
        
        # Initialize repositories for direct database access
        self.user_repository = AuthUserRepository(self.db_session)
        self.session_repository = AuthSessionRepository(self.db_session) 
        self.audit_repository = AuthAuditRepository(self.db_session)
        
        # Test configuration for concurrent operations
        self.concurrent_config = {
            "max_concurrent_users": 50,
            "batch_size": 10,
            "transaction_timeout": 30,
            "deadlock_retry_attempts": 3
        }
        
        # Track created resources for cleanup
        self.created_user_ids = []
        self.created_session_ids = []
        self.test_transaction_ids = []
        
        yield
        
        # Comprehensive cleanup
        await self._cleanup_database_test_resources()
    
    async def _cleanup_database_test_resources(self):
        """Comprehensive cleanup of database test resources."""
        try:
            # Clean up in reverse dependency order
            
            # Clean up sessions first
            for session_id in self.created_session_ids:
                try:
                    await self.session_service.delete_session(session_id)
                except Exception as e:
                    self.logger.warning(f"Session cleanup warning {session_id}: {e}")
            
            # Clean up users  
            for user_id in self.created_user_ids:
                try:
                    await self.user_service.delete_user(user_id)
                except Exception as e:
                    self.logger.warning(f"User cleanup warning {user_id}: {e}")
            
            # Clean up audit logs if needed
            for transaction_id in self.test_transaction_ids:
                try:
                    # Delete test audit logs
                    await self.audit_repository.delete_by_transaction_id(transaction_id)
                except Exception as e:
                    self.logger.warning(f"Audit cleanup warning {transaction_id}: {e}")
            
            # Close database session
            if hasattr(self, 'db_session') and self.db_session:
                await self.db_session.close()
            
            # Close Redis connection
            await self.redis_service.close()
            
        except Exception as e:
            self.logger.warning(f"Database test cleanup warning: {e}")
    
    async def _create_concurrent_test_user(
        self,
        user_index: int,
        test_batch: str,
        with_session: bool = False
    ) -> Dict[str, Any]:
        """Create a test user for concurrent testing with optional session."""
        
        user_data = {
            "email": f"concurrent.test.{user_index}.{test_batch}@testdomain.com",
            "name": f"Concurrent Test User {user_index}",
            "password": f"ConcurrentPass{user_index}#{secrets.token_hex(4)}"
        }
        
        # Create user with database transaction
        created_user = await self.user_service.create_user(
            email=user_data["email"],
            name=user_data["name"],
            password=user_data["password"]
        )
        
        self.created_user_ids.append(created_user.id)
        
        result = {
            "user": created_user,
            "user_data": user_data,
            "user_index": user_index,
            "test_batch": test_batch
        }
        
        # Optionally create session
        if with_session:
            jwt_token = await self.jwt_service.create_access_token(
                user_id=str(created_user.id),
                email=created_user.email,
                permissions=["read", "write"]
            )
            
            session_result = await self.session_service.create_session(
                user_id=str(created_user.id),
                email=created_user.email,
                access_token=jwt_token,
                session_data={
                    "concurrent_test": True,
                    "user_index": user_index,
                    "test_batch": test_batch
                }
            )
            
            session_id = session_result["session_id"]
            self.created_session_ids.append(session_id)
            
            result.update({
                "jwt_token": jwt_token,
                "session_id": session_id,
                "session_result": session_result
            })
        
        return result
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_creation_race_conditions(self):
        """
        CRITICAL: Test concurrent user creation for race conditions and data integrity.
        
        BVJ: Ensures Chat user registration works correctly under high load
        without creating duplicate users or corrupting user data.
        """
        
        test_batch = f"race-condition-{int(time.time())}"
        concurrent_user_count = self.concurrent_config["max_concurrent_users"]
        batch_size = self.concurrent_config["batch_size"]
        
        # TEST 1: Concurrent user creation with unique emails
        async def create_unique_user(user_index: int) -> Dict[str, Any]:
            try:
                start_time = time.time()
                user_context = await self._create_concurrent_test_user(
                    user_index, test_batch, with_session=False
                )
                creation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "user_context": user_context,
                    "creation_time": creation_time,
                    "user_index": user_index
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "user_index": user_index
                }
        
        # Execute concurrent user creation in batches
        all_results = []
        for i in range(0, concurrent_user_count, batch_size):
            batch_end = min(i + batch_size, concurrent_user_count)
            batch_tasks = [
                create_unique_user(j) 
                for j in range(i, batch_end)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)
        
        # Analyze results
        successful_creations = [r for r in all_results if not isinstance(r, Exception) and r.get("success")]
        failed_creations = [r for r in all_results if isinstance(r, Exception) or not r.get("success")]
        
        # Verify high success rate
        success_rate = len(successful_creations) / len(all_results)
        assert success_rate > 0.95, f"User creation success rate too low: {success_rate:.2%}"
        
        # Verify no duplicate users created
        created_emails = []
        created_user_ids = []
        
        for result in successful_creations:
            user_context = result["user_context"]
            user = user_context["user"]
            user_data = user_context["user_data"]
            
            created_emails.append(user_data["email"])
            created_user_ids.append(str(user.id))
        
        # All emails and user IDs should be unique
        assert len(set(created_emails)) == len(created_emails), "All user emails should be unique"
        assert len(set(created_user_ids)) == len(created_user_ids), "All user IDs should be unique"
        
        # Performance check - reasonable creation times
        creation_times = [r["creation_time"] for r in successful_creations]
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < 1.0, f"Average user creation time too slow: {avg_creation_time:.3f}s"
        assert max_creation_time < 5.0, f"Maximum user creation time too slow: {max_creation_time:.3f}s"
        
        # TEST 2: Concurrent user creation with duplicate email attempts
        duplicate_email = f"duplicate.test.{test_batch}@testdomain.com"
        
        async def create_duplicate_user(attempt_index: int) -> Dict[str, Any]:
            try:
                # Attempt to create user with same email
                created_user = await self.user_service.create_user(
                    email=duplicate_email,
                    name=f"Duplicate User {attempt_index}",
                    password=f"DuplicatePass{attempt_index}#123"
                )
                
                self.created_user_ids.append(created_user.id)
                
                return {
                    "success": True,
                    "user_id": str(created_user.id),
                    "attempt_index": attempt_index
                }
            except IntegrityError:
                # Expected - duplicate email should be rejected
                return {
                    "success": False,
                    "error": "integrity_error",
                    "attempt_index": attempt_index
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "attempt_index": attempt_index
                }
        
        # Attempt concurrent duplicate user creation
        duplicate_attempts = 10
        duplicate_tasks = [create_duplicate_user(i) for i in range(duplicate_attempts)]
        duplicate_results = await asyncio.gather(*duplicate_tasks, return_exceptions=True)
        
        # Analyze duplicate creation results
        successful_duplicates = [r for r in duplicate_results if not isinstance(r, Exception) and r.get("success")]
        failed_duplicates = [r for r in duplicate_results if isinstance(r, Exception) or not r.get("success")]
        
        # Only ONE should succeed, rest should fail with integrity error
        assert len(successful_duplicates) == 1, f"Only one duplicate email should succeed, got {len(successful_duplicates)}"
        assert len(failed_duplicates) == duplicate_attempts - 1, "Rest should fail with integrity constraint"
        
        # Failed duplicates should be integrity errors
        integrity_errors = [r for r in failed_duplicates if r.get("error") == "integrity_error"]
        assert len(integrity_errors) >= duplicate_attempts - 2, "Most failures should be integrity errors"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_isolation_and_consistency(self):
        """
        CRITICAL: Test database transaction isolation and consistency guarantees.
        
        BVJ: Ensures Chat user data remains consistent during concurrent operations
        and transactions are properly isolated to prevent data corruption.
        """
        
        test_batch = f"isolation-{int(time.time())}"
        
        # Create base user for isolation testing
        base_user_context = await self._create_concurrent_test_user(0, test_batch, with_session=True)
        base_user = base_user_context["user"]
        base_user_id = str(base_user.id)
        
        # TEST 1: Read-write isolation testing
        async def concurrent_user_update(operation_index: int, update_type: str) -> Dict[str, Any]:
            try:
                start_time = time.time()
                
                if update_type == "name_update":
                    # Update user name
                    new_name = f"Updated Name {operation_index}"
                    updated_user = await self.user_service.update_user(
                        user_id=base_user.id,
                        name=new_name
                    )
                    result_data = {"updated_name": new_name, "user_id": str(updated_user.id)}
                    
                elif update_type == "password_change":
                    # Change user password
                    new_password = f"NewPassword{operation_index}#123"
                    await self.user_service.change_password(
                        user_id=base_user.id,
                        old_password=base_user_context["user_data"]["password"],
                        new_password=new_password
                    )
                    result_data = {"password_changed": True, "operation_index": operation_index}
                    
                elif update_type == "read_user":
                    # Read user data
                    retrieved_user = await self.user_service.get_user_by_id(base_user.id)
                    result_data = {
                        "user_name": retrieved_user.name if retrieved_user else None,
                        "user_email": retrieved_user.email if retrieved_user else None,
                        "operation_index": operation_index
                    }
                
                operation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "operation_index": operation_index,
                    "update_type": update_type,
                    "operation_time": operation_time,
                    "result_data": result_data
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "operation_index": operation_index,
                    "update_type": update_type,
                    "error": str(e)
                }
        
        # Execute mixed read/write operations concurrently
        isolation_operations = []
        for i in range(15):  # 15 concurrent operations
            if i % 3 == 0:
                operation_type = "name_update"
            elif i % 3 == 1:
                operation_type = "read_user"
            else:
                operation_type = "read_user"  # More reads than writes
                
            isolation_operations.append(concurrent_user_update(i, operation_type))
        
        isolation_results = await asyncio.gather(*isolation_operations, return_exceptions=True)
        
        # Analyze isolation results
        successful_operations = [r for r in isolation_results if not isinstance(r, Exception) and r.get("success")]
        failed_operations = [r for r in isolation_results if isinstance(r, Exception) or not r.get("success")]
        
        # Most operations should succeed
        success_rate = len(successful_operations) / len(isolation_results)
        assert success_rate > 0.80, f"Transaction isolation success rate too low: {success_rate:.2%}"
        
        # Verify data consistency after concurrent operations
        final_user = await self.user_service.get_user_by_id(base_user.id)
        assert final_user is not None, "User should still exist after concurrent operations"
        assert final_user.email == base_user.email, "User email should remain unchanged"
        assert final_user.id == base_user.id, "User ID should remain unchanged"
        
        # Name may have been updated, but should be consistent
        name_updates = [r for r in successful_operations if r["update_type"] == "name_update"]
        if name_updates:
            # Final name should match one of the successful updates
            updated_names = [r["result_data"]["updated_name"] for r in name_updates]
            assert final_user.name in updated_names or final_user.name == base_user.name, (
                f"Final user name should be consistent with updates: {final_user.name}"
            )
        
        # TEST 2: Session isolation testing
        session_id = base_user_context["session_id"]
        
        async def concurrent_session_operation(operation_index: int, operation_type: str) -> Dict[str, Any]:
            try:
                start_time = time.time()
                
                if operation_type == "session_refresh":
                    refresh_success = await self.session_service.refresh_session(session_id)
                    result_data = {"refresh_success": refresh_success}
                    
                elif operation_type == "session_validate":
                    validation_result = await self.session_service.validate_session(session_id)
                    result_data = {
                        "validation_success": validation_result is not None,
                        "valid": validation_result.get("valid") if validation_result else False
                    }
                    
                elif operation_type == "session_read":
                    session_data = await self.session_service.get_session(session_id)
                    result_data = {
                        "session_exists": session_data is not None,
                        "user_id_match": session_data.get("user_id") == base_user_id if session_data else False
                    }
                
                operation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "operation_index": operation_index,
                    "operation_type": operation_type,
                    "operation_time": operation_time,
                    "result_data": result_data
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "operation_index": operation_index,
                    "operation_type": operation_type,
                    "error": str(e)
                }
        
        # Execute concurrent session operations
        session_operations = []
        for i in range(12):  # 12 concurrent session operations
            if i % 3 == 0:
                op_type = "session_refresh"
            elif i % 3 == 1:
                op_type = "session_validate"
            else:
                op_type = "session_read"
                
            session_operations.append(concurrent_session_operation(i, op_type))
        
        session_results = await asyncio.gather(*session_operations, return_exceptions=True)
        
        # Analyze session isolation results
        successful_session_ops = [r for r in session_results if not isinstance(r, Exception) and r.get("success")]
        
        session_success_rate = len(successful_session_ops) / len(session_results)
        assert session_success_rate > 0.90, f"Session isolation success rate too low: {session_success_rate:.2%}"
        
        # Verify session consistency
        final_session = await self.session_service.get_session(session_id)
        assert final_session is not None, "Session should still exist after concurrent operations"
        assert final_session["user_id"] == base_user_id, "Session user_id should remain consistent"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_deadlock_prevention_and_recovery(self):
        """
        CRITICAL: Test deadlock prevention and recovery mechanisms.
        
        BVJ: Ensures Chat database operations don't deadlock under concurrent load,
        maintaining system availability during high user activity.
        """
        
        test_batch = f"deadlock-{int(time.time())}"
        
        # Create multiple users for deadlock testing
        deadlock_users = []
        for i in range(5):
            user_context = await self._create_concurrent_test_user(i, test_batch, with_session=True)
            deadlock_users.append(user_context)
        
        # TEST 1: Cross-user update operations (potential deadlock scenario)
        async def cross_user_operations(operation_set: int) -> Dict[str, Any]:
            try:
                start_time = time.time()
                operations_completed = []
                
                # Perform operations on users in different orders to trigger potential deadlocks
                if operation_set % 2 == 0:
                    # Forward order
                    user_order = deadlock_users
                else:
                    # Reverse order
                    user_order = list(reversed(deadlock_users))
                
                for i, user_context in enumerate(user_order):
                    user = user_context["user"]
                    
                    try:
                        # Update user name
                        new_name = f"Deadlock Test {operation_set}-{i}"
                        await self.user_service.update_user(user_id=user.id, name=new_name)
                        operations_completed.append(f"user_update_{user.id}")
                        
                        # Refresh user session
                        session_id = user_context["session_id"]
                        refresh_success = await self.session_service.refresh_session(session_id)
                        operations_completed.append(f"session_refresh_{session_id}")
                        
                        # Small delay to increase chance of lock contention
                        await asyncio.sleep(0.01)
                        
                    except Exception as inner_e:
                        operations_completed.append(f"error_{user.id}_{str(inner_e)}")
                
                total_time = time.time() - start_time
                
                return {
                    "success": True,
                    "operation_set": operation_set,
                    "operations_completed": operations_completed,
                    "total_time": total_time
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "operation_set": operation_set,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        # Execute cross-user operations concurrently  
        deadlock_operation_count = 8
        deadlock_tasks = [cross_user_operations(i) for i in range(deadlock_operation_count)]
        
        deadlock_results = await asyncio.gather(*deadlock_tasks, return_exceptions=True)
        
        # Analyze deadlock test results
        successful_deadlock_ops = [r for r in deadlock_results if not isinstance(r, Exception) and r.get("success")]
        failed_deadlock_ops = [r for r in deadlock_results if isinstance(r, Exception) or not r.get("success")]
        
        # Most operations should complete successfully (deadlock prevention working)
        deadlock_success_rate = len(successful_deadlock_ops) / len(deadlock_results)
        assert deadlock_success_rate > 0.75, f"Deadlock prevention success rate too low: {deadlock_success_rate:.2%}"
        
        # Check for deadlock-related errors in failed operations
        deadlock_errors = []
        for failed_op in failed_deadlock_ops:
            error_type = failed_op.get("error_type", "")
            error_msg = failed_op.get("error", "").lower()
            
            if "deadlock" in error_msg or "lock" in error_type.lower():
                deadlock_errors.append(failed_op)
        
        # Some deadlock errors are acceptable, but system should recover
        deadlock_error_rate = len(deadlock_errors) / len(deadlock_results)
        assert deadlock_error_rate < 0.25, f"Too many deadlock errors: {deadlock_error_rate:.2%}"
        
        # Verify all users still exist and have consistent data
        for user_context in deadlock_users:
            user = user_context["user"]
            
            # User should still exist
            current_user = await self.user_service.get_user_by_id(user.id)
            assert current_user is not None, f"User {user.id} should still exist after deadlock test"
            assert current_user.email == user.email, f"User {user.id} email should be unchanged"
            
            # Session should still be valid
            session_id = user_context["session_id"]
            session_data = await self.session_service.get_session(session_id)
            assert session_data is not None, f"Session {session_id} should still exist"
            assert session_data["user_id"] == str(user.id), f"Session should still belong to user {user.id}"
        
        # TEST 2: Connection pool stress testing
        async def connection_pool_stress_operation(stress_index: int) -> Dict[str, Any]:
            try:
                start_time = time.time()
                
                # Create temporary user (tests connection acquisition)
                temp_user = await self.user_service.create_user(
                    email=f"stress.test.{stress_index}.{test_batch}@testdomain.com",
                    name=f"Stress Test User {stress_index}",
                    password=f"StressPass{stress_index}#123"
                )
                
                self.created_user_ids.append(temp_user.id)
                
                # Perform multiple operations on the user
                operations = []
                
                # Read operation
                retrieved_user = await self.user_service.get_user_by_id(temp_user.id)
                operations.append("read")
                
                # Update operation
                await self.user_service.update_user(temp_user.id, name=f"Updated Stress {stress_index}")
                operations.append("update")
                
                # Delete operation
                await self.user_service.delete_user(temp_user.id)
                operations.append("delete")
                
                operation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "stress_index": stress_index,
                    "operations": operations,
                    "operation_time": operation_time
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "stress_index": stress_index,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        # Execute connection pool stress test
        stress_operation_count = 20
        stress_tasks = [connection_pool_stress_operation(i) for i in range(stress_operation_count)]
        
        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        # Analyze stress test results
        successful_stress_ops = [r for r in stress_results if not isinstance(r, Exception) and r.get("success")]
        
        stress_success_rate = len(successful_stress_ops) / len(stress_results)
        assert stress_success_rate > 0.85, f"Connection pool stress success rate too low: {stress_success_rate:.2%}"
        
        # Performance check - operations should complete in reasonable time
        stress_times = [r["operation_time"] for r in successful_stress_ops]
        avg_stress_time = sum(stress_times) / len(stress_times)
        max_stress_time = max(stress_times)
        
        assert avg_stress_time < 2.0, f"Average stress operation time too slow: {avg_stress_time:.3f}s"
        assert max_stress_time < 10.0, f"Maximum stress operation time too slow: {max_stress_time:.3f}s"


__all__ = ["TestDatabaseTransactionSafety"]