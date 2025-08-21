"""Configuration loading exceptions - part of modular config_loader split."""

from typing import Dict, Any, Optional, List


class ConfigLoadError(Exception):
    """Exception raised when configuration loading fails."""
    
    def __init__(self, message: str, missing_keys: Optional[List[str]] = None, invalid_values: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.missing_keys = missing_keys or []
        self.invalid_values = invalid_values or {}