"""
Schema Validator

Validates schemas for breaking changes.
Maintains 8-line function limit and focused responsibility.
"""

from typing import Dict, Any, List, Set
from .models import SchemaValidationLevel, SchemaChangeInfo


class SchemaValidator:
    """Validates schemas for breaking changes."""
    
    def __init__(self, validation_level: SchemaValidationLevel = SchemaValidationLevel.MODERATE):
        self._validation_level = validation_level
    
    def validate_schema_changes(
        self, 
        old_schemas: Dict[str, Dict[str, Any]], 
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Validate changes between old and new schemas."""
        changes = []
        
        changes.extend(self._check_removed_schemas(old_schemas, new_schemas))
        changes.extend(self._check_added_schemas(old_schemas, new_schemas))
        changes.extend(self._check_modified_schemas(old_schemas, new_schemas))
        
        return changes
    
    def is_breaking_change(self, change: SchemaChangeInfo) -> bool:
        """Determine if a change is breaking based on validation level."""
        if self._validation_level == SchemaValidationLevel.LENIENT:
            return self._is_breaking_lenient(change)
        elif self._validation_level == SchemaValidationLevel.MODERATE:
            return self._is_breaking_moderate(change)
        else:  # STRICT
            return True
    
    def _check_removed_schemas(
        self, 
        old_schemas: Dict[str, Dict[str, Any]], 
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Check for removed schemas"""
        changes = []
        for schema_name in old_schemas:
            if schema_name not in new_schemas:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="removed",
                    description="Schema was removed"
                ))
        return changes
    
    def _check_added_schemas(
        self, 
        old_schemas: Dict[str, Dict[str, Any]], 
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Check for added schemas"""
        changes = []
        for schema_name in new_schemas:
            if schema_name not in old_schemas:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="added",
                    description="Schema was added"
                ))
        return changes
    
    def _check_modified_schemas(
        self, 
        old_schemas: Dict[str, Dict[str, Any]], 
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Check for modified schemas"""
        changes = []
        common_schemas = set(old_schemas.keys()) & set(new_schemas.keys())
        
        for schema_name in common_schemas:
            schema_changes = self._compare_schemas(
                old_schemas[schema_name], 
                new_schemas[schema_name], 
                schema_name
            )
            changes.extend(schema_changes)
        
        return changes
    
    def _compare_schemas(
        self, 
        old_schema: Dict[str, Any], 
        new_schema: Dict[str, Any], 
        schema_name: str
    ) -> List[SchemaChangeInfo]:
        """Compare two schemas for changes."""
        changes = []
        
        old_props = old_schema.get('properties', {})
        new_props = new_schema.get('properties', {})
        old_required = set(old_schema.get('required', []))
        new_required = set(new_schema.get('required', []))
        
        changes.extend(self._check_removed_fields(old_props, new_props, schema_name))
        changes.extend(self._check_added_fields(old_props, new_props, schema_name))
        changes.extend(self._check_modified_fields(old_props, new_props, old_required, new_required, schema_name))
        
        return changes
    
    def _check_removed_fields(
        self, 
        old_props: Dict[str, Any], 
        new_props: Dict[str, Any], 
        schema_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for removed fields"""
        changes = []
        for field_name in old_props:
            if field_name not in new_props:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="removed",
                    field_name=field_name,
                    description="Field was removed"
                ))
        return changes
    
    def _check_added_fields(
        self, 
        old_props: Dict[str, Any], 
        new_props: Dict[str, Any], 
        schema_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for added fields"""
        changes = []
        for field_name in new_props:
            if field_name not in old_props:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="added",
                    field_name=field_name,
                    description="Field was added"
                ))
        return changes
    
    def _check_modified_fields(
        self, 
        old_props: Dict[str, Any], 
        new_props: Dict[str, Any],
        old_required: Set[str],
        new_required: Set[str],
        schema_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for modified fields"""
        changes = []
        common_fields = set(old_props.keys()) & set(new_props.keys())
        
        for field_name in common_fields:
            old_field = old_props[field_name]
            new_field = new_props[field_name]
            
            changes.extend(self._check_type_changes(old_field, new_field, schema_name, field_name))
            changes.extend(self._check_required_changes(old_required, new_required, schema_name, field_name))
        
        return changes
    
    def _check_type_changes(
        self, 
        old_field: Dict[str, Any], 
        new_field: Dict[str, Any], 
        schema_name: str, 
        field_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for type changes"""
        changes = []
        if old_field.get('type') != new_field.get('type'):
            changes.append(SchemaChangeInfo(
                schema_name=schema_name,
                change_type="modified",
                field_name=field_name,
                old_type=old_field.get('type'),
                new_type=new_field.get('type'),
                description="Field type changed"
            ))
        return changes
    
    def _check_required_changes(
        self, 
        old_required: Set[str], 
        new_required: Set[str], 
        schema_name: str, 
        field_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for required status changes"""
        changes = []
        was_required = field_name in old_required
        is_required = field_name in new_required
        
        if was_required != is_required:
            changes.append(SchemaChangeInfo(
                schema_name=schema_name,
                change_type="modified",
                field_name=field_name,
                description=f"Field required status changed: {was_required} -> {is_required}"
            ))
        return changes
    
    def _is_breaking_lenient(self, change: SchemaChangeInfo) -> bool:
        """Check if breaking change in lenient mode"""
        return change.change_type == "removed" and change.field_name is None
    
    def _is_breaking_moderate(self, change: SchemaChangeInfo) -> bool:
        """Check if breaking change in moderate mode"""
        return (change.change_type == "removed" or
                (change.change_type == "modified" and change.old_type != change.new_type))