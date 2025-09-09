"""
Test WebSocket Connection Metadata Tracking and Application State Correlation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable comprehensive connection tracking and analytics for system optimization
- Value Impact: Users benefit from optimized connection management based on usage patterns
- Strategic Impact: Provides data-driven insights for system performance improvements

This integration test validates that WebSocket connection metadata is properly tracked
and correlated with application state for analytics and optimization purposes.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestWebSocketConnectionMetadataTrackingApplicationStateIntegration(BaseIntegrationTest):
    """Test WebSocket connection metadata tracking with comprehensive application state correlation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_metadata_tracking_with_application_state_correlation(self, real_services_fixture):
        """Test comprehensive metadata tracking and state correlation for connections."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'metadata_tracking_user@netra.ai',
            'name': 'Metadata Tracking User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create WebSocket with rich metadata tracking
        class MetadataTrackingWebSocket:
            def __init__(self, connection_id: str):
                self.connection_id = connection_id
                self.messages_sent = []
                self.is_closed = False
                self.metadata = {
                    'browser': 'Chrome/91.0',
                    'os': 'Windows 10',
                    'viewport': {'width': 1920, 'height': 1080},
                    'timezone': 'UTC-8',
                    'language': 'en-US',
                    'connection_quality': 'excellent',
                    'last_seen': datetime.utcnow().isoformat()
                }
            
            async def send_json(self, data):
                # Update metadata with each interaction
                self.metadata['last_seen'] = datetime.utcnow().isoformat()
                self.metadata['message_count'] = len(self.messages_sent) + 1
                
                data['_metadata_snapshot'] = self.metadata.copy()
                self.messages_sent.append(data)
            
            async def close(self):
                self.is_closed = True
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="metadata_tracking",
            context={"user_id": user_id, "test": "metadata"}
        )
        
        metadata_websocket = MetadataTrackingWebSocket(connection_id)
        
        # Rich connection metadata
        connection_metadata = {
            "connection_type": "metadata_tracking_test",
            "client_info": metadata_websocket.metadata,
            "connection_source": "web_app",
            "session_context": {
                "page": "/dashboard",
                "feature": "agent_chat",
                "user_tier": "enterprise"
            },
            "performance_metrics": {
                "initial_latency_ms": 45,
                "bandwidth_estimate_kbps": 10000,
                "connection_stability": "stable"
            }
        }
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=metadata_websocket,
            connected_at=datetime.utcnow(),
            metadata=connection_metadata
        )
        
        await websocket_manager.add_connection(connection)
        
        # Store connection metadata in application state for analytics
        metadata_key = f"connection_analytics:{connection_id}"
        analytics_data = {
            'user_id': user_id,
            'connection_id': connection_id,
            'connection_metadata': connection_metadata,
            'created_at': datetime.utcnow().isoformat(),
            'interaction_history': []
        }
        
        await real_services_fixture["redis"].set(
            metadata_key,
            json.dumps(analytics_data),
            ex=86400  # 24 hour retention
        )
        
        # Send messages and track metadata correlation
        for i in range(5):
            message = {
                "type": "metadata_test_message",
                "data": {"message_index": i, "test_metadata": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, message)
            
            # Update analytics with interaction
            analytics_data['interaction_history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'message_type': message['type'],
                'message_index': i
            })
            
            await real_services_fixture["redis"].set(
                metadata_key,
                json.dumps(analytics_data),
                ex=86400
            )
            
            await asyncio.sleep(0.1)
        
        # Verify metadata tracking in messages
        for i, message in enumerate(metadata_websocket.messages_sent):
            assert '_metadata_snapshot' in message
            snapshot = message['_metadata_snapshot']
            assert snapshot['message_count'] == i + 1
            assert 'last_seen' in snapshot
            assert snapshot['browser'] == 'Chrome/91.0'
        
        # Verify application state correlation
        stored_analytics = await real_services_fixture["redis"].get(metadata_key)
        assert stored_analytics is not None
        
        analytics_info = json.loads(stored_analytics)
        assert analytics_info['user_id'] == user_id
        assert len(analytics_info['interaction_history']) == 5
        assert analytics_info['connection_metadata']['client_info']['browser'] == 'Chrome/91.0'
        
        # Test connection health correlation with metadata
        connection_health = websocket_manager.get_connection_health(user_id)
        assert connection_health['has_active_connections'] is True
        
        # Verify metadata is accessible in connection details
        conn_details = connection_health['connections'][0]
        assert 'metadata' in conn_details
        stored_metadata = conn_details['metadata']
        assert stored_metadata['connection_type'] == 'metadata_tracking_test'
        assert 'client_info' in stored_metadata
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        await real_services_fixture["redis"].delete(metadata_key)
        
        self.assert_business_value_delivered({
            'metadata_tracking': True,
            'application_state_correlation': True,
            'analytics_data_collection': True,
            'connection_insights': True
        }, 'insights')
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_metadata_evolution_tracking_across_connection_lifecycle(self, real_services_fixture):
        """Test that connection metadata properly evolves and is tracked across connection lifecycle."""
        user_data = await self.create_test_user_context(real_services_fixture, {
            'email': 'metadata_evolution_user@netra.ai',
            'name': 'Metadata Evolution User',
            'is_active': True
        })
        user_id = user_data['id']
        
        websocket_manager = UnifiedWebSocketManager()
        id_manager = UnifiedIDManager()
        
        # Create WebSocket that tracks metadata evolution
        class EvolvingMetadataWebSocket:
            def __init__(self, connection_id: str):
                self.connection_id = connection_id
                self.messages_sent = []
                self.is_closed = False
                self.metadata_history = []
                self.current_metadata = {
                    'connection_phase': 'initial',
                    'message_count': 0,
                    'quality_score': 1.0,
                    'last_updated': datetime.utcnow().isoformat()
                }
                self._record_metadata_snapshot('initialization')
            
            def _record_metadata_snapshot(self, trigger: str):
                """Record metadata snapshot for evolution tracking."""
                snapshot = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'trigger': trigger,
                    'metadata': self.current_metadata.copy()
                }
                self.metadata_history.append(snapshot)
            
            def _evolve_metadata(self, evolution_type: str):
                """Evolve metadata based on connection usage."""
                if evolution_type == 'message_activity':
                    self.current_metadata['message_count'] += 1
                    if self.current_metadata['message_count'] > 10:
                        self.current_metadata['connection_phase'] = 'active_user'
                    elif self.current_metadata['message_count'] > 20:
                        self.current_metadata['connection_phase'] = 'power_user'
                
                elif evolution_type == 'quality_degradation':
                    self.current_metadata['quality_score'] = max(0.1, self.current_metadata['quality_score'] - 0.1)
                    if self.current_metadata['quality_score'] < 0.7:
                        self.current_metadata['connection_phase'] = 'degraded'
                
                elif evolution_type == 'quality_improvement':
                    self.current_metadata['quality_score'] = min(1.0, self.current_metadata['quality_score'] + 0.1)
                
                self.current_metadata['last_updated'] = datetime.utcnow().isoformat()
                self._record_metadata_snapshot(evolution_type)
            
            async def send_json(self, data):
                # Evolve metadata with each message
                self._evolve_metadata('message_activity')
                
                # Simulate occasional quality changes
                import random
                if random.random() < 0.3:  # 30% chance
                    if random.random() < 0.5:
                        self._evolve_metadata('quality_degradation')
                    else:
                        self._evolve_metadata('quality_improvement')
                
                data['_metadata_evolution'] = {
                    'current': self.current_metadata.copy(),
                    'evolution_count': len(self.metadata_history)
                }
                
                self.messages_sent.append(data)
            
            async def close(self):
                self._evolve_metadata('connection_closing')
                self.is_closed = True
        
        connection_id = id_manager.generate_id(
            IDType.CONNECTION,
            prefix="metadata_evolution",
            context={"user_id": user_id, "test": "evolution"}
        )
        
        evolution_websocket = EvolvingMetadataWebSocket(connection_id)
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=evolution_websocket,
            connected_at=datetime.utcnow(),
            metadata={
                "connection_type": "metadata_evolution_test",
                "tracks_evolution": True
            }
        )
        
        await websocket_manager.add_connection(connection)
        
        # Send multiple messages to trigger metadata evolution
        for i in range(15):
            message = {
                "type": "evolution_test_message",
                "data": {"message_index": i},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket_manager.send_to_user(user_id, message)
            await asyncio.sleep(0.05)
        
        # Verify metadata evolution
        assert len(evolution_websocket.messages_sent) == 15
        
        # Check that metadata evolved over time
        first_message_metadata = evolution_websocket.messages_sent[0]['_metadata_evolution']['current']
        last_message_metadata = evolution_websocket.messages_sent[-1]['_metadata_evolution']['current']
        
        assert first_message_metadata['connection_phase'] == 'initial'
        assert last_message_metadata['connection_phase'] == 'active_user'  # Should have evolved
        assert last_message_metadata['message_count'] == 15
        
        # Verify evolution history
        assert len(evolution_websocket.metadata_history) > 15  # Should have multiple snapshots
        
        # Check evolution triggers
        triggers = [snapshot['trigger'] for snapshot in evolution_websocket.metadata_history]
        assert 'initialization' in triggers
        assert 'message_activity' in triggers
        
        # Clean up
        await websocket_manager.remove_connection(connection_id)
        
        self.assert_business_value_delivered({
            'metadata_evolution_tracking': True,
            'connection_lifecycle_insights': True,
            'usage_pattern_analysis': True,
            'quality_monitoring': True
        }, 'insights')