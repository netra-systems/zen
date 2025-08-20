#!/usr/bin/env python3
"""
Business Value Test Index Generator

Scans the codebase to create a comprehensive index of all tests,
categorized by business value, customer tier, and coverage dimensions.
"""

import ast
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import subprocess
import sys

@dataclass
class TestMetadata:
    """Metadata for a single test"""
    file_path: str
    test_name: str
    function_name: str
    line_number: int
    test_type: str  # unit, integration, e2e, real_llm, performance, etc.
    business_tier: str  # all, free, early, mid, enterprise
    component: str  # auth, websocket, agent, etc.
    category: str  # infrastructure_plumbing, customer_value_features, quality_gates
    decorators: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    real_services: List[str] = field(default_factory=list)
    uses_real_llm: bool = False
    is_e2e: bool = False
    is_multi_service: bool = False
    environment_validated: List[str] = field(default_factory=list)
    business_value_score: float = 0.0
    value_justification: str = ""
    coverage_percentage: Optional[float] = None
    last_run_status: Optional[str] = None
    failure_rate: float = 0.0

@dataclass
class ComponentCoverage:
    """Coverage metrics for a component"""
    component_name: str
    tier: str
    total_tests: int = 0
    unit_tests: int = 0
    integration_tests: int = 0
    e2e_tests: int = 0
    real_llm_tests: int = 0
    performance_tests: int = 0
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    business_value_total: float = 0.0
    critical_paths_covered: int = 0
    critical_paths_total: int = 0
    multi_env_pass_rate: float = 0.0

class BusinessValueTestIndexer:
    """Indexes all tests with business value perspective"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.tests: List[TestMetadata] = []
        self.coverage_by_component: Dict[str, ComponentCoverage] = {}
        self.tier_summary: Dict[str, Dict] = defaultdict(lambda: {
            'total_tests': 0,
            'coverage': 0.0,
            'value_score': 0.0,
            'components': set()
        })
        
        # Load business value spec
        self.spec = self._load_business_value_spec()
        
        # Test categorization patterns
        self.test_patterns = {
            'unit': r'test_.*_unit|unit_test_|TestUnit',
            'integration': r'test_.*_integration|integration_test_|TestIntegration',
            'e2e': r'test_.*_e2e|e2e_test_|TestE2E|test_end_to_end',
            'real_llm': r'test_.*_real_llm|real_llm_test_|with_real_llm|@real_llm',
            'performance': r'test_.*_performance|performance_test_|TestPerformance|test_.*_perf',
            'security': r'test_.*_security|security_test_|TestSecurity',
            'load': r'test_.*_load|load_test_|TestLoad'
        }
        
        # Component detection patterns
        self.component_patterns = {
            'authentication': r'auth|login|jwt|session|token',
            'websocket': r'websocket|ws|realtime|socket',
            'agent_orchestration': r'agent|supervisor|executor|chain',
            'database': r'database|db|postgres|clickhouse|orm',
            'cost_optimization': r'cost|optimization|pricing|billing',
            'analytics': r'analytics|metrics|dashboard|reporting',
            'team_collaboration': r'team|collaboration|sharing|permissions',
            'observability': r'observability|monitoring|logging|tracing|metrics'
        }
        
        # Tier detection patterns
        self.tier_patterns = {
            'free': r'free|trial|basic|onboarding',
            'early': r'early|starter|standard',
            'mid': r'mid|professional|advanced',
            'enterprise': r'enterprise|premium|sso|saml|sla'
        }

    def _load_business_value_spec(self) -> ET.Element:
        """Load the business value test coverage spec"""
        spec_path = self.project_root / 'SPEC' / 'business_value_test_coverage.xml'
        if spec_path.exists():
            return ET.parse(spec_path).getroot()
        return ET.Element('business_value_test_coverage')

    def scan_tests(self) -> None:
        """Scan all test files in the project"""
        # Focus on specific test directories for faster execution
        test_dirs = ['app/tests', 'tests', 'test_framework', 'dev_launcher/tests']
        test_count = 0
        max_tests = 500  # Limit for faster execution
        
        for test_dir in test_dirs:
            dir_path = self.project_root / test_dir
            if not dir_path.exists():
                continue
                
            for test_file in dir_path.glob('**/*.py'):
                if test_count >= max_tests:
                    break
                if test_file.name.startswith('test_') or test_file.name.endswith('_test.py'):
                    if 'node_modules' not in str(test_file) and '.venv' not in str(test_file):
                        self._scan_python_test(test_file)
                        test_count += 1
        
        # Also scan frontend tests if they exist (limited)
        frontend_dir = self.project_root / 'frontend'
        if frontend_dir.exists() and test_count < max_tests:
            for test_file in list(frontend_dir.glob('**/*.test.ts*'))[:50]:  # Limit frontend tests
                if 'node_modules' not in str(test_file):
                    self._scan_typescript_test(test_file)
                    test_count += 1

    def _scan_python_test(self, file_path: Path) -> None:
        """Scan a Python test file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    metadata = self._extract_python_test_metadata(node, file_path, content)
                    self.tests.append(metadata)
                elif isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                            metadata = self._extract_python_test_metadata(item, file_path, content, node.name)
                            self.tests.append(metadata)
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")

    def _extract_python_test_metadata(self, node: ast.FunctionDef, file_path: Path, 
                                     content: str, class_name: str = None) -> TestMetadata:
        """Extract metadata from a Python test function"""
        rel_path = str(file_path.relative_to(self.project_root))
        full_name = f"{class_name}.{node.name}" if class_name else node.name
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(decorator.attr)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(decorator.func.attr)
        
        # Determine test type
        test_type = self._determine_test_type(full_name, decorators, content)
        
        # Determine component
        component = self._determine_component(rel_path, full_name, content)
        
        # Determine tier
        tier = self._determine_tier(full_name, content, decorators)
        
        # Determine category
        category = self._determine_category(component)
        
        # Check for real services
        real_services = self._detect_real_services(content)
        uses_real_llm = 'real_llm' in decorators or 'real_llm' in test_type
        is_e2e = test_type == 'e2e' or 'e2e' in decorators
        is_multi_service = len(real_services) > 1
        
        # Calculate business value score
        value_score = self._calculate_business_value_score(
            tier, test_type, component, is_e2e, uses_real_llm, is_multi_service
        )
        
        return TestMetadata(
            file_path=rel_path,
            test_name=full_name,
            function_name=node.name,
            line_number=node.lineno,
            test_type=test_type,
            business_tier=tier,
            component=component,
            category=category,
            decorators=decorators,
            real_services=real_services,
            uses_real_llm=uses_real_llm,
            is_e2e=is_e2e,
            is_multi_service=is_multi_service,
            business_value_score=value_score,
            value_justification=self._generate_value_justification(tier, component, test_type)
        )

    def _scan_typescript_test(self, file_path: Path) -> None:
        """Scan a TypeScript/TSX test file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple regex-based extraction for TypeScript tests
            test_pattern = r"(?:test|it|describe)\s*\(\s*['\"`]([^'\"`]+)['\"`]"
            matches = re.findall(test_pattern, content)
            
            for match in matches:
                rel_path = str(file_path.relative_to(self.project_root))
                test_type = self._determine_test_type(match, [], content)
                component = self._determine_component(rel_path, match, content)
                tier = self._determine_tier(match, content, [])
                category = self._determine_category(component)
                
                metadata = TestMetadata(
                    file_path=rel_path,
                    test_name=match,
                    function_name=match,
                    line_number=0,  # Would need proper AST parsing for accurate line numbers
                    test_type=test_type,
                    business_tier=tier,
                    component=component,
                    category=category,
                    business_value_score=self._calculate_business_value_score(
                        tier, test_type, component, False, False, False
                    ),
                    value_justification=self._generate_value_justification(tier, component, test_type)
                )
                self.tests.append(metadata)
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")

    def _determine_test_type(self, name: str, decorators: List[str], content: str) -> str:
        """Determine the type of test"""
        name_lower = name.lower()
        content_lower = content.lower()
        
        for test_type, pattern in self.test_patterns.items():
            if re.search(pattern, name_lower) or re.search(pattern, ' '.join(decorators).lower()):
                return test_type
                
        # Default classification based on content
        if 'mock' in content_lower and 'real' not in content_lower:
            return 'unit'
        elif any(service in content_lower for service in ['redis', 'postgres', 'clickhouse']):
            return 'integration'
        else:
            return 'unit'

    def _determine_component(self, file_path: str, name: str, content: str) -> str:
        """Determine which component the test belongs to"""
        combined = f"{file_path} {name} {content[:500]}".lower()
        
        for component, pattern in self.component_patterns.items():
            if re.search(pattern, combined):
                return component
                
        # Default based on file path
        if 'frontend' in file_path:
            return 'frontend'
        elif 'app' in file_path:
            return 'backend'
        else:
            return 'other'

    def _determine_tier(self, name: str, content: str, decorators: List[str]) -> str:
        """Determine which business tier the test targets"""
        combined = f"{name} {' '.join(decorators)} {content[:500]}".lower()
        
        for tier, pattern in self.tier_patterns.items():
            if re.search(pattern, combined):
                return tier
                
        return 'all'  # Default to all tiers

    def _determine_category(self, component: str) -> str:
        """Determine the category based on component"""
        infrastructure = ['authentication', 'websocket', 'database', 'observability']
        customer_value = ['agent_orchestration', 'cost_optimization', 'analytics', 'team_collaboration']
        quality = ['performance', 'security', 'compliance']
        
        if component in infrastructure:
            return 'infrastructure_plumbing'
        elif component in customer_value:
            return 'customer_value_features'
        elif component in quality:
            return 'quality_gates'
        else:
            return 'other'

    def _detect_real_services(self, content: str) -> List[str]:
        """Detect which real services are used in the test"""
        services = []
        service_patterns = {
            'redis': r'redis|Redis|REDIS',
            'postgres': r'postgres|PostgreSQL|psycopg',
            'clickhouse': r'clickhouse|ClickHouse',
            'llm': r'openai|anthropic|gemini|gpt|claude',
            'websocket': r'websocket|WebSocket|ws://',
            'auth_service': r'auth_service|AuthService'
        }
        
        for service, pattern in service_patterns.items():
            if re.search(pattern, content):
                services.append(service)
                
        return services

    def _calculate_business_value_score(self, tier: str, test_type: str, component: str,
                                       is_e2e: bool, uses_real_llm: bool, 
                                       is_multi_service: bool) -> float:
        """Calculate business value score based on XML spec scoring model"""
        score = 0.0
        
        # Tier weight (25%)
        tier_scores = {'enterprise': 25, 'mid': 20, 'early': 15, 'free': 10, 'all': 18}
        score += tier_scores.get(tier, 5)
        
        # Test depth weight (20%)
        type_scores = {'e2e': 20, 'real_llm': 18, 'integration': 12, 'performance': 15, 
                      'security': 15, 'unit': 8, 'load': 14}
        score += type_scores.get(test_type, 5)
        
        # Component criticality (35% - revenue impact)
        critical_components = ['authentication', 'agent_orchestration', 'websocket']
        if component in critical_components:
            score += 35
        elif component in ['cost_optimization', 'analytics']:
            score += 25
        else:
            score += 15
            
        # Multi-service and real service bonus (10%)
        if is_multi_service:
            score += 10
        elif uses_real_llm or is_e2e:
            score += 7
            
        # Environment coverage placeholder (10%)
        score += 5  # Default, would be updated with actual multi-env data
        
        return min(100, score)  # Cap at 100

    def _generate_value_justification(self, tier: str, component: str, test_type: str) -> str:
        """Generate business value justification for the test"""
        justifications = {
            'authentication': f"Protects {tier} tier customer data and access control",
            'agent_orchestration': f"Core AI optimization delivering 30-50% cost savings for {tier} customers",
            'websocket': f"Enables real-time agent interactions for {tier} tier",
            'cost_optimization': f"Direct cost reduction features for {tier} customers",
            'analytics': f"Insights enabling optimization decisions for {tier} tier",
            'database': f"Data integrity and performance for {tier} workloads",
            'team_collaboration': f"Multi-user productivity for {tier} organizations",
            'observability': f"SLA compliance and incident prevention for {tier} tier"
        }
        
        base = justifications.get(component, f"Supports {tier} tier functionality")
        
        if test_type == 'e2e':
            return f"{base} - Full customer journey validation"
        elif test_type == 'real_llm':
            return f"{base} - Ensures AI quality meets expectations"
        elif test_type == 'performance':
            return f"{base} - Validates SLA compliance"
        else:
            return base

    def aggregate_coverage(self) -> None:
        """Aggregate coverage metrics by component and tier"""
        for test in self.tests:
            # Update component coverage
            if test.component not in self.coverage_by_component:
                self.coverage_by_component[test.component] = ComponentCoverage(
                    component_name=test.component,
                    tier=test.business_tier
                )
            
            comp_coverage = self.coverage_by_component[test.component]
            comp_coverage.total_tests += 1
            comp_coverage.business_value_total += test.business_value_score
            
            # Count test types
            if test.test_type == 'unit':
                comp_coverage.unit_tests += 1
            elif test.test_type == 'integration':
                comp_coverage.integration_tests += 1
            elif test.test_type == 'e2e':
                comp_coverage.e2e_tests += 1
            elif test.uses_real_llm:
                comp_coverage.real_llm_tests += 1
            elif test.test_type == 'performance':
                comp_coverage.performance_tests += 1
            
            # Update tier summary
            tier = test.business_tier
            self.tier_summary[tier]['total_tests'] += 1
            self.tier_summary[tier]['value_score'] += test.business_value_score
            self.tier_summary[tier]['components'].add(test.component)

    def load_coverage_data(self) -> None:
        """Load actual coverage data from coverage reports"""
        # Try to load Python coverage
        coverage_file = self.project_root / '.coverage'
        if coverage_file.exists():
            try:
                subprocess.run(['coverage', 'json', '-o', 'coverage.json'], 
                             cwd=self.project_root, capture_output=True)
                with open(self.project_root / 'coverage.json', 'r') as f:
                    coverage_data = json.load(f)
                    # Process coverage data
                    for file_path, file_data in coverage_data.get('files', {}).items():
                        # Map to components and update coverage
                        pass
            except Exception as e:
                print(f"Error loading Python coverage: {e}")
        
        # Try to load Jest coverage
        jest_coverage = self.project_root / 'frontend' / 'coverage' / 'coverage-final.json'
        if jest_coverage.exists():
            try:
                with open(jest_coverage, 'r') as f:
                    jest_data = json.load(f)
                    # Process Jest coverage data
                    pass
            except Exception as e:
                print(f"Error loading Jest coverage: {e}")

    def load_test_results(self) -> None:
        """Load test results from test reports"""
        test_results_file = self.project_root / 'test_reports' / 'test_results.json'
        if test_results_file.exists():
            try:
                with open(test_results_file, 'r') as f:
                    results = json.load(f)
                    
                # Map results to tests
                for test in self.tests:
                    # Match test results by name/path
                    # Update last_run_status, failure_rate, environment_validated
                    pass
            except Exception as e:
                print(f"Error loading test results: {e}")

    def generate_report(self) -> Dict:
        """Generate comprehensive business value test coverage report"""
        total_tests = len(self.tests)
        total_value = sum(t.business_value_score for t in self.tests)
        
        # Calculate tier coverage
        tier_report = {}
        for tier, data in self.tier_summary.items():
            tier_report[tier] = {
                'total_tests': data['total_tests'],
                'average_value_score': data['value_score'] / max(data['total_tests'], 1),
                'components_covered': len(data['components']),
                'coverage_percentage': 0.0  # Would be populated from actual coverage data
            }
        
        # Calculate test type distribution
        test_type_dist = defaultdict(int)
        for test in self.tests:
            test_type_dist[test.test_type] += 1
        
        # Calculate quality metrics
        real_llm_count = sum(1 for t in self.tests if t.uses_real_llm)
        e2e_count = sum(1 for t in self.tests if t.is_e2e)
        multi_service_count = sum(1 for t in self.tests if t.is_multi_service)
        
        # High value tests (score >= 70)
        high_value_tests = [t for t in self.tests if t.business_value_score >= 70]
        critical_tests = [t for t in self.tests if t.business_value_score >= 90]
        
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_tests': total_tests,
                'total_business_value': total_value,
                'average_value_score': total_value / max(total_tests, 1)
            },
            'tier_coverage': tier_report,
            'component_coverage': {
                comp: asdict(coverage) 
                for comp, coverage in self.coverage_by_component.items()
            },
            'test_type_distribution': dict(test_type_dist),
            'quality_metrics': {
                'real_llm_coverage': (real_llm_count / max(total_tests, 1)) * 100,
                'e2e_coverage': (e2e_count / max(total_tests, 1)) * 100,
                'multi_service_coverage': (multi_service_count / max(total_tests, 1)) * 100,
                'high_value_test_count': len(high_value_tests),
                'critical_test_count': len(critical_tests),
                'critical_test_percentage': (len(critical_tests) / max(total_tests, 1)) * 100
            },
            'top_value_tests': [
                {
                    'name': t.test_name,
                    'file': t.file_path,
                    'score': t.business_value_score,
                    'justification': t.value_justification
                }
                for t in sorted(self.tests, key=lambda x: x.business_value_score, reverse=True)[:20]
            ],
            'coverage_gaps': self._identify_coverage_gaps(),
            'recommendations': self._generate_recommendations()
        }
        
        return report

    def _identify_coverage_gaps(self) -> List[Dict]:
        """Identify critical coverage gaps"""
        gaps = []
        
        # Check for components with low test counts
        for comp, coverage in self.coverage_by_component.items():
            if coverage.total_tests < 10:
                gaps.append({
                    'type': 'low_test_count',
                    'component': comp,
                    'severity': 'high' if comp in ['authentication', 'agent_orchestration'] else 'medium',
                    'message': f"{comp} has only {coverage.total_tests} tests"
                })
            
            if coverage.e2e_tests == 0:
                gaps.append({
                    'type': 'missing_e2e',
                    'component': comp,
                    'severity': 'high',
                    'message': f"{comp} has no end-to-end tests"
                })
        
        # Check tier coverage
        for tier in ['enterprise', 'mid']:
            if self.tier_summary[tier]['total_tests'] < 20:
                gaps.append({
                    'type': 'low_tier_coverage',
                    'tier': tier,
                    'severity': 'critical' if tier == 'enterprise' else 'high',
                    'message': f"{tier} tier has insufficient test coverage"
                })
        
        return gaps

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check real LLM coverage
        real_llm_percentage = (sum(1 for t in self.tests if t.uses_real_llm) / max(len(self.tests), 1)) * 100
        if real_llm_percentage < 60:
            recommendations.append(
                f"Increase real LLM test coverage from {real_llm_percentage:.1f}% to target 85%"
            )
        
        # Check E2E coverage
        e2e_percentage = (sum(1 for t in self.tests if t.is_e2e) / max(len(self.tests), 1)) * 100
        if e2e_percentage < 45:
            recommendations.append(
                f"Add more end-to-end tests (current: {e2e_percentage:.1f}%, target: 75%)"
            )
        
        # Check critical components
        critical_components = ['authentication', 'agent_orchestration', 'websocket']
        for comp in critical_components:
            if comp in self.coverage_by_component:
                coverage = self.coverage_by_component[comp]
                if coverage.total_tests < 50:
                    recommendations.append(
                        f"Increase test coverage for critical component '{comp}' (current: {coverage.total_tests} tests)"
                    )
        
        return recommendations

    def save_report(self, output_path: Optional[Path] = None) -> None:
        """Save the report to a JSON file"""
        if output_path is None:
            output_path = self.project_root / 'test_reports' / 'business_value_coverage.json'
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = self.generate_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Business value test coverage report saved to {output_path}")

    def print_summary(self) -> None:
        """Print a summary of the coverage analysis"""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("BUSINESS VALUE TEST COVERAGE SUMMARY")
        print("="*80)
        
        print(f"\nTotal Tests: {report['metadata']['total_tests']}")
        print(f"Average Business Value Score: {report['metadata']['average_value_score']:.1f}")
        
        print("\nTIER COVERAGE:")
        for tier, data in report['tier_coverage'].items():
            print(f"  {tier.upper()}: {data['total_tests']} tests, "
                  f"avg score: {data['average_value_score']:.1f}")
        
        print("\nQUALITY METRICS:")
        metrics = report['quality_metrics']
        print(f"  Real LLM Coverage: {metrics['real_llm_coverage']:.1f}%")
        print(f"  E2E Coverage: {metrics['e2e_coverage']:.1f}%")
        print(f"  Multi-Service Coverage: {metrics['multi_service_coverage']:.1f}%")
        print(f"  Critical Tests (90+ score): {metrics['critical_test_count']} "
              f"({metrics['critical_test_percentage']:.1f}%)")
        
        print("\nTOP VALUE TESTS:")
        for i, test in enumerate(report['top_value_tests'][:5], 1):
            print(f"  {i}. {test['name'][:50]} (Score: {test['score']:.1f})")
        
        if report['coverage_gaps']:
            print("\nCRITICAL GAPS:")
            for gap in report['coverage_gaps'][:5]:
                if gap['severity'] in ['critical', 'high']:
                    print(f"  - {gap['message']}")
        
        if report['recommendations']:
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(report['recommendations'][:5], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*80)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Business Value Test Coverage Index')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--output', help='Output file path for the report')
    parser.add_argument('--format', choices=['json', 'html', 'summary'], default='summary',
                       help='Output format')
    
    args = parser.parse_args()
    
    indexer = BusinessValueTestIndexer(args.project_root)
    
    print("Scanning tests...")
    indexer.scan_tests()
    
    print("Aggregating coverage...")
    indexer.aggregate_coverage()
    
    print("Loading coverage data...")
    indexer.load_coverage_data()
    
    print("Loading test results...")
    indexer.load_test_results()
    
    if args.format == 'json':
        indexer.save_report(Path(args.output) if args.output else None)
    elif args.format == 'summary':
        indexer.print_summary()
        if args.output:
            indexer.save_report(Path(args.output))
    
    return 0

if __name__ == '__main__':
    sys.exit(main())