"""Type validation helper functions and TypeScript parsing utilities."""

import re
from typing import Any, Dict

from .exceptions_config import ValidationError as NetraValidationError
from .error_context import ErrorContext


class TypeScriptParser:
    """Parses TypeScript type definitions."""
    
    def __init__(self):
        self.interface_pattern = re.compile(
            r'export interface (\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        )
        self.type_pattern = re.compile(r'export type (\w+)\s*=\s*([^;]+);')
        self.field_pattern = re.compile(r'(\w+)(\??)\s*:\s*([^;,}]+)[;,]?')
    
    def parse_typescript_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Parse TypeScript file and extract type definitions."""
        try:
            content = _read_file_content(file_path)
            types = _parse_typescript_content(content, self.interface_pattern, 
                                            self.type_pattern, self._parse_interface_fields)
            return types
        except Exception as e:
            raise NetraValidationError(
                message=f"Failed to parse TypeScript file {file_path}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def _parse_interface_fields(self, interface_body: str) -> Dict[str, Dict[str, Any]]:
        """Parse interface fields from interface body."""
        fields = {}
        cleaned_body = _clean_interface_body(interface_body)
        for match in self.field_pattern.finditer(cleaned_body):
            field_data = _extract_field_data(match)
            fields[field_data['name']] = {
                'type': field_data['type'],
                'optional': field_data['optional']
            }
        return fields


def _read_file_content(file_path: str) -> str:
    """Read and return file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def _parse_interfaces(content: str, pattern: re.Pattern, field_parser) -> Dict[str, Dict[str, Any]]:
    """Parse all interfaces from content."""
    interfaces = {}
    for match in pattern.finditer(content):
        interface_name = match.group(1)
        interface_body = match.group(2)
        fields = field_parser(interface_body)
        interfaces[interface_name] = {'type': 'interface', 'fields': fields}
    return interfaces


def _parse_type_aliases(content: str, pattern: re.Pattern) -> Dict[str, Dict[str, Any]]:
    """Parse all type aliases from content."""
    aliases = {}
    for match in pattern.finditer(content):
        type_name = match.group(1)
        type_def = match.group(2).strip()
        aliases[type_name] = {'type': 'alias', 'definition': type_def}
    return aliases


def _clean_interface_body(interface_body: str) -> str:
    """Remove comments and clean up interface body."""
    # Remove block comments
    cleaned = re.sub(r'/\*\*[^*]*\*+(?:[^/*][^*]*\*+)*/', '', interface_body)
    # Remove line comments
    cleaned = re.sub(r'//.*', '', cleaned)
    return cleaned


def _extract_field_data(match: re.Match) -> Dict[str, Any]:
    """Extract field data from regex match."""
    return {
        'name': match.group(1),
        'optional': bool(match.group(2)),
        'type': match.group(3).strip()
    }


def get_backend_field_type(field_schema: Dict[str, Any]) -> str:
    """Extract type information from backend field schema."""
    field_type = field_schema.get('type')
    if field_type:
        return field_type
    if '$ref' in field_schema:
        return _handle_ref_type(field_schema['$ref'])
    if 'items' in field_schema:
        return _handle_array_type(field_schema['items'])
    if 'anyOf' in field_schema:
        return _handle_union_types(field_schema['anyOf'])
    return 'unknown'


def _handle_union_types(union_schemas: list) -> str:
    """Handle union type schemas."""
    union_types = []
    for union_schema in union_schemas:
        union_type = get_backend_field_type(union_schema)
        union_types.append(union_type)
    return f"Union[{', '.join(union_types)}]"


def _parse_typescript_content(
    content: str, interface_pattern: re.Pattern, 
    type_pattern: re.Pattern, field_parser
) -> Dict[str, Dict[str, Any]]:
    """Parse TypeScript content and return type definitions."""
    types = {}
    types.update(_parse_interfaces(content, interface_pattern, field_parser))
    types.update(_parse_type_aliases(content, type_pattern))
    return types


def _handle_ref_type(ref: str) -> str:
    """Handle reference type extraction."""
    if ref.startswith('#/definitions/'):
        return ref[14:]  # Remove '#/definitions/'
    return ref


def _handle_array_type(items_schema: Dict[str, Any]) -> str:
    """Handle array type extraction."""
    item_type = get_backend_field_type(items_schema)
    return f"List[{item_type}]"