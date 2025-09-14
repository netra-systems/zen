#!/usr/bin/env python3
"""
Batch Agent Test Collection Analyzer
Tests agent files in batches to efficiently identify collection failures.
"""

import subprocess
import os
import sys
from pathlib import Path
import random

def get_agent_files_by_category():
    """Get agent test files organized by category."""
    base_path = "/Users/anthony/Desktop/netra-apex"
    
    categories = {
        "unit_agents": [],
        "integration_agents": [],  
        "netra_backend_agents": [],
        "issue_specific_agents": []
    }
    
    # Unit tests
    result = subprocess.run(
        ["find", base_path, "-path", "*/tests/unit/agents/*test*.py"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        categories["unit_agents"] = [f for f in result.stdout.strip().split('\n') if f]
    
    # Integration tests  
    result = subprocess.run(
        ["find", base_path, "-path", "*/tests/integration/agents/*test*.py"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        categories["integration_agents"] = [f for f in result.stdout.strip().split('\n') if f]
    
    # Netra backend tests
    result = subprocess.run(
        ["find", base_path, "-path", "*/netra_backend/tests/unit/agents/*test*.py"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        categories["netra_backend_agents"] = [f for f in result.stdout.strip().split('\n') if f]
    
    # Issue-specific tests
    result = subprocess.run(
        ["find", base_path, "-path", "*/issue_*/*test*agent*.py"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        categories["issue_specific_agents"] = [f for f in result.stdout.strip().split('\n') if f]
    
    return categories

def test_file_batch(files, timeout=60):
    """Test a batch of files for collection issues."""
    results = {"success": [], "failures": []}
    
    for file_path in files:
        file_name = Path(file_path).name
        
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", file_path, "--collect-only", "-q"],
                capture_output=True, text=True, timeout=timeout
            )
            
            if result.returncode == 0:
                # Count tests
                test_count = len([line for line in result.stdout.split('\n') 
                                if '::' in line and 'test_' in line])
                results["success"].append((file_path, test_count))
            else:
                # Categorize error
                error = result.stderr
                if "ModuleNotFoundError" in error or "ImportError" in error:
                    category = "missing_module"
                elif "SyntaxError" in error:
                    category = "syntax_error"
                else:
                    category = "collection_error"
                
                error_detail = error.split('\n')[0] if error else "Unknown error"
                results["failures"].append((file_path, category, error_detail))
                
        except subprocess.TimeoutExpired:
            results["failures"].append((file_path, "timeout", f"Timeout after {timeout}s"))
        except Exception as e:
            results["failures"].append((file_path, "exception", str(e)))
    
    return results

def main():
    print("🔍 Batch Agent Test Collection Analysis")
    print("=" * 60)
    
    # Get files by category
    categories = get_agent_files_by_category()
    
    print("📊 FILE COUNTS BY CATEGORY:")
    total_files = 0
    for cat_name, files in categories.items():
        count = len(files)
        total_files += count
        print(f"   {cat_name:<25}: {count:3d} files")
    
    print(f"   {'TOTAL':<25}: {total_files:3d} files")
    
    # Test random samples from each category
    print(f"\n🧪 TESTING REPRESENTATIVE SAMPLES:")
    print("-" * 40)
    
    all_results = {"success": [], "failures": []}
    
    for cat_name, files in categories.items():
        if not files:
            continue
            
        # Test 20% sample or at least 3 files, max 15 files per category
        sample_size = max(3, min(15, len(files) // 5))
        sample_files = random.sample(files, min(sample_size, len(files)))
        
        print(f"\n{cat_name} (testing {len(sample_files)}/{len(files)} files):")
        
        results = test_file_batch(sample_files, timeout=30)
        
        # Update totals
        all_results["success"].extend(results["success"]) 
        all_results["failures"].extend(results["failures"])
        
        # Report category results
        success_count = len(results["success"])
        failure_count = len(results["failures"])
        success_rate = (success_count / len(sample_files)) * 100 if sample_files else 0
        
        print(f"   ✅ Success: {success_count}/{len(sample_files)} ({success_rate:.1f}%)")
        
        if results["failures"]:
            print(f"   ❌ Failures: {failure_count}")
            for file_path, category, error in results["failures"][:3]:  # Show first 3
                file_name = Path(file_path).name
                print(f"      {category:<15} | {file_name}")
                print(f"                      | {error[:60]}{'...' if len(error) > 60 else ''}")
    
    # Summary
    total_tested = len(all_results["success"]) + len(all_results["failures"])
    overall_success_rate = (len(all_results["success"]) / total_tested * 100) if total_tested else 0
    
    print(f"\n" + "=" * 60)
    print(f"📈 OVERALL SUMMARY:")
    print(f"   Files tested: {total_tested}")  
    print(f"   Success rate: {overall_success_rate:.1f}%")
    print(f"   Estimated total failures: ~{int((total_files * (100 - overall_success_rate)) / 100)} files")
    
    # Failure breakdown
    if all_results["failures"]:
        print(f"\n❌ FAILURE CATEGORIES:")
        failure_categories = {}
        for _, category, _ in all_results["failures"]:
            failure_categories[category] = failure_categories.get(category, 0) + 1
        
        for category, count in sorted(failure_categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category:<15}: {count} files")
    
    # First 10 problematic files
    if all_results["failures"]:
        print(f"\n🚨 FIRST 10 PROBLEMATIC FILES:")
        for i, (file_path, category, error) in enumerate(all_results["failures"][:10], 1):
            file_name = Path(file_path).name
            print(f"{i:2d}. {category:<15} | {file_name}")
            print(f"    {error[:80]}{'...' if len(error) > 80 else ''}")
    
    return all_results

if __name__ == "__main__":
    main()