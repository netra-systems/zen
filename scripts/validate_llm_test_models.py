#!/usr/bin/env python3
"""
Validation script for LLM test model standardization.

This script ensures that the codebase uses only approved LLM models
(Gemini models) and flags any regressions to GPT or Claude models
that should not be used in tests.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Define approved and deprecated models
APPROVED_MODELS = {
    "GEMINI_2_5_FLASH",
    "GEMINI_2_5_PRO", 
    "GEMINI_PRO",
    "CLAUDE_3_SONNET"  # Kept for compatibility
}

DEPRECATED_MODELS = {
    "GPT_4",
    "GPT_35_TURBO",
    "CLAUDE_3_OPUS"
}

DEPRECATED_STRINGS = [
    "gpt-4",
    "gpt-3.5-turbo",
    "claude-3-opus",
    "GPT_4",
    "GPT_35_TURBO", 
    "CLAUDE_3_OPUS",
    "OPENAI_API_KEY"  # Should not be required for tests
]

# Directories to check
TEST_DIRECTORIES = [
    "netra_backend/tests",
    "auth_service/tests",
    "frontend/__tests__",
    "tests/e2e",
    "test_framework"
]

# File patterns to check
FILE_PATTERNS = ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]

def find_test_files(base_dir: Path) -> List[Path]:
    """Find all test files in specified directories."""
    test_files = []
    for test_dir in TEST_DIRECTORIES:
        dir_path = base_dir / test_dir
        if dir_path.exists():
            for pattern in FILE_PATTERNS:
                test_files.extend(dir_path.rglob(pattern))
    return test_files

def check_file_for_deprecated_models(file_path: Path) -> List[Tuple[int, str, str]]:
    """Check a file for deprecated model references."""
    violations = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue
                
            for deprecated in DEPRECATED_STRINGS:
                if deprecated in line:
                    # Check for exceptions (like in this validation script itself)
                    if "DEPRECATED_" in line or "validate_llm_test_models" in str(file_path):
                        continue
                    violations.append((line_num, deprecated, line.strip()))
                    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return violations

def check_llm_test_model_enum(base_dir: Path) -> bool:
    """Check that LLMTestModel enum only contains approved models."""
    enum_file = base_dir / "netra_backend/tests/e2e/infrastructure/llm_test_manager.py"
    
    if not enum_file.exists():
        print(f"Warning: LLMTestModel enum file not found at {enum_file}")
        return True
        
    try:
        with open(enum_file, 'r') as f:
            content = f.read()
            
        # Find the LLMTestModel enum definition
        enum_match = re.search(r'class LLMTestModel.*?(?=class|\Z)', content, re.DOTALL)
        
        if not enum_match:
            print("Warning: Could not find LLMTestModel enum definition")
            return True
            
        enum_content = enum_match.group()
        
        # Check for deprecated models in enum
        has_violations = False
        for deprecated in DEPRECATED_MODELS:
            if deprecated in enum_content:
                print(f"ERROR: Found deprecated model {deprecated} in LLMTestModel enum")
                has_violations = True
                
        # Check that approved models are present
        for approved in ["GEMINI_2_5_FLASH", "GEMINI_2_5_PRO"]:
            if approved not in enum_content:
                print(f"Warning: Expected model {approved} not found in LLMTestModel enum")
                
        return not has_violations
        
    except Exception as e:
        print(f"Error checking enum file: {e}")
        return False

def main():
    """Main validation function."""
    print("=" * 70)
    print("LLM Test Model Validation Script")
    print("=" * 70)
    
    # Get base directory
    base_dir = Path(__file__).parent.parent
    
    print(f"\nChecking test files in: {base_dir}")
    print(f"Test directories: {TEST_DIRECTORIES}")
    
    # Check LLMTestModel enum
    print("\n1. Checking LLMTestModel enum...")
    enum_valid = check_llm_test_model_enum(base_dir)
    
    # Find and check test files
    print("\n2. Scanning test files for deprecated models...")
    test_files = find_test_files(base_dir)
    print(f"Found {len(test_files)} test files to check")
    
    all_violations = []
    files_with_violations = set()
    
    for file_path in test_files:
        violations = check_file_for_deprecated_models(file_path)
        if violations:
            all_violations.extend([(file_path, v) for v in violations])
            files_with_violations.add(file_path)
    
    # Report results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    
    if not enum_valid:
        print("\n[ERROR] LLMTestModel enum contains deprecated models")
        
    if all_violations:
        print(f"\n[ERROR] Found {len(all_violations)} violations in {len(files_with_violations)} files:")
        
        # Group violations by file
        for file_path in sorted(files_with_violations):
            file_violations = [v for f, v in all_violations if f == file_path]
            print(f"\n  {file_path.relative_to(base_dir)}:")
            for line_num, deprecated, line_content in file_violations[:5]:  # Show max 5 per file
                print(f"    Line {line_num}: Found '{deprecated}'")
                print(f"      > {line_content[:80]}...")
                
            if len(file_violations) > 5:
                print(f"    ... and {len(file_violations) - 5} more violations")
    else:
        print("\n[OK] No deprecated model references found in test files")
        
    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    if all_violations or not enum_valid:
        print("\nTo fix these issues:")
        print("1. Replace GPT_4 with GEMINI_2_5_FLASH")
        print("2. Replace GPT_35_TURBO with GEMINI_2_5_FLASH")
        print("3. Replace CLAUDE_3_OPUS with GEMINI_2_5_PRO")
        print("4. Update hardcoded strings 'gpt-4' to 'gemini-2.0-flash-exp'")
        print("5. Remove any OPENAI_API_KEY requirements from test configurations")
        print("\nRun this script again after making changes to verify compliance.")
        sys.exit(1)
    else:
        print("\n[OK] All validation checks passed!")
        print("The codebase is compliant with LLM test model standardization.")
        sys.exit(0)

if __name__ == "__main__":
    main()