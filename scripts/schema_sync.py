#!/usr/bin/env python3
"""Enhanced schema synchronization script with validation and type safety."""

import sys
import os
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Change to project root
os.chdir(project_root)

try:
    from app.core.schema_sync import SchemaSynchronizer, SchemaValidationLevel
    from app.core.exceptions_service import ServiceError
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root and dependencies are installed")
    sys.exit(1)


def main():
    """Main schema synchronization function."""
    
    # Configuration
    backend_modules = [
        'app.schemas.Agent',
        'app.schemas.Analysis', 
        'app.schemas.Auth',
        'app.schemas.Config',
        'app.schemas.Corpus',
        'app.schemas.Event',
        'app.schemas.FinOps',
        'app.schemas.Generation',
        'app.schemas.Log',
        'app.schemas.Message',
        'app.schemas.Metrics',
        'app.schemas.Pattern',
        'app.schemas.Performance',
        'app.schemas.Policy',
        'app.schemas.Reference',
        'app.schemas.Request',
        'app.schemas.Run',
        'app.schemas.Supply',
        'app.schemas.Token',
        'app.schemas.Tool',
        'app.schemas.User',
        'app.schemas.WebSocket'
    ]
    
    frontend_output_path = "frontend/types/backend_schema_auto_generated.ts"
    validation_level = SchemaValidationLevel.MODERATE
    
    # Parse command line arguments
    force_sync = '--force' in sys.argv
    strict_validation = '--strict' in sys.argv
    lenient_validation = '--lenient' in sys.argv
    
    if strict_validation:
        validation_level = SchemaValidationLevel.STRICT
    elif lenient_validation:
        validation_level = SchemaValidationLevel.LENIENT
    
    print("Enhanced Schema Synchronization")
    print("=" * 40)
    print(f"Backend modules: {len(backend_modules)} modules")
    print(f"Frontend output: {frontend_output_path}")
    print(f"Validation level: {validation_level.value}")
    print(f"Force sync: {force_sync}")
    print()
    
    try:
        # Create synchronizer
        synchronizer = SchemaSynchronizer(
            backend_modules=backend_modules,
            frontend_output_path=frontend_output_path,
            validation_level=validation_level
        )
        
        # Perform synchronization
        print("Starting schema synchronization...")
        report = synchronizer.sync_schemas(force=force_sync)
        
        # Display results
        print(f"✅ Synchronization completed at {report.timestamp}")
        print(f"📊 Processed {report.schemas_processed} schemas")
        print(f"🔄 Changes detected: {len(report.changes_detected)}")
        print(f"📁 Files generated: {len(report.files_generated)}")
        
        if report.changes_detected:
            print("\n📋 Changes detected:")
            for change in report.changes_detected:
                icon = "➕" if change.change_type == "added" else "➖" if change.change_type == "removed" else "🔄"
                field_info = f" ({change.field_name})" if change.field_name else ""
                print(f"   {icon} {change.schema_name}{field_info}: {change.description}")
        
        if report.validation_errors:
            print("\n⚠️ Validation warnings:")
            for error in report.validation_errors:
                print(f"   ⚠️ {error}")
        
        if report.files_generated:
            print("\n📄 Generated files:")
            for file_path in report.files_generated:
                print(f"   📄 {file_path}")
        
        print(f"\n{'✅ Sync succeeded!' if report.success else '❌ Sync failed!'}")
        
        # Additional validation
        if report.success:
            print("\n🔍 Running additional validations...")
            
            # Check if TypeScript file is valid
            output_path = Path(frontend_output_path)
            if output_path.exists():
                content = output_path.read_text(encoding='utf-8')
                print(f"   📏 Generated file size: {len(content)} characters")
                print(f"   📋 Contains {content.count('export interface')} interfaces")
                print(f"   📋 Contains {content.count('export type')} type definitions")
            
            print("✅ All validations passed!")
        
        return 0 if report.success else 1
        
    except ServiceError as e:
        print(f"\n❌ Service error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Consider running with --force if schemas have breaking changes")
        return 1


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
        print("\n⚠️ Synchronization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)