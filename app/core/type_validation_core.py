"""Core type validation functionality and schema validation."""

from typing import Any, Dict, List

from .type_validation_errors import TypeMismatch, TypeMismatchSeverity
from .type_validation_helpers import TypeScriptParser, get_backend_field_type
from .type_validation_rules import TypeCompatibilityChecker


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
        mismatches.extend(_validate_backend_schemas(
            backend_schemas, frontend_types, self.compat_checker
        ))
        
        # Check for extra schemas in frontend
        mismatches.extend(_validate_frontend_schemas(frontend_types, backend_schemas))
        
        return mismatches


def validate_type_consistency(
    backend_schemas: Dict[str, Dict[str, Any]],
    frontend_types_file: str
) -> List[TypeMismatch]:
    """Validate type consistency between backend schemas and frontend types."""
    
    validator = SchemaValidator()
    return validator.validate_schemas(backend_schemas, frontend_types_file)


def _validate_backend_schemas(
    backend_schemas: Dict[str, Dict[str, Any]], 
    frontend_types: Dict[str, Dict[str, Any]],
    compat_checker: TypeCompatibilityChecker
) -> List[TypeMismatch]:
    """Validate backend schemas against frontend types."""
    mismatches = []
    
    for schema_name, backend_schema in backend_schemas.items():
        if schema_name not in frontend_types:
            mismatches.append(_create_missing_schema_mismatch(schema_name, "frontend"))
            continue
        
        frontend_type = frontend_types[schema_name]
        
        # Only validate interfaces (not type aliases)
        if frontend_type.get('type') != 'interface':
            continue
        
        # Check fields
        mismatches.extend(_validate_schema_fields(
            schema_name, backend_schema, frontend_type, compat_checker
        ))
    
    return mismatches


def _validate_frontend_schemas(
    frontend_types: Dict[str, Dict[str, Any]], 
    backend_schemas: Dict[str, Dict[str, Any]]
) -> List[TypeMismatch]:
    """Validate frontend schemas against backend schemas."""
    mismatches = []
    
    for schema_name in frontend_types:
        if schema_name not in backend_schemas:
            mismatches.append(_create_missing_schema_mismatch(schema_name, "backend"))
    
    return mismatches


def _validate_schema_fields(
    schema_name: str,
    backend_schema: Dict[str, Any],
    frontend_type: Dict[str, Any],
    compat_checker: TypeCompatibilityChecker
) -> List[TypeMismatch]:
    """Validate fields between backend schema and frontend type."""
    mismatches = []
    
    backend_properties = backend_schema.get('properties', {})
    frontend_fields = frontend_type.get('fields', {})
    
    # Check for missing fields in frontend
    mismatches.extend(_check_missing_frontend_fields(
        schema_name, backend_properties, frontend_fields
    ))
    
    # Check type compatibility for existing fields
    mismatches.extend(_check_field_type_compatibility(
        schema_name, backend_properties, frontend_fields, compat_checker
    ))
    
    # Check for extra fields in frontend
    mismatches.extend(_check_extra_frontend_fields(
        schema_name, backend_properties, frontend_fields
    ))
    
    return mismatches


def _check_missing_frontend_fields(
    schema_name: str,
    backend_properties: Dict[str, Any],
    frontend_fields: Dict[str, Any]
) -> List[TypeMismatch]:
    """Check for fields missing in frontend."""
    mismatches = []
    
    for field_name, field_schema in backend_properties.items():
        if field_name not in frontend_fields:
            field_path = f"{schema_name}.{field_name}"
            mismatches.append(TypeMismatch(
                field_path=field_path,
                backend_type=field_schema.get('type', 'unknown'),
                frontend_type="missing",
                severity=TypeMismatchSeverity.WARNING,
                message=f"Field {field_name} exists in backend but not in frontend"
            ))
    
    return mismatches


def _check_field_type_compatibility(
    schema_name: str,
    backend_properties: Dict[str, Any],
    frontend_fields: Dict[str, Any],
    compat_checker: TypeCompatibilityChecker
) -> List[TypeMismatch]:
    """Check type compatibility for existing fields."""
    mismatches = []
    
    for field_name, field_schema in backend_properties.items():
        if field_name not in frontend_fields:
            continue
        
        field_path = f"{schema_name}.{field_name}"
        backend_field_type = get_backend_field_type(field_schema)
        frontend_field = frontend_fields[field_name]
        frontend_field_type = frontend_field.get('type', 'unknown')
        
        mismatch = compat_checker.check_field_compatibility(
            backend_field_type,
            frontend_field_type,
            field_path
        )
        
        if mismatch:
            mismatches.append(mismatch)
    
    return mismatches


def _check_extra_frontend_fields(
    schema_name: str,
    backend_properties: Dict[str, Any],
    frontend_fields: Dict[str, Any]
) -> List[TypeMismatch]:
    """Check for extra fields in frontend."""
    mismatches = []
    
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
    
    return mismatches


def _create_missing_schema_mismatch(schema_name: str, missing_in: str) -> TypeMismatch:
    """Create mismatch for missing schema."""
    if missing_in == "frontend":
        return TypeMismatch(
            field_path=schema_name,
            backend_type="schema",
            frontend_type="missing",
            severity=TypeMismatchSeverity.ERROR,
            message=f"Schema {schema_name} exists in backend but not in frontend"
        )
    else:
        return TypeMismatch(
            field_path=schema_name,
            backend_type="missing",
            frontend_type="schema",
            severity=TypeMismatchSeverity.INFO,
            message=f"Schema {schema_name} exists in frontend but not in backend"
        )