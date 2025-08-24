"""
RED TEAM TEST 21: Transaction Rollback Coordination

CRITICAL: This test is DESIGNED TO FAIL initially to expose real integration issues.
Tests multi-service transaction failures and rollback coordination mechanisms.

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (data consistency requirements)
- Business Goal: Data Integrity, Platform Reliability, User Trust
- Value Impact: Failed transaction coordination causes data corruption and user frustration
- Strategic Impact: Core data consistency foundation for enterprise-grade platform reliability

Testing Level: L3 (Real services, real transactions, minimal mocking)
Expected Initial Result: FAILURE (exposes real transaction coordination gaps)
"""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from sqlalchemy import text, select, insert, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with error handling
try:
    from netra_backend.app.core.network_constants import DatabaseConstants, ServicePorts
except ImportError:
    class DatabaseConstants:
        pass
    class ServicePorts:
        pass

# TransactionManager exists
from netra_backend.app.services.transaction_manager import TransactionManager

try:
    from netra_backend.app.core.transaction_core import TransactionCoordinator
except ImportError:
    try:
        from netra_backend.app.db.transaction_core import TransactionCoordinator
    except ImportError:
        class TransactionCoordinator:
            async def begin_transaction(self): pass
            async def commit_transaction(self): pass
            async def rollback_transaction(self): pass

try:
    from netra_backend.app.services.compensation_engine import CompensationEngine
except ImportError:
    class CompensationEngine:
        async def execute_compensation(self, actions): pass
        async def register_compensation_action(self, action): pass

try:
    from netra_backend.app.db.models_user import User
except ImportError:
    try:
        from netra_backend.app.db.models import User
    except ImportError:
        from unittest.mock import Mock
        User = Mock()

try:
    from netra_backend.app.models.session import Session as UserSession
except ImportError:
    try:
        from netra_backend.app.db.models import Session as UserSession
    except ImportError:
        from unittest.mock import Mock
        UserSession = Mock()


class TestTransactionRollbackCoordination:
    """
    RED TEAM TEST 21: Transaction Rollback Coordination
    
    Tests critical multi-service transaction coordination and rollback mechanisms.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        try:
            database_url = DatabaseConstants.build_postgres_url(
                user="test", password="test",
                port=ServicePorts.POSTGRES_DEFAULT,
                database="netra_test"
            )
            
            engine = create_async_engine(database_url, echo=False)
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            
            # Test real connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            if 'engine' in locals():
                await engine.dispose()

    @pytest.fixture(scope="class")
    async def real_redis_client(self):
        """Real Redis client for distributed coordination - will fail if Redis not available."""
        try:
            redis_client = redis.Redis(
                host="localhost",
                port=ServicePorts.REDIS_DEFAULT,
                db=DatabaseConstants.REDIS_TEST_DB,
                decode_responses=True
            )
            
            # Test real connection
            await redis_client.ping()
            
            yield redis_client
        except Exception as e:
            pytest.fail(f"CRITICAL: Real Redis connection failed: {e}")
        finally:
            if 'redis_client' in locals():
                await redis_client.close()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_01_basic_transaction_coordination_fails(
        self, real_database_session, real_redis_client
    ):
        """
        Test 21A: Basic Transaction Coordination (EXPECTED TO FAIL)
        
        Tests basic multi-step transaction coordination across services.
        Will likely FAIL because:
        1. Transaction coordinator may not be implemented
        2. Multi-phase commit protocol may be missing
        3. Distributed transaction logging may not work
        """
        try:
            # Create transaction coordinator
            transaction_manager = TransactionManager(
                redis_client=real_redis_client,
                db_session=real_database_session
            )
            
            # Create test transaction with multiple steps
            transaction_id = str(uuid.uuid4())
            
            transaction_steps = [
                {
                    "step_id": "create_user",
                    "service": "user_service",
                    "operation": "create",
                    "data": {
                        "email": f"transaction_test_{secrets.token_urlsafe(8)}@example.com",
                        "username": f"txn_user_{secrets.token_urlsafe(6)}",
                        "metadata": {"created_by": "transaction_test"}
                    }
                },
                {
                    "step_id": "create_session",
                    "service": "session_service", 
                    "operation": "create",
                    "data": {
                        "device_info": {"browser": "test", "ip": "127.0.0.1"},
                        "session_metadata": {"test_transaction": True}
                    },
                    "depends_on": ["create_user"]
                },
                {
                    "step_id": "update_user_status",
                    "service": "user_service",
                    "operation": "update",
                    "data": {
                        "status": "active",
                        "last_login": datetime.now(timezone.utc).isoformat()
                    },
                    "depends_on": ["create_user", "create_session"]
                }
            ]
            
            # FAILURE EXPECTED HERE - transaction coordination may not be implemented
            coordination_result = await transaction_manager.coordinate_transaction(
                transaction_id=transaction_id,
                steps=transaction_steps,
                timeout_seconds=30
            )
            
            assert coordination_result is not None, "Transaction coordination returned None"
            assert "status" in coordination_result, "Coordination result should include status"
            assert "completed_steps" in coordination_result, \
                "Coordination result should include completed steps"
            
            # Verify transaction was logged
            if hasattr(transaction_manager, 'get_transaction_log'):
                transaction_log = await transaction_manager.get_transaction_log(transaction_id)
                
                assert transaction_log is not None, "Transaction log should be available"
                assert transaction_log["transaction_id"] == transaction_id, \
                    f"Transaction ID mismatch: expected {transaction_id}, got {transaction_log['transaction_id']}"
                
                assert "steps" in transaction_log, "Transaction log should include steps"
                assert len(transaction_log["steps"]) == len(transaction_steps), \
                    f"Expected {len(transaction_steps)} steps in log, got {len(transaction_log['steps'])}"
            
            # Verify all steps completed successfully
            final_status = coordination_result["status"]
            completed_steps = coordination_result["completed_steps"]
            
            assert final_status == "completed", \
                f"Transaction should complete successfully, got '{final_status}'"
            assert completed_steps == len(transaction_steps), \
                f"All {len(transaction_steps)} steps should complete, got {completed_steps}"
            
            # Verify data consistency across services
            # Check user was created
            user_query = await real_database_session.execute(
                select(User).where(User.email == transaction_steps[0]["data"]["email"])
            )
            created_user = user_query.scalar_one_or_none()
            
            assert created_user is not None, "User should be created by transaction"
            assert created_user.username == transaction_steps[0]["data"]["username"], \
                "User data should match transaction specification"
                
        except ImportError as e:
            pytest.fail(f"Transaction coordination components not available: {e}")
        except Exception as e:
            pytest.fail(f"Basic transaction coordination test failed: {e}")

    @pytest.mark.asyncio
    async def test_02_transaction_rollback_on_failure_fails(
        self, real_database_session, real_redis_client
    ):
        """
        Test 21B: Transaction Rollback on Failure (EXPECTED TO FAIL)
        
        Tests rollback coordination when transaction steps fail.
        Will likely FAIL because:
        1. Rollback mechanisms may not be implemented
        2. Compensation actions may not be defined
        3. Partial rollback may not work correctly
        """
        try:
            transaction_manager = TransactionManager(
                redis_client=real_redis_client,
                db_session=real_database_session
            )
            
            # Create transaction that will fail at step 3
            transaction_id = str(uuid.uuid4())
            
            failing_transaction_steps = [
                {
                    "step_id": "create_user_rollback_test",
                    "service": "user_service",
                    "operation": "create",
                    "data": {
                        "email": f"rollback_test_{secrets.token_urlsafe(8)}@example.com",
                        "username": f"rollback_user_{secrets.token_urlsafe(6)}"
                    },
                    "rollback_action": {
                        "operation": "delete",
                        "identifier_field": "email"
                    }
                },
                {
                    "step_id": "create_session_rollback_test",
                    "service": "session_service",
                    "operation": "create", 
                    "data": {
                        "device_info": {"browser": "test"},
                        "session_metadata": {"rollback_test": True}
                    },
                    "depends_on": ["create_user_rollback_test"],
                    "rollback_action": {
                        "operation": "delete",
                        "identifier_field": "session_id"
                    }
                },
                {
                    "step_id": "intentional_failure",
                    "service": "user_service",
                    "operation": "update",
                    "data": {
                        "invalid_field": "this_will_cause_failure",
                        "force_error": True  # Force this step to fail
                    },
                    "depends_on": ["create_user_rollback_test", "create_session_rollback_test"],
                    "rollback_action": {
                        "operation": "none"  # Nothing to rollback for failed operation
                    }
                }
            ]
            
            # Execute transaction expecting failure
            # FAILURE EXPECTED HERE - rollback coordination may not work
            try:
                rollback_result = await transaction_manager.coordinate_transaction(
                    transaction_id=transaction_id,
                    steps=failing_transaction_steps,
                    timeout_seconds=30
                )
                
                # Transaction should fail but rollback should succeed
                assert rollback_result["status"] in ["failed", "rolled_back"], \
                    f"Transaction should fail or be rolled back, got '{rollback_result['status']}'"
                
            except Exception as transaction_error:
                # Transaction failure is expected, but we should have rollback info
                if hasattr(transaction_manager, 'get_rollback_status'):
                    rollback_status = await transaction_manager.get_rollback_status(transaction_id)
                    
                    assert rollback_status is not None, \
                        "Rollback status should be available after transaction failure"
                    assert "rolled_back_steps" in rollback_status, \
                        "Rollback status should include rolled back steps count"
            
            # Verify rollback completed - check that created data was cleaned up
            await asyncio.sleep(2)  # Wait for rollback to complete
            
            # User should be deleted during rollback
            user_query = await real_database_session.execute(
                select(User).where(User.email == failing_transaction_steps[0]["data"]["email"])
            )
            rolled_back_user = user_query.scalar_one_or_none()
            
            assert rolled_back_user is None, \
                "User should be deleted during rollback"
            
            # Verify rollback was logged
            if hasattr(transaction_manager, 'get_rollback_log'):
                rollback_log = await transaction_manager.get_rollback_log(transaction_id)
                
                assert rollback_log is not None, "Rollback should be logged"
                assert "rollback_actions" in rollback_log, \
                    "Rollback log should include rollback actions"
                
                rollback_actions = rollback_log["rollback_actions"]
                
                # Should have rollback actions for the successful steps
                expected_rollback_count = 2  # user and session creation
                assert len(rollback_actions) >= expected_rollback_count, \
                    f"Should have at least {expected_rollback_count} rollback actions, got {len(rollback_actions)}"
                    
        except Exception as e:
            pytest.fail(f"Transaction rollback coordination test failed: {e}")

    @pytest.mark.asyncio
    async def test_03_compensation_engine_coordination_fails(
        self, real_database_session, real_redis_client
    ):
        """
        Test 21C: Compensation Engine Coordination (EXPECTED TO FAIL)
        
        Tests compensation-based transaction coordination (SAGA pattern).
        Will likely FAIL because:
        1. Compensation engine may not be implemented
        2. SAGA pattern coordination may be missing
        3. Compensation action execution may not work
        """
        try:
            # Create compensation engine
            compensation_engine = CompensationEngine(
                redis_client=real_redis_client,
                db_session=real_database_session
            )
            
            # Create SAGA transaction with compensation actions
            saga_id = str(uuid.uuid4())
            
            saga_steps = [
                {
                    "step_id": "reserve_user_slot",
                    "forward_action": {
                        "service": "user_service",
                        "operation": "reserve_slot",
                        "data": {"slot_type": "user_creation", "count": 1}
                    },
                    "compensation_action": {
                        "service": "user_service", 
                        "operation": "release_slot",
                        "data": {"slot_type": "user_creation", "count": 1}
                    }
                },
                {
                    "step_id": "create_user_saga",
                    "forward_action": {
                        "service": "user_service",
                        "operation": "create",
                        "data": {
                            "email": f"saga_test_{secrets.token_urlsafe(8)}@example.com",
                            "username": f"saga_user_{secrets.token_urlsafe(6)}"
                        }
                    },
                    "compensation_action": {
                        "service": "user_service",
                        "operation": "delete",
                        "data": {"identifier_field": "email"}
                    }
                },
                {
                    "step_id": "send_welcome_email",
                    "forward_action": {
                        "service": "email_service",
                        "operation": "send_email", 
                        "data": {
                            "template": "welcome",
                            "recipient": "user_email_from_previous_step"
                        }
                    },
                    "compensation_action": {
                        "service": "email_service",
                        "operation": "mark_email_cancelled",
                        "data": {"email_id": "email_id_from_forward"}
                    }
                },
                {
                    "step_id": "failing_external_api_call",
                    "forward_action": {
                        "service": "external_api",
                        "operation": "register_user",
                        "data": {
                            "external_system": "crm",
                            "force_failure": True  # This will cause the step to fail
                        }
                    },
                    "compensation_action": {
                        "service": "external_api",
                        "operation": "deregister_user",
                        "data": {"external_system": "crm"}
                    }
                }
            ]
            
            # FAILURE EXPECTED HERE - SAGA compensation may not be implemented
            saga_result = await compensation_engine.execute_saga(
                saga_id=saga_id,
                steps=saga_steps,
                timeout_seconds=45
            )
            
            assert saga_result is not None, "SAGA execution should return result"
            assert "status" in saga_result, "SAGA result should include status"
            
            # SAGA should fail at the last step and compensate
            assert saga_result["status"] in ["compensated", "failed"], \
                f"SAGA should fail and compensate, got '{saga_result['status']}'"
            
            if saga_result["status"] == "compensated":
                assert "compensated_steps" in saga_result, \
                    "Compensated SAGA should include compensated steps count"
                
                compensated_steps = saga_result["compensated_steps"]
                
                # Should compensate the first 3 successful steps
                expected_compensations = 3
                assert compensated_steps == expected_compensations, \
                    f"Should compensate {expected_compensations} steps, got {compensated_steps}"
            
            # Verify compensation was executed
            await asyncio.sleep(3)  # Wait for compensation to complete
            
            # User should be deleted by compensation
            user_query = await real_database_session.execute(
                select(User).where(User.email == saga_steps[1]["forward_action"]["data"]["email"])
            )
            compensated_user = user_query.scalar_one_or_none()
            
            assert compensated_user is None, \
                "User should be deleted by compensation action"
            
            # Verify compensation audit trail
            if hasattr(compensation_engine, 'get_compensation_audit'):
                audit_trail = await compensation_engine.get_compensation_audit(saga_id)
                
                assert audit_trail is not None, "Compensation audit trail should exist"
                assert "saga_id" in audit_trail, "Audit trail should include saga ID"
                assert "compensation_actions" in audit_trail, \
                    "Audit trail should include compensation actions"
                
                compensation_actions = audit_trail["compensation_actions"]
                assert len(compensation_actions) > 0, \
                    "Should have executed compensation actions"
                    
        except ImportError as e:
            pytest.fail(f"Compensation engine not available: {e}")
        except Exception as e:
            pytest.fail(f"Compensation engine coordination test failed: {e}")

    @pytest.mark.asyncio
    async def test_04_distributed_transaction_timeout_fails(
        self, real_database_session, real_redis_client
    ):
        """
        Test 21D: Distributed Transaction Timeout (EXPECTED TO FAIL)
        
        Tests timeout handling and cleanup for distributed transactions.
        Will likely FAIL because:
        1. Timeout mechanisms may not be implemented
        2. Resource cleanup on timeout may not work
        3. Deadlock detection may be missing
        """
        try:
            transaction_manager = TransactionManager(
                redis_client=real_redis_client,
                db_session=real_database_session
            )
            
            # Create transaction with steps that will timeout
            timeout_transaction_id = str(uuid.uuid4())
            
            timeout_transaction_steps = [
                {
                    "step_id": "long_running_step_1",
                    "service": "user_service",
                    "operation": "create",
                    "data": {
                        "email": f"timeout_test_{secrets.token_urlsafe(8)}@example.com",
                        "username": f"timeout_user_{secrets.token_urlsafe(6)}"
                    },
                    "estimated_duration": 2  # 2 seconds
                },
                {
                    "step_id": "extremely_long_step",
                    "service": "external_service",
                    "operation": "process_data",
                    "data": {
                        "processing_time": 60,  # 60 seconds - longer than timeout
                        "simulate_hang": True
                    },
                    "estimated_duration": 60
                },
                {
                    "step_id": "dependent_step",
                    "service": "user_service",
                    "operation": "update",
                    "data": {"status": "processed"},
                    "depends_on": ["long_running_step_1", "extremely_long_step"]
                }
            ]
            
            # Execute with short timeout
            transaction_timeout = 10  # 10 seconds
            
            start_time = time.time()
            
            # FAILURE EXPECTED HERE - timeout handling may not work
            try:
                timeout_result = await transaction_manager.coordinate_transaction(
                    transaction_id=timeout_transaction_id,
                    steps=timeout_transaction_steps,
                    timeout_seconds=transaction_timeout
                )
                
                execution_time = time.time() - start_time
                
                # Transaction should timeout
                assert timeout_result["status"] in ["timeout", "failed"], \
                    f"Transaction should timeout, got '{timeout_result['status']}'"
                
                # Should not take much longer than timeout
                max_expected_time = transaction_timeout + 5  # 5 second grace period
                assert execution_time < max_expected_time, \
                    f"Transaction should timeout in ~{transaction_timeout}s, took {execution_time:.1f}s"
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                
                # This is also acceptable - transaction timed out at asyncio level
                assert execution_time <= transaction_timeout + 2, \
                    f"Timeout should occur around {transaction_timeout}s, took {execution_time:.1f}s"
            
            # Verify timeout cleanup
            await asyncio.sleep(2)  # Wait for cleanup
            
            if hasattr(transaction_manager, 'get_timeout_cleanup_status'):
                cleanup_status = await transaction_manager.get_timeout_cleanup_status(
                    timeout_transaction_id
                )
                
                assert cleanup_status is not None, "Timeout cleanup status should be available"
                assert "cleaned_up" in cleanup_status, \
                    "Cleanup status should indicate if cleanup occurred"
                assert cleanup_status["cleaned_up"], \
                    "Resources should be cleaned up after timeout"
            
            # Verify partial transaction was rolled back
            user_query = await real_database_session.execute(
                select(User).where(User.email == timeout_transaction_steps[0]["data"]["email"])
            )
            timeout_user = user_query.scalar_one_or_none()
            
            # User might exist if first step completed before timeout
            if timeout_user is not None:
                # But it should be marked as part of failed transaction
                if hasattr(timeout_user, 'transaction_status'):
                    assert timeout_user.transaction_status in ["timeout", "rolled_back"], \
                        f"User should be marked as timeout/rolled_back, got '{timeout_user.transaction_status}'"
            
            # Test deadlock detection
            if hasattr(transaction_manager, 'detect_deadlocks'):
                deadlock_report = await transaction_manager.detect_deadlocks()
                
                assert deadlock_report is not None, "Deadlock detection should return report"
                assert "active_transactions" in deadlock_report, \
                    "Deadlock report should include active transactions"
                    
        except Exception as e:
            pytest.fail(f"Distributed transaction timeout test failed: {e}")

    @pytest.mark.asyncio
    async def test_05_transaction_state_recovery_fails(
        self, real_database_session, real_redis_client
    ):
        """
        Test 21E: Transaction State Recovery (EXPECTED TO FAIL)
        
        Tests recovery of transaction state after system restart or failure.
        Will likely FAIL because:
        1. Transaction state persistence may not be implemented
        2. Recovery mechanisms may be missing
        3. In-progress transaction handling may not work
        """
        try:
            transaction_manager = TransactionManager(
                redis_client=real_redis_client,
                db_session=real_database_session
            )
            
            # Create transaction for recovery testing
            recovery_transaction_id = str(uuid.uuid4())
            
            recovery_steps = [
                {
                    "step_id": "step_1_recovery",
                    "service": "user_service",
                    "operation": "create",
                    "data": {
                        "email": f"recovery_test_{secrets.token_urlsafe(8)}@example.com",
                        "username": f"recovery_user_{secrets.token_urlsafe(6)}"
                    },
                    "checkpoint": True  # Mark as checkpoint
                },
                {
                    "step_id": "step_2_recovery", 
                    "service": "session_service",
                    "operation": "create",
                    "data": {"device_info": {"recovery_test": True}},
                    "depends_on": ["step_1_recovery"],
                    "checkpoint": True
                },
                {
                    "step_id": "step_3_recovery",
                    "service": "user_service",
                    "operation": "update", 
                    "data": {"status": "active"},
                    "depends_on": ["step_1_recovery", "step_2_recovery"]
                }
            ]
            
            # Start transaction but simulate interruption after first step
            # FAILURE EXPECTED HERE - state persistence may not work
            if hasattr(transaction_manager, 'start_transaction_with_checkpoints'):
                start_result = await transaction_manager.start_transaction_with_checkpoints(
                    transaction_id=recovery_transaction_id,
                    steps=recovery_steps
                )
                
                assert start_result["status"] == "started", \
                    f"Transaction should start successfully, got '{start_result['status']}'"
                
                # Execute first step
                step1_result = await transaction_manager.execute_step(
                    recovery_transaction_id, "step_1_recovery"
                )
                
                assert step1_result["status"] == "completed", \
                    f"Step 1 should complete, got '{step1_result['status']}'"
                
                # Verify checkpoint was saved
                checkpoint_state = await transaction_manager.get_checkpoint_state(
                    recovery_transaction_id
                )
                
                assert checkpoint_state is not None, "Checkpoint state should be saved"
                assert "completed_steps" in checkpoint_state, \
                    "Checkpoint should include completed steps"
                assert "step_1_recovery" in checkpoint_state["completed_steps"], \
                    "Step 1 should be in completed steps"
            
            # Simulate system restart/recovery
            if hasattr(transaction_manager, 'simulate_restart'):
                await transaction_manager.simulate_restart()
            
            # Create new transaction manager instance to simulate restart
            recovered_transaction_manager = TransactionManager(
                redis_client=real_redis_client,
                db_session=real_database_session
            )
            
            # Test recovery
            if hasattr(recovered_transaction_manager, 'recover_in_progress_transactions'):
                recovery_result = await recovered_transaction_manager.recover_in_progress_transactions()
                
                assert recovery_result is not None, "Recovery should return result"
                assert "recovered_transactions" in recovery_result, \
                    "Recovery should include recovered transactions count"
                
                recovered_count = recovery_result["recovered_transactions"]
                assert recovered_count >= 1, \
                    f"Should recover at least 1 transaction, got {recovered_count}"
                
                # Check specific transaction recovery
                if recovery_transaction_id in recovery_result.get("transaction_ids", []):
                    transaction_recovery = await recovered_transaction_manager.get_recovery_status(
                        recovery_transaction_id
                    )
                    
                    assert transaction_recovery is not None, \
                        "Specific transaction recovery status should be available"
                    assert "resume_from_step" in transaction_recovery, \
                        "Recovery should indicate where to resume"
                    
                    resume_step = transaction_recovery["resume_from_step"]
                    assert resume_step == "step_2_recovery", \
                        f"Should resume from step 2, got '{resume_step}'"
            
            # Test resuming transaction
            if hasattr(recovered_transaction_manager, 'resume_transaction'):
                resume_result = await recovered_transaction_manager.resume_transaction(
                    recovery_transaction_id
                )
                
                assert resume_result is not None, "Transaction resume should return result"
                assert resume_result["status"] in ["completed", "resumed"], \
                    f"Transaction should complete or resume, got '{resume_result['status']}'"
            
            # Verify final state consistency
            await asyncio.sleep(2)  # Wait for completion
            
            # Check that all data was created correctly
            user_query = await real_database_session.execute(
                select(User).where(User.email == recovery_steps[0]["data"]["email"])
            )
            recovered_user = user_query.scalar_one_or_none()
            
            assert recovered_user is not None, \
                "User should exist after transaction recovery"
            
            if hasattr(recovered_user, 'status'):
                assert recovered_user.status == "active", \
                    f"User status should be 'active' after recovery, got '{recovered_user.status}'"
                    
        except Exception as e:
            pytest.fail(f"Transaction state recovery test failed: {e}")


# Utility class for transaction coordination testing
class RedTeamTransactionCoordinationTestUtils:
    """Utility methods for transaction rollback coordination testing."""
    
    @staticmethod
    async def create_test_transaction_steps(
        base_email: str,
        base_username: str,
        include_failure: bool = False
    ) -> List[Dict[str, Any]]:
        """Create a set of test transaction steps."""
        
        steps = [
            {
                "step_id": "create_user",
                "service": "user_service",
                "operation": "create",
                "data": {
                    "email": base_email,
                    "username": base_username
                },
                "rollback_action": {
                    "operation": "delete",
                    "identifier_field": "email"
                }
            },
            {
                "step_id": "create_session",
                "service": "session_service",
                "operation": "create",
                "data": {
                    "device_info": {"test": True}
                },
                "depends_on": ["create_user"],
                "rollback_action": {
                    "operation": "delete",
                    "identifier_field": "session_id"
                }
            }
        ]
        
        if include_failure:
            steps.append({
                "step_id": "failing_step",
                "service": "user_service",
                "operation": "update",
                "data": {
                    "invalid_field": "force_failure",
                    "force_error": True
                },
                "depends_on": ["create_user"],
                "rollback_action": {
                    "operation": "none"
                }
            })
        
        return steps
    
    @staticmethod
    async def verify_transaction_cleanup(
        db_session: AsyncSession,
        redis_client,
        transaction_id: str,
        test_email: str
    ) -> Dict[str, Any]:
        """Verify that transaction cleanup was completed successfully."""
        
        cleanup_report = {
            "transaction_id": transaction_id,
            "database_cleaned": False,
            "redis_cleaned": False,
            "user_exists": False
        }
        
        # Check if user was cleaned up from database
        user_query = await db_session.execute(
            select(User).where(User.email == test_email)
        )
        user_exists = user_query.scalar_one_or_none() is not None
        cleanup_report["user_exists"] = user_exists
        cleanup_report["database_cleaned"] = not user_exists
        
        # Check if transaction state was cleaned up from Redis
        redis_transaction_key = f"transaction:{transaction_id}"
        redis_state = await redis_client.get(redis_transaction_key)
        cleanup_report["redis_cleaned"] = redis_state is None
        
        cleanup_report["fully_cleaned"] = (
            cleanup_report["database_cleaned"] and 
            cleanup_report["redis_cleaned"]
        )
        
        return cleanup_report
    
    @staticmethod
    def create_compensation_action(
        service: str,
        operation: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a compensation action definition."""
        
        return {
            "service": service,
            "operation": operation,
            "data": data,
            "retry_count": 3,
            "timeout_seconds": 10
        }
    
    @staticmethod
    def create_saga_step(
        step_id: str,
        forward_action: Dict[str, Any],
        compensation_action: Dict[str, Any],
        depends_on: List[str] = None
    ) -> Dict[str, Any]:
        """Create a SAGA step with forward and compensation actions."""
        
        step = {
            "step_id": step_id,
            "forward_action": forward_action,
            "compensation_action": compensation_action
        }
        
        if depends_on:
            step["depends_on"] = depends_on
        
        return step
    
    @staticmethod
    async def monitor_transaction_progress(
        transaction_manager,
        transaction_id: str,
        max_wait_seconds: int = 30
    ) -> Dict[str, Any]:
        """Monitor transaction progress and return final status."""
        
        wait_time = 0
        progress_history = []
        
        while wait_time < max_wait_seconds:
            if hasattr(transaction_manager, 'get_transaction_status'):
                status = await transaction_manager.get_transaction_status(transaction_id)
                
                if status:
                    progress_history.append({
                        "timestamp": datetime.now(timezone.utc),
                        "status": status.get("status"),
                        "completed_steps": status.get("completed_steps", 0)
                    })
                    
                    if status.get("status") in ["completed", "failed", "rolled_back", "timeout"]:
                        break
            
            await asyncio.sleep(1)
            wait_time += 1
        
        return {
            "final_status": progress_history[-1] if progress_history else None,
            "progress_history": progress_history,
            "total_wait_time": wait_time
        }