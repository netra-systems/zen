"""
Test Suite: Concurrent Connection Scalability - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Multi-tenant Scalability
- Value Impact: Supports enterprise concurrent user requirements
- Strategic/Revenue Impact: Enables high-value enterprise contracts

This test validates connection scalability under concurrent load.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.resource_monitoring import ResourceMonitor
from tests.e2e.test_helpers.throughput_helpers import E2E_TEST_CONFIG
from tests.e2e.test_helpers.websocket_helpers import (
    stress_test_connections,
)

logger = logging.getLogger(__name__)

SCALABILITY_CONFIG = {
    "connection_levels": [10, 50, 100, 200],
    "messages_per_connection": 100,
    "max_connection_time": 30,
    "min_success_rate": 0.95,
    "max_resource_growth": 500  # MB
}

class TestConcurrentConnectionScalability:
    """Test concurrent connection scalability"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(600)
    async def test_concurrent_connection_scaling(self, high_volume_server):
        """Test scaling with increasing concurrent connections"""
        monitor = ResourceMonitor(interval_seconds=2.0)
        await monitor.start()
        
        try:
            scaling_results = {}
            
            for connection_count in SCALABILITY_CONFIG["connection_levels"]:
                logger.info(f"Testing {connection_count} concurrent connections")
                
                result = await self._test_connection_level(connection_count)
                scaling_results[connection_count] = result
                
                # Validate scaling requirements
                assert result["success_rate"] >= SCALABILITY_CONFIG["min_success_rate"], \
                    f"Success rate too low at {connection_count} connections: {result['success_rate']:.3f}"
                
                assert result["avg_connection_time"] <= SCALABILITY_CONFIG["max_connection_time"], \
                    f"Connection time too high: {result['avg_connection_time']:.2f}s"
                
                # Allow system to stabilize
                await asyncio.sleep(5.0)
            
            self._validate_linear_scaling(scaling_results)
            
        finally:
            stats = await monitor.stop()
            
        # Resource usage should remain reasonable
        assert stats["memory"]["growth_mb"] <= SCALABILITY_CONFIG["max_resource_growth"], \
            f"Memory growth too high: {stats['memory']['growth_mb']:.1f}MB"
        
        logger.info("Connection scalability test completed")
    
    @pytest.mark.asyncio
    async def test_connection_burst_handling(self, high_volume_server):
        """Test handling of sudden connection bursts"""
        burst_connections = 100
        burst_duration = 10  # seconds
        
        logger.info(f"Testing connection burst: {burst_connections} connections in {burst_duration}s")
        
        # Create connections rapidly
        start_time = time.time()
        
        async def create_connection_burst():
            tasks = []
            for i in range(burst_connections):
                task = asyncio.create_task(self._single_connection_test(i))
                tasks.append(task)
                
                # Stagger connection attempts
                if i % 10 == 0 and i > 0:
                    await asyncio.sleep(0.1)
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        results = await create_connection_burst()
        total_time = time.time() - start_time
        
        # Analyze burst results
        successful_connections = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        success_rate = successful_connections / burst_connections
        
        assert success_rate >= 0.8, \
            f"Burst success rate too low: {success_rate:.3f}"
        
        assert total_time <= burst_duration * 2, \
            f"Burst took too long: {total_time:.2f}s"
        
        logger.info(f"Connection burst test passed: {success_rate:.3f} success rate")
    
    async def _test_connection_level(self, connection_count: int) -> Dict[str, float]:
        """Test specific connection level"""
        messages_per_conn = SCALABILITY_CONFIG["messages_per_connection"]
        
        start_time = time.time()
        
        result = await stress_test_connections(
            server_url=E2E_TEST_CONFIG["websocket_url"],
            num_connections=connection_count,
            messages_per_connection=messages_per_conn
        )
        
        total_time = time.time() - start_time
        
        success_rate = result["successful_connections"] / result["total_connections"]
        avg_connection_time = total_time / connection_count if connection_count > 0 else 0
        
        return {
            "connection_count": connection_count,
            "success_rate": success_rate,
            "avg_connection_time": avg_connection_time,
            "total_time": total_time,
            "message_success_rate": result["total_messages_received"] / result["total_messages_sent"] if result["total_messages_sent"] > 0 else 0
        }
    
    async def _single_connection_test(self, connection_id: int) -> Dict[str, any]:
        """Single connection test for burst testing"""
        from tests.e2e.test_helpers.websocket_helpers import (
            test_websocket_test_context as websocket_test_context,
        )
        
        try:
            async with websocket_test_context(E2E_TEST_CONFIG["websocket_url"], timeout=10.0) as websocket:
                # Send a few test messages
                for i in range(5):
                    message = {
                        "message_id": f"burst_conn_{connection_id}_msg_{i}",
                        "connection_id": connection_id,
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(message))
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        pass
                
                return {"success": True, "connection_id": connection_id}
                
        except Exception as e:
            logger.warning(f"Connection {connection_id} failed: {e}")
            return {"success": False, "connection_id": connection_id, "error": str(e)}
    
    def _validate_linear_scaling(self, scaling_results: Dict[int, Dict]):
        """Validate that connection handling scales reasonably"""
        connection_counts = sorted(scaling_results.keys())
        success_rates = [scaling_results[c]["success_rate"] for c in connection_counts]
        
        # Success rate should not degrade significantly with scale
        for i, rate in enumerate(success_rates):
            min_acceptable = SCALABILITY_CONFIG["min_success_rate"] - (i * 0.02)  # Allow 2% degradation per level
            assert rate >= min_acceptable, \
                f"Success rate degraded too much at {connection_counts[i]} connections: {rate:.3f}"
        
        logger.info("Linear scaling validation passed")
