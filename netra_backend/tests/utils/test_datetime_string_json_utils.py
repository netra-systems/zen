"""
Tests for datetime, string, and JSON utilities (Tests 86-88).
Each function  <= 8 lines, using helper functions for setup and assertions.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from netra_backend.tests.datetime_string_test_helpers import (
    DatetimeTestHelpers,
    StringTestHelpers,
)
from netra_backend.tests.json_file_crypto_test_helpers import JsonTestHelpers

# Test 86: Datetime utils timezone
class TestDatetimeUtilsTimezone:
    """test_datetime_utils_timezone - Test timezone conversions and DST handling"""
    
    @pytest.mark.asyncio
    async def test_timezone_conversions(self):
        from netra_backend.app.utils.datetime_utils import DatetimeUtils
        utils = DatetimeUtils()
        utc_time = DatetimeTestHelpers.create_utc_time()
        
        local_time = utils.utc_to_local(utc_time)
        assert local_time.tzinfo != None
        
        utc_converted = utils.local_to_utc(local_time)
        self._assert_utc_conversion(utc_converted, utc_time)
        
        self._assert_timezone_difference(utils, utc_time)
    
    @pytest.mark.asyncio
    async def test_dst_handling(self):
        from netra_backend.app.utils.datetime_utils import DatetimeUtils
        utils = DatetimeUtils()
        
        before_dst = DatetimeTestHelpers.create_dst_spring_time()
        after_dst = datetime(2025, 3, 9, 7, 30, tzinfo=timezone.utc)
        
        before_local = utils.convert_timezone(before_dst, "America/New_York")
        after_local = utils.convert_timezone(after_dst, "America/New_York")
        
        DatetimeTestHelpers.assert_timezone_offset_change(before_local, after_local)
        self._assert_ambiguous_time_resolution(utils)
    
    def _assert_utc_conversion(self, utc_converted: datetime, utc_time: datetime):
        """Assert UTC conversion is correct."""
        assert utc_converted.tzinfo == timezone.utc
        assert abs((utc_converted - utc_time).total_seconds()) < 1
    
    def _assert_timezone_difference(self, utils, utc_time: datetime):
        """Assert timezone differences are correct."""
        ny_time = utils.convert_timezone(utc_time, "America/New_York")
        la_time = utils.convert_timezone(utc_time, "America/Los_Angeles")
        time_diff = (ny_time.hour - la_time.hour) % 24
        assert time_diff in [3, 4]  # 3 or 4 hours depending on DST
    
    def _assert_ambiguous_time_resolution(self, utils):
        """Assert ambiguous time handling works."""
        ambiguous = DatetimeTestHelpers.create_dst_fall_time()
        resolved = utils.resolve_ambiguous_time(ambiguous, "America/New_York", is_dst=False)
        assert resolved != None

# Test 87: String utils sanitization
class TestStringUtilsSanitization:
    """test_string_utils_sanitization - Test string sanitization and XSS prevention"""
    
    @pytest.mark.asyncio
    async def test_xss_prevention(self):
        from netra_backend.app.utils.string_utils import StringUtils
        utils = StringUtils()
        
        malicious = StringTestHelpers.create_xss_payload()
        sanitized = utils.sanitize_html(malicious)
        StringTestHelpers.assert_xss_sanitized(malicious, sanitized)
        
        self._assert_event_handler_removal(utils)
        self._assert_sql_injection_prevention(utils)
        self._assert_path_traversal_prevention(utils)
    
    @pytest.mark.asyncio
    async def test_input_validation(self):
        from netra_backend.app.utils.string_utils import StringUtils
        utils = StringUtils()
        
        self._assert_email_validation(utils)
        self._assert_url_validation(utils)
        self._assert_alphanumeric_validation(utils)
        self._assert_length_truncation(utils)
    
    def _assert_event_handler_removal(self, utils):
        """Assert event handlers are removed."""
        malicious = StringTestHelpers.create_event_handler_payload()
        sanitized = utils.sanitize_html(malicious)
        assert 'onclick' not in sanitized
    
    def _assert_sql_injection_prevention(self, utils):
        """Assert SQL injection is prevented."""
        sql_input = StringTestHelpers.create_sql_injection_payload()
        escaped = utils.escape_sql(sql_input)
        assert "DROP TABLE" not in escaped or "\\'" in escaped
    
    def _assert_path_traversal_prevention(self, utils):
        """Assert path traversal is prevented."""
        path = "../../../etc/passwd"
        safe_path = utils.sanitize_path(path)
        assert ".." not in safe_path
    
    def _assert_email_validation(self, utils):
        """Assert email validation works."""
        assert utils.is_valid_email("test@example.com") == True
        assert utils.is_valid_email("invalid.email") == False
    
    def _assert_url_validation(self, utils):
        """Assert URL validation works."""
        assert utils.is_valid_url("https://example.com") == True
        assert utils.is_valid_url("javascript:alert(1)") == False
    
    def _assert_alphanumeric_validation(self, utils):
        """Assert alphanumeric validation works."""
        assert utils.is_alphanumeric("Test123") == True
        assert utils.is_alphanumeric("Test@123") == False
    
    def _assert_length_truncation(self, utils):
        """Assert length truncation works."""
        truncated = utils.truncate("x" * 1000, max_length=100)
        assert len(truncated) <= 100

# Test 88: JSON utils serialization
class TestJsonUtilsSerialization:
    """test_json_utils_serialization - Test custom serialization and circular reference handling"""
    
    @pytest.mark.asyncio
    async def test_custom_serialization(self):
        from netra_backend.app.core.serialization.unified_json_handler import CircularReferenceHandler
        utils = CircularReferenceHandler()
        
        data = JsonTestHelpers.create_datetime_data()
        serialized = utils.serialize(data)
        assert isinstance(serialized, str)
        
        deserialized = utils.deserialize(serialized)
        assert "timestamp" in deserialized
        
        self._assert_custom_object_serialization(utils)
    
    @pytest.mark.asyncio
    async def test_circular_reference_handling(self):
        from netra_backend.app.core.serialization.unified_json_handler import CircularReferenceHandler
        utils = CircularReferenceHandler()
        
        obj1 = JsonTestHelpers.create_circular_reference()
        serialized = utils.serialize_safe(obj1)
        self._assert_circular_reference_handled(serialized)
        
        nested = JsonTestHelpers.create_nested_data(100)
        serialized_nested = utils.serialize(nested, max_depth=10)
        assert serialized_nested != None
    
    def _assert_custom_object_serialization(self, utils):
        """Assert custom objects can be serialized."""
        class CustomObject:
            def __init__(self):
                self.value = 42
                self.name = "test"
        
        obj = CustomObject()
        serialized = utils.serialize(obj, custom_encoder=True)
        assert "value" in serialized
        assert "name" in serialized
    
    def _assert_circular_reference_handled(self, serialized: str):
        """Assert circular reference was handled."""
        assert serialized != None
        assert "[Circular Reference]" in serialized or "..." in serialized