#!/usr/bin/env python3
"""Fix duplicate try blocks that cause IndentationError.

This script fixes the pattern:
try:
    # Use backend-specific isolated environment
try:

Converting it to:
try:
"""

import os
import re
from pathlib import Path

def fix_duplicate_try_blocks(file_path: Path) -> bool:
    """Fix duplicate try blocks in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match the duplicate try blocks
        pattern = re.compile(
            r'try:\s*\n\s*# Use backend-specific isolated environment\s*\ntry:',
            re.MULTILINE
        )
        
        # Replace with single try block
        new_content = pattern.sub('try:', content)
        
        # Also handle the simpler pattern
        pattern2 = re.compile(
            r'# Use backend-specific isolated environment\s*\ntry:\s*\n\s*# Use backend-specific isolated environment\s*\ntry:',
            re.MULTILINE
        )
        new_content = pattern2.sub('# Use backend-specific isolated environment\ntry:', new_content)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all files with duplicate try blocks."""
    # List of files identified by grep
    files_to_fix = [
        "netra_backend/tests/integration/critical_missing/shared_infrastructure/containerized_services.py",
        "netra_backend/tests/integration/staging_config/base.py",
        "netra_backend/tests/integration/critical_paths/l4_staging_critical_base.py",
        "netra_backend/tests/integration/test_dev_launcher_startup.py",
        "netra_backend/tests/helpers/staging_base.py",
        "netra_backend/tests/e2e/conftest.py",
        "netra_backend/app/services/cache/semantic_cache.py",
        "netra_backend/app/core/configuration/unified_secrets.py",
        "netra_backend/app/core/configuration/secrets.py",
        "netra_backend/app/core/configuration/environment_detector.py",
        "netra_backend/app/core/configuration/database.py",
        "netra_backend/app/core/configuration/environment.py",
        "netra_backend/app/agents/chat_orchestrator/model_cascade.py",
        "netra_backend/app/tools/deep_research_api.py",
        "netra_backend/app/tools/sandboxed_interpreter.py",
        "netra_backend/app/services/unified_health_service.py",
        "netra_backend/app/services/startup_fixes_integration.py",
        "netra_backend/app/guardrails/input_filters.py",
        "netra_backend/app/db/postgres_core.py",
        "netra_backend/app/db/database_initializer.py",
        "netra_backend/app/core/startup_config.py",
        "netra_backend/app/core/health_configuration.py",
        "netra_backend/app/agents/chat_orchestrator_main.py",
        "netra_backend/app/startup_module.py"
    ]
    
    base_path = Path.cwd()
    fixed_count = 0
    
    for file_path_str in files_to_fix:
        file_path = base_path / file_path_str
        if file_path.exists():
            if fix_duplicate_try_blocks(file_path):
                fixed_count += 1
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nFixed {fixed_count} files total.")

if __name__ == "__main__":
    main()