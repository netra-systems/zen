#!/usr/bin/env python3
"""
Final comprehensive cleanup of DeepAgentState imports
"""
import os
import re
import subprocess

def get_active_imports():
    """Find files with active DeepAgentState imports."""
    try:
        # Find all files with the problematic import
        result = subprocess.run([
            'grep', '-r', '^from netra_backend\\.app\\.agents\\.state import.*DeepAgentState',
            '.', '--include=*.py', '--exclude-dir=backups', '--exclude-dir=.venv', '--exclude-dir=venv'
        ], capture_output=True, text=True)

        files = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    file_path = line.split(':', 1)[0]
                    # Skip fix scripts and legacy backups
                    if not any(skip in file_path for skip in ['fix_', '_backup', '_legacy']):
                        files.append(file_path)

        return list(set(files))  # Remove duplicates
    except Exception as e:
        print(f"Error finding files: {e}")
        return []

def fix_file(filepath):
    """Fix DeepAgentState imports in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Handle multi-import cases
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import AgentMetadata, DeepAgentState',
            'from netra_backend.app.agents.state import AgentMetadata\nfrom netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState, AgentMetadata',
            'from netra_backend.app.agents.state import AgentMetadata\nfrom netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        # Basic replacement
        content = re.sub(
            r'from netra_backend\.app\.agents\.state import DeepAgentState',
            'from netra_backend.app.schemas.agent_models import DeepAgentState',
            content
        )

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def main():
    print("Final DeepAgentState import cleanup...")

    files_to_fix = get_active_imports()
    print(f"Found {len(files_to_fix)} files to fix")

    fixed_count = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath) and fix_file(filepath):
            print(f"Fixed: {filepath}")
            fixed_count += 1

    print(f"Final cleanup: Fixed {fixed_count} files")

    # Verify the fix
    remaining = get_active_imports()
    print(f"Remaining files with issues: {len(remaining)}")

if __name__ == "__main__":
    main()