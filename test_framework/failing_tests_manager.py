"""Failing tests management utilities."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from .test_parser import extract_failing_tests

def load_failing_tests(reports_dir: Path) -> Dict:
    """Load existing failing tests from JSON file."""
    failing_tests_path = reports_dir / "failing_tests.json"
    
    if failing_tests_path.exists():
        try:
            with open(failing_tests_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Return default structure if file doesn't exist or is invalid
    return {
        "last_updated": datetime.now().isoformat(),
        "backend": {"count": 0, "failures": []},
        "frontend": {"count": 0, "failures": []},
        "e2e": {"count": 0, "failures": []}
    }

def update_failing_tests(component: str, new_failures: List[Dict], passed_tests: List[str], reports_dir: Path) -> Dict:
    """Update failing tests log with new results."""
    failing_tests = load_failing_tests(reports_dir)
    
    # Update timestamp
    failing_tests["last_updated"] = datetime.now().isoformat()
    
    if component not in failing_tests:
        failing_tests[component] = {"count": 0, "failures": []}
    
    # Remove tests that passed
    if passed_tests:
        failing_tests[component]["failures"] = [
            f for f in failing_tests[component]["failures"]
            if f"{f['test_path']}::{f['test_name']}" not in passed_tests
        ]
    
    # Update or add new failures
    for new_failure in new_failures:
        existing = None
        for i, old_failure in enumerate(failing_tests[component]["failures"]):
            if (old_failure["test_path"] == new_failure["test_path"] and 
                old_failure["test_name"] == new_failure["test_name"]):
                existing = i
                break
        
        if existing is not None:
            # Update existing failure
            old_failure = failing_tests[component]["failures"][existing]
            old_failure["consecutive_failures"] += 1
            old_failure["error_message"] = new_failure["error_message"]
            old_failure["error_type"] = new_failure["error_type"]
            if "traceback" in new_failure:
                old_failure["traceback"] = new_failure["traceback"]
        else:
            # Add new failure
            failing_tests[component]["failures"].append(new_failure)
    
    # Update counts
    failing_tests[component]["count"] = len(failing_tests[component]["failures"])
    
    # Save updated failing tests
    failing_tests_path = reports_dir / "failing_tests.json"
    with open(failing_tests_path, 'w', encoding='utf-8') as f:
        json.dump(failing_tests, f, indent=2)
    
    return failing_tests

def organize_failures_by_category(failures: List[Dict], categorize_func) -> Dict[str, List[Dict]]:
    """Organize failures by category for better processing."""
    organized = defaultdict(list)
    for failure in failures:
        category = categorize_func(failure.get("test_path", ""), failure.get("component", "backend"))
        organized[category].append(failure)
    return dict(organized)

def show_failing_tests(reports_dir: Path):
    """Display current failing tests."""
    failing_tests = load_failing_tests(reports_dir)
    print("\n" + "=" * 80)
    print("CURRENTLY FAILING TESTS")
    print("=" * 80)
    print(f"Last Updated: {failing_tests.get('last_updated', 'N/A')}\n")
    
    for component in ["backend", "frontend", "e2e"]:
        if component in failing_tests and failing_tests[component]["count"] > 0:
            print(f"\n{component.upper()} ({failing_tests[component]['count']} failures):")
            print("-" * 40)
            for i, failure in enumerate(failing_tests[component]["failures"], 1):
                print(f"{i}. {failure['test_path']}::{failure['test_name']}")
                print(f"   Error: {failure['error_type']} - {failure['error_message'][:100]}...")
                print(f"   Consecutive Failures: {failure.get('consecutive_failures', 1)}")
    
    if all(failing_tests.get(c, {}).get("count", 0) == 0 for c in ["backend", "frontend", "e2e"]):
        print("No failing tests found!")
    
    print("\n" + "=" * 80)

def clear_failing_tests(reports_dir: Path):
    """Clear the failing tests log."""
    failing_tests_path = reports_dir / "failing_tests.json"
    if failing_tests_path.exists():
        failing_tests_path.unlink()
        print("[INFO] Failing tests log cleared")
    else:
        print("[INFO] No failing tests log to clear")