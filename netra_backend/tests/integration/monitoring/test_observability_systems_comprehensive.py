"""
Test Observability Systems Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal, Enterprise customers
- Business Goal: System reliability and operational excellence
- Value Impact: Enables proactive issue detection and resolution
- Strategic Impact: Foundation for SLA compliance and customer trust

CRITICAL REQUIREMENTS:
- Tests real logging, metrics, and monitoring systems
- Validates data collection accuracy and alerting
- Ensures observability in production scenarios
- No mocks - uses real observability infrastructure
"""
import asyncio
import pytest
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid
from contextlib import asynccontextmanager
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env
from netra_backend.app.monitoring.websocket_metrics import WebSocketMetricsCollector
from netra_backend.app.monitoring.websocket_dashboard import WebSocketDashboard
from netra_backend.app.db.observability_core import ObservabilityCore
from netra_backend.app.db.observability_metrics import MetricsCollector
from netra_backend.app.db.observability_alerts import AlertManager

class ObservabilitySystemsComprehensiveTests(SSotBaseTestCase):
    """
    Comprehensive observability systems tests.
    
    Tests critical monitoring infrastructure that ensures business continuity:
    - Logging accuracy and structured data
    - Metrics collection and aggregation  
    - Alert triggering and notification
    - Performance monitoring and SLA tracking
    - Business KPI monitoring
    """

    def setup_method(self):
        """Set up test environment for each test method."""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.isolated_helper = IsolatedTestHelper()
        self.test_prefix = f'observability_{uuid.uuid4().hex[:8]}'

    async def setup_observability_system(self) -> Tuple[ObservabilityCore, MetricsCollector, AlertManager]:
        """Set up observability system with real infrastructure."""
        observability = ObservabilityCore()
        metrics_collector = MetricsCollector()
        alert_manager = AlertManager()
        await observability.initialize()
        await metrics_collector.initialize()
        await alert_manager.initialize()
        return (observability, metrics_collector, alert_manager)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_structured_logging_accuracy_and_searchability(self):
        """
        Test structured logging accuracy and searchability.
        
        BUSINESS CRITICAL: Accurate logs enable fast incident resolution.
        Poor logging increases mean time to recovery (MTTR).
        """
        observability, metrics_collector, alert_manager = await self.setup_observability_system()
        try:
            test_logger = logging.getLogger(f'test.{self.test_prefix}')
            test_logger.setLevel(logging.INFO)
            test_scenarios = [{'level': 'INFO', 'message': 'User authentication successful', 'structured_data': {'user_id': f'user_{uuid.uuid4().hex[:8]}', 'ip_address': '192.168.1.100', 'user_agent': 'Mozilla/5.0 Test Browser', 'authentication_method': 'JWT', 'session_duration': 1800}, 'expected_fields': ['user_id', 'ip_address', 'authentication_method']}, {'level': 'WARNING', 'message': 'Rate limit approaching for user', 'structured_data': {'user_id': f'user_{uuid.uuid4().hex[:8]}', 'current_requests': 95, 'rate_limit': 100, 'window_seconds': 60, 'remaining_requests': 5}, 'expected_fields': ['user_id', 'current_requests', 'rate_limit']}, {'level': 'ERROR', 'message': 'Database connection failed', 'structured_data': {'database_name': 'production_postgres', 'error_code': 'CONN_TIMEOUT', 'connection_attempts': 3, 'last_error': 'Connection timed out after 30s', 'affected_operations': ['user_login', 'data_query']}, 'expected_fields': ['database_name', 'error_code', 'connection_attempts']}, {'level': 'CRITICAL', 'message': 'Service degradation detected', 'structured_data': {'service_name': 'agent_execution_engine', 'degradation_type': 'response_time', 'current_latency_ms': 5000, 'sla_threshold_ms': 2000, 'affected_users': 150, 'business_impact': 'HIGH'}, 'expected_fields': ['service_name', 'degradation_type', 'business_impact']}]
            logged_entries = []
            for scenario in test_scenarios:
                log_entry = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level': scenario['level'], 'message': scenario['message'], 'test_id': f'{self.test_prefix}_{len(logged_entries)}', **scenario['structured_data']}
                await observability.log_structured_event(level=scenario['level'], message=scenario['message'], structured_data=log_entry)
                logged_entries.append({'scenario': scenario, 'log_entry': log_entry, 'timestamp': datetime.now()})
                await asyncio.sleep(0.1)
            await asyncio.sleep(2.0)
            for logged_entry in logged_entries:
                scenario = logged_entry['scenario']
                log_data = logged_entry['log_entry']
                test_id = log_data['test_id']
                search_result = await observability.search_logs(query={'test_id': test_id}, time_range_minutes=5)
                assert len(search_result.entries) > 0, f'Log entry not found: {test_id}'
                found_entry = search_result.entries[0]
                for field in scenario['expected_fields']:
                    assert field in found_entry.data, f"Expected field '{field}' missing from log entry {test_id}"
                    expected_value = log_data[field]
                    actual_value = found_entry.data[field]
                    assert actual_value == expected_value, f'Field value mismatch in {test_id}: expected {expected_value}, got {actual_value}'
                assert found_entry.level == scenario['level'], f"Log level mismatch: expected {scenario['level']}, got {found_entry.level}"
                assert scenario['message'] in found_entry.message, f"Message not preserved: expected '{scenario['message']}' in '{found_entry.message}'"
            error_logs = await observability.search_logs(query={'level': 'ERROR'}, time_range_minutes=5)
            error_count = len([e for e in logged_entries if e['scenario']['level'] == 'ERROR'])
            assert len(error_logs.entries) >= error_count, f'Error log aggregation failed: expected at least {error_count}, got {len(error_logs.entries)}'
            high_impact_logs = await observability.search_logs(query={'business_impact': 'HIGH'}, time_range_minutes=5)
            assert len(high_impact_logs.entries) >= 1, 'High impact logs not properly indexed'
        finally:
            await observability.cleanup_test_data(test_prefix=self.test_prefix)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_metrics_collection_and_business_kpi_tracking(self):
        """
        Test metrics collection and business KPI tracking.
        
        BUSINESS CRITICAL: Accurate metrics drive business decisions.
        Incorrect metrics lead to wrong strategic choices.
        """
        observability, metrics_collector, alert_manager = await self.setup_observability_system()
        try:
            business_kpis = [{'name': 'user_registrations', 'type': 'counter', 'business_value': 'Growth tracking', 'test_values': [1, 1, 1, 1, 1]}, {'name': 'agent_executions', 'type': 'counter', 'business_value': 'Usage tracking', 'test_values': [1, 2, 1, 3, 2]}, {'name': 'revenue_generated', 'type': 'gauge', 'business_value': 'Revenue tracking', 'test_values': [100.0, 150.0, 200.0, 175.0, 225.0]}, {'name': 'response_time_ms', 'type': 'histogram', 'business_value': 'Performance SLA', 'test_values': [150, 200, 180, 220, 190]}, {'name': 'error_rate', 'type': 'gauge', 'business_value': 'Reliability tracking', 'test_values': [0.01, 0.02, 0.015, 0.03, 0.018]}]
            collection_start = datetime.now()
            for time_step in range(5):
                timestamp = collection_start + timedelta(seconds=time_step * 10)
                for kpi in business_kpis:
                    metric_value = kpi['test_values'][time_step]
                    await metrics_collector.record_metric(name=kpi['name'], value=metric_value, metric_type=kpi['type'], tags={'test_id': self.test_prefix, 'business_kpi': 'true', 'time_step': str(time_step)}, timestamp=timestamp)
                await asyncio.sleep(1.0)
            await asyncio.sleep(3.0)
            for kpi in business_kpis:
                metrics_result = await metrics_collector.query_metrics(metric_name=kpi['name'], time_range_minutes=5, tags={'test_id': self.test_prefix})
                assert len(metrics_result.data_points) >= 5, f"Insufficient data points for {kpi['name']}: expected 5, got {len(metrics_result.data_points)}"
                recorded_values = [dp.value for dp in metrics_result.data_points]
                expected_values = kpi['test_values']
                if kpi['type'] == 'counter':
                    for expected_val in expected_values:
                        assert any((abs(recorded - expected_val) < 0.01 for recorded in recorded_values)), f"Counter value {expected_val} not found in {kpi['name']} recordings"
                elif kpi['type'] in ['gauge', 'histogram']:
                    for i, expected_val in enumerate(expected_values):
                        if i < len(recorded_values):
                            recorded_val = recorded_values[i]
                            assert abs(recorded_val - expected_val) < 0.01, f"Value mismatch for {kpi['name']} at step {i}: expected {expected_val}, got {recorded_val}"
            total_registrations = await metrics_collector.aggregate_metric(metric_name='user_registrations', aggregation='SUM', time_range_minutes=5, tags={'test_id': self.test_prefix})
            expected_total_registrations = sum(business_kpis[0]['test_values'])
            assert abs(total_registrations - expected_total_registrations) < 0.01, f'Registration aggregation incorrect: expected {expected_total_registrations}, got {total_registrations}'
            avg_response_time = await metrics_collector.aggregate_metric(metric_name='response_time_ms', aggregation='AVERAGE', time_range_minutes=5, tags={'test_id': self.test_prefix})
            expected_avg_response = sum(business_kpis[3]['test_values']) / len(business_kpis[3]['test_values'])
            assert abs(avg_response_time - expected_avg_response) < 5.0, f'Response time aggregation incorrect: expected {expected_avg_response}, got {avg_response_time}'
            dashboard_metrics = await metrics_collector.get_business_dashboard_metrics(time_range_minutes=5, tags={'test_id': self.test_prefix})
            assert 'user_registrations' in dashboard_metrics, 'User registrations missing from dashboard'
            assert 'agent_executions' in dashboard_metrics, 'Agent executions missing from dashboard'
            assert 'revenue_generated' in dashboard_metrics, 'Revenue missing from dashboard'
            dashboard_registrations = dashboard_metrics['user_registrations']['total']
            assert abs(dashboard_registrations - expected_total_registrations) < 0.01, f'Dashboard registrations incorrect: expected {expected_total_registrations}, got {dashboard_registrations}'
        finally:
            await metrics_collector.cleanup_test_data(test_prefix=self.test_prefix)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_alert_system_and_incident_detection(self):
        """
        Test alert system and automated incident detection.
        
        BUSINESS CRITICAL: Timely alerts prevent service outages.
        Late detection leads to customer churn and revenue loss.
        """
        observability, metrics_collector, alert_manager = await self.setup_observability_system()
        try:
            alert_rules = [{'name': 'high_error_rate', 'description': 'Error rate exceeds SLA threshold', 'metric': 'error_rate', 'condition': 'greater_than', 'threshold': 0.05, 'severity': 'HIGH', 'business_impact': 'Customer experience degradation'}, {'name': 'slow_response_time', 'description': 'Response time exceeds SLA', 'metric': 'response_time_ms', 'condition': 'greater_than', 'threshold': 2000, 'severity': 'MEDIUM', 'business_impact': 'User experience impact'}, {'name': 'low_agent_success_rate', 'description': 'Agent success rate below threshold', 'metric': 'agent_success_rate', 'condition': 'less_than', 'threshold': 0.95, 'severity': 'HIGH', 'business_impact': 'Core product functionality degraded'}, {'name': 'revenue_drop', 'description': 'Revenue drops significantly', 'metric': 'hourly_revenue', 'condition': 'percent_decrease', 'threshold': 0.25, 'severity': 'CRITICAL', 'business_impact': 'Direct revenue impact'}]
            for rule in alert_rules:
                await alert_manager.create_alert_rule(name=f"{self.test_prefix}_{rule['name']}", description=rule['description'], metric_name=rule['metric'], condition=rule['condition'], threshold=rule['threshold'], severity=rule['severity'], tags={'test_id': self.test_prefix, 'business_impact': rule['business_impact']})
            normal_metrics = [{'name': 'error_rate', 'value': 0.02}, {'name': 'response_time_ms', 'value': 1500}, {'name': 'agent_success_rate', 'value': 0.98}, {'name': 'hourly_revenue', 'value': 1000.0}]
            for metric in normal_metrics:
                await metrics_collector.record_metric(name=metric['name'], value=metric['value'], metric_type='gauge', tags={'test_id': self.test_prefix, 'scenario': 'normal'})
            await asyncio.sleep(2.0)
            active_alerts = await alert_manager.get_active_alerts(tags={'test_id': self.test_prefix})
            normal_scenario_alerts = [a for a in active_alerts if 'scenario:normal' in str(a.tags)]
            assert len(normal_scenario_alerts) == 0, f'False positive alerts triggered: {[a.name for a in normal_scenario_alerts]}'
            alert_scenarios = [{'scenario': 'high_error_rate', 'metrics': [{'name': 'error_rate', 'value': 0.08}], 'expected_alerts': ['high_error_rate'], 'expected_severity': 'HIGH'}, {'scenario': 'performance_degradation', 'metrics': [{'name': 'response_time_ms', 'value': 3000}, {'name': 'agent_success_rate', 'value': 0.9}], 'expected_alerts': ['slow_response_time', 'low_agent_success_rate'], 'expected_severity': 'HIGH'}, {'scenario': 'revenue_crisis', 'metrics': [{'name': 'hourly_revenue', 'value': 700.0}, {'name': 'error_rate', 'value': 0.12}], 'expected_alerts': ['revenue_drop', 'high_error_rate'], 'expected_severity': 'CRITICAL'}]
            triggered_alerts = []
            for scenario in alert_scenarios:
                for metric in scenario['metrics']:
                    await metrics_collector.record_metric(name=metric['name'], value=metric['value'], metric_type='gauge', tags={'test_id': self.test_prefix, 'scenario': scenario['scenario']})
                await asyncio.sleep(3.0)
                scenario_alerts = await alert_manager.get_active_alerts(tags={'test_id': self.test_prefix})
                scenario_alert_names = [a.name for a in scenario_alerts if scenario['scenario'] in str(a.tags)]
                for expected_alert in scenario['expected_alerts']:
                    expected_alert_full_name = f'{self.test_prefix}_{expected_alert}'
                    matching_alerts = [a for a in scenario_alerts if expected_alert in a.name]
                    assert len(matching_alerts) > 0, f"Expected alert '{expected_alert}' not triggered in scenario '{scenario['scenario']}'"
                    triggered_alert = matching_alerts[0]
                    triggered_alerts.append(triggered_alert)
                    if scenario['expected_severity'] == 'CRITICAL':
                        assert triggered_alert.severity in ['CRITICAL', 'HIGH'], f'Alert severity too low for critical scenario: {triggered_alert.severity}'
            for alert in triggered_alerts:
                notifications = await alert_manager.get_alert_notifications(alert.id)
                assert len(notifications) > 0, f'No notifications sent for alert {alert.name}'
                notification = notifications[0]
                assert alert.name in notification.title, f'Alert name missing from notification title: {notification.title}'
                assert 'business_impact' in notification.content.lower() or 'impact' in notification.content.lower(), f'Business impact missing from notification: {notification.content}'
            critical_alerts = [a for a in triggered_alerts if a.severity == 'CRITICAL']
            if critical_alerts:
                critical_alert = critical_alerts[0]
                await asyncio.sleep(2.0)
                escalations = await alert_manager.get_alert_escalations(critical_alert.id)
                assert len(escalations) > 0, f'No escalation configured for critical alert {critical_alert.name}'
        finally:
            await alert_manager.cleanup_test_alerts(test_prefix=self.test_prefix)
            await metrics_collector.cleanup_test_data(test_prefix=self.test_prefix)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_monitoring_and_sla_tracking(self):
        """
        Test performance monitoring and SLA compliance tracking.
        
        BUSINESS CRITICAL: SLA breaches trigger customer penalties.
        Must accurately track and report SLA compliance.
        """
        observability, metrics_collector, alert_manager = await self.setup_observability_system()
        try:
            sla_requirements = {'response_time_p95': {'threshold': 2000, 'unit': 'ms', 'penalty': 'customer_credits'}, 'uptime_percentage': {'threshold': 99.9, 'unit': 'percent', 'penalty': 'service_credits'}, 'agent_success_rate': {'threshold': 95.0, 'unit': 'percent', 'penalty': 'refund_eligible'}, 'error_rate_hourly': {'threshold': 1.0, 'unit': 'percent', 'penalty': 'escalation_required'}}
            performance_data = []
            sla_start_time = datetime.now(timezone.utc)
            for minute in range(100):
                timestamp = sla_start_time + timedelta(minutes=minute)
                if minute < 70:
                    scenario_data = {'response_time_ms': 1200 + minute % 10 * 50, 'success_rate': 0.98 + minute % 5 * 0.002, 'error_rate': 0.005 + minute % 3 * 0.001, 'uptime': 1.0}
                elif minute < 85:
                    degradation_factor = (minute - 70) / 15
                    scenario_data = {'response_time_ms': 1800 + degradation_factor * 400, 'success_rate': 0.96 - degradation_factor * 0.02, 'error_rate': 0.008 + degradation_factor * 0.005, 'uptime': 1.0}
                else:
                    breach_severity = (minute - 85) / 15
                    scenario_data = {'response_time_ms': 2500 + breach_severity * 1000, 'success_rate': 0.92 - breach_severity * 0.05, 'error_rate': 0.02 + breach_severity * 0.03, 'uptime': 0.95 - breach_severity * 0.1}
                await metrics_collector.record_metric(name='response_time_ms', value=scenario_data['response_time_ms'], metric_type='histogram', tags={'test_id': self.test_prefix, 'sla_tracking': 'true'}, timestamp=timestamp)
                await metrics_collector.record_metric(name='agent_success_rate', value=scenario_data['success_rate'] * 100, metric_type='gauge', tags={'test_id': self.test_prefix, 'sla_tracking': 'true'}, timestamp=timestamp)
                await metrics_collector.record_metric(name='error_rate_hourly', value=scenario_data['error_rate'] * 100, metric_type='gauge', tags={'test_id': self.test_prefix, 'sla_tracking': 'true'}, timestamp=timestamp)
                await metrics_collector.record_metric(name='uptime_percentage', value=scenario_data['uptime'] * 100, metric_type='gauge', tags={'test_id': self.test_prefix, 'sla_tracking': 'true'}, timestamp=timestamp)
                performance_data.append({'minute': minute, 'timestamp': timestamp, 'data': scenario_data})
                if minute % 10 == 0:
                    await asyncio.sleep(0.5)
            await asyncio.sleep(3.0)
            sla_report = await observability.calculate_sla_compliance(start_time=sla_start_time, end_time=sla_start_time + timedelta(minutes=100), tags={'test_id': self.test_prefix, 'sla_tracking': 'true'})
            assert sla_report is not None, 'SLA report generation failed'
            response_time_p95 = sla_report.metrics['response_time_p95']
            assert response_time_p95 > sla_requirements['response_time_p95']['threshold'], f"SLA breach not detected: P95 response time {response_time_p95}ms should exceed {sla_requirements['response_time_p95']['threshold']}ms"
            avg_success_rate = sla_report.metrics['agent_success_rate_avg']
            assert avg_success_rate < sla_requirements['agent_success_rate']['threshold'], f"Success rate SLA breach not detected: {avg_success_rate}% should be below {sla_requirements['agent_success_rate']['threshold']}%"
            max_error_rate = sla_report.metrics['error_rate_max']
            assert max_error_rate > sla_requirements['error_rate_hourly']['threshold'], f"Error rate SLA breach not detected: {max_error_rate}% should exceed {sla_requirements['error_rate_hourly']['threshold']}%"
            avg_uptime = sla_report.metrics['uptime_percentage_avg']
            assert avg_uptime < sla_requirements['uptime_percentage']['threshold'], f"Uptime SLA breach not detected: {avg_uptime}% should be below {sla_requirements['uptime_percentage']['threshold']}%"
            breach_periods = sla_report.breach_periods
            assert len(breach_periods) > 0, 'SLA breach periods not identified'
            first_breach = breach_periods[0]
            breach_start_minute = (first_breach.start_time - sla_start_time).total_seconds() / 60
            assert 80 <= breach_start_minute <= 90, f'SLA breach timing incorrect: detected at minute {breach_start_minute}, expected around minute 85'
            business_impact = await observability.calculate_sla_business_impact(sla_report)
            assert business_impact.total_affected_users > 0, 'Business impact calculation missing affected users'
            assert business_impact.estimated_revenue_impact > 0, 'Business impact calculation missing revenue impact'
            assert business_impact.customer_credits_required > 0, 'Business impact calculation missing customer credits'
            if response_time_p95 > 3000 or avg_uptime < 95:
                assert business_impact.severity == 'HIGH', f'Business impact severity incorrect: expected HIGH for severe SLA breach, got {business_impact.severity}'
        finally:
            await observability.cleanup_test_data(test_prefix=self.test_prefix)
            await metrics_collector.cleanup_test_data(test_prefix=self.test_prefix)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')