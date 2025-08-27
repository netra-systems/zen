"""Test Suite: Performance Alert Thresholds (Iteration 98)

Production-critical tests for performance alert threshold management.
Validates proper alerting for performance issues before they impact users.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from netra_backend.app.monitoring.alert_manager import PerformanceAlertManager
from netra_backend.app.monitoring.threshold_manager import ThresholdManager


class TestPerformanceAlertThresholds:
    """Performance alert threshold tests."""

    @pytest.mark.asyncio
    async def test_cascading_performance_alert_levels(self):
        """Test cascading performance alerts with escalating severity levels."""
        alert_manager = PerformanceAlertManager()
        
        # Define performance thresholds
        thresholds = {
            'response_time_warning_ms': 200,
            'response_time_critical_ms': 500,
            'response_time_emergency_ms': 1000,
            'error_rate_warning': 0.02,  # 2%
            'error_rate_critical': 0.05,  # 5%
            'error_rate_emergency': 0.10,  # 10%
            'cpu_warning': 0.80,  # 80%
            'cpu_critical': 0.90,  # 90%
            'cpu_emergency': 0.95   # 95%
        }
        
        # Performance metrics exceeding critical thresholds
        critical_metrics = {
            'avg_response_time_ms': 750,  # Above critical threshold
            'error_rate': 0.08,  # Above critical threshold
            'cpu_utilization': 0.93,  # Above critical threshold
            'timestamp': '2025-08-27T14:40:00Z'
        }
        
        with patch.object(alert_manager, '_load_alert_thresholds', return_value=thresholds):
            with patch.object(alert_manager, '_send_critical_alert', AsyncMock()) as mock_critical:
                with patch.object(alert_manager, '_trigger_emergency_response', AsyncMock()) as mock_emergency:
                    result = await alert_manager.evaluate_performance_metrics(critical_metrics)
                    
                    assert result.alert_level == 'emergency'  # Highest severity triggered
                    assert result.critical_alerts_sent > 0
                    assert result.emergency_response_triggered is True
                    assert len(result.breached_thresholds) >= 3
                    mock_critical.assert_called()
                    mock_emergency.assert_called_once()

    @pytest.mark.asyncio
    async def test_adaptive_threshold_adjustment(self):
        """Test adaptive threshold adjustment based on historical performance patterns."""
        threshold_manager = ThresholdManager()
        
        # Historical performance data showing improved baseline
        historical_data = {
            'last_30_days': {
                'avg_response_time_p95': 120.0,  # Improved performance
                'error_rate_avg': 0.008,  # Lower error rate
                'cpu_utilization_p95': 0.70  # More efficient
            },
            'previous_thresholds': {
                'response_time_warning_ms': 200,
                'error_rate_warning': 0.02,
                'cpu_warning': 0.80
            }
        }
        
        with patch.object(threshold_manager, '_analyze_performance_trends', AsyncMock()) as mock_analyze:
            with patch.object(threshold_manager, '_update_threshold_configuration', AsyncMock()) as mock_update:
                result = await threshold_manager.adjust_thresholds_adaptively(historical_data)
                
                assert result.thresholds_adjusted is True
                assert result.new_thresholds['response_time_warning_ms'] < 200  # Tighter threshold
                assert result.new_thresholds['error_rate_warning'] < 0.02  # Tighter threshold
                assert result.optimization_enabled is True
                mock_analyze.assert_called_once()
                mock_update.assert_called_once()