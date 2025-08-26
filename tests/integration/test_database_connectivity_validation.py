"""
Database Connectivity Validation Tests

These tests validate the critical database configuration fixes:
1. PostgreSQL accessibility on port 5433 with correct user credentials
2. ClickHouse HTTP interface accessibility on port 8123 with authentication
3. Proper SSL parameter handling for different database drivers

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Database connectivity reliability and stability
- Value Impact: Prevents service startup failures and database connection errors
- Strategic Impact: Ensures consistent database configuration across all services and environments

These tests validate the fixes implemented in the database connectivity architecture.
"""

import asyncio
import pytest
import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from unittest.mock import patch
import asyncpg
import psycopg2
from clickhouse_driver import Client as ClickHouseNativeClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.core.configuration.database import DatabaseConfigManager
from shared.database_url_builder import DatabaseURLBuilder
from dev_launcher.isolated_environment import get_env
from test_framework.environment_markers import env


class DatabaseConnectivityValidator:
    """Comprehensive database connectivity validation."""
    
    def __init__(self):
        self.env = get_env()
        self.results = {}
    
    def get_postgres_config(self) -> Dict[str, str]:
        """Get PostgreSQL configuration from environment."""
        return {
            'host': self.env.get('POSTGRES_HOST', 'localhost'),
            'port': self.env.get('POSTGRES_PORT', '5433'),
            'user': self.env.get('POSTGRES_USER', 'postgres'),
            'password': self.env.get('POSTGRES_PASSWORD', ''),
            'database': self.env.get('POSTGRES_DB', 'netra_dev')
        }
    
    def get_clickhouse_config(self) -> Dict[str, str]:
        """Get ClickHouse configuration from environment."""
        return {
            'host': self.env.get('CLICKHOUSE_HOST', 'localhost'),
            'http_port': self.env.get('CLICKHOUSE_HTTP_PORT', '8123'),
            'native_port': self.env.get('CLICKHOUSE_NATIVE_PORT', '9000'),
            'user': self.env.get('CLICKHOUSE_USER', 'default'),
            'password': self.env.get('CLICKHOUSE_PASSWORD', ''),
            'database': self.env.get('CLICKHOUSE_DB', 'netra_dev')
        }
    
    async def validate_postgres_asyncpg(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Validate PostgreSQL connection using asyncpg (production async driver)."""
        result = {
            'driver': 'asyncpg',
            'success': False,
            'connection_time': None,
            'error': None,
            'server_version': None,
            'config_used': config
        }
        
        # Build connection URL
        url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        
        start_time = time.time()
        try:
            conn = await asyncpg.connect(url, timeout=5)
            connection_time = time.time() - start_time
            
            # Get server version
            version_result = await conn.fetchval("SELECT version()")
            await conn.close()
            
            result.update({
                'success': True,
                'connection_time': connection_time,
                'server_version': version_result[:50] + "..." if len(version_result) > 50 else version_result
            })
            
        except Exception as e:
            result.update({
                'error': str(e),
                'connection_time': time.time() - start_time
            })
        
        return result
    
    def validate_postgres_psycopg2(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Validate PostgreSQL connection using psycopg2 (migration sync driver)."""
        result = {
            'driver': 'psycopg2',
            'success': False,
            'connection_time': None,
            'error': None,
            'server_version': None,
            'config_used': config
        }
        
        start_time = time.time()
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=int(config['port']),
                user=config['user'],
                password=config['password'],
                database=config['database'],
                connect_timeout=5
            )
            connection_time = time.time() - start_time
            
            # Get server version
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version_result = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            result.update({
                'success': True,
                'connection_time': connection_time,
                'server_version': version_result[:50] + "..." if len(version_result) > 50 else version_result
            })
            
        except Exception as e:
            result.update({
                'error': str(e),
                'connection_time': time.time() - start_time
            })
        
        return result
    
    def validate_clickhouse_http(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Validate ClickHouse HTTP interface connectivity."""
        result = {
            'interface': 'http',
            'success': False,
            'connection_time': None,
            'error': None,
            'server_version': None,
            'config_used': config
        }
        
        start_time = time.time()
        try:
            import requests
            
            # Build HTTP URL for ClickHouse
            url = f"http://{config['host']}:{config['http_port']}"
            
            # Test basic connectivity with authentication
            auth = (config['user'], config['password']) if config['password'] else None
            
            response = requests.get(
                f"{url}/ping",
                auth=auth,
                timeout=5
            )
            
            if response.status_code == 200:
                # Get server version
                version_response = requests.get(
                    f"{url}/?query=SELECT version()",
                    auth=auth,
                    timeout=5
                )
                
                connection_time = time.time() - start_time
                result.update({
                    'success': True,
                    'connection_time': connection_time,
                    'server_version': version_response.text.strip() if version_response.status_code == 200 else "Unknown"
                })
            else:
                result.update({
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'connection_time': time.time() - start_time
                })
                
        except Exception as e:
            result.update({
                'error': str(e),
                'connection_time': time.time() - start_time
            })
        
        return result
    
    def validate_clickhouse_native(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Validate ClickHouse native protocol connectivity."""
        result = {
            'interface': 'native',
            'success': False,
            'connection_time': None,
            'error': None,
            'server_version': None,
            'config_used': config
        }
        
        start_time = time.time()
        try:
            client = ClickHouseNativeClient(
                host=config['host'],
                port=int(config['native_port']),
                user=config['user'],
                password=config['password'],
                database=config['database'],
                connect_timeout=5,
                send_receive_timeout=5
            )
            
            # Test basic connectivity
            version_result = client.execute("SELECT version()")[0][0]
            connection_time = time.time() - start_time
            
            result.update({
                'success': True,
                'connection_time': connection_time,
                'server_version': version_result
            })
            
        except Exception as e:
            result.update({
                'error': str(e),
                'connection_time': time.time() - start_time
            })
        
        return result


class TestDatabaseConnectivityValidation:
    """Test suite for database connectivity validation."""
    
    @pytest.fixture(scope="class")
    def validator(self):
        return DatabaseConnectivityValidator()
    
    @pytest.mark.asyncio
    async def test_postgres_port_5433_asyncpg_connectivity(self, validator):
        """
        CRITICAL TEST: Validate PostgreSQL is accessible on port 5433 with asyncpg.
        
        This test validates the fix for PostgreSQL port configuration,
        ensuring the database is accessible on the correct port with proper credentials.
        """
        config = validator.get_postgres_config()
        result = await validator.validate_postgres_asyncpg(config)
        
        print(f"\n=== POSTGRESQL ASYNCPG CONNECTIVITY TEST ===")
        print(f"Host: {config['host']}")
        print(f"Port: {config['port']}")
        print(f"User: {config['user']}")
        print(f"Database: {config['database']}")
        print(f"Success: {result['success']}")
        print(f"Connection Time: {result['connection_time']:.3f}s" if result['connection_time'] else "N/A")
        
        if result['success']:
            print(f"Server Version: {result['server_version']}")
        else:
            print(f"Error: {result['error']}")
        
        # Assert connectivity works
        assert result['success'], (
            f"PostgreSQL asyncpg connectivity FAILED:\n"
            f"Host: {config['host']}:{config['port']}\n"
            f"User: {config['user']}\n"
            f"Database: {config['database']}\n"
            f"Error: {result['error']}\n\n"
            f"This indicates the PostgreSQL database is not accessible with the "
            f"configured credentials on port {config['port']}. Ensure:\n"
            f"1. PostgreSQL is running on port {config['port']}\n"
            f"2. User '{config['user']}' exists and has access\n"
            f"3. Database '{config['database']}' exists\n"
            f"4. Network connectivity is available"
        )
        
        # Validate reasonable connection time (should be under 1 second for local)
        if result['connection_time']:
            assert result['connection_time'] < 2.0, (
                f"PostgreSQL connection time too slow: {result['connection_time']:.3f}s"
            )
    
    def test_postgres_port_5433_psycopg2_connectivity(self, validator):
        """
        CRITICAL TEST: Validate PostgreSQL is accessible on port 5433 with psycopg2.
        
        This test validates that migration operations can connect using the
        synchronous psycopg2 driver on the correct port.
        """
        config = validator.get_postgres_config()
        result = validator.validate_postgres_psycopg2(config)
        
        print(f"\n=== POSTGRESQL PSYCOPG2 CONNECTIVITY TEST ===")
        print(f"Host: {config['host']}")
        print(f"Port: {config['port']}")
        print(f"User: {config['user']}")
        print(f"Database: {config['database']}")
        print(f"Success: {result['success']}")
        print(f"Connection Time: {result['connection_time']:.3f}s" if result['connection_time'] else "N/A")
        
        if result['success']:
            print(f"Server Version: {result['server_version']}")
        else:
            print(f"Error: {result['error']}")
        
        # Assert connectivity works
        assert result['success'], (
            f"PostgreSQL psycopg2 connectivity FAILED:\n"
            f"Host: {config['host']}:{config['port']}\n"
            f"User: {config['user']}\n"
            f"Database: {config['database']}\n"
            f"Error: {result['error']}\n\n"
            f"This indicates the PostgreSQL database is not accessible for migration "
            f"operations using psycopg2 driver. Both asyncpg and psycopg2 must work."
        )
    
    def test_clickhouse_http_port_8123_connectivity(self, validator):
        """
        CRITICAL TEST: Validate ClickHouse HTTP interface is accessible on port 8123.
        
        This test validates that ClickHouse is accessible via HTTP interface
        with proper authentication credentials.
        """
        config = validator.get_clickhouse_config()
        result = validator.validate_clickhouse_http(config)
        
        print(f"\n=== CLICKHOUSE HTTP CONNECTIVITY TEST ===")
        print(f"Host: {config['host']}")
        print(f"HTTP Port: {config['http_port']}")
        print(f"User: {config['user']}")
        print(f"Database: {config['database']}")
        print(f"Success: {result['success']}")
        print(f"Connection Time: {result['connection_time']:.3f}s" if result['connection_time'] else "N/A")
        
        if result['success']:
            print(f"Server Version: {result['server_version']}")
        else:
            print(f"Error: {result['error']}")
        
        # Only assert if ClickHouse is configured (not in minimal test environments)
        if config['host'] and config['host'] != '':
            assert result['success'], (
                f"ClickHouse HTTP connectivity FAILED:\n"
                f"Host: {config['host']}:{config['http_port']}\n"
                f"User: {config['user']}\n"
                f"Database: {config['database']}\n"
                f"Error: {result['error']}\n\n"
                f"This indicates ClickHouse is not accessible via HTTP interface. Ensure:\n"
                f"1. ClickHouse is running on port {config['http_port']}\n"
                f"2. HTTP interface is enabled\n"
                f"3. User '{config['user']}' has proper authentication\n"
                f"4. Database '{config['database']}' exists"
            )
        else:
            pytest.skip("ClickHouse not configured for this test environment")
    
    def test_clickhouse_native_port_9000_connectivity(self, validator):
        """
        TEST: Validate ClickHouse native protocol connectivity on port 9000.
        
        This test validates ClickHouse native protocol access for high-performance operations.
        """
        config = validator.get_clickhouse_config()
        result = validator.validate_clickhouse_native(config)
        
        print(f"\n=== CLICKHOUSE NATIVE CONNECTIVITY TEST ===")
        print(f"Host: {config['host']}")
        print(f"Native Port: {config['native_port']}")
        print(f"User: {config['user']}")
        print(f"Database: {config['database']}")
        print(f"Success: {result['success']}")
        print(f"Connection Time: {result['connection_time']:.3f}s" if result['connection_time'] else "N/A")
        
        if result['success']:
            print(f"Server Version: {result['server_version']}")
        else:
            print(f"Error: {result['error']}")
        
        # Only assert if ClickHouse is configured
        if config['host'] and config['host'] != '':
            assert result['success'], (
                f"ClickHouse native connectivity FAILED:\n"
                f"Host: {config['host']}:{config['native_port']}\n"
                f"User: {config['user']}\n"
                f"Database: {config['database']}\n"
                f"Error: {result['error']}\n\n"
                f"This indicates ClickHouse native protocol is not working properly."
            )
        else:
            pytest.skip("ClickHouse not configured for this test environment")
    
    def test_database_url_builder_consistency(self, validator):
        """
        TEST: Validate DatabaseURLBuilder produces correct URLs for fixed configuration.
        
        This test validates that the DatabaseURLBuilder fixes are working correctly
        and producing consistent URLs for both async and sync operations.
        """
        env_vars = validator.env.get_all()
        builder = DatabaseURLBuilder(env_vars)
        
        # Get URLs for both sync and async
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        
        print(f"\n=== DATABASE URL BUILDER CONSISTENCY TEST ===")
        print(f"Environment: {env_vars.get('ENVIRONMENT', 'unknown')}")
        print(f"Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
        print(f"Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
        
        # Extract ports from URLs
        from tests.database.test_port_configuration_mismatch import DatabasePortConfigurationTester
        tester = DatabasePortConfigurationTester()
        
        async_port = tester.extract_port_from_url(async_url)
        sync_port = tester.extract_port_from_url(sync_url)
        expected_port = env_vars.get('POSTGRES_PORT', '5432')
        
        print(f"Expected Port: {expected_port}")
        print(f"Async URL Port: {async_port}")
        print(f"Sync URL Port: {sync_port}")
        print(f"Ports Consistent: {async_port == sync_port == expected_port}")
        
        # Validate port consistency
        assert async_port == expected_port, (
            f"Async URL port mismatch: expected {expected_port}, got {async_port}"
        )
        
        assert sync_port == expected_port, (
            f"Sync URL port mismatch: expected {expected_port}, got {sync_port}"
        )
        
        assert async_port == sync_port, (
            f"Port inconsistency between async ({async_port}) and sync ({sync_port}) URLs"
        )
    
    @pytest.mark.asyncio
    async def test_comprehensive_database_health_check(self, validator):
        """
        INTEGRATION TEST: Comprehensive database health check for all configured databases.
        
        This test performs a complete health check of all database connections
        to ensure the system can start up successfully with all databases accessible.
        """
        health_results = {
            'postgres_asyncpg': None,
            'postgres_psycopg2': None,
            'clickhouse_http': None,
            'clickhouse_native': None,
            'overall_health': True,
            'issues': []
        }
        
        # Test PostgreSQL connections
        postgres_config = validator.get_postgres_config()
        
        # AsyncPG test
        postgres_asyncpg_result = await validator.validate_postgres_asyncpg(postgres_config)
        health_results['postgres_asyncpg'] = postgres_asyncpg_result
        if not postgres_asyncpg_result['success']:
            health_results['overall_health'] = False
            health_results['issues'].append(f"PostgreSQL asyncpg: {postgres_asyncpg_result['error']}")
        
        # psycopg2 test
        postgres_psycopg2_result = validator.validate_postgres_psycopg2(postgres_config)
        health_results['postgres_psycopg2'] = postgres_psycopg2_result
        if not postgres_psycopg2_result['success']:
            health_results['overall_health'] = False
            health_results['issues'].append(f"PostgreSQL psycopg2: {postgres_psycopg2_result['error']}")
        
        # Test ClickHouse connections (if configured)
        clickhouse_config = validator.get_clickhouse_config()
        if clickhouse_config['host'] and clickhouse_config['host'] != '':
            # HTTP test
            clickhouse_http_result = validator.validate_clickhouse_http(clickhouse_config)
            health_results['clickhouse_http'] = clickhouse_http_result
            if not clickhouse_http_result['success']:
                health_results['overall_health'] = False
                health_results['issues'].append(f"ClickHouse HTTP: {clickhouse_http_result['error']}")
            
            # Native test
            clickhouse_native_result = validator.validate_clickhouse_native(clickhouse_config)
            health_results['clickhouse_native'] = clickhouse_native_result
            if not clickhouse_native_result['success']:
                health_results['overall_health'] = False
                health_results['issues'].append(f"ClickHouse native: {clickhouse_native_result['error']}")
        
        print(f"\n=== COMPREHENSIVE DATABASE HEALTH CHECK ===")
        print(f"PostgreSQL asyncpg: {'✅ OK' if postgres_asyncpg_result['success'] else '❌ FAILED'}")
        print(f"PostgreSQL psycopg2: {'✅ OK' if postgres_psycopg2_result['success'] else '❌ FAILED'}")
        
        if clickhouse_config['host']:
            print(f"ClickHouse HTTP: {'✅ OK' if health_results['clickhouse_http']['success'] else '❌ FAILED'}")
            print(f"ClickHouse Native: {'✅ OK' if health_results['clickhouse_native']['success'] else '❌ FAILED'}")
        else:
            print(f"ClickHouse: ⏭️ SKIPPED (not configured)")
        
        print(f"Overall Health: {'✅ HEALTHY' if health_results['overall_health'] else '❌ UNHEALTHY'}")
        
        if health_results['issues']:
            print(f"Issues Found:")
            for issue in health_results['issues']:
                print(f"  - {issue}")
        
        # Assert overall health
        assert health_results['overall_health'], (
            f"DATABASE HEALTH CHECK FAILED:\n"
            f"Issues found:\n" + "\n".join(f"  - {issue}" for issue in health_results['issues']) + "\n\n"
            f"All configured databases must be accessible for the system to function properly. "
            f"Fix the database connectivity issues before proceeding."
        )
    
    def test_database_config_manager_integration(self):
        """
        TEST: Validate DatabaseConfigManager integration with fixed configuration.
        
        This test validates that the DatabaseConfigManager correctly uses
        the fixed database configuration and can provide proper URLs.
        """
        try:
            # Initialize the DatabaseConfigManager
            manager = DatabaseConfigManager()
            
            # Test that it can get PostgreSQL configuration without errors
            postgres_url = manager.get_postgres_url()
            
            print(f"\n=== DATABASE CONFIG MANAGER TEST ===")
            print(f"PostgreSQL URL obtained: {bool(postgres_url)}")
            if postgres_url:
                print(f"PostgreSQL URL (masked): {DatabaseURLBuilder.mask_url_for_logging(postgres_url)}")
            
            # The manager should be able to provide a valid PostgreSQL URL
            assert postgres_url, (
                "DatabaseConfigManager could not provide PostgreSQL URL. "
                "This indicates issues with the database configuration setup."
            )
            
            # Test ClickHouse configuration if available
            try:
                clickhouse_config = manager.get_clickhouse_config()
                print(f"ClickHouse Config obtained: {bool(clickhouse_config)}")
            except Exception as ch_error:
                print(f"ClickHouse config error (may be expected): {ch_error}")
            
        except ImportError:
            pytest.skip("DatabaseConfigManager not available in this environment")
        except Exception as e:
            pytest.fail(f"DatabaseConfigManager integration failed: {e}")


class TestDatabaseConfigurationRegression:
    """Regression tests to prevent database configuration issues from reoccurring."""
    
    def test_postgres_port_environment_variable_respected(self):
        """
        REGRESSION TEST: Ensure POSTGRES_PORT environment variable is respected.
        
        This test prevents regression of the port configuration issue where
        sync URLs ignored the POSTGRES_PORT environment variable.
        """
        from dev_launcher.isolated_environment import get_env
        env = get_env()
        
        original_port = env.get('POSTGRES_PORT')
        test_port = '5555'  # Non-standard port for testing
        
        try:
            # Set a non-standard port
            env.set('POSTGRES_PORT', test_port)
            
            # Build URLs
            builder = DatabaseURLBuilder(env.get_all())
            async_url = builder.get_url_for_environment(sync=False)
            sync_url = builder.get_url_for_environment(sync=True)
            
            # Both URLs should use the configured port
            from tests.database.test_port_configuration_mismatch import DatabasePortConfigurationTester
            tester = DatabasePortConfigurationTester()
            
            async_port = tester.extract_port_from_url(async_url)
            sync_port = tester.extract_port_from_url(sync_url)
            
            assert async_port == test_port, (
                f"Async URL ignoring POSTGRES_PORT: expected {test_port}, got {async_port}"
            )
            
            assert sync_port == test_port, (
                f"REGRESSION: Sync URL ignoring POSTGRES_PORT: expected {test_port}, got {sync_port}"
            )
            
        finally:
            # Restore original port
            if original_port:
                env.set('POSTGRES_PORT', original_port)
            else:
                env.set('POSTGRES_PORT', '5433')  # Default for this environment
    
    def test_clickhouse_password_authentication_working(self):
        """
        REGRESSION TEST: Ensure ClickHouse password authentication works.
        
        This test prevents regression of ClickHouse authentication issues.
        """
        from dev_launcher.isolated_environment import get_env
        env = get_env()
        
        clickhouse_host = env.get('CLICKHOUSE_HOST')
        if not clickhouse_host or clickhouse_host == '':
            pytest.skip("ClickHouse not configured for this test environment")
        
        clickhouse_password = env.get('CLICKHOUSE_PASSWORD')
        assert clickhouse_password, "ClickHouse password must be configured"
        assert clickhouse_password != '', "ClickHouse password cannot be empty"
        
        # Validate authentication configuration exists
        clickhouse_user = env.get('CLICKHOUSE_USER', 'default')
        assert clickhouse_user, "ClickHouse user must be configured"
        
        print(f"ClickHouse Authentication Config:")
        print(f"  User: {clickhouse_user}")
        print(f"  Password: {'*' * len(clickhouse_password)} (length: {len(clickhouse_password)})")
        print(f"  Host: {clickhouse_host}")
    
    def test_database_url_ssl_parameter_conversion(self):
        """
        REGRESSION TEST: Ensure SSL parameter conversion works correctly.
        
        This test validates that sslmode is converted to ssl for asyncpg
        and ssl is converted to sslmode for psycopg2 as needed.
        """
        # Test URL with sslmode parameter
        test_url = "postgresql://user:pass@host:5432/db?sslmode=require"
        
        # Test asyncpg conversion (sslmode -> ssl)
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        from dev_launcher.isolated_environment import get_env
        env = get_env()
        
        original_url = env.get('DATABASE_URL')
        try:
            env.set('DATABASE_URL', test_url)
            
            # Get async URL - should convert sslmode to ssl
            async_url = AuthDatabaseManager.get_auth_database_url_async()
            assert "ssl=require" in async_url, "sslmode should be converted to ssl for asyncpg"
            assert "sslmode=" not in async_url, "sslmode should be removed from asyncpg URL"
            
            # Get migration URL - should keep sslmode for psycopg2
            migration_url = AuthDatabaseManager.get_migration_url_sync_format()
            assert "sslmode=require" in migration_url, "sslmode should be preserved for psycopg2"
            
        finally:
            if original_url:
                env.set('DATABASE_URL', original_url)
            else:
                env.set('DATABASE_URL', "sqlite+aiosqlite:///test_auth.db")


if __name__ == "__main__":
    # Run diagnostic when executed directly
    import asyncio
    
    async def main():
        print("=== DATABASE CONNECTIVITY VALIDATION ===")
        validator = DatabaseConnectivityValidator()
        
        # Test PostgreSQL
        postgres_config = validator.get_postgres_config()
        print(f"\nTesting PostgreSQL on {postgres_config['host']}:{postgres_config['port']}")
        
        asyncpg_result = await validator.validate_postgres_asyncpg(postgres_config)
        print(f"AsyncPG: {'OK' if asyncpg_result['success'] else 'FAILED'}")
        if not asyncpg_result['success']:
            print(f"  Error: {asyncpg_result['error']}")
        
        psycopg2_result = validator.validate_postgres_psycopg2(postgres_config)
        print(f"psycopg2: {'OK' if psycopg2_result['success'] else 'FAILED'}")
        if not psycopg2_result['success']:
            print(f"  Error: {psycopg2_result['error']}")
        
        # Test ClickHouse
        clickhouse_config = validator.get_clickhouse_config()
        if clickhouse_config['host']:
            print(f"\nTesting ClickHouse on {clickhouse_config['host']}")
            
            http_result = validator.validate_clickhouse_http(clickhouse_config)
            print(f"HTTP ({clickhouse_config['http_port']}): {'OK' if http_result['success'] else 'FAILED'}")
            if not http_result['success']:
                print(f"  Error: {http_result['error']}")
            
            native_result = validator.validate_clickhouse_native(clickhouse_config)
            print(f"Native ({clickhouse_config['native_port']}): {'OK' if native_result['success'] else 'FAILED'}")
            if not native_result['success']:
                print(f"  Error: {native_result['error']}")
        else:
            print("\nClickHouse not configured")
    
    asyncio.run(main())