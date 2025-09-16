"""
Test WebSocket SSOT Consolidation - Developer Complexity Metrics

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: Reduce developer cognitive load and improve maintainability
- Value Impact: Simpler WebSocket code = faster development = more business features
- Strategic Impact: Developer productivity directly impacts time-to-market

PURPOSE: Measure the ACTUAL issue (developer complexity) not compliance scores
This test validates that SSOT consolidation reduces developer cognitive burden.
"""

import pytest
import ast
import unittest
from pathlib import Path
from typing import Dict, List, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketComplexityMetrics(SSotBaseTestCase, unittest.TestCase):
    """Test current WebSocket complexity to validate consolidation benefits."""

    def setUp(self):
        """Set up complexity measurement infrastructure."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.websocket_unified_manager = (
            self.project_root / "netra_backend" / "app" / "websocket_core" / "unified_manager.py"
        )

    @pytest.mark.unit
    def test_unified_manager_file_size_complexity(self):
        """Test that unified_manager.py has measurable size complexity."""
        # Business requirement: File should be under 2000 lines for maintainability
        # Current state: Nearly 4000 lines (too complex for developers)

        with open(self.websocket_unified_manager, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        line_count = len(lines)
        non_empty_lines = len([line for line in lines if line.strip()])

        # Measure current state (will be high)
        self.assertGreater(line_count, 3000,
            "File should be large to demonstrate complexity issue")
        self.assertGreater(non_empty_lines, 2500,
            "Non-empty lines should demonstrate density complexity")

        # Business goal: Post-consolidation should be <2000 lines
        complexity_factor = line_count / 2000  # Target size

        # Document the complexity metrics for business case
        print(f"\n=== WebSocket Unified Manager Complexity Metrics ===")
        print(f"Total lines: {line_count}")
        print(f"Non-empty lines: {non_empty_lines}")
        print(f"Complexity factor: {complexity_factor:.2f}x target size")
        print(f"Business impact: {complexity_factor:.1f}x longer for developers to understand")

        # This demonstrates the problem we're solving
        self.assertGreater(complexity_factor, 1.5,
            "Complexity factor should demonstrate need for consolidation")

    @pytest.mark.unit
    def test_unified_manager_class_complexity(self):
        """Test class and method complexity in unified manager."""
        with open(self.websocket_unified_manager, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST to measure structural complexity
        tree = ast.parse(content)

        class_count = 0
        method_count = 0
        function_count = 0
        max_method_lines = 0
        method_line_counts = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, ast.FunctionDef):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    method_lines = node.end_lineno - node.lineno
                    method_line_counts.append(method_lines)
                    max_method_lines = max(max_method_lines, method_lines)

                # Count methods vs functions based on context
                parent_classes = [n for n in ast.walk(tree)
                                if isinstance(n, ast.ClassDef)]
                if any(node.lineno > cls.lineno and
                      node.lineno < cls.end_lineno
                      for cls in parent_classes if hasattr(cls, 'end_lineno')):
                    method_count += 1
                else:
                    function_count += 1

        # Calculate complexity metrics
        avg_method_lines = sum(method_line_counts) / len(method_line_counts) if method_line_counts else 0

        print(f"\n=== Structural Complexity Metrics ===")
        print(f"Classes: {class_count}")
        print(f"Methods: {method_count}")
        print(f"Functions: {function_count}")
        print(f"Max method lines: {max_method_lines}")
        print(f"Average method lines: {avg_method_lines:.1f}")

        # Business thresholds for developer comprehension
        # Research shows >25 lines per method hurts comprehension
        self.assertGreater(max_method_lines, 50,
            "Should have some large methods demonstrating complexity")
        self.assertGreater(avg_method_lines, 20,
            "Average method size should show complexity issue")

        # Too many responsibilities in one file
        total_entities = class_count + method_count + function_count
        self.assertGreater(total_entities, 30,
            "High entity count demonstrates consolidation opportunity")

    @pytest.mark.unit
    def test_import_complexity_measurement(self):
        """Test import complexity in WebSocket unified manager."""
        with open(self.websocket_unified_manager, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Count different types of imports
        import_lines = []
        from_imports = []
        local_imports = []
        external_imports = []

        for line in lines[:100]:  # Check first 100 lines for imports
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append(line)

                if line.startswith('from '):
                    from_imports.append(line)
                    # Categorize imports
                    if any(pkg in line for pkg in ['netra_backend', 'auth_service', 'shared']):
                        local_imports.append(line)
                    else:
                        external_imports.append(line)

        import_count = len(import_lines)
        from_import_count = len(from_imports)
        local_import_count = len(local_imports)
        external_import_count = len(external_imports)

        print(f"\n=== Import Complexity Metrics ===")
        print(f"Total imports: {import_count}")
        print(f"From imports: {from_import_count}")
        print(f"Local imports: {local_import_count}")
        print(f"External imports: {external_import_count}")

        # High import count indicates tight coupling
        self.assertGreater(import_count, 20,
            "High import count demonstrates coupling complexity")

        # Many local imports suggest consolidation opportunity
        self.assertGreater(local_import_count, 10,
            "Many local imports suggest SSOT consolidation benefit")

    @pytest.mark.unit
    def test_developer_cognitive_load_metrics(self):
        """Test metrics that directly impact developer cognitive load."""
        with open(self.websocket_unified_manager, 'r', encoding='utf-8') as f:
            content = f.read()

        # Metrics that research shows impact developer comprehension

        # 1. Nesting depth complexity
        max_nesting = 0
        current_nesting = 0
        for line in content.split('\n'):
            stripped = line.lstrip()
            if stripped:
                # Calculate indentation depth
                indent_level = (len(line) - len(stripped)) // 4
                max_nesting = max(max_nesting, indent_level)

        # 2. Pattern repetition (copy-paste indicators)
        lines = content.split('\n')
        similar_lines = {}
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 20:  # Only check substantial lines
                similar_lines[stripped] = similar_lines.get(stripped, 0) + 1

        repeated_patterns = sum(1 for count in similar_lines.values() if count > 1)

        # 3. Conditional complexity (if/elif/try chains)
        conditional_keywords = ['if ', 'elif ', 'try:', 'except', 'while ', 'for ']
        conditional_count = sum(content.count(keyword) for keyword in conditional_keywords)

        print(f"\n=== Developer Cognitive Load Metrics ===")
        print(f"Max nesting depth: {max_nesting}")
        print(f"Repeated patterns: {repeated_patterns}")
        print(f"Conditional complexity: {conditional_count}")

        # Research-based thresholds for cognitive load
        self.assertGreater(max_nesting, 6,
            "Deep nesting demonstrates cognitive load issue")
        self.assertGreater(repeated_patterns, 15,
            "Pattern repetition suggests DRY violations")
        self.assertGreater(conditional_count, 50,
            "High conditional complexity impacts comprehension")

    @pytest.mark.unit
    def test_consolidation_opportunity_metrics(self):
        """Test metrics that indicate SSOT consolidation opportunities."""

        # Identify potential duplicate patterns across WebSocket files
        websocket_files = [
            self.project_root / "netra_backend" / "app" / "websocket_core" / "unified_manager.py",
            self.project_root / "netra_backend" / "app" / "websocket_core" / "manager.py",
            self.project_root / "netra_backend" / "app" / "routes" / "websocket.py",
        ]

        existing_files = [f for f in websocket_files if f.exists()]
        self.assertGreater(len(existing_files), 1,
            "Should have multiple WebSocket files to demonstrate fragmentation")

        # Look for common patterns that suggest consolidation opportunities
        common_patterns = [
            "websocket",
            "connection_manager",
            "send_message",
            "receive_message",
            "event_handler",
            "user_context",
            "session_manager"
        ]

        pattern_occurrences = {}
        total_lines_across_files = 0

        for file_path in existing_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    lines = content.split('\n')
                    total_lines_across_files += len(lines)

                    for pattern in common_patterns:
                        count = content.count(pattern)
                        if count > 0:
                            pattern_occurrences.setdefault(pattern, []).append((file_path.name, count))
            except Exception as e:
                print(f"Could not read {file_path}: {e}")

        # Calculate consolidation metrics
        fragmented_patterns = {pattern: files for pattern, files
                             in pattern_occurrences.items() if len(files) > 1}

        print(f"\n=== SSOT Consolidation Opportunity Metrics ===")
        print(f"Total WebSocket files: {len(existing_files)}")
        print(f"Total lines across files: {total_lines_across_files}")
        print(f"Fragmented patterns: {len(fragmented_patterns)}")

        for pattern, files in fragmented_patterns.items():
            print(f"  {pattern}: {len(files)} files")

        # Business case metrics
        fragmentation_factor = len(fragmented_patterns) / len(common_patterns)
        consolidation_potential = total_lines_across_files / 2000  # Target size

        print(f"Fragmentation factor: {fragmentation_factor:.2f}")
        print(f"Consolidation potential: {consolidation_potential:.1f}x")

        # These metrics validate the consolidation opportunity
        self.assertGreater(len(fragmented_patterns), 3,
            "Should have fragmented patterns justifying consolidation")
        self.assertGreater(fragmentation_factor, 0.4,
            "Fragmentation factor should justify SSOT consolidation")