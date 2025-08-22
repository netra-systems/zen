"""Part 1: Basic type validation tests - TypeMismatchSeverity, TypeMismatch, basic TypeScriptParser."""

import sys
from pathlib import Path

from test_framework import setup_test_path

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest

from netra_backend.app.core.exceptions_config import (
    ValidationError as NetraValidationError,
)

from netra_backend.app.core.type_validation import (
    SchemaValidator,
    TypeCompatibilityChecker,
    TypeMismatch,
    TypeMismatchSeverity,
    TypeScriptParser,
    generate_validation_report,
    validate_type_consistency,
)

class TestTypeMismatchSeverity:
    """Test TypeMismatchSeverity enum."""
    
    def test_severity_values(self):
        """Test severity enum values."""
        assert TypeMismatchSeverity.INFO.value == "info"
        assert TypeMismatchSeverity.WARNING.value == "warning"
        assert TypeMismatchSeverity.ERROR.value == "error"
        assert TypeMismatchSeverity.CRITICAL.value == "critical"

class TestTypeMismatch:
    """Test TypeMismatch dataclass."""
    
    def test_type_mismatch_creation(self):
        """Test creating TypeMismatch instances."""
        mismatch = TypeMismatch(
            field_path="user.id",
            backend_type="int",
            frontend_type="string",
            severity=TypeMismatchSeverity.ERROR,
            message="Type mismatch detected",
            suggestion="Change to number"
        )
        
        assert mismatch.field_path == "user.id"
        assert mismatch.backend_type == "int"
        assert mismatch.frontend_type == "string"
        assert mismatch.severity == TypeMismatchSeverity.ERROR
        assert mismatch.message == "Type mismatch detected"
        assert mismatch.suggestion == "Change to number"
    
    def test_type_mismatch_without_suggestion(self):
        """Test TypeMismatch without suggestion."""
        mismatch = TypeMismatch(
            field_path="data.value",
            backend_type="float",
            frontend_type="boolean",
            severity=TypeMismatchSeverity.CRITICAL,
            message="Critical mismatch"
        )
        
        assert mismatch.suggestion == None

class TestTypeScriptParserBasic:
    """Test basic TypeScriptParser functionality."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = TypeScriptParser()
        assert parser.interface_pattern != None
        assert parser.type_pattern != None
        assert parser.field_pattern != None
    
    def test_parse_typescript_file_with_interface(self):
        """Test parsing TypeScript file with interface."""
        typescript_content = """
        export interface User {
            id: number;
            name: string;
            email?: string;
            isActive: boolean;
        }
        
        export interface Product {
            id: string;
            price: number;
            tags: string[];
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            
            assert 'User' in types
            assert types['User']['type'] == 'interface'
            assert 'id' in types['User']['fields']
            assert types['User']['fields']['id']['type'] == 'number'
            assert not types['User']['fields']['id']['optional']
            assert types['User']['fields']['email']['optional']
            
            assert 'Product' in types
            assert types['Product']['fields']['tags']['type'] == 'string[]'
        finally:
            Path(temp_path).unlink()
    
    def test_parse_typescript_file_with_type_alias(self):
        """Test parsing TypeScript file with type aliases."""
        typescript_content = """
        export type Status = 'active' | 'inactive' | 'pending';
        export type ID = string | number;
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            
            assert 'Status' in types
            assert types['Status']['type'] == 'alias'
            assert types['Status']['definition'] == "'active' | 'inactive' | 'pending'"
            
            assert 'ID' in types
            assert types['ID']['definition'] == 'string | number'
        finally:
            Path(temp_path).unlink()
    
    def test_parse_typescript_file_with_nested_objects(self):
        """Test parsing TypeScript with nested objects."""
        typescript_content = """
        export interface Config {
            server: {
                host: string;
                port: number;
            };
            database?: {
                url: string;
            };
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            
            assert 'Config' in types
            assert 'server' in types['Config']['fields']
            assert 'database' in types['Config']['fields']
            assert types['Config']['fields']['database']['optional']
        finally:
            Path(temp_path).unlink()
    
    def test_parse_interface_fields_with_comments(self):
        """Test parsing interface fields with comments."""
        parser = TypeScriptParser()
        interface_body = """
            /** User ID */
            id: number;
            // User name
            name: string;
            /* Optional email */
            email?: string;
        """
        
        fields = parser._parse_interface_fields(interface_body)
        
        assert 'id' in fields
        assert fields['id']['type'] == 'number'
        assert 'name' in fields
        assert fields['name']['type'] == 'string'
        assert 'email' in fields
        assert fields['email']['optional']
    
    def test_parse_typescript_file_error(self):
        """Test error handling when parsing fails."""
        parser = TypeScriptParser()
        
        # Mock ErrorContext.get_all_context to avoid the error
        with patch('app.core.type_validation.ErrorContext.get_all_context', return_value={}):
            with pytest.raises(NetraValidationError) as exc_info:
                parser.parse_typescript_file('/nonexistent/file.ts')
            
            assert "Failed to parse TypeScript file" in str(exc_info.value)

class TestTypeCompatibilityCheckerBasic:
    """Test basic TypeCompatibilityChecker functionality."""
    
    def test_checker_initialization(self):
        """Test checker initialization."""
        checker = TypeCompatibilityChecker()
        assert 'str' in checker.type_mappings
        assert checker.type_mappings['str'] == 'string'
        assert checker.type_mappings['int'] == 'number'
    
    def test_check_field_compatibility_exact_match(self):
        """Test field compatibility with exact match."""
        checker = TypeCompatibilityChecker()
        result = checker.check_field_compatibility('string', 'string', 'user.name')
        assert result == None
    
    def test_check_field_compatibility_mapped_types(self):
        """Test field compatibility with mapped types."""
        checker = TypeCompatibilityChecker()
        
        # Python str to TypeScript string
        result = checker.check_field_compatibility('str', 'string', 'user.name')
        assert result == None
        
        # Python int to TypeScript number
        result = checker.check_field_compatibility('int', 'number', 'user.age')
        assert result == None
    
    def test_check_field_compatibility_mismatch(self):
        """Test field compatibility with mismatch."""
        checker = TypeCompatibilityChecker()
        result = checker.check_field_compatibility('str', 'number', 'user.id')
        
        assert result != None
        assert result.field_path == 'user.id'
        assert result.backend_type == 'str'
        assert result.frontend_type == 'number'
        assert result.severity == TypeMismatchSeverity.CRITICAL
    
    def test_check_field_compatibility_compatible_types(self):
        """Test field compatibility with compatible but not exact types."""
        checker = TypeCompatibilityChecker()
        
        # Test array compatibility (covers line 137)
        result = checker.check_field_compatibility('List[str]', 'string[]', 'items')
        assert result == None  # Compatible array types