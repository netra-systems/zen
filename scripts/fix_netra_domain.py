#!/usr/bin/env python3
"""Fix incorrect netrasystems.ai domain references to netrasystems.ai."""

import os
import re
from pathlib import Path
from typing import List, Tuple

def fix_domain_in_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Fix netrasystems.ai domain references in a file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        for i, line in enumerate(lines):
            # Find all variations of netrasystems.ai domain
            if 'netrasystems.ai' in line and 'netrasystems.ai' not in line:
                old_line = line
                # Replace domain while preserving the rest of the URL structure
                new_line = line.replace('netrasystems.ai', 'netrasystems.ai')
                
                if new_line != old_line:
                    lines[i] = new_line
                    modified = True
                    changes.append((i + 1, old_line.strip(), new_line.strip()))
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"[FIXED] {file_path}")
            for line_num, old, new in changes:
                print(f"  Line {line_num}:")
                print(f"    - {old}")
                print(f"    + {new}")
        
    except Exception as e:
        print(f"[ERROR] Processing {file_path}: {e}")
    
    return changes

def main():
    """Main function to fix all files."""
    # List of files identified with netrasystems.ai references
    test_files = [
        'netra_backend/tests/integration/critical_paths/test_multi_tenant_data_isolation_l4.py',
        'netra_backend/tests/integration/critical_paths/test_production_deployment_e2e_l4.py',
        'netra_backend/tests/integration/critical_paths/test_production_deployment_validation_l4.py',
        'netra_backend/tests/integration/critical_paths/test_enterprise_auth_integration_l4.py',
        'netra_backend/tests/integration/test_websocket_auth_cold_start_extended_l3.py',
        'netra_backend/tests/integration/test_auth_edge_cases_l3.py',
        'netra_backend/tests/integration/test_websocket_auth_cold_start_l3.py',
        'netra_backend/tests/integration/test_user_login_flows_l3.py',
        'scripts/fix_e2e_imports.py'
    ]
    
    # Convert to Path objects
    root_dir = Path('C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1')
    
    total_changes = 0
    files_fixed = 0
    
    print("=== Fixing netrasystems.ai domain references to netrasystems.ai ===\n")
    
    for file_path in test_files:
        full_path = root_dir / file_path
        if full_path.exists():
            changes = fix_domain_in_file(full_path)
            if changes:
                files_fixed += 1
                total_changes += len(changes)
        else:
            print(f"[WARNING] File not found: {full_path}")
    
    print(f"\n=== Summary ===")
    print(f"Files fixed: {files_fixed}")
    print(f"Total changes: {total_changes}")
    
    # Also update string literals JSON files
    print("\n=== Note ===")
    print("String literal index files will need to be regenerated:")
    print("  python scripts/scan_string_literals.py")

if __name__ == "__main__":
    main()