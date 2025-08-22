"""Unified Test Quality Analyzer - Detects bad tests, fake tests, and circular imports.

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Platform/Internal - All customer tiers benefit from quality assurance
2. **Business Goal**: Platform Stability, Development Velocity, Risk Reduction
3. **Value Impact**: Eliminates false confidence from fake tests, improves real test coverage
4. **Strategic Impact**: Prevents system degradation from undetected issues, accelerates debugging

This module consolidates:
- Bad test detection (consistently failing tests)
- Fake test detection (tests providing no real value)
- Circular import detection (import dependency issues)
"""

import ast
import json
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class TestQualityIssue:
    """Represents a test quality issue"""
    test_file: str
    test_name: str
    issue_type: str  # 'bad', 'fake', 'circular_import'
    severity: str    # 'critical', 'high', 'medium', 'low'
    description: str
    recommendation: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any]


class TestQualityAnalyzer:
    """Unified analyzer for test quality issues."""
    
    def __init__(self, data_file: Path = None):
        """Initialize the test quality analyzer.
        
        Args:
            data_file: Path to persist analysis data
        """
        self.data_file = data_file or self._get_default_data_file()
        self.analysis_data = self._load_analysis_data()
        self.current_run_id = self._generate_run_id()
        
        # Bad test tracking
        self.failure_data = self.analysis_data.get('bad_tests', {})
        self.current_run_failures = defaultdict(list)
        
        # Fake test patterns
        self.fake_test_patterns = self._init_fake_test_patterns()
        
        # Circular import tracking
        self.import_graph = defaultdict(set)
        
    def _get_default_data_file(self) -> Path:
        """Get default data file path."""
        reports_dir = Path(__file__).parent.parent / "test_reports"
        reports_dir.mkdir(exist_ok=True)
        return reports_dir / "test_quality_analysis.json"
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 100000}"
    
    def _load_analysis_data(self) -> Dict:
        """Load existing analysis data from file."""
        if not self.data_file.exists():
            return self._create_empty_data_structure()
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._create_empty_data_structure()
    
    def _create_empty_data_structure(self) -> Dict:
        """Create empty data structure."""
        return {
            'bad_tests': {},
            'fake_tests': {},
            'circular_imports': {},
            'runs': {},
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
    
    def _init_fake_test_patterns(self) -> Dict:
        """Initialize fake test detection patterns."""
        return {
            'auto_pass': [
                r'assert\s+True',
                r'assert\s+1\s*==\s*1',
                r'assert\s+".*"\s*==\s*".*"',  # Same string comparison
                r'pass\s*#.*TODO',
                r'pytest\.skip\(\s*\)',
            ],
            'mock_only': [
                r'mock\.',
                r'@mock\.',
                r'Mock\(',
                r'MagicMock\(',
            ],
            'trivial': [
                r'assert\s+isinstance\(',
                r'assert\s+hasattr\(',
                r'assert\s+len\(',
            ]
        }
    
    # BAD TEST DETECTION
    def record_test_failure(self, test_name: str, failure_reason: str, test_file: str = None):
        """Record a test failure for bad test analysis."""
        test_key = self._normalize_test_name(test_name)
        
        if test_key not in self.failure_data:
            self.failure_data[test_key] = {
                'test_name': test_name,
                'test_file': test_file,
                'failure_count': 0,
                'first_failure': None,
                'last_failure': None,
                'failure_reasons': [],
                'runs': []
            }
        
        failure_entry = {
            'run_id': self.current_run_id,
            'timestamp': datetime.now().isoformat(),
            'reason': failure_reason
        }
        
        test_data = self.failure_data[test_key]
        test_data['failure_count'] += 1
        test_data['last_failure'] = failure_entry['timestamp']
        test_data['failure_reasons'].append(failure_reason)
        test_data['runs'].append(failure_entry)
        
        if test_data['first_failure'] is None:
            test_data['first_failure'] = failure_entry['timestamp']
        
        self.current_run_failures[test_key].append(failure_entry)
    
    def get_bad_tests(self, min_failures: int = 3, max_age_days: int = 30) -> List[TestQualityIssue]:
        """Get tests that consistently fail."""
        bad_tests = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for test_key, data in self.failure_data.items():
            if data['failure_count'] >= min_failures:
                last_failure = datetime.fromisoformat(data['last_failure'])
                if last_failure >= cutoff_date:
                    issue = TestQualityIssue(
                        test_file=data.get('test_file', 'unknown'),
                        test_name=data['test_name'],
                        issue_type='bad',
                        severity='high' if data['failure_count'] >= 5 else 'medium',
                        description=f"Test has failed {data['failure_count']} times",
                        recommendation="Investigate and fix or remove this test",
                        confidence=min(0.95, data['failure_count'] / 10),
                        metadata={
                            'failure_count': data['failure_count'],
                            'last_failure': data['last_failure'],
                            'failure_reasons': data['failure_reasons'][-3:]  # Last 3 reasons
                        }
                    )
                    bad_tests.append(issue)
        
        return sorted(bad_tests, key=lambda x: x.metadata['failure_count'], reverse=True)
    
    # FAKE TEST DETECTION
    def analyze_fake_tests(self, test_directory: Path) -> List[TestQualityIssue]:
        """Analyze directory for fake tests."""
        fake_tests = []
        
        for test_file in test_directory.rglob("test_*.py"):
            try:
                issues = self._analyze_test_file(test_file)
                fake_tests.extend(issues)
            except Exception as e:
                logger.warning(f"Failed to analyze {test_file}: {e}")
        
        return fake_tests
    
    def _analyze_test_file(self, test_file: Path) -> List[TestQualityIssue]:
        """Analyze a single test file for fake tests."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analyzer = FakeTestVisitor(test_file, self.fake_test_patterns)
            analyzer.visit(tree)
            return analyzer.get_issues()
        
        except Exception as e:
            logger.error(f"Error parsing {test_file}: {e}")
            return []
    
    # CIRCULAR IMPORT DETECTION
    def detect_circular_imports(self, root_directory: Path) -> List[TestQualityIssue]:
        """Detect circular import dependencies."""
        self._build_import_graph(root_directory)
        cycles = self._find_cycles()
        
        issues = []
        for cycle in cycles:
            issue = TestQualityIssue(
                test_file=cycle[0] if cycle else 'unknown',
                test_name='circular_import',
                issue_type='circular_import',
                severity='high',
                description=f"Circular import detected: {' -> '.join(cycle)}",
                recommendation="Refactor imports to remove circular dependency",
                confidence=0.9,
                metadata={'cycle': cycle}
            )
            issues.append(issue)
        
        return issues
    
    def _build_import_graph(self, root_directory: Path):
        """Build import dependency graph."""
        for py_file in root_directory.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                file_path = str(py_file.relative_to(root_directory))
                imports = self._extract_imports(tree)
                self.import_graph[file_path].update(imports)
                
            except Exception as e:
                logger.warning(f"Failed to analyze imports in {py_file}: {e}")
    
    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """Extract import statements from AST."""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        
        return imports
    
    def _find_cycles(self) -> List[List[str]]:
        """Find cycles in import graph using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.import_graph.get(node, []):
                if dfs(neighbor, path + [node]):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.import_graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    # UNIFIED ANALYSIS
    def analyze_all(self, test_directory: Path) -> Dict[str, List[TestQualityIssue]]:
        """Run all quality analyses."""
        results = {
            'bad_tests': self.get_bad_tests(),
            'fake_tests': self.analyze_fake_tests(test_directory),
            'circular_imports': self.detect_circular_imports(test_directory)
        }
        
        # Save analysis data
        self._save_analysis_data()
        
        return results
    
    def generate_quality_report(self, results: Dict[str, List[TestQualityIssue]]) -> str:
        """Generate comprehensive quality report."""
        report = ["# Test Quality Analysis Report", ""]
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Run ID: {self.current_run_id}")
        report.append("")
        
        total_issues = sum(len(issues) for issues in results.values())
        report.append(f"## Summary: {total_issues} total issues found")
        report.append("")
        
        for category, issues in results.items():
            if issues:
                report.append(f"### {category.replace('_', ' ').title()} ({len(issues)} issues)")
                report.append("")
                
                for issue in issues[:10]:  # Top 10 per category
                    report.append(f"- **{issue.test_name}** ({issue.severity})")
                    report.append(f"  - File: {issue.test_file}")
                    report.append(f"  - Issue: {issue.description}")
                    report.append(f"  - Recommendation: {issue.recommendation}")
                    report.append("")
                
                if len(issues) > 10:
                    report.append(f"... and {len(issues) - 10} more issues")
                    report.append("")
        
        return "\n".join(report)
    
    def _save_analysis_data(self):
        """Save analysis data to file."""
        self.analysis_data['bad_tests'] = self.failure_data
        self.analysis_data['last_updated'] = datetime.now().isoformat()
        self.analysis_data['runs'][self.current_run_id] = {
            'timestamp': datetime.now().isoformat(),
            'failures': dict(self.current_run_failures)
        }
        
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save analysis data: {e}")
    
    def _normalize_test_name(self, test_name: str) -> str:
        """Normalize test name for consistent tracking."""
        return test_name.strip().replace(' ', '_').lower()


class FakeTestVisitor(ast.NodeVisitor):
    """AST visitor for detecting fake tests."""
    
    def __init__(self, test_file: Path, patterns: Dict):
        self.test_file = test_file
        self.patterns = patterns
        self.issues = []
        self.current_function = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        if node.name.startswith('test_'):
            self.current_function = node.name
            self._analyze_test_function(node)
        self.generic_visit(node)
    
    def _analyze_test_function(self, node: ast.FunctionDef):
        """Analyze a test function for fake test patterns."""
        source = ast.get_source_segment(open(self.test_file).read(), node)
        if not source:
            return
        
        # Check for auto-pass patterns
        for pattern in self.patterns['auto_pass']:
            if any(pattern in line for line in source.split('\n')):
                self.issues.append(TestQualityIssue(
                    test_file=str(self.test_file),
                    test_name=node.name,
                    issue_type='fake',
                    severity='high',
                    description="Test contains auto-pass pattern",
                    recommendation="Add meaningful assertions",
                    confidence=0.8,
                    metadata={'pattern': pattern, 'type': 'auto_pass'}
                ))
                break
        
        # Check for mock-only tests
        mock_count = sum(1 for pattern in self.patterns['mock_only'] 
                        for line in source.split('\n') if pattern in line)
        assert_count = source.count('assert')
        
        if mock_count > 0 and assert_count == 0:
            self.issues.append(TestQualityIssue(
                test_file=str(self.test_file),
                test_name=node.name,
                issue_type='fake',
                severity='medium',
                description="Test only contains mocks without assertions",
                recommendation="Add assertions to verify behavior",
                confidence=0.7,
                metadata={'mock_count': mock_count, 'type': 'mock_only'}
            ))
    
    def get_issues(self) -> List[TestQualityIssue]:
        """Get detected issues."""
        return self.issues