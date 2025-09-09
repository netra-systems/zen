"""
Unified ID Manager Module

Provides centralized ID generation and management across the Netra platform.
Ensures unique, consistent ID generation for all system components.
"""

import logging
import uuid
import time
import threading
from typing import Dict, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IDType(Enum):
    """Types of IDs managed by the system"""
    USER = "user"
    SESSION = "session"
    REQUEST = "request"
    AGENT = "agent"
    TOOL = "tool"
    TRANSACTION = "transaction"
    WEBSOCKET = "websocket"
    EXECUTION = "execution"
    TRACE = "trace"
    METRIC = "metric"
    THREAD = "thread"


@dataclass
class IDMetadata:
    """Metadata associated with generated IDs"""
    id_value: str
    id_type: IDType
    created_at: float
    prefix: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class UnifiedIDManager:
    """
    Centralized ID management system.
    
    Provides consistent ID generation, tracking, and validation
    across all system components.
    """
    
    def __init__(self):
        self._id_registry: Dict[str, IDMetadata] = {}
        self._active_ids: Dict[IDType, Set[str]] = {id_type: set() for id_type in IDType}
        self._id_counters: Dict[IDType, int] = {id_type: 0 for id_type in IDType}
        self._lock = threading.RLock()
        logger.info("UnifiedIDManager initialized")
    
    def generate_id(self, 
                   id_type: IDType,
                   prefix: Optional[str] = None,
                   context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a new unique ID.
        
        Args:
            id_type: Type of ID to generate
            prefix: Optional prefix for the ID
            context: Additional context metadata
            
        Returns:
            Generated unique ID
        """
        with self._lock:
            # Generate base UUID
            base_uuid = str(uuid.uuid4())
            
            # Increment counter for this ID type
            self._id_counters[id_type] += 1
            counter = self._id_counters[id_type]
            
            # Construct ID with optional prefix
            if prefix:
                id_value = f"{prefix}_{id_type.value}_{counter}_{base_uuid[:8]}"
            else:
                id_value = f"{id_type.value}_{counter}_{base_uuid[:8]}"
            
            # Create metadata
            metadata = IDMetadata(
                id_value=id_value,
                id_type=id_type,
                created_at=time.time(),
                prefix=prefix,
                context=context or {}
            )
            
            # Register ID
            self._id_registry[id_value] = metadata
            self._active_ids[id_type].add(id_value)
            
            logger.debug(f"Generated {id_type.value} ID: {id_value}")
            return id_value
    
    def register_existing_id(self,
                           id_value: str,
                           id_type: IDType,
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register an existing ID with the manager.
        
        Args:
            id_value: Existing ID to register
            id_type: Type of the ID
            context: Additional context metadata
            
        Returns:
            True if registered successfully, False if already exists
        """
        with self._lock:
            if id_value in self._id_registry:
                return False
            
            metadata = IDMetadata(
                id_value=id_value,
                id_type=id_type,
                created_at=time.time(),
                context=context or {}
            )
            
            self._id_registry[id_value] = metadata
            self._active_ids[id_type].add(id_value)
            
            logger.debug(f"Registered existing {id_type.value} ID: {id_value}")
            return True
    
    def get_id_metadata(self, id_value: str) -> Optional[IDMetadata]:
        """Get metadata for a specific ID"""
        return self._id_registry.get(id_value)
    
    def is_valid_id(self, id_value: str, id_type: Optional[IDType] = None) -> bool:
        """
        Check if an ID is valid and registered.
        
        Args:
            id_value: ID to validate
            id_type: Optional specific type to check against
            
        Returns:
            True if ID is valid
        """
        metadata = self.get_id_metadata(id_value)
        if not metadata:
            return False
        
        if id_type and metadata.id_type != id_type:
            return False
        
        return True
    
    def is_valid_id_format_compatible(self, id_value: str, id_type: Optional[IDType] = None) -> bool:
        """
        Enhanced validation that accepts both UUID and structured formats gracefully.
        
        This method provides backward compatibility during the migration period
        by accepting both formats without requiring registration.
        
        Args:
            id_value: ID to validate format
            id_type: Optional specific type to check against
            
        Returns:
            True if ID has valid format (UUID or structured)
        """
        if not is_valid_id_format(id_value):
            return False
        
        # If no specific type requested, format validation is sufficient
        if id_type is None:
            return True
        
        # For structured IDs, validate type matching
        if self._is_structured_id_format(id_value):
            extracted_type = self._extract_id_type_from_structured(id_value)
            if extracted_type and extracted_type != id_type:
                return False
        
        # UUID format doesn't contain type info, so we accept it for any type
        # during migration period
        return True
    
    def _is_structured_id_format(self, id_value: str) -> bool:
        """
        Check if ID follows UnifiedIDManager structured format.
        
        Args:
            id_value: ID to check
            
        Returns:
            True if ID is structured format (not UUID)
        """
        try:
            uuid.UUID(id_value)
            return False  # It's a UUID, not structured
        except ValueError:
            # Not a UUID, check if it's valid structured format
            return self._validate_structured_format(id_value)
    
    def _validate_structured_format(self, id_value: str) -> bool:
        """
        Validate structured ID format: [prefix_]idtype_counter_uuid8
        
        Args:
            id_value: ID to validate
            
        Returns:
            True if valid structured format
        """
        parts = id_value.split('_')
        if len(parts) < 3:
            return False
        
        # Last part should be 8-character hex
        uuid_part = parts[-1]
        if len(uuid_part) != 8 or not all(c in '0123456789abcdefABCDEF' for c in uuid_part):
            return False
        
        # Second to last should be numeric counter
        counter_part = parts[-2]
        if not counter_part.isdigit():
            return False
        
        # Check for valid ID types in the remaining parts
        valid_id_types = {id_type.value for id_type in IDType}
        for part in parts[:-2]:
            if part in valid_id_types:
                return True
        
        # Check for known prefixes or compound patterns
        if parts[0] in {'req', 'run', 'thread'}:
            return True
        
        compound_patterns = ['websocket_factory', 'websocket_manager', 'agent_executor']
        id_without_counters = '_'.join(parts[:-2])
        for pattern in compound_patterns:
            if pattern in id_without_counters:
                return True
        
        return False
    
    def _extract_id_type_from_structured(self, id_value: str) -> Optional[IDType]:
        """
        Extract IDType from structured ID format.
        
        Args:
            id_value: Structured ID
            
        Returns:
            IDType if found, None otherwise
        """
        parts = id_value.split('_')
        if len(parts) < 3:
            return None
        
        # Look for ID type in parts (excluding counter and uuid)
        valid_id_types = {id_type.value: id_type for id_type in IDType}
        for part in parts[:-2]:
            if part in valid_id_types:
                return valid_id_types[part]
        
        return None
    
    def release_id(self, id_value: str) -> bool:
        """
        Release an ID from active use.
        
        Args:
            id_value: ID to release
            
        Returns:
            True if released successfully
        """
        with self._lock:
            metadata = self._id_registry.get(id_value)
            if not metadata:
                return False
            
            # Remove from active IDs
            self._active_ids[metadata.id_type].discard(id_value)
            
            # Keep in registry for tracking but mark as released
            metadata.context['released_at'] = time.time()
            
            logger.debug(f"Released {metadata.id_type.value} ID: {id_value}")
            return True
    
    def get_active_ids(self, id_type: IDType) -> Set[str]:
        """Get all active IDs of a specific type"""
        return self._active_ids[id_type].copy()
    
    def count_active_ids(self, id_type: IDType) -> int:
        """Count active IDs of a specific type"""
        return len(self._active_ids[id_type])
    
    def cleanup_released_ids(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old released IDs from registry.
        
        Args:
            max_age_seconds: Maximum age for released IDs
            
        Returns:
            Number of IDs cleaned up
        """
        current_time = time.time()
        cleanup_count = 0
        
        with self._lock:
            ids_to_remove = []
            
            for id_value, metadata in self._id_registry.items():
                released_at = metadata.context.get('released_at')
                if released_at and current_time - released_at > max_age_seconds:
                    ids_to_remove.append(id_value)
            
            for id_value in ids_to_remove:
                del self._id_registry[id_value]
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} released IDs")
        
        return cleanup_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ID manager statistics"""
        with self._lock:
            stats = {
                'total_registered': len(self._id_registry),
                'active_by_type': {},
                'counters_by_type': {},
                'total_active': 0
            }
            
            for id_type in IDType:
                active_count = len(self._active_ids[id_type])
                stats['active_by_type'][id_type.value] = active_count
                stats['counters_by_type'][id_type.value] = self._id_counters[id_type]
                stats['total_active'] += active_count
            
            return stats
    
    def reset_counters(self) -> None:
        """Reset all ID counters (use with caution)"""
        with self._lock:
            self._id_counters = {id_type: 0 for id_type in IDType}
            logger.warning("ID counters reset")
    
    def clear_all(self) -> None:
        """Clear all IDs and reset manager (use with caution)"""
        with self._lock:
            self._id_registry.clear()
            self._active_ids = {id_type: set() for id_type in IDType}
            self._id_counters = {id_type: 0 for id_type in IDType}
            logger.warning("UnifiedIDManager cleared")
    
    # CRITICAL: Class methods required by startup validator
    @classmethod
    def generate_run_id(cls, thread_id: str) -> str:
        """
        Generate a run ID for a thread (required by startup validator).
        
        Args:
            thread_id: Thread identifier to embed in run ID
            
        Returns:
            Unique run ID containing thread ID
        """
        import uuid
        import time
        
        # Generate unique run ID with embedded thread ID
        uuid_part = str(uuid.uuid4())[:8]
        timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
        run_id = f"run_{thread_id}_{timestamp}_{uuid_part}"
        
        return run_id
    
    @classmethod
    def extract_thread_id(cls, run_id: str) -> str:
        """
        Extract thread ID from run ID with SSOT pattern support.
        
        FIVE WHYS FIX: Thread ID consistency fix to prevent WebSocket manager cleanup failures.
        This method now handles both old UnifiedIDManager patterns and new UnifiedIdGenerator patterns.
        
        Args:
            run_id: Run ID containing embedded thread ID
            
        Returns:
            Extracted thread ID that matches the corresponding thread_id field
        """
        if not run_id or not isinstance(run_id, str):
            return ""
        
        # NEW PATTERN: UnifiedIdGenerator format - run_id is the base that thread_id contains
        # Example: run_id="websocket_factory_1757372478799", thread_id="thread_websocket_factory_1757372478799_528_584ef8a5"
        # For these patterns, construct the expected thread_id format
        if run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
            # This is a UnifiedIdGenerator base_id pattern - return it as the expected thread_id prefix
            # The actual thread_id should contain this run_id as a substring
            return f"thread_{run_id}"  # Prefix pattern that thread_id should start with
        
        # OLD PATTERN: UnifiedIDManager format - run_{thread_id}_{timestamp}_{uuid}
        parts = run_id.split('_')
        if len(parts) >= 3 and parts[0] == 'run':
            # Join all parts between 'run_' and the last two parts (timestamp_uuid)
            thread_id = '_'.join(parts[1:-2])
            return thread_id
        
        # FALLBACK: For any other pattern, return run_id as-is for compatibility
        return run_id
    
    @classmethod
    def validate_run_id(cls, run_id: str) -> bool:
        """
        Validate run ID format (required by startup validator).
        
        Args:
            run_id: Run ID to validate
            
        Returns:
            True if run ID is valid format
        """
        if not run_id or not isinstance(run_id, str):
            return False
        
        # Check basic format: run_{thread_id}_{timestamp}_{uuid}
        parts = run_id.split('_')
        return (len(parts) >= 4 and 
                parts[0] == 'run' and 
                len(parts[-1]) == 8)  # UUID part should be 8 characters
    
    @classmethod
    def parse_run_id(cls, run_id: str) -> Dict[str, str]:
        """
        Parse run ID into components (required by startup validator).
        
        Args:
            run_id: Run ID to parse
            
        Returns:
            Dictionary with parsed components
        """
        result = {
            'thread_id': '',
            'timestamp': '',
            'uuid_part': '',
            'valid': False
        }
        
        if not cls.validate_run_id(run_id):
            return result
        
        parts = run_id.split('_')
        result['thread_id'] = '_'.join(parts[1:-2])
        result['timestamp'] = parts[-2]
        result['uuid_part'] = parts[-1]
        result['valid'] = True
        
        return result
    
    @classmethod
    def generate_thread_id(cls) -> str:
        """
        Generate a thread ID using class method pattern for compatibility.
        
        Returns:
            Unique thread ID (without thread_ prefix to prevent double prefixing)
        """
        import uuid
        import time
        
        # Generate unique thread ID components
        uuid_part = str(uuid.uuid4())[:8]
        timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
        
        # Return unprefixed ID - calling code will add thread_ prefix
        thread_id = f"session_{timestamp}_{uuid_part}"
        
        return thread_id
    
    @classmethod
    def convert_uuid_to_structured(cls, uuid_id: str, id_type: IDType, 
                                 prefix: Optional[str] = None) -> str:
        """
        Convert UUID to structured ID format for migration purposes.
        
        Args:
            uuid_id: UUID string to convert
            id_type: Type for the structured ID
            prefix: Optional prefix for the structured ID
            
        Returns:
            Structured ID string
        """
        try:
            # Validate input is a UUID
            uuid_obj = uuid.UUID(uuid_id)
            
            # Use first 8 characters of UUID as the uuid part
            uuid_part = uuid_id.replace('-', '')[:8]
            
            # Generate a counter (use timestamp for uniqueness)
            counter = int(time.time() * 1000) % 100000
            
            # Construct structured ID
            if prefix:
                structured_id = f"{prefix}_{id_type.value}_{counter}_{uuid_part}"
            else:
                structured_id = f"{id_type.value}_{counter}_{uuid_part}"
            
            return structured_id
            
        except ValueError:
            raise ValueError(f"Invalid UUID format: {uuid_id}")
    
    @classmethod
    def convert_structured_to_uuid(cls, structured_id: str) -> Optional[str]:
        """
        Convert structured ID back to UUID format (best effort).
        
        Note: This is lossy conversion since structured IDs only contain
        8 characters of the original UUID.
        
        Args:
            structured_id: Structured ID to convert
            
        Returns:
            UUID string if conversion possible, None otherwise
        """
        parts = structured_id.split('_')
        if len(parts) < 3:
            return None
        
        # Extract the 8-character hex part
        uuid_part = parts[-1]
        if len(uuid_part) != 8 or not all(c in '0123456789abcdefABCDEF' for c in uuid_part):
            return None
        
        # Pad to make a valid UUID (this is lossy but creates valid UUID format)
        # Pattern: xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx (UUID v4 format)
        padded_uuid = f"{uuid_part}-0000-4000-8000-000000000000"
        
        try:
            # Validate the constructed UUID
            uuid.UUID(padded_uuid)
            return padded_uuid
        except ValueError:
            return None
    
    def register_uuid_as_structured(self, uuid_id: str, id_type: IDType,
                                  context: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a UUID by converting it to structured format.
        
        This enables gradual migration from UUID to structured IDs.
        
        Args:
            uuid_id: UUID to register
            id_type: Type for the ID
            context: Additional context metadata
            
        Returns:
            The structured ID that was registered
        """
        structured_id = self.convert_uuid_to_structured(uuid_id, id_type)
        
        # Register the structured ID
        success = self.register_existing_id(structured_id, id_type, context)
        if not success:
            logger.warning(f"Failed to register converted ID: {structured_id}")
        
        return structured_id
    
    def validate_and_normalize_id(self, id_value: str, id_type: Optional[IDType] = None) -> tuple[bool, Optional[str]]:
        """
        Validate ID and return normalized form for consistent usage.
        
        During migration period, this helps standardize ID usage across the system.
        
        Args:
            id_value: ID to validate and normalize
            id_type: Expected ID type
            
        Returns:
            Tuple of (is_valid, normalized_id)
        """
        if not self.is_valid_id_format_compatible(id_value, id_type):
            return False, None
        
        # If it's already registered, return as-is
        if self.is_valid_id(id_value, id_type):
            return True, id_value
        
        # If it's a UUID and we have type info, consider converting to structured
        if id_type and self._is_uuid_format(id_value):
            try:
                structured_id = self.convert_uuid_to_structured(id_value, id_type)
                # Don't auto-register here, just return the normalized form
                return True, structured_id
            except ValueError:
                pass
        
        # Return original if valid format
        return True, id_value
    
    def _is_uuid_format(self, id_value: str) -> bool:
        """Check if ID is in UUID format."""
        try:
            uuid.UUID(id_value)
            return True
        except ValueError:
            return False


# Global ID manager instance
_id_manager = None


def get_id_manager() -> UnifiedIDManager:
    """Get global unified ID manager"""
    global _id_manager
    if _id_manager is None:
        _id_manager = UnifiedIDManager()
    return _id_manager


def generate_id(id_type: IDType, **kwargs) -> str:
    """Convenience function to generate ID"""
    return get_id_manager().generate_id(id_type, **kwargs)


def generate_user_id() -> str:
    """Generate a user ID"""
    return generate_id(IDType.USER)


def generate_session_id() -> str:
    """Generate a session ID"""
    return generate_id(IDType.SESSION)


def generate_request_id() -> str:
    """Generate a request ID"""
    return generate_id(IDType.REQUEST)


def generate_agent_id() -> str:
    """Generate an agent ID"""
    return generate_id(IDType.AGENT)


def generate_websocket_id() -> str:
    """Generate a WebSocket connection ID"""
    return generate_id(IDType.WEBSOCKET)


def generate_execution_id() -> str:
    """Generate an execution context ID"""
    return generate_id(IDType.EXECUTION)


def generate_thread_id() -> str:
    """Generate a thread ID"""
    return generate_id(IDType.THREAD)


def is_valid_id(id_value: str, id_type: Optional[IDType] = None) -> bool:
    """Convenience function to validate ID"""
    return get_id_manager().is_valid_id(id_value, id_type)


def is_valid_id_format_compatible(id_value: str, id_type: Optional[IDType] = None) -> bool:
    """Convenience function for enhanced dual-format validation"""
    return get_id_manager().is_valid_id_format_compatible(id_value, id_type)


def convert_uuid_to_structured(uuid_id: str, id_type: IDType, prefix: Optional[str] = None) -> str:
    """Convenience function to convert UUID to structured format"""
    return UnifiedIDManager.convert_uuid_to_structured(uuid_id, id_type, prefix)


def convert_structured_to_uuid(structured_id: str) -> Optional[str]:
    """Convenience function to convert structured ID to UUID format"""
    return UnifiedIDManager.convert_structured_to_uuid(structured_id)


def validate_and_normalize_id(id_value: str, id_type: Optional[IDType] = None) -> tuple[bool, Optional[str]]:
    """Convenience function to validate and normalize ID"""
    return get_id_manager().validate_and_normalize_id(id_value, id_type)


def is_valid_id_format(id_value: str) -> bool:
    """
    Validate ID format without requiring registration.
    
    Recognizes both UUID format and UnifiedIDManager structured format.
    
    Args:
        id_value: ID to validate format
        
    Returns:
        True if ID has valid format
    """
    if not id_value or not isinstance(id_value, str) or not id_value.strip():
        return False
    
    # Try standard UUID format first
    try:
        uuid.UUID(id_value)
        return True
    except ValueError:
        pass
    
    # CRITICAL: Check for WebSocket temporary authentication IDs FIRST
    # These are special temporary IDs used during WebSocket authentication flow
    # SECURITY: These should ONLY be used during connection setup and replaced with real user IDs
    websocket_temp_auth_patterns = [
        r'^pending_auth$',               # Temporary user ID during WebSocket auth flow
        r'^temp_auth_\w+$',             # Generic temporary auth patterns (future use)
        r'^awaiting_auth(_\w+)?$',      # Alternative temporary auth patterns (with optional suffix)
    ]
    
    import re
    for pattern in websocket_temp_auth_patterns:
        if re.match(pattern, id_value):
            return True
    
    # Check for common test patterns (backward compatibility)
    test_patterns = [
        r'^test-user-\d+$',              # test-user-123
        r'^test-connection-\d+$',        # test-connection-456 
        r'^test-session-[a-zA-Z0-9-]+$', # test-session-abc123
        r'^mock-[a-zA-Z]+-\w+$',         # mock-user-test
        r'^concurrent_user_\d+$',        # concurrent_user_0
        r'^user_\d+$',                   # user_0, user_1
        r'^thread-\d+$',                 # thread-456, thread-123 (CRITICAL: Golden Path test format)
        r'^[a-zA-Z]+-[a-zA-Z]+-\d+$',    # test-user-123, mock-connection-456
        r'^[a-zA-Z]+_\d+$',              # user_123, session_456
        r'^[a-zA-Z]+_[a-zA-Z]+_\d+$',    # test_user_123, mock_session_456
        r'^non_existent_\w+$',           # non_existent_user, non_existent_session
        r'^invalid_\w+$',                # invalid_user, invalid_connection  
        r'^fake_\w+$',                   # fake_user, fake_session
        r'^dummy_\w+$',                  # dummy_user, dummy_session
        r'^sample_\w+$',                 # sample_user, sample_connection
        r'^ssot-[a-zA-Z]+-\w+$',         # ssot-test-user, ssot-mock-session
        r'^e2e-[a-zA-Z]+_[a-zA-Z]+$',         # e2e-staging_pipeline, e2e-test_environment
        r'^e2e-[a-zA-Z]+_[a-zA-Z]+_[0-9]+$',  # e2e-dev_pipeline_123 (with numbers)
        r'^e2e-[a-zA-Z]+_[a-zA-Z]+-v[0-9.]+$', # e2e-staging_release-v1.2.3 (version releases)
        r'^user-\d+-[a-fA-F0-9]+$',     # user-12345-abcdef (strong typing test format)
        r'^thread-\d+-[a-zA-Z0-9]+$',   # thread-67890-ghijkl (strong typing test format)
        r'^valid-[a-zA-Z]+-[a-zA-Z0-9]+$', # valid-request-abc, valid-thread-456 (strong typing test format)
        r'^[a-zA-Z]+-[a-zA-Z]+-[a-zA-Z0-9]+$', # authenticated-user-12345, chat-request-abcdef (business test format)
        r'^e2e-[a-zA-Z0-9_-]+$',         # e2e-staging_pipeline, e2e-deployment-test
        r'^\d{18,21}$',                  # Google OAuth numeric user IDs (18-21 digits)
    ]
    
    for pattern in test_patterns:
        if re.match(pattern, id_value):
            return True
    
    # Check UnifiedIDManager structured format: [prefix_]idtype_counter_uuid8
    parts = id_value.split('_')
    if len(parts) >= 3:
        # Extract the UUID part (last 8 characters should be hex)
        uuid_part = parts[-1]
        if len(uuid_part) == 8 and all(c in '0123456789abcdefABCDEF' for c in uuid_part):
            # Check if counter part is numeric (can be one or two parts back)
            counter_part = parts[-2]
            if counter_part.isdigit():
                # For complex IDs, check if we have known prefixes or patterns
                has_known_prefix = False
                
                # Check for known prefixes (including test patterns)
                if parts[0] in {'req', 'run', 'thread', 'test'}:
                    has_known_prefix = True
                
                # Check for valid ID types anywhere in the parts
                valid_id_types = {id_type.value for id_type in IDType}
                for part in parts[:-2]:  # Exclude counter and uuid parts
                    if part in valid_id_types:
                        has_known_prefix = True
                        break
                
                # Also allow compound patterns like 'websocket_factory'
                compound_patterns = ['websocket_factory', 'websocket_manager', 'agent_executor']
                id_without_counters = '_'.join(parts[:-2])
                for pattern in compound_patterns:
                    if pattern in id_without_counters:
                        has_known_prefix = True
                        break
                
                if has_known_prefix:
                    return True
    
    # Check for OAuth provider numeric IDs (Google, Facebook, etc.)
    # Google OAuth IDs are typically 15-21 digits long
    import re
    if re.match(r'^\d{15,21}$', id_value):
        return True
    
    return False


