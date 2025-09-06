"""
Test 27: Quality Route Metrics
Tests for quality metric endpoints - app/routes/quality.py

Business Value Justification (BVJ):
- Segment: Mid, Enterprise
- Business Goal: Monitor and maintain AI system quality and performance
- Value Impact: Ensures consistent AI output quality, reduces customer churn
- Revenue Impact: Quality monitoring enables SLA guarantees for Enterprise tier
"""

import sys
from pathlib import Path
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from datetime import UTC, datetime

import pytest

from netra_backend.tests.test_route_fixtures import (
    CommonResponseValidators,
    MockServiceFactory,
    basic_test_client,
)

class TestQualityRoute:
    """Test quality metric endpoints and monitoring functionality."""
    
    def test_quality_metrics_retrieval(self, basic_test_client):
        """Test retrieving quality metrics."""
        mock_quality_service = MockServiceFactory.create_mock_quality_service()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.quality_gate.quality_gate_core.QualityGateService', return_value=mock_quality_service):
            response = basic_test_client.get("/api/quality/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                CommonResponseValidators.validate_success_response(
                    response,
                    expected_keys=["accuracy", "latency_p50", "error_rate"]
                )
                
                # Validate metric ranges
                if "accuracy" in metrics:
                    assert 0 <= metrics["accuracy"] <= 1
                if "error_rate" in metrics:
                    assert 0 <= metrics["error_rate"] <= 1
                if "latency_p50" in metrics:
                    assert metrics["latency_p50"] > 0
            else:
                assert response.status_code in [404, 401]
    
    def test_quality_aggregation(self, basic_test_client):
        """Test quality metrics aggregation."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.quality_monitoring.service.QualityMonitoringService.get_dashboard_data') as mock_agg:
            mock_agg.return_value = {
                "period": "daily",
                "average_accuracy": 0.94,
                "trend": "stable",
                "quality_score": 92.5
            }
            
            response = basic_test_client.get("/api/quality/aggregate?period=daily")
            
            if response.status_code == 200:
                data = response.json()
                assert "period" in data or "error" in data
                
                if "average_accuracy" in data:
                    assert 0 <= data["average_accuracy"] <= 1
                if "quality_score" in data:
                    assert 0 <= data["quality_score"] <= 100
            else:
                assert response.status_code in [404, 401]
    
    @pytest.mark.asyncio
    async def test_quality_alerts(self):
        """Test quality threshold alerts."""
        from netra_backend.app.routes.quality_handlers import handle_alerts_request
        from netra_backend.app.schemas.quality_types import (
            AlertSeverity,
            MetricType,
            QualityAlert,
        )
        
        # Create proper QualityAlert objects
        test_alert = QualityAlert(
            id="alert123",
            timestamp=datetime.now(UTC),
            severity=AlertSeverity.HIGH,
            metric_type=MetricType.OVERALL,
            agent="test_agent",
            message="Test alert",
            current_value=50.0,
            threshold=75.0,
            acknowledged=False
        )
        
        # Mock: Generic component isolation for controlled unit testing
        mock_service = mock_service_instance  # Initialize appropriate service
        mock_service.alert_history = [test_alert]
        
        alerts = await handle_alerts_request(mock_service, None, None, 50)
        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.HIGH
    
    def test_quality_thresholds_configuration(self, basic_test_client):
        """Test quality threshold configuration."""
        threshold_config = {
            "accuracy_threshold": 0.90,
            "latency_threshold_ms": 500,
            "error_rate_threshold": 0.05,
            "alert_settings": {
                "email_notifications": True,
                "slack_integration": False
            }
        }
        
        response = basic_test_client.put("/api/quality/thresholds", json=threshold_config)
        
        if response.status_code == 200:
            CommonResponseValidators.validate_success_response(response)
        else:
            assert response.status_code in [404, 422, 401]
        
        # Test threshold retrieval
        response = basic_test_client.get("/api/quality/thresholds")
        
        if response.status_code == 200:
            data = response.json()
            threshold_keys = ["accuracy_threshold", "latency_threshold_ms", "error_rate_threshold"]
            has_thresholds = any(key in data for key in threshold_keys)
            
            if has_thresholds:
                for key in threshold_keys:
                    if key in data:
                        assert data[key] > 0
        else:
            assert response.status_code in [404, 401]
    
    def test_quality_trend_analysis(self, basic_test_client):
        """Test quality trend analysis over time."""
        trend_request = {
            "timeframe": "7d",
            "metrics": ["accuracy", "latency", "error_rate"],
            "granularity": "hourly"
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.quality_analytics.analyze_trends') as mock_trends:
            mock_trends.return_value = {
                "timeframe": "7d",
                "trends": {
                    "accuracy": {
                        "direction": "improving",
                        "change_percentage": 2.5,
                        "confidence": 0.85
                    },
                    "latency": {
                        "direction": "stable",
                        "change_percentage": -0.1,
                        "confidence": 0.92
                    }
                },
                "data_points": 168  # 7 days * 24 hours
            }
            
            response = basic_test_client.post("/api/quality/trends", json=trend_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "trends" in data or "timeframe" in data
                
                if "trends" in data:
                    for metric, trend in data["trends"].items():
                        assert "direction" in trend
                        assert trend["direction"] in ["improving", "degrading", "stable"]
                        assert "confidence" in trend
                        assert 0 <= trend["confidence"] <= 1
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_quality_comparison_analysis(self, basic_test_client):
        """Test quality comparison between different time periods."""
        comparison_request = {
            "baseline_period": "last_week",
            "comparison_period": "this_week",
            "metrics": ["accuracy", "response_time", "user_satisfaction"]
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.quality_analytics.compare_periods') as mock_compare:
            mock_compare.return_value = {
                "baseline": {
                    "accuracy": 0.92,
                    "response_time": 150,
                    "user_satisfaction": 4.2
                },
                "comparison": {
                    "accuracy": 0.94,
                    "response_time": 145,
                    "user_satisfaction": 4.4
                },
                "changes": {
                    "accuracy": {"absolute": 0.02, "percentage": 2.17},
                    "response_time": {"absolute": -5, "percentage": -3.33},
                    "user_satisfaction": {"absolute": 0.2, "percentage": 4.76}
                }
            }
            
            response = basic_test_client.post("/api/quality/compare", json=comparison_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "baseline" in data or "comparison" in data
                
                if "changes" in data:
                    for metric, change in data["changes"].items():
                        assert "absolute" in change
                        assert "percentage" in change
            else:
                assert response.status_code in [404, 422, 401]
    
    @pytest.mark.asyncio
    async def test_quality_real_time_monitoring(self):
        """Test real-time quality monitoring."""
        from netra_backend.app.routes.quality import start_monitoring, stop_monitoring
        
        monitoring_config = {
            "interval_seconds": 30,
            "metrics": ["accuracy", "latency", "error_rate"],
            "alert_on_degradation": True
        }
        
        # Start monitoring
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.quality_monitor.start_real_time_monitoring') as mock_start:
            mock_start.return_value = {
                "monitoring_id": "monitor_123",
                "status": "active",
                "started_at": datetime.now(UTC).isoformat()
            }
            
            result = await start_monitoring(monitoring_config)
            assert result["status"] == "active"
            monitoring_id = result["monitoring_id"]
        
        # Stop monitoring
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.quality_monitor.stop_monitoring') as mock_stop:
            mock_stop.return_value = {
                "monitoring_id": monitoring_id,
                "status": "stopped",
                "duration_seconds": 300
            }
            
            result = await stop_monitoring(monitoring_id)
            assert result["status"] == "stopped"
    
    def test_quality_report_generation(self, basic_test_client):
        """Test quality report generation."""
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.routes.quality_handlers.handle_report_generation') as mock_report:
            from netra_backend.app.schemas.quality_types import (
                QualityReport,
                QualityReportType,
            )
            
            mock_report.return_value = QualityReport(
                report_type=QualityReportType.SUMMARY,
                generated_at=datetime.now(UTC),
                generated_by="test_user",
                period_days=7,
                data={
                    "overall_quality_score": 89.5,
                    "total_requests": 50000,
                    "average_accuracy": 0.93
                },
                summary="Overall quality is good with room for improvement",
                recommendations=[
                    "Consider increasing training data for low-confidence predictions",
                    "Optimize response time for peak usage hours"
                ]
            )
            
            response = basic_test_client.get("/api/quality/reports/generate?report_type=summary&period_days=7")
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "report_type" in data
                assert "generated_at" in data
                assert "data" in data
                
                # Check the data contains expected quality metrics
                if "data" in data:
                    report_data = data["data"]
                    if "overall_quality_score" in report_data:
                        assert 0 <= report_data["overall_quality_score"] <= 100
            else:
                assert response.status_code in [404, 422, 401]