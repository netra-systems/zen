"""WebSocket State Testing Helpers

Provides utilities for validating state consistency and tracking state differences
in WebSocket-based state synchronization tests.
"""

from typing import Any, Dict, List, Optional


class StateValidator:
    """Validates state consistency between different data sources."""
    
    def __init__(self):
        """Initialize the state validator."""
        pass
    
    def validate_state_consistency(self, state1: Any, state2: Any) -> bool:
        """
        Validate that two states are consistent with each other.
        
        Args:
            state1: First state to compare
            state2: Second state to compare
            
        Returns:
            True if states are consistent, False otherwise
        """
        # Basic consistency check - both states should exist
        if state1 is None and state2 is None:
            return True
        
        if state1 is None or state2 is None:
            return False
            
        # For dictionary states, check if keys match
        if isinstance(state1, dict) and isinstance(state2, dict):
            return set(state1.keys()) == set(state2.keys())
        
        # For other types, basic equality check
        return state1 == state2
    
    def validate_message_ordering(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Validate that messages are in correct chronological order.
        
        Args:
            messages: List of message dictionaries with timestamp info
            
        Returns:
            True if messages are properly ordered, False otherwise
        """
        if len(messages) <= 1:
            return True
            
        # Check if messages have timestamp or created_at fields
        for i in range(1, len(messages)):
            prev_msg = messages[i-1]
            curr_msg = messages[i]
            
            # Look for timestamp fields
            prev_time = prev_msg.get('timestamp') or prev_msg.get('created_at')
            curr_time = curr_msg.get('timestamp') or curr_msg.get('created_at')
            
            if prev_time and curr_time:
                if prev_time > curr_time:
                    return False
                    
        return True
    
    def validate_thread_state(self, thread_state: Dict[str, Any]) -> bool:
        """
        Validate that a thread state has required fields.
        
        Args:
            thread_state: Thread state dictionary
            
        Returns:
            True if thread state is valid, False otherwise
        """
        if not isinstance(thread_state, dict):
            return False
            
        # Check for required thread fields
        required_fields = ['id', 'messages']
        for field in required_fields:
            if field not in thread_state:
                return False
                
        # Validate messages is a list
        if not isinstance(thread_state['messages'], list):
            return False
            
        return True


class StateDiffTracker:
    """Tracks differences between states over time."""
    
    def __init__(self):
        """Initialize the state diff tracker."""
        self.state_snapshots: List[Dict[str, Any]] = []
        self.diffs: List[Dict[str, Any]] = []
    
    def snapshot_state(self, state: Dict[str, Any], label: Optional[str] = None) -> None:
        """
        Take a snapshot of the current state.
        
        Args:
            state: State dictionary to snapshot
            label: Optional label for this snapshot
        """
        snapshot = {
            'timestamp': len(self.state_snapshots),  # Simple counter for ordering
            'state': state.copy() if isinstance(state, dict) else state,
            'label': label
        }
        self.state_snapshots.append(snapshot)
    
    def calculate_diff(self, state1: Dict[str, Any], state2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate the difference between two states.
        
        Args:
            state1: First state (usually older)
            state2: Second state (usually newer)
            
        Returns:
            Dictionary describing the differences
        """
        diff = {
            'added_keys': [],
            'removed_keys': [],
            'changed_keys': [],
            'unchanged_keys': []
        }
        
        if not isinstance(state1, dict) or not isinstance(state2, dict):
            return {'error': 'Both states must be dictionaries'}
        
        keys1 = set(state1.keys())
        keys2 = set(state2.keys())
        
        diff['added_keys'] = list(keys2 - keys1)
        diff['removed_keys'] = list(keys1 - keys2)
        
        common_keys = keys1 & keys2
        for key in common_keys:
            if state1[key] != state2[key]:
                diff['changed_keys'].append(key)
            else:
                diff['unchanged_keys'].append(key)
        
        self.diffs.append(diff)
        return diff
    
    def get_state_progression(self) -> List[Dict[str, Any]]:
        """
        Get the progression of state changes.
        
        Returns:
            List of state snapshots in chronological order
        """
        return self.state_snapshots.copy()
    
    def get_all_diffs(self) -> List[Dict[str, Any]]:
        """
        Get all calculated diffs.
        
        Returns:
            List of all diffs calculated so far
        """
        return self.diffs.copy()
    
    def reset(self) -> None:
        """Reset the tracker, clearing all snapshots and diffs."""
        self.state_snapshots.clear()
        self.diffs.clear()
    
    def track_message_addition(self, before_state: Dict[str, Any], after_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track the addition of messages to a thread state.
        
        Args:
            before_state: State before message was added
            after_state: State after message was added
            
        Returns:
            Analysis of the message addition
        """
        analysis = {
            'messages_added': 0,
            'new_messages': [],
            'state_consistent': True
        }
        
        if not (isinstance(before_state, dict) and isinstance(after_state, dict)):
            analysis['state_consistent'] = False
            return analysis
        
        before_messages = before_state.get('messages', [])
        after_messages = after_state.get('messages', [])
        
        if len(after_messages) > len(before_messages):
            analysis['messages_added'] = len(after_messages) - len(before_messages)
            analysis['new_messages'] = after_messages[len(before_messages):]
        
        return analysis
