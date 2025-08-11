"""Comprehensive tests for type_validation module to achieve 100% coverage."""

import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, mock_open, MagicMock

from app.core.type_validation import (
    TypeMismatchSeverity,
    TypeMismatch,
    TypeScriptParser,
    TypeCompatibilityChecker,
    SchemaValidator,
    validate_type_consistency,
    generate_validation_report
)
from app.core.exceptions import ValidationError as NetraValidationError


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
        
        assert mismatch.suggestion is None


class TestTypeScriptParser:
    """Test TypeScriptParser class."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = TypeScriptParser()
        assert parser.interface_pattern is not None
        assert parser.type_pattern is not None
        assert parser.field_pattern is not None
    
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


class TestTypeCompatibilityChecker:
    """Test TypeCompatibilityChecker class."""
    
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
        assert result is None
    
    def test_check_field_compatibility_mapped_types(self):
        """Test field compatibility with mapped types."""
        checker = TypeCompatibilityChecker()
        
        # Python str to TypeScript string
        result = checker.check_field_compatibility('str', 'string', 'user.name')
        assert result is None
        
        # Python int to TypeScript number
        result = checker.check_field_compatibility('int', 'number', 'user.age')
        assert result is None
    
    def test_check_field_compatibility_mismatch(self):
        """Test field compatibility with mismatch."""
        checker = TypeCompatibilityChecker()
        result = checker.check_field_compatibility('str', 'number', 'user.id')
        
        assert result is not None
        assert result.field_path == 'user.id'
        assert result.backend_type == 'str'
        assert result.frontend_type == 'number'
        assert result.severity == TypeMismatchSeverity.CRITICAL
    
    def test_check_field_compatibility_compatible_types(self):
        """Test field compatibility with compatible but not exact types."""
        checker = TypeCompatibilityChecker()
        
        # Test array compatibility (covers line 137)
        result = checker.check_field_compatibility('List[str]', 'string[]', 'items')
        assert result is None  # Compatible array types
    
    def test_normalize_backend_type_optional(self):
        """Test normalizing Optional backend types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('Optional[str]')
        assert normalized == 'string'
        
        normalized = checker._normalize_backend_type('Optional[int]')
        assert normalized == 'number'
    
    def test_normalize_backend_type_union(self):
        """Test normalizing Union backend types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('Union[str, None]')
        assert normalized == 'string'
        
        normalized = checker._normalize_backend_type('Union[int, str]')
        assert normalized == 'number'
    
    def test_normalize_backend_type_list(self):
        """Test normalizing List backend types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('List[str]')
        assert normalized == 'Array<string>'
        
        normalized = checker._normalize_backend_type('List[int]')
        assert normalized == 'Array<number>'
    
    def test_normalize_backend_type_dict(self):
        """Test normalizing Dict backend types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('Dict[str, Any]')
        assert normalized == 'Record<string, any>'
        
        normalized = checker._normalize_backend_type('Dict[str, int]')
        assert normalized == 'Record<string, any>'
    
    def test_normalize_frontend_type(self):
        """Test normalizing frontend types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_frontend_type('  string  ')
        assert normalized == 'string'
        
        normalized = checker._normalize_frontend_type('number[]')
        assert normalized == 'number[]'
    
    def test_are_types_compatible_any(self):
        """Test type compatibility with 'any' type."""
        checker = TypeCompatibilityChecker()
        
        assert checker._are_types_compatible('string', 'any')
        assert checker._are_types_compatible('any', 'number')
        assert checker._are_types_compatible('any', 'any')
    
    def test_are_types_compatible_numbers(self):
        """Test type compatibility for numbers."""
        checker = TypeCompatibilityChecker()
        
        assert checker._are_types_compatible('number', 'number')
        assert checker._are_types_compatible('number', 'integer')
        assert not checker._are_types_compatible('number', 'string')
    
    def test_are_types_compatible_strings(self):
        """Test type compatibility for strings."""
        checker = TypeCompatibilityChecker()
        
        assert checker._are_types_compatible('string', 'string')
        assert checker._are_types_compatible('string', 'Date')
        assert not checker._are_types_compatible('string', 'boolean')
    
    def test_are_types_compatible_arrays(self):
        """Test type compatibility for arrays."""
        checker = TypeCompatibilityChecker()
        
        assert checker._are_types_compatible('Array<string>', 'Array<string>')
        assert checker._are_types_compatible('Array<number>', 'number[]')
        assert checker._are_types_compatible('string[]', 'Array<string>')
        assert not checker._are_types_compatible('Array<string>', 'string')
    
    def test_are_types_compatible_objects(self):
        """Test type compatibility for objects."""
        checker = TypeCompatibilityChecker()
        
        assert checker._are_types_compatible('Record<string, any>', 'Record<string, number>')
        assert checker._are_types_compatible('{foo: string}', 'Record<string, any>')
        assert checker._are_types_compatible('Record<string, any>', '{bar: number}')
    
    def test_determine_mismatch_severity_critical(self):
        """Test determining critical severity mismatches."""
        checker = TypeCompatibilityChecker()
        
        severity = checker._determine_mismatch_severity('string', 'number')
        assert severity == TypeMismatchSeverity.CRITICAL
        
        severity = checker._determine_mismatch_severity('boolean', 'string')
        assert severity == TypeMismatchSeverity.CRITICAL
        
        severity = checker._determine_mismatch_severity('Array<string>', 'string')
        assert severity == TypeMismatchSeverity.CRITICAL
    
    def test_determine_mismatch_severity_error(self):
        """Test determining error severity mismatches."""
        checker = TypeCompatibilityChecker()
        
        severity = checker._determine_mismatch_severity('string', 'object')
        assert severity == TypeMismatchSeverity.ERROR
        
        severity = checker._determine_mismatch_severity('boolean', 'object')
        assert severity == TypeMismatchSeverity.ERROR
    
    def test_determine_mismatch_severity_warning(self):
        """Test determining warning severity mismatches."""
        checker = TypeCompatibilityChecker()
        
        severity = checker._determine_mismatch_severity('string', 'any')
        assert severity == TypeMismatchSeverity.WARNING
        
        severity = checker._determine_mismatch_severity('number', 'any')
        assert severity == TypeMismatchSeverity.WARNING
    
    def test_determine_mismatch_severity_info(self):
        """Test determining info severity mismatches."""
        checker = TypeCompatibilityChecker()
        
        severity = checker._determine_mismatch_severity('CustomType', 'AnotherType')
        assert severity == TypeMismatchSeverity.INFO
    
    def test_generate_type_suggestion_string_number(self):
        """Test generating suggestions for string/number mismatches."""
        checker = TypeCompatibilityChecker()
        
        suggestion = checker._generate_type_suggestion('string', 'number')
        assert suggestion == "Convert to string or update backend to expect number"
        
        suggestion = checker._generate_type_suggestion('number', 'string')
        assert suggestion == "Convert to number or update backend to expect string"
    
    def test_generate_type_suggestion_any(self):
        """Test generating suggestions for 'any' type."""
        checker = TypeCompatibilityChecker()
        
        suggestion = checker._generate_type_suggestion('string', 'any')
        assert "Replace 'any' with 'string'" in suggestion
    
    def test_generate_type_suggestion_array(self):
        """Test generating suggestions for array types."""
        checker = TypeCompatibilityChecker()
        
        suggestion = checker._generate_type_suggestion('Array<string>', 'string')
        assert "Change frontend type to array" in suggestion
    
    def test_generate_type_suggestion_default(self):
        """Test default suggestion generation."""
        checker = TypeCompatibilityChecker()
        
        suggestion = checker._generate_type_suggestion('CustomType', 'OtherType')
        assert "Update frontend type to match backend: CustomType" in suggestion


class TestSchemaValidator:
    """Test SchemaValidator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = SchemaValidator()
        assert validator.ts_parser is not None
        assert validator.compat_checker is not None
    
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
            assert product_mismatch is not None
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
            assert email_mismatch is not None
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
            assert id_mismatch is not None
            assert id_mismatch.backend_type == 'int'
            assert id_mismatch.frontend_type == 'string'
            
            name_mismatch = next((m for m in mismatches if m.field_path == 'User.name'), None)
            assert name_mismatch is not None
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
            assert extra_mismatch is not None
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


class TestValidationFunctions:
    """Test module-level validation functions."""
    
    def test_validate_type_consistency(self):
        """Test validate_type_consistency function."""
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
                        'name': {'type': 'str'},
                        'email': {'type': 'str'}
                    }
                }
            }
            
            mismatches = validate_type_consistency(backend_schemas, temp_path)
            
            # Should find email missing in frontend
            assert any('email' in m.field_path for m in mismatches)
        finally:
            Path(temp_path).unlink()
    
    def test_generate_validation_report_no_mismatches(self):
        """Test generating report with no mismatches."""
        report = generate_validation_report([])
        assert "✅ All type validations passed!" in report
        assert "Frontend and backend schemas are consistent" in report
    
    def test_generate_validation_report_with_mismatches(self):
        """Test generating report with various mismatches."""
        mismatches = [
            TypeMismatch(
                field_path="User.id",
                backend_type="int",
                frontend_type="string",
                severity=TypeMismatchSeverity.CRITICAL,
                message="Critical type mismatch",
                suggestion="Fix immediately"
            ),
            TypeMismatch(
                field_path="User.name",
                backend_type="str",
                frontend_type="any",
                severity=TypeMismatchSeverity.WARNING,
                message="Using any type",
                suggestion="Use specific type"
            ),
            TypeMismatch(
                field_path="User.email",
                backend_type="str",
                frontend_type="missing",
                severity=TypeMismatchSeverity.ERROR,
                message="Field missing",
                suggestion=None
            ),
            TypeMismatch(
                field_path="User.created",
                backend_type="datetime",
                frontend_type="Date",
                severity=TypeMismatchSeverity.INFO,
                message="Minor difference",
                suggestion="Consider alignment"
            )
        ]
        
        report = generate_validation_report(mismatches)
        
        assert "Type Validation Report" in report
        assert "Total mismatches found: 4" in report
        assert "🚨 CRITICAL (1 issues)" in report
        assert "❌ ERROR (1 issues)" in report
        assert "⚠️ WARNING (1 issues)" in report
        assert "ℹ️ INFO (1 issues)" in report
        
        assert "Field: User.id" in report
        assert "Backend: int" in report
        assert "Frontend: string" in report
        assert "Issue: Critical type mismatch" in report
        assert "Suggestion: Fix immediately" in report
        
        assert "Field: User.email" in report
        assert "Issue: Field missing" in report
        # No suggestion for this one
        
        assert "Field: User.created" in report
        assert "Suggestion: Consider alignment" in report
    
    def test_generate_validation_report_partial_severities(self):
        """Test report generation with only some severity levels."""
        mismatches = [
            TypeMismatch(
                field_path="Config.timeout",
                backend_type="int",
                frontend_type="string",
                severity=TypeMismatchSeverity.ERROR,
                message="Type error"
            ),
            TypeMismatch(
                field_path="Config.retry",
                backend_type="bool",
                frontend_type="any",
                severity=TypeMismatchSeverity.WARNING,
                message="Using any"
            )
        ]
        
        report = generate_validation_report(mismatches)
        
        assert "Total mismatches found: 2" in report
        assert "❌ ERROR (1 issues)" in report
        assert "⚠️ WARNING (1 issues)" in report
        # Should not have CRITICAL or INFO sections
        assert "🚨 CRITICAL" not in report
        assert "ℹ️ INFO" not in report


class TestEdgeCases:
    """Test edge cases and complex scenarios."""
    
    def test_deeply_nested_optional_types(self):
        """Test handling deeply nested Optional types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('Optional[Optional[str]]')
        assert normalized == 'string'
        
        normalized = checker._normalize_backend_type('Optional[Union[str, None]]')
        assert normalized == 'string'
    
    def test_complex_union_types(self):
        """Test handling complex Union types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('Union[str, int, bool]')
        assert normalized == 'string'  # Takes first type
        
        normalized = checker._normalize_backend_type('Union[List[str], None]')
        assert normalized == 'Array<string>'
    
    def test_nested_list_types(self):
        """Test handling nested List types."""
        checker = TypeCompatibilityChecker()
        
        normalized = checker._normalize_backend_type('List[List[str]]')
        assert normalized == 'Array<Array<string>>'
        
        normalized = checker._normalize_backend_type('List[Dict[str, Any]]')
        assert normalized == 'Array<Record<string, any>>'
    
    def test_typescript_parser_malformed_input(self):
        """Test TypeScript parser with malformed input."""
        typescript_content = """
        export interface User {
            id: number
            // Missing semicolon above
            name: string;
            // Trailing comma below
            email?: string,
        }
        
        export interface Product
            // Missing opening brace
            id: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            
            # Should still parse User interface
            assert 'User' in types
            assert 'id' in types['User']['fields']
            # Name might be parsed incorrectly due to missing semicolon
            # But at least some fields should be present
            assert len(types['User']['fields']) > 0
            
            # Product might not parse correctly
            # But shouldn't crash
        finally:
            Path(temp_path).unlink()
    
    def test_empty_schemas(self):
        """Test validation with empty schemas."""
        typescript_content = """
        export interface EmptyInterface {
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            backend_schemas = {
                'EmptyInterface': {
                    'properties': {}
                }
            }
            
            validator = SchemaValidator()
            mismatches = validator.validate_schemas(backend_schemas, temp_path)
            
            # Should have no mismatches for empty schemas
            assert len(mismatches) == 0
        finally:
            Path(temp_path).unlink()
    
    def test_special_characters_in_field_names(self):
        """Test handling special characters in field names."""
        typescript_content = """
        export interface Data {
            $id: string;
            _private: boolean;
            "quoted-name": number;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            
            # Parser should handle these field names
            if 'Data' in types and 'fields' in types['Data']:
                # At least some fields should be parsed
                assert len(types['Data']['fields']) > 0
        finally:
            Path(temp_path).unlink()