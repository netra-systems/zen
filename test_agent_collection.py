#!/usr/bin/env python3
"""
Systematic Agent Test Collection Analysis Script
Tests all agent test files for collection issues and categorizes failures.
"""

import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import re

def find_agent_test_files() -> List[str]:
    """Find all agent test files in the specified directories."""
    base_path = "/Users/anthony/Desktop/netra-apex"
    patterns = [
        "*/tests/unit/agents/*test*.py",
        "*/tests/integration/agents/*test*.py", 
        "*/netra_backend/tests/unit/agents/*test*.py"
    ]
    
    agent_files = []
    for pattern in patterns:
        cmd = f"find {base_path} -path '{pattern}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            agent_files.extend([f for f in files if f])
    
    return sorted(list(set(agent_files)))

def test_collection(file_path: str) -> Tuple[bool, str, str]:
    """Test collection for a single test file."""
    try:
        cmd = ["python3", "-m", "pytest", file_path, "--collect-only", "-q"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        success = result.returncode == 0
        error_output = result.stderr
        
        if not success:
            return False, categorize_error(error_output), error_output
        else:
            # Count collected tests
            test_count = len([line for line in result.stdout.split('\n') 
                            if '::' in line and 'test_' in line])
            return True, f"SUCCESS: {test_count} tests collected", result.stdout
            
    except subprocess.TimeoutExpired:
        return False, "timeout_exception", "Collection timeout after 30 seconds"
    except Exception as e:
        return False, "timeout_exception", f"Exception during collection: {str(e)}"

def categorize_error(error_output: str) -> str:
    """Categorize the type of collection error."""
    if not error_output:
        return "collection_error"
    
    if "ModuleNotFoundError" in error_output or "ImportError" in error_output:
        return "missing_module"
    elif "SyntaxError" in error_output:
        return "syntax_error"
    elif "TimeoutExpired" in error_output or "timeout" in error_output.lower():
        return "timeout_exception"
    else:
        return "collection_error"

def extract_error_details(error_output: str) -> str:
    """Extract key error details for reporting."""
    lines = error_output.split('\n')
    for line in lines:
        if any(keyword in line for keyword in ["ModuleNotFoundError", "ImportError", "SyntaxError"]):
            return line.strip()
    
    # If no specific error found, return first non-empty line
    for line in lines:
        if line.strip():
            return line.strip()
    
    return "Unknown error"

def main():
    print("🔍 Systematic Agent Test Collection Analysis")
    print("=" * 60)
    
    # Find all agent test files
    agent_files = find_agent_test_files()
    print(f"📊 Found {len(agent_files)} agent test files")
    
    # Initialize tracking
    results = {
        'success': [],
        'missing_module': [],
        'syntax_error': [],
        'collection_error': [],
        'timeout_exception': []
    }
    
    # Test each file
    print("\n🧪 Testing collection for each file...")
    for i, file_path in enumerate(agent_files, 1):
        print(f"\r[{i}/{len(agent_files)}] Testing: {os.path.basename(file_path)}", end="", flush=True)
        
        success, category, output = test_collection(file_path)
        
        if success:
            results['success'].append((file_path, output))
        else:
            error_detail = extract_error_details(output)
            results[category].append((file_path, error_detail))
    
    print("\n")  # New line after progress indicator
    
    # Generate report
    print("\n📈 COLLECTION ANALYSIS REPORT")
    print("=" * 60)
    print(f"Total agent test files analyzed: {len(agent_files)}")
    print(f"✅ Successful collections: {len(results['success'])}")
    print(f"❌ Failed collections: {len(agent_files) - len(results['success'])}")
    
    print(f"\n📊 FAILURE BREAKDOWN:")
    print(f"   🔧 Missing modules: {len(results['missing_module'])}")
    print(f"   💥 Syntax errors: {len(results['syntax_error'])}")
    print(f"   ⚠️  Collection errors: {len(results['collection_error'])}")
    print(f"   ⏱️  Timeouts/exceptions: {len(results['timeout_exception'])}")
    
    # Show first 20 problematic files
    print(f"\n🚨 FIRST 20 PROBLEMATIC FILES:")
    print("-" * 40)
    
    problem_count = 0
    for category in ['missing_module', 'syntax_error', 'collection_error', 'timeout_exception']:
        if problem_count >= 20:
            break
            
        for file_path, error in results[category]:
            if problem_count >= 20:
                break
                
            file_name = os.path.basename(file_path)
            print(f"{problem_count + 1:2d}. {category:15s} | {file_name}")
            print(f"    Error: {error[:100]}{'...' if len(error) > 100 else ''}")
            print()
            problem_count += 1
    
    # Summary statistics
    success_rate = (len(results['success']) / len(agent_files)) * 100
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"   Most Common Issue: {max(results.keys(), key=lambda k: len(results[k]) if k != 'success' else 0)}")
    
    return results

if __name__ == "__main__":
    main()