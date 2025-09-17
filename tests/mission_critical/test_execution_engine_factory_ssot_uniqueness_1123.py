"Issue #1123: SSOT Factory Uniqueness Test - ExecutionEngine Factory Fragmentation Detection.

This test creates NEW validation for execution engine factory fragmentation specifically
for Issue #1123. It validates that only ONE canonical factory exists and detects
multiple factory implementations that violate SSOT principles.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: System Integrity & Stability  
- Value Impact: Protects $500K+ ARR Golden Path by ensuring single execution engine factory
- Strategic Impact: Critical foundation for multi-user chat isolation and performance

EXPECTED BEHAVIOR:
This test SHOULD FAIL initially, exposing existing factory fragmentation issues.
After SSOT consolidation is complete, this test should pass, confirming the
ExecutionEngineFactory as the single source of truth.

TEST STRATEGY:
- Detect multiple factory implementations across codebase
- Validate import path consistency to canonical factory
- Test factory instance uniqueness and proper isolation
- Ensure no legacy factory patterns remain active
""

import unittest
import importlib
import inspect
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionEngineFactorySSotUniqueness1123Tests(SSotBaseTestCase):
    Test for detecting ExecutionEngine Factory SSOT uniqueness violations (Issue #1123)."
    
    def setUp(self):
        "Set up test environment for SSOT factory uniqueness detection.
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent
        self.factory_implementations = []
        self.legacy_factory_imports = []
        self.factory_instantiation_violations = []
        self.ssot_factory_violations = []
        
        # Expected SSOT factory pattern
        self.canonical_factory_module = netra_backend.app.agents.supervisor.execution_engine_factory""
        self.canonical_factory_class = ExecutionEngineFactory
        self.canonical_factory_function = get_execution_engine_factory"
        
        logger.info("🚀 Issue #1123: Starting ExecutionEngine Factory SSOT uniqueness validation)
    
    def test_detect_multiple_execution_engine_factories(self):
        Detect multiple ExecutionEngineFactory implementations - SHOULD INITIALLY FAIL.""
        logger.info(🔍 FACTORY SSOT VIOLATION: Scanning for multiple ExecutionEngineFactory classes)
        
        # Find all factory implementations
        factory_implementations = self._find_all_execution_engine_factories()
        
        # Log findings
        logger.info(fFound {len(factory_implementations)} ExecutionEngineFactory implementations:)"
        for module_path, class_name, source_file in factory_implementations:
            logger.info(f"  - {class_name} in {module_path} (file: {source_file})
        
        # SSOT VALIDATION: Should only have ONE canonical factory implementation
        canonical_factories = [
            impl for impl in factory_implementations
            if impl[0] == self.canonical_factory_module and impl[1] == self.canonical_factory_class
        ]
        
        non_canonical_factories = [
            impl for impl in factory_implementations
            if not (impl[0] == self.canonical_factory_module and impl[1] == self.canonical_factory_class)
        ]
        
        # Store violations
        self.factory_implementations = factory_implementations
        self.ssot_factory_violations.extend([
            fNon-canonical ExecutionEngineFactory: {class_name} in {module_path}
            for module_path, class_name, source_file in non_canonical_factories
        ]
        
        logger.warning(f❌ SSOT VIOLATION: Found {len(non_canonical_factories)} non-canonical factory classes)
        logger.info(f✅ CANONICAL: Found {len(canonical_factories)} canonical factory classes")"
        
        # Store detailed violation information
        for module_path, class_name, source_file in non_canonical_factories:
            logger.error(fVIOLATION DETAIL: {class_name} in {module_path} conflicts with SSOT factory)
        
        # EXPECTED TO FAIL: Multiple factory classes indicate SSOT fragmentation
        self.assertGreater(
            len(non_canonical_factories), 0,
            fEXPECTED FAILURE (Issue #1123): Should detect ExecutionEngineFactory fragmentation. 
            f"Found {len(non_canonical_factories)} non-canonical factory implementations violating SSOT. 
            fBusiness Impact: Threatens $500K+ ARR Golden Path due to factory inconsistency."
        )
        
        # Additional validation: Ensure canonical factory exists
        self.assertGreater(
            len(canonical_factories), 0,
            fCRITICAL: Canonical ExecutionEngineFactory not found in {self.canonical_factory_module}. 
            fSSOT consolidation incomplete."
        )
    
    def test_detect_factory_import_path_violations(self):
        "Detect factory import path violations bypassing SSOT - SHOULD INITIALLY FAIL.
        logger.info(🔍 IMPORT PATH VIOLATION: Scanning for non-SSOT factory import patterns")"
        
        # Find legacy and non-SSOT factory imports
        import_violations = self._find_factory_import_violations()
        
        # Log findings
        logger.info(fFound {len(import_violations)} factory import path violations:)
        for file_path, line_num, import_line, violation_type in import_violations:
            logger.info(f  - {violation_type}: {file_path}:{line_num} - {import_line.strip()})
        
        # Store violations
        self.legacy_factory_imports = import_violations
        self.ssot_factory_violations.extend([
            f"Import path violation ({violation_type}: {file_path}:{line_num} - {import_line.strip()}
            for file_path, line_num, import_line, violation_type in import_violations
        ]
        
        # EXPECTED TO FAIL: Import path violations should be detected
        self.assertGreater(
            len(import_violations), 0,
            fEXPECTED FAILURE (Issue #1123): Should detect factory import path violations. "
            fFound {len(import_violations)} imports bypassing SSOT ExecutionEngineFactory. 
            fThese violations prevent consistent factory usage across the system."
        )
    
    def test_detect_factory_instantiation_violations(self):
        "Detect direct factory instantiation bypassing SSOT patterns - SHOULD INITIALLY FAIL.
        logger.info(🔍 INSTANTIATION VIOLATION: Scanning for direct factory instantiation bypassing SSOT")"
        
        # Find direct factory instantiations that bypass the SSOT function
        instantiation_violations = self._find_factory_instantiation_violations()
        
        # Log findings
        logger.info(fFound {len(instantiation_violations)} factory instantiation violations:)
        for file_path, line_num, code_line, violation_type in instantiation_violations:
            logger.info(f  - {violation_type}: {file_path}:{line_num} - {code_line.strip()})
        
        # Store violations
        self.factory_instantiation_violations = instantiation_violations
        self.ssot_factory_violations.extend([
            f"Instantiation violation ({violation_type}: {file_path}:{line_num} - {code_line.strip()}
            for file_path, line_num, code_line, violation_type in instantiation_violations
        ]
        
        # EXPECTED TO FAIL: Direct instantiation violations should be detected
        self.assertGreater(
            len(instantiation_violations), 0,
            fEXPECTED FAILURE (Issue #1123): Should detect factory instantiation violations. "
            fFound {len(instantiation_violations)} direct factory instantiations bypassing SSOT pattern. 
            fThis threatens user isolation and factory consistency."
        )
    
    def test_validate_canonical_factory_accessibility(self):
        "Validate that canonical factory is accessible and properly configured - SHOULD PASS.
        logger.info(✅ CANONICAL VALIDATION: Verifying canonical ExecutionEngineFactory accessibility")"
        
        # Test canonical factory import
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory, 
                get_execution_engine_factory
            )
            canonical_import_success = True
        except ImportError as e:
            canonical_import_success = False
            logger.error(f❌ CANONICAL IMPORT FAILED: {e})
        
        # Test factory function availability
        factory_function_available = False
        if canonical_import_success:
            try:
                # Check if function exists and is callable
                factory_function_available = callable(get_execution_engine_factory)
                logger.info(f✅ CANONICAL FUNCTION: get_execution_engine_factory is callable)
            except Exception as e:
                logger.error(f"❌ CANONICAL FUNCTION ERROR: {e})
        
        # Test factory class availability
        factory_class_available = False
        if canonical_import_success:
            try:
                factory_class_available = inspect.isclass(ExecutionEngineFactory)
                logger.info(f✅ CANONICAL CLASS: ExecutionEngineFactory is available as class")
            except Exception as e:
                logger.error(f❌ CANONICAL CLASS ERROR: {e})
        
        # This test should PASS - canonical factory should be accessible
        self.assertTrue(
            canonical_import_success,
            fFAILURE: Canonical ExecutionEngineFactory not importable from {self.canonical_factory_module}. "
            f"SSOT factory must be accessible for Golden Path functionality.
        )
        
        self.assertTrue(
            factory_function_available,
            fFAILURE: get_execution_engine_factory() not available or not callable. 
            fSSOT factory function required for proper factory access pattern.
        )
        
        self.assertTrue(
            factory_class_available,
            fFAILURE: ExecutionEngineFactory class not available. ""
            fSSOT factory class required for proper instantiation.
        )
        
        logger.info(✅ CANONICAL VALIDATION COMPLETE: ExecutionEngineFactory SSOT is accessible)
    
    def test_comprehensive_factory_ssot_violation_report(self):
        "Generate comprehensive factory SSOT violation report - SHOULD INITIALLY FAIL."
        logger.info(📊 COMPREHENSIVE FACTORY SSOT VIOLATION REPORT (Issue #1123))"
        
        # Collect all violations from previous tests if not already done
        if not self.ssot_factory_violations:
            self.test_detect_multiple_execution_engine_factories()
            self.test_detect_factory_import_path_violations()
            self.test_detect_factory_instantiation_violations()
        
        # Generate comprehensive violation report
        violation_summary = {
            'total_factory_violations': len(self.ssot_factory_violations),
            'factory_implementations_found': len(self.factory_implementations),
            'import_violations': len(self.legacy_factory_imports),
            'instantiation_violations': len(self.factory_instantiation_violations),
            'business_impact': self._assess_factory_business_impact(),
            'remediation_strategy': self._generate_factory_remediation_strategy(),
            'golden_path_risk': self._assess_golden_path_risk()
        }
        
        logger.info(f"🚨 FACTORY SSOT VIOLATION SUMMARY (Issue #1123):)
        logger.info(f  Total Factory Violations: {violation_summary['total_factory_violations']})
        logger.info(f  Factory Implementations: {violation_summary['factory_implementations_found']})
        logger.info(f  Import Violations: {violation_summary['import_violations']}")"
        logger.info(f  Instantiation Violations: {violation_summary['instantiation_violations']})
        logger.info(f  Business Impact: {violation_summary['business_impact']['severity']})
        logger.info(f"  Golden Path Risk: {violation_summary['golden_path_risk']['risk_level']})
        
        # Log detailed violations
        for i, violation in enumerate(self.ssot_factory_violations[:15], 1):
            logger.info(f    {i:2d}. ❌ {violation}")
        
        if len(self.ssot_factory_violations) > 15:
            logger.info(f    ... and {len(self.ssot_factory_violations) - 15} more factory violations)
        
        # EXPECTED TO FAIL: Comprehensive factory violations should be detected
        self.assertGreater(
            violation_summary['total_factory_violations'], 0,
            fEXPECTED FAILURE (Issue #1123): ExecutionEngineFactory SSOT consolidation needed. "
            f"Detected {violation_summary['total_factory_violations']} factory violations requiring immediate remediation. 
            fBusiness Impact: {violation_summary['business_impact']['description']} 
            fGolden Path Risk: {violation_summary['golden_path_risk']['description']}
        )
    
    def _find_all_execution_engine_factories(self) -> List[Tuple[str, str, str]]:
        ""Find all ExecutionEngineFactory class definitions in the codebase.
        factories = []
        
        # Scan Python files for ExecutionEngineFactory classes
        for py_file in self.codebase_root.rglob(*.py):"
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for class definitions containing ExecutionEngineFactory
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith('class ') and 'ExecutionEngineFactory' in line:
                        class_name = self._extract_class_name(line)
                        if class_name and 'ExecutionEngineFactory' in class_name:
                            module_path = self._file_to_module_path(py_file)
                            if module_path:
                                factories.append((module_path, class_name, str(py_file)))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e}")
        
        return factories
    
    def _find_factory_import_violations(self) -> List[Tuple[str, int, str, str]]:
        Find factory import violations bypassing SSOT patterns.""
        violations = []
        
        for py_file in self.codebase_root.rglob(*.py):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Skip if it's the canonical import
                    if self.canonical_factory_module in line_stripped:
                        continue
                    
                    # Detect legacy factory import patterns
                    if self._is_legacy_factory_import(line_stripped):
                        violations.append((str(py_file), line_num, line, legacy_import))"
                    
                    # Detect direct factory imports bypassing SSOT function
                    elif self._is_direct_factory_import(line_stripped):
                        violations.append((str(py_file), line_num, line, direct_import"))
                    
                    # Detect factory imports from non-canonical modules
                    elif self._is_non_canonical_factory_import(line_stripped):
                        violations.append((str(py_file), line_num, line, non_canonical_import))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e}")"
        
        return violations
    
    def _find_factory_instantiation_violations(self) -> List[Tuple[str, int, str, str]]:
        Find factory instantiation violations bypassing SSOT patterns."
        violations = []
        
        for py_file in self.codebase_root.rglob(*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Skip comments
                    if line_stripped.startswith('#'):
                        continue
                    
                    # Detect direct factory instantiation
                    if 'ExecutionEngineFactory(' in line_stripped:
                        # Check if it's not in the canonical module
                        if self.canonical_factory_module not in str(py_file):
                            violations.append((str(py_file), line_num, line, direct_instantiation))
                    
                    # Detect factory creation bypassing get_execution_engine_factory()
                    elif ('= ExecutionEngineFactory' in line_stripped or 
                          'ExecutionEngineFactory()' in line_stripped):
                        if 'get_execution_engine_factory' not in line_stripped:
                            violations.append((str(py_file), line_num, line, bypassing_ssot_function"))"
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e})
        
        return violations
    
    def _should_skip_file(self, file_path: Path) -> bool:
        Check if file should be skipped during scanning.""
        skip_patterns = [
            '__pycache__', '.pyc', 'node_modules', '.git', 'venv', '.env',
            'test_execution_engine_factory_ssot_uniqueness_1123.py',  # Skip self
            'backup', 'archived', '.pytest_cache'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _extract_class_name(self, line: str) -> str:
        Extract class name from class definition line."
        try:
            class_part = line.split('class ')[1]
            if '(' in class_part:
                class_name = class_part.split('(')[0].strip()
            elif ':' in class_part:
                class_name = class_part.split(':')[0].strip()
            else:
                class_name = class_part.strip()
            return class_name
        except (IndexError, AttributeError):
            return "
    
    def _file_to_module_path(self, file_path: Path) -> str:
        Convert file path to Python module path.""
        try:
            rel_path = file_path.relative_to(self.codebase_root)
            module_path = str(rel_path.with_suffix(''))
            module_path = module_path.replace('/', '.').replace('\\', '.')
            return module_path
        except (ValueError, AttributeError):
            return 
    
    def _is_legacy_factory_import(self, line: str) -> bool:
        Check if line contains legacy factory import.""
        legacy_patterns = [
            'from netra_backend.app.agents.supervisor.legacy_execution_factory import',
            'from netra_backend.app.agents.execution_factory import',
            'import netra_backend.app.agents.legacy_execution_factory',
        ]
        return any(pattern in line for pattern in legacy_patterns)
    
    def _is_direct_factory_import(self, line: str) -> bool:
        Check if line contains direct factory import bypassing SSOT function.""
        direct_patterns = [
            'from.*import.*ExecutionEngineFactory',
            'ExecutionEngineFactory,',
        ]
        # Exclude canonical imports
        if self.canonical_factory_module in line:
            return False
        return any(pattern in line for pattern in direct_patterns)
    
    def _is_non_canonical_factory_import(self, line: str) -> bool:
        Check if line imports factory from non-canonical module."
        if 'ExecutionEngineFactory' not in line:
            return False
        if self.canonical_factory_module in line:
            return False
        return 'import' in line and 'ExecutionEngineFactory' in line
    
    def _assess_factory_business_impact(self) -> Dict[str, Any]:
        "Assess business impact of factory SSOT violations.
        total_violations = len(self.ssot_factory_violations)
        
        if total_violations > 15:
            severity = "CRITICAL"
            description = Severe factory fragmentation threatens $500K+ ARR Golden Path reliability
        elif total_violations > 8:
            severity = HIGH"
            description = Significant factory fragmentation risks multi-user isolation failures"
        elif total_violations > 3:
            severity = MEDIUM
            description = Moderate factory fragmentation may cause intermittent execution issues""
        else:
            severity = LOW
            description = Minor factory fragmentation with limited impact"
        
        return {
            'severity': severity,
            'description': description,
            'golden_path_risk': severity in ['CRITICAL', 'HIGH'],
            'user_isolation_risk': len(self.factory_instantiation_violations) > 0,
            'performance_risk': len(self.factory_implementations) > 2
        }
    
    def _generate_factory_remediation_strategy(self) -> Dict[str, Any]:
        "Generate factory SSOT remediation strategy.
        return {
            'phase_1': 'Consolidate all factory implementations to single canonical ExecutionEngineFactory',
            'phase_2': 'Migrate all imports to use get_execution_engine_factory() function',
            'phase_3': 'Remove all direct factory instantiation patterns',
            'phase_4': 'Validate user isolation and Golden Path functionality',
            'success_criteria': 'All tests pass, single factory implementation, consistent import paths'
        }
    
    def _assess_golden_path_risk(self) -> Dict[str, Any]:
        ""Assess Golden Path risk from factory fragmentation.
        factory_count = len(self.factory_implementations)
        violation_count = len(self.ssot_factory_violations)
        
        if factory_count > 3 or violation_count > 10:
            risk_level = HIGH"
            description = Factory fragmentation directly threatens Golden Path user flow reliability"
        elif factory_count > 1 or violation_count > 5:
            risk_level = MEDIUM
            description = Factory inconsistency may cause Golden Path intermittent failures""
        else:
            risk_level = LOW
            description = Factory fragmentation poses minimal Golden Path risk"
        
        return {
            'risk_level': risk_level,
            'description': description,
            'chat_functionality_impact': risk_level in ['HIGH', 'MEDIUM'],
            'user_isolation_impact': len(self.factory_instantiation_violations) > 0
        }


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()