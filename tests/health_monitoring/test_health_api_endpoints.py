"""
Test Suite for Health Monitoring API Endpoints

Tests all health check API endpoints including staging health overview,
WebSocket health, database health, services health, and performance metrics.
"""

import pytest
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from typing import Any, Dict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from netra_backend.app.routes.staging_health import router as staging_health_router
from fastapi import FastAPI

# Create test app
app = FastAPI()
app.include_router(staging_health_router)
client = TestClient(app)


class TestStagingHealthOverview:
    """Test staging health overview endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_staging_health_overview_success(self, mock_monitor):
        """Test successful staging health overview retrieval."""
        # Mock comprehensive health response
        mock_health_data = {
            "status": "healthy",
            "service": "staging_environment",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0,
                    "response_time_ms": 50.0
                },
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 25.0
                }
            },
            "staging_analysis": {
                "business_impact": {"impact_level": "none"},
                "trend_analysis": {"overall_trend": "stable"},
                "remediation_suggestions": [],
                "failure_prediction": {"failure_prediction_available": False}
            },
            "alert_status": {
                "alerts_active": False,
                "alert_count": 0,
                "alert_severity": "none"
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "staging_environment"
        assert "staging_analysis" in data
        assert "alert_status" in data
        assert "response_metadata" in data
        assert data["response_metadata"]["endpoint"] == "staging_health_overview"
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_staging_health_overview_simplified(self, mock_monitor):
        """Test simplified staging health overview (details=false)."""
        mock_health_data = {
            "status": "healthy",
            "service": "staging_environment",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {"success": True, "health_score": 1.0},
                "database_postgres": {"success": True, "health_score": 0.95}
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health?details=false")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "component_count" in data
        assert data["component_count"] == 2
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_staging_health_overview_error(self, mock_monitor):
        """Test staging health overview with monitor error."""
        mock_monitor.get_comprehensive_health.side_effect = Exception("Monitor failed")
        
        response = client.get("/staging/health")
        
        assert response.status_code == 500
        assert "Failed to retrieve staging health overview" in response.json()["detail"]


class TestWebSocketHealthEndpoint:
    """Test WebSocket health monitoring endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_websocket_health_success(self, mock_monitor):
        """Test successful WebSocket health check."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0,
                    "response_time_ms": 50.0,
                    "details": {
                        "websocket_server_available": True,
                        "event_transmission_working": True,
                        "event_pipeline_functional": True
                    }
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/websocket")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["health_percentage"] == 100.0
        assert data["components_healthy"] == 1
        assert data["components_total"] == 1
        assert "critical_events_status" in data
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_websocket_health_degraded(self, mock_monitor):
        """Test WebSocket health check with degraded performance."""
        mock_health_data = {
            "status": "degraded",
            "checks": {
                "staging_websocket": {
                    "success": False,
                    "health_score": 0.6,
                    "response_time_ms": 200.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/websocket")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["health_percentage"] == 0.0  # Failed component
        assert data["components_healthy"] == 0
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_websocket_health_with_event_details(self, mock_monitor):
        """Test WebSocket health check with event details."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/websocket?include_event_details=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "event_pipeline_details" in data
        assert "critical_events" in data["event_pipeline_details"]
        
        # Verify critical events are included
        critical_events = data["event_pipeline_details"]["critical_events"]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert all(event in critical_events for event in expected_events)


class TestDatabaseHealthEndpoint:
    """Test database health monitoring endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_database_health_all_databases(self, mock_monitor):
        """Test database health check for all databases."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 25.0
                },
                "database_redis": {
                    "success": True,
                    "health_score": 0.98,
                    "response_time_ms": 15.0
                },
                "database_clickhouse": {
                    "success": True,
                    "health_score": 0.92,
                    "response_time_ms": 35.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/database")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["databases_healthy"] == 3
        assert data["databases_total"] == 3
        assert "connection_status" in data
        assert "databases_monitored" in data
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_database_health_specific_database(self, mock_monitor):
        """Test database health check for specific database type."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 25.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/database?database_type=postgres")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["databases_healthy"] == 1
        assert data["databases_total"] == 1
        assert "postgres" in data["databases_monitored"]
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_database_health_with_performance_metrics(self, mock_monitor):
        """Test database health check with performance metrics."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 25.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/database?include_performance=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "performance_metrics" in data
        assert "average_query_time_ms" in data["performance_metrics"]
        assert "connection_pool_utilization" in data["performance_metrics"]


class TestServicesHealthEndpoint:
    """Test services health monitoring endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_services_health_all_services(self, mock_monitor):
        """Test services health check for all services."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "service_auth_service": {
                    "success": True,
                    "health_score": 0.98,
                    "response_time_ms": 100.0
                },
                "service_backend": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 120.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/services")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["services_healthy"] == 2
        assert data["services_total"] == 2
        assert "service_connectivity" in data
        assert "services_monitored" in data
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_services_health_specific_service(self, mock_monitor):
        """Test services health check for specific service."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "service_auth_service": {
                    "success": True,
                    "health_score": 0.98,
                    "response_time_ms": 100.0
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/services?service_name=auth_service")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["services_healthy"] == 1
        assert "auth_service" in data["services_monitored"]
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_services_health_with_dependencies(self, mock_monitor):
        """Test services health check with dependency analysis."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "service_backend": {
                    "success": True,
                    "health_score": 0.95
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/services?include_dependencies=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dependency_analysis" in data
        assert "dependency_chain" in data["dependency_analysis"]
        assert "critical_path" in data["dependency_analysis"]


class TestPerformanceMetricsEndpoint:
    """Test performance metrics monitoring endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_performance_metrics_all_types(self, mock_monitor):
        """Test performance metrics retrieval for all metric types."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "staging_performance": {
                    "success": True,
                    "details": {
                        "performance_metrics": {
                            "api_response_time_ms": 200.0,
                            "websocket_latency_ms": 50.0,
                            "database_query_time_ms": 30.0
                        }
                    }
                },
                "staging_resources": {
                    "success": True,
                    "details": {
                        "cpu_usage_percent": 45.0,
                        "memory_usage_percent": 60.0,
                        "disk_usage_percent": 70.0
                    }
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "performance" in data
        assert "resources" in data
        assert "configuration" in data
        assert "real_time_metrics" in data
        assert "collection_metadata" in data
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_performance_metrics_specific_type(self, mock_monitor):
        """Test performance metrics retrieval for specific metric type."""
        mock_health_data = {
            "status": "healthy",
            "checks": {
                "staging_performance": {
                    "success": True,
                    "details": {
                        "performance_metrics": {
                            "api_response_time_ms": 200.0,
                            "websocket_latency_ms": 50.0,
                            "database_query_time_ms": 30.0
                        }
                    }
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/metrics?metric_type=performance")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "performance" in data
        assert "resources" not in data
        assert "configuration" not in data
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_performance_metrics_with_trends(self, mock_monitor):
        """Test performance metrics with trend analysis."""
        mock_health_data = {
            "status": "healthy",
            "staging_analysis": {
                "trend_analysis": {
                    "overall_trend": "stable",
                    "recent_average_health_score": 0.95
                },
                "failure_prediction": {
                    "failure_prediction_available": False,
                    "potential_failures": []
                }
            }
        }
        
        mock_monitor.get_comprehensive_health.return_value = mock_health_data
        
        response = client.get("/staging/health/metrics?include_trends=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "trend_analysis" in data
        assert "performance_predictions" in data


class TestCriticalHealthEndpoint:
    """Test critical health monitoring endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_critical_health_success(self, mock_monitor):
        """Test critical health check with healthy components."""
        mock_critical_data = {
            "status": "healthy",
            "service": "staging_environment_critical",
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0
                },
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95
                }
            },
            "staging_analysis": {
                "business_impact": {"impact_level": "none"},
                "remediation_suggestions": []
            },
            "alert_status": {
                "alerts_active": False,
                "alert_count": 0,
                "alert_severity": "none"
            }
        }
        
        mock_monitor.get_critical_health.return_value = mock_critical_data
        
        response = client.get("/staging/health/critical")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["focus"] == "critical_components_only"
        assert "critical_analysis" in data
        assert data["critical_analysis"]["components_below_threshold"] == 0
        assert data["critical_analysis"]["immediate_action_required"] is False
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_critical_health_with_failures(self, mock_monitor):
        """Test critical health check with component failures."""
        mock_critical_data = {
            "status": "degraded",
            "service": "staging_environment_critical",
            "checks": {
                "staging_websocket": {
                    "success": False,
                    "health_score": 0.3
                },
                "database_postgres": {
                    "success": False,
                    "health_score": 0.2
                }
            },
            "staging_analysis": {
                "business_impact": {"impact_level": "critical"},
                "remediation_suggestions": [
                    {
                        "action": "restart_websocket_service",
                        "description": "Restart WebSocket service",
                        "urgency": "high"
                    }
                ]
            },
            "alert_status": {
                "alerts_active": True,
                "alert_count": 2,
                "alert_severity": "critical"
            }
        }
        
        mock_monitor.get_critical_health.return_value = mock_critical_data
        
        response = client.get("/staging/health/critical?alert_threshold=0.8")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["critical_analysis"]["components_below_threshold"] == 2
        assert data["critical_analysis"]["business_impact_level"] == "critical"
        assert data["critical_analysis"]["alert_severity"] == "critical"
        assert data["critical_analysis"]["immediate_action_required"] is True
        assert len(data["automated_remediation"]) > 0
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_critical_health_custom_threshold(self, mock_monitor):
        """Test critical health check with custom alert threshold."""
        mock_critical_data = {
            "status": "degraded",
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 0.75  # Below custom threshold of 0.8
                }
            },
            "staging_analysis": {
                "remediation_suggestions": []
            }
        }
        
        mock_monitor.get_critical_health.return_value = mock_critical_data
        
        response = client.get("/staging/health/critical?alert_threshold=0.8")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["alert_threshold_used"] == 0.8
        assert data["critical_analysis"]["components_below_threshold"] == 1


class TestHealthAlertsEndpoint:
    """Test health alerts subscription endpoint."""
    
    def test_subscribe_to_health_alerts_success(self):
        """Test successful health alerts subscription."""
        webhook_payload = {
            "webhook_url": "https://example.com/webhook",
            "alert_types": ["critical", "warning"]
        }
        
        with patch('netra_backend.app.routes.staging_health._is_valid_webhook_url', return_value=True), \
             patch('netra_backend.app.routes.staging_health._register_webhook_subscription', return_value="sub-123"):
            
            response = client.post(
                "/staging/health/alerts/subscribe",
                params={
                    "webhook_url": webhook_payload["webhook_url"],
                    "alert_types": webhook_payload["alert_types"]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "subscribed"
        assert data["subscription_id"] == "sub-123"
        assert data["webhook_url"] == webhook_payload["webhook_url"]
        assert data["alert_types"] == webhook_payload["alert_types"]
        assert data["test_notification_sent"] is True
    
    def test_subscribe_to_health_alerts_invalid_webhook(self):
        """Test health alerts subscription with invalid webhook URL."""
        with patch('netra_backend.app.routes.staging_health._is_valid_webhook_url', return_value=False):
            
            response = client.post(
                "/staging/health/alerts/subscribe",
                params={"webhook_url": "invalid-url"}
            )
        
        assert response.status_code == 400
        assert "Invalid webhook URL provided" in response.json()["detail"]


class TestHealthSummaryEndpoint:
    """Test health status summary endpoint."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_get_health_summary_success(self, mock_monitor):
        """Test successful health summary retrieval."""
        mock_critical_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {"success": True},
                "database_postgres": {"success": True},
                "service_auth": {"success": True}
            },
            "alert_status": {
                "alerts_active": False,
                "alert_count": 0,
                "alert_severity": "none"
            }
        }
        
        mock_monitor.get_critical_health.return_value = mock_critical_data
        
        response = client.get("/staging/health/status/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["overall_status"] == "healthy"
        assert "component_summary" in data
        assert "alert_summary" in data
        assert "uptime_seconds" in data
        assert data["endpoint"] == "health_summary"
        
        # Verify component summary
        component_summary = data["component_summary"]
        assert component_summary["total_components"] == 3
        assert component_summary["healthy_components"] == 3
        assert component_summary["unhealthy_components"] == 0
        assert component_summary["health_percentage"] == 100.0
        
        # Verify alert summary
        alert_summary = data["alert_summary"]
        assert alert_summary["alerts_active"] is False
        assert alert_summary["alert_count"] == 0
        assert alert_summary["highest_severity"] == "none"


class TestHealthEndpointsErrorHandling:
    """Test error handling across health monitoring endpoints."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_websocket_health_error_handling(self, mock_monitor):
        """Test WebSocket health endpoint error handling."""
        mock_monitor.get_comprehensive_health.side_effect = Exception("Monitor failed")
        
        response = client.get("/staging/health/websocket")
        
        assert response.status_code == 500
        assert "Failed to retrieve WebSocket health" in response.json()["detail"]
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_database_health_error_handling(self, mock_monitor):
        """Test database health endpoint error handling."""
        mock_monitor.get_comprehensive_health.side_effect = Exception("Database check failed")
        
        response = client.get("/staging/health/database")
        
        assert response.status_code == 500
        assert "Failed to retrieve database health" in response.json()["detail"]
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_services_health_error_handling(self, mock_monitor):
        """Test services health endpoint error handling."""
        mock_monitor.get_comprehensive_health.side_effect = Exception("Service check failed")
        
        response = client.get("/staging/health/services")
        
        assert response.status_code == 500
        assert "Failed to retrieve services health" in response.json()["detail"]
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_performance_metrics_error_handling(self, mock_monitor):
        """Test performance metrics endpoint error handling."""
        mock_monitor.get_comprehensive_health.side_effect = Exception("Metrics collection failed")
        
        response = client.get("/staging/health/metrics")
        
        assert response.status_code == 500
        assert "Failed to retrieve performance metrics" in response.json()["detail"]
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_critical_health_error_handling(self, mock_monitor):
        """Test critical health endpoint error handling."""
        mock_monitor.get_critical_health.side_effect = Exception("Critical health check failed")
        
        response = client.get("/staging/health/critical")
        
        assert response.status_code == 500
        assert "Failed to retrieve critical health status" in response.json()["detail"]


class TestHealthEndpointsIntegration:
    """Integration tests for health monitoring API endpoints."""
    
    @patch('netra_backend.app.routes.staging_health.staging_health_monitor')
    def test_complete_health_monitoring_workflow(self, mock_monitor):
        """Test complete health monitoring workflow across all endpoints."""
        # Setup comprehensive health data
        comprehensive_health_data = {
            "status": "healthy",
            "service": "staging_environment",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0,
                    "response_time_ms": 50.0,
                    "details": {
                        "websocket_server_available": True,
                        "event_transmission_working": True,
                        "event_pipeline_functional": True
                    }
                },
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 25.0
                },
                "service_auth_service": {
                    "success": True,
                    "health_score": 0.98,
                    "response_time_ms": 100.0
                },
                "staging_performance": {
                    "success": True,
                    "details": {
                        "performance_metrics": {
                            "api_response_time_ms": 200.0,
                            "websocket_latency_ms": 50.0,
                            "database_query_time_ms": 30.0
                        }
                    }
                }
            },
            "staging_analysis": {
                "business_impact": {"impact_level": "none"},
                "trend_analysis": {"overall_trend": "stable"},
                "remediation_suggestions": [],
                "failure_prediction": {"failure_prediction_available": False}
            },
            "alert_status": {
                "alerts_active": False,
                "alert_count": 0,
                "alert_severity": "none"
            }
        }
        
        # Setup critical health data
        critical_health_data = {
            "status": "healthy",
            "service": "staging_environment_critical",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {"success": True, "health_score": 1.0},
                "database_postgres": {"success": True, "health_score": 0.95},
                "service_auth_service": {"success": True, "health_score": 0.98}
            },
            "focus": "critical_components_only"
        }
        
        mock_monitor.get_comprehensive_health.return_value = comprehensive_health_data
        mock_monitor.get_critical_health.return_value = critical_health_data
        
        # Test 1: Overall health overview
        response = client.get("/staging/health")
        assert response.status_code == 200
        overview_data = response.json()
        assert overview_data["status"] == "healthy"
        
        # Test 2: WebSocket specific health
        response = client.get("/staging/health/websocket")
        assert response.status_code == 200
        websocket_data = response.json()
        assert websocket_data["status"] == "healthy"
        assert websocket_data["health_percentage"] == 100.0
        
        # Test 3: Database health
        response = client.get("/staging/health/database")
        assert response.status_code == 200
        database_data = response.json()
        assert database_data["status"] == "healthy"
        assert database_data["databases_healthy"] == 1
        
        # Test 4: Services health
        response = client.get("/staging/health/services")
        assert response.status_code == 200
        services_data = response.json()
        assert services_data["status"] == "healthy"
        assert services_data["services_healthy"] == 1
        
        # Test 5: Performance metrics
        response = client.get("/staging/health/metrics")
        assert response.status_code == 200
        metrics_data = response.json()
        assert "performance" in metrics_data
        
        # Test 6: Critical health
        response = client.get("/staging/health/critical")
        assert response.status_code == 200
        critical_data = response.json()
        assert critical_data["status"] == "healthy"
        
        # Test 7: Health summary
        response = client.get("/staging/health/status/summary")
        assert response.status_code == 200
        summary_data = response.json()
        assert summary_data["overall_status"] == "healthy"
        
        # Verify all endpoints return consistent status
        statuses = [
            overview_data["status"],
            websocket_data["status"],
            database_data["status"],
            services_data["status"],
            critical_data["status"],
            summary_data["overall_status"]
        ]
        
        assert all(status == "healthy" for status in statuses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])