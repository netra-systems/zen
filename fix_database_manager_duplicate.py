#!/usr/bin/env python3
"""
Fix DatabaseManager SSOT violation by removing duplicate class from test_framework/real_services.py
"""

import re

def fix_database_manager_duplicate():
    file_path = 'test_framework/real_services.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match the entire DatabaseManager class - from the comment line through to the next section
    # We'll replace everything from the comment line until the Redis Manager section
    pattern = r'# DatabaseManager imported from SSOT location at top of file.*?(?=# =============================================================================\n# REDIS MANAGER)'
    
    replacement = '''# DatabaseManager imported from SSOT location at top of file
# (see import at top: from netra_backend.app.db.database_manager import DatabaseManager)


'''
    
    # Replace the pattern
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed DatabaseManager duplicate in test_framework/real_services.py")
    print("✅ Removed duplicate class implementation")
    print("✅ Kept SSOT import from netra_backend.app.db.database_manager")

if __name__ == "__main__":
    fix_database_manager_duplicate()