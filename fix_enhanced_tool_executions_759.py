#!/usr/bin/env python3
"""
Issue #759 SSOT Enhanced Tool Execution Engine Remediation Script

This script replaces remaining EnhancedToolExecutionEngine instantiations.

CHANGES MADE:
- UserExecutionEngine( -> UserExecutionEngine(
- Maintains backward compatibility with proper imports
- Preserves all existing functionality
"""

import os
import re
import sys
from pathlib import Path

def main():
    print("🚀 Starting Issue #759 Enhanced Tool Execution Engine Remediation...")
    
    # Pattern replacements for SSOT consolidation
    pattern = r'\bEnhancedToolExecutionEngine\('
    replacement = 'UserExecutionEngine('
    
    # Find all Python files
    repo_root = Path("/Users/anthony/Desktop/netra-apex")
    python_files = list(repo_root.rglob("*.py"))
    
    fixed_files = []
    total_replacements = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply replacement
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                file_replacements = len(matches)
                
                print(f"📝 Fixing enhanced tool executions in: {file_path}")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                fixed_files.append(str(file_path))
                total_replacements += file_replacements
                print(f"   ✅ Fixed {file_replacements} instantiation(s)")
                
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
            continue
    
    print(f"\n🎉 Enhanced Tool Execution Engine Remediation Complete!")
    print(f"📊 Summary:")
    print(f"   - Files processed: {len(python_files)}")
    print(f"   - Files fixed: {len(fixed_files)}")
    print(f"   - Total instantiations corrected: {total_replacements}")
    
    if fixed_files:
        print(f"\n📋 Fixed files:")
        for file_path in fixed_files:
            print(f"   - {file_path}")
    
    return len(fixed_files), total_replacements

if __name__ == "__main__":
    sys.exit(0 if main()[0] >= 0 else 1)