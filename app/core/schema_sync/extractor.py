"""
Schema Extractor

Extracts schema information from Pydantic models.
Maintains 8-line function limit and single responsibility.
"""

from typing import Any, Dict, List, Type
from datetime import datetime, UTC
from pydantic import BaseModel
from app.core.exceptions_service import ServiceError
from app.core.error_context import ErrorContext
from app.logging_config import central_logger as logger


class SchemaExtractor:
    """Extracts schema information from Pydantic models."""
    
    def __init__(self):
        self._extracted_schemas: Dict[str, Dict[str, Any]] = {}
    
    def extract_schema_from_model(self, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Extract JSON schema from a Pydantic model."""
        try:
            schema = model_class.schema()
            schema['_metadata'] = self._create_metadata(model_class)
            return schema
            
        except Exception as e:
            raise ServiceError(
                message=f"Failed to extract schema from {model_class.__name__}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def extract_schemas_from_module(self, module_name: str) -> Dict[str, Dict[str, Any]]:
        """Extract schemas from all Pydantic models in a module."""
        try:
            module = __import__(module_name, fromlist=[''])
            schemas = {}
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if self._is_pydantic_model(attr):
                    schema = self.extract_schema_from_model(attr)
                    schemas[attr_name] = schema
            
            return schemas
            
        except Exception as e:
            raise ServiceError(
                message=f"Failed to extract schemas from module {module_name}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def extract_all_schemas(self, module_patterns: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract schemas from multiple modules."""
        all_schemas = {}
        
        for pattern in module_patterns:
            try:
                schemas = self.extract_schemas_from_module(pattern)
                all_schemas.update(schemas)
            except Exception as e:
                logger.warning(f"Warning: Could not extract schemas from {pattern}: {e}")
                continue
        
        self._extracted_schemas = all_schemas
        return all_schemas
    
    def _create_metadata(self, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Create metadata for schema"""
        return {
            'class_name': model_class.__name__,
            'module': model_class.__module__,
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def _is_pydantic_model(self, attr) -> bool:
        """Check if attribute is a Pydantic model"""
        return (isinstance(attr, type) and 
                issubclass(attr, BaseModel) and 
                attr != BaseModel)