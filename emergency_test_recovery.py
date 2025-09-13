#!/usr/bin/env python3
"""
EMERGENCY TEST RECOVERY SCRIPT

Restores all test files corrupted by commit 247052097 (linting disaster).
This script reverses the mass corruption that added empty lines throughout test files.

BUSINESS IMPACT:
- 573+ test files with syntax errors
- ZERO test coverage for $500K+ ARR functionality  
- Production deployment blocked
- Complete test infrastructure collapse

RECOVERY STRATEGY:
1. Get list of all corrupted files from the bad commit
2. Restore each file to its pre-corruption state
3. Validate syntax of restored files
4. Report recovery status

Usage:
    python3 emergency_test_recovery.py [--dry-run] [--priority-only]
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple, Set

# Critical files that MUST be restored first (Golden Path revenue protection)
PRIORITY_FILES = {
    'tests/mission_critical/test_websocket_agent_events_suite.py',
    'tests/staging/test_staging_websocket_agent_events.py', 
    'tests/integration/test_websocket_agent_events_integration.py',
    'tests/e2e/test_websocket_dev_docker_connection.py',
    'tests/mission_critical/test_no_ssot_violations.py',
    'tests/mission_critical/test_orchestration_integration.py',
}

CORRUPTION_COMMIT = '247052097'  # The linting disaster commit
GOOD_COMMIT = '247052097^'      # The commit before corruption


def run_command(cmd: List[str], capture_output=True) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, cwd=os.getcwd())
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_corrupted_files() -> List[str]:
    """Get list of all files corrupted by the linting disaster."""
    cmd = ['git', 'diff', '--name-only', f'{GOOD_COMMIT}..{CORRUPTION_COMMIT}']
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"ERROR: Failed to get corrupted files: {stderr}")
        return []
    
    # Filter for Python files only
    files = [f.strip() for f in stdout.split('\n') if f.strip().endswith('.py')]
    return files


def check_file_syntax(filepath: str) -> bool:
    """Check if a Python file has valid syntax."""
    cmd = ['python3', '-m', 'py_compile', filepath]
    exit_code, stdout, stderr = run_command(cmd)
    return exit_code == 0


def restore_file(filepath: str) -> bool:
    """Restore a single file to its pre-corruption state."""
    print(f"Restoring: {filepath}")
    
    # Check if file exists
    if not os.path.exists(filepath):
        print(f"  WARNING: File does not exist: {filepath}")
        return False
    
    # Restore from good commit
    cmd = ['git', 'checkout', GOOD_COMMIT, '--', filepath]
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"  ERROR: Failed to restore {filepath}: {stderr}")
        return False
    
    # Verify syntax
    if check_file_syntax(filepath):
        print(f"  SUCCESS: {filepath} restored and validated")
        return True
    else:
        print(f"  WARNING: {filepath} restored but still has syntax errors")
        return False


def main():
    """Main recovery function."""
    import argparse
    parser = argparse.ArgumentParser(description='Emergency test file recovery')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be restored without making changes')
    parser.add_argument('--priority-only', action='store_true',
                       help='Only restore priority files')
    args = parser.parse_args()
    
    print("🚨 EMERGENCY TEST RECOVERY - MISSION CRITICAL")
    print("=" * 60)
    print(f"Corruption commit: {CORRUPTION_COMMIT}")
    print(f"Restoring from:    {GOOD_COMMIT}")
    print()
    
    # Get list of corrupted files
    print("📋 Getting list of corrupted files...")
    corrupted_files = get_corrupted_files()
    
    if not corrupted_files:
        print("ERROR: No corrupted files found!")
        sys.exit(1)
    
    print(f"Found {len(corrupted_files)} corrupted Python files")
    
    # Filter for priority files if requested
    if args.priority_only:
        files_to_restore = [f for f in corrupted_files if f in PRIORITY_FILES]
        print(f"Priority mode: restoring {len(files_to_restore)} critical files")
    else:
        files_to_restore = corrupted_files
        
    # Show priority files first
    priority_found = [f for f in files_to_restore if f in PRIORITY_FILES]
    if priority_found:
        print(f"\n🚨 PRIORITY FILES (Golden Path revenue protection):")
        for f in priority_found:
            print(f"  - {f}")
    
    print(f"\n📁 Files to restore: {len(files_to_restore)}")
    
    if args.dry_run:
        print("\n--dry-run mode: showing files that would be restored")
        for filepath in files_to_restore:
            print(f"  Would restore: {filepath}")
        return
    
    # Restore files
    print(f"\n🔧 RESTORING {len(files_to_restore)} FILES...")
    restored_count = 0
    failed_count = 0
    
    for filepath in files_to_restore:
        try:
            if restore_file(filepath):
                restored_count += 1
            else:
                failed_count += 1
        except KeyboardInterrupt:
            print("\n\nRestoration interrupted by user")
            break
        except Exception as e:
            print(f"  UNEXPECTED ERROR: {filepath}: {e}")
            failed_count += 1
    
    # Final report
    print(f"\n📊 RECOVERY SUMMARY")
    print("=" * 40)
    print(f"Successfully restored: {restored_count}")
    print(f"Failed to restore:     {failed_count}")
    print(f"Total files:           {len(files_to_restore)}")
    
    if restored_count > 0:
        print("\n✅ RECOVERY SUCCESSFUL - Test infrastructure partially restored!")
        print("\nNext steps:")
        print("1. Run mission-critical tests: python3 tests/mission_critical/test_websocket_agent_events_suite.py")
        print("2. Check staging tests: python3 tests/staging_real_tests.py")
        print("3. Validate unit test infrastructure")
        
        # Run a quick validation
        print("\n🔍 VALIDATION CHECK...")
        sample_files = files_to_restore[:5]  # Check first 5 restored files
        validation_passed = 0
        for filepath in sample_files:
            if check_file_syntax(filepath):
                validation_passed += 1
                print(f"  ✅ {filepath}")
            else:
                print(f"  ❌ {filepath}")
                
        print(f"\nValidation: {validation_passed}/{len(sample_files)} files passed syntax check")
        
    else:
        print("\n❌ RECOVERY FAILED - No files restored successfully")
        sys.exit(1)


if __name__ == '__main__':
    main()