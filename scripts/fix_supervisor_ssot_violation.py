#!/usr/bin/env python
"""Fix SSOT violation: Consolidate all SupervisorAgent imports to use supervisor_consolidated.py"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_files_with_supervisor_imports(root_dir: Path) -> List[Path]:
    """Find all Python files that import SupervisorAgent."""
    files = []
    
    # Patterns to match
    patterns = [
        r'from\s+netra_backend\.app\.agents\.supervisor_agent\s+import',
        r'from\s+netra_backend\.app\.agents\.supervisor_agent_modern\s+import',
        r'import\s+netra_backend\.app\.agents\.supervisor_agent',
        r'import\s+netra_backend\.app\.agents\.supervisor_agent_modern',
    ]
    
    # Only scan relevant directories
    dirs_to_scan = [
        root_dir / "netra_backend",
        root_dir / "tests",
        root_dir / "scripts",
        root_dir / "docs",
    ]
    
    for scan_dir in dirs_to_scan:
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*.py"):
            # Skip the files we're going to delete
            if path.name in ['supervisor_agent.py', 'supervisor_agent_modern.py']:
                if 'netra_backend/app/agents' in str(path).replace('\\', '/'):
                    continue
                    
            try:
                content = path.read_text(encoding='utf-8')
                for pattern in patterns:
                    if re.search(pattern, content):
                        files.append(path)
                        break
            except Exception as e:
                print(f"Error reading {path}: {e}")
    
    return files

def update_imports_in_file(file_path: Path) -> Tuple[bool, str]:
    """Update imports in a single file to use supervisor_consolidated."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Replace supervisor_agent imports
        content = re.sub(
            r'from\s+netra_backend\.app\.agents\.supervisor_agent\s+import\s+SupervisorAgent',
            'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent',
            content
        )
        
        # Replace supervisor_agent_modern imports
        content = re.sub(
            r'from\s+netra_backend\.app\.agents\.supervisor_agent_modern\s+import\s+SupervisorAgent',
            'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent',
            content
        )
        
        # Replace module-level imports
        content = re.sub(
            r'import\s+netra_backend\.app\.agents\.supervisor_agent\s+as\s+(\w+)',
            r'import netra_backend.app.agents.supervisor_consolidated as \1',
            content
        )
        
        content = re.sub(
            r'import\s+netra_backend\.app\.agents\.supervisor_agent_modern\s+as\s+(\w+)',
            r'import netra_backend.app.agents.supervisor_consolidated as \1',
            content
        )
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True, "Updated"
        else:
            return False, "No changes needed"
            
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main function to fix SSOT violations."""
    root_dir = Path(__file__).parent.parent
    
    print("=== SSOT Violation Fix: Consolidating SupervisorAgent Imports ===\n")
    
    # Find all files with incorrect imports
    print("Scanning for files with SupervisorAgent imports...")
    files = find_files_with_supervisor_imports(root_dir)
    
    print(f"Found {len(files)} files with SupervisorAgent imports\n")
    
    # Update imports
    updated_count = 0
    error_count = 0
    
    for file_path in files:
        rel_path = file_path.relative_to(root_dir)
        success, message = update_imports_in_file(file_path)
        
        if success:
            print(f"[UPDATED] {rel_path}: {message}")
            updated_count += 1
        elif "No changes" in message:
            print(f"[SKIP] {rel_path}: {message}")
        else:
            print(f"[ERROR] {rel_path}: {message}")
            error_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Files updated: {updated_count}")
    print(f"Files unchanged: {len(files) - updated_count - error_count}")
    print(f"Errors: {error_count}")
    
    # Files to remove
    files_to_remove = [
        root_dir / "netra_backend" / "app" / "agents" / "supervisor_agent.py",
        root_dir / "netra_backend" / "app" / "agents" / "supervisor_agent_modern.py",
    ]
    
    print(f"\n=== Files to Remove (Legacy/Redundant) ===")
    for file_path in files_to_remove:
        if file_path.exists():
            print(f"- {file_path.relative_to(root_dir)}")
    
    print("\nRun the following commands to remove redundant files:")
    print("del netra_backend\\app\\agents\\supervisor_agent.py")
    print("del netra_backend\\app\\agents\\supervisor_agent_modern.py")
    
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    exit(main())