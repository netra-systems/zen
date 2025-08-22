"""
WebSocket Broadcast Mechanisms Tests
Tests for broadcast mechanisms and subscription management.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict, List

import pytest

# Add project root to path
from app.services.websocket.broadcast_manager import BroadcastManager

# Add project root to path


class TestBroadcastMechanisms:
    """Test broadcast mechanisms and subscription management."""
    
    @pytest.fixture
    def broadcast_manager(self):
        """Create broadcast manager for testing."""
        return BroadcastManager()
    
    def test_user_subscription(self, broadcast_manager):
        """Test user subscription to broadcasts."""
        # Subscribe users
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        broadcast_manager.subscribe('user2', {'topic': 'updates'})
        broadcast_manager.subscribe('user3')  # No filters
        
        # Verify subscriptions
        assert len(broadcast_manager.subscribers) == 3
        assert 'user1' in broadcast_manager.subscribers
        assert broadcast_manager.subscribers['user1'] == {'topic': 'alerts'}
        assert broadcast_manager.subscribers['user3'] == {}
    
    def test_user_unsubscription(self, broadcast_manager):
        """Test user unsubscription from broadcasts."""
        # Subscribe then unsubscribe
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        assert 'user1' in broadcast_manager.subscribers
        
        broadcast_manager.unsubscribe('user1')
        assert 'user1' not in broadcast_manager.subscribers
        
        # Unsubscribing non-existent user should not error
        broadcast_manager.unsubscribe('non_existent')
    
    def test_broadcast_filtering(self, broadcast_manager):
        """Test broadcast message filtering."""
        # Subscribe users with different filters
        broadcast_manager.subscribe('user1', {'topic': 'alerts', 'priority': 'high'})
        broadcast_manager.subscribe('user2', {'topic': 'alerts'})
        broadcast_manager.subscribe('user3', {'priority': 'high'})
        broadcast_manager.subscribe('user4')  # No filters
        
        # Test different broadcast messages
        alert_high = {'topic': 'alerts', 'priority': 'high', 'message': 'Critical alert'}
        alert_low = {'topic': 'alerts', 'priority': 'low', 'message': 'Info alert'}
        update_high = {'topic': 'updates', 'priority': 'high', 'message': 'System update'}
        
        # user1: should receive alert_high only (both filters match)
        assert broadcast_manager.should_receive_broadcast('user1', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user1', alert_low) == False
        assert broadcast_manager.should_receive_broadcast('user1', update_high) == False
        
        # user2: should receive both alerts (topic matches)
        assert broadcast_manager.should_receive_broadcast('user2', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user2', alert_low) == True
        assert broadcast_manager.should_receive_broadcast('user2', update_high) == False
        
        # user3: should receive high priority messages (priority matches)
        assert broadcast_manager.should_receive_broadcast('user3', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user3', alert_low) == False
        assert broadcast_manager.should_receive_broadcast('user3', update_high) == True
        
        # user4: should receive all messages (no filters)
        assert broadcast_manager.should_receive_broadcast('user4', alert_high) == True
        assert broadcast_manager.should_receive_broadcast('user4', alert_low) == True
        assert broadcast_manager.should_receive_broadcast('user4', update_high) == True

    async def test_broadcast_message_delivery(self, broadcast_manager):
        """Test broadcast message delivery."""
        # Subscribe users
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        broadcast_manager.subscribe('user2', {'topic': 'alerts'})
        broadcast_manager.subscribe('user3', {'topic': 'updates'})
        
        # Broadcast alert message
        message_data = {'topic': 'alerts', 'message': 'System maintenance scheduled'}
        results = await broadcast_manager.broadcast_message(message_data)
        
        # Verify delivery results
        assert results['success'] == 2  # user1 and user2
        assert results['failed'] == 0
        
        # Verify broadcast history
        assert len(broadcast_manager.broadcast_history) == 1
        history_entry = broadcast_manager.broadcast_history[0]
        assert history_entry['message_data'] == message_data
        assert history_entry['results'] == results
        
        # Verify delivery stats
        stats = broadcast_manager.delivery_stats
        assert stats['total_broadcasts'] == 1
        assert stats['successful_deliveries'] == 2
        assert stats['failed_deliveries'] == 0

    async def test_targeted_broadcast(self, broadcast_manager):
        """Test targeted broadcast to specific users."""
        # Subscribe multiple users
        for i in range(10):
            broadcast_manager.subscribe(f'user_{i}', {'topic': 'alerts'})
        
        # Broadcast to specific subset
        target_users = ['user_1', 'user_3', 'user_5']
        message_data = {'topic': 'alerts', 'message': 'Targeted alert'}
        results = await broadcast_manager.broadcast_message(message_data, target_users)
        
        # Verify only targeted users received message
        assert results['success'] == 3
        assert results['failed'] == 0
        
        # Verify broadcast history
        history_entry = broadcast_manager.broadcast_history[0]
        assert history_entry['target_users'] == target_users

    async def test_broadcast_delivery_failure_handling(self, broadcast_manager):
        """Test handling of broadcast delivery failures."""
        # Subscribe users
        broadcast_manager.subscribe('user1', {'topic': 'alerts'})
        broadcast_manager.subscribe('user2', {'topic': 'alerts'})
        
        # Mock delivery failure for user2
        original_deliver = broadcast_manager._deliver_message
        
        async def mock_deliver(user_id, message_data):
            if user_id == 'user2':
                raise Exception("Delivery failed")
            return await original_deliver(user_id, message_data)
        
        broadcast_manager._deliver_message = mock_deliver
        
        # Broadcast message
        message_data = {'topic': 'alerts', 'message': 'Test message'}
        results = await broadcast_manager.broadcast_message(message_data)
        
        # Verify results
        assert results['success'] == 1  # user1 succeeded
        assert results['failed'] == 1   # user2 failed
        
        # Verify stats
        stats = broadcast_manager.delivery_stats
        assert stats['successful_deliveries'] == 1
        assert stats['failed_deliveries'] == 1

    async def test_high_volume_broadcasting(self, broadcast_manager):
        """Test broadcasting under high volume conditions."""
        # Subscribe many users
        num_users = 100
        for i in range(num_users):
            broadcast_manager.subscribe(f'user_{i}', {'topic': 'alerts'})
        
        # Broadcast multiple messages rapidly
        num_messages = 50
        tasks = []
        
        for i in range(num_messages):
            message_data = {'topic': 'alerts', 'message': f'Bulk message {i}'}
            tasks.append(broadcast_manager.broadcast_message(message_data))
        
        # Execute all broadcasts
        results = await asyncio.gather(*tasks)
        
        # Verify all broadcasts succeeded
        total_success = sum(result['success'] for result in results)
        total_failed = sum(result['failed'] for result in results)
        
        expected_success = num_messages * num_users
        assert total_success == expected_success
        assert total_failed == 0
        
        # Verify history and stats
        assert len(broadcast_manager.broadcast_history) == num_messages
        assert broadcast_manager.delivery_stats['total_broadcasts'] == num_messages
        assert broadcast_manager.delivery_stats['successful_deliveries'] == expected_success