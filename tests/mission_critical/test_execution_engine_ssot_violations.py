"Issue #874: ExecutionEngine SSOT consolidation compliance test."

This test detects existing ExecutionEngine fragmentation and validates the SSOT
consolidation status. It identifies multiple ExecutionEngine implementations
that violate the Single Source of Truth principle.

Business Value Justification:
    - Segment: Platform/Internal  
- Business Goal: Stability & System Integrity
- Value Impact: Ensures reliable multi-user chat functionality by eliminating execution engine fragmentation
- Strategic Impact: Critical foundation for $500K+ plus ARR chat operations requiring zero user isolation failures

Key Detection Areas:
    - Multiple ExecutionEngine class definitions across modules
- Legacy execution engine instances still in use
- Import path violations bypassing UserExecutionEngine SSOT
- Factory pattern consolidation status
- User isolation security vulnerabilities

EXPECTED BEHAVIOR: 
    This test SHOULD FAIL initially, demonstrating existing fragmentation issues.
After SSOT consolidation is complete, this test should pass, confirming
UserExecutionEngine as the canonical implementation.
""

import unittest
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionEngineSSotViolationsTests(SSotBaseTestCase):
    Test for detecting ExecutionEngine SSOT violations and fragmentation."
    Test for detecting ExecutionEngine SSOT violations and fragmentation.""

    
    def setUp(self):
        "Set up test environment for SSOT violation detection."
        super().setUp()
        # Set up instance attributes after parent setup
        self._initialize_test_attributes()
        logger.info(Starting ExecutionEngine SSOT violation detection")"
    
    def _initialize_test_attributes(self):
        Initialize test attributes - separate method to avoid conflicts."
        Initialize test attributes - separate method to avoid conflicts.""

        self.codebase_root = Path(__file__).parent.parent.parent
        self.execution_engine_classes = []
        self.execution_engine_modules = []
        self.legacy_imports = []
        self.ssot_violations = []
        
        # Expected SSOT pattern
        self.canonical_module = netra_backend.app.agents.supervisor.user_execution_engine"
        self.canonical_module = netra_backend.app.agents.supervisor.user_execution_engine""

        self.canonical_class = UserExecutionEngine
    
    def test_detect_multiple_execution_engine_classes(self):
        ""Detect multiple ExecutionEngine class definitions - SHOULD INITIALLY FAIL."
        logger.info(🔍 SSOT VIOLATION DETECTION: Scanning for multiple ExecutionEngine classes)"
        logger.info(🔍 SSOT VIOLATION DETECTION: Scanning for multiple ExecutionEngine classes)""

        
        # Ensure attributes are initialized (safety check)
        if not hasattr(self, 'codebase_root'):
            self._initialize_test_attributes()
        
        execution_engine_classes = self._find_all_execution_engine_classes()
        
        # Log findings
        logger.info(fFound {len(execution_engine_classes)} ExecutionEngine-related classes:")"
        for module_path, class_name, class_obj in execution_engine_classes:
            logger.info(f  - {class_name} in {module_path})
            if hasattr(class_obj, '__module__'):
                logger.info(f    Module: {class_obj.__module__})"
                logger.info(f    Module: {class_obj.__module__})""

        
        # SSOT VALIDATION: Should only have UserExecutionEngine as the canonical implementation
        canonical_classes = [
            (module_path, class_name) for module_path, class_name, class_obj in execution_engine_classes
            if class_name == self.canonical_class and self.canonical_module in module_path
        ]
        
        non_canonical_classes = [
            (module_path, class_name) for module_path, class_name, class_obj in execution_engine_classes
            if not (class_name == self.canonical_class and self.canonical_module in module_path)
        ]
        
        # Store violation details for reporting
        self.ssot_violations.extend([
            f"Non-canonical ExecutionEngine: {class_name} in {module_path}"
            for module_path, class_name in non_canonical_classes
        ]
        
        logger.warning(fX SSOT VIOLATION: Found {len(non_canonical_classes)} non-canonical ExecutionEngine classes)
        logger.info(fCHECK CANONICAL: Found {len(canonical_classes)} canonical ExecutionEngine classes)
        
        # EXPECTED TO FAIL: Multiple execution engine classes indicate fragmentation
        self.assertGreater(
            len(non_canonical_classes), 0,
            EXPECTED FAILURE: Should detect ExecutionEngine fragmentation violations. ""
            fFound {len(non_canonical_classes)} non-canonical classes, indicating SSOT consolidation needed.
        )
    
    def test_detect_legacy_execution_engine_imports(self):
        Detect legacy ExecutionEngine import patterns - SHOULD INITIALLY FAIL.""
        logger.info(🔍 SSOT VIOLATION DETECTION: Scanning for legacy ExecutionEngine imports)
        
        legacy_imports = self._find_legacy_execution_engine_imports()
        
        # Log findings
        logger.info(fFound {len(legacy_imports)} legacy ExecutionEngine imports:)"
        logger.info(fFound {len(legacy_imports)} legacy ExecutionEngine imports:)""

        for file_path, line_num, import_line in legacy_imports:
            logger.info(f"  - {file_path}:{line_num}: {import_line.strip()})"
        
        # Store violation details
        self.legacy_imports = legacy_imports
        self.ssot_violations.extend([
            fLegacy import: {file_path}:{line_num} - {import_line.strip()}
            for file_path, line_num, import_line in legacy_imports
        ]
        
        # EXPECTED TO FAIL: Legacy imports should be detected
        self.assertGreater(
            len(legacy_imports), 0,
            EXPECTED FAILURE: Should detect legacy ExecutionEngine import patterns. "
            EXPECTED FAILURE: Should detect legacy ExecutionEngine import patterns. "
            fFound {len(legacy_imports)} legacy imports requiring migration to UserExecutionEngine SSOT."
            fFound {len(legacy_imports)} legacy imports requiring migration to UserExecutionEngine SSOT.""

        )
    
    def test_detect_execution_engine_factory_violations(self):
        Detect ExecutionEngine factory pattern violations - SHOULD INITIALLY FAIL.""
        logger.info(🔍 SSOT VIOLATION DETECTION: Scanning for ExecutionEngine factory violations)
        
        factory_violations = self._find_execution_engine_factory_violations()
        
        # Log findings
        logger.info(fFound {len(factory_violations)} ExecutionEngine factory violations:)
        for violation_type, file_path, details in factory_violations:
            logger.info(f  - {violation_type}: {file_path} - {details}")"
        
        # Store violation details
        self.ssot_violations.extend([
            fFactory violation ({violation_type): {file_path) - {details)
            for violation_type, file_path, details in factory_violations
        ]
        
        # EXPECTED TO FAIL: Factory violations should be detected
        self.assertGreater(
            len(factory_violations), 0,
            EXPECTED FAILURE: Should detect ExecutionEngine factory pattern violations. 
            f"Found {len(factory_violations)} violations requiring factory consolidation."
        )
    
    def test_detect_user_isolation_vulnerabilities(self):
        "Detect user isolation vulnerabilities in execution engines - SHOULD INITIALLY FAIL."
        logger.info("🔍 SECURITY VIOLATION DETECTION: Scanning for user isolation vulnerabilities)"
        
        isolation_violations = self._find_user_isolation_vulnerabilities()
        
        # Log findings
        logger.info(fFound {len(isolation_violations)} user isolation vulnerabilities:)
        for vuln_type, file_path, details in isolation_violations:
            logger.info(f  - {vuln_type}: {file_path} - {details})
        
        # Store violation details
        self.ssot_violations.extend([
            fIsolation vulnerability ({vuln_type): {file_path) - {details)""
            for vuln_type, file_path, details in isolation_violations
        ]
        
        # EXPECTED TO FAIL: Isolation vulnerabilities should be detected
        self.assertGreater(
            len(isolation_violations), 0,
            EXPECTED FAILURE: Should detect user isolation vulnerabilities. 
            fFound {len(isolation_violations)} vulnerabilities requiring secure UserExecutionEngine patterns."
            fFound {len(isolation_violations)} vulnerabilities requiring secure UserExecutionEngine patterns.""

        )
    
    def test_comprehensive_ssot_violation_summary(self):
        "Generate comprehensive SSOT violation report - SHOULD INITIALLY FAIL."
        logger.info(📊 COMPREHENSIVE SSOT VIOLATION SUMMARY")"
        
        # Collect all violations from previous tests
        if not self.ssot_violations:
            # Run detection if not already done
            self.test_detect_multiple_execution_engine_classes()
            self.test_detect_legacy_execution_engine_imports()
            self.test_detect_execution_engine_factory_violations()
            self.test_detect_user_isolation_vulnerabilities()
        
        # Generate comprehensive report
        violation_summary = {
            'total_violations': len(self.ssot_violations),
            'violations_by_type': self._categorize_violations(),
            'business_impact': self._assess_business_impact(),
            'remediation_priority': self._assess_remediation_priority(),
            'canonical_status': self._assess_canonical_status()
        }
        
        logger.info(fSSOT VIOLATION SUMMARY:)
        logger.info(f  Total Violations: {violation_summary['total_violations']})
        logger.info(f"  Business Impact: {violation_summary['business_impact']['severity']})"
        logger.info(f  Remediation Priority: {violation_summary['remediation_priority']}")"
        logger.info(f  Canonical Status: {violation_summary['canonical_status']['status']})
        
        for violation in self.ssot_violations[:10]:  # Log first 10 violations
            logger.info(f    X {violation})"
            logger.info(f    X {violation})""

        
        if len(self.ssot_violations) > 10:
            logger.info(f"    ... and {len(self.ssot_violations) - 10} more violations)"
        
        # EXPECTED TO FAIL: Comprehensive violations should be detected
        self.assertGreater(
            violation_summary['total_violations'], 0,
            EXPECTED FAILURE: ExecutionEngine SSOT consolidation needed. 
            fDetected {violation_summary['total_violations']} violations requiring remediation. 
            fBusiness Impact: {violation_summary['business_impact']['description']}""
        )
    
    def _find_all_execution_engine_classes(self) -> List[Tuple[str, str, Any]]:
        Find all ExecutionEngine class definitions in the codebase."
        Find all ExecutionEngine class definitions in the codebase.""

        classes = []
        
        # Scan Python files for ExecutionEngine classes
        for py_file in self.codebase_root.rglob(*.py"):"
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for class definitions containing ExecutionEngine
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith('class ') and 'ExecutionEngine' in line:
                        class_name = self._extract_class_name(line)
                        if class_name:
                            try:
                                # Try to import and get the actual class object
                                module_path = self._file_to_module_path(py_file)
                                if module_path:
                                    module = importlib.import_module(module_path)
                                    if hasattr(module, class_name):
                                        class_obj = getattr(module, class_name)
                                        classes.append((str(py_file), class_name, class_obj))
                            except (ImportError, AttributeError) as e:
                                logger.debug(fCould not import {class_name} from {py_file}: {e})
                                # Still record the class definition even if import fails
                                classes.append((str(py_file), class_name, None))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e})"
                logger.debug(fCould not read {py_file}: {e})""

        
        return classes
    
    def _find_legacy_execution_engine_imports(self) -> List[Tuple[str, int, str]]:
        "Find legacy ExecutionEngine import statements."
        legacy_imports = []
        
        for py_file in self.codebase_root.rglob(*.py"):"
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Detect legacy import patterns
                    if self._is_legacy_execution_engine_import(line_stripped):
                        legacy_imports.append((str(py_file), line_num, line))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e})
        
        return legacy_imports
    
    def _find_execution_engine_factory_violations(self) -> List[Tuple[str, str, str]]:
        Find ExecutionEngine factory pattern violations.""
        violations = []
        
        for py_file in self.codebase_root.rglob(*.py):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Detect direct ExecutionEngine instantiation (bypassing factory)
                if 'ExecutionEngine(' in content and 'UserExecutionEngine(' not in content:
                    violations.append((direct_instantiation, str(py_file), "
                    violations.append((direct_instantiation, str(py_file), "
                                     "Direct ExecutionEngine instantiation bypassing factory))"
                
                # Detect multiple factory implementations
                if 'class ' in content and 'ExecutionEngineFactory' in content:
                    if self.canonical_module not in str(py_file):
                        violations.append((duplicate_factory, str(py_file),
                                         "Duplicate ExecutionEngineFactory implementation))"
                
                # Detect singleton pattern violations
                if '_instance' in content and 'ExecutionEngine' in content:
                    violations.append((singleton_violation, str(py_file),
                                     Singleton pattern detected - violates user isolation))"
                                     Singleton pattern detected - violates user isolation))""

                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e}")"
        
        return violations
    
    def _find_user_isolation_vulnerabilities(self) -> List[Tuple[str, str, str]]:
        Find user isolation vulnerabilities in execution engines.""
        vulnerabilities = []
        
        for py_file in self.codebase_root.rglob(*.py):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Detect shared state patterns
                if 'global ' in content and ('execution' in content.lower() or 'engine' in content.lower()):
                    vulnerabilities.append((global_state, str(py_file),"
                    vulnerabilities.append((global_state, str(py_file),"
                                          Global state detected in execution engine"))"
                
                # Detect class-level state that could leak between users
                if 'class ' in content and 'ExecutionEngine' in content:
                    lines = content.split('\n')
                    in_class = False
                    for line in lines:
                        if line.strip().startswith('class ') and 'ExecutionEngine' in line:
                            in_class = True
                        elif line.strip().startswith('class ') and in_class:
                            in_class = False
                        elif in_class and '=' in line and not line.strip().startswith('def '):
                            # Class-level assignment - potential shared state
                            if not line.strip().startswith('#') and 'self.' not in line:
                                vulnerabilities.append((class_level_state, str(py_file),
                                                       fClass-level state: {line.strip()[:50]}..."))"
                
                # Detect missing user context validation
                if 'ExecutionEngine' in content and 'user_id' in content:
                    if 'validate_user_context' not in content:
                        vulnerabilities.append((missing_user_validation, str(py_file),
                                              Missing user context validation))"
                                              Missing user context validation))""

                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(f"Could not read {py_file}: {e})"
        
        return vulnerabilities
    
    def _should_skip_file(self, file_path: Path) -> bool:
        Check if file should be skipped during scanning."
        Check if file should be skipped during scanning.""

        skip_patterns = [
            '__pycache__',
            '.pyc',
            'node_modules',
            '.git',
            'venv',
            '.env',
            'test_execution_engine_ssot_violations.py',  # Skip self
            'backup',
            'archived'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _extract_class_name(self, line: str) -> str:
        "Extract class name from class definition line."
        try:
            # Remove 'class ' and everything after '(' or ':'
            class_part = line.split('class ')[1]
            if '(' in class_part:
                class_name = class_part.split('(')[0].strip()
            elif ':' in class_part:
                class_name = class_part.split(':')[0].strip()
            else:
                class_name = class_part.strip()
            return class_name
        except (IndexError, AttributeError):
            return ""
    
    def _file_to_module_path(self, file_path: Path) -> str:
        Convert file path to Python module path."
        Convert file path to Python module path.""

        try:
            # Convert to relative path from codebase root
            rel_path = file_path.relative_to(self.codebase_root)
            # Remove .py extension and convert to module path
            module_path = str(rel_path.with_suffix(''))
            module_path = module_path.replace('/', '.').replace('\\', '.')
            return module_path
        except (ValueError, AttributeError):
            return "
            return ""

    
    def _is_legacy_execution_engine_import(self, line: str) -> bool:
        Check if line contains legacy ExecutionEngine import.""
        legacy_patterns = [
            'from netra_backend.app.agents.supervisor.execution_engine import',
            'import netra_backend.app.agents.supervisor.execution_engine',
            'from netra_backend.app.agents.execution_engine import',
            'import netra_backend.app.agents.execution_engine',
            'ExecutionEngine,',  # Import list containing ExecutionEngine
        ]
        
        # Exclude canonical imports
        if self.canonical_module in line:
            return False
        
        return any(pattern in line for pattern in legacy_patterns)
    
    def _categorize_violations(self) -> Dict[str, int]:
        Categorize SSOT violations by type."
        Categorize SSOT violations by type.""

        categories = {}
        for violation in self.ssot_violations:
            if 'Non-canonical ExecutionEngine' in violation:
                categories['multiple_classes'] = categories.get('multiple_classes', 0) + 1
            elif 'Legacy import' in violation:
                categories['legacy_imports'] = categories.get('legacy_imports', 0) + 1
            elif 'Factory violation' in violation:
                categories['factory_violations'] = categories.get('factory_violations', 0) + 1
            elif 'Isolation vulnerability' in violation:
                categories['isolation_vulnerabilities'] = categories.get('isolation_vulnerabilities', 0) + 1
            else:
                categories['other'] = categories.get('other', 0) + 1
        return categories
    
    def _assess_business_impact(self) -> Dict[str, Any]:
        "Assess business impact of SSOT violations."
        total_violations = len(self.ssot_violations)
        
        if total_violations > 50:
            severity = CRITICAL""
            description = Severe ExecutionEngine fragmentation threatens $500K+ plus ARR chat functionality
        elif total_violations > 20:
            severity = HIGH"
            severity = HIGH"
            description = "Significant fragmentation risks multi-user chat reliability"
        elif total_violations > 10:
            severity = MEDIUM
            description = "Moderate fragmentation may cause intermittent chat issues"
        else:
            severity = LOW
            description = Minor fragmentation with limited business impact"
            description = Minor fragmentation with limited business impact""

        
        return {
            'severity': severity,
            'description': description,
            'chat_functionality_risk': severity in ['CRITICAL', 'HIGH'],
            'multi_user_isolation_risk': any('isolation' in v for v in self.ssot_violations),
            'performance_degradation_risk': any('factory' in v for v in self.ssot_violations)
        }
    
    def _assess_remediation_priority(self) -> str:
        "Assess remediation priority based on violation types."
        if any('isolation' in v for v in self.ssot_violations):
            return "P0 - IMMEDIATE (Security vulnerabilities detected)"
        elif len(self.ssot_violations) > 20:
            return P1 - URGENT (Major fragmentation detected)
        elif any('factory' in v for v in self.ssot_violations):
            return P2 - HIGH (Factory consolidation needed)"
            return P2 - HIGH (Factory consolidation needed)""

        else:
            return P3 - MEDIUM (Cleanup and optimization)"
            return P3 - MEDIUM (Cleanup and optimization)""

    
    def _assess_canonical_status(self) -> Dict[str, Any]:
        Assess canonical ExecutionEngine implementation status.""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            canonical_available = True
        except ImportError:
            canonical_available = False
        
        canonical_classes = [v for v in self.ssot_violations if self.canonical_class in v and 'Non-canonical' not in v]
        
        if canonical_available and len(canonical_classes) == 1:
            status = PARTIAL - Canonical class available but violations exist
        elif canonical_available:
            status = DEGRADED - Canonical class available with multiple implementations"
            status = DEGRADED - Canonical class available with multiple implementations""

        else:
            status = MISSING - Canonical UserExecutionEngine not available""
        
        return {
            'status': status,
            'canonical_available': canonical_available,
            'canonical_class': self.canonical_class,
            'canonical_module': self.canonical_module
        }


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()
)))))))))))