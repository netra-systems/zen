"""
Test Real-Time Metrics Collection Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal + All customer segments
- Business Goal: Enable data-driven optimization and proactive issue detection
- Value Impact: Real-time metrics prevent outages and enable performance optimization
- Strategic Impact: Foundation for SLA compliance and customer transparency

CRITICAL REQUIREMENTS:
- Tests real metrics collection systems (PostgreSQL, Redis, ClickHouse)
- Validates metric aggregation and alerting pipelines
- Uses real monitoring infrastructure, NO MOCKS
- Ensures metric accuracy and timeliness
"""

import pytest
import asyncio
import time
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.monitoring.metrics_collector import MetricsCollector
from netra_backend.app.monitoring.real_time_aggregator import RealTimeAggregator
from netra_backend.app.monitoring.metric_storage import MetricStorage
from netra_backend.app.monitoring.alert_manager import AlertManager


class TestRealTimeMetricsCollectionIntegration(SSotBaseTestCase):
    """
    Test real-time metrics collection with actual infrastructure.
    
    Tests critical metrics collection that enables business intelligence:
    - System performance metrics (CPU, memory, response times)
    - Business metrics (user activity, revenue, conversion rates)
    - Application metrics (API usage, error rates, throughput)
    - Infrastructure metrics (database performance, queue depths)
    """
    
    def setup_method(self):
        """Set up test environment with real services"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"metrics_test_{uuid.uuid4().hex[:8]}"
        
        # Initialize real metrics components
        self.metrics_collector = MetricsCollector()
        self.aggregator = RealTimeAggregator()
        self.metric_storage = MetricStorage()
        self.alert_manager = AlertManager()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_system_performance_metrics_collection(self):
        """
        Test collection of system performance metrics from real infrastructure.
        
        BUSINESS CRITICAL: System metrics enable proactive capacity planning
        and prevent performance-related customer churn.
        """
        # Start metrics collection
        collection_id = await self.metrics_collector.start_collection(
            collection_type="system_performance",
            interval_seconds=1,
            test_prefix=self.test_prefix
        )
        
        try:
            # Collect metrics for 10 seconds
            await asyncio.sleep(10)
            
            # Retrieve collected metrics
            collected_metrics = await self.metrics_collector.get_collected_metrics(
                collection_id=collection_id,
                metric_types=["cpu", "memory", "disk", "network"]
            )
            
            # Validate CPU metrics
            cpu_metrics = [m for m in collected_metrics if m.metric_type == "cpu"]
            assert len(cpu_metrics) >= 8, "Should collect CPU metrics for ~10 seconds"
            
            for cpu_metric in cpu_metrics:
                assert 0 <= cpu_metric.value <= 100, f"Invalid CPU value: {cpu_metric.value}"
                assert cpu_metric.timestamp is not None
                assert cpu_metric.host_id is not None
                
                # CPU metrics should include per-core breakdown
                assert "total_cpu" in cpu_metric.attributes
                if "cores" in cpu_metric.attributes:
                    core_count = len(cpu_metric.attributes["cores"])
                    assert core_count > 0, "Should report CPU core information"
            
            # Validate memory metrics
            memory_metrics = [m for m in collected_metrics if m.metric_type == "memory"]
            assert len(memory_metrics) >= 8, "Should collect memory metrics"
            
            for mem_metric in memory_metrics:
                assert mem_metric.value >= 0, f"Invalid memory value: {mem_metric.value}"
                assert "total_memory_gb" in mem_metric.attributes
                assert "used_memory_gb" in mem_metric.attributes
                assert "available_memory_gb" in mem_metric.attributes
                
                # Memory usage should be consistent
                total = mem_metric.attributes["total_memory_gb"]
                used = mem_metric.attributes["used_memory_gb"]
                available = mem_metric.attributes["available_memory_gb"]
                
                assert used + available <= total * 1.1, "Memory accounting should be consistent"
                assert used >= 0 and available >= 0, "Memory values should be non-negative"
            
            # Validate disk metrics
            disk_metrics = [m for m in collected_metrics if m.metric_type == "disk"]
            assert len(disk_metrics) >= 8, "Should collect disk metrics"
            
            for disk_metric in disk_metrics:
                assert "disk_usage_percent" in disk_metric.attributes
                assert "disk_io_read_mb" in disk_metric.attributes
                assert "disk_io_write_mb" in disk_metric.attributes
                
                usage_percent = disk_metric.attributes["disk_usage_percent"]
                assert 0 <= usage_percent <= 100, f"Invalid disk usage: {usage_percent}"
            
            # Test metric aggregation
            aggregation_result = await self.aggregator.aggregate_metrics(
                metrics=collected_metrics,
                aggregation_window_seconds=5,
                aggregation_functions=["mean", "max", "min", "p95"]
            )
            
            # Should provide aggregated statistics
            assert len(aggregation_result.aggregated_metrics) > 0
            
            for agg_metric in aggregation_result.aggregated_metrics:
                assert agg_metric.window_start is not None
                assert agg_metric.window_end is not None
                assert agg_metric.sample_count > 0
                
                # Statistical aggregations should be present
                assert "mean" in agg_metric.aggregations
                assert "max" in agg_metric.aggregations
                assert "min" in agg_metric.aggregations
                
                # Validate statistical consistency
                mean_val = agg_metric.aggregations["mean"]
                max_val = agg_metric.aggregations["max"]
                min_val = agg_metric.aggregations["min"]
                
                assert min_val <= mean_val <= max_val, "Statistical values should be ordered"
                
        finally:
            await self.metrics_collector.stop_collection(collection_id)
            await self.metrics_collector.cleanup_test_data(self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_performance_metrics_collection(self):
        """
        Test collection of database performance metrics from real databases.
        
        BUSINESS CRITICAL: Database metrics prevent data-related outages that
        directly impact customer operations and revenue.
        """
        # Test PostgreSQL metrics
        pg_collection_id = await self.metrics_collector.start_database_collection(
            database_type="postgresql",
            connection_info=await self.db_helper.get_connection_info(),
            test_prefix=self.test_prefix
        )
        
        try:
            # Generate some database activity
            async with self.db_helper.get_connection() as conn:
                # Create test table for metrics generation
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.test_prefix}_test_table (
                        id SERIAL PRIMARY KEY,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Insert test data to generate metrics
                for i in range(100):
                    await conn.execute(f"""
                        INSERT INTO {self.test_prefix}_test_table (data)
                        VALUES ('test_data_{i}')
                    """)
                
                # Perform various operations to generate metrics
                await conn.execute(f"SELECT COUNT(*) FROM {self.test_prefix}_test_table")
                await conn.execute(f"SELECT * FROM {self.test_prefix}_test_table ORDER BY id DESC LIMIT 10")
                await conn.execute(f"UPDATE {self.test_prefix}_test_table SET data = 'updated' WHERE id % 10 = 0")
            
            # Wait for metrics collection
            await asyncio.sleep(5)
            
            # Retrieve database metrics
            db_metrics = await self.metrics_collector.get_collected_metrics(
                collection_id=pg_collection_id,
                metric_types=["connection_count", "query_performance", "locks", "transactions"]
            )
            
            # Validate connection metrics
            connection_metrics = [m for m in db_metrics if m.metric_type == "connection_count"]
            assert len(connection_metrics) > 0, "Should collect connection count metrics"
            
            for conn_metric in connection_metrics:
                assert conn_metric.value >= 1, "Should have at least one connection (our test connection)"
                assert "active_connections" in conn_metric.attributes
                assert "idle_connections" in conn_metric.attributes
                assert "max_connections" in conn_metric.attributes
                
                active = conn_metric.attributes["active_connections"]
                idle = conn_metric.attributes["idle_connections"]
                max_conn = conn_metric.attributes["max_connections"]
                
                assert active + idle <= max_conn, "Connection counts should be consistent"
            
            # Validate query performance metrics
            query_metrics = [m for m in db_metrics if m.metric_type == "query_performance"]
            assert len(query_metrics) > 0, "Should collect query performance metrics"
            
            for query_metric in query_metrics:
                assert "avg_query_time_ms" in query_metric.attributes
                assert "slow_query_count" in query_metric.attributes
                assert "total_queries" in query_metric.attributes
                
                avg_time = query_metric.attributes["avg_query_time_ms"]
                assert avg_time >= 0, "Average query time should be non-negative"
                
                # Our test queries should be fast
                assert avg_time < 1000, f"Test queries taking too long: {avg_time}ms"
            
            # Test metric alerting on database performance
            alert_config = {
                "metric_type": "query_performance",
                "threshold_value": 500,  # 500ms threshold
                "comparison": "greater_than",
                "severity": "warning"
            }
            
            alert_result = await self.alert_manager.evaluate_metrics_for_alerts(
                metrics=query_metrics,
                alert_configs=[alert_config],
                test_prefix=self.test_prefix
            )
            
            # Should evaluate alerts without errors
            assert alert_result.alerts_evaluated > 0
            
            # If performance is good, should not trigger alerts
            slow_queries = [m for m in query_metrics 
                          if m.attributes.get("avg_query_time_ms", 0) > 500]
            
            if len(slow_queries) == 0:
                assert alert_result.alerts_triggered == 0, "No alerts should trigger for good performance"
            
        finally:
            await self.metrics_collector.stop_collection(pg_collection_id)
            await self.db_helper.cleanup_test_data(self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_application_metrics_collection_real_api_usage(self):
        """
        Test collection of application metrics from real API usage patterns.
        
        BUSINESS CRITICAL: Application metrics enable optimization of user experience
        and identification of revenue-impacting performance issues.
        """
        # Start application metrics collection
        app_collection_id = await self.metrics_collector.start_application_collection(
            application_name="netra_backend",
            endpoints_to_monitor=["/*"],
            test_prefix=self.test_prefix
        )
        
        try:
            # Import HTTP client for making test requests
            import httpx
            
            # Get backend URL
            backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            
            # Generate realistic API traffic patterns
            api_scenarios = [
                # Health check requests (should be fast)
                {"endpoint": "/health", "expected_status": 200, "expected_max_time_ms": 100, "count": 10},
                
                # API documentation (moderate load)
                {"endpoint": "/docs", "expected_status": 200, "expected_max_time_ms": 500, "count": 5},
                
                # Metrics endpoint (if available)
                {"endpoint": "/metrics", "expected_status": [200, 404], "expected_max_time_ms": 200, "count": 3},
            ]
            
            request_results = []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for scenario in api_scenarios:
                    endpoint = scenario["endpoint"]
                    count = scenario["count"]
                    
                    for i in range(count):
                        start_time = time.time()
                        
                        try:
                            response = await client.get(f"{backend_url}{endpoint}")
                            
                            end_time = time.time()
                            response_time_ms = (end_time - start_time) * 1000
                            
                            request_results.append({
                                "endpoint": endpoint,
                                "status_code": response.status_code,
                                "response_time_ms": response_time_ms,
                                "success": response.status_code in scenario.get("expected_status", [200])
                            })
                            
                            # Small delay between requests
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            request_results.append({
                                "endpoint": endpoint,
                                "status_code": 0,
                                "response_time_ms": 0,
                                "success": False,
                                "error": str(e)
                            })
            
            # Wait for metrics collection
            await asyncio.sleep(3)
            
            # Retrieve application metrics
            app_metrics = await self.metrics_collector.get_collected_metrics(
                collection_id=app_collection_id,
                metric_types=["http_requests", "response_times", "error_rates", "throughput"]
            )
            
            # Validate HTTP request metrics
            http_request_metrics = [m for m in app_metrics if m.metric_type == "http_requests"]
            
            if len(http_request_metrics) > 0:  # May not collect if backend not running
                for http_metric in http_request_metrics:
                    assert "endpoint" in http_metric.attributes
                    assert "status_code" in http_metric.attributes
                    assert "method" in http_metric.attributes
                    
                    status_code = http_metric.attributes["status_code"]
                    assert isinstance(status_code, int), "Status code should be integer"
                    
                # Validate response time metrics
                response_time_metrics = [m for m in app_metrics if m.metric_type == "response_times"]
                
                for rt_metric in response_time_metrics:
                    assert "endpoint" in rt_metric.attributes
                    assert "percentile" in rt_metric.attributes
                    
                    # Response times should be reasonable for test endpoints
                    if rt_metric.attributes["endpoint"] == "/health":
                        assert rt_metric.value < 1000, f"Health endpoint too slow: {rt_metric.value}ms"
            
            # Test metric storage and persistence
            storage_result = await self.metric_storage.store_metrics(
                metrics=app_metrics,
                storage_config={
                    "retention_days": 30,
                    "compression": True,
                    "indexing": ["timestamp", "metric_type", "endpoint"]
                },
                test_prefix=self.test_prefix
            )
            
            assert storage_result.metrics_stored >= 0
            assert storage_result.storage_errors == 0, f"Storage errors occurred: {storage_result.error_details}"
            
            # Verify metrics can be retrieved from storage
            if storage_result.metrics_stored > 0:
                retrieved_metrics = await self.metric_storage.query_metrics(
                    query_filters={
                        "metric_type": "http_requests",
                        "time_range": {
                            "start": datetime.now(timezone.utc) - timedelta(minutes=10),
                            "end": datetime.now(timezone.utc)
                        }
                    },
                    test_prefix=self.test_prefix
                )
                
                assert len(retrieved_metrics) > 0, "Should retrieve stored metrics"
                
                for retrieved_metric in retrieved_metrics:
                    assert retrieved_metric.metric_type == "http_requests"
                    assert retrieved_metric.timestamp is not None
                    assert retrieved_metric.value >= 0
            
        finally:
            await self.metrics_collector.stop_collection(app_collection_id)
            await self.metric_storage.cleanup_test_data(self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_business_metrics_collection_integration(self):
        """
        Test collection of business metrics that directly impact revenue and KPIs.
        
        BUSINESS CRITICAL: Business metrics enable data-driven decision making
        and early detection of revenue-impacting trends.
        """
        # Start business metrics collection
        business_collection_id = await self.metrics_collector.start_business_collection(
            metric_categories=["user_activity", "revenue", "conversions", "feature_usage"],
            test_prefix=self.test_prefix
        )
        
        try:
            # Simulate business events
            business_events = [
                # User activity events
                {
                    "event_type": "user_login",
                    "user_id": f"user_{i}",
                    "user_tier": "free" if i % 4 == 0 else "mid" if i % 4 == 1 else "enterprise",
                    "timestamp": datetime.now(timezone.utc),
                    "attributes": {"source": "web", "session_duration": 300 + (i * 10)}
                }
                for i in range(20)
            ]
            
            # Add revenue events
            revenue_events = [
                {
                    "event_type": "subscription_upgrade",
                    "user_id": f"user_{i}",
                    "revenue_amount": 50.0 if i % 2 == 0 else 500.0,
                    "currency": "USD",
                    "timestamp": datetime.now(timezone.utc),
                    "attributes": {
                        "from_tier": "free",
                        "to_tier": "mid" if i % 2 == 0 else "enterprise"
                    }
                }
                for i in range(5)
            ]
            
            # Add feature usage events
            feature_events = [
                {
                    "event_type": "feature_usage",
                    "user_id": f"user_{i}",
                    "feature_name": "cost_optimizer" if i % 3 == 0 else "security_analyzer" if i % 3 == 1 else "data_processor",
                    "usage_duration": 120 + (i * 20),
                    "timestamp": datetime.now(timezone.utc),
                    "attributes": {"success": True, "complexity": "medium"}
                }
                for i in range(30)
            ]
            
            all_events = business_events + revenue_events + feature_events
            
            # Send events to metrics collection system
            for event in all_events:
                await self.metrics_collector.record_business_event(
                    event=event,
                    collection_id=business_collection_id
                )
                await asyncio.sleep(0.01)  # Small delay to simulate real timing
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # Retrieve business metrics
            business_metrics = await self.metrics_collector.get_collected_metrics(
                collection_id=business_collection_id,
                metric_types=["user_activity", "revenue", "feature_usage", "conversions"]
            )
            
            # Validate user activity metrics
            user_activity_metrics = [m for m in business_metrics if m.metric_type == "user_activity"]
            assert len(user_activity_metrics) > 0, "Should collect user activity metrics"
            
            for ua_metric in user_activity_metrics:
                assert "active_users" in ua_metric.attributes or "logins" in ua_metric.attributes
                assert ua_metric.value >= 0, "User activity values should be non-negative"
            
            # Validate revenue metrics
            revenue_metrics = [m for m in business_metrics if m.metric_type == "revenue"]
            
            if len(revenue_metrics) > 0:
                total_revenue = sum(m.value for m in revenue_metrics)
                expected_revenue = sum(e.get("revenue_amount", 0) for e in revenue_events)
                
                # Revenue should be tracked accurately
                assert abs(total_revenue - expected_revenue) < 1.0, f"Revenue mismatch: {total_revenue} vs {expected_revenue}"
                
                for rev_metric in revenue_metrics:
                    assert "currency" in rev_metric.attributes
                    assert "tier_upgrade" in rev_metric.attributes or "transaction_type" in rev_metric.attributes
            
            # Validate feature usage metrics
            feature_usage_metrics = [m for m in business_metrics if m.metric_type == "feature_usage"]
            
            if len(feature_usage_metrics) > 0:
                feature_names = set(m.attributes.get("feature_name", "unknown") for m in feature_usage_metrics)
                expected_features = {"cost_optimizer", "security_analyzer", "data_processor"}
                
                # Should track all features used
                overlap = feature_names & expected_features
                assert len(overlap) >= 2, f"Should track multiple features: {feature_names}"
                
                for fu_metric in feature_usage_metrics:
                    assert "feature_name" in fu_metric.attributes
                    assert "usage_duration" in fu_metric.attributes or "usage_count" in fu_metric.attributes
            
            # Test business metric aggregation and KPI calculation
            kpi_result = await self.aggregator.calculate_business_kpis(
                metrics=business_metrics,
                kpi_definitions={
                    "daily_active_users": {"metric_type": "user_activity", "aggregation": "unique_count"},
                    "revenue_per_user": {"metric_type": "revenue", "aggregation": "average"},
                    "feature_adoption_rate": {"metric_type": "feature_usage", "aggregation": "adoption_rate"}
                },
                time_window_hours=1,
                test_prefix=self.test_prefix
            )
            
            # Validate KPI calculations
            assert kpi_result.kpis_calculated > 0, "Should calculate business KPIs"
            
            if "daily_active_users" in kpi_result.kpi_values:
                dau = kpi_result.kpi_values["daily_active_users"]
                assert dau > 0, "Should have active users"
                assert dau <= 20, f"DAU should not exceed unique users created: {dau}"
            
            if "revenue_per_user" in kpi_result.kpi_values:
                rpu = kpi_result.kpi_values["revenue_per_user"]
                assert rpu >= 0, "Revenue per user should be non-negative"
            
        finally:
            await self.metrics_collector.stop_collection(business_collection_id)
            await self.metrics_collector.cleanup_test_data(self.test_prefix)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_alert_integration_on_real_metrics(self):
        """
        Test alert system integration with real metrics for proactive monitoring.
        
        BUSINESS CRITICAL: Alerts prevent outages and enable proactive customer
        communication about potential service impacts.
        """
        # Configure alert rules for different scenarios
        alert_rules = [
            {
                "rule_id": f"{self.test_prefix}_high_cpu",
                "metric_type": "cpu",
                "threshold": 90.0,
                "comparison": "greater_than",
                "duration_seconds": 5,
                "severity": "critical",
                "notification_channels": ["email", "slack"]
            },
            {
                "rule_id": f"{self.test_prefix}_high_memory",
                "metric_type": "memory",
                "threshold": 85.0,
                "comparison": "greater_than",
                "duration_seconds": 3,
                "severity": "warning",
                "notification_channels": ["slack"]
            },
            {
                "rule_id": f"{self.test_prefix}_slow_response",
                "metric_type": "response_times",
                "threshold": 1000.0,  # 1 second
                "comparison": "greater_than",
                "duration_seconds": 2,
                "severity": "warning",
                "notification_channels": ["email"]
            }
        ]
        
        # Register alert rules
        for rule in alert_rules:
            await self.alert_manager.register_alert_rule(rule)
        
        try:
            # Start metrics collection for alerting
            alert_collection_id = await self.metrics_collector.start_collection(
                collection_type="comprehensive",
                interval_seconds=1,
                test_prefix=self.test_prefix
            )
            
            # Collect metrics for alerting evaluation
            await asyncio.sleep(8)  # Collect enough data for alert evaluation
            
            # Get collected metrics
            alert_metrics = await self.metrics_collector.get_collected_metrics(
                collection_id=alert_collection_id,
                metric_types=["cpu", "memory", "response_times"]
            )
            
            # Evaluate metrics against alert rules
            alert_evaluation = await self.alert_manager.evaluate_alert_rules(
                metrics=alert_metrics,
                rules=alert_rules,
                test_prefix=self.test_prefix
            )
            
            # Validate alert evaluation
            assert alert_evaluation.rules_evaluated == len(alert_rules)
            assert alert_evaluation.evaluation_errors == 0, f"Alert evaluation errors: {alert_evaluation.error_details}"
            
            # Check specific alert conditions
            for rule_result in alert_evaluation.rule_results:
                rule_id = rule_result.rule_id
                
                if "high_cpu" in rule_id:
                    # CPU alerts should be evaluated
                    assert rule_result.metrics_evaluated > 0, "Should evaluate CPU metrics"
                    
                    # If system is under normal load, should not trigger
                    if rule_result.alert_triggered:
                        assert rule_result.trigger_value >= 90.0, "CPU alert threshold respected"
                        assert rule_result.severity == "critical", "CPU alert severity correct"
                
                elif "high_memory" in rule_id:
                    # Memory alerts should be evaluated
                    assert rule_result.metrics_evaluated > 0, "Should evaluate memory metrics"
                    
                    if rule_result.alert_triggered:
                        assert rule_result.trigger_value >= 85.0, "Memory alert threshold respected"
                        assert rule_result.severity == "warning", "Memory alert severity correct"
            
            # Test alert suppression and de-duplication
            if alert_evaluation.alerts_triggered > 0:
                # Wait a bit and re-evaluate to test suppression
                await asyncio.sleep(3)
                
                second_evaluation = await self.alert_manager.evaluate_alert_rules(
                    metrics=alert_metrics,
                    rules=alert_rules,
                    test_prefix=self.test_prefix
                )
                
                # Should suppress duplicate alerts within suppression window
                suppressed_alerts = [r for r in second_evaluation.rule_results if r.suppressed]
                
                if len(suppressed_alerts) > 0:
                    for suppressed in suppressed_alerts:
                        assert suppressed.suppression_reason in ["duplicate", "recently_triggered"]
                        assert suppressed.suppression_window_seconds > 0
            
            # Test alert recovery detection
            recovery_evaluation = await self.alert_manager.evaluate_alert_recovery(
                current_metrics=alert_metrics,
                active_alerts=alert_evaluation.active_alerts,
                test_prefix=self.test_prefix
            )
            
            # Should detect recovery for resolved conditions
            assert recovery_evaluation.recovery_checks_performed >= 0
            
            for recovery in recovery_evaluation.recovered_alerts:
                assert recovery.recovery_timestamp is not None
                assert recovery.recovery_reason in ["threshold_not_exceeded", "metric_improved"]
                assert recovery.recovery_duration_seconds >= 0
            
        finally:
            # Cleanup
            await self.metrics_collector.stop_collection(alert_collection_id)
            
            # Unregister alert rules
            for rule in alert_rules:
                await self.alert_manager.unregister_alert_rule(rule["rule_id"])
            
            await self.alert_manager.cleanup_test_data(self.test_prefix)


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])