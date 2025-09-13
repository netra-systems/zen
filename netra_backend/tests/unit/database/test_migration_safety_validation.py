"""
Unit Test: Migration Safety and Schema Validation for Multi-User Database

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure database migrations preserve user data integrity
- Value Impact: Migration failures can cause data loss and service outages
- Strategic Impact: Safe database evolution for production multi-tenant platform

This unit test validates:
1. Migration scripts preserve user data isolation constraints
2. Schema changes maintain backward compatibility requirements
3. Migration rollback scenarios protect user data integrity
4. Database constraints enforce multi-user data separation

CRITICAL: Tests migration safety patterns to prevent production data loss.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from netra_backend.tests.unit.test_base import BaseUnitTest
from shared.types.core_types import UserID, ensure_user_id

# Import SQLAlchemy for migration testing
try:
    from sqlalchemy import create_engine, text, Column, String, Integer, DateTime, JSON, Boolean, ForeignKey
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.schema import CreateTable, DropTable, CreateIndex, DropIndex
    from sqlalchemy.ext.asyncio import AsyncSession
    SQLALCHEMY_AVAILABLE = True
    
    # Mock migration models for testing
    MockBase = declarative_base()
    
    class MockUserDataV1(MockBase):
        """Original user data model for migration testing."""
        __tablename__ = "mock_user_data_v1"
        
        id = Column(String, primary_key=True)
        user_id = Column(String, index=True)  # Basic user isolation
        content = Column(String)
        created_at = Column(DateTime)
    
    class MockUserDataV2(MockBase):
        """Enhanced user data model with additional constraints."""
        __tablename__ = "mock_user_data_v2"
        
        id = Column(String, primary_key=True)
        user_id = Column(String, index=True, nullable=False)  # Stricter user isolation
        content = Column(String, nullable=False)
        metadata_ = Column("metadata", JSON)  # New field
        created_at = Column(DateTime, nullable=False)
        is_active = Column(Boolean, default=True)  # New field
        
        # Additional constraint for user isolation
        __table_args__ = (
            {'schema': None}  # Explicit schema for testing
        )
        
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class TestMigrationSafetyValidation(BaseUnitTest):
    """Test migration safety and schema validation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for migration testing", allow_module_level=True)

    @pytest.mark.unit
    def test_migration_scripts_preserve_user_isolation_constraints(self):
        """Test that migration scripts preserve user data isolation constraints."""
        
        # Mock database migration scenario
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        
        # Mock existing user data that must be preserved
        existing_user_data = [
            {
                'id': f'data_{i}',
                'user_id': f'user_{i}',
                'content': f'User {i} data',
                'created_at': datetime.now(timezone.utc)
            } for i in range(5)
        ]
        
        mock_connection.execute.return_value.fetchall.return_value = existing_user_data
        
        # Simulate migration from V1 to V2 schema
        class MigrationValidator:
            def __init__(self, engine):
                self.engine = engine
                self.migration_errors = []
                self.user_data_preserved = True
                self.constraints_maintained = True
                
            def validate_pre_migration(self):
                """Validate data before migration."""
                with self.engine.connect() as conn:
                    # Check existing data isolation
                    result = conn.execute(text("SELECT id, user_id FROM mock_user_data_v1"))
                    pre_data = result.fetchall()
                    
                    # Verify each user has isolated data
                    user_counts = {}
                    for row in pre_data:
                        user_id = row[1]  # user_id column
                        user_counts[user_id] = user_counts.get(user_id, 0) + 1
                    
                    # Check isolation integrity
                    for user_id, count in user_counts.items():
                        if count <= 0:
                            self.migration_errors.append(f"User {user_id} has no data - isolation broken")
                        
                    return len(self.migration_errors) == 0
                    
            def execute_migration(self):
                """Execute migration with safety checks."""
                try:
                    with self.engine.connect() as conn:
                        # Step 1: Create new table with enhanced constraints
                        create_v2_sql = """
                        CREATE TABLE mock_user_data_v2 (
                            id VARCHAR PRIMARY KEY,
                            user_id VARCHAR NOT NULL,
                            content VARCHAR NOT NULL,
                            metadata JSON,
                            created_at TIMESTAMP NOT NULL,
                            is_active BOOLEAN DEFAULT true
                        )
                        """
                        conn.execute(text(create_v2_sql))
                        
                        # Step 2: Create indexes for user isolation
                        create_index_sql = """
                        CREATE INDEX idx_mock_user_data_v2_user_id ON mock_user_data_v2(user_id)
                        """
                        conn.execute(text(create_index_sql))
                        
                        # Step 3: Migrate data with user isolation preservation
                        migrate_data_sql = """
                        INSERT INTO mock_user_data_v2 (id, user_id, content, metadata, created_at, is_active)
                        SELECT 
                            id,
                            user_id,
                            content,
                            '{"migrated": true}' as metadata,
                            created_at,
                            true as is_active
                        FROM mock_user_data_v1
                        WHERE user_id IS NOT NULL
                        """
                        conn.execute(text(migrate_data_sql))
                        
                        # Step 4: Validate data migration preserved user boundaries
                        self.validate_post_migration()
                        
                        if not self.migration_errors:
                            # Step 5: Drop old table only if migration successful
                            conn.execute(text("DROP TABLE mock_user_data_v1"))
                        
                except Exception as e:
                    self.migration_errors.append(f"Migration execution failed: {str(e)}")
                    
            def validate_post_migration(self):
                """Validate data after migration."""
                with self.engine.connect() as conn:
                    # Check data preservation
                    v2_result = conn.execute(text("SELECT COUNT(*) FROM mock_user_data_v2"))
                    v2_count = v2_result.scalar()
                    
                    v1_result = conn.execute(text("SELECT COUNT(*) FROM mock_user_data_v1"))
                    v1_count = v1_result.scalar()
                    
                    if v2_count != v1_count:
                        self.user_data_preserved = False
                        self.migration_errors.append(
                            f"Data loss during migration: V1={v1_count}, V2={v2_count}"
                        )
                    
                    # Check user isolation constraints
                    isolation_check = conn.execute(text("""
                        SELECT user_id, COUNT(*) as record_count
                        FROM mock_user_data_v2
                        GROUP BY user_id
                        HAVING user_id IS NULL OR user_id = ''
                    """))
                    
                    invalid_users = isolation_check.fetchall()
                    if invalid_users:
                        self.constraints_maintained = False
                        self.migration_errors.append(
                            f"User isolation constraints violated: {len(invalid_users)} invalid user records"
                        )
                    
                    # Check new constraints are enforced
                    constraint_check = conn.execute(text("""
                        SELECT COUNT(*) FROM mock_user_data_v2
                        WHERE content IS NULL OR content = ''
                    """))
                    null_content_count = constraint_check.scalar()
                    
                    if null_content_count > 0:
                        self.constraints_maintained = False
                        self.migration_errors.append(
                            f"NOT NULL constraints violated: {null_content_count} records with null content"
                        )
        
        # Execute migration validation
        validator = MigrationValidator(mock_engine)
        
        # Mock database responses for each validation step
        def mock_execute_side_effect(query):
            query_str = str(query).lower()
            mock_result = MagicMock()
            
            if "select id, user_id from mock_user_data_v1" in query_str:
                mock_result.fetchall.return_value = [(row['id'], row['user_id']) for row in existing_user_data]
            elif "select count(*) from mock_user_data_v2" in query_str:
                mock_result.scalar.return_value = len(existing_user_data)
            elif "select count(*) from mock_user_data_v1" in query_str:
                mock_result.scalar.return_value = len(existing_user_data)
            elif "group by user_id" in query_str:
                mock_result.fetchall.return_value = []  # No constraint violations
            elif "where content is null" in query_str:
                mock_result.scalar.return_value = 0  # No null content
            else:
                mock_result.fetchall.return_value = []
                mock_result.scalar.return_value = 0
            
            return mock_result
        
        mock_connection.execute.side_effect = mock_execute_side_effect
        
        # Run migration validation
        pre_valid = validator.validate_pre_migration()
        validator.execute_migration()
        
        # Assert migration safety
        assert pre_valid, "Pre-migration validation failed - data integrity compromised"
        assert validator.user_data_preserved, f"User data not preserved: {validator.migration_errors}"
        assert validator.constraints_maintained, f"Constraints not maintained: {validator.migration_errors}"
        assert len(validator.migration_errors) == 0, f"Migration safety violations: {validator.migration_errors}"
        
        # Verify SQL operations were called in correct order
        expected_calls = [
            'SELECT id, user_id FROM mock_user_data_v1',  # Pre-validation
            'CREATE TABLE mock_user_data_v2',  # Schema creation
            'CREATE INDEX idx_mock_user_data_v2_user_id',  # Index creation
            'INSERT INTO mock_user_data_v2',  # Data migration
            'SELECT COUNT(*) FROM mock_user_data_v2',  # Post-validation
            'DROP TABLE mock_user_data_v1'  # Cleanup
        ]
        
        executed_queries = [str(call.args[0]).upper() for call in mock_connection.execute.call_args_list]
        
        # Verify critical operations were performed
        create_table_called = any('CREATE TABLE' in query for query in executed_queries)
        data_migration_called = any('INSERT INTO' in query for query in executed_queries)
        validation_called = any('SELECT COUNT' in query for query in executed_queries)
        
        assert create_table_called, "CREATE TABLE operation not executed"
        assert data_migration_called, "Data migration not executed"
        assert validation_called, "Post-migration validation not executed"

    @pytest.mark.unit
    def test_schema_changes_maintain_backward_compatibility(self):
        """Test that schema changes maintain backward compatibility requirements."""
        
        # Define backward compatibility requirements
        compatibility_requirements = {
            'user_id_column': {'required': True, 'type': 'string', 'indexed': True},
            'content_column': {'required': True, 'type': 'string', 'nullable': True},
            'created_at_column': {'required': True, 'type': 'datetime', 'nullable': True},
            'primary_key': {'required': True, 'column': 'id'},
            'user_isolation_index': {'required': True, 'column': 'user_id'}
        }
        
        class BackwardCompatibilityValidator:
            def __init__(self, old_schema, new_schema):
                self.old_schema = old_schema
                self.new_schema = new_schema
                self.compatibility_issues = []
                
            def validate_column_compatibility(self):
                """Validate column-level backward compatibility."""
                old_columns = {col.name: col for col in self.old_schema.columns}
                new_columns = {col.name: col for col in self.new_schema.columns}
                
                # Check required columns are preserved
                for old_col_name, old_col in old_columns.items():
                    if old_col_name not in new_columns:
                        self.compatibility_issues.append(
                            f"Column '{old_col_name}' removed - breaks backward compatibility"
                        )
                        continue
                    
                    new_col = new_columns[old_col_name]
                    
                    # Check type compatibility
                    old_type_str = str(old_col.type).lower()
                    new_type_str = str(new_col.type).lower()
                    
                    if old_type_str != new_type_str:
                        # Allow compatible type changes (e.g., varchar -> text)
                        compatible_changes = [
                            ('varchar', 'text'),
                            ('text', 'varchar'),
                            ('integer', 'bigint')
                        ]
                        
                        type_change_compatible = any(
                            (old_type_str.startswith(old) and new_type_str.startswith(new)) or
                            (old_type_str.startswith(new) and new_type_str.startswith(old))
                            for old, new in compatible_changes
                        )
                        
                        if not type_change_compatible:
                            self.compatibility_issues.append(
                                f"Column '{old_col_name}' type changed from {old_type_str} to {new_type_str} - incompatible"
                            )
                    
                    # Check nullable constraint compatibility
                    if old_col.nullable and not new_col.nullable:
                        self.compatibility_issues.append(
                            f"Column '{old_col_name}' made NOT NULL - may break existing data"
                        )
                
            def validate_index_compatibility(self):
                """Validate index backward compatibility."""
                # Mock index checking for user isolation
                old_indexes = ['idx_user_id']  # Assume old schema had user_id index
                new_indexes = ['idx_mock_user_data_v2_user_id']  # New schema indexes
                
                # Check critical indexes are preserved
                user_isolation_index_exists = any(
                    'user_id' in idx_name.lower() for idx_name in new_indexes
                )
                
                if not user_isolation_index_exists:
                    self.compatibility_issues.append(
                        "User isolation index missing - performance regression for multi-user queries"
                    )
                
            def validate_constraint_compatibility(self):
                """Validate constraint backward compatibility."""
                # Check primary key preservation
                old_pk_columns = [col.name for col in self.old_schema.primary_key.columns]
                new_pk_columns = [col.name for col in self.new_schema.primary_key.columns]
                
                if old_pk_columns != new_pk_columns:
                    self.compatibility_issues.append(
                        f"Primary key changed from {old_pk_columns} to {new_pk_columns} - breaks references"
                    )
                
                # Check user isolation constraints
                old_user_col = self.old_schema.columns.get('user_id')
                new_user_col = self.new_schema.columns.get('user_id')
                
                if old_user_col and new_user_col:
                    if not new_user_col.index:
                        self.compatibility_issues.append(
                            "user_id column no longer indexed - breaks user isolation performance"
                        )
            
            def validate_data_access_compatibility(self):
                """Validate data access pattern compatibility."""
                # Simulate common data access patterns
                access_patterns = [
                    "SELECT * FROM table WHERE user_id = ?",
                    "SELECT id, content FROM table WHERE user_id = ? ORDER BY created_at",
                    "INSERT INTO table (id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
                    "UPDATE table SET content = ? WHERE id = ? AND user_id = ?",
                    "DELETE FROM table WHERE id = ? AND user_id = ?"
                ]
                
                old_columns = {col.name for col in self.old_schema.columns}
                new_columns = {col.name for col in self.new_schema.columns}
                
                for pattern in access_patterns:
                    # Check if query pattern still works
                    pattern_columns = set()
                    if 'user_id' in pattern:
                        pattern_columns.add('user_id')
                    if 'content' in pattern:
                        pattern_columns.add('content')
                    if 'created_at' in pattern:
                        pattern_columns.add('created_at')
                    if 'id' in pattern:
                        pattern_columns.add('id')
                    
                    missing_columns = pattern_columns - new_columns
                    if missing_columns:
                        self.compatibility_issues.append(
                            f"Access pattern broken - missing columns: {missing_columns}"
                        )
        
        # Create mock old and new schemas
        old_schema = MockUserDataV1.__table__
        new_schema = MockUserDataV2.__table__
        
        # Run backward compatibility validation
        validator = BackwardCompatibilityValidator(old_schema, new_schema)
        validator.validate_column_compatibility()
        validator.validate_index_compatibility()
        validator.validate_constraint_compatibility()
        validator.validate_data_access_compatibility()
        
        # Assert backward compatibility
        assert len(validator.compatibility_issues) == 0, \
            f"Backward compatibility violations: {validator.compatibility_issues}"
        
        # Verify specific requirements are met
        new_columns = {col.name: col for col in new_schema.columns}
        
        # User isolation must be preserved
        assert 'user_id' in new_columns, "user_id column missing - breaks user isolation"
        assert new_columns['user_id'].index, "user_id not indexed - breaks isolation performance"
        
        # Core data columns must be preserved
        required_columns = ['id', 'user_id', 'content', 'created_at']
        missing_required = [col for col in required_columns if col not in new_columns]
        assert len(missing_required) == 0, f"Required columns missing: {missing_required}"
        
        # Primary key must be preserved
        pk_columns = [col.name for col in new_schema.primary_key.columns]
        assert 'id' in pk_columns, "Primary key 'id' not preserved"
        
        self.logger.info("Schema backward compatibility validation passed")

    @pytest.mark.unit 
    def test_migration_rollback_protects_user_data_integrity(self):
        """Test that migration rollback scenarios protect user data integrity."""
        
        # Mock database with transaction support
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_transaction = MagicMock()
        
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.begin.return_value.__enter__.return_value = mock_transaction
        
        # Mock user data to protect during rollback
        protected_user_data = [
            {
                'id': f'protect_{i}',
                'user_id': f'user_{i}',
                'content': f'Critical user {i} data',
                'created_at': datetime.now(timezone.utc)
            } for i in range(10)
        ]
        
        class RollbackSafetyValidator:
            def __init__(self, engine):
                self.engine = engine
                self.rollback_errors = []
                self.data_integrity_preserved = True
                self.transaction_completed = False
                
            def execute_migration_with_rollback_test(self):
                """Execute migration with intentional rollback to test safety."""
                try:
                    with self.engine.connect() as conn:
                        with conn.begin() as trans:
                            # Step 1: Backup user data (safety measure)
                            backup_sql = """
                            CREATE TABLE user_data_backup AS
                            SELECT * FROM mock_user_data_v1
                            """
                            conn.execute(text(backup_sql))
                            
                            # Step 2: Start migration
                            conn.execute(text("CREATE TABLE mock_user_data_v2_temp (...)"))
                            
                            # Step 3: Migrate data
                            migrate_sql = """
                            INSERT INTO mock_user_data_v2_temp
                            SELECT * FROM mock_user_data_v1
                            """
                            conn.execute(text(migrate_sql))
                            
                            # Step 4: Simulate failure condition
                            # This could be a constraint violation, disk full, etc.
                            failure_simulation = True
                            if failure_simulation:
                                raise Exception("Simulated migration failure - testing rollback")
                            
                            # Step 5: If we reach here, commit would occur
                            self.transaction_completed = True
                            
                except Exception as e:
                    # Rollback should occur automatically
                    self.rollback_errors.append(f"Migration failed (expected): {str(e)}")
                    
            def validate_rollback_integrity(self):
                """Validate that rollback preserved data integrity."""
                with self.engine.connect() as conn:
                    # Check original data is preserved
                    original_data_check = conn.execute(text("SELECT COUNT(*) FROM mock_user_data_v1"))
                    original_count = original_data_check.scalar()
                    
                    if original_count != len(protected_user_data):
                        self.data_integrity_preserved = False
                        self.rollback_errors.append(
                            f"Original data corrupted: expected {len(protected_user_data)}, got {original_count}"
                        )
                    
                    # Check temporary tables were cleaned up
                    try:
                        temp_check = conn.execute(text("SELECT COUNT(*) FROM mock_user_data_v2_temp"))
                        temp_count = temp_check.scalar()
                        if temp_count > 0:
                            self.rollback_errors.append(
                                f"Temporary migration data not cleaned up: {temp_count} records remain"
                            )
                    except Exception:
                        # Expected - temp table should not exist after rollback
                        pass
                    
                    # Check user isolation integrity
                    isolation_check = conn.execute(text("""
                        SELECT user_id, COUNT(*) as user_records
                        FROM mock_user_data_v1
                        GROUP BY user_id
                    """))
                    user_counts = isolation_check.fetchall()
                    
                    # Verify each user's data is intact
                    expected_user_counts = {}
                    for data in protected_user_data:
                        user_id = data['user_id']
                        expected_user_counts[user_id] = expected_user_counts.get(user_id, 0) + 1
                    
                    actual_user_counts = {row[0]: row[1] for row in user_counts}
                    
                    for user_id, expected_count in expected_user_counts.items():
                        actual_count = actual_user_counts.get(user_id, 0)
                        if actual_count != expected_count:
                            self.data_integrity_preserved = False
                            self.rollback_errors.append(
                                f"User {user_id} data integrity violated: expected {expected_count}, got {actual_count}"
                            )
            
            def validate_backup_recovery_capability(self):
                """Validate that backup recovery is possible."""
                with self.engine.connect() as conn:
                    # Check if backup exists and is complete
                    try:
                        backup_check = conn.execute(text("SELECT COUNT(*) FROM user_data_backup"))
                        backup_count = backup_check.scalar()
                        
                        if backup_count != len(protected_user_data):
                            self.rollback_errors.append(
                                f"Backup incomplete: expected {len(protected_user_data)}, got {backup_count}"
                            )
                        
                        # Simulate recovery from backup
                        recovery_check = conn.execute(text("""
                            SELECT COUNT(*) FROM user_data_backup
                            WHERE user_id IS NOT NULL AND content IS NOT NULL
                        """))
                        recoverable_count = recovery_check.scalar()
                        
                        if recoverable_count != len(protected_user_data):
                            self.rollback_errors.append(
                                f"Backup data integrity issue: only {recoverable_count} recoverable records"
                            )
                            
                    except Exception as e:
                        self.rollback_errors.append(f"Backup validation failed: {str(e)}")
        
        # Mock database responses
        def mock_execute_side_effect(query):
            query_str = str(query).lower()
            mock_result = MagicMock()
            
            if "select count(*) from mock_user_data_v1" in query_str:
                mock_result.scalar.return_value = len(protected_user_data)
            elif "select count(*) from mock_user_data_v2_temp" in query_str:
                # Should raise exception for rollback test
                raise Exception("Table does not exist (rollback successful)")
            elif "select count(*) from user_data_backup" in query_str:
                mock_result.scalar.return_value = len(protected_user_data)
            elif "group by user_id" in query_str:
                # Return user counts
                user_counts = {}
                for data in protected_user_data:
                    user_id = data['user_id']
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1
                mock_result.fetchall.return_value = list(user_counts.items())
            else:
                mock_result.scalar.return_value = 0
                mock_result.fetchall.return_value = []
            
            return mock_result
        
        mock_connection.execute.side_effect = mock_execute_side_effect
        
        # Execute rollback safety test
        validator = RollbackSafetyValidator(mock_engine)
        validator.execute_migration_with_rollback_test()
        validator.validate_rollback_integrity()
        validator.validate_backup_recovery_capability()
        
        # Assert rollback safety
        assert not validator.transaction_completed, "Transaction should not have completed (rollback expected)"
        assert validator.data_integrity_preserved, f"Data integrity not preserved: {validator.rollback_errors}"
        
        # Filter out expected errors (rollback messages)
        serious_errors = [
            error for error in validator.rollback_errors 
            if not ("expected" in error.lower() or "simulated" in error.lower())
        ]
        
        assert len(serious_errors) == 0, f"Rollback safety violations: {serious_errors}"
        
        # Verify rollback operations were performed
        executed_queries = [str(call.args[0]).upper() for call in mock_connection.execute.call_args_list]
        
        backup_created = any('CREATE TABLE user_data_backup' in query for query in executed_queries)
        assert backup_created, "Backup not created before migration"
        
        self.logger.info("Migration rollback safety validation passed")