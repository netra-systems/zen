"""Test Suite: Security Threat Response (Iteration 96)

Production-critical tests for automated security threat response and mitigation.
Validates system's ability to respond to and neutralize security threats.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from netra_backend.app.core.security_response import SecurityThreatResponder
from netra_backend.app.core.async_rate_limiter import AsyncRateLimiter


class TestSecurityThreatResponse:
    """Security threat response tests."""

    @pytest.mark.asyncio
    async def test_automated_threat_isolation_response(self):
        """Test automated isolation of compromised accounts and IP addresses."""
        threat_responder = SecurityThreatResponder()
        
        threat_context = {
            'threat_type': 'compromised_account',
            'affected_user_id': 'user_456',
            'source_ips': ['203.0.113.45', '198.51.100.78'],
            'severity': 'critical',
            'detection_time': '2025-08-27T14:35:22Z',
            'evidence': ['multiple_location_logins', 'suspicious_api_calls', 'data_exfiltration_attempt']
        }
        
        with patch.object(threat_responder, '_isolate_user_account', AsyncMock()) as mock_isolate:
            with patch.object(threat_responder, '_block_source_ips', AsyncMock()) as mock_block:
                with patch.object(threat_responder, '_notify_security_team', AsyncMock()) as mock_notify:
                    result = await threat_responder.execute_threat_response(threat_context)
                    
                    assert result.account_isolated is True
                    assert result.ips_blocked is True
                    assert result.security_team_notified is True
                    assert result.response_time_seconds < 30  # Must respond within 30 seconds
                    mock_isolate.assert_called_once_with('user_456')
                    mock_block.assert_called_once_with(['203.0.113.45', '198.51.100.78'])

    @pytest.mark.asyncio
    async def test_ddos_mitigation_activation(self):
        """Test DDoS attack detection and automated mitigation activation."""
        threat_responder = SecurityThreatResponder()
        rate_limiter = Mock(spec=AsyncRateLimiter)
        
        ddos_attack = {
            'attack_type': 'volumetric_ddos',
            'requests_per_second': 5000,  # Extremely high
            'source_count': 150,  # Multiple sources
            'target_endpoints': ['/api/threads', '/api/users', '/websocket'],
            'attack_duration_seconds': 45,
            'legitimate_traffic_ratio': 0.05  # Very low legitimate traffic
        }
        
        with patch.object(threat_responder, 'rate_limiter', rate_limiter):
            with patch.object(threat_responder, '_activate_ddos_protection', AsyncMock()) as mock_protect:
                with patch.object(threat_responder, '_enable_emergency_rate_limits', AsyncMock()) as mock_emergency:
                    result = await threat_responder.mitigate_ddos_attack(ddos_attack)
                    
                    assert result.ddos_protection_activated is True
                    assert result.emergency_limits_enabled is True
                    assert result.attack_mitigated is True
                    assert result.legitimate_traffic_preserved >= 0.95  # Preserve legitimate traffic
                    mock_protect.assert_called_once()
                    mock_emergency.assert_called_once()