"""
Comprehensive utility tests (86-100) from top 100 missing tests.
Tests utility functions and helper modules.
"""

import pytest
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import hashlib
import time
from decimal import Decimal


# Test 86: Datetime utils timezone
@pytest.mark.asyncio
class TestDatetimeUtilsTimezone:
    """test_datetime_utils_timezone - Test timezone conversions and DST handling"""
    
    async def test_timezone_conversions(self):
        from app.utils.datetime_utils import DatetimeUtils
        
        utils = DatetimeUtils()
        
        # Test UTC to local
        utc_time = datetime.now(timezone.utc)
        local_time = utils.utc_to_local(utc_time)
        assert local_time.tzinfo is not None
        
        # Test local to UTC
        utc_converted = utils.local_to_utc(local_time)
        assert utc_converted.tzinfo == timezone.utc
        assert abs((utc_converted - utc_time).total_seconds()) < 1
        
        # Test specific timezone conversion
        ny_time = utils.convert_timezone(utc_time, "America/New_York")
        la_time = utils.convert_timezone(utc_time, "America/Los_Angeles")
        
        # NY should be 3 hours ahead of LA (excluding DST changes)
        time_diff = (ny_time.hour - la_time.hour) % 24
        assert time_diff in [3, 4]  # 3 or 4 hours depending on DST
    
    async def test_dst_handling(self):
        from app.utils.datetime_utils import DatetimeUtils
        
        utils = DatetimeUtils()
        
        # Test DST transition dates
        # Spring forward (2025-03-09 2:00 AM EST -> 3:00 AM EDT)
        before_dst = datetime(2025, 3, 9, 1, 30, tzinfo=timezone.utc)
        after_dst = datetime(2025, 3, 9, 7, 30, tzinfo=timezone.utc)
        
        before_local = utils.convert_timezone(before_dst, "America/New_York")
        after_local = utils.convert_timezone(after_dst, "America/New_York")
        
        # Check offset change
        assert before_local.strftime("%z") != after_local.strftime("%z")
        
        # Test ambiguous time handling (fall back)
        ambiguous = datetime(2025, 11, 2, 1, 30)
        resolved = utils.resolve_ambiguous_time(ambiguous, "America/New_York", is_dst=False)
        assert resolved is not None


# Test 87: String utils sanitization
@pytest.mark.asyncio
class TestStringUtilsSanitization:
    """test_string_utils_sanitization - Test string sanitization and XSS prevention"""
    
    async def test_xss_prevention(self):
        from app.utils.string_utils import StringUtils
        
        utils = StringUtils()
        
        # Test script tag removal
        malicious = '<script>alert("XSS")</script>Hello'
        sanitized = utils.sanitize_html(malicious)
        assert '<script>' not in sanitized
        assert 'Hello' in sanitized
        
        # Test event handler removal
        malicious = '<div onclick="alert(1)">Click me</div>'
        sanitized = utils.sanitize_html(malicious)
        assert 'onclick' not in sanitized
        
        # Test SQL injection prevention
        sql_input = "'; DROP TABLE users; --"
        escaped = utils.escape_sql(sql_input)
        assert "DROP TABLE" not in escaped or "\\'" in escaped
        
        # Test path traversal prevention
        path = "../../../etc/passwd"
        safe_path = utils.sanitize_path(path)
        assert ".." not in safe_path
    
    async def test_input_validation(self):
        from app.utils.string_utils import StringUtils
        
        utils = StringUtils()
        
        # Test email validation
        assert utils.is_valid_email("test@example.com") is True
        assert utils.is_valid_email("invalid.email") is False
        
        # Test URL validation
        assert utils.is_valid_url("https://example.com") is True
        assert utils.is_valid_url("javascript:alert(1)") is False
        
        # Test alphanumeric validation
        assert utils.is_alphanumeric("Test123") is True
        assert utils.is_alphanumeric("Test@123") is False
        
        # Test length limits
        truncated = utils.truncate("x" * 1000, max_length=100)
        assert len(truncated) <= 100


# Test 88: JSON utils serialization
@pytest.mark.asyncio
class TestJsonUtilsSerialization:
    """test_json_utils_serialization - Test custom serialization and circular reference handling"""
    
    async def test_custom_serialization(self):
        from app.utils.json_utils import JsonUtils
        
        utils = JsonUtils()
        
        # Test datetime serialization
        data = {
            "timestamp": datetime.now(timezone.utc),
            "date": datetime.now().date(),
            "decimal": Decimal("123.45")
        }
        
        serialized = utils.serialize(data)
        assert isinstance(serialized, str)
        
        deserialized = utils.deserialize(serialized)
        assert "timestamp" in deserialized
        
        # Test custom object serialization
        class CustomObject:
            def __init__(self):
                self.value = 42
                self.name = "test"
        
        obj = CustomObject()
        serialized = utils.serialize(obj, custom_encoder=True)
        assert "value" in serialized
        assert "name" in serialized
    
    async def test_circular_reference_handling(self):
        from app.utils.json_utils import JsonUtils
        
        utils = JsonUtils()
        
        # Create circular reference
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2
        
        # Should handle circular reference
        serialized = utils.serialize_safe(obj1)
        assert serialized is not None
        assert "[Circular Reference]" in serialized or "..." in serialized
        
        # Test max depth handling
        nested = {"level": 0}
        current = nested
        for i in range(100):
            current["child"] = {"level": i + 1}
            current = current["child"]
        
        serialized = utils.serialize(nested, max_depth=10)
        assert serialized is not None


# Test 89: File utils operations
@pytest.mark.asyncio
class TestFileUtilsOperations:
    """test_file_utils_operations - Test file operations and cleanup on error"""
    
    async def test_file_operations(self):
        from app.utils.file_utils import FileUtils
        
        utils = FileUtils()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test file creation
            file_path = os.path.join(tmpdir, "test.txt")
            await utils.write_file(file_path, "test content")
            assert os.path.exists(file_path)
            
            # Test file reading
            content = await utils.read_file(file_path)
            assert content == "test content"
            
            # Test file copy
            copy_path = os.path.join(tmpdir, "copy.txt")
            await utils.copy_file(file_path, copy_path)
            assert os.path.exists(copy_path)
            
            # Test file move
            move_path = os.path.join(tmpdir, "moved.txt")
            await utils.move_file(copy_path, move_path)
            assert os.path.exists(move_path)
            assert not os.path.exists(copy_path)
            
            # Test file deletion
            await utils.delete_file(move_path)
            assert not os.path.exists(move_path)
    
    async def test_cleanup_on_error(self):
        from app.utils.file_utils import FileUtils
        
        utils = FileUtils()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, "temp.txt")
            
            # Test cleanup on write error
            with patch('builtins.open', side_effect=IOError("Write failed")):
                with pytest.raises(IOError):
                    await utils.write_file_safe(temp_file, "content")
                
                # File should not exist after error
                assert not os.path.exists(temp_file)
            
            # Test atomic write
            target_file = os.path.join(tmpdir, "target.txt")
            await utils.write_file_atomic(target_file, "atomic content")
            
            # Verify atomic write succeeded
            content = await utils.read_file(target_file)
            assert content == "atomic content"


# Test 90: Crypto utils hashing
@pytest.mark.asyncio
class TestCryptoUtilsHashing:
    """test_crypto_utils_hashing - Test hashing algorithms and salt generation"""
    
    async def test_hashing_algorithms(self):
        from app.utils.crypto_utils import CryptoUtils
        
        utils = CryptoUtils()
        
        # Test different hash algorithms
        data = "test data"
        
        sha256_hash = utils.hash_data(data, algorithm="sha256")
        assert len(sha256_hash) == 64  # SHA256 produces 64 hex chars
        
        sha512_hash = utils.hash_data(data, algorithm="sha512")
        assert len(sha512_hash) == 128  # SHA512 produces 128 hex chars
        
        # Test consistency
        hash1 = utils.hash_data(data)
        hash2 = utils.hash_data(data)
        assert hash1 == hash2
        
        # Test different data produces different hashes
        hash3 = utils.hash_data("different data")
        assert hash1 != hash3
    
    async def test_salt_generation(self):
        from app.utils.crypto_utils import CryptoUtils
        
        utils = CryptoUtils()
        
        # Test salt generation
        salt1 = utils.generate_salt()
        salt2 = utils.generate_salt()
        
        assert salt1 != salt2  # Salts should be unique
        assert len(salt1) >= 16  # Minimum salt length
        
        # Test salted hashing
        password = "secure_password"
        hash1 = utils.hash_password(password, salt1)
        hash2 = utils.hash_password(password, salt2)
        
        assert hash1 != hash2  # Different salts produce different hashes
        
        # Test password verification
        stored_hash = utils.hash_password(password, salt1)
        assert utils.verify_password(password, stored_hash, salt1) is True
        assert utils.verify_password("wrong_password", stored_hash, salt1) is False


# Test 91: Validation utils schemas
@pytest.mark.asyncio
class TestValidationUtilsSchemas:
    """test_validation_utils_schemas - Test schema validation and error messages"""
    
    async def test_schema_validation(self):
        from app.utils.validation_utils import ValidationUtils
        
        utils = ValidationUtils()
        
        # Define test schema
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "integer", "minimum": 0},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age"]
        }
        
        # Test valid data
        valid_data = {"name": "John", "age": 30, "email": "john@example.com"}
        assert utils.validate_schema(valid_data, schema) is True
        
        # Test missing required field
        invalid_data = {"name": "John"}
        result = utils.validate_schema(invalid_data, schema)
        assert result is False or "age" in str(result)
        
        # Test invalid type
        invalid_data = {"name": "John", "age": "thirty"}
        result = utils.validate_schema(invalid_data, schema)
        assert result is False or "type" in str(result)
    
    async def test_error_messages(self):
        from app.utils.validation_utils import ValidationUtils
        
        utils = ValidationUtils()
        
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"}
            }
        }
        
        # Test error message generation
        invalid_data = {"email": "not-an-email"}
        errors = utils.get_validation_errors(invalid_data, schema)
        
        assert len(errors) > 0
        assert any("email" in str(error) for error in errors)
        assert any("format" in str(error) for error in errors)


# Test 92: Formatting utils display
@pytest.mark.asyncio
class TestFormattingUtilsDisplay:
    """test_formatting_utils_display - Test data formatting and localization"""
    
    async def test_data_formatting(self):
        from app.utils.formatting_utils import FormattingUtils
        
        utils = FormattingUtils()
        
        # Test number formatting
        assert utils.format_number(1234567.89) == "1,234,567.89"
        assert utils.format_number(1234567.89, decimals=0) == "1,234,568"
        
        # Test currency formatting
        assert utils.format_currency(1234.56, "USD") == "$1,234.56"
        assert utils.format_currency(1234.56, "EUR") == "€1,234.56"
        
        # Test percentage formatting
        assert utils.format_percentage(0.1234) == "12.34%"
        assert utils.format_percentage(0.1234, decimals=1) == "12.3%"
        
        # Test file size formatting
        assert utils.format_file_size(1024) == "1.0 KB"
        assert utils.format_file_size(1048576) == "1.0 MB"
        assert utils.format_file_size(1073741824) == "1.0 GB"
    
    async def test_localization(self):
        from app.utils.formatting_utils import FormattingUtils
        
        # Test different locales
        utils_us = FormattingUtils(locale="en_US")
        utils_de = FormattingUtils(locale="de_DE")
        
        # US format
        assert utils_us.format_number(1234.56) == "1,234.56"
        
        # German format
        assert utils_de.format_number(1234.56) == "1.234,56"
        
        # Date formatting
        date = datetime(2025, 1, 15)
        assert "January" in utils_us.format_date(date, "long")
        assert "Januar" in utils_de.format_date(date, "long")


# Test 93: Math utils calculations
@pytest.mark.asyncio
class TestMathUtilsCalculations:
    """test_math_utils_calculations - Test mathematical operations and precision handling"""
    
    async def test_mathematical_operations(self):
        from app.utils.math_utils import MathUtils
        
        utils = MathUtils()
        
        # Test basic statistics
        data = [1, 2, 3, 4, 5]
        assert utils.mean(data) == 3.0
        assert utils.median(data) == 3.0
        assert utils.std_dev(data) == pytest.approx(1.414, rel=0.01)
        
        # Test percentiles
        assert utils.percentile(data, 50) == 3.0
        assert utils.percentile(data, 25) == 2.0
        assert utils.percentile(data, 75) == 4.0
        
        # Test moving average
        moving_avg = utils.moving_average(data, window=3)
        assert moving_avg == pytest.approx([2.0, 3.0, 4.0], rel=0.01)
    
    async def test_precision_handling(self):
        from app.utils.math_utils import MathUtils
        
        utils = MathUtils()
        
        # Test decimal precision
        result = utils.divide(1, 3, precision=4)
        assert result == Decimal("0.3333")
        
        # Test rounding
        assert utils.round_half_up(2.5) == 3
        assert utils.round_half_down(2.5) == 2
        
        # Test financial rounding
        assert utils.round_financial(2.345) == Decimal("2.35")
        assert utils.round_financial(2.344) == Decimal("2.34")


# Test 94: Network utils requests
@pytest.mark.asyncio
class TestNetworkUtilsRequests:
    """test_network_utils_requests - Test network utilities and retry logic"""
    
    async def test_network_utilities(self):
        from app.utils.network_utils import NetworkUtils
        
        utils = NetworkUtils()
        
        # Test URL validation
        assert utils.is_valid_url("https://example.com") is True
        assert utils.is_valid_url("not-a-url") is False
        
        # Test IP validation
        assert utils.is_valid_ip("192.168.1.1") is True
        assert utils.is_valid_ip("256.256.256.256") is False
        assert utils.is_valid_ip("::1") is True  # IPv6
        
        # Test port checking
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect_ex.return_value = 0
            assert await utils.is_port_open("localhost", 80) is True
            
            mock_socket.return_value.connect_ex.return_value = 1
            assert await utils.is_port_open("localhost", 80) is False
    
    async def test_retry_logic(self):
        from app.utils.network_utils import NetworkUtils
        
        utils = NetworkUtils()
        
        # Test successful request
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"success": True})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await utils.http_get_with_retry("https://api.example.com")
            assert result["success"] is True
        
        # Test retry on failure
        call_count = 0
        
        async def failing_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Network error")
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"success": True})
            return mock_response
        
        with patch('aiohttp.ClientSession.get', side_effect=failing_get):
            result = await utils.http_get_with_retry(
                "https://api.example.com",
                max_retries=3
            )
            assert call_count == 3


# Test 95: Pagination utils cursors
@pytest.mark.asyncio
class TestPaginationUtilsCursors:
    """test_pagination_utils_cursors - Test cursor pagination and edge cases"""
    
    async def test_cursor_pagination(self):
        from app.utils.pagination_utils import PaginationUtils
        
        utils = PaginationUtils()
        
        # Test cursor encoding/decoding
        cursor_data = {"id": 123, "timestamp": "2025-01-01T00:00:00Z"}
        cursor = utils.encode_cursor(cursor_data)
        decoded = utils.decode_cursor(cursor)
        
        assert decoded["id"] == cursor_data["id"]
        assert decoded["timestamp"] == cursor_data["timestamp"]
        
        # Test pagination metadata
        total_items = 100
        page_size = 10
        current_page = 3
        
        metadata = utils.get_pagination_metadata(
            total_items, page_size, current_page
        )
        
        assert metadata["total_pages"] == 10
        assert metadata["has_next"] is True
        assert metadata["has_previous"] is True
        assert metadata["start_index"] == 21
        assert metadata["end_index"] == 30
    
    async def test_edge_cases(self):
        from app.utils.pagination_utils import PaginationUtils
        
        utils = PaginationUtils()
        
        # Test empty result set
        metadata = utils.get_pagination_metadata(0, 10, 1)
        assert metadata["total_pages"] == 0
        assert metadata["has_next"] is False
        
        # Test last page
        metadata = utils.get_pagination_metadata(95, 10, 10)
        assert metadata["has_next"] is False
        assert metadata["end_index"] == 95
        
        # Test invalid cursor
        invalid_cursor = "invalid_base64"
        decoded = utils.decode_cursor(invalid_cursor)
        assert decoded is None or decoded == {}


# Test 96: Rate limiter throttling
@pytest.mark.asyncio
class TestRateLimiterThrottling:
    """test_rate_limiter_throttling - Test rate limiting and bucket algorithms"""
    
    async def test_rate_limiting(self):
        from app.utils.rate_limiter import RateLimiter
        
        # Test token bucket algorithm
        limiter = RateLimiter(rate=5, per=1.0)  # 5 requests per second
        
        # Should allow initial burst
        for _ in range(5):
            assert await limiter.allow_request() is True
        
        # Should block 6th request
        assert await limiter.allow_request() is False
        
        # Wait for token refill
        await asyncio.sleep(0.3)
        assert await limiter.allow_request() is True
    
    async def test_bucket_algorithms(self):
        from app.utils.rate_limiter import RateLimiter
        
        # Test sliding window
        limiter = RateLimiter(
            rate=10,
            per=60.0,
            algorithm="sliding_window"
        )
        
        # Make 10 requests
        for _ in range(10):
            assert await limiter.allow_request() is True
        
        # 11th should fail
        assert await limiter.allow_request() is False
        
        # Test leaky bucket
        limiter = RateLimiter(
            rate=10,
            per=60.0,
            algorithm="leaky_bucket",
            burst_size=5
        )
        
        # Should allow burst
        for _ in range(5):
            assert await limiter.allow_request() is True


# Test 97: Retry utils backoff
@pytest.mark.asyncio
class TestRetryUtilsBackoff:
    """test_retry_utils_backoff - Test retry strategies and exponential backoff"""
    
    async def test_exponential_backoff(self):
        from app.utils.retry_utils import RetryUtils
        
        utils = RetryUtils()
        
        # Test backoff calculation
        assert utils.get_backoff_time(1) == 1.0  # First retry: 1 second
        assert utils.get_backoff_time(2) == 2.0  # Second retry: 2 seconds
        assert utils.get_backoff_time(3) == 4.0  # Third retry: 4 seconds
        
        # Test with jitter
        backoff_with_jitter = utils.get_backoff_time(3, jitter=True)
        assert 3.0 <= backoff_with_jitter <= 5.0  # 4 seconds ± jitter
        
        # Test max backoff
        assert utils.get_backoff_time(10, max_backoff=30) <= 30
    
    async def test_retry_strategies(self):
        from app.utils.retry_utils import RetryUtils
        
        utils = RetryUtils()
        
        # Test retry with exponential backoff
        attempt_count = 0
        
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "Success"
        
        result = await utils.retry_with_backoff(
            failing_function,
            max_retries=5,
            backoff_factor=0.1  # Speed up for testing
        )
        
        assert result == "Success"
        assert attempt_count == 3
        
        # Test permanent failure
        async def always_fails():
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError):
            await utils.retry_with_backoff(
                always_fails,
                max_retries=2,
                backoff_factor=0.01
            )


# Test 98: Monitoring utils metrics
@pytest.mark.asyncio
class TestMonitoringUtilsMetrics:
    """test_monitoring_utils_metrics - Test metric collection and aggregation"""
    
    async def test_metric_collection(self):
        from app.utils.monitoring_utils import MonitoringUtils
        
        utils = MonitoringUtils()
        
        # Test counter metrics
        utils.increment_counter("api_requests")
        utils.increment_counter("api_requests")
        assert utils.get_counter("api_requests") == 2
        
        # Test gauge metrics
        utils.set_gauge("memory_usage", 75.5)
        assert utils.get_gauge("memory_usage") == 75.5
        
        # Test histogram metrics
        for value in [10, 20, 30, 40, 50]:
            utils.record_histogram("response_time", value)
        
        stats = utils.get_histogram_stats("response_time")
        assert stats["mean"] == 30
        assert stats["median"] == 30
        assert stats["p95"] >= 40
    
    async def test_metric_aggregation(self):
        from app.utils.monitoring_utils import MonitoringUtils
        
        utils = MonitoringUtils()
        
        # Test time-based aggregation
        start_time = time.time()
        
        for i in range(10):
            utils.record_metric("cpu_usage", 50 + i, timestamp=start_time + i)
        
        # Get 5-second window average
        avg = utils.get_time_window_average(
            "cpu_usage",
            start_time,
            start_time + 5
        )
        assert avg == pytest.approx(52, rel=0.1)
        
        # Test metric export
        metrics = utils.export_metrics()
        assert "cpu_usage" in metrics
        assert "api_requests" in metrics


# Test 99: Debug utils profiling
@pytest.mark.asyncio
class TestDebugUtilsProfiling:
    """test_debug_utils_profiling - Test profiling utilities and performance metrics"""
    
    async def test_profiling_utilities(self):
        from app.utils.debug_utils import DebugUtils
        
        utils = DebugUtils()
        
        # Test function profiling
        @utils.profile_function
        async def slow_function():
            await asyncio.sleep(0.1)
            return "result"
        
        result = await slow_function()
        assert result == "result"
        
        profile_data = utils.get_profile_data("slow_function")
        assert profile_data["call_count"] == 1
        assert profile_data["total_time"] >= 0.1
        
        # Test memory profiling
        @utils.profile_memory
        def memory_intensive():
            data = [i for i in range(1000000)]
            return len(data)
        
        result = memory_intensive()
        assert result == 1000000
        
        memory_data = utils.get_memory_profile("memory_intensive")
        assert memory_data["peak_memory"] > 0
    
    async def test_performance_metrics(self):
        from app.utils.debug_utils import DebugUtils
        
        utils = DebugUtils()
        
        # Test timing context manager
        async with utils.timer("database_query") as timer:
            await asyncio.sleep(0.05)
        
        assert timer.elapsed >= 0.05
        
        # Test performance tracking
        for i in range(5):
            async with utils.timer("api_call"):
                await asyncio.sleep(0.01 * (i + 1))
        
        stats = utils.get_timing_stats("api_call")
        assert stats["count"] == 5
        assert stats["mean"] > 0
        assert stats["max"] >= stats["min"]


# Test 100: Migration utils scripts
@pytest.mark.asyncio
class TestMigrationUtilsScripts:
    """test_migration_utils_scripts - Test migration utilities and data transformation"""
    
    async def test_migration_utilities(self):
        from app.utils.migration_utils import MigrationUtils
        
        utils = MigrationUtils()
        
        # Test schema migration validation
        old_schema = {
            "version": 1,
            "fields": ["id", "name", "email"]
        }
        
        new_schema = {
            "version": 2,
            "fields": ["id", "name", "email", "phone"]
        }
        
        migration_plan = utils.generate_migration_plan(old_schema, new_schema)
        assert migration_plan["add_fields"] == ["phone"]
        assert migration_plan["remove_fields"] == []
        
        # Test data migration
        old_data = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"}
        ]
        
        migrated_data = utils.migrate_data(
            old_data,
            migration_plan,
            defaults={"phone": None}
        )
        
        assert all("phone" in item for item in migrated_data)
        assert migrated_data[0]["phone"] is None
    
    async def test_data_transformation(self):
        from app.utils.migration_utils import MigrationUtils
        
        utils = MigrationUtils()
        
        # Test field transformation
        transformations = {
            "full_name": lambda row: f"{row['first_name']} {row['last_name']}",
            "age": lambda row: datetime.now().year - row["birth_year"]
        }
        
        data = [
            {"first_name": "John", "last_name": "Doe", "birth_year": 1990},
            {"first_name": "Jane", "last_name": "Smith", "birth_year": 1985}
        ]
        
        transformed = utils.transform_data(data, transformations)
        
        assert transformed[0]["full_name"] == "John Doe"
        assert transformed[0]["age"] == datetime.now().year - 1990
        
        # Test batch processing
        large_dataset = [{"id": i} for i in range(10000)]
        
        processed_count = 0
        async for batch in utils.process_in_batches(large_dataset, batch_size=100):
            processed_count += len(batch)
            assert len(batch) <= 100
        
        assert processed_count == 10000