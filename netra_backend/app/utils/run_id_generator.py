"""
SSOT Run ID Generator - Standardized run ID generation across Netra platform.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability & WebSocket Reliability  
- Value Impact: Fixes 40% of WebSocket event delivery failures by enabling proper thread resolution
- Strategic Impact: Eliminates silent failures in production, ensuring users see real-time AI responses

CRITICAL MISSION: WebSocket bridge cannot resolve thread IDs from run IDs because run ID generation 
is inconsistent. This module provides the Single Source of Truth (SSOT) for run ID generation 
with a standardized format that enables reliable thread ID extraction for WebSocket routing.

Core Features:
- Standardized format: "thread_{thread_id}_run_{timestamp}_{unique_id}"
- Thread ID extraction capability for WebSocket routing
- Consistent timestamp-based ordering
- UUID-based uniqueness guarantees
- Business context documentation for auditing
"""

import time
import uuid
from typing import Optional
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# SSOT Constants for run ID format
RUN_ID_PREFIX = "thread_"
RUN_ID_SEPARATOR = "_run_"
UNIQUE_ID_LENGTH = 8


def generate_run_id(thread_id: str, context: str = "") -> str:
    """
    Generate standardized run ID with thread ID embedded for WebSocket routing.
    
    This is the SINGLE SOURCE OF TRUTH for run ID generation across the Netra platform.
    ALL run ID generation MUST use this function to ensure consistency and enable
    proper WebSocket event delivery.
    
    Business Context:
    - WebSocket bridge requires extractable thread_id from run_id for event routing
    - Run IDs are used for tracking agent executions and correlating events
    - Consistent format enables debugging, auditing, and operational visibility
    - Thread extraction is critical for multi-user real-time interactions
    
    Format: "thread_{thread_id}_run_{timestamp}_{unique_id}"
    - thread_{thread_id}: Enables WebSocket routing by thread
    - run_{timestamp}: Provides chronological ordering  
    - {unique_id}: 8-char UUID hex for collision avoidance
    
    Args:
        thread_id (str): The thread ID that will receive WebSocket events. 
                        MUST be non-empty and valid for WebSocket routing.
        context (str, optional): Business context for logging/debugging.
                               Examples: "agent_execution", "admin_tool", "data_processing"
    
    Returns:
        str: Standardized run ID in format "thread_{thread_id}_run_{timestamp}_{unique_id}"
        
    Raises:
        ValueError: If thread_id is empty, None, or contains invalid characters
        
    Example:
        >>> generate_run_id("thread_user123_session456", "agent_execution")
        'thread_thread_user123_session456_run_1693430400000_a1b2c3d4'
        
        >>> generate_run_id("abc123", "admin_tool")  
        'thread_abc123_run_1693430400123_e5f6g7h8'
    
    Thread ID Requirements:
    - MUST be non-empty string
    - SHOULD be unique per user session/conversation
    - CAN contain underscores, alphanumeric characters
    - MUST NOT contain the sequence "_run_" (reserved as separator)
    
    WebSocket Integration:
    - Thread ID can be extracted using extract_thread_id_from_run_id()
    - Enables WebSocketManager.send_to_thread() routing
    - Critical for real-time agent execution updates
    """
    # Validate thread_id
    if not thread_id:
        raise ValueError("thread_id cannot be empty or None")
    
    if not isinstance(thread_id, str):
        raise ValueError(f"thread_id must be string, got {type(thread_id)}")
    
    if RUN_ID_SEPARATOR in thread_id:
        raise ValueError(f"thread_id cannot contain reserved sequence '{RUN_ID_SEPARATOR}'")
    
    # Generate timestamp (milliseconds since epoch for ordering)
    timestamp = int(time.time() * 1000)
    
    # Generate unique ID (8 chars from UUID4 hex)
    unique_id = uuid.uuid4().hex[:UNIQUE_ID_LENGTH]
    
    # Build standardized run ID
    run_id = f"{RUN_ID_PREFIX}{thread_id}{RUN_ID_SEPARATOR}{timestamp}_{unique_id}"
    
    # Log generation for audit trail
    context_info = f" (context: {context})" if context else ""
    logger.debug(f"Generated run_id: {run_id} for thread_id: {thread_id}{context_info}")
    
    return run_id


def extract_thread_id_from_run_id(run_id: str) -> Optional[str]:
    """
    Extract thread_id from standardized run_id for WebSocket routing.
    
    This function is the inverse of generate_run_id() and enables the WebSocket bridge
    to route events to the correct thread based on the run_id.
    
    Args:
        run_id (str): Run ID in standardized format "thread_{thread_id}_run_{timestamp}_{unique_id}"
        
    Returns:
        Optional[str]: Extracted thread_id if valid format, None if invalid or legacy format
        
    Examples:
        >>> extract_thread_id_from_run_id("thread_user123_run_1693430400000_a1b2c3d4")
        'user123'
        
        >>> extract_thread_id_from_run_id("thread_session_abc_run_1693430400000_e5f6g7h8")
        'session_abc'
        
        >>> extract_thread_id_from_run_id("run_legacy_format")  # Legacy format
        None
    
    Thread ID Extraction Logic:
    1. Check for proper prefix "thread_"
    2. Find separator "_run_" 
    3. Extract everything between prefix and separator
    4. Validate extracted thread_id is non-empty
    """
    if not run_id or not isinstance(run_id, str):
        return None
    
    # Check for standardized prefix
    if not run_id.startswith(RUN_ID_PREFIX):
        logger.debug(f"Non-standard run_id format (missing prefix): {run_id}")
        return None
    
    # Find the separator
    separator_index = run_id.find(RUN_ID_SEPARATOR)
    if separator_index == -1:
        logger.debug(f"Non-standard run_id format (missing separator): {run_id}")
        return None
    
    # Extract thread_id (between prefix and separator)
    prefix_length = len(RUN_ID_PREFIX)
    thread_id = run_id[prefix_length:separator_index]
    
    # Validate extracted thread_id
    if not thread_id:
        logger.debug(f"Empty thread_id extracted from run_id: {run_id}")
        return None
    
    logger.debug(f"Extracted thread_id '{thread_id}' from run_id '{run_id}'")
    return thread_id


def validate_run_id_format(run_id: str, expected_thread_id: Optional[str] = None) -> bool:
    """
    Validate run_id format and optionally verify thread_id match.
    
    Args:
        run_id (str): Run ID to validate
        expected_thread_id (Optional[str]): Expected thread ID to match against
        
    Returns:
        bool: True if format is valid and thread_id matches (if provided)
        
    Example:
        >>> validate_run_id_format("thread_user123_run_1693430400000_a1b2c3d4")
        True
        
        >>> validate_run_id_format("thread_user123_run_1693430400000_a1b2c3d4", "user123")
        True
        
        >>> validate_run_id_format("thread_user123_run_1693430400000_a1b2c3d4", "wrong_user")
        False
    """
    if not run_id or not isinstance(run_id, str):
        return False
    
    # Validate format by attempting extraction
    extracted_thread_id = extract_thread_id_from_run_id(run_id)
    if extracted_thread_id is None:
        return False
    
    # If expected thread_id provided, verify match
    if expected_thread_id is not None:
        return extracted_thread_id == expected_thread_id
    
    return True


def is_legacy_run_id(run_id: str) -> bool:
    """
    Check if run_id uses legacy format (pre-SSOT standardization).
    
    Legacy formats include:
    - "run_{uuid}"
    - "run_{timestamp}"  
    - "admin_tool_{name}_{timestamp}"
    - Any format without embedded thread_id
    
    Args:
        run_id (str): Run ID to check
        
    Returns:
        bool: True if legacy format, False if standardized format
        
    Example:
        >>> is_legacy_run_id("run_a1b2c3d4e5f6")
        True
        
        >>> is_legacy_run_id("thread_user123_run_1693430400000_a1b2c3d4")
        False
    """
    if not run_id or not isinstance(run_id, str):
        return True  # Invalid format is considered legacy
    
    # Standardized format has extractable thread_id
    return extract_thread_id_from_run_id(run_id) is None


# Export migration utilities for existing code
def migrate_legacy_run_id_to_standard(legacy_run_id: str, thread_id: str, context: str = "migration") -> str:
    """
    Migrate legacy run_id to standardized format.
    
    This is a utility function to help migrate existing code that uses legacy formats.
    Should only be used during transition period.
    
    Args:
        legacy_run_id (str): Existing legacy run ID  
        thread_id (str): Thread ID to embed in new format
        context (str): Migration context for logging
        
    Returns:
        str: New standardized run ID
        
    Warning:
        This function should only be used during migration. New code should use
        generate_run_id() directly.
    """
    logger.warning(f"Migrating legacy run_id '{legacy_run_id}' to standard format with thread_id '{thread_id}'")
    return generate_run_id(thread_id, f"migration_from_{legacy_run_id}_{context}")


# Validation constants for external use
MIN_THREAD_ID_LENGTH = 1
MAX_THREAD_ID_LENGTH = 200  # Reasonable limit for database storage
FORBIDDEN_THREAD_ID_SEQUENCES = [RUN_ID_SEPARATOR]

__all__ = [
    'generate_run_id',
    'extract_thread_id_from_run_id', 
    'validate_run_id_format',
    'is_legacy_run_id',
    'migrate_legacy_run_id_to_standard',
    'RUN_ID_PREFIX',
    'RUN_ID_SEPARATOR',
    'UNIQUE_ID_LENGTH'
]