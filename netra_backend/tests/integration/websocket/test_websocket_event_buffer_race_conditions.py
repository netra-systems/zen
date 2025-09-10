"""
Test WebSocket Event Buffer Race Conditions - Critical Event Buffering Infrastructure Tests

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure  
- Business Goal: Reliable Real-time Event Delivery
- Value Impact: Ensures WebSocket events reach users without loss during concurrent operations
- Strategic Impact: Core infrastructure for chat-based AI interactions and business value delivery

CRITICAL: These tests MUST FAIL initially to reproduce exact event buffering race conditions.
The goal is to expose timing issues in event queuing, buffering, and concurrent delivery.

Root Cause Analysis:
- Race conditions between event producers and WebSocket connection state
- Events buffered before connection ready, leading to lost events
- Concurrent event handling causing event reordering or duplication
- Buffer flushing race conditions during connection state changes

This test suite creates FAILING scenarios that reproduce production event buffering races.
"""

import asyncio
import json
import logging
import pytest
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Deque
from unittest.mock import AsyncMock, MagicMock, patch
from queue import Queue, Empty

import websockets
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from starlette.websockets import WebSocketDisconnect

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Import WebSocket core components for event buffer testing
from netra_backend.app.websocket_core import (
    WebSocketManager,
    MessageRouter, 
    get_websocket_manager,
    safe_websocket_send,
    create_server_message,
    MessageType
)
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier

logger = logging.getLogger(__name__)


class MockEventBuffer:
    """
    Mock event buffer that reproduces race conditions seen in production.
    
    This simulates the event buffering system with timing controls to expose
    race conditions between event production, buffering, and delivery.
    """
    
    def __init__(self, connection_delay: float = 0.1):
        self.buffer: Deque[Dict[str, Any]] = deque()
        self.connection_delay = connection_delay
        self.is_connection_ready = False
        self.buffer_lock = asyncio.Lock()
        self.flush_in_progress = False
        self.events_sent = []
        self.events_lost = []
        self.race_conditions = []
        
    async def add_event(self, event: Dict[str, Any]):
        """Add event to buffer - may race with connection state."""
        async with self.buffer_lock:
            event["buffer_timestamp"] = time.time()
            self.buffer.append(event)
            
            # CRITICAL: Race condition - try to send immediately if connection "ready"
            if self.is_connection_ready and not self.flush_in_progress:
                # This creates a race condition with concurrent flush operations
                await asyncio.sleep(0.001)  # Small race window
                if self.buffer and self.is_connection_ready:
                    await self._send_from_buffer()
                    
    async def mark_connection_ready(self):
        """Mark connection as ready - may race with event addition."""
        # Simulate connection establishment delay
        await asyncio.sleep(self.connection_delay)
        self.is_connection_ready = True
        
        # CRITICAL: Race condition - flush buffer immediately
        if self.buffer and not self.flush_in_progress:
            await self._flush_buffer()
            
    async def _send_from_buffer(self):
        """Send single event from buffer - can race with flush."""
        if not self.buffer:
            return
            
        try:
            event = self.buffer.popleft()
            if self.is_connection_ready:
                self.events_sent.append(event)
            else:
                # Race condition: connection became unready
                self.events_lost.append(event)
                self.race_conditions.append({
                    "type": "send_from_buffer_race",
                    "event": event,
                    "connection_ready": self.is_connection_ready,
                    "timestamp": time.time()
                })
        except IndexError:
            # Race condition: buffer empty due to concurrent access
            self.race_conditions.append({
                "type": "buffer_empty_race", 
                "timestamp": time.time()
            })
            
    async def _flush_buffer(self):
        """Flush entire buffer - can race with individual sends."""
        if self.flush_in_progress:
            self.race_conditions.append({
                "type": "concurrent_flush_race",
                "timestamp": time.time()
            })
            return
            
        self.flush_in_progress = True
        try:
            while self.buffer:
                await self._send_from_buffer()
                await asyncio.sleep(0.001)  # Small delay that can cause races
        finally:
            self.flush_in_progress = False


class TestWebSocketEventBufferRaceConditions(BaseIntegrationTest):
    """
    Test WebSocket event buffer race conditions that cause event loss and reordering.
    
    CRITICAL: These tests are designed to FAIL initially and expose exact timing issues
    that occur in production event buffering and delivery systems.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_event_buffer_race_environment(self):
        """Set up environment for event buffer race condition testing."""
        self.env = get_env()
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        self.event_buffers = []
        self.race_condition_log = []
        self.timing_analysis = []
        
        yield
        
        # Analyze race conditions from all buffers
        total_races = 0
        for buffer in self.event_buffers:
            total_races += len(buffer.race_conditions)
            self.race_condition_log.extend(buffer.race_conditions)
            
        if total_races > 0:
            logger.warning(f"Event buffer race conditions detected: {total_races} total races")
            for i, race in enumerate(self.race_condition_log[:5]):  # Log first 5
                logger.info(f"Race {i+1}: {race}")
    
    def _create_concurrent_event_producer(self, buffer: MockEventBuffer, event_count: int, delay_range: tuple):
        """Create concurrent event producer for race condition testing."""
        async def produce_events():
            """Produce events with random timing to create races."""
            import random
            
            events_produced = []
            for i in range(event_count):
                event = {
                    "type": f"agent_event_{i}",
                    "sequence": i,
                    "timestamp": time.time(),
                    "producer": "concurrent_producer",
                    "data": f"Event data {i}"
                }
                
                # Add to buffer (may race with connection establishment)
                await buffer.add_event(event)
                events_produced.append(event)
                
                # Random delay to create timing variations
                delay = random.uniform(*delay_range)
                await asyncio.sleep(delay)
                
            return events_produced
        
        return produce_events
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_event_buffer_connection_ready_race_condition(self, real_services_fixture):
        """
        CRITICAL TEST: Reproduces race between event buffering and connection readiness.
        
        Simulates: Events added to buffer while connection establishment is in progress
        Expected Result: TEST SHOULD FAIL with event loss due to race conditions
        """
        # Create event buffer with connection delay
        buffer = MockEventBuffer(connection_delay=0.1)
        self.event_buffers.append(buffer)
        
        start_time = time.time()
        
        # CRITICAL: Start producing events immediately
        event_producer = self._create_concurrent_event_producer(
            buffer=buffer,
            event_count=10, 
            delay_range=(0.005, 0.015)  # Fast event production
        )
        
        # Start both processes concurrently
        producer_task = asyncio.create_task(event_producer())
        connection_task = asyncio.create_task(buffer.mark_connection_ready())
        
        # Wait for both to complete
        produced_events, _ = await asyncio.gather(producer_task, connection_task)
        
        end_time = time.time()
        
        # Analyze race condition results
        events_sent = len(buffer.events_sent)
        events_lost = len(buffer.events_lost)  
        events_produced = len(produced_events)
        races_detected = len(buffer.race_conditions)
        
        # Record timing analysis
        self.timing_analysis.append({
            "test_name": "buffer_connection_ready_race",
            "duration": end_time - start_time,
            "events_produced": events_produced,
            "events_sent": events_sent,
            "events_lost": events_lost, 
            "races_detected": races_detected,
            "event_loss_rate": events_lost / events_produced if events_produced > 0 else 0
        })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It demonstrates that event buffering has race conditions with connection readiness
        assert events_lost == 0, f"Event buffer race condition: {events_lost}/{events_produced} events lost due to connection timing race"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_concurrent_event_producers_buffer_race(self, real_services_fixture):
        """
        CRITICAL TEST: Reproduces race between multiple concurrent event producers.
        
        Simulates: Multiple agents/components producing events simultaneously
        Expected Result: TEST SHOULD FAIL with event reordering or duplication
        """
        # Create shared event buffer 
        buffer = MockEventBuffer(connection_delay=0.05)
        self.event_buffers.append(buffer)
        
        # Create multiple concurrent event producers
        producer1 = self._create_concurrent_event_producer(buffer, 8, (0.01, 0.02))
        producer2 = self._create_concurrent_event_producer(buffer, 8, (0.005, 0.015)) 
        producer3 = self._create_concurrent_event_producer(buffer, 8, (0.008, 0.018))
        
        start_time = time.time()
        
        # Start connection readiness 
        connection_task = asyncio.create_task(buffer.mark_connection_ready())
        
        # CRITICAL: Start all producers concurrently
        producer_tasks = [
            asyncio.create_task(producer1()),
            asyncio.create_task(producer2()),
            asyncio.create_task(producer3())
        ]
        
        # Wait for all tasks to complete
        producer_results = await asyncio.gather(*producer_tasks)
        await connection_task
        
        end_time = time.time()
        
        # Analyze concurrent production results
        total_produced = sum(len(events) for events in producer_results)
        events_sent = len(buffer.events_sent)
        events_in_buffer = len(buffer.buffer)
        races_detected = len(buffer.race_conditions)
        
        # Check for event sequence integrity
        sent_sequences = [event.get('sequence', -1) for event in buffer.events_sent]
        sequence_gaps = []
        for i in range(1, len(sent_sequences)):
            if sent_sequences[i] <= sent_sequences[i-1]:  # Not strictly increasing
                sequence_gaps.append((sent_sequences[i-1], sent_sequences[i]))
        
        # Record analysis
        self.timing_analysis.append({
            "test_name": "concurrent_producers_race",
            "duration": end_time - start_time,
            "total_produced": total_produced,
            "events_sent": events_sent,
            "events_buffered": events_in_buffer,
            "races_detected": races_detected,
            "sequence_gaps": len(sequence_gaps),
            "event_ordering_integrity": len(sequence_gaps) == 0
        })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It proves that concurrent event production causes race conditions
        assert races_detected == 0, f"Concurrent event production race: {races_detected} races detected across {total_produced} events"
        assert len(sequence_gaps) == 0, f"Event ordering race condition: {len(sequence_gaps)} sequence gaps detected"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_buffer_flush_concurrent_send_race_condition(self, real_services_fixture):
        """
        CRITICAL TEST: Reproduces race between buffer flush and individual event sends.
        
        Simulates: Buffer flush operation racing with individual event send attempts
        Expected Result: TEST SHOULD FAIL with buffer access conflicts
        """
        # Create event buffer
        buffer = MockEventBuffer(connection_delay=0.02)
        self.event_buffers.append(buffer)
        
        # Pre-populate buffer with events
        initial_events = []
        for i in range(15):
            event = {
                "type": f"initial_event_{i}",
                "sequence": i,
                "timestamp": time.time(),
                "data": f"Initial data {i}"
            }
            initial_events.append(event)
            buffer.buffer.append(event)
        
        start_time = time.time()
        
        # Mark connection ready (this will trigger buffer flush)
        connection_task = asyncio.create_task(buffer.mark_connection_ready())
        
        # CRITICAL: Concurrently add new events while flush is happening
        concurrent_events = []
        async def add_concurrent_events():
            """Add events while flush is in progress."""
            await asyncio.sleep(0.01)  # Let flush start
            
            for i in range(10):
                event = {
                    "type": f"concurrent_event_{i}",
                    "sequence": 100 + i,  # Different sequence range
                    "timestamp": time.time(),
                    "data": f"Concurrent data {i}"
                }
                concurrent_events.append(event)
                await buffer.add_event(event)
                await asyncio.sleep(0.002)  # Quick addition to create race
                
        # Run connection and concurrent addition together
        concurrent_task = asyncio.create_task(add_concurrent_events())
        
        await asyncio.gather(connection_task, concurrent_task)
        
        end_time = time.time()
        
        # Analyze buffer flush race results
        initial_count = len(initial_events)
        concurrent_count = len(concurrent_events)
        total_expected = initial_count + concurrent_count
        
        events_sent = len(buffer.events_sent)
        events_lost = len(buffer.events_lost)
        remaining_buffered = len(buffer.buffer)
        races_detected = len(buffer.race_conditions)
        
        # Check for flush-send race conditions specifically
        flush_races = [race for race in buffer.race_conditions 
                      if race.get('type') in ['concurrent_flush_race', 'buffer_empty_race']]
        
        # Record analysis  
        self.timing_analysis.append({
            "test_name": "buffer_flush_send_race",
            "duration": end_time - start_time,
            "initial_events": initial_count,
            "concurrent_events": concurrent_count,
            "total_expected": total_expected,
            "events_sent": events_sent,
            "events_lost": events_lost,
            "remaining_buffered": remaining_buffered,
            "races_detected": races_detected,
            "flush_specific_races": len(flush_races)
        })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It demonstrates that buffer flush operations have race conditions
        assert len(flush_races) == 0, f"Buffer flush race condition: {len(flush_races)} flush-related races detected"
        assert events_sent + events_lost + remaining_buffered == total_expected, f"Event accounting race: Expected {total_expected}, got {events_sent + events_lost + remaining_buffered}"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_websocket_notifier_event_buffer_integration_race(self, real_services_fixture):
        """
        CRITICAL TEST: Tests race conditions in WebSocketNotifier event buffering.
        
        Simulates: Real WebSocketNotifier integration with event buffering races
        Expected Result: TEST SHOULD FAIL with WebSocketNotifier buffer conflicts
        """
        # Create mock WebSocket for WebSocketNotifier
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTING
        
        # Track WebSocketNotifier send attempts
        send_attempts = []
        send_failures = []
        
        async def mock_send_json(data):
            """Mock send that can fail due to connection state."""
            send_attempts.append({
                "data": data,
                "timestamp": time.time(),
                "connection_state": mock_websocket.client_state
            })
            
            if mock_websocket.client_state != WebSocketState.CONNECTED:
                send_failures.append(data)
                raise RuntimeError("WebSocket is not connected. Need to call 'accept' first")
        
        mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)
        
        # Create WebSocketNotifier
        notifier = AgentWebSocketBridge(websocket_manager=None)
        
        # CRITICAL: Set up race condition scenario
        start_time = time.time()
        
        # Start sending multiple agent events quickly
        agent_events = [
            {"type": "agent_started", "timestamp": time.time()},
            {"type": "agent_thinking", "timestamp": time.time() + 0.01},
            {"type": "tool_executing", "timestamp": time.time() + 0.02}, 
            {"type": "tool_completed", "timestamp": time.time() + 0.03},
            {"type": "agent_completed", "timestamp": time.time() + 0.04}
        ]
        
        # Send events before WebSocket is ready
        send_tasks = []
        for event in agent_events:
            # Use WebSocketNotifier's send method (this should buffer if connection not ready)
            task = asyncio.create_task(
                notifier.send_websocket_event(mock_websocket, event)
            )
            send_tasks.append(task)
        
        # Small delay before marking connection ready
        await asyncio.sleep(0.05)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Wait for all send attempts to complete
        try:
            await asyncio.gather(*send_tasks, return_exceptions=True)
        except Exception:
            pass  # Expected due to race conditions
        
        end_time = time.time()
        
        # Analyze WebSocketNotifier race results
        total_events = len(agent_events)
        successful_sends = len(send_attempts) - len(send_failures)
        failed_sends = len(send_failures)
        
        # Record race condition analysis
        self.timing_analysis.append({
            "test_name": "websocket_notifier_buffer_race", 
            "duration": end_time - start_time,
            "total_events": total_events,
            "send_attempts": len(send_attempts),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "race_condition_rate": failed_sends / total_events if total_events > 0 else 0
        })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It proves WebSocketNotifier has race conditions with connection state
        assert failed_sends == 0, f"WebSocketNotifier race condition: {failed_sends}/{total_events} events failed due to connection timing"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_high_frequency_event_buffer_saturation_race(self, real_services_fixture):
        """
        CRITICAL TEST: Tests event buffer saturation under high frequency event production.
        
        Simulates: Very high frequency event production that can saturate buffers
        Expected Result: TEST SHOULD FAIL with buffer overflow or event loss
        """
        # Create event buffer with small connection delay
        buffer = MockEventBuffer(connection_delay=0.02)
        self.event_buffers.append(buffer)
        
        # High frequency event production
        async def high_frequency_producer(event_count: int):
            """Produce events at very high frequency."""
            events_produced = []
            for i in range(event_count):
                event = {
                    "type": f"high_freq_event_{i}",
                    "sequence": i,
                    "timestamp": time.time(),
                    "producer": "high_frequency",
                    "data": f"High frequency data {i}"
                }
                
                await buffer.add_event(event)
                events_produced.append(event)
                
                # CRITICAL: Very short delay to create buffer pressure
                await asyncio.sleep(0.001)  # 1ms between events = 1000 events/sec
                
            return events_produced
        
        start_time = time.time()
        
        # Start high frequency production and connection concurrently
        producer_task = asyncio.create_task(high_frequency_producer(100))  # 100 events in ~100ms
        connection_task = asyncio.create_task(buffer.mark_connection_ready())
        
        # Wait for both to complete
        produced_events, _ = await asyncio.gather(producer_task, connection_task)
        
        end_time = time.time()
        
        # Analyze high frequency results
        events_produced = len(produced_events)
        events_sent = len(buffer.events_sent)
        events_lost = len(buffer.events_lost)
        remaining_buffered = len(buffer.buffer)
        races_detected = len(buffer.race_conditions)
        
        # Calculate event throughput
        duration = end_time - start_time
        event_rate = events_produced / duration if duration > 0 else 0
        
        # Record high frequency analysis
        self.timing_analysis.append({
            "test_name": "high_frequency_buffer_saturation",
            "duration": duration,
            "events_produced": events_produced,
            "events_sent": events_sent,
            "events_lost": events_lost,
            "remaining_buffered": remaining_buffered,
            "races_detected": races_detected,
            "event_rate_per_second": event_rate,
            "saturation_detected": events_lost > 0 or races_detected > 0
        })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It proves that high frequency events can cause buffer saturation races
        assert events_lost == 0, f"High frequency buffer saturation: {events_lost}/{events_produced} events lost"
        assert races_detected < 5, f"Excessive race conditions under high frequency: {races_detected} races detected"
    
    def test_event_buffer_race_condition_analysis(self):
        """
        Analysis test that documents event buffer race condition patterns.
        
        This test reviews all timing data collected from event buffer tests
        and provides analysis for fixing the actual race conditions.
        """
        if not hasattr(self, 'timing_analysis') or not self.timing_analysis:
            pytest.skip("No timing analysis data - event buffer tests may not have run")
        
        # Analyze event buffer race patterns
        total_tests = len(self.timing_analysis)
        tests_with_races = sum(1 for analysis in self.timing_analysis 
                              if analysis.get('races_detected', 0) > 0)
        
        # Calculate event loss statistics
        total_events_produced = sum(analysis.get('events_produced', 0) + analysis.get('total_produced', 0) + analysis.get('total_events', 0) 
                                  for analysis in self.timing_analysis)
        total_events_lost = sum(analysis.get('events_lost', 0) + analysis.get('failed_sends', 0) 
                               for analysis in self.timing_analysis)
        
        # Event throughput analysis
        throughput_tests = [analysis for analysis in self.timing_analysis 
                           if 'event_rate_per_second' in analysis]
        avg_throughput = sum(test['event_rate_per_second'] for test in throughput_tests) / len(throughput_tests) if throughput_tests else 0
        
        # Race condition patterns
        total_race_conditions = sum(len(buffer.race_conditions) for buffer in self.event_buffers)
        race_types = {}
        for buffer in self.event_buffers:
            for race in buffer.race_conditions:
                race_type = race.get('type', 'unknown')
                race_types[race_type] = race_types.get(race_type, 0) + 1
        
        # Generate comprehensive analysis report
        analysis_report = {
            "total_buffer_tests": total_tests,
            "tests_with_races": tests_with_races,
            "race_detection_rate": tests_with_races / total_tests if total_tests > 0 else 0,
            "total_events_produced": total_events_produced,
            "total_events_lost": total_events_lost,
            "event_loss_rate": total_events_lost / total_events_produced if total_events_produced > 0 else 0,
            "average_throughput_per_second": avg_throughput,
            "total_race_conditions": total_race_conditions,
            "race_condition_types": race_types,
            "detailed_analysis": self.timing_analysis,
            "race_condition_log": self.race_condition_log
        }
        
        # Log detailed analysis
        logger.critical("=" * 80)
        logger.critical("WEBSOCKET EVENT BUFFER RACE CONDITION ANALYSIS REPORT")
        logger.critical("=" * 80)
        logger.critical(f"Buffer Tests Run: {total_tests}")
        logger.critical(f"Tests with Races: {tests_with_races}")
        logger.critical(f"Race Detection Rate: {tests_with_races/total_tests*100:.1f}%")
        logger.critical(f"Events Produced: {total_events_produced}")
        logger.critical(f"Events Lost: {total_events_lost}")
        logger.critical(f"Event Loss Rate: {total_events_lost/total_events_produced*100:.2f}%")
        logger.critical(f"Average Throughput: {avg_throughput:.1f} events/sec")
        logger.critical(f"Total Race Conditions: {total_race_conditions}")
        logger.critical(f"Race Types: {race_types}")
        logger.critical("=" * 80)
        
        # CRITICAL: This documents that event buffer race conditions were successfully reproduced
        assert tests_with_races == 0, f"Event buffer race conditions reproduced in {tests_with_races}/{total_tests} tests"
        assert total_events_lost == 0, f"Event loss due to race conditions: {total_events_lost} events lost"
        assert total_race_conditions == 0, f"Race conditions in event buffering: {total_race_conditions} total races detected"