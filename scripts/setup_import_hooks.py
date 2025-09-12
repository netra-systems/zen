#!/usr/bin/env python3
"""
Setup script for import management hooks and tools

This script:
1. Installs pre-commit hooks for import validation
2. Configures git hooks
3. Verifies import management tools are working
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def setup_pre_commit_hook():
    """Install the pre-commit hook for import checking."""
    print("Setting up pre-commit hook for import validation...")
    
    # Source and destination paths
    source_hook = PROJECT_ROOT / '.githooks' / 'pre-commit-imports'
    git_hooks_dir = PROJECT_ROOT / '.git' / 'hooks'
    dest_hook = git_hooks_dir / 'pre-commit'
    
    # Create hooks directory if it doesn't exist
    git_hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if a pre-commit hook already exists
    if dest_hook.exists():
        print(f"   WARNING:  Pre-commit hook already exists at {dest_hook}")
        response = input("  Replace with import checking hook? (y/n): ")
        if response.lower() != 'y':
            print("  Skipping pre-commit hook setup")
            return False
        
        # Backup existing hook
        backup_path = dest_hook.with_suffix('.backup')
        shutil.copy2(dest_hook, backup_path)
        print(f"  Backed up existing hook to {backup_path}")
    
    # Copy the hook
    shutil.copy2(source_hook, dest_hook)
    
    # Make it executable on Unix-like systems
    if sys.platform != 'win32':
        os.chmod(dest_hook, 0o755)
    
    print(f"  [U+2713] Pre-commit hook installed at {dest_hook}")
    print("  To skip import checks: git config hooks.skipimports true")
    print("  To re-enable: git config --unset hooks.skipimports")
    
    return True


def verify_tools():
    """Verify that import management tools are available."""
    print("\nVerifying import management tools...")
    
    tools = [
        ('import_management.py', 'Unified import management'),
        ('fix_all_import_issues.py', 'Import issue fixer'),
        ('fix_comprehensive_imports.py', 'Comprehensive import fixer'),
    ]
    
    scripts_dir = PROJECT_ROOT / 'scripts'
    all_present = True
    
    for tool_name, description in tools:
        tool_path = scripts_dir / tool_name
        if tool_path.exists():
            print(f"  [U+2713] {tool_name}: {description}")
        else:
            print(f"  [U+2717] {tool_name}: NOT FOUND")
            all_present = False
    
    return all_present


def test_import_check():
    """Run a quick import check to verify the system works."""
    print("\nRunning import check...")
    
    try:
        cmd = [sys.executable, str(PROJECT_ROOT / 'scripts' / 'import_management.py'), 'check']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if 'Total Errors Found:' in result.stdout:
            # Extract error count
            for line in result.stdout.split('\n'):
                if 'Total Errors Found:' in line:
                    error_count = line.split(':')[1].strip()
                    print(f"  Import check completed. Errors found: {error_count}")
                    
                    if int(error_count) > 0:
                        print(f"   WARNING:  {error_count} import errors detected")
                        print("  Run 'python scripts/import_management.py fix' to fix them")
                    else:
                        print("  [U+2713] No import errors detected!")
                    return True
        
        print("   WARNING:  Could not parse import check results")
        return False
        
    except subprocess.TimeoutExpired:
        print("  [U+2717] Import check timed out")
        return False
    except Exception as e:
        print(f"  [U+2717] Import check failed: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("IMPORT MANAGEMENT SETUP")
    print("=" * 60)
    
    # Check if we're in a git repository
    if not (PROJECT_ROOT / '.git').exists():
        print(" FAIL:  Not in a git repository. Please run from project root.")
        return 1
    
    # Setup pre-commit hook
    hook_installed = setup_pre_commit_hook()
    
    # Verify tools
    tools_available = verify_tools()
    
    # Run test check
    check_success = test_import_check()
    
    # Summary
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    
    if hook_installed:
        print("[U+2713] Pre-commit hook installed")
    else:
        print(" WARNING:  Pre-commit hook not installed")
    
    if tools_available:
        print("[U+2713] All import management tools available")
    else:
        print(" WARNING:  Some tools missing")
    
    if check_success:
        print("[U+2713] Import checking system functional")
    else:
        print(" WARNING:  Import checking needs attention")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Fix any existing import issues:")
    print("   python scripts/import_management.py fix")
    print("\n2. Check import status:")
    print("   python scripts/import_management.py check")
    print("\n3. Run comprehensive workflow:")
    print("   python scripts/import_management.py all")
    print("\n4. View detailed documentation:")
    print("   cat SPEC/learnings/import_management.xml")
    
    return 0 if (hook_installed and tools_available) else 1


if __name__ == '__main__':
    sys.exit(main())