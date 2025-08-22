"""
Test Database Migrations

Validates Alembic migrations work correctly with Cloud SQL
in the staging environment.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import os
import subprocess
from typing import Dict, List

import psycopg2

from alembic import command
from alembic.config import Config

# Add project root to path
from tests.base import StagingConfigTestBase

# Add project root to path


class TestDatabaseMigrations(StagingConfigTestBase):
    """Test database migrations in staging."""
    
    def setUp(self):
        """Set up migration testing."""
        super().setUp()
        
        # Get database configuration
        try:
            self.db_url = self.assert_secret_exists('database-url')
        except AssertionError:
            self.skipTest("Database URL secret not found")
            
        self.alembic_ini = 'alembic.ini'
        
    def test_migration_history(self):
        """Verify migration history is consistent."""
        self.skip_if_not_staging()
        
        try:
            # Connect to database
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Check alembic version table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """)
            
            table_exists = cursor.fetchone()[0]
            self.assertTrue(table_exists, "Alembic version table missing")
            
            # Get current revision
            cursor.execute("SELECT version_num FROM alembic_version")
            current_revision = cursor.fetchone()
            
            self.assertIsNotNone(current_revision,
                               "No migration revision found")
                               
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            self.fail(f"Migration history check failed: {e}")
            
    def test_pending_migrations(self):
        """Check for pending migrations."""
        self.skip_if_not_staging()
        
        try:
            # Run alembic check
            result = subprocess.run(
                ['alembic', 'current'],
                capture_output=True,
                text=True,
                env={**os.environ, 'DATABASE_URL': self.db_url}
            )
            
            if result.returncode != 0:
                self.fail(f"Failed to check current migration: {result.stderr}")
                
            current = result.stdout.strip()
            
            # Check for pending migrations
            result = subprocess.run(
                ['alembic', 'heads'],
                capture_output=True,
                text=True,
                env={**os.environ, 'DATABASE_URL': self.db_url}
            )
            
            if result.returncode != 0:
                self.fail(f"Failed to check migration heads: {result.stderr}")
                
            heads = result.stdout.strip()
            
            # Current should match heads (no pending migrations)
            if current != heads:
                self.fail(f"Pending migrations detected. Current: {current}, Heads: {heads}")
                
        except Exception as e:
            self.fail(f"Migration check failed: {e}")
            
    def test_migration_rollback(self):
        """Test migration rollback capability."""
        self.skip_if_not_staging()
        
        # This test is dangerous in staging, skip if not explicitly enabled
        if not os.getenv('TEST_MIGRATION_ROLLBACK'):
            self.skipTest("Migration rollback test disabled for safety")
            
        try:
            # Get current revision
            result = subprocess.run(
                ['alembic', 'current'],
                capture_output=True,
                text=True,
                env={**os.environ, 'DATABASE_URL': self.db_url}
            )
            
            original_revision = result.stdout.strip()
            
            # Downgrade one revision
            result = subprocess.run(
                ['alembic', 'downgrade', '-1'],
                capture_output=True,
                text=True,
                env={**os.environ, 'DATABASE_URL': self.db_url}
            )
            
            if result.returncode != 0:
                self.fail(f"Migration rollback failed: {result.stderr}")
                
            # Upgrade back
            result = subprocess.run(
                ['alembic', 'upgrade', original_revision],
                capture_output=True,
                text=True,
                env={**os.environ, 'DATABASE_URL': self.db_url}
            )
            
            if result.returncode != 0:
                self.fail(f"Migration re-apply failed: {result.stderr}")
                
        except Exception as e:
            self.fail(f"Rollback test failed: {e}")
            
    def test_schema_consistency(self):
        """Verify database schema matches expectations."""
        self.skip_if_not_staging()
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Check critical tables exist
            critical_tables = [
                'users',
                'threads',
                'messages',
                'agents',
                'teams',
                'workspaces'
            ]
            
            missing_tables = []
            
            for table in critical_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table,))
                
                if not cursor.fetchone()[0]:
                    missing_tables.append(table)
                    
            if missing_tables:
                self.fail(f"Missing critical tables: {missing_tables}")
                
            # Check indexes
            cursor.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Verify critical indexes exist
            critical_indexes = [
                'ix_users_email',
                'ix_threads_user_id',
                'ix_messages_thread_id'
            ]
            
            missing_indexes = []
            for index in critical_indexes:
                if index not in indexes:
                    missing_indexes.append(index)
                    
            if missing_indexes:
                self.fail(f"Missing critical indexes: {missing_indexes}")
                
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            self.fail(f"Schema consistency check failed: {e}")
            
    def test_migration_data_integrity(self):
        """Test data integrity during migrations."""
        self.skip_if_not_staging()
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Check for orphaned records
            integrity_checks = [
                {
                    'name': 'Orphaned messages',
                    'query': """
                        SELECT COUNT(*) FROM messages m
                        LEFT JOIN threads t ON m.thread_id = t.id
                        WHERE t.id IS NULL
                    """
                },
                {
                    'name': 'Orphaned threads',
                    'query': """
                        SELECT COUNT(*) FROM threads t
                        LEFT JOIN users u ON t.user_id = u.id
                        WHERE u.id IS NULL
                    """
                }
            ]
            
            integrity_issues = []
            
            for check in integrity_checks:
                cursor.execute(check['query'])
                count = cursor.fetchone()[0]
                
                if count > 0:
                    integrity_issues.append(
                        f"{check['name']}: {count} records"
                    )
                    
            if integrity_issues:
                self.fail("Data integrity issues found:\n" +
                         '\n'.join(f"  - {i}" for i in integrity_issues))
                         
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            self.fail(f"Data integrity check failed: {e}")
            
    def test_migration_performance(self):
        """Test migration performance metrics."""
        self.skip_if_not_staging()
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Check table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)
            
            large_tables = cursor.fetchall()
            
            # Warn about large tables that might affect migration performance
            for schema, table, size in large_tables:
                if 'GB' in size:
                    size_gb = float(size.replace(' GB', ''))
                    if size_gb > 1:
                        print(f"Warning: Large table {table} ({size}) may affect migration performance")
                        
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            self.fail(f"Performance check failed: {e}")