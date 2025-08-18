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
        return self._collect_all_schema_changes(old_schemas, new_schemas)
    
    def _collect_all_schema_changes(
        self,
        old_schemas: Dict[str, Dict[str, Any]],
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Collect all types of schema changes."""
        removed_changes = self._check_removed_schemas(old_schemas, new_schemas)
        added_changes = self._check_added_schemas(old_schemas, new_schemas)
        modified_changes = self._check_modified_schemas(old_schemas, new_schemas)
        return self._combine_all_changes(removed_changes, added_changes, modified_changes)
    
    def _combine_all_changes(
        self,
        removed: List[SchemaChangeInfo],
        added: List[SchemaChangeInfo],
        modified: List[SchemaChangeInfo]
    ) -> List[SchemaChangeInfo]:
        """Combine all types of changes into single list."""
        changes = []
        changes.extend(removed)
        changes.extend(added)
        changes.extend(modified)
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
        removed_names = self._find_removed_schema_names(old_schemas, new_schemas)
        return self._create_removal_changes(removed_names)
    
    def _find_removed_schema_names(
        self,
        old_schemas: Dict[str, Dict[str, Any]],
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Find names of schemas that were removed."""
        removed = []
        for schema_name in old_schemas:
            if schema_name not in new_schemas:
                removed.append(schema_name)
        return removed
    
    def _create_removal_changes(self, schema_names: List[str]) -> List[SchemaChangeInfo]:
        """Create change info objects for removed schemas."""
        changes = []
        for schema_name in schema_names:
            changes.append(self._create_schema_removed_change(schema_name))
        return changes
    
    def _create_schema_removed_change(self, schema_name: str) -> SchemaChangeInfo:
        """Create schema removal change info."""
        return SchemaChangeInfo(
            schema_name=schema_name,
            change_type="removed",
            description="Schema was removed"
        )
    
    def _check_added_schemas(
        self, 
        old_schemas: Dict[str, Dict[str, Any]], 
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Check for added schemas"""
        added_names = self._find_added_schema_names(old_schemas, new_schemas)
        return self._create_addition_changes(added_names)
    
    def _find_added_schema_names(
        self,
        old_schemas: Dict[str, Dict[str, Any]],
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Find names of schemas that were added."""
        added = []
        for schema_name in new_schemas:
            if schema_name not in old_schemas:
                added.append(schema_name)
        return added
    
    def _create_addition_changes(self, schema_names: List[str]) -> List[SchemaChangeInfo]:
        """Create change info objects for added schemas."""
        changes = []
        for schema_name in schema_names:
            changes.append(self._create_schema_added_change(schema_name))
        return changes
    
    def _create_schema_added_change(self, schema_name: str) -> SchemaChangeInfo:
        """Create schema addition change info."""
        return SchemaChangeInfo(
            schema_name=schema_name,
            change_type="added",
            description="Schema was added"
        )
    
    def _check_modified_schemas(
        self, 
        old_schemas: Dict[str, Dict[str, Any]], 
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> List[SchemaChangeInfo]:
        """Check for modified schemas"""
        common_schemas = self._get_common_schema_names(old_schemas, new_schemas)
        return self._process_common_schemas(old_schemas, new_schemas, common_schemas)
    
    def _get_common_schema_names(
        self,
        old_schemas: Dict[str, Dict[str, Any]],
        new_schemas: Dict[str, Dict[str, Any]]
    ) -> Set[str]:
        """Get schema names common to both old and new schemas."""
        return set(old_schemas.keys()) & set(new_schemas.keys())
    
    def _process_common_schemas(
        self,
        old_schemas: Dict[str, Dict[str, Any]],
        new_schemas: Dict[str, Dict[str, Any]],
        common_schemas: Set[str]
    ) -> List[SchemaChangeInfo]:
        """Process common schemas for changes."""
        changes = []
        for schema_name in common_schemas:
            schema_changes = self._compare_schemas(
                old_schemas[schema_name], new_schemas[schema_name], schema_name
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
        schema_props = self._extract_schema_properties(old_schema, new_schema)
        return self._check_all_field_changes(schema_props, schema_name)
    
    def _extract_schema_properties(
        self,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract properties and required fields from schemas."""
        return {
            'old_props': old_schema.get('properties', {}),
            'new_props': new_schema.get('properties', {}),
            'old_required': set(old_schema.get('required', [])),
            'new_required': set(new_schema.get('required', []))
        }
    
    def _check_all_field_changes(
        self,
        schema_props: Dict[str, Any],
        schema_name: str
    ) -> List[SchemaChangeInfo]:
        """Check all types of field changes."""
        changes = []
        changes.extend(self._check_removed_fields(schema_props['old_props'], schema_props['new_props'], schema_name))
        changes.extend(self._check_added_fields(schema_props['old_props'], schema_props['new_props'], schema_name))
        changes.extend(self._check_modified_fields(
            schema_props['old_props'], schema_props['new_props'],
            schema_props['old_required'], schema_props['new_required'], schema_name
        ))
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
                changes.append(self._create_field_removed_change(schema_name, field_name))
        return changes
    
    def _create_field_removed_change(
        self,
        schema_name: str,
        field_name: str
    ) -> SchemaChangeInfo:
        """Create field removal change info."""
        return SchemaChangeInfo(
            schema_name=schema_name,
            change_type="removed",
            field_name=field_name,
            description="Field was removed"
        )
    
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
                changes.append(self._create_field_added_change(schema_name, field_name))
        return changes
    
    def _create_field_added_change(
        self,
        schema_name: str,
        field_name: str
    ) -> SchemaChangeInfo:
        """Create field addition change info."""
        return SchemaChangeInfo(
            schema_name=schema_name,
            change_type="added",
            field_name=field_name,
            description="Field was added"
        )
    
    def _check_modified_fields(
        self, 
        old_props: Dict[str, Any], 
        new_props: Dict[str, Any],
        old_required: Set[str],
        new_required: Set[str],
        schema_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for modified fields"""
        common_fields = set(old_props.keys()) & set(new_props.keys())
        return self._process_common_fields(
            old_props, new_props, old_required, new_required, schema_name, common_fields
        )
    
    def _process_common_fields(
        self,
        old_props: Dict[str, Any],
        new_props: Dict[str, Any],
        old_required: Set[str],
        new_required: Set[str],
        schema_name: str,
        common_fields: Set[str]
    ) -> List[SchemaChangeInfo]:
        """Process common fields for changes."""
        changes = []
        for field_name in common_fields:
            changes.extend(self._check_field_changes(
                old_props[field_name], new_props[field_name],
                old_required, new_required, schema_name, field_name
            ))
        return changes
    
    def _check_field_changes(
        self,
        old_field: Dict[str, Any],
        new_field: Dict[str, Any],
        old_required: Set[str],
        new_required: Set[str],
        schema_name: str,
        field_name: str
    ) -> List[SchemaChangeInfo]:
        """Check individual field for changes."""
        changes = []
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
        if self._has_type_change(old_field, new_field):
            return [self._create_type_change_info(old_field, new_field, schema_name, field_name)]
        return []
    
    def _has_type_change(self, old_field: Dict[str, Any], new_field: Dict[str, Any]) -> bool:
        """Check if field type has changed."""
        return old_field.get('type') != new_field.get('type')
    
    def _create_type_change_info(
        self,
        old_field: Dict[str, Any],
        new_field: Dict[str, Any],
        schema_name: str,
        field_name: str
    ) -> SchemaChangeInfo:
        """Create type change info."""
        return SchemaChangeInfo(
            schema_name=schema_name,
            change_type="modified",
            field_name=field_name,
            old_type=old_field.get('type'),
            new_type=new_field.get('type'),
            description="Field type changed"
        )
    
    def _check_required_changes(
        self, 
        old_required: Set[str], 
        new_required: Set[str], 
        schema_name: str, 
        field_name: str
    ) -> List[SchemaChangeInfo]:
        """Check for required status changes"""
        required_status = self._get_required_status_change(old_required, new_required, field_name)
        if required_status['changed']:
            return [self._create_required_change_info(schema_name, field_name, required_status)]
        return []
    
    def _get_required_status_change(
        self,
        old_required: Set[str],
        new_required: Set[str],
        field_name: str
    ) -> Dict[str, Any]:
        """Get required status change information."""
        was_required = field_name in old_required
        is_required = field_name in new_required
        return {
            'changed': was_required != is_required,
            'was_required': was_required,
            'is_required': is_required
        }
    
    def _create_required_change_info(
        self,
        schema_name: str,
        field_name: str,
        required_status: Dict[str, Any]
    ) -> SchemaChangeInfo:
        """Create required status change info."""
        return SchemaChangeInfo(
            schema_name=schema_name,
            change_type="modified",
            field_name=field_name,
            description=f"Field required status changed: {required_status['was_required']} -> {required_status['is_required']}"
        )
    
    def _is_breaking_lenient(self, change: SchemaChangeInfo) -> bool:
        """Check if breaking change in lenient mode"""
        return change.change_type == "removed" and change.field_name is None
    
    def _is_breaking_moderate(self, change: SchemaChangeInfo) -> bool:
        """Check if breaking change in moderate mode"""
        return (change.change_type == "removed" or
                (change.change_type == "modified" and change.old_type != change.new_type))