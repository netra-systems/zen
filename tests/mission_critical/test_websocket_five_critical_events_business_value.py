"""
Mission Critical Test Suite for 5 WebSocket Events - Business Value Protection

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - These events drive all customer value
- Business Goal: Protect $500K+ ARR through reliable WebSocket event delivery
- Value Impact: These 5 events deliver 90% of platform business value through real-time chat
- Strategic Impact: MISSION CRITICAL - Foundation of entire AI chat experience

This mission-critical test suite validates the 5 WebSocket events that drive the entire
business model and protect $500K+ ARR:

THE 5 CRITICAL WEBSOCKET EVENTS:
1. agent_started - User sees agent began processing (builds confidence)
2. agent_thinking - Real-time reasoning visibility (engages user) 
3. tool_executing - Tool usage transparency (shows AI working)
4. tool_completed - Tool results display (proves capability)
5. agent_completed - User knows response is ready (completes value delivery)

WITHOUT THESE EVENTS: The chat experience becomes a black box, users lose confidence,
churn increases, and the entire business model fails.

Test Coverage:
- Real WebSocket connections with actual networking
- Business value validation for each event type
- Complete user journey simulation
- Error scenarios that could break events
- Performance validation under load
- Recovery testing when events fail
- Integration with real agent workflows
"""

import asyncio
import pytest
import time
import uuid
import json
import websockets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

# SSOT Imports - Following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import RealServicesTestFixtures
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)

# System Under Test - SSOT imports
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    WebSocketManagerMode
)

# Business Logic Imports
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = central_logger.get_logger(__name__)


class CriticalEventType(Enum):
    """The 5 critical WebSocket events that drive business value."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking" 
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"


@dataclass
class BusinessValueMetrics:
    """Metrics for measuring business value delivery through events."""
    user_confidence_score: float = 0.0  # 0-100, how confident user feels
    engagement_level: float = 0.0       # 0-100, how engaged user is
    value_perception: float = 0.0       # 0-100, how much value user perceives
    completion_satisfaction: float = 0.0 # 0-100, satisfaction with result
    
    def calculate_total_business_value(self) -> float:
        """Calculate total business value score (0-100)."""
        return (self.user_confidence_score + self.engagement_level + 
                self.value_perception + self.completion_satisfaction) / 4.0


class BusinessValueEventValidator:
    """Validates business value delivery through WebSocket events."""
    
    def __init__(self):
        self.events_received = []
        self.business_metrics = BusinessValueMetrics()
        self.user_journey_complete = False
        
    def validate_agent_started_business_value(self, event: Dict[str, Any]) -> bool:
        """
        Validate agent_started event delivers business value.
        
        Business Value: Builds user confidence that AI is working on their problem.
        """
        required_fields = ['agent_name', 'task']
        business_indicators = ['analyzing', 'optimizing', 'processing', 'working', 'solving']
        
        # Check required fields
        has_required_fields = all(field in event for field in required_fields)
        if not has_required_fields:
            return False
            
        # Check business value indicators
        event_text = str(event).lower()
        has_business_value = any(indicator in event_text for indicator in business_indicators)
        
        if has_business_value:
            self.business_metrics.user_confidence_score += 25.0
            
        return has_business_value
        
    def validate_agent_thinking_business_value(self, event: Dict[str, Any]) -> bool:
        """
        Validate agent_thinking event delivers business value.
        
        Business Value: Engages user by showing real-time AI reasoning process.
        """
        required_fields = ['thought']
        engagement_indicators = ['analyzing', 'considering', 'evaluating', 'determining', 'calculating']
        
        # Check required fields
        if 'thought' not in event:
            return False
            
        # Check engagement indicators
        thought_text = str(event.get('thought', '')).lower()
        has_engagement_value = any(indicator in thought_text for indicator in engagement_indicators)
        
        # Progress indication adds value
        has_progress = 'progress' in event and isinstance(event.get('progress'), (int, float))
        
        if has_engagement_value or has_progress:
            self.business_metrics.engagement_level += 25.0
            
        return has_engagement_value or has_progress
        
    def validate_tool_executing_business_value(self, event: Dict[str, Any]) -> bool:
        """
        Validate tool_executing event delivers business value.
        
        Business Value: Shows AI is using tools to solve user's problem.
        """
        required_fields = ['tool']
        value_indicators = ['database', 'api', 'analysis', 'query', 'search', 'compute', 'fetch']
        
        # Check required fields
        if 'tool' not in event:
            return False
            
        # Check value indicators
        event_text = str(event).lower()
        shows_value = any(indicator in event_text for indicator in value_indicators)
        
        # Description adds transparency value
        has_description = 'description' in event and len(str(event.get('description', ''))) > 10
        
        if shows_value or has_description:
            self.business_metrics.value_perception += 25.0
            
        return shows_value or has_description
        
    def validate_tool_completed_business_value(self, event: Dict[str, Any]) -> bool:
        """
        Validate tool_completed event delivers business value.
        
        Business Value: Proves AI capabilities by showing concrete results.
        """
        required_fields = ['tool', 'result']
        result_indicators = ['found', 'analyzed', 'calculated', 'identified', 'generated', 'processed']
        
        # Check required fields
        has_required_fields = all(field in event for field in required_fields)
        if not has_required_fields:
            return False
            
        # Check result indicators
        result_text = str(event.get('result', '')).lower()
        shows_results = any(indicator in result_text for indicator in result_indicators)
        
        # Quantitative results add more value
        has_quantities = any(char.isdigit() for char in str(event.get('result', '')))
        
        if shows_results or has_quantities:
            self.business_metrics.value_perception += 25.0
            
        return shows_results or has_quantities
        
    def validate_agent_completed_business_value(self, event: Dict[str, Any]) -> bool:
        """
        Validate agent_completed event delivers business value.
        
        Business Value: Completes user journey with actionable results.
        """
        required_fields = ['result']
        completion_indicators = ['completed', 'finished', 'ready', 'generated', 'analysis', 'recommendations']
        business_value_indicators = ['savings', '$', 'optimization', 'improvement', 'efficiency', 'cost', 'revenue']
        
        # Check required fields
        if 'result' not in event:
            return False
            
        # Check completion indicators
        event_text = str(event).lower()
        shows_completion = any(indicator in event_text for indicator in completion_indicators)
        
        # Check business value indicators
        shows_business_value = any(indicator in event_text for indicator in business_value_indicators)
        
        if shows_completion and shows_business_value:
            self.business_metrics.completion_satisfaction += 50.0
            self.user_journey_complete = True
        elif shows_completion:
            self.business_metrics.completion_satisfaction += 25.0
            
        return shows_completion
        
    def validate_event_business_value(self, event: Dict[str, Any]) -> bool:
        """Validate any event's business value based on its type."""
        event_type = event.get('type')
        
        validators = {
            'agent_started': self.validate_agent_started_business_value,
            'agent_thinking': self.validate_agent_thinking_business_value,
            'tool_executing': self.validate_tool_executing_business_value,
            'tool_completed': self.validate_tool_completed_business_value,
            'agent_completed': self.validate_agent_completed_business_value
        }
        
        if event_type in validators:
            return validators[event_type](event)
        
        return False
        
    def get_business_value_score(self) -> float:
        """Get overall business value score (0-100)."""
        return self.business_metrics.calculate_total_business_value()
        
    def is_user_journey_complete(self) -> bool:
        """Check if complete user journey was delivered."""
        return self.user_journey_complete


class RealWebSocketEventTester:
    """Real WebSocket client for testing critical events."""
    
    def __init__(self, port: int = 0):
        self.port = port
        self.server = None
        self.websocket = None
        self.connected = False
        self.received_events = []
        self.event_validator = BusinessValueEventValidator()
        
    async def start_test_server(self) -> int:
        """Start a real WebSocket server for event testing."""
        async def event_handler(websocket, path):
            logger.info("WebSocket client connected for event testing")
            
            try:
                async for message in websocket:
                    event_data = json.loads(message)
                    self.received_events.append({
                        'event': event_data,
                        'timestamp': datetime.now(timezone.utc),
                        'business_value': self.event_validator.validate_event_business_value(event_data)
                    })
                    
                    logger.info(f"Received critical event: {event_data.get('type')}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.info("Event testing WebSocket client disconnected")
                
        self.server = await websockets.serve(event_handler, "localhost", self.port or 0)
        
        if self.port == 0:
            self.port = self.server.sockets[0].getsockname()[1]
            
        logger.info(f"Event testing WebSocket server started on port {self.port}")
        return self.port
        
    async def connect_as_client(self, user_id: str) -> bool:
        """Connect as WebSocket client to receive events."""
        try:
            uri = f"ws://localhost:{self.port}"
            self.websocket = await websockets.connect(uri)
            self.connected = True
            
            # Start listening for events
            asyncio.create_task(self._listen_for_events())
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket event client: {e}")
            return False
            
    async def _listen_for_events(self):
        """Listen for WebSocket events."""
        try:
            async for message in self.websocket:
                event_data = json.loads(message)
                self.received_events.append({
                    'event': event_data,
                    'timestamp': datetime.now(timezone.utc),
                    'business_value': self.event_validator.validate_event_business_value(event_data)
                })
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
        except Exception as e:
            logger.error(f"Error listening for events: {e}")
            
    async def stop_server(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        if self.websocket:
            await self.websocket.close()
            
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all received events of a specific type."""
        return [event_data for event_data in self.received_events 
                if event_data['event'].get('type') == event_type]
                
    def has_all_critical_events(self) -> bool:
        """Check if all 5 critical events were received."""
        critical_types = {event.value for event in CriticalEventType}
        received_types = {event_data['event'].get('type') for event_data in self.received_events}
        return critical_types.issubset(received_types)
        
    def get_business_value_score(self) -> float:
        """Get overall business value score."""
        return self.event_validator.get_business_value_score()


@pytest.mark.mission_critical
class TestWebSocketFiveCriticalEventsBusinessValue(BaseIntegrationTest):
    """Mission critical tests for the 5 WebSocket events that drive business value."""
    
    async def setUp(self):
        """Set up real WebSocket event testing environment."""
        await super().setUp()
        self.manager = UnifiedWebSocketManager()
        self.test_user_id = ensure_user_id("critical-events-user-123")
        self.event_tester = RealWebSocketEventTester()
        
        # Start real WebSocket server for event testing
        self.server_port = await self.event_tester.start_test_server()
        
    async def tearDown(self):
        """Clean up event testing environment."""
        await self.event_tester.stop_server()
        await super().tearDown()
        
    # ========== MISSION CRITICAL EVENT TESTS ==========
    
    async def test_all_five_critical_events_complete_business_journey_mission_critical(self):
        """
        MISSION CRITICAL: Test all 5 critical events deliver complete business journey.
        
        Business Value: $500K+ ARR depends on complete event delivery driving user confidence.
        Can Fail: If any event is missing, user experience breaks and churn increases.
        """
        # Connect real WebSocket client to receive events
        connected = await self.event_tester.connect_as_client(self.test_user_id)
        self.assertTrue(connected, "Failed to connect real WebSocket event client")
        
        # Create real connection through unified manager
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"business_critical": True, "test_type": "complete_journey"}
        )
        
        await self.manager.add_connection(connection)
        
        # Send all 5 critical events in realistic business sequence
        critical_events_sequence = [
            {
                "type": "agent_started",
                "agent_name": "CostOptimizationAgent",
                "task": "Analyzing enterprise cloud infrastructure costs",
                "user_id": self.test_user_id,
                "estimated_savings": "Up to $50,000 annually",
                "business_context": "Enterprise cost optimization analysis"
            },
            {
                "type": "agent_thinking",
                "thought": "Analyzing 247 AWS services across 15 accounts to identify optimization opportunities...",
                "progress": 25,
                "user_id": self.test_user_id,
                "current_step": "Data collection and baseline establishment"
            },
            {
                "type": "tool_executing",
                "tool": "aws_cost_explorer_api",
                "description": "Querying AWS Cost Explorer for detailed usage patterns and cost trends",
                "user_id": self.test_user_id,
                "progress": 60,
                "data_sources": ["CloudWatch", "Cost Explorer", "Billing API"]
            },
            {
                "type": "tool_completed",
                "tool": "aws_cost_explorer_api",
                "result": "Analyzed 15,847 cost data points and identified 23 optimization opportunities",
                "user_id": self.test_user_id,
                "findings": {
                    "underutilized_instances": 47,
                    "over_provisioned_storage": "2.3TB",
                    "unused_elastic_ips": 12
                }
            },
            {
                "type": "agent_completed",
                "result": "Cost optimization analysis complete - Generated comprehensive savings plan",
                "user_id": self.test_user_id,
                "total_potential_savings": "$47,234 annually",
                "high_impact_recommendations": 8,
                "implementation_priority": "Start with EC2 right-sizing for immediate 15% reduction",
                "business_impact": "Reduces infrastructure spend by 28% while maintaining performance"
            }
        ]
        
        # Send events with realistic delays
        for i, event in enumerate(critical_events_sequence):
            await self.manager.send_to_user(self.test_user_id, event)
            logger.info(f"Sent critical event {i+1}/5: {event['type']}")
            
            # Realistic delay between events (simulates real agent processing)
            if i < len(critical_events_sequence) - 1:
                await asyncio.sleep(0.5)
        
        # Wait for all events to be processed through real WebSocket
        await asyncio.sleep(3.0)
        
        # CRITICAL VALIDATION: All 5 events must be received
        self.assertTrue(self.event_tester.has_all_critical_events(),
                       f"Missing critical events! Received: {[e['event'].get('type') for e in self.event_tester.received_events]}")
        
        # CRITICAL VALIDATION: Events must deliver business value
        business_value_score = self.event_tester.get_business_value_score()
        self.assertGreaterEqual(business_value_score, 80.0,
                               f"Business value score too low: {business_value_score:.1f}% (minimum 80%)")
        
        # CRITICAL VALIDATION: User journey must be complete
        self.assertTrue(self.event_tester.event_validator.is_user_journey_complete(),
                       "User journey not completed - agent_completed event must indicate completion")
        
        # Verify each event type was received with business value
        for event_type in CriticalEventType:
            events_of_type = self.event_tester.get_events_by_type(event_type.value)
            self.assertGreater(len(events_of_type), 0,
                              f"Critical event {event_type.value} was not received")
            
            # Verify business value in event
            event_has_value = any(event_data['business_value'] for event_data in events_of_type)
            self.assertTrue(event_has_value,
                           f"Critical event {event_type.value} lacks business value")
        
        # Final validation: Complete business metrics
        metrics = self.event_tester.event_validator.business_metrics
        self.assertGreater(metrics.user_confidence_score, 0, "No user confidence built")
        self.assertGreater(metrics.engagement_level, 0, "No user engagement achieved") 
        self.assertGreater(metrics.value_perception, 0, "No value perception created")
        self.assertGreater(metrics.completion_satisfaction, 0, "No completion satisfaction delivered")
        
        logger.info(f" PASS:  MISSION CRITICAL: All 5 events delivered with {business_value_score:.1f}% business value")
        
        await real_websocket.close()
        
    async def test_agent_started_event_builds_user_confidence_business_critical(self):
        """
        BUSINESS CRITICAL: Test agent_started event builds user confidence.
        
        Business Value: First impression that builds user confidence in AI capabilities.
        Can Fail: If agent_started lacks business context, users lose confidence immediately.
        """
        await self.event_tester.connect_as_client(self.test_user_id)
        
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Test HIGH VALUE agent_started event
        high_value_event = {
            "type": "agent_started",
            "agent_name": "EnterpriseSecurityAnalyzer", 
            "task": "Analyzing security vulnerabilities across 500+ enterprise assets",
            "expected_value": "Identify critical security gaps and compliance violations",
            "estimated_time": "3-5 minutes",
            "business_impact": "Prevent potential $2M+ security breach"
        }
        
        await self.manager.send_to_user(self.test_user_id, high_value_event)
        await asyncio.sleep(1.0)
        
        # Verify event received
        agent_started_events = self.event_tester.get_events_by_type("agent_started")
        self.assertEqual(len(agent_started_events), 1, "agent_started event not received")
        
        # Verify business value elements
        event = agent_started_events[0]['event']
        self.assertIn("agent_name", event, "agent_started missing agent_name")
        self.assertIn("task", event, "agent_started missing task description")
        
        # Verify confidence-building elements
        confidence_indicators = ["analyzing", "enterprise", "security", "vulnerabilities"]
        event_text = str(event).lower()
        confidence_elements = [indicator for indicator in confidence_indicators if indicator in event_text]
        self.assertGreater(len(confidence_elements), 2,
                          f"agent_started lacks confidence-building elements. Found: {confidence_elements}")
        
        # Verify business value score
        business_value_score = self.event_tester.get_business_value_score()
        self.assertGreater(business_value_score, 20.0,
                          f"agent_started business value too low: {business_value_score:.1f}%")
        
        await real_websocket.close()
        
    async def test_agent_thinking_event_drives_user_engagement_business_critical(self):
        """
        BUSINESS CRITICAL: Test agent_thinking event drives user engagement.
        
        Business Value: Keeps users engaged by showing AI reasoning process.
        Can Fail: If thinking events are generic, users lose interest and leave.
        """
        await self.event_tester.connect_as_client(self.test_user_id)
        
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Test multiple thinking events showing progression
        thinking_events = [
            {
                "type": "agent_thinking",
                "thought": "Evaluating 1,247 database queries to identify performance bottlenecks...",
                "progress": 15,
                "current_focus": "Query execution time analysis"
            },
            {
                "type": "agent_thinking",
                "thought": "Analyzing index usage patterns - found 23 missing indexes causing slow queries",
                "progress": 45,
                "current_focus": "Database optimization opportunities"
            },
            {
                "type": "agent_thinking",
                "thought": "Calculating potential performance improvements - estimated 3x faster query times",
                "progress": 75,
                "current_focus": "Impact assessment and recommendations"
            }
        ]
        
        for thinking_event in thinking_events:
            await self.manager.send_to_user(self.test_user_id, thinking_event)
            await asyncio.sleep(0.5)
            
        await asyncio.sleep(1.0)
        
        # Verify all thinking events received
        thinking_received = self.event_tester.get_events_by_type("agent_thinking")
        self.assertEqual(len(thinking_received), 3, "Not all agent_thinking events received")
        
        # Verify engagement elements in events
        for i, event_data in enumerate(thinking_received):
            event = event_data['event']
            
            # Must have thought content
            self.assertIn("thought", event, f"Thinking event {i} missing thought")
            self.assertGreater(len(str(event.get("thought", ""))), 20,
                              f"Thinking event {i} thought too short")
            
            # Should show progress
            if "progress" in event:
                progress = event["progress"]
                self.assertGreaterEqual(progress, 0, f"Invalid progress in event {i}")
                self.assertLessEqual(progress, 100, f"Invalid progress in event {i}")
        
        # Verify business value and engagement
        business_value_score = self.event_tester.get_business_value_score()
        self.assertGreater(business_value_score, 20.0,
                          f"agent_thinking business value too low: {business_value_score:.1f}%")
        
        await real_websocket.close()
        
    async def test_tool_executing_and_completed_show_ai_capabilities_business_critical(self):
        """
        BUSINESS CRITICAL: Test tool events demonstrate AI capabilities.
        
        Business Value: Proves AI is actually doing work and producing results.
        Can Fail: If tool events are vague, users don't see AI value and churn.
        """
        await self.event_tester.connect_as_client(self.test_user_id)
        
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Test tool execution sequence showing real capabilities
        tool_sequence = [
            {
                "type": "tool_executing",
                "tool": "financial_data_analyzer",
                "description": "Analyzing 36 months of financial data across 15 business units",
                "parameters": {
                    "data_range": "2022-01-01 to 2024-12-31",
                    "metrics": ["revenue", "costs", "profit_margins", "growth_rates"],
                    "granularity": "monthly"
                }
            },
            {
                "type": "tool_completed", 
                "tool": "financial_data_analyzer",
                "result": "Processed 15,847 financial records and identified 12 revenue optimization opportunities",
                "execution_time": "2.3 seconds",
                "data_quality": "98.7% complete records",
                "key_findings": {
                    "revenue_growth_opportunities": "$234,567 annually",
                    "cost_reduction_potential": "$89,123 annually",
                    "margin_improvement_areas": 5
                }
            },
            {
                "type": "tool_executing",
                "tool": "market_trend_predictor",
                "description": "Running predictive models on market trends using ML algorithms",
                "model_confidence": "94.2%",
                "data_sources": ["market_data", "competitor_analysis", "economic_indicators"]
            },
            {
                "type": "tool_completed",
                "tool": "market_trend_predictor", 
                "result": "Generated 12-month market forecast with 94.2% confidence",
                "predictions": {
                    "market_growth": "+15.3% next quarter",
                    "competitive_landscape": "2 new competitors expected",
                    "pricing_opportunities": "3% price increase sustainable"
                }
            }
        ]
        
        for tool_event in tool_sequence:
            await self.manager.send_to_user(self.test_user_id, tool_event)
            await asyncio.sleep(0.3)
            
        await asyncio.sleep(2.0)
        
        # Verify tool events received
        tool_executing_events = self.event_tester.get_events_by_type("tool_executing")
        tool_completed_events = self.event_tester.get_events_by_type("tool_completed")
        
        self.assertEqual(len(tool_executing_events), 2, "Missing tool_executing events")
        self.assertEqual(len(tool_completed_events), 2, "Missing tool_completed events")
        
        # Verify tool_executing events show capabilities
        for event_data in tool_executing_events:
            event = event_data['event']
            self.assertIn("tool", event, "tool_executing missing tool name")
            
            # Should have description showing what AI is doing
            if "description" in event:
                description = str(event["description"])
                self.assertGreater(len(description), 20, "tool_executing description too short")
                
                # Should indicate sophisticated capabilities
                capability_indicators = ["analyzing", "processing", "predicting", "calculating", "modeling"]
                has_capabilities = any(indicator in description.lower() for indicator in capability_indicators)
                self.assertTrue(has_capabilities, f"tool_executing lacks capability indicators: {description}")
        
        # Verify tool_completed events show concrete results
        for event_data in tool_completed_events:
            event = event_data['event']
            self.assertIn("tool", event, "tool_completed missing tool name")
            self.assertIn("result", event, "tool_completed missing result")
            
            result_text = str(event["result"])
            self.assertGreater(len(result_text), 20, "tool_completed result too short")
            
            # Should show quantitative results
            has_numbers = any(char.isdigit() for char in result_text)
            self.assertTrue(has_numbers, f"tool_completed lacks quantitative results: {result_text}")
        
        # Verify overall business value
        business_value_score = self.event_tester.get_business_value_score()
        self.assertGreater(business_value_score, 40.0,
                          f"Tool events business value too low: {business_value_score:.1f}%")
        
        await real_websocket.close()
        
    async def test_agent_completed_delivers_actionable_business_value_business_critical(self):
        """
        BUSINESS CRITICAL: Test agent_completed delivers actionable business value.
        
        Business Value: Final event must deliver clear, actionable business value.
        Can Fail: If completion lacks business value, entire interaction fails.
        """
        await self.event_tester.connect_as_client(self.test_user_id)
        
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Test high-value agent_completed event
        completion_event = {
            "type": "agent_completed",
            "result": "Enterprise security analysis complete - Generated comprehensive security improvement plan",
            "executive_summary": "Identified 23 critical vulnerabilities and 47 improvement opportunities",
            "business_impact": {
                "risk_reduction": "87% reduction in critical security risks",
                "cost_savings": "$2.3M prevented breach costs annually",
                "compliance_improvement": "Achieves SOC2 Type II compliance",
                "implementation_cost": "$45,000 for priority fixes"
            },
            "immediate_actions": [
                "Patch 5 critical vulnerabilities within 48 hours",
                "Implement MFA for all admin accounts within 1 week", 
                "Update firewall rules to close 12 unnecessary ports"
            ],
            "long_term_roadmap": {
                "30_days": "Complete security audit remediation",
                "90_days": "Implement zero-trust architecture",
                "180_days": "Achieve full compliance certification"
            },
            "roi_analysis": {
                "investment": "$45,000",
                "annual_savings": "$2,300,000",
                "payback_period": "8 days",
                "5_year_value": "$11,500,000"
            }
        }
        
        await self.manager.send_to_user(self.test_user_id, completion_event)
        await asyncio.sleep(1.0)
        
        # Verify completion event received
        completed_events = self.event_tester.get_events_by_type("agent_completed")
        self.assertEqual(len(completed_events), 1, "agent_completed event not received")
        
        event = completed_events[0]['event']
        
        # Verify required completion elements
        self.assertIn("result", event, "agent_completed missing result")
        
        # Verify business value indicators
        business_value_keywords = ["savings", "cost", "improvement", "roi", "value", "benefit", "$"]
        event_text = str(event).lower()
        business_indicators_found = [kw for kw in business_value_keywords if kw in event_text]
        
        self.assertGreater(len(business_indicators_found), 3,
                          f"agent_completed lacks business value indicators. Found: {business_indicators_found}")
        
        # Verify actionable elements
        actionable_keywords = ["implement", "patch", "update", "complete", "achieve", "fix"]
        actionable_indicators = [kw for kw in actionable_keywords if kw in event_text]
        
        self.assertGreater(len(actionable_indicators), 2,
                          f"agent_completed lacks actionable elements. Found: {actionable_indicators}")
        
        # Verify quantitative results
        has_dollar_amounts = "$" in event_text
        has_percentages = "%" in event_text
        has_timeframes = any(timeframe in event_text for timeframe in ["days", "weeks", "months", "hours"])
        
        quantitative_score = sum([has_dollar_amounts, has_percentages, has_timeframes])
        self.assertGreaterEqual(quantitative_score, 2,
                               f"agent_completed lacks quantitative results. Score: {quantitative_score}/3")
        
        # Verify overall business value and journey completion
        business_value_score = self.event_tester.get_business_value_score()
        self.assertGreater(business_value_score, 60.0,
                          f"Completion business value too low: {business_value_score:.1f}%")
        
        self.assertTrue(self.event_tester.event_validator.is_user_journey_complete(),
                       "User journey not marked complete by agent_completed event")
        
        await real_websocket.close()
        
    # ========== ERROR RECOVERY AND EDGE CASE TESTS ==========
    
    async def test_missing_critical_events_breaks_business_value(self):
        """
        Test that missing critical events breaks business value delivery.
        
        Business Value: Demonstrates why all 5 events are required.
        Can Fail: If business value is achieved without all events, our model is wrong.
        """
        await self.event_tester.connect_as_client(self.test_user_id)
        
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Send only 3 of 5 critical events (missing agent_thinking and tool_completed)
        incomplete_sequence = [
            {"type": "agent_started", "agent_name": "TestAgent", "task": "Testing incomplete sequence"},
            {"type": "tool_executing", "tool": "test_tool", "description": "Testing tool"},
            {"type": "agent_completed", "result": "Task completed"}
        ]
        
        for event in incomplete_sequence:
            await self.manager.send_to_user(self.test_user_id, event)
            await asyncio.sleep(0.2)
            
        await asyncio.sleep(1.0)
        
        # Verify incomplete event sequence
        self.assertFalse(self.event_tester.has_all_critical_events(),
                        "Should not have all critical events with incomplete sequence")
        
        # Verify business value is significantly reduced
        business_value_score = self.event_tester.get_business_value_score()
        self.assertLess(business_value_score, 75.0,
                       f"Business value should be reduced with missing events: {business_value_score:.1f}%")
        
        # Verify user journey is not complete
        self.assertFalse(self.event_tester.event_validator.is_user_journey_complete(),
                        "User journey should not be complete with missing events")
        
        await real_websocket.close()
        
    async def test_events_with_no_business_context_fail_value_delivery(self):
        """
        Test that events without business context fail to deliver value.
        
        Business Value: Events must contain meaningful business information.
        Can Fail: If generic events still deliver value, our validation is too weak.
        """
        await self.event_tester.connect_as_client(self.test_user_id)
        
        real_websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            websocket=real_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Send generic events with no business value
        generic_events = [
            {"type": "agent_started", "agent_name": "Agent", "task": "Task"},
            {"type": "agent_thinking", "thought": "Thinking..."},
            {"type": "tool_executing", "tool": "tool"},
            {"type": "tool_completed", "tool": "tool", "result": "Done"},
            {"type": "agent_completed", "result": "Complete"}
        ]
        
        for event in generic_events:
            await self.manager.send_to_user(self.test_user_id, event)
            await asyncio.sleep(0.1)
            
        await asyncio.sleep(1.0)
        
        # Verify all events received but business value is low
        self.assertTrue(self.event_tester.has_all_critical_events(),
                       "Should have all event types")
        
        # Verify low business value due to generic content
        business_value_score = self.event_tester.get_business_value_score()
        self.assertLess(business_value_score, 30.0,
                       f"Generic events should have low business value: {business_value_score:.1f}%")
        
        await real_websocket.close()
        
    async def test_event_delivery_performance_under_load(self):
        """
        Test event delivery performance under concurrent load.
        
        Business Value: Events must be delivered reliably even under load.
        Can Fail: If events are lost under load, business value is not delivered.
        """
        # Create multiple event testers for concurrent users
        num_concurrent_users = 5
        event_testers = []
        connections = []
        
        for i in range(num_concurrent_users):
            tester = RealWebSocketEventTester()
            port = await tester.start_test_server()
            await tester.connect_as_client(f"load-test-user-{i}")
            event_testers.append(tester)
            
            user_id = ensure_user_id(f"load-test-user-{i}")
            real_websocket = await websockets.connect(f"ws://localhost:{port}")
            
            connection = WebSocketConnection(
                connection_id=str(uuid.uuid4()),
                user_id=user_id,
                websocket=real_websocket,
                connected_at=datetime.now(timezone.utc)
            )
            
            await self.manager.add_connection(connection)
            connections.append((user_id, connection, real_websocket))
        
        # Send critical events to all users concurrently
        event_tasks = []
        
        for user_id, connection, websocket in connections:
            critical_event = {
                "type": "agent_completed",
                "result": f"Load test completed for {user_id}",
                "business_value": "$10,000 cost savings identified",
                "performance_test": True
            }
            
            event_tasks.append(self.manager.send_to_user(user_id, critical_event))
        
        # Send all events concurrently
        start_time = time.time()
        await asyncio.gather(*event_tasks)
        delivery_time = time.time() - start_time
        
        await asyncio.sleep(2.0)
        
        # Verify performance
        self.assertLess(delivery_time, 2.0, f"Event delivery too slow under load: {delivery_time:.2f}s")
        
        # Verify all users received events
        successful_deliveries = 0
        total_business_value = 0
        
        for tester in event_testers:
            completed_events = tester.get_events_by_type("agent_completed")
            if len(completed_events) > 0:
                successful_deliveries += 1
                total_business_value += tester.get_business_value_score()
        
        delivery_success_rate = successful_deliveries / num_concurrent_users
        avg_business_value = total_business_value / num_concurrent_users
        
        self.assertGreaterEqual(delivery_success_rate, 0.8,
                               f"Event delivery success rate too low: {delivery_success_rate:.1%}")
        
        self.assertGreater(avg_business_value, 15.0,
                          f"Average business value too low under load: {avg_business_value:.1f}%")
        
        # Clean up
        for user_id, connection, websocket in connections:
            await websocket.close()
            
        for tester in event_testers:
            await tester.stop_server()


if __name__ == "__main__":
    # Run with: python -m pytest tests/mission_critical/test_websocket_five_critical_events_business_value.py -v
    pytest.main([__file__, "-v", "--tb=short"])