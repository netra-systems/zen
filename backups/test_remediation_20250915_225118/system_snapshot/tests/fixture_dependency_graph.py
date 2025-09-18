'''
Fixture Dependency Graph Analysis Tool

This module analyzes pytest fixture dependencies to identify:
- Circular dependencies that can cause memory issues
- Heavy fixture chains that should be optimized
- Memory impact patterns across the test suite
- Fixture usage patterns and optimization opportunities

Usage:
python -m tests.fixture_dependency_graph
pytest --collect-only -q | python -m tests.fixture_dependency_graph --from-pytest
'''
import ast
import os
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json

class FixtureNode:
    """Represents a pytest fixture in the dependency graph."""

    def __init__(self, name: str, file_path: str, line_number: int = 0):
        self.name = name
        self.file_path = file_path
        self.line_number = line_number
        self.dependencies: List[str] = []  # Fixtures this depends on
        self.dependents: List[str] = []    # Fixtures that depend on this
        self.scope: str = "function"       # function, class, module, session
        self.memory_impact: str = "UNKNOWN"  # LOW, MEDIUM, HIGH, VERY_HIGH
        self.memory_description: str = ""
        self.is_autouse: bool = False
        self.is_async: bool = False

    def __repr__(self):
        return "formatted_string"

class FixtureDependencyGraph:
        """Analyzes fixture dependencies across pytest conftest files."""

    def __init__(self, test_root: str = "tests"):
        self.test_root = Path(test_root)
        self.nodes: Dict[str, FixtureNode] = {}
        self.circular_dependencies: List[List[str]] = []
        self.heavy_chains: List[Tuple[List[str], str]] = []  # (chain, total_impact)

    def analyze_conftest_files(self) -> None:
        """Analyze all conftest.py files to build the dependency graph."""
        conftest_files = []

    # Find all conftest files
        for root, dirs, files in os.walk(self.test_root):
        for file in files:
        if file.startswith("conftest") and file.endswith(".py"):
        conftest_files.append(Path(root) / file)

                # Parse each conftest file
        for conftest_file in conftest_files:
        try:
        self._parse_conftest_file(conftest_file)
        except Exception as e:
        print("formatted_string")

                            # Build dependency relationships
        self._build_dependency_relationships()

                            # Detect issues
        self._detect_circular_dependencies()
        self._detect_heavy_chains()

    def _parse_conftest_file(self, file_path: Path) -> None:
        """Parse a conftest file to extract fixture definitions."""
        with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

        # Parse AST to find fixture definitions
        try:
        tree = ast.parse(content)
        except SyntaxError as e:
        print("formatted_string")
        return

        for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
                        # Check if this is a fixture
        fixture_info = self._extract_fixture_info(node, content, str(file_path))
        if fixture_info:
        fixture_node = FixtureNode( )
        name=fixture_info['name'],
        file_path=str(file_path),
        line_number=node.lineno
                            
        fixture_node.scope = fixture_info['scope']
        fixture_node.is_autouse = fixture_info['autouse']
        fixture_node.is_async = fixture_info['is_async']
        fixture_node.dependencies = fixture_info['dependencies']
        fixture_node.memory_impact = fixture_info['memory_impact']
        fixture_node.memory_description = fixture_info['memory_description']

        self.nodes[fixture_info['name']] = fixture_node

    def _extract_fixture_info(self, node: ast.FunctionDef, content: str, file_path: str) -> Optional[Dict]:
        """Extract fixture information from a function definition."""
    # Check for @pytest.fixture decorator
        fixture_decorator = None
        for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == 'fixture':
        fixture_decorator = decorator
        break
        elif isinstance(decorator, ast.Attribute):
        if (isinstance(decorator.value, ast.Name) and )
        decorator.value.id == 'pytest' and
        decorator.attr == 'fixture'):
        fixture_decorator = decorator
        break
        elif isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name) and decorator.func.id == 'fixture':
        fixture_decorator = decorator
        break
        elif (isinstance(decorator.func, ast.Attribute) and )
        isinstance(decorator.func.value, ast.Name) and
        decorator.func.value.id == 'pytest' and
        decorator.func.attr == 'fixture'):
        fixture_decorator = decorator
        break

        if not fixture_decorator:
        return None

                                    # Extract fixture parameters
        scope = "function"
        autouse = False

        if isinstance(fixture_decorator, ast.Call):
        for keyword in fixture_decorator.keywords:
        if keyword.arg == 'scope' and isinstance(keyword.value, ast.Constant):
        scope = keyword.value.value
        elif keyword.arg == 'autouse' and isinstance(keyword.value, ast.Constant):
        autouse = keyword.value.value

                                                    # Extract function parameters (dependencies)
        dependencies = []
        for arg in node.args.args:
        if arg.arg != 'self':  # Skip 'self' parameter
        dependencies.append(arg.arg)

                                                        # Check if async
        is_async = isinstance(node, ast.AsyncFunctionDef)

                                                        # Extract memory profiling info
        memory_impact = "UNKNOWN"
        memory_description = ""

                                                        # Look for memory_profile decorator
        for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
        if (isinstance(decorator.func, ast.Name) and )
        decorator.func.id == 'memory_profile'):
                                                                    # Extract memory profile arguments
        for keyword in decorator.keywords:
        if keyword.arg == 'impact' and isinstance(keyword.value, ast.Constant):
        memory_impact = keyword.value.value
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
        memory_description = decorator.args[0].value

                                                                                Try to infer memory impact from function content/docstring
        if memory_impact == "UNKNOWN":
        memory_impact = self._infer_memory_impact(node, content)

        return { )
        'name': node.name,
        'scope': scope,
        'autouse': autouse,
        'is_async': is_async,
        'dependencies': dependencies,
        'memory_impact': memory_impact,
        'memory_description': memory_description
                                                                                    

    def _infer_memory_impact(self, node: ast.FunctionDef, content: str) -> str:
        """Infer memory impact from fixture code."""
        lines = content.split(" )
        ")
        func_start = node.lineno - 1
        func_end = node.end_lineno if hasattr(node, 'end_lineno') else func_start + 20

        func_content = "
        ".join(lines[func_start:func_end]).lower()

    # High impact indicators
        high_impact_indicators = [ )
        'database', 'postgres', 'mysql', 'mongodb',
        'redis', 'clickhouse',
        'websocket', 'httpx', 'requests',
        'service_orchestrator', 'docker',
        'real_services', 'e2e', 'integration'
    

    # Very high impact indicators
        very_high_indicators = [ )
        'orchestrate', 'full_environment', 'all_services',
        'high_volume', 'performance_test', 'load_test'
    

    # Medium impact indicators
        medium_indicators = [ )
        'session', 'manager', 'service', 'client',
        'memory_optimization', 'async'
    

        for indicator in very_high_indicators:
        if indicator in func_content:
        return "VERY_HIGH"

        for indicator in high_impact_indicators:
        if indicator in func_content:
        return "HIGH"

        for indicator in medium_indicators:
        if indicator in func_content:
        return "MEDIUM"

                            # Check for mock indicators (usually low impact)
        if 'mock' in func_content or 'magicmock' in func_content:
        return "LOW"

        return "LOW"  # Default to LOW if no indicators found

    def _build_dependency_relationships(self) -> None:
        """Build bidirectional dependency relationships."""
        for fixture_name, fixture_node in self.nodes.items():
        for dep_name in fixture_node.dependencies:
        if dep_name in self.nodes:
                # Add dependency relationship
        self.nodes[dep_name].dependents.append(fixture_name)

    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        path = []

    def dfs(node_name: str) -> bool:
        if node_name in rec_stack:
        # Found a cycle
        cycle_start = path.index(node_name)
        cycle = path[cycle_start:] + [node_name]
        self.circular_dependencies.append(cycle)
        return True

        if node_name in visited:
        return False

        visited.add(node_name)
        rec_stack.add(node_name)
        path.append(node_name)

        if node_name in self.nodes:
        for dep in self.nodes[node_name].dependencies:
        if dep in self.nodes:
        if dfs(dep):
        return True

        rec_stack.remove(node_name)
        path.pop()
        return False

        for fixture_name in self.nodes:
        if fixture_name not in visited:
        dfs(fixture_name)

    def _detect_heavy_chains(self) -> None:
        """Detect chains of fixtures with high memory impact."""
    def get_chain_impact_score(chain: List[str]) -> Tuple[int, str]:
        impact_scores = {"LOW": 1, "MEDIUM": 3, "HIGH": 5, "VERY_HIGH": 10, "UNKNOWN": 2}
        total_score = 0
        impact_details = []

        for fixture_name in chain:
        if fixture_name in self.nodes:
        impact = self.nodes[fixture_name].memory_impact
        total_score += impact_scores.get(impact, 2)
        impact_details.append("formatted_string")

            # Determine overall impact level
        if total_score >= 20:
        impact_level = "CRITICAL"
        elif total_score >= 10:
        impact_level = "HIGH"
        elif total_score >= 5:
        impact_level = "MEDIUM"
        else:
        impact_level = "LOW"

        return total_score, "formatted_string"

    def find_chains(start_fixture: str, visited: Set[str], current_chain: List[str]) -> None:
        if start_fixture in visited:
        return

        visited.add(start_fixture)
        current_chain.append(start_fixture)

        # If chain has more than 2 fixtures, check its impact
        if len(current_chain) >= 3:
        score, description = get_chain_impact_score(current_chain)
        if score >= 5:  # Only report chains with medium+ impact
        self.heavy_chains.append((current_chain.copy(), description))

            # Continue the chain with dependencies
        if start_fixture in self.nodes:
        for dep in self.nodes[start_fixture].dependencies:
        if dep in self.nodes:
        find_chains(dep, visited.copy(), current_chain.copy())

                        Find all chains starting from each fixture
        for fixture_name in self.nodes:
        find_chains(fixture_name, set(), [])

                            # Remove duplicate chains and sort by impact
        unique_chains = []
        seen = set()
        for chain, description in self.heavy_chains:
        chain_key = tuple(sorted(chain))
        if chain_key not in seen:
        seen.add(chain_key)
        unique_chains.append((chain, description))

        self.heavy_chains = sorted(unique_chains, key=lambda x: None x[1], reverse=True)[:10]  # Top 10

    def generate_report(self) -> str:
        """Generate a comprehensive fixture dependency report."""
        report = []
        report.append("# Fixture Dependency Analysis Report")
        report.append("formatted_string")
        report.append("formatted_string")
        report.append("")

    # Memory impact summary
        impact_counts = defaultdict(int)
        for node in self.nodes.values():
        impact_counts[node.memory_impact] += 1

        report.append("## Memory Impact Summary")
        for impact in ["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
        count = impact_counts[impact]
        if count > 0:
        report.append("formatted_string")
        report.append("")

                # Circular dependencies
        report.append("## Circular Dependencies")
        if self.circular_dependencies:
        report.append("WARNING: **CRITICAL: Circular dependencies detected!**")
        for i, cycle in enumerate(self.circular_dependencies):
        report.append("formatted_string")
        else:
        report.append("OK: No circular dependencies detected")
        report.append("")

                            # Heavy fixture chains
        report.append("## Heavy Memory Impact Chains")
        if self.heavy_chains:
        report.append("These fixture chains have high memory usage:")
        for i, (chain, description) in enumerate(self.heavy_chains[:5]):  # Top 5
        report.append("formatted_string")
        else:
        report.append("OK: No heavy fixture chains detected")
        report.append("")

                                    # High impact fixtures
        report.append("## High Impact Fixtures")
        high_impact_fixtures = [ )
        node for node in self.nodes.values()
        if node.memory_impact in ["HIGH", "VERY_HIGH"]
                                    
        high_impact_fixtures.sort(key=lambda x: None (x.memory_impact == "VERY_HIGH", x.memory_impact), reverse=True)

        for fixture in high_impact_fixtures[:10]:  # Top 10
        report.append("formatted_string")
        if fixture.memory_description:
        report.append("formatted_string")
        report.append("formatted_string")
        report.append("formatted_string")
        if fixture.dependencies:
        report.append("formatted_string")
        report.append("")

                                            # Session-scoped fixtures (potential memory retention)
        report.append("## Session-Scoped Fixtures")
        session_fixtures = [item for item in []]
        if session_fixtures:
        report.append("These fixtures persist for the entire test session:")
        for fixture in session_fixtures:
        report.append("formatted_string")
        if fixture.is_autouse:
        report.append("  - WARNING: Auto-use fixture (runs automatically)")
        if fixture.memory_description:
        report.append("formatted_string")
        else:
        report.append("OK: No session-scoped fixtures detected")
        report.append("")

                                                                # Recommendations
        report.append("## Optimization Recommendations")

        if self.circular_dependencies:
        report.append("1. **CRITICAL**: Fix circular dependencies to prevent memory leaks")

        if len([item for item in []]) > 3:
        report.append("2. Consider reducing the number of VERY_HIGH impact fixtures")

        if len(session_fixtures) > 5:
        report.append("3. Review session-scoped fixtures - consider function scope when possible")

        if len([item for item in []]) > 2:
        report.append("4. Review auto-use fixtures - they increase memory usage for all tests")

        heavy_imports = len([item for item in []])
        if heavy_imports > 10:
        report.append("5. Consider implementing lazy loading for heavy imports in E2E fixtures")

        return "
        ".join(report)

    def export_json(self) -> str:
        """Export fixture data as JSON for programmatic analysis."""
        export_data = { )
        'fixtures': {},
        'circular_dependencies': self.circular_dependencies,
        'heavy_chains': [(chain, desc) for chain, desc in self.heavy_chains]
    

        for name, node in self.nodes.items():
        export_data['fixtures'][name] = { )
        'file_path': node.file_path,
        'line_number': node.line_number,
        'scope': node.scope,
        'memory_impact': node.memory_impact,
        'memory_description': node.memory_description,
        'is_autouse': node.is_autouse,
        'is_async': node.is_async,
        'dependencies': node.dependencies,
        'dependents': node.dependents
        

        return json.dumps(export_data, indent=2)

    def main():
        """Main entry point for fixture dependency analysis."""
        import argparse

        parser = argparse.ArgumentParser(description="Analyze pytest fixture dependencies")
        parser.add_argument("--test-root", default="tests", help="Root directory for tests")
        parser.add_argument("--output", help="Output file for report")
        parser.add_argument("--json", action="store_true", help="Output as JSON")

        args = parser.parse_args()

    # Run analysis
        analyzer = FixtureDependencyGraph(args.test_root)
        analyzer.analyze_conftest_files()

    # Generate output
        if args.json:
        output = analyzer.export_json()
        else:
        output = analyzer.generate_report()

            # Write output
        if args.output:
        with open(args.output, 'w') as f:
        f.write(output)
        print("formatted_string")
        else:
        print(output)

        if __name__ == "__main__":
        main()
