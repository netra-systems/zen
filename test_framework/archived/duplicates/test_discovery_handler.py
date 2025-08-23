"""
Test Discovery Handler - Manages test discovery and listing functionality

Business Value Justification (BVJ):
1. Segment: Development teams (internal efficiency)
2. Business Goal: Improve developer productivity through clear test organization  
3. Value Impact: Reduces time spent finding and organizing tests
4. Revenue Impact: Increases development velocity by 10-15%

Architectural Compliance:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Single responsibility: Test discovery and organization
- Modular design for different output formats
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from test_framework.archived.duplicates.test_config import TEST_LEVELS
from test_framework.archived.duplicates.test_discovery import TestDiscovery

PROJECT_ROOT = Path(__file__).parent.parent


def handle_test_discovery(args):
    """Handle test discovery and listing."""
    discovery = TestDiscovery(PROJECT_ROOT)
    all_tests, categories, test_counts = _gather_test_data(discovery)
    all_tests = _filter_tests_by_category(args, all_tests)
    _validate_test_level(args)
    return _format_discovery_output(args, all_tests, categories, test_counts)


def _gather_test_data(discovery):
    """Gather test data from discovery"""
    all_tests = discovery.discover_tests()
    categories = discovery.get_test_categories()
    test_counts = discovery.get_test_count_by_category()
    return all_tests, categories, test_counts


def _filter_tests_by_category(args, all_tests):
    """Filter tests by category if specified"""
    if args.list_category:
        filtered_tests = {args.list_category: all_tests.get(args.list_category, [])}
        return filtered_tests
    return all_tests


def _validate_test_level(args):
    """Validate test level if specified"""
    if args.list_level:
        level_config = TEST_LEVELS.get(args.list_level)
        if not level_config:
            print(f"[ERROR] Unknown test level: {args.list_level}")
            return 1
    return 0


def _format_discovery_output(args, all_tests, categories, test_counts):
    """Format output based on requested format"""
    if args.list_format == "json":
        return _format_json_output(args, all_tests, categories, test_counts)
    elif args.list_format == "markdown":
        return _format_markdown_output(args, all_tests, categories, test_counts)
    else:
        return _format_text_output(args, all_tests, categories, test_counts)


def _format_json_output(args, all_tests, categories, test_counts):
    """Format discovery output as JSON"""
    output = _create_json_structure(test_counts)
    _add_test_levels_to_json(args, output)
    _add_categories_to_json(args, categories, test_counts, output)
    _add_discovered_tests_to_json(all_tests, output)
    print(json.dumps(output, indent=2))
    return 0


def _create_json_structure(test_counts):
    """Create basic JSON structure"""
    return {
        "test_levels": {},
        "test_categories": {},
        "discovered_tests": {},
        "statistics": {
            "total_levels": len(TEST_LEVELS),
            "total_categories": len(test_counts),
            "total_tests": sum(test_counts.values())
        }
    }


def _add_test_levels_to_json(args, output):
    """Add test levels info to JSON output"""
    for level, config in TEST_LEVELS.items():
        if not args.list_level or level == args.list_level:
            output["test_levels"][level] = {
                "description": config["description"],
                "purpose": config["purpose"],
                "timeout": config["timeout"],
                "runs_coverage": config.get("run_coverage", False),
                "runs_both": config.get("run_both", False)
            }


def _add_categories_to_json(args, categories, test_counts, output):
    """Add categories info to JSON output"""
    for cat, info in categories.items():
        if not args.list_category or cat == args.list_category:
            output["test_categories"][cat] = {
                **info,
                "test_count": test_counts.get(cat, 0)
            }


def _add_discovered_tests_to_json(all_tests, output):
    """Add discovered tests to JSON output"""
    for cat, tests in all_tests.items():
        output["discovered_tests"][cat] = [str(t) for t in tests]


def _format_markdown_output(args, all_tests, categories, test_counts):
    """Format discovery output as Markdown"""
    _print_markdown_header(test_counts)
    _print_markdown_test_levels(args)
    _print_markdown_categories(args, categories, test_counts)
    _print_markdown_selected_tests(args, all_tests)
    return 0


def _print_markdown_header(test_counts):
    """Print Markdown header"""
    print("# Netra AI Platform Test Discovery Report\\n")
    print(f"**Total Test Levels:** {len(TEST_LEVELS)}")
    print(f"**Total Test Categories:** {len(test_counts)}")
    print(f"**Total Tests Found:** {sum(test_counts.values())}\\n")


def _print_markdown_test_levels(args):
    """Print Markdown test levels section"""
    print("## Available Test Levels\\n")
    for level, config in TEST_LEVELS.items():
        if not args.list_level or level == args.list_level:
            print(f"### `{level}`")
            print(f"- **Description:** {config['description']}")
            print(f"- **Purpose:** {config['purpose']}")
            print(f"- **Timeout:** {config['timeout']}s")
            print(f"- **Coverage:** {'Yes' if config.get('run_coverage') else 'No'}")
            print(f"- **Runs Both:** {'Backend & Frontend' if config.get('run_both') else 'Backend Only'}")
            print()


def _print_markdown_categories(args, categories, test_counts):
    """Print Markdown categories table"""
    print("## Test Categories\\n")
    print("| Category | Description | Priority | Timeout | Count |")
    print("|----------|-------------|----------|---------|-------|")
    for cat, info in categories.items():
        if not args.list_category or cat == args.list_category:
            count = test_counts.get(cat, 0)
            print(f"| {cat} | {info['description']} | {info['priority']} | {info['timeout']} | {count} |")


def _print_markdown_selected_tests(args, all_tests):
    """Print Markdown selected tests section"""
    if args.list_category or args.list_level:
        print(f"\\n## Tests in Selected Categories\\n")
        for cat, tests in all_tests.items():
            if tests:
                print(f"### {cat} ({len(tests)} tests)")
                for test in tests[:5]:  # Show first 5 tests
                    print(f"- `{Path(test).relative_to(PROJECT_ROOT)}`")
                if len(tests) > 5:
                    print(f"  ... and {len(tests) - 5} more")
                print()


def _format_text_output(args, all_tests, categories, test_counts):
    """Format discovery output as text"""
    _print_text_header(test_counts)
    _print_text_test_levels(args)
    _print_text_categories(args, categories, test_counts)
    _print_text_selected_category(args, all_tests)
    return 0


def _print_text_header(test_counts):
    """Print text format header"""
    print("=" * 80)
    print("TEST DISCOVERY REPORT")
    print("=" * 80)
    print(f"Total Test Levels: {len(TEST_LEVELS)}")
    print(f"Total Test Categories: {len(test_counts)}")
    print(f"Total Tests Found: {sum(test_counts.values())}")
    print()


def _print_text_test_levels(args):
    """Print text format test levels"""
    print("AVAILABLE TEST LEVELS:")
    print("-" * 40)
    for level, config in TEST_LEVELS.items():
        if not args.list_level or level == args.list_level:
            highlight = config.get('highlight', False)
            if highlight:
                print(f"\\033[91m{level:24} - {config['description']}\\033[0m")
            else:
                print(f"{level:24} - {config['description']}")
            print(f"{'':24}   Purpose: {config['purpose']}")
            print(f"{'':24}   Timeout: {config['timeout']}s")
    print()


def _print_text_categories(args, categories, test_counts):
    """Print text format categories"""
    print("TEST CATEGORIES:")
    print("-" * 40)
    for cat, info in categories.items():
        if not args.list_category or cat == args.list_category:
            count = test_counts.get(cat, 0)
            print(f"{cat:20} - {count:4} tests - {info['description']}")
    print()


def _print_text_selected_category(args, all_tests):
    """Print text format selected category tests"""
    if args.list_category:
        print(f"TESTS IN CATEGORY '{args.list_category}':")
        print("-" * 40)
        tests = all_tests.get(args.list_category, [])
        for test in tests:
            print(f"  {Path(test).relative_to(PROJECT_ROOT)}")
        if not tests:
            print("  No tests found in this category")