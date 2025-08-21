"""Schema Mapper for API Gateway

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (API transformation and integration)
- Business Goal: Enable seamless API integration with schema transformation
- Value Impact: Reduces integration costs and enables legacy system compatibility
- Strategic Impact: Critical for enterprise API ecosystem integration

Provides request/response schema mapping and transformation capabilities.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.core.exceptions_base import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransformationType(Enum):
    """Types of transformations available."""
    FIELD_RENAME = "field_rename"
    FIELD_REMOVE = "field_remove"
    FIELD_ADD = "field_add"
    VALUE_TRANSFORM = "value_transform"
    NESTED_OBJECT = "nested_object"
    ARRAY_TRANSFORM = "array_transform"
    CONDITIONAL = "conditional"
    CUSTOM_FUNCTION = "custom_function"


@dataclass
class TransformationRule:
    """Represents a single transformation rule."""
    rule_id: str
    transformation_type: TransformationType
    source_path: str
    target_path: Optional[str] = None
    value: Any = None
    condition: Optional[Dict[str, Any]] = None
    custom_function: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaMapping:
    """Represents a complete schema mapping configuration."""
    mapping_id: str
    name: str
    source_schema: Dict[str, Any]
    target_schema: Dict[str, Any]
    transformation_rules: List[TransformationRule] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationResult:
    """Result of a schema transformation."""
    success: bool
    transformed_data: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    rules_applied: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaMapper:
    """Manages schema mappings and transformations."""
    
    def __init__(self):
        """Initialize the schema mapper."""
        self._mappings: Dict[str, SchemaMapping] = {}
        self._custom_functions: Dict[str, Callable] = {}
        self._transformation_cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def register_mapping(self, mapping: SchemaMapping) -> None:
        """Register a new schema mapping."""
        async with self._lock:
            mapping.updated_at = datetime.now(timezone.utc)
            self._mappings[mapping.mapping_id] = mapping
            logger.info(f"Registered schema mapping: {mapping.mapping_id}")
    
    async def unregister_mapping(self, mapping_id: str) -> bool:
        """Unregister a schema mapping."""
        async with self._lock:
            if mapping_id in self._mappings:
                del self._mappings[mapping_id]
                logger.info(f"Unregistered schema mapping: {mapping_id}")
                return True
            return False
    
    async def register_custom_function(self, function_name: str, function: Callable) -> None:
        """Register a custom transformation function."""
        async with self._lock:
            self._custom_functions[function_name] = function
            logger.info(f"Registered custom function: {function_name}")
    
    async def transform_data(self, mapping_id: str, source_data: Any) -> TransformationResult:
        """Transform data using the specified mapping."""
        start_time = datetime.now(timezone.utc)
        
        async with self._lock:
            mapping = self._mappings.get(mapping_id)
            if not mapping:
                return TransformationResult(
                    success=False,
                    transformed_data=None,
                    errors=[f"Schema mapping {mapping_id} not found"]
                )
            
            if not mapping.is_active:
                return TransformationResult(
                    success=False,
                    transformed_data=None,
                    errors=[f"Schema mapping {mapping_id} is not active"]
                )
        
        try:
            # Create a deep copy of source data to avoid modifying original
            transformed_data = self._deep_copy(source_data)
            errors = []
            warnings = []
            rules_applied = 0
            
            # Apply transformation rules in order
            for rule in mapping.transformation_rules:
                try:
                    transformed_data = await self._apply_transformation_rule(
                        rule, transformed_data, errors, warnings
                    )
                    rules_applied += 1
                except Exception as e:
                    error_msg = f"Failed to apply rule {rule.rule_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return TransformationResult(
                success=len(errors) == 0,
                transformed_data=transformed_data,
                errors=errors,
                warnings=warnings,
                processing_time_ms=processing_time,
                rules_applied=rules_applied
            )
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TransformationResult(
                success=False,
                transformed_data=None,
                errors=[f"Transformation failed: {str(e)}"],
                processing_time_ms=processing_time
            )
    
    async def validate_mapping(self, mapping: SchemaMapping) -> List[str]:
        """Validate a schema mapping configuration."""
        errors = []
        
        # Validate basic structure
        if not mapping.mapping_id:
            errors.append("Mapping ID is required")
        
        if not mapping.name:
            errors.append("Mapping name is required")
        
        # Validate transformation rules
        for i, rule in enumerate(mapping.transformation_rules):
            rule_errors = await self._validate_transformation_rule(rule)
            for error in rule_errors:
                errors.append(f"Rule {i}: {error}")
        
        return errors
    
    async def test_mapping(self, mapping_id: str, test_data: Any) -> TransformationResult:
        """Test a mapping with sample data."""
        return await self.transform_data(mapping_id, test_data)
    
    async def get_mapping_stats(self) -> Dict[str, Any]:
        """Get statistics about registered mappings."""
        async with self._lock:
            active_mappings = len([m for m in self._mappings.values() if m.is_active])
            total_rules = sum(len(m.transformation_rules) for m in self._mappings.values())
            
            return {
                "total_mappings": len(self._mappings),
                "active_mappings": active_mappings,
                "total_transformation_rules": total_rules,
                "custom_functions": len(self._custom_functions),
                "cache_size": len(self._transformation_cache),
                "mappings": [
                    {
                        "mapping_id": m.mapping_id,
                        "name": m.name,
                        "is_active": m.is_active,
                        "rules_count": len(m.transformation_rules),
                        "created_at": m.created_at.isoformat(),
                        "updated_at": m.updated_at.isoformat()
                    }
                    for m in self._mappings.values()
                ]
            }
    
    async def _apply_transformation_rule(self, rule: TransformationRule, data: Any, 
                                       errors: List[str], warnings: List[str]) -> Any:
        """Apply a single transformation rule to data."""
        if rule.transformation_type == TransformationType.FIELD_RENAME:
            return self._apply_field_rename(rule, data)
        
        elif rule.transformation_type == TransformationType.FIELD_REMOVE:
            return self._apply_field_remove(rule, data)
        
        elif rule.transformation_type == TransformationType.FIELD_ADD:
            return self._apply_field_add(rule, data)
        
        elif rule.transformation_type == TransformationType.VALUE_TRANSFORM:
            return self._apply_value_transform(rule, data)
        
        elif rule.transformation_type == TransformationType.NESTED_OBJECT:
            return self._apply_nested_object_transform(rule, data)
        
        elif rule.transformation_type == TransformationType.ARRAY_TRANSFORM:
            return self._apply_array_transform(rule, data)
        
        elif rule.transformation_type == TransformationType.CONDITIONAL:
            return await self._apply_conditional_transform(rule, data)
        
        elif rule.transformation_type == TransformationType.CUSTOM_FUNCTION:
            return await self._apply_custom_function(rule, data)
        
        else:
            warnings.append(f"Unknown transformation type: {rule.transformation_type}")
            return data
    
    def _apply_field_rename(self, rule: TransformationRule, data: Any) -> Any:
        """Apply field rename transformation."""
        if not isinstance(data, dict):
            return data
        
        if rule.source_path in data and rule.target_path:
            data[rule.target_path] = data.pop(rule.source_path)
        
        return data
    
    def _apply_field_remove(self, rule: TransformationRule, data: Any) -> Any:
        """Apply field removal transformation."""
        if not isinstance(data, dict):
            return data
        
        data.pop(rule.source_path, None)
        return data
    
    def _apply_field_add(self, rule: TransformationRule, data: Any) -> Any:
        """Apply field addition transformation."""
        if not isinstance(data, dict):
            return data
        
        if rule.target_path:
            data[rule.target_path] = rule.value
        
        return data
    
    def _apply_value_transform(self, rule: TransformationRule, data: Any) -> Any:
        """Apply value transformation."""
        if not isinstance(data, dict) or rule.source_path not in data:
            return data
        
        # Simple value transformations based on rule metadata
        transform_type = rule.metadata.get("transform_type")
        current_value = data[rule.source_path]
        
        if transform_type == "upper":
            data[rule.source_path] = str(current_value).upper()
        elif transform_type == "lower":
            data[rule.source_path] = str(current_value).lower()
        elif transform_type == "multiply":
            multiplier = rule.metadata.get("multiplier", 1)
            data[rule.source_path] = float(current_value) * multiplier
        elif transform_type == "format_date":
            # Would implement date formatting logic
            pass
        
        return data
    
    def _apply_nested_object_transform(self, rule: TransformationRule, data: Any) -> Any:
        """Apply nested object transformation."""
        # This would implement nested object transformation logic
        return data
    
    def _apply_array_transform(self, rule: TransformationRule, data: Any) -> Any:
        """Apply array transformation."""
        if not isinstance(data, dict) or rule.source_path not in data:
            return data
        
        array_data = data[rule.source_path]
        if not isinstance(array_data, list):
            return data
        
        # Apply transformation to each array element
        transform_function = rule.metadata.get("transform_function")
        if transform_function and transform_function in self._custom_functions:
            try:
                data[rule.source_path] = [
                    self._custom_functions[transform_function](item) 
                    for item in array_data
                ]
            except Exception as e:
                logger.error(f"Array transformation failed: {e}")
        
        return data
    
    async def _apply_conditional_transform(self, rule: TransformationRule, data: Any) -> Any:
        """Apply conditional transformation."""
        if not isinstance(data, dict) or not rule.condition:
            return data
        
        # Simple condition evaluation (would be more sophisticated in production)
        condition_field = rule.condition.get("field")
        condition_value = rule.condition.get("value")
        condition_operator = rule.condition.get("operator", "equals")
        
        if condition_field in data:
            current_value = data[condition_field]
            
            condition_met = False
            if condition_operator == "equals":
                condition_met = current_value == condition_value
            elif condition_operator == "not_equals":
                condition_met = current_value != condition_value
            elif condition_operator == "greater_than":
                condition_met = float(current_value) > float(condition_value)
            elif condition_operator == "less_than":
                condition_met = float(current_value) < float(condition_value)
            
            if condition_met and rule.target_path:
                data[rule.target_path] = rule.value
        
        return data
    
    async def _apply_custom_function(self, rule: TransformationRule, data: Any) -> Any:
        """Apply custom function transformation."""
        function_name = rule.metadata.get("function_name")
        if function_name and function_name in self._custom_functions:
            try:
                return self._custom_functions[function_name](data, rule)
            except Exception as e:
                logger.error(f"Custom function {function_name} failed: {e}")
        
        return data
    
    async def _validate_transformation_rule(self, rule: TransformationRule) -> List[str]:
        """Validate a transformation rule."""
        errors = []
        
        if not rule.rule_id:
            errors.append("Rule ID is required")
        
        if not rule.source_path and rule.transformation_type != TransformationType.FIELD_ADD:
            errors.append("Source path is required for this transformation type")
        
        if (rule.transformation_type == TransformationType.FIELD_RENAME and 
            not rule.target_path):
            errors.append("Target path is required for field rename")
        
        if (rule.transformation_type == TransformationType.CUSTOM_FUNCTION and
            not rule.metadata.get("function_name")):
            errors.append("Function name is required for custom function transformation")
        
        return errors
    
    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of an object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    async def clear_cache(self) -> None:
        """Clear the transformation cache."""
        async with self._lock:
            self._transformation_cache.clear()
            logger.info("Cleared transformation cache")
    
    async def enable_mapping(self, mapping_id: str) -> bool:
        """Enable a schema mapping."""
        async with self._lock:
            if mapping_id in self._mappings:
                self._mappings[mapping_id].is_active = True
                self._mappings[mapping_id].updated_at = datetime.now(timezone.utc)
                logger.info(f"Enabled schema mapping: {mapping_id}")
                return True
            return False
    
    async def disable_mapping(self, mapping_id: str) -> bool:
        """Disable a schema mapping."""
        async with self._lock:
            if mapping_id in self._mappings:
                self._mappings[mapping_id].is_active = False
                self._mappings[mapping_id].updated_at = datetime.now(timezone.utc)
                logger.info(f"Disabled schema mapping: {mapping_id}")
                return True
            return False


# Global schema mapper instance
schema_mapper = SchemaMapper()