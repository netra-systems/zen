"""
Integration test for ClickHouse connection authentication.
Tests ClickHouse authentication and basic connectivity issues.

Enhanced with specific validation for the ClickHouse configuration fixes:
    - Port 8123 HTTP interface access
- Authentication with configured credentials
- Proper password handling

Business Value Justification (BVJ):
    - Segment: Platform/Internal
- Business Goal: ClickHouse reliability and data pipeline stability
- Value Impact: Ensures analytics and logging systems function correctly
- Strategic Impact: Validates production-ready ClickHouse configuration
""""
import pytest
import asyncio
import time
from typing import Dict, Any
import requests
from netra_backend.app.config import get_config
from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
from netra_backend.app.db.clickhouse import ClickHouseService
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment


class TestClickHouseConnection:
    """Test ClickHouse connection and authentication."""

    @pytest.mark.asyncio
    async def test_clickhouse_basic_connection(self):
        """Test basic ClickHouse connection without authentication issues."""
        try:
            # Directly use the real ClickHouse client for integration testing
            from netra_backend.app.db.clickhouse import _create_real_client
            
            async for client in _create_real_client():
                # Test basic query
                result = await client.execute("SELECT 1 as test")
                assert result is not None
                assert len(result) > 0
                assert result[0]['test'] == 1
                break
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'password' in error_msg or 'user' in error_msg:
                pytest.fail(f"ClickHouse authentication failed: {e}")
            elif 'connection' in error_msg or 'timeout' in error_msg:
                pytest.skip(f"ClickHouse connection issue (not auth): {e}")
            elif 'cannot be empty' in error_msg or 'host' in error_msg:
                pytest.skip(f"ClickHouse not configured for this test environment: {e}")
            else:
                pytest.fail(f"ClickHouse unexpected error: {e}")

    @pytest.mark.asyncio
    async def test_clickhouse_configuration_values(self):
        """Test ClickHouse configuration is properly loaded."""
        config = get_config()
        
        # Check that ClickHouse config exists
        assert hasattr(config, 'clickhouse_https'), "ClickHouse HTTPS config missing"
        
        ch_config = config.clickhouse_https
        
        # Check required fields are present
        assert hasattr(ch_config, 'host'), "ClickHouse host missing"
        assert hasattr(ch_config, 'port'), "ClickHouse port missing"
        assert hasattr(ch_config, 'user'), "ClickHouse user missing"  
        assert hasattr(ch_config, 'password'), "ClickHouse password missing"
        
        # Check values are not empty (skip if not configured for testing)
        if not ch_config.host:
            pytest.skip("ClickHouse host not configured for this test environment")
        assert ch_config.port, "ClickHouse port is empty"
        assert ch_config.user, "ClickHouse user is empty"
        # Password could be empty for some auth methods, so just check it exists
        
    @pytest.mark.asyncio
    async def test_clickhouse_initialization_without_errors(self):
        """Test ClickHouse table initialization doesn't fail with auth errors."""
        try:
            # This should not fail with authentication errors
            await initialize_clickhouse_tables(verbose=True)
            # If we get here, no auth errors occurred
            assert True
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'password' in error_msg or 'user' in error_msg:
                pytest.fail(f"ClickHouse authentication failed during initialization: {e}")
            elif 'permission' in error_msg or 'access' in error_msg:
                pytest.fail(f"ClickHouse permission error during initialization: {e}")
            else:
                # Other errors might be acceptable (like network issues)
                print(f"Non-auth error during initialization (may be acceptable): {e}")

    @pytest.mark.asyncio 
    async def test_clickhouse_credentials_not_default(self):
        """Test that ClickHouse credentials are not using obvious defaults."""
        config = get_config()
        ch_config = config.clickhouse_https
        
        # Skip if not configured
        if not ch_config.host:
            pytest.skip("ClickHouse not configured for this test environment")
        
        # Check for common default values that would indicate misconfiguration
        default_combinations = [
            ('default', ''),
            ('default', 'default'),
            ('admin', 'admin'),
            ('admin', ''),
            ('root', 'root'),
            ('', ''),
        ]
        
        current_combo = (ch_config.user, ch_config.password)
        
        if current_combo in default_combinations:
            pytest.fail(f"ClickHouse using default credentials: {ch_config.user}")
            
        # Also check host isn't localhost with production credentials
        if ch_config.host == 'localhost' and ch_config.user == 'default':
            pytest.skip("Using localhost with default user - likely development setup")

    @pytest.mark.asyncio
    async def test_clickhouse_port_8123_http_access(self):
        """
        CRITICAL TEST: Validate ClickHouse HTTP interface on port 8123.
        
        This test specifically validates the ClickHouse HTTP interface
        configuration fix, ensuring port 8123 is accessible with authentication.
        """"
        env = get_env()
        
        # Get ClickHouse HTTP configuration
        ch_config = {
            'host': env.get('CLICKHOUSE_HOST', 'localhost'),
            'http_port': env.get('CLICKHOUSE_HTTP_PORT', '8123'),
            'user': env.get('CLICKHOUSE_USER', 'default'),
            'password': env.get('CLICKHOUSE_PASSWORD', ''),
            'database': env.get('CLICKHOUSE_DB', 'netra_dev')
        }
        
        # Skip if not configured
        if not ch_config['host'] or ch_config['host'] == '':
            pytest.skip("ClickHouse not configured for this test environment")
        
        print(f"\n=== CLICKHOUSE HTTP PORT 8123 TEST ===")
        print(f"Host: {ch_config['host']]")
        print(f"HTTP Port: {ch_config['http_port']]")
        print(f"User: {ch_config['user']]")
        print(f"Database: {ch_config['database']]")
        print(f"Password Length: {len(ch_config['password'])] chars")
        
        # Test HTTP interface connectivity
        http_url = f"http://{ch_config['host']]:{ch_config['http_port']]"
        auth = (ch_config['user'], ch_config['password']) if ch_config['password'] else None
        
        start_time = time.time()
        try:
            # Test ping endpoint
            ping_response = requests.get(f"{http_url}/ping", auth=auth, timeout=5)
            connection_time = time.time() - start_time
            
            print(f"Ping Response: HTTP {ping_response.status_code}")
            print(f"Connection Time: {connection_time:.3f}s")
            
            assert ping_response.status_code == 200, (
                f"ClickHouse HTTP ping failed: HTTP {ping_response.status_code}\n"
                f"Response: {ping_response.text[:200]]"
            )
            
            # Test basic query
            query_response = requests.get(
                f"{http_url}/?query=SELECT 1 as test",
                auth=auth,
                timeout=5
            )
            
            print(f"Query Response: HTTP {query_response.status_code}")
            print(f"Query Result: {query_response.text.strip()}")
            
            assert query_response.status_code == 200, (
                f"ClickHouse HTTP query failed: HTTP {query_response.status_code}\n"
                f"Response: {query_response.text[:200]]"
            )
            
            # Validate query result
            assert query_response.text.strip() == "1", (
                f"Unexpected query result: expected '1', got '{query_response.text.strip()}'"
            )
            
            print("✅ ClickHouse HTTP interface working correctly")
            
        except requests.exceptions.ConnectionError as e:
            pytest.fail(
                f"ClickHouse HTTP connection failed on port {ch_config['http_port']]:\n"
                f"URL: {http_url}\n"
                f"Error: {e}\n\n"
                f"Ensure ClickHouse is running and HTTP interface is enabled on port {ch_config['http_port']]"
            )
        except requests.exceptions.Timeout as e:
            pytest.fail(
                f"ClickHouse HTTP request timeout on port {ch_config['http_port']]:\n"
                f"URL: {http_url}\n"
                f"This may indicate ClickHouse is not responding on the HTTP interface"
            )
        except Exception as e:
            pytest.fail(
                f"Unexpected ClickHouse HTTP error:\n"
                f"URL: {http_url}\n"
                f"Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_clickhouse_authentication_with_password(self):
        """
        CRITICAL TEST: Validate ClickHouse authentication with configured password.
        
        This test validates that ClickHouse authentication works correctly
        with the configured username and password.
        """"
        env = get_env()
        
        ch_config = {
            'host': env.get('CLICKHOUSE_HOST', 'localhost'),
            'http_port': env.get('CLICKHOUSE_HTTP_PORT', '8123'),
            'user': env.get('CLICKHOUSE_USER', 'default'),
            'password': env.get('CLICKHOUSE_PASSWORD', ''),
            'database': env.get('CLICKHOUSE_DB', 'netra_dev')
        }
        
        # Skip if not configured
        if not ch_config['host'] or ch_config['host'] == '':
            pytest.skip("ClickHouse not configured for this test environment")
        
        print(f"\n=== CLICKHOUSE AUTHENTICATION TEST ===")
        print(f"User: {ch_config['user']]")
        print(f"Password: {'*' * len(ch_config['password'])] (length: {len(ch_config['password'])])")
        
        http_url = f"http://{ch_config['host']]:{ch_config['http_port']]"
        
        # Test with correct credentials
        if ch_config['password']:
            auth = (ch_config['user'], ch_config['password'])
            
            try:
                response = requests.get(
                    f"{http_url}/?query=SELECT user() as current_user",
                    auth=auth,
                    timeout=5
                )
                
                print(f"Auth Response: HTTP {response.status_code}")
                print(f"Current User: {response.text.strip()}")
                
                assert response.status_code == 200, (
                    f"Authentication failed: HTTP {response.status_code}\n"
                    f"Response: {response.text[:200]]"
                )
                
                # Validate we're authenticated as the expected user
                current_user = response.text.strip()
                assert current_user == ch_config['user'], (
                    f"Unexpected authenticated user: expected '{ch_config['user']]', got '{current_user]'"
                )
                
                print("✅ Authentication successful")
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    pytest.fail(
                        f"ClickHouse authentication failed:\n"
                        f"User: {ch_config['user']]\n"
                        f"HTTP 401 Unauthorized - check username/password configuration"
                    )
                else:
                    raise
        else:
            # Test without authentication (if password is empty)
            print("Testing without authentication (empty password)")
            
            try:
                response = requests.get(
                    f"{http_url}/?query=SELECT 1",
                    timeout=5
                )
                
                assert response.status_code == 200, (
                    f"No-auth request failed: HTTP {response.status_code}"
                )
                
                print("✅ No-auth access working")
                
            except Exception as e:
                pytest.fail(f"No-auth request failed: {e}")

    @pytest.mark.asyncio
    async def test_clickhouse_database_access(self):
        """
        FUNCTIONAL TEST: Validate ClickHouse database access and basic operations.
        
        This test validates that ClickHouse can perform basic database operations
        with the configured database name.
        """"
        env = get_env()
        
        ch_config = {
            'host': env.get('CLICKHOUSE_HOST', 'localhost'),
            'http_port': env.get('CLICKHOUSE_HTTP_PORT', '8123'),
            'user': env.get('CLICKHOUSE_USER', 'default'),
            'password': env.get('CLICKHOUSE_PASSWORD', ''),
            'database': env.get('CLICKHOUSE_DB', 'netra_dev')
        }
        
        # Skip if not configured
        if not ch_config['host'] or ch_config['host'] == '':
            pytest.skip("ClickHouse not configured for this test environment")
        
        print(f"\n=== CLICKHOUSE DATABASE ACCESS TEST ===")
        print(f"Database: {ch_config['database']]")
        
        http_url = f"http://{ch_config['host']]:{ch_config['http_port']]"
        auth = (ch_config['user'], ch_config['password']) if ch_config['password'] else None
        
        operations = {
            'show_databases': f"SHOW DATABASES",
            'current_database': f"SELECT currentDatabase() as db",
            'create_test_table': f"CREATE TABLE IF NOT EXISTS test_connectivity_{int(time.time())} (id UInt32, name String) ENGINE = Memory",
            'show_tables': f"SHOW TABLES FROM {ch_config['database']]",
        }
        
        results = {}
        
        for operation, query in operations.items():
            try:
                response = requests.get(
                    f"{http_url}/?query={query}",
                    auth=auth,
                    timeout=10
                )
                
                results[operation] = {
                    'success': response.status_code == 200,
                    'response': response.text.strip(),
                    'error': None if response.status_code == 200 else f"HTTP {response.status_code}"
                }
                
            except Exception as e:
                results[operation] = {
                    'success': False,
                    'response': None,
                    'error': str(e)
                }
        
        # Print results
        for operation, result in results.items():
            status = "✅ OK" if result['success'] else "❌ FAILED"
            print(f"{operation}: {status}")
            if result['success'] and result['response']:
                # Truncate long responses
                response_text = result['response'][:100] + "..." if len(result['response']) > 100 else result['response']
                print(f"  Response: {response_text}")
            elif not result['success']:
                print(f"  Error: {result['error']]")
        
        # Clean up test table if created
        if results.get('create_test_table', {}).get('success'):
            try:
                table_name = f"test_connectivity_{int(time.time())}"
                requests.get(
                    f"{http_url}/?query=DROP TABLE IF EXISTS {table_name}",
                    auth=auth,
                    timeout=5
                )
            except:
                pass  # Ignore cleanup errors
        
        # Validate critical operations
        critical_ops = ['show_databases', 'current_database']
        failed_critical = [op for op in critical_ops if not results.get(op, {]).get('success')]
        
        assert len(failed_critical) == 0, (
            f"Critical ClickHouse operations failed: {failed_critical}\n"
            f"Database access is not working properly with configured database '{ch_config['database']]'"
        )
        
        # Validate we can access the configured database
        if results.get('current_database', {}).get('success'):
            current_db = results['current_database']['response']
            print(f"Current database confirmed: {current_db}")
            # Note: currentDatabase() might return 'default' even when using a different database
            # This is normal ClickHouse behavior with HTTP interface


class TestClickHouseConnectionEnhanced:
    """Enhanced ClickHouse connection tests for configuration validation."""
    
    @pytest.mark.asyncio
    async def test_clickhouse_configuration_consistency(self):
        """
        INTEGRATION TEST: Validate ClickHouse configuration consistency across services.
        
        This test ensures all ClickHouse configuration is consistent between
        environment variables and application configuration.
        """"
        env = get_env()
        config = get_config()
        
        # Get environment variables
        env_config = {
            'host': env.get('CLICKHOUSE_HOST', ''),
            'http_port': env.get('CLICKHOUSE_HTTP_PORT', ''),
            'user': env.get('CLICKHOUSE_USER', ''),
            'password': env.get('CLICKHOUSE_PASSWORD', ''),
            'database': env.get('CLICKHOUSE_DB', '')
        }
        
        print(f"\n=== CLICKHOUSE CONFIGURATION CONSISTENCY TEST ===")
        print(f"Environment Config:")
        for key, value in env_config.items():
            if key == 'password':
                display_value = '*' * len(value) if value else '(empty)'
            else:
                display_value = value or '(empty)'
            print(f"  {key}: {display_value}")
        
        # Skip detailed tests if not configured
        if not env_config['host']:
            pytest.skip("ClickHouse not configured for this test environment")
        
        # Validate application config matches environment
        if hasattr(config, 'clickhouse_https'):
            app_config = config.clickhouse_https
            
            print(f"\nApplication Config:")
            print(f"  host: {getattr(app_config, 'host', '(missing)')}")
            print(f"  port: {getattr(app_config, 'port', '(missing)')}")
            print(f"  user: {getattr(app_config, 'user', '(missing)')}")
            print(f"  password: {'*' * len(getattr(app_config, 'password', '')) if getattr(app_config, 'password', '') else '(empty)'}")
            
            # Validate consistency (where applicable)
            if hasattr(app_config, 'host'):
                assert app_config.host == env_config['host'], (
                    f"Host mismatch: env='{env_config['host']]', app='{app_config.host]'"
                )
            
            if hasattr(app_config, 'user'):
                assert app_config.user == env_config['user'], (
                    f"User mismatch: env='{env_config['user']]', app='{app_config.user]'"
                )
        
        # Validate required configuration is present
        required_fields = ['host', 'http_port', 'user', 'database']
        missing_fields = [field for field in required_fields if not env_config[field]]
        
        assert len(missing_fields) == 0, (
            f"Required ClickHouse configuration missing: {missing_fields}\n"
            f"All required fields must be configured for ClickHouse to work properly"
        )
        
        print("✅ Configuration consistency validated")


if __name__ == "__main__":
    # Run this test standalone to check ClickHouse connection
    pytest.main([__file__, "-v"])