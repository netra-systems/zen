#!/usr/bin/env python3
"""
Factory Pattern Analysis Script - Issue #1194 Phase 1

This script provides comprehensive analysis of factory patterns in the Netra Apex codebase
to support the factory cleanup initiative. It identifies factories, their usage patterns,
and provides data for migration planning.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Reduce architectural complexity and improve maintainability
- Value Impact: Reduce 65 factories to <20, eliminate over-engineering
- Strategic Impact: Enable faster development and reduced maintenance overhead

Key Features:
- Comprehensive factory pattern detection
- Usage point mapping and analysis
- Complexity metrics and recommendations
- Migration impact assessment
- Safety validation for factory removal

Part of Issue #1194 Phase 1: Safety Infrastructure & Analysis
"""

import argparse
import ast
import json
import re
import sys
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
class FactoryUsage:
    """Represents a single usage of a factory."""
    file_path: str
    line_number: int
    function_name: str
    usage_type: str  # 'call', 'import', 'inheritance', 'assignment'
    context: str
    is_critical: bool = False
    user_isolation_required: bool = False


@dataclass
class FactoryPattern:
    """Represents a factory pattern found in the codebase."""
    name: str
    file_path: str
    line_number: int
    factory_type: str  # 'function', 'class', 'method', 'singleton'
    purpose: str
    complexity_score: int = 0
    essential: bool = False
    multi_user_isolation: bool = False
    usage_count: int = 0
    usages: List[FactoryUsage] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    migration_risk: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class FactoryAnalysisResult:
    """Complete factory analysis results."""
    total_factories: int = 0
    essential_factories: int = 0
    over_engineered_factories: int = 0
    singleton_factories: int = 0
    multi_user_factories: int = 0
    total_usage_points: int = 0
    factories: List[FactoryPattern] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    migration_plan: Dict[str, Any] = field(default_factory=dict)


class FactoryPatternAnalyzer:
    """Analyzes factory patterns throughout the codebase."""

    # Essential factories that must be preserved (from issue description)
    ESSENTIAL_FACTORIES = {
        'AgentInstanceFactory': 'Multi-user isolation for agent creation',
        'UserExecutionContextFactory': 'User context isolation',
        'DatabaseSessionFactory': 'Database session management',
        'WebSocketConnectionFactory': 'WebSocket connection management',
        'LLMClientFactory': 'LLM client instantiation',
        'ToolDispatcherFactory': 'Tool creation and dispatch',
        'ConfigurationFactory': 'Environment-specific configuration',
        'TestRepositoryFactory': 'Test data creation'
    }

    # Patterns that indicate over-engineering
    OVER_ENGINEERING_PATTERNS = [
        r'create_.*_factory_factory',  # Factory factories
        r'get_.*_factory_instance',    # Singleton getters
        r'Factory.*Factory',           # Nested factory names
        r'Simple.*Factory',            # Unnecessarily simple factories
        r'Basic.*Factory',             # Basic wrappers
        r'Default.*Factory',           # Default implementations
    ]

    # Keywords that suggest complexity
    COMPLEXITY_KEYWORDS = [
        'registry', 'pool', 'cache', 'singleton', 'global', 'shared',
        'manager', 'coordinator', 'orchestrator', 'builder', 'director'
    ]

    def __init__(self):
        self.result = FactoryAnalysisResult()
        self.file_cache = {}  # Cache parsed files to avoid re-parsing

    def analyze_codebase(self, base_path: Path,
                        exclude_patterns: Optional[List[str]] = None) -> FactoryAnalysisResult:
        """
        Analyze the entire codebase for factory patterns.

        Args:
            base_path: Root directory to analyze
            exclude_patterns: Patterns to exclude from analysis

        Returns:
            FactoryAnalysisResult: Complete analysis results
        """
        if exclude_patterns is None:
            exclude_patterns = [
                '__pycache__', '.git', 'node_modules', '.pytest_cache',
                'venv', 'env', '.venv', 'htmlcov', 'backups'
            ]

        logger.info(f"Starting factory pattern analysis of {base_path}")

        # Find all Python files
        python_files = []
        for py_file in base_path.rglob("*.py"):
            if self._should_skip_file(py_file, exclude_patterns):
                continue
            python_files.append(py_file)

        logger.info(f"Found {len(python_files)} Python files to analyze")

        # Analyze each file
        for file_path in python_files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {e}")
                continue

        # Post-process results
        self._calculate_metrics()
        self._generate_recommendations()
        self._create_migration_plan()

        logger.info(f"Analysis complete: {self.result.total_factories} factories found")
        return self.result

    def _should_skip_file(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """Check if file should be skipped based on exclude patterns."""
        path_str = str(file_path)
        return any(pattern in path_str for pattern in exclude_patterns)

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for factory patterns."""
        try:
            content = file_path.read_text(encoding='utf-8')

            # Cache the content for usage analysis
            self.file_cache[str(file_path)] = content

            # Parse AST for detailed analysis
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, file_path, content)
            except SyntaxError as e:
                logger.debug(f"Syntax error in {file_path}: {e}")
                # Fallback to regex analysis for files with syntax issues
                self._analyze_with_regex(file_path, content)

        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")

    def _analyze_ast(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Analyze AST for factory patterns."""
        lines = content.split('\n')

        for node in ast.walk(tree):
            # Analyze class definitions
            if isinstance(node, ast.ClassDef):
                self._analyze_class_def(node, file_path, lines)

            # Analyze function definitions
            elif isinstance(node, ast.FunctionDef):
                self._analyze_function_def(node, file_path, lines)

            # Analyze assignments for factory variables
            elif isinstance(node, ast.Assign):
                self._analyze_assignment(node, file_path, lines)

    def _analyze_class_def(self, node: ast.ClassDef, file_path: Path, lines: List[str]) -> None:
        """Analyze class definition for factory patterns."""
        class_name = node.name

        # Check if it's a factory class
        if self._is_factory_class(class_name):
            factory = FactoryPattern(
                name=class_name,
                file_path=str(file_path),
                line_number=getattr(node, 'lineno', 0),
                factory_type='class',
                purpose=self._extract_purpose_from_docstring(node),
                essential=class_name in self.ESSENTIAL_FACTORIES,
                multi_user_isolation=self._has_multi_user_isolation(node, lines)
            )

            # Calculate complexity
            factory.complexity_score = self._calculate_class_complexity(node, class_name)

            # Determine migration risk
            factory.migration_risk = self._assess_migration_risk(factory)

            self.result.factories.append(factory)

    def _analyze_function_def(self, node: ast.FunctionDef, file_path: Path, lines: List[str]) -> None:
        """Analyze function definition for factory patterns."""
        func_name = node.name

        # Check if it's a factory function
        if self._is_factory_function(func_name):
            factory = FactoryPattern(
                name=func_name,
                file_path=str(file_path),
                line_number=getattr(node, 'lineno', 0),
                factory_type='function',
                purpose=self._extract_purpose_from_docstring(node),
                essential=self._is_essential_function(func_name),
                multi_user_isolation=self._function_has_user_isolation(node, lines)
            )

            # Calculate complexity
            factory.complexity_score = self._calculate_function_complexity(node, func_name)

            # Check for singleton patterns
            if self._is_singleton_pattern(node, lines):
                factory.factory_type = 'singleton'

            # Determine migration risk
            factory.migration_risk = self._assess_migration_risk(factory)

            self.result.factories.append(factory)

    def _analyze_assignment(self, node: ast.Assign, file_path: Path, lines: List[str]) -> None:
        """Analyze assignments for factory pattern variables."""
        # Look for factory assignments like _factory = SomeFactory()
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if self._is_factory_variable(var_name):
                    # Create a factory pattern entry for this variable
                    factory = FactoryPattern(
                        name=var_name,
                        file_path=str(file_path),
                        line_number=getattr(node, 'lineno', 0),
                        factory_type='variable',
                        purpose=f"Factory variable: {var_name}",
                        complexity_score=1  # Simple assignment
                    )

                    self.result.factories.append(factory)

    def _analyze_with_regex(self, file_path: Path, content: str) -> None:
        """Fallback regex analysis for files with syntax issues."""
        lines = content.split('\n')

        # Look for factory class definitions
        for i, line in enumerate(lines):
            # Class factories
            class_match = re.search(r'class\s+(\w*[Ff]actory\w*)', line)
            if class_match:
                factory_name = class_match.group(1)
                factory = FactoryPattern(
                    name=factory_name,
                    file_path=str(file_path),
                    line_number=i + 1,
                    factory_type='class',
                    purpose=f"Factory class (regex detected): {factory_name}",
                    essential=factory_name in self.ESSENTIAL_FACTORIES,
                    complexity_score=2  # Estimated
                )
                self.result.factories.append(factory)

            # Function factories
            func_match = re.search(r'def\s+(create_\w+|get_\w+_factory|.*_factory)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                factory = FactoryPattern(
                    name=func_name,
                    file_path=str(file_path),
                    line_number=i + 1,
                    factory_type='function',
                    purpose=f"Factory function (regex detected): {func_name}",
                    essential=self._is_essential_function(func_name),
                    complexity_score=1  # Estimated
                )
                self.result.factories.append(factory)

    def _is_factory_class(self, class_name: str) -> bool:
        """Check if a class name indicates a factory pattern."""
        factory_indicators = [
            'factory', 'Factory', 'creator', 'Creator',
            'builder', 'Builder', 'provider', 'Provider'
        ]
        return any(indicator in class_name for indicator in factory_indicators)

    def _is_factory_function(self, func_name: str) -> bool:
        """Check if a function name indicates a factory pattern."""
        factory_patterns = [
            r'^create_\w+',
            r'^get_\w+_factory',
            r'^make_\w+',
            r'^build_\w+',
            r'.*_factory$',
            r'^configure_\w+_factory',
            r'^setup_\w+'
        ]
        return any(re.match(pattern, func_name) for pattern in factory_patterns)

    def _is_factory_variable(self, var_name: str) -> bool:
        """Check if a variable name indicates a factory pattern."""
        return 'factory' in var_name.lower() and not var_name.startswith('_')

    def _is_essential_function(self, func_name: str) -> bool:
        """Check if a function is essential based on naming patterns."""
        essential_patterns = [
            'create_agent_instance_factory',
            'create_user_execution_context',
            'create_websocket_manager',
            'create_database_session',
            'create_llm_client',
            'get_agent_class_registry'
        ]
        return any(pattern in func_name for pattern in essential_patterns)

    def _extract_purpose_from_docstring(self, node) -> str:
        """Extract purpose from function/class docstring."""
        if ast.get_docstring(node):
            docstring = ast.get_docstring(node)
            # Get first line of docstring as purpose
            first_line = docstring.split('\n')[0].strip()
            return first_line[:100]  # Limit length
        return "No documentation"

    def _has_multi_user_isolation(self, node: ast.ClassDef, lines: List[str]) -> bool:
        """Check if class supports multi-user isolation."""
        # Look for user_context parameters, user isolation patterns
        class_content = '\n'.join(lines[node.lineno-1:node.end_lineno or node.lineno])

        isolation_indicators = [
            'user_context', 'UserExecutionContext', 'user_id',
            'isolation', 'per_user', 'per_request', 'context_isolation'
        ]
        return any(indicator in class_content for indicator in isolation_indicators)

    def _function_has_user_isolation(self, node: ast.FunctionDef, lines: List[str]) -> bool:
        """Check if function supports user isolation."""
        # Check function parameters for user context
        args = [arg.arg for arg in node.args.args]
        isolation_args = ['user_context', 'user_id', 'context', 'user_execution_context']
        return any(arg in args for arg in isolation_args)

    def _calculate_class_complexity(self, node: ast.ClassDef, class_name: str) -> int:
        """Calculate complexity score for a class."""
        score = 0

        # Base complexity for being a class
        score += 2

        # Number of methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        score += len(methods)

        # Complexity keywords in name
        score += sum(1 for keyword in self.COMPLEXITY_KEYWORDS
                    if keyword.lower() in class_name.lower())

        # Over-engineering patterns
        score += sum(2 for pattern in self.OVER_ENGINEERING_PATTERNS
                    if re.search(pattern, class_name, re.IGNORECASE))

        # Lines of code (estimated)
        if hasattr(node, 'end_lineno') and node.end_lineno:
            lines_of_code = node.end_lineno - node.lineno
            score += min(lines_of_code // 50, 10)  # Cap at 10 points for LOC

        return score

    def _calculate_function_complexity(self, node: ast.FunctionDef, func_name: str) -> int:
        """Calculate complexity score for a function."""
        score = 0

        # Base complexity for being a function
        score += 1

        # Number of parameters
        score += len(node.args.args)

        # Complexity keywords in name
        score += sum(1 for keyword in self.COMPLEXITY_KEYWORDS
                    if keyword.lower() in func_name.lower())

        # Over-engineering patterns
        score += sum(2 for pattern in self.OVER_ENGINEERING_PATTERNS
                    if re.search(pattern, func_name, re.IGNORECASE))

        # Body complexity (number of statements)
        score += len(node.body)

        return score

    def _is_singleton_pattern(self, node: ast.FunctionDef, lines: List[str]) -> bool:
        """Check if function implements singleton pattern."""
        func_content = '\n'.join(lines[node.lineno-1:node.end_lineno or node.lineno])

        singleton_indicators = [
            '_instance', 'singleton', 'global', '_global_',
            'if not hasattr', 'if _instance is None',
            '@lru_cache', 'cached_property'
        ]
        return any(indicator in func_content for indicator in singleton_indicators)

    def _assess_migration_risk(self, factory: FactoryPattern) -> str:
        """Assess migration risk for a factory."""
        if factory.essential:
            return "CRITICAL"  # Essential factories need careful handling

        risk_score = 0

        # Complexity contributes to risk
        risk_score += factory.complexity_score // 3

        # Multi-user isolation makes migration riskier
        if factory.multi_user_isolation:
            risk_score += 2

        # Singleton patterns are high risk
        if factory.factory_type == 'singleton':
            risk_score += 3

        # Essential factories are critical risk
        if factory.name in self.ESSENTIAL_FACTORIES:
            return "CRITICAL"

        # Determine risk level
        if risk_score >= 6:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_metrics(self) -> None:
        """Calculate overall metrics from factory analysis."""
        self.result.total_factories = len(self.result.factories)

        for factory in self.result.factories:
            if factory.essential or factory.name in self.ESSENTIAL_FACTORIES:
                self.result.essential_factories += 1

            if factory.complexity_score > 5:
                self.result.over_engineered_factories += 1

            if factory.factory_type == 'singleton':
                self.result.singleton_factories += 1

            if factory.multi_user_isolation:
                self.result.multi_user_factories += 1

    def _generate_recommendations(self) -> None:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Over-engineering recommendations
        if self.result.over_engineered_factories > 0:
            recommendations.append(
                f"Remove {self.result.over_engineered_factories} over-engineered factories "
                f"with complexity scores > 5"
            )

        # Singleton recommendations
        if self.result.singleton_factories > 0:
            recommendations.append(
                f"Eliminate {self.result.singleton_factories} singleton factories "
                f"to prevent multi-user state contamination"
            )

        # Target achievement
        factories_to_remove = max(0, self.result.total_factories - 20)
        if factories_to_remove > 0:
            recommendations.append(
                f"Remove {factories_to_remove} factories to achieve target of <20 factories"
            )

        # Multi-user isolation
        non_isolated = self.result.total_factories - self.result.multi_user_factories
        if non_isolated > self.result.essential_factories:
            recommendations.append(
                f"Consider adding user isolation to {non_isolated - self.result.essential_factories} "
                f"factories or remove if not needed"
            )

        self.result.recommendations = recommendations

    def _create_migration_plan(self) -> None:
        """Create migration plan based on analysis."""
        # Group factories by migration risk
        by_risk = {'LOW': [], 'MEDIUM': [], 'HIGH': [], 'CRITICAL': []}

        for factory in self.result.factories:
            by_risk[factory.migration_risk].append(factory.name)

        # Create phased migration plan
        migration_plan = {
            'total_factories': self.result.total_factories,
            'target_factories': 20,
            'factories_to_remove': max(0, self.result.total_factories - 20),
            'phases': {
                'phase_1_low_risk': {
                    'factories': by_risk['LOW'],
                    'count': len(by_risk['LOW']),
                    'description': 'Remove simple, low-complexity factories with minimal usage'
                },
                'phase_2_medium_risk': {
                    'factories': by_risk['MEDIUM'],
                    'count': len(by_risk['MEDIUM']),
                    'description': 'Consolidate medium-complexity factories with validation'
                },
                'phase_3_high_risk': {
                    'factories': by_risk['HIGH'],
                    'count': len(by_risk['HIGH']),
                    'description': 'Carefully migrate high-complexity factories with extensive testing'
                },
                'preserve_critical': {
                    'factories': by_risk['CRITICAL'],
                    'count': len(by_risk['CRITICAL']),
                    'description': 'Preserve essential factories with multi-user isolation'
                }
            },
            'success_criteria': [
                'Reduce total factories from {} to <20'.format(self.result.total_factories),
                'Preserve 8 essential factories for multi-user isolation',
                'Eliminate all singleton patterns',
                'Maintain business functionality throughout migration'
            ]
        }

        self.result.migration_plan = migration_plan

    def find_factory_usage(self, factory_name: str) -> List[FactoryUsage]:
        """Find all usage points of a specific factory."""
        usages = []

        for file_path, content in self.file_cache.items():
            lines = content.split('\n')

            for i, line in enumerate(lines):
                if factory_name in line:
                    # Determine usage type
                    usage_type = 'call'
                    if 'import' in line:
                        usage_type = 'import'
                    elif 'class' in line and 'extends' in line:
                        usage_type = 'inheritance'
                    elif '=' in line and factory_name in line.split('=')[1]:
                        usage_type = 'assignment'

                    # Extract function context
                    function_name = self._find_containing_function(lines, i)

                    usage = FactoryUsage(
                        file_path=file_path,
                        line_number=i + 1,
                        function_name=function_name,
                        usage_type=usage_type,
                        context=line.strip(),
                        is_critical=self._is_critical_usage(line),
                        user_isolation_required=self._requires_user_isolation(line)
                    )
                    usages.append(usage)

        return usages

    def _find_containing_function(self, lines: List[str], line_index: int) -> str:
        """Find the function that contains the given line."""
        for i in range(line_index, -1, -1):
            line = lines[i].strip()
            if line.startswith('def ') or line.startswith('async def '):
                func_match = re.search(r'def\s+(\w+)', line)
                if func_match:
                    return func_match.group(1)
        return "module_level"

    def _is_critical_usage(self, line: str) -> bool:
        """Check if usage is critical for business functionality."""
        critical_indicators = [
            'user_context', 'agent_', 'websocket', 'database',
            'auth', 'llm', 'critical', 'production'
        ]
        return any(indicator in line.lower() for indicator in critical_indicators)

    def _requires_user_isolation(self, line: str) -> bool:
        """Check if usage requires user isolation."""
        isolation_indicators = [
            'user_id', 'user_context', 'UserExecutionContext',
            'per_user', 'isolation', 'multi_user'
        ]
        return any(indicator in line for indicator in isolation_indicators)

    def analyze_factory_dependencies(self) -> Dict[str, List[str]]:
        """Analyze dependencies between factories."""
        dependencies = {}

        for factory in self.result.factories:
            factory_deps = []

            # Look for other factories used in this factory's file
            if str(factory.file_path) in self.file_cache:
                content = self.file_cache[str(factory.file_path)]

                for other_factory in self.result.factories:
                    if (other_factory.name != factory.name and
                        other_factory.name in content):
                        factory_deps.append(other_factory.name)

            dependencies[factory.name] = factory_deps
            factory.dependencies = factory_deps

        return dependencies

    def generate_detailed_report(self) -> str:
        """Generate comprehensive analysis report."""
        report_lines = [
            "=" * 80,
            "FACTORY PATTERN ANALYSIS REPORT - Issue #1194 Phase 1",
            "=" * 80,
            "",
            "EXECUTIVE SUMMARY:",
            f"  Total Factories Found: {self.result.total_factories}",
            f"  Essential Factories: {self.result.essential_factories}",
            f"  Over-engineered Factories: {self.result.over_engineered_factories}",
            f"  Singleton Factories: {self.result.singleton_factories}",
            f"  Multi-user Isolation Factories: {self.result.multi_user_factories}",
            f"  Target Reduction: {max(0, self.result.total_factories - 20)} factories",
            "",
            "MIGRATION STRATEGY:",
        ]

        # Add migration plan details
        if self.result.migration_plan:
            plan = self.result.migration_plan
            for phase_name, phase_data in plan['phases'].items():
                report_lines.extend([
                    f"  {phase_name.upper()}:",
                    f"    Factories: {phase_data['count']}",
                    f"    Description: {phase_data['description']}",
                    ""
                ])

        # Add recommendations
        if self.result.recommendations:
            report_lines.extend([
                "RECOMMENDATIONS:",
                *[f"  - {rec}" for rec in self.result.recommendations],
                ""
            ])

        # Add factory details grouped by risk
        factories_by_risk = {}
        for factory in self.result.factories:
            risk = factory.migration_risk
            if risk not in factories_by_risk:
                factories_by_risk[risk] = []
            factories_by_risk[risk].append(factory)

        for risk_level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            if risk_level in factories_by_risk:
                factories = factories_by_risk[risk_level]
                report_lines.extend([
                    f"{risk_level} RISK FACTORIES ({len(factories)}):",
                ])

                for factory in factories[:10]:  # Show first 10
                    report_lines.append(
                        f"  - {factory.name} ({factory.factory_type}, "
                        f"complexity: {factory.complexity_score}, "
                        f"essential: {factory.essential})"
                    )

                if len(factories) > 10:
                    report_lines.append(f"  ... and {len(factories) - 10} more")
                report_lines.append("")

        return "\n".join(report_lines)


def main():
    """Main entry point for factory pattern analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze factory patterns in the Netra Apex codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--path', '-p',
        type=Path,
        default=project_root,
        help='Path to analyze (default: project root)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for analysis results'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'text'],
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
        '--factory-usage',
        type=str,
        help='Find usage points for a specific factory'
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
        analyzer = FactoryPatternAnalyzer()

        # Perform main analysis
        result = analyzer.analyze_codebase(args.path, args.exclude)

        # Analyze dependencies
        dependencies = analyzer.analyze_factory_dependencies()

        # Find specific factory usage if requested
        if args.factory_usage:
            usages = analyzer.find_factory_usage(args.factory_usage)
            logger.info(f"Found {len(usages)} usage points for {args.factory_usage}")

            # Add usage information to result
            result.total_usage_points = len(usages)

        # Generate output
        if args.format == 'json':
            output_data = {
                'analysis_result': asdict(result),
                'dependencies': dependencies,
                'factory_usage': asdict(usages) if args.factory_usage else None
            }
            output_content = json.dumps(output_data, indent=2, default=str)
        else:
            output_content = analyzer.generate_detailed_report()

            # Add dependency information
            if dependencies:
                output_content += "\n\nFACTORY DEPENDENCIES:\n"
                for factory, deps in dependencies.items():
                    if deps:
                        output_content += f"  {factory}: {', '.join(deps)}\n"

        # Write output
        if args.output:
            args.output.write_text(output_content, encoding='utf-8')
            logger.info(f"Analysis report written to {args.output}")
        else:
            print(output_content)

        # Summary
        logger.info(f"Analysis complete:")
        logger.info(f"  Found {result.total_factories} factories")
        logger.info(f"  {result.essential_factories} essential")
        logger.info(f"  {result.over_engineered_factories} over-engineered")
        logger.info(f"  Target reduction: {max(0, result.total_factories - 20)} factories")

        # Exit with warning if too many factories
        if result.total_factories > 20:
            logger.warning(f"Factory count ({result.total_factories}) exceeds target (20)")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Factory analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())