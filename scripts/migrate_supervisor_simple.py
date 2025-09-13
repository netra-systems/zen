#!/usr/bin/env python3
"""
Simple SSOT Migration Script: supervisor_consolidated -> supervisor_ssot
Resolves Issue #800 - SSOT-incomplete-migration-duplicate-supervisor-agents
"""

import os
import re
from pathlib import Path

# Files to migrate
FILES_TO_MIGRATE = [
    "netra_backend/app/dependencies.py",
    "netra_backend/app/websocket_core/supervisor_factory.py",
    "netra_backend/app/websocket_core/ssot_service_initializer.py",
    "netra_backend/app/core/supervisor_factory.py",
    "netra_backend/app/agents/supervisor_admin_init.py",
    "netra_backend/app/startup_module.py",
    "netra_backend/app/services/agent_service_factory.py",
    "netra_backend/app/routes/agent_route.py",
    "netra_backend/app/services/agent_service_core.py",
    "netra_backend/app/services/message_handlers.py",
]

def migrate_file(file_path):
    """Migrate imports in a single file."""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Replace all supervisor_consolidated imports with supervisor_ssot
    content = re.sub(
        r'from netra_backend\.app\.agents\.supervisor_consolidated import',
        'from netra_backend.app.agents.supervisor_ssot import',
        content
    )

    # Handle TYPE_CHECKING imports
    content = re.sub(
        r'from netra_backend\.app\.agents\.supervisor_consolidated import \(\s*SupervisorAgent as Supervisor,?\s*\)',
        'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as Supervisor',
        content
    )

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Migrated: {file_path}")
        return True
    else:
        print(f"No changes needed: {file_path}")
        return False

def main():
    print("Starting SSOT migration...")
    migrated_count = 0

    for file_path in FILES_TO_MIGRATE:
        if migrate_file(file_path):
            migrated_count += 1

    print(f"Migration complete. Files migrated: {migrated_count}")

if __name__ == "__main__":
    main()