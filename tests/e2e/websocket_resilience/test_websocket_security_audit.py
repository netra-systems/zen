"""
WebSocket Security Audit Tests: Logging and Monitoring

Security audit and logging tests for expired JWT tokens including comprehensive
audit trails, security event logging, and monitoring capabilities.

Business Value: Ensures regulatory compliance and provides security visibility
for enterprise customers requiring detailed audit capabilities.
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
from websockets import ConnectionClosed, InvalidStatusCode

from netra_backend.app.logging_config import central_logger
from tests.e2e.websocket_resilience.websocket_recovery_fixtures import (
    SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient, TokenRefreshService, jwt_generator, audit_logger, token_refresh_service, expired_token, valid_token, near_expiry_token,
    SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient,
    TokenRefreshService, jwt_generator, audit_logger, token_refresh_service,
    expired_token, valid_token, near_expiry_token
)

logger = central_logger.get_logger(__name__)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_security_logging_comprehensive_audit_trail(jwt_generator, audit_logger):
    """
    Test Case 1: Security logging and comprehensive audit trail verification.
    
    Ensures comprehensive security logging for expired token attempts with
    complete audit trail for compliance and security monitoring.
    """
    logger.info("Testing comprehensive security logging for expired token attempts")
    
    # Create multiple expired tokens with different scenarios
    test_scenarios = [
        {"user": "user_001", "expired_minutes": 1, "ip": "192.168.1.10", "agent": "Browser/1.0"},
        {"user": "user_002", "expired_minutes": 30, "ip": "10.0.0.50", "agent": "Mobile/2.0"},
        {"user": "user_001", "expired_minutes": 5, "ip": "192.168.1.10", "agent": "Browser/1.0"},  # Repeat user
        {"user": "user_003", "expired_minutes": 120, "ip": "172.16.0.100", "agent": "API/1.0"},
        {"user": "user_001", "expired_minutes": 2, "ip": "192.168.1.10", "agent": "Browser/1.0"},  # Third attempt
    ]
    
    clients = []
    
    for i, scenario in enumerate(test_scenarios):
        # Create expired token for scenario
        expired_token = jwt_generator.create_expired_token(
            scenario["user"], 
            expired_minutes_ago=scenario["expired_minutes"]
        )
        
        # Create client and attempt connection
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            expired_token,
            jwt_generator,
            audit_logger
        )
        
        # Attempt connection with scenario-specific headers
        headers = {
            "X-Forwarded-For": scenario["ip"],
            "User-Agent": scenario["agent"],
            "X-Request-ID": f"req_{i+1}_{uuid.uuid4().hex[:8]}"
        }
        
        success, result = await client.attempt_connection(headers)
        assert not success, f"Scenario {i+1}: Expired token should be rejected"
        
        clients.append(client)
        
        # Brief delay between attempts to simulate realistic timing
        await asyncio.sleep(0.1)
    
    # Validate comprehensive audit logging
    all_events = audit_logger.security_events
    expired_events = [e for e in all_events if e["event_type"] == "expired_token_attempt"]
    
    assert len(expired_events) == len(test_scenarios), f"Expected {len(test_scenarios)} events, got {len(expired_events)}"
    
    # Validate event completeness
    for i, event in enumerate(expired_events):
        scenario = test_scenarios[i]
        
        # Validate required fields
        required_fields = ["timestamp", "event_type", "severity", "user_id", 
                          "source_ip", "token_fingerprint", "user_agent"]
        for field in required_fields:
            assert field in event, f"Event {i+1}: Missing required field {field}"
        
        # Validate field values
        assert event["severity"] == "HIGH", f"Event {i+1}: Expected HIGH severity"
        assert event["user_id"] == scenario["user"], f"Event {i+1}: User ID mismatch"
        assert event["source_ip"] == scenario["ip"], f"Event {i+1}: Source IP mismatch"
        assert event["user_agent"] == scenario["agent"], f"Event {i+1}: User agent mismatch"
        
        # Validate timestamp format and recency
        event_time = datetime.fromisoformat(event["timestamp"])
        time_diff = (datetime.now(timezone.utc) - event_time).total_seconds()
        assert time_diff < 60, f"Event {i+1}: Timestamp too old ({time_diff}s)"
    
    # Validate suspicious pattern detection
    alert_count = audit_logger.get_alert_count()
    
    # user_001 had 3 attempts, should trigger alert
    user_001_events = audit_logger.get_events_for_user("user_001")
    assert len(user_001_events) == 3, "User_001 should have 3 events"
    
    # Check if alerts were triggered for repeated attempts
    if alert_count > 0:
        alerts = audit_logger.alert_triggers
        user_001_alerts = [a for a in alerts if a["user_id"] == "user_001"]
        assert len(user_001_alerts) >= 1, "Alert should be triggered for repeated attempts"
        
        alert = user_001_alerts[0]
        assert alert["alert_type"] == "repeated_expired_token_attempts", "Correct alert type"
        assert alert["severity"] == "CRITICAL", "Critical severity for repeated attempts"
        assert alert["attempt_count"] >= 3, "Should count multiple attempts"
    
    # Cleanup
    for client in clients:
        if client.is_connected:
            await client.disconnect()
    
    logger.info(f"✓ Comprehensive audit trail: {len(expired_events)} events logged, {alert_count} alerts triggered")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_security_event_correlation_and_pattern_detection(jwt_generator, audit_logger):
    """
    Test Case 2: Security event correlation and pattern detection.
    
    Tests the system's ability to correlate security events and detect
    attack patterns across multiple users and time windows.
    """
    logger.info("Testing security event correlation and pattern detection")
    
    # Create coordinated attack simulation
    attack_patterns = [
        {
            "pattern": "distributed_attack",
            "users": ["target_1", "target_2", "target_3"],
            "ips": ["203.0.113.10", "203.0.113.11", "203.0.113.12"],
            "attempts_per_user": 3
        },
        {
            "pattern": "single_source_multi_target",
            "users": ["victim_a", "victim_b", "victim_c"],
            "ips": ["198.51.100.50"] * 3,  # Same IP for all
            "attempts_per_user": 2
        }
    ]
    
    all_clients = []
    pattern_results = []
    
    for pattern_info in attack_patterns:
        pattern_start = time.time()
        pattern_clients = []
        
        logger.info(f"Simulating {pattern_info['pattern']} attack pattern")
        
        for user_idx, user_id in enumerate(pattern_info["users"]):
            user_ip = pattern_info["ips"][user_idx % len(pattern_info["ips"])]
            
            for attempt in range(pattern_info["attempts_per_user"]):
                # Create expired token
                expired_token = jwt_generator.create_expired_token(
                    user_id, 
                    expired_minutes_ago=5 + attempt
                )
                
                # Create client
                client = SecureWebSocketTestClient(
                    "ws://mock-server/ws",
                    expired_token,
                    jwt_generator,
                    audit_logger
                )
                
                # Attempt connection
                headers = {
                    "X-Forwarded-For": user_ip,
                    "User-Agent": f"AttackBot/{pattern_info['pattern']}/{user_idx}.{attempt}",
                    "X-Attack-Pattern": pattern_info["pattern"]
                }
                
                success, result = await client.attempt_connection(headers)
                assert not success, f"Attack attempt should be blocked"
                
                pattern_clients.append(client)
                
                # Brief delay between attempts
                await asyncio.sleep(0.05)
        
        pattern_time = time.time() - pattern_start
        
        pattern_results.append({
            "pattern": pattern_info["pattern"],
            "total_attempts": len(pattern_info["users"]) * pattern_info["attempts_per_user"],
            "pattern_time": pattern_time,
            "clients": pattern_clients
        })
        
        all_clients.extend(pattern_clients)
        
        # Delay between attack patterns
        await asyncio.sleep(0.2)
    
    # Validate pattern detection
    total_attempts = sum(p["total_attempts"] for p in pattern_results)
    
    # Check security events
    security_events = audit_logger.security_events
    recent_events = [
        e for e in security_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 120
    ]
    
    expired_events = [e for e in recent_events if e["event_type"] == "expired_token_attempt"]
    assert len(expired_events) >= total_attempts, f"All {total_attempts} attempts should be logged"
    
    # Check alert generation
    alert_count = audit_logger.get_alert_count()
    
    # Should have alerts for repeated attempts
    if alert_count > 0:
        alerts = audit_logger.alert_triggers
        
        # Check for pattern-specific alerts
        for pattern_info in attack_patterns:
            for user_id in pattern_info["users"]:
                user_alerts = [a for a in alerts if a["user_id"] == user_id]
                if pattern_info["attempts_per_user"] >= 3:  # Threshold for alerts
                    assert len(user_alerts) >= 1, f"Should have alerts for user {user_id}"
    
    # Validate IP-based correlation for single source attacks
    single_source_pattern = next(p for p in attack_patterns if p["pattern"] == "single_source_multi_target")
    single_source_ip = single_source_pattern["ips"][0]
    
    single_source_events = [
        e for e in expired_events 
        if e.get("source_ip") == single_source_ip
    ]
    
    expected_single_source = len(single_source_pattern["users"]) * single_source_pattern["attempts_per_user"]
    assert len(single_source_events) >= expected_single_source, "Single source events should be correlated"
    
    # Cleanup
    for client in all_clients:
        if client.is_connected:
            await client.disconnect()
    
    logger.info(f"✓ Pattern detection: {len(pattern_results)} patterns, {total_attempts} attempts, {alert_count} alerts")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_audit_trail_data_integrity_and_retention(jwt_generator, audit_logger):
    """
    Test Case 3: Audit trail data integrity and retention.
    
    Tests data integrity of audit trails including timestamp accuracy,
    data completeness, and proper retention of security events.
    """
    logger.info("Testing audit trail data integrity and retention")
    
    # Create test events with specific timing
    test_users = ["integrity_user_1", "integrity_user_2", "integrity_user_3"]
    event_timestamps = []
    
    for i, user_id in enumerate(test_users):
        # Create expired token
        expired_token = jwt_generator.create_expired_token(user_id, expired_minutes_ago=10)
        
        # Record timestamp before connection attempt
        before_attempt = datetime.now(timezone.utc)
        
        # Create client and attempt connection
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            expired_token,
            jwt_generator,
            audit_logger
        )
        
        headers = {
            "X-Forwarded-For": f"192.168.100.{10+i}",
            "User-Agent": f"IntegrityTestClient/{i+1}.0",
            "X-Test-Sequence": str(i+1)
        }
        
        success, result = await client.attempt_connection(headers)
        assert not success, f"Expired token should be rejected for {user_id}"
        
        # Record timestamp after connection attempt
        after_attempt = datetime.now(timezone.utc)
        
        event_timestamps.append({
            "user_id": user_id,
            "before": before_attempt,
            "after": after_attempt,
            "sequence": i+1
        })
        
        await client.disconnect()
        
        # Specific delay between attempts for timing verification
        await asyncio.sleep(0.5)
    
    # Validate audit trail integrity
    security_events = audit_logger.security_events
    recent_events = [
        e for e in security_events
        if e["event_type"] == "expired_token_attempt" and
           any(e["user_id"] == ts["user_id"] for ts in event_timestamps)
    ]
    
    assert len(recent_events) >= len(test_users), "All test events should be recorded"
    
    # Validate timestamp accuracy
    for event in recent_events:
        user_id = event["user_id"]
        event_time = datetime.fromisoformat(event["timestamp"])
        
        # Find corresponding timing info
        timing_info = next(ts for ts in event_timestamps if ts["user_id"] == user_id)
        
        # Validate timestamp is within expected window
        assert timing_info["before"] <= event_time <= timing_info["after"], \
            f"Event timestamp {event_time} outside expected window for {user_id}"
        
        # Validate required fields are present and non-empty
        required_fields = ["timestamp", "event_type", "severity", "user_id", "source_ip"]
        for field in required_fields:
            assert field in event, f"Missing required field {field}"
            assert event[field], f"Empty value for required field {field}"
    
    # Validate event ordering
    sorted_events = sorted(recent_events, key=lambda e: e["timestamp"])
    for i in range(1, len(sorted_events)):
        prev_time = datetime.fromisoformat(sorted_events[i-1]["timestamp"])
        curr_time = datetime.fromisoformat(sorted_events[i]["timestamp"])
        assert prev_time <= curr_time, "Events should be in chronological order"
    
    # Validate data consistency
    for event in recent_events:
        # Check IP format
        ip = event.get("source_ip", "")
        assert ip.count('.') == 3, f"Invalid IP format: {ip}"
        
        # Check user agent format
        user_agent = event.get("user_agent", "")
        assert "IntegrityTestClient" in user_agent, f"Unexpected user agent: {user_agent}"
        
        # Check severity level
        assert event["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"], \
            f"Invalid severity level: {event['severity']}"
        
        # Check token fingerprint format
        if "token_fingerprint" in event:
            fingerprint = event["token_fingerprint"]
            assert len(fingerprint) == 16, f"Invalid fingerprint length: {len(fingerprint)}"
            assert all(c in "0123456789abcdef" for c in fingerprint), \
                f"Invalid fingerprint format: {fingerprint}"
    
    # Test retention policy (simulate time-based cleanup)
    # In a real system, old events would be archived or cleaned up
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    old_events = [
        e for e in security_events
        if datetime.fromisoformat(e["timestamp"]) < one_hour_ago
    ]
    
    # For testing, we just validate that recent events are properly retained
    recent_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    truly_recent_events = [
        e for e in security_events
        if datetime.fromisoformat(e["timestamp"]) > recent_threshold
    ]
    
    assert len(truly_recent_events) >= len(test_users), "Recent events should be retained"
    
    logger.info(f"✓ Audit trail integrity: {len(recent_events)} events validated, proper timestamps and data")


if __name__ == "__main__":
    # Run security audit tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto",
        "-k", "test_"  # Run all test functions
    ])
