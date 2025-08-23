"""Mock implementation of freezegun for time manipulation in tests

This provides a minimal mock implementation of freezegun to avoid external dependencies
while maintaining compatibility with existing test code.
"""

import time
from datetime import datetime, timezone
from typing import Any, Optional, Union
from unittest.mock import patch
from contextlib import contextmanager


class FrozenTime:
    """Mock frozen time context manager"""
    
    def __init__(self, frozen_time: Union[str, datetime, float]):
        if isinstance(frozen_time, str):
            # Simple ISO format parsing
            if 'T' in frozen_time:
                self.frozen_datetime = datetime.fromisoformat(frozen_time.replace('Z', '+00:00'))
            else:
                self.frozen_datetime = datetime.fromisoformat(frozen_time)
        elif isinstance(frozen_time, datetime):
            self.frozen_datetime = frozen_time
        elif isinstance(frozen_time, (int, float)):
            self.frozen_datetime = datetime.fromtimestamp(frozen_time, tz=timezone.utc)
        else:
            self.frozen_datetime = datetime.now(timezone.utc)
            
        self.frozen_timestamp = self.frozen_datetime.timestamp()
        self.patches = []
        
    def __enter__(self):
        # Mock time.time()
        self.patches.append(patch('time.time', return_value=self.frozen_timestamp))
        
        # Mock datetime.now()
        def mock_now(tz=None):
            if tz is None:
                return self.frozen_datetime.replace(tzinfo=None)
            return self.frozen_datetime.astimezone(tz)
            
        self.patches.append(patch('datetime.datetime.now', side_effect=mock_now))
        
        # Mock datetime.utcnow()
        self.patches.append(patch('datetime.datetime.utcnow', 
                                return_value=self.frozen_datetime.replace(tzinfo=None)))
        
        # Start all patches
        for p in self.patches:
            p.start()
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Stop all patches
        for p in self.patches:
            p.stop()
        self.patches.clear()
        
    def tick(self, delta=1):
        """Move time forward by delta seconds"""
        self.frozen_timestamp += delta
        self.frozen_datetime = datetime.fromtimestamp(self.frozen_timestamp, tz=timezone.utc)
        
        # Update the mock return values
        for p in self.patches:
            if hasattr(p, 'return_value'):
                if callable(p.return_value):
                    continue  # Skip side_effect patches
                p.return_value = self.frozen_timestamp


def freeze_time(time_to_freeze: Union[str, datetime, float]):
    """Mock freeze_time decorator/context manager"""
    return FrozenTime(time_to_freeze)


# Provide the same interface as the real freezegun
freeze = freeze_time