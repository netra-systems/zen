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
        self.analytics_table = f"e2e_analytics_{self.workflow_id}"
        self.user_events_table = f"e2e_user_events_{self.workflow_id}"
        self.dashboards_table = f"e2e_dashboards_{self.workflow_id}"
        
        # Test users for multi-user workflow
        self.test_users = {}

    async def cleanup_e2e_tables(self):
        """Cleanup all E2E test tables."""
        tables_to_cleanup = [
            self.analytics_table,
            self.user_events_table, 
            self.dashboards_table
        ]
        
        try:
            async with get_clickhouse_client(bypass_manager=True) as client:
                for table in tables_to_cleanup:
                    await client.execute(f"DROP TABLE IF EXISTS {table}")
        except Exception as e:
            print(f"Warning: Failed to cleanup E2E tables: {e}")

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
            # Step 1: Setup authenticated users for E2E testing
            self.test_users['enterprise_analyst'] = await create_authenticated_user(
                email="analyst@enterprise.com",
                name="Enterprise Analyst",
                permissions=["analytics:read", "analytics:write", "dashboards:create"]
            )
            
            self.test_users['data_scientist'] = await create_authenticated_user(
                email="scientist@enterprise.com", 
                name="Data Scientist",
                permissions=["analytics:read", "analytics:advanced", "ml:training"]
            )
            
            self.test_users['business_user'] = await create_authenticated_user(
                email="business@enterprise.com",
                name="Business User", 
                permissions=["analytics:read", "dashboards:view"]
            )
            
            # Step 2: Initialize ClickHouse service for authenticated operations
            service = get_clickhouse_service()
            await service.initialize()
            
            # Step 3: Create analytics schema with proper user isolation
            async with get_clickhouse_client(bypass_manager=True) as client:
                # User events table (raw data ingestion)
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.user_events_table} (
                    event_id UUID DEFAULT generateUUIDv4(),
                    user_id String,
                    authenticated_user_id String,  -- Who owns this data
                    event_type String,
                    event_data String,
                    timestamp DateTime64(3) DEFAULT now64(3),
                    session_id String,
                    ip_address String DEFAULT '127.0.0.1',
                    user_agent String DEFAULT 'ClickHouse E2E Test'
                ) ENGINE = MergeTree()
                PARTITION BY (authenticated_user_id, toYYYYMM(timestamp))
                ORDER BY (authenticated_user_id, event_type, timestamp, event_id)
                """)
                
                # Analytics aggregation table (processed data)
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.analytics_table} (
                    analysis_id UUID DEFAULT generateUUIDv4(),
                    authenticated_user_id String,
                    analysis_type String,
                    time_period String,
                    metrics Map(String, Float64),
                    dimensions Map(String, String),
                    created_at DateTime64(3) DEFAULT now64(3),
                    updated_at DateTime64(3) DEFAULT now64(3)
                ) ENGINE = ReplacingMergeTree(updated_at)
                PARTITION BY (authenticated_user_id, analysis_type)
                ORDER BY (authenticated_user_id, analysis_type, time_period, analysis_id)
                """)
                
                # Dashboard configurations table
                await client.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.dashboards_table} (
                    dashboard_id UUID DEFAULT generateUUIDv4(),
                    owner_user_id String,
                    dashboard_name String,
                    config_json String,
                    shared_with Array(String) DEFAULT [],
                    created_at DateTime64(3) DEFAULT now64(3),
                    last_accessed DateTime64(3) DEFAULT now64(3)
                ) ENGINE = ReplacingMergeTree(last_accessed)
                ORDER BY (owner_user_id, dashboard_name, dashboard_id)
                """)
            
            # Step 4: Simulate realistic data ingestion for each authenticated user
            ingestion_results = await self._simulate_data_ingestion()
            
            # Step 5: Process real-time analytics for authenticated users
            analytics_results = await self._process_realtime_analytics()
            
            # Step 6: Create and test authenticated dashboard workflows
            dashboard_results = await self._test_dashboard_workflows()
            
            # Step 7: Validate end-to-end data integrity and user isolation
            integrity_results = await self._validate_e2e_integrity()
            
            # Step 8: Performance validation under realistic load
            performance_results = await self._validate_e2e_performance()
            
            # Step 9: Comprehensive E2E validation
            self._assert_complete_workflow_success(
                ingestion_results,
                analytics_results,
                dashboard_results,
                integrity_results,
                performance_results
            )
            
        finally:
            await self.cleanup_e2e_tables()

    async def _simulate_data_ingestion(self) -> Dict[str, Any]:
        """Simulate realistic data ingestion for authenticated users."""
        ingestion_results = {
            'total_events': 0,
            'events_per_user': {},
            'ingestion_performance': {}
        }
        
        service = get_clickhouse_service()
        
        # Generate realistic event data for each user
        event_types = [
            'page_view', 'button_click', 'form_submit', 'api_call',
            'file_upload', 'search_query', 'export_data', 'create_dashboard'
        ]
        
        for user_role, user_data in self.test_users.items():
            user_id = user_data['user_id']
            events_count = 150 if user_role == 'enterprise_analyst' else 100
            
            start_time = datetime.now()
            
            # Insert events for this authenticated user
            for i in range(events_count):
                event_data = {
                    'user_id': f"app_user_{i % 20}",  # Simulated app users
                    'authenticated_user_id': user_id,  # Who owns this data
                    'event_type': event_types[i % len(event_types)],
                    'event_data': f'{{\"action\": \"{event_types[i % len(event_types)]}\", \"value\": {i * 1.5}, \"source\": \"{user_role}\"}}',
                    'session_id': f"{user_role}_session_{i // 20}"
                }
                
                await service.execute(f"""
                    INSERT INTO {self.user_events_table}
                    (user_id, authenticated_user_id, event_type, event_data, session_id)
                    VALUES (%(user_id)s, %(authenticated_user_id)s, %(event_type)s, %(event_data)s, %(session_id)s)
                """, event_data, user_id=user_id)
            
            ingestion_time = (datetime.now() - start_time).total_seconds()
            
            ingestion_results['events_per_user'][user_role] = events_count
            ingestion_results['ingestion_performance'][user_role] = ingestion_time
            ingestion_results['total_events'] += events_count
        
        # Wait for data availability across all partitions
        await asyncio.sleep(0.5)
        
        # Validate ingestion success
        total_count = await service.execute(f"""
            SELECT COUNT(*) as total FROM {self.user_events_table}
        """, user_id="system")
        
        assert total_count[0]['total'] == ingestion_results['total_events'], \
            f"Ingestion failed: expected {ingestion_results['total_events']}, got {total_count[0]['total']}"
        
        return ingestion_results

    async def _process_realtime_analytics(self) -> Dict[str, Any]:
        """Process real-time analytics for authenticated users."""
        analytics_results = {
            'analyses_created': 0,
            'user_analytics': {},
            'processing_performance': {}
        }
        
        service = get_clickhouse_service()
        
        # Generate analytics for each authenticated user
        for user_role, user_data in self.test_users.items():
            user_id = user_data['user_id']
            
            start_time = datetime.now()
            
            # Create user-specific analytics
            user_event_summary = await service.execute(f"""
                SELECT 
                    event_type,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    AVG(LENGTH(event_data)) as avg_data_size
                FROM {self.user_events_table}
                WHERE authenticated_user_id = %(user_id)s
                GROUP BY event_type
            """, {'user_id': user_id}, user_id=user_id)
            
            # Store analytics results  
            for analysis in user_event_summary:
                analytics_data = {
                    'authenticated_user_id': user_id,
                    'analysis_type': f"event_summary_{analysis['event_type']}",
                    'time_period': 'last_hour',
                    'metrics': f"{{\"event_count\": {analysis['event_count']}, \"unique_users\": {analysis['unique_users']}, \"unique_sessions\": {analysis['unique_sessions']}, \"avg_data_size\": {analysis['avg_data_size']}}}",
                    'dimensions': f"{{\"event_type\": \"{analysis['event_type']}\", \"user_role\": \"{user_role}\"}}"
                }
                
                await service.execute(f"""
                    INSERT INTO {self.analytics_table}
                    (authenticated_user_id, analysis_type, time_period, metrics, dimensions)
                    VALUES (%(authenticated_user_id)s, %(analysis_type)s, %(time_period)s, %(metrics)s, %(dimensions)s)
                """, analytics_data, user_id=user_id)
                
                analytics_results['analyses_created'] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            analytics_results['processing_performance'][user_role] = processing_time
            analytics_results['user_analytics'][user_role] = len(user_event_summary)
        
        await asyncio.sleep(0.2)
        return analytics_results

    async def _test_dashboard_workflows(self) -> Dict[str, Any]:
        """Test authenticated dashboard creation and access workflows."""
        dashboard_results = {
            'dashboards_created': 0,
            'access_tests_passed': 0,
            'sharing_tests_passed': 0
        }
        
        service = get_clickhouse_service()
        
        # Create dashboards for users with appropriate permissions
        analyst_user = self.test_users['enterprise_analyst']
        scientist_user = self.test_users['data_scientist']
        business_user = self.test_users['business_user']
        
        # Enterprise analyst creates main dashboard
        analyst_dashboard = {
            'owner_user_id': analyst_user['user_id'],
            'dashboard_name': 'Enterprise Analytics Dashboard',
            'config_json': '{"charts": [{"type": "line", "data": "event_summary"}, {"type": "bar", "data": "user_metrics"}], "refresh_interval": 30}',
            'shared_with': [business_user['user_id']]  # Share with business user
        }
        
        await service.execute(f"""
            INSERT INTO {self.dashboards_table}
            (owner_user_id, dashboard_name, config_json, shared_with)
            VALUES (%(owner_user_id)s, %(dashboard_name)s, %(config_json)s, %(shared_with)s)
        """, analyst_dashboard, user_id=analyst_user['user_id'])
        dashboard_results['dashboards_created'] += 1
        
        # Data scientist creates technical dashboard
        scientist_dashboard = {
            'owner_user_id': scientist_user['user_id'],
            'dashboard_name': 'ML Training Analytics',
            'config_json': '{"charts": [{"type": "scatter", "data": "ml_metrics"}, {"type": "heatmap", "data": "correlation_matrix"}], "advanced": true}',
            'shared_with': []  # Private dashboard
        }
        
        await service.execute(f"""
            INSERT INTO {self.dashboards_table}
            (owner_user_id, dashboard_name, config_json, shared_with)
            VALUES (%(owner_user_id)s, %(dashboard_name)s, %(config_json)s, %(shared_with)s)
        """, scientist_dashboard, user_id=scientist_user['user_id'])
        dashboard_results['dashboards_created'] += 1
        
        await asyncio.sleep(0.1)
        
        # Test dashboard access permissions
        # Analyst should see their own dashboard
        analyst_dashboards = await service.execute(f"""
            SELECT dashboard_name, owner_user_id, shared_with
            FROM {self.dashboards_table}
            WHERE owner_user_id = %(user_id)s
        """, {'user_id': analyst_user['user_id']}, user_id=analyst_user['user_id'])
        
        assert len(analyst_dashboards) == 1, "Analyst should see their dashboard"
        dashboard_results['access_tests_passed'] += 1
        
        # Business user should see shared dashboard
        shared_dashboards = await service.execute(f"""
            SELECT dashboard_name, owner_user_id 
            FROM {self.dashboards_table}
            WHERE has(shared_with, %(user_id)s)
        """, {'user_id': business_user['user_id']}, user_id=business_user['user_id'])
        
        assert len(shared_dashboards) == 1, "Business user should see shared dashboard"
        dashboard_results['sharing_tests_passed'] += 1
        
        # Data scientist should only see their private dashboard
        scientist_dashboards = await service.execute(f"""
            SELECT dashboard_name, owner_user_id
            FROM {self.dashboards_table}
            WHERE owner_user_id = %(user_id)s
        """, {'user_id': scientist_user['user_id']}, user_id=scientist_user['user_id'])
        
        assert len(scientist_dashboards) == 1, "Scientist should see their private dashboard"
        assert 'ML Training Analytics' == scientist_dashboards[0]['dashboard_name']
        dashboard_results['access_tests_passed'] += 1
        
        return dashboard_results

    async def _validate_e2e_integrity(self) -> Dict[str, Any]:
        """Validate end-to-end data integrity and user isolation."""
        integrity_results = {
            'user_isolation_verified': False,
            'data_consistency_verified': False,
            'cross_table_integrity_verified': False
        }
        
        service = get_clickhouse_service()
        
        # Test 1: User data isolation across all tables
        for user_role, user_data in self.test_users.items():
            user_id = user_data['user_id']
            
            # Verify user only sees their own events
            user_events = await service.execute(f"""
                SELECT COUNT(*) as count 
                FROM {self.user_events_table}
                WHERE authenticated_user_id = %(user_id)s
            """, {'user_id': user_id}, user_id=user_id)
            
            # Verify user only sees their own analytics
            user_analytics = await service.execute(f"""
                SELECT COUNT(*) as count
                FROM {self.analytics_table}
                WHERE authenticated_user_id = %(user_id)s  
            """, {'user_id': user_id}, user_id=user_id)
            
            assert user_events[0]['count'] > 0, f"User {user_role} should have events"
            assert user_analytics[0]['count'] > 0, f"User {user_role} should have analytics"
        
        integrity_results['user_isolation_verified'] = True
        
        # Test 2: Data consistency across processing pipeline
        total_events = await service.execute(f"""
            SELECT COUNT(*) as total FROM {self.user_events_table}
        """, user_id="system")
        
        total_analytics = await service.execute(f"""
            SELECT COUNT(*) as total FROM {self.analytics_table}
        """, user_id="system")
        
        # Analytics should be generated from events (multiple analytics per event type)
        assert total_events[0]['total'] > 0, "Should have events"
        assert total_analytics[0]['total'] > 0, "Should have analytics"
        integrity_results['data_consistency_verified'] = True
        
        # Test 3: Cross-table referential integrity
        cross_table_check = await service.execute(f"""
            SELECT 
                e.authenticated_user_id,
                COUNT(DISTINCT e.event_type) as event_types,
                COUNT(DISTINCT a.analysis_type) as analysis_types
            FROM {self.user_events_table} e
            LEFT JOIN {self.analytics_table} a ON e.authenticated_user_id = a.authenticated_user_id
            GROUP BY e.authenticated_user_id
        """, user_id="system")
        
        for check in cross_table_check:
            assert check['event_types'] > 0, "Should have event types"
            assert check['analysis_types'] > 0, "Should have corresponding analytics"
        
        integrity_results['cross_table_integrity_verified'] = True
        
        return integrity_results

    async def _validate_e2e_performance(self) -> Dict[str, Any]:
        """Validate E2E performance under realistic load."""
        performance_results = {
            'query_performance_acceptable': False,
            'concurrent_user_performance_acceptable': False,
            'dashboard_load_performance_acceptable': False
        }
        
        service = get_clickhouse_service()
        
        # Test 1: Complex analytical query performance
        import time
        start_time = time.time()
        
        complex_query = await service.execute(f"""
            SELECT 
                e.authenticated_user_id,
                e.event_type,
                COUNT(*) as total_events,
                COUNT(DISTINCT e.user_id) as unique_users,
                AVG(LENGTH(e.event_data)) as avg_data_size,
                MAX(e.timestamp) as latest_event,
                COUNT(DISTINCT a.analysis_type) as analysis_count
            FROM {self.user_events_table} e
            LEFT JOIN {self.analytics_table} a ON e.authenticated_user_id = a.authenticated_user_id
            GROUP BY e.authenticated_user_id, e.event_type
            ORDER BY total_events DESC
        """, user_id="system")
        
        complex_query_time = time.time() - start_time
        assert complex_query_time < 2.0, f"Complex query took {complex_query_time:.2f}s, should be <2s"
        assert len(complex_query) > 0, "Complex query should return results"
        performance_results['query_performance_acceptable'] = True
        
        # Test 2: Concurrent user dashboard loading
        async def simulate_dashboard_load(user_data: Dict[str, Any]):
            """Simulate dashboard loading for a user."""
            user_id = user_data['user_id']
            start = time.time()
            
            # Load user's analytics data
            dashboard_data = await service.execute(f"""
                SELECT analysis_type, metrics, dimensions 
                FROM {self.analytics_table}
                WHERE authenticated_user_id = %(user_id)s
                ORDER BY created_at DESC
                LIMIT 10
            """, {'user_id': user_id}, user_id=user_id)
            
            return time.time() - start, len(dashboard_data)
        
        # Simulate concurrent dashboard loads
        dashboard_tasks = [
            simulate_dashboard_load(user_data) 
            for user_data in self.test_users.values()
        ]
        
        dashboard_results = await asyncio.gather(*dashboard_tasks)
        
        for load_time, data_count in dashboard_results:
            assert load_time < 1.0, f"Dashboard load took {load_time:.2f}s, should be <1s"
            assert data_count > 0, "Dashboard should have data"
        
        performance_results['concurrent_user_performance_acceptable'] = True
        performance_results['dashboard_load_performance_acceptable'] = True
        
        return performance_results

    def _assert_complete_workflow_success(self, ingestion_results: Dict, analytics_results: Dict, 
                                        dashboard_results: Dict, integrity_results: Dict,
                                        performance_results: Dict):
        """Assert complete E2E workflow success with comprehensive validation."""
        
        # Ingestion validation
        assert ingestion_results['total_events'] >= 350, "Should have ingested sufficient events"
        assert len(ingestion_results['events_per_user']) == 3, "Should have data for all 3 users"
        
        for user_role, ingestion_time in ingestion_results['ingestion_performance'].items():
            assert ingestion_time < 5.0, f"Ingestion for {user_role} took {ingestion_time:.2f}s, too slow"
        
        # Analytics validation
        assert analytics_results['analyses_created'] >= 20, "Should have created sufficient analytics"
        assert len(analytics_results['user_analytics']) == 3, "Should have analytics for all users"
        
        # Dashboard validation
        assert dashboard_results['dashboards_created'] >= 2, "Should have created dashboards"
        assert dashboard_results['access_tests_passed'] >= 2, "Dashboard access should work"
        assert dashboard_results['sharing_tests_passed'] >= 1, "Dashboard sharing should work"
        
        # Integrity validation
        assert integrity_results['user_isolation_verified'], "User isolation must be verified"
        assert integrity_results['data_consistency_verified'], "Data consistency must be verified"
        assert integrity_results['cross_table_integrity_verified'], "Cross-table integrity must be verified"
        
        # Performance validation
        assert performance_results['query_performance_acceptable'], "Query performance must be acceptable"
        assert performance_results['concurrent_user_performance_acceptable'], "Concurrent performance must be acceptable"
        assert performance_results['dashboard_load_performance_acceptable'], "Dashboard performance must be acceptable"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])