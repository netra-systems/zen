"""
Unit tests for WebSocket Event Monitor - Testing event tracking and validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Real-time chat quality assurance
- Value Impact: Ensures all critical agent events are delivered to users  
- Strategic Impact: Validates the core WebSocket event system that delivers AI chat value

These tests focus on event monitoring, validation, and the critical requirement
that all 5 agent events are properly tracked and delivered for business value.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock
from netra_backend.app.websocket_core.event_monitor import (
    WebSocketEventMonitor,
    EventValidationError,
    MissingCriticalEventError,
    EventTracker,
    EventMetrics
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestWebSocketEventMonitor:
    """Unit tests for WebSocket event monitoring."""
    
    @pytest.fixture
    def event_monitor(self):
        """Create WebSocketEventMonitor instance."""
        return WebSocketEventMonitor(
            track_critical_events=True,
            validate_event_order=True,
            metrics_enabled=True
        )
    
    @pytest.fixture
    def critical_agent_events(self):
        """List of critical agent events that must be tracked."""
        return [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_THINKING, 
            MessageType.TOOL_EXECUTING,
            MessageType.TOOL_COMPLETED,
            MessageType.AGENT_COMPLETED
        ]
    
    @pytest.fixture
    def sample_agent_session(self):
        """Create sample agent execution session."""
        return {
            "user_id": "user_123",
            "thread_id": "thread_456", 
            "run_id": "run_789",
            "agent_name": "cost_optimizer",
            "started_at": datetime.now(timezone.utc)
        }
    
    def test_initializes_with_correct_configuration(self, event_monitor):
        """Test EventMonitor initializes with proper configuration."""
        assert event_monitor.track_critical_events is True
        assert event_monitor.validate_event_order is True
        assert event_monitor.metrics_enabled is True
        assert len(event_monitor._session_trackers) == 0
        assert event_monitor._validation_lock is not None
    
    @pytest.mark.asyncio
    async def test_starts_tracking_agent_session(self, event_monitor, sample_agent_session):
        """Test starting agent session tracking."""
        session_id = "session_123"
        
        # Start tracking
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Verify session tracker created
        assert session_id in event_monitor._session_trackers
        tracker = event_monitor._session_trackers[session_id]
        assert isinstance(tracker, EventTracker)
        assert tracker.user_id == sample_agent_session["user_id"]
        assert tracker.agent_name == sample_agent_session["agent_name"]
        assert len(tracker.events_received) == 0
        assert tracker.is_complete is False
    
    @pytest.mark.asyncio
    async def test_records_agent_events_correctly(self, event_monitor, critical_agent_events, 
                                                 sample_agent_session):
        """Test recording of agent events with proper validation."""
        session_id = "session_123"
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Record each critical event
        for event_type in critical_agent_events:
            message = WebSocketMessage(
                message_type=event_type,
                payload={
                    "agent_name": "cost_optimizer",
                    "session_id": session_id,
                    "status": "success"
                },
                user_id=sample_agent_session["user_id"],
                thread_id=sample_agent_session["thread_id"]
            )
            
            await event_monitor.record_event(session_id, message)
        
        # Verify all events recorded
        tracker = event_monitor._session_trackers[session_id]
        assert len(tracker.events_received) == 5
        
        # Verify event types recorded correctly
        recorded_types = [event.message_type for event in tracker.events_received]
        assert set(recorded_types) == set(critical_agent_events)
    
    @pytest.mark.asyncio
    async def test_validates_critical_event_completion(self, event_monitor, 
                                                      critical_agent_events, sample_agent_session):
        """Test validation that all critical events are received."""
        session_id = "session_123"
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Record all critical events
        for event_type in critical_agent_events:
            message = WebSocketMessage(
                message_type=event_type,
                payload={"agent_name": "cost_optimizer"},
                user_id=sample_agent_session["user_id"]
            )
            await event_monitor.record_event(session_id, message)
        
        # Validate completion - should pass
        is_complete = await event_monitor.validate_session_completion(session_id)
        assert is_complete is True
        
        # Verify tracker marked as complete
        tracker = event_monitor._session_trackers[session_id]
        assert tracker.is_complete is True
    
    @pytest.mark.asyncio
    async def test_detects_missing_critical_events(self, event_monitor, sample_agent_session):
        """Test detection of missing critical events."""
        session_id = "session_123"
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Record only some events (missing AGENT_THINKING and TOOL_COMPLETED)
        partial_events = [
            MessageType.AGENT_STARTED,
            MessageType.TOOL_EXECUTING,
            MessageType.AGENT_COMPLETED
        ]
        
        for event_type in partial_events:
            message = WebSocketMessage(
                message_type=event_type,
                payload={"agent_name": "cost_optimizer"},
                user_id=sample_agent_session["user_id"]
            )
            await event_monitor.record_event(session_id, message)
        
        # Validation should detect missing events
        with pytest.raises(MissingCriticalEventError) as exc_info:
            await event_monitor.validate_session_completion(session_id)
        
        error = exc_info.value
        assert "missing critical events" in str(error).lower()
        assert "AGENT_THINKING" in str(error)
        assert "TOOL_COMPLETED" in str(error)
    
    @pytest.mark.asyncio
    async def test_validates_event_order_correctness(self, event_monitor, sample_agent_session):
        """Test validation of proper event ordering."""
        session_id = "session_123"
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Record events in wrong order (AGENT_COMPLETED before AGENT_STARTED)
        wrong_order_events = [
            MessageType.AGENT_COMPLETED,  # Wrong - should be last
            MessageType.AGENT_STARTED,    # Wrong - should be first
            MessageType.AGENT_THINKING,
            MessageType.TOOL_EXECUTING,
            MessageType.TOOL_COMPLETED
        ]
        
        for event_type in wrong_order_events:
            message = WebSocketMessage(
                message_type=event_type,
                payload={"agent_name": "cost_optimizer"},
                user_id=sample_agent_session["user_id"]
            )
            await event_monitor.record_event(session_id, message)
        
        # Should detect ordering violation
        with pytest.raises(EventValidationError) as exc_info:
            await event_monitor.validate_session_completion(session_id)
        
        assert "event order" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_tracks_event_timing_metrics(self, event_monitor, sample_agent_session):
        """Test event timing metrics collection."""
        session_id = "session_123"
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Record events with delays
        events = [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_THINKING,
            MessageType.AGENT_COMPLETED
        ]
        
        for i, event_type in enumerate(events):
            # Add small delay between events
            if i > 0:
                await asyncio.sleep(0.01)
            
            message = WebSocketMessage(
                message_type=event_type,
                payload={"agent_name": "cost_optimizer"},
                user_id=sample_agent_session["user_id"]
            )
            await event_monitor.record_event(session_id, message)
        
        # Get metrics
        metrics = await event_monitor.get_session_metrics(session_id)
        assert isinstance(metrics, EventMetrics)
        
        # Verify timing captured
        assert metrics.session_duration_ms > 0
        assert metrics.total_events == 3
        assert len(metrics.event_timings) == 3
        
        # Verify event timestamps are in order
        timestamps = [timing.timestamp for timing in metrics.event_timings]
        assert timestamps == sorted(timestamps)
    
    @pytest.mark.asyncio
    async def test_handles_multiple_concurrent_sessions(self, event_monitor, critical_agent_events):
        """Test concurrent tracking of multiple agent sessions."""
        # Create multiple sessions
        sessions = {
            "session_1": {"user_id": "user_123", "agent_name": "optimizer"},
            "session_2": {"user_id": "user_456", "agent_name": "analyzer"}, 
            "session_3": {"user_id": "user_789", "agent_name": "reporter"}
        }
        
        # Start tracking all sessions
        for session_id, session_data in sessions.items():
            await event_monitor.start_session_tracking(session_id, session_data)
        
        # Record events for each session concurrently
        tasks = []
        for session_id, session_data in sessions.items():
            for event_type in critical_agent_events:
                message = WebSocketMessage(
                    message_type=event_type,
                    payload={"agent_name": session_data["agent_name"]},
                    user_id=session_data["user_id"]
                )
                task = asyncio.create_task(
                    event_monitor.record_event(session_id, message)
                )
                tasks.append(task)
        
        # Wait for all events
        await asyncio.gather(*tasks)
        
        # Verify all sessions tracked independently
        assert len(event_monitor._session_trackers) == 3
        for session_id in sessions:
            tracker = event_monitor._session_trackers[session_id]
            assert len(tracker.events_received) == 5
    
    @pytest.mark.asyncio
    async def test_cleans_up_completed_sessions(self, event_monitor, critical_agent_events,
                                               sample_agent_session):
        """Test cleanup of completed session trackers."""
        session_id = "session_123"
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Complete the session
        for event_type in critical_agent_events:
            message = WebSocketMessage(
                message_type=event_type,
                payload={"agent_name": "cost_optimizer"},
                user_id=sample_agent_session["user_id"]
            )
            await event_monitor.record_event(session_id, message)
        
        await event_monitor.validate_session_completion(session_id)
        
        # Request cleanup
        await event_monitor.cleanup_completed_sessions(max_age_minutes=0)
        
        # Verify cleanup (implementation dependent)
        # Completed sessions older than max_age should be cleaned up
        if event_monitor.auto_cleanup_enabled:
            assert session_id not in event_monitor._session_trackers
    
    @pytest.mark.asyncio
    async def test_handles_session_timeout_gracefully(self, event_monitor, sample_agent_session):
        """Test handling of session timeout scenarios."""
        session_id = "session_123" 
        await event_monitor.start_session_tracking(session_id, sample_agent_session)
        
        # Record only partial events
        message = WebSocketMessage(
            message_type=MessageType.AGENT_STARTED,
            payload={"agent_name": "cost_optimizer"},
            user_id=sample_agent_session["user_id"]
        )
        await event_monitor.record_event(session_id, message)
        
        # Simulate timeout by manipulating session start time
        tracker = event_monitor._session_trackers[session_id]
        tracker.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        # Check for timeout
        is_timeout = await event_monitor.check_session_timeout(
            session_id, timeout_minutes=5
        )
        assert is_timeout is True
        
        # Should be able to mark as timed out
        await event_monitor.mark_session_timeout(session_id)
        assert tracker.is_timeout is True
        assert tracker.is_complete is False