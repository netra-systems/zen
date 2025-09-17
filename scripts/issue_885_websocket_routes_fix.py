#!/usr/bin/env python3
"""
Issue #885 Phase 1b: WebSocket Routes Import Fix

Fix the WebSocket routes import to use canonical SSOT pattern.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: SSOT compliance in critical WebSocket routes
- Value Impact: Fix import violation in primary WebSocket endpoint
- Revenue Impact: Protect $500K+ ARR Golden Path functionality
"""

import os
import re
import sys
import subprocess
from pathlib import Path
import shutil

def create_backup(repo_path: Path) -> Path:
    """Create backup of websocket routes file."""
    timestamp = subprocess.check_output(['powershell', 'Get-Date -Format "yyyyMMdd_HHmmss"'],
                                      text=True).strip()
    backup_dir = repo_path / "backups" / f"websocket_routes_import_fix_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating backup at: {backup_dir}")

    # Backup the specific file
    source_file = repo_path / "netra_backend/app/routes/websocket.py"
    if source_file.exists():
        dest_file = backup_dir / "websocket.py"
        shutil.copy2(source_file, dest_file)
        print(f"Backup created: {backup_dir}")
        return backup_dir
    else:
        print(f"ERROR: Source file not found: {source_file}")
        return None

def apply_import_fix(repo_path: Path) -> bool:
    """Apply the specific import fix to websocket routes."""
    target_file = repo_path / "netra_backend/app/routes/websocket.py"

    if not target_file.exists():
        print(f"ERROR: Target file not found: {target_file}")
        return False

    try:
        # Read the file with encoding fallback
        content = None
        for encoding in ['utf-8', 'cp1252', 'latin-1']:
            try:
                with open(target_file, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            print(f"ERROR: Could not decode {target_file}")
            return False

        original_content = content

        # Apply the specific import replacement
        old_import = "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager"
        new_import = "from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager"

        if old_import in content:
            content = content.replace(old_import, new_import)
            print(f"SUCCESS: Replaced import in websocket routes")

            # Write back the file
            with open(target_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)

            return True
        else:
            print(f"Import pattern not found in {target_file}")
            print("Current imports in file:")
            lines = content.split('\n')
            for i, line in enumerate(lines[:50], 1):
                if 'import' in line and 'websocket' in line.lower():
                    print(f"  Line {i}: {line.strip()}")
            return False

    except Exception as e:
        print(f"ERROR: Failed to process {target_file}: {e}")
        return False

def validate_syntax(repo_path: Path) -> bool:
    """Validate syntax of the modified file."""
    target_file = repo_path / "netra_backend/app/routes/websocket.py"

    try:
        result = subprocess.run([sys.executable, "-m", "py_compile", str(target_file)],
                              capture_output=True, text=True, cwd=repo_path)
        if result.returncode == 0:
            print("SUCCESS: Syntax validation passed")
            return True
        else:
            print(f"ERROR: Syntax validation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"ERROR: Could not validate syntax: {e}")
        return False

def run_import_test(repo_path: Path) -> bool:
    """Test that the import works correctly."""
    test_script = """
try:
    from netra_backend.app.routes.websocket import router
    print("SUCCESS: WebSocket routes import test passed")
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")
    exit(1)
"""

    try:
        result = subprocess.run([sys.executable, "-c", test_script],
                              capture_output=True, text=True, cwd=repo_path, timeout=30)
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(f"ERROR: Import test failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("ERROR: Import test timed out")
        return False
    except Exception as e:
        print(f"ERROR: Could not run import test: {e}")
        return False

def rollback_changes(backup_dir: Path, repo_path: Path) -> bool:
    """Rollback changes from backup."""
    if not backup_dir or not backup_dir.exists():
        print(f"ERROR: Backup directory not found: {backup_dir}")
        return False

    try:
        backup_file = backup_dir / "websocket.py"
        target_file = repo_path / "netra_backend/app/routes/websocket.py"

        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            print(f"SUCCESS: Restored from backup: {backup_file}")
            return True
        else:
            print(f"ERROR: Backup file not found: {backup_file}")
            return False
    except Exception as e:
        print(f"ERROR: Rollback failed: {e}")
        return False

def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python issue_885_websocket_routes_fix.py <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1])

    print("Issue #885 Phase 1b: WebSocket Routes Import Fix")
    print("=" * 50)

    try:
        # Step 1: Create backup
        backup_dir = create_backup(repo_path)
        if not backup_dir:
            print("ERROR: Could not create backup")
            sys.exit(1)

        # Step 2: Apply import fix
        if not apply_import_fix(repo_path):
            print("ERROR: Import fix failed")
            rollback_changes(backup_dir, repo_path)
            sys.exit(1)

        # Step 3: Validate syntax
        if not validate_syntax(repo_path):
            print("ERROR: Syntax validation failed, rolling back")
            rollback_changes(backup_dir, repo_path)
            sys.exit(1)

        # Step 4: Test imports
        if not run_import_test(repo_path):
            print("ERROR: Import test failed, rolling back")
            rollback_changes(backup_dir, repo_path)
            sys.exit(1)

        # Success!
        print("\n" + "=" * 50)
        print("SUCCESS: Phase 1b WebSocket Routes Import Fix completed!")
        print("Fixed: netra_backend/app/routes/websocket.py")
        print(f"Backup: {backup_dir}")
        print("\nNext steps:")
        print("1. Commit this atomic change")
        print("2. Continue with additional import consolidations")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        if 'backup_dir' in locals() and backup_dir:
            rollback_changes(backup_dir, repo_path)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if 'backup_dir' in locals() and backup_dir:
            rollback_changes(backup_dir, repo_path)
        sys.exit(1)

if __name__ == "__main__":
    main()