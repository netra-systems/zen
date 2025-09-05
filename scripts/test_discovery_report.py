#!/usr/bin/env python
"""
Enhanced Test Discovery Report
Shows all test categories including real e2e tests prominently.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path

from test_framework.test_config import TEST_LEVELS
from test_framework.test_discovery import TestDiscovery


class EnhancedTestDiscoveryReport:
    """Enhanced test discovery reporting."""
    
    def __init__(self):
        self.discovery = TestDiscovery(PROJECT_ROOT)
        self.real_e2e_tests = []
        self.frontend_tests = []
        self.backend_tests = []
        self.cypress_tests = []
        
    def discover_all_tests(self) -> Dict[str, List[str]]:
        """Discover all tests with enhanced categorization."""
        all_tests = self.discovery.discover_tests()
        self._categorize_special_tests(all_tests)
        return all_tests
    
    def _categorize_special_tests(self, all_tests: Dict[str, List[str]]):
        """Categorize tests into special groups."""
        for category, tests in all_tests.items():
            for test in tests:
                self._categorize_single_test(test, category)
    
    def _categorize_single_test(self, test: str, category: str):
        """Categorize a single test."""
        test_lower = test.lower()
        if "real_" in test_lower or "_real" in test_lower:
            self.real_e2e_tests.append(test)
        if "frontend" in test:
            self.frontend_tests.append(test)
        elif "cypress" in test_lower:
            self.cypress_tests.append(test)
        else:
            self.backend_tests.append(test)
    
    def print_comprehensive_report(self):
        """Print comprehensive test discovery report."""
        all_tests = self.discover_all_tests()
        self._print_header()
        self._print_real_e2e_section()
        self._print_test_levels_section()
        self._print_test_categories_section(all_tests)
        self._print_test_type_summary()
    
    def _print_header(self):
        """Print report header."""
        print("=" * 80)
        print("NETRA AI PLATFORM - COMPREHENSIVE TEST DISCOVERY REPORT")
        print("=" * 80)
        print()
    
    def _print_real_e2e_section(self):
        """Print real e2e tests prominently."""
        print("\033[91m" + "[REAL E2E] TESTS WITH ACTUAL LLM/SERVICES" + "\033[0m")
        print("-" * 80)
        if self.real_e2e_tests:
            print(f"Found {len(self.real_e2e_tests)} real e2e tests:")
            for test in self.real_e2e_tests[:10]:
                relative_path = Path(test).relative_to(PROJECT_ROOT)
                print(f"  [OK] {relative_path}")
            if len(self.real_e2e_tests) > 10:
                print(f"  ... and {len(self.real_e2e_tests) - 10} more")
        else:
            print("  No real e2e tests found")
        print()
        print("To run real e2e tests:")
        print("  python test_runner.py --level real_e2e --real-llm")
        print()
    
    def _print_test_levels_section(self):
        """Print available test levels."""
        print("AVAILABLE TEST LEVELS")
        print("-" * 80)
        for level, config in TEST_LEVELS.items():
            if config.get('highlight'):
                print(f"\033[91m{level:20}\033[0m - {config['description']}")
            else:
                print(f"{level:20} - {config['description']}")
        print()
    
    def _print_test_categories_section(self, all_tests: Dict[str, List[str]]):
        """Print test categories with counts."""
        print("TEST CATEGORIES & COUNTS")
        print("-" * 80)
        categories = self.discovery.get_test_categories()
        for cat, info in sorted(categories.items()):
            count = len(all_tests.get(cat, []))
            if cat in ["real_e2e", "real_services"]:
                print(f"\033[91m{cat:15} ({count:4} tests)\033[0m - {info['description']}")
            else:
                print(f"{cat:15} ({count:4} tests) - {info['description']}")
        print()
    
    def _print_test_type_summary(self):
        """Print summary by test type."""
        print("TEST TYPE SUMMARY")
        print("-" * 80)
        print(f"Backend Tests:     {len(self.backend_tests):4} tests")
        print(f"Frontend Tests:    {len(self.frontend_tests):4} tests")
        print(f"Cypress E2E:       {len(self.cypress_tests):4} tests")
        print(f"\033[91mReal E2E Tests:    {len(self.real_e2e_tests):4} tests\033[0m")
        print()
        total = len(self.backend_tests) + len(self.frontend_tests) + len(self.cypress_tests)
        print(f"TOTAL:             {total:4} tests")
        print()
    
    def print_real_e2e_details(self):
        """Print detailed real e2e test information."""
        print("\033[91m" + "=" * 80 + "\033[0m")
        print("\033[91m" + "DETAILED REAL E2E TEST INFORMATION" + "\033[0m")
        print("\033[91m" + "=" * 80 + "\033[0m")
        print()
        
        if not self.real_e2e_tests:
            print("No real e2e tests found.")
            return
        
        # Group by directory
        tests_by_dir = defaultdict(list)
        for test in self.real_e2e_tests:
            dir_path = Path(test).parent
            tests_by_dir[str(dir_path)].append(test)
        
        for directory, tests in sorted(tests_by_dir.items()):
            relative_dir = Path(directory).relative_to(PROJECT_ROOT)
            print(f"\n[DIR] {relative_dir}/")
            for test in sorted(tests):
                test_name = Path(test).name
                print(f"    [OK] {test_name}")
        
        print()
        print("RUNNING REAL E2E TESTS:")
        print("-" * 40)
        print("1. Quick real e2e test (with mock services):")
        print("   python test_runner.py --level real_e2e")
        print()
        print("2. Full real e2e test (with actual LLM):")
        print("   python test_runner.py --level real_e2e --real-llm")
        print()
        print("3. With specific LLM model:")
        print("   python test_runner.py --level real_e2e --real-llm --llm-model gemini-2.5-pro")
        print()


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Enhanced Test Discovery Report")
    parser.add_argument("--real-e2e", action="store_true", 
                       help="Show detailed real e2e test information")
    args = parser.parse_args()
    
    reporter = EnhancedTestDiscoveryReport()
    
    if args.real_e2e:
        reporter.discover_all_tests()
        reporter.print_real_e2e_details()
    else:
        reporter.print_comprehensive_report()


if __name__ == "__main__":
    main()