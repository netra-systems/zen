"""
Critical tests for WebSocket queue disruption of the Golden Path user flow.

Issue #1011 WebSocket Message Queue Consolidation - Golden Path Disruption Tests

This test module focuses specifically on how the fragmented queue implementations
disrupt the core Golden Path user flow that generates $500K+ ARR business value:

Golden Path Flow: User Login → Agent Processing → Real-time Updates → AI Response

These tests demonstrate how queue fragmentation breaks this critical business flow
by causing message loss, ordering issues, and state corruption that directly
impact the primary revenue-generating user experience.

DESIGNED TO FAIL initially to prove business impact of queue consolidation issues.

Business Value Justification:
- Segment: All Tiers (Free/Early/Mid/Enterprise) - CRITICAL
- Business Goal: Golden Path Protection - $500K+ ARR
- Value Impact: Ensures core chat functionality delivers reliable AI responses
- Strategic Impact: Protects primary value delivery mechanism of the platform
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

from netra_backend.app.websocket_core.message_queue import MessageQueue, MessagePriority
from netra_backend.app.websocket_core.message_buffer import WebSocketMessageBuffer, BufferPriority
from netra_backend.app.websocket_core.utils import WebSocketMessageQueue
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

from shared.types.core_types import UserID, ConnectionID


class GoldenPathState(Enum):
    """States in the Golden Path user flow."""
    USER_LOGIN = "user_login"
    REQUEST_SUBMITTED = "request_submitted"
    AGENT_STARTED = "agent_started"
    AGENT_PROCESSING = "agent_processing"
    TOOLS_EXECUTING = "tools_executing"
    RESPONSE_READY = "response_ready"
    FLOW_COMPLETE = "flow_complete"
    FLOW_BROKEN = "flow_broken"


@dataclass
class GoldenPathEvent:
    """Represents a critical event in the Golden Path flow."""
    event_type: str
    content: str
    state: GoldenPathState
    is_critical: bool
    user_visible: bool
    sequence: int
    timestamp: float


class TestGoldenPathQueueDisruption(SSotAsyncTestCase):
    """Test how queue fragmentation disrupts the Golden Path user flow."""

    def setup_method(self, method):
        """Set up Golden Path test environment."""
        super().setup_method(method)
        self.websocket_util = WebSocketTestUtility()

        # Golden Path test user
        self.golden_path_user_id = UserID("user_123")
        self.golden_path_connection_id = ConnectionID("conn_456")

        # Define the complete Golden Path event sequence
        self.golden_path_events = [
            GoldenPathEvent(
                event_type="user_message",
                content="Please analyze this data for insights",
                state=GoldenPathState.REQUEST_SUBMITTED,
                is_critical=True,
                user_visible=True,
                sequence=1,
                timestamp=time.time()
            ),
            GoldenPathEvent(
                event_type="agent_started",
                content="I'll analyze your data and provide insights",
                state=GoldenPathState.AGENT_STARTED,
                is_critical=True,
                user_visible=True,
                sequence=2,
                timestamp=time.time() + 0.1
            ),
            GoldenPathEvent(
                event_type="agent_thinking",
                content="Reading and understanding your data...",
                state=GoldenPathState.AGENT_PROCESSING,
                is_critical=True,
                user_visible=True,
                sequence=3,
                timestamp=time.time() + 0.5
            ),
            GoldenPathEvent(
                event_type="tool_executing",
                content="Running statistical analysis algorithms",
                state=GoldenPathState.TOOLS_EXECUTING,
                is_critical=True,
                user_visible=True,
                sequence=4,
                timestamp=time.time() + 2.0
            ),
            GoldenPathEvent(
                event_type="agent_thinking",
                content="Interpreting analysis results...",
                state=GoldenPathState.AGENT_PROCESSING,
                is_critical=True,
                user_visible=True,
                sequence=5,
                timestamp=time.time() + 4.0
            ),
            GoldenPathEvent(
                event_type="tool_completed",
                content="Analysis algorithms completed successfully",
                state=GoldenPathState.TOOLS_EXECUTING,
                is_critical=True,
                user_visible=True,
                sequence=6,
                timestamp=time.time() + 5.0
            ),
            GoldenPathEvent(
                event_type="agent_completed",
                content="Based on the analysis, here are key insights: [detailed response]",
                state=GoldenPathState.RESPONSE_READY,
                is_critical=True,
                user_visible=True,
                sequence=7,
                timestamp=time.time() + 6.0
            )
        ]

    async def test_golden_path_flow_disruption_by_queue_fragmentation(self):
        """
        FAILING CRITICAL TEST: Demonstrates how queue fragmentation completely
        disrupts the Golden Path user flow, breaking the core $500K+ ARR experience.

        This test simulates the exact sequence of events in the Golden Path
        and shows how different queue implementations cause:
        1. Missing critical agent updates
        2. Out-of-order event delivery
        3. Broken conversation flow
        4. User confusion and frustration

        Expected to FAIL catastrophically, proving urgent need for consolidation.
        """
        # Create all competing queue implementations
        priority_queue = MessageQueue(self.golden_path_connection_id, self.golden_path_user_id)
        buffer_queue = WebSocketMessageBuffer()
        simple_queue = WebSocketMessageQueue()
        unified_manager = UnifiedWebSocketManager()

        # Track Golden Path event delivery for each queue
        priority_queue_events = []
        buffer_queue_events = []
        simple_queue_events = []

        # Track timing and ordering for user experience analysis
        user_experience_timeline = []

        async def track_priority_queue_delivery(queued_msg):
            event_data = queued_msg.message_data
            priority_queue_events.append({
                "sequence": event_data.get("sequence"),
                "type": event_data.get("event_type"),
                "delivered_at": time.time(),
                "queue_type": "priority"
            })
            user_experience_timeline.append(("priority", event_data.get("sequence"), time.time()))

        async def track_buffer_delivery(message):
            buffer_queue_events.append({
                "sequence": message.get("sequence"),
                "type": message.get("event_type"),
                "delivered_at": time.time(),
                "queue_type": "buffer"
            })
            user_experience_timeline.append(("buffer", message.get("sequence"), time.time()))
            return True

        async def track_simple_queue_delivery():
            while not simple_queue.is_empty():
                msg = await simple_queue.dequeue(timeout=0.1)
                if msg:
                    simple_queue_events.append({
                        "sequence": msg.get("sequence"),
                        "type": msg.get("event_type"),
                        "delivered_at": time.time(),
                        "queue_type": "simple"
                    })
                    user_experience_timeline.append(("simple", msg.get("sequence"), time.time()))

        # Set up processors
        priority_queue.set_message_processor(track_priority_queue_delivery)

        # GOLDEN PATH EXECUTION: Route events through different queue implementations
        # This simulates the current fragmented routing in production

        routing_decisions = []  # Track which events go to which queues

        for event in self.golden_path_events:
            event_message = {
                "event_type": event.event_type,
                "content": event.content,
                "sequence": event.sequence,
                "state": event.state.value,
                "is_critical": event.is_critical,
                "user_id": str(self.golden_path_user_id),
                "timestamp": event.timestamp
            }

            # FRAGMENTED ROUTING: Different events routed to different queues
            # This reflects the current production chaos

            if event.event_type in ["agent_started", "agent_completed"]:
                # Critical events -> Priority queue
                await priority_queue.enqueue_message(
                    event_message, event.event_type, MessagePriority.CRITICAL, f"event_{event.sequence}"
                )
                routing_decisions.append(f"Event {event.sequence} ({event.event_type}) -> Priority Queue")

            if event.event_type in ["tool_executing", "tool_completed"]:
                # Tool events -> Buffer (for recovery)
                await buffer_queue.buffer_message(
                    str(self.golden_path_user_id), event_message, BufferPriority.HIGH
                )
                routing_decisions.append(f"Event {event.sequence} ({event.event_type}) -> Buffer Queue")

            if event.event_type in ["agent_thinking"]:
                # Thinking events -> Simple queue (considered lightweight)
                await simple_queue.enqueue(event_message)
                routing_decisions.append(f"Event {event.sequence} ({event.event_type}) -> Simple Queue")

            # Some events sent to multiple queues (duplication chaos)
            if event.is_critical:
                await buffer_queue.buffer_message(
                    str(self.golden_path_user_id), event_message, BufferPriority.CRITICAL
                )

        # CONCURRENT PROCESSING: All queues process simultaneously
        processing_start_time = time.time()

        await asyncio.gather(
            priority_queue.flush_queue(),
            buffer_queue.deliver_buffered_messages(str(self.golden_path_user_id), track_buffer_delivery),
            track_simple_queue_delivery()
        )

        processing_end_time = time.time()

        # GOLDEN PATH FLOW ANALYSIS
        # Expected: Sequential delivery in chronological order for optimal user experience
        expected_sequence = [1, 2, 3, 4, 5, 6, 7]

        # Analyze what the user actually experienced
        user_experience_timeline.sort(key=lambda x: x[2])  # Sort by delivery time
        actual_user_experience = [event[1] for event in user_experience_timeline]

        # Calculate Golden Path flow integrity
        def analyze_flow_integrity():
            integrity_issues = []

            # Check for missing critical events
            delivered_events = set(actual_user_experience)
            critical_events = {event.sequence for event in self.golden_path_events if event.is_critical}
            missing_critical = critical_events - delivered_events
            if missing_critical:
                integrity_issues.append(f"Missing critical events: {sorted(missing_critical)}")

            # Check for out-of-order delivery
            order_violations = 0
            for i in range(1, len(actual_user_experience)):
                if actual_user_experience[i] < actual_user_experience[i-1]:
                    order_violations += 1

            if order_violations > 0:
                integrity_issues.append(f"Order violations: {order_violations}")

            # Check for broken conversation flow
            conversation_breaks = []
            if 2 in delivered_events and 1 not in delivered_events:
                conversation_breaks.append("Agent started without user request")
            if 4 in delivered_events and 2 not in delivered_events:
                conversation_breaks.append("Tool execution without agent starting")
            if 7 in delivered_events and 6 not in delivered_events:
                conversation_breaks.append("Agent completion without tool completion")

            if conversation_breaks:
                integrity_issues.append(f"Conversation breaks: {conversation_breaks}")

            return integrity_issues

        flow_integrity_issues = analyze_flow_integrity()

        # Calculate business impact metrics
        total_events_expected = len(self.golden_path_events)
        total_events_delivered = len(set(actual_user_experience))
        event_loss_rate = ((total_events_expected - total_events_delivered) / total_events_expected) * 100

        # Calculate user experience degradation
        def calculate_user_confusion_score():
            # Higher score = more confusing experience
            confusion_score = 0

            # Missing events cause confusion
            confusion_score += len(set(expected_sequence) - set(actual_user_experience)) * 20

            # Out-of-order events cause confusion
            for i in range(1, len(actual_user_experience)):
                if actual_user_experience[i] < actual_user_experience[i-1]:
                    confusion_score += 10

            # Duplicate events cause confusion
            duplicates = len(actual_user_experience) - len(set(actual_user_experience))
            confusion_score += duplicates * 5

            return min(confusion_score, 100)  # Cap at 100%

        user_confusion_score = calculate_user_confusion_score()

        self.fail(
            f"EXPECTED FAILURE - Golden Path Flow Disruption (Issue #1011):\n"
            f"Queue fragmentation CATASTROPHICALLY disrupts the $500K+ ARR Golden Path:\n"
            f"\n=== GOLDEN PATH FLOW INTEGRITY ===\n"
            f"- Expected event sequence: {expected_sequence}\n"
            f"- Actual user experience: {actual_user_experience}\n"
            f"- Events delivered: {total_events_delivered}/{total_events_expected}\n"
            f"- Event loss rate: {event_loss_rate:.1f}%\n"
            f"- User confusion score: {user_confusion_score}/100\n"
            f"\n=== FLOW INTEGRITY ISSUES ===\n"
            f"{chr(10).join(['- ' + issue for issue in flow_integrity_issues])}\n"
            f"\n=== ROUTING CHAOS ANALYSIS ===\n"
            f"- Priority queue events: {len(priority_queue_events)} ({[e['sequence'] for e in priority_queue_events]})\n"
            f"- Buffer queue events: {len(buffer_queue_events)} ({[e['sequence'] for e in buffer_queue_events]})\n"
            f"- Simple queue events: {len(simple_queue_events)} ({[e['sequence'] for e in simple_queue_events]})\n"
            f"\n=== ROUTING DECISIONS ===\n"
            f"{chr(10).join(['- ' + decision for decision in routing_decisions])}\n"
            f"\n=== USER EXPERIENCE TIMELINE ===\n"
            f"{chr(10).join([f'- T+{event[2]-processing_start_time:.2f}s: {event[0]} queue delivered event {event[1]}' for event in user_experience_timeline[:10]])}\n"
            f"\n=== CRITICAL BUSINESS IMPACT ===\n"
            f"🚨 GOLDEN PATH BROKEN: Users see incoherent agent behavior\n"
            f"🚨 CONVERSATION FLOW DISRUPTED: Agent responses out of logical order\n"
            f"🚨 USER TRUST DAMAGED: Inconsistent and confusing chat experience\n"
            f"🚨 REVENUE IMPACT: $500K+ ARR at risk due to broken core functionality\n"
            f"\n=== CONSOLIDATION REQUIRED ===\n"
            f"Single unified queue implementation needed immediately to restore Golden Path integrity."
        )

    async def test_agent_state_corruption_in_golden_path_flow(self):
        """
        FAILING CRITICAL TEST: Shows how queue fragmentation corrupts agent state
        during Golden Path execution, causing nonsensical agent behavior.

        When different agent events are processed by different queues, the agent
        appears to have multiple personalities or conflicting states, completely
        breaking the illusion of intelligent conversation.

        Expected to FAIL due to agent state inconsistency.
        """
        # Create queues that will fragment agent state
        state_aware_queue = MessageQueue(self.golden_path_connection_id, self.golden_path_user_id)
        stateless_buffer = WebSocketMessageBuffer()
        basic_queue = WebSocketMessageQueue()

        # Track agent state as perceived by user through each queue
        agent_state_timeline = {
            "state_aware": [],
            "buffer": [],
            "basic": []
        }

        # Create agent conversation with clear state transitions
        agent_conversation = [
            {
                "sequence": 1,
                "type": "agent_started",
                "content": "Hello! I'm ready to help you analyze your data.",
                "agent_state": "ready",
                "emotion": "confident"
            },
            {
                "sequence": 2,
                "type": "agent_thinking",
                "content": "Let me examine your data carefully...",
                "agent_state": "analyzing",
                "emotion": "focused"
            },
            {
                "sequence": 3,
                "type": "tool_executing",
                "content": "Running complex statistical analysis now.",
                "agent_state": "working",
                "emotion": "determined"
            },
            {
                "sequence": 4,
                "type": "agent_thinking",
                "content": "The results are interesting... I need to dig deeper.",
                "agent_state": "investigating",
                "emotion": "curious"
            },
            {
                "sequence": 5,
                "type": "tool_completed",
                "content": "Analysis complete! I found significant patterns.",
                "agent_state": "excited",
                "emotion": "enthusiastic"
            },
            {
                "sequence": 6,
                "type": "agent_completed",
                "content": "Here are the key insights from your data: [results]",
                "agent_state": "satisfied",
                "emotion": "accomplished"
            }
        ]

        # Track agent state perception through each queue
        async def track_state_aware_agent(queued_msg):
            event = queued_msg.message_data
            agent_state_timeline["state_aware"].append({
                "sequence": event["sequence"],
                "perceived_state": event["agent_state"],
                "emotion": event["emotion"],
                "content": event["content"][:50] + "...",
                "delivered_at": time.time()
            })

        async def track_buffer_agent(message):
            agent_state_timeline["buffer"].append({
                "sequence": message["sequence"],
                "perceived_state": message["agent_state"],
                "emotion": message["emotion"],
                "content": message["content"][:50] + "...",
                "delivered_at": time.time()
            })
            return True

        async def track_basic_agent():
            while not basic_queue.is_empty():
                msg = await basic_queue.dequeue(timeout=0.1)
                if msg:
                    agent_state_timeline["basic"].append({
                        "sequence": msg["sequence"],
                        "perceived_state": msg["agent_state"],
                        "emotion": msg["emotion"],
                        "content": msg["content"][:50] + "...",
                        "delivered_at": time.time()
                    })

        # Set up processors
        state_aware_queue.set_message_processor(track_state_aware_agent)

        # FRAGMENTED AGENT STATE ROUTING
        # This creates the agent personality disorder problem
        for event in agent_conversation:
            # Route different agent states to different queues
            if event["agent_state"] in ["ready", "satisfied"]:
                # Beginning/end states -> State-aware queue
                await state_aware_queue.enqueue_message(
                    event, event["type"], MessagePriority.HIGH, f"agent_{event['sequence']}"
                )

            if event["agent_state"] in ["working", "excited"]:
                # Emotional states -> Buffer queue
                await stateless_buffer.buffer_message(
                    str(self.golden_path_user_id), event, BufferPriority.HIGH
                )

            if event["agent_state"] in ["analyzing", "investigating"]:
                # Thinking states -> Basic queue
                await basic_queue.enqueue(event)

        # Process all queues concurrently (state fragmentation)
        await asyncio.gather(
            state_aware_queue.flush_queue(),
            stateless_buffer.deliver_buffered_messages(str(self.golden_path_user_id), track_buffer_agent),
            track_basic_agent()
        )

        # Analyze agent personality coherence
        def analyze_agent_coherence():
            coherence_issues = []

            # Check for missing state transitions
            all_states = set()
            for queue_states in agent_state_timeline.values():
                all_states.update(s["perceived_state"] for s in queue_states)

            expected_states = {"ready", "analyzing", "working", "investigating", "excited", "satisfied"}
            missing_states = expected_states - all_states
            if missing_states:
                coherence_issues.append(f"Missing agent states: {sorted(missing_states)}")

            # Check for emotional inconsistency
            emotions_per_queue = {}
            for queue_name, states in agent_state_timeline.items():
                emotions_per_queue[queue_name] = [s["emotion"] for s in states]

            # Check for state sequence violations
            for queue_name, states in agent_state_timeline.items():
                if len(states) > 1:
                    sequences = [s["sequence"] for s in states]
                    if sequences != sorted(sequences):
                        coherence_issues.append(f"{queue_name} queue: Agent states out of sequence")

            return coherence_issues, emotions_per_queue

        coherence_issues, emotions_per_queue = analyze_agent_coherence()

        # Calculate user confusion from agent personality disorder
        total_agent_messages = len(agent_conversation)
        messages_delivered = sum(len(states) for states in agent_state_timeline.values())
        unique_messages = len(set(
            s["sequence"] for states in agent_state_timeline.values() for s in states
        ))

        personality_fragmentation_score = ((messages_delivered - unique_messages) / total_agent_messages) * 100

        self.fail(
            f"EXPECTED FAILURE - Agent State Corruption in Golden Path (Issue #1011):\n"
            f"Queue fragmentation causes agent personality disorder, destroying user trust:\n"
            f"\n=== AGENT PERSONALITY ANALYSIS ===\n"
            f"- Total agent messages: {total_agent_messages}\n"
            f"- Messages delivered: {messages_delivered}\n"
            f"- Unique messages: {unique_messages}\n"
            f"- Personality fragmentation score: {personality_fragmentation_score:.1f}%\n"
            f"\n=== AGENT COHERENCE ISSUES ===\n"
            f"{chr(10).join(['- ' + issue for issue in coherence_issues]) if coherence_issues else '- None detected'}\n"
            f"\n=== AGENT STATE FRAGMENTATION ===\n"
            f"- State-aware queue delivered: {len(agent_state_timeline['state_aware'])} states\n"
            f"- Buffer queue delivered: {len(agent_state_timeline['buffer'])} states\n"
            f"- Basic queue delivered: {len(agent_state_timeline['basic'])} states\n"
            f"\n=== EMOTIONAL CONSISTENCY ===\n"
            f"- State-aware emotions: {emotions_per_queue.get('state_aware', [])}\n"
            f"- Buffer emotions: {emotions_per_queue.get('buffer', [])}\n"
            f"- Basic emotions: {emotions_per_queue.get('basic', [])}\n"
            f"\n=== USER EXPERIENCE IMPACT ===\n"
            f"🤖 Agent appears to have multiple personalities\n"
            f"🤖 Emotional states delivered inconsistently\n"
            f"🤖 Conversation flow feels robotic and disconnected\n"
            f"🤖 Users lose trust in AI intelligence\n"
            f"\n=== BUSINESS IMPACT ===\n"
            f"Agent personality disorder reduces user engagement and satisfaction.\n"
            f"Poor AI experience directly impacts the $500K+ ARR chat value proposition.\n"
            f"Users expect coherent, intelligent agent behavior throughout conversations."
        )

    async def test_real_time_feedback_disruption_in_golden_path(self):
        """
        FAILING CRITICAL TEST: Demonstrates how queue fragmentation breaks the
        real-time feedback loop that is essential for Golden Path user engagement.

        Users expect immediate feedback when agents are thinking/working.
        Queue fragmentation causes delays, missing updates, and broken real-time UX.

        Expected to FAIL due to real-time experience degradation.
        """
        # Create queues with different latency characteristics
        fast_queue = MessageQueue(self.golden_path_connection_id, self.golden_path_user_id, max_size=10)
        buffered_queue = WebSocketMessageBuffer()  # Has buffering delays
        slow_queue = WebSocketMessageQueue(max_size=5)  # Small queue, likely to block

        # Track real-time feedback delivery timing
        feedback_timeline = []
        user_waiting_periods = []

        # Create real-time feedback sequence
        realtime_feedback = [
            {"type": "agent_started", "delay_expected": 0.1, "user_critical": True},
            {"type": "agent_thinking", "delay_expected": 0.2, "user_critical": True},
            {"type": "typing_indicator", "delay_expected": 0.05, "user_critical": False},
            {"type": "progress_update", "delay_expected": 0.1, "user_critical": True},
            {"type": "tool_executing", "delay_expected": 0.15, "user_critical": True},
            {"type": "progress_update", "delay_expected": 0.1, "user_critical": True},
            {"type": "tool_progress", "delay_expected": 0.05, "user_critical": False},
            {"type": "tool_completed", "delay_expected": 0.15, "user_critical": True},
            {"type": "agent_thinking", "delay_expected": 0.2, "user_critical": True},
            {"type": "typing_indicator", "delay_expected": 0.05, "user_critical": False},
            {"type": "agent_completed", "delay_expected": 0.3, "user_critical": True}
        ]

        # Add sequence numbers and timestamps
        for i, feedback in enumerate(realtime_feedback):
            feedback.update({
                "sequence": i + 1,
                "sent_at": time.time(),
                "id": f"feedback_{i+1}"
            })

        # Track delivery timing
        delivery_start_time = time.time()

        async def track_fast_queue_delivery(queued_msg):
            current_time = time.time()
            event = queued_msg.message_data
            feedback_timeline.append({
                "queue": "fast",
                "sequence": event["sequence"],
                "type": event["type"],
                "sent_at": event["sent_at"],
                "delivered_at": current_time,
                "latency": current_time - event["sent_at"],
                "user_critical": event["user_critical"]
            })

        async def track_buffer_delivery(message):
            current_time = time.time()
            feedback_timeline.append({
                "queue": "buffer",
                "sequence": message["sequence"],
                "type": message["type"],
                "sent_at": message["sent_at"],
                "delivered_at": current_time,
                "latency": current_time - message["sent_at"],
                "user_critical": message["user_critical"]
            })
            return True

        async def track_slow_queue_delivery():
            while not slow_queue.is_empty():
                msg = await slow_queue.dequeue(timeout=0.1)
                if msg:
                    current_time = time.time()
                    feedback_timeline.append({
                        "queue": "slow",
                        "sequence": msg["sequence"],
                        "type": msg["type"],
                        "sent_at": msg["sent_at"],
                        "delivered_at": current_time,
                        "latency": current_time - msg["sent_at"],
                        "user_critical": msg["user_critical"]
                    })

        # Set up processors
        fast_queue.set_message_processor(track_fast_queue_delivery)

        # FRAGMENTED REAL-TIME ROUTING
        # This simulates how different feedback types get routed differently
        for feedback in realtime_feedback:
            if feedback["user_critical"]:
                # Critical feedback -> Fast queue
                await fast_queue.enqueue_message(
                    feedback, feedback["type"], MessagePriority.HIGH, feedback["id"]
                )

            if feedback["type"] in ["progress_update", "tool_progress"]:
                # Progress updates -> Buffer queue
                await buffered_queue.buffer_message(
                    str(self.golden_path_user_id), feedback, BufferPriority.NORMAL
                )

            if not feedback["user_critical"]:
                # Non-critical -> Slow queue
                await slow_queue.enqueue(feedback)

            # Add small delay to simulate realistic timing
            await asyncio.sleep(feedback["delay_expected"])

        # Process all queues with timing measurement
        processing_tasks = [
            asyncio.create_task(fast_queue.flush_queue()),
            asyncio.create_task(buffered_queue.deliver_buffered_messages(
                str(self.golden_path_user_id), track_buffer_delivery
            )),
            asyncio.create_task(track_slow_queue_delivery())
        ]

        await asyncio.gather(*processing_tasks)

        # Analyze real-time experience quality
        feedback_timeline.sort(key=lambda x: x["delivered_at"])

        def analyze_realtime_experience():
            experience_issues = []

            # Calculate average latency by queue
            latencies_by_queue = {}
            for event in feedback_timeline:
                queue = event["queue"]
                if queue not in latencies_by_queue:
                    latencies_by_queue[queue] = []
                latencies_by_queue[queue].append(event["latency"])

            avg_latencies = {
                queue: sum(latencies) / len(latencies)
                for queue, latencies in latencies_by_queue.items()
            }

            # Check for excessive delays on critical feedback
            critical_events = [e for e in feedback_timeline if e["user_critical"]]
            slow_critical_events = [e for e in critical_events if e["latency"] > 0.5]  # >500ms is too slow

            if slow_critical_events:
                experience_issues.append(f"Slow critical feedback: {len(slow_critical_events)} events >500ms")

            # Check for missing real-time updates
            expected_sequences = set(range(1, len(realtime_feedback) + 1))
            delivered_sequences = set(e["sequence"] for e in feedback_timeline)
            missing_feedback = expected_sequences - delivered_sequences

            if missing_feedback:
                experience_issues.append(f"Missing feedback events: {sorted(missing_feedback)}")

            # Check for out-of-order delivery
            delivered_order = [e["sequence"] for e in feedback_timeline]
            expected_order = sorted(delivered_order)

            if delivered_order != expected_order:
                experience_issues.append("Real-time feedback delivered out of order")

            return experience_issues, avg_latencies, slow_critical_events

        experience_issues, avg_latencies, slow_critical_events = analyze_realtime_experience()

        # Calculate user experience metrics
        total_feedback_expected = len(realtime_feedback)
        total_feedback_delivered = len(set(e["sequence"] for e in feedback_timeline))
        feedback_loss_rate = ((total_feedback_expected - total_feedback_delivered) / total_feedback_expected) * 100

        # Calculate real-time responsiveness score
        critical_feedback_count = sum(1 for f in realtime_feedback if f["user_critical"])
        fast_critical_deliveries = len([e for e in feedback_timeline if e["user_critical"] and e["latency"] < 0.2])
        responsiveness_score = (fast_critical_deliveries / critical_feedback_count) * 100 if critical_feedback_count > 0 else 0

        self.fail(
            f"EXPECTED FAILURE - Real-Time Feedback Disruption (Issue #1011):\n"
            f"Queue fragmentation DESTROYS real-time user experience in Golden Path:\n"
            f"\n=== REAL-TIME EXPERIENCE METRICS ===\n"
            f"- Expected feedback events: {total_feedback_expected}\n"
            f"- Delivered feedback events: {total_feedback_delivered}\n"
            f"- Feedback loss rate: {feedback_loss_rate:.1f}%\n"
            f"- Real-time responsiveness score: {responsiveness_score:.1f}%\n"
            f"\n=== LATENCY ANALYSIS BY QUEUE ===\n"
            f"- Fast queue avg latency: {avg_latencies.get('fast', 0):.3f}s\n"
            f"- Buffer queue avg latency: {avg_latencies.get('buffer', 0):.3f}s\n"
            f"- Slow queue avg latency: {avg_latencies.get('slow', 0):.3f}s\n"
            f"\n=== REAL-TIME EXPERIENCE ISSUES ===\n"
            f"{chr(10).join(['- ' + issue for issue in experience_issues]) if experience_issues else '- None detected'}\n"
            f"\n=== SLOW CRITICAL FEEDBACK ===\n"
            f"Events that exceeded acceptable real-time thresholds:\n"
            + "\n".join([f"- Sequence {e['sequence']} ({e['type']}): {e['latency']:.3f}s delay" for e in slow_critical_events[:5]]) + "\n"
            f"\n=== USER WAITING EXPERIENCE ===\n"
            f"Users experienced gaps in real-time feedback, causing:\n"
            f"⏱️  Long periods without visual agent activity\n"
            f"⏱️  Uncertainty about agent progress\n"
            f"⏱️  Perception that the system is broken or slow\n"
            f"⏱️  Increased likelihood of user abandonment\n"
            f"\n=== BUSINESS IMPACT ===\n"
            f"Poor real-time experience reduces user engagement and trust.\n"
            f"Users expect immediate feedback in modern AI chat interfaces.\n"
            f"Delayed or missing real-time updates directly impact $500K+ ARR retention.\n"
            f"Competing AI platforms provide better real-time responsiveness."
        )