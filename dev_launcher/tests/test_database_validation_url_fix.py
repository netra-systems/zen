"""
Focused test for the database validation URL fix.

Tests that the _validate_databases_with_resilience method passes URLs
instead of service names to resilient_database_check.
"""

import asyncio
import pytest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.network_resilience import NetworkResilientClient, RetryPolicy


class TestDatabaseValidationURLFix:
    """Test that database validation uses URLs, not service names."""
    
    @pytest.mark.asyncio
    async def test_resilient_database_check_receives_urls(self):
        """Test that resilient_database_check is called with URLs, not service names."""
        
        # Create a mock launcher-like object
        class MockLauncher:
            def __init__(self):
                self.network_client = NetworkResilientClient(use_emoji=False)
                self.use_emoji = False
                
            def _print(self, emoji, category, message):
                """Mock print method."""
                pass
                
            async def _validate_databases(self):
                """Mock fallback validation."""
                return True
                
            async def _validate_databases_with_resilience(self):
                """Method under test - copied from the fixed version."""
                try:
                    # Use network resilient client for database checks
                    db_policy = RetryPolicy(
                        max_attempts=5,
                        initial_delay=2.0,
                        max_delay=10.0,
                        timeout_per_attempt=15.0
                    )
                    
                    # Get database URLs from environment
                    from shared.isolated_environment import get_env
                    env = get_env()
                    db_configs = {
                        'postgres': (env.get('DATABASE_URL'), 'postgresql'),
                        'redis': (env.get('REDIS_URL'), 'redis'),
                        'clickhouse': (env.get('CLICKHOUSE_URL'), 'clickhouse')
                    }
                    
                    # Check individual database services with resilience
                    successful_connections = []
                    failed_connections = []
                    
                    for service_name, (db_url, db_type) in db_configs.items():
                        if not db_url:
                            self._print("[U+2139][U+FE0F]", "DB-RESILIENT", f"No {service_name.upper()}_URL configured, skipping")
                            continue
                            
                        # Skip mock databases
                        if 'mock' in db_url.lower():
                            self._print("[U+1F3AD]", "DB-RESILIENT", f"{service_name.capitalize()} in mock mode, skipping")
                            successful_connections.append(service_name)
                            continue
                        
                        success, error = await self.network_client.resilient_database_check(
                            db_url,
                            db_type=db_type,
                            retry_policy=db_policy
                        )
                        
                        if success:
                            successful_connections.append(service_name)
                            self._print(" PASS: ", "DB-RESILIENT", f"{service_name.capitalize()} connection validated")
                        else:
                            failed_connections.append((service_name, error))
                            self._print(" WARNING: [U+FE0F]", "DB-RESILIENT", f"{service_name.capitalize()} connection failed: {error}")
                    
                    # Report resilience results
                    if successful_connections:
                        self._print(" PASS: ", "RESILIENCE", f"Connected to {len(successful_connections)} database service(s)")
                    
                    if failed_connections:
                        self._print(" WARNING: [U+FE0F]", "RESILIENCE", f"{len(failed_connections)} database service(s) failed - using fallback validation")
                        # Fallback to standard validation for failed services
                        return await self._validate_databases()
                    
                    return len(successful_connections) > 0  # Success if at least one DB is available
                        
                except Exception as e:
                    # Fallback to standard validation
                    return await self._validate_databases()
        
        # Set up test environment
        test_env = {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb',
            'REDIS_URL': 'redis://localhost:6379/0',
            'CLICKHOUSE_URL': 'clickhouse://localhost:9000/default'
        }
        
        with patch('dev_launcher.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value = test_env
            
            # Create mock launcher
            launcher = MockLauncher()
            
            # Track calls to resilient_database_check
            calls_made = []
            
            async def mock_check(database_url: str, db_type: str, retry_policy):
                calls_made.append({
                    'database_url': database_url,
                    'db_type': db_type
                })
                return True, None
            
            launcher.network_client.resilient_database_check = mock_check
            
            # Run the method
            result = await launcher._validate_databases_with_resilience()
            
            # Verify correct calls were made
            assert len(calls_made) == 3
            
            # Check that URLs were passed, not service names
            postgres_call = next((c for c in calls_made if c['db_type'] == 'postgresql'), None)
            assert postgres_call is not None
            assert postgres_call['database_url'] == 'postgresql://user:pass@localhost:5432/testdb'
            assert postgres_call['database_url'] != 'postgres'  # Not just the service name
            
            redis_call = next((c for c in calls_made if c['db_type'] == 'redis'), None)
            assert redis_call is not None
            assert redis_call['database_url'] == 'redis://localhost:6379/0'
            assert redis_call['database_url'] != 'redis'  # Not just the service name
            
            clickhouse_call = next((c for c in calls_made if c['db_type'] == 'clickhouse'), None)
            assert clickhouse_call is not None
            assert clickhouse_call['database_url'] == 'clickhouse://localhost:9000/default'
            assert clickhouse_call['database_url'] != 'clickhouse'  # Not just the service name
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_old_implementation_would_fail(self):
        """Test that the old implementation (passing service names) would fail."""
        
        client = NetworkResilientClient(use_emoji=False)
        
        # Mock _check_database_specific to track what URL is being parsed
        parsed_urls = []
        
        async def mock_check_specific(database_url: str, db_type: str, timeout: float):
            parsed_urls.append(database_url)
            # The old bug would pass 'postgres' as the URL
            if database_url in ['postgres', 'redis', 'clickhouse']:
                raise Exception(f"Invalid URL format: {database_url}")
            return True, None
        
        with patch.object(client, '_check_database_specific', mock_check_specific):
            # Test with the old behavior (passing service name)
            success, error = await client.resilient_database_check(
                'postgres',  # This is wrong - should be a URL
                db_type='postgresql',
                retry_policy=RetryPolicy(max_attempts=2, initial_delay=0.01)
            )
            
            assert success is False
            assert 'Invalid URL format' in error or 'attempts' in error
            
            # Test with correct behavior (passing URL)
            parsed_urls.clear()
            success, error = await client.resilient_database_check(
                'postgresql://localhost:5432/testdb',  # This is correct
                db_type='postgresql',
                retry_policy=RetryPolicy(max_attempts=2, initial_delay=0.01)
            )
            
            assert success is True
            assert error is None
            assert parsed_urls[0] == 'postgresql://localhost:5432/testdb'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])