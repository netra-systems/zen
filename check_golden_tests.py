#!/usr/bin/env python
"""Check status of golden pattern test files."""

import os
import re
from pathlib import Path

TEST_FILES = [
    "test_supervisor_golden_compliance_quick.py",
    "test_data_sub_agent_golden_ssot.py",
    "test_actions_agent_golden_compliance.py",
    "test_reporting_agent_golden.py",
    "test_optimizations_agent_golden.py",
    "test_summary_extractor_golden.py",
    "test_tool_discovery_golden.py",
    "test_goals_triage_golden.py",
    "test_actions_to_meet_goals_golden.py",
    "test_agent_resilience_patterns.py",
    "test_baseagent_edge_cases_comprehensive.py",
    "test_baseagent_inheritance_violations.py",
    "test_agent_type_safety_comprehensive.py",
    "test_agent_communication_undefined_attributes.py",
    "test_agent_death_fix_complete.py",
    "test_agent_manager_lifecycle_events.py",
    "test_inheritance_architecture_violations.py",
    "test_datahelper_golden_alignment.py",
    "test_datahelper_websocket_integration.py",
    "test_circuit_breaker_comprehensive.py",
]

REQUIRED_PATTERNS = [
    "BaseAgent",
    "WebSocket",
    "_execute_core",
    "error.*recovery|resilience|retry",
    "cleanup|shutdown|resource",
]

def check_test_file(filepath):
    """Check if test file has comprehensive golden pattern tests."""
    if not filepath.exists():
        return {"exists": False, "lines": 0, "tests": 0, "patterns": []}
    
    content = filepath.read_text(encoding='utf-8')
    lines = len(content.splitlines())
    
    # Count test functions/methods
    test_count = len(re.findall(r'(?:async )?def test_\w+', content)) + \
                 len(re.findall(r'(?:async )?def (?:setup|teardown)_\w+', content))
    
    # Check for required patterns
    patterns_found = []
    for pattern in REQUIRED_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            patterns_found.append(pattern)
    
    # Check for comprehensive structure
    has_categories = all(
        category in content for category in [
            "INITIALIZATION", "WEBSOCKET", "EXECUTION", "ERROR", "CLEANUP"
        ]
    )
    
    return {
        "exists": True,
        "lines": lines,
        "tests": test_count,
        "patterns": patterns_found,
        "comprehensive": lines > 500 and test_count >= 20 and len(patterns_found) >= 4,
        "has_categories": has_categories
    }

def main():
    """Check all golden test files."""
    test_dir = Path("tests/mission_critical")
    
    print("=" * 80)
    print("GOLDEN PATTERN TEST FILES STATUS CHECK")
    print("=" * 80)
    print()
    
    summary = {"comprehensive": 0, "partial": 0, "missing": 0, "total_tests": 0}
    
    for i, test_file in enumerate(TEST_FILES, 1):
        filepath = test_dir / test_file
        status = check_test_file(filepath)
        
        if not status["exists"]:
            print(f"{i:2}. [X] {test_file:45} MISSING")
            summary["missing"] += 1
        elif status.get("comprehensive"):
            print(f"{i:2}. [OK] {test_file:45} COMPREHENSIVE ({status['lines']:4} lines, {status['tests']:2} tests)")
            summary["comprehensive"] += 1
            summary["total_tests"] += status["tests"]
        else:
            missing_patterns = [p for p in REQUIRED_PATTERNS if p not in status.get("patterns", [])]
            print(f"{i:2}. [!] {test_file:45} NEEDS WORK ({status['lines']:4} lines, {status['tests']:2} tests)")
            if missing_patterns:
                print(f"      Missing patterns: {', '.join(missing_patterns[:3])}")
            summary["partial"] += 1
            summary["total_tests"] += status["tests"]
    
    print()
    print("=" * 80)
    print("SUMMARY:")
    print(f"  Comprehensive: {summary['comprehensive']}/20")
    print(f"  Partial:       {summary['partial']}/20")
    print(f"  Missing:       {summary['missing']}/20")
    print(f"  Total Tests:   {summary['total_tests']}")
    print()
    
    if summary["comprehensive"] >= 20:
        print("[SUCCESS] ALL TEST FILES ARE COMPREHENSIVE!")
    elif summary["comprehensive"] >= 15:
        print("[GOOD] Most test files are comprehensive. A few need updates.")
    else:
        print("[WARNING] Significant work needed to achieve comprehensive coverage.")

if __name__ == "__main__":
    main()