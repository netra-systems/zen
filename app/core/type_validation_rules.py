"""Type compatibility checking rules and validation logic."""

from typing import Optional

from .type_validation_errors import TypeMismatch, TypeMismatchSeverity


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
        if _are_types_compatible(normalized_backend, normalized_frontend):
            return None
        
        # Create mismatch
        return _create_type_mismatch(
            field_path, backend_type, frontend_type, 
            normalized_backend, normalized_frontend
        )
    
    def _normalize_backend_type(self, backend_type: str) -> str:
        """Normalize backend type for comparison."""
        # Handle Optional types
        if backend_type.startswith('Optional[') and backend_type.endswith(']'):
            inner_type = backend_type[9:-1]
            return self._normalize_backend_type(inner_type)
        
        # Handle Union types
        if backend_type.startswith('Union[') and backend_type.endswith(']'):
            return _handle_union_type(backend_type, self._normalize_backend_type)
        
        # Handle List/Array types
        if backend_type.startswith('List[') and backend_type.endswith(']'):
            return _handle_list_type(backend_type, self._normalize_backend_type)
        
        # Handle Dict types
        if backend_type.startswith('Dict[') and backend_type.endswith(']'):
            return 'Record<string, any>'
        
        # Apply basic mappings
        return self.type_mappings.get(backend_type, backend_type)
    
    def _normalize_frontend_type(self, frontend_type: str) -> str:
        """Normalize frontend type for comparison."""
        # Remove extra whitespace
        return frontend_type.strip()


def _are_types_compatible(backend_type: str, frontend_type: str) -> bool:
    """Check if two normalized types are compatible."""
    # Exact match or any type
    if backend_type == frontend_type or 'any' in [backend_type, frontend_type]:
        return True
    # Check specific type compatibilities
    return (_check_number_compatibility(backend_type, frontend_type) or
            _check_string_compatibility(backend_type, frontend_type) or
            _are_array_types_compatible(backend_type, frontend_type) or
            _are_object_types_compatible(backend_type, frontend_type))


def _check_number_compatibility(backend_type: str, frontend_type: str) -> bool:
    """Check number type compatibility."""
    return backend_type == 'number' and frontend_type in ['number', 'integer']


def _check_string_compatibility(backend_type: str, frontend_type: str) -> bool:
    """Check string type compatibility."""
    return backend_type == 'string' and frontend_type in ['string', 'Date']


def _are_array_types_compatible(backend_type: str, frontend_type: str) -> bool:
    """Check if array types are compatible."""
    backend_is_array = backend_type.startswith('Array<') or backend_type.endswith('[]')
    frontend_is_array = frontend_type.startswith('Array<') or frontend_type.endswith('[]')
    return backend_is_array and frontend_is_array


def _are_object_types_compatible(backend_type: str, frontend_type: str) -> bool:
    """Check if object types are compatible."""
    backend_is_object = 'Record<' in backend_type or backend_type.startswith('{')
    frontend_is_object = 'Record<' in frontend_type or frontend_type.startswith('{')
    return backend_is_object and frontend_is_object


def _handle_union_type(backend_type: str, normalize_func) -> str:
    """Handle Union type normalization."""
    # For now, just take the first type
    inner_types = backend_type[6:-1]
    first_type = inner_types.split(',')[0].strip()
    return normalize_func(first_type)


def _handle_list_type(backend_type: str, normalize_func) -> str:
    """Handle List type normalization."""
    inner_type = backend_type[5:-1]
    return f'Array<{normalize_func(inner_type)}>'


def _create_type_mismatch(
    field_path: str, 
    backend_type: str, 
    frontend_type: str,
    normalized_backend: str, 
    normalized_frontend: str
) -> TypeMismatch:
    """Create a TypeMismatch object for incompatible types."""
    # Determine severity
    severity = _determine_mismatch_severity(normalized_backend, normalized_frontend)
    
    # Generate suggestion
    suggestion = _generate_type_suggestion(normalized_backend, normalized_frontend)
    
    return TypeMismatch(
        field_path=field_path,
        backend_type=backend_type,
        frontend_type=frontend_type,
        severity=severity,
        message=f"Type mismatch: backend expects {backend_type}, frontend has {frontend_type}",
        suggestion=suggestion
    )


def _determine_mismatch_severity(backend_type: str, frontend_type: str) -> TypeMismatchSeverity:
    """Determine the severity of a type mismatch."""
    
    # Critical: Completely incompatible types
    if _is_critical_mismatch(backend_type, frontend_type):
        return TypeMismatchSeverity.CRITICAL
    
    # Error: Likely to cause runtime issues
    if _is_error_mismatch(backend_type, frontend_type):
        return TypeMismatchSeverity.ERROR
    
    # Warning: May cause issues
    if _is_warning_mismatch(backend_type, frontend_type):
        return TypeMismatchSeverity.WARNING
    
    # Info: Minor differences
    return TypeMismatchSeverity.INFO


def _is_critical_mismatch(backend_type: str, frontend_type: str) -> bool:
    """Check if mismatch is critical severity."""
    critical_mismatches = [
        ('string', 'number'),
        ('boolean', 'string'),
        ('Array', 'string'),
        ('object', 'string'),
    ]
    
    for backend_pattern, frontend_pattern in critical_mismatches:
        if backend_pattern in backend_type and frontend_pattern in frontend_type:
            return True
    return False


def _is_error_mismatch(backend_type: str, frontend_type: str) -> bool:
    """Check if mismatch is error severity."""
    return (backend_type in ['string', 'number', 'boolean'] and 
            frontend_type not in ['string', 'number', 'boolean', 'any'])


def _is_warning_mismatch(backend_type: str, frontend_type: str) -> bool:
    """Check if mismatch is warning severity."""
    return 'any' in frontend_type and backend_type != 'any'


def _generate_type_suggestion(backend_type: str, frontend_type: str) -> Optional[str]:
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