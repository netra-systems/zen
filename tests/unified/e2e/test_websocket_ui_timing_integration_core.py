"""Core Tests - Split from test_websocket_ui_timing_integration.py

Business Value Justification (BVJ):
- Segment: All customer tiers using real-time UI features
- Business Goal: User experience optimization and retention
- Value Impact: Ensures responsive UI with appropriate timing expectations
- Strategic/Revenue Impact: Protects $10K MRR from poor UX causing churn

Test Coverage:
- Fast events (<100ms): Immediate UI feedback
- Medium events (<1s): Interactive responses  
- Slow events (>1s): Background processing with progress
- UI layer routing and timing validation
"""

import asyncio
import pytest
import time
import uuid
import json
import websockets
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from tests.unified.jwt_token_helpers import JWTTestHelper

    def to_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format."""
        return {
            "event_id": self.event_id,
            "type": self.event_type,
            "target_layer": self.target_layer.value,
            "payload": self.payload,
            "timestamp": time.time()
        }

    def __init__(self):
        """Initialize WebSocket UI timing tester."""
        self.jwt_helper = JWTTestHelper()
        self.websocket_url = "ws://localhost:8000"
        self.timing_results: List[TimingResult] = []
        self.test_events = self._define_test_events()

    def _define_test_events(self) -> List[TimingTestEvent]:
        """Define test events for different timing categories and UI layers."""
        return [
            # Fast events (<100ms) - Immediate feedback
            TimingTestEvent(
                event_id=f"fast_notification_{uuid.uuid4().hex[:8]}",
                event_type="user_action_feedback",
                target_layer=UILayer.NOTIFICATION,
                expected_timing=TimingCategory.FAST,
                payload={
                    "action": "button_click",
                    "feedback_type": "success",
                    "message": "Action completed"
                }
            ),
            TimingTestEvent(
                event_id=f"fast_status_{uuid.uuid4().hex[:8]}",
                event_type="status_update",
                target_layer=UILayer.STATUS,
                expected_timing=TimingCategory.FAST,
                payload={
                    "status": "processing",
                    "indicator": "spinner",
                    "context": "agent_request"
                }
            ),
            
            # Medium events (<1s) - Interactive responses
            TimingTestEvent(
                event_id=f"medium_chat_{uuid.uuid4().hex[:8]}",
                event_type="chat_message",
                target_layer=UILayer.CHAT,
                expected_timing=TimingCategory.MEDIUM,
                payload={
                    "message": "I'm analyzing your cost optimization opportunities...",
                    "sender": "assistant",
                    "message_type": "progress_update"
                }
            ),
            TimingTestEvent(
                event_id=f"medium_data_{uuid.uuid4().hex[:8]}",
                event_type="data_update",
                target_layer=UILayer.DATA,
                expected_timing=TimingCategory.MEDIUM,
                payload={
                    "update_type": "metrics_refresh",
                    "data": {
                        "current_cost": 1250.75,
                        "potential_savings": 375.25,
                        "optimization_score": 0.78
                    }
                }
            ),
            
            # Slow events (>1s) - Background processing
            TimingTestEvent(
                event_id=f"slow_analysis_{uuid.uuid4().hex[:8]}",
                event_type="analysis_complete",
                target_layer=UILayer.DATA,
                expected_timing=TimingCategory.SLOW,
                payload={
                    "analysis_type": "comprehensive_optimization",
                    "results": {
                        "cost_savings": "$2,150/month",
                        "performance_improvement": "3.2x faster",
                        "implementation_timeline": "2-3 weeks"
                    },
                    "recommendations": [
                        "Implement request batching",
                        "Add Redis caching layer", 
                        "Optimize database queries"
                    ]
                }
            ),
            TimingTestEvent(
                event_id=f"slow_system_{uuid.uuid4().hex[:8]}",
                event_type="system_notification",
                target_layer=UILayer.SYSTEM,
                expected_timing=TimingCategory.SLOW,
                payload={
                    "notification_type": "maintenance_complete",
                    "message": "System optimization completed successfully",
                    "details": {
                        "duration": "45 minutes",
                        "improvements": ["database_indexes", "cache_optimization"]
                    }
                }
            )
        ]

    def _validate_timing_expectation(
        self, 
        expected: TimingCategory, 
        actual: TimingCategory,
        response_time: float
    ) -> bool:
        """Validate if actual timing meets expectations."""
        # Fast events must be fast
        if expected == TimingCategory.FAST:
            return actual == TimingCategory.FAST and response_time < 0.1
        
        # Medium events can be fast or medium, but not slow
        elif expected == TimingCategory.MEDIUM:
            return actual in [TimingCategory.FAST, TimingCategory.MEDIUM] and response_time < 1.0
        
        # Slow events can be any timing (processing may complete faster than expected)
        elif expected == TimingCategory.SLOW:
            return actual != TimingCategory.TIMEOUT and response_time < 5.0
        
        return False
