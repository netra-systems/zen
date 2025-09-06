from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test Database Migrations

# REMOVED_SYNTAX_ERROR: Validates Alembic migrations work correctly with Cloud SQL
# REMOVED_SYNTAX_ERROR: in the staging environment.
""

import sys
from pathlib import Path

import pytest
# Test framework import - using pytest fixtures instead

import os
import subprocess
from typing import Dict, List

import psycopg2

from alembic import command
from alembic.config import Config

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

# REMOVED_SYNTAX_ERROR: class TestDatabaseMigrations(StagingConfigTestBase):
    # REMOVED_SYNTAX_ERROR: """Test database migrations in staging."""

# REMOVED_SYNTAX_ERROR: def setUp(self):
    # REMOVED_SYNTAX_ERROR: """Set up migration testing."""
    # REMOVED_SYNTAX_ERROR: super().setUp()

    # Get database configuration
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: self.db_url = self.assert_secret_exists('database-url')
        # REMOVED_SYNTAX_ERROR: except AssertionError:
            # REMOVED_SYNTAX_ERROR: self.skipTest("Database URL secret not found")

            # REMOVED_SYNTAX_ERROR: self.alembic_ini = 'alembic.ini'

# REMOVED_SYNTAX_ERROR: def test_migration_history(self):
    # REMOVED_SYNTAX_ERROR: """Verify migration history is consistent."""
    # REMOVED_SYNTAX_ERROR: self.skip_if_not_staging()

    # REMOVED_SYNTAX_ERROR: try:
        # Connect to database
        # REMOVED_SYNTAX_ERROR: conn = psycopg2.connect(self.db_url)
        # REMOVED_SYNTAX_ERROR: cursor = conn.cursor()

        # Check alembic version table exists
        # REMOVED_SYNTAX_ERROR: cursor.execute(''' )
        # REMOVED_SYNTAX_ERROR: SELECT EXISTS ( )
        # REMOVED_SYNTAX_ERROR: SELECT FROM information_schema.tables
        # REMOVED_SYNTAX_ERROR: WHERE table_name = 'alembic_version'
        
        # REMOVED_SYNTAX_ERROR: """)"

        # REMOVED_SYNTAX_ERROR: table_exists = cursor.fetchone()[0]
        # REMOVED_SYNTAX_ERROR: self.assertTrue(table_exists, "Alembic version table missing")

        # Get current revision
        # REMOVED_SYNTAX_ERROR: cursor.execute("SELECT version_num FROM alembic_version")
        # REMOVED_SYNTAX_ERROR: current_revision = cursor.fetchone()

        # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(current_revision,
        # REMOVED_SYNTAX_ERROR: "No migration revision found")

        # REMOVED_SYNTAX_ERROR: cursor.close()
        # REMOVED_SYNTAX_ERROR: conn.close()

        # REMOVED_SYNTAX_ERROR: except psycopg2.Error as e:
            # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_pending_migrations(self):
    # REMOVED_SYNTAX_ERROR: """Check for pending migrations."""
    # REMOVED_SYNTAX_ERROR: self.skip_if_not_staging()

    # REMOVED_SYNTAX_ERROR: try:
        # Run alembic check
        # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
        # REMOVED_SYNTAX_ERROR: ['alembic', 'current'],
        # REMOVED_SYNTAX_ERROR: capture_output=True,
        # REMOVED_SYNTAX_ERROR: text=True,
        # REMOVED_SYNTAX_ERROR: env={**os.environ, 'DATABASE_URL': self.db_url}
        

        # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
            # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

            # REMOVED_SYNTAX_ERROR: current = result.stdout.strip()

            # Check for pending migrations
            # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
            # REMOVED_SYNTAX_ERROR: ['alembic', 'heads'],
            # REMOVED_SYNTAX_ERROR: capture_output=True,
            # REMOVED_SYNTAX_ERROR: text=True,
            # REMOVED_SYNTAX_ERROR: env={**os.environ, 'DATABASE_URL': self.db_url}
            

            # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
                # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

                # REMOVED_SYNTAX_ERROR: heads = result.stdout.strip()

                # Current should match heads (no pending migrations)
                # REMOVED_SYNTAX_ERROR: if current != heads:
                    # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_migration_rollback(self):
    # REMOVED_SYNTAX_ERROR: """Test migration rollback capability."""
    # REMOVED_SYNTAX_ERROR: self.skip_if_not_staging()

    # This test is dangerous in staging, skip if not explicitly enabled
    # REMOVED_SYNTAX_ERROR: if not get_env().get('TEST_MIGRATION_ROLLBACK'):
        # REMOVED_SYNTAX_ERROR: self.skipTest("Migration rollback test disabled for safety")

        # REMOVED_SYNTAX_ERROR: try:
            # Get current revision
            # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
            # REMOVED_SYNTAX_ERROR: ['alembic', 'current'],
            # REMOVED_SYNTAX_ERROR: capture_output=True,
            # REMOVED_SYNTAX_ERROR: text=True,
            # REMOVED_SYNTAX_ERROR: env={**os.environ, 'DATABASE_URL': self.db_url}
            

            # REMOVED_SYNTAX_ERROR: original_revision = result.stdout.strip()

            # Downgrade one revision
            # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
            # REMOVED_SYNTAX_ERROR: ['alembic', 'downgrade', '-1'],
            # REMOVED_SYNTAX_ERROR: capture_output=True,
            # REMOVED_SYNTAX_ERROR: text=True,
            # REMOVED_SYNTAX_ERROR: env={**os.environ, 'DATABASE_URL': self.db_url}
            

            # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
                # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

                # Upgrade back
                # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
                # REMOVED_SYNTAX_ERROR: ['alembic', 'upgrade', original_revision],
                # REMOVED_SYNTAX_ERROR: capture_output=True,
                # REMOVED_SYNTAX_ERROR: text=True,
                # REMOVED_SYNTAX_ERROR: env={**os.environ, 'DATABASE_URL': self.db_url}
                

                # REMOVED_SYNTAX_ERROR: if result.returncode != 0:
                    # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_schema_consistency(self):
    # REMOVED_SYNTAX_ERROR: """Verify database schema matches expectations."""
    # REMOVED_SYNTAX_ERROR: self.skip_if_not_staging()

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: conn = psycopg2.connect(self.db_url)
        # REMOVED_SYNTAX_ERROR: cursor = conn.cursor()

        # Check critical tables exist
        # REMOVED_SYNTAX_ERROR: critical_tables = [ )
        # REMOVED_SYNTAX_ERROR: 'users',
        # REMOVED_SYNTAX_ERROR: 'threads',
        # REMOVED_SYNTAX_ERROR: 'messages',
        # REMOVED_SYNTAX_ERROR: 'agents',
        # REMOVED_SYNTAX_ERROR: 'teams',
        # REMOVED_SYNTAX_ERROR: 'workspaces'
        

        # REMOVED_SYNTAX_ERROR: missing_tables = []

        # REMOVED_SYNTAX_ERROR: for table in critical_tables:
            # REMOVED_SYNTAX_ERROR: cursor.execute(''' )
            # REMOVED_SYNTAX_ERROR: SELECT EXISTS ( )
            # REMOVED_SYNTAX_ERROR: SELECT FROM information_schema.tables
            # REMOVED_SYNTAX_ERROR: WHERE table_name = %s
            
            # REMOVED_SYNTAX_ERROR: """, (table,))"

            # REMOVED_SYNTAX_ERROR: if not cursor.fetchone()[0]:
                # REMOVED_SYNTAX_ERROR: missing_tables.append(table)

                # REMOVED_SYNTAX_ERROR: if missing_tables:
                    # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

                    # Check indexes
                    # REMOVED_SYNTAX_ERROR: cursor.execute(''' )
                    # REMOVED_SYNTAX_ERROR: SELECT indexname FROM pg_indexes
                    # REMOVED_SYNTAX_ERROR: WHERE schemaname = 'public'
                    # REMOVED_SYNTAX_ERROR: """)"

                    # REMOVED_SYNTAX_ERROR: indexes = [row[0] for row in cursor.fetchall()]

                    # Verify critical indexes exist
                    # REMOVED_SYNTAX_ERROR: critical_indexes = [ )
                    # REMOVED_SYNTAX_ERROR: 'ix_users_email',
                    # REMOVED_SYNTAX_ERROR: 'ix_threads_user_id',
                    # REMOVED_SYNTAX_ERROR: 'ix_messages_thread_id'
                    

                    # REMOVED_SYNTAX_ERROR: missing_indexes = []
                    # REMOVED_SYNTAX_ERROR: for index in critical_indexes:
                        # REMOVED_SYNTAX_ERROR: if index not in indexes:
                            # REMOVED_SYNTAX_ERROR: missing_indexes.append(index)

                            # REMOVED_SYNTAX_ERROR: if missing_indexes:
                                # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

                                # REMOVED_SYNTAX_ERROR: cursor.close()
                                # REMOVED_SYNTAX_ERROR: conn.close()

                                # REMOVED_SYNTAX_ERROR: except psycopg2.Error as e:
                                    # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_migration_data_integrity(self):
    # REMOVED_SYNTAX_ERROR: """Test data integrity during migrations."""
    # REMOVED_SYNTAX_ERROR: self.skip_if_not_staging()

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: conn = psycopg2.connect(self.db_url)
        # REMOVED_SYNTAX_ERROR: cursor = conn.cursor()

        # Check for orphaned records
        # REMOVED_SYNTAX_ERROR: integrity_checks = [ )
        # REMOVED_SYNTAX_ERROR: { )
        # REMOVED_SYNTAX_ERROR: 'name': 'Orphaned messages',
        # REMOVED_SYNTAX_ERROR: 'query': '''
        # REMOVED_SYNTAX_ERROR: SELECT COUNT(*) FROM messages m
        # REMOVED_SYNTAX_ERROR: LEFT JOIN threads t ON m.thread_id = t.id
        # REMOVED_SYNTAX_ERROR: WHERE t.id IS NULL
        # REMOVED_SYNTAX_ERROR: """"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: { )
        # REMOVED_SYNTAX_ERROR: 'name': 'Orphaned threads',
        # REMOVED_SYNTAX_ERROR: 'query': '''
        # REMOVED_SYNTAX_ERROR: SELECT COUNT(*) FROM threads t
        # REMOVED_SYNTAX_ERROR: LEFT JOIN users u ON t.user_id = u.id
        # REMOVED_SYNTAX_ERROR: WHERE u.id IS NULL
        # REMOVED_SYNTAX_ERROR: """"
        
        

        # REMOVED_SYNTAX_ERROR: integrity_issues = []

        # REMOVED_SYNTAX_ERROR: for check in integrity_checks:
            # REMOVED_SYNTAX_ERROR: cursor.execute(check['query'])
            # REMOVED_SYNTAX_ERROR: count = cursor.fetchone()[0]

            # REMOVED_SYNTAX_ERROR: if count > 0:
                # REMOVED_SYNTAX_ERROR: integrity_issues.append( )
                # REMOVED_SYNTAX_ERROR: "formatted_string" for i in integrity_issues))

                    # REMOVED_SYNTAX_ERROR: cursor.close()
                    # REMOVED_SYNTAX_ERROR: conn.close()

                    # REMOVED_SYNTAX_ERROR: except psycopg2.Error as e:
                        # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_migration_performance(self):
    # REMOVED_SYNTAX_ERROR: """Test migration performance metrics."""
    # REMOVED_SYNTAX_ERROR: self.skip_if_not_staging()

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: conn = psycopg2.connect(self.db_url)
        # REMOVED_SYNTAX_ERROR: cursor = conn.cursor()

        # Check table sizes
        # REMOVED_SYNTAX_ERROR: cursor.execute(''' )
        # REMOVED_SYNTAX_ERROR: SELECT
        # REMOVED_SYNTAX_ERROR: schemaname,
        # REMOVED_SYNTAX_ERROR: tablename,
        # REMOVED_SYNTAX_ERROR: pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
        # REMOVED_SYNTAX_ERROR: FROM pg_tables
        # REMOVED_SYNTAX_ERROR: WHERE schemaname = 'public'
        # REMOVED_SYNTAX_ERROR: ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        # REMOVED_SYNTAX_ERROR: LIMIT 10
        # REMOVED_SYNTAX_ERROR: """)"

        # REMOVED_SYNTAX_ERROR: large_tables = cursor.fetchall()

        # Warn about large tables that might affect migration performance
        # REMOVED_SYNTAX_ERROR: for schema, table, size in large_tables:
            # REMOVED_SYNTAX_ERROR: if 'GB' in size:
                # REMOVED_SYNTAX_ERROR: size_gb = float(size.replace(' GB', ''))
                # REMOVED_SYNTAX_ERROR: if size_gb > 1:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # REMOVED_SYNTAX_ERROR: cursor.close()
                    # REMOVED_SYNTAX_ERROR: conn.close()

                    # REMOVED_SYNTAX_ERROR: except psycopg2.Error as e:
                        # REMOVED_SYNTAX_ERROR: self.fail("formatted_string")
