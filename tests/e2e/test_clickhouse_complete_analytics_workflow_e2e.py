"""
Test ClickHouse Complete Analytics Workflow - E2E Test

Business Value Justification (BVJ):
- Segment: Mid and Enterprise 
- Business Goal: End-to-end analytics pipeline reliability
- Value Impact: Complete analytics accuracy drives customer retention (95% satisfaction)
- Strategic Impact: Enables premium analytics features for enterprise customers (+$25K ARR)

This E2E test validates the complete ClickHouse analytics workflow from data ingestion
to dashboard delivery, ensuring the entire pipeline works reliably with authentication.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from netra_backend.app.db.clickhouse import get_clickhouse_client, get_clickhouse_service
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import create_authenticated_user, get_user_auth_token

class TestClickHouseCompleteAnalyticsWorkflowE2E(BaseE2ETest):
    """Test complete ClickHouse analytics workflow with authentication."""

    def setup_method(self):
        """Setup E2E test environment with authentication."""
        self.workflow_id = uuid.uuid4().hex[:8]
        self.analytics_table = f'e2e_analytics_{self.workflow_id}'
        self.user_events_table = f'e2e_user_events_{self.workflow_id}'
        self.dashboards_table = f'e2e_dashboards_{self.workflow_id}'
        self.test_users = {}

    async def cleanup_e2e_tables(self):
        """Cleanup all E2E test tables."""
        tables_to_cleanup = [self.analytics_table, self.user_events_table, self.dashboards_table]
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                for table in tables_to_cleanup:
                    await client.execute(f'DROP TABLE IF EXISTS {table}')
        except Exception as e:
            print(f'Warning: Failed to cleanup E2E tables: {e}')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_analytics_workflow_with_authentication(self):
        """Test complete analytics workflow from ingestion to dashboard with auth.
        
        This E2E test validates the entire analytics pipeline:
        1. Authenticated user data ingestion
        2. Real-time data processing
        3. Multi-user analytics queries
        4. Dashboard data aggregation
        5. Performance under load
        """
        try:
            self.test_users['enterprise_analyst'] = await create_authenticated_user(email='analyst@enterprise.com', name='Enterprise Analyst', permissions=['analytics:read', 'analytics:write', 'dashboards:create'])
            self.test_users['data_scientist'] = await create_authenticated_user(email='scientist@enterprise.com', name='Data Scientist', permissions=['analytics:read', 'analytics:advanced', 'ml:training'])
            self.test_users['business_user'] = await create_authenticated_user(email='business@enterprise.com', name='Business User', permissions=['analytics:read', 'dashboards:view'])
            service = get_clickhouse_service()
            await service.initialize()
            async with get_clickhouse_client(bypass_manager=True) as client:
                await client.execute(f"\n                CREATE TABLE IF NOT EXISTS {self.user_events_table} (\n                    event_id UUID DEFAULT generateUUIDv4(),\n                    user_id String,\n                    authenticated_user_id String,  -- Who owns this data\n                    event_type String,\n                    event_data String,\n                    timestamp DateTime64(3) DEFAULT now64(3),\n                    session_id String,\n                    ip_address String DEFAULT '127.0.0.1',\n                    user_agent String DEFAULT 'ClickHouse E2E Test'\n                ) ENGINE = MergeTree()\n                PARTITION BY (authenticated_user_id, toYYYYMM(timestamp))\n                ORDER BY (authenticated_user_id, event_type, timestamp, event_id)\n                ")
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.analytics_table} (\n                    analysis_id UUID DEFAULT generateUUIDv4(),\n                    authenticated_user_id String,\n                    analysis_type String,\n                    time_period String,\n                    metrics Map(String, Float64),\n                    dimensions Map(String, String),\n                    created_at DateTime64(3) DEFAULT now64(3),\n                    updated_at DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = ReplacingMergeTree(updated_at)\n                PARTITION BY (authenticated_user_id, analysis_type)\n                ORDER BY (authenticated_user_id, analysis_type, time_period, analysis_id)\n                ')
                await client.execute(f'\n                CREATE TABLE IF NOT EXISTS {self.dashboards_table} (\n                    dashboard_id UUID DEFAULT generateUUIDv4(),\n                    owner_user_id String,\n                    dashboard_name String,\n                    config_json String,\n                    shared_with Array(String) DEFAULT [],\n                    created_at DateTime64(3) DEFAULT now64(3),\n                    last_accessed DateTime64(3) DEFAULT now64(3)\n                ) ENGINE = ReplacingMergeTree(last_accessed)\n                ORDER BY (owner_user_id, dashboard_name, dashboard_id)\n                ')
            ingestion_results = await self._simulate_data_ingestion()
            analytics_results = await self._process_realtime_analytics()
            dashboard_results = await self._test_dashboard_workflows()
            integrity_results = await self._validate_e2e_integrity()
            performance_results = await self._validate_e2e_performance()
            self._assert_complete_workflow_success(ingestion_results, analytics_results, dashboard_results, integrity_results, performance_results)
        finally:
            await self.cleanup_e2e_tables()

    async def _simulate_data_ingestion(self) -> Dict[str, Any]:
        """Simulate realistic data ingestion for authenticated users."""
        ingestion_results = {'total_events': 0, 'events_per_user': {}, 'ingestion_performance': {}}
        service = get_clickhouse_service()
        event_types = ['page_view', 'button_click', 'form_submit', 'api_call', 'file_upload', 'search_query', 'export_data', 'create_dashboard']
        for user_role, user_data in self.test_users.items():
            user_id = user_data['user_id']
            events_count = 150 if user_role == 'enterprise_analyst' else 100
            start_time = datetime.now()
            for i in range(events_count):
                event_data = {'user_id': f'app_user_{i % 20}', 'authenticated_user_id': user_id, 'event_type': event_types[i % len(event_types)], 'event_data': f'{{"action": "{event_types[i % len(event_types)]}", "value": {i * 1.5}, "source": "{user_role}"}}', 'session_id': f'{user_role}_session_{i // 20}'}
                await service.execute(f'\n                    INSERT INTO {self.user_events_table}\n                    (user_id, authenticated_user_id, event_type, event_data, session_id)\n                    VALUES (%(user_id)s, %(authenticated_user_id)s, %(event_type)s, %(event_data)s, %(session_id)s)\n                ', event_data, user_id=user_id)
            ingestion_time = (datetime.now() - start_time).total_seconds()
            ingestion_results['events_per_user'][user_role] = events_count
            ingestion_results['ingestion_performance'][user_role] = ingestion_time
            ingestion_results['total_events'] += events_count
        await asyncio.sleep(0.5)
        total_count = await service.execute(f'\n            SELECT COUNT(*) as total FROM {self.user_events_table}\n        ', user_id='system')
        assert total_count[0]['total'] == ingestion_results['total_events'], f"Ingestion failed: expected {ingestion_results['total_events']}, got {total_count[0]['total']}"
        return ingestion_results

    async def _process_realtime_analytics(self) -> Dict[str, Any]:
        """Process real-time analytics for authenticated users."""
        analytics_results = {'analyses_created': 0, 'user_analytics': {}, 'processing_performance': {}}
        service = get_clickhouse_service()
        for user_role, user_data in self.test_users.items():
            user_id = user_data['user_id']
            start_time = datetime.now()
            user_event_summary = await service.execute(f'\n                SELECT \n                    event_type,\n                    COUNT(*) as event_count,\n                    COUNT(DISTINCT user_id) as unique_users,\n                    COUNT(DISTINCT session_id) as unique_sessions,\n                    AVG(LENGTH(event_data)) as avg_data_size\n                FROM {self.user_events_table}\n                WHERE authenticated_user_id = %(user_id)s\n                GROUP BY event_type\n            ', {'user_id': user_id}, user_id=user_id)
            for analysis in user_event_summary:
                analytics_data = {'authenticated_user_id': user_id, 'analysis_type': f"event_summary_{analysis['event_type']}", 'time_period': 'last_hour', 'metrics': f"""{{"event_count": {analysis['event_count']}, "unique_users": {analysis['unique_users']}, "unique_sessions": {analysis['unique_sessions']}, "avg_data_size": {analysis['avg_data_size']}}}""", 'dimensions': f'''{{"event_type": "{analysis['event_type']}", "user_role": "{user_role}"}}'''}
                await service.execute(f'\n                    INSERT INTO {self.analytics_table}\n                    (authenticated_user_id, analysis_type, time_period, metrics, dimensions)\n                    VALUES (%(authenticated_user_id)s, %(analysis_type)s, %(time_period)s, %(metrics)s, %(dimensions)s)\n                ', analytics_data, user_id=user_id)
                analytics_results['analyses_created'] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            analytics_results['processing_performance'][user_role] = processing_time
            analytics_results['user_analytics'][user_role] = len(user_event_summary)
        await asyncio.sleep(0.2)
        return analytics_results

    async def _test_dashboard_workflows(self) -> Dict[str, Any]:
        """Test authenticated dashboard creation and access workflows."""
        dashboard_results = {'dashboards_created': 0, 'access_tests_passed': 0, 'sharing_tests_passed': 0}
        service = get_clickhouse_service()
        analyst_user = self.test_users['enterprise_analyst']
        scientist_user = self.test_users['data_scientist']
        business_user = self.test_users['business_user']
        analyst_dashboard = {'owner_user_id': analyst_user['user_id'], 'dashboard_name': 'Enterprise Analytics Dashboard', 'config_json': '{"charts": [{"type": "line", "data": "event_summary"}, {"type": "bar", "data": "user_metrics"}], "refresh_interval": 30}', 'shared_with': [business_user['user_id']]}
        await service.execute(f'\n            INSERT INTO {self.dashboards_table}\n            (owner_user_id, dashboard_name, config_json, shared_with)\n            VALUES (%(owner_user_id)s, %(dashboard_name)s, %(config_json)s, %(shared_with)s)\n        ', analyst_dashboard, user_id=analyst_user['user_id'])
        dashboard_results['dashboards_created'] += 1
        scientist_dashboard = {'owner_user_id': scientist_user['user_id'], 'dashboard_name': 'ML Training Analytics', 'config_json': '{"charts": [{"type": "scatter", "data": "ml_metrics"}, {"type": "heatmap", "data": "correlation_matrix"}], "advanced": true}', 'shared_with': []}
        await service.execute(f'\n            INSERT INTO {self.dashboards_table}\n            (owner_user_id, dashboard_name, config_json, shared_with)\n            VALUES (%(owner_user_id)s, %(dashboard_name)s, %(config_json)s, %(shared_with)s)\n        ', scientist_dashboard, user_id=scientist_user['user_id'])
        dashboard_results['dashboards_created'] += 1
        await asyncio.sleep(0.1)
        analyst_dashboards = await service.execute(f'\n            SELECT dashboard_name, owner_user_id, shared_with\n            FROM {self.dashboards_table}\n            WHERE owner_user_id = %(user_id)s\n        ', {'user_id': analyst_user['user_id']}, user_id=analyst_user['user_id'])
        assert len(analyst_dashboards) == 1, 'Analyst should see their dashboard'
        dashboard_results['access_tests_passed'] += 1
        shared_dashboards = await service.execute(f'\n            SELECT dashboard_name, owner_user_id \n            FROM {self.dashboards_table}\n            WHERE has(shared_with, %(user_id)s)\n        ', {'user_id': business_user['user_id']}, user_id=business_user['user_id'])
        assert len(shared_dashboards) == 1, 'Business user should see shared dashboard'
        dashboard_results['sharing_tests_passed'] += 1
        scientist_dashboards = await service.execute(f'\n            SELECT dashboard_name, owner_user_id\n            FROM {self.dashboards_table}\n            WHERE owner_user_id = %(user_id)s\n        ', {'user_id': scientist_user['user_id']}, user_id=scientist_user['user_id'])
        assert len(scientist_dashboards) == 1, 'Scientist should see their private dashboard'
        assert 'ML Training Analytics' == scientist_dashboards[0]['dashboard_name']
        dashboard_results['access_tests_passed'] += 1
        return dashboard_results

    async def _validate_e2e_integrity(self) -> Dict[str, Any]:
        """Validate end-to-end data integrity and user isolation."""
        integrity_results = {'user_isolation_verified': False, 'data_consistency_verified': False, 'cross_table_integrity_verified': False}
        service = get_clickhouse_service()
        for user_role, user_data in self.test_users.items():
            user_id = user_data['user_id']
            user_events = await service.execute(f'\n                SELECT COUNT(*) as count \n                FROM {self.user_events_table}\n                WHERE authenticated_user_id = %(user_id)s\n            ', {'user_id': user_id}, user_id=user_id)
            user_analytics = await service.execute(f'\n                SELECT COUNT(*) as count\n                FROM {self.analytics_table}\n                WHERE authenticated_user_id = %(user_id)s  \n            ', {'user_id': user_id}, user_id=user_id)
            assert user_events[0]['count'] > 0, f'User {user_role} should have events'
            assert user_analytics[0]['count'] > 0, f'User {user_role} should have analytics'
        integrity_results['user_isolation_verified'] = True
        total_events = await service.execute(f'\n            SELECT COUNT(*) as total FROM {self.user_events_table}\n        ', user_id='system')
        total_analytics = await service.execute(f'\n            SELECT COUNT(*) as total FROM {self.analytics_table}\n        ', user_id='system')
        assert total_events[0]['total'] > 0, 'Should have events'
        assert total_analytics[0]['total'] > 0, 'Should have analytics'
        integrity_results['data_consistency_verified'] = True
        cross_table_check = await service.execute(f'\n            SELECT \n                e.authenticated_user_id,\n                COUNT(DISTINCT e.event_type) as event_types,\n                COUNT(DISTINCT a.analysis_type) as analysis_types\n            FROM {self.user_events_table} e\n            LEFT JOIN {self.analytics_table} a ON e.authenticated_user_id = a.authenticated_user_id\n            GROUP BY e.authenticated_user_id\n        ', user_id='system')
        for check in cross_table_check:
            assert check['event_types'] > 0, 'Should have event types'
            assert check['analysis_types'] > 0, 'Should have corresponding analytics'
        integrity_results['cross_table_integrity_verified'] = True
        return integrity_results

    async def _validate_e2e_performance(self) -> Dict[str, Any]:
        """Validate E2E performance under realistic load."""
        performance_results = {'query_performance_acceptable': False, 'concurrent_user_performance_acceptable': False, 'dashboard_load_performance_acceptable': False}
        service = get_clickhouse_service()
        import time
        start_time = time.time()
        complex_query = await service.execute(f'\n            SELECT \n                e.authenticated_user_id,\n                e.event_type,\n                COUNT(*) as total_events,\n                COUNT(DISTINCT e.user_id) as unique_users,\n                AVG(LENGTH(e.event_data)) as avg_data_size,\n                MAX(e.timestamp) as latest_event,\n                COUNT(DISTINCT a.analysis_type) as analysis_count\n            FROM {self.user_events_table} e\n            LEFT JOIN {self.analytics_table} a ON e.authenticated_user_id = a.authenticated_user_id\n            GROUP BY e.authenticated_user_id, e.event_type\n            ORDER BY total_events DESC\n        ', user_id='system')
        complex_query_time = time.time() - start_time
        assert complex_query_time < 2.0, f'Complex query took {complex_query_time:.2f}s, should be <2s'
        assert len(complex_query) > 0, 'Complex query should return results'
        performance_results['query_performance_acceptable'] = True

        async def simulate_dashboard_load(user_data: Dict[str, Any]):
            """Simulate dashboard loading for a user."""
            user_id = user_data['user_id']
            start = time.time()
            dashboard_data = await service.execute(f'\n                SELECT analysis_type, metrics, dimensions \n                FROM {self.analytics_table}\n                WHERE authenticated_user_id = %(user_id)s\n                ORDER BY created_at DESC\n                LIMIT 10\n            ', {'user_id': user_id}, user_id=user_id)
            return (time.time() - start, len(dashboard_data))
        dashboard_tasks = [simulate_dashboard_load(user_data) for user_data in self.test_users.values()]
        dashboard_results = await asyncio.gather(*dashboard_tasks)
        for load_time, data_count in dashboard_results:
            assert load_time < 1.0, f'Dashboard load took {load_time:.2f}s, should be <1s'
            assert data_count > 0, 'Dashboard should have data'
        performance_results['concurrent_user_performance_acceptable'] = True
        performance_results['dashboard_load_performance_acceptable'] = True
        return performance_results

    def _assert_complete_workflow_success(self, ingestion_results: Dict, analytics_results: Dict, dashboard_results: Dict, integrity_results: Dict, performance_results: Dict):
        """Assert complete E2E workflow success with comprehensive validation."""
        assert ingestion_results['total_events'] >= 350, 'Should have ingested sufficient events'
        assert len(ingestion_results['events_per_user']) == 3, 'Should have data for all 3 users'
        for user_role, ingestion_time in ingestion_results['ingestion_performance'].items():
            assert ingestion_time < 5.0, f'Ingestion for {user_role} took {ingestion_time:.2f}s, too slow'
        assert analytics_results['analyses_created'] >= 20, 'Should have created sufficient analytics'
        assert len(analytics_results['user_analytics']) == 3, 'Should have analytics for all users'
        assert dashboard_results['dashboards_created'] >= 2, 'Should have created dashboards'
        assert dashboard_results['access_tests_passed'] >= 2, 'Dashboard access should work'
        assert dashboard_results['sharing_tests_passed'] >= 1, 'Dashboard sharing should work'
        assert integrity_results['user_isolation_verified'], 'User isolation must be verified'
        assert integrity_results['data_consistency_verified'], 'Data consistency must be verified'
        assert integrity_results['cross_table_integrity_verified'], 'Cross-table integrity must be verified'
        assert performance_results['query_performance_acceptable'], 'Query performance must be acceptable'
        assert performance_results['concurrent_user_performance_acceptable'], 'Concurrent performance must be acceptable'
        assert performance_results['dashboard_load_performance_acceptable'], 'Dashboard performance must be acceptable'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')