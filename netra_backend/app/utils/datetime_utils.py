"""
Datetime utilities for timezone conversions and DST handling.

Provides centralized datetime operations for the application,
including timezone conversions, UTC handling, and DST resolution.
"""

import pytz
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatetimeUtils:
    """Utility class for datetime operations and timezone handling."""
    
    def __init__(self):
        """Initialize datetime utilities."""
        self.utc_timezone = timezone.utc
    
    def utc_to_local(self, utc_time: datetime, timezone_name: str = "America/New_York") -> datetime:
        """Convert UTC time to local time.
        
        Args:
            utc_time: UTC datetime to convert
            timezone_name: Target timezone name (default: America/New_York)
            
        Returns:
            Local datetime in the specified timezone
        """
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        try:
            target_tz = ZoneInfo(timezone_name)
            return utc_time.astimezone(target_tz)
        except Exception as e:
            logger.error(f"Failed to convert UTC to local time: {e}")
            # Fallback to UTC if conversion fails
            return utc_time
    
    def local_to_utc(self, local_time: datetime) -> datetime:
        """Convert local time to UTC.
        
        Args:
            local_time: Local datetime to convert
            
        Returns:
            UTC datetime
        """
        if local_time.tzinfo is None:
            logger.warning("Local time has no timezone info, assuming UTC")
            return local_time.replace(tzinfo=timezone.utc)
        
        return local_time.astimezone(timezone.utc)
    
    def convert_timezone(self, dt: datetime, target_timezone: str) -> datetime:
        """Convert datetime to a different timezone.
        
        Args:
            dt: Source datetime
            target_timezone: Target timezone name
            
        Returns:
            Datetime in target timezone
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        try:
            target_tz = ZoneInfo(target_timezone)
            return dt.astimezone(target_tz)
        except Exception as e:
            logger.error(f"Failed to convert timezone to {target_timezone}: {e}")
            return dt
    
    def resolve_ambiguous_time(self, dt: datetime, timezone_name: str, is_dst: bool = False) -> Optional[datetime]:
        """Resolve ambiguous time during DST transitions.
        
        Args:
            dt: Ambiguous datetime
            timezone_name: Timezone name
            is_dst: Whether to assume DST is active
            
        Returns:
            Resolved datetime or None if resolution fails
        """
        try:
            tz = pytz.timezone(timezone_name)
            return tz.localize(dt.replace(tzinfo=None), is_dst=is_dst)
        except Exception as e:
            logger.error(f"Failed to resolve ambiguous time: {e}")
            return None
    
    def now_utc(self) -> datetime:
        """Get current UTC time.
        
        Returns:
            Current UTC datetime
        """
        return datetime.now(timezone.utc)
    
    def is_dst(self, dt: datetime, timezone_name: str) -> bool:
        """Check if datetime falls in DST period.
        
        Args:
            dt: Datetime to check
            timezone_name: Timezone name
            
        Returns:
            True if in DST period, False otherwise
        """
        try:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            target_tz = ZoneInfo(timezone_name)
            local_dt = dt.astimezone(target_tz)
            return bool(local_dt.dst())
        except Exception as e:
            logger.error(f"Failed to check DST status: {e}")
            return False