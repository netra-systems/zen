"""
Test Database Migration Integrity Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Data integrity during system upgrades
- Value Impact: Prevents data corruption and business continuity disruption
- Strategic Impact: Enables safe system evolution and feature deployment

CRITICAL REQUIREMENTS:
- Tests real database migration scenarios
- Validates data integrity across schema changes
- Ensures backward compatibility and rollback safety
- No mocks - uses real database migration tools
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid
import json

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.db.migration_utils import DatabaseMigrator
from netra_backend.app.db.database_manager import get_database_manager
from netra_backend.app.db.models_postgres import User, Thread, Message


class TestDatabaseMigrationIntegrityComprehensive(SSotBaseTestCase):
    """
    Comprehensive database migration integrity tests.
    
    Tests critical migration scenarios that protect business data:
    - Schema evolution without data loss
    - Migration rollback safety
    - Concurrent access during migrations
    - Data validation and consistency
    - Performance impact assessment
    """
    
    def setup_method(self):
        """Set up test environment for each test method."""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"migration_test_{uuid.uuid4().hex[:8]}"
        
    async def setup_migration_environment(self) -> DatabaseMigrator:
        """Set up migration testing environment."""
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        migrator = DatabaseMigrator(db_manager)
        return migrator
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_schema_evolution_without_data_loss(self):
        """
        Test schema evolution maintains data integrity.
        
        BUSINESS CRITICAL: Schema changes must not corrupt user data.
        Data loss during migrations destroys business value.
        """
        migrator = await self.setup_migration_environment()
        
        try:
            # Create test data in current schema
            test_users = []
            test_threads = []
            test_messages = []
            
            # Create comprehensive test dataset
            for i in range(5):
                user_email = f"{self.test_prefix}_user_{i}@example.com"
                
                # Create user with current schema
                user_data = {
                    "email": user_email,
                    "name": f"Test User {i}",
                    "subscription_tier": "mid",
                    "credits_remaining": 1000 + i * 100,
                    "created_at": datetime.now(timezone.utc)
                }
                
                user = await migrator.create_test_user(user_data)
                test_users.append(user)
                
                # Create threads for user
                for j in range(2):
                    thread_data = {
                        "user_id": user.id,
                        "title": f"Thread {j} for User {i}",
                        "created_at": datetime.now(timezone.utc) - timedelta(hours=j),
                        "metadata": {
                            "test_data": True,
                            "user_sequence": i,
                            "thread_sequence": j
                        }
                    }
                    
                    thread = await migrator.create_test_thread(thread_data)
                    test_threads.append(thread)
                    
                    # Create messages in thread
                    for k in range(3):
                        message_data = {
                            "thread_id": thread.id,
                            "user_id": user.id,
                            "content": f"Message {k} in thread {j} from user {i}",
                            "message_type": "user" if k % 2 == 0 else "agent",
                            "created_at": datetime.now(timezone.utc) - timedelta(minutes=k),
                            "metadata": {
                                "test_data": True,
                                "message_sequence": k
                            }
                        }
                        
                        message = await migrator.create_test_message(message_data)
                        test_messages.append(message)
            
            # Capture pre-migration data checksums
            pre_migration_checksums = await migrator.calculate_data_checksums(
                test_prefix=self.test_prefix
            )
            
            # Execute schema migration - add new column to users table
            migration_script = """
            ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
            ALTER TABLE threads ADD COLUMN priority_level INTEGER DEFAULT 1;
            ALTER TABLE messages ADD COLUMN edited_at TIMESTAMP;
            """
            
            migration_result = await migrator.execute_migration(
                script=migration_script,
                migration_name=f"add_columns_{self.test_prefix}",
                description="Add timestamp and priority columns"
            )
            
            assert migration_result.success, f"Migration failed: {migration_result.error}"
            assert migration_result.affected_tables == ["users", "threads", "messages"], \
                f"Unexpected affected tables: {migration_result.affected_tables}"
            
            # Verify data integrity after migration
            post_migration_checksums = await migrator.calculate_data_checksums(
                test_prefix=self.test_prefix
            )
            
            # Core data should be unchanged
            core_tables = ["users_core", "threads_core", "messages_core"]
            for table in core_tables:
                if table in pre_migration_checksums and table in post_migration_checksums:
                    assert pre_migration_checksums[table] == post_migration_checksums[table], \
                        f"Data corruption detected in {table}: checksum mismatch"
            
            # Verify all test records still exist and are accessible
            for user in test_users:
                migrated_user = await migrator.get_user_by_id(user.id)
                assert migrated_user is not None, f"User {user.id} lost during migration"
                assert migrated_user.email == user.email, "User email corrupted"
                assert migrated_user.subscription_tier == user.subscription_tier, "User tier corrupted"
                
                # New column should exist with default value
                assert hasattr(migrated_user, 'last_login_at'), "New column not added to user"
                assert migrated_user.last_login_at is None, "New column should be NULL by default"
            
            for thread in test_threads:
                migrated_thread = await migrator.get_thread_by_id(thread.id)
                assert migrated_thread is not None, f"Thread {thread.id} lost during migration"
                assert migrated_thread.title == thread.title, "Thread title corrupted"
                
                # New column should exist with default value
                assert hasattr(migrated_thread, 'priority_level'), "New column not added to thread"
                assert migrated_thread.priority_level == 1, "Thread priority not set to default"
            
            for message in test_messages:
                migrated_message = await migrator.get_message_by_id(message.id)
                assert migrated_message is not None, f"Message {message.id} lost during migration"
                assert migrated_message.content == message.content, "Message content corrupted"
                
                # New column should exist with default value
                assert hasattr(migrated_message, 'edited_at'), "New column not added to message"
                assert migrated_message.edited_at is None, "Message edited_at should be NULL"
            
            # Test writing to new schema works
            new_user_data = {
                "email": f"{self.test_prefix}_post_migration@example.com",
                "name": "Post Migration User",
                "subscription_tier": "enterprise",
                "credits_remaining": 5000,
                "last_login_at": datetime.now(timezone.utc),  # Use new column
                "created_at": datetime.now(timezone.utc)
            }
            
            post_migration_user = await migrator.create_test_user(new_user_data)
            assert post_migration_user.last_login_at is not None, "New column not writable"
            
            # Test complex queries still work
            complex_query_result = await migrator.execute_complex_query(
                f"""
                SELECT u.email, t.title, COUNT(m.id) as message_count
                FROM users u
                JOIN threads t ON u.id = t.user_id  
                JOIN messages m ON t.id = m.thread_id
                WHERE u.email LIKE '{self.test_prefix}%'
                GROUP BY u.email, t.title
                ORDER BY message_count DESC
                """
            )
            
            assert len(complex_query_result) > 0, "Complex queries broken after migration"
            
        finally:
            await migrator.cleanup_test_data(test_prefix=self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_migration_rollback_safety_and_data_recovery(self):
        """
        Test migration rollback preserves data integrity.
        
        BUSINESS CRITICAL: Failed migrations must be safely reversible.
        Rollback failures can cause permanent data loss.
        """
        migrator = await self.setup_migration_environment()
        
        try:
            # Create baseline data for rollback testing
            baseline_user = await migrator.create_test_user({
                "email": f"{self.test_prefix}_rollback@example.com",
                "name": "Rollback Test User",
                "subscription_tier": "early", 
                "credits_remaining": 500,
                "created_at": datetime.now(timezone.utc)
            })
            
            baseline_thread = await migrator.create_test_thread({
                "user_id": baseline_user.id,
                "title": "Rollback Test Thread",
                "created_at": datetime.now(timezone.utc)
            })
            
            # Capture pre-migration state
            pre_migration_state = await migrator.capture_database_state(
                test_prefix=self.test_prefix
            )
            
            # Execute a migration that will be rolled back
            forward_migration = """
            ALTER TABLE users ADD COLUMN test_rollback_column VARCHAR(255);
            UPDATE users SET test_rollback_column = 'test_value' WHERE email LIKE '%%rollback%%';
            ALTER TABLE threads ADD COLUMN test_priority INTEGER DEFAULT 5;
            """
            
            rollback_migration = """
            ALTER TABLE users DROP COLUMN test_rollback_column;
            ALTER TABLE threads DROP COLUMN test_priority;
            """
            
            # Execute forward migration
            forward_result = await migrator.execute_migration(
                script=forward_migration,
                migration_name=f"rollback_test_forward_{self.test_prefix}",
                description="Migration to be rolled back",
                rollback_script=rollback_migration
            )
            
            assert forward_result.success, f"Forward migration failed: {forward_result.error}"
            
            # Verify forward migration applied
            user_with_new_column = await migrator.get_user_by_id(baseline_user.id)
            assert hasattr(user_with_new_column, 'test_rollback_column'), \
                "Forward migration column not applied"
            assert user_with_new_column.test_rollback_column == 'test_value', \
                "Forward migration data not applied"
            
            # Execute rollback
            rollback_result = await migrator.execute_rollback(
                migration_name=f"rollback_test_forward_{self.test_prefix}"
            )
            
            assert rollback_result.success, f"Rollback failed: {rollback_result.error}"
            
            # Verify rollback restored original state
            post_rollback_state = await migrator.capture_database_state(
                test_prefix=self.test_prefix
            )
            
            # Data integrity should be preserved
            rolled_back_user = await migrator.get_user_by_id(baseline_user.id)
            assert rolled_back_user is not None, "User lost during rollback"
            assert rolled_back_user.email == baseline_user.email, "User data corrupted in rollback"
            assert rolled_back_user.subscription_tier == baseline_user.subscription_tier, \
                "User subscription corrupted in rollback"
            
            # New columns should be removed
            assert not hasattr(rolled_back_user, 'test_rollback_column'), \
                "Rollback did not remove added column"
            
            rolled_back_thread = await migrator.get_thread_by_id(baseline_thread.id)
            assert not hasattr(rolled_back_thread, 'test_priority'), \
                "Rollback did not remove thread column"
            
            # Test multiple rollback scenario
            multi_migration_1 = """
            ALTER TABLE users ADD COLUMN rollback_test_1 INTEGER DEFAULT 1;
            """
            
            multi_migration_2 = """
            ALTER TABLE users ADD COLUMN rollback_test_2 VARCHAR(50) DEFAULT 'test';
            """
            
            # Apply multiple migrations
            await migrator.execute_migration(
                script=multi_migration_1,
                migration_name=f"multi_rollback_1_{self.test_prefix}",
                rollback_script="ALTER TABLE users DROP COLUMN rollback_test_1;"
            )
            
            await migrator.execute_migration(
                script=multi_migration_2,
                migration_name=f"multi_rollback_2_{self.test_prefix}",
                rollback_script="ALTER TABLE users DROP COLUMN rollback_test_2;"
            )
            
            # Rollback in reverse order (LIFO)
            rollback_2_result = await migrator.execute_rollback(
                migration_name=f"multi_rollback_2_{self.test_prefix}"
            )
            assert rollback_2_result.success, "Second rollback failed"
            
            rollback_1_result = await migrator.execute_rollback(
                migration_name=f"multi_rollback_1_{self.test_prefix}"
            )
            assert rollback_1_result.success, "First rollback failed"
            
            # Verify final state matches original
            final_user = await migrator.get_user_by_id(baseline_user.id)
            assert not hasattr(final_user, 'rollback_test_1'), "Multi-rollback failed for column 1"
            assert not hasattr(final_user, 'rollback_test_2'), "Multi-rollback failed for column 2"
            
        finally:
            await migrator.cleanup_test_data(test_prefix=self.test_prefix)


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])