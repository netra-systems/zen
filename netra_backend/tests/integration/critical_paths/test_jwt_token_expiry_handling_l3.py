"""JWT Token Expiry Handling L3 Integration Tests

Tests comprehensive JWT token expiry scenarios including automatic refresh,
grace periods, sliding windows, and expiry notification mechanisms.

Business Value Justification (BVJ):
- Segment: ALL (Security foundation for all tiers)
- Business Goal: Balance security with user experience
- Value Impact: Reduce support tickets by 30% from token expiry issues
- Strategic Impact: Improve user retention through seamless auth experience

Critical Path:
Token creation -> Usage tracking -> Expiry detection -> 
Grace period -> Auto-refresh -> Notification -> Re-authentication

Mock-Real Spectrum: L3 (Real JWT with time manipulation)
- Real JWT encoding/decoding
- Real Redis TTL management
- Real refresh logic
- Simulated time progression
"""

import pytest
import asyncio
import time
import jwt
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import freezegun

from netra_backend.app.schemas.auth_types import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    Token, TokenData, RefreshRequest, RefreshResponse,
    TokenExpiryNotification, TokenStatus
)
from netra_backend.app.core.config import get_settings
from netra_backend.app.db.redis_manager import get_redis_manager
from clients.auth_client import auth_client
from netra_backend.app.core.token_manager import TokenManager
from netra_backend.app.core.monitoring import metrics_collector


@dataclass
class TokenLifecycle:
    """Track token lifecycle events"""
    token_id: str
    created_at: datetime
    expires_at: datetime
    last_used: datetime
    refresh_count: int = 0
    grace_period_used: bool = False
    auto_refreshed: bool = False
    notifications_sent: List[str] = field(default_factory=list)
    final_status: str = "active"  # active, expired, refreshed, revoked


@dataclass
class ExpiryTestMetrics:
    """Metrics for expiry testing"""
    tokens_created: int = 0
    tokens_expired: int = 0
    tokens_refreshed: int = 0
    auto_refresh_success: int = 0
    auto_refresh_failed: int = 0
    grace_period_grants: int = 0
    notifications_sent: int = 0
    avg_token_lifetime_minutes: float = 0.0
    
    @property
    def refresh_success_rate(self) -> float:
        total_attempts = self.auto_refresh_success + self.auto_refresh_failed
        if total_attempts == 0:
            return 0
        return (self.auto_refresh_success / total_attempts) * 100


class TestJWTTokenExpiryHandling:
    """Test suite for JWT token expiry handling"""
    
    @pytest.fixture
    async def token_manager(self):
        """Initialize token manager"""
        settings = get_settings()
        
        manager = TokenManager(
            secret_key=settings.jwt_secret_key,
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_minutes=60*24*7,  # 7 days
            grace_period_seconds=30
        )
        
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def notification_tracker(self):
        """Track expiry notifications"""
        notifications = []
        
        async def send_notification(notification: TokenExpiryNotification):
            notifications.append({
                "user_id": notification.user_id,
                "token_id": notification.token_id,
                "expires_in_seconds": notification.expires_in_seconds,
                "notification_type": notification.notification_type,
                "timestamp": notification.timestamp
            })
        
        return {"send": send_notification, "notifications": notifications}
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_token_natural_expiry_flow(
        self, token_manager, notification_tracker
    ):
        """Test natural token expiry with notifications"""
        metrics = ExpiryTestMetrics()
        
        # Create token with short expiry
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            token_data = await token_manager.create_token(
                user_id="user123",
                role="user",
                permissions=["read"],
                expire_minutes=5  # 5 minute expiry
            )
            metrics.tokens_created += 1
            
            lifecycle = TokenLifecycle(
                token_id=token_data.jti,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=5),
                last_used=datetime.utcnow()
            )
            
            # Advance time to 1 minute before expiry
            frozen_time.move_to("2024-01-01 12:04:00")
            
            # Check token status - should trigger warning
            status = await token_manager.check_token_status(token_data.access_token)
            assert status == TokenStatus.EXPIRING_SOON
            
            # Send expiry warning
            await notification_tracker["send"](
                TokenExpiryNotification(
                    user_id="user123",
                    token_id=token_data.jti,
                    expires_in_seconds=60,
                    notification_type="warning",
                    timestamp=datetime.utcnow()
                )
            )
            metrics.notifications_sent += 1
            lifecycle.notifications_sent.append("warning")
            
            # Advance to exact expiry time
            frozen_time.move_to("2024-01-01 12:05:00")
            
            # Token should be expired
            status = await token_manager.check_token_status(token_data.access_token)
            assert status == TokenStatus.EXPIRED
            metrics.tokens_expired += 1
            lifecycle.final_status = "expired"
            
            # Verify notification sent
            assert len(notification_tracker["notifications"]) == 1
            assert notification_tracker["notifications"][0]["notification_type"] == "warning"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_grace_period_allowance(
        self, token_manager
    ):
        """Test grace period for recently expired tokens"""
        metrics = ExpiryTestMetrics()
        
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create token
            token_data = await token_manager.create_token(
                user_id="user456",
                role="user",
                permissions=["read"],
                expire_minutes=10
            )
            
            # Advance just past expiry (within grace period)
            frozen_time.move_to("2024-01-01 12:10:15")  # 15 seconds past expiry
            
            # Token should be expired but within grace period
            validation_result = await token_manager.validate_with_grace(
                token_data.access_token
            )
            
            assert validation_result.is_valid, "Token should be valid within grace period"
            assert validation_result.grace_period_used, "Should indicate grace period used"
            metrics.grace_period_grants += 1
            
            # Advance beyond grace period
            frozen_time.move_to("2024-01-01 12:10:45")  # 45 seconds past expiry
            
            # Token should be completely invalid
            validation_result = await token_manager.validate_with_grace(
                token_data.access_token
            )
            
            assert not validation_result.is_valid, "Token should be invalid beyond grace period"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_automatic_token_refresh(
        self, token_manager
    ):
        """Test automatic token refresh before expiry"""
        metrics = ExpiryTestMetrics()
        
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create initial tokens
            token_data = await token_manager.create_token(
                user_id="user789",
                role="admin",
                permissions=["read", "write"],
                expire_minutes=15
            )
            metrics.tokens_created += 1
            
            # Advance to refresh window (e.g., 80% of lifetime)
            frozen_time.move_to("2024-01-01 12:12:00")  # 12 minutes (80% of 15)
            
            # Trigger auto-refresh
            try:
                new_token = await token_manager.auto_refresh(
                    token_data.refresh_token
                )
                metrics.auto_refresh_success += 1
                metrics.tokens_refreshed += 1
                
                # Verify new token
                assert new_token is not None
                assert new_token.access_token != token_data.access_token
                
                # Verify new expiry time
                decoded = jwt.decode(
                    new_token.access_token,
                    options={"verify_signature": False}
                )
                new_exp = datetime.fromtimestamp(decoded["exp"])
                assert new_exp > datetime.utcnow() + timedelta(minutes=14)
                
            except Exception:
                metrics.auto_refresh_failed += 1
                raise
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_sliding_window_expiry(
        self, token_manager
    ):
        """Test sliding window expiry (activity extends token)"""
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create token with sliding window enabled
            token_data = await token_manager.create_token(
                user_id="user_sliding",
                role="user",
                permissions=["read"],
                expire_minutes=30,
                sliding_window=True
            )
            
            initial_exp = datetime.utcnow() + timedelta(minutes=30)
            
            # Simulate activity at 10 minutes
            frozen_time.move_to("2024-01-01 12:10:00")
            await token_manager.update_activity(token_data.access_token)
            
            # Check new expiry (should be extended)
            status = await token_manager.get_token_info(token_data.access_token)
            assert status.expires_at > initial_exp, "Expiry should be extended"
            
            # Simulate more activity at 20 minutes
            frozen_time.move_to("2024-01-01 12:20:00")
            await token_manager.update_activity(token_data.access_token)
            
            # Token should still be valid at original expiry time
            frozen_time.move_to("2024-01-01 12:30:00")
            validation = await token_manager.validate_token(token_data.access_token)
            assert validation.is_valid, "Token should be valid due to sliding window"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_bulk_token_expiry_handling(
        self, token_manager
    ):
        """Test handling bulk token expiries"""
        metrics = ExpiryTestMetrics()
        token_count = 100
        
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create tokens with staggered expiry times
            tokens = []
            for i in range(token_count):
                expire_minutes = 5 + (i % 10)  # 5-14 minute expiry
                token = await token_manager.create_token(
                    user_id=f"user_{i}",
                    role="user",
                    permissions=["read"],
                    expire_minutes=expire_minutes
                )
                tokens.append({
                    "token": token,
                    "expires_at": datetime.utcnow() + timedelta(minutes=expire_minutes)
                })
                metrics.tokens_created += 1
            
            # Advance time and check expiries
            for minute in range(1, 16):
                frozen_time.move_to(f"2024-01-01 12:{minute:02d}:00")
                
                # Check which tokens expired
                for token_info in tokens:
                    if token_info["expires_at"] <= datetime.utcnow():
                        status = await token_manager.check_token_status(
                            token_info["token"].access_token
                        )
                        if status == TokenStatus.EXPIRED:
                            metrics.tokens_expired += 1
            
            # Verify expiry counts
            expected_expired = sum(
                1 for t in tokens 
                if t["expires_at"] <= datetime.utcnow()
            )
            assert metrics.tokens_expired >= expected_expired * 0.95, \
                "Not all expected tokens marked as expired"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_refresh_token_rotation(
        self, token_manager
    ):
        """Test refresh token rotation on use"""
        metrics = ExpiryTestMetrics()
        used_refresh_tokens = set()
        
        # Create initial token pair
        token_data = await token_manager.create_token(
            user_id="user_rotation",
            role="user",
            permissions=["read"],
            expire_minutes=15
        )
        
        current_refresh = token_data.refresh_token
        used_refresh_tokens.add(current_refresh)
        
        # Perform multiple refreshes
        for i in range(5):
            # Use refresh token
            new_tokens = await token_manager.refresh_tokens(
                RefreshRequest(refresh_token=current_refresh)
            )
            metrics.tokens_refreshed += 1
            
            # Verify new refresh token
            assert new_tokens.refresh_token != current_refresh, \
                "Refresh token should rotate"
            assert new_tokens.refresh_token not in used_refresh_tokens, \
                "Refresh token should be unique"
            
            # Old refresh token should be invalidated
            with pytest.raises(Exception) as exc_info:
                await token_manager.refresh_tokens(
                    RefreshRequest(refresh_token=current_refresh)
                )
            assert "invalid" in str(exc_info.value).lower() or \
                   "expired" in str(exc_info.value).lower()
            
            # Update for next iteration
            used_refresh_tokens.add(new_tokens.refresh_token)
            current_refresh = new_tokens.refresh_token
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_expiry_during_request_processing(
        self, token_manager
    ):
        """Test token expiring during request processing"""
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create token with very short expiry
            token_data = await token_manager.create_token(
                user_id="user_processing",
                role="user",
                permissions=["read"],
                expire_minutes=1  # 1 minute
            )
            
            # Start processing request
            async def long_running_request(token: str):
                # Validate token at start
                validation = await token_manager.validate_token(token)
                assert validation.is_valid, "Token should be valid at start"
                
                # Simulate long processing (40 seconds)
                frozen_time.move_to("2024-01-01 12:00:40")
                await asyncio.sleep(0.1)  # Simulated work
                
                # Token still valid (within original minute)
                validation = await token_manager.validate_token(token)
                assert validation.is_valid, "Token should still be valid"
                
                # More processing (another 30 seconds)
                frozen_time.move_to("2024-01-01 12:01:10")
                await asyncio.sleep(0.1)
                
                # Token now expired during processing
                validation = await token_manager.validate_token(token)
                return validation
            
            # Execute request
            final_validation = await long_running_request(token_data.access_token)
            
            # Token should be expired
            assert not final_validation.is_valid, \
                "Token should expire during long request"
            
            # But grace period might apply
            grace_validation = await token_manager.validate_with_grace(
                token_data.access_token
            )
            # 10 seconds past expiry, within 30-second grace period
            assert grace_validation.is_valid, \
                "Should be within grace period"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_token_family_expiry(
        self, token_manager
    ):
        """Test coordinated expiry of related tokens"""
        # Create parent session
        parent_token = await token_manager.create_token(
            user_id="parent_user",
            role="admin",
            permissions=["all"],
            expire_minutes=60
        )
        
        # Create child/delegated tokens
        child_tokens = []
        for i in range(3):
            child = await token_manager.create_delegated_token(
                parent_token=parent_token.access_token,
                scope_reduction=["read"],
                expire_minutes=30  # Shorter than parent
            )
            child_tokens.append(child)
        
        # Revoke parent token
        await token_manager.revoke_token(parent_token.access_token)
        
        # All child tokens should also be invalid
        for child in child_tokens:
            validation = await token_manager.validate_token(child.access_token)
            assert not validation.is_valid, \
                "Child tokens should be invalid when parent is revoked"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_expiry_notification_schedule(
        self, token_manager, notification_tracker
    ):
        """Test scheduled expiry notifications"""
        metrics = ExpiryTestMetrics()
        
        with freezegun.freeze_time("2024-01-01 12:00:00") as frozen_time:
            # Create token with 30-minute expiry
            token_data = await token_manager.create_token(
                user_id="user_notify",
                role="user",
                permissions=["read"],
                expire_minutes=30
            )
            
            # Define notification schedule
            notification_schedule = [
                (15, "halfway"),     # 15 minutes before expiry
                (5, "warning"),      # 5 minutes before
                (1, "urgent"),       # 1 minute before
                (0, "expired")       # At expiry
            ]
            
            for minutes_before, notification_type in notification_schedule:
                # Advance to notification time
                time_to_advance = 30 - minutes_before
                frozen_time.move_to(f"2024-01-01 12:{time_to_advance:02d}:00")
                
                # Check if notification needed
                status = await token_manager.check_token_status(token_data.access_token)
                
                if minutes_before > 0 and status == TokenStatus.EXPIRING_SOON:
                    await notification_tracker["send"](
                        TokenExpiryNotification(
                            user_id="user_notify",
                            token_id=token_data.jti,
                            expires_in_seconds=minutes_before * 60,
                            notification_type=notification_type,
                            timestamp=datetime.utcnow()
                        )
                    )
                    metrics.notifications_sent += 1
                elif minutes_before == 0 and status == TokenStatus.EXPIRED:
                    await notification_tracker["send"](
                        TokenExpiryNotification(
                            user_id="user_notify",
                            token_id=token_data.jti,
                            expires_in_seconds=0,
                            notification_type=notification_type,
                            timestamp=datetime.utcnow()
                        )
                    )
                    metrics.notifications_sent += 1
            
            # Verify notification sequence
            notifications = notification_tracker["notifications"]
            assert len(notifications) >= 3, \
                "Should have multiple notifications"
            
            # Verify notification order
            for i in range(len(notifications) - 1):
                assert notifications[i]["expires_in_seconds"] > \
                       notifications[i+1]["expires_in_seconds"], \
                       "Notifications should be in time order"