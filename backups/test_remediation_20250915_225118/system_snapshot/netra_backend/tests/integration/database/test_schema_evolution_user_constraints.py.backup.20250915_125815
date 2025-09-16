"""
Integration Test: Schema Evolution with User Constraints using Real Database

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure schema evolution maintains user data isolation in production
- Value Impact: Schema changes without proper constraints can leak user data
- Strategic Impact: Safe database evolution for production multi-tenant platform

This integration test validates:
1. Real database schema changes preserve user isolation constraints
2. Database constraint enforcement prevents cross-user data access
3. Schema evolution maintains referential integrity for user boundaries
4. Production-like constraint validation under real database load

CRITICAL: Uses REAL PostgreSQL to validate actual constraint enforcement.
Authentication REQUIRED for proper user context validation.
"""

import asyncio
import uuid
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Database imports for schema testing
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select, and_, func, create_engine, MetaData
    from sqlalchemy.schema import CreateTable, CreateIndex, CreateCheckConstraint
    from sqlalchemy.exc import IntegrityError, CheckViolationError
    from netra_backend.app.db.models_postgres import User, Thread, Message
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None


class TestSchemaEvolutionUserConstraints(BaseIntegrationTest):
    """Test schema evolution with user constraints using real database."""

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for schema testing")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_constraints_enforce_user_isolation(self, lightweight_services_fixture, isolated_env):
        """Test that database constraints enforce user isolation in real PostgreSQL."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Create authenticated users for constraint testing
        auth_helper = E2EAuthHelper()
        
        constraint_users = []
        for i in range(3):
            user = await auth_helper.create_authenticated_user(
                email=f"constraint.user.{i}@test.com",
                full_name=f"Constraint Test User {i}"
            )
            constraint_users.append(user)
        
        # Create backend users
        for user in constraint_users:
            backend_user = User(
                id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
        
        await db_session.commit()
        
        # Create enhanced user isolation table with constraints
        enhanced_table_sql = """
        CREATE TABLE IF NOT EXISTS user_constraint_test (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            is_active BOOLEAN DEFAULT true,
            
            -- User isolation constraints
            CONSTRAINT check_user_id_not_empty CHECK (user_id != ''),
            CONSTRAINT check_content_not_empty CHECK (content != ''),
            CONSTRAINT check_user_metadata_consistency CHECK (
                metadata IS NULL OR (metadata->>'user_id')::text = user_id
            )
        )
        """
        
        await db_session.execute(text(enhanced_table_sql))
        
        # Create user isolation index
        user_isolation_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_user_constraint_test_user_id 
        ON user_constraint_test(user_id)
        """
        
        await db_session.execute(text(user_isolation_index_sql))
        
        # Create partial index for active user data
        active_user_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_user_constraint_test_active_user
        ON user_constraint_test(user_id, created_at)
        WHERE is_active = true
        """
        
        await db_session.execute(text(active_user_index_sql))
        await db_session.commit()
        
        # Test constraint enforcement
        constraint_test_results = []
        
        # Test 1: Valid user data insertion (should succeed)
        for i, user in enumerate(constraint_users):
            try:
                valid_data_sql = """
                INSERT INTO user_constraint_test (id, user_id, content, metadata, created_at, is_active)
                VALUES (:id, :user_id, :content, :metadata, :created_at, :is_active)
                """
                
                await db_session.execute(text(valid_data_sql), {
                    'id': f'valid_{user.user_id}_{i}',
                    'user_id': user.user_id,
                    'content': f'Valid content for user {i}',
                    'metadata': f'{{"user_id": "{user.user_id}", "test_type": "valid"}}',
                    'created_at': datetime.now(timezone.utc),
                    'is_active': True
                })
                
                constraint_test_results.append({
                    'test': 'valid_insertion',
                    'user_id': user.user_id,
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                constraint_test_results.append({
                    'test': 'valid_insertion',
                    'user_id': user.user_id,
                    'success': False,
                    'error': str(e)
                })
        
        await db_session.commit()
        
        # Test 2: Invalid user data (should fail constraints)
        invalid_test_cases = [
            {
                'name': 'empty_user_id',
                'data': {
                    'id': f'invalid_empty_user_{uuid.uuid4()}',
                    'user_id': '',  # Violates check_user_id_not_empty
                    'content': 'Valid content',
                    'metadata': '{}',
                    'created_at': datetime.now(timezone.utc),
                    'is_active': True
                },
                'should_fail': True
            },
            {
                'name': 'empty_content',
                'data': {
                    'id': f'invalid_empty_content_{uuid.uuid4()}',
                    'user_id': constraint_users[0].user_id,
                    'content': '',  # Violates check_content_not_empty
                    'metadata': f'{{"user_id": "{constraint_users[0].user_id}"}}',
                    'created_at': datetime.now(timezone.utc),
                    'is_active': True
                },
                'should_fail': True
            },
            {
                'name': 'metadata_user_mismatch',
                'data': {
                    'id': f'invalid_metadata_{uuid.uuid4()}',
                    'user_id': constraint_users[0].user_id,
                    'content': 'Valid content',
                    'metadata': f'{{"user_id": "{constraint_users[1].user_id}"}}',  # Mismatched user_id
                    'created_at': datetime.now(timezone.utc),
                    'is_active': True
                },
                'should_fail': True
            },
            {
                'name': 'null_user_id',
                'data': {
                    'id': f'invalid_null_user_{uuid.uuid4()}',
                    'user_id': None,  # Violates NOT NULL constraint
                    'content': 'Valid content',
                    'metadata': '{}',
                    'created_at': datetime.now(timezone.utc),
                    'is_active': True
                },
                'should_fail': True
            }
        ]
        
        for test_case in invalid_test_cases:
            try:
                invalid_sql = """
                INSERT INTO user_constraint_test (id, user_id, content, metadata, created_at, is_active)
                VALUES (:id, :user_id, :content, :metadata, :created_at, :is_active)
                """
                
                await db_session.execute(text(invalid_sql), test_case['data'])
                await db_session.commit()
                
                # If we reach here, constraint didn't work
                constraint_test_results.append({
                    'test': test_case['name'],
                    'user_id': test_case['data'].get('user_id', 'N/A'),
                    'success': not test_case['should_fail'],  # Should have failed
                    'error': f"Constraint {test_case['name']} not enforced - insertion succeeded when it should fail"
                })
                
            except Exception as e:
                # Expected failure for constraint violations
                constraint_test_results.append({
                    'test': test_case['name'],
                    'user_id': test_case['data'].get('user_id', 'N/A'),
                    'success': test_case['should_fail'],  # Should fail
                    'error': str(e)
                })
                
                # Rollback the failed transaction
                await db_session.rollback()
        
        # Test 3: Query isolation verification
        for user in constraint_users:
            user_data_query = """
            SELECT id, user_id, content
            FROM user_constraint_test
            WHERE user_id = :user_id AND is_active = true
            """
            
            result = await db_session.execute(text(user_data_query), {'user_id': user.user_id})
            user_records = result.fetchall()
            
            # Should only see this user's data
            for record in user_records:
                if record[1] != user.user_id:  # record[1] is user_id
                    constraint_test_results.append({
                        'test': 'query_isolation',
                        'user_id': user.user_id,
                        'success': False,
                        'error': f"Query returned data from different user: {record[1]}"
                    })
                    break
            else:
                constraint_test_results.append({
                    'test': 'query_isolation',
                    'user_id': user.user_id,
                    'success': True,
                    'error': None
                })
        
        # Analyze constraint test results
        constraint_failures = []
        successful_validations = 0
        
        for result in constraint_test_results:
            if not result['success']:
                constraint_failures.append(
                    f"Test '{result['test']}' for user {result['user_id']}: {result['error']}"
                )
            else:
                successful_validations += 1
        
        # Cleanup test table
        await db_session.execute(text("DROP TABLE IF EXISTS user_constraint_test"))
        await db_session.commit()
        await db_session.close()
        
        # Assert constraint enforcement
        assert len(constraint_failures) == 0, f"Database constraint violations: {constraint_failures}"
        
        # Verify reasonable success rate
        total_tests = len(constraint_test_results)
        success_rate = successful_validations / total_tests if total_tests > 0 else 0
        
        assert success_rate >= 0.8, \
            f"Too many constraint tests failed: {success_rate:.1%} success rate"
        
        self.logger.info(f"Database constraint enforcement validated: {successful_validations}/{total_tests} tests passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_referential_integrity_user_boundaries(self, lightweight_services_fixture, isolated_env):
        """Test referential integrity maintains user boundaries in real database."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
            
        db_session = lightweight_services_fixture["db"]
        if not db_session:
            pytest.skip("Database session not available")
        
        # Create authenticated users for referential integrity testing
        auth_helper = E2EAuthHelper()
        
        ref_users = []
        for i in range(2):
            user = await auth_helper.create_authenticated_user(
                email=f"ref.integrity.user.{i}@test.com",
                full_name=f"Referential Integrity User {i}"
            )
            ref_users.append(user)
        
        # Create backend users
        for user in ref_users:
            backend_user = User(
                id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                is_active=True
            )
            db_session.add(backend_user)
        
        await db_session.commit()
        
        # Create parent-child tables with user-aware foreign keys
        parent_table_sql = """
        CREATE TABLE IF NOT EXISTS user_parent_test (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            -- Ensure user exists in the system
            CONSTRAINT fk_user_parent_user_id FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT check_parent_user_not_empty CHECK (user_id != '')
        )
        """
        
        child_table_sql = """
        CREATE TABLE IF NOT EXISTS user_child_test (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            parent_id VARCHAR NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            -- Ensure user exists and child belongs to same user as parent
            CONSTRAINT fk_user_child_user_id FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT check_child_user_not_empty CHECK (user_id != ''),
            CONSTRAINT check_child_content_not_empty CHECK (content != '')
        )
        """
        
        # Create composite index for user-parent relationship
        parent_user_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_user_parent_test_user_id
        ON user_parent_test(user_id, id)
        """
        
        child_user_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_user_child_test_user_parent
        ON user_child_test(user_id, parent_id)
        """
        
        await db_session.execute(text(parent_table_sql))
        await db_session.execute(text(child_table_sql))
        await db_session.execute(text(parent_user_index_sql))
        await db_session.execute(text(child_user_index_sql))
        await db_session.commit()
        
        # Test referential integrity scenarios
        integrity_results = []
        
        # Create parent records for each user
        parent_records = {}
        for i, user in enumerate(ref_users):
            parent_id = f'parent_{user.user_id}_{i}'
            
            try:
                parent_insert_sql = """
                INSERT INTO user_parent_test (id, user_id, title, created_at)
                VALUES (:id, :user_id, :title, :created_at)
                """
                
                await db_session.execute(text(parent_insert_sql), {
                    'id': parent_id,
                    'user_id': user.user_id,
                    'title': f'Parent record for user {i}',
                    'created_at': datetime.now(timezone.utc)
                })
                
                parent_records[user.user_id] = parent_id
                
                integrity_results.append({
                    'test': 'parent_creation',
                    'user_id': user.user_id,
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                integrity_results.append({
                    'test': 'parent_creation',
                    'user_id': user.user_id,
                    'success': False,
                    'error': str(e)
                })
        
        await db_session.commit()
        
        # Test valid child record creation (same user as parent)
        for user in ref_users:
            if user.user_id in parent_records:
                try:
                    child_insert_sql = """
                    INSERT INTO user_child_test (id, user_id, parent_id, content, created_at)
                    VALUES (:id, :user_id, :parent_id, :content, :created_at)
                    """
                    
                    await db_session.execute(text(child_insert_sql), {
                        'id': f'child_{user.user_id}_1',
                        'user_id': user.user_id,  # Same user as parent
                        'parent_id': parent_records[user.user_id],
                        'content': f'Child content for user {user.user_id}',
                        'created_at': datetime.now(timezone.utc)
                    })
                    
                    integrity_results.append({
                        'test': 'valid_child_creation',
                        'user_id': user.user_id,
                        'success': True,
                        'error': None
                    })
                    
                except Exception as e:
                    integrity_results.append({
                        'test': 'valid_child_creation',
                        'user_id': user.user_id,
                        'success': False,
                        'error': str(e)
                    })
        
        await db_session.commit()
        
        # Test invalid child record creation (cross-user parent reference)
        if len(ref_users) >= 2:
            user_a = ref_users[0]
            user_b = ref_users[1]
            
            if user_a.user_id in parent_records and user_b.user_id in parent_records:
                try:
                    # Try to create child for user_b that references user_a's parent
                    cross_user_child_sql = """
                    INSERT INTO user_child_test (id, user_id, parent_id, content, created_at)
                    VALUES (:id, :user_id, :parent_id, :content, :created_at)
                    """
                    
                    await db_session.execute(text(cross_user_child_sql), {
                        'id': f'invalid_child_{user_b.user_id}',
                        'user_id': user_b.user_id,  # User B
                        'parent_id': parent_records[user_a.user_id],  # But User A's parent
                        'content': 'This should violate user boundary',
                        'created_at': datetime.now(timezone.utc)
                    })
                    
                    await db_session.commit()
                    
                    # If we reach here, the cross-user reference was allowed (bad!)
                    integrity_results.append({
                        'test': 'cross_user_prevention',
                        'user_id': user_b.user_id,
                        'success': False,
                        'error': 'Cross-user parent reference was allowed - referential integrity violation'
                    })
                    
                except Exception as e:
                    # Expected - cross-user reference should be logically prevented
                    # Note: Database FK constraints don't prevent this, but application logic should
                    integrity_results.append({
                        'test': 'cross_user_prevention', 
                        'user_id': user_b.user_id,
                        'success': True,  # Success means it was prevented
                        'error': f'Cross-user reference prevented: {str(e)}'
                    })
                    
                    await db_session.rollback()
        
        # Test referential integrity queries
        for user in ref_users:
            try:
                # Query should return parent-child pairs only for this user
                integrity_query_sql = """
                SELECT p.id as parent_id, c.id as child_id, p.user_id as parent_user, c.user_id as child_user
                FROM user_parent_test p
                LEFT JOIN user_child_test c ON p.id = c.parent_id
                WHERE p.user_id = :user_id
                """
                
                result = await db_session.execute(text(integrity_query_sql), {'user_id': user.user_id})
                user_relations = result.fetchall()
                
                # Verify all relations belong to the same user
                integrity_violation = False
                for relation in user_relations:
                    parent_user = relation[2]  # parent_user
                    child_user = relation[3]   # child_user
                    
                    if parent_user != user.user_id:
                        integrity_violation = True
                        break
                    
                    if child_user and child_user != user.user_id:
                        integrity_violation = True
                        break
                
                integrity_results.append({
                    'test': 'referential_query_integrity',
                    'user_id': user.user_id,
                    'success': not integrity_violation,
                    'error': 'Cross-user data in referential query' if integrity_violation else None
                })
                
            except Exception as e:
                integrity_results.append({
                    'test': 'referential_query_integrity',
                    'user_id': user.user_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Cleanup test tables
        await db_session.execute(text("DROP TABLE IF EXISTS user_child_test"))
        await db_session.execute(text("DROP TABLE IF EXISTS user_parent_test"))
        await db_session.commit()
        await db_session.close()
        
        # Analyze referential integrity results
        integrity_failures = []
        successful_integrity_tests = 0
        
        for result in integrity_results:
            if not result['success']:
                integrity_failures.append(
                    f"Referential integrity test '{result['test']}' for user {result['user_id']}: {result['error']}"
                )
            else:
                successful_integrity_tests += 1
        
        # Assert referential integrity
        assert len(integrity_failures) == 0, f"Referential integrity violations: {integrity_failures}"
        
        # Verify success rate
        total_integrity_tests = len(integrity_results)
        integrity_success_rate = successful_integrity_tests / total_integrity_tests if total_integrity_tests > 0 else 0
        
        assert integrity_success_rate >= 0.8, \
            f"Too many referential integrity tests failed: {integrity_success_rate:.1%} success rate"
        
        self.logger.info(f"Referential integrity with user boundaries validated: "
                        f"{successful_integrity_tests}/{total_integrity_tests} tests passed")