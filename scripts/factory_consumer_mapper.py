#!/usr/bin/env python3
"""
Factory Consumer Mapper - Issue #1194 Phase 1

This script maps all consumer usage points of factories throughout the codebase
to understand the scope of factory migration impact. It provides detailed analysis
of where and how factories are used to enable safe migration planning.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Comprehensive impact analysis for factory consolidation
- Value Impact: Map 1,350+ usage points to prevent migration failures
- Strategic Impact: Enable confident factory removal with complete visibility

Key Features:
- Comprehensive usage point detection and mapping
- Consumer categorization and impact analysis
- Dependency graph generation
- Migration impact scoring
- Consumer relationship visualization
- Critical path identification

Part of Issue #1194 Phase 1: Safety Infrastructure & Analysis
"""

import argparse
import ast
import json
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ConsumerUsage:
    """Represents a single consumer usage point of a factory."""
    factory_name: str
    consumer_file: str
    consumer_function: str
    line_number: int
    usage_type: str  # 'import', 'call', 'instantiation', 'inheritance', 'parameter'
    usage_context: str  # The actual code line
    criticality: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    user_isolation_impact: bool = False
    business_function: Optional[str] = None
    migration_complexity: str = "SIMPLE"  # SIMPLE, MODERATE, COMPLEX
    dependency_chain: List[str] = field(default_factory=list)


@dataclass
class ConsumerRelationship:
    """Represents relationship between a factory and its consumers."""
    factory_name: str
    consumer_file: str
    relationship_type: str  # 'direct', 'transitive', 'circular'
    depth: int  # How many levels deep the relationship is
    path: List[str] = field(default_factory=list)  # Path through dependency chain


@dataclass
class FactoryConsumerMap:
    """Complete mapping of factory consumers."""
    factory_name: str
    total_usage_points: int = 0
    direct_consumers: int = 0
    transitive_consumers: int = 0
    critical_usage_points: int = 0
    usage_by_file: Dict[str, List[ConsumerUsage]] = field(default_factory=dict)
    usage_by_function: Dict[str, List[ConsumerUsage]] = field(default_factory=dict)
    usage_by_type: Dict[str, int] = field(default_factory=dict)
    consumer_relationships: List[ConsumerRelationship] = field(default_factory=list)
    migration_impact_score: int = 0
    critical_dependencies: List[str] = field(default_factory=list)


@dataclass
class ConsumerMappingResult:
    """Complete results of factory consumer mapping."""
    total_factories_analyzed: int = 0
    total_usage_points: int = 0
    factory_maps: Dict[str, FactoryConsumerMap] = field(default_factory=dict)
    global_dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    critical_paths: List[List[str]] = field(default_factory=list)
    migration_recommendations: List[str] = field(default_factory=list)


class FactoryConsumerMapper:
    """Maps all consumer usage points of factories in the codebase."""

    # Business function keywords for categorization
    BUSINESS_FUNCTIONS = {
        'authentication': ['auth', 'login', 'token', 'session', 'permission'],
        'agent_execution': ['agent', 'execute', 'run', 'supervisor', 'workflow'],
        'websocket_communication': ['websocket', 'emit', 'notify', 'event', 'message'],
        'database_operations': ['database', 'session', 'query', 'save', 'repository'],
        'llm_integration': ['llm', 'openai', 'anthropic', 'client', 'chat'],
        'file_management': ['upload', 'download', 'file', 'document', 'storage'],
        'configuration': ['config', 'settings', 'environment', 'setup'],
        'testing': ['test', 'mock', 'fixture', 'factory_boy', 'pytest']
    }

    # Criticality indicators
    CRITICAL_INDICATORS = [
        'critical', 'production', 'user_facing', 'security',
        'auth', 'payment', 'data_loss', 'compliance'
    ]

    # User isolation keywords
    USER_ISOLATION_KEYWORDS = [
        'user_id', 'user_context', 'UserExecutionContext',
        'per_user', 'user_specific', 'isolation', 'multi_user'
    ]

    def __init__(self):
        self.result = ConsumerMappingResult()
        self.file_cache = {}
        self.ast_cache = {}
        self.factory_definitions = {}  # Store factory definition locations

    def map_factory_consumers(self, base_path: Path,
                            factory_names: Optional[List[str]] = None,
                            exclude_patterns: Optional[List[str]] = None) -> ConsumerMappingResult:
        """
        Map all consumer usage points for specified factories.

        Args:
            base_path: Root directory to analyze
            factory_names: Specific factories to analyze (if None, auto-detect)
            exclude_patterns: Patterns to exclude from analysis

        Returns:
            ConsumerMappingResult: Complete consumer mapping results
        """
        if exclude_patterns is None:
            exclude_patterns = [
                '__pycache__', '.git', 'node_modules', '.pytest_cache',
                'venv', 'env', '.venv', 'htmlcov', 'backups'
            ]

        logger.info(f"Starting factory consumer mapping for {base_path}")

        # Step 1: Auto-detect factories if not specified
        if factory_names is None:
            factory_names = self._auto_detect_factories(base_path, exclude_patterns)

        logger.info(f"Analyzing {len(factory_names)} factories: {factory_names}")

        # Step 2: Find factory definitions
        self._find_factory_definitions(base_path, factory_names, exclude_patterns)

        # Step 3: Map consumers for each factory
        for factory_name in factory_names:
            logger.info(f"Mapping consumers for {factory_name}")
            factory_map = self._map_single_factory_consumers(
                base_path, factory_name, exclude_patterns
            )
            self.result.factory_maps[factory_name] = factory_map

        # Step 4: Analyze cross-factory dependencies
        self._analyze_dependency_graph()

        # Step 5: Identify critical paths
        self._identify_critical_paths()

        # Step 6: Calculate metrics and recommendations
        self._calculate_metrics()
        self._generate_recommendations()

        logger.info(f"Consumer mapping complete: {self.result.total_usage_points} usage points found")
        return self.result

    def _auto_detect_factories(self, base_path: Path, exclude_patterns: List[str]) -> List[str]:
        """Auto-detect factory names in the codebase."""
        factory_names = set()

        for py_file in base_path.rglob("*.py"):
            if self._should_skip_file(py_file, exclude_patterns):
                continue

            try:
                content = self._get_file_content(str(py_file))

                # Look for factory class definitions
                class_matches = re.findall(r'class\s+(\w*[Ff]actory\w*)', content)
                factory_names.update(class_matches)

                # Look for factory function definitions
                func_matches = re.findall(r'def\s+(create_\w+|get_\w+_factory|.*_factory)\s*\(', content)
                factory_names.update(func_matches)

                # Look for factory variables
                var_matches = re.findall(r'(\w*[Ff]actory\w*)\s*=', content)
                factory_names.update(var_matches)

            except Exception as e:
                logger.debug(f"Error auto-detecting factories in {py_file}: {e}")

        return sorted(list(factory_names))

    def _find_factory_definitions(self, base_path: Path, factory_names: List[str],
                                exclude_patterns: List[str]) -> None:
        """Find definition locations for all factories."""
        for py_file in base_path.rglob("*.py"):
            if self._should_skip_file(py_file, exclude_patterns):
                continue

            try:
                content = self._get_file_content(str(py_file))

                for factory_name in factory_names:
                    # Look for class definitions
                    if f"class {factory_name}" in content:
                        if factory_name not in self.factory_definitions:
                            self.factory_definitions[factory_name] = []
                        self.factory_definitions[factory_name].append({
                            'file': str(py_file),
                            'type': 'class'
                        })

                    # Look for function definitions
                    if f"def {factory_name}" in content:
                        if factory_name not in self.factory_definitions:
                            self.factory_definitions[factory_name] = []
                        self.factory_definitions[factory_name].append({
                            'file': str(py_file),
                            'type': 'function'
                        })

            except Exception as e:
                logger.debug(f"Error finding factory definitions in {py_file}: {e}")

    def _map_single_factory_consumers(self, base_path: Path, factory_name: str,
                                    exclude_patterns: List[str]) -> FactoryConsumerMap:
        """Map all consumers for a single factory."""
        factory_map = FactoryConsumerMap(factory_name=factory_name)

        # Find all files in the codebase
        for py_file in base_path.rglob("*.py"):
            if self._should_skip_file(py_file, exclude_patterns):
                continue

            try:
                usages = self._find_factory_usage_in_file(str(py_file), factory_name)

                if usages:
                    factory_map.usage_by_file[str(py_file)] = usages

                    # Categorize usages
                    for usage in usages:
                        # By function
                        func_key = f"{usage.consumer_file}::{usage.consumer_function}"
                        if func_key not in factory_map.usage_by_function:
                            factory_map.usage_by_function[func_key] = []
                        factory_map.usage_by_function[func_key].append(usage)

                        # By type
                        if usage.usage_type not in factory_map.usage_by_type:
                            factory_map.usage_by_type[usage.usage_type] = 0
                        factory_map.usage_by_type[usage.usage_type] += 1

                        # Count critical usages
                        if usage.criticality in ['HIGH', 'CRITICAL']:
                            factory_map.critical_usage_points += 1

            except Exception as e:
                logger.debug(f"Error mapping consumers in {py_file}: {e}")

        # Calculate summary metrics
        factory_map.total_usage_points = sum(
            len(usages) for usages in factory_map.usage_by_file.values()
        )
        factory_map.direct_consumers = len(factory_map.usage_by_file)

        # Calculate migration impact score
        factory_map.migration_impact_score = self._calculate_migration_impact_score(factory_map)

        return factory_map

    def _find_factory_usage_in_file(self, file_path: str, factory_name: str) -> List[ConsumerUsage]:
        """Find all usages of a factory in a specific file."""
        usages = []

        try:
            content = self._get_file_content(file_path)

            # Quick check if factory is mentioned at all
            if factory_name not in content:
                return usages

            # Try AST parsing for accurate analysis
            try:
                tree = self._get_ast(file_path)
                usages.extend(self._analyze_ast_for_usage(tree, file_path, factory_name))
            except SyntaxError:
                # Fallback to regex analysis
                usages.extend(self._analyze_regex_for_usage(content, file_path, factory_name))

        except Exception as e:
            logger.debug(f"Error finding factory usage in {file_path}: {e}")

        return usages

    def _analyze_ast_for_usage(self, tree: ast.AST, file_path: str, factory_name: str) -> List[ConsumerUsage]:
        """Analyze AST for factory usage patterns."""
        usages = []

        class FactoryUsageVisitor(ast.NodeVisitor):
            def __init__(self, outer_self):
                self.outer_self = outer_self
                self.current_function = "module_level"
                self.function_stack = []

            def visit_FunctionDef(self, node):
                self.function_stack.append(self.current_function)
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = self.function_stack.pop()

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

            def visit_ClassDef(self, node):
                self.function_stack.append(self.current_function)
                self.current_function = f"class_{node.name}"
                self.generic_visit(node)
                self.current_function = self.function_stack.pop()

            def visit_Import(self, node):
                for alias in node.names:
                    if factory_name in alias.name:
                        usage = self.outer_self._create_usage(
                            factory_name, file_path, self.current_function,
                            getattr(node, 'lineno', 0), 'import',
                            f"import {alias.name}"
                        )
                        usages.append(usage)

            def visit_ImportFrom(self, node):
                if node.names:
                    for alias in node.names:
                        if alias.name == factory_name:
                            usage = self.outer_self._create_usage(
                                factory_name, file_path, self.current_function,
                                getattr(node, 'lineno', 0), 'import',
                                f"from {node.module} import {alias.name}"
                            )
                            usages.append(usage)

            def visit_Call(self, node):
                # Direct function calls
                if isinstance(node.func, ast.Name) and node.func.id == factory_name:
                    usage = self.outer_self._create_usage(
                        factory_name, file_path, self.current_function,
                        getattr(node, 'lineno', 0), 'call',
                        f"{factory_name}(...)"
                    )
                    usages.append(usage)

                # Method calls on factory
                elif isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and
                        factory_name in node.func.value.id):
                        usage = self.outer_self._create_usage(
                            factory_name, file_path, self.current_function,
                            getattr(node, 'lineno', 0), 'call',
                            f"{node.func.value.id}.{node.func.attr}(...)"
                        )
                        usages.append(usage)

                self.generic_visit(node)

            def visit_Assign(self, node):
                # Variable assignments
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == factory_name:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                usage = self.outer_self._create_usage(
                                    factory_name, file_path, self.current_function,
                                    getattr(node, 'lineno', 0), 'instantiation',
                                    f"{target.id} = {factory_name}(...)"
                                )
                                usages.append(usage)

                self.generic_visit(node)

        visitor = FactoryUsageVisitor(self)
        visitor.visit(tree)
        return usages

    def _analyze_regex_for_usage(self, content: str, file_path: str, factory_name: str) -> List[ConsumerUsage]:
        """Fallback regex analysis for factory usage."""
        usages = []
        lines = content.split('\n')
        current_function = "module_level"

        for i, line in enumerate(lines):
            # Track current function context
            func_match = re.search(r'def\s+(\w+)', line)
            if func_match:
                current_function = func_match.group(1)

            # Look for factory usage
            if factory_name in line:
                usage_type = 'call'
                context = line.strip()

                # Determine usage type
                if 'import' in line:
                    usage_type = 'import'
                elif f'{factory_name}(' in line:
                    usage_type = 'call'
                elif f'= {factory_name}' in line:
                    usage_type = 'instantiation'
                elif f'class' in line and factory_name in line:
                    usage_type = 'inheritance'

                usage = self._create_usage(
                    factory_name, file_path, current_function,
                    i + 1, usage_type, context
                )
                usages.append(usage)

        return usages

    def _create_usage(self, factory_name: str, file_path: str, function_name: str,
                     line_number: int, usage_type: str, context: str) -> ConsumerUsage:
        """Create a ConsumerUsage object with analysis."""
        usage = ConsumerUsage(
            factory_name=factory_name,
            consumer_file=file_path,
            consumer_function=function_name,
            line_number=line_number,
            usage_type=usage_type,
            usage_context=context
        )

        # Analyze criticality
        usage.criticality = self._assess_usage_criticality(context, file_path)

        # Check user isolation impact
        usage.user_isolation_impact = self._has_user_isolation_impact(context)

        # Identify business function
        usage.business_function = self._identify_business_function(context, file_path)

        # Assess migration complexity
        usage.migration_complexity = self._assess_migration_complexity(usage_type, context)

        return usage

    def _assess_usage_criticality(self, context: str, file_path: str) -> str:
        """Assess the criticality of a factory usage."""
        context_lower = context.lower()
        file_path_lower = file_path.lower()

        # Critical indicators
        if any(indicator in context_lower for indicator in self.CRITICAL_INDICATORS):
            return "CRITICAL"

        # High criticality for production paths
        if any(keyword in file_path_lower for keyword in ['production', 'deploy', 'main']):
            return "HIGH"

        # High criticality for user-facing functionality
        if any(keyword in context_lower for keyword in ['user', 'auth', 'session', 'websocket']):
            return "HIGH"

        # Medium for business logic
        if any(keyword in context_lower for keyword in ['agent', 'execute', 'process', 'handle']):
            return "MEDIUM"

        # Low for tests and utilities
        if any(keyword in file_path_lower for keyword in ['test', 'util', 'helper', 'mock']):
            return "LOW"

        return "MEDIUM"  # Default

    def _has_user_isolation_impact(self, context: str) -> bool:
        """Check if usage impacts user isolation."""
        return any(keyword in context for keyword in self.USER_ISOLATION_KEYWORDS)

    def _identify_business_function(self, context: str, file_path: str) -> Optional[str]:
        """Identify the business function associated with this usage."""
        context_and_path = (context + " " + file_path).lower()

        for function_name, keywords in self.BUSINESS_FUNCTIONS.items():
            if any(keyword in context_and_path for keyword in keywords):
                return function_name

        return None

    def _assess_migration_complexity(self, usage_type: str, context: str) -> str:
        """Assess the complexity of migrating this usage."""
        # Imports are usually simple to migrate
        if usage_type == 'import':
            return "SIMPLE"

        # Inheritance is complex
        if usage_type == 'inheritance':
            return "COMPLEX"

        # Check for complex patterns in context
        complex_patterns = [
            'singleton', 'global', 'cache', 'pool',
            'registry', 'manager', 'coordinator'
        ]

        if any(pattern in context.lower() for pattern in complex_patterns):
            return "COMPLEX"

        # Check for parameters or configuration
        if '(' in context and len(context.split(',')) > 2:
            return "MODERATE"

        return "SIMPLE"

    def _analyze_dependency_graph(self) -> None:
        """Analyze dependencies between factories."""
        dependency_graph = defaultdict(list)

        for factory_name, factory_map in self.result.factory_maps.items():
            for file_path, usages in factory_map.usage_by_file.items():
                for usage in usages:
                    # Check if this file contains other factories
                    content = self._get_file_content(file_path)

                    for other_factory in self.result.factory_maps.keys():
                        if other_factory != factory_name and other_factory in content:
                            # There's a dependency relationship
                            dependency_graph[factory_name].append(other_factory)

        self.result.global_dependency_graph = dict(dependency_graph)

        # Add consumer relationships to factory maps
        for factory_name, dependencies in dependency_graph.items():
            factory_map = self.result.factory_maps[factory_name]
            for dep in dependencies:
                relationship = ConsumerRelationship(
                    factory_name=factory_name,
                    consumer_file=dep,  # In this case, dep is another factory
                    relationship_type='direct',
                    depth=1,
                    path=[factory_name, dep]
                )
                factory_map.consumer_relationships.append(relationship)

    def _identify_critical_paths(self) -> None:
        """Identify critical dependency paths in the factory graph."""
        critical_paths = []

        # Find paths that involve multiple factories
        def find_paths(start_factory: str, visited: Set[str], path: List[str]) -> None:
            if len(path) > 5:  # Prevent infinite loops
                return

            dependencies = self.result.global_dependency_graph.get(start_factory, [])

            for dep in dependencies:
                if dep in visited:
                    # Found a cycle - this is critical
                    critical_paths.append(path + [dep])
                else:
                    visited.add(dep)
                    find_paths(dep, visited.copy(), path + [dep])

        for factory_name in self.result.factory_maps.keys():
            find_paths(factory_name, {factory_name}, [factory_name])

        # Also find long chains
        for factory_name in self.result.factory_maps.keys():
            dependencies = self.result.global_dependency_graph.get(factory_name, [])
            if len(dependencies) > 2:
                critical_paths.append([factory_name] + dependencies)

        self.result.critical_paths = critical_paths

    def _calculate_migration_impact_score(self, factory_map: FactoryConsumerMap) -> int:
        """Calculate migration impact score for a factory."""
        score = 0

        # Base score from usage count
        score += min(factory_map.total_usage_points, 50)  # Cap at 50

        # Critical usage penalty
        score += factory_map.critical_usage_points * 3

        # Complex usage penalty
        for usages in factory_map.usage_by_file.values():
            for usage in usages:
                if usage.migration_complexity == "COMPLEX":
                    score += 5
                elif usage.migration_complexity == "MODERATE":
                    score += 2

        # User isolation impact penalty
        for usages in factory_map.usage_by_file.values():
            if any(usage.user_isolation_impact for usage in usages):
                score += 10

        return score

    def _calculate_metrics(self) -> None:
        """Calculate overall metrics."""
        self.result.total_factories_analyzed = len(self.result.factory_maps)

        total_usage = 0
        for factory_map in self.result.factory_maps.values():
            total_usage += factory_map.total_usage_points

        self.result.total_usage_points = total_usage

    def _generate_recommendations(self) -> None:
        """Generate migration recommendations based on analysis."""
        recommendations = []

        # Analyze factory complexity
        high_impact_factories = []
        low_impact_factories = []

        for factory_name, factory_map in self.result.factory_maps.items():
            if factory_map.migration_impact_score > 30:
                high_impact_factories.append(factory_name)
            elif factory_map.migration_impact_score < 10:
                low_impact_factories.append(factory_name)

        if low_impact_factories:
            recommendations.append(
                f"Consider removing {len(low_impact_factories)} low-impact factories first: "
                f"{', '.join(low_impact_factories[:5])}"
            )

        if high_impact_factories:
            recommendations.append(
                f"High-impact factories require careful migration planning: "
                f"{', '.join(high_impact_factories[:5])}"
            )

        # Circular dependency recommendations
        if self.result.critical_paths:
            recommendations.append(
                f"Resolve {len(self.result.critical_paths)} circular dependencies "
                f"before factory migration"
            )

        # User isolation recommendations
        isolation_factories = []
        for factory_name, factory_map in self.result.factory_maps.items():
            for usages in factory_map.usage_by_file.values():
                if any(usage.user_isolation_impact for usage in usages):
                    isolation_factories.append(factory_name)
                    break

        if isolation_factories:
            recommendations.append(
                f"Preserve user isolation in {len(isolation_factories)} factories "
                f"during migration"
            )

        self.result.migration_recommendations = recommendations

    def _get_file_content(self, file_path: str) -> str:
        """Get file content with caching."""
        if file_path not in self.file_cache:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.file_cache[file_path] = f.read()
            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")
                self.file_cache[file_path] = ""

        return self.file_cache[file_path]

    def _get_ast(self, file_path: str) -> ast.AST:
        """Get AST with caching."""
        if file_path not in self.ast_cache:
            content = self._get_file_content(file_path)
            self.ast_cache[file_path] = ast.parse(content)

        return self.ast_cache[file_path]

    def _should_skip_file(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if file should be skipped."""
        path_str = str(file_path)
        return any(pattern in path_str for pattern in exclude_patterns)

    def generate_consumer_graph_data(self) -> Dict[str, Any]:
        """Generate data for consumer relationship visualization."""
        nodes = []
        edges = []

        # Add factory nodes
        for factory_name, factory_map in self.result.factory_maps.items():
            nodes.append({
                'id': factory_name,
                'label': factory_name,
                'type': 'factory',
                'usage_count': factory_map.total_usage_points,
                'impact_score': factory_map.migration_impact_score,
                'critical_usage': factory_map.critical_usage_points
            })

        # Add consumer file nodes and edges
        for factory_name, factory_map in self.result.factory_maps.items():
            for file_path in factory_map.usage_by_file.keys():
                file_id = f"file_{hash(file_path)}"

                nodes.append({
                    'id': file_id,
                    'label': Path(file_path).name,
                    'type': 'consumer',
                    'full_path': file_path
                })

                edges.append({
                    'source': file_id,
                    'target': factory_name,
                    'type': 'uses',
                    'usage_count': len(factory_map.usage_by_file[file_path])
                })

        # Add factory-to-factory dependencies
        for factory_name, dependencies in self.result.global_dependency_graph.items():
            for dep in dependencies:
                edges.append({
                    'source': factory_name,
                    'target': dep,
                    'type': 'depends_on'
                })

        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_factories': len(self.result.factory_maps),
                'total_usage_points': self.result.total_usage_points,
                'critical_paths': len(self.result.critical_paths)
            }
        }

    def generate_detailed_report(self) -> str:
        """Generate comprehensive consumer mapping report."""
        report_lines = [
            "=" * 80,
            "FACTORY CONSUMER MAPPING REPORT - Issue #1194 Phase 1",
            "=" * 80,
            "",
            "MAPPING SUMMARY:",
            f"  Factories Analyzed: {self.result.total_factories_analyzed}",
            f"  Total Usage Points: {self.result.total_usage_points}",
            f"  Critical Dependency Paths: {len(self.result.critical_paths)}",
            ""
        ]

        # Factory analysis by impact score
        factories_by_impact = sorted(
            self.result.factory_maps.items(),
            key=lambda x: x[1].migration_impact_score,
            reverse=True
        )

        report_lines.extend([
            "FACTORIES BY MIGRATION IMPACT:",
            ""
        ])

        for factory_name, factory_map in factories_by_impact[:10]:  # Top 10
            report_lines.extend([
                f"  {factory_name}:",
                f"    Usage Points: {factory_map.total_usage_points}",
                f"    Critical Usage: {factory_map.critical_usage_points}",
                f"    Direct Consumers: {factory_map.direct_consumers}",
                f"    Impact Score: {factory_map.migration_impact_score}",
                ""
            ])

        # Usage patterns
        total_by_type = defaultdict(int)
        for factory_map in self.result.factory_maps.values():
            for usage_type, count in factory_map.usage_by_type.items():
                total_by_type[usage_type] += count

        if total_by_type:
            report_lines.extend([
                "USAGE PATTERNS:",
                *[f"  {usage_type}: {count}" for usage_type, count in total_by_type.items()],
                ""
            ])

        # Critical paths
        if self.result.critical_paths:
            report_lines.extend([
                "CRITICAL DEPENDENCY PATHS:",
                *[f"  {' → '.join(path)}" for path in self.result.critical_paths[:5]],
                ""
            ])

        # Recommendations
        if self.result.migration_recommendations:
            report_lines.extend([
                "MIGRATION RECOMMENDATIONS:",
                *[f"  - {rec}" for rec in self.result.migration_recommendations],
                ""
            ])

        # Business function analysis
        business_functions = defaultdict(int)
        for factory_map in self.result.factory_maps.values():
            for usages in factory_map.usage_by_file.values():
                for usage in usages:
                    if usage.business_function:
                        business_functions[usage.business_function] += 1

        if business_functions:
            report_lines.extend([
                "BUSINESS FUNCTION IMPACT:",
                *[f"  {func}: {count} usage points"
                  for func, count in sorted(business_functions.items(),
                                          key=lambda x: x[1], reverse=True)],
                ""
            ])

        return "\n".join(report_lines)


def main():
    """Main entry point for factory consumer mapping."""
    parser = argparse.ArgumentParser(
        description="Map factory consumer usage points throughout the codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--path', '-p',
        type=Path,
        default=project_root,
        help='Path to analyze (default: project root)'
    )

    parser.add_argument(
        '--factories', '-f',
        nargs='*',
        help='Specific factory names to analyze (if not provided, auto-detect)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for mapping results'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'text', 'graph'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '--exclude',
        nargs='*',
        default=['__pycache__', '.git', 'node_modules', '.pytest_cache', 'venv', 'backups'],
        help='Patterns to exclude from analysis'
    )

    parser.add_argument(
        '--min-usage',
        type=int,
        default=1,
        help='Minimum usage count to include factory in results'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        mapper = FactoryConsumerMapper()

        # Perform consumer mapping
        result = mapper.map_factory_consumers(
            args.path,
            args.factories,
            args.exclude
        )

        # Filter by minimum usage if specified
        if args.min_usage > 1:
            filtered_maps = {}
            for name, factory_map in result.factory_maps.items():
                if factory_map.total_usage_points >= args.min_usage:
                    filtered_maps[name] = factory_map
            result.factory_maps = filtered_maps
            result.total_factories_analyzed = len(filtered_maps)

        # Generate output
        if args.format == 'json':
            output_content = json.dumps(asdict(result), indent=2, default=str)
        elif args.format == 'graph':
            graph_data = mapper.generate_consumer_graph_data()
            output_content = json.dumps(graph_data, indent=2, default=str)
        else:
            output_content = mapper.generate_detailed_report()

        # Write output
        if args.output:
            args.output.write_text(output_content, encoding='utf-8')
            logger.info(f"Consumer mapping report written to {args.output}")
        else:
            print(output_content)

        # Summary
        logger.info(f"Consumer mapping complete:")
        logger.info(f"  Analyzed {result.total_factories_analyzed} factories")
        logger.info(f"  Found {result.total_usage_points} usage points")
        logger.info(f"  Identified {len(result.critical_paths)} critical paths")

        return 0

    except Exception as e:
        logger.error(f"Consumer mapping failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())