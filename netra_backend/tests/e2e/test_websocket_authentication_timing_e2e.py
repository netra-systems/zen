"""
Test WebSocket Authentication Timing Race Conditions - E2E Authentication Infrastructure Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Secure Real-time Authentication & Chat Value Delivery
- Value Impact: Ensures authenticated users can connect to WebSocket without timing failures
- Strategic Impact: Core security infrastructure enabling authenticated AI interactions

CRITICAL: These tests MUST FAIL initially to reproduce exact authentication timing race conditions.
The goal is to expose timing issues between JWT validation, WebSocket authentication, and connection establishment.

Root Cause Analysis:
- Race condition between JWT token validation and WebSocket accept()
- Authentication headers processed after connection establishment attempts
- Token validation racing with connection state management
- Auth bypass mechanisms racing with real authentication flows

This test suite creates FAILING E2E scenarios that reproduce production authentication races.
"""

import asyncio
import json
import jwt
import logging
import pytest
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import websockets
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from fastapi.testclient import TestClient

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, WebSocketID

# Import auth-related components for testing race conditions
from auth_service.auth_core.security.jwt_validator import JWTValidator
from netra_backend.app.auth.websocket_auth import WebSocketAuthenticator

logger = logging.getLogger(__name__)


class AuthenticationTimingController:
    """
    Controller for authentication timing to reproduce race conditions.
    
    This simulates different authentication timing scenarios to expose
    race conditions between JWT validation, WebSocket connection, and auth state.
    """
    
    def __init__(self):
        self.auth_events = []
        self.connection_events = []
        self.race_conditions = []
        self.timing_data = {}
        
    def log_auth_event(self, event_type: str, timestamp: float, details: Dict[str, Any] = None):
        """Log authentication event with timing."""
        event = {
            "type": event_type,
            "timestamp": timestamp,
            "details": details or {}
        }
        self.auth_events.append(event)
        
    def log_connection_event(self, event_type: str, timestamp: float, details: Dict[str, Any] = None):
        """Log connection event with timing."""
        event = {
            "type": event_type,
            "timestamp": timestamp,
            "details": details or {}
        }
        self.connection_events.append(event)
        
    def detect_race_conditions(self):
        """Analyze events to detect race conditions."""
        # Sort all events by timestamp
        all_events = []
        for event in self.auth_events:
            all_events.append(("auth", event))
        for event in self.connection_events:
            all_events.append(("connection", event))
            
        all_events.sort(key=lambda x: x[1]["timestamp"])
        
        # Detect problematic patterns
        for i in range(1, len(all_events)):
            prev_category, prev_event = all_events[i-1]
            curr_category, curr_event = all_events[i]
            
            # Race condition: connection accept before auth validation complete
            if (prev_event["type"] == "auth_validation_started" and 
                curr_event["type"] == "connection_accept" and
                curr_event["timestamp"] - prev_event["timestamp"] < 0.1):  # 100ms window
                
                self.race_conditions.append({
                    "type": "auth_before_accept_race",
                    "prev_event": prev_event,
                    "curr_event": curr_event,
                    "time_gap": curr_event["timestamp"] - prev_event["timestamp"]
                })
                
            # Race condition: websocket send before auth complete
            if (prev_event["type"] == "websocket_connected" and 
                curr_event["type"] == "auth_validation_complete" and
                curr_event["timestamp"] - prev_event["timestamp"] > 0.05):  # Auth too slow
                
                self.race_conditions.append({
                    "type": "websocket_before_auth_race",
                    "prev_event": prev_event,
                    "curr_event": curr_event,
                    "time_gap": curr_event["timestamp"] - prev_event["timestamp"]
                })
        
        return self.race_conditions


class TestWebSocketAuthenticationTimingE2E(BaseE2ETest):
    """
    E2E tests for WebSocket authentication timing race conditions.
    
    CRITICAL: These tests are designed to FAIL initially and expose exact timing issues
    that occur between JWT validation, WebSocket connection, and authentication state.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_auth_timing_environment(self, real_services_fixture):
        """Set up E2E environment for authentication timing race testing."""
        self.real_services = real_services_fixture
        self.env = get_env()
        
        # Use test environment for controlled timing
        self.auth_helper = E2EAuthHelper(environment="test") 
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Initialize timing controller
        self.timing_controller = AuthenticationTimingController()
        
        yield
        
        # Analyze race conditions detected
        races = self.timing_controller.detect_race_conditions()
        if races:
            logger.warning(f"Authentication timing race conditions detected: {len(races)}")
            for i, race in enumerate(races[:3]):  # Log first 3
                logger.info(f"Race {i+1}: {race['type']} - {race['time_gap']:.3f}s gap")
    
    async def _create_timed_jwt_validator(self, validation_delay: float = 0.1) -> JWTValidator:
        """Create JWT validator with controlled timing delay."""
        original_validator = JWTValidator()
        
        async def timed_validate_token(token: str) -> Dict[str, Any]:
            """JWT validation with artificial delay to create race conditions."""
            start_time = time.time()
            self.timing_controller.log_auth_event("auth_validation_started", start_time, {"token_length": len(token)})
            
            # Add delay to simulate slow validation (network latency, database lookup, etc.)
            await asyncio.sleep(validation_delay)
            
            # Perform actual validation
            try:
                result = original_validator.validate_token(token)
                end_time = time.time()
                self.timing_controller.log_auth_event("auth_validation_complete", end_time, {"result": "success"})
                return result
            except Exception as e:
                end_time = time.time()
                self.timing_controller.log_auth_event("auth_validation_complete", end_time, {"result": "failure", "error": str(e)})
                raise
        
        # Replace validate method with timed version
        original_validator.validate_token = timed_validate_token
        return original_validator
    
    async def _create_timed_websocket_connection(self, connection_url: str, headers: Dict[str, str], connection_delay: float = 0.05):
        """Create WebSocket connection with controlled timing."""
        
        async def timed_connect():
            """WebSocket connection with timing logging."""
            start_time = time.time()
            self.timing_controller.log_connection_event("connection_attempt", start_time, {"url": connection_url})
            
            try:
                # Add artificial connection delay
                await asyncio.sleep(connection_delay)
                
                # Attempt actual connection
                websocket = await websockets.connect(
                    connection_url,
                    additional_headers=headers,
                    timeout=10.0
                )
                
                connect_time = time.time()
                self.timing_controller.log_connection_event("connection_accept", connect_time, {"state": "connected"})
                
                return websocket
                
            except Exception as e:
                error_time = time.time()
                self.timing_controller.log_connection_event("connection_failed", error_time, {"error": str(e)})
                raise
                
        return await timed_connect()
    
    @pytest.mark.e2e
    @pytest.mark.websocket_race_conditions
    @pytest.mark.real_services
    async def test_jwt_validation_websocket_accept_race_condition(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Reproduces race between JWT validation and WebSocket accept.
        
        Simulates: JWT validation taking longer than WebSocket connection establishment
        Expected Result: TEST SHOULD FAIL with authentication timing race
        """
        # CRITICAL: This test uses real services to reproduce actual race conditions
        
        # Create JWT token
        token = self.auth_helper.create_test_jwt_token(
            user_id="race-test-user-001",
            email="race.test@example.com",
            exp_minutes=5
        )
        
        # Get WebSocket URL and headers
        websocket_url = f"ws://localhost:{self.real_services['backend_port']}/ws"
        headers = self.websocket_auth_helper.get_websocket_headers(token)
        
        start_time = time.time()
        
        # CRITICAL: Set up race condition - slow JWT validation vs fast WebSocket connection
        with patch('netra_backend.app.auth.websocket_auth.JWTValidator') as mock_validator_class:
            # Create timed validator that takes 150ms (slow)
            timed_validator = await self._create_timed_jwt_validator(validation_delay=0.15)
            mock_validator_class.return_value = timed_validator
            
            # Start WebSocket connection (which will trigger auth validation)
            connection_start = time.time()
            
            try:
                # CRITICAL: Connection attempt may succeed before validation completes
                websocket = await self._create_timed_websocket_connection(
                    websocket_url, 
                    headers, 
                    connection_delay=0.05  # Fast connection
                )
                
                connection_end = time.time()
                connection_duration = connection_end - connection_start
                
                # Try to send a message immediately after connection
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                message_start = time.time()
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message_end = time.time()
                
                # Close connection
                await websocket.close()
                
                # Log successful completion
                self.timing_controller.log_connection_event("websocket_connected", connection_end)
                self.timing_controller.log_connection_event("message_exchange_complete", message_end)
                
            except Exception as e:
                # Expected to fail due to race condition
                error_time = time.time()
                self.timing_controller.log_connection_event("race_condition_error", error_time, {"error": str(e)})
                
                # This is the race condition we're trying to reproduce
                if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                    self.timing_controller.race_conditions.append({
                        "type": "jwt_websocket_race_reproduced",
                        "error": str(e),
                        "timing": error_time - start_time
                    })
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Detect and analyze race conditions
        races = self.timing_controller.detect_race_conditions()
        
        # CRITICAL: This test SHOULD FAIL initially
        # It reproduces the race condition between JWT validation and WebSocket acceptance
        assert len(races) == 0, f"JWT validation WebSocket race condition reproduced: {len(races)} races detected in {total_duration:.3f}s"
    
    @pytest.mark.e2e
    @pytest.mark.websocket_race_conditions
    @pytest.mark.real_services
    async def test_concurrent_authentication_websocket_connections_race(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Tests concurrent authentication for multiple WebSocket connections.
        
        Simulates: Multiple users connecting simultaneously with authentication timing issues
        Expected Result: TEST SHOULD FAIL with concurrent authentication races
        """
        # Create multiple test users with different tokens
        user_tokens = []
        for i in range(5):
            token = self.auth_helper.create_test_jwt_token(
                user_id=f"concurrent-user-{i:03d}",
                email=f"concurrent.user.{i}@example.com",
                exp_minutes=5
            )
            user_tokens.append((i, token))
        
        websocket_url = f"ws://localhost:{self.real_services['backend_port']}/ws"
        
        # Track connection results
        connection_results = []
        auth_failures = []
        successful_connections = []
        
        async def attempt_user_connection(user_id: int, token: str):
            """Attempt WebSocket connection for a specific user."""
            try:
                start_time = time.time()
                self.timing_controller.log_auth_event(f"user_{user_id}_auth_start", start_time)
                
                headers = self.websocket_auth_helper.get_websocket_headers(token)
                
                # CRITICAL: All users connect at the same time (creates auth server load)
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=headers, 
                    timeout=8.0  # Shorter timeout to expose race conditions
                )
                
                connect_time = time.time()
                connection_duration = connect_time - start_time
                
                # Send a test message to verify full connection
                test_message = {
                    "type": "user_connected",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                
                await websocket.close()
                
                # Log successful connection
                self.timing_controller.log_auth_event(f"user_{user_id}_auth_success", connect_time)
                successful_connections.append({
                    "user_id": user_id,
                    "duration": connection_duration,
                    "response": response
                })
                
            except Exception as e:
                error_time = time.time()
                self.timing_controller.log_auth_event(f"user_{user_id}_auth_failure", error_time, {"error": str(e)})
                
                auth_failures.append({
                    "user_id": user_id,
                    "error": str(e),
                    "error_time": error_time
                })
        
        start_time = time.time()
        
        # CRITICAL: Start all connections simultaneously to create auth load
        connection_tasks = [
            asyncio.create_task(attempt_user_connection(user_id, token))
            for user_id, token in user_tokens
        ]
        
        # Wait for all connections to complete or fail
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze concurrent authentication results
        total_users = len(user_tokens)
        successful_count = len(successful_connections)
        failed_count = len(auth_failures)
        
        # Check for authentication race patterns
        auth_timeouts = [failure for failure in auth_failures if "timeout" in failure["error"].lower()]
        auth_conflicts = [failure for failure in auth_failures if "conflict" in failure["error"].lower() or "concurrent" in failure["error"].lower()]
        
        # Detect race conditions
        races = self.timing_controller.detect_race_conditions()
        
        # CRITICAL: This test SHOULD FAIL initially
        # It reproduces concurrent authentication race conditions
        assert failed_count == 0, f"Concurrent authentication race: {failed_count}/{total_users} users failed to authenticate"
        assert len(auth_timeouts) == 0, f"Authentication timeout race: {len(auth_timeouts)} users timed out"
        assert len(races) == 0, f"Authentication timing races detected: {len(races)} races in {total_duration:.3f}s"
    
    @pytest.mark.e2e
    @pytest.mark.websocket_race_conditions
    @pytest.mark.real_services
    async def test_token_expiration_during_connection_race_condition(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Tests race condition when JWT expires during WebSocket connection.
        
        Simulates: JWT token expiring while WebSocket connection/authentication is in progress
        Expected Result: TEST SHOULD FAIL with token expiration timing race
        """
        # Create short-lived JWT token (expires in 2 seconds)
        token = self.auth_helper.create_test_jwt_token(
            user_id="expiring-token-user",
            email="expiring.token@example.com",
            exp_minutes=0.033  # ~2 seconds
        )
        
        websocket_url = f"ws://localhost:{self.real_services['backend_port']}/ws"
        headers = self.websocket_auth_helper.get_websocket_headers(token)
        
        start_time = time.time()
        
        # CRITICAL: Add delay before connection to race token expiration
        await asyncio.sleep(1.5)  # Wait 1.5 seconds (token expires in 2 seconds)
        
        try:
            # Attempt connection with nearly-expired token
            connection_start = time.time()
            self.timing_controller.log_auth_event("expiring_token_connection_attempt", connection_start)
            
            websocket = await websockets.connect(
                websocket_url,
                additional_headers=headers,
                timeout=5.0
            )
            
            connection_success_time = time.time()
            self.timing_controller.log_connection_event("websocket_connected", connection_success_time)
            
            # CRITICAL: Try to send message after connection (token may have expired by now)
            message_start = time.time()
            await asyncio.sleep(1.0)  # Additional delay to ensure token expiration
            
            test_message = {
                "type": "ping_with_expired_token",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
            
            message_success_time = time.time()
            self.timing_controller.log_connection_event("message_with_expired_token_success", message_success_time)
            
            await websocket.close()
            
        except Exception as e:
            error_time = time.time()
            error_message = str(e)
            
            # Log token expiration race condition
            self.timing_controller.log_auth_event("token_expiration_race", error_time, {
                "error": error_message,
                "time_since_start": error_time - start_time
            })
            
            # Check if this is a token expiration race condition
            if "expired" in error_message.lower() or "unauthorized" in error_message.lower():
                self.timing_controller.race_conditions.append({
                    "type": "token_expiration_race",
                    "error": error_message,
                    "timing": error_time - start_time,
                    "description": "Token expired during WebSocket operation"
                })
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Detect all race conditions
        races = self.timing_controller.detect_race_conditions()
        
        # CRITICAL: This test SHOULD FAIL initially  
        # It reproduces race conditions between token expiration and WebSocket operations
        assert len(races) == 0, f"Token expiration race condition reproduced: {len(races)} races in {total_duration:.3f}s"
    
    @pytest.mark.e2e
    @pytest.mark.websocket_race_conditions
    @pytest.mark.real_services
    async def test_auth_bypass_vs_real_auth_race_condition(self, real_services_fixture):
        """
        CRITICAL E2E TEST: Tests race between E2E auth bypass and real authentication.
        
        Simulates: E2E test auth bypass racing with real JWT authentication flows
        Expected Result: TEST SHOULD FAIL with auth bypass/real auth timing conflicts
        """
        # CRITICAL: This test simulates the exact production issue with staging E2E tests
        
        # Create both real token and E2E bypass scenario
        real_token = self.auth_helper.create_test_jwt_token(
            user_id="real-auth-user",
            email="real.auth@example.com"
        )
        
        # Get E2E staging token (with bypass)
        staging_token = await self.websocket_auth_helper.get_staging_token_async(
            email="e2e.bypass@example.com"
        )
        
        websocket_url = f"ws://localhost:{self.real_services['backend_port']}/ws"
        
        # Track auth method results
        real_auth_results = []
        bypass_auth_results = []
        race_conflicts = []
        
        async def attempt_real_auth():
            """Attempt connection with real JWT authentication."""
            try:
                start_time = time.time()
                headers = self.auth_helper.get_websocket_headers(real_token)
                
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=headers,
                    timeout=5.0
                )
                
                # Send real auth message
                test_message = {
                    "type": "real_auth_test",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                
                end_time = time.time()
                real_auth_results.append({
                    "success": True,
                    "duration": end_time - start_time,
                    "response": response
                })
                
                await websocket.close()
                
            except Exception as e:
                end_time = time.time()
                real_auth_results.append({
                    "success": False,
                    "error": str(e),
                    "duration": end_time - start_time
                })
        
        async def attempt_bypass_auth():
            """Attempt connection with E2E bypass authentication."""
            try:
                start_time = time.time()
                headers = self.websocket_auth_helper.get_websocket_headers(staging_token)
                
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=headers,
                    timeout=5.0
                )
                
                # Send bypass auth message  
                test_message = {
                    "type": "bypass_auth_test",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                
                end_time = time.time()
                bypass_auth_results.append({
                    "success": True,
                    "duration": end_time - start_time,
                    "response": response
                })
                
                await websocket.close()
                
            except Exception as e:
                end_time = time.time()
                bypass_auth_results.append({
                    "success": False,
                    "error": str(e),
                    "duration": end_time - start_time
                })
        
        start_time = time.time()
        
        # CRITICAL: Run both auth methods concurrently to create race
        auth_tasks = [
            asyncio.create_task(attempt_real_auth()),
            asyncio.create_task(attempt_bypass_auth())
        ]
        
        await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze auth race results
        real_success = any(result.get("success", False) for result in real_auth_results)
        bypass_success = any(result.get("success", False) for result in bypass_auth_results)
        
        real_failures = [r for r in real_auth_results if not r.get("success", True)]
        bypass_failures = [r for r in bypass_auth_results if not r.get("success", True)]
        
        # Check for auth conflicts
        if real_failures and bypass_failures:
            race_conflicts.append({
                "type": "both_auth_methods_failed",
                "real_errors": [f["error"] for f in real_failures],
                "bypass_errors": [f["error"] for f in bypass_failures]
            })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It reproduces race conditions between real auth and bypass auth
        assert len(race_conflicts) == 0, f"Auth bypass vs real auth race condition: {len(race_conflicts)} conflicts detected"
        assert real_success or bypass_success, f"Auth race caused both methods to fail - Real: {real_success}, Bypass: {bypass_success}"
    
    def test_authentication_timing_race_analysis(self):
        """
        Analysis test that documents authentication timing race condition patterns.
        
        This test reviews all timing data collected from authentication race tests
        and provides analysis for fixing the actual authentication race conditions.
        """
        if not hasattr(self, 'timing_controller'):
            pytest.skip("No timing controller - authentication timing tests may not have run")
        
        # Get final race condition analysis
        final_races = self.timing_controller.detect_race_conditions()
        
        # Analyze authentication event patterns
        auth_events = self.timing_controller.auth_events
        connection_events = self.timing_controller.connection_events
        
        # Calculate timing statistics
        auth_durations = []
        connection_durations = []
        
        # Group events by type
        auth_starts = [e for e in auth_events if "started" in e["type"]]
        auth_completes = [e for e in auth_events if "complete" in e["type"]]
        
        for start, complete in zip(auth_starts, auth_completes):
            duration = complete["timestamp"] - start["timestamp"]
            auth_durations.append(duration)
        
        # Connection timing analysis
        connection_attempts = [e for e in connection_events if "attempt" in e["type"]]
        connection_accepts = [e for e in connection_events if "accept" in e["type"] or "connected" in e["type"]]
        
        for attempt, accept in zip(connection_attempts, connection_accepts):
            duration = accept["timestamp"] - attempt["timestamp"] 
            connection_durations.append(duration)
        
        # Generate comprehensive analysis
        avg_auth_duration = sum(auth_durations) / len(auth_durations) if auth_durations else 0
        avg_connection_duration = sum(connection_durations) / len(connection_durations) if connection_durations else 0
        
        race_types = {}
        for race in final_races:
            race_type = race.get('type', 'unknown')
            race_types[race_type] = race_types.get(race_type, 0) + 1
        
        # Log comprehensive analysis
        logger.critical("=" * 80)
        logger.critical("WEBSOCKET AUTHENTICATION TIMING RACE CONDITION ANALYSIS REPORT")
        logger.critical("=" * 80)
        logger.critical(f"Auth Events Recorded: {len(auth_events)}")
        logger.critical(f"Connection Events Recorded: {len(connection_events)}")
        logger.critical(f"Average Auth Duration: {avg_auth_duration:.3f}s")
        logger.critical(f"Average Connection Duration: {avg_connection_duration:.3f}s")
        logger.critical(f"Race Conditions Detected: {len(final_races)}")
        logger.critical(f"Race Types: {race_types}")
        logger.critical("=" * 80)
        
        # CRITICAL: This documents that authentication race conditions were successfully reproduced
        assert len(final_races) == 0, f"Authentication timing race conditions reproduced: {len(final_races)} total races detected"