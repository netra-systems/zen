"""WebSocket Load Testing Scenarios.

Realistic load testing scenarios for WebSocket performance validation.
"""

import pytest

from .test_websocket_load_metrics import WebSocketLoadTester


class TestWebSocketLoadScenarios:
    """Test realistic load scenarios."""
    
    async def test_moderate_load_scenario(self):
        """Test moderate load: 100 connections, 10 messages/sec each."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=100,
            duration_seconds=10,
            messages_per_second=10
        )
        
        self._verify_moderate_load_performance(results)
    
    async def test_high_load_scenario(self):
        """Test high load: 500 connections, 5 messages/sec each."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=500,
            duration_seconds=10,
            messages_per_second=5
        )
        
        self._verify_high_load_performance(results)
    
    async def test_burst_load_scenario(self):
        """Test burst load: rapid message sending."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=50,
            duration_seconds=5,
            messages_per_second=50  # High burst rate
        )
        
        self._verify_burst_load_performance(results)
    
    async def test_sustained_load_scenario(self):
        """Test sustained load over longer duration."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=200,
            duration_seconds=60,  # Longer duration
            messages_per_second=2
        )
        
        self._verify_sustained_load_performance(results)
    
    async def test_mixed_load_scenario(self):
        """Test mixed load with varying message rates."""
        tester = WebSocketLoadTester()
        
        # First batch: Low rate connections
        low_rate_results = await tester.run_concurrent_connections_test(
            num_connections=100,
            duration_seconds=15,
            messages_per_second=1
        )
        
        # Second batch: High rate connections
        high_rate_results = await tester.run_concurrent_connections_test(
            num_connections=50,
            duration_seconds=15,
            messages_per_second=20
        )
        
        self._verify_mixed_load_performance(low_rate_results, high_rate_results)
    
    async def test_stress_load_scenario(self):
        """Test stress load: pushing system limits."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=1000,
            duration_seconds=5,
            messages_per_second=10
        )
        
        self._verify_stress_load_performance(results)
    
    def _verify_moderate_load_performance(self, results):
        """Verify moderate load performance targets."""
        assert results["results"]["success_rate"] >= 0.95  # 95% success rate
        assert results["metrics"]["message_throughput_per_second"] >= 800  # 800+ msg/s
        assert results["metrics"]["connection_times"]["avg_ms"] < 100  # < 100ms connection time
        assert results["metrics"]["message_times"]["avg_ms"] < 50  # < 50ms message round-trip
    
    def _verify_high_load_performance(self, results):
        """Verify high load performance targets."""
        assert results["results"]["success_rate"] >= 0.90  # 90% success rate under high load
        assert results["metrics"]["message_throughput_per_second"] >= 2000  # 2000+ msg/s
        assert results["metrics"]["connection_times"]["avg_ms"] < 200  # < 200ms connection time
        assert results["metrics"]["error_count"] < 50  # Limited errors
    
    def _verify_burst_load_performance(self, results):
        """Verify burst load performance targets."""
        assert results["results"]["success_rate"] >= 0.85  # 85% success rate during bursts
        assert results["metrics"]["message_throughput_per_second"] >= 2000  # High throughput
        assert results["metrics"]["message_times"]["p95_ms"] < 100  # 95th percentile < 100ms
    
    def _verify_sustained_load_performance(self, results):
        """Verify sustained load performance targets."""
        assert results["results"]["success_rate"] >= 0.95  # Maintain high success rate
        assert results["metrics"]["connection_times"]["avg_ms"] < 150  # Stable connection times
        assert results["test_config"]["duration_seconds"] == 60  # Full duration completed
    
    def _verify_mixed_load_performance(self, low_rate_results, high_rate_results):
        """Verify mixed load performance targets."""
        # Low rate connections should have very high success rate
        assert low_rate_results["results"]["success_rate"] >= 0.98
        
        # High rate connections should still perform well
        assert high_rate_results["results"]["success_rate"] >= 0.90
        
        # Combined throughput should be reasonable
        total_throughput = (
            low_rate_results["metrics"]["message_throughput_per_second"] +
            high_rate_results["metrics"]["message_throughput_per_second"]
        )
        assert total_throughput >= 1000
    
    def _verify_stress_load_performance(self, results):
        """Verify stress load performance (more lenient targets)."""
        # Under stress, we expect some degradation but not complete failure
        assert results["results"]["success_rate"] >= 0.70  # 70% success rate under stress
        assert results["metrics"]["error_count"] < 300  # Acceptable error count
        assert results["metrics"]["connection_times"]["avg_ms"] < 500  # Connection time limit


class TestWebSocketLoadEdgeCases:
    """Test edge cases in load scenarios."""
    
    async def test_zero_message_rate(self):
        """Test connections with zero message rate."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=10,
            duration_seconds=5,
            messages_per_second=0  # No messages
        )
        
        # Should still establish connections successfully
        assert results["results"]["success_rate"] >= 0.90
        assert results["metrics"]["total_messages_sent"] == 0
    
    async def test_single_connection_high_rate(self):
        """Test single connection with very high message rate."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=1,
            duration_seconds=5,
            messages_per_second=1000  # Very high rate
        )
        
        # Single connection should handle high rate well
        assert results["results"]["success_rate"] == 1.0
        assert results["metrics"]["total_messages_sent"] > 4000  # Should send most messages
    
    async def test_short_duration_test(self):
        """Test very short duration load test."""
        tester = WebSocketLoadTester()
        
        results = await tester.run_concurrent_connections_test(
            num_connections=100,
            duration_seconds=1,  # Very short
            messages_per_second=10
        )
        
        # Should complete without errors despite short duration
        assert results["results"]["success_rate"] >= 0.90
        assert results["test_config"]["duration_seconds"] == 1


if __name__ == "__main__":
    import asyncio
    
    async def run_scenarios():
        test_scenarios = TestWebSocketLoadScenarios()
        
        print("Running moderate load scenario...")
        await test_scenarios.test_moderate_load_scenario()
        
        print("Running high load scenario...")
        await test_scenarios.test_high_load_scenario()
        
        print("Running burst load scenario...")
        await test_scenarios.test_burst_load_scenario()
        
        print("All load scenarios completed successfully!")
    
    asyncio.run(run_scenarios())
