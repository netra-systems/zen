"""
Factory Complexity Analysis - Phase 2 Validation
Analyzes factory implementations for unnecessary complexity.

Business Impact: $500K+ ARR protection through architectural simplification
Created: 2025-09-15
Purpose: Identify complex factories that exceed reasonable size/complexity limits
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
from test_framework.ssot.base_test_case import SSotBaseTestCase


class FactoryComplexityPhase2Tests(SSotBaseTestCase):
    """Validate factory implementations against complexity thresholds."""

    def setUp(self):
        """Set up test environment with codebase paths."""
        super().setUp()
        self.project_root = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")
        self.source_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service",
            self.project_root / "shared",
            self.project_root / "test_framework"
        ]

    def analyze_factory_complexity(self):
        """Analyze all factory classes for complexity metrics."""
        factory_analysis = []

        for source_dir in self.source_dirs:
            if not source_dir.exists():
                continue

            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.splitlines()

                    # Parse AST to find factory classes
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            if ("Factory" in class_name or
                                class_name.endswith("Factory") or
                                "factory" in class_name.lower()):

                                # Skip test factories for complexity analysis
                                if "test" in str(py_file).lower() or "mock" in class_name.lower():
                                    continue

                                # Calculate complexity metrics
                                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                                static_methods = [n for n in methods
                                                if any(isinstance(d, ast.Name) and d.id == 'staticmethod'
                                                       for d in n.decorator_list)]
                                property_methods = [n for n in methods
                                                  if any(isinstance(d, ast.Name) and d.id == 'property'
                                                         for d in n.decorator_list)]

                                # Calculate lines of code for this class
                                class_start_line = node.lineno
                                class_end_line = node.end_lineno if hasattr(node, 'end_lineno') else len(lines)
                                class_lines = class_end_line - class_start_line + 1

                                # Calculate cyclomatic complexity (simplified)
                                complexity_score = 0
                                for method in methods:
                                    for child in ast.walk(method):
                                        if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                                            complexity_score += 1
                                        elif isinstance(child, ast.BoolOp):
                                            complexity_score += len(child.values) - 1

                                # Analyze method complexity
                                method_analyses = []
                                for method in methods:
                                    method_start = method.lineno
                                    method_end = method.end_lineno if hasattr(method, 'end_lineno') else method_start + 20
                                    method_lines = method_end - method_start + 1

                                    # Count parameters
                                    param_count = len(method.args.args)

                                    method_analyses.append({
                                        "name": method.name,
                                        "lines": method_lines,
                                        "params": param_count,
                                        "is_static": method in static_methods,
                                        "is_property": method in property_methods
                                    })

                                factory_info = {
                                    "name": class_name,
                                    "file": str(py_file.relative_to(self.project_root)),
                                    "total_lines": class_lines,
                                    "method_count": len(methods),
                                    "static_method_count": len(static_methods),
                                    "property_count": len(property_methods),
                                    "complexity_score": complexity_score,
                                    "methods": method_analyses,
                                    "static_ratio": len(static_methods) / len(methods) if methods else 0
                                }

                                factory_analysis.append(factory_info)

                except Exception as e:
                    # Skip files that can't be parsed
                    continue

        return factory_analysis

    def test_01_factory_lines_of_code_analysis(self):
        """
        EXPECTED: FAIL - Shows factories exceeding reasonable size limits

        Simple factories should be <50 lines, complex factories <200 lines.
        Anything larger indicates potential over-engineering.

        Thresholds:
        - Simple factories: ≤50 lines (basic instantiation patterns)
        - Complex factories: ≤200 lines (with business logic)
        - Mega factories: >200 lines (likely over-engineered)
        """
        factory_analysis = self.analyze_factory_complexity()

        # Define size thresholds
        simple_threshold = 50
        complex_threshold = 200

        oversized_factories = []
        size_distribution = {
            "tiny": [],       # ≤25 lines
            "small": [],      # 26-50 lines
            "medium": [],     # 51-100 lines
            "large": [],      # 101-200 lines
            "oversized": []   # >200 lines
        }

        for factory in factory_analysis:
            lines = factory["total_lines"]

            # Categorize by size
            if lines <= 25:
                size_distribution["tiny"].append(factory)
            elif lines <= 50:
                size_distribution["small"].append(factory)
            elif lines <= 100:
                size_distribution["medium"].append(factory)
            elif lines <= 200:
                size_distribution["large"].append(factory)
            else:
                size_distribution["oversized"].append(factory)
                oversized_factories.append(factory)

        # Generate report
        report = f"""
FACTORY SIZE ANALYSIS
=====================

Total Factories Analyzed: {len(factory_analysis)}

Size Distribution:
- Tiny (≤25 lines): {len(size_distribution["tiny"])} factories
- Small (26-50 lines): {len(size_distribution["small"])} factories
- Medium (51-100 lines): {len(size_distribution["medium"])} factories
- Large (101-200 lines): {len(size_distribution["large"])} factories
- Oversized (>200 lines): {len(size_distribution["oversized"])} factories ⚠️

"""

        if oversized_factories:
            report += f"OVERSIZED FACTORIES (>200 lines - Likely Over-Engineered):\n"
            for factory in sorted(oversized_factories, key=lambda x: x["total_lines"], reverse=True):
                report += f"\n- {factory['name']}\n"
                report += f"  File: {factory['file']}\n"
                report += f"  Lines: {factory['total_lines']} (threshold: {complex_threshold})\n"
                report += f"  Methods: {factory['method_count']}\n"
                report += f"  Complexity Score: {factory['complexity_score']}\n"
                report += f"  Recommendation: Split into smaller, focused factories\n"

        # Show size recommendations
        report += f"\n\nSIZE RECOMMENDATIONS:\n"
        for category, factories in size_distribution.items():
            if factories:
                avg_lines = sum(f["total_lines"] for f in factories) / len(factories)
                report += f"- {category.title()}: {len(factories)} factories (avg: {avg_lines:.1f} lines)\n"

        # Detailed analysis of largest factories
        largest_factories = sorted(factory_analysis, key=lambda x: x["total_lines"], reverse=True)[:10]
        report += f"\n\nTOP 10 LARGEST FACTORIES:\n"
        for i, factory in enumerate(largest_factories, 1):
            status = "✗ OVERSIZED" if factory["total_lines"] > complex_threshold else "✓ ACCEPTABLE"
            report += f"{i:2d}. {factory['name']}: {factory['total_lines']} lines {status}\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        if oversized_factories:
            max_size = max(f["total_lines"] for f in oversized_factories)
            self.fail(f"Factory size violations detected: {len(oversized_factories)} factories exceed "
                     f"{complex_threshold}-line threshold. Largest factory: {max_size} lines. "
                     f"Refactoring required for maintainability.")
        else:
            self.fail("No oversized factories detected - this may indicate measurement issues or "
                     "unexpectedly good architecture.")

    def test_02_factory_method_count_analysis(self):
        """
        EXPECTED: FAIL - Demonstrates factories with excessive methods

        Most factories should have 2-5 methods. >10 methods indicates
        the factory is doing too much and should be split.

        Method Count Guidelines:
        - Simple factory: 2-3 methods (create, configure)
        - Standard factory: 4-5 methods (create, configure, validate, cleanup)
        - Complex factory: 6-10 methods (multiple creation patterns)
        - Over-engineered: >10 methods (should be split)
        """
        factory_analysis = self.analyze_factory_complexity()

        # Define method count thresholds
        simple_threshold = 3
        standard_threshold = 5
        complex_threshold = 10

        method_violations = []
        method_distribution = {
            "minimal": [],    # 1-3 methods
            "standard": [],   # 4-5 methods
            "complex": [],    # 6-10 methods
            "excessive": []   # >10 methods
        }

        for factory in factory_analysis:
            method_count = factory["method_count"]

            # Categorize by method count
            if method_count <= 3:
                method_distribution["minimal"].append(factory)
            elif method_count <= 5:
                method_distribution["standard"].append(factory)
            elif method_count <= 10:
                method_distribution["complex"].append(factory)
            else:
                method_distribution["excessive"].append(factory)
                method_violations.append(factory)

        # Generate report
        report = f"""
FACTORY METHOD COUNT ANALYSIS
=============================

Total Factories Analyzed: {len(factory_analysis)}

Method Count Distribution:
- Minimal (1-3 methods): {len(method_distribution["minimal"])} factories
- Standard (4-5 methods): {len(method_distribution["standard"])} factories
- Complex (6-10 methods): {len(method_distribution["complex"])} factories
- Excessive (>10 methods): {len(method_distribution["excessive"])} factories ⚠️

"""

        if method_violations:
            report += f"EXCESSIVE METHOD COUNT VIOLATIONS (>10 methods):\n"
            for factory in sorted(method_violations, key=lambda x: x["method_count"], reverse=True):
                report += f"\n- {factory['name']}\n"
                report += f"  File: {factory['file']}\n"
                report += f"  Methods: {factory['method_count']} (threshold: {complex_threshold})\n"
                report += f"  Lines: {factory['total_lines']}\n"

                # Show method breakdown
                methods_by_type = {
                    "static": [m for m in factory["methods"] if m["is_static"]],
                    "property": [m for m in factory["methods"] if m["is_property"]],
                    "instance": [m for m in factory["methods"]
                               if not m["is_static"] and not m["is_property"]]
                }

                report += f"  Method Breakdown:\n"
                report += f"    - Instance methods: {len(methods_by_type['instance'])}\n"
                report += f"    - Static methods: {len(methods_by_type['static'])}\n"
                report += f"    - Properties: {len(methods_by_type['property'])}\n"

                # Show largest methods
                largest_methods = sorted(factory["methods"], key=lambda x: x["lines"], reverse=True)[:3]
                report += f"  Largest Methods:\n"
                for method in largest_methods:
                    report += f"    - {method['name']}: {method['lines']} lines\n"

                report += f"  Recommendation: Split into smaller, focused factories\n"

        # Show method count statistics
        if factory_analysis:
            method_counts = [f["method_count"] for f in factory_analysis]
            avg_methods = sum(method_counts) / len(method_counts)
            max_methods = max(method_counts)
            min_methods = min(method_counts)

            report += f"\n\nMETHOD COUNT STATISTICS:\n"
            report += f"- Average: {avg_methods:.1f} methods per factory\n"
            report += f"- Range: {min_methods}-{max_methods} methods\n"
            report += f"- Recommended range: 2-5 methods for most factories\n"

        # Top factories by method count
        top_method_factories = sorted(factory_analysis, key=lambda x: x["method_count"], reverse=True)[:10]
        report += f"\n\nTOP 10 FACTORIES BY METHOD COUNT:\n"
        for i, factory in enumerate(top_method_factories, 1):
            status = "✗ EXCESSIVE" if factory["method_count"] > complex_threshold else "✓ ACCEPTABLE"
            report += f"{i:2d}. {factory['name']}: {factory['method_count']} methods {status}\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        if method_violations:
            max_methods = max(f["method_count"] for f in method_violations)
            self.fail(f"Factory method count violations detected: {len(method_violations)} factories "
                     f"exceed {complex_threshold}-method threshold. Maximum methods: {max_methods}. "
                     f"Factory splitting required for maintainability.")
        else:
            self.fail("No method count violations detected - this may indicate measurement issues.")

    def test_03_factory_static_method_ratio_analysis(self):
        """
        EXPECTED: FAIL - Shows factories that are just utility modules

        If all methods are static, the factory pattern adds no value
        and should be converted to a utility module.

        Static Method Guidelines:
        - 0-25% static methods: Good factory (instance-based patterns)
        - 26-50% static methods: Mixed factory (acceptable)
        - 51-75% static methods: Utility-heavy factory (review needed)
        - 76-100% static methods: Pseudo-utility module (convert to utility)
        """
        factory_analysis = self.analyze_factory_complexity()

        # Analyze static method ratios
        static_ratio_violations = []
        ratio_distribution = {
            "instance_heavy": [],  # 0-25% static
            "balanced": [],        # 26-50% static
            "static_heavy": [],    # 51-75% static
            "utility_like": []     # 76-100% static
        }

        for factory in factory_analysis:
            static_ratio = factory["static_ratio"]

            # Categorize by static ratio
            if static_ratio <= 0.25:
                ratio_distribution["instance_heavy"].append(factory)
            elif static_ratio <= 0.50:
                ratio_distribution["balanced"].append(factory)
            elif static_ratio <= 0.75:
                ratio_distribution["static_heavy"].append(factory)
            else:
                ratio_distribution["utility_like"].append(factory)
                static_ratio_violations.append(factory)

        # Generate report
        report = f"""
FACTORY STATIC METHOD RATIO ANALYSIS
====================================

Total Factories Analyzed: {len(factory_analysis)}

Static Method Ratio Distribution:
- Instance-Heavy (0-25% static): {len(ratio_distribution["instance_heavy"])} factories ✓
- Balanced (26-50% static): {len(ratio_distribution["balanced"])} factories ✓
- Static-Heavy (51-75% static): {len(ratio_distribution["static_heavy"])} factories ⚠️
- Utility-Like (76-100% static): {len(ratio_distribution["utility_like"])} factories ✗

"""

        if static_ratio_violations:
            report += f"UTILITY-LIKE FACTORIES (76-100% static methods):\n"
            report += f"These should be converted to utility modules, not factories.\n\n"

            for factory in sorted(static_ratio_violations, key=lambda x: x["static_ratio"], reverse=True):
                static_pct = factory["static_ratio"] * 100
                report += f"- {factory['name']}\n"
                report += f"  File: {factory['file']}\n"
                report += f"  Static Methods: {factory['static_method_count']}/{factory['method_count']} ({static_pct:.0f}%)\n"
                report += f"  Lines: {factory['total_lines']}\n"

                # Show method details
                static_methods = [m["name"] for m in factory["methods"] if m["is_static"]]
                instance_methods = [m["name"] for m in factory["methods"] if not m["is_static"]]

                if static_methods:
                    report += f"  Static Methods: {', '.join(static_methods)}\n"
                if instance_methods:
                    report += f"  Instance Methods: {', '.join(instance_methods)}\n"

                report += f"  Recommendation: Convert to utility module\n\n"

        # Show problematic static-heavy factories
        static_heavy = ratio_distribution["static_heavy"]
        if static_heavy:
            report += f"STATIC-HEAVY FACTORIES (51-75% static methods):\n"
            report += f"Review these for potential utility module conversion.\n\n"

            for factory in sorted(static_heavy, key=lambda x: x["static_ratio"], reverse=True):
                static_pct = factory["static_ratio"] * 100
                report += f"- {factory['name']}: {static_pct:.0f}% static ({factory['static_method_count']}/{factory['method_count']} methods)\n"

        # Show statistics
        if factory_analysis:
            static_ratios = [f["static_ratio"] for f in factory_analysis]
            avg_static_ratio = sum(static_ratios) / len(static_ratios) * 100

            report += f"\n\nSTATIC METHOD RATIO STATISTICS:\n"
            report += f"- Average: {avg_static_ratio:.1f}% static methods\n"
            report += f"- Recommended: <50% for true factory patterns\n"

        # Top factories by static ratio
        top_static_factories = sorted(factory_analysis, key=lambda x: x["static_ratio"], reverse=True)[:10]
        report += f"\n\nTOP 10 FACTORIES BY STATIC METHOD RATIO:\n"
        for i, factory in enumerate(top_static_factories, 1):
            static_pct = factory["static_ratio"] * 100
            status = "✗ UTILITY-LIKE" if factory["static_ratio"] > 0.75 else "✓ FACTORY-LIKE"
            report += f"{i:2d}. {factory['name']}: {static_pct:.0f}% static {status}\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        if static_ratio_violations:
            self.fail(f"Factory static method ratio violations detected: {len(static_ratio_violations)} "
                     f"factories have >75% static methods and should be converted to utility modules. "
                     f"These pseudo-factories add no architectural value.")
        else:
            self.fail("No static method ratio violations detected - this may indicate measurement issues.")


if __name__ == "__main__":
    import unittest
    unittest.main()