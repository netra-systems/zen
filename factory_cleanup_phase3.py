#!/usr/bin/env python3
"""
Factory Pattern Cleanup Remediation Script - PHASE 3
Fix SSOT Compliance Violations in Factory Imports

This script fixes import fragmentation and ensures all factory imports
follow SSOT principles with canonical import paths.
"""

import os
import re
import shutil
from pathlib import Path

def find_import_violations():
    """Find factory import violations that need SSOT compliance fixes."""
    violations = []

    # Common import fragmentation patterns
    problematic_patterns = [
        # Multiple import paths for the same factory
        (r'from.*execution_engine_unified_factory.*import', 'Use canonical ExecutionEngineFactory'),
        (r'from.*\.factory\..*import.*Factory', 'Use canonical factory import path'),
        (r'import.*factory.*as.*', 'Avoid factory import aliases that hide sources'),

        # Deprecated factory imports that need updating
        (r'from.*deprecated.*factory.*import', 'Remove deprecated factory imports'),
        (r'from.*compatibility.*factory.*import', 'Use canonical factory instead of compatibility wrapper'),
    ]

    print("Scanning for import violations...")

    # Scan relevant directories
    for root, dirs, files in os.walk('./netra_backend/app'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern, description in problematic_patterns:
                        if re.search(pattern, content):
                            violations.append((file_path, pattern, description, content))

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return violations

def fix_execution_engine_factory_imports():
    """Fix imports that reference the removed UnifiedExecutionEngineFactory."""
    files_to_fix = []

    # Find files that import the removed factory
    for root, dirs, files in os.walk('./netra_backend/app'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if 'execution_engine_unified_factory' in content:
                        files_to_fix.append((file_path, content))

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    fixed_count = 0
    for file_path, content in files_to_fix:
        # Backup original
        backup_path = file_path + '.backup_pre_import_fix'
        shutil.copy2(file_path, backup_path)

        # Fix the import
        new_content = content.replace(
            'from netra_backend.app.agents.execution_engine_unified_factory',
            'from netra_backend.app.agents.supervisor.execution_engine_factory'
        ).replace(
            'UnifiedExecutionEngineFactory',
            'ExecutionEngineFactory'
        )

        # Add import comment for clarity
        if new_content != content:
            new_content = new_content.replace(
                'from netra_backend.app.agents.supervisor.execution_engine_factory',
                '# FACTORY CLEANUP REMEDIATION: Updated to use canonical ExecutionEngineFactory\n'
                'from netra_backend.app.agents.supervisor.execution_engine_factory'
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"Fixed imports in: {file_path}")
            fixed_count += 1

    return fixed_count

def consolidate_factory_imports():
    """Consolidate fragmented factory import patterns."""
    import_mappings = {
        # Map old import patterns to canonical ones
        'from netra_backend.app.factories.': 'from netra_backend.app.agents.supervisor.',
        'from netra_backend.app.core.managers.execution_engine_factory': 'from netra_backend.app.agents.supervisor.execution_engine_factory',
        # Add more mappings as needed
    }

    fixed_count = 0
    for root, dirs, files in os.walk('./netra_backend/app'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    original_content = content
                    for old_pattern, new_pattern in import_mappings.items():
                        if old_pattern in content:
                            content = content.replace(old_pattern, new_pattern)

                    if content != original_content:
                        # Backup and update
                        backup_path = file_path + '.backup_pre_import_consolidation'
                        shutil.copy2(file_path, backup_path)

                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                        print(f"Consolidated imports in: {file_path}")
                        fixed_count += 1

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    return fixed_count

def validate_critical_imports():
    """Validate that critical factory imports are working correctly."""
    critical_factories = [
        'netra_backend.app.agents.supervisor.execution_engine_factory.ExecutionEngineFactory',
        'netra_backend.app.agents.supervisor.agent_instance_factory.AgentInstanceFactory',
        'netra_backend.app.agents.tool_executor_factory.ToolExecutorFactory'
    ]

    validation_results = {}

    for factory_import in critical_factories:
        try:
            module_path, class_name = factory_import.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            factory_class = getattr(module, class_name)
            validation_results[factory_import] = "OK"
            print(f"✓ {factory_import} - Valid")
        except Exception as e:
            validation_results[factory_import] = f"ERROR: {e}"
            print(f"✗ {factory_import} - Error: {e}")

    return validation_results

def run_phase3_remediation():
    """Execute Phase 3 - Fix SSOT compliance violations."""
    print("=== FACTORY CLEANUP REMEDIATION PHASE 3 ===")
    print("Fixing SSOT compliance violations in factory imports")
    print("Consolidating import paths to canonical sources")
    print()

    # Step 1: Fix specific import issues from removed factories
    print("1. Fixing imports for removed factories...")
    fixed_imports = fix_execution_engine_factory_imports()
    print(f"   Fixed {fixed_imports} files with import issues")

    # Step 2: Consolidate fragmented import patterns
    print("2. Consolidating fragmented import patterns...")
    consolidated_imports = consolidate_factory_imports()
    print(f"   Consolidated imports in {consolidated_imports} files")

    # Step 3: Validate critical imports still work
    print("3. Validating critical factory imports...")
    validation_results = validate_critical_imports()
    valid_imports = sum(1 for result in validation_results.values() if result == "OK")
    total_imports = len(validation_results)

    print(f"\n=== PHASE 3 REMEDIATION COMPLETE ===")
    print(f"Import fixes applied: {fixed_imports}")
    print(f"Import consolidations: {consolidated_imports}")
    print(f"Import validation: {valid_imports}/{total_imports} passing")

    if valid_imports == total_imports:
        print("\n✓ All critical imports validated successfully")
        print("NEXT STEPS:")
        print("1. Validate system stability")
        print("2. Test Golden Path functionality")
        print("3. Generate metrics improvement report")
    else:
        print("\n⚠ Some import validations failed - manual review needed")

    return {
        'fixed_imports': fixed_imports,
        'consolidated_imports': consolidated_imports,
        'validation_results': validation_results
    }

if __name__ == "__main__":
    results = run_phase3_remediation()
    print(f"\nPhase 3 completed: {results}")