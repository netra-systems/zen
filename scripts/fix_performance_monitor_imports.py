#!/usr/bin/env python3
"""Fix all incorrect PerformanceMonitor imports after refactoring.

This script addresses the issue where PerformanceMonitor was removed from
performance_monitor.py during system consolidation, but test files weren't updated.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file.
    
    Returns True if changes were made, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    changes_made = False
    
    # Pattern 1: Fix the main PerformanceMonitor import
    # Old: from netra_backend.app.monitoring.performance_monitor import PerformanceMonitor as PerformanceMetric
    # New: from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
    pattern1 = r'from netra_backend\.app\.monitoring\.performance_monitor import PerformanceMonitor as PerformanceMetric'
    replacement1 = 'from netra_backend.app.monitoring.metrics_collector import PerformanceMetric'
    
    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        changes_made = True
        print(f"Fixed import in {file_path}: monitoring.performance_monitor -> metrics_collector")
    
    # Pattern 2: Fix websocket performance monitor imports
    # Old: from netra_backend.app.websocket_core.performance_monitor import PerformanceMonitor
    # New: from netra_backend.app.monitoring.system_monitor import SystemPerformanceMonitor as PerformanceMonitor
    pattern2 = r'from netra_backend\.app\.websocket_core\.performance_monitor import PerformanceMonitor'
    replacement2 = 'from netra_backend.app.monitoring.system_monitor import SystemPerformanceMonitor as PerformanceMonitor'
    
    if re.search(pattern2, content):
        content = re.sub(pattern2, replacement2, content)
        changes_made = True
        print(f"Fixed import in {file_path}: websocket_core.performance_monitor -> system_monitor")
    
    # Pattern 3: Fix any direct PerformanceMonitor imports from monitoring.performance_monitor
    # Old: from netra_backend.app.monitoring.performance_monitor import (
    # This needs special handling for multiline imports
    pattern3 = r'from netra_backend\.app\.monitoring\.performance_monitor import \('
    if re.search(pattern3, content):
        # Find the complete import statement (can be multiline)
        import_match = re.search(
            r'from netra_backend\.app\.monitoring\.performance_monitor import \([^)]+\)',
            content,
            re.MULTILINE | re.DOTALL
        )
        if import_match:
            import_statement = import_match.group()
            # Check what's being imported
            if 'PerformanceMonitor' in import_statement:
                # Replace with SystemPerformanceMonitor
                new_import = 'from netra_backend.app.monitoring.system_monitor import (\n    SystemPerformanceMonitor as PerformanceMonitor,\n)'
                content = content.replace(import_statement, new_import)
                changes_made = True
                print(f"Fixed multiline import in {file_path}")
    
    # Pattern 4: Update the fix_e2e_imports.py script itself
    if 'fix_e2e_imports.py' in str(file_path):
        # This file contains the wrong import path in its config
        pattern4 = r"'PerformanceMetric': 'from netra_backend\.app\.monitoring\.performance_monitor import PerformanceMonitor as PerformanceMetric'"
        replacement4 = "'PerformanceMetric': 'from netra_backend.app.monitoring.metrics_collector import PerformanceMetric'"
        
        if re.search(pattern4, content):
            content = re.sub(pattern4, replacement4, content)
            changes_made = True
            print(f"Fixed import config in {file_path}")
    
    # Write back if changes were made
    if changes_made:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False
    
    return False

def find_files_to_fix() -> List[Path]:
    """Find all Python files that need fixing."""
    root_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
    
    # Files identified from the grep search
    files_to_check = [
        'netra_backend/tests/websocket/test_websocket_integration_performance.py',
        'netra_backend/tests/unit/test_metrics_collector_core.py',
        'netra_backend/tests/unified_system/test_service_recovery.py',
        'scripts/fix_e2e_imports.py',
        'netra_backend/tests/unified_system/test_dev_launcher_startup.py',
        'netra_backend/tests/clickhouse/metrics_aggregation_tests.py',
        'netra_backend/tests/clickhouse/test_query_correctness.py',
        'netra_backend/tests/clickhouse/test_performance_metrics_extraction.py',
        'netra_backend/tests/e2e/test_complete_real_pipeline_e2e.py',
        'netra_backend/tests/integration/critical_paths/test_billing_accuracy_l4.py',
        'netra_backend/tests/performance/performance_baseline_config.py',
        'netra_backend/tests/performance/test_agent_load_stress.py',
        'netra_backend/tests/performance/test_comprehensive_backend_performance.py',
        'tests/e2e/agent_startup_performance_measurer.py',
        'netra_backend/tests/performance/test_sla_compliance.py',
        'tests/e2e/test_soak_testing.py',
        'netra_backend/tests/performance/test_performance_monitoring.py',
        'netra_backend/tests/integration/critical_paths/test_dashboard_query_performance.py',
        'tests/e2e/service_failure_tester.py',
        'tests/e2e/performance/test_performance_sla_validation.py',
        'tests/e2e/test_concurrent_agent_startup_core.py',
        'tests/e2e/test_concurrent_agent_startup_performance.py',
        'netra_backend/tests/integration/critical_paths/test_performance_scalability_l2.py',
    ]
    
    return [root_dir / f for f in files_to_check if (root_dir / f).exists()]

def main():
    """Main execution function."""
    print("=" * 60)
    print("FIXING PERFORMANCE MONITOR IMPORTS")
    print("=" * 60)
    
    files = find_files_to_fix()
    print(f"\nFound {len(files)} files to check")
    
    fixed_count = 0
    for file_path in files:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: Fixed {fixed_count} files")
    print("=" * 60)
    
    if fixed_count > 0:
        print("\nNext steps:")
        print("1. Run tests to verify fixes: python unified_test_runner.py --category database --fast-fail")
        print("2. Document the learning to prevent future regressions")
    
    return 0

if __name__ == "__main__":
    exit(main())