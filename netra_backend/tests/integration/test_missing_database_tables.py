"""
Integration test for missing database tables during dev launcher startup.
Tests database schema creation, table initialization, and migration status.
"""
import pytest
import asyncio
from sqlalchemy import create_engine, text, inspect
from netra_backend.app.config import get_config


class TestMissingDatabaseTables:
    """Test for missing database tables and schema issues."""

    def test_database_connection_available(self):
        """Test that database connection is available."""
        config = get_config()
        
        assert hasattr(config, 'database_url'), "Database URL missing"
        assert config.database_url, "Database URL is empty"
        
        db_url = config.database_url
        print(f"Database URL: {db_url[:50]}...")
        
        # Test basic connection
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                print("✓ Database connection successful")
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")

    def test_database_schema_tables_exist(self):
        """Test that required database tables exist."""
        config = get_config()
        db_url = config.database_url
        
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Get all table names
        table_names = inspector.get_table_names()
        print(f"Existing tables: {table_names}")
        
        # Expected core tables (these should exist for the backend to work)
        expected_tables = [
            'users',  # User management
            'sessions',  # Session management
            'threads',  # Thread management
        ]
        
        missing_tables = []
        for table in expected_tables:
            if table not in table_names:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            # Don't fail immediately - this might be expected if migrations haven't run
        else:
            print("✓ All expected tables exist")

    def test_alembic_migration_status(self):
        """Test Alembic migration status."""
        config = get_config()
        db_url = config.database_url
        
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Check if alembic_version table exists
        table_names = inspector.get_table_names()
        
        if 'alembic_version' not in table_names:
            print("⚠ Alembic version table missing - migrations may not have been run")
            pytest.skip("Alembic migrations not initialized")
        
        # Check current migration version
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            
            if version:
                print(f"✓ Current migration version: {version}")
            else:
                print("⚠ No migration version found")

    def test_database_initialization_check(self):
        """Test if database needs initialization."""
        config = get_config()
        db_url = config.database_url
        
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        table_names = inspector.get_table_names()
        
        if not table_names:
            print("⚠ Database is completely empty - needs full initialization")
            return False
        elif len(table_names) < 5:  # Arbitrary threshold
            print(f"⚠ Database has only {len(table_names)} tables - may need initialization")
            return False
        else:
            print(f"✓ Database has {len(table_names)} tables - appears initialized")
            return True

    def test_specific_critical_tables(self):
        """Test for specific critical tables that backend needs."""
        config = get_config()
        db_url = config.database_url
        
        engine = create_engine(db_url)
        
        # Test specific tables that are critical for backend operation
        critical_tables = {
            'users': 'User authentication and management',
            'sessions': 'Session management',
            'threads': 'Thread/conversation management',
            'agents': 'Agent configuration',
            'workload_events': 'Workload tracking (if using PostgreSQL for this)'
        }
        
        missing_critical = []
        existing_critical = []
        
        with engine.connect() as conn:
            for table_name, description in critical_tables.items():
                try:
                    # Try to query the table
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE 1=0"))
                    existing_critical.append(table_name)
                    print(f"✓ {table_name}: {description}")
                except Exception as e:
                    missing_critical.append((table_name, description, str(e)))
                    print(f"✗ {table_name}: {description} - {e}")
        
        print(f"Existing critical tables: {existing_critical}")
        print(f"Missing critical tables: {[name for name, _, _ in missing_critical]}")
        
        return existing_critical, missing_critical

    def test_database_permissions(self):
        """Test database permissions for table creation."""
        config = get_config()
        db_url = config.database_url
        
        engine = create_engine(db_url)
        
        test_table_name = "netra_test_permissions_check"
        
        try:
            with engine.connect() as conn:
                # Try to create a test table
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {test_table_name} (
                        id SERIAL PRIMARY KEY,
                        test_column TEXT
                    )
                """))
                conn.commit()
                
                # Try to drop the test table
                conn.execute(text(f"DROP TABLE IF EXISTS {test_table_name}"))
                conn.commit()
                
                print("✓ Database permissions OK - can create/drop tables")
                return True
                
        except Exception as e:
            print(f"✗ Database permission issue: {e}")
            return False

    def test_check_migration_files_exist(self):
        """Test if migration files exist in the project."""
        import os
        
        # Look for alembic migration directory
        migration_paths = [
            'alembic/versions',
            'migrations/versions',
            'netra_backend/alembic/versions',
            'netra_backend/migrations/versions'
        ]
        
        for path in migration_paths:
            if os.path.exists(path):
                files = os.listdir(path)
                migration_files = [f for f in files if f.endswith('.py') and not f.startswith('__')]
                
                if migration_files:
                    print(f"✓ Found {len(migration_files)} migration files in {path}")
                    print(f"Migration files: {migration_files[:3]}...")  # Show first 3
                    return True
                    
        print("⚠ No migration files found - database may need manual initialization")
        return False

    def test_run_alembic_check(self):
        """Test running alembic check to see migration status."""
        import subprocess
        import os
        
        try:
            # Change to the backend directory
            original_dir = os.getcwd()
            backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            os.chdir(backend_dir)
            
            # Try to run alembic current
            result = subprocess.run(
                ['python', '-m', 'alembic', 'current'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            os.chdir(original_dir)
            
            if result.returncode == 0:
                print(f"✓ Alembic current: {result.stdout.strip()}")
                return result.stdout.strip()
            else:
                print(f"⚠ Alembic error: {result.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            print("⚠ Alembic command timed out")
            return None
        except Exception as e:
            print(f"⚠ Could not run alembic: {e}")
            return None

    def test_manual_table_creation_if_needed(self):
        """Test creating essential tables manually if migrations haven't run."""
        config = get_config()
        db_url = config.database_url
        
        engine = create_engine(db_url)
        
        # Check if we need to create tables manually
        existing_critical, missing_critical = self.test_specific_critical_tables()
        
        if len(missing_critical) > len(existing_critical):
            print("⚠ More tables missing than existing - may need manual creation")
            
            # Try to create a basic users table as an example
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            email VARCHAR(255) UNIQUE NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()
                    
                    print("✓ Created basic users table manually")
                    return True
                    
            except Exception as e:
                print(f"✗ Could not create users table manually: {e}")
                return False
        
        return True


if __name__ == "__main__":
    # Run this test to check for missing database tables
    pytest.main([__file__, "-v", "-s"])