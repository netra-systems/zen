"""
WebSocket Security Attack Tests: Protection and Prevention

Security attack simulation tests including session hijacking, brute force attacks,
malformed token handling, and token tampering detection.

Business Value: Validates security controls against real attack vectors,
ensuring customer data protection and regulatory compliance.
"""
import asyncio
import json
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment
import pytest
import jwt
import websockets
from websockets import ConnectionClosed, InvalidStatus
from netra_backend.app.logging_config import central_logger
from tests.e2e.websocket_resilience.websocket_recovery_fixtures import SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient, TokenRefreshService, jwt_generator, audit_logger, token_refresh_service, expired_token, valid_token, near_expiry_token, create_tampered_token_expiry, create_tampered_token_user, create_tampered_token_permissions, SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient, TokenRefreshService, jwt_generator, audit_logger, token_refresh_service, expired_token, valid_token, near_expiry_token, create_tampered_token_expiry, create_tampered_token_user, create_tampered_token_permissions
logger = central_logger.get_logger(__name__)

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_hijacking_prevention_with_expired_tokens(jwt_generator, audit_logger):
    """
    Test Case 1: Session hijacking prevention with old tokens.
    
    Validates protection against session hijacking attempts using expired tokens,
    ensuring complete access denial and session state cleanup.
    """
    logger.info('Testing session hijacking prevention with expired tokens')
    user_id = 'victim_user_123'
    original_token = jwt_generator.create_valid_token(user_id, expires_in_minutes=1)
    legitimate_client = SecureWebSocketTestClient('ws://mock-server/ws', original_token, jwt_generator, audit_logger)
    success, result = await legitimate_client.attempt_connection({'X-Forwarded-For': '192.168.1.100', 'User-Agent': 'LegitimateClient/1.0'})
    assert success, 'Legitimate connection should succeed'
    assert legitimate_client.is_connected, 'Legitimate client should be connected'
    logger.info('Waiting for token to expire to simulate captured expired token')
    await asyncio.sleep(65)
    token_validation = jwt_generator.validate_token_jwt(original_token)
    assert 'error' in token_validation, 'Token should be expired'
    attacker_ips = ['10.0.0.1', '172.16.0.50', '203.0.113.10']
    attack_attempts = []
    for i, attacker_ip in enumerate(attacker_ips):
        logger.info(f'Simulating hijacking attempt {i + 1} from {attacker_ip}')
        attacker_client = SecureWebSocketTestClient('ws://mock-server/ws', original_token, jwt_generator, audit_logger)
        attack_headers = {'X-Forwarded-For': attacker_ip, 'User-Agent': f'AttackerBot/{i + 1}.0', 'X-Attack-Vector': 'session_hijacking'}
        attack_start = time.time()
        attack_success, attack_result = await attacker_client.attempt_connection(attack_headers)
        attack_time = time.time() - attack_start
        assert not attack_success, f'Attack attempt {i + 1} should be blocked'
        assert attack_result['error'] == 'authentication_failed', 'Should get authentication error'
        assert 'Token expired' in attack_result['message'], 'Should indicate token expiry'
        assert attack_time < 0.1, f'Attack should be rejected immediately ({attack_time:.3f}s)'
        assert not attacker_client.is_connected, 'Attacker should not be connected'
        assert attacker_client.websocket is None, 'No session should be created for attacker'
        attack_attempts.append({'ip': attacker_ip, 'response_time': attack_time, 'result': attack_result})
        await attacker_client.disconnect()
        await asyncio.sleep(0.2)
    security_events = audit_logger.get_events_for_user(user_id)
    hijacking_events = [e for e in security_events if e['event_type'] == 'expired_token_attempt']
    assert len(hijacking_events) >= len(attacker_ips), 'All hijacking attempts should be logged'
    logged_ips = [event['source_ip'] for event in hijacking_events]
    for attacker_ip in attacker_ips:
        assert attacker_ip in logged_ips, f'Attacker IP {attacker_ip} should be logged'
    alert_count = audit_logger.get_alert_count()
    if alert_count > 0:
        alerts = audit_logger.alert_triggers
        victim_alerts = [a for a in alerts if a['user_id'] == user_id]
        if victim_alerts:
            alert = victim_alerts[0]
            assert alert['alert_type'] == 'repeated_expired_token_attempts', 'Should detect hijacking pattern'
            assert alert['severity'] == 'CRITICAL', 'Should have critical severity'
    response_times = [attempt['response_time'] for attempt in attack_attempts]
    max_time_variance = max(response_times) - min(response_times)
    assert max_time_variance < 0.05, f'Response time variance {max_time_variance:.3f}s too high (timing attack risk)'
    await legitimate_client.disconnect()
    logger.info(f'[U+2713] Session hijacking prevented: {len(attack_attempts)} attempts blocked, {alert_count} alerts triggered')

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiple_rapid_expired_token_attempts_brute_force_protection(jwt_generator, audit_logger):
    """
    Test Case 2: Multiple expired token attempts (brute force protection).
    
    Tests system resilience against brute force attacks using expired tokens,
    validating rate limiting and protection mechanisms.
    """
    logger.info('Testing brute force protection against expired token attempts')
    user_id = 'brute_force_target'
    attack_attempts = 15
    failed_attempts = []
    expired_tokens = [jwt_generator.create_expired_token(user_id, expired_minutes_ago=i + 1) for i in range(attack_attempts)]
    for i, token in enumerate(expired_tokens):
        client = SecureWebSocketTestClient('ws://mock-server/ws', token, jwt_generator, audit_logger)
        attack_headers = {'X-Forwarded-For': '203.0.113.50', 'User-Agent': f'BruteForceBot/1.{i}', 'X-Attack-Type': 'brute_force'}
        attempt_start = time.time()
        success, result = await client.attempt_connection(attack_headers)
        attempt_time = time.time() - attempt_start
        assert not success, f'Attempt {i + 1} should fail'
        assert result['error'] == 'authentication_failed', 'Should get authentication error'
        failed_attempts.append({'attempt': i + 1, 'response_time': attempt_time, 'result': result})
        await asyncio.sleep(0.05)
    assert len(failed_attempts) == attack_attempts, 'All brute force attempts should be blocked'
    response_times = [attempt['response_time'] for attempt in failed_attempts]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    assert avg_response_time < 0.1, f'Average response time {avg_response_time:.3f}s too slow under attack'
    assert max_response_time < 0.2, f'Max response time {max_response_time:.3f}s too slow under attack'
    user_events = audit_logger.get_events_for_user(user_id)
    assert len(user_events) >= attack_attempts, 'All attack attempts should be logged'
    alert_count = audit_logger.get_alert_count()
    assert alert_count > 0, 'Brute force attack should trigger alerts'
    alerts = audit_logger.alert_triggers
    brute_force_alerts = [a for a in alerts if a['user_id'] == user_id]
    assert len(brute_force_alerts) >= 1, 'Should have alerts for brute force target'
    alert = brute_force_alerts[0]
    assert alert['alert_type'] == 'repeated_expired_token_attempts', 'Should detect brute force pattern'
    assert alert['severity'] == 'CRITICAL', 'Should escalate to critical'
    assert alert['attempt_count'] >= 5, 'Should count multiple attempts'
    logger.info(f'[U+2713] Brute force protection: {attack_attempts} attempts blocked, avg {avg_response_time:.3f}s response')

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_malformed_expired_token_handling(jwt_generator, audit_logger):
    """
    Test Case 3: Malformed expired token handling.
    
    Tests handling of malformed tokens that appear expired, validating
    proper error handling and security logging.
    """
    logger.info('Testing malformed expired token handling')
    user_id = 'malformed_test_user'
    malformed_scenarios = [{'name': 'Invalid signature expired token', 'token': jwt_generator.create_malformed_expired_token(user_id), 'expected_error': 'invalid'}, {'name': 'Completely invalid token', 'token': 'invalid.token.string', 'expected_error': 'invalid'}, {'name': 'Empty token', 'token': '', 'expected_error': 'invalid'}, {'name': 'Base64 garbage', 'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.garbage.signature', 'expected_error': 'invalid'}]
    test_results = []
    for i, scenario in enumerate(malformed_scenarios):
        logger.info(f"Testing scenario: {scenario['name']}")
        client = SecureWebSocketTestClient('ws://mock-server/ws', scenario['token'], jwt_generator, audit_logger)
        test_headers = {'X-Forwarded-For': f'192.168.1.{100 + i}', 'User-Agent': f'MalformedTestClient/{i + 1}.0', 'X-Test-Scenario': scenario['name']}
        attempt_start = time.time()
        success, result = await client.attempt_connection(test_headers)
        attempt_time = time.time() - attempt_start
        assert not success, f"Malformed token should be rejected: {scenario['name']}"
        assert result['error'] == 'authentication_failed', 'Should get authentication error'
        assert 'Token expired' in result['message'] or 'Authentication failed' in result['message'], 'Should get appropriate error message'
        assert attempt_time < 0.1, f'Malformed token rejection should be immediate ({attempt_time:.3f}s)'
        test_results.append({'scenario': scenario['name'], 'response_time': attempt_time, 'result': result})
        await client.disconnect()
    response_times = [result['response_time'] for result in test_results]
    avg_response_time = sum(response_times) / len(response_times)
    time_variance = max(response_times) - min(response_times)
    assert avg_response_time < 0.05, f'Average malformed token handling {avg_response_time:.3f}s too slow'
    assert time_variance < 0.02, f'Response time variance {time_variance:.3f}s too high (timing attack risk)'
    all_events = audit_logger.security_events
    recent_events = [e for e in all_events if (datetime.now(timezone.utc) - datetime.fromisoformat(e['timestamp'])).total_seconds() < 60]
    assert len(recent_events) >= 1, 'Malformed token attempts should generate security events'
    logger.info(f'[U+2713] Malformed token handling: {len(test_results)} scenarios tested, avg {avg_response_time:.3f}s')

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_token_tampering_with_expired_timestamps(jwt_generator, audit_logger):
    """
    Test Case 4: Token tampering with expired timestamps.
    
    Tests detection and handling of tampered tokens that have been modified
    to extend expiration times or alter other claims.
    """
    logger.info('Testing token tampering with expired timestamps')
    user_id = 'tampering_test_user'
    legitimate_expired = jwt_generator.create_expired_token(user_id, expired_minutes_ago=10)
    tampering_scenarios = [{'name': 'Modified expiration time', 'token': create_tampered_token_expiry(legitimate_expired), 'description': 'Token with modified expiry timestamp'}, {'name': 'Modified user ID in expired token', 'token': create_tampered_token_user(legitimate_expired), 'description': 'Expired token with different user ID'}, {'name': 'Modified permissions in expired token', 'token': create_tampered_token_permissions(legitimate_expired), 'description': 'Expired token with elevated permissions'}]
    test_results = []
    for i, scenario in enumerate(tampering_scenarios):
        logger.info(f"Testing tampering scenario: {scenario['name']}")
        client = SecureWebSocketTestClient('ws://mock-server/ws', scenario['token'], jwt_generator, audit_logger)
        attempt_headers = {'X-Forwarded-For': f'203.0.113.{50 + i}', 'User-Agent': f'TamperingTestClient/{i + 1}.0', 'X-Tampering-Test': scenario['name']}
        attempt_start = time.time()
        success, result = await client.attempt_connection(attempt_headers)
        attempt_time = time.time() - attempt_start
        assert not success, f"Tampered token should be rejected: {scenario['name']}"
        assert result['error'] == 'authentication_failed', 'Should get authentication error'
        assert attempt_time < 0.1, f'Tampering detection should be immediate ({attempt_time:.3f}s)'
        test_results.append({'scenario': scenario['name'], 'response_time': attempt_time, 'result': result})
        await client.disconnect()
    response_times = [r['response_time'] for r in test_results]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    assert avg_response_time < 0.05, f'Average tampering detection {avg_response_time:.3f}s too slow'
    assert max_response_time < 0.1, f'Max tampering detection {max_response_time:.3f}s too slow'
    security_events = audit_logger.security_events
    recent_events = [e for e in security_events if (datetime.now(timezone.utc) - datetime.fromisoformat(e['timestamp'])).total_seconds() < 60]
    assert len(recent_events) >= len(tampering_scenarios), 'Tampering attempts should be logged'
    logger.info(f'[U+2713] Token tampering detection: {len(test_results)} scenarios, avg {avg_response_time:.3f}s detection')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')