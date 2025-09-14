#!/usr/bin/env python3
"""
DeepAgentState SSOT Import Remediation Script

This script systematically replaces all broken DeepAgentState imports with the correct SSOT import.
Broken: from netra_backend.app.agents.state import DeepAgentState
Correct: from netra_backend.app.schemas.agent_models import DeepAgentState
"""

import os
import re
import subprocess
from pathlib import Path

def find_files_with_broken_imports():
    """Find all files with broken DeepAgentState imports."""
    cmd = [
        'grep', '-r',
        'from netra_backend.app.agents.state import.*DeepAgentState',
        '.',
        '--include=*.py',
        '--exclude-dir=backups',
        '--exclude-dir=.venv',
        '--exclude-dir=venv'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
        lines = result.stdout.strip().split('\n')
        files = []

        for line in lines:
            if ':' in line and line.strip():
                # Skip commented lines
                if line.strip().startswith('#'):
                    continue

                file_path = line.split(':', 1)[0]
                if file_path and os.path.exists(file_path):
                    files.append(file_path)

        return list(set(files))  # Remove duplicates
    except Exception as e:
        print(f"Error finding files: {e}")
        return []

def fix_imports_in_file(file_path):
    """Fix DeepAgentState imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: Direct import
        pattern1 = r'from netra_backend\.app\.agents\.state import DeepAgentState'
        replacement1 = 'from netra_backend.app.schemas.agent_models import DeepAgentState'
        content = re.sub(pattern1, replacement1, content)

        # Pattern 2: Multi-import with DeepAgentState
        pattern2 = r'from netra_backend\.app\.agents\.state import ([^,\n]*,\s*)*DeepAgentState([^,\n]*,\s*)*([^,\n]*)'

        def replace_multi_import(match):
            full_match = match.group(0)
            # Extract all imports
            imports_part = full_match.split('import ', 1)[1]
            imports = [imp.strip() for imp in imports_part.split(',')]

            # Separate DeepAgentState from others
            other_imports = [imp for imp in imports if imp != 'DeepAgentState' and imp]

            lines = []
            if other_imports:
                lines.append(f"from netra_backend.app.agents.state import {', '.join(other_imports)}")
            lines.append("from netra_backend.app.schemas.agent_models import DeepAgentState")

            return '\n'.join(lines)

        content = re.sub(pattern2, replace_multi_import, content)

        # Pattern 3: Import with AgentMetadata (common case)
        pattern3 = r'from netra_backend\.app\.agents\.state import AgentMetadata,\s*DeepAgentState'
        replacement3 = 'from netra_backend.app.agents.state import AgentMetadata\nfrom netra_backend.app.schemas.agent_models import DeepAgentState'
        content = re.sub(pattern3, replacement3, content)

        pattern4 = r'from netra_backend\.app\.agents\.state import DeepAgentState,\s*AgentMetadata'
        replacement4 = 'from netra_backend.app.agents.state import AgentMetadata\nfrom netra_backend.app.schemas.agent_models import DeepAgentState'
        content = re.sub(pattern4, replacement4, content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main execution function."""
    print("Starting DeepAgentState SSOT Import Remediation...")

    # Find all files with broken imports
    print("Finding files with broken imports...")
    files_to_fix = find_files_with_broken_imports()

    if not files_to_fix:
        print("No files found with broken imports!")
        return

    print(f"Found {len(files_to_fix)} files to fix")

    # Fix files in batches
    batch_size = 50
    fixed_count = 0

    for i in range(0, len(files_to_fix), batch_size):
        batch = files_to_fix[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} files)...")

        for file_path in batch:
            if fix_imports_in_file(file_path):
                fixed_count += 1
                print(f"  Fixed: {file_path}")
            else:
                print(f"  No changes: {file_path}")

    print(f"\nRemediation complete! Fixed {fixed_count} files.")

    # Verify fix
    print("\nVerifying fixes...")
    remaining_files = find_files_with_broken_imports()

    if remaining_files:
        print(f"{len(remaining_files)} files still have issues:")
        for file in remaining_files[:10]:  # Show first 10
            print(f"  - {file}")
    else:
        print("All imports fixed successfully!")

if __name__ == "__main__":
    main()