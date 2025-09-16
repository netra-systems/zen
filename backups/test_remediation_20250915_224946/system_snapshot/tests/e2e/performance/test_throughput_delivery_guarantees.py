"""
Test Suite: Delivery Guarantee Validation - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Data Reliability, Compliance
- Value Impact: Ensures zero message loss for critical enterprise operations
- Strategic/Revenue Impact: Required for financial/healthcare compliance contracts

This test validates delivery guarantees under various failure scenarios.
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Set
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.throughput_helpers import (
    E2E_TEST_CONFIG,
    LoadTestResults,
    create_test_message,
)
from tests.e2e.test_helpers.websocket_helpers import (
    test_websocket_test_context as websocket_test_context,
)

logger = logging.getLogger(__name__)

# Delivery guarantee test configuration
DELIVERY_CONFIG = {
    "message_count": 5000,
    "send_rate": 500,  # msg/sec
    "min_delivery_ratio": 0.999,  # 99.9%
    "max_duplicate_ratio": 0.001,  # 0.1%
    "connection_failure_rate": 0.1,  # 10%
    "retry_timeout": 30.0,
    "max_retries": 3
}

class DeliveryGuaranteeValidationTests:
    """Test delivery guarantees under various conditions"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_perfect_delivery_normal_conditions(self, throughput_client, high_volume_server):
        """Test delivery guarantees under normal operating conditions"""
        message_count = DELIVERY_CONFIG["message_count"]
        
        logger.info(f"Testing delivery guarantees with {message_count} messages")
        
        # Generate unique messages with tracking IDs
        messages = [self._create_tracked_message(i) for i in range(message_count)]
        sent_ids = {msg["tracking_id"] for msg in messages}
        
        # Send all messages
        results = await throughput_client.send_messages_with_tracking(
            messages=messages,
            rate_limit=DELIVERY_CONFIG["send_rate"]
        )
        
        # Receive responses with extended timeout
        responses = await throughput_client.receive_responses(
            expected_count=message_count,
            timeout=120.0
        )
        
        # Analyze delivery
        delivery_analysis = self._analyze_delivery(sent_ids, responses)
        
        # Perfect delivery assertions
        assert delivery_analysis["delivery_ratio"] >= DELIVERY_CONFIG["min_delivery_ratio"], \
            f"Delivery ratio below threshold: {delivery_analysis['delivery_ratio']:.4f}"
        
        assert delivery_analysis["duplicate_ratio"] <= DELIVERY_CONFIG["max_duplicate_ratio"], \
            f"Duplicate ratio above threshold: {delivery_analysis['duplicate_ratio']:.4f}"
        
        assert len(delivery_analysis["missing_ids"]) == 0, \
            f"Missing message IDs: {delivery_analysis['missing_ids'][:10]}"
        
        logger.info(f"Perfect delivery test passed: {delivery_analysis['delivery_ratio']:.4f} ratio")
    
    @pytest.mark.asyncio
    async def test_delivery_with_connection_failures(self, high_volume_server):
        """Test delivery guarantees with simulated connection failures"""
        message_count = DELIVERY_CONFIG["message_count"]
        failure_rate = DELIVERY_CONFIG["connection_failure_rate"]
        
        logger.info(f"Testing delivery with {failure_rate:.1%} connection failure rate")
        
        messages = [self._create_tracked_message(i) for i in range(message_count)]
        sent_ids = {msg["tracking_id"] for msg in messages}
        
        # Send with simulated failures
        delivery_results = await self._send_with_connection_failures(messages, failure_rate)
        
        # Analyze delivery despite failures
        delivery_analysis = self._analyze_delivery(sent_ids, delivery_results["responses"])
        
        # Allow slightly lower delivery ratio with failures but still high
        min_delivery_with_failures = 0.99  # 99%
        assert delivery_analysis["delivery_ratio"] >= min_delivery_with_failures, \
            f"Delivery ratio with failures too low: {delivery_analysis['delivery_ratio']:.4f}"
        
        # Should still have minimal duplicates
        assert delivery_analysis["duplicate_ratio"] <= DELIVERY_CONFIG["max_duplicate_ratio"], \
            f"Duplicate ratio too high with failures: {delivery_analysis['duplicate_ratio']:.4f}"
        
        logger.info(f"Delivery with failures test passed: {delivery_analysis['delivery_ratio']:.4f} ratio")
    
    @pytest.mark.asyncio
    async def test_at_least_once_delivery_semantics(self, throughput_client, high_volume_server):
        """Test at-least-once delivery semantics with retries"""
        message_count = 2000
        
        logger.info(f"Testing at-least-once delivery with {message_count} messages")
        
        messages = [self._create_tracked_message(i) for i in range(message_count)]
        sent_ids = {msg["tracking_id"] for msg in messages}
        
        # Send with retry mechanism
        delivery_results = await self._send_with_retries(messages, throughput_client)
        
        # For at-least-once, we expect >= 100% delivery (duplicates allowed)
        received_ids = set()
        duplicate_ids = set()
        
        for response in delivery_results["responses"]:
            original_msg = response.get("original_message", {})
            tracking_id = original_msg.get("tracking_id")
            
            if tracking_id:
                if tracking_id in received_ids:
                    duplicate_ids.add(tracking_id)
                else:
                    received_ids.add(tracking_id)
        
        # At-least-once guarantees
        delivery_ratio = len(received_ids) / len(sent_ids)
        assert delivery_ratio >= 0.999, \
            f"At-least-once delivery ratio too low: {delivery_ratio:.4f}"
        
        # Some duplicates are acceptable for at-least-once
        duplicate_ratio = len(duplicate_ids) / len(sent_ids)
        max_duplicate_for_retries = 0.05  # 5% duplicates acceptable
        assert duplicate_ratio <= max_duplicate_for_retries, \
            f"Duplicate ratio too high: {duplicate_ratio:.4f}"
        
        missing_ids = sent_ids - received_ids
        assert len(missing_ids) == 0, \
            f"Missing messages in at-least-once: {list(missing_ids)[:10]}"
        
        logger.info(f"At-least-once delivery passed: {delivery_ratio:.4f} delivery, "
                   f"{duplicate_ratio:.4f} duplicates")
    
    @pytest.mark.asyncio
    async def test_exactly_once_delivery_semantics(self, throughput_client, high_volume_server):
        """Test exactly-once delivery semantics (if supported)"""
        message_count = 3000
        
        logger.info(f"Testing exactly-once delivery with {message_count} messages")
        
        messages = [self._create_tracked_message(i) for i in range(message_count)]
        sent_ids = {msg["tracking_id"] for msg in messages}
        
        # Send with exactly-once configuration
        results = await throughput_client.send_messages_exactly_once(
            messages=messages,
            rate_limit=DELIVERY_CONFIG["send_rate"]
        )
        
        responses = await throughput_client.receive_responses(
            expected_count=message_count,
            timeout=150.0
        )
        
        delivery_analysis = self._analyze_delivery(sent_ids, responses)
        
        # Exactly-once requires perfect delivery with no duplicates
        assert delivery_analysis["delivery_ratio"] >= DELIVERY_CONFIG["min_delivery_ratio"], \
            f"Exactly-once delivery ratio too low: {delivery_analysis['delivery_ratio']:.4f}"
        
        assert delivery_analysis["duplicate_ratio"] == 0.0, \
            f"Duplicates found in exactly-once: {delivery_analysis['duplicate_ratio']:.4f}"
        
        assert len(delivery_analysis["missing_ids"]) == 0, \
            f"Missing messages in exactly-once: {delivery_analysis['missing_ids'][:10]}"
        
        logger.info(f"Exactly-once delivery passed: {delivery_analysis['delivery_ratio']:.4f} ratio")
    
    def _create_tracked_message(self, sequence: int) -> Dict[str, Any]:
        """Create message with unique tracking ID"""
        tracking_id = f"track_{sequence:06d}_{int(time.time() * 1000000) % 1000000}"
        
        return {
            "message_id": f"msg_{sequence:06d}",
            "tracking_id": tracking_id,
            "sequence": sequence,
            "timestamp": time.time(),
            "type": "delivery_test",
            "content": f"Delivery test message {sequence}",
            "metadata": {
                "test_type": "delivery_guarantee",
                "requires_ack": True
            }
        }
    
    def _analyze_delivery(self, sent_ids: Set[str], responses: List[Dict]) -> Dict[str, Any]:
        """Analyze delivery metrics from responses"""
        received_ids = []
        
        for response in responses:
            original_msg = response.get("original_message", {})
            tracking_id = original_msg.get("tracking_id")
            if tracking_id:
                received_ids.append(tracking_id)
        
        received_set = set(received_ids)
        duplicate_ids = [id for id in received_ids if received_ids.count(id) > 1]
        missing_ids = sent_ids - received_set
        
        return {
            "sent_count": len(sent_ids),
            "received_count": len(received_ids),
            "unique_received": len(received_set),
            "delivery_ratio": len(received_set) / len(sent_ids) if sent_ids else 0,
            "duplicate_count": len(duplicate_ids),
            "duplicate_ratio": len(duplicate_ids) / len(sent_ids) if sent_ids else 0,
            "missing_ids": list(missing_ids),
            "duplicate_ids": list(set(duplicate_ids))
        }
    
    async def _send_with_connection_failures(self, messages: List[Dict], 
                                           failure_rate: float) -> Dict[str, Any]:
        """Send messages with simulated connection failures"""
        responses = []
        failed_sends = []
        
        async with websocket_test_context(E2E_TEST_CONFIG["websocket_url"]) as websocket:
            for i, message in enumerate(messages):
                # Simulate connection failure
                if random.random() < failure_rate:
                    failed_sends.append(message)
                    # Simulate reconnection delay
                    await asyncio.sleep(0.1)
                    continue
                
                try:
                    await websocket.send(json.dumps(message))
                    # Try to receive response
                    response_json = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    responses.append(json.loads(response_json))
                except asyncio.TimeoutError:
                    failed_sends.append(message)
                except Exception as e:
                    logger.warning(f"Send failed for message {i}: {e}")
                    failed_sends.append(message)
        
        return {
            "responses": responses,
            "failed_sends": failed_sends,
            "failure_count": len(failed_sends)
        }
    
    async def _send_with_retries(self, messages: List[Dict], 
                               throughput_client) -> Dict[str, Any]:
        """Send messages with retry mechanism"""
        responses = []
        retry_queue = messages.copy()
        retry_count = 0
        max_retries = DELIVERY_CONFIG["max_retries"]
        
        while retry_queue and retry_count < max_retries:
            current_batch = retry_queue.copy()
            retry_queue.clear()
            
            logger.info(f"Retry attempt {retry_count + 1}: {len(current_batch)} messages")
            
            # Send current batch
            batch_results = await throughput_client.send_messages_with_tracking(
                messages=current_batch,
                rate_limit=DELIVERY_CONFIG["send_rate"]
            )
            
            # Try to receive responses
            try:
                batch_responses = await throughput_client.receive_responses(
                    expected_count=len(current_batch),
                    timeout=60.0
                )
                responses.extend(batch_responses)
            except asyncio.TimeoutError:
                # Add unconfirmed messages back to retry queue
                confirmed_ids = {
                    resp.get("original_message", {}).get("tracking_id")
                    for resp in batch_responses
                }
                
                for msg in current_batch:
                    if msg["tracking_id"] not in confirmed_ids:
                        retry_queue.append(msg)
            
            retry_count += 1
            if retry_queue:
                await asyncio.sleep(2.0)  # Wait before retry
        
        return {
            "responses": responses,
            "final_retry_queue": retry_queue,
            "retry_attempts": retry_count
        }
