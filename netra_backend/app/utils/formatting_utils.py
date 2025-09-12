"""Formatting utilities for data display and localization.

This module provides utilities for formatting numbers, currencies, percentages,
and file sizes in a user-friendly and localized manner.

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise)
- Business Goal: Consistent data presentation across UI components
- Value Impact: Improves user experience with properly formatted data
- Strategic Impact: Foundation for internationalization and localization
"""

from typing import Any, Dict, Optional, Union


class FormattingUtils:
    """Utility class for data formatting and localization."""
    
    def __init__(self, locale: str = "en_US") -> None:
        """Initialize formatting utils with locale.
        
        Args:
            locale: Locale string for formatting (default: en_US)
        """
        self.locale = locale
    
    def format_number(self, value: Union[int, float], decimals: int = 2) -> str:
        """Format a number with proper thousands separators.
        
        Args:
            value: Number to format
            decimals: Number of decimal places
            
        Returns:
            Formatted number string
        """
        if isinstance(value, (int, float)):
            return f"{value:,.{decimals}f}"
        return str(value)
    
    def format_currency(self, value: Union[int, float], currency: str = "USD") -> str:
        """Format a value as currency.
        
        Args:
            value: Amount to format
            currency: Currency code (default: USD)
            
        Returns:
            Formatted currency string
        """
        if isinstance(value, (int, float)):
            symbols = {"USD": "$", "EUR": "[U+20AC]"}
            symbol = symbols.get(currency, currency)
            return f"{symbol}{value:,.2f}"
        return str(value)
    
    def format_percentage(self, value: Union[int, float], decimals: int = 2) -> str:
        """Format a value as percentage.
        
        Args:
            value: Value to format (0.1 = 10%)
            decimals: Number of decimal places
            
        Returns:
            Formatted percentage string
        """
        if isinstance(value, (int, float)):
            return f"{value * 100:.{decimals}f}%"
        return str(value)
    
    def format_file_size(self, size_bytes: Union[int, float]) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted file size string
        """
        if not isinstance(size_bytes, (int, float)):
            return str(size_bytes)
        
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"