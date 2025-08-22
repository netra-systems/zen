#!/usr/bin/env python3
"""
Fake Test Detector - Identifies tests that provide no real value

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Platform/Internal - All customer tiers benefit from quality assurance
2. **Business Goal**: Platform Stability, Development Velocity, Risk Reduction
3. **Value Impact**: Eliminates false confidence from fake tests, improves real test coverage
4. **Strategic Impact**: Prevents system degradation from undetected issues, accelerates debugging
5. **Platform Stability**: Ensures tests actually validate functionality

This module implements comprehensive fake test detection following SPEC/testing.xml 
requirements. It identifies 7 types of fake tests through AST analysis:

1. Auto-pass flags (skip without reason, assert True)
2. Runner bypass (excluded tests, unexecuted markers)
3. Trivial assertions (constants, language features)
4. Mock-only tests (mocking system under test)
5. Tautological tests (circular logic)
6. Empty tests (no meaningful assertions)
7. Duplicate tests (redundant implementations)

Usage:
    detector = FakeTestDetector()
    results = detector.scan_directory("app/tests")
    report = detector.generate_report()
"""

import ast
import configparser
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class FakeTestResult:
    """Result of fake test detection for a single test"""
    test_file: str
    test_name: str
    test_type: str  # Function name or class::method
    fake_types: List[str]  # Types of fake patterns detected
    severity: str  # low, medium, high, critical
    line_number: int
    evidence: List[str]  # Specific evidence of fake patterns
    recommendation: str  # Suggested action
    confidence: float  # 0.0-1.0 confidence in detection


@dataclass
class FakeTestStats:
    """Statistics about fake tests detected"""
    total_tests_scanned: int = 0
    total_fake_tests: int = 0
    fake_by_type: Dict[str, int] = None
    fake_by_severity: Dict[str, int] = None
    files_with_fakes: int = 0
    
    def __post_init__(self):
        if self.fake_by_type is None:
            self.fake_by_type = {}
        if self.fake_by_severity is None:
            self.fake_by_severity = {}


class FakeTestDetector:
    """Detects fake tests that provide no real testing value"""
    
    # Fake test type definitions matching SPEC/testing.xml
    FAKE_TYPES = {
        'auto_pass_flags': {
            'description': 'Tests with flags/conditions that force them to pass',
            'severity': 'critical',
            'patterns': [
                r'@pytest\.mark\.skip(?!\([^)]*reason=)',  # Skip without reason
                r'if\s+False\s*:\s*pytest\.fail',         # Conditional fail
                r'assert\s+True(?:\s|$|#)',               # Assert True alone
                r'except\s*:\s*pass',                     # Silent exception catching
            ]
        },
        'runner_bypass': {
            'description': 'Tests bypassed by test runners',
            'severity': 'high',
            'patterns': []  # Requires config analysis
        },
        'trivial_assertions': {
            'description': 'Tests that don\'t test significant functionality',
            'severity': 'medium',
            'patterns': [
                r'assert\s+\w+\s*==\s*["\'][^"\']+["\']',  # Constant assertions
                r'assert\s+1\s*\+\s*1\s*==\s*2',          # Math facts
                r'assert\s+isinstance\([^,]+,\s*\w+\)$',   # Simple type checks
            ]
        },
        'mock_only_tests': {
            'description': 'Tests that only test mocks, not functionality',
            'severity': 'high',
            'patterns': [
                r'mock\.called',                           # Testing mock.called
                r'assert_called_once\(\)',                # Mock call assertions only
                r'patch\(["\'][^"\']*["\'].*test_[^(]*$',  # Mocking system under test
            ]
        },
        'tautological_tests': {
            'description': 'Tests that test their own test setup',
            'severity': 'medium',
            'patterns': [
                r'(\w+)\s*=.*assert.*\1',                 # Set then assert same
                r'assert\s+fixture',                     # Testing fixture setup
            ]
        },
        'empty_tests': {
            'description': 'Tests with no meaningful verification',
            'severity': 'critical',
            'patterns': [
                r'def\s+test_[^(]*\([^)]*\):\s*pass',     # Pass-only tests
                r'def\s+test_[^(]*\([^)]*\):\s*print',    # Print-only tests
                r'#\s*assert',                            # Commented assertions
            ]
        },
        'duplicate_tests': {
            'description': 'Tests duplicating other tests without value',
            'severity': 'low',
            'patterns': []  # Requires semantic analysis
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize fake test detector
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.results: List[FakeTestResult] = []
        self.stats = FakeTestStats()
        self.test_configs = self._load_test_configs()
        
    def _get_default_config_path(self) -> Path:
        """Get default configuration path"""
        return Path(__file__).parent.parent / "app" / "pytest.ini"
    
    def _load_test_configs(self) -> Dict[str, Any]:
        """Load test runner configurations"""
        configs = {}
        
        # Load pytest.ini
        if self.config_path.exists():
            try:
                parser = configparser.ConfigParser()
                parser.read(self.config_path)
                configs['pytest'] = dict(parser['pytest']) if 'pytest' in parser else {}
            except Exception as e:
                logger.warning(f"Could not load pytest config: {e}")
                configs['pytest'] = {}
        
        return configs
    
    def scan_file(self, file_path: Path) -> List[FakeTestResult]:
        """Scan a single test file for fake tests
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of fake test results found in file
        """
        if not file_path.name.startswith('test_') or not file_path.suffix == '.py':
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse AST for deep analysis
            try:
                tree = ast.parse(content)
                return self._analyze_ast(tree, file_path, content)
            except SyntaxError:
                logger.warning(f"Could not parse {file_path}: syntax error")
                # Fallback to regex-based analysis
                return self._analyze_content(content, file_path)
                
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            return []
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, content: str) -> List[FakeTestResult]:
        """Analyze AST for fake test patterns
        
        Args:
            tree: Parsed AST
            file_path: File being analyzed
            content: Original file content for line numbers
            
        Returns:
            List of fake test results
        """
        results = []
        lines = content.split('\n')
        
        class TestVisitor(ast.NodeVisitor):
            def __init__(self, detector):
                self.detector = detector
                self.current_class = None
                self.imports = set()
                self.patches = set()
                
            def visit_Import(self, node):
                for alias in node.names:
                    self.imports.add(alias.name)
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module:
                    for alias in node.names:
                        self.imports.add(f"{node.module}.{alias.name}")
                self.generic_visit(node)
            
            def visit_ClassDef(self, node):
                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class
            
            def visit_FunctionDef(self, node):
                if node.name.startswith('test_'):
                    test_name = f"{self.current_class}::{node.name}" if self.current_class else node.name
                    fake_patterns = self.detector._analyze_test_function(
                        node, lines, test_name, str(file_path), self.imports, self.patches
                    )
                    if fake_patterns:
                        results.extend(fake_patterns)
                
                self.generic_visit(node)
        
        visitor = TestVisitor(self)
        visitor.visit(tree)
        
        return results
    
    def _analyze_test_function(self, node: ast.FunctionDef, lines: List[str], 
                             test_name: str, file_path: str, imports: Set[str],
                             patches: Set[str]) -> List[FakeTestResult]:
        """Analyze individual test function for fake patterns
        
        Args:
            node: AST node for test function
            lines: File lines for context
            test_name: Name of test function
            file_path: Path to test file
            imports: Set of imported modules
            patches: Set of patched modules
            
        Returns:
            List of fake test results for this function
        """
        results = []
        fake_types = []
        evidence = []
        
        # Get function body as text
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
        function_text = '\n'.join(lines[start_line:min(end_line, len(lines))])
        
        # Check for empty tests
        if self._is_empty_test(node, function_text):
            fake_types.append('empty_tests')
            evidence.append('Function contains no meaningful assertions')
        
        # Check for auto-pass flags
        auto_pass_evidence = self._check_auto_pass_flags(node, function_text, lines, start_line)
        if auto_pass_evidence:
            fake_types.append('auto_pass_flags')
            evidence.extend(auto_pass_evidence)
        
        # Check for trivial assertions
        trivial_evidence = self._check_trivial_assertions(node, function_text)
        if trivial_evidence:
            fake_types.append('trivial_assertions')
            evidence.extend(trivial_evidence)
        
        # Check for mock-only patterns
        mock_evidence = self._check_mock_only_patterns(node, function_text, imports)
        if mock_evidence:
            fake_types.append('mock_only_tests')
            evidence.extend(mock_evidence)
        
        # Check for tautological patterns
        tautology_evidence = self._check_tautological_patterns(node, function_text)
        if tautology_evidence:
            fake_types.append('tautological_tests')
            evidence.extend(tautology_evidence)
        
        if fake_types:
            severity = self._calculate_severity(fake_types)
            confidence = self._calculate_confidence(fake_types, evidence)
            recommendation = self._get_recommendation(fake_types, evidence)
            
            result = FakeTestResult(
                test_file=file_path,
                test_name=test_name,
                test_type='function',
                fake_types=fake_types,
                severity=severity,
                line_number=node.lineno,
                evidence=evidence,
                recommendation=recommendation,
                confidence=confidence
            )
            results.append(result)
        
        return results
    
    def _is_empty_test(self, node: ast.FunctionDef, function_text: str) -> bool:
        """Check if test function is empty or trivial"""
        # Check for pass-only functions
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            return True
        
        # Check for functions with only docstrings
        if (len(node.body) == 1 and isinstance(node.body[0], ast.Expr) 
            and isinstance(node.body[0].value, ast.Constant)):
            return True
        
        # Check for functions with only comments/prints
        meaningful_lines = []
        for line in function_text.split('\n')[1:]:  # Skip def line
            stripped = line.strip()
            if (stripped and not stripped.startswith('#') 
                and not stripped.startswith('"""') 
                and not stripped.startswith("'''")
                and 'print(' not in stripped):
                meaningful_lines.append(stripped)
        
        return len(meaningful_lines) == 0
    
    def _check_auto_pass_flags(self, node: ast.FunctionDef, function_text: str, 
                             lines: List[str], start_line: int) -> List[str]:
        """Check for auto-pass flag patterns"""
        evidence = []
        
        # Check decorators for skip without reason
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if (decorator.attr == 'skip' and 
                    isinstance(decorator.value, ast.Attribute) and
                    decorator.value.attr == 'mark'):
                    # Check if reason is provided
                    decorator_line = lines[decorator.lineno - 1]
                    if 'reason=' not in decorator_line:
                        evidence.append(f"@pytest.mark.skip without reason at line {decorator.lineno}")
            elif isinstance(decorator, ast.Call):
                if (isinstance(decorator.func, ast.Attribute) and
                    decorator.func.attr == 'skip' and
                    isinstance(decorator.func.value, ast.Attribute) and
                    decorator.func.value.attr == 'mark'):
                    # Check arguments for reason
                    has_reason = any(
                        (isinstance(kw, ast.keyword) and kw.arg == 'reason')
                        for kw in decorator.keywords
                    )
                    if not has_reason:
                        evidence.append(f"@pytest.mark.skip without reason at line {decorator.lineno}")
        
        # Check for assert True patterns
        if re.search(r'assert\s+True(?:\s|$|#)', function_text):
            # Check if it's meaningful (part of larger assertion)
            assert_lines = [line for line in function_text.split('\n') 
                          if 'assert True' in line]
            for line in assert_lines:
                if line.strip() == 'assert True' or line.strip().startswith('assert True #'):
                    evidence.append(f"Standalone 'assert True' found")
        
        # Check for silent exception handling
        if 'except:' in function_text and 'pass' in function_text:
            evidence.append("Silent exception handling (except: pass)")
        
        return evidence
    
    def _check_trivial_assertions(self, node: ast.FunctionDef, function_text: str) -> List[str]:
        """Check for trivial assertion patterns"""
        evidence = []
        
        # Look for constant assertions
        constant_patterns = [
            r'assert\s+\w+\s*==\s*["\'][^"\']+["\']',  # String constants
            r'assert\s+\w+\s*==\s*\d+',                # Number constants
            r'assert\s+1\s*\+\s*1\s*==\s*2',          # Math facts
            r'assert\s+True\s*==\s*True',              # Tautologies
        ]
        
        for pattern in constant_patterns:
            if re.search(pattern, function_text):
                evidence.append(f"Trivial assertion pattern: {pattern}")
        
        # Check for simple type checks without context
        if re.search(r'assert\s+isinstance\([^,]+,\s*\w+\)\s*$', function_text, re.MULTILINE):
            # Check if it's the only assertion
            assert_count = len(re.findall(r'assert\s+', function_text))
            if assert_count == 1:
                evidence.append("Single isinstance assertion without context")
        
        return evidence
    
    def _check_mock_only_patterns(self, node: ast.FunctionDef, function_text: str, 
                                imports: Set[str]) -> List[str]:
        """Check for mock-only test patterns"""
        evidence = []
        
        # Count mock usage vs real testing
        mock_indicators = [
            'mock.called', 'assert_called_once', 'assert_called_with',
            'Mock()', '@patch', 'MagicMock', '.called', '.call_count'
        ]
        
        mock_count = sum(function_text.count(indicator) for indicator in mock_indicators)
        total_lines = len([line for line in function_text.split('\n') if line.strip()])
        
        # If more than 70% of content is mock-related
        if total_lines > 0 and mock_count / total_lines > 0.7:
            evidence.append(f"High mock density: {mock_count} mock indicators in {total_lines} lines")
        
        # Check for mocking the system under test
        system_mock_patterns = [
            r'@patch\(["\']app\.',        # Patching app modules
            r'Mock\(\).*=.*app\.',        # Mocking app components
        ]
        
        for pattern in system_mock_patterns:
            if re.search(pattern, function_text):
                evidence.append(f"Mocking system under test: {pattern}")
        
        # Check for testing only mock behavior
        if 'mock.called' in function_text and 'assert' not in function_text.replace('assert_called', ''):
            evidence.append("Testing only mock.called without behavior verification")
        
        return evidence
    
    def _check_tautological_patterns(self, node: ast.FunctionDef, function_text: str) -> List[str]:
        """Check for tautological test patterns"""
        evidence = []
        
        # Look for set-then-assert patterns
        lines = function_text.split('\n')
        variables_set = set()
        
        for line in lines:
            # Find variable assignments
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    if var_name.isidentifier():
                        variables_set.add(var_name)
        
        # Check if assertions use the same variables
        for line in lines:
            if 'assert' in line:
                for var in variables_set:
                    if var in line and f"{var} ==" in line.replace(' ', ''):
                        evidence.append(f"Tautological pattern: variable '{var}' set then asserted")
        
        # Check for fixture testing
        if 'assert fixture' in function_text.lower():
            evidence.append("Testing fixture setup instead of application logic")
        
        # Check for circular logic patterns
        circular_patterns = [
            r'(\w+)\s*=.*\1',  # var = something with var
            r'assert\s+(\w+)\s*==\s*\1',  # assert var == var
        ]
        
        for pattern in circular_patterns:
            matches = re.finditer(pattern, function_text)
            for match in matches:
                evidence.append(f"Circular logic pattern: {match.group()}")
        
        return evidence
    
    def _calculate_severity(self, fake_types: List[str]) -> str:
        """Calculate severity based on fake types detected"""
        severity_scores = {
            'empty_tests': 4,      # Critical
            'auto_pass_flags': 4,  # Critical  
            'mock_only_tests': 3,  # High
            'runner_bypass': 3,    # High
            'trivial_assertions': 2,  # Medium
            'tautological_tests': 2,  # Medium
            'duplicate_tests': 1,     # Low
        }
        
        max_score = max((severity_scores.get(ft, 1) for ft in fake_types), default=1)
        
        if max_score >= 4:
            return 'critical'
        elif max_score >= 3:
            return 'high'
        elif max_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_confidence(self, fake_types: List[str], evidence: List[str]) -> float:
        """Calculate confidence in fake test detection"""
        base_confidence = 0.5
        
        # Higher confidence for clear patterns
        confidence_boosts = {
            'empty_tests': 0.4,
            'auto_pass_flags': 0.3,
            'mock_only_tests': 0.2,
            'trivial_assertions': 0.2,
            'tautological_tests': 0.1,
        }
        
        total_boost = sum(confidence_boosts.get(ft, 0.1) for ft in fake_types)
        evidence_boost = min(len(evidence) * 0.05, 0.2)  # Evidence adds confidence
        
        return min(base_confidence + total_boost + evidence_boost, 1.0)
    
    def _get_recommendation(self, fake_types: List[str], evidence: List[str]) -> str:
        """Get recommendation for remediation"""
        if 'empty_tests' in fake_types:
            return "Remove this test or implement meaningful assertions"
        elif 'auto_pass_flags' in fake_types:
            return "Remove skip decorator and implement proper test logic"
        elif 'mock_only_tests' in fake_types:
            return "Reduce mocking and test actual component behavior"
        elif 'trivial_assertions' in fake_types:
            return "Replace with assertions that test real business logic"
        elif 'tautological_tests' in fake_types:
            return "Refactor to test actual functionality, not test setup"
        else:
            return "Review test implementation for actual value provided"
    
    def _analyze_content(self, content: str, file_path: Path) -> List[FakeTestResult]:
        """Fallback regex-based analysis when AST parsing fails"""
        results = []
        lines = content.split('\n')
        
        # Find test functions with regex
        test_pattern = r'^(\s*)def\s+(test_\w+)\s*\('
        
        for i, line in enumerate(lines):
            match = re.match(test_pattern, line)
            if match:
                test_name = match.group(2)
                
                # Extract function body (simplified)
                indent_level = len(match.group(1))
                function_lines = [line]
                
                for j in range(i + 1, len(lines)):
                    if (lines[j].strip() == '' or 
                        lines[j].startswith(' ' * (indent_level + 4)) or
                        lines[j].strip().startswith('#')):
                        function_lines.append(lines[j])
                    else:
                        break
                
                function_text = '\n'.join(function_lines)
                
                # Apply basic pattern matching
                fake_types = []
                evidence = []
                
                # Check basic patterns
                for fake_type, config in self.FAKE_TYPES.items():
                    for pattern in config['patterns']:
                        if re.search(pattern, function_text, re.IGNORECASE):
                            fake_types.append(fake_type)
                            evidence.append(f"Pattern match: {pattern}")
                
                if fake_types:
                    result = FakeTestResult(
                        test_file=str(file_path),
                        test_name=test_name,
                        test_type='function',
                        fake_types=fake_types,
                        severity=self._calculate_severity(fake_types),
                        line_number=i + 1,
                        evidence=evidence,
                        recommendation=self._get_recommendation(fake_types, evidence),
                        confidence=0.6  # Lower confidence for regex-only analysis
                    )
                    results.append(result)
        
        return results
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> List[FakeTestResult]:
        """Scan directory for fake tests
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of all fake test results found
        """
        all_results = []
        
        pattern = "**/*.py" if recursive else "*.py"
        
        for file_path in directory.glob(pattern):
            if file_path.name.startswith('test_'):
                results = self.scan_file(file_path)
                all_results.extend(results)
                self.stats.total_tests_scanned += 1
        
        self.results.extend(all_results)
        self._update_stats()
        
        return all_results
    
    def _update_stats(self):
        """Update detection statistics"""
        self.stats.total_fake_tests = len(self.results)
        
        # Count by type
        type_counts = Counter()
        severity_counts = Counter()
        files_with_fakes = set()
        
        for result in self.results:
            for fake_type in result.fake_types:
                type_counts[fake_type] += 1
            severity_counts[result.severity] += 1
            files_with_fakes.add(result.test_file)
        
        self.stats.fake_by_type = dict(type_counts)
        self.stats.fake_by_severity = dict(severity_counts)
        self.stats.files_with_fakes = len(files_with_fakes)
    
    def generate_report(self, output_format: str = 'text') -> str:
        """Generate comprehensive fake test report
        
        Args:
            output_format: Format for report ('text', 'json', 'html')
            
        Returns:
            Formatted report string
        """
        if output_format == 'json':
            return self._generate_json_report()
        elif output_format == 'html':
            return self._generate_html_report()
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate text format report"""
        lines = [
            "=" * 80,
            "FAKE TEST DETECTION REPORT",
            "=" * 80,
            f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Tests Scanned: {self.stats.total_tests_scanned}",
            f"Total Fake Tests Found: {self.stats.total_fake_tests}",
            f"Files with Fake Tests: {self.stats.files_with_fakes}",
            ""
        ]
        
        # Summary by type
        if self.stats.fake_by_type:
            lines.extend([
                "FAKE TESTS BY TYPE:",
                "-" * 40
            ])
            for fake_type, count in sorted(self.stats.fake_by_type.items()):
                description = self.FAKE_TYPES.get(fake_type, {}).get('description', fake_type)
                lines.append(f"  {fake_type}: {count} ({description})")
            lines.append("")
        
        # Summary by severity
        if self.stats.fake_by_severity:
            lines.extend([
                "FAKE TESTS BY SEVERITY:",
                "-" * 40
            ])
            severity_order = ['critical', 'high', 'medium', 'low']
            for severity in severity_order:
                if severity in self.stats.fake_by_severity:
                    count = self.stats.fake_by_severity[severity]
                    lines.append(f"  {severity.upper()}: {count}")
            lines.append("")
        
        # Detailed results
        if self.results:
            lines.extend([
                "DETAILED RESULTS:",
                "=" * 40
            ])
            
            # Group by severity
            by_severity = defaultdict(list)
            for result in self.results:
                by_severity[result.severity].append(result)
            
            for severity in ['critical', 'high', 'medium', 'low']:
                results_for_severity = by_severity.get(severity, [])
                if results_for_severity:
                    lines.extend([
                        f"\n{severity.upper()} SEVERITY ({len(results_for_severity)} tests):",
                        "-" * 40
                    ])
                    
                    for result in results_for_severity:
                        lines.extend([
                            f"\nFile: {result.test_file}",
                            f"Test: {result.test_name}",
                            f"Line: {result.line_number}",
                            f"Types: {', '.join(result.fake_types)}",
                            f"Confidence: {result.confidence:.2f}",
                            f"Recommendation: {result.recommendation}",
                            "Evidence:"
                        ])
                        for evidence in result.evidence:
                            lines.append(f"  - {evidence}")
        
        # Recommendations
        lines.extend([
            "\n" + "=" * 40,
            "RECOMMENDATIONS:",
            "=" * 40,
            "1. Remove or fix CRITICAL fake tests immediately",
            "2. Address HIGH severity fake tests in current sprint", 
            "3. Schedule MEDIUM/LOW severity fixes for technical debt",
            "4. Run fake test detection in CI to prevent regressions",
            "5. Use examples from test_real_functionality_examples.py",
            "\nFor detailed guidance, see:",
            "- SPEC/testing.xml (fake_test_detection section)",
            "- app/tests/examples/test_real_functionality_examples.py",
            "- CLAUDE.md (Testing best practices)",
            "\n" + "=" * 80
        ])
        
        return "\n".join(lines)
    
    def _generate_json_report(self) -> str:
        """Generate JSON format report"""
        report_data = {
            "scan_date": datetime.now().isoformat(),
            "stats": asdict(self.stats),
            "results": [asdict(result) for result in self.results],
            "fake_type_definitions": self.FAKE_TYPES
        }
        
        return json.dumps(report_data, indent=2, default=str)
    
    def _generate_html_report(self) -> str:
        """Generate HTML format report"""
        # Simplified HTML report - could be enhanced with templates
        html_parts = [
            "<html><head><title>Fake Test Detection Report</title>",
            "<style>body{font-family:Arial;margin:20px;} ",
            ".critical{color:red;} .high{color:orange;} .medium{color:blue;} .low{color:green;}</style>",
            "</head><body>",
            f"<h1>Fake Test Detection Report</h1>",
            f"<p>Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p>Total Tests Scanned: {self.stats.total_tests_scanned}</p>",
            f"<p>Total Fake Tests: {self.stats.total_fake_tests}</p>",
            "<h2>Results by Severity</h2><ul>"
        ]
        
        # Group by severity for HTML
        by_severity = defaultdict(list)
        for result in self.results:
            by_severity[result.severity].append(result)
        
        for severity in ['critical', 'high', 'medium', 'low']:
            results_for_severity = by_severity.get(severity, [])
            if results_for_severity:
                html_parts.append(f'<li class="{severity}">{severity.upper()}: {len(results_for_severity)}</li>')
        
        html_parts.extend(["</ul>", "</body></html>"])
        
        return "".join(html_parts)
    
    def save_report(self, output_path: Path, format: str = 'text'):
        """Save report to file
        
        Args:
            output_path: Path to save report
            format: Report format ('text', 'json', 'html')
        """
        report_content = self.generate_report(format)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Fake test report saved to {output_path}")
        except Exception as e:
            logger.error(f"Could not save report to {output_path}: {e}")
    
    def get_fake_tests_by_file(self, file_path: str) -> List[FakeTestResult]:
        """Get fake tests for specific file"""
        return [result for result in self.results if result.test_file == file_path]
    
    def get_fake_tests_by_type(self, fake_type: str) -> List[FakeTestResult]:
        """Get fake tests of specific type"""
        return [result for result in self.results if fake_type in result.fake_types]
    
    def get_fake_tests_by_severity(self, severity: str) -> List[FakeTestResult]:
        """Get fake tests of specific severity"""
        return [result for result in self.results if result.severity == severity]
    
    def clear_results(self):
        """Clear all detection results"""
        self.results.clear()
        self.stats = FakeTestStats()


def main():
    """Command line interface for fake test detection"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Detect fake tests in codebase')
    parser.add_argument('directory', help='Directory to scan')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'html'], 
                       default='text', help='Output format')
    parser.add_argument('--recursive', '-r', action='store_true', 
                       help='Scan recursively')
    
    args = parser.parse_args()
    
    detector = FakeTestDetector()
    results = detector.scan_directory(Path(args.directory), args.recursive)
    
    print(f"Found {len(results)} fake tests")
    
    if args.output:
        detector.save_report(Path(args.output), args.format)
    else:
        print(detector.generate_report(args.format))


if __name__ == "__main__":
    main()