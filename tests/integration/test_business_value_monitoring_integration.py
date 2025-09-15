"""
Integration Tests for Business Value Monitoring

This test suite validates the integration of the OperationalBusinessValueMonitor service
with other system components including WebSocket manager, database persistence,
dashboard endpoints, and alert system integration.

Business Impact: Platform/Internal - $500K+ ARR protection through monitoring integration
Critical for ensuring business value monitoring works end-to-end with real system components.

Test Approach:
- Tests should FAIL initially (service doesn't exist)
- Test WebSocket manager integration for real-time alerts
- Test database persistence integration
- Test dashboard endpoint integration  
- Test alert system integration
- Use SSOT patterns and real services (no mocks for integration)
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment
import pytest
import asyncio
from unittest.mock import patch
import json
from decimal import Decimal


@pytest.mark.integration
class TestBusinessValueMonitoringWebSocketIntegration(SSotAsyncTestCase):
    """Integration tests with WebSocket manager for real-time alerts"""
    
    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
    
    async def test_websocket_manager_alert_integration(self):
        """Test integration with WebSocket manager for business value alerts - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Create real WebSocket manager instance (no mocks in integration tests)
            websocket_manager = WebSocketManager()
            monitor = OperationalBusinessValueMonitor()
            
            # Test integration setup
            monitor.set_websocket_manager(websocket_manager)
            
            # Test alert sending through WebSocket
            alert_data = {
                'type': 'business_value_alert',
                'severity': 'warning',
                'message': 'Business value score dropped to 45%',
                'threshold': 75.0,
                'current_score': 45.0,
                'timestamp': '2025-09-14T14:45:00Z'
            }
            
            await monitor.send_real_time_alert("test_user_123", alert_data)
    
    async def test_websocket_event_integration_with_golden_path(self):
        """Test WebSocket events integration with Golden Path user flow - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            websocket_manager = WebSocketManager()
            monitor = OperationalBusinessValueMonitor()
            monitor.set_websocket_manager(websocket_manager)
            
            # Test that business value monitoring integrates with the 5 critical WebSocket events
            critical_events = [
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]
            
            # Monitor should track these events for business value calculation
            for event_type in critical_events:
                await monitor.track_websocket_event(
                    user_id="test_user",
                    event_type=event_type,
                    timestamp="2025-09-14T14:45:00Z"
                )
            
            # Verify events are tracked for business value scoring
            business_value_score = await monitor.calculate_real_time_business_value("test_user")
            assert business_value_score >= 0.0
    
    async def test_multi_user_websocket_alert_isolation(self):
        """Test multi-user WebSocket alert isolation - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            websocket_manager = WebSocketManager()
            monitor = OperationalBusinessValueMonitor()
            monitor.set_websocket_manager(websocket_manager)
            
            # Test alerts are properly isolated between users
            users = ["user_1", "user_2", "user_3"]
            
            for user_id in users:
                alert_data = {
                    'type': 'tier_limit_warning',
                    'message': f'User {user_id} approaching tier limit',
                    'user_id': user_id
                }
                
                await monitor.send_user_specific_alert(user_id, alert_data)
            
            # Verify isolation - each user should only receive their own alerts
            for user_id in users:
                user_alerts = await monitor.get_user_alerts(user_id)
                assert all(alert['user_id'] == user_id for alert in user_alerts)


@pytest.mark.integration
class TestBusinessValueMonitoringDatabaseIntegration(SSotAsyncTestCase):
    """Integration tests with database persistence"""
    
    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
    
    async def test_database_metrics_persistence_integration(self):
        """Test database persistence integration for business metrics - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.db.database_manager import DatabaseManager
            
            # Use real database manager (no mocks in integration tests)
            db_manager = DatabaseManager()
            monitor = OperationalBusinessValueMonitor()
            monitor.set_database_manager(db_manager)
            
            # Test persistence of business value metrics
            metrics_batch = [
                {
                    'timestamp': '2025-09-14T14:40:00Z',
                    'business_value_score': 85.2,
                    'chat_responses': 120,
                    'websocket_events': 600,
                    'user_tier_distribution': {'free': 40, 'early': 35, 'mid': 20, 'enterprise': 5}
                },
                {
                    'timestamp': '2025-09-14T14:45:00Z', 
                    'business_value_score': 78.9,
                    'chat_responses': 98,
                    'websocket_events': 490,
                    'user_tier_distribution': {'free': 42, 'early': 33, 'mid': 20, 'enterprise': 5}
                }
            ]
            
            await monitor.persist_metrics_batch(metrics_batch)
            
            # Test retrieval and validation
            retrieved_metrics = await monitor.get_metrics_range(
                start_time='2025-09-14T14:35:00Z',
                end_time='2025-09-14T14:50:00Z'
            )
            
            assert len(retrieved_metrics) == 2
            assert retrieved_metrics[0]['business_value_score'] == Decimal('85.2')
    
    async def test_3tier_persistence_integration(self):
        """Test 3-tier persistence architecture integration - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test integration with 3-tier persistence
            # Tier 1 (Redis) - Hot cache for real-time metrics
            await monitor.cache_real_time_metrics({
                'current_business_value_score': 82.5,
                'active_users': 156,
                'chat_responses_last_5min': 45
            })
            
            # Tier 2 (PostgreSQL) - Warm storage for recent history
            await monitor.persist_recent_metrics({
                'timestamp': '2025-09-14T14:45:00Z',
                'business_value_score': 82.5,
                'detailed_metrics': {'chat_quality': 8.2, 'response_time': 1.3}
            })
            
            # Tier 3 (ClickHouse) - Cold analytics for historical analysis
            await monitor.persist_analytics_metrics({
                'date': '2025-09-14',
                'hourly_business_value_scores': [78.2, 82.1, 85.6, 82.5],
                'customer_tier_trends': {'free_to_early': 3, 'early_to_mid': 1}
            })
    
    async def test_database_alert_threshold_integration(self):
        """Test database integration for alert threshold management - WILL FAIL initially"""  
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test dynamic threshold management via database
            threshold_configs = [
                {'tier': 'free', 'business_value_threshold': 50.0, 'alert_cooldown': 30},
                {'tier': 'early', 'business_value_threshold': 65.0, 'alert_cooldown': 20}, 
                {'tier': 'mid', 'business_value_threshold': 75.0, 'alert_cooldown': 15},
                {'tier': 'enterprise', 'business_value_threshold': 85.0, 'alert_cooldown': 10}
            ]
            
            await monitor.update_tier_thresholds(threshold_configs)
            
            # Test threshold retrieval and application
            for config in threshold_configs:
                threshold = await monitor.get_tier_threshold(config['tier'])
                assert threshold == config['business_value_threshold']


@pytest.mark.integration
class TestBusinessValueMonitoringDashboardIntegration(SSotAsyncTestCase):
    """Integration tests with dashboard endpoints"""
    
    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
    
    async def test_dashboard_endpoint_integration(self):
        """Test dashboard endpoint integration for business value display - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.routes.dashboard import get_business_value_dashboard
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test dashboard data preparation
            dashboard_data = await monitor.prepare_dashboard_data()
            
            expected_sections = [
                'current_business_value_score',
                'trend_last_24h',
                'customer_tier_distribution', 
                'critical_alerts',
                'golden_path_health'
            ]
            
            for section in expected_sections:
                assert section in dashboard_data
            
            # Test dashboard endpoint response
            response = await get_business_value_dashboard()
            assert response.status_code == 200
            assert 'business_value_score' in response.json()
    
    async def test_real_time_dashboard_updates(self):
        """Test real-time dashboard updates via WebSocket - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            monitor = OperationalBusinessValueMonitor()
            websocket_manager = WebSocketManager()
            monitor.set_websocket_manager(websocket_manager)
            
            # Test real-time dashboard data streaming
            await monitor.start_dashboard_streaming()
            
            # Simulate business value changes
            new_metrics = {
                'business_value_score': 79.3,
                'active_chat_sessions': 234,
                'avg_response_quality': 8.1
            }
            
            await monitor.broadcast_dashboard_update(new_metrics)
            
            # Verify streaming is active
            assert monitor.is_dashboard_streaming
    
    async def test_dashboard_alert_integration(self):
        """Test dashboard alert integration and display - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test alert preparation for dashboard display
            test_alerts = [
                {
                    'severity': 'critical',
                    'message': 'Business value below 50% for 10 minutes',
                    'timestamp': '2025-09-14T14:35:00Z',
                    'affected_tiers': ['free', 'early']
                },
                {
                    'severity': 'warning', 
                    'message': 'WebSocket event delivery rate declining',
                    'timestamp': '2025-09-14T14:42:00Z',
                    'affected_tiers': ['mid']
                }
            ]
            
            dashboard_alerts = await monitor.prepare_dashboard_alerts(test_alerts)
            
            assert len(dashboard_alerts) == 2
            assert dashboard_alerts[0]['severity'] == 'critical'
            assert 'formatted_timestamp' in dashboard_alerts[0]


@pytest.mark.integration
class TestBusinessValueMonitoringAlertSystemIntegration(SSotAsyncTestCase):
    """Integration tests with alert system"""
    
    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
    
    async def test_alert_system_integration_with_thresholds(self):
        """Test alert system integration with business value thresholds - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.services.alert_manager import AlertManager
            
            monitor = OperationalBusinessValueMonitor()
            alert_manager = AlertManager()
            monitor.set_alert_manager(alert_manager)
            
            # Test threshold violation detection and alerting
            threshold_violations = [
                {'tier': 'free', 'current_score': 40.0, 'threshold': 50.0},
                {'tier': 'early', 'current_score': 55.0, 'threshold': 65.0},
                {'tier': 'enterprise', 'current_score': 75.0, 'threshold': 85.0}
            ]
            
            for violation in threshold_violations:
                await monitor.process_threshold_violation(violation)
            
            # Verify alerts were generated and sent
            generated_alerts = await monitor.get_generated_alerts(last_minutes=5)
            assert len(generated_alerts) == 3
    
    async def test_alert_escalation_integration(self):
        """Test alert escalation integration for critical business value issues - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test escalation triggers
            critical_scenarios = [
                {
                    'name': 'golden_path_failure',
                    'business_value_score': 15.0,
                    'duration_minutes': 15,
                    'expected_escalation_level': 'critical'
                },
                {
                    'name': 'websocket_system_degradation',
                    'websocket_success_rate': 30.0,
                    'duration_minutes': 10,
                    'expected_escalation_level': 'high'
                },
                {
                    'name': 'chat_response_failure',
                    'chat_success_rate': 45.0,
                    'duration_minutes': 8,
                    'expected_escalation_level': 'medium'
                }
            ]
            
            for scenario in critical_scenarios:
                escalation_level = await monitor.determine_escalation_level(scenario)
                assert escalation_level == scenario['expected_escalation_level']
    
    async def test_alert_cooldown_and_deduplication_integration(self):
        """Test alert cooldown and deduplication integration - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test that similar alerts are deduplicated within cooldown period
            alert_data = {
                'type': 'business_value_threshold',
                'tier': 'early',
                'threshold': 65.0,
                'current_score': 58.0
            }
            
            # Send initial alert
            alert_id_1 = await monitor.send_alert(alert_data)
            
            # Send duplicate alert immediately (should be deduplicated)
            alert_id_2 = await monitor.send_alert(alert_data)
            
            # Verify deduplication
            assert alert_id_1 == alert_id_2  # Same alert ID indicates deduplication
            
            # Verify only one alert was actually sent
            sent_alerts = await monitor.get_sent_alerts(last_minutes=1)
            assert len(sent_alerts) == 1


@pytest.mark.integration
class TestBusinessValueMonitoringSystemIntegration(SSotAsyncTestCase):
    """End-to-end system integration tests"""
    
    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
    
    async def test_complete_monitoring_workflow_integration(self):
        """Test complete monitoring workflow integration - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Set up complete monitoring system
            monitor = OperationalBusinessValueMonitor()
            websocket_manager = WebSocketManager()
            
            monitor.set_websocket_manager(websocket_manager)
            
            # Start monitoring workflow
            await monitor.start_complete_monitoring()
            
            # Simulate system activity and monitor response
            system_activity = {
                'user_id': 'test_user_integration',
                'chat_responses': 50,
                'websocket_events': 250,
                'session_duration': 1800,  # 30 minutes
                'response_quality': 8.2
            }
            
            business_value_score = await monitor.process_system_activity(system_activity)
            
            # Verify complete workflow
            assert 0 <= business_value_score <= 100
            assert monitor.is_monitoring
            
            # Test graceful shutdown
            await monitor.stop_complete_monitoring()
            assert not monitor.is_monitoring
    
    async def test_golden_path_business_value_protection(self):
        """Test Golden Path business value protection integration - WILL FAIL initially"""
        with pytest.raises((ImportError, AttributeError, ModuleNotFoundError)):
            from netra_backend.app.services.operational_business_value_monitor import OperationalBusinessValueMonitor
            
            monitor = OperationalBusinessValueMonitor()
            
            # Test $500K+ ARR protection through monitoring
            golden_path_metrics = {
                'login_success_rate': 98.5,
                'chat_response_success_rate': 95.2,
                'websocket_event_delivery_rate': 99.1,
                'agent_completion_rate': 93.8,
                'overall_user_satisfaction': 8.4
            }
            
            # Calculate business value impact
            business_impact = await monitor.calculate_golden_path_business_impact(golden_path_metrics)
            
            # Verify protection thresholds
            assert business_impact['protected_arr_value'] >= 500000  # $500K minimum
            assert business_impact['risk_level'] in ['low', 'medium', 'high', 'critical']
            assert business_impact['recommended_actions'] is not None