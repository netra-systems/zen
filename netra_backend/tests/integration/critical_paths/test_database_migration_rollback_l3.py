#!/usr/bin/env python3
"""
Comprehensive test to verify database migration and rollback:
1. Check current database schema version
2. Apply forward migrations
3. Verify schema changes
4. Test data integrity during migration
5. Simulate migration failure
6. Execute rollback procedures
7. Verify rollback completeness
8. Test zero-downtime migration

This test ensures database migrations are safe and reversible.
"""

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import asyncpg
import pytest

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/netra_test"

# Test credentials
TEST_USER_EMAIL = "migration_test@example.com"
TEST_USER_PASSWORD = "migrationtest123"

class DatabaseMigrationTester:
    """Test database migration and rollback flow."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.db_connection = None
        self.initial_schema_version: Optional[int] = None
        self.current_schema_version: Optional[int] = None
        self.backup_data: Dict[str, List] = {}
        self.migration_log: List[Dict] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.db_connection:
            await self.db_connection.close()
        if self.session:
            await self.session.close()
            
    async def setup_database_connection(self) -> bool:
        """Setup direct database connection."""
        print("\n[DB] STEP 1: Connecting to database...")
        
        try:
            self.db_connection = await asyncpg.connect(DATABASE_URL)
            
            # Test connection
            version = await self.db_connection.fetchval("SELECT version()")
            print(f"[OK] Connected to database: {version[:50]}...")
            return True
            
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_current_schema_version(self) -> bool:
        """Check current database schema version."""
        print("\n[VERSION] STEP 2: Checking current schema version...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            # Check if migration table exists
            table_exists = await self.db_connection.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'schema_migrations'
                )
            """)
            
            if not table_exists:
                # Create migration tracking table
                await self.db_connection.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT,
                        checksum VARCHAR(64)
                    )
                """)
                print("[INFO] Created schema_migrations table")
                
            # Get current version
            self.initial_schema_version = await self.db_connection.fetchval("""
                SELECT COALESCE(MAX(version), 0) FROM schema_migrations
            """)
            
            print(f"[OK] Current schema version: {self.initial_schema_version}")
            
            # Log migration state
            self.migration_log.append({
                "action": "check_version",
                "version": self.initial_schema_version,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Version check failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_backup_critical_data(self) -> bool:
        """Backup critical data before migration."""
        print("\n[BACKUP] STEP 3: Backing up critical data...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            # List of critical tables to backup
            critical_tables = ["users", "threads", "agents", "configurations"]
            
            for table in critical_tables:
                # Check if table exists
                table_exists = await self.db_connection.fetchval(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """)
                
                if table_exists:
                    # Get row count
                    count = await self.db_connection.fetchval(f"SELECT COUNT(*) FROM {table}")
                    
                    # Backup sample data (first 100 rows)
                    rows = await self.db_connection.fetch(f"SELECT * FROM {table} LIMIT 100")
                    self.backup_data[table] = [dict(row) for row in rows]
                    
                    print(f"[OK] Backed up {table}: {count} total rows, {len(self.backup_data[table])} sampled")
                else:
                    print(f"[INFO] Table {table} does not exist yet")
                    
            return True
            
        except Exception as e:
            print(f"[ERROR] Backup failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_forward_migration(self) -> bool:
        """Apply forward migration."""
        print("\n[FORWARD] STEP 4: Applying forward migration...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            # Example migration: Add new columns and indexes
            new_version = (self.initial_schema_version or 0) + 1
            
            # Begin transaction
            async with self.db_connection.transaction():
                # Migration 1: Add analytics tables
                await self.db_connection.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_events (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(100) NOT NULL,
                        user_id INTEGER,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_event_type (event_type),
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    )
                """)
                
                # Migration 2: Add column to existing table (if exists)
                table_exists = await self.db_connection.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """)
                
                if table_exists:
                    # Check if column already exists
                    column_exists = await self.db_connection.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_name = 'users' 
                            AND column_name = 'last_migration_test'
                        )
                    """)
                    
                    if not column_exists:
                        await self.db_connection.execute("""
                            ALTER TABLE users 
                            ADD COLUMN last_migration_test TIMESTAMP
                        """)
                        
                # Record migration
                migration_desc = "Add analytics tables and user columns"
                checksum = hashlib.sha256(migration_desc.encode()).hexdigest()
                
                await self.db_connection.execute("""
                    INSERT INTO schema_migrations (version, description, checksum)
                    VALUES ($1, $2, $3)
                """, new_version, migration_desc, checksum)
                
                self.current_schema_version = new_version
                
            print(f"[OK] Migration applied: version {new_version}")
            
            # Log migration
            self.migration_log.append({
                "action": "forward_migration",
                "from_version": self.initial_schema_version,
                "to_version": new_version,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Forward migration failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_schema_verification(self) -> bool:
        """Verify schema changes after migration."""
        print("\n[VERIFY] STEP 5: Verifying schema changes...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            # Check new table exists
            analytics_exists = await self.db_connection.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'analytics_events'
                )
            """)
            
            if not analytics_exists:
                print("[ERROR] Analytics table not created")
                return False
                
            # Check indexes
            indexes = await self.db_connection.fetch("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'analytics_events'
            """)
            
            print(f"[OK] New table created with {len(indexes)} indexes")
            
            # Verify column addition
            column_info = await self.db_connection.fetchrow("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'last_migration_test'
            """)
            
            if column_info:
                print(f"[OK] New column added: {column_info['column_name']} ({column_info['data_type']})")
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Schema verification failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_data_integrity(self) -> bool:
        """Test data integrity after migration."""
        print("\n[INTEGRITY] STEP 6: Testing data integrity...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            integrity_checks = []
            
            # Check backed up tables still have data
            for table, backup_rows in self.backup_data.items():
                if backup_rows:
                    # Check row count
                    current_count = await self.db_connection.fetchval(f"SELECT COUNT(*) FROM {table}")
                    
                    # Verify sample data still exists
                    sample_row = backup_rows[0]
                    if 'id' in sample_row:
                        exists = await self.db_connection.fetchval(f"""
                            SELECT EXISTS(SELECT 1 FROM {table} WHERE id = $1)
                        """, sample_row['id'])
                        
                        integrity_checks.append({
                            "table": table,
                            "original_sample": len(backup_rows),
                            "current_count": current_count,
                            "sample_exists": exists
                        })
                        
            # Verify all checks passed
            all_passed = all(check.get("sample_exists", True) for check in integrity_checks)
            
            if all_passed:
                print(f"[OK] Data integrity verified for {len(integrity_checks)} tables")
                for check in integrity_checks:
                    print(f"  - {check['table']}: {check['current_count']} rows")
                return True
            else:
                print("[ERROR] Data integrity check failed")
                return False
                
        except Exception as e:
            print(f"[ERROR] Integrity check failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_migration_failure_simulation(self) -> bool:
        """Simulate a migration failure."""
        print("\n[FAILURE] STEP 7: Simulating migration failure...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            failed_version = (self.current_schema_version or 0) + 1
            
            # Attempt a failing migration
            try:
                async with self.db_connection.transaction():
                    # This should fail due to invalid SQL
                    await self.db_connection.execute("""
                        CREATE TABLE test_failure (
                            id SERIAL PRIMARY KEY,
                            INVALID SYNTAX HERE
                        )
                    """)
                    
                    # This should not be reached
                    await self.db_connection.execute("""
                        INSERT INTO schema_migrations (version, description, checksum)
                        VALUES ($1, $2, $3)
                    """, failed_version, "Failed migration", "test")
                    
            except Exception as migration_error:
                print(f"[OK] Migration failed as expected: {str(migration_error)[:100]}...")
                
                # Verify version didn't change
                current_version = await self.db_connection.fetchval("""
                    SELECT MAX(version) FROM schema_migrations
                """)
                
                if current_version == self.current_schema_version:
                    print(f"[OK] Version unchanged: {current_version}")
                    
                    # Log failure
                    self.migration_log.append({
                        "action": "failed_migration",
                        "attempted_version": failed_version,
                        "error": str(migration_error)[:200],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    return True
                else:
                    print("[ERROR] Version changed despite failure")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Failure simulation error: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_rollback_execution(self) -> bool:
        """Execute rollback to previous version."""
        print("\n[ROLLBACK] STEP 8: Executing rollback...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            if not self.current_schema_version:
                print("[ERROR] No current version to rollback from")
                return False
                
            # Begin rollback transaction
            async with self.db_connection.transaction():
                # Rollback: Remove analytics table
                await self.db_connection.execute("DROP TABLE IF EXISTS analytics_events CASCADE")
                
                # Rollback: Remove added column
                table_exists = await self.db_connection.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    )
                """)
                
                if table_exists:
                    column_exists = await self.db_connection.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_name = 'users' 
                            AND column_name = 'last_migration_test'
                        )
                    """)
                    
                    if column_exists:
                        await self.db_connection.execute("""
                            ALTER TABLE users 
                            DROP COLUMN last_migration_test
                        """)
                        
                # Remove migration record
                await self.db_connection.execute("""
                    DELETE FROM schema_migrations 
                    WHERE version = $1
                """, self.current_schema_version)
                
            # Verify rollback
            new_version = await self.db_connection.fetchval("""
                SELECT COALESCE(MAX(version), 0) FROM schema_migrations
            """)
            
            if new_version == self.initial_schema_version:
                print(f"[OK] Rolled back to version {new_version}")
                
                # Log rollback
                self.migration_log.append({
                    "action": "rollback",
                    "from_version": self.current_schema_version,
                    "to_version": new_version,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                self.current_schema_version = new_version
                return True
            else:
                print(f"[ERROR] Rollback failed: version is {new_version}, expected {self.initial_schema_version}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Rollback execution failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_rollback_verification(self) -> bool:
        """Verify rollback completeness."""
        print("\n[VERIFY] STEP 9: Verifying rollback completeness...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            # Check analytics table removed
            analytics_exists = await self.db_connection.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'analytics_events'
                )
            """)
            
            if analytics_exists:
                print("[ERROR] Analytics table still exists")
                return False
                
            # Check column removed
            column_exists = await self.db_connection.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'last_migration_test'
                )
            """)
            
            if column_exists:
                print("[ERROR] Migration column still exists")
                return False
                
            print("[OK] Rollback verified: schema restored to original state")
            
            # Verify data integrity after rollback
            for table, backup_rows in self.backup_data.items():
                if backup_rows and 'id' in backup_rows[0]:
                    exists = await self.db_connection.fetchval(f"""
                        SELECT EXISTS(SELECT 1 FROM {table} WHERE id = $1)
                    """, backup_rows[0]['id'])
                    
                    if not exists:
                        print(f"[ERROR] Data lost in {table} during rollback")
                        return False
                        
            print("[OK] Data integrity maintained after rollback")
            return True
            
        except Exception as e:
            print(f"[ERROR] Rollback verification failed: {e}")
            return False
            
    @pytest.mark.asyncio
    async def test_zero_downtime_migration(self) -> bool:
        """Test zero-downtime migration strategy."""
        print("\n[ZERO-DT] STEP 10: Testing zero-downtime migration...")
        
        if not self.db_connection:
            print("[ERROR] No database connection")
            return False
            
        try:
            # Create shadow table for zero-downtime migration
            async with self.db_connection.transaction():
                # Step 1: Create shadow table
                await self.db_connection.execute("""
                    CREATE TABLE IF NOT EXISTS users_shadow (
                        LIKE users INCLUDING ALL
                    )
                """)
                
                # Step 2: Add new column to shadow table
                await self.db_connection.execute("""
                    ALTER TABLE users_shadow 
                    ADD COLUMN IF NOT EXISTS zero_dt_test VARCHAR(100)
                """)
                
                # Step 3: Copy data to shadow table
                await self.db_connection.execute("""
                    INSERT INTO users_shadow 
                    SELECT *, NULL as zero_dt_test FROM users
                    ON CONFLICT DO NOTHING
                """)
                
                # Step 4: Create trigger for real-time sync
                await self.db_connection.execute("""
                    CREATE OR REPLACE FUNCTION sync_users_shadow()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        IF TG_OP = 'INSERT' THEN
                            INSERT INTO users_shadow SELECT NEW.*, NULL;
                        ELSIF TG_OP = 'UPDATE' THEN
                            UPDATE users_shadow SET * = NEW.* WHERE id = NEW.id;
                        ELSIF TG_OP = 'DELETE' THEN
                            DELETE FROM users_shadow WHERE id = OLD.id;
                        END IF;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql
                """)
                
                await self.db_connection.execute("""
                    CREATE TRIGGER sync_users_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON users
                    FOR EACH ROW EXECUTE FUNCTION sync_users_shadow()
                """)
                
            print("[OK] Zero-downtime migration prepared with shadow table")
            
            # Simulate table swap (would be atomic in production)
            print("[INFO] Would perform atomic table rename in production")
            
            # Cleanup
            async with self.db_connection.transaction():
                await self.db_connection.execute("DROP TRIGGER IF EXISTS sync_users_trigger ON users")
                await self.db_connection.execute("DROP FUNCTION IF EXISTS sync_users_shadow()")
                await self.db_connection.execute("DROP TABLE IF EXISTS users_shadow")
                
            print("[OK] Zero-downtime migration test completed")
            return True
            
        except Exception as e:
            print(f"[ERROR] Zero-downtime migration failed: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        # Setup database connection
        results["database_connection"] = await self.setup_database_connection()
        if not results["database_connection"]:
            print("\n[CRITICAL] Database connection failed. Aborting tests.")
            return results
            
        # Run migration tests
        results["schema_version"] = await self.test_current_schema_version()
        results["data_backup"] = await self.test_backup_critical_data()
        results["forward_migration"] = await self.test_forward_migration()
        results["schema_verification"] = await self.test_schema_verification()
        results["data_integrity"] = await self.test_data_integrity()
        results["failure_simulation"] = await self.test_migration_failure_simulation()
        results["rollback_execution"] = await self.test_rollback_execution()
        results["rollback_verification"] = await self.test_rollback_verification()
        results["zero_downtime"] = await self.test_zero_downtime_migration()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_database_migration_rollback():
    """Test database migration and rollback flow."""
    async with DatabaseMigrationTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("DATABASE MIGRATION TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        # Print migration log
        print(f"\nMigration Log ({len(tester.migration_log)} events):")
        for event in tester.migration_log:
            print(f"  - {event['action']}: {event.get('to_version', 'N/A')}")
            
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] All database migration tests passed!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed.")
            
        # Assert all tests passed
        assert all(results.values()), f"Some tests failed: {results}"

async def main():
    """Run the test standalone."""
    print("="*60)
    print("DATABASE MIGRATION AND ROLLBACK TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with DatabaseMigrationTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        if all(results.values()):
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)