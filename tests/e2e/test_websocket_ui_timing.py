"""WebSocket UI Timing Layer Validation Tests.

Tests UI layer timing requirements per SPEC/websocket_communication.xml:
- Fast Layer: 0-100ms (immediate feedback)
- Medium Layer: 100ms-1s (progressive updates)  
- Slow Layer: 1s+ (final results)

Business Value: Ensures responsive user experience through proper event timing,
preventing user perception of system slowness or unresponsiveness.

BVJ: Enterprise/Early - User Experience - Timing compliance directly impacts
user retention and perceived platform performance quality.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pytest

from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient
from tests.config import UnifiedTestConfig


class TestWebSocketUITiming:
    """Test suite for WebSocket UI layer timing requirements."""
    
    @pytest.fixture
    async def backend_client(self):
        """Get authenticated backend client."""
        client = BackendTestClient()
        await client.authenticate()
        try:
            yield client
        finally:
            await client.close()
    
    @pytest.fixture
    async def websocket_client(self, backend_client):
        """Get authenticated WebSocket client."""
        token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        await ws_client.connect(token)
        try:
            yield ws_client
        finally:
            await ws_client.disconnect()
    
    async def test_fast_layer_timing_compliance(self, websocket_client):
        """Test Fast Layer events arrive within 0-100ms for immediate feedback."""
        # Fast layer events per SPEC/websocket_communication.xml
        fast_layer_events = {"agent_started", "tool_executing"}
        
        # Record send time and trigger action
        send_time = time.time()
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Trigger fast feedback events for timing test"}
        })
        
        # Collect events with precise timing
        fast_events_timing = []
        timeout = 5.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                receive_time = time.time()
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") in fast_layer_events:
                    latency_ms = (receive_time - send_time) * 1000
                    fast_events_timing.append({
                        "event_type": message["type"],
                        "latency_ms": latency_ms,
                        "timestamp": receive_time
                    })
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate Fast Layer timing (0-100ms)
        assert len(fast_events_timing) > 0, "No fast layer events received for timing validation"
        
        for event_timing in fast_events_timing:
            latency = event_timing["latency_ms"]
            event_type = event_timing["event_type"]
            
            # Fast Layer requirement: ≤100ms
            assert latency <= 100.0, (
                f"Fast Layer violation: {event_type} took {latency:.1f}ms (max 100ms). "
                f"This impacts immediate user feedback perception."
            )
            
            # Ultra-fast events should be near-instantaneous
            if event_type == "agent_started":
                assert latency <= 50.0, (
                    f"agent_started should be ultra-fast (≤50ms), got {latency:.1f}ms"
                )
    
    async def test_medium_layer_timing_compliance(self, websocket_client):
        """Test Medium Layer events arrive within 100ms-1s for progressive updates."""
        # Medium layer events per spec
        medium_layer_events = {"agent_thinking", "partial_result"}
        
        # Trigger action that generates medium layer events
        send_time = time.time()
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Generate progressive updates with thinking and partial results"}
        })
        
        # Collect medium layer events with timing
        medium_events_timing = []
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                receive_time = time.time()
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") in medium_layer_events:
                    latency_ms = (receive_time - send_time) * 1000
                    medium_events_timing.append({
                        "event_type": message["type"],
                        "latency_ms": latency_ms,
                        "timestamp": receive_time
                    })
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate Medium Layer timing (100ms-1000ms)
        if len(medium_events_timing) > 0:  # Only validate if events were received
            for event_timing in medium_events_timing:
                latency = event_timing["latency_ms"]
                event_type = event_timing["event_type"]
                
                # Medium Layer requirement: 100ms ≤ latency ≤ 1000ms
                assert 100.0 <= latency <= 1000.0, (
                    f"Medium Layer violation: {event_type} took {latency:.1f}ms "
                    f"(expected 100-1000ms). This impacts progressive update perception."
                )
    
    async def test_slow_layer_timing_compliance(self, websocket_client):
        """Test Slow Layer events arrive after 1s for final results."""
        # Slow layer events per spec  
        slow_layer_events = {"agent_completed", "final_report"}
        
        # Trigger comprehensive action for slow layer events
        send_time = time.time()
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Execute comprehensive analysis for final results timing test"}
        })
        
        # Collect slow layer events with timing
        slow_events_timing = []
        timeout = 20.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=3.0
                )
                receive_time = time.time()
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") in slow_layer_events:
                    latency_ms = (receive_time - send_time) * 1000
                    slow_events_timing.append({
                        "event_type": message["type"],
                        "latency_ms": latency_ms,
                        "timestamp": receive_time
                    })
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate Slow Layer timing (≥1000ms)
        assert len(slow_events_timing) > 0, "No slow layer events received for timing validation"
        
        for event_timing in slow_events_timing:
            latency = event_timing["latency_ms"]
            event_type = event_timing["event_type"]
            
            # Slow Layer requirement: ≥1000ms (indicates substantial work)
            assert latency >= 1000.0, (
                f"Slow Layer violation: {event_type} took only {latency:.1f}ms "
                f"(expected ≥1000ms). This may indicate insufficient processing depth."
            )
    
    async def test_event_timing_layer_segregation(self, websocket_client):
        """Test events are properly segregated into correct timing layers."""
        # Expected layer assignments per SPEC/websocket_communication.xml
        expected_layers = {
            "agent_started": "fast",      # 0-100ms
            "tool_executing": "fast",     # 0-100ms  
            "agent_thinking": "medium",   # 100ms-1s
            "partial_result": "medium",   # 100ms-1s
            "agent_completed": "slow",    # 1s+
            "final_report": "slow"        # 1s+
        }
        
        # Trigger comprehensive workflow
        send_time = time.time()
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Full workflow test for timing layer segregation validation"}
        })
        
        # Collect all events with precise timing
        all_events_timing = []
        timeout = 25.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                receive_time = time.time()
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    event_type = message["type"]
                    if event_type in expected_layers:
                        latency_ms = (receive_time - send_time) * 1000
                        all_events_timing.append({
                            "event_type": event_type,
                            "latency_ms": latency_ms,
                            "expected_layer": expected_layers[event_type],
                            "timestamp": receive_time
                        })
                        
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate layer segregation
        layer_violations = []
        
        for event in all_events_timing:
            event_type = event["event_type"]
            latency = event["latency_ms"]
            expected_layer = event["expected_layer"]
            
            # Check layer compliance
            actual_layer = self._classify_timing_layer(latency)
            
            if actual_layer != expected_layer:
                layer_violations.append({
                    "event_type": event_type,
                    "latency_ms": latency,
                    "expected_layer": expected_layer,
                    "actual_layer": actual_layer
                })
        
        # Report violations
        if layer_violations:
            violation_details = "\n".join([
                f"  {v['event_type']}: {v['latency_ms']:.1f}ms "
                f"(expected {v['expected_layer']}, got {v['actual_layer']})"
                for v in layer_violations
            ])
            pytest.fail(
                f"Timing layer segregation violations:\n{violation_details}\n"
                f"This impacts UI responsiveness perception."
            )
    
    async def test_progressive_timing_sequence(self, websocket_client):
        """Test events follow progressive timing sequence (fast→medium→slow)."""
        # Trigger workflow with full timing spectrum
        await websocket_client.send_message({
            "type": "user_message", 
            "payload": {"content": "Progressive timing sequence test with all layer events"}
        })
        
        # Collect events with arrival order
        events_sequence = []
        timeout = 20.0
        start_time = asyncio.get_event_loop().time()
        sequence_start = time.time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                arrival_time = time.time()
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    event_type = message["type"]
                    latency_ms = (arrival_time - sequence_start) * 1000
                    layer = self._classify_timing_layer(latency_ms)
                    
                    events_sequence.append({
                        "event_type": event_type,
                        "latency_ms": latency_ms,
                        "layer": layer,
                        "order": len(events_sequence)
                    })
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Analyze progressive sequence
        if len(events_sequence) >= 2:
            # Check general trend: fast events should come before slow events
            fast_events = [e for e in events_sequence if e["layer"] == "fast"]
            slow_events = [e for e in events_sequence if e["layer"] == "slow"]
            
            if fast_events and slow_events:
                last_fast_order = max(e["order"] for e in fast_events)
                first_slow_order = min(e["order"] for e in slow_events)
                
                assert last_fast_order <= first_slow_order, (
                    f"Progressive timing violation: slow events started before fast events finished. "
                    f"Last fast event at order {last_fast_order}, first slow at {first_slow_order}"
                )
    
    async def test_timing_consistency_across_requests(self, websocket_client):
        """Test timing consistency across multiple requests."""
        timing_measurements = []
        
        # Run multiple identical requests
        for i in range(3):
            send_time = time.time()
            await websocket_client.send_message({
                "type": "user_message",
                "payload": {"content": f"Timing consistency test request {i+1}"}
            })
            
            # Measure first event latency
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        websocket_client.receive_message(),
                        timeout=1.0
                    )
                    receive_time = time.time()
                    
                    if isinstance(message, str):
                        message = json.loads(message)
                    
                    if isinstance(message, dict) and "type" in message:
                        latency_ms = (receive_time - send_time) * 1000
                        timing_measurements.append(latency_ms)
                        break
                        
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    continue
            
            # Brief pause between requests
            await asyncio.sleep(1.0)
        
        # Validate consistency (coefficient of variation < 50%)
        if len(timing_measurements) >= 2:
            avg_latency = sum(timing_measurements) / len(timing_measurements)
            variance = sum((x - avg_latency) ** 2 for x in timing_measurements) / len(timing_measurements)
            std_dev = variance ** 0.5
            coefficient_of_variation = (std_dev / avg_latency) * 100 if avg_latency > 0 else 0
            
            assert coefficient_of_variation <= 50.0, (
                f"Timing inconsistency: CV={coefficient_of_variation:.1f}% (max 50%). "
                f"Measurements: {[f'{x:.1f}ms' for x in timing_measurements]}"
            )
    
    # Helper methods (each ≤8 lines)
    def _classify_timing_layer(self, latency_ms: float) -> str:
        """Classify latency into timing layer per spec."""
        if latency_ms <= 100.0:
            return "fast"
        elif latency_ms <= 1000.0:
            return "medium"
        else:
            return "slow"
    
    def _calculate_timing_stats(self, timings: List[float]) -> Dict[str, float]:
        """Calculate timing statistics for analysis."""
        if not timings:
            return {}
        return {
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "count": len(timings)
        }