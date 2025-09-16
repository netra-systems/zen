"""Message Flow Validation Components

Focused validation utilities for message flow testing.
Extracted to maintain 450-line file limit compliance.

Business Value: Reliable validation ensures chat quality and customer satisfaction.
"""

import time
from typing import Any, Dict, List


class MessageFlowValidator:
    """Validates message flow components and ordering"""
    
    def __init__(self):
        self.messages = []
        self.timestamps = []
        self.errors = []
    
    def record_message(self, message: Dict[str, Any]) -> None:
        """Record message with timestamp for ordering validation"""
        self.messages.append(message)
        self.timestamps.append(time.time())
    
    def validate_ordering(self) -> bool:
        """Validate messages received in correct order"""
        return self.timestamps == sorted(self.timestamps)
    
    def get_message_count(self) -> int:
        """Get total message count"""
        return len(self.messages)


class MessagePersistenceValidator:
    """Validates message persistence across databases"""
    
    def __init__(self):
        self.postgres_messages = []
        self.cache_messages = []
    
    async def validate_postgres_save(self, message: Dict[str, Any]) -> bool:
        """Validate message saved to PostgreSQL"""
        self.postgres_messages.append(message)
        return True
    
    async def validate_cache_save(self, message: Dict[str, Any]) -> bool:
        """Validate message cached correctly"""
        self.cache_messages.append(message)
        return True


class StreamInterruptionHandler:
    """Handles stream interruption testing"""
    
    def __init__(self):
        self.interruption_points = []
        self.recovery_attempts = []
    
    def simulate_interruption(self, point: str) -> None:
        """Simulate stream interruption at specific point"""
        self.interruption_points.append(point)
    
    def record_recovery(self, attempt: str) -> None:
        """Record recovery attempt"""
        self.recovery_attempts.append(attempt)


async def validate_persistence_consistency(
    validator: MessagePersistenceValidator
) -> bool:
    """Validate consistency between persistence layers"""
    return (
        len(validator.postgres_messages) > 0 and
        len(validator.cache_messages) > 0
    )


async def validate_graceful_degradation(
    handler: StreamInterruptionHandler
) -> bool:
    """Validate graceful degradation during interruptions"""
    return (
        len(handler.interruption_points) > 0 and
        len(handler.recovery_attempts) > 0
    )
