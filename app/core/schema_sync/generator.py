"""
TypeScript Generator

Generates TypeScript type definitions from schemas.
Maintains 8-line function limit and modular design.
"""

from typing import Dict, Any, List
from datetime import datetime, UTC
from app.core.exceptions_service import ServiceError
from app.core.error_context import ErrorContext
from .models import SchemaValidationLevel


class TypeScriptGenerator:
    """Generates TypeScript type definitions from schemas."""
    
    def __init__(self, validation_level: SchemaValidationLevel = SchemaValidationLevel.MODERATE):
        self._validation_level = validation_level
    
    def generate_typescript_interface(self, schema_name: str, schema: Dict[str, Any]) -> str:
        """Generate TypeScript interface from JSON schema."""
        try:
            properties = schema.get('properties', {})
            required = set(schema.get('required', []))
            
            interface_lines = [f"export interface {schema_name} {{"]
            interface_lines.extend(self._generate_property_lines(properties, required))
            interface_lines.append("}")
            
            return "\n".join(interface_lines)
            
        except Exception as e:
            raise ServiceError(
                message=f"Failed to generate TypeScript interface for {schema_name}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def generate_typescript_file(self, schemas: Dict[str, Dict[str, Any]]) -> str:
        """Generate complete TypeScript file from schemas."""
        lines = self._generate_file_header()
        lines.extend(self._generate_enums(schemas))
        lines.extend(self._generate_interfaces(schemas))
        
        return "\n".join(lines)
    
    def _generate_property_lines(self, properties: Dict[str, Any], required: set) -> List[str]:
        """Generate property lines for interface"""
        lines = []
        
        for field_name, field_schema in properties.items():
            field_type = self._convert_json_schema_type_to_typescript(field_schema)
            optional = "" if field_name in required else "?"
            
            if 'description' in field_schema:
                lines.append(f"  /** {field_schema['description']} */")
            
            lines.append(f"  {field_name}{optional}: {field_type};")
        
        return lines
    
    def _convert_json_schema_type_to_typescript(self, field_schema: Dict[str, Any]) -> str:
        """Convert JSON schema type to TypeScript type."""
        field_type = field_schema.get('type', 'any')
        
        if field_type == 'string':
            return self._handle_string_type(field_schema)
        elif field_type in ['number', 'integer']:
            return 'number'
        elif field_type == 'boolean':
            return 'boolean'
        elif field_type == 'array':
            return self._handle_array_type(field_schema)
        elif field_type == 'object':
            return self._handle_object_type(field_schema)
        elif 'anyOf' in field_schema:
            return self._handle_union_type(field_schema)
        else:
            return 'any'
    
    def _handle_string_type(self, field_schema: Dict[str, Any]) -> str:
        """Handle string type conversion"""
        if 'enum' in field_schema:
            enum_values = [f'"{value}"' for value in field_schema['enum']]
            return ' | '.join(enum_values)
        return 'string'
    
    def _handle_array_type(self, field_schema: Dict[str, Any]) -> str:
        """Handle array type conversion"""
        items_schema = field_schema.get('items', {})
        item_type = self._convert_json_schema_type_to_typescript(items_schema)
        return f'{item_type}[]'
    
    def _handle_object_type(self, field_schema: Dict[str, Any]) -> str:
        """Handle object type conversion"""
        if 'properties' in field_schema:
            properties = []
            required = set(field_schema.get('required', []))
            
            for prop_name, prop_schema in field_schema['properties'].items():
                prop_type = self._convert_json_schema_type_to_typescript(prop_schema)
                optional = "" if prop_name in required else "?"
                properties.append(f"{prop_name}{optional}: {prop_type}")
            
            return "{ " + "; ".join(properties) + " }"
        else:
            return 'Record<string, any>'
    
    def _handle_union_type(self, field_schema: Dict[str, Any]) -> str:
        """Handle union type conversion"""
        union_types = []
        for union_schema in field_schema['anyOf']:
            union_type = self._convert_json_schema_type_to_typescript(union_schema)
            union_types.append(union_type)
        return ' | '.join(union_types)
    
    def _generate_file_header(self) -> List[str]:
        """Generate TypeScript file header"""
        return [
            "/* tslint:disable */",
            "/* eslint-disable */",
            "/**",
            " * Auto-generated TypeScript definitions from Pydantic models",
            f" * Generated at: {datetime.now(UTC).isoformat()}",
            " * Do not modify this file manually - regenerate using schema sync",
            " */",
            ""
        ]
    
    def _generate_enums(self, schemas: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate enum definitions"""
        lines = []
        enums = self._extract_enums_from_schemas(schemas)
        
        for enum_name, enum_values in enums.items():
            enum_lines = [f"export type {enum_name} = {' | '.join(enum_values)};", ""]
            lines.extend(enum_lines)
        
        return lines
    
    def _generate_interfaces(self, schemas: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate interface definitions"""
        lines = []
        
        for schema_name, schema in schemas.items():
            interface_ts = self.generate_typescript_interface(schema_name, schema)
            lines.extend([interface_ts, ""])
        
        return lines
    
    def _extract_enums_from_schemas(self, schemas: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract enum definitions from schemas."""
        enums = {}
        
        for schema_name, schema in schemas.items():
            properties = schema.get('properties', {})
            for field_name, field_schema in properties.items():
                if 'enum' in field_schema and field_schema.get('type') == 'string':
                    enum_name = f"{schema_name}{field_name.title()}Enum"
                    enum_values = [f'"{value}"' for value in field_schema['enum']]
                    enums[enum_name] = enum_values
        
        return enums