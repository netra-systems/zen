"""
WebSocket State Management Helpers

Utility classes for validating state synchronization and tracking state differences
in backend-frontend communication tests.
"""

import time
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StateSnapshot:
    """Represents a point-in-time state snapshot."""
    timestamp: float
    state_type: str  # 'user', 'thread', 'websocket', 'ui'
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "state_type": self.state_type,
            "data": self.data,
            "event_id": self.event_id
        }


@dataclass
class StateDiff:
    """Represents differences between two state snapshots."""
    before: StateSnapshot
    after: StateSnapshot
    added: Dict[str, Any] = field(default_factory=dict)
    removed: Dict[str, Any] = field(default_factory=dict)
    modified: Dict[str, Any] = field(default_factory=dict)
    unchanged: Dict[str, Any] = field(default_factory=dict)
    diff_time_ms: float = 0.0
    
    def has_changes(self) -> bool:
        """Check if diff contains any changes."""
        return bool(self.added or self.removed or self.modified)
    
    def get_change_summary(self) -> Dict[str, int]:
        """Get summary of changes."""
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "modified": len(self.modified),
            "unchanged": len(self.unchanged)
        }


class StateValidator:
    """Validates state consistency and synchronization."""
    
    def __init__(self):
        self.validation_rules = {
            "user": self._validate_user_state,
            "thread": self._validate_thread_state,
            "websocket": self._validate_websocket_state,
            "ui": self._validate_ui_state
        }
    
    def validate_state(self, snapshot: StateSnapshot) -> Dict[str, Any]:
        """Validate a state snapshot against defined rules."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "state_type": snapshot.state_type,
            "timestamp": snapshot.timestamp
        }
        
        # Get validator for state type
        validator = self.validation_rules.get(snapshot.state_type)
        if not validator:
            validation_result["errors"].append(f"No validator for state type: {snapshot.state_type}")
            validation_result["valid"] = False
            return validation_result
        
        # Run validation
        try:
            validator(snapshot.data, validation_result)
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            validation_result["valid"] = False
        
        return validation_result
    
    def _validate_user_state(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate user state structure."""
        required_fields = ["id", "email"]
        
        for field in required_fields:
            if field not in data:
                result["errors"].append(f"Missing required user field: {field}")
        
        # Validate email format
        if "email" in data and "@" not in str(data["email"]):
            result["errors"].append("Invalid email format")
        
        # Check permissions structure
        if "permissions" in data and not isinstance(data["permissions"], (list, dict)):
            result["warnings"].append("Permissions should be list or dict")
    
    def _validate_thread_state(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate thread state structure."""
        required_fields = ["id", "messages"]
        
        for field in required_fields:
            if field not in data:
                result["errors"].append(f"Missing required thread field: {field}")
        
        # Validate messages structure
        if "messages" in data:
            messages = data["messages"]
            if not isinstance(messages, list):
                result["errors"].append("Messages must be a list")
            else:
                for i, msg in enumerate(messages):
                    if not isinstance(msg, dict):
                        result["errors"].append(f"Message {i} must be a dict")
                        continue
                    
                    # Check required message fields
                    required_msg_fields = ["id", "content", "role", "timestamp"]
                    for field in required_msg_fields:
                        if field not in msg:
                            result["errors"].append(f"Message {i} missing field: {field}")
        
        # Validate status
        if "status" in data:
            valid_statuses = ["active", "archived", "deleted"]
            if data["status"] not in valid_statuses:
                result["warnings"].append(f"Unknown thread status: {data['status']}")
    
    def _validate_websocket_state(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate WebSocket state structure."""
        required_fields = ["connected"]
        
        for field in required_fields:
            if field not in data:
                result["errors"].append(f"Missing required websocket field: {field}")
        
        # Validate connection status
        if "connected" in data and not isinstance(data["connected"], bool):
            result["errors"].append("WebSocket connected must be boolean")
        
        # Validate message queue
        if "messageQueue" in data and not isinstance(data["messageQueue"], list):
            result["warnings"].append("Message queue should be a list")
        
        # Check last event timestamp
        if "lastEvent" in data:
            if not isinstance(data["lastEvent"], (int, float)):
                result["warnings"].append("lastEvent should be timestamp")
    
    def _validate_ui_state(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate UI state structure."""
        # Check loading states
        if "loading" in data and not isinstance(data["loading"], bool):
            result["warnings"].append("Loading should be boolean")
        
        # Check error state
        if "error" in data and data["error"] is not None:
            if not isinstance(data["error"], str):
                result["warnings"].append("Error should be string or null")
        
        # Validate optimistic updates
        if "optimisticUpdates" in data:
            updates = data["optimisticUpdates"]
            if not isinstance(updates, (list, dict)):
                result["warnings"].append("OptimisticUpdates should be list or dict")


class StateDiffTracker:
    """Tracks and computes differences between state snapshots."""
    
    def __init__(self):
        self.snapshots: List[StateSnapshot] = []
        self.diffs: List[StateDiff] = []
    
    def add_snapshot(self, state_type: str, data: Dict[str, Any]) -> StateSnapshot:
        """Add a new state snapshot."""
        snapshot = StateSnapshot(
            timestamp=time.time(),
            state_type=state_type,
            data=data.copy()
        )
        
        self.snapshots.append(snapshot)
        
        # Compute diff with previous snapshot of same type
        previous = self._get_previous_snapshot(state_type)
        if previous:
            diff = self.compute_diff(previous, snapshot)
            self.diffs.append(diff)
        
        return snapshot
    
    def _get_previous_snapshot(self, state_type: str) -> Optional[StateSnapshot]:
        """Get the most recent snapshot of the given type."""
        for snapshot in reversed(self.snapshots[:-1]):  # Exclude the last one we just added
            if snapshot.state_type == state_type:
                return snapshot
        return None
    
    def compute_diff(self, before: StateSnapshot, after: StateSnapshot) -> StateDiff:
        """Compute difference between two snapshots."""
        start_time = time.time()
        
        diff = StateDiff(before=before, after=after)
        
        # Ensure both snapshots are same type
        if before.state_type != after.state_type:
            raise ValueError(f"Cannot diff different state types: {before.state_type} vs {after.state_type}")
        
        # Compute differences
        self._compute_dict_diff(before.data, after.data, diff)
        
        diff.diff_time_ms = (time.time() - start_time) * 1000
        
        return diff
    
    def _compute_dict_diff(self, before_data: Dict[str, Any], after_data: Dict[str, Any], diff: StateDiff) -> None:
        """Compute differences between two dictionaries."""
        before_keys = set(before_data.keys())
        after_keys = set(after_data.keys())
        
        # Added keys
        added_keys = after_keys - before_keys
        for key in added_keys:
            diff.added[key] = after_data[key]
        
        # Removed keys
        removed_keys = before_keys - after_keys
        for key in removed_keys:
            diff.removed[key] = before_data[key]
        
        # Check common keys for modifications
        common_keys = before_keys & after_keys
        for key in common_keys:
            before_value = before_data[key]
            after_value = after_data[key]
            
            if self._values_different(before_value, after_value):
                diff.modified[key] = {
                    "before": before_value,
                    "after": after_value
                }
            else:
                diff.unchanged[key] = after_value
    
    def _values_different(self, value1: Any, value2: Any) -> bool:
        """Check if two values are different with special handling for complex types."""
        # Handle lists
        if isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                return True
            return any(self._values_different(v1, v2) for v1, v2 in zip(value1, value2))
        
        # Handle dicts
        if isinstance(value1, dict) and isinstance(value2, dict):
            if set(value1.keys()) != set(value2.keys()):
                return True
            return any(self._values_different(value1[k], value2[k]) for k in value1.keys())
        
        # Default comparison
        return value1 != value2
    
    def get_diffs_by_type(self, state_type: str) -> List[StateDiff]:
        """Get all diffs for a specific state type."""
        return [diff for diff in self.diffs if diff.before.state_type == state_type]
    
    def get_recent_diffs(self, seconds: float = 10.0) -> List[StateDiff]:
        """Get diffs from the last N seconds."""
        cutoff_time = time.time() - seconds
        return [diff for diff in self.diffs if diff.after.timestamp >= cutoff_time]
    
    def get_snapshots_by_type(self, state_type: str) -> List[StateSnapshot]:
        """Get all snapshots for a specific state type."""
        return [snapshot for snapshot in self.snapshots if snapshot.state_type == state_type]
    
    def clear(self) -> None:
        """Clear all snapshots and diffs."""
        self.snapshots.clear()
        self.diffs.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of tracked state changes."""
        summary = {
            "total_snapshots": len(self.snapshots),
            "total_diffs": len(self.diffs),
            "state_types": {},
            "recent_activity": {}
        }
        
        # Count by state type
        for snapshot in self.snapshots:
            state_type = snapshot.state_type
            if state_type not in summary["state_types"]:
                summary["state_types"][state_type] = 0
            summary["state_types"][state_type] += 1
        
        # Recent activity (last 30 seconds)
        recent_diffs = self.get_recent_diffs(30.0)
        summary["recent_activity"] = {
            "diffs_count": len(recent_diffs),
            "changes_detected": sum(1 for diff in recent_diffs if diff.has_changes())
        }
        
        return summary


class StatePerformanceTracker:
    """Tracks performance metrics for state operations."""
    
    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
    
    def track_operation(self, operation: str, duration_ms: float, **metadata) -> None:
        """Track a state operation with its duration and metadata."""
        metric = {
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
            **metadata
        }
        self.metrics.append(metric)
    
    def get_average_duration(self, operation: str = None) -> float:
        """Get average duration for an operation or all operations."""
        filtered_metrics = self.metrics
        if operation:
            filtered_metrics = [m for m in self.metrics if m["operation"] == operation]
        
        if not filtered_metrics:
            return 0.0
        
        total_duration = sum(m["duration_ms"] for m in filtered_metrics)
        return total_duration / len(filtered_metrics)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.metrics:
            return {"no_data": True}
        
        operations = {}
        for metric in self.metrics:
            op = metric["operation"]
            if op not in operations:
                operations[op] = []
            operations[op].append(metric["duration_ms"])
        
        summary = {}
        for op, durations in operations.items():
            summary[op] = {
                "count": len(durations),
                "avg_ms": sum(durations) / len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations),
                "total_ms": sum(durations)
            }
        
        return summary