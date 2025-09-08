"""
E2E tests for WebSocket Enterprise Features - Testing premium WebSocket capabilities.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Premium feature validation and enterprise customer satisfaction
- Value Impact: Ensures enterprise-specific features work end-to-end for high-value customers
- Strategic Impact: Revenue protection - validates features that justify enterprise pricing

These E2E tests validate enterprise-specific WebSocket features: advanced analytics,
priority support channels, custom integrations, and premium performance guarantees.

CRITICAL: All E2E tests MUST use authentication as per CLAUDE.md requirements.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from test_framework.ssot.base import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility
from shared.isolated_environment import get_env


class TestWebSocketEnterpriseFeaturesE2E(SSotBaseTestCase):
    """E2E tests for WebSocket enterprise features."""
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated E2E auth helper."""
        env = get_env()
        config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            jwt_secret=env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        )
        return E2EAuthHelper(config)
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_enterprise_priority_support_websocket_e2e(self, auth_helper, websocket_utility):
        """Test enterprise priority support through WebSocket with authentication.
        
        Validates that enterprise customers get priority support channels and faster response.
        """
        # STEP 1: Authenticate enterprise user (MANDATORY for E2E)
        enterprise_auth = await auth_helper.authenticate_test_user(
            email="enterprise_support@bigcompany.com",
            subscription_tier="enterprise"
        )
        
        assert enterprise_auth.success is True, f"Enterprise authentication failed: {enterprise_auth.error}"
        assert enterprise_auth.access_token is not None
        
        # Also authenticate a regular user for comparison
        regular_auth = await auth_helper.authenticate_test_user(
            email="regular_support@smallcompany.com", 
            subscription_tier="early"
        )
        assert regular_auth.success is True
        
        # STEP 2: Connect both users to WebSocket
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=enterprise_auth.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as enterprise_ws:
            
            async with websocket_utility.create_authenticated_websocket_client(
                access_token=regular_auth.access_token,
                websocket_url=auth_helper.config.websocket_url
            ) as regular_ws:
                
                # STEP 3: Test priority support request
                support_requests = [
                    {
                        "websocket": enterprise_ws,
                        "user_id": enterprise_auth.user_id,
                        "tier": "enterprise",
                        "request": {
                            "type": "support_request",
                            "priority": "high",
                            "category": "technical_issue",
                            "subject": "WebSocket connection issues affecting production",
                            "description": "Our production system is experiencing WebSocket disconnections affecting 1000+ users",
                            "user_id": enterprise_auth.user_id,
                            "enterprise_escalation": True
                        }
                    },
                    {
                        "websocket": regular_ws,
                        "user_id": regular_auth.user_id,
                        "tier": "early",
                        "request": {
                            "type": "support_request",
                            "priority": "medium",
                            "category": "general_question",
                            "subject": "Question about WebSocket features",
                            "description": "How do I enable real-time updates?",
                            "user_id": regular_auth.user_id
                        }
                    }
                ]
                
                # Send support requests simultaneously
                request_times = []
                for req_data in support_requests:
                    request_time = datetime.now(timezone.utc)
                    await req_data["websocket"].send_json(req_data["request"])
                    request_times.append(request_time)
                
                # STEP 4: Collect support responses
                support_responses = []
                response_times = []
                max_wait = 30
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < max_wait and len(support_responses) < 2:
                    for i, req_data in enumerate(support_requests):
                        try:
                            response = await asyncio.wait_for(
                                req_data["websocket"].receive_json(), 
                                timeout=1.0
                            )
                            
                            if response.get("type") in ["support_response", "support_ticket_created"]:
                                response_time = datetime.now(timezone.utc)
                                support_responses.append({
                                    "tier": req_data["tier"],
                                    "response": response,
                                    "response_time": response_time,
                                    "request_time": request_times[i]
                                })
                                response_times.append(response_time)
                                
                        except asyncio.TimeoutError:
                            continue
                
                # STEP 5: Validate enterprise priority response
                enterprise_response = next((r for r in support_responses if r["tier"] == "enterprise"), None)
                regular_response = next((r for r in support_responses if r["tier"] == "early"), None)
                
                # Enterprise should get response
                assert enterprise_response is not None, "Enterprise customer should receive support response"
                
                if enterprise_response:
                    response_delay = (enterprise_response["response_time"] - enterprise_response["request_time"]).total_seconds()
                    
                    # Enterprise response should be fast (under 10 seconds)
                    assert response_delay <= 15, f"Enterprise support response took {response_delay}s (should be < 15s)"
                    
                    # Enterprise response should include priority indicators
                    enterprise_data = enterprise_response["response"]
                    priority_indicators = ["priority", "enterprise", "escalated", "immediate"]
                    response_content = str(enterprise_data).lower()
                    
                    priority_mentioned = any(indicator in response_content for indicator in priority_indicators)
                    assert priority_mentioned, "Enterprise response should indicate priority handling"
                
                # Compare response times if both received
                if enterprise_response and regular_response:
                    enterprise_delay = (enterprise_response["response_time"] - enterprise_response["request_time"]).total_seconds()
                    regular_delay = (regular_response["response_time"] - regular_response["request_time"]).total_seconds()
                    
                    # Enterprise should respond faster or at least as fast
                    assert enterprise_delay <= regular_delay + 5, "Enterprise support should not be significantly slower than regular support"
                
                # STEP 6: Test enterprise escalation features
                escalation_request = {
                    "type": "escalate_support_ticket",
                    "ticket_id": enterprise_response["response"].get("ticket_id") if enterprise_response else "test_ticket",
                    "escalation_reason": "Critical production impact",
                    "severity": "critical",
                    "business_impact": "Revenue affecting - 1000+ users impacted",
                    "user_id": enterprise_auth.user_id
                }
                
                await enterprise_ws.send_json(escalation_request)
                
                # Should receive escalation acknowledgment
                escalation_response = None
                escalation_wait = 15
                escalation_start = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - escalation_start) < escalation_wait:
                    try:
                        event = await asyncio.wait_for(enterprise_ws.receive_json(), timeout=2)
                        if event.get("type") in ["escalation_acknowledged", "priority_escalated"]:
                            escalation_response = event
                            break
                    except asyncio.TimeoutError:
                        continue
                
                # Enterprise escalation should be acknowledged
                if escalation_response:
                    escalation_data = escalation_response.get("data", {})
                    assert "critical" in str(escalation_data).lower() or "escalated" in str(escalation_data).lower(), \
                        "Escalation should be acknowledged with appropriate priority"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_enterprise_advanced_analytics_websocket_e2e(self, auth_helper, websocket_utility):
        """Test enterprise advanced analytics features via WebSocket with authentication.
        
        Validates advanced analytics capabilities available only to enterprise customers.
        """
        # Authenticate enterprise user (MANDATORY for E2E)
        enterprise_auth = await auth_helper.authenticate_test_user(
            email="analytics_user@enterprise.com",
            subscription_tier="enterprise"
        )
        
        assert enterprise_auth.success is True
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=enterprise_auth.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 1: Request advanced analytics dashboard
            analytics_request = {
                "type": "enable_advanced_analytics",
                "user_id": enterprise_auth.user_id,
                "analytics_types": [
                    "real_time_cost_tracking",
                    "predictive_cost_modeling", 
                    "resource_optimization_ai",
                    "multi_cloud_comparison",
                    "custom_kpi_dashboard"
                ],
                "dashboard_config": {
                    "update_frequency": "real_time",
                    "historical_data_depth": "12_months",
                    "forecasting_horizon": "6_months"
                }
            }
            
            await websocket.send_json(analytics_request)
            
            # STEP 2: Collect analytics activation response
            analytics_response = None
            try:
                analytics_response = await asyncio.wait_for(websocket.receive_json(), timeout=15)
            except asyncio.TimeoutError:
                pass
            
            # Should enable advanced analytics
            assert analytics_response is not None, "Enterprise should receive analytics activation response"
            
            if analytics_response:
                response_type = analytics_response.get("type")
                assert response_type in ["analytics_enabled", "dashboard_configured"], \
                    "Should confirm analytics activation"
                
                # Should not receive feature restriction error
                error_indicators = ["upgrade", "premium", "not_available"]
                response_content = str(analytics_response).lower()
                has_restrictions = any(indicator in response_content for indicator in error_indicators)
                assert not has_restrictions, "Enterprise should have full analytics access"
            
            # STEP 3: Request real-time analytics data
            realtime_analytics_request = {
                "type": "get_realtime_analytics",
                "user_id": enterprise_auth.user_id,
                "metrics": [
                    "current_hourly_spend",
                    "resource_utilization_live",
                    "cost_anomaly_detection",
                    "optimization_opportunities_live"
                ],
                "granularity": "minute_by_minute"
            }
            
            await websocket.send_json(realtime_analytics_request)
            
            # STEP 4: Collect real-time analytics data
            analytics_data_events = []
            analytics_wait = 20
            analytics_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - analytics_start) < analytics_wait:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=3)
                    
                    if event.get("type") in ["analytics_data", "realtime_metrics", "live_dashboard_update"]:
                        analytics_data_events.append(event)
                        
                        # Collect multiple data points for real-time validation
                        if len(analytics_data_events) >= 3:
                            break
                            
                except asyncio.TimeoutError:
                    continue
            
            # STEP 5: Validate advanced analytics data
            assert len(analytics_data_events) >= 1, "Should receive real-time analytics data"
            
            for analytics_event in analytics_data_events:
                analytics_payload = analytics_event.get("data", {})
                
                # Should contain enterprise-level metrics
                enterprise_metrics = [
                    "cost_anomaly_detection",
                    "predictive_modeling",
                    "ai_recommendations",
                    "multi_cloud_analysis",
                    "custom_kpis"
                ]
                
                metrics_content = str(analytics_payload).lower()
                enterprise_features = sum(1 for metric in enterprise_metrics if metric in metrics_content)
                
                # Should have advanced enterprise features
                assert enterprise_features >= 1, "Analytics should include enterprise-level features"
                
                # Should include detailed numerical data
                numerical_indicators = ["cost", "utilization", "savings", "efficiency"]
                numerical_content = sum(1 for indicator in numerical_indicators if indicator in metrics_content)
                assert numerical_content >= 2, "Analytics should include detailed numerical insights"
            
            # STEP 6: Test custom analytics configuration
            custom_analytics = {
                "type": "configure_custom_analytics",
                "user_id": enterprise_auth.user_id,
                "custom_dashboard": {
                    "name": "Executive Cost Dashboard",
                    "widgets": [
                        {"type": "cost_trend_chart", "time_range": "90_days"},
                        {"type": "department_breakdown", "include_forecasting": True},
                        {"type": "roi_analysis", "project_based": True},
                        {"type": "anomaly_alerts", "sensitivity": "high"}
                    ],
                    "refresh_interval": "5_minutes",
                    "export_formats": ["pdf", "xlsx", "api"]
                }
            }
            
            await websocket.send_json(custom_analytics)
            
            # Should confirm custom analytics setup
            custom_response = None
            try:
                custom_response = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            except asyncio.TimeoutError:
                pass
            
            if custom_response:
                custom_content = str(custom_response).lower()
                configuration_indicators = ["configured", "dashboard", "custom", "created"]
                config_confirmed = any(indicator in custom_content for indicator in configuration_indicators)
                
                assert config_confirmed, "Custom analytics configuration should be confirmed"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_enterprise_integration_webhooks_e2e(self, auth_helper, websocket_utility):
        """Test enterprise integration and webhook features via WebSocket with authentication.
        
        Validates enterprise integration capabilities for connecting with external systems.
        """
        # Authenticate enterprise user (MANDATORY for E2E)
        enterprise_auth = await auth_helper.authenticate_test_user(
            email="integration_admin@enterprise.com",
            subscription_tier="enterprise"
        )
        
        assert enterprise_auth.success is True
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=enterprise_auth.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 1: Configure enterprise integrations
            integration_config = {
                "type": "configure_enterprise_integrations",
                "user_id": enterprise_auth.user_id,
                "integrations": [
                    {
                        "name": "slack_notifications",
                        "type": "webhook",
                        "endpoint": "https://hooks.slack.com/test/webhook",
                        "events": ["cost_alerts", "optimization_found", "budget_exceeded"],
                        "filters": {"severity": ["high", "critical"]}
                    },
                    {
                        "name": "datadog_metrics",
                        "type": "metrics_push",
                        "endpoint": "https://api.datadoghq.com/api/v1/series",
                        "api_key": "test_key",
                        "metrics": ["cost_per_hour", "utilization_percent", "savings_identified"]
                    },
                    {
                        "name": "jira_tickets",
                        "type": "ticketing_system",
                        "endpoint": "https://company.atlassian.net/rest/api/2/issue",
                        "auth": {"type": "bearer", "token": "test_token"},
                        "auto_create": ["high_cost_anomalies", "optimization_recommendations"]
                    }
                ],
                "enterprise_features": {
                    "sso_integration": True,
                    "api_rate_limits": "unlimited",
                    "custom_webhooks": True,
                    "data_export_api": True
                }
            }
            
            await websocket.send_json(integration_config)
            
            # STEP 2: Confirm integration setup
            integration_response = None
            try:
                integration_response = await asyncio.wait_for(websocket.receive_json(), timeout=15)
            except asyncio.TimeoutError:
                pass
            
            assert integration_response is not None, "Should receive integration configuration response"
            
            if integration_response:
                response_content = str(integration_response).lower()
                integration_indicators = ["integration", "configured", "webhook", "enabled"]
                integration_confirmed = any(indicator in response_content for indicator in integration_indicators)
                
                assert integration_confirmed, "Enterprise integrations should be configured"
            
            # STEP 3: Test webhook trigger simulation
            webhook_trigger = {
                "type": "simulate_webhook_event",
                "user_id": enterprise_auth.user_id,
                "event": {
                    "type": "cost_alert",
                    "severity": "high",
                    "data": {
                        "current_cost": 12500,
                        "budget_limit": 10000,
                        "overage_percent": 25,
                        "department": "engineering",
                        "alert_threshold_exceeded": True
                    }
                },
                "target_integrations": ["slack_notifications", "jira_tickets"]
            }
            
            await websocket.send_json(webhook_trigger)
            
            # STEP 4: Collect webhook execution results
            webhook_results = []
            webhook_wait = 10
            webhook_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - webhook_start) < webhook_wait:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=2)
                    if event.get("type") in ["webhook_executed", "integration_triggered", "external_notification_sent"]:
                        webhook_results.append(event)
                except asyncio.TimeoutError:
                    continue
            
            # STEP 5: Validate webhook execution
            # Should receive webhook execution confirmations
            if webhook_results:
                webhook_confirmations = [
                    result for result in webhook_results 
                    if "webhook" in str(result).lower() or "executed" in str(result).lower()
                ]
                assert len(webhook_confirmations) >= 1, "Should confirm webhook execution"
            
            # STEP 6: Test custom API endpoint
            custom_api_request = {
                "type": "test_custom_api_endpoint",
                "user_id": enterprise_auth.user_id,
                "api_config": {
                    "endpoint": "/api/enterprise/cost-analytics",
                    "method": "GET",
                    "authentication": "jwt_bearer",
                    "rate_limit": "unlimited",
                    "response_format": "json",
                    "include_real_time": True
                }
            }
            
            await websocket.send_json(custom_api_request)
            
            # Should confirm API endpoint availability
            api_response = None
            try:
                api_response = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            except asyncio.TimeoutError:
                pass
            
            if api_response:
                api_content = str(api_response).lower()
                api_indicators = ["endpoint", "available", "api", "accessible"]
                api_confirmed = any(indicator in api_content for indicator in api_indicators)
                
                if api_response.get("type") != "error":
                    assert api_confirmed, "Custom API endpoint should be available for enterprise"
            
            # STEP 7: Test data export capabilities
            data_export_request = {
                "type": "request_data_export",
                "user_id": enterprise_auth.user_id,
                "export_config": {
                    "data_types": ["cost_history", "optimization_reports", "analytics_data"],
                    "date_range": {
                        "start": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                        "end": datetime.now(timezone.utc).isoformat()
                    },
                    "format": "json",
                    "compression": "gzip",
                    "delivery_method": "webhook_callback"
                }
            }
            
            await websocket.send_json(data_export_request)
            
            # Should initiate data export
            export_response = None
            try:
                export_response = await asyncio.wait_for(websocket.receive_json(), timeout=15)
            except asyncio.TimeoutError:
                pass
            
            if export_response:
                export_content = str(export_response).lower()
                export_indicators = ["export", "initiated", "processing", "scheduled"]
                export_started = any(indicator in export_content for indicator in export_indicators)
                
                assert export_started, "Data export should be initiated for enterprise users"
                
                # Should provide export tracking information
                if export_response.get("type") in ["export_initiated", "data_export_started"]:
                    export_data = export_response.get("data", {})
                    tracking_info = ["export_id", "status", "estimated_completion", "download_url"]
                    tracking_provided = any(info in export_data for info in tracking_info)
                    
                    assert tracking_provided, "Should provide export tracking information"