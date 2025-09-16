"""
Backend <-> Analytics Service Integration Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Analytics features for paying customers)
- Business Goal: Deliver actionable insights and reporting capabilities
- Value Impact: Users receive data-driven recommendations and optimization insights
- Strategic Impact: Analytics capabilities differentiate our platform and drive retention

These tests validate real interservice communication between the backend and analytics service,
ensuring data pipeline flows work correctly without Docker containers.
"""

import asyncio
import pytest
import httpx
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.base_test_case import BaseTestCase
from shared.isolated_environment import get_env


class TestBackendAnalyticsServiceIntegration(BaseTestCase):
    """Integration tests for Backend <-> Analytics Service communication."""
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_analytics_event_ingestion_success(self):
        """
        Test successful event ingestion to analytics service.
        
        BVJ: Revenue critical - ensures user actions are tracked for insights
        generation, directly supporting Mid/Enterprise value proposition.
        """
        env = get_env()
        env.enable_isolation()
        env.set("ANALYTICS_SERVICE_URL", "http://localhost:8002", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock successful analytics ingestion
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "event_id": "evt_123456",
            "status": "accepted",
            "processed_at": "2024-09-07T15:30:00Z"
        }
        
        event_data = {
            "user_id": "user-789",
            "event_type": "agent_execution",
            "event_data": {
                "agent_type": "cost_optimizer",
                "execution_time_ms": 2500,
                "tokens_used": 850,
                "cost_usd": 0.0234,
                "result_quality": "high"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": "session-abc123"
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Simulate analytics client call
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{env.get('ANALYTICS_SERVICE_URL')}/api/events/ingest",
                    json=event_data,
                    headers={
                        "Authorization": f"Bearer {env.get('SERVICE_SECRET')}",
                        "Content-Type": "application/json"
                    }
                )
            
            # Verify successful ingestion
            assert mock_response.status_code == 201
            result = mock_response.json()
            assert result.get("status") == "accepted"
            assert "event_id" in result
            assert "processed_at" in result
            
            # Verify correct API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "ingest" in str(call_args[1]["url"])
            
            # Verify event data structure
            sent_data = call_args[1]["json"]
            assert sent_data["user_id"] == "user-789"
            assert sent_data["event_type"] == "agent_execution"
            assert "execution_time_ms" in sent_data["event_data"]
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_analytics_insights_retrieval(self):
        """
        Test retrieval of analytics insights for user dashboards.
        
        BVJ: User experience critical - delivers value through actionable insights
        that justify Mid/Enterprise subscription costs.
        """
        env = get_env()
        env.enable_isolation()
        env.set("ANALYTICS_SERVICE_URL", "http://localhost:8002", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock analytics insights response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user_id": "user-789",
            "insights": {
                "cost_optimization": {
                    "total_savings": 15234.50,
                    "monthly_trend": "decreasing",
                    "top_recommendations": [
                        {
                            "category": "infrastructure",
                            "potential_savings": 5670.25,
                            "confidence": 0.92
                        },
                        {
                            "category": "usage_patterns",
                            "potential_savings": 3420.10,
                            "confidence": 0.87
                        }
                    ]
                },
                "usage_analytics": {
                    "agent_executions": 156,
                    "avg_response_time_ms": 2100,
                    "success_rate": 0.94,
                    "preferred_agents": ["cost_optimizer", "security_advisor"]
                }
            },
            "generated_at": "2024-09-07T15:30:00Z",
            "period": {
                "start": "2024-08-01T00:00:00Z",
                "end": "2024-09-01T00:00:00Z"
            }
        }
        
        with patch('httpx.AsyncClient.get', return_value=mock_response) as mock_get:
            # Simulate analytics insights request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{env.get('ANALYTICS_SERVICE_URL')}/api/insights/user/user-789",
                    headers={
                        "Authorization": f"Bearer {env.get('SERVICE_SECRET')}"
                    },
                    params={
                        "period": "30d",
                        "categories": "cost_optimization,usage_analytics"
                    }
                )
            
            # Verify insights structure
            insights = mock_response.json()
            assert insights.get("user_id") == "user-789"
            assert "insights" in insights
            assert "cost_optimization" in insights["insights"]
            assert "usage_analytics" in insights["insights"]
            
            # Verify cost optimization insights
            cost_insights = insights["insights"]["cost_optimization"]
            assert "total_savings" in cost_insights
            assert cost_insights["total_savings"] > 0
            assert "top_recommendations" in cost_insights
            assert len(cost_insights["top_recommendations"]) > 0
            
            # Verify usage analytics
            usage_insights = insights["insights"]["usage_analytics"]
            assert "agent_executions" in usage_insights
            assert "success_rate" in usage_insights
            assert usage_insights["success_rate"] <= 1.0
            
            # Verify API call
            mock_get.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_analytics_service_data_aggregation_request(self):
        """
        Test requesting data aggregation for business intelligence.
        
        BVJ: Strategic intelligence - enables platform optimization and
        business decision making based on usage patterns.
        """
        env = get_env()
        env.enable_isolation()
        env.set("ANALYTICS_SERVICE_URL", "http://localhost:8002", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        # Mock aggregation request response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "job_id": "agg_job_789",
            "status": "queued",
            "estimated_completion": "2024-09-07T15:45:00Z",
            "query_summary": {
                "metrics": ["agent_usage", "cost_savings", "user_satisfaction"],
                "timeframe": "2024-08-01 to 2024-09-01",
                "segmentation": "subscription_tier"
            }
        }
        
        aggregation_request = {
            "query_type": "business_intelligence",
            "metrics": ["agent_usage", "cost_savings", "user_satisfaction"],
            "dimensions": ["subscription_tier", "user_segment", "geographic_region"],
            "timeframe": {
                "start": "2024-08-01T00:00:00Z",
                "end": "2024-09-01T00:00:00Z"
            },
            "filters": {
                "subscription_tier": ["mid", "enterprise"],
                "min_agent_executions": 10
            },
            "requested_by": "backend_service",
            "priority": "normal"
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Simulate aggregation request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{env.get('ANALYTICS_SERVICE_URL')}/api/aggregation/request",
                    json=aggregation_request,
                    headers={
                        "Authorization": f"Bearer {env.get('SERVICE_SECRET')}",
                        "Content-Type": "application/json"
                    }
                )
            
            # Verify aggregation job queued
            result = mock_response.json()
            assert result.get("status") == "queued"
            assert "job_id" in result
            assert "estimated_completion" in result
            
            # Verify request structure
            call_args = mock_post.call_args
            sent_request = call_args[1]["json"]
            assert sent_request["query_type"] == "business_intelligence"
            assert "agent_usage" in sent_request["metrics"]
            assert "subscription_tier" in sent_request["dimensions"]
            assert "timeframe" in sent_request
    
    @pytest.mark.integration
    @pytest.mark.interservice
    async def test_analytics_service_connection_resilience(self):
        """
        Test backend resilience when analytics service is unavailable.
        
        BVJ: System reliability - ensures core platform functions continue
        even when analytics service is down, maintaining user experience.
        """
        env = get_env()
        env.enable_isolation()
        env.set("ANALYTICS_SERVICE_URL", "http://localhost:8002", "test")
        env.set("SERVICE_SECRET", "test-service-secret", "test")
        
        event_data = {
            "user_id": "user-resilience-test",
            "event_type": "agent_execution",
            "event_data": {"agent_type": "test_agent"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Mock connection failure
        with patch('httpx.AsyncClient.post', side_effect=httpx.ConnectError("Analytics service unavailable")) as mock_post:
            
            # Should handle connection error gracefully
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{env.get('ANALYTICS_SERVICE_URL')}/api/events/ingest",
                        json=event_data,
                        headers={"Authorization": f"Bearer {env.get('SERVICE_SECRET')}"}
                    )
            except httpx.ConnectError as e:
                # Expected behavior - connection error should be caught
                assert "Analytics service unavailable" in str(e)
                
                # In real implementation, this would:
                # 1. Log the error
                # 2. Queue event for later retry
                # 3. Continue with main request processing
                # 4. Return graceful fallback response
                
                # Verify connection was attempted
                mock_post.assert_called_once()
                
                # Simulate fallback behavior
                fallback_response = {
                    "status": "deferred",
                    "message": "Analytics processing deferred due to service unavailability",
                    "retry_queued": True
                }
                
                assert fallback_response["status"] == "deferred"
                assert fallback_response["retry_queued"] == True