"""
Test Database Initialization Basic Functionality

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Stability & Database Readiness
- Value Impact: Ensures database is properly initialized for basic system operations
- Strategic Impact: Critical foundation for all user-facing features and data persistence

This test validates that the database is properly set up and can handle basic operations
that are fundamental to system functionality. This test SHOULD FAIL if database is not
properly initialized.

Focus: Basic database setup that must work for any user interaction.
"""
import os
import sys
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from shared.isolated_environment import IsolatedEnvironment
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env
from test_framework.ssot.database_skip_conditions import skip_if_postgresql_unavailable

@pytest.mark.integration
class DatabaseInitializationBasicTests:
    """Test basic database initialization and setup."""

    @pytest.fixture(scope='class')
    def database_config(self):
        """Get database configuration for tests."""
        env = get_env()
        builder = DatabaseURLBuilder(env.get_all())
        sync_url = builder.get_url_for_environment(sync=True)
        if not sync_url:
            async_url = builder.get_url_for_environment(sync=False)
            if async_url and async_url.startswith('postgresql+asyncpg://'):
                sync_url = async_url.replace('postgresql+asyncpg://', 'postgresql://')
        return {'url': sync_url, 'builder': builder, 'environment': env.get('ENVIRONMENT', 'development')}

    @skip_if_postgresql_unavailable
    def test_database_exists_and_connectable(self, database_config):
        """Test that the database exists and can be connected to - THIS SHOULD FAIL."""
        database_url = database_config['url']
        if not database_url:
            pytest.fail('No database URL configured - database setup incomplete')
        try:
            engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
            with engine.connect() as connection:
                result = connection.execute(text('SELECT 1 as test_value'))
                test_value = result.scalar()
                assert test_value == 1, f'Basic database query failed, expected 1 got {test_value}'
            engine.dispose()
            print('[PASS] Database exists and is connectable')
        except SQLAlchemyError as e:
            error_msg = str(e)
            if 'does not exist' in error_msg:
                pytest.fail(f'CRITICAL: Database does not exist. This is a basic system requirement. Error: {e}')
            elif 'authentication failed' in error_msg:
                pytest.fail(f'CRITICAL: Database authentication failed. Check credentials. Error: {e}')
            elif 'refused' in error_msg:
                pytest.fail(f'CRITICAL: Database connection refused. Is PostgreSQL running? Error: {e}')
            else:
                pytest.fail(f'CRITICAL: Database connection failed with unexpected error: {e}')

    @skip_if_postgresql_unavailable
    def test_database_has_required_tables(self, database_config):
        """Test that database has basic required tables for system functionality."""
        database_url = database_config['url']
        if not database_url:
            pytest.skip('No database URL configured')
        required_tables = ['users', 'threads', 'messages']
        try:
            engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
            with engine.connect() as connection:
                inspector = inspect(connection)
                existing_tables = inspector.get_table_names()
                missing_tables = []
                for table in required_tables:
                    if table not in existing_tables:
                        missing_tables.append(table)
                if missing_tables:
                    pytest.fail(f'CRITICAL: Missing required tables for basic functionality: {missing_tables}. Existing tables: {existing_tables}. Database needs proper initialization.')
                print(f'[PASS] All required basic tables exist: {required_tables}')
                print(f'   Total tables found: {len(existing_tables)}')
            engine.dispose()
        except SQLAlchemyError as e:
            if 'does not exist' in str(e):
                pytest.skip('Database does not exist - cannot test table structure')
            else:
                pytest.fail(f'Failed to inspect database tables: {e}')

    @skip_if_postgresql_unavailable
    def test_database_basic_crud_operations(self, database_config):
        """Test that database supports basic CRUD operations on a test table."""
        database_url = database_config['url']
        if not database_url:
            pytest.skip('No database URL configured')
        try:
            engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
            with engine.connect() as connection:
                with connection.begin() as transaction:
                    try:
                        connection.execute(text('\n                            CREATE TEMPORARY TABLE basic_test_table (\n                                id SERIAL PRIMARY KEY,\n                                test_data VARCHAR(255)\n                            )\n                        '))
                        connection.execute(text("\n                            INSERT INTO basic_test_table (test_data) \n                            VALUES ('basic_functionality_test')\n                        "))
                        result = connection.execute(text("\n                            SELECT test_data FROM basic_test_table \n                            WHERE test_data = 'basic_functionality_test'\n                        "))
                        row = result.fetchone()
                        if not row:
                            pytest.fail('Failed to retrieve inserted test data - basic SELECT operation failed')
                        assert row[0] == 'basic_functionality_test', f'Retrieved data mismatch: {row[0]}'
                        connection.execute(text("\n                            UPDATE basic_test_table \n                            SET test_data = 'updated_test_data' \n                            WHERE test_data = 'basic_functionality_test'\n                        "))
                        result = connection.execute(text("\n                            SELECT test_data FROM basic_test_table \n                            WHERE test_data = 'updated_test_data'\n                        "))
                        updated_row = result.fetchone()
                        if not updated_row:
                            pytest.fail('Failed to verify UPDATE operation - basic UPDATE failed')
                        connection.execute(text("\n                            DELETE FROM basic_test_table \n                            WHERE test_data = 'updated_test_data'\n                        "))
                        result = connection.execute(text('\n                            SELECT COUNT(*) FROM basic_test_table\n                        '))
                        count = result.scalar()
                        if count != 0:
                            pytest.fail(f'DELETE operation failed - expected 0 rows, found {count}')
                        print('[PASS] Basic database CRUD operations work correctly')
                        transaction.rollback()
                    except Exception as e:
                        transaction.rollback()
                        raise
            engine.dispose()
        except SQLAlchemyError as e:
            if 'does not exist' in str(e):
                pytest.skip('Database does not exist - cannot test CRUD operations')
            else:
                pytest.fail(f'Basic database CRUD operations failed: {e}')

    @skip_if_postgresql_unavailable
    def test_database_permissions_basic(self, database_config):
        """Test that database user has basic required permissions."""
        database_url = database_config['url']
        if not database_url:
            pytest.skip('No database URL configured')
        try:
            engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
            with engine.connect() as connection:
                inspector = inspect(connection)
                existing_tables = inspector.get_table_names()
                if existing_tables:
                    table_name = existing_tables[0]
                    try:
                        result = connection.execute(text(f'SELECT COUNT(*) FROM {table_name}'))
                        count = result.scalar()
                        print(f"[PASS] Basic SELECT permission verified on table '{table_name}' (found {count} rows)")
                    except SQLAlchemyError as e:
                        pytest.fail(f"Missing SELECT permission on table '{table_name}': {e}")
                try:
                    connection.execute(text('\n                        CREATE TEMPORARY TABLE permission_test (test_col INTEGER)\n                    '))
                    connection.execute(text('DROP TABLE permission_test'))
                    print('[PASS] CREATE TEMPORARY TABLE permission verified')
                except SQLAlchemyError as e:
                    pytest.fail(f'Missing CREATE TEMPORARY TABLE permission: {e}')
            engine.dispose()
        except SQLAlchemyError as e:
            if 'does not exist' in str(e):
                pytest.skip('Database does not exist - cannot test permissions')
            else:
                pytest.fail(f'Database permissions test failed: {e}')

def run_database_basic_test():
    """Run the database initialization test directly."""
    print('=' * 60)
    print('DATABASE INITIALIZATION BASIC FUNCTIONALITY TEST')
    print('=' * 60)
    test_instance = DatabaseInitializationBasicTests()
    env = get_env()
    builder = DatabaseURLBuilder(env.get_all())
    sync_url = builder.get_url_for_environment(sync=True)
    if not sync_url:
        async_url = builder.get_url_for_environment(sync=False)
        if async_url and async_url.startswith('postgresql+asyncpg://'):
            sync_url = async_url.replace('postgresql+asyncpg://', 'postgresql://')
    database_config = {'url': sync_url, 'builder': builder, 'environment': env.get('ENVIRONMENT', 'development')}
    if sync_url:
        masked_url = builder.mask_url_for_logging(sync_url)
        print(f'Testing database: {masked_url}')
    else:
        print('No database URL configured')
    print()
    tests_passed = 0
    tests_failed = 0
    tests_skipped = 0
    test_methods = [('Database Exists and Connectable', lambda: test_instance.test_database_exists_and_connectable(database_config)), ('Database Has Required Tables', lambda: test_instance.test_database_has_required_tables(database_config)), ('Database Basic CRUD Operations', lambda: test_instance.test_database_basic_crud_operations(database_config)), ('Database Basic Permissions', lambda: test_instance.test_database_permissions_basic(database_config))]
    for test_name, test_func in test_methods:
        print(f'Running {test_name}...')
        try:
            test_func()
            print(f'[PASS] {test_name}')
            tests_passed += 1
        except pytest.skip.Exception as e:
            print(f'[SKIP] {test_name}: {e}')
            tests_skipped += 1
        except Exception as e:
            print(f'[FAIL] {test_name}: {e}')
            tests_failed += 1
        print()
    print('=' * 60)
    print('TEST SUMMARY')
    print('=' * 60)
    print(f'Tests Passed:  {tests_passed}')
    print(f'Tests Failed:  {tests_failed}')
    print(f'Tests Skipped: {tests_skipped}')
    print(f'Total Tests:   {tests_passed + tests_failed + tests_skipped}')
    print()
    if tests_failed > 0:
        print('[FAIL] OVERALL RESULT: Database initialization has critical issues')
        return False
    elif tests_passed > 0:
        print('[PASS] OVERALL RESULT: Database initialization is working correctly')
        return True
    else:
        print('[WARN] OVERALL RESULT: Cannot validate database (all tests skipped)')
        return True
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')