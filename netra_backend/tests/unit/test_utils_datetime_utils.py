"""
Unit Test for Datetime Utilities Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Data Consistency and User Experience
- Value Impact: Ensures accurate timestamp handling for agent execution logs and user interactions
- Strategic Impact: Prevents timezone-related bugs that could disrupt Golden Path user experience

CRITICAL: NO MOCKS except for external dependencies. Tests use real business logic.
Tests essential datetime functions supporting global Golden Path user base.
"""

import pytest
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.utils.datetime_utils import DatetimeUtils


class DatetimeUtilsTests(SSotBaseTestCase):
    """Test suite for DatetimeUtils following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.datetime_utils = DatetimeUtils()
        self.record_metric("test_category", "datetime_operations")
    
    def test_utc_now_returns_timezone_aware(self):
        """
        Test UTC now returns timezone-aware datetime.
        
        BVJ: Ensures consistent timestamp recording for agent execution tracking
        """
        result = self.datetime_utils.now_utc()
        
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc
        assert isinstance(result, datetime)
        self.record_metric("utc_timezone_consistency", "passed")
    
    def test_utc_to_local_conversion(self):
        """
        Test UTC to local timezone conversion.
        
        BVJ: Enables accurate time display for global Golden Path users
        """
        utc_time = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        local_time = self.datetime_utils.utc_to_local(utc_time, "America/New_York")
        
        # EDT offset is -4 hours in June
        assert local_time.hour == 8  # 12 UTC - 4 hours = 8 AM EDT
        assert local_time.tzinfo is not None
        self.record_metric("timezone_conversion_accuracy", "passed")
    
    def test_local_to_utc_conversion(self):
        """
        Test local to UTC timezone conversion.
        
        BVJ: Standardizes agent execution timestamps for consistent backend processing
        """
        # Create a timezone-aware local time
        from zoneinfo import ZoneInfo
        local_tz = ZoneInfo("America/Los_Angeles")
        local_time = datetime(2023, 6, 15, 10, 0, 0, tzinfo=local_tz)
        
        utc_time = self.datetime_utils.local_to_utc(local_time)
        
        # PDT offset is +7 hours in June
        assert utc_time.hour == 17  # 10 AM PDT + 7 hours = 17 UTC
        assert utc_time.tzinfo == timezone.utc
        self.record_metric("local_to_utc_accuracy", "passed")
    
    def test_timezone_conversion_between_zones(self):
        """
        Test conversion between different timezones.
        
        BVJ: Supports multi-timezone Golden Path user collaboration
        """
        # Start with UTC time
        utc_time = datetime(2023, 6, 15, 20, 0, 0, tzinfo=timezone.utc)
        
        # Convert to Tokyo time
        tokyo_time = self.datetime_utils.convert_timezone(utc_time, "Asia/Tokyo")
        
        # JST is UTC+9
        assert tokyo_time.hour == 5  # 20 UTC + 9 hours = 5 AM next day
        self.record_metric("cross_timezone_conversion", "passed")
    
    def test_dst_detection_accuracy(self):
        """
        Test DST detection for accurate scheduling.
        
        BVJ: Prevents agent scheduling errors during DST transitions
        """
        # Summer time (DST active)
        summer_time = datetime(2023, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        is_summer_dst = self.datetime_utils.is_dst(summer_time, "America/New_York")
        
        # Winter time (DST inactive)
        winter_time = datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        is_winter_dst = self.datetime_utils.is_dst(winter_time, "America/New_York")
        
        assert is_summer_dst == True  # July should be DST
        assert is_winter_dst == False  # January should not be DST
        self.record_metric("dst_detection_accuracy", "passed")
    
    def test_ambiguous_time_resolution(self):
        """
        Test resolution of ambiguous times during DST transitions.
        
        BVJ: Ensures accurate agent scheduling during DST boundary periods
        """
        # Create an ambiguous time during fall DST transition
        ambiguous_dt = datetime(2023, 11, 5, 1, 30, 0)  # 1:30 AM on DST end date
        
        # Resolve assuming DST is active
        dst_resolved = self.datetime_utils.resolve_ambiguous_time(
            ambiguous_dt, "America/New_York", is_dst=True
        )
        
        # Resolve assuming DST is not active  
        non_dst_resolved = self.datetime_utils.resolve_ambiguous_time(
            ambiguous_dt, "America/New_York", is_dst=False
        )
        
        assert dst_resolved is not None
        assert non_dst_resolved is not None
        assert dst_resolved != non_dst_resolved  # Should be different times
        self.record_metric("ambiguous_time_resolution", "passed")