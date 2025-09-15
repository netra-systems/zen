#!/usr/bin/env python3
"""
Quick demo to show the actual command generation for Issue #1270
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "tests"))

from unified_test_runner import UnifiedTestRunner

def demo_command_generation():
    """Demonstrate the command generation issue"""
    print("🔍 ISSUE #1270 COMMAND GENERATION DEMO")
    print("="*60)

    runner = UnifiedTestRunner()

    # Mock args
    class MockArgs:
        def __init__(self, pattern=None):
            self.pattern = pattern
            self.no_coverage = True
            self.parallel = False
            self.verbose = False
            self.fast_fail = False
            self.env = "test"

    test_cases = [
        ("Database with pattern", "database", "test_connection"),
        ("Database without pattern", "database", None),
        ("E2E with pattern", "e2e", "test_auth"),
        ("Unit with pattern", "unit", "test_model"),
    ]

    for name, category, pattern in test_cases:
        args = MockArgs(pattern=pattern)
        cmd = runner._build_pytest_command("backend", category, args)

        has_k_filter = " -k " in cmd
        pattern_text = f"pattern='{pattern}'" if pattern else "no pattern"

        print(f"\n{name} ({pattern_text}):")
        print(f"  Command: {cmd}")
        print(f"  Has -k filter: {'YES' if has_k_filter else 'NO'}")

        if category == "database" and pattern and has_k_filter:
            print("  🐛 BUG: Database should NOT have -k filter with pattern!")
        elif category != "database" and pattern and has_k_filter:
            print("  ✅ CORRECT: Non-database categories should have -k filter")
        elif not pattern and not has_k_filter:
            print("  ✅ CORRECT: No pattern means no -k filter")

if __name__ == "__main__":
    demo_command_generation()