"""Unified ID Generator - SSOT Implementation for Python

CLAUDE.md Compliance:
- Single Source of Truth for all ID generation across Python backend
- Eliminates scattered uuid.uuid4().hex[:8] patterns causing SSOT violations
- Provides consistent, predictable ID formats with collision protection
- Enables proper request isolation and context tracking

Business Value Justification (BVJ):
- Segment: All (Infrastructure supporting all user tiers)
- Business Goal: System reliability and request isolation integrity
- Value Impact: Prevents ID collisions that could cause user data leakage
- Strategic Impact: CRITICAL - Proper isolation prevents security vulnerabilities

FIXES IDENTIFIED SSOT VIOLATIONS:
1. Scattered uuid.uuid4().hex[:8] patterns throughout codebase
2. Inconsistent ID formats between components
3. No collision detection or validation mechanisms
4. Manual UserExecutionContext creation with inline ID generation
"""

import time
import uuid
import secrets
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

# Global counter for ID generation with thread safety
_global_counter_lock = Lock()
_global_counter = 0


def _get_next_counter() -> int:
    """Thread-safe global counter for ID uniqueness."""
    global _global_counter
    with _global_counter_lock:
        _global_counter += 1
        return _global_counter


def reset_global_counter() -> None:
    """Reset counter for testing purposes."""
    global _global_counter
    with _global_counter_lock:
        _global_counter = 0


@dataclass
class IdComponents:
    """Components of a generated ID for analysis and debugging."""
    prefix: str
    timestamp: int
    counter: int
    random: str
    full_id: str


class UnifiedIdGenerator:
    """Single Source of Truth for all ID generation in the system.
    
    This class provides consistent, collision-resistant ID generation
    following CLAUDE.md SSOT principles. All ID generation throughout
    the codebase should use this class.
    """
    
    @staticmethod
    def generate_base_id(prefix: str = "id", include_random: bool = True, 
                        random_length: int = 8) -> str:
        """Core ID generation with triple collision protection.
        
        Args:
            prefix: String prefix for the ID
            include_random: Whether to include random component
            random_length: Length of random component (default 8)
            
        Returns:
            Guaranteed unique ID string with format: prefix_timestamp_counter[_random]
        """
        timestamp = int(time.time() * 1000)  # Milliseconds for higher precision
        counter = _get_next_counter()
        
        if include_random:
            # Use secrets for cryptographically strong randomness
            random_component = secrets.token_hex(random_length // 2)
            return f"{prefix}_{timestamp}_{counter}_{random_component}"
        
        return f"{prefix}_{timestamp}_{counter}"
    
    @staticmethod
    def generate_user_context_ids(user_id: str, operation: str = "context") -> Tuple[str, str, str]:
        """Generate consistent IDs for UserExecutionContext creation.
        
        CRITICAL FIX: Thread ID consistency to prevent WebSocket Factory resource leaks.
        This addresses the root cause where thread_id and run_id have different patterns,
        causing cleanup logic to fail to find the right manager during disconnection.
        
        This is the SSOT method for creating UserExecutionContext IDs,
        replacing all scattered uuid.uuid4().hex[:8] patterns.
        
        Args:
            user_id: User identifier for context
            operation: Operation type for context naming
            
        Returns:
            Tuple of (thread_id, run_id, request_id) with CONSISTENT patterns
        """
        base_timestamp = int(time.time() * 1000)
        counter_base = _get_next_counter()
        
        # CRITICAL FIX: Use consistent ID pattern for both thread_id and run_id
        # This prevents the pattern mismatch that causes WebSocket manager cleanup failures
        base_id = f"{operation}_{base_timestamp}"
        random_part = secrets.token_hex(4)
        
        # Generate related but CONSISTENT IDs - thread_id contains same base as run_id
        thread_id = f"thread_{base_id}_{counter_base}_{random_part}"
        run_id = f"{base_id}"  # run_id is the base that thread_id contains
        request_id = f"req_{operation}_{base_timestamp}_{counter_base + 1}_{secrets.token_hex(4)}"
        
        return thread_id, run_id, request_id
    
    @staticmethod
    def generate_websocket_connection_id(user_id: str, connection_timestamp: Optional[float] = None) -> str:
        """Generate WebSocket connection ID.
        
        Args:
            user_id: User identifier
            connection_timestamp: Optional connection timestamp
            
        Returns:
            Unique WebSocket connection ID
        """
        timestamp = int((connection_timestamp or time.time()) * 1000)
        counter = _get_next_counter()
        user_prefix = user_id[:8] if len(user_id) >= 8 else user_id
        random_part = secrets.token_hex(4)
        
        return f"ws_conn_{user_prefix}_{timestamp}_{counter}_{random_part}"
    
    @staticmethod
    def generate_websocket_client_id(user_id: str, connection_timestamp: Optional[float] = None) -> str:
        """Generate WebSocket client ID.
        
        Args:
            user_id: User identifier
            connection_timestamp: Optional connection timestamp
            
        Returns:
            Unique WebSocket client ID
        """
        timestamp = int((connection_timestamp or time.time()) * 1000)
        counter = _get_next_counter()
        user_prefix = user_id[:8] if len(user_id) >= 8 else user_id
        random_part = secrets.token_hex(4)
        
        return f"ws_client_{user_prefix}_{timestamp}_{counter}_{random_part}"
    
    @staticmethod
    def generate_agent_execution_id(agent_type: str, user_id: str) -> str:
        """Generate agent execution ID.
        
        Args:
            agent_type: Type of agent being executed
            user_id: User context identifier
            
        Returns:
            Unique agent execution ID
        """
        return UnifiedIdGenerator.generate_base_id(f"agent_{agent_type}_{user_id[:8]}")
    
    @staticmethod
    def generate_tool_execution_id(tool_name: str, agent_id: Optional[str] = None) -> str:
        """Generate tool execution ID.
        
        Args:
            tool_name: Name of the tool being executed
            agent_id: Optional parent agent ID
            
        Returns:
            Unique tool execution ID
        """
        prefix = f"tool_{tool_name}"
        if agent_id:
            # Extract agent identifier for context
            agent_part = agent_id.split('_')[-1][:8] if '_' in agent_id else agent_id[:8]
            prefix = f"tool_{tool_name}_{agent_part}"
        
        return UnifiedIdGenerator.generate_base_id(prefix)
    
    @staticmethod
    def generate_message_id(message_type: str, user_id: str, thread_id: Optional[str] = None) -> str:
        """Generate message ID for chat/WebSocket messages.
        
        Args:
            message_type: Type of message (user, agent, system)
            user_id: User identifier
            thread_id: Optional thread context
            
        Returns:
            Unique message ID
        """
        prefix = f"msg_{message_type}_{user_id[:8]}"
        if thread_id:
            thread_part = thread_id.split('_')[-1][:8] if '_' in thread_id else thread_id[:8]
            prefix = f"msg_{message_type}_{user_id[:8]}_{thread_part}"
        
        return UnifiedIdGenerator.generate_base_id(prefix)
    
    @staticmethod
    def generate_session_id(user_id: str, session_type: str = "web") -> str:
        """Generate session ID.
        
        Args:
            user_id: User identifier
            session_type: Type of session (web, mobile, api)
            
        Returns:
            Unique session ID
        """
        user_prefix = user_id[:8] if len(user_id) >= 8 else user_id
        return UnifiedIdGenerator.generate_base_id(f"session_{session_type}_{user_prefix}")
    
    @staticmethod
    def generate_error_context_id(error_type: str, user_id: str) -> str:
        """Generate error context ID for error handling.
        
        Args:
            error_type: Type of error (json, websocket, exception)
            user_id: User identifier
            
        Returns:
            Unique error context ID
        """
        user_prefix = user_id[:8] if len(user_id) >= 8 else user_id
        return UnifiedIdGenerator.generate_base_id(f"error_{error_type}_{user_prefix}")
    
    @staticmethod
    def generate_batch_ids(prefix: str, count: int, include_random: bool = True) -> List[str]:
        """Generate multiple unique IDs efficiently.
        
        Args:
            prefix: Common prefix for all IDs
            count: Number of IDs to generate
            include_random: Whether to include random components
            
        Returns:
            List of unique IDs
        """
        ids = []
        timestamp = int(time.time() * 1000)
        
        for i in range(count):
            counter = _get_next_counter()
            if include_random:
                random_part = secrets.token_hex(4)
                ids.append(f"{prefix}_{timestamp}_{counter}_{random_part}")
            else:
                ids.append(f"{prefix}_{timestamp}_{counter}")
        
        return ids
    
    @staticmethod
    def parse_id(id_string: str) -> Optional[IdComponents]:
        """Parse a generated ID into its components.
        
        Args:
            id_string: Generated ID to parse
            
        Returns:
            IdComponents object or None if invalid
        """
        if not id_string or not isinstance(id_string, str):
            return None
        
        parts = id_string.split('_')
        if len(parts) < 3:
            return None
        
        try:
            # Extract components (format: prefix_timestamp_counter[_random])
            prefix = '_'.join(parts[:-3]) if len(parts) > 3 else parts[0]
            timestamp = int(parts[-3])
            counter = int(parts[-2])
            random_part = parts[-1] if len(parts) > 3 else ""
            
            return IdComponents(
                prefix=prefix,
                timestamp=timestamp,
                counter=counter,
                random=random_part,
                full_id=id_string
            )
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def is_valid_id(id_string: str, expected_prefix: Optional[str] = None) -> bool:
        """Validate that an ID follows the expected format.
        
        Args:
            id_string: ID to validate
            expected_prefix: Optional expected prefix
            
        Returns:
            True if ID is valid
        """
        parsed = UnifiedIdGenerator.parse_id(id_string)
        if not parsed:
            return False
        
        if expected_prefix and not parsed.prefix.startswith(expected_prefix):
            return False
        
        # Validate timestamp is reasonable (not too old, not in future)
        current_time = int(time.time() * 1000)
        time_diff = abs(current_time - parsed.timestamp)
        
        # Allow IDs from up to 1 year ago or 1 hour in future (clock skew)
        max_age = 365 * 24 * 60 * 60 * 1000  # 1 year in milliseconds
        max_future = 60 * 60 * 1000  # 1 hour in milliseconds
        
        return time_diff <= max_age and (parsed.timestamp <= current_time + max_future)
    
    @staticmethod
    def get_id_age(id_string: str) -> int:
        """Get age of ID in milliseconds.
        
        Args:
            id_string: ID to analyze
            
        Returns:
            Age in milliseconds or -1 if invalid
        """
        parsed = UnifiedIdGenerator.parse_id(id_string)
        if not parsed:
            return -1
        
        current_time = int(time.time() * 1000)
        return current_time - parsed.timestamp
    
    # Session Management Methods - SSOT for Context Lifecycle
    _active_sessions: Dict[str, Dict[str, Any]] = {}
    _session_lock = Lock()
    
    @classmethod
    def get_or_create_user_session(cls, user_id: str, thread_id: Optional[str] = None, 
                                  run_id: Optional[str] = None, operation: str = "session") -> Dict[str, str]:
        """Get existing session or create new one - SSOT for session lifecycle.
        
        This method addresses the critical architectural issue where the system
        creates new contexts for every message instead of maintaining continuity.
        
        Args:
            user_id: User identifier
            thread_id: Optional thread identifier for conversation continuity
            run_id: Optional run identifier - determines session behavior:
                   - None: Use existing session run_id or create new
                   - Matches existing: Continue with existing session  
                   - Different: Create new run within thread (new agent execution)
            operation: Operation type for context naming
            
        Returns:
            Dictionary with session identifiers (thread_id, run_id, request_id)
        """
        with cls._session_lock:
            # Generate session key
            if thread_id:
                session_key = f"{user_id}:{thread_id}"
            else:
                session_key = f"{user_id}:default"
            
            # Check if session exists
            if session_key in cls._active_sessions:
                existing_session = cls._active_sessions[session_key]
                
                # Handle run_id logic
                if run_id is None:
                    # No run_id specified - use existing session's run_id
                    session_run_id = existing_session["run_id"]
                elif run_id == existing_session["run_id"]:
                    # Same run_id - continue existing session
                    session_run_id = existing_session["run_id"]
                else:
                    # Different run_id - create new run within same thread
                    session_run_id = run_id
                    existing_session["run_id"] = session_run_id
                    existing_session["operation"] = f"{operation}_new_run"
                
                # Update last activity
                existing_session["last_activity"] = int(time.time() * 1000)
                return {
                    "thread_id": existing_session["thread_id"],
                    "run_id": session_run_id,
                    "request_id": cls.generate_base_id("req", True, 8)  # Always new request ID
                }
            
            # Create new session
            if thread_id:
                session_thread_id = thread_id
            else:
                session_thread_id = cls.generate_base_id(f"thread_{operation}", True, 8)
            
            # Handle run_id for new session
            if run_id:
                session_run_id = run_id
            else:
                session_run_id = cls.generate_base_id(f"run_{operation}", True, 8)
                
            session_request_id = cls.generate_base_id("req", True, 8)
            
            # Store session
            cls._active_sessions[session_key] = {
                "user_id": user_id,
                "thread_id": session_thread_id,
                "run_id": session_run_id,
                "created_at": int(time.time() * 1000),
                "last_activity": int(time.time() * 1000),
                "operation": operation
            }
            
            return {
                "thread_id": session_thread_id,
                "run_id": session_run_id,
                "request_id": session_request_id
            }
    
    @classmethod
    def get_existing_session(cls, user_id: str, thread_id: str) -> Optional[Dict[str, str]]:
        """Get existing session without creating new one.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            
        Returns:
            Session identifiers if exists, None otherwise
        """
        with cls._session_lock:
            session_key = f"{user_id}:{thread_id}"
            if session_key in cls._active_sessions:
                existing_session = cls._active_sessions[session_key]
                existing_session["last_activity"] = int(time.time() * 1000)
                return {
                    "thread_id": existing_session["thread_id"],
                    "run_id": existing_session["run_id"],
                    "request_id": cls.generate_base_id("req", True, 8)
                }
            return None
    
    @classmethod
    def cleanup_expired_sessions(cls, max_age_hours: int = 24) -> int:
        """Clean up expired sessions to prevent memory leaks.
        
        Args:
            max_age_hours: Maximum age of sessions in hours
            
        Returns:
            Number of sessions cleaned up
        """
        with cls._session_lock:
            current_time = int(time.time() * 1000)
            max_age_ms = max_age_hours * 60 * 60 * 1000
            
            expired_keys = []
            for session_key, session_data in cls._active_sessions.items():
                age = current_time - session_data["last_activity"]
                if age > max_age_ms:
                    expired_keys.append(session_key)
            
            for key in expired_keys:
                del cls._active_sessions[key]
                
            return len(expired_keys)
    
    @classmethod
    def get_active_sessions_count(cls) -> int:
        """Get count of active sessions for monitoring.
        
        Returns:
            Number of active sessions
        """
        with cls._session_lock:
            return len(cls._active_sessions)
    
    @classmethod
    def invalidate_user_sessions(cls, user_id: str) -> int:
        """Invalidate all sessions for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        with cls._session_lock:
            keys_to_remove = [key for key in cls._active_sessions.keys() 
                             if key.startswith(f"{user_id}:")]
            
            for key in keys_to_remove:
                del cls._active_sessions[key]
                
            return len(keys_to_remove)


# Convenience functions for common use cases
def generate_uuid_replacement() -> str:
    """Direct replacement for uuid.uuid4().hex[:8] patterns.
    
    Returns:
        8-character unique identifier
    """
    return UnifiedIdGenerator.generate_base_id("uid", True, 8).split('_')[-1]


def create_user_execution_context_factory(user_id: str, operation: str = "context"):
    """Factory function for creating UserExecutionContext with proper IDs.
    
    This is the SSOT method for UserExecutionContext creation, eliminating
    all manual ID generation patterns.
    
    Args:
        user_id: User identifier
        operation: Operation type for context
        
    Returns:
        Dictionary with thread_id, run_id, request_id for context creation
    """
    thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, operation)
    
    return {
        'user_id': user_id,
        'thread_id': thread_id,
        'run_id': run_id,
        'request_id': request_id
    }


# Test utilities
class TestIdUtils:
    """Test utilities for predictable ID generation."""
    
    @staticmethod
    def reset() -> None:
        """Reset counters for test isolation."""
        reset_global_counter()
    
    @staticmethod
    def create_test_id(prefix: str, sequence: int) -> str:
        """Create predictable test ID."""
        return f"{prefix}_test_{sequence}"
    
    @staticmethod
    def validate_uniqueness_in_list(ids: List[str]) -> bool:
        """Validate that all IDs in list are unique."""
        return len(ids) == len(set(ids))
    
    @staticmethod
    def create_test_context_ids(user_id: str, sequence: int) -> Dict[str, str]:
        """Create predictable context IDs for testing."""
        return {
            'user_id': user_id,
            'thread_id': f"thread_test_{sequence}",
            'run_id': f"run_test_{sequence}",
            'request_id': f"req_test_{sequence}"
        }


# Export the main class and convenience functions
__all__ = [
    'UnifiedIdGenerator',
    'generate_uuid_replacement', 
    'create_user_execution_context_factory',
    'TestIdUtils',
    'IdComponents'
]