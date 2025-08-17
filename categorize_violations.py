#!/usr/bin/env python
"""Categorize violations by module for parallel fixing."""
import json
from collections import defaultdict
import os

def categorize_violations():
    """Categorize violations by module."""
    with open('violations.json', 'r') as f:
        data = json.load(f)
    
    # Categorize by module/directory
    categories = defaultdict(lambda: {'files': [], 'functions': []})
    
    # Process file violations
    for violation in data['file_violations']:
        file_path = violation['file']
        parts = file_path.split(os.sep)
        
        # Determine category based on path structure
        if 'tests' in parts:
            # Test files by subdirectory
            if len(parts) > 2:
                category = os.sep.join(parts[:3])  # app/tests/subdirectory
            else:
                category = 'app/tests'
        else:
            # Non-test files by module
            if len(parts) > 2:
                category = os.sep.join(parts[:2])  # app/module
            else:
                category = parts[0] if parts else 'root'
        
        categories[category]['files'].append(violation)
    
    # Process function violations
    for violation in data['function_violations']:
        file_path = violation['file']
        parts = file_path.split(os.sep)
        
        # Determine category based on path structure
        if 'tests' in parts:
            if len(parts) > 2:
                category = os.sep.join(parts[:3])
            else:
                category = 'app/tests'
        else:
            if len(parts) > 2:
                category = os.sep.join(parts[:2])
            else:
                category = parts[0] if parts else 'root'
        
        categories[category]['functions'].append(violation)
    
    # Convert to sorted list of categories
    result = []
    for category, violations in sorted(categories.items()):
        result.append({
            'category': category,
            'file_count': len(violations['files']),
            'function_count': len(violations['functions']),
            'files': violations['files'],
            'functions': violations['functions']
        })
    
    return result

def main():
    categories = categorize_violations()
    
    # Save categorized violations
    with open('categorized_violations.json', 'w') as f:
        json.dump(categories, f, indent=2)
    
    print("VIOLATION CATEGORIES")
    print("=" * 60)
    
    # Priority 1: Non-test production code
    print("\nPRODUCTION CODE (Priority 1):")
    print("-" * 40)
    for cat in categories:
        if 'tests' not in cat['category']:
            print(f"{cat['category']}: {cat['file_count']} files, {cat['function_count']} functions")
    
    # Priority 2: Test code
    print("\nTEST CODE (Priority 2):")
    print("-" * 40)
    for cat in categories:
        if 'tests' in cat['category']:
            print(f"{cat['category']}: {cat['file_count']} files, {cat['function_count']} functions")
    
    return categories

if __name__ == '__main__':
    main()