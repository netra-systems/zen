#!/usr/bin/env python3
"""
Migration Readiness Validation Script (Issue #346)

Validates that the migration infrastructure is ready and identifies
the exact files that need migration for systematic remediation.

Usage:
    python scripts/validate_migration_readiness.py
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

def check_infrastructure_readiness() -> bool:
    """Check if migration infrastructure is ready."""
    print("CHECKING MIGRATION INFRASTRUCTURE READINESS\n")
    
    ready = True
    
    # Check test utilities exist
    required_files = [
        "tests/unit/agents/supervisor/test_user_execution_context_migration_helpers.py",
        "tests/unit/agents/supervisor/test_user_execution_context_correct_patterns.py",
        "tests/unit/agents/supervisor/test_user_execution_context_validation_security.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"OK {file_path}")
        else:
            print(f"MISSING: {file_path}")
            ready = False
    
    # Check if UserExecutionContext is available
    try:
        result = subprocess.run([
            sys.executable, '-c', 
            'from netra_backend.app.services.user_execution_context import UserExecutionContext; print("UserExecutionContext available")'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("OK UserExecutionContext importable")
        else:
            print("ERROR UserExecutionContext import failed:")
            print(f"   {result.stderr}")
            ready = False
            
    except Exception as e:
        print(f"ERROR Failed to check UserExecutionContext: {e}")
        ready = False
    
    return ready

def find_files_with_mock_patterns() -> List[Tuple[str, int]]:
    """Find all test files with Mock UserExecutionContext patterns."""
    print("\nSCANNING FOR MOCK PATTERNS\n")
    
    mock_patterns = [
        r"Mock.*UserExecutionContext",
        r"mock.*UserExecutionContext", 
        r"SSotMockFactory\.create_mock_user_context",
        r"mock_user_context\s*=\s*Mock\(\)"
    ]
    
    files_with_patterns = []
    
    # Search in test directories
    test_dirs = [
        "tests/",
        "netra_backend/tests/",
        "auth_service/tests/" if os.path.exists("auth_service/tests/") else None
    ]
    
    for test_dir in test_dirs:
        if not test_dir or not os.path.exists(test_dir):
            continue
            
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        import re
                        pattern_count = 0
                        for pattern in mock_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            pattern_count += len(matches)
                        
                        if pattern_count > 0:
                            files_with_patterns.append((file_path, pattern_count))
                            
                    except Exception as e:
                        print(f"ERROR reading {file_path}: {e}")
    
    return files_with_patterns

def categorize_files_by_priority(files_with_patterns: List[Tuple[str, int]]) -> Dict[str, List[Tuple[str, int]]]:
    """Categorize files by migration priority."""
    
    categories = {
        "Golden Path": [],
        "Mission Critical": [],
        "WebSocket Events": [], 
        "Integration Tests": [],
        "Unit Tests": [],
        "Other": []
    }
    
    for file_path, pattern_count in files_with_patterns:
        if "golden_path" in file_path:
            categories["Golden Path"].append((file_path, pattern_count))
        elif "mission_critical" in file_path:
            categories["Mission Critical"].append((file_path, pattern_count))
        elif "websocket" in file_path and ("test_websocket_agent_events" in file_path or "test_websocket_event" in file_path):
            categories["WebSocket Events"].append((file_path, pattern_count))
        elif "integration" in file_path:
            categories["Integration Tests"].append((file_path, pattern_count))
        elif "unit" in file_path:
            categories["Unit Tests"].append((file_path, pattern_count))
        else:
            categories["Other"].append((file_path, pattern_count))
    
    return categories

def print_migration_summary(categories: Dict[str, List[Tuple[str, int]]]):
    """Print migration summary by category."""
    print("\nMIGRATION SUMMARY BY PRIORITY\n")
    
    total_files = 0
    total_patterns = 0
    
    priority_order = [
        ("CRITICAL Golden Path", "Golden Path"),
        ("CRITICAL Mission Critical", "Mission Critical"), 
        ("CRITICAL WebSocket Events", "WebSocket Events"),
        ("MEDIUM Integration Tests", "Integration Tests"),
        ("LOW Unit Tests", "Unit Tests"),
        ("LOW Other", "Other")
    ]
    
    for display_name, category_key in priority_order:
        files = categories[category_key]
        if not files:
            continue
            
        file_count = len(files)
        pattern_count = sum(count for _, count in files)
        total_files += file_count
        total_patterns += pattern_count
        
        print(f"{display_name}: {file_count} files, {pattern_count} patterns")
        
        # Show top 5 files with most patterns
        sorted_files = sorted(files, key=lambda x: x[1], reverse=True)
        for i, (file_path, count) in enumerate(sorted_files[:5]):
            print(f"  {count:2d} patterns: {file_path}")
        
        if len(sorted_files) > 5:
            print(f"  ... and {len(sorted_files) - 5} more files")
        print()
    
    print(f"TOTAL: {total_files} files, {total_patterns} patterns need migration\n")

def generate_batch_execution_commands(categories: Dict[str, List[Tuple[str, int]]]):
    """Generate commands for batch execution."""
    print("RECOMMENDED EXECUTION COMMANDS\n")
    
    # Batch 1: Business Critical (Golden Path + Mission Critical + WebSocket Events)
    batch1_files = (
        categories["Golden Path"] + 
        categories["Mission Critical"] + 
        categories["WebSocket Events"]
    )
    
    if batch1_files:
        print("BATCH 1 - BUSINESS CRITICAL (Execute Today):")
        print(f"  Files: {len(batch1_files)}")
        print("  Command:")
        print("    python scripts/migrate_mock_to_usercontext.py --execute-batch 1 --dry-run")
        print("    python scripts/migrate_mock_to_usercontext.py --execute-batch 1 --auto-commit")
        print()
    
    # Batch 2: Integration Tests
    if categories["Integration Tests"]:
        print("BATCH 2 - INTEGRATION TESTS (This Week):")
        print(f"  Files: {len(categories['Integration Tests'])}")
        print("  Command:")
        print("    python scripts/migrate_mock_to_usercontext.py --execute-batch 2 --dry-run")
        print("    python scripts/migrate_mock_to_usercontext.py --execute-batch 2 --auto-commit")
        print()
    
    # Batch 3: Unit Tests  
    if categories["Unit Tests"] or categories["Other"]:
        unit_count = len(categories["Unit Tests"]) + len(categories["Other"])
        print("BATCH 3 - UNIT TESTS (Next Sprint):")
        print(f"  Files: {unit_count}")
        print("  Command:")
        print("    python scripts/migrate_mock_to_usercontext.py --execute-batch 3 --dry-run")
        print("    python scripts/migrate_mock_to_usercontext.py --execute-batch 3 --auto-commit")
        print()

def main():
    print("="*70)
    print("MOCK-TO-USEREXECUTIONCONTEXT MIGRATION READINESS CHECK (Issue #346)")
    print("="*70)
    
    # Check infrastructure readiness
    if not check_infrastructure_readiness():
        print("\nERROR MIGRATION INFRASTRUCTURE NOT READY")
        print("Please ensure test utilities are implemented before proceeding.")
        sys.exit(1)
    
    print("\nOK MIGRATION INFRASTRUCTURE READY")
    
    # Find files needing migration
    files_with_patterns = find_files_with_mock_patterns()
    
    if not files_with_patterns:
        print("\nOK NO MOCK PATTERNS FOUND - NO MIGRATION NEEDED")
        sys.exit(0)
    
    # Categorize by priority
    categories = categorize_files_by_priority(files_with_patterns)
    
    # Print summary
    print_migration_summary(categories)
    
    # Generate execution commands
    generate_batch_execution_commands(categories)
    
    print("NEXT STEPS:")
    print("1. Review the file list above")
    print("2. Start with BATCH 1 (Business Critical) using dry-run first")
    print("3. Execute migrations systematically with auto-commit")
    print("4. Validate Golden Path tests after Batch 1 completion")
    print("\nREADY TO BEGIN MIGRATION")

if __name__ == "__main__":
    main()