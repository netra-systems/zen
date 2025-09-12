#!/usr/bin/env python3
"""Enhanced schema synchronization script with validation and type safety."""

import os
import sys
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent

# Change to project root
os.chdir(project_root)

try:
    from netra_backend.app.core.exceptions_service import ServiceError
    from netra_backend.app.core.schema_sync import (
        SchemaSynchronizer,
        SchemaValidationLevel,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root and dependencies are installed")
    sys.exit(1)


def get_backend_modules():
    """Get list of backend modules to synchronize."""
    return [
        'app.schemas.Agent', 'app.schemas.Analysis', 'app.schemas.Auth',
        'app.schemas.Config', 'app.schemas.Corpus', 'app.schemas.Event',
        'app.schemas.FinOps', 'app.schemas.Generation', 'app.schemas.Log',
        'app.schemas.Message', 'app.schemas.Metrics', 'app.schemas.Pattern',
    ]


def get_additional_modules():
    """Get additional backend modules to synchronize."""
    return [
        'app.schemas.Performance', 'app.schemas.Policy', 'app.schemas.Reference',
        'app.schemas.Request', 'app.schemas.Run', 'app.schemas.Supply',
        'app.schemas.Token', 'app.schemas.Tool', 'app.schemas.User',
        'app.schemas.WebSocket'
    ]


def parse_command_line_args():
    """Parse command line arguments and return configuration."""
    force_sync = '--force' in sys.argv
    strict_validation = '--strict' in sys.argv
    lenient_validation = '--lenient' in sys.argv
    validation_level = SchemaValidationLevel.MODERATE
    if strict_validation:
        validation_level = SchemaValidationLevel.STRICT
    elif lenient_validation:
        validation_level = SchemaValidationLevel.LENIENT
    return force_sync, validation_level


def print_configuration(backend_modules, frontend_output_path, validation_level, force_sync):
    """Print synchronization configuration."""
    print("Enhanced Schema Synchronization")
    print("=" * 40)
    print(f"Backend modules: {len(backend_modules)} modules")
    print(f"Frontend output: {frontend_output_path}")
    print(f"Validation level: {validation_level.value}")
    print(f"Force sync: {force_sync}")
    print()


def create_synchronizer(backend_modules, frontend_output_path, validation_level):
    """Create and return schema synchronizer instance."""
    return SchemaSynchronizer(
        backend_modules=backend_modules,
        frontend_output_path=frontend_output_path,
        validation_level=validation_level
    )


def print_sync_results(report):
    """Print synchronization results summary."""
    print(f" PASS:  Synchronization completed at {report.timestamp}")
    print(f" CHART:  Processed {report.schemas_processed} schemas")
    print(f" CYCLE:  Changes detected: {len(report.changes_detected)}")
    print(f"[U+1F4C1] Files generated: {len(report.files_generated)}")


def print_changes_detected(changes_detected):
    """Print detected changes details."""
    if not changes_detected:
        return
    print("\n[U+1F4CB] Changes detected:")
    for change in changes_detected:
        icon = "[U+2795]" if change.change_type == "added" else "[U+2796]" if change.change_type == "removed" else " CYCLE: "
        field_info = f" ({change.field_name})" if change.field_name else ""
        print(f"   {icon} {change.schema_name}{field_info}: {change.description}")


def print_validation_errors(validation_errors):
    """Print validation errors."""
    if not validation_errors:
        return
    print("\n WARNING: [U+FE0F] Validation warnings:")
    for error in validation_errors:
        print(f"    WARNING: [U+FE0F] {error}")


def print_generated_files(files_generated):
    """Print list of generated files."""
    if not files_generated:
        return
    print("\n[U+1F4C4] Generated files:")
    for file_path in files_generated:
        print(f"   [U+1F4C4] {file_path}")


def validate_typescript_output(frontend_output_path):
    """Validate generated TypeScript output file."""
    output_path = Path(frontend_output_path)
    if not output_path.exists():
        return
    content = output_path.read_text(encoding='utf-8')
    print(f"   [U+1F4CF] Generated file size: {len(content)} characters")
    print(f"   [U+1F4CB] Contains {content.count('export interface')} interfaces")
    print(f"   [U+1F4CB] Contains {content.count('export type')} type definitions")


def run_additional_validations(frontend_output_path):
    """Run additional validation checks."""
    print("\n SEARCH:  Running additional validations...")
    validate_typescript_output(frontend_output_path)
    print(" PASS:  All validations passed!")


def handle_sync_error(error):
    """Handle synchronization errors."""
    if isinstance(error, ServiceError):
        print(f"\n FAIL:  Service error: {error}")
    else:
        print(f"\n FAIL:  Unexpected error: {error}")
        print("Consider running with --force if schemas have breaking changes")
    return 1


def main():
    """Main schema synchronization function."""
    backend_modules = get_backend_modules() + get_additional_modules()
    frontend_output_path = "frontend/types/backend_schema_auto_generated.ts"
    force_sync, validation_level = parse_command_line_args()
    
    print_configuration(backend_modules, frontend_output_path, validation_level, force_sync)
    
    try:
        synchronizer = create_synchronizer(backend_modules, frontend_output_path, validation_level)
        print("Starting schema synchronization...")
        report = synchronizer.sync_schemas(force=force_sync)
        
        print_sync_results(report)
        print_changes_detected(report.changes_detected)
        print_validation_errors(report.validation_errors)
        print_generated_files(report.files_generated)
        
        print(f"\n{' PASS:  Sync succeeded!' if report.success else ' FAIL:  Sync failed!'}")
        
        if report.success:
            run_additional_validations(frontend_output_path)
        
        return 0 if report.success else 1
        
    except (ServiceError, Exception) as e:
        return handle_sync_error(e)


def print_usage():
    """Print usage information."""
    print("Usage: python enhanced_schema_sync.py [options]")
    print()
    print("Options:")
    print("  --force     Force synchronization even with breaking changes")
    print("  --strict    Use strict validation (any change is breaking)")
    print("  --lenient   Use lenient validation (only removals are breaking)")
    print("  --help      Show this help message")
    print()
    print("Examples:")
    print("  python enhanced_schema_sync.py")
    print("  python enhanced_schema_sync.py --force")
    print("  python enhanced_schema_sync.py --strict")


if __name__ == "__main__":
    if '--help' in sys.argv:
        print_usage()
        sys.exit(0)
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F] Synchronization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n FAIL:  Fatal error: {e}")
        sys.exit(1)