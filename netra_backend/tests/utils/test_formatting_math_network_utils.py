"""
Tests for formatting, math, and network utilities (Tests 92-94).
Each function ≤8 lines, using helper functions for setup and assertions.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import socket
from datetime import datetime
from decimal import Decimal

import pytest

from netra_backend.tests.network_pagination_test_helpers import (
    NetworkTestHelpers,
)

from netra_backend.tests.validation_formatting_test_helpers import (
    FormattingTestHelpers,
)

# Test 92: Formatting utils display
class TestFormattingUtilsDisplay:
    """test_formatting_utils_display - Test data formatting and localization"""
    
    @pytest.mark.asyncio
    async def test_data_formatting(self):
        from netra_backend.app.utils.formatting_utils import FormattingUtils
        utils = FormattingUtils()
        
        self._assert_number_formatting(utils)
        self._assert_currency_formatting(utils)
        self._assert_percentage_formatting(utils)
        self._assert_file_size_formatting(utils)
    
    @pytest.mark.asyncio
    async def test_localization(self):
        from netra_backend.app.utils.formatting_utils import FormattingUtils
        utils_us = FormattingUtils(locale="en_US")
        utils_de = FormattingUtils(locale="de_DE")
        
        self._assert_locale_number_formatting(utils_us, utils_de)
        self._assert_locale_date_formatting(utils_us, utils_de)
    
    def _assert_number_formatting(self, utils):
        """Assert number formatting works correctly."""
        FormattingTestHelpers.assert_number_formatting(
            utils.format_number(1234567.89), "1,234,567.89"
        )
        FormattingTestHelpers.assert_number_formatting(
            utils.format_number(1234567.89, decimals=0), "1,234,568"
        )
    
    def _assert_currency_formatting(self, utils):
        """Assert currency formatting works correctly."""
        FormattingTestHelpers.assert_currency_formatting(
            utils.format_currency(1234.56, "USD"), "USD"
        )
        FormattingTestHelpers.assert_currency_formatting(
            utils.format_currency(1234.56, "EUR"), "EUR"
        )
    
    def _assert_percentage_formatting(self, utils):
        """Assert percentage formatting works correctly."""
        assert utils.format_percentage(0.1234) == "12.34%"
        assert utils.format_percentage(0.1234, decimals=1) == "12.3%"
    
    def _assert_file_size_formatting(self, utils):
        """Assert file size formatting works correctly."""
        assert utils.format_file_size(1024) == "1.0 KB"
        assert utils.format_file_size(1048576) == "1.0 MB"
        assert utils.format_file_size(1073741824) == "1.0 GB"
    
    def _assert_locale_number_formatting(self, utils_us, utils_de):
        """Assert locale-specific number formatting."""
        assert utils_us.format_number(1234.56) == "1,234.56"
        assert utils_de.format_number(1234.56) == "1.234,56"
    
    def _assert_locale_date_formatting(self, utils_us, utils_de):
        """Assert locale-specific date formatting."""
        date = datetime(2025, 1, 15)
        assert "January" in utils_us.format_date(date, "long")
        assert "Januar" in utils_de.format_date(date, "long")

# Test 93: Math utils calculations
class TestMathUtilsCalculations:
    """test_math_utils_calculations - Test mathematical operations and precision handling"""
    
    @pytest.mark.asyncio
    async def test_mathematical_operations(self):
        from netra_backend.app.utils.math_utils import MathUtils
        utils = MathUtils()
        data = [1, 2, 3, 4, 5]
        
        self._assert_basic_statistics(utils, data)
        self._assert_percentiles(utils, data)
        self._assert_moving_average(utils, data)
    
    @pytest.mark.asyncio
    async def test_precision_handling(self):
        from netra_backend.app.utils.math_utils import MathUtils
        utils = MathUtils()
        
        self._assert_decimal_precision(utils)
        self._assert_rounding_methods(utils)
        self._assert_financial_rounding(utils)
    
    def _assert_basic_statistics(self, utils, data):
        """Assert basic statistical operations."""
        assert utils.mean(data) == 3.0
        assert utils.median(data) == 3.0
        assert utils.std_dev(data) == pytest.approx(1.414, rel=0.01)
    
    def _assert_percentiles(self, utils, data):
        """Assert percentile calculations."""
        assert utils.percentile(data, 50) == 3.0
        assert utils.percentile(data, 25) == 2.0
        assert utils.percentile(data, 75) == 4.0
    
    def _assert_moving_average(self, utils, data):
        """Assert moving average calculation."""
        moving_avg = utils.moving_average(data, window=3)
        assert moving_avg == pytest.approx([2.0, 3.0, 4.0], rel=0.01)
    
    def _assert_decimal_precision(self, utils):
        """Assert decimal precision handling."""
        result = utils.divide(1, 3, precision=4)
        assert result == Decimal("0.3333")
    
    def _assert_rounding_methods(self, utils):
        """Assert different rounding methods."""
        assert utils.round_half_up(2.5) == 3
        assert utils.round_half_down(2.5) == 2
    
    def _assert_financial_rounding(self, utils):
        """Assert financial rounding methods."""
        assert utils.round_financial(2.345) == Decimal("2.35")
        assert utils.round_financial(2.344) == Decimal("2.34")

# Test 94: Network utils requests
class TestNetworkUtilsRequests:
    """test_network_utils_requests - Test network utilities and retry logic"""
    
    @pytest.mark.asyncio
    async def test_network_utilities(self):
        from netra_backend.app.utils.network_utils import NetworkUtils
        utils = NetworkUtils()
        
        self._assert_url_validation(utils)
        self._assert_ip_validation(utils)
        await self._assert_port_checking(utils)
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        from netra_backend.app.utils.network_utils import NetworkUtils
        utils = NetworkUtils()
        
        await self._assert_successful_request(utils)
        await self._assert_retry_on_failure(utils)
    
    def _assert_url_validation(self, utils):
        """Assert URL validation works."""
        assert utils.is_valid_url("https://example.com") == True
        assert utils.is_valid_url("not-a-url") == False
    
    def _assert_ip_validation(self, utils):
        """Assert IP validation works."""
        assert utils.is_valid_ip("192.168.1.1") == True
        assert utils.is_valid_ip("256.256.256.256") == False
        assert utils.is_valid_ip("::1") == True  # IPv6
    
    async def _assert_port_checking(self, utils):
        """Assert port checking works."""
        # Mock: Component isolation for testing without external dependencies
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.connect_ex.return_value = 0
            assert await utils.is_port_open("localhost", 80) == True
            
            mock_socket.return_value.connect_ex.return_value = 1
            assert await utils.is_port_open("localhost", 80) == False
    
    async def _assert_successful_request(self, utils):
        """Assert successful HTTP request."""
        mock_response = NetworkTestHelpers.mock_successful_response()
        # Mock: Session isolation for controlled testing without external state
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            result = await utils.http_get_with_retry("https://api.example.com")
            assert result["success"] == True
    
    async def _assert_retry_on_failure(self, utils):
        """Assert retry logic on failure."""
        failing_get, get_call_count = NetworkTestHelpers.create_failing_request(3)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('aiohttp.ClientSession.get', side_effect=failing_get):
            result = await utils.http_get_with_retry(
                "https://api.example.com", max_retries=3
            )
            assert get_call_count() == 3