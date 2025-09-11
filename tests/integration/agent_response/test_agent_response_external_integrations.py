"""Integration Tests for Agent Response External System Integrations

Tests the integration of agent responses with external systems including
APIs, databases, monitoring systems, and third-party services.

Business Value Justification (BVJ):
- Segment: Mid/Enterprise - External integrations are key for enterprise workflows
- Business Goal: Enable seamless integration with customer existing systems
- Value Impact: Reduces friction for enterprise adoption and increases platform value
- Strategic Impact: Enables premium pricing for enterprise integration capabilities
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.real_services_test_fixtures import (
    real_database_session,
    real_redis_connection
)
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import (
    TypedAgentResult,
    AgentExecutionResult
)
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseExternalIntegrations(BaseIntegrationTest):
    """Test agent response integration with external systems."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # BVJ: Real database for integration state tracking
        self.db_session = real_database_session()
        
        # BVJ: Real Redis for external API caching
        self.redis_client = real_redis_connection()
        
        # External system configurations
        self.external_systems = {
            "monitoring_system": {
                "type": "prometheus",
                "endpoint": "http://monitoring.internal:9090",
                "auth_required": True,
                "timeout": 30
            },
            "data_warehouse": {
                "type": "snowflake",
                "endpoint": "company.snowflakecomputing.com",
                "auth_required": True,
                "timeout": 60
            },
            "notification_service": {
                "type": "slack",
                "endpoint": "https://hooks.slack.com/services/xxx",
                "auth_required": True,
                "timeout": 15
            },
            "analytics_platform": {
                "type": "datadog",
                "endpoint": "https://api.datadoghq.com",
                "auth_required": True,
                "timeout": 45
            }
        }
        
        # Integration test scenarios
        self.integration_scenarios = {
            "metrics_export": {
                "description": "Export optimization metrics to external monitoring",
                "systems": ["monitoring_system", "analytics_platform"],
                "data_type": "time_series"
            },
            "data_sync": {
                "description": "Sync optimization results to data warehouse",
                "systems": ["data_warehouse"],
                "data_type": "structured"
            },
            "notification_delivery": {
                "description": "Send optimization alerts to notification services",
                "systems": ["notification_service"],
                "data_type": "message"
            }
        }

    async def test_external_api_integration(self):
        """
        Test integration with external REST APIs.
        
        BVJ: Enterprise segment - API integrations enable workflow automation
        and data synchronization with enterprise systems.
        """
        logger.info("Testing external API integration")
        
        env = self.get_env()
        user_id = "api_integration_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["external_integrations_enabled"] = True
            context.context_data["api_timeout"] = 30
            
            # Mock external API configurations
            context.context_data["external_apis"] = {
                "metrics_api": {
                    "url": "https://api.metrics.company.com/v1",
                    "auth_token": "test_token_123",
                    "enabled": True
                },
                "reporting_api": {
                    "url": "https://api.reports.company.com/v2", 
                    "auth_token": "test_token_456",
                    "enabled": True
                }
            }
            
            agent = DataHelperAgent(
                agent_id="api_integration_agent",
                user_context=context
            )
            
            # Test API integration scenarios
            api_scenarios = [
                "Export current optimization metrics to external metrics API",
                "Send optimization report to external reporting system",
                "Sync performance data with external analytics platform"
            ]
            
            api_results = []
            
            for scenario in api_scenarios:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=scenario,
                    user_context=context
                )
                
                integration_time = time.time() - start_time
                
                api_result = {
                    "scenario": scenario,
                    "success": result is not None,
                    "integration_time": integration_time,
                    "response_content": str(result.result_data) if result else ""
                }
                
                api_results.append(api_result)
                
                # Validate API integration
                assert result is not None, f"API integration should succeed: {scenario}"
                
                # Should complete within reasonable time
                assert integration_time < 30, \
                    f"API integration should complete quickly: {integration_time:.3f}s"
                
                # Should indicate external integration
                response_text = api_result["response_content"].lower()
                integration_indicators = ["exported", "sent", "synced", "integrated", "api"]
                
                has_integration = any(indicator in response_text for indicator in integration_indicators)
                assert has_integration, \
                    f"Response should indicate external integration: {scenario}"
                
                logger.info(f"API integration successful: {scenario[:50]}... ({integration_time:.3f}s)")
            
            # Validate overall API integration performance
            successful_integrations = sum(1 for r in api_results if r["success"])
            total_integrations = len(api_scenarios)
            
            assert successful_integrations == total_integrations, \
                f"All API integrations should succeed: {successful_integrations}/{total_integrations}"

    async def test_database_external_sync(self):
        """
        Test synchronization with external databases and data warehouses.
        
        BVJ: Enterprise segment - Data warehouse integration enables
        comprehensive analytics and business intelligence workflows.
        """
        logger.info("Testing database external sync")
        
        env = self.get_env()
        user_id = "db_sync_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["database_sync_enabled"] = True
            context.context_data["data_warehouse_config"] = {
                "type": "snowflake",
                "database": "ANALYTICS_DB",
                "schema": "OPTIMIZATION_METRICS",
                "table": "AGENT_RESPONSES",
                "sync_interval": 300  # 5 minutes
            }
            
            agent = DataHelperAgent(
                agent_id="db_sync_agent",
                user_context=context
            )
            
            # Test database sync scenarios
            sync_scenarios = [
                {
                    "query": "Generate optimization report for data warehouse sync",
                    "sync_type": "batch_export",
                    "expected_format": "structured"
                },
                {
                    "query": "Create real-time metrics for external analytics",
                    "sync_type": "streaming",
                    "expected_format": "time_series"
                },
                {
                    "query": "Export user interaction data for business intelligence",
                    "sync_type": "incremental",
                    "expected_format": "normalized"
                }
            ]
            
            sync_results = []
            
            for scenario in sync_scenarios:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=scenario["query"],
                    user_context=context
                )
                
                sync_time = time.time() - start_time
                
                sync_result = {
                    "sync_type": scenario["sync_type"],
                    "success": result is not None,
                    "sync_time": sync_time,
                    "expected_format": scenario["expected_format"],
                    "response_size": len(str(result.result_data)) if result else 0
                }
                
                sync_results.append(sync_result)
                
                # Validate database sync
                assert result is not None, f"Database sync should succeed: {scenario['sync_type']}"
                
                # Should indicate data preparation for sync
                response_text = str(result.result_data).lower()
                sync_indicators = ["export", "sync", "warehouse", "database", "analytics"]
                
                has_sync = any(indicator in response_text for indicator in sync_indicators)
                assert has_sync, \
                    f"Response should indicate database sync: {scenario['sync_type']}"
                
                # Should have substantial data for warehouse sync
                assert sync_result["response_size"] > 50, \
                    f"Sync data should be substantial: {sync_result['response_size']} chars"
                
                logger.info(f"Database sync successful: {scenario['sync_type']} ({sync_time:.3f}s)")
            
            # Validate sync performance
            avg_sync_time = sum(r["sync_time"] for r in sync_results) / len(sync_results)
            assert avg_sync_time < 10, \
                f"Average sync time should be reasonable: {avg_sync_time:.3f}s"

    async def test_monitoring_system_integration(self):
        """
        Test integration with external monitoring and alerting systems.
        
        BVJ: Enterprise segment - Monitoring integration enables proactive
        system management and compliance with enterprise monitoring standards.
        """
        logger.info("Testing monitoring system integration")
        
        env = self.get_env()
        user_id = "monitoring_integration_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["monitoring_enabled"] = True
            context.context_data["monitoring_config"] = {
                "prometheus_endpoint": "http://prometheus:9090",
                "grafana_endpoint": "http://grafana:3000",
                "alert_manager": "http://alertmanager:9093",
                "metrics_namespace": "netra_optimization"
            }
            
            agent = DataHelperAgent(
                agent_id="monitoring_integration_agent",
                user_context=context
            )
            
            # Test monitoring integration scenarios
            monitoring_scenarios = [
                {
                    "query": "Generate performance metrics for Prometheus monitoring",
                    "metric_type": "gauge",
                    "alert_level": "info"
                },
                {
                    "query": "Create optimization alerts for system monitoring",
                    "metric_type": "counter",
                    "alert_level": "warning"
                },
                {
                    "query": "Export system health metrics for external monitoring",
                    "metric_type": "histogram",
                    "alert_level": "critical"
                }
            ]
            
            monitoring_results = []
            
            for scenario in monitoring_scenarios:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=scenario["query"],
                    user_context=context
                )
                
                integration_time = time.time() - start_time
                
                monitoring_result = {
                    "metric_type": scenario["metric_type"],
                    "alert_level": scenario["alert_level"],
                    "success": result is not None,
                    "integration_time": integration_time,
                    "has_metrics": False
                }
                
                if result:
                    response_text = str(result.result_data).lower()
                    
                    # Check for monitoring-specific content
                    monitoring_indicators = [
                        "metric", "alert", "monitoring", "prometheus", 
                        "gauge", "counter", "histogram", "dashboard"
                    ]
                    
                    monitoring_score = sum(
                        1 for indicator in monitoring_indicators 
                        if indicator in response_text
                    )
                    
                    monitoring_result["has_metrics"] = monitoring_score >= 2
                
                monitoring_results.append(monitoring_result)
                
                # Validate monitoring integration
                assert result is not None, f"Monitoring integration should succeed: {scenario['metric_type']}"
                
                assert monitoring_result["has_metrics"], \
                    f"Response should include monitoring metrics: {scenario['metric_type']}"
                
                logger.info(f"Monitoring integration successful: {scenario['metric_type']} ({integration_time:.3f}s)")
            
            # Validate overall monitoring integration
            successful_monitoring = sum(1 for r in monitoring_results if r["success"])
            total_scenarios = len(monitoring_scenarios)
            
            assert successful_monitoring == total_scenarios, \
                f"All monitoring integrations should succeed: {successful_monitoring}/{total_scenarios}"

    async def test_notification_service_integration(self):
        """
        Test integration with external notification services.
        
        BVJ: All segments - Notification integration improves user engagement
        and enables real-time communication of optimization results.
        """
        logger.info("Testing notification service integration")
        
        env = self.get_env()
        user_id = "notification_integration_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["notifications_enabled"] = True
            context.context_data["notification_services"] = {
                "slack": {
                    "webhook_url": "https://hooks.slack.com/services/test",
                    "channel": "#optimization-alerts",
                    "enabled": True
                },
                "email": {
                    "smtp_server": "smtp.company.com",
                    "sender": "optimization@company.com",
                    "enabled": True
                },
                "sms": {
                    "provider": "twilio",
                    "account_sid": "test_sid",
                    "enabled": False
                }
            }
            
            agent = DataHelperAgent(
                agent_id="notification_integration_agent",
                user_context=context
            )
            
            # Test notification scenarios
            notification_scenarios = [
                {
                    "query": "Send optimization completion notification to Slack",
                    "service": "slack",
                    "priority": "normal",
                    "format": "rich"
                },
                {
                    "query": "Email optimization report to stakeholders",
                    "service": "email", 
                    "priority": "high",
                    "format": "formatted"
                },
                {
                    "query": "Create alert notification for system administrators",
                    "service": "multiple",
                    "priority": "urgent",
                    "format": "simple"
                }
            ]
            
            notification_results = []
            
            for scenario in notification_scenarios:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=scenario["query"],
                    user_context=context
                )
                
                notification_time = time.time() - start_time
                
                notification_result = {
                    "service": scenario["service"],
                    "priority": scenario["priority"],
                    "success": result is not None,
                    "notification_time": notification_time,
                    "has_notification_content": False
                }
                
                if result:
                    response_text = str(result.result_data).lower()
                    
                    # Check for notification-specific content
                    notification_indicators = [
                        "sent", "delivered", "notification", "alert", 
                        "slack", "email", "message", "notified"
                    ]
                    
                    notification_score = sum(
                        1 for indicator in notification_indicators 
                        if indicator in response_text
                    )
                    
                    notification_result["has_notification_content"] = notification_score >= 1
                
                notification_results.append(notification_result)
                
                # Validate notification integration
                assert result is not None, f"Notification should succeed: {scenario['service']}"
                
                assert notification_result["has_notification_content"], \
                    f"Response should indicate notification sent: {scenario['service']}"
                
                # Notifications should be fast
                assert notification_time < 5, \
                    f"Notification should be fast: {notification_time:.3f}s"
                
                logger.info(f"Notification integration successful: {scenario['service']} ({notification_time:.3f}s)")
            
            # Validate notification performance
            successful_notifications = sum(1 for r in notification_results if r["success"])
            total_notifications = len(notification_scenarios)
            
            assert successful_notifications == total_notifications, \
                f"All notifications should succeed: {successful_notifications}/{total_notifications}"

    async def test_webhook_delivery_integration(self):
        """
        Test webhook delivery to external systems.
        
        BVJ: Enterprise segment - Webhook integration enables real-time
        event-driven workflows and system automation.
        """
        logger.info("Testing webhook delivery integration")
        
        env = self.get_env()
        user_id = "webhook_integration_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["webhooks_enabled"] = True
            context.context_data["webhook_endpoints"] = [
                {
                    "name": "optimization_completed",
                    "url": "https://api.customer.com/webhooks/optimization",
                    "secret": "webhook_secret_123",
                    "events": ["optimization_complete", "metrics_updated"]
                },
                {
                    "name": "alert_handler",
                    "url": "https://monitoring.customer.com/webhooks/alerts",
                    "secret": "webhook_secret_456",
                    "events": ["alert_triggered", "threshold_exceeded"]
                }
            ]
            
            agent = DataHelperAgent(
                agent_id="webhook_integration_agent",
                user_context=context
            )
            
            # Test webhook scenarios
            webhook_scenarios = [
                {
                    "query": "Trigger optimization completion webhook",
                    "event_type": "optimization_complete",
                    "payload_type": "structured"
                },
                {
                    "query": "Send metrics update webhook to external system",
                    "event_type": "metrics_updated",
                    "payload_type": "json"
                },
                {
                    "query": "Deliver alert webhook to monitoring system",
                    "event_type": "alert_triggered",
                    "payload_type": "formatted"
                }
            ]
            
            webhook_results = []
            
            for scenario in webhook_scenarios:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=scenario["query"],
                    user_context=context
                )
                
                webhook_time = time.time() - start_time
                
                webhook_result = {
                    "event_type": scenario["event_type"],
                    "payload_type": scenario["payload_type"],
                    "success": result is not None,
                    "webhook_time": webhook_time,
                    "has_webhook_content": False
                }
                
                if result:
                    response_text = str(result.result_data).lower()
                    
                    # Check for webhook-specific content
                    webhook_indicators = [
                        "webhook", "delivered", "triggered", "sent", 
                        "endpoint", "payload", "event", "notification"
                    ]
                    
                    webhook_score = sum(
                        1 for indicator in webhook_indicators 
                        if indicator in response_text
                    )
                    
                    webhook_result["has_webhook_content"] = webhook_score >= 2
                
                webhook_results.append(webhook_result)
                
                # Validate webhook delivery
                assert result is not None, f"Webhook should succeed: {scenario['event_type']}"
                
                assert webhook_result["has_webhook_content"], \
                    f"Response should indicate webhook delivery: {scenario['event_type']}"
                
                # Webhooks should be delivered quickly
                assert webhook_time < 3, \
                    f"Webhook delivery should be fast: {webhook_time:.3f}s"
                
                logger.info(f"Webhook integration successful: {scenario['event_type']} ({webhook_time:.3f}s)")
            
            # Validate webhook performance
            successful_webhooks = sum(1 for r in webhook_results if r["success"])
            total_webhooks = len(webhook_scenarios)
            
            assert successful_webhooks == total_webhooks, \
                f"All webhooks should succeed: {successful_webhooks}/{total_webhooks}"

    async def test_external_system_failover(self):
        """
        Test failover handling when external systems are unavailable.
        
        BVJ: Enterprise segment - Robust failover ensures system reliability
        even when external dependencies are unavailable.
        """
        logger.info("Testing external system failover")
        
        env = self.get_env()
        user_id = "failover_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["external_integrations"] = True
            context.context_data["failover_enabled"] = True
            context.context_data["system_availability"] = {
                "monitoring_system": False,  # Simulated outage
                "data_warehouse": True,
                "notification_service": False,  # Simulated outage
                "backup_notification": True
            }
            
            agent = DataHelperAgent(
                agent_id="failover_agent",
                user_context=context
            )
            
            # Test failover scenarios
            failover_scenarios = [
                {
                    "query": "Send metrics to monitoring system with failover",
                    "primary_system": "monitoring_system",
                    "backup_strategy": "local_storage"
                },
                {
                    "query": "Deliver notifications with service failover",
                    "primary_system": "notification_service",
                    "backup_strategy": "backup_notification"
                },
                {
                    "query": "Export data with warehouse failover handling",
                    "primary_system": "data_warehouse",
                    "backup_strategy": "queue_for_retry"
                }
            ]
            
            failover_results = []
            
            for scenario in failover_scenarios:
                start_time = time.time()
                
                result = await agent.arun(
                    input_data=scenario["query"],
                    user_context=context
                )
                
                failover_time = time.time() - start_time
                
                failover_result = {
                    "primary_system": scenario["primary_system"],
                    "backup_strategy": scenario["backup_strategy"],
                    "success": result is not None,
                    "failover_time": failover_time,
                    "handled_gracefully": False
                }
                
                if result:
                    response_text = str(result.result_data).lower()
                    
                    # Check for graceful failover handling
                    failover_indicators = [
                        "failover", "backup", "alternative", "fallback",
                        "queued", "retry", "stored locally", "degraded"
                    ]
                    
                    graceful_handling = any(
                        indicator in response_text 
                        for indicator in failover_indicators
                    )
                    
                    failover_result["handled_gracefully"] = graceful_handling
                
                failover_results.append(failover_result)
                
                # Validate failover handling
                assert result is not None, f"Failover should succeed: {scenario['primary_system']}"
                
                # Should handle failure gracefully
                assert failover_result["handled_gracefully"], \
                    f"Should handle {scenario['primary_system']} failure gracefully"
                
                # Failover should not take too long
                assert failover_time < 10, \
                    f"Failover should be responsive: {failover_time:.3f}s"
                
                logger.info(f"Failover successful: {scenario['primary_system']} -> {scenario['backup_strategy']}")
            
            # Validate overall failover robustness
            successful_failovers = sum(1 for r in failover_results if r["handled_gracefully"])
            total_failovers = len(failover_scenarios)
            
            assert successful_failovers == total_failovers, \
                f"All failovers should be handled gracefully: {successful_failovers}/{total_failovers}"

    async def test_integration_circuit_breaker(self):
        """
        Test circuit breaker pattern for external system integrations.
        
        BVJ: Enterprise segment - Circuit breaker prevents cascade failures
        and maintains system stability during external system issues.
        """
        logger.info("Testing integration circuit breaker")
        
        env = self.get_env()
        user_id = "circuit_breaker_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data["circuit_breaker_enabled"] = True
            context.context_data["circuit_breaker_config"] = {
                "failure_threshold": 3,
                "timeout": 60,  # seconds
                "half_open_max_calls": 2
            }
            
            agent = DataHelperAgent(
                agent_id="circuit_breaker_agent",
                user_context=context
            )
            
            # Simulate multiple integration attempts
            integration_attempts = []
            
            for attempt in range(5):
                start_time = time.time()
                
                # Simulate varying external system health
                context.context_data["external_system_health"] = {
                    "api_available": attempt < 2,  # First 2 attempts fail
                    "response_time": 30 if attempt < 2 else 1,  # Slow then fast
                    "error_rate": 0.8 if attempt < 2 else 0.1  # High then low error rate
                }
                
                result = await agent.arun(
                    input_data=f"Attempt external integration #{attempt + 1}",
                    user_context=context
                )
                
                attempt_time = time.time() - start_time
                
                attempt_result = {
                    "attempt": attempt + 1,
                    "success": result is not None,
                    "attempt_time": attempt_time,
                    "circuit_breaker_active": False
                }
                
                if result:
                    response_text = str(result.result_data).lower()
                    
                    # Check for circuit breaker indicators
                    circuit_indicators = [
                        "circuit breaker", "circuit open", "circuit closed",
                        "rate limited", "throttled", "degraded mode"
                    ]
                    
                    attempt_result["circuit_breaker_active"] = any(
                        indicator in response_text 
                        for indicator in circuit_indicators
                    )
                
                integration_attempts.append(attempt_result)
                
                logger.info(f"Integration attempt {attempt + 1}: {'Success' if result else 'Failed'} ({attempt_time:.3f}s)")
                
                # Small delay between attempts
                await asyncio.sleep(0.1)
            
            # Validate circuit breaker behavior
            failed_attempts = [a for a in integration_attempts if not a["success"]]
            successful_attempts = [a for a in integration_attempts if a["success"]]
            
            # Should have some recovery after initial failures
            assert len(successful_attempts) > 0, \
                "Should have some successful attempts after circuit breaker recovery"
            
            # Later attempts should be faster (circuit breaker working)
            if len(integration_attempts) >= 4:
                early_avg_time = sum(a["attempt_time"] for a in integration_attempts[:2]) / 2
                later_avg_time = sum(a["attempt_time"] for a in integration_attempts[-2:]) / 2
                
                assert later_avg_time <= early_avg_time + 2, \
                    f"Circuit breaker should improve response time: {early_avg_time:.3f}s -> {later_avg_time:.3f}s"
            
            logger.info(f"Circuit breaker test completed: {len(successful_attempts)}/{len(integration_attempts)} successful")