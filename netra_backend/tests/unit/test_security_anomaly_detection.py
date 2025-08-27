"""Test Suite: Security Anomaly Detection (Iteration 95)

Production-critical tests for security anomaly detection and threat identification.
Ensures system can detect and respond to security incidents in real-time.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from netra_backend.app.core.security_monitor import SecurityAnomalyDetector
from netra_backend.app.monitoring.metrics_collector import MetricsCollector


class TestSecurityAnomalyDetection:
    """Security anomaly detection tests."""

    @pytest.mark.asyncio
    async def test_unusual_authentication_pattern_detection(self):
        """Test detection of unusual authentication patterns and potential attacks."""
        anomaly_detector = SecurityAnomalyDetector()
        metrics = Mock(spec=MetricsCollector)
        
        # Simulate suspicious authentication activity
        auth_events = [
            {'user_id': 'user_123', 'ip': '192.168.1.100', 'timestamp': '2025-08-27T14:30:00Z', 'success': False},
            {'user_id': 'user_123', 'ip': '192.168.1.101', 'timestamp': '2025-08-27T14:30:05Z', 'success': False},
            {'user_id': 'user_123', 'ip': '192.168.1.102', 'timestamp': '2025-08-27T14:30:10Z', 'success': False},
            {'user_id': 'user_123', 'ip': '10.0.0.50', 'timestamp': '2025-08-27T14:30:15Z', 'success': True}
        ]
        
        with patch.object(anomaly_detector, 'metrics_collector', metrics):
            with patch.object(anomaly_detector, '_trigger_security_alert', AsyncMock()) as mock_alert:
                result = await anomaly_detector.analyze_authentication_patterns(auth_events)
                
                assert result.anomaly_detected is True
                assert result.threat_level == 'high'
                assert result.pattern_type == 'brute_force_with_ip_hopping'
                assert len(result.suspicious_ips) >= 3
                mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_abuse_detection_and_response(self):
        """Test detection of API abuse patterns and automated response."""
        anomaly_detector = SecurityAnomalyDetector()
        
        # Simulate API abuse pattern
        api_activity = {
            'client_id': 'suspicious_client_789',
            'requests_per_minute': 500,  # Far above normal
            'error_rate': 0.85,  # Very high error rate
            'endpoints_hit': ['/api/users', '/api/threads', '/api/agents'],
            'time_window': '2025-08-27T14:30:00Z_to_2025-08-27T14:35:00Z'
        }
        
        with patch.object(anomaly_detector, '_implement_rate_limiting', AsyncMock()) as mock_limit:
            with patch.object(anomaly_detector, '_log_security_incident', AsyncMock()) as mock_log:
                result = await anomaly_detector.detect_api_abuse(api_activity)
                
                assert result.abuse_detected is True
                assert result.severity == 'critical'
                assert result.mitigation_applied is True
                assert 'rate_limiting' in result.applied_mitigations
                mock_limit.assert_called_once()
                mock_log.assert_called_once()