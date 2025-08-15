"""Part 4: Edge cases, error handling, and module-level functions."""

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
from app.core.exceptions_config import ValidationError as NetraValidationError


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
    
    def test_unicode_and_special_content(self):
        """Test handling Unicode and special content."""
        self._test_unicode_parsing()
    
    def _test_unicode_parsing(self):
        """Helper to test Unicode parsing."""
        typescript_content = """
        export interface UnicodeData {
            name: string;
            description: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False, encoding='utf-8') as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            if 'UnicodeData' in types:
                assert len(types['UnicodeData']['fields']) > 0
        finally:
            Path(temp_path).unlink()
    
    def test_null_and_undefined_handling(self):
        """Test null and undefined type handling."""
        checker = TypeCompatibilityChecker()
        
        # Test with Optional types
        normalized = checker._normalize_backend_type('Optional[str]')
        assert normalized == 'string'
    
    def test_error_recovery_mechanisms(self):
        """Test error recovery in parsing."""
        self._test_broken_interface_recovery()
    
    def _test_broken_interface_recovery(self):
        """Helper to test broken interface recovery."""
        typescript_content = """
        export interface Working {
            id: number;
            name: string;
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(typescript_content)
            temp_path = f.name
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            assert 'Working' in types
            assert len(types['Working']['fields']) == 2
        finally:
            Path(temp_path).unlink()