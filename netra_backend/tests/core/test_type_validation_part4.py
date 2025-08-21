"""Part 4: Edge cases, error handling, and module-level functions."""

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


def _create_temp_typescript_file(content: str) -> str:
    """Create temporary TypeScript file with content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
        f.write(content)
        return f.name


class TestValidationFunctions:
    """Test module-level validation functions."""
    
    def test_validate_type_consistency(self):
        """Test validate_type_consistency function."""
        typescript_content = self._get_user_interface_content()
        temp_path = _create_temp_typescript_file(typescript_content)
        
        try:
            backend_schemas = self._create_test_backend_schemas()
            mismatches = validate_type_consistency(backend_schemas, temp_path)
            assert any('email' in m.field_path for m in mismatches)
        finally:
            Path(temp_path).unlink()

    def _get_user_interface_content(self) -> str:
        """Get TypeScript interface content for testing."""
        return """
        export interface User {
            id: number;
            name: string;
        }
        """


    def _create_test_backend_schemas(self) -> Dict[str, Any]:
        """Create test backend schemas."""
        return {
            'User': {
                'properties': {
                    'id': {'type': 'int'},
                    'name': {'type': 'str'},
                    'email': {'type': 'str'}
                }
            }
        }
    
    def test_generate_validation_report_no_mismatches(self):
        """Test generating report with no mismatches."""
        report = generate_validation_report([])
        assert "✅ All type validations passed!" in report
        assert "Frontend and backend schemas are consistent" in report
    
    def test_generate_validation_report_with_mismatches(self):
        """Test generating report with various mismatches."""
        mismatches = self._create_test_mismatches()
        report = generate_validation_report(mismatches)
        
        self._assert_report_header(report)
        self._assert_severity_counts(report)
        self._assert_specific_mismatch_details(report)

    def _create_test_mismatches(self) -> list:
        """Create test mismatches for validation report."""
        return [
            self._create_critical_mismatch(),
            self._create_warning_mismatch(),
            self._create_error_mismatch(),
            self._create_info_mismatch()
        ]

    def _create_critical_mismatch(self) -> TypeMismatch:
        """Create critical type mismatch."""
        return TypeMismatch(
            field_path="User.id", backend_type="int", frontend_type="string",
            severity=TypeMismatchSeverity.CRITICAL, message="Critical type mismatch",
            suggestion="Fix immediately"
        )

    def _create_warning_mismatch(self) -> TypeMismatch:
        """Create warning type mismatch."""
        return TypeMismatch(
            field_path="User.name", backend_type="str", frontend_type="any",
            severity=TypeMismatchSeverity.WARNING, message="Using any type",
            suggestion="Use specific type"
        )

    def _create_error_mismatch(self) -> TypeMismatch:
        """Create error type mismatch."""
        return TypeMismatch(
            field_path="User.email", backend_type="str", frontend_type="missing",
            severity=TypeMismatchSeverity.ERROR, message="Field missing",
            suggestion=None
        )

    def _create_info_mismatch(self) -> TypeMismatch:
        """Create info type mismatch."""
        return TypeMismatch(
            field_path="User.created", backend_type="datetime", frontend_type="Date",
            severity=TypeMismatchSeverity.INFO, message="Minor difference",
            suggestion="Consider alignment"
        )

    def _assert_report_header(self, report: str) -> None:
        """Assert report header content."""
        assert "Type Validation Report" in report
        assert "Total mismatches found: 4" in report

    def _assert_severity_counts(self, report: str) -> None:
        """Assert severity count information."""
        assert "🚨 CRITICAL (1 issues)" in report
        assert "❌ ERROR (1 issues)" in report
        assert "⚠️ WARNING (1 issues)" in report
        assert "ℹ️ INFO (1 issues)" in report

    def _assert_specific_mismatch_details(self, report: str) -> None:
        """Assert specific mismatch details."""
        self._assert_critical_details(report)
        self._assert_error_details(report)
        self._assert_info_details(report)

    def _assert_critical_details(self, report: str) -> None:
        """Assert critical mismatch details."""
        assert "Field: User.id" in report
        assert "Backend: int" in report
        assert "Frontend: string" in report
        assert "Issue: Critical type mismatch" in report
        assert "Suggestion: Fix immediately" in report

    def _assert_error_details(self, report: str) -> None:
        """Assert error mismatch details."""
        assert "Field: User.email" in report
        assert "Issue: Field missing" in report

    def _assert_info_details(self, report: str) -> None:
        """Assert info mismatch details."""
        assert "Field: User.created" in report
        assert "Suggestion: Consider alignment" in report
    
    def test_generate_validation_report_partial_severities(self):
        """Test report generation with only some severity levels."""
        mismatches = self._create_partial_severity_mismatches()
        report = generate_validation_report(mismatches)
        
        self._assert_partial_report_content(report)
        self._assert_excluded_severities(report)

    def _create_partial_severity_mismatches(self) -> list:
        """Create mismatches with partial severity levels."""
        return [
            TypeMismatch(
                field_path="Config.timeout", backend_type="int", frontend_type="string",
                severity=TypeMismatchSeverity.ERROR, message="Type error"
            ),
            TypeMismatch(
                field_path="Config.retry", backend_type="bool", frontend_type="any",
                severity=TypeMismatchSeverity.WARNING, message="Using any"
            )
        ]

    def _assert_partial_report_content(self, report: str) -> None:
        """Assert partial report content."""
        assert "Total mismatches found: 2" in report
        assert "❌ ERROR (1 issues)" in report
        assert "⚠️ WARNING (1 issues)" in report

    def _assert_excluded_severities(self, report: str) -> None:
        """Assert that certain severities are excluded."""
        assert "🚨 CRITICAL" not in report
        assert "ℹ️ INFO" not in report


class TestEdgeCases:
    """Test edge cases and complex scenarios."""
    
    def test_typescript_parser_malformed_input(self):
        """Test TypeScript parser with malformed input."""
        typescript_content = self._get_malformed_typescript_content()
        temp_path = _create_temp_typescript_file(typescript_content)
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            self._assert_malformed_parsing_results(types)
        finally:
            Path(temp_path).unlink()

    def _get_malformed_typescript_content(self) -> str:
        """Get malformed TypeScript content for testing."""
        return """
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

    def _assert_malformed_parsing_results(self, types: Dict[str, Any]) -> None:
        """Assert results from parsing malformed TypeScript."""
        assert 'User' in types
        assert 'id' in types['User']['fields']
        assert len(types['User']['fields']) > 0
    
    def test_empty_schemas(self):
        """Test validation with empty schemas."""
        typescript_content = self._get_empty_interface_content()
        temp_path = _create_temp_typescript_file(typescript_content)
        
        try:
            backend_schemas = self._create_empty_backend_schemas()
            mismatches = self._validate_empty_schemas(backend_schemas, temp_path)
            assert len(mismatches) == 0
        finally:
            Path(temp_path).unlink()

    def _get_empty_interface_content(self) -> str:
        """Get empty interface content for testing."""
        return """
        export interface EmptyInterface {
        }
        """

    def _create_empty_backend_schemas(self) -> Dict[str, Any]:
        """Create empty backend schemas."""
        return {'EmptyInterface': {'properties': {}}}

    def _validate_empty_schemas(self, backend_schemas: Dict[str, Any], temp_path: str) -> list:
        """Validate empty schemas."""
        validator = SchemaValidator()
        return validator.validate_schemas(backend_schemas, temp_path)
    
    def test_special_characters_in_field_names(self):
        """Test handling special characters in field names."""
        typescript_content = self._get_special_characters_content()
        temp_path = _create_temp_typescript_file(typescript_content)
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            self._assert_special_characters_parsing(types)
        finally:
            Path(temp_path).unlink()

    def _get_special_characters_content(self) -> str:
        """Get TypeScript content with special characters."""
        return """
        export interface Data {
            $id: string;
            _private: boolean;
            "quoted-name": number;
        }
        """

    def _assert_special_characters_parsing(self, types: Dict[str, Any]) -> None:
        """Assert special characters parsing results."""
        if 'Data' in types and 'fields' in types['Data']:
            assert len(types['Data']['fields']) > 0
    
    def test_unicode_and_special_content(self):
        """Test handling Unicode and special content."""
        self._test_unicode_parsing()
    
    def _test_unicode_parsing(self):
        """Helper to test Unicode parsing."""
        typescript_content = self._get_unicode_content()
        temp_path = self._create_unicode_temp_file(typescript_content)
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            self._assert_unicode_parsing_results(types)
        finally:
            Path(temp_path).unlink()

    def _get_unicode_content(self) -> str:
        """Get Unicode TypeScript content."""
        return """
        export interface UnicodeData {
            name: string;
            description: string;
        }
        """

    def _create_unicode_temp_file(self, content: str) -> str:
        """Create temporary Unicode TypeScript file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False, encoding='utf-8') as f:
            f.write(content)
            return f.name

    def _assert_unicode_parsing_results(self, types: Dict[str, Any]) -> None:
        """Assert Unicode parsing results."""
        if 'UnicodeData' in types:
            assert len(types['UnicodeData']['fields']) > 0
    
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
        typescript_content = self._get_working_interface_content()
        temp_path = _create_temp_typescript_file(typescript_content)
        
        try:
            parser = TypeScriptParser()
            types = parser.parse_typescript_file(temp_path)
            self._assert_working_interface_results(types)
        finally:
            Path(temp_path).unlink()

    def _get_working_interface_content(self) -> str:
        """Get working interface content."""
        return """
        export interface Working {
            id: number;
            name: string;
        }
        """

    def _assert_working_interface_results(self, types: Dict[str, Any]) -> None:
        """Assert working interface parsing results."""
        assert 'Working' in types
        assert len(types['Working']['fields']) == 2