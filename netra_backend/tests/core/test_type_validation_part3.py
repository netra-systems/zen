"""Part 3: Schema validation and integration tests - SchemaValidator class."""

import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, mock_open, MagicMock

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.core.type_validation import (

# Add project root to path
    TypeMismatchSeverity,
    TypeMismatch,
    TypeScriptParser,
    TypeCompatibilityChecker,
    SchemaValidator,
    validate_type_consistency,
    generate_validation_report
)
from netra_backend.app.core.exceptions_config import ValidationError as NetraValidationError


class TestSchemaValidator:
    """Test SchemaValidator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = SchemaValidator()
        assert validator.ts_parser != None
        assert validator.compat_checker != None
    
    def test_validate_schemas_missing_frontend_schema(self):
        """Test validation when frontend schema is missing."""
        typescript_content = """
        export interface User {
            id: number;
            name: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            backend_schemas = {
                'User': {
                    'properties': {
                        'id': {'type': 'int'},
                        'name': {'type': 'str'}
                    }
                },
                'Product': {
                    'properties': {
                        'id': {'type': 'str'}
                    }
                }
            }
            
            validator = SchemaValidator()
            mismatches = validator.validate_schemas(backend_schemas, temp_path)
            
            # Should find Product missing in frontend
            product_mismatch = next((m for m in mismatches if m.field_path == 'Product'), None)
            assert product_mismatch != None
            assert product_mismatch.frontend_type == 'missing'
            assert product_mismatch.severity == TypeMismatchSeverity.ERROR
        finally:
            Path(temp_path).unlink()
    
    def test_validate_schemas_missing_backend_field(self):
        """Test validation when backend field is missing."""
        typescript_content = """
        export interface User {
            id: number;
            name: string;
            email: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            backend_schemas = {
                'User': {
                    'properties': {
                        'id': {'type': 'int'},
                        'name': {'type': 'str'}
                    }
                }
            }
            
            validator = SchemaValidator()
            mismatches = validator.validate_schemas(backend_schemas, temp_path)
            
            # Should find email field in frontend but not backend
            email_mismatch = next((m for m in mismatches if 'email' in m.field_path), None)
            assert email_mismatch != None
            assert email_mismatch.backend_type == 'missing'
            assert email_mismatch.severity == TypeMismatchSeverity.INFO
        finally:
            Path(temp_path).unlink()
    
    def test_validate_schemas_with_type_mismatch(self):
        """Test validation with type mismatches (covers line 328)."""
        typescript_content = """
        export interface User {
            id: string;
            name: number;
            active: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            backend_schemas = {
                'User': {
                    'properties': {
                        'id': {'type': 'int'},
                        'name': {'type': 'str'},
                        'active': {'type': 'bool'}
                    }
                }
            }
            
            validator = SchemaValidator()
            mismatches = validator.validate_schemas(backend_schemas, temp_path)
            
            # Should find type mismatches for all fields
            assert len(mismatches) >= 3  # At least 3 mismatches
            
            # Check specific mismatches
            id_mismatch = next((m for m in mismatches if m.field_path == 'User.id'), None)
            assert id_mismatch != None
            assert id_mismatch.backend_type == 'int'
            assert id_mismatch.frontend_type == 'string'
            
            name_mismatch = next((m for m in mismatches if m.field_path == 'User.name'), None)
            assert name_mismatch != None
            assert name_mismatch.backend_type == 'str'
            assert name_mismatch.frontend_type == 'number'
        finally:
            Path(temp_path).unlink()
    
    def test_validate_schemas_type_alias_skip(self):
        """Test that type aliases are skipped in validation."""
        typescript_content = """
        export type Status = 'active' | 'inactive';
        export interface User {
            id: number;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            backend_schemas = {
                'Status': {
                    'properties': {}
                },
                'User': {
                    'properties': {
                        'id': {'type': 'int'}
                    }
                }
            }
            
            validator = SchemaValidator()
            mismatches = validator.validate_schemas(backend_schemas, temp_path)
            
            # Status should not be validated since it's a type alias
            status_mismatches = [m for m in mismatches if 'Status' in m.field_path]
            assert len(status_mismatches) == 0
        finally:
            Path(temp_path).unlink()
    
    def test_validate_schemas_extra_frontend_schema(self):
        """Test validation with extra frontend schemas."""
        typescript_content = """
        export interface User {
            id: number;
        }
        export interface Extra {
            value: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            backend_schemas = {
                'User': {
                    'properties': {
                        'id': {'type': 'int'}
                    }
                }
            }
            
            validator = SchemaValidator()
            mismatches = validator.validate_schemas(backend_schemas, temp_path)
            
            extra_mismatch = next((m for m in mismatches if m.field_path == 'Extra'), None)
            assert extra_mismatch != None
            assert extra_mismatch.backend_type == 'missing'
            assert extra_mismatch.severity == TypeMismatchSeverity.INFO
        finally:
            Path(temp_path).unlink()
    
    def test_get_backend_field_type_with_ref(self):
        """Test extracting backend field type with $ref."""
        validator = SchemaValidator()
        
        # Test with standard definitions ref
        field_schema = {'$ref': '#/definitions/CustomType'}
        field_type = validator._get_backend_field_type(field_schema)
        assert field_type == 'CustomType'
        
        # Test with longer definition path
        field_schema = {'$ref': '#/definitions/models/UserSchema'}
        field_type = validator._get_backend_field_type(field_schema)
        assert field_type == 'models/UserSchema'
        
        # Test with non-standard ref path - should return 'unknown' 
        field_schema = {'$ref': '#/CustomType'}
        field_type = validator._get_backend_field_type(field_schema)
        assert field_type == 'unknown'  # Falls through to default return
    
    def test_get_backend_field_type_with_items(self):
        """Test extracting backend field type with items (array)."""
        validator = SchemaValidator()
        
        field_schema = {
            'items': {'type': 'string'}
        }
        field_type = validator._get_backend_field_type(field_schema)
        assert field_type == 'List[string]'
    
    def test_get_backend_field_type_with_anyof(self):
        """Test extracting backend field type with anyOf (union)."""
        validator = SchemaValidator()
        
        field_schema = {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'}
            ]
        }
        field_type = validator._get_backend_field_type(field_schema)
        assert field_type == 'Union[string, number]'
    
    def test_get_backend_field_type_unknown(self):
        """Test extracting backend field type when unknown."""
        validator = SchemaValidator()
        
        field_schema = {}
        field_type = validator._get_backend_field_type(field_schema)
        assert field_type == 'unknown'


