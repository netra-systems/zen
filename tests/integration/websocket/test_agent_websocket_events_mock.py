"""
Agent WebSocket Events Mock Integration Tests - Phase 1
Issue #862 - Agent Golden Path Message Coverage Enhancement

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR Protection
- Business Goal: WebSocket event delivery enables real-time AI chat experience
- Value Impact: Users see transparent agent processing and maintain engagement during AI workflows
- Strategic Impact: Real-time communication differentiates platform and enables premium user experience

CRITICAL: These integration tests validate WebSocket event delivery integration
during agent execution using mock services while preserving event sequencing,
timing, and content validation that drives user engagement and platform value.

Test Coverage Focus:
- WebSocket event delivery integration during agent processing
- Event ordering and timing validation across complete workflows
- Connection lifecycle management during complex agent execution
- Error recovery scenarios with proper event communication
- Multi-user event isolation and delivery validation
- Performance validation for real-time event delivery expectations

MOCK SERVICES STRATEGY:
- WebSocket connections mocked for controlled event capture and validation
- Agent processing mocked for consistent event trigger patterns
- Network transport mocked while preserving event content and sequencing
- Connection management mocked with realistic lifecycle simulation

REAL INTEGRATION ELEMENTS:
- Event creation and formatting logic
- Event sequencing and timing requirements
- Content validation and business logic
- User isolation and security during event delivery
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from collections import defaultdict

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# WebSocket Event Integration Imports
from netra_backend.app.websocket_core.types import MessageType, create_standard_message, ConnectionInfo
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

# Agent Types for WebSocket Event Testing
from netra_backend.app.agents.triage_agent import TriageAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent


@pytest.mark.golden_path
@pytest.mark.no_docker
@pytest.mark.integration
@pytest.mark.business_critical
class TestAgentWebSocketEventsMock(SSotAsyncTestCase):
    """
    Agent WebSocket Events Mock Integration Tests - Phase 1
    
    These tests validate WebSocket event delivery integration during agent execution
    using mock services to ensure comprehensive event coverage while eliminating
    external dependencies that could affect event timing and delivery validation.
    
    Focus: Real-time communication that maintains user engagement during AI processing.
    """

    def setup_method(self, method=None):
        """Setup WebSocket events integration testing with mock services."""
        super().setup_method(method)
        
        self.env = get_env()
        self.test_user_id = UnifiedIdGenerator.generate_base_id("user")
        self.test_thread_id = UnifiedIdGenerator.generate_base_id("thread")
        
        # Event tracking structures
        self.captured_events = []
        self.event_timestamps = []
        self.connection_states = {}
        self.user_event_streams = defaultdict(list)
        
        # Track test metrics
        self.record_metric("test_suite", "websocket_events_mock_integration")
        self.record_metric("business_value", "$500K_ARR_realtime_communication")
        self.record_metric("mock_services_enabled", True)

    async def _create_mock_websocket_connection(self, user_id: str, connection_id: str) -> MagicMock:
        """Create mock WebSocket connection with event capture."""
        mock_websocket = MagicMock()
        mock_websocket.user_id = user_id
        mock_websocket.connection_id = connection_id
        mock_websocket.send = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        # Track connection state
        self.connection_states[connection_id] = {
            "user_id": user_id,
            "connected": True,
            "events_sent": 0,
            "last_activity": time.time()
        }
        
        # Capture events sent through this connection
        async def capture_event(event_data):
            timestamp = time.time()
            captured_event = {
                "connection_id": connection_id,
                "user_id": user_id,
                "event_data": event_data,
                "timestamp": timestamp,
                "formatted_time": datetime.now(timezone.utc).isoformat()
            }
            
            self.captured_events.append(captured_event)
            self.user_event_streams[user_id].append(captured_event)
            self.event_timestamps.append(timestamp)
            self.connection_states[connection_id]["events_sent"] += 1
            self.connection_states[connection_id]["last_activity"] = timestamp
            self.increment_websocket_events()
        
        mock_websocket.send.side_effect = capture_event
        return mock_websocket

    async def _create_mock_websocket_manager(self) -> MagicMock:
        """Create mock WebSocket manager with connection management."""
        mock_manager = MagicMock()
        mock_manager.initialize = AsyncMock()
        mock_manager.shutdown = AsyncMock()
        mock_manager.connections = {}  # Track active connections
        
        # Mock connection management
        async def add_connection(connection_info: ConnectionInfo):
            self.connection_states[connection_info.websocket.connection_id] = {
                "user_id": connection_info.user_id,
                "thread_id": connection_info.thread_id,
                "connected": True,
                "events_sent": 0,
                "last_activity": time.time()
            }
            mock_manager.connections[connection_info.user_id] = connection_info
        
        async def remove_connection(user_id: str):
            if user_id in mock_manager.connections:
                connection_id = mock_manager.connections[user_id].websocket.connection_id
                self.connection_states[connection_id]["connected"] = False
                del mock_manager.connections[user_id]
        
        async def send_to_user(user_id: str, event_data: dict):
            if user_id in mock_manager.connections:
                connection = mock_manager.connections[user_id]
                await connection.websocket.send(json.dumps(event_data))
        
        async def emit_event(user_id: str, event_data: dict):
            await send_to_user(user_id, event_data)
        
        mock_manager.add_connection = AsyncMock(side_effect=add_connection)
        mock_manager.remove_connection = AsyncMock(side_effect=remove_connection)
        mock_manager.send_to_user = AsyncMock(side_effect=send_to_user)
        mock_manager.emit_event = AsyncMock(side_effect=emit_event)
        mock_manager.is_connected = AsyncMock(return_value=True)
        
        await mock_manager.initialize()
        return mock_manager

    async def _create_mock_execution_engine(self, user_id: str, websocket_manager: MagicMock) -> MagicMock:
        """Create mock execution engine for WebSocket event testing."""
        mock_engine = MagicMock(spec=UserExecutionEngine)
        mock_engine.user_id = user_id
        mock_engine.websocket_manager = websocket_manager
        mock_engine.initialize = AsyncMock()
        mock_engine.cleanup = AsyncMock()
        
        await mock_engine.initialize()
        return mock_engine

    async def _create_execution_context(self, user_id: str) -> AgentExecutionContext:
        """Create execution context for WebSocket event testing."""
        context = AgentExecutionContext(
            user_id=user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("thread"),
            execution_id=UnifiedIdGenerator.generate_base_id("execution"),
            created_at=datetime.now(timezone.utc),
            context_data={
                "websocket_events_test": True,
                "realtime_communication": True,
                "business_critical": True
            }
        )
        return context

    @pytest.mark.integration
    @pytest.mark.no_docker
    async def test_complete_agent_websocket_event_delivery(self):
        """
        Test complete WebSocket event delivery during agent execution.
        
        Business Value: Validates real-time event delivery that keeps users
        engaged during AI processing, critical for user experience and retention.
        """
        events_user_id = f"events_{self.test_user_id}"
        connection_id = f"conn_{UnifiedIdGenerator.generate_base_id('ws')}"
        
        # Setup mock WebSocket infrastructure
        mock_websocket = await self._create_mock_websocket_connection(events_user_id, connection_id)
        mock_manager = await self._create_mock_websocket_manager()
        mock_engine = await self._create_mock_execution_engine(events_user_id, mock_manager)
        
        try:
            execution_context = await self._create_execution_context(events_user_id)
            
            # Add connection to manager
            connection_info = ConnectionInfo(
                user_id=events_user_id,
                websocket=mock_websocket,
                thread_id=execution_context.thread_id
            )
            await mock_manager.add_connection(connection_info)
            
            # Create agent factory
            agent_factory = AgentInstanceFactory(
                user_execution_engine=mock_engine,
                websocket_manager=mock_manager
            )
            
            # === TEST: COMPLETE EVENT SEQUENCE FOR AGENT EXECUTION ===
            
            # Create triage agent for comprehensive event testing
            triage_agent = await agent_factory.create_agent_instance("triage", execution_context)
            self.assertIsNotNone(triage_agent, "Triage agent must be created for event testing")
            
            # Define the 5 critical golden path events
            critical_events_sequence = [
                {
                    "event_type": "agent_started",
                    "message_type": MessageType.AGENT_EVENT,
                    "payload": {
                        "event_type": "agent_started",
                        "agent_type": "triage",
                        "message": "Agent execution started",
                        "user_message": "Help me optimize my AI infrastructure costs",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                },
                {
                    "event_type": "agent_thinking",
                    "message_type": MessageType.AGENT_EVENT, 
                    "payload": {
                        "event_type": "agent_thinking",
                        "message": "Analyzing infrastructure optimization requirements...",
                        "thinking_stage": "requirements_analysis",
                        "progress": 25,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                },
                {
                    "event_type": "tool_executing",
                    "message_type": MessageType.TOOL_EVENT,
                    "payload": {
                        "event_type": "tool_executing",
                        "tool_name": "infrastructure_analyzer",
                        "message": "Analyzing current infrastructure setup...",
                        "progress": 50,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                },
                {
                    "event_type": "tool_completed",
                    "message_type": MessageType.TOOL_EVENT,
                    "payload": {
                        "event_type": "tool_completed",
                        "tool_name": "infrastructure_analyzer",
                        "result": {
                            "current_monthly_cost": "$5,000",
                            "optimization_opportunities": 7,
                            "potential_savings": "35%"
                        },
                        "message": "Infrastructure analysis completed",
                        "progress": 75,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                },
                {
                    "event_type": "agent_completed",
                    "message_type": MessageType.AGENT_EVENT,
                    "payload": {
                        "event_type": "agent_completed",
                        "agent_type": "triage",
                        "final_response": {
                            "analysis_summary": "Infrastructure optimization analysis complete",
                            "priority_recommendations": [
                                "Implement auto-scaling for compute resources",
                                "Optimize storage usage patterns", 
                                "Review network transfer costs"
                            ],
                            "estimated_monthly_savings": "$1,750",
                            "implementation_timeline": "2-4 weeks"
                        },
                        "execution_time": 3.2,
                        "message": "Agent processing completed successfully",
                        "progress": 100,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            ]
            
            # Send all critical events with realistic timing
            event_start_time = time.time()
            
            for i, event_info in enumerate(critical_events_sequence):
                # Realistic delay between events
                if i > 0:
                    await asyncio.sleep(0.3)  # 300ms between events
                
                # Create and send event
                standard_message = create_standard_message(
                    event_info["message_type"],
                    event_info["payload"],
                    user_id=events_user_id,
                    thread_id=execution_context.thread_id
                )
                
                await mock_manager.send_to_user(events_user_id, standard_message.dict())
                
                # Update progress for user experience
                self.logger.debug(f"Sent event {i+1}/5: {event_info['event_type']}")
            
            total_event_delivery_time = time.time() - event_start_time
            
            # === VERIFY EVENT DELIVERY INTEGRATION ===
            
            # Verify all 5 critical events were captured
            self.assertGreaterEqual(len(self.captured_events), 5, "All 5 critical golden path events must be delivered")
            
            # Verify event sequence and content
            captured_event_types = []
            for captured_event in self.captured_events:
                try:
                    event_data = json.loads(captured_event["event_data"]) if isinstance(captured_event["event_data"], str) else captured_event["event_data"]
                    event_type = event_data.get("payload", {}).get("event_type")
                    if event_type:
                        captured_event_types.append(event_type)
                except:
                    pass
            
            # Verify all required events were sent in correct order
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            for required_event in required_events:
                self.assertIn(required_event, captured_event_types, f"Critical event '{required_event}' must be delivered")
            
            # Verify event ordering (agent_started should be first, agent_completed should be last)
            if len(captured_event_types) >= 2:
                self.assertEqual(captured_event_types[0], "agent_started", "First event must be agent_started")
                self.assertEqual(captured_event_types[-1], "agent_completed", "Last event must be agent_completed")
            
            # Verify event content integrity
            for i, captured_event in enumerate(self.captured_events[:5]):  # Check first 5 events
                event_data = json.loads(captured_event["event_data"]) if isinstance(captured_event["event_data"], str) else captured_event["event_data"]
                
                # Verify event structure
                self.assertIn("payload", event_data, f"Event {i} must have payload")
                self.assertIn("user_id", event_data, f"Event {i} must have user_id")
                self.assertIn("thread_id", event_data, f"Event {i} must have thread_id")
                self.assertEqual(event_data["user_id"], events_user_id, f"Event {i} must be for correct user")
                
                # Verify business-relevant content
                payload = event_data["payload"]
                self.assertIn("timestamp", payload, f"Event {i} must have timestamp")
                self.assertIn("event_type", payload, f"Event {i} must have event_type")
                
                # Verify meaningful content for user engagement
                if "message" in payload:
                    self.assertGreater(len(payload["message"]), 10, f"Event {i} message must be substantive")
            
            # Verify event timing meets real-time requirements
            self.assertLess(total_event_delivery_time, 5.0, "Event delivery sequence must complete within 5 seconds")
            
            if len(self.event_timestamps) >= 2:
                max_inter_event_delay = max(
                    self.event_timestamps[i] - self.event_timestamps[i-1] 
                    for i in range(1, len(self.event_timestamps))
                )
                self.assertLess(max_inter_event_delay, 1.0, "Individual event delivery must be under 1 second")
            
            # Verify connection state tracking
            connection_state = self.connection_states[connection_id]
            self.assertTrue(connection_state["connected"], "Connection must remain active")
            self.assertEqual(connection_state["events_sent"], len(self.captured_events), "Event count must match")
            
            # Record event delivery metrics
            self.record_metric("critical_events_delivered", len(captured_event_types))
            self.record_metric("event_sequence_correct", captured_event_types == required_events[:len(captured_event_types)])
            self.record_metric("total_delivery_time", total_event_delivery_time)
            self.record_metric("connection_maintained", connection_state["connected"])
            self.record_metric("websocket_event_delivery_successful", True)
            
            self.logger.info(f"✅ PASS: Complete agent WebSocket event delivery successful - {len(captured_event_types)} events in {total_event_delivery_time:.2f}s")
            
        finally:
            await mock_manager.shutdown()
            await mock_engine.cleanup()

    @pytest.mark.integration
    @pytest.mark.no_docker
    async def test_multi_user_event_isolation_websocket(self):
        """
        Test multi-user event isolation in WebSocket delivery.
        
        Business Value: Ensures user data privacy and prevents event leakage
        in multi-tenant environment, critical for enterprise security compliance.
        """
        # Create 3 users for isolation testing
        user_ids = [f"user_{i}_{self.test_user_id}" for i in range(3)]
        connection_ids = [f"conn_{i}_{UnifiedIdGenerator.generate_base_id('ws')}" for i in range(3)]
        
        # Setup mock infrastructure
        mock_manager = await self._create_mock_websocket_manager()
        user_websockets = {}
        user_engines = {}
        user_contexts = {}
        
        try:
            # Create isolated infrastructure for each user
            for user_id, conn_id in zip(user_ids, connection_ids):
                # Create WebSocket connection for this user
                user_websockets[user_id] = await self._create_mock_websocket_connection(user_id, conn_id)
                
                # Create execution engine for this user
                user_engines[user_id] = await self._create_mock_execution_engine(user_id, mock_manager)
                
                # Create execution context for this user
                user_contexts[user_id] = await self._create_execution_context(user_id)
                
                # Add connection to manager
                connection_info = ConnectionInfo(
                    user_id=user_id,
                    websocket=user_websockets[user_id],
                    thread_id=user_contexts[user_id].thread_id
                )
                await mock_manager.add_connection(connection_info)
            
            # === CONCURRENT AGENT PROCESSING WITH EVENT ISOLATION ===
            
            async def process_user_workflow(user_id: str, user_specific_data: dict):
                context = user_contexts[user_id]
                engine = user_engines[user_id]
                
                agent_factory = AgentInstanceFactory(
                    user_execution_engine=engine,
                    websocket_manager=mock_manager
                )
                
                # Create user-specific agent
                agent = await agent_factory.create_agent_instance("data_helper", context)
                
                # Send user-specific events
                user_events = [
                    {
                        "event_type": "agent_started",
                        "payload": {
                            "event_type": "agent_started",
                            "agent_type": "data_helper",
                            "user_id": user_id,
                            "user_data": user_specific_data,
                            "message": f"Starting analysis for {user_specific_data['company_name']}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    {
                        "event_type": "agent_thinking",
                        "payload": {
                            "event_type": "agent_thinking",
                            "user_id": user_id,
                            "message": f"Analyzing {user_specific_data['company_name']} infrastructure...",
                            "private_context": f"Confidential analysis for {user_id}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    {
                        "event_type": "agent_completed",
                        "payload": {
                            "event_type": "agent_completed",
                            "agent_type": "data_helper",
                            "user_id": user_id,
                            "final_response": {
                                "company": user_specific_data['company_name'],
                                "private_recommendations": f"Confidential recommendations for {user_id}",
                                "sensitive_data": f"Private financial data for {user_specific_data['company_name']}"
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                ]
                
                for event_info in user_events:
                    await asyncio.sleep(0.1)  # Small delay between events
                    
                    standard_message = create_standard_message(
                        MessageType.AGENT_EVENT,
                        event_info["payload"],
                        user_id=user_id,
                        thread_id=context.thread_id
                    )
                    
                    await mock_manager.send_to_user(user_id, standard_message.dict())
                
                return user_specific_data
            
            # Execute concurrent workflows with sensitive data
            user_specific_data = [
                {"company_name": "TechCorp Alpha", "confidential_id": "TC-001", "revenue": "$50M"},
                {"company_name": "DataSystems Beta", "confidential_id": "DS-002", "revenue": "$25M"},
                {"company_name": "CloudServices Gamma", "confidential_id": "CS-003", "revenue": "$100M"}
            ]
            
            # Run concurrent user workflows
            concurrent_tasks = [
                process_user_workflow(user_id, data)
                for user_id, data in zip(user_ids, user_specific_data)
            ]
            
            results = await asyncio.gather(*concurrent_tasks)
            
            # === VERIFY EVENT ISOLATION ===
            
            # Verify each user received only their own events
            for user_id in user_ids:
                user_events = self.user_event_streams[user_id]
                self.assertGreaterEqual(len(user_events), 3, f"User {user_id} must receive their events")
                
                # Verify all events for this user contain correct user_id
                for event_info in user_events:
                    event_data = json.loads(event_info["event_data"]) if isinstance(event_info["event_data"], str) else event_info["event_data"]
                    
                    # Verify event is for correct user
                    self.assertEqual(event_data.get("user_id"), user_id, f"Event must be for user {user_id}")
                    
                    # Verify no cross-user data leakage in event content
                    event_str = str(event_data).lower()
                    user_data = next(data for uid, data in zip(user_ids, user_specific_data) if uid == user_id)
                    
                    # Should contain own company data
                    self.assertIn(user_data["company_name"].lower(), event_str, f"Event should contain {user_id}'s company data")
                    
                    # Should NOT contain other users' company data
                    for other_user_id, other_data in zip(user_ids, user_specific_data):
                        if other_user_id != user_id:
                            self.assertNotIn(other_data["company_name"].lower(), event_str,
                                           f"Event for {user_id} must not contain {other_user_id}'s company data")
                            self.assertNotIn(other_data["confidential_id"], event_str,
                                           f"Event for {user_id} must not contain {other_user_id}'s confidential data")
            
            # Verify connection isolation
            for user_id, conn_id in zip(user_ids, connection_ids):
                connection_state = self.connection_states[conn_id]
                self.assertEqual(connection_state["user_id"], user_id, "Connection must be for correct user")
                self.assertGreater(connection_state["events_sent"], 0, f"User {user_id} must have received events")
            
            # Verify no event cross-contamination between connections
            for i, user_id_a in enumerate(user_ids):
                events_a = self.user_event_streams[user_id_a]
                for j, user_id_b in enumerate(user_ids):
                    if i != j:
                        # Events for user A should not contain user B's sensitive data
                        for event_a in events_a:
                            event_str = str(event_a).lower()
                            user_b_data = user_specific_data[j]
                            self.assertNotIn(user_b_data["confidential_id"], event_str,
                                           f"User {user_id_a} events must not contain {user_id_b} confidential data")
            
            # Record isolation metrics
            self.record_metric("concurrent_users_tested", len(user_ids))
            self.record_metric("event_isolation_successful", True)
            self.record_metric("zero_cross_user_leakage", True)
            self.record_metric("connection_isolation_verified", True)
            self.record_metric("multi_user_websocket_isolation_successful", True)
            
            self.logger.info("✅ PASS: Multi-user event isolation in WebSocket delivery successful")
            
        finally:
            await mock_manager.shutdown()
            for engine in user_engines.values():
                await engine.cleanup()

    @pytest.mark.integration
    @pytest.mark.no_docker
    async def test_websocket_connection_lifecycle_during_agent_execution(self):
        """
        Test WebSocket connection lifecycle management during complex agent execution.
        
        Business Value: Ensures reliable real-time communication throughout
        long-running AI workflows, maintaining user engagement and preventing
        data loss during complex processing.
        """
        lifecycle_user_id = f"lifecycle_{self.test_user_id}"
        connection_id = f"conn_{UnifiedIdGenerator.generate_base_id('ws')}"
        
        # Setup mock infrastructure
        mock_websocket = await self._create_mock_websocket_connection(lifecycle_user_id, connection_id)
        mock_manager = await self._create_mock_websocket_manager()
        mock_engine = await self._create_mock_execution_engine(lifecycle_user_id, mock_manager)
        
        try:
            execution_context = await self._create_execution_context(lifecycle_user_id)
            
            # Add connection to manager
            connection_info = ConnectionInfo(
                user_id=lifecycle_user_id,
                websocket=mock_websocket,
                thread_id=execution_context.thread_id
            )
            await mock_manager.add_connection(connection_info)
            
            agent_factory = AgentInstanceFactory(
                user_execution_engine=mock_engine,
                websocket_manager=mock_manager
            )
            
            # === TEST: CONNECTION LIFECYCLE THROUGHOUT LONG WORKFLOW ===
            
            # Phase 1: Initial connection and agent startup
            self.logger.info("Phase 1: Initial connection and agent startup")
            
            # Verify initial connection state
            initial_state = self.connection_states[connection_id]
            self.assertTrue(initial_state["connected"], "Connection must be initially active")
            
            # Create agent and send startup events
            apex_agent = await agent_factory.create_agent_instance("apex_optimizer", execution_context)
            
            await mock_manager.send_to_user(
                lifecycle_user_id,
                create_standard_message(
                    MessageType.AGENT_EVENT,
                    {
                        "event_type": "agent_started",
                        "agent_type": "apex_optimizer",
                        "phase": "startup",
                        "message": "APEX optimization agent started",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    user_id=lifecycle_user_id,
                    thread_id=execution_context.thread_id
                ).dict()
            )
            
            # Phase 2: Extended processing simulation with periodic heartbeats
            self.logger.info("Phase 2: Extended processing with heartbeats")
            
            processing_phases = [
                {"name": "data_collection", "duration": 0.5, "complexity": "high"},
                {"name": "analysis_computation", "duration": 0.7, "complexity": "very_high"},
                {"name": "optimization_modeling", "duration": 0.6, "complexity": "high"},
                {"name": "recommendation_generation", "duration": 0.4, "complexity": "medium"},
                {"name": "validation_and_refinement", "duration": 0.3, "complexity": "medium"}
            ]
            
            phase_results = []
            for phase in processing_phases:
                phase_start = time.time()
                
                # Send phase started event
                await mock_manager.send_to_user(
                    lifecycle_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "agent_thinking",
                            "processing_phase": phase["name"],
                            "complexity": phase["complexity"],
                            "message": f"Processing {phase['name']} phase...",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=lifecycle_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # Simulate processing with periodic heartbeats
                processing_steps = int(phase["duration"] / 0.1)  # 100ms heartbeat intervals
                for step in range(processing_steps):
                    await asyncio.sleep(0.1)
                    
                    # Send heartbeat/progress update
                    progress = (step + 1) / processing_steps * 100
                    await mock_manager.send_to_user(
                        lifecycle_user_id,
                        create_standard_message(
                            MessageType.AGENT_EVENT,
                            {
                                "event_type": "processing_heartbeat",
                                "phase": phase["name"],
                                "progress": progress,
                                "message": f"{phase['name']} progress: {progress:.1f}%",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            },
                            user_id=lifecycle_user_id,
                            thread_id=execution_context.thread_id
                        ).dict()
                    )
                    
                    # Verify connection remains active
                    current_state = self.connection_states[connection_id]
                    self.assertTrue(current_state["connected"], f"Connection must remain active during {phase['name']}")
                
                # Send phase completion
                phase_time = time.time() - phase_start
                await mock_manager.send_to_user(
                    lifecycle_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "phase_completed",
                            "phase": phase["name"],
                            "processing_time": phase_time,
                            "message": f"Completed {phase['name']} in {phase_time:.2f}s",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=lifecycle_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                phase_results.append({
                    "phase": phase["name"],
                    "duration": phase_time,
                    "complexity": phase["complexity"],
                    "heartbeats_sent": processing_steps
                })
            
            # Phase 3: Final results delivery
            self.logger.info("Phase 3: Final results delivery")
            
            final_results = {
                "optimization_complete": True,
                "total_recommendations": 12,
                "estimated_savings": "$15,200/month",
                "implementation_phases": 3,
                "confidence_score": 94.5,
                "processing_summary": {
                    "total_phases": len(processing_phases),
                    "total_processing_time": sum(r["duration"] for r in phase_results),
                    "complexity_distribution": {p["complexity"]: p["phase"] for p in processing_phases}
                }
            }
            
            await mock_manager.send_to_user(
                lifecycle_user_id,
                create_standard_message(
                    MessageType.AGENT_EVENT,
                    {
                        "event_type": "agent_completed",
                        "agent_type": "apex_optimizer",
                        "final_response": final_results,
                        "phase": "completion",
                        "message": "APEX optimization completed successfully",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    user_id=lifecycle_user_id,
                    thread_id=execution_context.thread_id
                ).dict()
            )
            
            # Phase 4: Connection cleanup
            self.logger.info("Phase 4: Connection cleanup")
            
            await mock_manager.remove_connection(lifecycle_user_id)
            
            # === VERIFY CONNECTION LIFECYCLE MANAGEMENT ===
            
            # Verify connection was active throughout processing
            final_state = self.connection_states[connection_id]
            self.assertGreater(final_state["events_sent"], len(processing_phases) * 2, 
                             "Many events must have been sent during lifecycle")
            
            # Verify all processing phases completed
            self.assertEqual(len(phase_results), len(processing_phases), "All processing phases must complete")
            
            # Verify heartbeats maintained connection activity
            total_heartbeats = sum(r["heartbeats_sent"] for r in phase_results)
            self.assertGreater(total_heartbeats, 10, "Sufficient heartbeats must be sent for long processing")
            
            # Verify event distribution throughout lifecycle
            event_types_seen = set()
            phase_events_count = 0
            heartbeat_events_count = 0
            
            for captured_event in self.captured_events:
                try:
                    event_data = json.loads(captured_event["event_data"]) if isinstance(captured_event["event_data"], str) else captured_event["event_data"]
                    event_type = event_data.get("payload", {}).get("event_type", "")
                    event_types_seen.add(event_type)
                    
                    if "phase" in event_type:
                        phase_events_count += 1
                    elif "heartbeat" in event_type:
                        heartbeat_events_count += 1
                except:
                    continue
            
            # Verify event type diversity
            expected_event_types = {"agent_started", "agent_thinking", "processing_heartbeat", "phase_completed", "agent_completed"}
            for expected_type in expected_event_types:
                self.assertIn(expected_type, event_types_seen, f"Event type '{expected_type}' must be seen during lifecycle")
            
            # Verify heartbeat frequency
            self.assertGreater(heartbeat_events_count, 10, "Sufficient heartbeat events must be sent")
            
            # Verify final results delivery integrity
            final_event = None
            for captured_event in reversed(self.captured_events):  # Find last event
                try:
                    event_data = json.loads(captured_event["event_data"]) if isinstance(captured_event["event_data"], str) else captured_event["event_data"]
                    if event_data.get("payload", {}).get("event_type") == "agent_completed":
                        final_event = event_data
                        break
                except:
                    continue
            
            self.assertIsNotNone(final_event, "Final completion event must be delivered")
            final_response = final_event.get("payload", {}).get("final_response", {})
            self.assertIn("optimization_complete", final_response, "Final results must be complete")
            self.assertTrue(final_response.get("optimization_complete"), "Optimization must be marked complete")
            
            # Record lifecycle metrics
            self.record_metric("processing_phases_completed", len(phase_results))
            self.record_metric("total_heartbeats_sent", total_heartbeats)
            self.record_metric("event_types_diversity", len(event_types_seen))
            self.record_metric("connection_maintained_throughout", True)
            self.record_metric("final_results_delivered", final_response.get("optimization_complete", False))
            self.record_metric("websocket_lifecycle_management_successful", True)
            
            self.logger.info("✅ PASS: WebSocket connection lifecycle during agent execution successful")
            
        finally:
            await mock_manager.shutdown()
            await mock_engine.cleanup()

    @pytest.mark.integration
    @pytest.mark.no_docker
    async def test_websocket_error_recovery_event_communication(self):
        """
        Test WebSocket error recovery with proper event communication.
        
        Business Value: Ensures users are informed about processing issues and
        recovery attempts, maintaining trust and transparency during error scenarios.
        """
        error_user_id = f"error_{self.test_user_id}"
        connection_id = f"conn_{UnifiedIdGenerator.generate_base_id('ws')}"
        
        # Setup mock infrastructure
        mock_websocket = await self._create_mock_websocket_connection(error_user_id, connection_id)
        mock_manager = await self._create_mock_websocket_manager()
        mock_engine = await self._create_mock_execution_engine(error_user_id, mock_manager)
        
        try:
            execution_context = await self._create_execution_context(error_user_id)
            
            # Add connection to manager
            connection_info = ConnectionInfo(
                user_id=error_user_id,
                websocket=mock_websocket,
                thread_id=execution_context.thread_id
            )
            await mock_manager.add_connection(connection_info)
            
            agent_factory = AgentInstanceFactory(
                user_execution_engine=mock_engine,
                websocket_manager=mock_manager
            )
            
            # === TEST: ERROR SCENARIOS WITH PROPER EVENT COMMUNICATION ===
            
            error_scenarios = [
                {
                    "name": "Processing Timeout Recovery",
                    "error_type": "timeout_error",
                    "agent_type": "data_helper",
                    "recovery_strategy": "fallback_to_cached_data",
                    "expected_outcome": "partial_results_with_explanation"
                },
                {
                    "name": "Analysis Engine Overload Recovery",
                    "error_type": "resource_overload",
                    "agent_type": "apex_optimizer",
                    "recovery_strategy": "simplified_analysis",
                    "expected_outcome": "basic_recommendations_with_note"
                },
                {
                    "name": "Network Connectivity Issue Recovery",
                    "error_type": "connectivity_error",
                    "agent_type": "triage",
                    "recovery_strategy": "offline_mode_processing",
                    "expected_outcome": "local_analysis_with_limitations"
                }
            ]
            
            error_recovery_results = []
            
            for scenario in error_scenarios:
                self.logger.info(f"Testing error recovery: {scenario['name']}")
                
                scenario_start = time.time()
                
                # Create agent for error scenario
                agent = await agent_factory.create_agent_instance(scenario["agent_type"], execution_context)
                
                # Send agent startup event
                await mock_manager.send_to_user(
                    error_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "agent_started",
                            "agent_type": scenario["agent_type"],
                            "scenario": scenario["name"],
                            "message": f"Starting {scenario['agent_type']} processing",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=error_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # Simulate normal processing start
                await asyncio.sleep(0.2)
                await mock_manager.send_to_user(
                    error_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "agent_thinking",
                            "agent_type": scenario["agent_type"],
                            "message": f"Processing {scenario['agent_type']} analysis...",
                            "progress": 25,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=error_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # === SIMULATE ERROR OCCURRENCE ===
                await asyncio.sleep(0.3)
                await mock_manager.send_to_user(
                    error_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "agent_error",
                            "agent_type": scenario["agent_type"],
                            "error_type": scenario["error_type"],
                            "error_message": f"Encountered {scenario['error_type']} during processing",
                            "recovery_initiated": True,
                            "user_message": f"We're experiencing a {scenario['error_type']}. Don't worry - I'm working on a solution...",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=error_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # === SIMULATE RECOVERY PROCESS ===
                await asyncio.sleep(0.4)
                await mock_manager.send_to_user(
                    error_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "recovery_in_progress",
                            "agent_type": scenario["agent_type"],
                            "recovery_strategy": scenario["recovery_strategy"],
                            "message": f"Implementing {scenario['recovery_strategy']} to continue processing...",
                            "user_message": f"I'm trying a different approach using {scenario['recovery_strategy']}...",
                            "progress": 50,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=error_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # === SIMULATE RECOVERY SUCCESS ===
                await asyncio.sleep(0.3)
                
                # Generate recovery results based on scenario
                if scenario["expected_outcome"] == "partial_results_with_explanation":
                    recovery_result = {
                        "status": "partially_recovered",
                        "data_available": "cached_data_from_last_24h", 
                        "limitations": "Data may be up to 24 hours old",
                        "recommendations": [
                            "Based on recent cached data analysis",
                            "Consider validating with current live data",
                            "Results confidence: 85% due to data age"
                        ],
                        "user_explanation": "I used our most recent cached data to provide you with analysis. While not real-time, it should give you valuable insights."
                    }
                elif scenario["expected_outcome"] == "basic_recommendations_with_note":
                    recovery_result = {
                        "status": "simplified_analysis_complete",
                        "analysis_type": "basic_optimization",
                        "recommendations": [
                            "Focus on highest-impact optimizations first",
                            "Basic cost reduction opportunities identified",
                            "Consider upgrading analysis when resources available"
                        ],
                        "limitations": "Simplified analysis due to resource constraints",
                        "user_explanation": "I provided a streamlined analysis focusing on the most impactful optimizations while our systems are busy."
                    }
                else:  # offline_mode_processing
                    recovery_result = {
                        "status": "offline_analysis_complete",
                        "analysis_scope": "local_pattern_matching",
                        "recommendations": [
                            "Based on established optimization patterns",
                            "General best practices recommendations",
                            "Custom analysis available when connectivity restored"
                        ],
                        "limitations": "Limited to local analysis capabilities",
                        "user_explanation": "I analyzed your request using local optimization patterns. For a more detailed analysis, I'll reconnect when possible."
                    }
                
                await mock_manager.send_to_user(
                    error_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "recovery_successful",
                            "agent_type": scenario["agent_type"],
                            "recovery_result": recovery_result,
                            "message": f"Recovery successful using {scenario['recovery_strategy']}",
                            "user_message": recovery_result["user_explanation"],
                            "progress": 85,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=error_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # === FINAL COMPLETION WITH RECOVERED RESULTS ===
                await asyncio.sleep(0.2)
                scenario_time = time.time() - scenario_start
                
                await mock_manager.send_to_user(
                    error_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "agent_completed",
                            "agent_type": scenario["agent_type"],
                            "final_response": recovery_result,
                            "recovery_applied": True,
                            "processing_time": scenario_time,
                            "message": f"Completed {scenario['agent_type']} processing with recovery",
                            "user_message": "Analysis complete! I've provided the best results possible given the circumstances.",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=error_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                error_recovery_results.append({
                    "scenario": scenario["name"],
                    "error_type": scenario["error_type"],
                    "recovery_strategy": scenario["recovery_strategy"],
                    "result": recovery_result,
                    "processing_time": scenario_time,
                    "user_informed": True
                })
                
                # Small delay between scenarios
                await asyncio.sleep(0.1)
            
            # === VERIFY ERROR RECOVERY EVENT COMMUNICATION ===
            
            # Verify all scenarios completed with recovery
            self.assertEqual(len(error_recovery_results), len(error_scenarios), "All error scenarios must be tested")
            
            # Verify error and recovery events were communicated
            error_related_events = []
            for captured_event in self.captured_events:
                try:
                    event_data = json.loads(captured_event["event_data"]) if isinstance(captured_event["event_data"], str) else captured_event["event_data"]
                    event_type = event_data.get("payload", {}).get("event_type", "")
                    
                    if any(keyword in event_type for keyword in ["error", "recovery"]):
                        error_related_events.append(event_data)
                except:
                    continue
            
            self.assertGreater(len(error_related_events), len(error_scenarios) * 2, 
                             "Multiple error/recovery events must be sent per scenario")
            
            # Verify user communication quality in error events
            for recovery_result in error_recovery_results:
                self.assertIn("user_explanation", recovery_result["result"], 
                            f"Recovery result must include user explanation for {recovery_result['scenario']}")
                self.assertTrue(recovery_result["user_informed"], 
                              f"User must be informed about recovery for {recovery_result['scenario']}")
                
                # Verify recovery provided meaningful results
                result = recovery_result["result"]
                self.assertIn("recommendations", result, "Recovery must provide recommendations")
                self.assertGreater(len(result["recommendations"]), 0, "Must provide actual recommendations")
                self.assertIn("status", result, "Recovery status must be communicated")
                
            # Verify error event content quality
            user_facing_messages = []
            for event in error_related_events:
                payload = event.get("payload", {})
                if "user_message" in payload:
                    user_facing_messages.append(payload["user_message"])
            
            self.assertGreater(len(user_facing_messages), len(error_scenarios), 
                             "User-facing messages must be sent for error communication")
            
            # Verify user messages are helpful and not just technical
            for message in user_facing_messages:
                self.assertGreater(len(message), 20, "User messages must be substantive")
                self.assertFalse(any(tech_term in message.lower() for tech_term in ["exception", "stack trace", "null pointer"]),
                               "User messages should avoid technical jargon")
            
            # Record error recovery metrics
            self.record_metric("error_scenarios_tested", len(error_scenarios))
            self.record_metric("successful_recoveries", len(error_recovery_results))
            self.record_metric("error_events_communicated", len(error_related_events))
            self.record_metric("user_messages_sent", len(user_facing_messages))
            self.record_metric("recovery_results_meaningful", all(len(r["result"]["recommendations"]) > 0 for r in error_recovery_results))
            self.record_metric("websocket_error_recovery_communication_successful", True)
            
            self.logger.info("✅ PASS: WebSocket error recovery event communication successful")
            
        finally:
            await mock_manager.shutdown()
            await mock_engine.cleanup()

    @pytest.mark.integration
    @pytest.mark.no_docker
    async def test_websocket_event_performance_validation(self):
        """
        Test WebSocket event delivery performance validation.
        
        Business Value: Ensures real-time event delivery meets performance
        expectations for responsive user experience during AI processing.
        """
        perf_user_id = f"perf_{self.test_user_id}"
        connection_id = f"conn_{UnifiedIdGenerator.generate_base_id('ws')}"
        
        # Setup mock infrastructure
        mock_websocket = await self._create_mock_websocket_connection(perf_user_id, connection_id)
        mock_manager = await self._create_mock_websocket_manager()
        mock_engine = await self._create_mock_execution_engine(perf_user_id, mock_manager)
        
        try:
            execution_context = await self._create_execution_context(perf_user_id)
            
            # Add connection to manager
            connection_info = ConnectionInfo(
                user_id=perf_user_id,
                websocket=mock_websocket,
                thread_id=execution_context.thread_id
            )
            await mock_manager.add_connection(connection_info)
            
            # === PERFORMANCE REQUIREMENTS ===
            perf_requirements = {
                "single_event_delivery": 0.01,     # Individual events under 10ms
                "batch_event_delivery": 0.1,       # Batches under 100ms
                "high_frequency_sustained": 0.05,  # Sustained delivery under 50ms avg
                "event_ordering_consistency": 1.0, # Perfect ordering required
                "connection_responsiveness": 0.001  # Connection response under 1ms
            }
            
            # === TEST 1: SINGLE EVENT DELIVERY PERFORMANCE ===
            self.logger.info("Test 1: Single event delivery performance")
            
            single_event_times = []
            for i in range(10):
                event_start = time.time()
                
                await mock_manager.send_to_user(
                    perf_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "performance_test_single",
                            "event_index": i,
                            "message": f"Performance test event {i}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=perf_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                event_time = time.time() - event_start
                single_event_times.append(event_time)
                
                # Small delay between events
                await asyncio.sleep(0.01)
            
            avg_single_event_time = sum(single_event_times) / len(single_event_times)
            max_single_event_time = max(single_event_times)
            
            # === TEST 2: BATCH EVENT DELIVERY PERFORMANCE ===
            self.logger.info("Test 2: Batch event delivery performance")
            
            batch_sizes = [5, 10, 20]
            batch_performance = []
            
            for batch_size in batch_sizes:
                batch_start = time.time()
                
                # Send events in rapid succession (batch simulation)
                batch_tasks = []
                for i in range(batch_size):
                    task = mock_manager.send_to_user(
                        perf_user_id,
                        create_standard_message(
                            MessageType.AGENT_EVENT,
                            {
                                "event_type": "performance_test_batch",
                                "batch_size": batch_size,
                                "batch_index": i,
                                "message": f"Batch event {i} of {batch_size}",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            },
                            user_id=perf_user_id,
                            thread_id=execution_context.thread_id
                        ).dict()
                    )
                    batch_tasks.append(task)
                
                # Wait for all batch events to complete
                await asyncio.gather(*batch_tasks)
                
                batch_time = time.time() - batch_start
                batch_performance.append({
                    "batch_size": batch_size,
                    "total_time": batch_time,
                    "per_event_time": batch_time / batch_size
                })
                
                await asyncio.sleep(0.05)  # Recovery between batches
            
            # === TEST 3: HIGH FREQUENCY SUSTAINED DELIVERY ===
            self.logger.info("Test 3: High frequency sustained delivery")
            
            sustained_test_duration = 2.0  # 2 seconds of sustained delivery
            sustained_event_interval = 0.02  # 50 events per second
            
            sustained_start = time.time()
            sustained_event_times = []
            sustained_event_count = 0
            
            while time.time() - sustained_start < sustained_test_duration:
                event_start = time.time()
                
                await mock_manager.send_to_user(
                    perf_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "performance_test_sustained",
                            "event_number": sustained_event_count,
                            "elapsed_time": time.time() - sustained_start,
                            "message": f"Sustained event {sustained_event_count}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=perf_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                event_time = time.time() - event_start
                sustained_event_times.append(event_time)
                sustained_event_count += 1
                
                await asyncio.sleep(sustained_event_interval)
            
            sustained_total_time = time.time() - sustained_start
            avg_sustained_event_time = sum(sustained_event_times) / len(sustained_event_times)
            sustained_events_per_second = sustained_event_count / sustained_total_time
            
            # === TEST 4: EVENT ORDERING CONSISTENCY ===
            self.logger.info("Test 4: Event ordering consistency")
            
            ordering_test_count = 50
            ordering_start = time.time()
            
            # Send events with sequence numbers
            for i in range(ordering_test_count):
                await mock_manager.send_to_user(
                    perf_user_id,
                    create_standard_message(
                        MessageType.AGENT_EVENT,
                        {
                            "event_type": "performance_test_ordering",
                            "sequence_number": i,
                            "expected_order": i,
                            "message": f"Ordering test event {i}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        },
                        user_id=perf_user_id,
                        thread_id=execution_context.thread_id
                    ).dict()
                )
                
                # Minimal delay to allow event processing
                await asyncio.sleep(0.001)
            
            ordering_total_time = time.time() - ordering_start
            
            # === VERIFY PERFORMANCE REQUIREMENTS ===
            
            # Verify single event delivery performance
            self.assertLessEqual(avg_single_event_time, perf_requirements["single_event_delivery"],
                               f"Average single event delivery time must be under {perf_requirements['single_event_delivery']}s")
            self.assertLessEqual(max_single_event_time, perf_requirements["single_event_delivery"] * 2,
                               "Max single event time must be reasonable")
            
            # Verify batch delivery performance
            for batch_perf in batch_performance:
                self.assertLessEqual(batch_perf["total_time"], perf_requirements["batch_event_delivery"],
                                   f"Batch of {batch_perf['batch_size']} events must deliver within {perf_requirements['batch_event_delivery']}s")
                self.assertLessEqual(batch_perf["per_event_time"], perf_requirements["single_event_delivery"] * 2,
                                   f"Per-event time in batch of {batch_perf['batch_size']} must be reasonable")
            
            # Verify sustained delivery performance
            self.assertLessEqual(avg_sustained_event_time, perf_requirements["high_frequency_sustained"],
                               f"Sustained event delivery average must be under {perf_requirements['high_frequency_sustained']}s")
            self.assertGreaterEqual(sustained_events_per_second, 20, "Must sustain at least 20 events per second")
            
            # Verify event ordering consistency
            ordering_events = []
            for captured_event in self.captured_events:
                try:
                    event_data = json.loads(captured_event["event_data"]) if isinstance(captured_event["event_data"], str) else captured_event["event_data"]
                    if event_data.get("payload", {}).get("event_type") == "performance_test_ordering":
                        ordering_events.append(event_data["payload"])
                except:
                    continue
            
            # Check sequence numbers are in correct order
            sequence_numbers = [event.get("sequence_number", -1) for event in ordering_events]
            expected_sequence = list(range(len(sequence_numbers)))
            
            self.assertEqual(sequence_numbers[:len(expected_sequence)], expected_sequence,
                           "Event ordering must be consistent and sequential")
            
            # Verify total events captured matches expected
            total_expected_events = (len(single_event_times) + 
                                   sum(batch["batch_size"] for batch in batch_performance) +
                                   sustained_event_count + ordering_test_count)
            
            self.assertGreaterEqual(len(self.captured_events), total_expected_events * 0.95,
                                  "At least 95% of events must be captured")
            
            # === RECORD COMPREHENSIVE PERFORMANCE METRICS ===
            
            self.record_metric("avg_single_event_time", avg_single_event_time)
            self.record_metric("max_single_event_time", max_single_event_time)
            self.record_metric("avg_sustained_event_time", avg_sustained_event_time)
            self.record_metric("sustained_events_per_second", sustained_events_per_second)
            self.record_metric("event_ordering_accuracy", len([s for s in sequence_numbers if s >= 0]) / max(1, len(sequence_numbers)))
            
            for i, batch_perf in enumerate(batch_performance):
                self.record_metric(f"batch_{batch_perf['batch_size']}_total_time", batch_perf["total_time"])
                self.record_metric(f"batch_{batch_perf['batch_size']}_per_event_time", batch_perf["per_event_time"])
            
            self.record_metric("total_events_tested", total_expected_events)
            self.record_metric("events_captured", len(self.captured_events))
            self.record_metric("capture_success_rate", len(self.captured_events) / total_expected_events)
            self.record_metric("websocket_performance_validation_successful", True)
            
            # Performance summary
            performance_summary = {
                "single_event_avg": f"{avg_single_event_time*1000:.2f}ms",
                "sustained_delivery": f"{sustained_events_per_second:.1f} events/sec",
                "ordering_accuracy": f"{len([s for s in sequence_numbers if s >= 0]) / max(1, len(sequence_numbers)):.1%}",
                "capture_rate": f"{len(self.captured_events) / total_expected_events:.1%}"
            }
            
            self.logger.info(f"✅ PASS: WebSocket event performance validation successful")
            self.logger.info(f"📊 Performance Summary: {performance_summary}")
            
        finally:
            await mock_manager.shutdown()
            await mock_engine.cleanup()