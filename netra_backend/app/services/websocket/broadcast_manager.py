"""
Subscription-based broadcast manager for targeted message delivery.

Handles user subscriptions with filter-based message routing and delivery tracking.
Business Value: Enables targeted messaging to reduce noise and increase engagement.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BroadcastManager:
    """Manages subscription-based broadcasting with filtering capabilities."""
    
    def __init__(self):
        """Initialize the broadcast manager."""
        self.subscribers: Dict[str, Dict[str, Any]] = {}
        self.broadcast_history: List[Dict[str, Any]] = []
        self.delivery_stats = self._create_initial_stats()

    def _create_initial_stats(self) -> Dict[str, int]:
        """Create initial delivery statistics."""
        return {
            'total_broadcasts': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0
        }

    def subscribe(self, user_id: str, filters: Optional[Dict[str, Any]] = None) -> None:
        """Subscribe user to broadcasts with optional filters."""
        self.subscribers[user_id] = filters or {}
        self._log_subscription_event(user_id, filters)

    def unsubscribe(self, user_id: str) -> None:
        """Unsubscribe user from broadcasts."""
        if user_id in self.subscribers:
            del self.subscribers[user_id]
            self._log_unsubscription_event(user_id)

    def should_receive_broadcast(self, user_id: str, message_data: Dict[str, Any]) -> bool:
        """Check if user should receive a broadcast message."""
        if user_id not in self.subscribers:
            return False
        return self._evaluate_message_filters(user_id, message_data)

    async def broadcast_message(self, message_data: Dict[str, Any], target_users: Optional[List[str]] = None) -> Dict[str, int]:
        """Broadcast message to subscribers or targeted users."""
        recipients = self._determine_message_recipients(message_data, target_users)
        results = await self._deliver_message_to_recipients(recipients, message_data)
        self._record_broadcast_results(message_data, results, target_users)
        return results

    def _log_subscription_event(self, user_id: str, filters: Optional[Dict[str, Any]]) -> None:
        """Log user subscription event."""
        filter_info = filters if filters else "no filters"
        logger.info(f"User {user_id} subscribed with {filter_info}")

    def _log_unsubscription_event(self, user_id: str) -> None:
        """Log user unsubscription event."""
        logger.info(f"User {user_id} unsubscribed from broadcasts")

    def _evaluate_message_filters(self, user_id: str, message_data: Dict[str, Any]) -> bool:
        """Evaluate if message matches user's subscription filters."""
        user_filters = self.subscribers[user_id]
        if not user_filters:
            return True
        return self._check_filter_matches(user_filters, message_data)

    def _check_filter_matches(self, user_filters: Dict[str, Any], message_data: Dict[str, Any]) -> bool:
        """Check if all user filters match the message data."""
        for filter_key, filter_value in user_filters.items():
            if not self._single_filter_matches(filter_key, filter_value, message_data):
                return False
        return True

    def _single_filter_matches(self, filter_key: str, filter_value: Any, message_data: Dict[str, Any]) -> bool:
        """Check if a single filter matches the message."""
        message_value = message_data.get(filter_key)
        return message_value == filter_value

    def _determine_message_recipients(self, message_data: Dict[str, Any], target_users: Optional[List[str]]) -> List[str]:
        """Determine which users should receive the message."""
        if target_users:
            return self._filter_targeted_users(target_users, message_data)
        return self._filter_all_subscribers(message_data)

    def _filter_targeted_users(self, target_users: List[str], message_data: Dict[str, Any]) -> List[str]:
        """Filter targeted users based on subscription and filters."""
        return [
            user_id for user_id in target_users
            if self.should_receive_broadcast(user_id, message_data)
        ]

    def _filter_all_subscribers(self, message_data: Dict[str, Any]) -> List[str]:
        """Filter all subscribers based on message filters."""
        return [
            user_id for user_id in self.subscribers.keys()
            if self.should_receive_broadcast(user_id, message_data)
        ]

    async def _deliver_message_to_recipients(self, recipients: List[str], message_data: Dict[str, Any]) -> Dict[str, int]:
        """Deliver message to all recipients."""
        delivery_tasks = self._create_delivery_tasks(recipients, message_data)
        delivery_results = await self._execute_delivery_tasks(delivery_tasks)
        return self._count_delivery_results(delivery_results)

    def _create_delivery_tasks(self, recipients: List[str], message_data: Dict[str, Any]) -> List:
        """Create delivery tasks for all recipients."""
        return [
            self._deliver_message(user_id, message_data)
            for user_id in recipients
        ]

    async def _execute_delivery_tasks(self, delivery_tasks: List) -> List[Any]:
        """Execute all delivery tasks concurrently."""
        return await asyncio.gather(*delivery_tasks, return_exceptions=True)

    async def _deliver_message(self, user_id: str, message_data: Dict[str, Any]) -> bool:
        """Deliver message to a single user."""
        try:
            return await self._simulate_message_delivery(user_id, message_data)
        except Exception as e:
            self._log_delivery_error(user_id, e)
            return False

    async def _simulate_message_delivery(self, user_id: str, message_data: Dict[str, Any]) -> bool:
        """Simulate message delivery (replace with actual delivery logic)."""
        # Simulate network delay
        await asyncio.sleep(0.001)
        logger.debug(f"Delivered message to {user_id}: {message_data}")
        return True

    def _log_delivery_error(self, user_id: str, error: Exception) -> None:
        """Log message delivery error."""
        logger.error(f"Failed to deliver message to {user_id}: {error}")

    def _count_delivery_results(self, delivery_results: List[Any]) -> Dict[str, int]:
        """Count successful and failed delivery results."""
        successful = sum(1 for result in delivery_results if result is True)
        failed = len(delivery_results) - successful
        return {'success': successful, 'failed': failed}

    def _record_broadcast_results(self, message_data: Dict[str, Any], results: Dict[str, int], target_users: Optional[List[str]]) -> None:
        """Record broadcast results in history and update stats."""
        self._add_to_broadcast_history(message_data, results, target_users)
        self._update_delivery_statistics(results)

    def _add_to_broadcast_history(self, message_data: Dict[str, Any], results: Dict[str, int], target_users: Optional[List[str]]) -> None:
        """Add broadcast to history."""
        history_entry = self._create_history_entry(message_data, results, target_users)
        self.broadcast_history.append(history_entry)

    def _create_history_entry(self, message_data: Dict[str, Any], results: Dict[str, int], target_users: Optional[List[str]]) -> Dict[str, Any]:
        """Create broadcast history entry."""
        entry = self._create_base_history_entry(message_data, results)
        return self._add_target_users_to_entry(entry, target_users)

    def _create_base_history_entry(self, message_data: Dict[str, Any], results: Dict[str, int]) -> Dict[str, Any]:
        """Create base history entry with timestamp, message, and results."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message_data': message_data,
            'results': results
        }

    def _add_target_users_to_entry(self, entry: Dict[str, Any], target_users: Optional[List[str]]) -> Dict[str, Any]:
        """Add target users to history entry if provided."""
        if target_users:
            entry['target_users'] = target_users
        return entry

    def _update_delivery_statistics(self, results: Dict[str, int]) -> None:
        """Update delivery statistics."""
        self.delivery_stats['total_broadcasts'] += 1
        self.delivery_stats['successful_deliveries'] += results['success']
        self.delivery_stats['failed_deliveries'] += results['failed']