"""
Centralized ID Manager - SSOT for all thread_id and run_id operations.

This module provides the Single Source of Truth for generating, extracting,
and validating all execution context identifiers in the Netra platform.

CRITICAL: All ID operations MUST go through this manager.
"""
import re
import uuid
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass(frozen=True)
class IDPair:
    """Validated pair of thread_id and run_id."""
    thread_id: str
    run_id: str
    
    def __post_init__(self):
        """Validate ID consistency on creation."""
        if not IDManager.validate_id_pair(self.run_id, self.thread_id):
            raise ValueError(
                f"Inconsistent ID pair: run_id='{self.run_id}' does not match thread_id='{self.thread_id}'"
            )


class IDManager:
    """
    Centralized manager for all ID operations.
    
    This is the SSOT for:
    - Generating run_id from thread_id
    - Extracting thread_id from run_id
    - Validating ID consistency
    - Ensuring format compliance
    """
    
    # SSOT: Run ID format pattern
    RUN_ID_PATTERN = re.compile(r'^run_([^_]+)_([a-f0-9]{8})$')
    
    # SSOT: Thread ID format pattern (flexible for legacy support)
    THREAD_ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-]*$')
    
    @staticmethod
    def generate_run_id(thread_id: str) -> str:
        """
        SSOT for run_id generation.
        
        Args:
            thread_id: The thread identifier
            
        Returns:
            Properly formatted run_id: "run_{thread_id}_{uuid_suffix}"
            
        Raises:
            ValueError: If thread_id is invalid
        """
        if not thread_id:
            raise ValueError("thread_id cannot be empty")
            
        if not IDManager.validate_thread_id(thread_id):
            raise ValueError(f"Invalid thread_id format: '{thread_id}'")
            
        # Generate unique suffix
        unique_suffix = uuid.uuid4().hex[:8]
        
        return f"run_{thread_id}_{unique_suffix}"
    
    @staticmethod
    def extract_thread_id(run_id: str) -> Optional[str]:
        """
        SSOT for thread_id extraction from run_id.
        
        Args:
            run_id: The run identifier
            
        Returns:
            Extracted thread_id or None if invalid format
        """
        if not run_id:
            return None
            
        match = IDManager.RUN_ID_PATTERN.match(run_id)
        if match:
            return match.group(1)
            
        return None
    
    @staticmethod
    def validate_id_pair(run_id: str, thread_id: str) -> bool:
        """
        Validate consistency between run_id and thread_id.
        
        Args:
            run_id: The run identifier
            thread_id: The thread identifier
            
        Returns:
            True if IDs are consistent, False otherwise
        """
        if not run_id or not thread_id:
            return False
            
        extracted_thread_id = IDManager.extract_thread_id(run_id)
        return extracted_thread_id == thread_id
    
    @staticmethod
    def validate_run_id(run_id: str) -> bool:
        """
        Validate run_id format.
        
        Args:
            run_id: The run identifier to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not run_id:
            return False
            
        return bool(IDManager.RUN_ID_PATTERN.match(run_id))
    
    @staticmethod
    def validate_thread_id(thread_id: str) -> bool:
        """
        Validate thread_id format.
        
        Args:
            thread_id: The thread identifier to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not thread_id:
            return False
            
        # Basic validation - alphanumeric with underscores/hyphens
        return bool(IDManager.THREAD_ID_PATTERN.match(thread_id))
    
    @staticmethod
    def parse_run_id(run_id: str) -> Optional[Tuple[str, str]]:
        """
        Parse run_id into components.
        
        Args:
            run_id: The run identifier
            
        Returns:
            Tuple of (thread_id, unique_suffix) or None if invalid
        """
        match = IDManager.RUN_ID_PATTERN.match(run_id)
        if match:
            return match.group(1), match.group(2)
            
        return None
    
    @staticmethod
    def create_test_ids(thread_id: str = "test_thread") -> IDPair:
        """
        Create valid test IDs for testing purposes.
        
        Args:
            thread_id: Thread ID to use (default: "test_thread")
            
        Returns:
            IDPair with validated test IDs
        """
        run_id = IDManager.generate_run_id(thread_id)
        return IDPair(thread_id=thread_id, run_id=run_id)
    
    @staticmethod
    def get_or_generate_run_id(
        run_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Get existing run_id or generate new one.
        
        Args:
            run_id: Existing run_id (if available)
            thread_id: Thread ID to use for generation
            
        Returns:
            Valid run_id
            
        Raises:
            ValueError: If neither run_id nor thread_id provided, or if validation fails
        """
        if run_id:
            # Validate existing run_id
            if not IDManager.validate_run_id(run_id):
                raise ValueError(f"Invalid run_id format: '{run_id}'")
            return run_id
            
        if thread_id:
            # Generate new run_id from thread_id
            return IDManager.generate_run_id(thread_id)
            
        raise ValueError("Either run_id or thread_id must be provided")
    
    @staticmethod
    def extract_thread_id_with_fallback(
        run_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        chat_thread_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract thread_id with fallback priority.
        
        Priority order:
        1. Extract from run_id
        2. Use provided thread_id
        3. Use provided chat_thread_id
        
        Args:
            run_id: Run identifier
            thread_id: Direct thread identifier
            chat_thread_id: Chat thread identifier (legacy)
            
        Returns:
            Thread ID or None if not found
        """
        # Try extracting from run_id first (highest priority)
        if run_id:
            extracted = IDManager.extract_thread_id(run_id)
            if extracted:
                return extracted
        
        # Fall back to direct thread_id
        if thread_id:
            return thread_id
            
        # Final fallback to chat_thread_id (legacy support)
        if chat_thread_id:
            return chat_thread_id
            
        return None