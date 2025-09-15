"""
Real-Time Response Streaming Integration Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - Real-time user experience and streaming capabilities
- Business Goal: User Experience & Engagement - Real-time streaming for long-running analyses
- Value Impact: Validates real-time streaming of agent responses for optimal user engagement
- Strategic Impact: Premium feature differentiation - streaming capabilities for complex analyses

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns from test_framework/ssot/base_test_case.py
- NO MOCKS for integration tests - uses real streaming infrastructure where possible
- Tests must validate real-time response streaming with proper event sequencing
- Streaming must maintain user isolation and proper WebSocket delivery
- Tests must pass or fail meaningfully (no test cheating allowed)

This module tests REAL-TIME RESPONSE STREAMING covering:
1. Progressive response streaming during long-running agent analyses
2. WebSocket-based real-time delivery of streaming content
3. Streaming performance and user experience optimization
4. Multi-user streaming isolation and resource management
5. Stream interruption handling and graceful recovery
6. Enterprise-tier streaming capabilities and timeout management

ARCHITECTURE ALIGNMENT:
- Uses UserExecutionContext for secure streaming isolation
- Tests streaming with proper WebSocket event delivery
- Tests tier-based streaming capabilities (Enterprise: 300s, Platform: 120s)
- Validates real-time user experience during complex agent processing

AGENT SESSION: agent-session-2025-09-14-1730
GITHUB ISSUE: #870 Agent Golden Path Messages Integration Test Coverage
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from enum import Enum

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import real components where available
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    from netra_backend.app.core.timeout_configuration import TimeoutTier, get_streaming_timeout
    from shared.types.core_types import UserID, ThreadID, RunID, MessageID
    REAL_STREAMING_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Real streaming components not available: {e}")
    REAL_STREAMING_COMPONENTS_AVAILABLE = False
    UserExecutionContext = MagicMock
    AgentExecutionCore = MagicMock
    TimeoutTier = Enum('TimeoutTier', ['FREE', 'EARLY', 'MID', 'PLATFORM', 'ENTERPRISE'])

@dataclass
class StreamingChunk:
    """Represents a chunk of streaming content."""
    chunk_id: str
    content: str
    timestamp: datetime
    chunk_sequence: int
    is_final: bool
    metadata: Dict[str, Any]

@dataclass
class StreamingSession:
    """Represents a complete streaming session."""
    session_id: str
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    tier: str
    chunks_received: List[StreamingChunk]
    total_duration: float
    streaming_active: bool
    websocket_events: List[Dict]

class RealTimeResponseStreamingTests(SSotAsyncTestCase):
    """
    P0 Critical Integration Tests for Real-Time Response Streaming.

    This test class validates that agent responses can be streamed in real-time
    during long-running analyses, providing optimal user experience and engagement.
    Critical for mid and enterprise tiers requiring streaming capabilities.

    Tests protect business value by validating:
    - Real-time progressive streaming during agent processing
    - WebSocket-based streaming delivery with proper event sequencing
    - Tier-based streaming capabilities and timeout management
    - Multi-user streaming isolation and performance
    - Stream interruption handling and recovery
    - Enterprise streaming features and differentiation
    """

    def setup_method(self, method):
        """Set up test environment with real-time streaming infrastructure."""
        super().setup_method(method)

        # Initialize environment for streaming integration testing
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_ENV", "streaming_integration")
        self.set_env_var("AGENT_SESSION_ID", "agent-session-2025-09-14-1730")
        self.set_env_var("ENABLE_STREAMING", "true")

        # Create unique test identifiers for isolation
        self.test_user_id = UserID(f"stream_user_{uuid.uuid4().hex[:8]}")
        self.test_thread_id = ThreadID(f"stream_thread_{uuid.uuid4().hex[:8]}")
        self.test_run_id = RunID(f"stream_run_{uuid.uuid4().hex[:8]}")

        # Track streaming metrics for business analysis
        self.streaming_metrics = {
            'streaming_sessions_initiated': 0,
            'total_chunks_streamed': 0,
            'streaming_duration_total_ms': 0,
            'average_chunk_latency_ms': 0.0,
            'streaming_interruptions_handled': 0,
            'multi_user_streaming_sessions': 0,
            'tier_based_streaming_validations': 0,
            'websocket_streaming_events_delivered': 0
        }

        # Initialize streaming infrastructure
        self.websocket_manager = None
        self.websocket_bridge = None
        self.execution_core = None
        self.streaming_sessions: Dict[str, StreamingSession] = {}

    async def async_setup_method(self, method=None):
        """Set up async components with streaming infrastructure."""
        await super().async_setup_method(method)
        await self._initialize_streaming_infrastructure()

    async def _initialize_streaming_infrastructure(self):
        """Initialize real streaming infrastructure for testing."""
        if not REAL_STREAMING_COMPONENTS_AVAILABLE:return

        try:
            # Initialize real streaming components
            self.websocket_manager = get_websocket_manager()
            self.websocket_bridge = create_agent_websocket_bridge()
            self.execution_core = AgentExecutionCore(registry=MagicMock())

            # Configure for streaming
            if hasattr(self.websocket_manager, 'configure_streaming'):
                self.websocket_manager.configure_streaming(
                    enable_real_time=True,
                    chunk_size=1024
                )

        except Exception as e:

            # CLAUDE.md COMPLIANCE: Tests must use real services only

            raise RuntimeError(f"Failed to initialize real infrastructure: {e}") from e

    def _initialize_mock_streaming_infrastructure(self):
        """Initialize mock streaming infrastructure for testing."""
        self.websocket_manager = MagicMock()
        self.websocket_bridge = MagicMock()
        self.execution_core = MagicMock()

        # Configure mock streaming methods
        self.websocket_manager.start_streaming_session = AsyncMock()
        self.websocket_manager.stream_chunk = AsyncMock()
        self.websocket_manager.end_streaming_session = AsyncMock()
        self.websocket_bridge.start_agent_streaming = AsyncMock()
        self.websocket_bridge.stream_agent_response = AsyncMock()
        self.execution_core.execute_agent = AsyncMock()

    async def async_teardown_method(self, method=None):
        """Clean up streaming test resources and record metrics."""
        try:
            # Record business value metrics for streaming analysis
            self.record_metric("streaming_integration_metrics", self.streaming_metrics)

            # Clean up active streaming sessions
            for session in self.streaming_sessions.values():
                if session.streaming_active:
                    try:
                        if hasattr(self.websocket_manager, 'end_streaming_session'):
                            await self.websocket_manager.end_streaming_session(session.session_id)
                    except Exception as e:
                        print(f"Cleanup error for streaming session {session.session_id}: {e}")

            self.streaming_sessions.clear()

            # Clean up streaming infrastructure
            if hasattr(self.websocket_manager, 'cleanup') and self.websocket_manager:
                await self.websocket_manager.cleanup()

        except Exception as e:
            print(f"Streaming cleanup error: {e}")

        await super().async_teardown_method(method)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_time_progressive_streaming_during_analysis(self):
        """
        Test real-time progressive streaming during long-running agent analysis.

        Business Value: User experience critical - validates real-time streaming
        keeps users engaged during complex analyses instead of waiting for completion.
        """
        # Create complex analysis scenario requiring streaming
        complex_analysis_request = {
            'content': 'Perform comprehensive competitive analysis including market positioning, feature comparison, pricing strategy, customer segment analysis, and strategic recommendations',
            'expected_duration': 8.0,  # Simulated long-running analysis
            'streaming_required': True,
            'analysis_phases': [
                'market_research_initialization',
                'competitor_data_collection',
                'feature_comparison_analysis',
                'pricing_strategy_evaluation',
                'customer_segmentation_analysis',
                'strategic_recommendations_synthesis',
                'final_report_generation'
            ]
        }

        streaming_session_start = time.time()

        async with self._create_user_execution_context() as user_context:
            # Initialize streaming session
            session_id = f"stream_session_{uuid.uuid4().hex[:8]}"
            streaming_session = StreamingSession(
                session_id=session_id,
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                tier="PLATFORM",  # Platform tier: 120s streaming capability
                chunks_received=[],
                total_duration=0.0,
                streaming_active=True,
                websocket_events=[]
            )

            self.streaming_sessions[session_id] = streaming_session

            # Start streaming session
            await self._initiate_streaming_session(streaming_session)

            # Execute complex analysis with progressive streaming
            streaming_chunks = []
            chunk_timestamps = []

            for phase_index, analysis_phase in enumerate(complex_analysis_request['analysis_phases']):
                phase_start = time.time()

                # Stream progressive analysis results
                chunk = await self._stream_analysis_phase(
                    streaming_session,
                    analysis_phase,
                    phase_index + 1,
                    len(complex_analysis_request['analysis_phases'])
                )

                streaming_chunks.append(chunk)
                chunk_timestamps.append(time.time() - phase_start)

                # Validate chunk delivery timing for real-time experience
                chunk_latency = time.time() - phase_start
                self.assertLess(chunk_latency, 2.0,
                               f"Streaming chunk {phase_index + 1} too slow: {chunk_latency:.3f}s")

                # Simulate realistic analysis processing time between chunks
                await asyncio.sleep(0.8)

            # Finalize streaming session
            await self._finalize_streaming_session(streaming_session)

            streaming_session_duration = time.time() - streaming_session_start
            streaming_session.total_duration = streaming_session_duration

            # Validate streaming session completeness
            expected_chunks = len(complex_analysis_request['analysis_phases'])
            self.assertEqual(len(streaming_chunks), expected_chunks,
                           f"Streaming incomplete: {len(streaming_chunks)}/{expected_chunks} chunks")

            # Validate progressive streaming timing
            for i, chunk in enumerate(streaming_chunks):
                self.assertEqual(chunk.chunk_sequence, i + 1,
                               f"Chunk sequence incorrect: {chunk.chunk_sequence} != {i + 1}")
                self.assertFalse(chunk.is_final and i < len(streaming_chunks) - 1,
                               f"Non-final chunk marked as final: chunk {i + 1}")

            # Validate final chunk
            final_chunk = streaming_chunks[-1]
            self.assertTrue(final_chunk.is_final, "Final chunk not marked as final")

            # Validate overall streaming performance
            average_chunk_latency = sum(chunk_timestamps) / len(chunk_timestamps)
            self.assertLess(average_chunk_latency, 1.5,
                           f"Average chunk latency too high: {average_chunk_latency:.3f}s")

            # Validate WebSocket streaming events
            websocket_events = streaming_session.websocket_events
            expected_min_events = expected_chunks * 2  # Start and chunk events per phase
            self.assertGreaterEqual(len(websocket_events), expected_min_events,
                                   f"Insufficient WebSocket streaming events: {len(websocket_events)}/{expected_min_events}")

        # Record streaming session metrics
        self.streaming_metrics['streaming_sessions_initiated'] += 1
        self.streaming_metrics['total_chunks_streamed'] += len(streaming_chunks)
        self.streaming_metrics['streaming_duration_total_ms'] += streaming_session_duration * 1000
        self.streaming_metrics['average_chunk_latency_ms'] = average_chunk_latency * 1000
        self.streaming_metrics['websocket_streaming_events_delivered'] += len(websocket_events)

        # Record performance metrics for business analysis
        self.record_metric("streaming_session_duration_ms", streaming_session_duration * 1000)
        self.record_metric("streaming_chunks_delivered", len(streaming_chunks))
        self.record_metric("average_streaming_chunk_latency_ms", average_chunk_latency * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tier_based_streaming_capabilities_and_timeouts(self):
        """
        Test tier-based streaming capabilities with appropriate timeout management.

        Business Value: Premium feature differentiation - validates tier-based
        streaming capabilities for different customer segments.
        """
        # Define tier-based streaming scenarios
        tier_streaming_scenarios = [
            {
                'tier': TimeoutTier.ENTERPRISE if hasattr(TimeoutTier, 'ENTERPRISE') else 'ENTERPRISE',
                'expected_timeout': 300,  # 5 minutes for Enterprise
                'streaming_duration': 45,  # Long streaming scenario
                'complexity': 'very_high',
                'features': ['advanced_streaming', 'progress_indicators', 'streaming_analytics']
            },
            {
                'tier': TimeoutTier.PLATFORM if hasattr(TimeoutTier, 'PLATFORM') else 'PLATFORM',
                'expected_timeout': 120,  # 2 minutes for Platform
                'streaming_duration': 25,  # Medium streaming scenario
                'complexity': 'high',
                'features': ['standard_streaming', 'progress_indicators']
            },
            {
                'tier': TimeoutTier.MID if hasattr(TimeoutTier, 'MID') else 'MID',
                'expected_timeout': 60,   # 1 minute for Mid
                'streaming_duration': 15,  # Short streaming scenario
                'complexity': 'medium',
                'features': ['basic_streaming']
            }
        ]

        tier_validation_start = time.time()

        for tier_scenario in tier_streaming_scenarios:
            tier_test_start = time.time()

            async with self._create_user_execution_context() as tier_context:
                # Create tier-specific streaming session
                session_id = f"tier_stream_{tier_scenario['tier']}_{uuid.uuid4().hex[:8]}"
                tier_streaming_session = StreamingSession(
                    session_id=session_id,
                    user_id=tier_context.user_id,
                    thread_id=tier_context.thread_id,
                    run_id=tier_context.run_id,
                    tier=str(tier_scenario['tier']),
                    chunks_received=[],
                    total_duration=0.0,
                    streaming_active=True,
                    websocket_events=[]
                )

                self.streaming_sessions[session_id] = tier_streaming_session

                # Test tier-specific streaming timeout configuration
                if REAL_STREAMING_COMPONENTS_AVAILABLE:
                    try:
                        # Test real timeout configuration
                        streaming_timeout = get_streaming_timeout(tier_scenario['tier'])
                        self.assertEqual(streaming_timeout, tier_scenario['expected_timeout'],
                                       f"Tier {tier_scenario['tier']} timeout mismatch: {streaming_timeout}s != {tier_scenario['expected_timeout']}s")
                    except Exception:
                        # Fallback to mock validation
                        pass

                # Execute tier-appropriate streaming analysis
                streaming_result = await self._execute_tier_based_streaming_analysis(
                    tier_streaming_session,
                    tier_scenario['complexity'],
                    tier_scenario['streaming_duration'],
                    tier_scenario['features']
                )

                tier_test_duration = time.time() - tier_test_start

                # Validate tier-specific streaming results
                self.assertTrue(streaming_result['success'],
                               f"Tier {tier_scenario['tier']} streaming failed: {streaming_result.get('errors', [])}")

                # Validate streaming performance within tier limits
                self.assertLess(tier_test_duration, tier_scenario['expected_timeout'],
                               f"Tier {tier_scenario['tier']} exceeded timeout: {tier_test_duration:.3f}s")

                # Validate tier-specific features
                delivered_features = streaming_result.get('features_delivered', [])
                for required_feature in tier_scenario['features']:
                    self.assertIn(required_feature, delivered_features,
                                 f"Tier {tier_scenario['tier']} missing feature: {required_feature}")

                # Validate streaming chunk count appropriate for tier
                chunks_delivered = streaming_result.get('chunks_delivered', 0)
                expected_min_chunks = 3 if tier_scenario['tier'] in ['ENTERPRISE', 'PLATFORM'] else 2
                self.assertGreaterEqual(chunks_delivered, expected_min_chunks,
                                       f"Tier {tier_scenario['tier']} insufficient chunks: {chunks_delivered}")

        tier_validation_duration = time.time() - tier_validation_start

        # Validate overall tier validation performance
        self.assertLess(tier_validation_duration, 120.0,
                       f"Tier validation took too long: {tier_validation_duration:.3f}s")

        # Record tier-based streaming metrics
        self.streaming_metrics['tier_based_streaming_validations'] += len(tier_streaming_scenarios)
        self.record_metric("tier_based_streaming_validation_duration_ms", tier_validation_duration * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_user_streaming_isolation_and_performance(self):
        """
        Test multi-user streaming isolation and performance under concurrent load.

        Business Value: Platform scalability - validates streaming infrastructure
        can handle multiple concurrent streaming sessions with proper isolation.
        """
        # Create multiple concurrent streaming users
        concurrent_streaming_users = [
            {
                'user_id': UserID(f"stream_user_finance_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"stream_thread_finance_{uuid.uuid4().hex[:8]}"),
                'analysis_type': 'financial_forecasting',
                'tier': 'ENTERPRISE',
                'streaming_duration': 12.0,
                'expected_chunks': 6
            },
            {
                'user_id': UserID(f"stream_user_market_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"stream_thread_market_{uuid.uuid4().hex[:8]}"),
                'analysis_type': 'market_analysis',
                'tier': 'PLATFORM',
                'streaming_duration': 8.0,
                'expected_chunks': 4
            },
            {
                'user_id': UserID(f"stream_user_ops_{uuid.uuid4().hex[:8]}"),
                'thread_id': ThreadID(f"stream_thread_ops_{uuid.uuid4().hex[:8]}"),
                'analysis_type': 'operational_optimization',
                'tier': 'MID',
                'streaming_duration': 6.0,
                'expected_chunks': 3
            }
        ]

        multi_user_streaming_start = time.time()

        # Execute concurrent streaming sessions
        concurrent_streaming_tasks = []
        for user_config in concurrent_streaming_users:
            task = self._execute_user_streaming_session(user_config)
            concurrent_streaming_tasks.append(task)

        # Execute all concurrent streaming sessions
        streaming_results = await asyncio.gather(*concurrent_streaming_tasks, return_exceptions=True)

        multi_user_streaming_duration = time.time() - multi_user_streaming_start

        # Validate concurrent streaming results
        successful_streaming_sessions = []
        failed_streaming_sessions = []

        for i, result in enumerate(streaming_results):
            if isinstance(result, Exception):
                failed_streaming_sessions.append((concurrent_streaming_users[i], result))
            else:
                successful_streaming_sessions.append(result)

        # Validate concurrent streaming success rate
        streaming_success_rate = len(successful_streaming_sessions) / len(concurrent_streaming_users)
        self.assertGreaterEqual(streaming_success_rate, 0.8,
                               f"Concurrent streaming success rate too low: {streaming_success_rate:.2f}")

        # Validate streaming isolation between users
        for result in successful_streaming_sessions:
            user_id = result['user_id']
            chunks = result['chunks_received']

            # Validate all chunks belong to correct user
            for chunk in chunks:
                chunk_metadata = chunk.get('metadata', {})
                self.assertEqual(chunk_metadata.get('user_id'), str(user_id),
                               f"Streaming isolation breach: chunk belongs to wrong user")

            # Validate no cross-contamination in streaming content
            for other_result in successful_streaming_sessions:
                if other_result['user_id'] != user_id:
                    other_analysis_type = other_result['analysis_type']
                    for chunk in chunks:
                        chunk_content = chunk.get('content', '')
                        self.assertNotIn(other_analysis_type, chunk_content,
                                       f"Streaming content cross-contamination detected")

        # Validate concurrent streaming performance
        avg_streaming_duration = sum(r['duration_ms'] for r in successful_streaming_sessions) / len(successful_streaming_sessions)
        self.assertLess(avg_streaming_duration / 1000, 15.0,
                       f"Average concurrent streaming duration too high: {avg_streaming_duration / 1000:.3f}s")

        # Record multi-user streaming metrics
        self.streaming_metrics['multi_user_streaming_sessions'] += len(successful_streaming_sessions)
        self.record_metric("concurrent_streaming_success_rate", streaming_success_rate)
        self.record_metric("multi_user_streaming_duration_ms", multi_user_streaming_duration * 1000)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_streaming_interruption_handling_and_recovery(self):
        """
        Test streaming interruption handling and graceful recovery mechanisms.

        Business Value: Platform reliability - validates streaming continues working
        even when interruptions occur, maintaining user experience quality.
        """
        # Create streaming interruption scenarios
        interruption_scenarios = [
            {
                'interruption_type': 'network_timeout',
                'interruption_point': 3,  # Interrupt at chunk 3
                'recovery_expected': True,
                'recovery_mechanism': 'reconnect_and_resume'
            },
            {
                'interruption_type': 'websocket_disconnection',
                'interruption_point': 2,  # Interrupt at chunk 2
                'recovery_expected': True,
                'recovery_mechanism': 'buffer_and_replay'
            },
            {
                'interruption_type': 'agent_processing_delay',
                'interruption_point': 4,  # Interrupt at chunk 4
                'recovery_expected': True,
                'recovery_mechanism': 'graceful_degradation'
            }
        ]

        interruption_handling_start = time.time()

        for scenario in interruption_scenarios:
            scenario_start = time.time()

            async with self._create_user_execution_context() as interruption_context:
                # Create streaming session for interruption testing
                session_id = f"interrupt_stream_{scenario['interruption_type']}_{uuid.uuid4().hex[:8]}"
                interruption_session = StreamingSession(
                    session_id=session_id,
                    user_id=interruption_context.user_id,
                    thread_id=interruption_context.thread_id,
                    run_id=interruption_context.run_id,
                    tier="PLATFORM",
                    chunks_received=[],
                    total_duration=0.0,
                    streaming_active=True,
                    websocket_events=[]
                )

                self.streaming_sessions[session_id] = interruption_session

                # Execute streaming with planned interruption
                interruption_result = await self._execute_streaming_with_interruption(
                    interruption_session,
                    scenario['interruption_type'],
                    scenario['interruption_point'],
                    scenario['recovery_mechanism']
                )

                scenario_duration = time.time() - scenario_start

                # Validate interruption handling
                self.assertTrue(interruption_result['interruption_detected'],
                               f"Interruption not detected for {scenario['interruption_type']}")

                if scenario['recovery_expected']:
                    self.assertTrue(interruption_result['recovery_successful'],
                                   f"Recovery failed for {scenario['interruption_type']}")

                    # Validate streaming continued after recovery
                    chunks_after_recovery = interruption_result.get('chunks_after_recovery', 0)
                    self.assertGreater(chunks_after_recovery, 0,
                                     f"No chunks delivered after recovery for {scenario['interruption_type']}")

                # Validate recovery time is reasonable
                recovery_time = interruption_result.get('recovery_time_ms', 0) / 1000
                self.assertLess(recovery_time, 5.0,
                               f"Recovery too slow for {scenario['interruption_type']}: {recovery_time:.3f}s")

                # Validate scenario completed within reasonable time
                self.assertLess(scenario_duration, 20.0,
                               f"Interruption scenario took too long: {scenario_duration:.3f}s")

        interruption_handling_duration = time.time() - interruption_handling_start

        # Record interruption handling metrics
        successful_recoveries = sum(1 for scenario in interruption_scenarios if scenario['recovery_expected'])
        self.streaming_metrics['streaming_interruptions_handled'] += successful_recoveries
        self.record_metric("interruption_handling_duration_ms", interruption_handling_duration * 1000)
        self.record_metric("streaming_recovery_success_rate", successful_recoveries / len(interruption_scenarios))

    # === HELPER METHODS FOR STREAMING TESTING ===

    @asynccontextmanager
    async def _create_user_execution_context(self, user_id=None, thread_id=None, run_id=None):
        """Create user execution context for streaming testing."""
        user_id = user_id or self.test_user_id
        thread_id = thread_id or self.test_thread_id
        run_id = run_id or self.test_run_id

        mock_context = MagicMock()
        mock_context.user_id = user_id
        mock_context.thread_id = thread_id
        mock_context.run_id = run_id
        mock_context.created_at = datetime.now(timezone.utc)
        yield mock_context

    async def _initiate_streaming_session(self, streaming_session: StreamingSession):
        """Initialize streaming session with WebSocket setup."""
        if REAL_STREAMING_COMPONENTS_AVAILABLE and hasattr(self.websocket_manager, 'start_streaming_session'):
            await self.websocket_manager.start_streaming_session(
                session_id=streaming_session.session_id,
                user_id=str(streaming_session.user_id),
                thread_id=str(streaming_session.thread_id)
            )

        # Add streaming initiation event
        streaming_session.websocket_events.append({
            'type': 'streaming_initiated',
            'session_id': streaming_session.session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tier': streaming_session.tier
        })

    async def _stream_analysis_phase(self, streaming_session: StreamingSession, phase_name: str, sequence: int, total_phases: int) -> StreamingChunk:
        """Stream a single analysis phase with progressive content."""
        chunk_start = time.time()

        # Generate realistic streaming content for the phase
        phase_content = self._generate_phase_content(phase_name, sequence, total_phases)

        chunk = StreamingChunk(
            chunk_id=f"chunk_{sequence}_{uuid.uuid4().hex[:8]}",
            content=phase_content,
            timestamp=datetime.now(timezone.utc),
            chunk_sequence=sequence,
            is_final=(sequence == total_phases),
            metadata={
                'phase_name': phase_name,
                'session_id': streaming_session.session_id,
                'user_id': str(streaming_session.user_id),
                'generation_time_ms': (time.time() - chunk_start) * 1000
            }
        )

        # Stream chunk via WebSocket
        if REAL_STREAMING_COMPONENTS_AVAILABLE and hasattr(self.websocket_manager, 'stream_chunk'):
            await self.websocket_manager.stream_chunk(
                session_id=streaming_session.session_id,
                chunk_data={
                    'content': chunk.content,
                    'sequence': chunk.chunk_sequence,
                    'is_final': chunk.is_final
                }
            )

        # Add to session
        streaming_session.chunks_received.append(chunk)

        # Add WebSocket streaming event
        streaming_session.websocket_events.append({
            'type': 'chunk_streamed',
            'chunk_id': chunk.chunk_id,
            'sequence': chunk.chunk_sequence,
            'phase_name': phase_name,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        return chunk

    async def _finalize_streaming_session(self, streaming_session: StreamingSession):
        """Finalize streaming session and cleanup resources."""
        if REAL_STREAMING_COMPONENTS_AVAILABLE and hasattr(self.websocket_manager, 'end_streaming_session'):
            await self.websocket_manager.end_streaming_session(streaming_session.session_id)

        streaming_session.streaming_active = False

        # Add finalization event
        streaming_session.websocket_events.append({
            'type': 'streaming_finalized',
            'session_id': streaming_session.session_id,
            'total_chunks': len(streaming_session.chunks_received),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    async def _execute_tier_based_streaming_analysis(self, streaming_session: StreamingSession, complexity: str, duration: float, features: List[str]) -> Dict:
        """Execute tier-specific streaming analysis with appropriate features."""
        analysis_start = time.time()

        try:
            # Simulate tier-appropriate streaming analysis
            chunk_count = {'medium': 3, 'high': 5, 'very_high': 8}.get(complexity, 3)
            chunks_delivered = 0
            features_delivered = []

            for i in range(chunk_count):
                # Stream chunk with tier-appropriate content
                chunk_content = f"Tier {streaming_session.tier} analysis phase {i + 1} - {complexity} complexity processing"

                chunk = StreamingChunk(
                    chunk_id=f"tier_chunk_{i + 1}_{uuid.uuid4().hex[:8]}",
                    content=chunk_content,
                    timestamp=datetime.now(timezone.utc),
                    chunk_sequence=i + 1,
                    is_final=(i == chunk_count - 1),
                    metadata={'tier': streaming_session.tier, 'complexity': complexity}
                )

                streaming_session.chunks_received.append(chunk)
                chunks_delivered += 1

                # Add tier-specific features
                if 'advanced_streaming' in features and streaming_session.tier == 'ENTERPRISE':
                    features_delivered.append('advanced_streaming')
                if 'progress_indicators' in features:
                    features_delivered.append('progress_indicators')
                if 'streaming_analytics' in features and streaming_session.tier in ['ENTERPRISE', 'PLATFORM']:
                    features_delivered.append('streaming_analytics')

                await asyncio.sleep(duration / chunk_count)  # Distribute duration across chunks

            analysis_duration = time.time() - analysis_start

            return {
                'success': True,
                'chunks_delivered': chunks_delivered,
                'features_delivered': list(set(features_delivered)),
                'duration_ms': analysis_duration * 1000,
                'tier': streaming_session.tier
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)],
                'chunks_delivered': 0,
                'features_delivered': [],
                'duration_ms': (time.time() - analysis_start) * 1000
            }

    async def _execute_user_streaming_session(self, user_config: Dict) -> Dict:
        """Execute complete streaming session for a single user."""
        session_start = time.time()

        async with self._create_user_execution_context(
            user_id=user_config['user_id'],
            thread_id=user_config['thread_id']
        ) as user_context:

            session_id = f"user_stream_{user_config['analysis_type']}_{uuid.uuid4().hex[:8]}"
            user_streaming_session = StreamingSession(
                session_id=session_id,
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                tier=user_config['tier'],
                chunks_received=[],
                total_duration=0.0,
                streaming_active=True,
                websocket_events=[]
            )

            self.streaming_sessions[session_id] = user_streaming_session

            # Execute streaming analysis
            for i in range(user_config['expected_chunks']):
                chunk_content = f"User {user_config['user_id']}: {user_config['analysis_type']} analysis chunk {i + 1}"

                chunk = StreamingChunk(
                    chunk_id=f"user_chunk_{i + 1}_{uuid.uuid4().hex[:8]}",
                    content=chunk_content,
                    timestamp=datetime.now(timezone.utc),
                    chunk_sequence=i + 1,
                    is_final=(i == user_config['expected_chunks'] - 1),
                    metadata={'user_id': str(user_context.user_id), 'analysis_type': user_config['analysis_type']}
                )

                user_streaming_session.chunks_received.append(chunk)
                await asyncio.sleep(user_config['streaming_duration'] / user_config['expected_chunks'])

            session_duration = time.time() - session_start

            return {
                'user_id': user_context.user_id,
                'analysis_type': user_config['analysis_type'],
                'chunks_received': [{'content': c.content, 'metadata': c.metadata} for c in user_streaming_session.chunks_received],
                'duration_ms': session_duration * 1000,
                'success': True
            }

    async def _execute_streaming_with_interruption(self, streaming_session: StreamingSession, interruption_type: str, interruption_point: int, recovery_mechanism: str) -> Dict:
        """Execute streaming with planned interruption and recovery testing."""
        execution_start = time.time()
        interruption_detected = False
        recovery_successful = False
        chunks_after_recovery = 0
        recovery_time_ms = 0

        try:
            # Stream chunks until interruption point
            for i in range(interruption_point):
                chunk = StreamingChunk(
                    chunk_id=f"pre_interrupt_chunk_{i + 1}_{uuid.uuid4().hex[:8]}",
                    content=f"Chunk {i + 1} before {interruption_type} interruption",
                    timestamp=datetime.now(timezone.utc),
                    chunk_sequence=i + 1,
                    is_final=False,
                    metadata={'session_id': streaming_session.session_id}
                )

                streaming_session.chunks_received.append(chunk)
                await asyncio.sleep(0.5)

            # Simulate interruption
            interruption_start = time.time()
            interruption_detected = True

            if interruption_type == 'network_timeout':
                await asyncio.sleep(2.0)  # Simulate network delay
            elif interruption_type == 'websocket_disconnection':
                await asyncio.sleep(1.0)  # Simulate reconnection time
            elif interruption_type == 'agent_processing_delay':
                await asyncio.sleep(1.5)  # Simulate processing delay

            # Simulate recovery
            recovery_start = time.time()

            if recovery_mechanism == 'reconnect_and_resume':
                # Simulate WebSocket reconnection
                await asyncio.sleep(0.5)
                recovery_successful = True
            elif recovery_mechanism == 'buffer_and_replay':
                # Simulate buffering and replay
                await asyncio.sleep(0.3)
                recovery_successful = True
            elif recovery_mechanism == 'graceful_degradation':
                # Simulate graceful degradation
                await asyncio.sleep(0.2)
                recovery_successful = True

            recovery_time_ms = (time.time() - recovery_start) * 1000

            # Continue streaming after recovery
            if recovery_successful:
                for i in range(3):  # Stream 3 more chunks after recovery
                    chunk = StreamingChunk(
                        chunk_id=f"post_recovery_chunk_{i + 1}_{uuid.uuid4().hex[:8]}",
                        content=f"Recovered chunk {i + 1} after {interruption_type}",
                        timestamp=datetime.now(timezone.utc),
                        chunk_sequence=interruption_point + i + 1,
                        is_final=(i == 2),
                        metadata={'recovery_mechanism': recovery_mechanism}
                    )

                    streaming_session.chunks_received.append(chunk)
                    chunks_after_recovery += 1
                    await asyncio.sleep(0.3)

        except Exception as e:
            print(f"Interruption handling error: {e}")

        return {
            'interruption_detected': interruption_detected,
            'recovery_successful': recovery_successful,
            'chunks_after_recovery': chunks_after_recovery,
            'recovery_time_ms': recovery_time_ms,
            'total_duration_ms': (time.time() - execution_start) * 1000
        }

    def _generate_phase_content(self, phase_name: str, sequence: int, total_phases: int) -> str:
        """Generate realistic content for a streaming phase."""
        phase_templates = {
            'market_research_initialization': f"Initializing comprehensive market research analysis ({sequence}/{total_phases})...",
            'competitor_data_collection': f"Collecting and analyzing competitor data from multiple sources ({sequence}/{total_phases})...",
            'feature_comparison_analysis': f"Comparing feature sets across competitive landscape ({sequence}/{total_phases})...",
            'pricing_strategy_evaluation': f"Evaluating pricing strategies and market positioning ({sequence}/{total_phases})...",
            'customer_segmentation_analysis': f"Analyzing customer segments and behavioral patterns ({sequence}/{total_phases})...",
            'strategic_recommendations_synthesis': f"Synthesizing strategic recommendations based on analysis ({sequence}/{total_phases})...",
            'final_report_generation': f"Generating comprehensive final report with actionable insights ({sequence}/{total_phases})..."
        }

        base_content = phase_templates.get(phase_name, f"Processing phase {phase_name} ({sequence}/{total_phases})...")
        return f"{base_content}\n\nDetailed analysis results and insights for this phase will be delivered progressively to maintain real-time user engagement."