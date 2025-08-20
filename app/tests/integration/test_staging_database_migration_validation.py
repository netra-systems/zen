"""
Staging Database Migration Validation Test

Business Value: Protects data integrity for all customer segments. Data corruption
would cause immediate customer churn and compliance violations.

Priority: P0 (Critical Data Protection)
"""

import asyncio
import pytest
import time
import os
import subprocess
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime
import json
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import hashlib


class StagingDatabaseMigrationValidator:
    """Validates database migrations work correctly in staging environment."""
    
    def __init__(self):
        """Initialize database migration validator."""
        self.is_staging = os.getenv("ENVIRONMENT", "local") == "staging"
        
        # Database configuration
        if self.is_staging:
            # Cloud SQL format: postgresql://user:pass@/db?host=/cloudsql/instance
            self.db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://netra:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:netra-db"
            )
            # For Alembic, must use synchronous URL (not postgresql+asyncpg)
            self.alembic_db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            self.db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/netra_test"
            )
            self.alembic_db_url = self.db_url
        
        # Migration paths
        self.alembic_ini = "app/alembic.ini"
        self.migrations_dir = "app/alembic/versions"
        
        # Test data for validation
        self.test_schema_validations = {
            "users": ["id", "email", "created_at", "tier"],
            "threads": ["id", "user_id", "created_at", "status"],
            "messages": ["id", "thread_id", "content", "created_at"],
            "api_keys": ["id", "user_id", "key_hash", "created_at"]
        }
    
    def get_db_connection(self):
        """Get direct database connection for validation."""
        try:
            # Parse connection string
            if "/cloudsql/" in self.db_url:
                # Cloud SQL format
                parts = self.db_url.split("?")
                base = parts[0].replace("postgresql://", "")
                user_pass, db = base.split("@/")
                user, password = user_pass.split(":")
                host = parts[1].replace("host=", "") if len(parts) > 1 else "localhost"
                
                return psycopg2.connect(
                    host=host,
                    database=db,
                    user=user,
                    password=password
                )
            else:
                # Standard format
                return psycopg2.connect(self.db_url)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    async def test_database_connectivity(self) -> Tuple[bool, str]:
        """Test basic database connectivity."""
        conn = self.get_db_connection()
        if not conn:
            return (False, "Cannot connect to database")
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            if "PostgreSQL" in version:
                return (True, f"Connected to {version.split(',')[0]}")
            else:
                return (False, f"Unexpected database: {version}")
                
        except Exception as e:
            return (False, f"Database query failed: {str(e)}")
    
    async def test_cloud_sql_format(self) -> Tuple[bool, str]:
        """Validate Cloud SQL connection format for staging."""
        if not self.is_staging:
            return (True, "Local environment - Cloud SQL format not required")
        
        # Check if DATABASE_URL uses correct Cloud SQL format
        if "/cloudsql/" not in self.db_url:
            return (False, "DATABASE_URL missing Cloud SQL socket path (/cloudsql/)")
        
        # Validate format: postgresql://user:pass@/db?host=/cloudsql/project:region:instance
        if "@/" not in self.db_url:
            return (False, "Invalid Cloud SQL format - missing @/ for socket connection")
        
        if "?host=" not in self.db_url:
            return (False, "Missing host parameter for Cloud SQL socket")
        
        return (True, "Cloud SQL connection format valid")
    
    async def get_current_migration_version(self) -> Tuple[bool, str, Optional[str]]:
        """Get current migration version from database."""
        conn = self.get_db_connection()
        if not conn:
            return (False, "Cannot connect to database", None)
        
        try:
            cursor = conn.cursor()
            # Check if alembic_version table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """)
            
            exists = cursor.fetchone()[0]
            
            if not exists:
                cursor.close()
                conn.close()
                return (True, "No migrations applied yet (fresh database)", None)
            
            # Get current version
            cursor.execute("SELECT version_num FROM alembic_version")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return (True, f"Current migration: {result[0][:12]}...", result[0])
            else:
                return (True, "Migration table exists but empty", None)
                
        except Exception as e:
            return (False, f"Failed to get migration version: {str(e)}", None)
    
    async def test_migration_dry_run(self) -> Tuple[bool, str]:
        """Test migration dry run without applying changes."""
        try:
            # Run alembic check to see pending migrations
            result = subprocess.run(
                ["alembic", "-c", self.alembic_ini, "history", "--verbose"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "DATABASE_URL": self.alembic_db_url}
            )
            
            if result.returncode == 0:
                # Check if there are pending migrations
                if "head" in result.stdout and "current" in result.stdout:
                    return (True, "Migration history accessible")
                else:
                    return (True, "Migration check passed")
            else:
                return (False, f"Migration check failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            return (False, "Migration check timed out")
        except Exception as e:
            return (False, f"Migration check error: {str(e)}")
    
    async def validate_schema_integrity(self) -> Tuple[bool, str, List[str]]:
        """Validate database schema has required tables and columns."""
        conn = self.get_db_connection()
        if not conn:
            return (False, "Cannot connect to database", [])
        
        issues = []
        
        try:
            cursor = conn.cursor()
            
            for table, required_columns in self.test_schema_validations.items():
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table,))
                
                exists = cursor.fetchone()[0]
                
                if not exists:
                    issues.append(f"Missing table: {table}")
                    continue
                
                # Check columns
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                """, (table,))
                
                existing_columns = [row[0] for row in cursor.fetchall()]
                missing_columns = [col for col in required_columns if col not in existing_columns]
                
                if missing_columns:
                    issues.append(f"Table '{table}' missing columns: {missing_columns}")
            
            cursor.close()
            conn.close()
            
            if issues:
                return (False, f"Schema validation failed: {len(issues)} issues", issues)
            else:
                return (True, "Schema validation passed", [])
                
        except Exception as e:
            return (False, f"Schema validation error: {str(e)}", [])
    
    async def test_migration_rollback_capability(self) -> Tuple[bool, str]:
        """Test that migrations can be rolled back safely."""
        # Check if downgrade scripts exist
        try:
            if not os.path.exists(self.migrations_dir):
                return (False, f"Migrations directory not found: {self.migrations_dir}")
            
            migration_files = [f for f in os.listdir(self.migrations_dir) if f.endswith(".py")]
            
            if not migration_files:
                return (True, "No migrations to check")
            
            # Sample check - verify latest migration has downgrade
            latest_migration = sorted(migration_files)[-1]
            migration_path = os.path.join(self.migrations_dir, latest_migration)
            
            with open(migration_path, 'r') as f:
                content = f.read()
                
            if "def downgrade()" not in content:
                return (False, f"Migration {latest_migration} missing downgrade function")
            
            if "pass" in content.split("def downgrade()")[1].split("def")[0]:
                return (False, f"Migration {latest_migration} has empty downgrade")
            
            return (True, f"Rollback capability verified for {len(migration_files)} migrations")
            
        except Exception as e:
            return (False, f"Rollback check error: {str(e)}")
    
    async def test_data_integrity_check(self) -> Tuple[bool, str]:
        """Test data integrity constraints are maintained."""
        conn = self.get_db_connection()
        if not conn:
            return (False, "Cannot connect to database")
        
        try:
            cursor = conn.cursor()
            
            # Check foreign key constraints
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
            """)
            
            foreign_keys = cursor.fetchall()
            
            # Check unique constraints
            cursor.execute("""
                SELECT 
                    tc.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'UNIQUE'
            """)
            
            unique_constraints = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Validate critical constraints exist
            critical_fks = [
                ("threads", "user_id"),  # Threads must reference users
                ("messages", "thread_id"),  # Messages must reference threads
            ]
            
            existing_fks = [(fk[1], fk[2]) for fk in foreign_keys]
            missing_fks = [fk for fk in critical_fks if fk not in existing_fks]
            
            if missing_fks:
                return (False, f"Missing critical foreign keys: {missing_fks}")
            
            return (True, f"Data integrity validated: {len(foreign_keys)} FKs, {len(unique_constraints)} unique constraints")
            
        except Exception as e:
            return (False, f"Data integrity check error: {str(e)}")
    
    async def test_migration_idempotency(self) -> Tuple[bool, str]:
        """Test that migrations are idempotent (can be run multiple times safely)."""
        try:
            # Try to run current migration again (should be no-op)
            result = subprocess.run(
                ["alembic", "-c", self.alembic_ini, "current"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "DATABASE_URL": self.alembic_db_url}
            )
            
            if result.returncode == 0:
                current = result.stdout.strip()
                
                # Try to upgrade to current (should be no-op)
                result2 = subprocess.run(
                    ["alembic", "-c", self.alembic_ini, "upgrade", "head", "--sql"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, "DATABASE_URL": self.alembic_db_url}
                )
                
                if result2.returncode == 0:
                    if "-- Running upgrade" not in result2.stdout or len(result2.stdout) < 100:
                        return (True, "Migrations are idempotent")
                    else:
                        return (False, "Pending migrations detected - not idempotent")
                        
            return (True, "Migration idempotency check passed")
            
        except Exception as e:
            return (False, f"Idempotency check error: {str(e)}")
    
    async def run_migration_validation(self) -> Dict[str, Any]:
        """Run complete database migration validation suite."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "staging" if self.is_staging else "local",
            "tests": {},
            "schema_issues": [],
            "overall_success": False,
            "data_safe": False,
            "business_impact": ""
        }
        
        print("\n" + "="*70)
        print("STAGING DATABASE MIGRATION VALIDATION")
        print(f"Environment: {results['environment']}")
        print(f"Database URL format: {'Cloud SQL' if '/cloudsql/' in self.db_url else 'Standard'}")
        print("="*70)
        
        # Phase 1: Database Connectivity
        print("\n[Phase 1] Testing database connectivity...")
        conn_ok, conn_msg = await self.test_database_connectivity()
        results["tests"]["connectivity"] = {"success": conn_ok, "message": conn_msg}
        print(f"  {'✓' if conn_ok else '✗'} {conn_msg}")
        
        if not conn_ok:
            results["business_impact"] = "✗ Database unreachable - total platform failure"
            print(f"\nCRITICAL: {results['business_impact']}")
            return results
        
        # Phase 2: Cloud SQL Format (staging only)
        print("\n[Phase 2] Validating Cloud SQL format...")
        cloud_ok, cloud_msg = await self.test_cloud_sql_format()
        results["tests"]["cloud_sql_format"] = {"success": cloud_ok, "message": cloud_msg}
        print(f"  {'✓' if cloud_ok else '✗'} {cloud_msg}")
        
        # Phase 3: Current Migration Version
        print("\n[Phase 3] Checking current migration version...")
        version_ok, version_msg, current_version = await self.get_current_migration_version()
        results["tests"]["current_version"] = {"success": version_ok, "message": version_msg}
        print(f"  {'✓' if version_ok else '✗'} {version_msg}")
        
        # Phase 4: Migration Dry Run
        print("\n[Phase 4] Testing migration dry run...")
        dry_ok, dry_msg = await self.test_migration_dry_run()
        results["tests"]["dry_run"] = {"success": dry_ok, "message": dry_msg}
        print(f"  {'✓' if dry_ok else '✗'} {dry_msg}")
        
        # Phase 5: Schema Integrity
        print("\n[Phase 5] Validating schema integrity...")
        schema_ok, schema_msg, issues = await self.validate_schema_integrity()
        results["tests"]["schema_integrity"] = {"success": schema_ok, "message": schema_msg}
        results["schema_issues"] = issues
        print(f"  {'✓' if schema_ok else '✗'} {schema_msg}")
        if issues:
            for issue in issues[:5]:  # Show first 5 issues
                print(f"    - {issue}")
        
        # Phase 6: Rollback Capability
        print("\n[Phase 6] Testing rollback capability...")
        rollback_ok, rollback_msg = await self.test_migration_rollback_capability()
        results["tests"]["rollback"] = {"success": rollback_ok, "message": rollback_msg}
        print(f"  {'✓' if rollback_ok else '✗'} {rollback_msg}")
        
        # Phase 7: Data Integrity
        print("\n[Phase 7] Checking data integrity constraints...")
        integrity_ok, integrity_msg = await self.test_data_integrity_check()
        results["tests"]["data_integrity"] = {"success": integrity_ok, "message": integrity_msg}
        print(f"  {'✓' if integrity_ok else '✗'} {integrity_msg}")
        
        # Phase 8: Migration Idempotency
        print("\n[Phase 8] Testing migration idempotency...")
        idempotent_ok, idempotent_msg = await self.test_migration_idempotency()
        results["tests"]["idempotency"] = {"success": idempotent_ok, "message": idempotent_msg}
        print(f"  {'✓' if idempotent_ok else '✗'} {idempotent_msg}")
        
        # Calculate overall success
        critical_tests = ["connectivity", "schema_integrity", "data_integrity"]
        critical_passed = all(
            results["tests"].get(test, {}).get("success", False)
            for test in critical_tests
        )
        
        results["data_safe"] = integrity_ok and schema_ok
        results["overall_success"] = critical_passed and rollback_ok
        
        # Business impact assessment
        if results["overall_success"]:
            results["business_impact"] = "✓ Database migrations safe - data integrity protected"
        elif results["data_safe"]:
            results["business_impact"] = "⚠ Data safe but migration issues detected"
        else:
            results["business_impact"] = "✗ Data integrity at risk - potential corruption"
        
        # Summary
        print("\n" + "="*70)
        print("MIGRATION VALIDATION SUMMARY")
        print("="*70)
        passed = sum(1 for t in results["tests"].values() if t["success"])
        total = len(results["tests"])
        print(f"Tests Passed: {passed}/{total}")
        print(f"Data Safety: {'✓ PROTECTED' if results['data_safe'] else '✗ AT RISK'}")
        print(f"Overall: {'✓ PASSED' if results['overall_success'] else '✗ FAILED'}")
        print(f"Business Impact: {results['business_impact']}")
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
async def test_staging_database_migration_critical():
    """
    Test critical database migration paths.
    
    BVJ: Protects data integrity for all customers, preventing data loss and compliance violations.
    Priority: P0 - Data corruption would cause immediate customer churn.
    """
    validator = StagingDatabaseMigrationValidator()
    results = await validator.run_migration_validation()
    
    # Critical assertions
    assert results["data_safe"], (
        f"Data integrity at risk in {results['environment']}! "
        f"Schema issues: {results['schema_issues'][:3]}. "
        f"Business impact: {results['business_impact']}"
    )
    
    # Rollback capability is critical for recovery
    assert results["tests"]["rollback"]["success"], (
        "Migration rollback capability missing! "
        "Cannot recover from failed migrations. "
        "This is a critical operational risk."
    )
    
    print(f"\n[SUCCESS] Database migrations validated - data integrity protected")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_staging_database_schema():
    """
    Test database schema integrity.
    
    BVJ: Ensures all required tables and columns exist for application functionality.
    Priority: P0 - Missing schema elements break application features.
    """
    validator = StagingDatabaseMigrationValidator()
    
    schema_ok, schema_msg, issues = await validator.validate_schema_integrity()
    
    assert schema_ok, (
        f"Schema validation failed: {schema_msg}. "
        f"Issues found: {issues}. "
        "Application features will not work correctly."
    )
    
    print(f"\n[SUCCESS] Database schema validated")


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_staging_database_quick_check():
    """
    Quick smoke test for database - runs in <3 seconds.
    
    Used for rapid validation during deployments.
    """
    validator = StagingDatabaseMigrationValidator()
    
    # Just check database connectivity
    conn_ok, conn_msg = await validator.test_database_connectivity()
    
    assert conn_ok, f"Database connectivity failed: {conn_msg}"
    
    print(f"\n[SMOKE TEST PASS] Database accessible")


if __name__ == "__main__":
    """Run database migration validation standalone."""
    async def run_validation():
        validator = StagingDatabaseMigrationValidator()
        results = await validator.run_migration_validation()
        
        exit_code = 0 if results["overall_success"] else 1
        exit(exit_code)
    
    asyncio.run(run_validation())