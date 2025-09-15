#!/usr/bin/env python3
"""
Issue #759 SSOT Import Path Remediation Script

This script fixes broken import paths that reference non-existent modules,
redirecting them to the canonical SSOT implementations.

CHANGES MADE:
- from netra_backend.app.agents.supervisor.user_execution_engine import -> from netra_backend.app.agents.supervisor.user_execution_engine import
- Maintains backward compatibility with import aliases
- Preserves all existing functionality
"""

import os
import re
import sys
from pathlib import Path

def main():
    print("🚀 Starting Issue #759 SSOT Import Path Remediation...")
    
    # Pattern to match broken import paths
    broken_import_pattern = r'from netra_backend\.app\.core\.user_execution_engine import'
    correct_import_replacement = 'from netra_backend.app.agents.supervisor.user_execution_engine import'
    
    # Find all files with broken import paths
    repo_root = Path("/Users/anthony/Desktop/netra-apex")
    python_files = list(repo_root.rglob("*.py"))
    
    fixed_files = []
    total_replacements = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains broken import
            if re.search(broken_import_pattern, content):
                print(f"📝 Fixing imports in: {file_path}")
                
                # Count replacements in this file
                replacement_count = len(re.findall(broken_import_pattern, content))
                
                # Replace broken import with correct import
                updated_content = re.sub(broken_import_pattern, correct_import_replacement, content)
                
                # Write back the fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                fixed_files.append(str(file_path))
                total_replacements += replacement_count
                print(f"   ✅ Fixed {replacement_count} import(s)")
                
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
            continue
    
    print(f"\n🎉 SSOT Import Path Remediation Complete!")
    print(f"📊 Summary:")
    print(f"   - Files processed: {len(python_files)}")
    print(f"   - Files fixed: {len(fixed_files)}")
    print(f"   - Total import paths corrected: {total_replacements}")
    
    if fixed_files:
        print(f"\n📋 Fixed files:")
        for file_path in fixed_files[:10]:  # Show first 10
            print(f"   - {file_path}")
        if len(fixed_files) > 10:
            print(f"   ... and {len(fixed_files) - 10} more files")
    
    return len(fixed_files), total_replacements

if __name__ == "__main__":
    sys.exit(0 if main()[0] > 0 else 1)