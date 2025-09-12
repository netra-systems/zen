"""
Test suite for database validation resilience in dev launcher.

Tests that database connection validation correctly handles URLs and service names,
preventing regression of the issue where service names were passed as URLs.
"""

import asyncio
import pytest
from pathlib import Path
from typing import Dict, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig
from dev_launcher.network_resilience import NetworkResilientClient, RetryPolicy


class TestDatabaseValidationResilience:
    """Test cases for database validation with network resilience."""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables for testing."""
        return {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb',
            'REDIS_URL': 'redis://localhost:6379/0',
            'CLICKHOUSE_URL': 'clickhouse://localhost:9000/default',
            'ENVIRONMENT': 'development'
        }
    
    @pytest.fixture
    def mock_launcher(self, tmp_path, mock_env):
        """Create a mock dev launcher instance."""
        # Create required directories for config validation
        (tmp_path / "netra_backend" / "app").mkdir(parents=True, exist_ok=True)
        (tmp_path / "frontend").mkdir(parents=True, exist_ok=True)
        
        with patch('dev_launcher.launcher.get_env') as mock_get_env:
            mock_get_env.return_value = mock_env
            config = LauncherConfig(project_root=tmp_path)
            launcher = DevLauncher(config)
            launcher.network_client = NetworkResilientClient(use_emoji=False)
            return launcher
    
    @pytest.mark.asyncio
    async def test_validate_databases_with_resilience_uses_urls_not_names(self, mock_launcher, mock_env):
        """Test that _validate_databases_with_resilience passes URLs, not service names."""
        # Mock the resilient_database_check method to capture arguments
        calls_made = []
        
        async def mock_check(database_url: str, db_type: str, retry_policy):
            calls_made.append({
                'database_url': database_url,
                'db_type': db_type
            })
            # Simulate successful connection
            return True, None
        
        mock_launcher.network_client.resilient_database_check = mock_check
        
        # Run validation
        result = await mock_launcher._validate_databases_with_resilience()
        
        # Verify correct URLs were passed, not service names
        assert len(calls_made) == 3
        
        # Check PostgreSQL call
        postgres_call = next((c for c in calls_made if c['db_type'] == 'postgresql'), None)
        assert postgres_call is not None
        assert postgres_call['database_url'] == mock_env['DATABASE_URL']
        assert 'postgres' not in postgres_call['database_url']  # Should not be just 'postgres'
        
        # Check Redis call
        redis_call = next((c for c in calls_made if c['db_type'] == 'redis'), None)
        assert redis_call is not None
        assert redis_call['database_url'] == mock_env['REDIS_URL']
        assert redis_call['database_url'] != 'redis'  # Should not be just 'redis'
        
        # Check ClickHouse call
        clickhouse_call = next((c for c in calls_made if c['db_type'] == 'clickhouse'), None)
        assert clickhouse_call is not None
        assert clickhouse_call['database_url'] == mock_env['CLICKHOUSE_URL']
        assert clickhouse_call['database_url'] != 'clickhouse'  # Should not be just 'clickhouse'
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_skips_unconfigured_databases(self, mock_launcher):
        """Test that validation skips databases without configured URLs."""
        # Set up environment with only PostgreSQL configured
        with patch('dev_launcher.launcher.get_env') as mock_get_env:
            mock_get_env.return_value = {
                'DATABASE_URL': 'postgresql://localhost:5432/testdb',
                # No REDIS_URL or CLICKHOUSE_URL
            }
            
            calls_made = []
            
            async def mock_check(database_url: str, db_type: str, retry_policy):
                calls_made.append(db_type)
                return True, None
            
            mock_launcher.network_client.resilient_database_check = mock_check
            
            result = await mock_launcher._validate_databases_with_resilience()
            
            # Only PostgreSQL should be checked
            assert len(calls_made) == 1
            assert calls_made[0] == 'postgresql'
            assert result is True
    
    @pytest.mark.asyncio
    async def test_skips_mock_databases(self, mock_launcher):
        """Test that validation skips databases in mock mode."""
        # Set up environment with mock databases
        with patch('dev_launcher.launcher.get_env') as mock_get_env:
            mock_get_env.return_value = {
                'DATABASE_URL': 'postgresql://mock:mock@mock:5432/mock',
                'REDIS_URL': 'redis://mock:6379',
                'CLICKHOUSE_URL': 'clickhouse://localhost:9000/default',
            }
            
            calls_made = []
            
            async def mock_check(database_url: str, db_type: str, retry_policy):
                calls_made.append(db_type)
                return True, None
            
            mock_launcher.network_client.resilient_database_check = mock_check
            
            result = await mock_launcher._validate_databases_with_resilience()
            
            # Only ClickHouse (non-mock) should be checked
            assert len(calls_made) == 1
            assert calls_made[0] == 'clickhouse'
            assert result is True
    
    @pytest.mark.asyncio
    async def test_handles_connection_failures_gracefully(self, mock_launcher, mock_env):
        """Test that validation handles connection failures and falls back correctly."""
        with patch('dev_launcher.launcher.get_env') as mock_get_env:
            mock_get_env.return_value = mock_env
            
            # Mock connection failures
            async def mock_check(database_url: str, db_type: str, retry_policy):
                if db_type == 'postgresql':
                    return False, "Connection refused"
                return True, None
            
            mock_launcher.network_client.resilient_database_check = mock_check
            
            # Mock the fallback _validate_databases method
            mock_launcher._validate_databases = AsyncMock(return_value=True)
            
            result = await mock_launcher._validate_databases_with_resilience()
            
            # Should fall back to standard validation
            mock_launcher._validate_databases.assert_called_once()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_network_resilient_client_parses_urls_correctly(self):
        """Test that NetworkResilientClient correctly parses database URLs."""
        client = NetworkResilientClient(use_emoji=False)
        
        # Test with valid PostgreSQL URL
        with patch.object(client, '_check_database_specific') as mock_check:
            mock_check.return_value = (True, None)
            
            success, error = await client.resilient_database_check(
                'postgresql://user:pass@localhost:5432/testdb',
                db_type='postgresql'
            )
            
            assert success is True
            assert error is None
            mock_check.assert_called()
    
    @pytest.mark.asyncio
    async def test_network_resilient_client_fails_with_invalid_urls(self):
        """Test that NetworkResilientClient handles invalid URLs gracefully."""
        client = NetworkResilientClient(use_emoji=False)
        
        # Test with just service name (the bug we're fixing)
        with patch.object(client, '_check_database_specific') as mock_check:
            mock_check.side_effect = Exception("Invalid URL")
            
            success, error = await client.resilient_database_check(
                'postgres',  # Invalid - just service name
                db_type='postgresql',
                retry_policy=RetryPolicy(max_attempts=2, initial_delay=0.1)
            )
            
            assert success is False
            assert 'Invalid URL' in error or 'attempts' in error
    
    @pytest.mark.asyncio
    async def test_retry_policy_is_applied(self, mock_launcher, mock_env):
        """Test that retry policy is correctly applied to database checks."""
        with patch('dev_launcher.launcher.get_env') as mock_get_env:
            mock_get_env.return_value = mock_env
            
            attempt_count = {'count': 0}
            
            async def mock_check(database_url: str, db_type: str, retry_policy):
                attempt_count['count'] += 1
                # Verify retry policy parameters
                assert retry_policy.max_attempts == 5
                assert retry_policy.initial_delay == 2.0
                assert retry_policy.max_delay == 10.0
                assert retry_policy.timeout_per_attempt == 15.0
                return True, None
            
            mock_launcher.network_client.resilient_database_check = mock_check
            
            await mock_launcher._validate_databases_with_resilience()
            
            # Should have been called for each configured database
            assert attempt_count['count'] == 3
    
    @pytest.mark.asyncio
    async def test_successful_connections_are_reported(self, mock_launcher, mock_env):
        """Test that successful connections are properly tracked and reported."""
        with patch('dev_launcher.launcher.get_env') as mock_get_env:
            mock_get_env.return_value = mock_env
            
            # Mock mixed success/failure
            async def mock_check(database_url: str, db_type: str, retry_policy):
                if 'redis' in database_url:
                    return False, "Connection timeout"
                return True, None
            
            mock_launcher.network_client.resilient_database_check = mock_check
            
            # Mock the fallback
            mock_launcher._validate_databases = AsyncMock(return_value=True)
            
            # Capture print output
            printed_messages = []
            original_print = mock_launcher._print
            
            def capture_print(emoji, category, message):
                printed_messages.append((emoji, category, message))
                original_print(emoji, category, message)
            
            mock_launcher._print = capture_print
            
            result = await mock_launcher._validate_databases_with_resilience()
            
            # Check that appropriate messages were printed
            success_messages = [m for m in printed_messages if m[0] == " PASS: "]
            warning_messages = [m for m in printed_messages if m[0] == " WARNING: [U+FE0F]"]
            
            assert len(success_messages) >= 2  # Two successful connections
            assert len(warning_messages) >= 1  # One failed connection
            
            # Verify specific messages
            assert any('Postgres connection validated' in m[2] for m in success_messages)
            assert any('Clickhouse connection validated' in m[2] for m in success_messages)
            assert any('Redis connection failed' in m[2] for m in warning_messages)


class TestDatabaseConnectionErrorMessages:
    """Test that error messages are consistent and informative."""
    
    @pytest.mark.asyncio
    async def test_error_message_format(self):
        """Test that error messages follow expected format."""
        client = NetworkResilientClient(use_emoji=False)
        
        # Force all attempts to fail
        with patch.object(client, '_check_database_specific') as mock_check:
            mock_check.side_effect = Exception("Connection refused")
            
            success, error = await client.resilient_database_check(
                'postgresql://localhost:5432/testdb',
                db_type='postgresql',
                retry_policy=RetryPolicy(max_attempts=3, initial_delay=0.01)
            )
            
            assert success is False
            assert 'Database connection failed after 3 attempts' in error
    
    @pytest.mark.asyncio
    async def test_critical_database_errors_stop_retries(self):
        """Test that critical errors (like auth failures) stop retries immediately."""
        client = NetworkResilientClient(use_emoji=False)
        
        attempt_count = {'count': 0}
        
        async def mock_check(database_url: str, db_type: str, timeout: float):
            attempt_count['count'] += 1
            # Simulate authentication failure
            return False, "password incorrect"
        
        with patch.object(client, '_check_database_specific', mock_check):
            success, error = await client.resilient_database_check(
                'postgresql://user:wrongpass@localhost:5432/testdb',
                db_type='postgresql',
                retry_policy=RetryPolicy(max_attempts=5, initial_delay=0.01)
            )
            
            assert success is False
            assert 'Critical database error' in error
            assert 'password incorrect' in error
            # Should stop after first attempt due to critical error
            assert attempt_count['count'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])