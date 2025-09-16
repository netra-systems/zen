"""
Test Suite: Message Ordering Preservation - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise/Mid  
- Business Goal: Data Integrity, Platform Reliability
- Value Impact: Ensures critical message ordering for enterprise workflows
- Strategic/Revenue Impact: Essential for financial/audit compliance requirements

This test validates that message ordering is preserved under high load.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.throughput_helpers import (
    E2E_TEST_CONFIG,
    LoadTestResults,
    create_test_message,
)
from tests.e2e.test_helpers.websocket_helpers import (
    validate_message_ordering,
)

logger = logging.getLogger(__name__)

# Message ordering test configuration
ORDERING_CONFIG = {
    "single_connection_messages": 10000,
    "concurrent_clients": 10,
    "messages_per_client": 1000,
    "send_rate_limit": 1000,  # msg/sec
    "concurrent_rate_limit": 100,  # msg/sec per client
    "max_ordering_violations": 0,
    "min_delivery_ratio": 0.99,
    "concurrent_delivery_ratio": 0.95
}

class MessageOrderingPreservationTests:
    """Test message ordering preservation under high load"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(180)
    async def test_single_connection_ordering(self, throughput_client, high_volume_server):
        """Ensure strict message ordering with single connection flood test"""
        message_count = ORDERING_CONFIG["single_connection_messages"]
        
        logger.info(f"Testing ordering with {message_count} sequential messages")
        
        # Generate sequentially numbered messages
        messages = [self._create_ordered_message(i) for i in range(message_count)]
        
        start_time = time.perf_counter()
        results = await throughput_client.send_messages_sequential(
            messages=messages,
            rate_limit=ORDERING_CONFIG["send_rate_limit"]
        )
        send_duration = time.perf_counter() - start_time
        
        responses = await throughput_client.receive_responses(
            expected_count=message_count,
            timeout=120.0
        )
        
        # Validate ordering
        ordering_result = self._validate_sequence_ordering(messages, responses)
        
        # Assertions
        assert ordering_result["violations"] == 0, \
            f"Ordering violations detected: {ordering_result['violation_details']}"
        
        assert ordering_result["missing_count"] == 0, \
            f"Missing messages: {ordering_result['missing_sequences']}"
        
        delivery_ratio = len(responses) / message_count
        assert delivery_ratio >= ORDERING_CONFIG["min_delivery_ratio"], \
            f"Delivery ratio too low: {delivery_ratio:.3f}"
        
        logger.info(f"Single connection ordering test passed: {delivery_ratio:.3f} delivery ratio")
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_ordering(self, high_volume_server):
        """Test ordering preservation with multiple concurrent connections"""
        concurrent_clients = ORDERING_CONFIG["concurrent_clients"]
        messages_per_client = ORDERING_CONFIG["messages_per_client"]
        
        logger.info(f"Testing ordering with {concurrent_clients} concurrent clients")
        
        client_results = await self._execute_concurrent_ordering_test()
        
        # Validate each client's ordering independently
        for client_id, result in client_results.items():
            ordering_result = self._validate_sequence_ordering(
                result["sent_messages"], 
                result["received_responses"]
            )
            
            assert ordering_result["violations"] == 0, \
                f"Client {client_id} ordering violations: {ordering_result['violation_details']}"
            
            client_delivery = len(result["received_responses"]) / len(result["sent_messages"])
            assert client_delivery >= ORDERING_CONFIG["concurrent_delivery_ratio"], \
                f"Client {client_id} delivery ratio too low: {client_delivery:.3f}"
        
        # Calculate overall metrics
        total_sent = sum(len(r["sent_messages"]) for r in client_results.values())
        total_received = sum(len(r["received_responses"]) for r in client_results.values())
        overall_delivery = total_received / total_sent if total_sent > 0 else 0
        
        assert overall_delivery >= ORDERING_CONFIG["concurrent_delivery_ratio"], \
            f"Overall concurrent delivery ratio too low: {overall_delivery:.3f}"
        
        logger.info(f"Concurrent ordering test passed: {overall_delivery:.3f} overall delivery")
    
    @pytest.mark.asyncio
    async def test_ordering_under_backpressure(self, throughput_client, high_volume_server):
        """Test ordering preservation when system is under backpressure"""
        # Create backpressure by sending at very high rate
        burst_rate = 5000  # High rate to trigger backpressure
        message_count = 5000
        
        logger.info(f"Testing ordering under backpressure at {burst_rate} msg/sec")
        
        messages = [self._create_ordered_message(i) for i in range(message_count)]
        
        # Send at high rate to trigger backpressure
        results = await throughput_client.send_messages_sequential(
            messages=messages,
            rate_limit=burst_rate
        )
        
        # Allow extra time for backpressure recovery
        responses = await throughput_client.receive_responses(
            expected_count=message_count,
            timeout=180.0
        )
        
        ordering_result = self._validate_sequence_ordering(messages, responses)
        
        # Under backpressure, allow some delivery loss but no ordering violations
        assert ordering_result["violations"] == 0, \
            f"Ordering violations under backpressure: {ordering_result['violation_details']}"
        
        delivery_ratio = len(responses) / message_count
        # More lenient delivery ratio under backpressure
        assert delivery_ratio >= 0.8, \
            f"Delivery ratio too low under backpressure: {delivery_ratio:.3f}"
        
        logger.info(f"Backpressure ordering test passed: {delivery_ratio:.3f} delivery ratio")
    
    async def _execute_concurrent_ordering_test(self) -> Dict[str, Any]:
        """Execute concurrent client ordering test"""
        from tests.e2e.test_helpers.websocket_helpers import (
            test_websocket_test_context as websocket_test_context,
        )
        
        concurrent_clients = ORDERING_CONFIG["concurrent_clients"]
        messages_per_client = ORDERING_CONFIG["messages_per_client"]
        
        async def single_client_test(client_id: int) -> Dict[str, Any]:
            """Single client ordering test"""
            messages = [
                self._create_ordered_message(i, client_prefix=f"client_{client_id}")
                for i in range(messages_per_client)
            ]
            
            async with websocket_test_context(E2E_TEST_CONFIG["websocket_url"]) as websocket:
                # Send messages sequentially
                for msg in messages:
                    await websocket.send(json.dumps(msg))
                
                # Receive responses
                responses = []
                for _ in range(messages_per_client):
                    try:
                        response_json = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        responses.append(json.loads(response_json))
                    except asyncio.TimeoutError:
                        break
                
                return {
                    "client_id": client_id,
                    "sent_messages": messages,
                    "received_responses": responses
                }
        
        # Run all clients concurrently
        tasks = [single_client_test(i) for i in range(concurrent_clients)]
        results = await asyncio.gather(*tasks)
        
        return {result["client_id"]: result for result in results}
    
    def _create_ordered_message(self, sequence: int, client_prefix: str = "main") -> Dict[str, Any]:
        """Create message with sequence ordering information"""
        return {
            "message_id": f"{client_prefix}_seq_{sequence:06d}",
            "sequence": sequence,
            "timestamp": time.time(),
            "type": "ordering_test",
            "content": f"Message {sequence}",
            "metadata": {
                "client_prefix": client_prefix,
                "test_type": "ordering"
            }
        }
    
    def _validate_sequence_ordering(self, sent_messages: List[Dict], 
                                   received_responses: List[Dict]) -> Dict[str, Any]:
        """Validate that message sequence ordering is preserved"""
        # Extract sequence numbers from sent messages
        sent_sequences = [msg["sequence"] for msg in sent_messages]
        
        # Extract sequence numbers from responses
        received_sequences = []
        for response in received_responses:
            original_msg = response.get("original_message", {})
            if "sequence" in original_msg:
                received_sequences.append(original_msg["sequence"])
        
        # Find violations
        violations = []
        missing_sequences = []
        
        # Check for missing sequences
        sent_set = set(sent_sequences)
        received_set = set(received_sequences)
        missing_sequences = list(sent_set - received_set)
        
        # Check for ordering violations
        prev_sequence = -1
        for seq in received_sequences:
            if seq <= prev_sequence:
                violations.append({
                    "sequence": seq,
                    "previous": prev_sequence,
                    "position": len(violations)
                })
            prev_sequence = seq
        
        return {
            "violations": len(violations),
            "violation_details": violations,
            "missing_count": len(missing_sequences),
            "missing_sequences": missing_sequences,
            "sent_count": len(sent_sequences),
            "received_count": len(received_sequences)
        }
