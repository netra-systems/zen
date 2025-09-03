"""
Unified ID Manager - Single Source of Truth for ALL ID generation in Netra platform.

CRITICAL MISSION: This module consolidates competing ID generation implementations
to fix SSOT violation causing 40% WebSocket routing failures.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Stability & WebSocket Reliability
- Value Impact: Fixes production WebSocket failures by providing consistent ID parsing
- Strategic Impact: Eliminates silent failures, ensures users receive real-time AI responses

SSOT Consolidation:
This module replaces and unifies:
- IDManager (legacy): "run_{thread_id}_{uuid}" format
- run_id_generator (newer): "thread_{thread_id}_run_{timestamp}_{uuid}" format

The canonical format is: "thread_{thread_id}_run_{timestamp}_{8_hex_uuid}"
All legacy formats are supported for backward compatibility.

Format Evolution Documentation:
1. Legacy IDManager: run_{thread_id}_{uuid} (circa 2024)
2. run_id_generator: thread_{thread_id}_run_{timestamp}_{uuid} (current SSOT)
3. UnifiedIDManager: Canonical format with full legacy support (this implementation)

CRITICAL: WebSocket routing depends on thread ID extraction working across ALL formats.
"""

import re
import time
import uuid
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class IDFormat(Enum):
    """ID format versions for tracking and migration."""
    LEGACY_IDMANAGER = "legacy_idmanager"        # run_{thread_id}_{uuid}
    CANONICAL = "canonical"                       # thread_{thread_id}_run_{timestamp}_{uuid}
    UNKNOWN = "unknown"                          # Invalid or unrecognized format


@dataclass(frozen=True)
class ParsedRunID:
    """Complete parsed run ID information."""
    thread_id: str
    timestamp: Optional[int]
    uuid_suffix: str
    format_version: IDFormat
    original_run_id: str
    
    def is_legacy(self) -> bool:
        """Check if this ID uses a legacy format."""
        return self.format_version == IDFormat.LEGACY_IDMANAGER
    
    def to_canonical_format(self) -> str:
        """Convert to canonical format, preserving thread_id."""
        return UnifiedIDManager.generate_run_id(self.thread_id)


class UnifiedIDManager:
    """
    Single Source of Truth for all ID generation in Netra platform.
    
    This class consolidates all ID generation logic to eliminate SSOT violations
    and provide consistent behavior across the entire platform.
    
    Supported Formats (Backward Compatible):
    1. Canonical: "thread_{thread_id}_run_{timestamp}_{8_hex_uuid}" 
    2. Legacy IDManager: "run_{thread_id}_{uuid}"
    
    Key Features:
    - Thread ID extraction works across ALL formats 
    - Prevents double prefixing (thread_thread_xyz)
    - Comprehensive validation and error handling
    - Migration utilities for legacy systems
    - Performance optimized with compiled regex patterns
    """
    
    # SSOT: Format constants
    THREAD_PREFIX = "thread_"
    RUN_SEPARATOR = "_run_"
    UUID_LENGTH = 8
    
    # SSOT: Compiled regex patterns for performance
    CANONICAL_PATTERN = re.compile(
        r'^thread_(.*?)_run_(\d+)_([a-f0-9A-F]{8})$'
    )
    LEGACY_IDMANAGER_PATTERN = re.compile(
        r'^run_(.+)_([a-f0-9A-F]{8})$'
    )
    THREAD_ID_VALIDATION_PATTERN = re.compile(
        r'^[a-zA-Z0-9][a-zA-Z0-9_\-]*$'
    )
    
    @staticmethod
    def generate_run_id(thread_id: str) -> str:
        """
        Generate canonical run ID format.
        
        Format: thread_{thread_id}_run_{timestamp}_{8_hex_uuid}
        
        CRITICAL: This is the SINGLE SOURCE OF TRUTH for new run ID generation.
        All new code MUST use this method for consistency.
        
        Args:
            thread_id: The thread identifier (will be normalized)
            
        Returns:
            Canonical format run ID
            
        Raises:
            ValueError: If thread_id is invalid or empty
            
        Example:
            >>> UnifiedIDManager.generate_run_id("user_session_123")
            'thread_user_session_123_run_1693430400000_a1b2c3d4'
            
            >>> UnifiedIDManager.generate_run_id("thread_already_prefixed")  
            'thread_already_prefixed_run_1693430400123_e5f6g7h8'
        """
        if not thread_id:
            raise ValueError("thread_id cannot be empty or None")
        
        if not isinstance(thread_id, str):
            raise ValueError(f"thread_id must be string, got {type(thread_id)}")
        
        # Check for forbidden sequences before normalization
        if UnifiedIDManager.RUN_SEPARATOR in thread_id:
            raise ValueError(f"thread_id cannot contain reserved sequence '{UnifiedIDManager.RUN_SEPARATOR}'")
        
        # Normalize thread_id (prevent double prefixing)
        normalized_thread_id = UnifiedIDManager.normalize_thread_id(thread_id)
        
        # Check if empty after prefix removal
        if not normalized_thread_id:
            raise ValueError("thread_id cannot be empty after removing prefix")
        
        # Validate normalized thread_id format
        if not UnifiedIDManager.validate_thread_id(normalized_thread_id):
            raise ValueError(f"Invalid thread_id format after normalization: '{normalized_thread_id}'")
        
        # Generate timestamp (milliseconds for ordering)
        timestamp = int(time.time() * 1000)
        
        # Generate 8-character UUID suffix
        uuid_suffix = uuid.uuid4().hex[:UnifiedIDManager.UUID_LENGTH]
        
        # Build canonical format
        run_id = f"{UnifiedIDManager.THREAD_PREFIX}{normalized_thread_id}{UnifiedIDManager.RUN_SEPARATOR}{timestamp}_{uuid_suffix}"
        
        logger.debug(f"Generated canonical run_id: {run_id} from thread_id: {thread_id}")
        return run_id
    
    @staticmethod
    def generate_thread_id() -> str:
        """
        Generate a new thread ID (no double prefixing).
        
        Returns thread_id in format suitable for use with generate_run_id().
        Does NOT include "thread_" prefix to prevent double prefixing.
        
        Returns:
            Thread ID without prefix: "session_{timestamp}_{uuid}"
            
        Example:
            >>> UnifiedIDManager.generate_thread_id()
            'session_1693430400000_a1b2c3d4'
        """
        timestamp = int(time.time() * 1000)
        uuid_suffix = uuid.uuid4().hex[:UnifiedIDManager.UUID_LENGTH]
        
        thread_id = f"session_{timestamp}_{uuid_suffix}"
        logger.debug(f"Generated thread_id: {thread_id}")
        return thread_id
    
    @staticmethod
    def parse_run_id(run_id: str) -> Optional[ParsedRunID]:
        """
        Parse any run ID format (backward compatible).
        
        Handles ALL supported formats:
        - Canonical: "thread_{thread_id}_run_{timestamp}_{uuid}"
        - Legacy IDManager: "run_{thread_id}_{uuid}"
        
        Args:
            run_id: Run ID in any supported format
            
        Returns:
            ParsedRunID with extracted components, or None if invalid
            
        Example:
            >>> mgr = UnifiedIDManager()
            >>> parsed = mgr.parse_run_id("thread_user123_run_1693430400000_a1b2c3d4")
            >>> parsed.thread_id
            'user123'
            >>> parsed.format_version
            <IDFormat.CANONICAL: 'canonical'>
            
            >>> parsed = mgr.parse_run_id("run_user123_a1b2c3d4")
            >>> parsed.thread_id
            'user123'
            >>> parsed.format_version
            <IDFormat.LEGACY_IDMANAGER: 'legacy_idmanager'>
        """
        if not run_id or not isinstance(run_id, str):
            return None
        
        # Try canonical format first (most common)
        canonical_match = UnifiedIDManager.CANONICAL_PATTERN.match(run_id)
        if canonical_match:
            thread_id, timestamp_str, uuid_suffix = canonical_match.groups()
            return ParsedRunID(
                thread_id=thread_id,
                timestamp=int(timestamp_str),
                uuid_suffix=uuid_suffix,
                format_version=IDFormat.CANONICAL,
                original_run_id=run_id
            )
        
        # Try legacy IDManager format using flexible parsing
        if run_id.startswith('run_') and len(run_id) > 13:  # "run_" + at least 1 char + "_" + 8 char UUID
            parts = run_id.split('_')
            if len(parts) >= 3:
                # Last part should be 8-character hex UUID
                potential_uuid = parts[-1]
                if len(potential_uuid) == 8 and re.match(r'^[a-f0-9A-F]+$', potential_uuid):
                    # Everything between "run_" and the UUID is the thread_id
                    # Handle consecutive underscores after "run_" prefix
                    thread_parts = parts[1:-1]  # All parts between run_ and uuid
                    
                    # Remove leading empty strings (caused by consecutive underscores after run_)
                    while thread_parts and thread_parts[0] == "":
                        thread_parts.pop(0)
                    
                    # Join remaining parts, preserving internal consecutive underscores
                    thread_id = '_'.join(thread_parts)
                    
                    # Allow empty thread_id (edge case handling)
                    logger.debug(f"Parsed legacy IDManager format run_id: {run_id}")
                    return ParsedRunID(
                        thread_id=thread_id,
                        timestamp=None,  # Legacy format doesn't have timestamp
                        uuid_suffix=potential_uuid,
                        format_version=IDFormat.LEGACY_IDMANAGER,
                        original_run_id=run_id
                    )
        
        # Unknown format
        logger.warning(f"Unknown run_id format: {run_id}")
        return None
    
    @staticmethod
    def extract_thread_id(run_id: str) -> Optional[str]:
        """
        Extract thread ID from any run ID format.
        
        CRITICAL: This method MUST work with ALL legacy formats for WebSocket routing.
        Used by WebSocket bridge to route events to correct threads.
        
        Args:
            run_id: Run ID in any supported format
            
        Returns:
            Extracted thread ID, or None if invalid format
            
        Example:
            >>> UnifiedIDManager.extract_thread_id("thread_user123_run_1693430400000_a1b2c3d4")
            'user123'
            
            >>> UnifiedIDManager.extract_thread_id("run_legacy_user123_a1b2c3d4")  
            'legacy_user123'
        """
        parsed = UnifiedIDManager.parse_run_id(run_id)
        if parsed:
            logger.debug(f"Extracted thread_id '{parsed.thread_id}' from run_id '{run_id}' (format: {parsed.format_version.value})")
            return parsed.thread_id
        
        logger.warning(f"Could not extract thread_id from run_id: {run_id}")
        return None
    
    @staticmethod
    def validate_run_id(run_id: str) -> bool:
        """
        Validate run ID format (any supported format).
        
        Args:
            run_id: Run ID to validate
            
        Returns:
            True if valid format, False otherwise
            
        Example:
            >>> UnifiedIDManager.validate_run_id("thread_user123_run_1693430400000_a1b2c3d4")
            True
            
            >>> UnifiedIDManager.validate_run_id("run_user123_a1b2c3d4")
            True
            
            >>> UnifiedIDManager.validate_run_id("invalid_format")
            False
        """
        return UnifiedIDManager.parse_run_id(run_id) is not None
    
    @staticmethod
    def validate_thread_id(thread_id: str) -> bool:
        """
        Validate thread ID format.
        
        Thread ID requirements:
        - Must be non-empty string
        - Must start with alphanumeric character  
        - Can contain alphanumeric, underscore, hyphen
        - Cannot contain reserved sequences
        
        Args:
            thread_id: Thread ID to validate
            
        Returns:
            True if valid format, False otherwise
            
        Example:
            >>> UnifiedIDManager.validate_thread_id("user123")
            True
            
            >>> UnifiedIDManager.validate_thread_id("user_session_abc")
            True
            
            >>> UnifiedIDManager.validate_thread_id("_invalid")
            False
        """
        if not thread_id or not isinstance(thread_id, str):
            return False
        
        # Check basic format requirements
        if not UnifiedIDManager.THREAD_ID_VALIDATION_PATTERN.match(thread_id):
            return False
        
        # Check for forbidden sequences
        if UnifiedIDManager.RUN_SEPARATOR in thread_id:
            return False
        
        return True
    
    @staticmethod
    def normalize_thread_id(thread_id: str) -> str:
        """
        Normalize thread ID by removing duplicate prefixes.
        
        Handles cases where thread_id already has "thread_" prefix to prevent
        double prefixing in final run_id.
        
        Args:
            thread_id: Thread ID to normalize
            
        Returns:
            Normalized thread ID without "thread_" prefix
            
        Example:
            >>> UnifiedIDManager.normalize_thread_id("thread_user123")
            'user123'
            
            >>> UnifiedIDManager.normalize_thread_id("user123")
            'user123'
            
            >>> UnifiedIDManager.normalize_thread_id("thread_thread_user123")  
            'user123'
        """
        if not thread_id:
            return thread_id
        
        normalized = thread_id
        original = thread_id
        
        # Remove "thread_" prefixes iteratively (handles multiple levels)
        while normalized.startswith(UnifiedIDManager.THREAD_PREFIX):
            normalized = normalized[len(UnifiedIDManager.THREAD_PREFIX):]
        
        if normalized != original:
            logger.debug(f"Normalized thread_id '{original}' -> '{normalized}'")
        
        return normalized
    
    @staticmethod
    def validate_id_pair(run_id: str, thread_id: str) -> bool:
        """
        Validate consistency between run_id and thread_id.
        
        Args:
            run_id: Run ID to check
            thread_id: Expected thread ID
            
        Returns:
            True if IDs are consistent, False otherwise
            
        Example:
            >>> UnifiedIDManager.validate_id_pair(
            ...     "thread_user123_run_1693430400000_a1b2c3d4", 
            ...     "user123"
            ... )
            True
        """
        if not run_id or not thread_id:
            return False
        
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        if not extracted_thread_id:
            return False
        
        # Normalize both for comparison
        normalized_extracted = UnifiedIDManager.normalize_thread_id(extracted_thread_id)
        normalized_expected = UnifiedIDManager.normalize_thread_id(thread_id)
        
        return normalized_extracted == normalized_expected
    
    @staticmethod
    def get_format_info(run_id: str) -> Dict[str, Any]:
        """
        Get detailed format information about a run_id.
        
        Useful for debugging, migration, and monitoring format usage.
        
        Args:
            run_id: Run ID to analyze
            
        Returns:
            Dict with format details, or empty dict if invalid
            
        Example:
            >>> UnifiedIDManager.get_format_info("thread_user123_run_1693430400000_a1b2c3d4")
            {
                'format_version': 'canonical',
                'thread_id': 'user123',
                'has_timestamp': True,
                'timestamp': 1693430400000,
                'uuid_suffix': 'a1b2c3d4',
                'is_legacy': False
            }
        """
        parsed = UnifiedIDManager.parse_run_id(run_id)
        if not parsed:
            return {}
        
        return {
            'format_version': parsed.format_version.value,
            'thread_id': parsed.thread_id,
            'has_timestamp': parsed.timestamp is not None,
            'timestamp': parsed.timestamp,
            'uuid_suffix': parsed.uuid_suffix,
            'is_legacy': parsed.is_legacy(),
            'original_run_id': parsed.original_run_id
        }
    
    @staticmethod
    def migrate_to_canonical(run_id: str) -> Optional[str]:
        """
        Migrate any run_id to canonical format.
        
        Preserves the original thread_id while updating to canonical format.
        Useful for gradual migration of legacy systems.
        
        Args:
            run_id: Run ID in any supported format
            
        Returns:
            New run_id in canonical format, or None if input invalid
            
        Example:
            >>> UnifiedIDManager.migrate_to_canonical("run_user123_a1b2c3d4")
            'thread_user123_run_1693430401000_b2c3d4e5'
        """
        parsed = UnifiedIDManager.parse_run_id(run_id)
        if not parsed:
            return None
        
        if parsed.format_version == IDFormat.CANONICAL:
            return parsed.original_run_id  # Already canonical
        
        # Generate new canonical ID with same thread_id
        new_run_id = UnifiedIDManager.generate_run_id(parsed.thread_id)
        logger.info(f"Migrated run_id '{run_id}' -> '{new_run_id}' (from {parsed.format_version.value})")
        
        return new_run_id
    
    @staticmethod
    def create_test_ids(thread_id: str = "test_session") -> Tuple[str, str]:
        """
        Create valid test IDs for testing purposes.
        
        Args:
            thread_id: Base thread ID for tests
            
        Returns:
            Tuple of (thread_id, run_id) 
            
        Example:
            >>> thread_id, run_id = UnifiedIDManager.create_test_ids("test_user")
            >>> UnifiedIDManager.validate_id_pair(run_id, thread_id)
            True
        """
        normalized_thread_id = UnifiedIDManager.normalize_thread_id(thread_id)
        run_id = UnifiedIDManager.generate_run_id(normalized_thread_id)
        
        return normalized_thread_id, run_id
    
    @staticmethod
    def extract_thread_id_with_fallback(
        run_id: Optional[str] = None,
        thread_id: Optional[str] = None, 
        chat_thread_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract thread_id with multiple fallback sources.
        
        Priority order:
        1. Extract from run_id (highest priority)
        2. Use provided thread_id
        3. Use provided chat_thread_id (legacy support)
        
        Args:
            run_id: Run identifier for extraction
            thread_id: Direct thread identifier
            chat_thread_id: Legacy chat thread identifier
            
        Returns:
            Thread ID or None if not found
            
        Example:
            >>> UnifiedIDManager.extract_thread_id_with_fallback(
            ...     run_id="thread_user123_run_1693430400000_a1b2c3d4"
            ... )
            'user123'
        """
        # Priority 1: Extract from run_id
        if run_id:
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            if extracted:
                return UnifiedIDManager.normalize_thread_id(extracted)
        
        # Priority 2: Direct thread_id
        if thread_id:
            return UnifiedIDManager.normalize_thread_id(thread_id)
        
        # Priority 3: Legacy chat_thread_id
        if chat_thread_id:
            return UnifiedIDManager.normalize_thread_id(chat_thread_id)
        
        return None


# Backward compatibility aliases for migration
# These will be deprecated in future versions

def generate_run_id(thread_id: str, context: str = "") -> str:
    """Deprecated: Use UnifiedIDManager.generate_run_id() instead."""
    logger.warning("generate_run_id() is deprecated, use UnifiedIDManager.generate_run_id()")
    return UnifiedIDManager.generate_run_id(thread_id)


def extract_thread_id_from_run_id(run_id: str) -> Optional[str]:
    """Deprecated: Use UnifiedIDManager.extract_thread_id() instead."""
    logger.warning("extract_thread_id_from_run_id() is deprecated, use UnifiedIDManager.extract_thread_id()")
    return UnifiedIDManager.extract_thread_id(run_id)


# Export public interface
__all__ = [
    'UnifiedIDManager',
    'ParsedRunID', 
    'IDFormat',
    # Deprecated functions for backward compatibility
    'generate_run_id',
    'extract_thread_id_from_run_id'
]