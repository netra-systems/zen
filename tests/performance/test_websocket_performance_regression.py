"""
WebSocket Performance Regression Test Suite

BUSINESS CRITICAL: Tests to identify and measure WebSocket performance bottlenecks
causing user-reported slowdowns in chat functionality (90% of platform value).

This test suite specifically targets:
1. Windows-safe sleep performance impact
2. WebSocket connection timing
3. Message round-trip latency
4. Recent SSOT consolidation performance impact

Business Value Justification:
- Segment: ALL (Free -> Enterprise)
- Business Goal: Restore chat performance to acceptable levels
- Value Impact: Chat responsiveness directly affects user experience
- Revenue Impact: Slow chat = user abandonment = revenue loss
"""

import asyncio
import time
import pytest
import statistics
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Import the performance bottleneck modules
from netra_backend.app.core.windows_asyncio_safe import (
    windows_safe_sleep,
    windows_safe_wait_for,
    WindowsAsyncioSafePatterns
)

# Import WebSocket components
from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketPerformanceRegression(SSotBaseTestCase):
    """Test suite for identifying WebSocket performance regressions."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """Setup performance test environment."""
        self.performance_data = {}
        self.baseline_targets = {
            'simple_connection': 1.0,  # 1 second max for simple connection
            'message_round_trip': 0.5,  # 500ms max for message round-trip
            'sleep_accuracy': 0.1,      # 100ms max deviation from expected sleep
        }
    
    async def test_windows_safe_sleep_performance_impact(self):
        """
        CRITICAL TEST: Measure performance impact of Windows-safe sleep chunking.
        
        This test identifies if the Windows-safe sleep implementation is causing
        the reported performance regression by breaking long sleeps into 50ms chunks.
        """
        # Test different sleep durations
        test_durations = [0.1, 0.5, 1.0, 2.0, 5.0]
        results = {}
        
        for duration in test_durations:
            # Measure original asyncio.sleep
            start_time = time.time()
            await asyncio.sleep(duration)
            original_time = time.time() - start_time
            
            # Measure windows_safe_sleep
            start_time = time.time()
            await windows_safe_sleep(duration)
            safe_time = time.time() - start_time
            
            # Calculate overhead
            overhead = safe_time - original_time
            overhead_percent = (overhead / original_time) * 100
            
            results[duration] = {
                'original': original_time,
                'safe': safe_time,
                'overhead': overhead,
                'overhead_percent': overhead_percent
            }
            
            print(f"Sleep {duration}s: Original={original_time:.3f}s, Safe={safe_time:.3f}s, Overhead={overhead:.3f}s ({overhead_percent:.1f}%)")
        
        # Alert on excessive overhead
        for duration, data in results.items():
            if data['overhead_percent'] > 20:  # More than 20% overhead is concerning
                pytest.fail(f"Windows-safe sleep has {data['overhead_percent']:.1f}% overhead for {duration}s sleep - this could cause user-noticeable delays")
        
        self.performance_data['sleep_overhead'] = results
    
    async def test_websocket_connection_timing(self):
        """
        PERFORMANCE TEST: Measure WebSocket connection establishment time.
        
        Tests if recent SSOT consolidation introduced connection delays.
        """
        # Mock WebSocket for testing
        mock_websocket = MagicMock()
        mock_websocket.state = MagicMock()
        mock_websocket.headers = {'authorization': 'Bearer test-token'}
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "ping"}')
        mock_websocket.close = AsyncMock()
        
        # Time WebSocket manager creation
        start_time = time.time()
        manager = UnifiedWebSocketManager()
        creation_time = time.time() - start_time
        
        # Time connection simulation
        start_time = time.time()
        # Simulate connection process without actual network
        await asyncio.sleep(0.01)  # Minimal delay to simulate processing
        connection_time = time.time() - start_time
        
        print(f"WebSocket Manager Creation: {creation_time:.3f}s")
        print(f"WebSocket Connection Simulation: {connection_time:.3f}s")
        
        # Alert if creation is too slow
        if creation_time > 0.5:
            pytest.fail(f"WebSocket manager creation took {creation_time:.3f}s - exceeds 500ms threshold")
        
        self.performance_data['connection_timing'] = {
            'creation': creation_time,
            'connection': connection_time
        }
    
    async def test_message_round_trip_performance(self):
        """
        PERFORMANCE TEST: Measure message processing round-trip time.
        
        Tests if message handling has performance regressions.
        """
        manager = UnifiedWebSocketManager()
        
        # Simulate message processing
        test_messages = [
            {"type": "ping"},
            {"type": "agent_started", "data": {"agent_id": "test"}},
            {"type": "tool_executing", "data": {"tool": "test", "params": {}}},
            {"type": "agent_completed", "data": {"result": "test"}}
        ]
        
        round_trip_times = []
        
        for message in test_messages:
            start_time = time.time()
            
            # Simulate message serialization and processing
            from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
            serialized = _serialize_message_safely(message)
            
            # Simulate processing delay (normally network + computation)
            await asyncio.sleep(0.01)
            
            round_trip_time = time.time() - start_time
            round_trip_times.append(round_trip_time)
            
            print(f"Message {message['type']}: {round_trip_time:.3f}s")
        
        # Calculate statistics
        avg_time = statistics.mean(round_trip_times)
        max_time = max(round_trip_times)
        
        print(f"Average round-trip: {avg_time:.3f}s, Max: {max_time:.3f}s")
        
        # Alert if too slow
        if avg_time > self.baseline_targets['message_round_trip']:
            pytest.fail(f"Average message round-trip {avg_time:.3f}s exceeds {self.baseline_targets['message_round_trip']}s target")
        
        self.performance_data['message_round_trip'] = {
            'average': avg_time,
            'max': max_time,
            'times': round_trip_times
        }
    
    async def test_chunked_sleep_vs_direct_sleep_comparison(self):
        """
        CRITICAL TEST: Direct comparison of chunked vs direct sleep patterns.
        
        This test specifically measures the Windows-safe sleep chunking impact
        that could be causing the reported performance regression.
        """
        async def chunked_sleep(duration: float, chunk_size: float = 0.05):
            """Simulate the Windows-safe chunked sleep pattern."""
            remaining = duration
            while remaining > 0:
                sleep_time = min(chunk_size, remaining)
                await asyncio.sleep(sleep_time)
                remaining -= sleep_time
                # Allow other tasks to run between chunks
                await asyncio.sleep(0)
        
        # Test different scenarios
        test_cases = [
            {'duration': 1.0, 'description': 'Moderate delay (1s)'},
            {'duration': 2.0, 'description': 'Longer delay (2s)'},
            {'duration': 5.0, 'description': 'Extended delay (5s)'},
        ]
        
        results = {}
        
        for case in test_cases:
            duration = case['duration']
            
            # Direct sleep timing
            start_time = time.time()
            await asyncio.sleep(duration)
            direct_time = time.time() - start_time
            
            # Chunked sleep timing
            start_time = time.time()
            await chunked_sleep(duration)
            chunked_time = time.time() - start_time
            
            # Calculate performance impact
            impact = chunked_time - direct_time
            impact_percent = (impact / direct_time) * 100
            
            results[duration] = {
                'direct': direct_time,
                'chunked': chunked_time,
                'impact': impact,
                'impact_percent': impact_percent
            }
            
            print(f"{case['description']}: Direct={direct_time:.3f}s, Chunked={chunked_time:.3f}s, Impact={impact:.3f}s ({impact_percent:.1f}%)")
            
            # CRITICAL: Alert if chunked sleep adds significant delay
            if impact > 0.2:  # More than 200ms added delay
                print(f" WARNING: [U+FE0F]  WARNING: Chunked sleep adds {impact:.3f}s ({impact_percent:.1f}%) delay for {duration}s sleep")
            
            if impact_percent > 10:  # More than 10% performance impact
                print(f" ALERT:  CRITICAL: Chunked sleep has {impact_percent:.1f}% performance impact - likely cause of user-reported slowness")
        
        self.performance_data['chunked_vs_direct'] = results
        
        # Fail test if any scenario shows significant performance regression
        for duration, data in results.items():
            if data['impact_percent'] > 15:  # 15% threshold for regression
                pytest.fail(f"Chunked sleep shows {data['impact_percent']:.1f}% performance regression for {duration}s - this explains user-reported slowness")
    
    async def test_cloud_environment_detection_performance(self):
        """
        PERFORMANCE TEST: Check if environment detection is causing delays.
        
        The Windows-safe patterns include cloud environment detection that
        might be running on every operation.
        """
        patterns = WindowsAsyncioSafePatterns()
        
        # Time multiple environment detections
        detection_times = []
        
        for i in range(10):
            start_time = time.time()
            is_cloud = patterns._detect_cloud_environment()
            detection_time = time.time() - start_time
            detection_times.append(detection_time)
        
        avg_detection_time = statistics.mean(detection_times)
        max_detection_time = max(detection_times)
        
        print(f"Environment detection - Avg: {avg_detection_time:.4f}s, Max: {max_detection_time:.4f}s")
        
        # Alert if environment detection is slow
        if avg_detection_time > 0.01:  # 10ms threshold
            pytest.fail(f"Environment detection takes {avg_detection_time:.4f}s on average - this could slow WebSocket connections")
        
        self.performance_data['environment_detection'] = {
            'average': avg_detection_time,
            'max': max_detection_time,
            'times': detection_times
        }
    
    def test_performance_summary(self):
        """
        SUMMARY TEST: Print comprehensive performance analysis.
        
        This test runs last and provides a summary of all performance findings.
        """
        print("\n" + "="*60)
        print("WEBSOCKET PERFORMANCE REGRESSION ANALYSIS SUMMARY")
        print("="*60)
        
        if 'sleep_overhead' in self.performance_data:
            print("\n SEARCH:  WINDOWS-SAFE SLEEP OVERHEAD:")
            for duration, data in self.performance_data['sleep_overhead'].items():
                print(f"  {duration}s sleep: +{data['overhead']:.3f}s ({data['overhead_percent']:.1f}% overhead)")
        
        if 'chunked_vs_direct' in self.performance_data:
            print("\n ALERT:  CHUNKED VS DIRECT SLEEP COMPARISON:")
            for duration, data in self.performance_data['chunked_vs_direct'].items():
                print(f"  {duration}s sleep: +{data['impact']:.3f}s ({data['impact_percent']:.1f}% slower)")
        
        if 'connection_timing' in self.performance_data:
            print("\n LIGHTNING:  CONNECTION TIMING:")
            data = self.performance_data['connection_timing']
            print(f"  Manager creation: {data['creation']:.3f}s")
            print(f"  Connection time: {data['connection']:.3f}s")
        
        if 'message_round_trip' in self.performance_data:
            print("\n[U+1F4AC] MESSAGE ROUND-TRIP:")
            data = self.performance_data['message_round_trip']
            print(f"  Average: {data['average']:.3f}s")
            print(f"  Maximum: {data['max']:.3f}s")
        
        if 'environment_detection' in self.performance_data:
            print("\n[U+1F329][U+FE0F] ENVIRONMENT DETECTION:")
            data = self.performance_data['environment_detection']
            print(f"  Average: {data['average']:.4f}s")
            print(f"  Maximum: {data['max']:.4f}s")
        
        print("\n" + "="*60)
        print("PERFORMANCE ANALYSIS COMPLETE")
        print("="*60)


if __name__ == "__main__":
    # Run performance tests directly
    import pytest
    pytest.main([__file__, "-v", "-s"])