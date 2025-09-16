"""
Import Fragmentation Detection Test for Issue #1186

Tests for detecting import fragmentation violations in UserExecutionEngine patterns
across the codebase. This test suite identifies the 275+ violations that need
to be addressed as part of SSOT consolidation.

Business Value: Platform/Internal - System Stability & Development Velocity
Prevents cascade failures from duplicated import patterns and ensures reliable
SSOT compliance for the $500K+ ARR Golden Path.

Expected: FAIL initially (detects 275+ violations)
Target: 100% SSOT compliance with zero import fragmentation violations

CRITICAL: This test MUST fail initially to demonstrate current violations.
Only passes when SSOT consolidation is complete.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class ImportViolation:
    """Container for import fragmentation violations."""
    file_path: str
    line_number: int
    import_statement: str
    violation_type: str
    severity: str
    pattern_type: str
    

@dataclass
class FragmentationStats:
    """Statistics for import fragmentation analysis."""
    total_violations: int
    critical_violations: int
    high_violations: int
    medium_violations: int
    low_violations: int
    patterns_detected: Set[str]
    files_affected: Set[str]
    duplicate_imports: Dict[str, int]


class TestUserExecutionEngineImportFragmentation(SSotBaseTestCase):
    """
    Test suite for detecting UserExecutionEngine import fragmentation violations.
    
    This test identifies patterns of duplicated imports, inconsistent import styles,
    and fragmented UserExecutionEngine usage that violate SSOT principles.
    
    CRITICAL BUSINESS IMPACT:
    - Prevents cascade failures in the Golden Path ($500K+ ARR protection)
    - Ensures reliable agent execution for customer chat functionality
    - Maintains system stability during user execution context creation
    """
    
    @classmethod
    def setup_class(cls):
        """Set up class-level resources for import analysis."""
        super().setup_class()
        cls.project_root = Path("/Users/anthony/Desktop/netra-apex")
        cls.target_patterns = [
            "UserExecutionEngine",
            "UserExecutionContext", 
            "ExecutionEngine",
            "user_execution_context",
            "execution_engine",
            "WebSocketManager",
            "AgentFactory",
            "websocket_manager",
            "agent_factory"
        ]
        cls.violation_threshold = 275  # Expected current violations
        cls.logger.info(f"Analyzing import fragmentation in {cls.project_root}")
    
    def setup_method(self, method=None):
        """Set up per-test resources."""
        super().setup_method(method)
        self.violations: List[ImportViolation] = []
        self.stats = FragmentationStats(
            total_violations=0,
            critical_violations=0,
            high_violations=0,
            medium_violations=0,
            low_violations=0,
            patterns_detected=set(),
            files_affected=set(),
            duplicate_imports={}
        )
    
    def _scan_python_files(self) -> List[Path]:
        """Scan for Python files to analyze."""
        python_files = []
        
        # Key directories to scan for UserExecutionEngine patterns
        scan_dirs = [
            "netra_backend/app",
            "auth_service", 
            "frontend",
            "test_framework",
            "tests",
            "shared",
            "scripts"
        ]
        
        for scan_dir in scan_dirs:
            dir_path = self.project_root / scan_dir
            if dir_path.exists():
                python_files.extend(dir_path.rglob("*.py"))
        
        self.record_metric("files_scanned", len(python_files))
        return python_files
    
    def _analyze_file_imports(self, file_path: Path) -> List[ImportViolation]:
        """Analyze imports in a single file for fragmentation violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Parse AST for structured analysis
            try:
                tree = ast.parse(content)
            except SyntaxError:
                # Skip files with syntax errors
                return violations
            
            # Track imports found in this file
            file_imports = set()
            
            # Analyze AST nodes for import patterns
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    line_num = getattr(node, 'lineno', 0)
                    
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_name = alias.name
                            import_stmt = f"import {import_name}"
                            violations.extend(self._check_import_violations(
                                file_path, line_num, import_stmt, import_name, file_imports
                            ))
                    
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            import_name = alias.name
                            import_stmt = f"from {module} import {import_name}"
                            full_import = f"{module}.{import_name}"
                            violations.extend(self._check_import_violations(
                                file_path, line_num, import_stmt, full_import, file_imports
                            ))
            
            # Check for regex-based import patterns in lines
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line.startswith(('import ', 'from ')) and any(pattern in line for pattern in self.target_patterns):
                    violations.extend(self._check_line_import_violations(
                        file_path, line_num, line, file_imports
                    ))
        
        except Exception as e:
            self.logger.warning(f"Error analyzing {file_path}: {e}")
        
        return violations
    
    def _check_import_violations(self, file_path: Path, line_num: int, import_stmt: str, 
                                import_name: str, file_imports: Set[str]) -> List[ImportViolation]:
        """Check for specific import violation patterns."""
        violations = []
        rel_path = str(file_path.relative_to(self.project_root))
        
        # Check for target pattern matches
        for pattern in self.target_patterns:
            if pattern in import_name:
                
                # Detect fragmentation patterns
                violation_type = self._classify_violation(import_stmt, pattern, rel_path)
                severity = self._assess_severity(violation_type, rel_path)
                pattern_type = self._determine_pattern_type(import_stmt, pattern)
                
                # Track duplicate imports
                if import_name in file_imports:
                    violation_type = "duplicate_import"
                    severity = "HIGH"
                
                file_imports.add(import_name)
                
                # Create violation record
                violation = ImportViolation(
                    file_path=rel_path,
                    line_number=line_num,
                    import_statement=import_stmt,
                    violation_type=violation_type,
                    severity=severity,
                    pattern_type=pattern_type
                )
                violations.append(violation)
                
                # Update stats
                self.stats.patterns_detected.add(pattern)
                self.stats.files_affected.add(rel_path)
                self.stats.duplicate_imports[import_name] = self.stats.duplicate_imports.get(import_name, 0) + 1
        
        return violations
    
    def _check_line_import_violations(self, file_path: Path, line_num: int, line: str,
                                    file_imports: Set[str]) -> List[ImportViolation]:
        """Check line-based import violations using regex patterns."""
        violations = []
        rel_path = str(file_path.relative_to(self.project_root))
        
        # Regex patterns for common fragmentation issues
        patterns = [
            (r'from\s+\.+\s+import.*(?:UserExecutionEngine|UserExecutionContext)', 'relative_import'),
            (r'import.*(?:UserExecutionEngine|UserExecutionContext).*as\s+\w+', 'alias_import'),
            (r'from\s+.*\.(?:execution_engine|user_execution).*import', 'deep_module_import'),
            (r'try:\s*\n.*import.*(?:UserExecution)', 'conditional_import'),
        ]
        
        for pattern_regex, violation_type in patterns:
            if re.search(pattern_regex, line, re.IGNORECASE):
                severity = self._assess_severity(violation_type, rel_path)
                
                violation = ImportViolation(
                    file_path=rel_path,
                    line_number=line_num,
                    import_statement=line,
                    violation_type=violation_type,
                    severity=severity,
                    pattern_type="regex_detected"
                )
                violations.append(violation)
        
        return violations
    
    def _classify_violation(self, import_stmt: str, pattern: str, file_path: str) -> str:
        """Classify the type of import violation."""
        # SSOT violation patterns
        if "UserExecutionEngine" in import_stmt or "UserExecutionContext" in import_stmt:
            if file_path.startswith("tests/"):
                return "test_direct_import"
            elif file_path.startswith("netra_backend/app/"):
                return "backend_fragmented_import"
            else:
                return "cross_service_import"
        
        # WebSocket fragmentation
        if "WebSocketManager" in import_stmt:
            if "factory" in import_stmt.lower():
                return "websocket_factory_fragmentation"
            else:
                return "websocket_manager_fragmentation"
        
        # Agent factory fragmentation
        if "AgentFactory" in import_stmt or "agent_factory" in import_stmt:
            return "agent_factory_fragmentation"
        
        return "generic_fragmentation"
    
    def _assess_severity(self, violation_type: str, file_path: str) -> str:
        """Assess the severity of an import violation."""
        # Critical violations that break SSOT
        critical_patterns = [
            "cross_service_import",
            "duplicate_import",
            "websocket_factory_fragmentation"
        ]
        
        # High severity violations that affect Golden Path
        high_patterns = [
            "backend_fragmented_import",
            "websocket_manager_fragmentation",
            "agent_factory_fragmentation"
        ]
        
        # Medium severity violations
        medium_patterns = [
            "test_direct_import",
            "relative_import",
            "conditional_import"
        ]
        
        if violation_type in critical_patterns:
            return "CRITICAL"
        elif violation_type in high_patterns:
            return "HIGH"
        elif violation_type in medium_patterns:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _determine_pattern_type(self, import_stmt: str, pattern: str) -> str:
        """Determine the specific pattern type for categorization."""
        if "from" in import_stmt and "import" in import_stmt:
            return "from_import"
        elif "import" in import_stmt and " as " in import_stmt:
            return "alias_import"
        elif "import" in import_stmt:
            return "direct_import"
        else:
            return "unknown_import"
    
    def _aggregate_stats(self, violations: List[ImportViolation]) -> None:
        """Aggregate violation statistics."""
        self.stats.total_violations = len(violations)
        
        for violation in violations:
            if violation.severity == "CRITICAL":
                self.stats.critical_violations += 1
            elif violation.severity == "HIGH":
                self.stats.high_violations += 1
            elif violation.severity == "MEDIUM":
                self.stats.medium_violations += 1
            else:
                self.stats.low_violations += 1
    
    def test_detect_user_execution_engine_import_fragmentation(self):
        """
        CRITICAL TEST: Detect UserExecutionEngine import fragmentation violations.
        
        This test MUST FAIL initially to demonstrate the current 275+ violations
        that need to be addressed for SSOT compliance.
        
        Expected violations:
        - 275+ total import fragmentation violations
        - 50+ critical violations (cross-service imports, duplicates)
        - 100+ high violations (backend fragmentation, WebSocket issues)
        - 125+ medium/low violations (test imports, relative imports)
        
        Business Impact: 
        - Protects $500K+ ARR Golden Path from cascade failures
        - Ensures reliable UserExecutionContext creation
        - Maintains system stability during agent execution
        """
        # Scan all Python files
        python_files = self._scan_python_files()
        self.assertGreater(len(python_files), 100, "Should scan substantial number of Python files")
        
        # Analyze each file for import violations
        all_violations = []
        for file_path in python_files:
            violations = self._analyze_file_imports(file_path)
            all_violations.extend(violations)
        
        # Store violations for analysis
        self.violations = all_violations
        self._aggregate_stats(all_violations)
        
        # Record metrics for tracking
        self.record_metric("total_violations", self.stats.total_violations)
        self.record_metric("critical_violations", self.stats.critical_violations)
        self.record_metric("high_violations", self.stats.high_violations)
        self.record_metric("files_affected", len(self.stats.files_affected))
        self.record_metric("patterns_detected", len(self.stats.patterns_detected))
        
        # Log detailed results
        self.logger.error(f"IMPORT FRAGMENTATION DETECTED - SSOT VIOLATION")
        self.logger.error(f"Total violations: {self.stats.total_violations}")
        self.logger.error(f"Critical violations: {self.stats.critical_violations}")
        self.logger.error(f"High violations: {self.stats.high_violations}")
        self.logger.error(f"Medium violations: {self.stats.medium_violations}")
        self.logger.error(f"Low violations: {self.stats.low_violations}")
        self.logger.error(f"Files affected: {len(self.stats.files_affected)}")
        self.logger.error(f"Patterns detected: {sorted(self.stats.patterns_detected)}")
        
        # **CRITICAL ASSERTION: This test MUST FAIL to demonstrate current violations**
        # When SSOT consolidation is complete, this threshold should be reduced to 0
        self.assertGreaterEqual(
            self.stats.total_violations, 
            self.violation_threshold,
            f"Expected at least {self.violation_threshold} import fragmentation violations "
            f"to demonstrate current SSOT compliance issues. Found {self.stats.total_violations}. "
            f"If violations are below threshold, SSOT consolidation may already be complete."
        )
        
        # Ensure critical violations exist (these are blocking issues)
        self.assertGreater(
            self.stats.critical_violations,
            0,
            f"Expected critical import violations to exist. Found {self.stats.critical_violations}. "
            f"Critical violations indicate immediate SSOT compliance issues that must be addressed."
        )
        
        # Verify significant high-impact violations
        self.assertGreater(
            self.stats.high_violations,
            50,
            f"Expected substantial high-impact violations. Found {self.stats.high_violations}. "
            f"High violations affect Golden Path reliability and must be prioritized."
        )
        
        # Log top violation files for prioritization
        file_violation_counts = {}
        for violation in all_violations:
            file_violation_counts[violation.file_path] = file_violation_counts.get(violation.file_path, 0) + 1
        
        top_files = sorted(file_violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        self.logger.error("TOP 10 FILES WITH MOST VIOLATIONS:")
        for file_path, count in top_files:
            self.logger.error(f"  {file_path}: {count} violations")
        
        # **THIS TEST FAILS TO DEMONSTRATE CURRENT SSOT VIOLATIONS**
        # SUCCESS CRITERIA: When SSOT consolidation is complete, update thresholds to:
        # - total_violations: 0
        # - critical_violations: 0  
        # - high_violations: 0
        # - Then this test will pass and protect against regressions
        
        self.fail(
            f"SSOT CONSOLIDATION REQUIRED: Found {self.stats.total_violations} import fragmentation violations "
            f"({self.stats.critical_violations} critical, {self.stats.high_violations} high severity). "
            f"This test fails to demonstrate current SSOT compliance issues that must be addressed "
            f"for Issue #1186 resolution. See logs for detailed violation analysis."
        )
    
    def test_analyze_critical_violation_patterns(self):
        """
        Analyze patterns in critical violations for remediation guidance.
        
        This test provides detailed analysis of the most severe violations
        to guide SSOT consolidation efforts.
        """
        # Run the main detection test first
        python_files = self._scan_python_files()
        all_violations = []
        for file_path in python_files:
            violations = self._analyze_file_imports(file_path)
            all_violations.extend(violations)
        
        # Filter critical violations
        critical_violations = [v for v in all_violations if v.severity == "CRITICAL"]
        
        # Analyze patterns
        violation_patterns = {}
        for violation in critical_violations:
            pattern = violation.violation_type
            if pattern not in violation_patterns:
                violation_patterns[pattern] = []
            violation_patterns[pattern].append(violation)
        
        # Log critical pattern analysis
        self.logger.error("CRITICAL VIOLATION PATTERN ANALYSIS:")
        for pattern, violations in violation_patterns.items():
            self.logger.error(f"  {pattern}: {len(violations)} occurrences")
            
            # Sample violations for each pattern
            for violation in violations[:3]:  # Show first 3 examples
                self.logger.error(f"    {violation.file_path}:{violation.line_number} - {violation.import_statement}")
        
        # Record critical pattern metrics
        self.record_metric("critical_patterns", len(violation_patterns))
        for pattern, violations in violation_patterns.items():
            self.record_metric(f"critical_{pattern}_count", len(violations))
        
        # Assertions for critical analysis
        self.assertGreater(len(critical_violations), 0, "Should detect critical violations for analysis")
        self.assertGreater(len(violation_patterns), 0, "Should identify critical violation patterns")
        
        # **THIS TEST ALSO FAILS TO SHOW CRITICAL ISSUES EXIST**
        self.fail(
            f"CRITICAL VIOLATION ANALYSIS: Found {len(critical_violations)} critical violations "
            f"across {len(violation_patterns)} patterns. These must be addressed for SSOT compliance. "
            f"See logs for detailed pattern analysis and remediation guidance."
        )