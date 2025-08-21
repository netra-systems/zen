"""
Schema Synchronizer

Main schema synchronization orchestrator.
Maintains 25-line function limit and modular design.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, UTC
from app.core.exceptions_service import ServiceError
from app.core.error_context import ErrorContext
from netra_backend.app.models import SchemaValidationLevel, SyncReport
from netra_backend.app.extractor import SchemaExtractor
from netra_backend.app.generator import TypeScriptGenerator
from netra_backend.app.validator import SchemaValidator


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
            report = self._create_initial_report()
            
            current_schemas = self.extractor.extract_all_schemas(self.backend_modules)
            report.schemas_processed = len(current_schemas)
            
            if not self._validate_changes(current_schemas, report, force):
                return report
            
            self._create_backup()
            self._generate_and_write_typescript(current_schemas, report)
            self._save_current_schemas(current_schemas)
            
            report.success = True
            return report
            
        except Exception as e:
            self._restore_backup()
            raise ServiceError(
                message=f"Schema synchronization failed: {e}",
                context=ErrorContext.get_all_context()
            )
    
    def _create_initial_report(self) -> SyncReport:
        """Create initial sync report"""
        return SyncReport(
            timestamp=datetime.now(UTC),
            schemas_processed=0,
            changes_detected=[],
            validation_errors=[],
            files_generated=[],
            success=False
        )
    
    def _validate_changes(
        self, 
        current_schemas: Dict[str, Dict[str, Any]], 
        report: SyncReport, 
        force: bool
    ) -> bool:
        """Validate schema changes"""
        previous_schemas = self._load_previous_schemas()
        
        if previous_schemas and not force:
            changes = self.validator.validate_schema_changes(previous_schemas, current_schemas)
            report.changes_detected = changes
            
            breaking_changes = [c for c in changes if self.validator.is_breaking_change(c)]
            if breaking_changes:
                report.validation_errors = [
                    f"Breaking change detected: {c.description} in {c.schema_name}"
                    for c in breaking_changes
                ]
                
                if not force:
                    report.success = False
                    return False
        
        return True
    
    def _create_backup(self) -> None:
        """Create backup of existing file"""
        if self.frontend_output_path.exists():
            self.frontend_output_path.rename(self._backup_path)
    
    def _generate_and_write_typescript(
        self, 
        current_schemas: Dict[str, Dict[str, Any]], 
        report: SyncReport
    ) -> None:
        """Generate and write TypeScript file"""
        typescript_content = self.generator.generate_typescript_file(current_schemas)
        
        self.frontend_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.frontend_output_path.write_text(typescript_content, encoding='utf-8')
        
        report.files_generated = [str(self.frontend_output_path)]
    
    def _restore_backup(self) -> None:
        """Restore backup if sync failed"""
        if self._backup_path.exists():
            self._backup_path.rename(self.frontend_output_path)
    
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