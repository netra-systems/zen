#!/usr/bin/env python3
"""
Fix Alpine Dockerfile path references for Issue #1082
Replaces Alpine-specific Dockerfile references with regular ones
"""

import os
import re

def fix_docker_compose_paths():
    """Fix paths in Alpine docker-compose files"""

    # File mappings: Alpine -> Regular
    dockerfile_mappings = {
        '../dockerfiles/migration.alpine.Dockerfile': '../dockerfiles/backend.Dockerfile',
        '../dockerfiles/backend.alpine.Dockerfile': '../dockerfiles/backend.Dockerfile',
        '../dockerfiles/auth.alpine.Dockerfile': '../dockerfiles/auth.Dockerfile',
        '../dockerfiles/frontend.alpine.Dockerfile': '../dockerfiles/frontend.Dockerfile',
        'dockerfiles/backend.staging.alpine.Dockerfile': 'dockerfiles/backend.staging.Dockerfile',
        'dockerfiles/auth.staging.alpine.Dockerfile': 'dockerfiles/auth.staging.Dockerfile',
        'dockerfiles/frontend.staging.alpine.Dockerfile': 'dockerfiles/frontend.staging.Dockerfile'
    }

    files_to_fix = [
        '/c/netra-apex/docker/docker-compose.alpine-test.yml',
        '/c/netra-apex/docker/docker-compose.staging.alpine.yml'
    ]

    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} does not exist")
            continue

        print(f"Fixing {file_path}...")

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Track changes
        changes_made = []
        original_content = content

        # Apply mappings
        for alpine_path, regular_path in dockerfile_mappings.items():
            if alpine_path in content:
                content = content.replace(alpine_path, regular_path)
                changes_made.append(f"  {alpine_path} -> {regular_path}")

        # Write back if changes were made
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed {file_path}:")
            for change in changes_made:
                print(change)
        else:
            print(f"✅ No changes needed for {file_path}")

    print("\n🎉 Alpine path remediation complete!")

if __name__ == "__main__":
    fix_docker_compose_paths()