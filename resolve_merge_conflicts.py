#!/usr/bin/env python3
"""
Git merge conflict resolution script for Issue #539.
Resolves merge conflicts by choosing appropriate code sections based on functionality analysis.
"""

import re
from pathlib import Path
import sys

def resolve_conflicts_in_file(file_path: Path):
    """Resolve merge conflicts in a single file."""
    print(f"Resolving conflicts in: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all merge conflicts
        conflict_pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [a-f0-9]{40}'
        matches = list(re.finditer(conflict_pattern, content, re.DOTALL))
        
        if not matches:
            print(f"  No conflicts found in {file_path.name}")
            return True
            
        print(f"  Found {len(matches)} conflicts")
        
        # Resolve conflicts from end to beginning to maintain indices
        for match in reversed(matches):
            head_section = match.group(1).strip()
            merge_section = match.group(2).strip()
            
            # Choose resolution strategy based on analysis
            resolved = choose_resolution(file_path, head_section, merge_section)
            
            # Replace the entire conflict block with the resolution
            content = content[:match.start()] + resolved + content[match.end():]
        
        # Write resolved content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"  SUCCESS: Resolved all conflicts in {file_path.name}")
        return True
        
    except Exception as e:
        print(f"  ERROR: Error resolving {file_path.name}: {e}")
        return False

def choose_resolution(file_path: Path, head_section: str, merge_section: str):
    """Choose the appropriate resolution for a conflict based on file analysis."""
    
    # Redis client handling - prefer async version with null checking
    if 'redis_client.flushdb()' in head_section or 'redis_client.flushdb()' in merge_section:
        if 'if self.redis_client:' in merge_section and 'asyncio.get_event_loop()' in merge_section:
            return merge_section  # Better null checking and async handling
        else:
            return head_section
    
    # Async execution patterns - prefer asyncio.gather over ThreadPoolExecutor
    if 'ThreadPoolExecutor' in merge_section and 'asyncio.gather' in head_section:
        return head_section  # asyncio.gather is more appropriate for async tests
    elif 'ThreadPoolExecutor' in head_section and 'asyncio.gather' in merge_section:
        return merge_section
    
    # Error handling patterns - prefer more descriptive error messages
    if 'getattr(self, \'_testMethodName\', \'unknown\')' in merge_section:
        return merge_section  # More descriptive logging
    
    # Service initialization - prefer more robust initialization
    if 'get_redis_client()' in merge_section and 'redis.Redis(' in head_section:
        return merge_section  # Use SSOT Redis client
        
    # Default to head section for safety
    return head_section

def main():
    """Main execution function."""
    project_root = Path(__file__).parent
    
    # Files to resolve
    files_to_resolve = [
        project_root / "tests/mission_critical/test_ssot_regression_prevention.py",
        project_root / "tests/mission_critical/test_ssot_backward_compatibility.py"
    ]
    
    success_count = 0
    total_count = len(files_to_resolve)
    
    print("Starting merge conflict resolution...")
    
    for file_path in files_to_resolve:
        if file_path.exists():
            if resolve_conflicts_in_file(file_path):
                success_count += 1
        else:
            print(f"  WARNING: File not found: {file_path}")
    
    print(f"\nResolution Summary: {success_count}/{total_count} files resolved")
    
    if success_count == total_count:
        print("SUCCESS: All merge conflicts resolved successfully!")
        return 0
    else:
        print("ERROR: Some files could not be resolved")
        return 1

if __name__ == "__main__":
    sys.exit(main())