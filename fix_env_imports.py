#!/usr/bin/env python
"""Script to fix env import issues in test files."""

import os
import re

# List of files to fix
files_to_fix = [
    "netra_backend/tests/critical/test_assistant_foreign_key_violation.py",  # Already fixed
    "netra_backend/tests/e2e/test_complete_real_pipeline_e2e.py",
    "netra_backend/tests/integration/test_agent_pipeline_core.py",
    "netra_backend/tests/integration/test_auth_edge_cases.py", 
    "netra_backend/tests/integration/test_redis_session_performance.py",
    "netra_backend/tests/integration/test_user_login_flows.py",
    "netra_backend/tests/integration/test_websocket_auth_cold_start.py",
    "netra_backend/tests/integration/test_websocket_auth_cold_start_extended.py",
    "netra_backend/tests/routes/test_health_route_llm_issue.py"
]

# Pattern to fix: env = get_env() inside docstring
pattern = re.compile(r'(from shared\.isolated_environment import get_env)\n("""\nenv = get_env\(\)\n)')
replacement = r'\1\n\nenv = get_env()\n\n"""' + '\n'

fixed_files = []
skipped_files = []

for file_path in files_to_fix:
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        skipped_files.append(file_path)
        continue
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if 'env = get_env()' in content and '"""\nenv = get_env()' not in content:
        print(f"Already fixed: {file_path}")
        skipped_files.append(file_path)
        continue
    
    # Apply fix
    new_content = pattern.sub(replacement, content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed: {file_path}")
        fixed_files.append(file_path)
    else:
        print(f"No changes needed: {file_path}")
        skipped_files.append(file_path)

print(f"\nSummary:")
print(f"Fixed: {len(fixed_files)} files")
print(f"Skipped: {len(skipped_files)} files")