"""
Tests for file, crypto, and validation utilities (Tests 89-91).
Each function  <= 8 lines, using helper functions for setup and assertions.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import os
import tempfile

import pytest

from netra_backend.tests.json_file_crypto_test_helpers import (
    CryptoTestHelpers,
    FileTestHelpers,
)
from netra_backend.tests.validation_formatting_test_helpers import (
    ValidationTestHelpers,
)

# Utility modules (file_utils, crypto_utils, validation_utils) are now implemented

# Test 89: File utils operations
class TestFileUtilsOperations:
    """test_file_utils_operations - Test file operations and cleanup on error"""
    
    @pytest.mark.asyncio
    async def test_file_operations(self):
        from netra_backend.app.utils.file_utils import FileUtils
        utils = FileUtils()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            await FileTestHelpers.assert_file_operations(utils, tmpdir)
            await self._test_file_copy_operations(utils, tmpdir)
            await self._test_file_move_operations(utils, tmpdir)
            await self._test_file_deletion(utils, tmpdir)
    
    @pytest.mark.asyncio
    async def test_cleanup_on_error(self):
        from netra_backend.app.utils.file_utils import FileUtils
        utils = FileUtils()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = FileTestHelpers.create_temp_file_path(tmpdir, "temp.txt")
            await self._test_write_error_cleanup(utils, temp_file)
            await self._test_atomic_write(utils, tmpdir)
    
    async def _test_file_copy_operations(self, utils, tmpdir: str):
        """Test file copy operations."""
        file_path = FileTestHelpers.create_temp_file_path(tmpdir, "test.txt")
        copy_path = FileTestHelpers.create_temp_file_path(tmpdir, "copy.txt")
        
        await utils.write_file(file_path, "test content")
        await utils.copy_file(file_path, copy_path)
        assert os.path.exists(copy_path)
    
    async def _test_file_move_operations(self, utils, tmpdir: str):
        """Test file move operations."""
        copy_path = FileTestHelpers.create_temp_file_path(tmpdir, "copy.txt")
        move_path = FileTestHelpers.create_temp_file_path(tmpdir, "moved.txt")
        
        await utils.move_file(copy_path, move_path)
        assert os.path.exists(move_path)
        assert not os.path.exists(copy_path)
    
    async def _test_file_deletion(self, utils, tmpdir: str):
        """Test file deletion."""
        move_path = FileTestHelpers.create_temp_file_path(tmpdir, "moved.txt")
        await utils.delete_file(move_path)
        assert not os.path.exists(move_path)
    
    async def _test_write_error_cleanup(self, utils, temp_file: str):
        """Test cleanup on write error."""
        with FileTestHelpers.mock_write_failure():
            with pytest.raises(IOError):
                await utils.write_file_safe(temp_file, "content")
            assert not os.path.exists(temp_file)
    
    async def _test_atomic_write(self, utils, tmpdir: str):
        """Test atomic write operations."""
        target_file = FileTestHelpers.create_temp_file_path(tmpdir, "target.txt")
        await utils.write_file_atomic(target_file, "atomic content")
        
        content = await utils.read_file(target_file)
        assert content == "atomic content"

# Test 90: Crypto utils hashing
class TestCryptoUtilsHashing:
    """test_crypto_utils_hashing - Test hashing algorithms and salt generation"""
    
    @pytest.mark.asyncio
    async def test_hashing_algorithms(self):
        from netra_backend.app.utils.crypto_utils import CryptoUtils
        utils = CryptoUtils()
        data = "test data"
        
        sha256_hash = utils.hash_data(data, algorithm="sha256")
        CryptoTestHelpers.assert_hash_properties(sha256_hash, 64)
        
        sha512_hash = utils.hash_data(data, algorithm="sha512")
        CryptoTestHelpers.assert_hash_properties(sha512_hash, 128)
        
        self._assert_hash_consistency(utils, data)
        self._assert_different_data_different_hash(utils)
    
    @pytest.mark.asyncio
    async def test_salt_generation(self):
        from netra_backend.app.utils.crypto_utils import CryptoUtils
        utils = CryptoUtils()
        
        salt1, salt2 = utils.generate_salt(), utils.generate_salt()
        self._assert_salts_unique(salt1, salt2)
        
        password = "secure_password"
        self._assert_salted_hashing(utils, password, salt1, salt2)
        CryptoTestHelpers.assert_password_verification(utils, password, salt1)
    
    def _assert_hash_consistency(self, utils, data: str):
        """Assert hash consistency."""
        hash1 = utils.hash_data(data)
        hash2 = utils.hash_data(data)
        assert hash1 == hash2
    
    def _assert_different_data_different_hash(self, utils):
        """Assert different data produces different hashes."""
        hash1 = utils.hash_data("test data")
        hash3 = utils.hash_data("different data")
        assert hash1 != hash3
    
    def _assert_salts_unique(self, salt1: str, salt2: str):
        """Assert salts are unique and proper length."""
        assert salt1 != salt2
        assert len(salt1) >= 16
    
    def _assert_salted_hashing(self, utils, password: str, salt1: str, salt2: str):
        """Assert salted hashing produces different results."""
        hash1 = utils.hash_password(password, salt1)
        hash2 = utils.hash_password(password, salt2)
        assert hash1 != hash2

# Test 91: Validation utils schemas
class TestValidationUtilsSchemas:
    """test_validation_utils_schemas - Test schema validation and error messages"""
    
    @pytest.mark.asyncio
    async def test_schema_validation(self):
        from netra_backend.app.utils.validation_utils import ValidationUtils
        utils = ValidationUtils()
        
        schema = ValidationTestHelpers.create_user_schema()
        valid_data = ValidationTestHelpers.create_valid_user()
        assert utils.validate_schema(valid_data, schema) == True
        
        self._assert_missing_required_field(utils, schema)
        self._assert_invalid_type_validation(utils, schema)
    
    @pytest.mark.asyncio
    async def test_error_messages(self):
        from netra_backend.app.utils.validation_utils import ValidationUtils
        utils = ValidationUtils()
        
        schema = self._create_email_schema()
        invalid_data = {"email": "not-an-email"}
        errors = utils.get_validation_errors(invalid_data, schema)
        
        self._assert_error_messages(errors)
    
    def _assert_missing_required_field(self, utils, schema):
        """Assert missing required field validation."""
        invalid_data = ValidationTestHelpers.create_invalid_user()
        result = utils.validate_schema(invalid_data, schema)
        assert result == False or "age" in str(result)
    
    def _assert_invalid_type_validation(self, utils, schema):
        """Assert invalid type validation."""
        invalid_data = {"name": "John", "age": "thirty"}
        result = utils.validate_schema(invalid_data, schema)
        assert result == False or "type" in str(result)
    
    def _create_email_schema(self):
        """Create email validation schema."""
        return {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"}
            }
        }
    
    def _assert_error_messages(self, errors):
        """Assert error messages are properly generated."""
        assert len(errors) > 0
        assert any("email" in str(error) for error in errors)
        assert any("format" in str(error) for error in errors)