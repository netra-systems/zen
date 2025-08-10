"""Enhanced schema synchronization system for maintaining type safety between frontend and backend."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, get_type_hints
from dataclasses import dataclass, asdict
from enum import Enum

from pydantic import BaseModel
import pydantic

from .exceptions import ValidationError, ServiceError
from .error_context import ErrorContext


class SchemaValidationLevel(Enum):
    """Schema validation levels."""
    STRICT = "strict"
    MODERATE = "moderate"  
    LENIENT = "lenient"


@dataclass
class SchemaChangeInfo:
    """Information about schema changes."""
    schema_name: str
    change_type: str  # added, removed, modified
    field_name: Optional[str] = None
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SyncReport:
    """Report of schema synchronization."""
    timestamp: datetime
    schemas_processed: int
    changes_detected: List[SchemaChangeInfo]
    validation_errors: List[str]
    files_generated: List[str]
    success: bool


class SchemaExtractor:
    """Extracts schema information from Pydantic models."""
    
    def __init__(self):
        self._extracted_schemas: Dict[str, Dict[str, Any]] = {}
    
    def extract_schema_from_model(self, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Extract JSON schema from a Pydantic model."""
        try:
            schema = model_class.schema()
            
            # Add metadata
            schema['_metadata'] = {
                'class_name': model_class.__name__,
                'module': model_class.__module__,
                'timestamp': datetime.utcnow().isoformat()
            }
            
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
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseModel) and 
                    attr != BaseModel):
                    
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
                print(f"Warning: Could not extract schemas from {pattern}: {e}")
                continue
        
        self._extracted_schemas = all_schemas
        return all_schemas


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
            
            for field_name, field_schema in properties.items():
                field_type = self._convert_json_schema_type_to_typescript(field_schema)
                optional = "" if field_name in required else "?"
                
                # Add field documentation if available
                if 'description' in field_schema:
                    interface_lines.append(f"  /** {field_schema['description']} */")
                
                interface_lines.append(f"  {field_name}{optional}: {field_type};")
            
            interface_lines.append("}")
            
            return "\n".join(interface_lines)
            
        except Exception as e:
            raise ServiceError(
                message=f"Failed to generate TypeScript interface for {schema_name}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def _convert_json_schema_type_to_typescript(self, field_schema: Dict[str, Any]) -> str:
        """Convert JSON schema type to TypeScript type."""
        field_type = field_schema.get('type', 'any')
        
        if field_type == 'string':
            # Check for enum values
            if 'enum' in field_schema:
                enum_values = [f'"{value}"' for value in field_schema['enum']]
                return ' | '.join(enum_values)
            return 'string'
        
        elif field_type == 'number':
            return 'number'
        
        elif field_type == 'integer':
            return 'number'
        
        elif field_type == 'boolean':
            return 'boolean'
        
        elif field_type == 'array':
            items_schema = field_schema.get('items', {})
            item_type = self._convert_json_schema_type_to_typescript(items_schema)
            return f'{item_type}[]'
        
        elif field_type == 'object':
            # Check for additional properties
            if 'properties' in field_schema:
                # Nested object - generate inline interface
                properties = []
                required = set(field_schema.get('required', []))
                
                for prop_name, prop_schema in field_schema['properties'].items():
                    prop_type = self._convert_json_schema_type_to_typescript(prop_schema)
                    optional = "" if prop_name in required else "?"
                    properties.append(f"{prop_name}{optional}: {prop_type}")
                
                return "{ " + "; ".join(properties) + " }"
            else:
                return 'Record<string, any>'
        
        elif 'anyOf' in field_schema:
            # Union types
            union_types = []
            for union_schema in field_schema['anyOf']:
                union_type = self._convert_json_schema_type_to_typescript(union_schema)
                union_types.append(union_type)
            return ' | '.join(union_types)
        
        else:
            # Fallback to any
            return 'any'
    
    def generate_typescript_file(self, schemas: Dict[str, Dict[str, Any]]) -> str:
        """Generate complete TypeScript file from schemas."""
        lines = [
            "/* tslint:disable */",
            "/* eslint-disable */",
            "/**",
            " * Auto-generated TypeScript definitions from Pydantic models",
            f" * Generated at: {datetime.utcnow().isoformat()}",
            " * Do not modify this file manually - regenerate using schema sync",
            " */",
            ""
        ]
        
        # Generate enums first
        enums = self._extract_enums_from_schemas(schemas)
        for enum_name, enum_values in enums.items():
            enum_lines = [f"export type {enum_name} = {' | '.join(enum_values)};", ""]
            lines.extend(enum_lines)
        
        # Generate interfaces
        for schema_name, schema in schemas.items():
            interface_ts = self.generate_typescript_interface(schema_name, schema)
            lines.extend([interface_ts, ""])
        
        return "\n".join(lines)
    
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
        
        # Check for removed schemas
        for schema_name in old_schemas:
            if schema_name not in new_schemas:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="removed",
                    description="Schema was removed"
                ))
        
        # Check for added schemas
        for schema_name in new_schemas:
            if schema_name not in old_schemas:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="added",
                    description="Schema was added"
                ))
        
        # Check for modified schemas
        for schema_name in set(old_schemas.keys()) & set(new_schemas.keys()):
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
        
        # Check for removed fields
        for field_name in old_props:
            if field_name not in new_props:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="removed",
                    field_name=field_name,
                    description="Field was removed"
                ))
        
        # Check for added fields
        for field_name in new_props:
            if field_name not in old_props:
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="added",
                    field_name=field_name,
                    description="Field was added"
                ))
        
        # Check for modified fields
        for field_name in set(old_props.keys()) & set(new_props.keys()):
            old_field = old_props[field_name]
            new_field = new_props[field_name]
            
            # Check type changes
            if old_field.get('type') != new_field.get('type'):
                changes.append(SchemaChangeInfo(
                    schema_name=schema_name,
                    change_type="modified",
                    field_name=field_name,
                    old_type=old_field.get('type'),
                    new_type=new_field.get('type'),
                    description="Field type changed"
                ))
            
            # Check required status changes
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
    
    def is_breaking_change(self, change: SchemaChangeInfo) -> bool:
        """Determine if a change is breaking based on validation level."""
        if self._validation_level == SchemaValidationLevel.LENIENT:
            # Only schema removal is breaking in lenient mode
            return change.change_type == "removed" and change.field_name is None
        
        elif self._validation_level == SchemaValidationLevel.MODERATE:
            # Schema/field removal and type changes are breaking
            return (change.change_type == "removed" or
                    (change.change_type == "modified" and change.old_type != change.new_type))
        
        else:  # STRICT
            # Any change is potentially breaking in strict mode
            return True


class SchemaSynchronizer:
    """Main schema synchronization orchestrator."""
    
    def __init__(
        self, 
        backend_modules: List[str],
        frontend_output_path: str,
        validation_level: SchemaValidationLevel = SchemaValidationLevel.MODERATE
    ):
        self.backend_modules = backend_modules
        self.frontend_output_path = Path(frontend_output_path)
        self.validation_level = validation_level
        
        self.extractor = SchemaExtractor()
        self.generator = TypeScriptGenerator(validation_level)
        self.validator = SchemaValidator(validation_level)
        
        self._backup_path = self.frontend_output_path.with_suffix('.backup')
    
    def sync_schemas(self, force: bool = False) -> SyncReport:
        """Perform complete schema synchronization."""
        try:
            report = SyncReport(
                timestamp=datetime.utcnow(),
                schemas_processed=0,
                changes_detected=[],
                validation_errors=[],
                files_generated=[],
                success=False
            )
            
            # Extract current schemas
            current_schemas = self.extractor.extract_all_schemas(self.backend_modules)
            report.schemas_processed = len(current_schemas)
            
            # Load previous schemas if they exist
            previous_schemas = self._load_previous_schemas()
            
            # Validate changes
            if previous_schemas and not force:
                changes = self.validator.validate_schema_changes(previous_schemas, current_schemas)
                report.changes_detected = changes
                
                # Check for breaking changes
                breaking_changes = [c for c in changes if self.validator.is_breaking_change(c)]
                if breaking_changes:
                    report.validation_errors = [
                        f"Breaking change detected: {c.description} in {c.schema_name}"
                        for c in breaking_changes
                    ]
                    
                    if not force:
                        report.success = False
                        return report
            
            # Create backup
            if self.frontend_output_path.exists():
                self.frontend_output_path.rename(self._backup_path)
            
            # Generate TypeScript file
            typescript_content = self.generator.generate_typescript_file(current_schemas)
            
            # Write to file
            self.frontend_output_path.parent.mkdir(parents=True, exist_ok=True)
            self.frontend_output_path.write_text(typescript_content, encoding='utf-8')
            
            report.files_generated = [str(self.frontend_output_path)]
            
            # Save current schemas for future comparison
            self._save_current_schemas(current_schemas)
            
            report.success = True
            return report
            
        except Exception as e:
            # Restore backup if sync failed
            if self._backup_path.exists():
                self._backup_path.rename(self.frontend_output_path)
            
            raise ServiceError(
                message=f"Schema synchronization failed: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def _load_previous_schemas(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Load previously saved schemas."""
        schema_cache_path = self.frontend_output_path.with_suffix('.cache.json')
        
        if schema_cache_path.exists():
            try:
                return json.loads(schema_cache_path.read_text(encoding='utf-8'))
            except Exception:
                return None
        
        return None
    
    def _save_current_schemas(self, schemas: Dict[str, Dict[str, Any]]):
        """Save current schemas for future comparison."""
        schema_cache_path = self.frontend_output_path.with_suffix('.cache.json')
        
        schema_cache_path.write_text(
            json.dumps(schemas, indent=2, default=str),
            encoding='utf-8'
        )


def create_sync_command():
    """Create a CLI command for schema synchronization."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Synchronize schemas between backend and frontend")
    parser.add_argument('--modules', nargs='+', default=['app.schemas'], help='Backend modules to extract schemas from')
    parser.add_argument('--output', default='frontend/types/backend_schema_auto_generated.ts', help='Frontend output path')
    parser.add_argument('--validation-level', choices=['strict', 'moderate', 'lenient'], default='moderate', help='Validation level')
    parser.add_argument('--force', action='store_true', help='Force sync even with breaking changes')
    
    args = parser.parse_args()
    
    validation_level = SchemaValidationLevel(args.validation_level)
    
    synchronizer = SchemaSynchronizer(
        backend_modules=args.modules,
        frontend_output_path=args.output,
        validation_level=validation_level
    )
    
    try:
        report = synchronizer.sync_schemas(force=args.force)
        
        print(f"Schema synchronization completed at {report.timestamp}")
        print(f"Processed {report.schemas_processed} schemas")
        print(f"Changes detected: {len(report.changes_detected)}")
        print(f"Files generated: {len(report.files_generated)}")
        
        if report.changes_detected:
            print("\nChanges detected:")
            for change in report.changes_detected:
                print(f"  - {change.schema_name}: {change.description}")
        
        if report.validation_errors:
            print("\nValidation errors:")
            for error in report.validation_errors:
                print(f"  - {error}")
        
        print(f"\nSync {'succeeded' if report.success else 'failed'}")
        
        return 0 if report.success else 1
        
    except Exception as e:
        print(f"Schema synchronization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(create_sync_command())