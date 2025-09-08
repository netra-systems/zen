"""Type validation utilities for ensuring frontend-backend consistency."""

from typing import Any, Dict, List

from netra_backend.app.core.type_validation_core import (
    SchemaValidator,
    validate_type_consistency,
)

# Import all components from new modules
from netra_backend.app.core.type_validation_errors import (
    TypeMismatch,
    TypeMismatchSeverity,
    generate_validation_report,
)
from netra_backend.app.core.type_validation_helpers import (
    TypeScriptParser,
    get_backend_field_type,
)
from netra_backend.app.core.type_validation_rules import TypeCompatibilityChecker
from netra_backend.app.core.input_validators import EnhancedInputValidator

# Create TypeValidator alias for backward compatibility
TypeValidator = EnhancedInputValidator

# Re-export main functions for backward compatibility
__all__ = [
    'TypeMismatch',
    'TypeMismatchSeverity', 
    'TypeScriptParser',
    'TypeCompatibilityChecker',
    'SchemaValidator',
    'validate_type_consistency',
    'generate_validation_report',
    'get_backend_field_type',
    'TypeValidator'
]