"""
Test helpers for JSON, file, and crypto utilities testing.
Provides setup, assertion, and fixture functions for JSON, file, and crypto utility tests.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import patch

class JsonTestHelpers:
    """Helper functions for JSON utility testing."""
    
    @staticmethod
    def create_datetime_data() -> Dict[str, Any]:
        """Create data with datetime objects."""
        return {
            "timestamp": datetime.now(timezone.utc),
            "date": datetime.now().date(),
            "decimal": Decimal("123.45")
        }
    
    @staticmethod
    def create_circular_reference() -> Dict[str, Any]:
        """Create circular reference for testing."""
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2
        return obj1
    
    @staticmethod
    def create_nested_data(depth: int = 100) -> Dict[str, Any]:
        """Create deeply nested data structure."""
        nested = {"level": 0}
        current = nested
        for i in range(depth):
            current["child"] = {"level": i + 1}
            current = current["child"]
        return nested

class FileTestHelpers:
    """Helper functions for file utility testing."""
    
    @staticmethod
    def create_temp_file_path(tmpdir: str, filename: str) -> str:
        """Create temporary file path."""
        return os.path.join(tmpdir, filename)
    
    @staticmethod
    async def assert_file_operations(utils, tmpdir: str):
        """Assert basic file operations work."""
        file_path = FileTestHelpers.create_temp_file_path(tmpdir, "test.txt")
        await utils.write_file(file_path, "test content")
        assert os.path.exists(file_path)
        
        content = await utils.read_file(file_path)
        assert content == "test content"
    
    @staticmethod
    def mock_write_failure():
        """Mock write failure for testing."""
        # Mock: Component isolation for testing without external dependencies
        return patch('builtins.open', side_effect=IOError("Write failed"))

class CryptoTestHelpers:
    """Helper functions for crypto utility testing."""
    
    @staticmethod
    def assert_hash_properties(hash_value: str, expected_length: int):
        """Assert hash has expected properties."""
        assert len(hash_value) == expected_length
    
    @staticmethod
    def assert_password_verification(utils, password: str, salt: str):
        """Assert password verification works correctly."""
        stored_hash = utils.hash_password(password, salt)
        assert utils.verify_password(password, stored_hash, salt) == True
        assert utils.verify_password("wrong_password", stored_hash, salt) == False