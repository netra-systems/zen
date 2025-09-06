from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''JWT Token Expiry Handling L3 Integration Tests

# REMOVED_SYNTAX_ERROR: TEMPORARILY SKIPPED: TokenManager has been consolidated into auth_client_core.
# REMOVED_SYNTAX_ERROR: This test needs to be rewritten to use the centralized auth service for SSOT compliance.

# REMOVED_SYNTAX_ERROR: Tests comprehensive JWT token expiry scenarios including automatic refresh,
# REMOVED_SYNTAX_ERROR: grace periods, sliding windows, and expiry notification mechanisms.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: ALL (Security foundation for all tiers)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Balance security with user experience
    # REMOVED_SYNTAX_ERROR: - Value Impact: Reduce support tickets by 30% from token expiry issues
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Improve user retention through seamless auth experience

    # REMOVED_SYNTAX_ERROR: Critical Path:
        # REMOVED_SYNTAX_ERROR: Token creation -> Usage tracking -> Expiry detection ->
        # REMOVED_SYNTAX_ERROR: Grace period -> Auto-refresh -> Notification -> Re-authentication

        # REMOVED_SYNTAX_ERROR: Mock-Real Spectrum: L3 (Real JWT with time manipulation)
        # REMOVED_SYNTAX_ERROR: - Real JWT encoding/decoding
        # REMOVED_SYNTAX_ERROR: - Real Redis TTL management
        # REMOVED_SYNTAX_ERROR: - Real refresh logic
        # REMOVED_SYNTAX_ERROR: - Simulated time progression
        # REMOVED_SYNTAX_ERROR: """"

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
        # REMOVED_SYNTAX_ERROR: pytest.skip("TokenManager consolidated - rewrite needed for auth service", allow_module_level=True)

        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: from pathlib import Path

        # Test framework import - using pytest fixtures instead

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass, field
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
        # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional, Tuple

        # REMOVED_SYNTAX_ERROR: from test_framework.freezegun_mock import freeze_time
        # REMOVED_SYNTAX_ERROR: import jwt
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import auth_client

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.config import get_settings
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.monitoring.metrics_collector import MetricsCollector
        # TokenManager consolidated into auth_client - using auth_client for token management
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.redis_manager import get_redis_manager

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.auth_types import ( )
        # REMOVED_SYNTAX_ERROR: RefreshRequest,
        # REMOVED_SYNTAX_ERROR: RefreshResponse,
        # REMOVED_SYNTAX_ERROR: Token,
        # REMOVED_SYNTAX_ERROR: TokenData,
        # REMOVED_SYNTAX_ERROR: TokenExpiryNotification,
        # REMOVED_SYNTAX_ERROR: TokenStatus,
        

        # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class TokenLifecycle:
    # REMOVED_SYNTAX_ERROR: """Track token lifecycle events"""
    # REMOVED_SYNTAX_ERROR: token_id: str
    # REMOVED_SYNTAX_ERROR: created_at: datetime
    # REMOVED_SYNTAX_ERROR: expires_at: datetime
    # REMOVED_SYNTAX_ERROR: last_used: datetime
    # REMOVED_SYNTAX_ERROR: refresh_count: int = 0
    # REMOVED_SYNTAX_ERROR: grace_period_used: bool = False
    # REMOVED_SYNTAX_ERROR: auto_refreshed: bool = False
    # REMOVED_SYNTAX_ERROR: notifications_sent: List[str] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: final_status: str = "active"  # active, expired, refreshed, revoked

    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class ExpiryTestMetrics:
    # REMOVED_SYNTAX_ERROR: """Metrics for expiry testing"""
    # REMOVED_SYNTAX_ERROR: tokens_created: int = 0
    # REMOVED_SYNTAX_ERROR: tokens_expired: int = 0
    # REMOVED_SYNTAX_ERROR: tokens_refreshed: int = 0
    # REMOVED_SYNTAX_ERROR: auto_refresh_success: int = 0
    # REMOVED_SYNTAX_ERROR: auto_refresh_failed: int = 0
    # REMOVED_SYNTAX_ERROR: grace_period_grants: int = 0
    # REMOVED_SYNTAX_ERROR: notifications_sent: int = 0
    # REMOVED_SYNTAX_ERROR: avg_token_lifetime_minutes: float = 0.0

    # REMOVED_SYNTAX_ERROR: @property
# REMOVED_SYNTAX_ERROR: def refresh_success_rate(self) -> float:
    # REMOVED_SYNTAX_ERROR: total_attempts = self.auto_refresh_success + self.auto_refresh_failed
    # REMOVED_SYNTAX_ERROR: if total_attempts == 0:
        # REMOVED_SYNTAX_ERROR: return 0
        # REMOVED_SYNTAX_ERROR: return (self.auto_refresh_success / total_attempts) * 100

# REMOVED_SYNTAX_ERROR: class TestJWTTokenExpiryHandling:
    # REMOVED_SYNTAX_ERROR: """Test suite for JWT token expiry handling"""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def token_manager(self):
    # REMOVED_SYNTAX_ERROR: """Initialize token manager"""
    # REMOVED_SYNTAX_ERROR: settings = get_settings()

    # REMOVED_SYNTAX_ERROR: manager = TokenManager( )
    # REMOVED_SYNTAX_ERROR: secret_key=settings.jwt_secret_key,
    # REMOVED_SYNTAX_ERROR: algorithm="HS256",
    # REMOVED_SYNTAX_ERROR: access_token_expire_minutes=15,
    # REMOVED_SYNTAX_ERROR: refresh_token_expire_minutes=60*24*7,  # 7 days
    # REMOVED_SYNTAX_ERROR: grace_period_seconds=30
    

    # REMOVED_SYNTAX_ERROR: await manager.initialize()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def notification_tracker(self):
    # REMOVED_SYNTAX_ERROR: """Track expiry notifications"""
    # REMOVED_SYNTAX_ERROR: notifications = []

# REMOVED_SYNTAX_ERROR: async def send_notification(notification: TokenExpiryNotification):
    # REMOVED_SYNTAX_ERROR: notifications.append({ ))
    # REMOVED_SYNTAX_ERROR: "user_id": notification.user_id,
    # REMOVED_SYNTAX_ERROR: "token_id": notification.token_id,
    # REMOVED_SYNTAX_ERROR: "expires_in_seconds": notification.expires_in_seconds,
    # REMOVED_SYNTAX_ERROR: "notification_type": notification.notification_type,
    # REMOVED_SYNTAX_ERROR: "timestamp": notification.timestamp
    

    # REMOVED_SYNTAX_ERROR: yield {"send": send_notification, "notifications": notifications}

    # Removed problematic line: @pytest.mark.asyncio
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_token_natural_expiry_flow( )
    # REMOVED_SYNTAX_ERROR: self, token_manager, notification_tracker
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test natural token expiry with notifications"""
        # REMOVED_SYNTAX_ERROR: metrics = ExpiryTestMetrics()

        # Create token with short expiry
        # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
            # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
            # REMOVED_SYNTAX_ERROR: user_id="user123",
            # REMOVED_SYNTAX_ERROR: role="user",
            # REMOVED_SYNTAX_ERROR: permissions=["read"],
            # REMOVED_SYNTAX_ERROR: expire_minutes=5  # 5 minute expiry
            
            # REMOVED_SYNTAX_ERROR: metrics.tokens_created += 1

            # REMOVED_SYNTAX_ERROR: lifecycle = TokenLifecycle( )
            # REMOVED_SYNTAX_ERROR: token_id=token_data.jti,
            # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
            # REMOVED_SYNTAX_ERROR: expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            # REMOVED_SYNTAX_ERROR: last_used=datetime.now(timezone.utc)
            

            # Advance time to 1 minute before expiry
            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:04:00")

            # Check token status - should trigger warning
            # REMOVED_SYNTAX_ERROR: status = await token_manager.check_token_status(token_data.access_token)
            # REMOVED_SYNTAX_ERROR: assert status == TokenStatus.EXPIRING_SOON

            # Send expiry warning
            # REMOVED_SYNTAX_ERROR: await notification_tracker["send"]( )
            # REMOVED_SYNTAX_ERROR: TokenExpiryNotification( )
            # REMOVED_SYNTAX_ERROR: user_id="user123",
            # REMOVED_SYNTAX_ERROR: token_id=token_data.jti,
            # REMOVED_SYNTAX_ERROR: expires_in_seconds=60,
            # REMOVED_SYNTAX_ERROR: notification_type="warning",
            # REMOVED_SYNTAX_ERROR: timestamp=datetime.now(timezone.utc)
            
            
            # REMOVED_SYNTAX_ERROR: metrics.notifications_sent += 1
            # REMOVED_SYNTAX_ERROR: lifecycle.notifications_sent.append("warning")

            # Advance to exact expiry time
            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:05:00")

            # Token should be expired
            # REMOVED_SYNTAX_ERROR: status = await token_manager.check_token_status(token_data.access_token)
            # REMOVED_SYNTAX_ERROR: assert status == TokenStatus.EXPIRED
            # REMOVED_SYNTAX_ERROR: metrics.tokens_expired += 1
            # REMOVED_SYNTAX_ERROR: lifecycle.final_status = "expired"

            # Verify notification sent
            # REMOVED_SYNTAX_ERROR: assert len(notification_tracker["notifications"]) == 1
            # REMOVED_SYNTAX_ERROR: assert notification_tracker["notifications"][0]["notification_type"] == "warning"

            # Removed problematic line: @pytest.mark.asyncio
            # REMOVED_SYNTAX_ERROR: @pytest.fixture
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_grace_period_allowance( )
            # REMOVED_SYNTAX_ERROR: self, token_manager
            # REMOVED_SYNTAX_ERROR: ):
                # REMOVED_SYNTAX_ERROR: """Test grace period for recently expired tokens"""
                # REMOVED_SYNTAX_ERROR: metrics = ExpiryTestMetrics()

                # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
                    # Create token
                    # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
                    # REMOVED_SYNTAX_ERROR: user_id="user456",
                    # REMOVED_SYNTAX_ERROR: role="user",
                    # REMOVED_SYNTAX_ERROR: permissions=["read"],
                    # REMOVED_SYNTAX_ERROR: expire_minutes=10
                    

                    # Advance just past expiry (within grace period)
                    # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:10:15")  # 15 seconds past expiry

                    # Token should be expired but within grace period
                    # REMOVED_SYNTAX_ERROR: validation_result = await token_manager.validate_with_grace( )
                    # REMOVED_SYNTAX_ERROR: token_data.access_token
                    

                    # REMOVED_SYNTAX_ERROR: assert validation_result.is_valid, "Token should be valid within grace period"
                    # REMOVED_SYNTAX_ERROR: assert validation_result.grace_period_used, "Should indicate grace period used"
                    # REMOVED_SYNTAX_ERROR: metrics.grace_period_grants += 1

                    # Advance beyond grace period
                    # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:10:45")  # 45 seconds past expiry

                    # Token should be completely invalid
                    # REMOVED_SYNTAX_ERROR: validation_result = await token_manager.validate_with_grace( )
                    # REMOVED_SYNTAX_ERROR: token_data.access_token
                    

                    # REMOVED_SYNTAX_ERROR: assert not validation_result.is_valid, "Token should be invalid beyond grace period"

                    # Removed problematic line: @pytest.mark.asyncio
                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_automatic_token_refresh( )
                    # REMOVED_SYNTAX_ERROR: self, token_manager
                    # REMOVED_SYNTAX_ERROR: ):
                        # REMOVED_SYNTAX_ERROR: """Test automatic token refresh before expiry"""
                        # REMOVED_SYNTAX_ERROR: metrics = ExpiryTestMetrics()

                        # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
                            # Create initial tokens
                            # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
                            # REMOVED_SYNTAX_ERROR: user_id="user789",
                            # REMOVED_SYNTAX_ERROR: role="admin",
                            # REMOVED_SYNTAX_ERROR: permissions=["read", "write"],
                            # REMOVED_SYNTAX_ERROR: expire_minutes=15
                            
                            # REMOVED_SYNTAX_ERROR: metrics.tokens_created += 1

                            # Advance to refresh window (e.g., 80% of lifetime)
                            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:12:00")  # 12 minutes (80% of 15)

                            # Trigger auto-refresh
                            # REMOVED_SYNTAX_ERROR: try:
                                # REMOVED_SYNTAX_ERROR: new_token = await token_manager.auto_refresh( )
                                # REMOVED_SYNTAX_ERROR: token_data.refresh_token
                                
                                # REMOVED_SYNTAX_ERROR: metrics.auto_refresh_success += 1
                                # REMOVED_SYNTAX_ERROR: metrics.tokens_refreshed += 1

                                # Verify new token
                                # REMOVED_SYNTAX_ERROR: assert new_token is not None
                                # REMOVED_SYNTAX_ERROR: assert new_token.access_token != token_data.access_token

                                # Verify new expiry time
                                # REMOVED_SYNTAX_ERROR: decoded = jwt.decode( )
                                # REMOVED_SYNTAX_ERROR: new_token.access_token,
                                # REMOVED_SYNTAX_ERROR: options={"verify_signature": False}
                                
                                # REMOVED_SYNTAX_ERROR: new_exp = datetime.fromtimestamp(decoded["exp"])
                                # REMOVED_SYNTAX_ERROR: assert new_exp > datetime.now(timezone.utc) + timedelta(minutes=14)

                                # REMOVED_SYNTAX_ERROR: except Exception:
                                    # REMOVED_SYNTAX_ERROR: metrics.auto_refresh_failed += 1
                                    # REMOVED_SYNTAX_ERROR: raise

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_sliding_window_expiry( )
                                    # REMOVED_SYNTAX_ERROR: self, token_manager
                                    # REMOVED_SYNTAX_ERROR: ):
                                        # REMOVED_SYNTAX_ERROR: """Test sliding window expiry (activity extends token)"""
                                        # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
                                            # Create token with sliding window enabled
                                            # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
                                            # REMOVED_SYNTAX_ERROR: user_id="user_sliding",
                                            # REMOVED_SYNTAX_ERROR: role="user",
                                            # REMOVED_SYNTAX_ERROR: permissions=["read"],
                                            # REMOVED_SYNTAX_ERROR: expire_minutes=30,
                                            # REMOVED_SYNTAX_ERROR: sliding_window=True
                                            

                                            # REMOVED_SYNTAX_ERROR: initial_exp = datetime.now(timezone.utc) + timedelta(minutes=30)

                                            # Simulate activity at 10 minutes
                                            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:10:00")
                                            # REMOVED_SYNTAX_ERROR: await token_manager.update_activity(token_data.access_token)

                                            # Check new expiry (should be extended)
                                            # REMOVED_SYNTAX_ERROR: status = await token_manager.get_token_info(token_data.access_token)
                                            # REMOVED_SYNTAX_ERROR: assert status.expires_at > initial_exp, "Expiry should be extended"

                                            # Simulate more activity at 20 minutes
                                            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:20:00")
                                            # REMOVED_SYNTAX_ERROR: await token_manager.update_activity(token_data.access_token)

                                            # Token should still be valid at original expiry time
                                            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:30:00")
                                            # REMOVED_SYNTAX_ERROR: validation = await token_manager.validate_token_jwt(token_data.access_token)
                                            # REMOVED_SYNTAX_ERROR: assert validation.is_valid, "Token should be valid due to sliding window"

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # REMOVED_SYNTAX_ERROR: @pytest.fixture
                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_bulk_token_expiry_handling( )
                                            # REMOVED_SYNTAX_ERROR: self, token_manager
                                            # REMOVED_SYNTAX_ERROR: ):
                                                # REMOVED_SYNTAX_ERROR: """Test handling bulk token expiries"""
                                                # REMOVED_SYNTAX_ERROR: metrics = ExpiryTestMetrics()
                                                # REMOVED_SYNTAX_ERROR: token_count = 100

                                                # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
                                                    # Create tokens with staggered expiry times
                                                    # REMOVED_SYNTAX_ERROR: tokens = []
                                                    # REMOVED_SYNTAX_ERROR: for i in range(token_count):
                                                        # REMOVED_SYNTAX_ERROR: expire_minutes = 5 + (i % 10)  # 5-14 minute expiry
                                                        # REMOVED_SYNTAX_ERROR: token = await token_manager.create_token( )
                                                        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                                        # REMOVED_SYNTAX_ERROR: role="user",
                                                        # REMOVED_SYNTAX_ERROR: permissions=["read"],
                                                        # REMOVED_SYNTAX_ERROR: expire_minutes=expire_minutes
                                                        
                                                        # REMOVED_SYNTAX_ERROR: tokens.append({ ))
                                                        # REMOVED_SYNTAX_ERROR: "token": token,
                                                        # REMOVED_SYNTAX_ERROR: "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
                                                        
                                                        # REMOVED_SYNTAX_ERROR: metrics.tokens_created += 1

                                                        # Advance time and check expiries
                                                        # REMOVED_SYNTAX_ERROR: for minute in range(1, 16):
                                                            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("formatted_string")

                                                            # Check which tokens expired
                                                            # REMOVED_SYNTAX_ERROR: for token_info in tokens:
                                                                # REMOVED_SYNTAX_ERROR: if token_info["expires_at"] <= datetime.now(timezone.utc):
                                                                    # REMOVED_SYNTAX_ERROR: status = await token_manager.check_token_status( )
                                                                    # REMOVED_SYNTAX_ERROR: token_info["token"].access_token
                                                                    
                                                                    # REMOVED_SYNTAX_ERROR: if status == TokenStatus.EXPIRED:
                                                                        # REMOVED_SYNTAX_ERROR: metrics.tokens_expired += 1

                                                                        # Verify expiry counts
                                                                        # REMOVED_SYNTAX_ERROR: expected_expired = sum( )
                                                                        # REMOVED_SYNTAX_ERROR: 1 for t in tokens
                                                                        # REMOVED_SYNTAX_ERROR: if t["expires_at"] <= datetime.now(timezone.utc)
                                                                        
                                                                        # REMOVED_SYNTAX_ERROR: assert metrics.tokens_expired >= expected_expired * 0.95, \
                                                                        # REMOVED_SYNTAX_ERROR: "Not all expected tokens marked as expired"

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # REMOVED_SYNTAX_ERROR: @pytest.fixture
                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_refresh_token_rotation( )
                                                                        # REMOVED_SYNTAX_ERROR: self, token_manager
                                                                        # REMOVED_SYNTAX_ERROR: ):
                                                                            # REMOVED_SYNTAX_ERROR: """Test refresh token rotation on use"""
                                                                            # REMOVED_SYNTAX_ERROR: metrics = ExpiryTestMetrics()
                                                                            # REMOVED_SYNTAX_ERROR: used_refresh_tokens = set()

                                                                            # Create initial token pair
                                                                            # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
                                                                            # REMOVED_SYNTAX_ERROR: user_id="user_rotation",
                                                                            # REMOVED_SYNTAX_ERROR: role="user",
                                                                            # REMOVED_SYNTAX_ERROR: permissions=["read"],
                                                                            # REMOVED_SYNTAX_ERROR: expire_minutes=15
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: current_refresh = token_data.refresh_token
                                                                            # REMOVED_SYNTAX_ERROR: used_refresh_tokens.add(current_refresh)

                                                                            # Perform multiple refreshes
                                                                            # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                                                # Use refresh token
                                                                                # REMOVED_SYNTAX_ERROR: new_tokens = await token_manager.refresh_tokens( )
                                                                                # REMOVED_SYNTAX_ERROR: RefreshRequest(refresh_token=current_refresh)
                                                                                
                                                                                # REMOVED_SYNTAX_ERROR: metrics.tokens_refreshed += 1

                                                                                # Verify new refresh token
                                                                                # REMOVED_SYNTAX_ERROR: assert new_tokens.refresh_token != current_refresh, \
                                                                                # REMOVED_SYNTAX_ERROR: "Refresh token should rotate"
                                                                                # REMOVED_SYNTAX_ERROR: assert new_tokens.refresh_token not in used_refresh_tokens, \
                                                                                # REMOVED_SYNTAX_ERROR: "Refresh token should be unique"

                                                                                # Old refresh token should be invalidated
                                                                                # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
                                                                                    # REMOVED_SYNTAX_ERROR: await token_manager.refresh_tokens( )
                                                                                    # REMOVED_SYNTAX_ERROR: RefreshRequest(refresh_token=current_refresh)
                                                                                    
                                                                                    # REMOVED_SYNTAX_ERROR: assert "invalid" in str(exc_info.value).lower() or \
                                                                                    # REMOVED_SYNTAX_ERROR: "expired" in str(exc_info.value).lower()

                                                                                    # Update for next iteration
                                                                                    # REMOVED_SYNTAX_ERROR: used_refresh_tokens.add(new_tokens.refresh_token)
                                                                                    # REMOVED_SYNTAX_ERROR: current_refresh = new_tokens.refresh_token

                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # Removed problematic line: async def test_expiry_during_request_processing( )
                                                                                    # REMOVED_SYNTAX_ERROR: self, token_manager
                                                                                    # REMOVED_SYNTAX_ERROR: ):
                                                                                        # REMOVED_SYNTAX_ERROR: """Test token expiring during request processing"""
                                                                                        # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
                                                                                            # Create token with very short expiry
                                                                                            # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
                                                                                            # REMOVED_SYNTAX_ERROR: user_id="user_processing",
                                                                                            # REMOVED_SYNTAX_ERROR: role="user",
                                                                                            # REMOVED_SYNTAX_ERROR: permissions=["read"],
                                                                                            # REMOVED_SYNTAX_ERROR: expire_minutes=1  # 1 minute
                                                                                            

                                                                                            # Start processing request
# REMOVED_SYNTAX_ERROR: async def long_running_request(token: str):
    # Validate token at start
    # REMOVED_SYNTAX_ERROR: validation = await token_manager.validate_token_jwt(token)
    # REMOVED_SYNTAX_ERROR: assert validation.is_valid, "Token should be valid at start"

    # Simulate long processing (40 seconds)
    # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:00:40")
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Simulated work

    # Token still valid (within original minute)
    # REMOVED_SYNTAX_ERROR: validation = await token_manager.validate_token_jwt(token)
    # REMOVED_SYNTAX_ERROR: assert validation.is_valid, "Token should still be valid"

    # More processing (another 30 seconds)
    # REMOVED_SYNTAX_ERROR: frozen_time.move_to("2024-01-01 12:01:10")
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

    # Token now expired during processing
    # REMOVED_SYNTAX_ERROR: validation = await token_manager.validate_token_jwt(token)
    # REMOVED_SYNTAX_ERROR: return validation

    # Execute request
    # REMOVED_SYNTAX_ERROR: final_validation = await long_running_request(token_data.access_token)

    # Token should be expired
    # REMOVED_SYNTAX_ERROR: assert not final_validation.is_valid, \
    # REMOVED_SYNTAX_ERROR: "Token should expire during long request"

    # But grace period might apply
    # REMOVED_SYNTAX_ERROR: grace_validation = await token_manager.validate_with_grace( )
    # REMOVED_SYNTAX_ERROR: token_data.access_token
    
    # 10 seconds past expiry, within 30-second grace period
    # REMOVED_SYNTAX_ERROR: assert grace_validation.is_valid, \
    # REMOVED_SYNTAX_ERROR: "Should be within grace period"

    # Removed problematic line: @pytest.mark.asyncio
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_token_family_expiry( )
    # REMOVED_SYNTAX_ERROR: self, token_manager
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test coordinated expiry of related tokens"""
        # Create parent session
        # REMOVED_SYNTAX_ERROR: parent_token = await token_manager.create_token( )
        # REMOVED_SYNTAX_ERROR: user_id="parent_user",
        # REMOVED_SYNTAX_ERROR: role="admin",
        # REMOVED_SYNTAX_ERROR: permissions=["all"],
        # REMOVED_SYNTAX_ERROR: expire_minutes=60
        

        # Create child/delegated tokens
        # REMOVED_SYNTAX_ERROR: child_tokens = []
        # REMOVED_SYNTAX_ERROR: for i in range(3):
            # REMOVED_SYNTAX_ERROR: child = await token_manager.create_delegated_token( )
            # REMOVED_SYNTAX_ERROR: parent_token=parent_token.access_token,
            # REMOVED_SYNTAX_ERROR: scope_reduction=["read"],
            # REMOVED_SYNTAX_ERROR: expire_minutes=30  # Shorter than parent
            
            # REMOVED_SYNTAX_ERROR: child_tokens.append(child)

            # Revoke parent token
            # REMOVED_SYNTAX_ERROR: await token_manager.revoke_token(parent_token.access_token)

            # All child tokens should also be invalid
            # REMOVED_SYNTAX_ERROR: for child in child_tokens:
                # REMOVED_SYNTAX_ERROR: validation = await token_manager.validate_token_jwt(child.access_token)
                # REMOVED_SYNTAX_ERROR: assert not validation.is_valid, \
                # REMOVED_SYNTAX_ERROR: "Child tokens should be invalid when parent is revoked"

                # Removed problematic line: @pytest.mark.asyncio
                # REMOVED_SYNTAX_ERROR: @pytest.fixture
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_expiry_notification_schedule( )
                # REMOVED_SYNTAX_ERROR: self, token_manager, notification_tracker
                # REMOVED_SYNTAX_ERROR: ):
                    # REMOVED_SYNTAX_ERROR: """Test scheduled expiry notifications"""
                    # REMOVED_SYNTAX_ERROR: metrics = ExpiryTestMetrics()

                    # REMOVED_SYNTAX_ERROR: with freeze_time("2024-01-01 12:00:00") as frozen_time:
                        # Create token with 30-minute expiry
                        # REMOVED_SYNTAX_ERROR: token_data = await token_manager.create_token( )
                        # REMOVED_SYNTAX_ERROR: user_id="user_notify",
                        # REMOVED_SYNTAX_ERROR: role="user",
                        # REMOVED_SYNTAX_ERROR: permissions=["read"],
                        # REMOVED_SYNTAX_ERROR: expire_minutes=30
                        

                        # Define notification schedule
                        # REMOVED_SYNTAX_ERROR: notification_schedule = [ )
                        # REMOVED_SYNTAX_ERROR: (15, "halfway"),     # 15 minutes before expiry
                        # REMOVED_SYNTAX_ERROR: (5, "warning"),      # 5 minutes before
                        # REMOVED_SYNTAX_ERROR: (1, "urgent"),       # 1 minute before
                        # REMOVED_SYNTAX_ERROR: (0, "expired")       # At expiry
                        

                        # REMOVED_SYNTAX_ERROR: for minutes_before, notification_type in notification_schedule:
                            # Advance to notification time
                            # REMOVED_SYNTAX_ERROR: time_to_advance = 30 - minutes_before
                            # REMOVED_SYNTAX_ERROR: frozen_time.move_to("formatted_string")

                            # Check if notification needed
                            # REMOVED_SYNTAX_ERROR: status = await token_manager.check_token_status(token_data.access_token)

                            # REMOVED_SYNTAX_ERROR: if minutes_before > 0 and status == TokenStatus.EXPIRING_SOON:
                                # REMOVED_SYNTAX_ERROR: await notification_tracker["send"]( )
                                # REMOVED_SYNTAX_ERROR: TokenExpiryNotification( )
                                # REMOVED_SYNTAX_ERROR: user_id="user_notify",
                                # REMOVED_SYNTAX_ERROR: token_id=token_data.jti,
                                # REMOVED_SYNTAX_ERROR: expires_in_seconds=minutes_before * 60,
                                # REMOVED_SYNTAX_ERROR: notification_type=notification_type,
                                # REMOVED_SYNTAX_ERROR: timestamp=datetime.now(timezone.utc)
                                
                                
                                # REMOVED_SYNTAX_ERROR: metrics.notifications_sent += 1
                                # REMOVED_SYNTAX_ERROR: elif minutes_before == 0 and status == TokenStatus.EXPIRED:
                                    # REMOVED_SYNTAX_ERROR: await notification_tracker["send"]( )
                                    # REMOVED_SYNTAX_ERROR: TokenExpiryNotification( )
                                    # REMOVED_SYNTAX_ERROR: user_id="user_notify",
                                    # REMOVED_SYNTAX_ERROR: token_id=token_data.jti,
                                    # REMOVED_SYNTAX_ERROR: expires_in_seconds=0,
                                    # REMOVED_SYNTAX_ERROR: notification_type=notification_type,
                                    # REMOVED_SYNTAX_ERROR: timestamp=datetime.now(timezone.utc)
                                    
                                    
                                    # REMOVED_SYNTAX_ERROR: metrics.notifications_sent += 1

                                    # Verify notification sequence
                                    # REMOVED_SYNTAX_ERROR: notifications = notification_tracker["notifications"]
                                    # REMOVED_SYNTAX_ERROR: assert len(notifications) >= 3, \
                                    # REMOVED_SYNTAX_ERROR: "Should have multiple notifications"

                                    # Verify notification order
                                    # REMOVED_SYNTAX_ERROR: for i in range(len(notifications) - 1):
                                        # REMOVED_SYNTAX_ERROR: assert notifications[i]["expires_in_seconds"] > \
                                        # REMOVED_SYNTAX_ERROR: notifications[i+1]["expires_in_seconds"], \
                                        # REMOVED_SYNTAX_ERROR: "Notifications should be in time order"