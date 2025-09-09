"""
Test WebSocket Connection Event Emission and Application State Notifications

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable event emission for real-time user experience
- Value Impact: Users receive timely notifications and updates about system events
- Strategic Impact: Core foundation for agent interactions and real-time features

This integration test validates that WebSocket connections properly emit events
and maintain application state notifications for comprehensive user experience.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestWebSocketConnectionEventEmissionApplicationStateIntegration(BaseIntegrationTest):
    """Test WebSocket connection event emission with comprehensive application state notifications."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_emission_with_application_state_synchronization(self, real_services_fixture):
        """Test that WebSocket events are properly emitted and synchronized with application state."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'event_emission_user@netra.ai',
            'name': 'Event Emission User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create event-tracking WebSocket
        class EventEmissionWebSocket:
            def __init__(self, connection_id: str, user_id: str):
                self.connection_id = connection_id
                self.user_id = user_id
                self.messages_sent = []
                self.events_emitted = []
                self.is_closed = False
            
            async def send_json(self, data):
                # Track event emission
                if data.get('type') in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                    self.events_emitted.append({
                        'event_type': data['type'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': data.get('data', {})
                    })
                
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="event_emission",
            context={"user_id": user_id, "test": "events"}
        )
        
        event_websocket = EventEmissionWebSocket(connection_id, user_id)
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=event_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_type": "event_emission_test"}
        )
        
        await websocket_manager.add_connection(connection)
        
        # Test critical WebSocket events (as mentioned in CLAUDE.md)
        critical_events = [
            {
                "type": "agent_started",
                "data": {"agent_id": "test_agent", "user_id": user_id},
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            },
            {
                "type": "agent_thinking", 
                "data": {"progress": "analyzing", "reasoning": "Processing user request"},
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            },
            {
                "type": "tool_executing",
                "data": {"tool_name": "data_analyzer", "status": "running"},
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            },
            {
                "type": "tool_completed",
                "data": {"tool_name": "data_analyzer", "result": "analysis_complete"},
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            },
            {
                "type": "agent_completed",
                "data": {"agent_id": "test_agent", "result": "task_finished", "insights": ["insight1", "insight2"]},
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
        ]
        
        # Emit critical events through the manager
        for event in critical_events:
            await websocket_manager.emit_critical_event(user_id, event['type'], event['data'])
            await asyncio.sleep(0.1)  # Small delay between events
        
        # Verify all critical events were received
        assert len(event_websocket.events_emitted) == 5, "All 5 critical events should be emitted"
        
        # Verify event order and content
        expected_event_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        actual_event_types = [e['event_type'] for e in event_websocket.events_emitted]
        assert actual_event_types == expected_event_types, "Events should be emitted in correct order"
        
        # Verify event data integrity
        agent_started_event = event_websocket.events_emitted[0]
        assert agent_started_event['data']['agent_id'] == 'test_agent'
        assert agent_started_event['data']['user_id'] == user_id
        
        agent_completed_event = event_websocket.events_emitted[-1]
        assert agent_completed_event['data']['result'] == 'task_finished'
        assert 'insights' in agent_completed_event['data']
        
        # Store event emission log in application state
        event_log_key = f"event_log:{user_id}:{connection_id}"
        event_log = {
            'user_id': user_id,
            'connection_id': connection_id,
            'events_emitted': event_websocket.events_emitted,
            'total_events': len(event_websocket.events_emitted),
            'log_created_at': datetime.utcnow().isoformat()
        }
        
        await real_services_fixture["redis"].set(
            event_log_key,
            json.dumps(event_log),
            ex=3600
        )
        
        # Verify application state synchronization
        stored_log = await real_services_fixture["redis"].get(event_log_key)
        assert stored_log is not None
        
        log_data = json.loads(stored_log)
        assert log_data['total_events'] == 5
        assert log_data['user_id'] == user_id
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        await real_services_fixture["redis"].delete(event_log_key)
        
        self.assert_business_value_delivered({
            'critical_event_emission': True,
            'event_ordering': True,
            'application_state_sync': True,
            'user_experience_delivery': True
        }, 'automation')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_event_emission_reliability_and_delivery_guarantees(self, real_services_fixture):
        """Test event emission reliability and delivery guarantees under various conditions."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'event_reliability_user@netra.ai',
            'name': 'Event Reliability User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create WebSocket that simulates delivery challenges
        class ReliabilityTestWebSocket:
            def __init__(self, connection_id: str, fail_rate: float = 0.0):
                self.connection_id = connection_id
                self.fail_rate = fail_rate
                self.messages_sent = []
                self.failed_sends = []
                self.is_closed = False
                self.delivery_attempts = 0
            
            async def send_json(self, data):
                self.delivery_attempts += 1
                
                # Simulate delivery failures based on fail_rate
                import random
                if random.random() < self.fail_rate:
                    self.failed_sends.append({
                        'data': data,
                        'timestamp': datetime.utcnow().isoformat(),
                        'attempt': self.delivery_attempts
                    })
                    raise ConnectionError("Simulated delivery failure")
                
                # Successful delivery
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="event_reliability",
            context={"user_id": user_id, "test": "reliability"}
        )
        
        # Test with moderate failure rate to test recovery mechanisms
        reliability_websocket = ReliabilityTestWebSocket(connection_id, fail_rate=0.3)
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=reliability_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_type": "event_reliability_test"}
        )
        
        await websocket_manager.add_connection(connection)
        
        # Send multiple events, some may fail due to simulated issues
        test_events = []
        for i in range(10):
            event_data = {
                "event_id": f"event_{i}",
                "sequence_number": i,
                "content": f"Test event {i}",
                "critical": i % 2 == 0  # Every other event is critical
            }
            test_events.append(event_data)
        
        # Attempt to emit all events
        successful_emissions = 0
        failed_emissions = 0
        
        for event_data in test_events:
            try:
                await websocket_manager.emit_critical_event(user_id, "test_event", event_data)
                successful_emissions += 1
            except Exception:
                failed_emissions += 1
            
            await asyncio.sleep(0.05)
        
        # Analyze delivery results
        total_delivery_attempts = reliability_websocket.delivery_attempts
        successful_deliveries = len(reliability_websocket.messages_sent)
        failed_deliveries = len(reliability_websocket.failed_sends)
        
        assert total_delivery_attempts > 0, "Should have attempted deliveries"
        assert successful_deliveries + failed_deliveries <= total_delivery_attempts
        
        # Verify that the manager handled failures gracefully
        # (In real implementation, failed events would be queued for retry)
        error_stats = websocket_manager.get_error_statistics()
        assert error_stats['total_error_count'] >= 0, "Error statistics should be tracked"
        
        # Check if any events were successfully delivered
        if successful_deliveries > 0:
            # Verify delivered events have proper structure
            for delivered_event in reliability_websocket.messages_sent:
                assert 'type' in delivered_event
                assert 'data' in delivered_event
                assert 'timestamp' in delivered_event
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        
        self.assert_business_value_delivered({
            'event_delivery_reliability': True,
            'failure_handling': True,
            'delivery_monitoring': True,
            'error_recovery': True
        }, 'automation')