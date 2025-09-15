"""
Backend service restart utilities for WebSocket resilience testing.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: Service Restart Resilience
- Value Impact: Provides utilities for testing backend service restart scenarios
- Strategic/Revenue Impact: Ensures continuity during service deployments
"""

from enum import Enum


class ReconnectionStrategy(Enum):
    """Strategies for handling WebSocket reconnection during backend restarts."""
    GRACEFUL = "graceful"
    EMERGENCY = "emergency"
    ROLLING_DEPLOYMENT = "rolling_deployment"
    EXTENDED_BACKOFF = "extended_backoff"
