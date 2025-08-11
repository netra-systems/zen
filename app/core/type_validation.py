"""Type validation utilities for ensuring frontend-backend consistency."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ValidationError

from .exceptions import ValidationError as NetraValidationError
from .error_context import ErrorContext


class TypeMismatchSeverity(Enum):
    """Severity levels for type mismatches."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TypeMismatch:
    """Represents a type mismatch between frontend and backend."""
    field_path: str
    backend_type: str
    frontend_type: str
    severity: TypeMismatchSeverity
    message: str
    suggestion: Optional[str] = None


class TypeScriptParser:
    """Parses TypeScript type definitions."""
    
    def __init__(self):
        self.interface_pattern = re.compile(r'export interface (\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}')
        self.type_pattern = re.compile(r'export type (\w+)\s*=\s*([^;]+);')
        self.field_pattern = re.compile(r'(\w+)(\??)\s*:\s*([^;,}]+)[;,]?')
    
    def parse_typescript_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Parse TypeScript file and extract type definitions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            types = {}
            
            # Parse interfaces
            for match in self.interface_pattern.finditer(content):
                interface_name = match.group(1)
                interface_body = match.group(2)
                
                fields = self._parse_interface_fields(interface_body)
                types[interface_name] = {
                    'type': 'interface',
                    'fields': fields
                }
            
            # Parse type aliases
            for match in self.type_pattern.finditer(content):
                type_name = match.group(1)
                type_def = match.group(2).strip()
                
                types[type_name] = {
                    'type': 'alias',
                    'definition': type_def
                }
            
            return types
            
        except Exception as e:
            raise NetraValidationError(
                message=f"Failed to parse TypeScript file {file_path}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def _parse_interface_fields(self, interface_body: str) -> Dict[str, Dict[str, Any]]:
        """Parse interface fields from interface body."""
        fields = {}
        
        # Remove comments and clean up
        cleaned_body = re.sub(r'/\*\*[^*]*\*+(?:[^/*][^*]*\*+)*/', '', interface_body)
        cleaned_body = re.sub(r'//.*', '', cleaned_body)
        
        for match in self.field_pattern.finditer(cleaned_body):
            field_name = match.group(1)
            is_optional = bool(match.group(2))
            field_type = match.group(3).strip()
            
            fields[field_name] = {
                'type': field_type,
                'optional': is_optional
            }
        
        return fields


class TypeCompatibilityChecker:
    """Checks type compatibility between backend and frontend."""
    
    def __init__(self):
        self.type_mappings = {
            # Python -> TypeScript mappings
            'str': 'string',
            'int': 'number',
            'float': 'number',
            'bool': 'boolean',
            'datetime': 'string',  # Usually serialized as ISO string
            'date': 'string',
            'UUID': 'string',
            'Any': 'any',
            'Dict': 'Record<string, any>',
            'List': 'Array',
        }
    
    def check_field_compatibility(
        self, 
        backend_type: str, 
        frontend_type: str,
        field_path: str
    ) -> Optional[TypeMismatch]:
        """Check if backend and frontend types are compatible."""
        
        # Normalize types
        normalized_backend = self._normalize_backend_type(backend_type)
        normalized_frontend = self._normalize_frontend_type(frontend_type)
        
        # Direct match
        if normalized_backend == normalized_frontend:
            return None
        
        # Check for compatible types
        if self._are_types_compatible(normalized_backend, normalized_frontend):
            return None
        
        # Determine severity
        severity = self._determine_mismatch_severity(normalized_backend, normalized_frontend)
        
        # Generate suggestion
        suggestion = self._generate_type_suggestion(normalized_backend, normalized_frontend)
        
        return TypeMismatch(
            field_path=field_path,
            backend_type=backend_type,
            frontend_type=frontend_type,
            severity=severity,
            message=f"Type mismatch: backend expects {backend_type}, frontend has {frontend_type}",
            suggestion=suggestion
        )
    
    def _normalize_backend_type(self, backend_type: str) -> str:
        """Normalize backend type for comparison."""
        # Handle Optional types
        if backend_type.startswith('Optional[') and backend_type.endswith(']'):
            inner_type = backend_type[9:-1]
            return self._normalize_backend_type(inner_type)
        
        # Handle Union types
        if backend_type.startswith('Union[') and backend_type.endswith(']'):
            # For now, just take the first type
            inner_types = backend_type[6:-1]
            first_type = inner_types.split(',')[0].strip()
            return self._normalize_backend_type(first_type)
        
        # Handle List/Array types
        if backend_type.startswith('List[') and backend_type.endswith(']'):
            inner_type = backend_type[5:-1]
            return f'Array<{self._normalize_backend_type(inner_type)}>'
        
        # Handle Dict types
        if backend_type.startswith('Dict[') and backend_type.endswith(']'):
            return 'Record<string, any>'
        
        # Apply basic mappings
        return self.type_mappings.get(backend_type, backend_type)
    
    def _normalize_frontend_type(self, frontend_type: str) -> str:
        """Normalize frontend type for comparison."""
        # Remove extra whitespace
        return frontend_type.strip()
    
    def _are_types_compatible(self, backend_type: str, frontend_type: str) -> bool:
        """Check if two normalized types are compatible."""
        
        # Exact match
        if backend_type == frontend_type:
            return True
        
        # Any type is compatible with everything
        if backend_type == 'any' or frontend_type == 'any':
            return True
        
        # Number compatibility
        if backend_type == 'number' and frontend_type in ['number', 'integer']:
            return True
        
        # String compatibility (including dates)
        if backend_type == 'string' and frontend_type in ['string', 'Date']:
            return True
        
        # Array compatibility
        if (backend_type.startswith('Array<') or backend_type.endswith('[]')) and \
           (frontend_type.startswith('Array<') or frontend_type.endswith('[]')):
            return True
        
        # Object/Record compatibility
        if ('Record<' in backend_type or backend_type.startswith('{')) and \
           ('Record<' in frontend_type or frontend_type.startswith('{')):
            return True
        
        return False
    
    def _determine_mismatch_severity(self, backend_type: str, frontend_type: str) -> TypeMismatchSeverity:
        """Determine the severity of a type mismatch."""
        
        # Critical: Completely incompatible types
        critical_mismatches = [
            ('string', 'number'),
            ('boolean', 'string'),
            ('Array', 'string'),
            ('object', 'string'),
        ]
        
        for backend_pattern, frontend_pattern in critical_mismatches:
            if backend_pattern in backend_type and frontend_pattern in frontend_type:
                return TypeMismatchSeverity.CRITICAL
        
        # Error: Likely to cause runtime issues
        if (backend_type in ['string', 'number', 'boolean'] and 
            frontend_type not in ['string', 'number', 'boolean', 'any']):
            return TypeMismatchSeverity.ERROR
        
        # Warning: May cause issues
        if 'any' in frontend_type and backend_type != 'any':
            return TypeMismatchSeverity.WARNING
        
        # Info: Minor differences
        return TypeMismatchSeverity.INFO
    
    def _generate_type_suggestion(self, backend_type: str, frontend_type: str) -> Optional[str]:
        """Generate a suggestion for fixing the type mismatch."""
        
        if backend_type == 'string' and frontend_type == 'number':
            return "Convert to string or update backend to expect number"
        
        if backend_type == 'number' and frontend_type == 'string':
            return "Convert to number or update backend to expect string"
        
        if 'any' in frontend_type and backend_type != 'any':
            return f"Replace 'any' with '{backend_type}' for better type safety"
        
        if backend_type.startswith('Array<') and not frontend_type.endswith('[]'):
            return f"Change frontend type to array: {backend_type}"
        
        return f"Update frontend type to match backend: {backend_type}"


class SchemaValidator:
    """Validates schemas for consistency between backend and frontend."""
    
    def __init__(self):
        self.ts_parser = TypeScriptParser()
        self.compat_checker = TypeCompatibilityChecker()
    
    def validate_schemas(
        self, 
        backend_schemas: Dict[str, Dict[str, Any]],
        frontend_types_file: str
    ) -> List[TypeMismatch]:
        """Validate schemas for consistency."""
        
        # Parse frontend types
        frontend_types = self.ts_parser.parse_typescript_file(frontend_types_file)
        
        mismatches = []
        
        # Check each backend schema
        for schema_name, backend_schema in backend_schemas.items():
            if schema_name not in frontend_types:
                mismatches.append(TypeMismatch(
                    field_path=schema_name,
                    backend_type="schema",
                    frontend_type="missing",
                    severity=TypeMismatchSeverity.ERROR,
                    message=f"Schema {schema_name} exists in backend but not in frontend"
                ))
                continue
            
            frontend_type = frontend_types[schema_name]
            
            # Only validate interfaces (not type aliases)
            if frontend_type.get('type') != 'interface':
                continue
            
            # Check fields
            backend_properties = backend_schema.get('properties', {})
            frontend_fields = frontend_type.get('fields', {})
            
            # Check for missing fields in frontend
            for field_name, field_schema in backend_properties.items():
                field_path = f"{schema_name}.{field_name}"
                
                if field_name not in frontend_fields:
                    mismatches.append(TypeMismatch(
                        field_path=field_path,
                        backend_type=field_schema.get('type', 'unknown'),
                        frontend_type="missing",
                        severity=TypeMismatchSeverity.WARNING,
                        message=f"Field {field_name} exists in backend but not in frontend"
                    ))
                    continue
                
                # Check type compatibility
                backend_field_type = self._get_backend_field_type(field_schema)
                frontend_field = frontend_fields[field_name]
                frontend_field_type = frontend_field.get('type', 'unknown')
                
                mismatch = self.compat_checker.check_field_compatibility(
                    backend_field_type,
                    frontend_field_type,
                    field_path
                )
                
                if mismatch:
                    mismatches.append(mismatch)
            
            # Check for extra fields in frontend
            for field_name in frontend_fields:
                if field_name not in backend_properties:
                    field_path = f"{schema_name}.{field_name}"
                    mismatches.append(TypeMismatch(
                        field_path=field_path,
                        backend_type="missing",
                        frontend_type=frontend_fields[field_name].get('type', 'unknown'),
                        severity=TypeMismatchSeverity.INFO,
                        message=f"Field {field_name} exists in frontend but not in backend"
                    ))
        
        # Check for extra schemas in frontend
        for schema_name in frontend_types:
            if schema_name not in backend_schemas:
                mismatches.append(TypeMismatch(
                    field_path=schema_name,
                    backend_type="missing",
                    frontend_type="schema",
                    severity=TypeMismatchSeverity.INFO,
                    message=f"Schema {schema_name} exists in frontend but not in backend"
                ))
        
        return mismatches
    
    def _get_backend_field_type(self, field_schema: Dict[str, Any]) -> str:
        """Extract type information from backend field schema."""
        field_type = field_schema.get('type')
        
        if field_type:
            return field_type
        
        # Handle references
        if '$ref' in field_schema:
            ref = field_schema['$ref']
            if ref.startswith('#/definitions/'):
                return ref[14:]  # Remove '#/definitions/'
        
        # Handle arrays
        if 'items' in field_schema:
            item_type = self._get_backend_field_type(field_schema['items'])
            return f"List[{item_type}]"
        
        # Handle unions
        if 'anyOf' in field_schema:
            union_types = []
            for union_schema in field_schema['anyOf']:
                union_type = self._get_backend_field_type(union_schema)
                union_types.append(union_type)
            return f"Union[{', '.join(union_types)}]"
        
        return 'unknown'


def validate_type_consistency(
    backend_schemas: Dict[str, Dict[str, Any]],
    frontend_types_file: str
) -> List[TypeMismatch]:
    """Validate type consistency between backend schemas and frontend types."""
    
    validator = SchemaValidator()
    return validator.validate_schemas(backend_schemas, frontend_types_file)


def generate_validation_report(mismatches: List[TypeMismatch]) -> str:
    """Generate a human-readable validation report."""
    
    if not mismatches:
        return "✅ All type validations passed! Frontend and backend schemas are consistent."
    
    # Group by severity
    by_severity = {}
    for mismatch in mismatches:
        severity = mismatch.severity
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(mismatch)
    
    report_lines = [
        "Type Validation Report",
        "=" * 50,
        f"Total mismatches found: {len(mismatches)}",
        ""
    ]
    
    # Report by severity
    for severity in [TypeMismatchSeverity.CRITICAL, TypeMismatchSeverity.ERROR, 
                     TypeMismatchSeverity.WARNING, TypeMismatchSeverity.INFO]:
        
        if severity not in by_severity:
            continue
        
        severity_mismatches = by_severity[severity]
        icon = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}[severity.value]
        
        report_lines.extend([
            f"{icon} {severity.value.upper()} ({len(severity_mismatches)} issues)",
            "-" * 30
        ])
        
        for mismatch in severity_mismatches:
            report_lines.extend([
                f"Field: {mismatch.field_path}",
                f"Backend: {mismatch.backend_type}",
                f"Frontend: {mismatch.frontend_type}",
                f"Issue: {mismatch.message}"
            ])
            
            if mismatch.suggestion:
                report_lines.append(f"Suggestion: {mismatch.suggestion}")
            
            report_lines.append("")
    
    return "\n".join(report_lines)