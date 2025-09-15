#!/usr/bin/env python3
"""
Direct Factory Analysis Script
Analyzes factory patterns without test framework dependencies.
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict, Counter


def find_factory_classes():
    """Scan codebase for factory classes and categorize them."""
    project_root = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")
    source_dirs = [
        project_root / "netra_backend" / "app",
        project_root / "auth_service",
        project_root / "shared",
        project_root / "test_framework"
    ]

    factory_classes = []
    factory_usage = defaultdict(int)

    for source_dir in source_dirs:
        if not source_dir.exists():
            continue

        for py_file in source_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST to find factory classes
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        if ("Factory" in class_name or
                            class_name.endswith("Factory") or
                            "factory" in class_name.lower()):

                            factory_info = {
                                "name": class_name,
                                "file": str(py_file.relative_to(project_root)),
                                "line_count": len(content.splitlines()),
                                "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                                "static_methods": [n.name for n in node.body
                                                 if isinstance(n, ast.FunctionDef) and
                                                 any(isinstance(d, ast.Name) and d.id == 'staticmethod'
                                                     for d in n.decorator_list)]
                            }
                            factory_classes.append(factory_info)

                # Count factory usage in this file
                for factory in factory_classes:
                    usage_count = content.count(factory["name"])
                    factory_usage[factory["name"]] += usage_count

            except Exception as e:
                # Skip files that can't be parsed
                continue

    return factory_classes, factory_usage


def categorize_factories_by_domain(factory_classes):
    """Categorize factories by business domain."""
    categories = {
        "user_isolation": [],
        "websocket": [],
        "database": [],
        "auth": [],
        "tools": [],
        "execution": [],
        "testing": [],
        "unknown": []
    }

    for factory in factory_classes:
        name_lower = factory["name"].lower()
        file_path = factory["file"].lower()

        if "user" in name_lower and ("context" in name_lower or "isolation" in name_lower):
            categories["user_isolation"].append(factory)
        elif "websocket" in name_lower or "socket" in name_lower:
            categories["websocket"].append(factory)
        elif "database" in name_lower or "db" in name_lower or "session" in name_lower:
            categories["database"].append(factory)
        elif "auth" in name_lower or "token" in name_lower:
            categories["auth"].append(factory)
        elif "tool" in name_lower or "dispatcher" in name_lower:
            categories["tools"].append(factory)
        elif "execution" in name_lower or "engine" in name_lower:
            categories["execution"].append(factory)
        elif "test" in file_path or "mock" in name_lower:
            categories["testing"].append(factory)
        else:
            categories["unknown"].append(factory)

    return categories


def analyze_factory_proliferation():
    """Main analysis function."""
    print("FACTORY PROLIFERATION ANALYSIS")
    print("=" * 50)

    # Find all factory classes
    factory_classes, factory_usage = find_factory_classes()
    categories = categorize_factories_by_domain(factory_classes)

    total_factories = len(factory_classes)
    non_test_factories = total_factories - len(categories["testing"])

    print(f"FACTORY DISCOVERY RESULTS:")
    print(f"   Total Factories Found: {total_factories}")
    print(f"   Non-Test Factories: {non_test_factories}")
    print(f"   Test-Related Factories: {len(categories['testing'])}")
    print()

    # Business justification thresholds
    thresholds = {
        "user_isolation": 5,
        "websocket": 3,
        "database": 4,
        "auth": 3,
        "tools": 2,
        "execution": 3,
        "testing": 999,  # Testing factories are allowed
        "unknown": 0     # Unknown factories should be zero
    }

    print(f"CATEGORY BREAKDOWN:")
    violations = []

    for category, threshold in thresholds.items():
        count = len(categories[category])
        status = " PASS" if count <= threshold or category == "testing" else " FAIL"

        if category != "testing" and count > threshold:
            violations.append(f"{category}: {count} factories (threshold: {threshold})")

        print(f"   {category.title().replace('_', ' ')}: {count} factories (threshold: {threshold}) {status}")

    # Check total factory count (excluding testing)
    max_total_factories = 20
    if non_test_factories > max_total_factories:
        violations.append(f"Total: {non_test_factories} factories (threshold: {max_total_factories})")

    print()
    print(f"OVER-ENGINEERING ASSESSMENT:")
    if violations:
        print(f"   VIOLATIONS DETECTED: {len(violations)}")
        for violation in violations:
            print(f"   - {violation}")
        print()
        print(f"   RESULT: Factory proliferation detected - cleanup required!")
        print(f"   Over-Engineering Score: {non_test_factories}/{max_total_factories} ({((non_test_factories/max_total_factories)*100):.0f}%)")
    else:
        print(f"   RESULT: Factory count within acceptable limits")

    print()
    print(f"TOP FACTORY CATEGORIES (Non-Test):")

    non_test_categories = {k: v for k, v in categories.items() if k != "testing"}
    sorted_categories = sorted(non_test_categories.items(), key=lambda x: len(x[1]), reverse=True)

    for category, factories in sorted_categories[:5]:
        if factories:
            print(f"   {category.title().replace('_', ' ')}: {len(factories)} factories")
            for factory in factories[:3]:  # Show top 3
                print(f"     - {factory['name']} ({factory['file']})")
            if len(factories) > 3:
                print(f"     ... and {len(factories) - 3} more")

    print()
    print(f"CLEANUP RECOMMENDATIONS:")

    # Single-use factory analysis
    single_use_factories = []
    for factory in factory_classes:
        if "test" not in factory["file"].lower():
            usage_count = factory_usage.get(factory["name"], 0)
            if usage_count <= 2 and usage_count > 0:
                single_use_factories.append(factory)

    if single_use_factories:
        print(f"    Single-Use Factories ({len(single_use_factories)} found):")
        for factory in single_use_factories[:5]:  # Show top 5
            print(f"     - {factory['name']} (used {factory_usage.get(factory['name'], 0)}x) - Replace with direct instantiation")
        if len(single_use_factories) > 5:
            print(f"     ... and {len(single_use_factories) - 5} more")

    # Large factory analysis
    large_factories = [f for f in factory_classes if f["line_count"] > 200 and "test" not in f["file"].lower()]
    if large_factories:
        print(f"    Oversized Factories ({len(large_factories)} found):")
        for factory in sorted(large_factories, key=lambda x: x["line_count"], reverse=True)[:5]:
            print(f"     - {factory['name']} ({factory['line_count']} lines) - Split into smaller components")

    # High method count factories
    high_method_factories = [f for f in factory_classes if len(f["methods"]) > 10 and "test" not in f["file"].lower()]
    if high_method_factories:
        print(f"    Complex Factories ({len(high_method_factories)} found):")
        for factory in sorted(high_method_factories, key=lambda x: len(x["methods"]), reverse=True)[:5]:
            print(f"     - {factory['name']} ({len(factory['methods'])} methods) - Reduce complexity")

    print()
    print(f" BUSINESS VALUE ANALYSIS:")

    essential_categories = ["user_isolation", "auth", "websocket"]
    essential_factories = sum(len(categories[cat]) for cat in essential_categories)
    over_engineered_factories = non_test_factories - essential_factories

    print(f"   Essential Factories (User Isolation, Auth, WebSocket): {essential_factories}")
    print(f"   Over-Engineered Factories: {over_engineered_factories}")
    print(f"   Cleanup Potential: {over_engineered_factories} factories can be simplified/removed")

    if over_engineered_factories > 0:
        performance_improvement = min(over_engineered_factories * 2, 25)  # Estimate 2% per factory, max 25%
        print(f"   Estimated Performance Improvement: +{performance_improvement}%")

    print()
    print(f" PHASE 2 FACTORY CLEANUP SUMMARY:")
    print(f"   Current Status: {non_test_factories} factories (Target: <=20)")
    print(f"   Cleanup Opportunity: {max(0, non_test_factories - 20)} factories to remove/simplify")
    print(f"   Business Impact: Simplified architecture, improved performance, easier maintenance")

    return {
        "total_factories": total_factories,
        "non_test_factories": non_test_factories,
        "violations": violations,
        "categories": categories,
        "single_use_factories": single_use_factories,
        "large_factories": large_factories,
        "high_method_factories": high_method_factories,
        "essential_factories": essential_factories,
        "over_engineered_factories": over_engineered_factories
    }


if __name__ == "__main__":
    results = analyze_factory_proliferation()

    # Print specific remediation recommendations
    print()
    print("️  SPECIFIC REMEDIATION PLAN:")
    print("="*50)

    if results["single_use_factories"]:
        print("1. IMMEDIATE WINS - Single-Use Factory Removal:")
        for factory in results["single_use_factories"][:10]:
            print(f"    Remove {factory['name']} - Replace with direct instantiation")

    if results["large_factories"]:
        print("\n2. ARCHITECTURE SIMPLIFICATION - Oversized Factory Refactoring:")
        for factory in results["large_factories"][:5]:
            print(f"    Refactor {factory['name']} ({factory['line_count']} lines) - Split into focused components")

    if results["high_method_factories"]:
        print("\n3. COMPLEXITY REDUCTION - Method Count Optimization:")
        for factory in results["high_method_factories"][:5]:
            print(f"    Simplify {factory['name']} ({len(factory['methods'])} methods) - Extract utility functions")

    print(f"\nTARGET STATE: {results['essential_factories']} essential factories + minimal support factories = <=20 total")
    print(f" BUSINESS BENEFIT: Improved maintainability, reduced complexity, enhanced performance")