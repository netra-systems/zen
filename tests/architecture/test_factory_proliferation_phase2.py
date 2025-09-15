"""
Factory Proliferation Detection - Phase 2 Cleanup
Tests designed to FAIL and demonstrate factory over-engineering scope.

Business Impact: $500K+ ARR protection through architectural simplification
Created: 2025-09-15
Purpose: Identify unnecessary factory abstractions for cleanup
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestFactoryProliferationPhase2(SSotBaseTestCase):
    """Tests to detect and validate removal of over-engineered factory patterns."""

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

    def find_factory_classes(self):
        """Scan codebase for factory classes and categorize them."""
        factory_classes = []
        factory_usage = defaultdict(int)

        for source_dir in self.source_dirs:
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
                                    "file": str(py_file.relative_to(self.project_root)),
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

    def categorize_factories_by_domain(self, factory_classes):
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

    def test_01_factory_count_exceeds_business_justification_threshold(self):
        """
        EXPECTED: FAIL - Demonstrates factory count exceeds reasonable thresholds

        Scans entire codebase for factory classes and validates against
        business justification thresholds based on domain complexity.

        Business Justification:
        - User isolation: 5 factories max (multi-user security)
        - WebSocket: 3 factories max (real-time communication)
        - Database: 4 factories max (connection management)
        - Auth: 3 factories max (security tokens)
        - Tools: 2 factories max (tool dispatch)
        - Execution: 3 factories max (agent execution)
        - Total: 20 factories maximum for entire system
        """
        factory_classes, factory_usage = self.find_factory_classes()
        categories = self.categorize_factories_by_domain(factory_classes)

        total_factories = len(factory_classes)

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

        violations = []

        # Check category violations
        for category, threshold in thresholds.items():
            if category == "testing":
                continue  # Skip testing factories in this check

            count = len(categories[category])
            if count > threshold:
                violations.append(f"{category}: {count} factories (threshold: {threshold})")

        # Check total factory count (excluding testing)
        non_test_factories = total_factories - len(categories["testing"])
        max_total_factories = 20

        if non_test_factories > max_total_factories:
            violations.append(f"Total: {non_test_factories} factories (threshold: {max_total_factories})")

        # Create detailed report
        report = f"""
FACTORY PROLIFERATION ANALYSIS
==============================

Total Factories Found: {total_factories}
Non-Test Factories: {non_test_factories}
Business Threshold: {max_total_factories}

Category Breakdown:
"""
        for category, factories in categories.items():
            threshold = thresholds.get(category, 0)
            status = "✓ PASS" if len(factories) <= threshold or category == "testing" else "✗ FAIL"
            report += f"- {category.title()}: {len(factories)} factories (threshold: {threshold}) {status}\n"

        if violations:
            report += f"\nVIOLATIONS DETECTED:\n"
            for violation in violations:
                report += f"- {violation}\n"

            report += f"\nFACTORY DETAILS:\n"
            for category, factories in categories.items():
                if category != "testing" and factories:
                    report += f"\n{category.upper()} FACTORIES:\n"
                    for factory in factories:
                        report += f"  - {factory['name']} ({factory['file']})\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        self.fail(f"Factory proliferation detected: {len(violations)} violations found. "
                 f"System has {non_test_factories} factories vs {max_total_factories} threshold. "
                 f"Over-engineering cleanup required.")

    def test_02_single_use_factory_over_engineering_detection(self):
        """
        EXPECTED: FAIL - Shows factories used only once or twice

        Identifies factory classes that are only instantiated in 1-2 places,
        indicating direct instantiation would be simpler.
        """
        factory_classes, factory_usage = self.find_factory_classes()

        # Scan for actual instantiation patterns
        single_use_factories = []
        usage_patterns = {}

        for factory in factory_classes:
            factory_name = factory["name"]

            # Skip testing factories
            if "test" in factory["file"].lower() or "mock" in factory_name.lower():
                continue

            instantiation_count = 0
            usage_files = []

            # Scan all source files for usage patterns
            for source_dir in self.source_dirs:
                if not source_dir.exists():
                    continue

                for py_file in source_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for instantiation patterns
                        patterns = [
                            f"{factory_name}()",
                            f"{factory_name}.create",
                            f"= {factory_name}",
                            f"import.*{factory_name}",
                            f"from.*{factory_name}"
                        ]

                        file_usage = 0
                        for pattern in patterns:
                            matches = len(re.findall(pattern, content, re.IGNORECASE))
                            file_usage += matches

                        if file_usage > 0:
                            instantiation_count += file_usage
                            usage_files.append(str(py_file.relative_to(self.project_root)))

                    except Exception:
                        continue

            usage_patterns[factory_name] = {
                "count": instantiation_count,
                "files": usage_files,
                "factory_info": factory
            }

            # Flag as single-use if used in 2 or fewer places
            if instantiation_count <= 2 and instantiation_count > 0:
                single_use_factories.append({
                    "name": factory_name,
                    "usage_count": instantiation_count,
                    "files": usage_files,
                    "factory_info": factory
                })

        # Generate report
        report = f"""
SINGLE-USE FACTORY ANALYSIS
===========================

Single-Use Factories Found: {len(single_use_factories)}
(Factories used in ≤2 places - candidates for direct instantiation)

"""

        if single_use_factories:
            report += "OVER-ENGINEERED SINGLE-USE FACTORIES:\n"
            for factory in single_use_factories:
                report += f"\n- {factory['name']}\n"
                report += f"  Usage Count: {factory['usage_count']}\n"
                report += f"  File: {factory['factory_info']['file']}\n"
                report += f"  Used In: {factory['files']}\n"
                report += f"  Recommendation: Replace with direct instantiation\n"

        # Show usage summary for all factories
        report += f"\n\nFULL USAGE ANALYSIS:\n"
        sorted_usage = sorted(usage_patterns.items(), key=lambda x: x[1]["count"])

        for factory_name, usage_info in sorted_usage:
            if "test" not in usage_info["factory_info"]["file"].lower():
                report += f"- {factory_name}: {usage_info['count']} uses in {len(usage_info['files'])} files\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        if single_use_factories:
            self.fail(f"Single-use factory over-engineering detected: {len(single_use_factories)} factories "
                     f"used in ≤2 places. These should be replaced with direct instantiation.")
        else:
            self.fail("No single-use factories detected - this may indicate measurement issues.")

    def test_03_factory_chain_depth_violation_detection(self):
        """
        EXPECTED: FAIL - Demonstrates excessive factory abstraction layers

        Detects factory chains like:
        ExecutionEngineFactory → AgentInstanceFactory → UserWebSocketEmitter
        """
        factory_classes, _ = self.find_factory_classes()

        # Analyze factory dependencies and chains
        factory_dependencies = {}

        for factory in factory_classes:
            if "test" in factory["file"].lower():
                continue

            try:
                file_path = self.project_root / factory["file"]
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find other factories referenced in this factory
                dependencies = []
                for other_factory in factory_classes:
                    if (other_factory["name"] != factory["name"] and
                        other_factory["name"] in content):
                        dependencies.append(other_factory["name"])

                factory_dependencies[factory["name"]] = {
                    "dependencies": dependencies,
                    "file": factory["file"],
                    "methods": factory["methods"]
                }

            except Exception:
                continue

        # Find chains by traversing dependencies
        factory_chains = []

        def find_chains(factory_name, current_chain, visited):
            if factory_name in visited:
                return  # Avoid cycles

            visited.add(factory_name)
            current_chain.append(factory_name)

            if factory_name in factory_dependencies:
                dependencies = factory_dependencies[factory_name]["dependencies"]

                if dependencies:
                    for dep in dependencies:
                        find_chains(dep, current_chain.copy(), visited.copy())
                else:
                    # End of chain
                    if len(current_chain) > 2:  # Chains > 2 levels are violations
                        factory_chains.append(current_chain.copy())
            else:
                # End of chain
                if len(current_chain) > 2:
                    factory_chains.append(current_chain.copy())

        # Start chain analysis from each factory
        for factory_name in factory_dependencies:
            find_chains(factory_name, [], set())

        # Remove duplicate chains and sort by length
        unique_chains = []
        for chain in factory_chains:
            chain_str = " → ".join(chain)
            if chain_str not in [" → ".join(c) for c in unique_chains]:
                unique_chains.append(chain)

        unique_chains.sort(key=len, reverse=True)

        # Generate report
        report = f"""
FACTORY CHAIN DEPTH ANALYSIS
============================

Factory Chains Found: {len(unique_chains)}
Threshold: 2 levels maximum (Business justification required for >2 levels)

"""

        violations = [chain for chain in unique_chains if len(chain) > 2]

        if violations:
            report += f"EXCESSIVE FACTORY CHAINS ({len(violations)} violations):\n"
            for i, chain in enumerate(violations, 1):
                report += f"\n{i}. Chain Length: {len(chain)} levels\n"
                report += f"   Path: {' → '.join(chain)}\n"

                # Show file locations
                for factory_name in chain:
                    if factory_name in factory_dependencies:
                        file_info = factory_dependencies[factory_name]["file"]
                        report += f"   - {factory_name}: {file_info}\n"

                report += f"   Recommendation: Reduce chain depth to ≤2 levels\n"

        # Show factory dependency summary
        report += f"\n\nFACTORY DEPENDENCY SUMMARY:\n"
        for factory_name, info in factory_dependencies.items():
            if info["dependencies"]:
                report += f"- {factory_name} depends on: {', '.join(info['dependencies'])}\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        if violations:
            self.fail(f"Factory chain depth violations detected: {len(violations)} chains exceed "
                     f"2-level threshold. Maximum chain length: {max(len(chain) for chain in violations)} levels.")
        else:
            self.fail("No factory chain violations detected - this may indicate measurement issues or "
                     "good architecture (unexpected for this test).")

    def test_04_database_factory_over_abstraction_detection(self):
        """
        EXPECTED: FAIL - Shows database factory proliferation

        Identifies multiple factory layers for simple database operations
        that could use standard connection patterns.
        """
        factory_classes, _ = self.find_factory_classes()

        # Find database-related factories
        db_factories = []
        db_patterns = [
            "database", "db", "session", "connection", "postgres", "clickhouse",
            "redis", "sql", "orm", "repository", "dao"
        ]

        for factory in factory_classes:
            factory_name_lower = factory["name"].lower()
            factory_file_lower = factory["file"].lower()

            # Skip test factories
            if "test" in factory_file_lower:
                continue

            # Check if this is a database-related factory
            is_db_factory = any(pattern in factory_name_lower or pattern in factory_file_lower
                              for pattern in db_patterns)

            if is_db_factory:
                db_factories.append(factory)

        # Analyze database factory complexity
        complex_db_factories = []
        simple_db_operations = []

        for factory in db_factories:
            try:
                file_path = self.project_root / factory["file"]
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Analyze complexity indicators
                method_count = len(factory["methods"])
                line_count = factory["line_count"]

                # Look for simple operations that don't need factories
                simple_patterns = [
                    "def get_connection", "def create_session", "def close",
                    "return Session(", "return connection", "session.commit()"
                ]

                simple_operations_found = sum(1 for pattern in simple_patterns
                                            if pattern in content)

                complexity_score = method_count + (line_count / 50) + simple_operations_found

                factory_analysis = {
                    "factory": factory,
                    "method_count": method_count,
                    "line_count": line_count,
                    "simple_operations": simple_operations_found,
                    "complexity_score": complexity_score
                }

                # Flag as over-engineered if it's doing simple operations
                if simple_operations_found > 2 or (method_count > 1 and line_count < 100):
                    complex_db_factories.append(factory_analysis)

                if simple_operations_found > 0:
                    simple_db_operations.append(factory_analysis)

            except Exception:
                continue

        # Generate report
        report = f"""
DATABASE FACTORY OVER-ABSTRACTION ANALYSIS
==========================================

Total Database Factories: {len(db_factories)}
Business Threshold: 4 factories maximum
Over-Engineered Database Factories: {len(complex_db_factories)}

"""

        if len(db_factories) > 4:
            report += f"✗ VIOLATION: {len(db_factories)} database factories exceed threshold of 4\n\n"

        if db_factories:
            report += "DATABASE FACTORIES FOUND:\n"
            for factory in db_factories:
                report += f"- {factory['name']} ({factory['file']})\n"
                report += f"  Methods: {len(factory['methods'])}\n"
                report += f"  Lines: {factory['line_count']}\n\n"

        if complex_db_factories:
            report += "OVER-ENGINEERED DATABASE FACTORIES:\n"
            for analysis in complex_db_factories:
                factory = analysis["factory"]
                report += f"\n- {factory['name']}\n"
                report += f"  File: {factory['file']}\n"
                report += f"  Methods: {analysis['method_count']}\n"
                report += f"  Lines: {analysis['line_count']}\n"
                report += f"  Simple Operations: {analysis['simple_operations']}\n"
                report += f"  Complexity Score: {analysis['complexity_score']:.1f}\n"
                report += f"  Recommendation: Replace with direct database connection pattern\n"

        if simple_db_operations:
            report += f"\nSIMPLE DATABASE OPERATIONS IN FACTORIES:\n"
            report += f"(These could use standard connection patterns instead)\n"
            for analysis in simple_db_operations:
                factory = analysis["factory"]
                report += f"- {factory['name']}: {analysis['simple_operations']} simple operations\n"

        print(report)

        # This test should FAIL to demonstrate over-engineering
        violations = []

        if len(db_factories) > 4:
            violations.append(f"Too many database factories: {len(db_factories)} > 4")

        if complex_db_factories:
            violations.append(f"Over-engineered database factories: {len(complex_db_factories)}")

        if violations:
            self.fail(f"Database factory over-abstraction detected: {', '.join(violations)}. "
                     f"Simplification required for better performance and maintainability.")
        else:
            self.fail("No database factory violations detected - this may indicate measurement issues.")


if __name__ == "__main__":
    import unittest
    unittest.main()