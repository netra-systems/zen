"""Core type validation functionality and schema validation."""

from typing import Any, Dict, List

from netra_backend.app.core.type_validation_errors import TypeMismatch, TypeMismatchSeverity
from netra_backend.app.core.type_validation_helpers import TypeScriptParser, get_backend_field_type
from netra_backend.app.core.type_validation_rules import TypeCompatibilityChecker


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
        frontend_types = self.ts_parser.parse_typescript_file(frontend_types_file)
        return _perform_validation_checks(self, backend_schemas, frontend_types)


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
        mismatches.extend(_validate_single_backend_schema(
            schema_name, backend_schema, frontend_types, compat_checker
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
    backend_properties = backend_schema.get('properties', {})
    frontend_fields = frontend_type.get('fields', {})
    return _perform_all_field_checks(
        schema_name, backend_properties, frontend_fields, compat_checker
    )


def _check_missing_frontend_fields(
    schema_name: str,
    backend_properties: Dict[str, Any],
    frontend_fields: Dict[str, Any]
) -> List[TypeMismatch]:
    """Check for fields missing in frontend."""
    mismatches = []
    for field_name, field_schema in backend_properties.items():
        if field_name not in frontend_fields:
            mismatches.append(_create_missing_field_mismatch(
                schema_name, field_name, field_schema, "frontend"
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
        if field_name in frontend_fields:
            mismatch = _check_single_field_compatibility(
                schema_name, field_name, field_schema, frontend_fields, compat_checker
            )
            _append_mismatch_if_exists(mismatches, mismatch)
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
            mismatches.append(_create_extra_field_mismatch(
                schema_name, field_name, frontend_fields[field_name]
            ))
    return mismatches


def _create_missing_schema_mismatch(schema_name: str, missing_in: str) -> TypeMismatch:
    """Create mismatch for missing schema."""
    if missing_in == "frontend":
        return _create_frontend_missing_mismatch(schema_name)
    else:
        return _create_backend_missing_mismatch(schema_name)


def _validate_single_backend_schema(
    schema_name: str, backend_schema: Dict[str, Any], 
    frontend_types: Dict[str, Dict[str, Any]], compat_checker: TypeCompatibilityChecker
) -> List[TypeMismatch]:
    """Validate a single backend schema against frontend types."""
    if schema_name not in frontend_types:
        return [_create_missing_schema_mismatch(schema_name, "frontend")]
    return _validate_existing_frontend_schema(schema_name, backend_schema, frontend_types, compat_checker)


def _validate_existing_frontend_schema(
    schema_name: str, backend_schema: Dict[str, Any],
    frontend_types: Dict[str, Dict[str, Any]], compat_checker: TypeCompatibilityChecker
) -> List[TypeMismatch]:
    """Validate schema when frontend type exists."""
    frontend_type = frontend_types[schema_name]
    if frontend_type.get('type') != 'interface':
        return []
    return _validate_schema_fields(schema_name, backend_schema, frontend_type, compat_checker)


def _perform_all_field_checks(
    schema_name: str, backend_properties: Dict[str, Any],
    frontend_fields: Dict[str, Any], compat_checker: TypeCompatibilityChecker
) -> List[TypeMismatch]:
    """Perform all field validation checks."""
    missing_checks = _check_missing_frontend_fields(schema_name, backend_properties, frontend_fields)
    compat_checks = _check_field_type_compatibility(schema_name, backend_properties, frontend_fields, compat_checker)
    extra_checks = _check_extra_frontend_fields(schema_name, backend_properties, frontend_fields)
    return _combine_validation_results(missing_checks, compat_checks, extra_checks)


def _combine_validation_results(
    missing_checks: List[TypeMismatch], compat_checks: List[TypeMismatch], extra_checks: List[TypeMismatch]
) -> List[TypeMismatch]:
    """Combine all validation check results."""
    return missing_checks + compat_checks + extra_checks


def _create_missing_field_mismatch(
    schema_name: str, field_name: str, field_schema: Dict[str, Any], missing_in: str
) -> TypeMismatch:
    """Create mismatch for missing field."""
    field_path = f"{schema_name}.{field_name}"
    backend_type = field_schema.get('type', 'unknown')
    message = f"Field {field_name} exists in backend but not in {missing_in}"
    return _build_missing_field_type_mismatch(field_path, backend_type, message)


def _build_missing_field_type_mismatch(field_path: str, backend_type: str, message: str) -> TypeMismatch:
    """Build TypeMismatch object for missing field."""
    return TypeMismatch(
        field_path=field_path, backend_type=backend_type, frontend_type="missing",
        severity=TypeMismatchSeverity.WARNING, message=message
    )


def _check_single_field_compatibility(
    schema_name: str, field_name: str, field_schema: Dict[str, Any],
    frontend_fields: Dict[str, Any], compat_checker: TypeCompatibilityChecker
):
    """Check compatibility for a single field."""
    field_path = f"{schema_name}.{field_name}"
    backend_field_type = get_backend_field_type(field_schema)
    frontend_field_type = _extract_frontend_field_type(frontend_fields, field_name)
    return compat_checker.check_field_compatibility(backend_field_type, frontend_field_type, field_path)


def _extract_frontend_field_type(frontend_fields: Dict[str, Any], field_name: str) -> str:
    """Extract frontend field type from fields dictionary."""
    frontend_field = frontend_fields[field_name]
    return frontend_field.get('type', 'unknown')


def _create_extra_field_mismatch(
    schema_name: str, field_name: str, frontend_field: Dict[str, Any]
) -> TypeMismatch:
    """Create mismatch for extra field in frontend."""
    field_path = f"{schema_name}.{field_name}"
    frontend_type = frontend_field.get('type', 'unknown')
    message = f"Field {field_name} exists in frontend but not in backend"
    return _build_extra_field_type_mismatch(field_path, frontend_type, message)


def _build_extra_field_type_mismatch(field_path: str, frontend_type: str, message: str) -> TypeMismatch:
    """Build TypeMismatch object for extra field."""
    return TypeMismatch(
        field_path=field_path, backend_type="missing", frontend_type=frontend_type,
        severity=TypeMismatchSeverity.INFO, message=message
    )


def _perform_validation_checks(
    validator_instance, backend_schemas: Dict[str, Dict[str, Any]],
    frontend_types: Dict[str, Dict[str, Any]]
) -> List[TypeMismatch]:
    """Perform both backend and frontend validation checks."""
    backend_mismatches = _validate_backend_schemas(
        backend_schemas, frontend_types, validator_instance.compat_checker
    )
    frontend_mismatches = _validate_frontend_schemas(frontend_types, backend_schemas)
    return backend_mismatches + frontend_mismatches


def _create_frontend_missing_mismatch(schema_name: str) -> TypeMismatch:
    """Create mismatch for schema missing in frontend."""
    message = f"Schema {schema_name} exists in backend but not in frontend"
    return _build_schema_missing_type_mismatch(
        schema_name, "schema", "missing", TypeMismatchSeverity.ERROR, message
    )


def _build_schema_missing_type_mismatch(
    field_path: str, backend_type: str, frontend_type: str, severity: TypeMismatchSeverity, message: str
) -> TypeMismatch:
    """Build TypeMismatch object for missing schema."""
    return TypeMismatch(
        field_path=field_path, backend_type=backend_type, frontend_type=frontend_type,
        severity=severity, message=message
    )


def _create_backend_missing_mismatch(schema_name: str) -> TypeMismatch:
    """Create mismatch for schema missing in backend."""
    message = f"Schema {schema_name} exists in frontend but not in backend"
    return _build_schema_missing_type_mismatch(
        schema_name, "missing", "schema", TypeMismatchSeverity.INFO, message
    )


def _append_mismatch_if_exists(mismatches: List[TypeMismatch], mismatch) -> None:
    """Append mismatch to list if it exists."""
    if mismatch:
        mismatches.append(mismatch)