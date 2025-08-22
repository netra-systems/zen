"""API Gateway Request Transformation Engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TransformationRule:
    """Defines a transformation rule."""
    name: str
    source_field: str
    target_field: str
    transformer: Callable[[Any], Any]
    enabled: bool = True


class SchemaMapper:
    """Maps between different API schemas."""
    
    def __init__(self):
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.transformations: List[TransformationRule] = []
    
    def add_mapping(self, source_schema: str, target_schema: str, field_mappings: Dict[str, str]) -> None:
        """Add schema mapping."""
        key = f"{source_schema}->{target_schema}"
        self.mappings[key] = field_mappings
    
    def map_fields(self, data: Dict[str, Any], source_schema: str, target_schema: str) -> Dict[str, Any]:
        """Map fields from source to target schema."""
        key = f"{source_schema}->{target_schema}"
        field_mappings = self.mappings.get(key, {})
        
        result = {}
        for source_field, target_field in field_mappings.items():
            if source_field in data:
                result[target_field] = data[source_field]
        
        return result


class DataConverter:
    """Converts data types and formats."""
    
    def __init__(self):
        self.converters: Dict[str, Callable] = {
            'string_to_int': lambda x: int(x) if isinstance(x, str) and x.isdigit() else x,
            'int_to_string': lambda x: str(x) if isinstance(x, int) else x,
            'timestamp_to_iso': lambda x: x,  # Placeholder
            'iso_to_timestamp': lambda x: x,  # Placeholder
        }
    
    def register_converter(self, name: str, converter: Callable) -> None:
        """Register a custom converter."""
        self.converters[name] = converter
    
    def convert(self, data: Any, converter_name: str) -> Any:
        """Apply a converter to data."""
        converter = self.converters.get(converter_name)
        if converter:
            try:
                return converter(data)
            except Exception:
                return data  # Return original on conversion error
        return data
    
    def convert_fields(self, data: Dict[str, Any], field_converters: Dict[str, str]) -> Dict[str, Any]:
        """Apply converters to specific fields."""
        result = data.copy()
        for field, converter_name in field_converters.items():
            if field in result:
                result[field] = self.convert(result[field], converter_name)
        return result


class TransformationEngine:
    """Main transformation engine for API requests/responses."""
    
    def __init__(self):
        self.schema_mapper = SchemaMapper()
        self.data_converter = DataConverter()
        self.transformations: List[TransformationRule] = []
        self.enabled = True
    
    def add_transformation(self, rule: TransformationRule) -> None:
        """Add a transformation rule."""
        self.transformations.append(rule)
    
    def transform_request(self, data: Dict[str, Any], source_schema: str, target_schema: str) -> Dict[str, Any]:
        """Transform request data."""
        if not self.enabled:
            return data
        
        # Apply schema mapping
        result = self.schema_mapper.map_fields(data, source_schema, target_schema)
        
        # Apply field transformations
        for rule in self.transformations:
            if rule.enabled and rule.source_field in result:
                try:
                    result[rule.target_field] = rule.transformer(result[rule.source_field])
                    if rule.target_field != rule.source_field:
                        del result[rule.source_field]
                except Exception:
                    # Keep original value on transformation error
                    pass
        
        return result
    
    def transform_response(self, data: Dict[str, Any], source_schema: str, target_schema: str) -> Dict[str, Any]:
        """Transform response data."""
        # For now, same logic as request transformation
        return self.transform_request(data, source_schema, target_schema)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get transformation statistics."""
        return {
            'enabled': self.enabled,
            'transformation_count': len(self.transformations),
            'active_transformations': len([t for t in self.transformations if t.enabled]),
            'schema_mappings': len(self.schema_mapper.mappings)
        }
    
    def disable(self) -> None:
        """Disable transformations."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable transformations."""
        self.enabled = True
