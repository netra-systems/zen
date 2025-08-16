"""Mock response generators for LLM testing.

Contains mock functions for generating fake LLM responses during testing.
Each function must be ≤8 lines as per module architecture requirements.
"""
from typing import Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def create_mock_structured_response(schema: Type[T]) -> T:
    """Create mock structured response for testing."""
    mock_data = {}
    for field_name, field_info in schema.model_fields.items():
        if field_info.is_required():
            mock_data[field_name] = get_mock_value_for_field(field_info)
    return schema(**mock_data)


def get_mock_value_for_field(field_info: Any) -> Any:
    """Get mock value based on field type annotation."""
    annotation = field_info.annotation
    if annotation == str:
        return f"[Mock {field_info}]"
    elif annotation == float:
        return 0.5
    elif annotation == int:
        return 1
    elif annotation == bool:
        return False
    return get_complex_mock_value(annotation)


def get_complex_mock_value(annotation: Any) -> Any:
    """Handle complex field types for mock values."""
    if annotation == dict:
        return {}
    elif annotation == list:
        return []
    elif hasattr(annotation, '__origin__'):
        return handle_generic_type(annotation)
    return {}


def handle_generic_type(annotation: Any) -> Any:
    """Handle generic types like List, Dict, Optional."""
    origin = annotation.__origin__
    if origin == list:
        return []
    elif origin == dict:
        return {}
    return None