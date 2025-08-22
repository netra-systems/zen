"""
In-memory log buffer with deduplication for silent logging.

Implements circular buffer for memory-efficient log management
with pattern-based deduplication as per dev launcher performance spec.
"""

import hashlib
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class LogLevel(Enum):
    """Log levels with priority ordering."""
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEntry:
    """Single log entry with metadata."""
    timestamp: float
    level: LogLevel
    message: str
    hash: str
    source: str
    count: int = 1


class LogBuffer:
    """
    Memory-efficient circular buffer for development logs.
    
    Features:
    - Circular buffer to prevent memory overflow
    - Message deduplication based on content hash
    - Level-based filtering and flushing
    - Error context preservation
    """
    
    def __init__(self, max_size: int = 1000, max_duplicates: int = 10):
        """
        Initialize log buffer.
        
        Args:
            max_size: Maximum buffer size (circular)
            max_duplicates: Max count for duplicate messages
        """
        self.max_size = max_size
        self.max_duplicates = max_duplicates
        self.buffer: deque[LogEntry] = deque(maxlen=max_size)
        self.message_hashes: Dict[str, int] = {}
        self.error_context: List[LogEntry] = []
        self.last_flush = time.time()
        
    def add_message(self, message: str, level: LogLevel = LogLevel.INFO, 
                   source: str = "system") -> bool:
        """
        Add message to buffer with deduplication.
        
        Args:
            message: Log message content
            level: Log severity level
            source: Message source identifier
            
        Returns:
            True if message was added, False if deduplicated
        """
        msg_hash = self._generate_hash(message)
        timestamp = time.time()
        
        # Handle duplicate detection
        if self._is_duplicate(msg_hash):
            return self._handle_duplicate(msg_hash, timestamp)
            
        # Create new entry
        entry = LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            hash=msg_hash,
            source=source
        )
        
        self._store_entry(entry, msg_hash)
        self._preserve_error_context(entry)
        
        return True
    
    def should_flush(self) -> bool:
        """
        Determine if buffer should be flushed.
        
        Returns:
            True if flush conditions are met
        """
        return (
            self._has_errors() or
            self._buffer_full() or
            self._timeout_exceeded()
        )
    
    def flush_buffer(self, force: bool = False) -> List[LogEntry]:
        """
        Flush buffer and return entries.
        
        Args:
            force: Force flush regardless of conditions
            
        Returns:
            List of log entries to output
        """
        if not force and not self.should_flush():
            return []
            
        entries = self._select_flush_entries()
        self._clear_processed_entries()
        self.last_flush = time.time()
        
        return entries
    
    def get_error_context(self, lines_before: int = 5) -> List[LogEntry]:
        """
        Get error context with surrounding messages.
        
        Args:
            lines_before: Number of context lines before error
            
        Returns:
            Context entries around errors
        """
        if not self.error_context:
            return []
            
        context = []
        buffer_list = list(self.buffer)
        
        for error_entry in self.error_context:
            error_idx = self._find_entry_index(error_entry, buffer_list)
            if error_idx >= 0:
                start_idx = max(0, error_idx - lines_before)
                context.extend(buffer_list[start_idx:error_idx + 1])
                
        return context
    
    def _generate_hash(self, message: str) -> str:
        """Generate hash for message deduplication."""
        normalized = self._normalize_message(message)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def _normalize_message(self, message: str) -> str:
        """Normalize message for deduplication."""
        # Remove timestamps and variable content
        import re
        normalized = re.sub(r'\d{2}:\d{2}:\d{2}', 'HH:MM:SS', message)
        normalized = re.sub(r'\d+ms', 'XXXms', normalized)
        normalized = re.sub(r'port \d+', 'port XXXX', normalized)
        return normalized.strip().lower()
    
    def _is_duplicate(self, msg_hash: str) -> bool:
        """Check if message is a duplicate."""
        return msg_hash in self.message_hashes
    
    def _handle_duplicate(self, msg_hash: str, timestamp: float) -> bool:
        """Handle duplicate message."""
        if self.message_hashes[msg_hash] >= self.max_duplicates:
            return False
            
        # Update existing entry count
        for entry in reversed(self.buffer):
            if entry.hash == msg_hash:
                entry.count += 1
                entry.timestamp = timestamp
                break
                
        self.message_hashes[msg_hash] += 1
        return True
    
    def _store_entry(self, entry: LogEntry, msg_hash: str) -> None:
        """Store new entry in buffer."""
        self.buffer.append(entry)
        self.message_hashes[msg_hash] = 1
        
        # Clean old hashes when buffer wraps
        if len(self.buffer) == self.max_size:
            self._clean_old_hashes()
    
    def _preserve_error_context(self, entry: LogEntry) -> None:
        """Preserve error entries for context."""
        if entry.level.value >= LogLevel.ERROR.value:
            self.error_context.append(entry)
            # Keep only recent errors
            if len(self.error_context) > 10:
                self.error_context = self.error_context[-10:]
    
    def _has_errors(self) -> bool:
        """Check if buffer contains errors."""
        return len(self.error_context) > 0
    
    def _buffer_full(self) -> bool:
        """Check if buffer is near capacity."""
        return len(self.buffer) > self.max_size * 0.8
    
    def _timeout_exceeded(self) -> bool:
        """Check if flush timeout exceeded."""
        return time.time() - self.last_flush > 30  # 30 second timeout
    
    def _select_flush_entries(self) -> List[LogEntry]:
        """Select entries for flushing based on importance."""
        entries = list(self.buffer)
        
        if self._has_errors():
            # Include error context
            return self.get_error_context()
        
        # Filter for important messages only
        important_entries = []
        for entry in entries:
            if self._is_important_message(entry):
                important_entries.append(entry)
                
        return important_entries[-50:]  # Last 50 important messages
    
    def _is_important_message(self, entry: LogEntry) -> bool:
        """Determine if message is important enough to show."""
        # Always show warnings and errors
        if entry.level.value >= LogLevel.WARNING.value:
            return True
            
        # Show startup/completion messages
        important_keywords = [
            "started", "ready", "listening", "completed",
            "failed", "success", "error", "port"
        ]
        
        message_lower = entry.message.lower()
        return any(keyword in message_lower for keyword in important_keywords)
    
    def _clear_processed_entries(self) -> None:
        """Clear processed entries from buffer."""
        # Keep error context and recent entries
        keep_entries = []
        recent_cutoff = time.time() - 300  # Keep last 5 minutes
        
        for entry in self.buffer:
            if (entry.level.value >= LogLevel.ERROR.value or 
                entry.timestamp > recent_cutoff):
                keep_entries.append(entry)
                
        self.buffer = deque(keep_entries, maxlen=self.max_size)
        self.error_context = []  # Clear since errors are flushed
    
    def _find_entry_index(self, target: LogEntry, entries: List[LogEntry]) -> int:
        """Find entry index in buffer."""
        for i, entry in enumerate(entries):
            if entry.hash == target.hash and entry.timestamp == target.timestamp:
                return i
        return -1
    
    def _clean_old_hashes(self) -> None:
        """Clean old message hashes when buffer wraps."""
        # Keep hashes for messages still in buffer
        active_hashes = {entry.hash for entry in self.buffer}
        self.message_hashes = {
            h: count for h, count in self.message_hashes.items() 
            if h in active_hashes
        }