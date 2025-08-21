"""Failing tests management utilities."""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .test_parser import extract_failing_tests


def _read_failing_tests_file(failing_tests_path: Path) -> Optional[Dict]:
    """Read failing tests from JSON file."""
    if not failing_tests_path.exists():
        return None
    try:
        with open(failing_tests_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def _create_default_structure() -> Dict:
    """Create default failing tests structure."""
    return {
        "last_updated": datetime.now().isoformat(),
        "backend": {"count": 0, "failures": []},
        "frontend": {"count": 0, "failures": []},
        "e2e": {"count": 0, "failures": []}
    }

def load_failing_tests(reports_dir: Path) -> Dict:
    """Load existing failing tests from JSON file."""
    failing_tests_path = reports_dir / "failing_tests.json"
    failing_tests = _read_failing_tests_file(failing_tests_path)
    if failing_tests is not None:
        return failing_tests
    return _create_default_structure()

def _remove_passed_tests(failing_tests: Dict, component: str, passed_tests: List[str]):
    """Remove tests that passed from failures list."""
    if not passed_tests:
        return
    failing_tests[component]["failures"] = [
        f for f in failing_tests[component]["failures"]
        if f"{f['test_path']}::{f['test_name']}" not in passed_tests
    ]

def _find_existing_failure(failures: List[Dict], new_failure: Dict) -> Optional[int]:
    """Find existing failure index by test path and name."""
    for i, old_failure in enumerate(failures):
        if (old_failure["test_path"] == new_failure["test_path"] and 
            old_failure["test_name"] == new_failure["test_name"]):
            return i
    return None

def _update_existing_failure(old_failure: Dict, new_failure: Dict):
    """Update existing failure with new error information."""
    old_failure["consecutive_failures"] += 1
    old_failure["error_message"] = new_failure["error_message"]
    old_failure["error_type"] = new_failure["error_type"]
    if "traceback" in new_failure:
        old_failure["traceback"] = new_failure["traceback"]

def _process_new_failures(failing_tests: Dict, component: str, new_failures: List[Dict]):
    """Process list of new failures, updating or adding as needed."""
    for new_failure in new_failures:
        existing_index = _find_existing_failure(failing_tests[component]["failures"], new_failure)
        if existing_index is not None:
            _update_existing_failure(failing_tests[component]["failures"][existing_index], new_failure)
        else:
            failing_tests[component]["failures"].append(new_failure)

def _save_updated_tests(failing_tests: Dict, reports_dir: Path):
    """Save updated failing tests to JSON file."""
    failing_tests_path = reports_dir / "failing_tests.json"
    with open(failing_tests_path, 'w', encoding='utf-8') as f:
        json.dump(failing_tests, f, indent=2)

def update_failing_tests(component: str, new_failures: List[Dict], passed_tests: List[str], reports_dir: Path) -> Dict:
    """Update failing tests log with new results."""
    failing_tests = load_failing_tests(reports_dir)
    failing_tests["last_updated"] = datetime.now().isoformat()
    if component not in failing_tests:
        failing_tests[component] = {"count": 0, "failures": []}
    _remove_passed_tests(failing_tests, component, passed_tests)
    _process_new_failures(failing_tests, component, new_failures)
    failing_tests[component]["count"] = len(failing_tests[component]["failures"])
    _save_updated_tests(failing_tests, reports_dir)
    return failing_tests

def organize_failures_by_category(failures: List[Dict], categorize_func) -> Dict[str, List[Dict]]:
    """Organize failures by category for better processing."""
    organized = defaultdict(list)
    for failure in failures:
        category = categorize_func(failure.get("test_path", ""), failure.get("component", "backend"))
        organized[category].append(failure)
    return dict(organized)

def _print_failing_tests_header(failing_tests: Dict):
    """Print header for failing tests display."""
    print("\n" + "=" * 80)
    print("CURRENTLY FAILING TESTS")
    print("=" * 80)
    print(f"Last Updated: {failing_tests.get('last_updated', 'N/A')}\n")

def _print_component_failures(component: str, component_data: Dict):
    """Print failures for a specific component."""
    print(f"\n{component.upper()} ({component_data['count']} failures):")
    print("-" * 40)
    for i, failure in enumerate(component_data["failures"], 1):
        print(f"{i}. {failure['test_path']}::{failure['test_name']}")
        print(f"   Error: {failure['error_type']} - {failure['error_message'][:100]}...")
        print(f"   Consecutive Failures: {failure.get('consecutive_failures', 1)}")

def _has_any_failures(failing_tests: Dict) -> bool:
    """Check if there are any failures across all components."""
    return any(failing_tests.get(c, {}).get("count", 0) > 0 for c in ["backend", "frontend", "e2e"])

def show_failing_tests(reports_dir: Path):
    """Display current failing tests."""
    failing_tests = load_failing_tests(reports_dir)
    _print_failing_tests_header(failing_tests)
    for component in ["backend", "frontend", "e2e"]:
        if component in failing_tests and failing_tests[component]["count"] > 0:
            _print_component_failures(component, failing_tests[component])
    if not _has_any_failures(failing_tests):
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