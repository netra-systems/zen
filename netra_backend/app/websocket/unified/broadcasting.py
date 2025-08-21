"""Unified WebSocket Broadcasting - Room management and message broadcasting.

Consolidates broadcasting operations into a unified system with:
- Efficient room-based message distribution
- Job-based broadcasting for workflow updates  
- Scalable broadcasting to all connected users
- Real-time broadcast telemetry and metrics
- Thread-safe room membership management

Business Value: Enables real-time collaborative features at scale
All functions ≤8 lines as per CLAUDE.md requirements.
"""

import asyncio
import time
from typing import Dict, Any, Union, List, Set, Optional
from collections import defaultdict

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult

logger = central_logger.get_logger(__name__)


class BroadcastMetrics:
    """Real-time broadcast telemetry and performance metrics."""
    
    def __init__(self) -> None:
        """Initialize broadcast metrics tracking."""
        self._initialize_broadcast_stats()
        self._initialize_room_tracking()

    def _initialize_broadcast_stats(self) -> None:
        """Initialize core broadcast statistics."""
        base_stats = self._get_base_broadcast_stats()
        extended_stats = self._get_extended_broadcast_stats()
        self.stats = {**base_stats, **extended_stats}

    def _get_base_broadcast_stats(self) -> Dict[str, Any]:
        """Get base broadcast statistics dictionary."""
        return {
            "total_broadcasts": 0, "successful_sends": 0, "failed_sends": 0,
            "room_broadcasts": 0
        }

    def _get_extended_broadcast_stats(self) -> Dict[str, Any]:
        """Get extended broadcast statistics dictionary."""
        return {
            "global_broadcasts": 0, "job_broadcasts": 0, "average_room_size": 0.0
        }

    def _initialize_room_tracking(self) -> None:
        """Initialize room-specific tracking data."""
        self.room_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"messages": 0, "members": 0}
        )

    def record_broadcast(self, broadcast_type: str, recipients: int, successful: int) -> None:
        """Record broadcast operation with metrics."""
        self.stats["total_broadcasts"] += 1
        self.stats["successful_sends"] += successful
        self.stats["failed_sends"] += (recipients - successful)
        self.stats[f"{broadcast_type}_broadcasts"] += 1

    def record_room_activity(self, room_id: str, member_count: int) -> None:
        """Record room activity metrics."""
        self.room_stats[room_id]["messages"] += 1
        self.room_stats[room_id]["members"] = member_count
        self._update_average_room_size()

    def _update_average_room_size(self) -> None:
        """Update average room size metric."""
        if not self.room_stats:
            return
        total_members = sum(stats["members"] for stats in self.room_stats.values())
        self.stats["average_room_size"] = total_members / len(self.room_stats)

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive broadcast metrics."""
        return {
            "broadcast_stats": self.stats.copy(),
            "room_stats": dict(self.room_stats),
            "top_active_rooms": self._get_top_active_rooms()
        }

    def _get_top_active_rooms(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most active rooms by message count."""
        sorted_rooms = sorted(
            self.room_stats.items(),
            key=lambda x: x[1]["messages"],
            reverse=True
        )
        return [{"room_id": room_id, **stats} for room_id, stats in sorted_rooms[:limit]]


class RoomManager:
    """Thread-safe room membership management."""
    
    def __init__(self) -> None:
        """Initialize room manager with thread-safe data structures."""
        self.room_members: Dict[str, Set[str]] = defaultdict(set)
        self.user_rooms: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join_room(self, user_id: str, room_id: str) -> None:
        """Add user to room with thread safety."""
        async with self._lock:
            self.room_members[room_id].add(user_id)
            self.user_rooms[user_id].add(room_id)

    async def leave_room(self, user_id: str, room_id: str) -> None:
        """Remove user from room with cleanup."""
        async with self._lock:
            self.room_members[room_id].discard(user_id)
            self.user_rooms[user_id].discard(room_id)
            self._cleanup_empty_room(room_id)

    def _cleanup_empty_room(self, room_id: str) -> None:
        """Clean up empty room to prevent memory leaks."""
        if not self.room_members[room_id]:
            del self.room_members[room_id]

    async def leave_all_rooms(self, user_id: str) -> None:
        """Remove user from all rooms with batch cleanup."""
        async with self._lock:
            rooms_to_leave = list(self.user_rooms[user_id])
            for room_id in rooms_to_leave:
                self.room_members[room_id].discard(user_id)
                self._cleanup_empty_room(room_id)
            self.user_rooms[user_id].clear()

    def get_room_members(self, room_id: str) -> List[str]:
        """Get list of members in room."""
        return list(self.room_members[room_id])

    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get list of rooms user belongs to."""
        return list(self.user_rooms[user_id])

    def get_room_count(self, room_id: str) -> int:
        """Get member count for room."""
        return len(self.room_members[room_id])

    def get_total_rooms(self) -> int:
        """Get total number of active rooms."""
        return len(self.room_members)


class UnifiedBroadcastingManager:
    """Unified broadcasting manager with room management and telemetry."""
    
    def __init__(self, manager) -> None:
        """Initialize with reference to unified manager."""
        self.manager = manager
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize broadcasting components."""
        self.room_manager = RoomManager()
        self.metrics = BroadcastMetrics()

    async def broadcast_to_job(self, job_id: str, 
                              message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast message to all users in job room."""
        validated_message = await self._prepare_message_for_broadcast(message)
        if not validated_message:
            return False
        return await self._execute_room_broadcast(job_id, validated_message, "job")

    async def _prepare_message_for_broadcast(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Prepare and validate message for broadcasting."""
        prepared = self.manager.messaging.message_handler.prepare_and_validate_message(message)
        if prepared:
            prepared["broadcast_timestamp"] = time.time()
        return prepared

    async def _execute_room_broadcast(self, room_id: str, message: Dict[str, Any], broadcast_type: str) -> bool:
        """Execute broadcast to room members with metrics."""
        room_members = self.room_manager.get_room_members(room_id)
        if not room_members:
            return False
        success_count = await self._send_to_room_members(room_members, message)
        self._record_broadcast_metrics(broadcast_type, len(room_members), success_count, room_id)
        return success_count > 0

    async def _send_to_room_members(self, room_members: List[str], message: Dict[str, Any]) -> int:
        """Send message to all room members and count successes."""
        send_tasks = [self._send_to_member(user_id, message) for user_id in room_members]
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        return sum(1 for result in results if result is True)

    async def _send_to_member(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to individual room member."""
        return await self.manager.messaging.send_to_user(user_id, message, retry=True)

    def _record_broadcast_metrics(self, broadcast_type: str, recipients: int, successful: int, room_id: str) -> None:
        """Record broadcast metrics for telemetry."""
        self.metrics.record_broadcast(broadcast_type, recipients, successful)
        if room_id:
            self.metrics.record_room_activity(room_id, recipients)

    async def broadcast_to_all(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast message to all connected users."""
        validated_message = await self._prepare_message_for_broadcast(message)
        if not validated_message:
            return self._create_failed_broadcast_result()
        return await self._execute_global_broadcast(validated_message)

    def _create_failed_broadcast_result(self) -> BroadcastResult:
        """Create broadcast result for validation failure."""
        return BroadcastResult(
            successful=0, failed=0, total_connections=0, message_type="invalid"
        )

    async def _execute_global_broadcast(self, message: Dict[str, Any]) -> BroadcastResult:
        """Execute global broadcast to all users."""
        all_users = self._get_all_connected_users()
        success_count = await self._send_to_all_users(all_users, message)
        total_connections = len(all_users)
        self._record_broadcast_metrics("global", total_connections, success_count, "")
        return self._create_broadcast_result(success_count, total_connections, message)

    def _get_all_connected_users(self) -> List[str]:
        """Get list of all connected user IDs."""
        return list(self.manager.connection_manager.active_connections.keys())

    async def _send_to_all_users(self, user_ids: List[str], message: Dict[str, Any]) -> int:
        """Send message to all users and count successes."""
        if not user_ids:
            return 0
        send_tasks = [self._send_to_member(user_id, message) for user_id in user_ids]
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        return sum(1 for result in results if result is True)

    def _create_broadcast_result(self, successful: int, total: int, message: Dict[str, Any]) -> BroadcastResult:
        """Create broadcast result object."""
        return BroadcastResult(
            successful=successful,
            failed=total - successful,
            total_connections=total,
            message_type=message.get("type", "unknown")
        )

    async def send_to_thread(self, thread_id: str, 
                           message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send message to thread room (alias for job broadcast)."""
        return await self.broadcast_to_job(thread_id, message)

    # Room management interface methods
    async def join_room(self, user_id: str, room_id: str) -> None:
        """Add user to broadcasting room."""
        await self.room_manager.join_room(user_id, room_id)

    async def leave_room(self, user_id: str, room_id: str) -> None:
        """Remove user from broadcasting room."""
        await self.room_manager.leave_room(user_id, room_id)

    async def leave_all_rooms(self, user_id: str) -> None:
        """Remove user from all broadcasting rooms."""
        await self.room_manager.leave_all_rooms(user_id)

    def get_room_members(self, room_id: str) -> List[str]:
        """Get members of broadcasting room."""
        return self.room_manager.get_room_members(room_id)

    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get rooms user belongs to."""
        return self.room_manager.get_user_rooms(user_id)

    # Job-specific broadcasting methods
    async def notify_job_progress(self, job_id: str, progress_data: Dict[str, Any]) -> bool:
        """Send job progress notification to job room."""
        progress_message = {
            "type": "generation_progress",
            "payload": progress_data,
            "timestamp": time.time()
        }
        return await self.broadcast_to_job(job_id, progress_message)

    async def notify_job_completion(self, job_id: str, completion_data: Dict[str, Any]) -> bool:
        """Send job completion notification to job room."""
        completion_message = {
            "type": "generation_complete",
            "payload": completion_data,
            "timestamp": time.time()
        }
        return await self.broadcast_to_job(job_id, completion_message)

    async def notify_job_error(self, job_id: str, error_data: Dict[str, Any]) -> bool:
        """Send job error notification to job room."""
        error_message = {
            "type": "generation_error",
            "payload": error_data,
            "timestamp": time.time()
        }
        return await self.broadcast_to_job(job_id, error_message)

    # Batch notification methods for efficiency
    async def notify_batch_complete(self, job_id: str, batch_num: int, batch_size: int) -> bool:
        """Send batch completion notification."""
        batch_message = self._create_batch_completion_message(job_id, batch_num, batch_size)
        return await self.broadcast_to_job(job_id, batch_message)

    def _create_batch_completion_message(self, job_id: str, batch_num: int, batch_size: int) -> Dict[str, Any]:
        """Create batch completion message structure."""
        return {
            "type": "batch_complete",
            "payload": {"job_id": job_id, "batch_num": batch_num, "batch_size": batch_size},
            "timestamp": time.time()
        }

    # Administrative broadcasting methods
    async def broadcast_system_announcement(self, announcement: str, priority: bool = False) -> BroadcastResult:
        """Broadcast system announcement to all users."""
        announcement_message = {
            "type": "system_announcement",
            "payload": {"message": announcement, "priority": priority},
            "timestamp": time.time(),
            "system": True
        }
        return await self.broadcast_to_all(announcement_message)

    async def broadcast_maintenance_notice(self, maintenance_data: Dict[str, Any]) -> BroadcastResult:
        """Broadcast maintenance notice to all users."""
        maintenance_message = {
            "type": "maintenance_notice",
            "payload": maintenance_data,
            "timestamp": time.time(),
            "system": True
        }
        return await self.broadcast_to_all(maintenance_message)

    def get_broadcasting_stats(self) -> Dict[str, Any]:
        """Get comprehensive broadcasting statistics."""
        room_stats = self._create_room_statistics()
        return self._combine_stats_with_metrics(room_stats)

    def _create_room_statistics(self) -> Dict[str, Any]:
        """Create room management statistics."""
        return {
            "total_rooms": self.room_manager.get_total_rooms(),
            "room_details": {room_id: self.room_manager.get_room_count(room_id) 
                           for room_id in self.room_manager.room_members.keys()}
        }

    def _combine_stats_with_metrics(self, room_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Combine room stats with broadcast metrics."""
        return {
            **self.metrics.get_metrics(),
            "room_management": room_stats
        }