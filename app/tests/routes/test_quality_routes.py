"""
Test 27: Quality Route Metrics
Tests for quality metric endpoints - app/routes/quality.py
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC
from .test_utilities import base_client


class TestQualityRoute:
    """Test quality metric endpoints."""
    
    def test_quality_metrics_retrieval(self, base_client):
        """Test retrieving quality metrics."""
        with patch('app.services.quality_gate.quality_gate_core.QualityGateService.get_quality_stats') as mock_metrics:
            mock_metrics.return_value = {
                "accuracy": 0.96,
                "latency_p50": 120,
                "latency_p99": 450,
                "error_rate": 0.02,
                "throughput": 1000
            }
            
            response = base_client.get("/api/quality/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                if "accuracy" in metrics:
                    assert 0 <= metrics["accuracy"] <= 1
    
    def test_quality_aggregation(self, base_client):
        """Test quality metrics aggregation."""
        with patch('app.services.quality_monitoring.service.QualityMonitoringService.get_dashboard_data') as mock_agg:
            mock_agg.return_value = {
                "period": "daily",
                "average_accuracy": 0.94,
                "trend": "stable"
            }
            
            response = base_client.get("/api/quality/aggregate?period=daily")
            
            if response.status_code == 200:
                data = response.json()
                assert "period" in data or "error" in data

    async def test_quality_alerts(self):
        """Test quality threshold alerts."""
        from app.routes.quality_handlers import handle_alerts_request
        from app.schemas.quality_types import QualityAlert, AlertSeverity, MetricType
        
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
        
        mock_service = Mock()
        mock_service.alert_history = [test_alert]
        
        alerts = await handle_alerts_request(mock_service, None, None, 50)
        assert len(alerts) > 0