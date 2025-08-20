"""
WebSocket UI Layer Timing Integration Test

Validates that events reach correct UI layers within timing windows to ensure
optimal user perceived performance and protect $10K MRR from timing issues.

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


class TimingCategory(str, Enum):
    """WebSocket event timing categories."""
    FAST = "fast"       # <100ms - Immediate feedback
    MEDIUM = "medium"   # <1s - Interactive responses
    SLOW = "slow"       # >1s - Background processing
    TIMEOUT = "timeout" # Failed timing requirement


class UILayer(str, Enum):
    """UI layers for event routing."""
    NOTIFICATION = "notification"   # Toast notifications, alerts
    CHAT = "chat"                  # Chat interface updates
    STATUS = "status"              # Status indicators, progress
    DATA = "data"                  # Data updates, results
    SYSTEM = "system"              # System messages, errors


@dataclass
class TimingTestEvent:
    """Test event for timing validation."""
    event_id: str
    event_type: str
    target_layer: UILayer
    expected_timing: TimingCategory
    payload: Dict[str, Any]
    
    def to_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format."""
        return {
            "event_id": self.event_id,
            "type": self.event_type,
            "target_layer": self.target_layer.value,
            "payload": self.payload,
            "timestamp": time.time()
        }


@dataclass
class TimingResult:
    """Result of timing validation test."""
    event_id: str
    expected_timing: TimingCategory
    actual_timing: float
    timing_category: TimingCategory
    ui_layer: UILayer
    success: bool
    latency_ms: float


class WebSocketUITimingTester:
    """Integration tester for WebSocket UI timing."""
    
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
    
    async def test_websocket_connection_timing(self, token: str) -> Tuple[bool, str]:
        """Test WebSocket connection establishment timing."""
        try:
            start_time = time.time()
            
            ws_uri = f"{self.websocket_url}/ws?token={token}"
            websocket = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            connection_time = time.time() - start_time
            
            # Send ping to validate connection
            await websocket.ping()
            await websocket.close()
            
            # Connection should be fast (<500ms)
            if connection_time < 0.5:
                return True, f"Connection established in {connection_time*1000:.1f}ms"
            else:
                return False, f"Connection too slow: {connection_time*1000:.1f}ms"
                
        except Exception as e:
            return False, f"Connection timing test failed: {e}"
    
    async def test_event_timing_by_category(
        self, 
        token: str,
        events: List[TimingTestEvent]
    ) -> List[TimingResult]:
        """Test event timing validation by category."""
        results = []
        
        try:
            ws_uri = f"{self.websocket_url}/ws?token={token}"
            websocket = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            for event in events:
                # Send event and measure response timing
                start_time = time.time()
                
                message = event.to_message()
                await websocket.send(json.dumps(message))
                
                # Wait for response with timeout based on expected category
                timeout_map = {
                    TimingCategory.FAST: 0.15,    # 150ms timeout for fast events
                    TimingCategory.MEDIUM: 1.5,   # 1.5s timeout for medium events
                    TimingCategory.SLOW: 5.0      # 5s timeout for slow events
                }
                
                timeout = timeout_map.get(event.expected_timing, 5.0)
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    response_time = time.time() - start_time
                    response_data = json.loads(response)
                    
                    # Categorize actual timing
                    if response_time < 0.1:
                        actual_category = TimingCategory.FAST
                    elif response_time < 1.0:
                        actual_category = TimingCategory.MEDIUM
                    else:
                        actual_category = TimingCategory.SLOW
                    
                    # Validate timing expectation
                    timing_success = self._validate_timing_expectation(
                        event.expected_timing, 
                        actual_category,
                        response_time
                    )
                    
                    result = TimingResult(
                        event_id=event.event_id,
                        expected_timing=event.expected_timing,
                        actual_timing=response_time,
                        timing_category=actual_category,
                        ui_layer=event.target_layer,
                        success=timing_success,
                        latency_ms=response_time * 1000
                    )
                    
                except asyncio.TimeoutError:
                    # Event timed out
                    result = TimingResult(
                        event_id=event.event_id,
                        expected_timing=event.expected_timing,
                        actual_timing=timeout,
                        timing_category=TimingCategory.TIMEOUT,
                        ui_layer=event.target_layer,
                        success=False,
                        latency_ms=timeout * 1000
                    )
                
                results.append(result)
                self.timing_results.append(result)
                
                # Brief pause between events
                await asyncio.sleep(0.1)
            
            await websocket.close()
            
        except Exception as e:
            # Create error result for failed test
            error_result = TimingResult(
                event_id="connection_error",
                expected_timing=TimingCategory.FAST,
                actual_timing=float('inf'),
                timing_category=TimingCategory.TIMEOUT,
                ui_layer=UILayer.SYSTEM,
                success=False,
                latency_ms=float('inf')
            )
            results.append(error_result)
        
        return results
    
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
    
    async def test_ui_layer_routing_accuracy(
        self, 
        token: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Test that events are routed to correct UI layers."""
        try:
            ws_uri = f"{self.websocket_url}/ws?token={token}"
            websocket = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            # Test each UI layer
            layer_tests = {}
            for layer in UILayer:
                test_event = TimingTestEvent(
                    event_id=f"layer_test_{layer.value}_{uuid.uuid4().hex[:6]}",
                    event_type=f"{layer.value}_test",
                    target_layer=layer,
                    expected_timing=TimingCategory.MEDIUM,
                    payload={"test": True, "target_layer": layer.value}
                )
                
                message = test_event.to_message()
                await websocket.send(json.dumps(message))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    # Validate layer routing
                    routed_correctly = (
                        response_data.get("target_layer") == layer.value or
                        response_data.get("ui_layer") == layer.value
                    )
                    
                    layer_tests[layer.value] = {
                        "routed_correctly": routed_correctly,
                        "response_time": time.time() - message["timestamp"]
                    }
                    
                except asyncio.TimeoutError:
                    layer_tests[layer.value] = {
                        "routed_correctly": False,
                        "response_time": None,
                        "error": "timeout"
                    }
            
            await websocket.close()
            
            # Evaluate routing accuracy
            successful_routes = sum(
                1 for test in layer_tests.values() 
                if test.get("routed_correctly", False)
            )
            
            routing_rate = successful_routes / len(UILayer)
            
            if routing_rate >= 0.8:  # 80% routing accuracy required
                return True, f"UI layer routing: {routing_rate:.1%} accurate", layer_tests
            else:
                return False, f"UI layer routing below threshold: {routing_rate:.1%}", layer_tests
                
        except Exception as e:
            return False, f"UI layer routing test failed: {e}", {}
    
    async def analyze_timing_performance_metrics(self) -> Dict[str, Any]:
        """Analyze overall timing performance metrics."""
        if not self.timing_results:
            return {"error": "No timing results available"}
        
        # Calculate metrics by timing category
        fast_results = [r for r in self.timing_results if r.expected_timing == TimingCategory.FAST]
        medium_results = [r for r in self.timing_results if r.expected_timing == TimingCategory.MEDIUM]
        slow_results = [r for r in self.timing_results if r.expected_timing == TimingCategory.SLOW]
        
        metrics = {
            "total_events_tested": len(self.timing_results),
            "overall_success_rate": sum(1 for r in self.timing_results if r.success) / len(self.timing_results),
            "fast_events": {
                "count": len(fast_results),
                "success_rate": sum(1 for r in fast_results if r.success) / len(fast_results) if fast_results else 0,
                "avg_latency_ms": sum(r.latency_ms for r in fast_results) / len(fast_results) if fast_results else 0,
                "max_latency_ms": max(r.latency_ms for r in fast_results) if fast_results else 0
            },
            "medium_events": {
                "count": len(medium_results),
                "success_rate": sum(1 for r in medium_results if r.success) / len(medium_results) if medium_results else 0,
                "avg_latency_ms": sum(r.latency_ms for r in medium_results) / len(medium_results) if medium_results else 0,
                "max_latency_ms": max(r.latency_ms for r in medium_results) if medium_results else 0
            },
            "slow_events": {
                "count": len(slow_results),
                "success_rate": sum(1 for r in slow_results if r.success) / len(slow_results) if slow_results else 0,
                "avg_latency_ms": sum(r.latency_ms for r in slow_results) / len(slow_results) if slow_results else 0,
                "max_latency_ms": max(r.latency_ms for r in slow_results) if slow_results else 0
            }
        }
        
        return metrics


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_ui_timing_integration():
    """
    Integration test for WebSocket UI layer timing.
    
    Validates that events reach correct UI layers within timing windows
    to ensure optimal user experience and protect $10K MRR.
    
    BVJ: User experience optimization through responsive UI timing
    """
    tester = WebSocketUITimingTester()
    
    try:
        # Create test JWT token
        payload = tester.jwt_helper.create_valid_payload()
        payload.update({
            "sub": f"ui_timing_user_{uuid.uuid4().hex[:8]}",
            "permissions": ["read", "write", "websocket_access"],
            "ui_timing_test": True
        })
        token = await tester.jwt_helper.create_jwt_token(payload)
        
        # Test 1: WebSocket connection timing
        conn_success, conn_msg = await tester.test_websocket_connection_timing(token)
        assert conn_success, f"WebSocket connection timing failed: {conn_msg}"
        
        # Test 2: Event timing by category
        timing_results = await tester.test_event_timing_by_category(token, tester.test_events)
        assert len(timing_results) >= 5, "Insufficient timing test results"
        
        # Test 3: UI layer routing accuracy
        routing_success, routing_msg, routing_data = await tester.test_ui_layer_routing_accuracy(token)
        assert routing_success, f"UI layer routing failed: {routing_msg}"
        
        # Test 4: Performance metrics validation
        metrics = await tester.analyze_timing_performance_metrics()
        assert metrics["overall_success_rate"] >= 0.8, f"Overall timing success rate too low: {metrics['overall_success_rate']:.1%}"
        
        # Fast event validation
        fast_metrics = metrics["fast_events"]
        if fast_metrics["count"] > 0:
            assert fast_metrics["success_rate"] >= 0.9, f"Fast events success rate too low: {fast_metrics['success_rate']:.1%}"
            assert fast_metrics["avg_latency_ms"] < 100, f"Fast events too slow: {fast_metrics['avg_latency_ms']:.1f}ms"
        
        # Medium event validation
        medium_metrics = metrics["medium_events"]
        if medium_metrics["count"] > 0:
            assert medium_metrics["success_rate"] >= 0.8, f"Medium events success rate too low: {medium_metrics['success_rate']:.1%}"
            assert medium_metrics["avg_latency_ms"] < 1000, f"Medium events too slow: {medium_metrics['avg_latency_ms']:.1f}ms"
        
        # Business value validation
        assert len(tester.timing_results) >= 5, "Multiple timing scenarios should be tested"
        
        print(f"[SUCCESS] WebSocket UI timing integration test PASSED")
        print(f"[BUSINESS VALUE] $10K MRR protection validated through UI timing")
        print(f"[CONNECTION] {conn_msg}")
        print(f"[ROUTING] {routing_msg}")
        print(f"[PERFORMANCE] Overall success: {metrics['overall_success_rate']:.1%}")
        print(f"[FAST EVENTS] {fast_metrics['count']} tested, {fast_metrics['avg_latency_ms']:.1f}ms avg")
        print(f"[MEDIUM EVENTS] {medium_metrics['count']} tested, {medium_metrics['avg_latency_ms']:.1f}ms avg")
        
    except Exception as e:
        print(f"[ERROR] WebSocket UI timing test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_websocket_timing_quick_check():
    """
    Quick timing check for WebSocket UI components.
    
    Lightweight test for CI/CD pipelines focused on basic timing validation.
    """
    tester = WebSocketUITimingTester()
    
    try:
        # Create test token
        payload = tester.jwt_helper.create_valid_payload()
        payload.update({"sub": f"quick_timing_user_{uuid.uuid4().hex[:8]}"})
        token = await tester.jwt_helper.create_jwt_token(payload)
        
        # Test connection timing only
        conn_success, conn_msg = await tester.test_websocket_connection_timing(token)
        assert conn_success, f"Quick timing check failed: {conn_msg}"
        
        print(f"[QUICK CHECK PASS] WebSocket timing: {conn_msg}")
        
    except Exception as e:
        print(f"[QUICK CHECK FAIL] WebSocket timing check failed: {e}")
        raise


if __name__ == "__main__":
    """Run WebSocket UI timing test standalone."""
    async def run_test():
        print("Running WebSocket UI Timing Integration Test...")
        await test_websocket_ui_timing_integration()
        print("Test completed successfully!")
    
    asyncio.run(run_test())


# Business Value Summary
"""
WebSocket UI Layer Timing Integration Test - Business Value Summary

BVJ: User experience optimization protecting $10K MRR through responsive UI
- Validates fast events (<100ms) for immediate user feedback
- Tests medium events (<1s) for interactive response expectations
- Ensures slow events (>1s) properly communicate background processing
- Protects against poor UX causing user frustration and churn

Strategic Value:
- Foundation for responsive real-time user interfaces
- Quality assurance for user perceived performance
- Prevention of timing-related UX issues affecting retention
- Support for enterprise-grade responsiveness requirements
"""