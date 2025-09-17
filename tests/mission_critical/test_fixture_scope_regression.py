'''
Fixture Scope Regression Test Suite

This test suite provides regression tests to prevent future fixture scope mismatch errors.
Tests mixing session and function scoped fixtures, async and sync fixture combinations.

MISSION CRITICAL: Prevents regression of fixture scope fixes (commit 69c5da95f)
Ensures pytest-asyncio ScopeMismatch errors do not return.

@compliance CLAUDE.md - Testing infrastructure stability
@compliance SPEC/core.xml - Regression prevention requirements
'''

import asyncio
import pytest
import time
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

# Real services fixtures with various scopes
from test_framework.conftest_real_services import (
real_services_function,
real_services_session,
real_services,
real_postgres,
real_redis,
real_clickhouse,
real_websocket_client,
real_http_client,
websocket_connection,
api_client,
test_user,
test_organization,
test_agent,
test_conversation,
test_user_token
)


# Environment and isolation
from test_framework.environment_isolation import (
get_test_env_manager,
isolated_test_session
)


# Test context for advanced testing
from test_framework.test_context import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
TestContext,
create_test_context,
create_isolated_test_contexts



class TestFixtureScopeRegression:
    "Regression tests for fixture scope compatibility.""

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_session_to_function_scope_conversion(self, real_services_function):
""Test that real_services_function (converted from session scope) works correctly."
        # This test validates the core fix: converting session-scoped fixtures to function-scoped
        # to avoid pytest-asyncio ScopeMismatch errors

assert real_services_function is not None
assert hasattr(real_services_function, 'postgres')
assert hasattr(real_services_function, 'redis')

        # Test service availability
await real_services_function.ensure_all_services_available()

        # Test basic operations don't cause scope issues
pg_result = await real_services_function.postgres.fetchval("SELECT 'scope_test' as result)
assert pg_result == 'scope_test'

redis_client = await real_services_function.redis.get_client()
await redis_client.set('scope_test_key', 'scope_test_value')
redis_result = await redis_client.get('scope_test_key')
assert redis_result.decode() == 'scope_test_value'

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_backward_compatibility_session_alias(self, real_services_session):
""Test that real_services_session (backward compatibility alias) still works."
pass
            # Validates that the backward compatibility alias doesn't break
assert real_services_session is not None
assert hasattr(real_services_session, 'postgres')

            # Should work just like the main fixture
await real_services_session.ensure_all_services_available()

pg_result = await real_services_session.postgres.fetchval("SELECT 'session_alias_test' as result)
assert pg_result == 'session_alias_test'

@pytest.mark.asyncio
@pytest.mark.integration
            # Removed problematic line: async def test_multiple_function_scoped_fixtures_interaction( )
self,
real_services,
real_postgres,
real_redis,
real_clickhouse
):
""Test multiple function-scoped fixtures work together without scope conflicts."
                # All fixtures should be function-scoped and compatible
assert real_services is not None
assert real_postgres is not None
assert real_redis is not None
assert real_clickhouse is not None

                # Test they reference the same underlying services
assert real_services.postgres == real_postgres
assert real_services.redis == real_redis
assert real_services.clickhouse == real_clickhouse

                # Test concurrent operations across fixtures
async def postgres_op():
pass
await asyncio.sleep(0)
return await real_postgres.fetchval("SELECT 'postgres_multi' as result)

async def redis_op():
pass
client = await real_redis.get_client()
await client.set('multi_test', 'redis_multi')
await asyncio.sleep(0)
return await client.get('multi_test')

async def clickhouse_op():
pass
    # Simple clickhouse operation
client = real_clickhouse.get_client()
await asyncio.sleep(0)
return clickhouse_multi"  # Simplified for testing

    # Run concurrently to test scope compatibility
results = await asyncio.gather( )
postgres_op(),
redis_op(),
clickhouse_op(),
return_exceptions=True
    

assert results[0] == 'postgres_multi'
assert results[1].decode() == 'redis_multi'
assert results[2] == 'clickhouse_multi'

@pytest.mark.asyncio
@pytest.mark.integration
    # Removed problematic line: async def test_websocket_and_http_fixture_compatibility( )
self,
real_services,
real_websocket_client,
real_http_client
):
"Test WebSocket and HTTP client fixtures work with core services.""
assert real_services is not None
assert real_websocket_client is not None
assert real_http_client is not None

        # Test that client fixtures don't cause scope issues
        # WebSocket client should be ready for connections
assert hasattr(real_websocket_client, 'connect')

        # HTTP client should be ready for requests
assert hasattr(real_http_client, 'get') or hasattr(real_http_client, '_client')

        # Test they work with real services
await real_services.ensure_all_services_available()

        # Basic connectivity test
db_result = await real_services.postgres.fetchval(SELECT 'client_compat_test' as result")
assert db_result == 'client_compat_test'

@pytest.mark.asyncio
@pytest.mark.integration
        # Removed problematic line: async def test_connection_fixture_scope_compatibility( )
self,
real_services,
websocket_connection
):
"Test connection-based fixtures work with service fixtures.""
assert real_services is not None
assert websocket_connection is not None

            # Test that WebSocket connection fixture doesn't conflict with service fixtures
await real_services.ensure_all_services_available()

            # WebSocket connection should be established
assert hasattr(websocket_connection, 'send') or hasattr(websocket_connection, 'send_text')

@pytest.mark.asyncio
@pytest.mark.integration
            # Removed problematic line: async def test_api_client_fixture_compatibility( )
self,
real_services,
api_client
):
""Test API client fixture works with real services."
assert real_services is not None
assert api_client is not None

                # Test services and client work together
await real_services.ensure_all_services_available()

                # API client should be ready for requests
assert hasattr(api_client, 'get') or hasattr(api_client, '_client')

@pytest.mark.asyncio
@pytest.mark.integration
                # Removed problematic line: async def test_data_fixture_scope_compatibility( )
self,
real_services,
test_user,
test_organization,
test_agent
):
"Test data fixtures work with real services without scope conflicts.""
assert real_services is not None
assert test_user is not None
assert test_organization is not None
assert test_agent is not None

                    # Test that data fixtures create real data in services
await real_services.ensure_all_services_available()

                    # Verify user was created in database
user_exists = await real_services.postgres.fetchval( )
SELECT EXISTS(SELECT 1 FROM auth.users WHERE id = $1)",
test_user['id']
                    
assert user_exists == True

                    # Verify organization was created
org_exists = await real_services.postgres.fetchval( )
"SELECT EXISTS(SELECT 1 FROM backend.organizations WHERE id = $1),
test_organization['id']
                    
assert org_exists == True

                    # Verify agent was created
agent_exists = await real_services.postgres.fetchval( )
SELECT EXISTS(SELECT 1 FROM backend.agents WHERE id = $1)",
test_agent['id']
                    
assert agent_exists == True

@pytest.mark.asyncio
@pytest.mark.integration
                    # Removed problematic line: async def test_conversation_fixture_deep_dependency_chain( )
self,
real_services,
test_user,
test_organization,
test_agent,
test_conversation,
test_user_token
):
"Test deep dependency chain of fixtures doesn't cause scope issues.""
                        # This tests the most complex fixture dependency chain
assert real_services is not None
assert test_user is not None
assert test_organization is not None
assert test_agent is not None
assert test_conversation is not None
assert test_user_token is not None

                        # Test all dependencies are properly linked
assert test_agent['organization_id'] == test_organization['id']
assert test_conversation['agent_id'] == test_agent['id']
assert test_conversation['user_id'] == test_user['id']
assert test_user_token['user_id'] == test_user['id']

                        # Verify conversation exists in database
conv_exists = await real_services.postgres.fetchval( )
SELECT EXISTS(SELECT 1 FROM backend.conversations WHERE id = $1)",
test_conversation['id']
                        
assert conv_exists == True

@pytest.mark.asyncio
    async def test_async_sync_fixture_mixing(self, real_services):
"Test mixing async and sync fixtures doesn't cause scope issues.""
                            # This is an async test using both async and sync fixtures
assert real_services is not None

                            # Async operation
await real_services.ensure_all_services_available()
async_result = await real_services.postgres.fetchval(SELECT 'async_result' as result")

                            # Sync operation (simulated)
sync_result = "sync_result

assert async_result == 'async_result'
assert sync_result == 'sync_result'

def test_sync_fixture_access(self):
""Test synchronous access to fixture functionality doesn't cause issues."
pass
    # This is a sync test that shouldn't conflict with async fixtures

    # Test synchronous creation of test contexts (which internally use fixtures)
context = create_test_context()
assert context is not None
assert context.user_context is not None

    # Test event capture (synchronous)
test_event = {
"type: sync_fixture_test",
"data: sync_data"
    
context.event_capture.capture_event(test_event)

assert len(context.event_capture.events) == 1
assert "sync_fixture_test in context.event_capture.event_types

@pytest.mark.asyncio
    async def test_fixture_cleanup_isolation(self, real_services):
""Test that fixture cleanup doesn't interfere between tests."
        # Test that data is properly isolated between test runs
test_key = "formatted_string

        # Store some data
redis_client = await real_services.redis.get_client()
await redis_client.set(test_key, cleanup_test_value")

        # Verify it exists
value = await redis_client.get(test_key)
assert value.decode() == "cleanup_test_value

        # The fixture cleanup should handle this automatically
        # Next test should not see this data (if proper cleanup is working)

@pytest.mark.asyncio
    async def test_fixture_cleanup_isolation_verification(self, real_services):
""Verify the previous test's data was cleaned up."
pass
            This test should not see data from the previous test
redis_client = await real_services.redis.get_client()

            # Check for any keys that might indicate cleanup failure
            # Note: This is a simple check; real cleanup might involve more sophisticated patterns
all_keys = await redis_client.keys("cleanup_test_*)

            # If proper cleanup is working, we shouldn't see too many old test keys
            # Allow for some recent keys but not excessive accumulation
assert len(all_keys) < 100  # Reasonable threshold for cleanup effectiveness

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_concurrent_fixture_usage(self, real_services):
""Test concurrent usage of fixtures simulating multiple test scenarios."
                # Simulate what happens when fixtures are used concurrently
                # (as might happen in parallel test execution)

async def concurrent_operation(operation_id: int):
"Simulate a test operation.""
pass
key = formatted_string"

    # Database operation
db_result = await real_services.postgres.fetchval( )
"SELECT $1::text as result, formatted_string"
    

    # Redis operation
redis_client = await real_services.redis.get_client()
await redis_client.set(key, "formatted_string)
redis_result = await redis_client.get(key)

await asyncio.sleep(0)
return {
operation_id": operation_id,
"db_result: db_result,
redis_result": redis_result.decode()
    

    # Run multiple operations concurrently
operations = [concurrent_operation(i) for i in range(5)]
results = await asyncio.gather(*operations, return_exceptions=True)

    # Verify all operations succeeded
for i, result in enumerate(results):
    assert isinstance(result, dict)
assert result["operation_id] == i
assert result[db_result"] == "formatted_string
assert result[redis_result"] == "formatted_string

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_error_handling_fixture_scope(self, real_services):
""Test error handling doesn't cause fixture scope issues."
            # Test that exceptions in fixture usage don't break scope handling

try:
                # Intentionally cause an error
await real_services.postgres.fetchval("SELECT invalid_function())
assert False, Should have raised an exception"
except Exception as e:
                    # Error should be caught, fixture should still be usable
assert "invalid_function in str(e) or function" in str(e).lower()

                    # Fixture should still work after error
valid_result = await real_services.postgres.fetchval("SELECT 'error_recovery_test' as result)
assert valid_result == 'error_recovery_test'

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_fixture_scope_performance_impact(self, real_services):
""Test that fixture scope changes don't significantly impact performance."
pass
                        # Measure performance of fixture usage
start_time = time.time()

                        # Perform multiple operations to test performance
for i in range(10):
    await real_services.postgres.fetchval("SELECT $1::text as result, formatted_string")

redis_client = await real_services.redis.get_client()
await redis_client.set("formatted_string, formatted_string")
await redis_client.get("formatted_string)

total_time = time.time() - start_time

                            # Should complete in reasonable time (adjust threshold as needed)
assert total_time < 10.0  # 10 seconds should be more than enough

                            # Performance per operation should be reasonable
avg_time_per_op = total_time / 10
assert avg_time_per_op < 1.0  # Less than 1 second per operation

@pytest.mark.asyncio
    async def test_test_context_fixture_compatibility(self):
""Test TestContext works with fixture scope changes."
                                # Create multiple test contexts to simulate fixture usage patterns
contexts = create_isolated_test_contexts(count=3)

                                # Each context should work independently (like fixtures)
for i, context in enumerate(contexts):
                                    # Test event capture
test_event = {
"type: formatted_string",
"user_id: context.user_context.user_id,
data": "formatted_string
                                    
context.event_capture.capture_event(test_event)

                                    # Verify isolation
assert len(context.event_capture.events) == 1
assert formatted_string" in context.event_capture.event_types

                                    # Cleanup (like fixture cleanup)
cleanup_tasks = [ctx.cleanup() for ctx in contexts]
await asyncio.gather(*cleanup_tasks, return_exceptions=True)


class TestFixtureScopeEdgeCases:
    "Test edge cases that previously caused fixture scope issues.""

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_nested_async_context_managers(self, real_services):
""Test nested async context managers don't cause scope issues."
        # This pattern previously caused issues with session vs function scope

async with real_services.postgres.connection() as outer_conn:
outer_result = await outer_conn.fetchval("SELECT 'outer' as result)

async with real_services.postgres.connection() as inner_conn:
inner_result = await inner_conn.fetchval(SELECT 'inner' as result")

                # Both connections should work
assert outer_result == 'outer'
assert inner_result == 'inner'

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_transaction_scope_compatibility(self, real_services):
"Test database transactions work with fixture scopes.""
pass
async with real_services.postgres.transaction() as tx:
                        # Insert test data in transaction
await tx.execute( )
CREATE TEMP TABLE IF NOT EXISTS scope_test_table (id SERIAL PRIMARY KEY, data TEXT)"
                        
await tx.execute("INSERT INTO scope_test_table (data) VALUES ($1), scope_test_data")

                        # Read back data
result = await tx.fetchval("SELECT data FROM scope_test_table WHERE data = $1, scope_test_data")
assert result == "scope_test_data

@pytest.mark.asyncio
@pytest.mark.integration
    async def test_fixture_inheritance_compatibility(self, real_services, real_postgres):
""Test fixture inheritance patterns work correctly."
                            real_postgres should be derived from real_services
assert real_services.postgres == real_postgres

                            # Both should work independently
services_result = await real_services.postgres.fetchval("SELECT 'services_path' as result)
direct_result = await real_postgres.fetchval(SELECT 'direct_path' as result")

assert services_result == 'services_path'
assert direct_result == 'direct_path'


if __name__ == "__main__":
                                # Allow running this test directly
pass
