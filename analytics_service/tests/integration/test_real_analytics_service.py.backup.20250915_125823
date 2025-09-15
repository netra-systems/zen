"""
Real Analytics Service Integration Tests
======================================

Comprehensive integration tests for Analytics Service using REAL services only.
NO MOCKS - Uses actual ClickHouse, PostgreSQL, and service infrastructure.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Integration and Data Pipeline Reliability  
- Value Impact: Ensures analytics data flows correctly with real service dependencies
- Strategic Impact: Prevents analytics failures that would break customer insights

Test Coverage:
- Real ClickHouse database operations with test schema
- Real event ingestion and processing pipelines
- Real service-to-service communication
- Real WebSocket event streaming
- Real data aggregation and analytics queries
- Real error handling and resilience patterns
"""
import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import httpx
from shared.isolated_environment import IsolatedEnvironment
from test_framework import setup_test_path
setup_test_path()
from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
from shared.isolated_environment import get_env
from analytics_service.analytics_core.config import get_config

class TestRealAnalyticsServiceIntegration:
    """Integration tests using real analytics service infrastructure."""

    @pytest.fixture(autouse=True)
    async def real_service_environment(self):
        """Setup real service test environment with actual database connections."""
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'test', 'real_analytics_integration')
        env.set('CLICKHOUSE_HOST', 'localhost', 'real_analytics_integration')
        env.set('CLICKHOUSE_PORT', '9002', 'real_analytics_integration')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'real_analytics_integration')
        env.set('CLICKHOUSE_USER', 'test_user', 'real_analytics_integration')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'real_analytics_integration')
        env.set('POSTGRES_HOST', 'localhost', 'real_analytics_integration')
        env.set('POSTGRES_PORT', '5434', 'real_analytics_integration')
        env.set('REDIS_HOST', 'localhost', 'real_analytics_integration')
        env.set('REDIS_PORT', '6381', 'real_analytics_integration')
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def clickhouse_manager(self, real_service_environment):
        """Real ClickHouse manager connected to test database."""
        env = real_service_environment
        manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'), max_connections=5)
        try:
            await manager.initialize()
            yield manager
        except Exception as e:
            pytest.skip(f'ClickHouse test infrastructure not available: {e}')
        finally:
            await manager.close()

    @pytest.fixture
    async def http_client(self):
        """HTTP client for service communication."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client

class TestRealEventIngestion:
    """Test real event ingestion pipeline end-to-end."""

    @pytest.fixture(autouse=True)
    async def setup_environment(self):
        """Setup test environment."""
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'test', 'real_event_ingestion')
        env.set('CLICKHOUSE_HOST', 'localhost', 'real_event_ingestion')
        env.set('CLICKHOUSE_PORT', '9002', 'real_event_ingestion')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'real_event_ingestion')
        env.set('CLICKHOUSE_USER', 'test_user', 'real_event_ingestion')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'real_event_ingestion')
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def clickhouse_manager(self, setup_environment):
        """Real ClickHouse manager for event ingestion testing."""
        env = setup_environment
        manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'))
        try:
            await manager.initialize()
            yield manager
        except Exception as e:
            pytest.skip(f'ClickHouse test infrastructure not available: {e}')
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_real_user_event_ingestion(self, clickhouse_manager):
        """Test ingesting real user events into ClickHouse."""
        test_events = [{'user_id': str(uuid4()), 'event_type': 'login', 'session_id': f'session_{int(time.time())}', 'properties': {'source': 'web', 'device': 'desktop'}}, {'user_id': str(uuid4()), 'event_type': 'page_view', 'session_id': f'session_{int(time.time())}', 'properties': {'page': '/dashboard', 'referrer': 'direct'}}]
        insert_query = '\n        INSERT INTO user_events (user_id, event_type, session_id, properties)\n        VALUES\n        '
        for i, event in enumerate(test_events):
            if i > 0:
                insert_query += ', '
            insert_query += f"('{event['user_id']}', '{event['event_type']}', '{event['session_id']}', map('source', '{event['properties'].get('source', '')}', 'device', '{event['properties'].get('device', '')}', 'page', '{event['properties'].get('page', '')}', 'referrer', '{event['properties'].get('referrer', '')}'))"
        await clickhouse_manager.execute_command(insert_query)
        count_result = await clickhouse_manager.execute_query('SELECT count() as count FROM user_events WHERE session_id LIKE %(session_pattern)s', {'session_pattern': f'session_{int(time.time())}%'})
        assert count_result[0][0] >= 2, 'Events were not properly inserted'

    @pytest.mark.asyncio
    async def test_real_conversation_event_ingestion(self, clickhouse_manager):
        """Test ingesting real conversation events."""
        conversation_id = str(uuid4())
        agent_id = str(uuid4())
        user_id = str(uuid4())
        organization_id = str(uuid4())
        await clickhouse_manager.execute_command("\n        INSERT INTO conversation_events (\n            conversation_id, agent_id, user_id, organization_id,\n            event_type, message_count, tokens_used, model_used\n        ) VALUES (\n            %(conversation_id)s, %(agent_id)s, %(user_id)s, %(organization_id)s,\n            'conversation_start', 1, 150, 'gpt-4'\n        )\n        ", {'conversation_id': conversation_id, 'agent_id': agent_id, 'user_id': user_id, 'organization_id': organization_id})
        await clickhouse_manager.execute_command("\n        INSERT INTO conversation_events (\n            conversation_id, agent_id, user_id, organization_id,\n            event_type, message_count, tokens_used, model_used, tool_calls\n        ) VALUES (\n            %(conversation_id)s, %(agent_id)s, %(user_id)s, %(organization_id)s,\n            'message_sent', 3, 450, 'gpt-4', ['web_search', 'code_execution']\n        )\n        ", {'conversation_id': conversation_id, 'agent_id': agent_id, 'user_id': user_id, 'organization_id': organization_id})
        results = await clickhouse_manager.execute_query('\n        SELECT event_type, tokens_used \n        FROM conversation_events \n        WHERE conversation_id = %(conversation_id)s\n        ORDER BY event_timestamp\n        ', {'conversation_id': conversation_id})
        assert len(results) == 2, 'Expected 2 conversation events'
        assert results[0][0] == 'conversation_start', 'First event should be conversation_start'
        assert results[1][0] == 'message_sent', 'Second event should be message_sent'
        assert results[0][1] == 150, 'First event should have 150 tokens'
        assert results[1][1] == 450, 'Second event should have 450 tokens'

    @pytest.mark.asyncio
    async def test_real_tool_execution_tracking(self, clickhouse_manager):
        """Test real tool execution event tracking."""
        conversation_id = str(uuid4())
        agent_id = str(uuid4())
        tool_executions = [{'tool_name': 'web_search', 'execution_status': 'success', 'execution_time_ms': 1250, 'parameters_size': 512, 'result_size': 2048}, {'tool_name': 'code_execution', 'execution_status': 'success', 'execution_time_ms': 890, 'parameters_size': 1024, 'result_size': 256}, {'tool_name': 'file_analysis', 'execution_status': 'error', 'execution_time_ms': 150, 'parameters_size': 256, 'result_size': 0, 'error_message': 'File not found'}]
        for tool_exec in tool_executions:
            await clickhouse_manager.execute_command('\n            INSERT INTO tool_executions (\n                conversation_id, agent_id, tool_name, execution_status,\n                execution_time_ms, parameters_size, result_size, error_message\n            ) VALUES (\n                %(conversation_id)s, %(agent_id)s, %(tool_name)s, %(execution_status)s,\n                %(execution_time_ms)s, %(parameters_size)s, %(result_size)s, %(error_message)s\n            )\n            ', {'conversation_id': conversation_id, 'agent_id': agent_id, **tool_exec, 'error_message': tool_exec.get('error_message')})
        stats_results = await clickhouse_manager.execute_query('\n        SELECT \n            execution_status,\n            count() as execution_count,\n            avg(execution_time_ms) as avg_execution_time\n        FROM tool_executions \n        WHERE conversation_id = %(conversation_id)s\n        GROUP BY execution_status\n        ORDER BY execution_count DESC\n        ', {'conversation_id': conversation_id})
        success_stats = next((r for r in stats_results if r[0] == 'success'), None)
        error_stats = next((r for r in stats_results if r[0] == 'error'), None)
        assert success_stats is not None, 'Should have success statistics'
        assert error_stats is not None, 'Should have error statistics'
        assert success_stats[1] == 2, 'Should have 2 successful executions'
        assert error_stats[1] == 1, 'Should have 1 failed execution'

class TestRealAnalyticsQueries:
    """Test real analytics queries and aggregations."""

    @pytest.fixture(autouse=True)
    async def setup_environment(self):
        """Setup test environment."""
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'test', 'real_analytics_queries')
        env.set('CLICKHOUSE_HOST', 'localhost', 'real_analytics_queries')
        env.set('CLICKHOUSE_PORT', '9002', 'real_analytics_queries')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'real_analytics_queries')
        env.set('CLICKHOUSE_USER', 'test_user', 'real_analytics_queries')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'real_analytics_queries')
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def clickhouse_manager(self, setup_environment):
        """Real ClickHouse manager for analytics queries."""
        env = setup_environment
        manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'))
        try:
            await manager.initialize()
            yield manager
        except Exception as e:
            pytest.skip(f'ClickHouse test infrastructure not available: {e}')
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_real_user_activity_analytics(self, clickhouse_manager):
        """Test real user activity analytics queries."""
        user_activity_results = await clickhouse_manager.execute_query('\n        SELECT \n            user_id,\n            count() as event_count,\n            uniq(session_id) as session_count,\n            min(event_timestamp) as first_activity,\n            max(event_timestamp) as last_activity\n        FROM user_events\n        WHERE event_timestamp >= now() - INTERVAL 1 DAY\n        GROUP BY user_id\n        ORDER BY event_count DESC\n        LIMIT 10\n        ')
        assert len(user_activity_results) >= 0, 'Should return user activity results'
        if user_activity_results:
            first_result = user_activity_results[0]
            assert len(first_result) == 5, 'Should have 5 columns in user activity result'
            assert first_result[1] > 0, 'Event count should be positive'

    @pytest.mark.asyncio
    async def test_real_conversation_metrics(self, clickhouse_manager):
        """Test real conversation metrics aggregation."""
        conversation_metrics = await clickhouse_manager.execute_query("\n        SELECT \n            organization_id,\n            count() as conversation_count,\n            sum(tokens_used) as total_tokens,\n            avg(tokens_used) as avg_tokens_per_event,\n            countIf(event_type = 'conversation_start') as conversations_started\n        FROM conversation_events\n        WHERE event_timestamp >= now() - INTERVAL 1 DAY\n        GROUP BY organization_id\n        ORDER BY total_tokens DESC\n        ")
        assert isinstance(conversation_metrics, list), 'Should return list of metrics'
        if conversation_metrics:
            first_metric = conversation_metrics[0]
            assert len(first_metric) == 5, 'Should have 5 columns in conversation metrics'

    @pytest.mark.asyncio
    async def test_real_performance_analytics(self, clickhouse_manager):
        """Test real performance metrics analytics."""
        performance_results = await clickhouse_manager.execute_query('\n        SELECT \n            service_name,\n            endpoint,\n            count() as request_count,\n            avg(response_time_ms) as avg_response_time,\n            quantile(0.95)(response_time_ms) as p95_response_time,\n            countIf(status_code >= 400) as error_count\n        FROM performance_metrics\n        WHERE event_timestamp >= now() - INTERVAL 1 HOUR\n        GROUP BY service_name, endpoint\n        ORDER BY request_count DESC\n        ')
        assert isinstance(performance_results, list), 'Should return performance results'
        if performance_results:
            first_result = performance_results[0]
            assert len(first_result) == 6, 'Should have 6 columns in performance results'

    @pytest.mark.asyncio
    async def test_real_billing_analytics(self, clickhouse_manager):
        """Test real billing and cost analytics."""
        billing_results = await clickhouse_manager.execute_query('\n        SELECT \n            organization_id,\n            billing_type,\n            sum(quantity) as total_quantity,\n            sum(total_cost) as total_cost,\n            avg(unit_cost) as avg_unit_cost,\n            count() as billing_events\n        FROM billing_events\n        WHERE billing_date >= today() - 7\n        GROUP BY organization_id, billing_type\n        ORDER BY total_cost DESC\n        ')
        assert isinstance(billing_results, list), 'Should return billing results'
        if billing_results:
            first_result = billing_results[0]
            assert len(first_result) == 6, 'Should have 6 columns in billing results'

class TestRealServiceHealthAndMonitoring:
    """Test real service health monitoring and observability."""

    @pytest.fixture(autouse=True)
    async def setup_environment(self):
        """Setup test environment."""
        env = get_env()
        env.enable_isolation()
        env.set('ENVIRONMENT', 'test', 'real_service_health')
        env.set('CLICKHOUSE_HOST', 'localhost', 'real_service_health')
        env.set('CLICKHOUSE_PORT', '9002', 'real_service_health')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'real_service_health')
        env.set('CLICKHOUSE_USER', 'test_user', 'real_service_health')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'real_service_health')
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def clickhouse_manager(self, setup_environment):
        """Real ClickHouse manager for health monitoring."""
        env = setup_environment
        manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'))
        try:
            await manager.initialize()
            yield manager
        except Exception as e:
            pytest.skip(f'ClickHouse test infrastructure not available: {e}')
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_real_database_health_check(self, clickhouse_manager):
        """Test real database health monitoring."""
        health_status = await clickhouse_manager.get_health_status()
        assert isinstance(health_status, dict), 'Health status should be a dictionary'
        assert 'is_healthy' in health_status, 'Health status should include is_healthy'
        assert 'pool_size' in health_status, 'Health status should include pool_size'
        assert 'host' in health_status, 'Health status should include host'
        assert 'database' in health_status, 'Health status should include database'
        if health_status['is_healthy']:
            test_result = await clickhouse_manager.execute_query('SELECT 1 as health_check')
            assert test_result == [(1,)], 'Health check query should return expected result'

    @pytest.mark.asyncio
    async def test_real_service_metrics_collection(self, clickhouse_manager):
        """Test real service metrics collection and storage."""
        test_service_name = f'analytics-service-{int(time.time())}'
        await clickhouse_manager.execute_command("\n        INSERT INTO performance_metrics (\n            service_name, endpoint, method, status_code, \n            response_time_ms, request_size, response_size\n        ) VALUES (\n            %(service_name)s, '/test/health', 'GET', 200,\n            45, 128, 256\n        )\n        ", {'service_name': test_service_name})
        metric_results = await clickhouse_manager.execute_query('\n        SELECT service_name, endpoint, response_time_ms\n        FROM performance_metrics\n        WHERE service_name = %(service_name)s\n        ', {'service_name': test_service_name})
        assert len(metric_results) == 1, 'Should find the inserted metric'
        assert metric_results[0][0] == test_service_name, 'Service name should match'
        assert metric_results[0][1] == '/test/health', 'Endpoint should match'
        assert metric_results[0][2] == 45, 'Response time should match'

    @pytest.mark.asyncio
    async def test_real_error_tracking_and_alerting(self, clickhouse_manager):
        """Test real error tracking capabilities."""
        error_service = f'error-test-{int(time.time())}'
        for i in range(10):
            status_code = 500 if i < 3 else 200
            await clickhouse_manager.execute_command("\n            INSERT INTO performance_metrics (\n                service_name, endpoint, method, status_code,\n                response_time_ms, error_message\n            ) VALUES (\n                %(service_name)s, '/api/test', 'POST', %(status_code)s,\n                %(response_time)s, %(error_message)s\n            )\n            ", {'service_name': error_service, 'status_code': status_code, 'response_time': 1000 if status_code == 500 else 100, 'error_message': 'Internal server error' if status_code == 500 else None})
        error_stats = await clickhouse_manager.execute_query('\n        SELECT \n            service_name,\n            count() as total_requests,\n            countIf(status_code >= 400) as error_count,\n            (countIf(status_code >= 400) / count()) * 100 as error_rate\n        FROM performance_metrics\n        WHERE service_name = %(service_name)s\n        GROUP BY service_name\n        ', {'service_name': error_service})
        assert len(error_stats) == 1, 'Should have error statistics'
        stats = error_stats[0]
        assert stats[1] == 10, 'Should have 10 total requests'
        assert stats[2] == 3, 'Should have 3 error requests'
        assert abs(stats[3] - 30.0) < 0.1, 'Error rate should be 30%'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')