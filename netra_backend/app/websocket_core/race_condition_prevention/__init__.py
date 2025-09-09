"""
WebSocket Race Condition Prevention Module

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Eliminate race conditions that cause WebSocket failures
- Value Impact: Prevents "Need to call accept first" errors in Cloud Run environments
- Strategic/Revenue Impact: Protects $500K+ ARR by ensuring reliable WebSocket connections

This module provides race condition detection and prevention components for WebSocket
connections, specifically addressing timing issues in Cloud Run and staging environments.

CRITICAL COMPONENTS:
1. ApplicationConnectionState - Connection state tracking for race condition prevention
2. RaceConditionPattern - Pattern detection for systematic race condition analysis
3. RaceConditionDetector - Core timing violation detection logic
4. HandshakeCoordinator - Handshake completion validation and coordination

ROOT CAUSE ADDRESSED:
- Missing environment-aware WebSocket handshake validation
- Message handling starting before WebSocket handshake completion
- Progressive delay calculation for different deployment environments
- Connection state transition management for multi-user isolation
"""

from netra_backend.app.websocket_core.race_condition_prevention.types import (
    ApplicationConnectionState,
    RaceConditionPattern
)
from netra_backend.app.websocket_core.race_condition_prevention.race_condition_detector import (
    RaceConditionDetector
)
from netra_backend.app.websocket_core.race_condition_prevention.handshake_coordinator import (
    HandshakeCoordinator
)

__all__ = [
    "ApplicationConnectionState",
    "RaceConditionPattern", 
    "RaceConditionDetector",
    "HandshakeCoordinator"
]