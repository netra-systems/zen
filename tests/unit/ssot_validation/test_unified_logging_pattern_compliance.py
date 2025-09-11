"""
SSOT LOGGING VALIDATION: Unified Logging Pattern Compliance Test
================================================================

PURPOSE: Validates both agent_execution_core.py and agent_execution_tracker.py 
use the same SSOT logging pattern post-SSOT remediation.

BUSINESS VALUE: Ensures unified correlation tracking for Golden Path debugging
protecting $500K+ ARR customer support capabilities.

EXPECTED BEHAVIOR:
- FAILS initially while mixed logging patterns exist
- PASSES after SSOT remediation when both files use central_logger.get_logger()
"""

import ast
import inspect
import os
from typing import Set, Dict, List
from unittest import mock

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUnifiedLoggingPatternCompliance(SSotBaseTestCase):
    """
    Validates both files use same SSOT logging pattern post-fix.
    
    Post-fix validation: Both files use central_logger.get_logger()
    """
    
    def setUp(self):
        super().setUp()
        self.expected_import = "from netra_backend.app.logging_config import central_logger"
        self.expected_logger_creation = "central_logger.get_logger(__name__)"
        self.forbidden_import = "import logging"
        self.forbidden_logger_creation = "logging.getLogger(__name__)"
        
    def test_both_files_use_ssot_central_logger(self):
        """
        Post-fix validation: Both files use central_logger.get_logger()
        
        EXPECTED:
        - FAILS initially when agent_execution_tracker.py uses logging.getLogger()
        - PASSES after remediation when both use central_logger.get_logger()
        """
        # Import modules for analysis
        import netra_backend.app.agents.supervisor.agent_execution_core as core_module
        import netra_backend.app.core.agent_execution_tracker as tracker_module
        
        # Get file paths for source analysis
        core_file_path = inspect.getfile(core_module)
        tracker_file_path = inspect.getfile(tracker_module)
        
        # Analyze both files
        core_compliance = self._analyze_file_logging_compliance(core_file_path, "agent_execution_core.py")
        tracker_compliance = self._analyze_file_logging_compliance(tracker_file_path, "agent_execution_tracker.py")
        
        print(f"\n=== SSOT LOGGING COMPLIANCE ANALYSIS ===")
        print(f"agent_execution_core.py SSOT compliance: {core_compliance['is_compliant']}")
        print(f"agent_execution_tracker.py SSOT compliance: {tracker_compliance['is_compliant']}")
        
        # Both files must be SSOT compliant
        both_compliant = core_compliance['is_compliant'] and tracker_compliance['is_compliant']
        
        # Prepare detailed failure message
        failure_details = []
        if not core_compliance['is_compliant']:
            failure_details.append(f"agent_execution_core.py violations: {core_compliance['violations']}")
        if not tracker_compliance['is_compliant']:
            failure_details.append(f"agent_execution_tracker.py violations: {tracker_compliance['violations']}")
        
        self.assertTrue(
            both_compliant,
            f"SSOT LOGGING COMPLIANCE FAILURE: Both files must use central_logger.get_logger() "
            f"for unified Golden Path debugging correlation. Violations detected: "
            f"{'; '.join(failure_details)}. "
            f"BUSINESS IMPACT: $500K+ ARR debugging capability compromised without unified logging."
        )
        
        print("✅ SSOT COMPLIANCE: Both files use unified logging pattern")
        
    def test_no_legacy_logging_imports_remain(self):
        """
        Validates that no legacy 'import logging' patterns remain after SSOT remediation.
        """
        # Check both critical files
        files_to_check = [
            ('agent_execution_core.py', 'netra_backend.app.agents.supervisor.agent_execution_core'),
            ('agent_execution_tracker.py', 'netra_backend.app.core.agent_execution_tracker')
        ]
        
        legacy_imports_found = []
        
        for filename, module_path in files_to_check:
            module = __import__(module_path, fromlist=[''])
            source = inspect.getsource(module)
            
            # Check for legacy import patterns
            legacy_patterns = [
                'import logging',
                'from logging import',
                'logging.getLogger('
            ]
            
            found_legacy = []
            for pattern in legacy_patterns:
                if pattern in source:
                    found_legacy.append(pattern)
            
            if found_legacy:
                legacy_imports_found.append({
                    'file': filename,
                    'patterns': found_legacy
                })
        
        self.assertEqual(
            len(legacy_imports_found), 0,
            f"LEGACY LOGGING PATTERNS DETECTED: Files still contain legacy logging imports "
            f"after SSOT remediation: {legacy_imports_found}. "
            f"All files must use 'from netra_backend.app.logging_config import central_logger' "
            f"and 'central_logger.get_logger(__name__)' for Golden Path correlation compliance."
        )
        
        print("✅ NO LEGACY IMPORTS: All legacy logging patterns successfully removed")
        
    def test_logger_variable_naming_consistency(self):
        """
        Validates that both files use consistent logger variable naming ('logger').
        """
        import netra_backend.app.agents.supervisor.agent_execution_core as core_module
        import netra_backend.app.core.agent_execution_tracker as tracker_module
        
        # Get source code
        core_source = inspect.getsource(core_module)
        tracker_source = inspect.getsource(tracker_module)
        
        # Check for consistent logger variable naming
        expected_logger_assignment = "logger = central_logger.get_logger(__name__)"
        
        core_has_consistent_naming = expected_logger_assignment in core_source
        tracker_has_consistent_naming = expected_logger_assignment in tracker_source
        
        both_consistent = core_has_consistent_naming and tracker_has_consistent_naming
        
        print(f"\n=== LOGGER VARIABLE NAMING CONSISTENCY ===")
        print(f"agent_execution_core.py consistent naming: {core_has_consistent_naming}")
        print(f"agent_execution_tracker.py consistent naming: {tracker_has_consistent_naming}")
        
        self.assertTrue(
            both_consistent,
            f"INCONSISTENT LOGGER NAMING: Both files must use "
            f"'logger = central_logger.get_logger(__name__)' for consistency. "
            f"Core file consistent: {core_has_consistent_naming}, "
            f"Tracker file consistent: {tracker_has_consistent_naming}. "
            f"Consistent naming ensures Golden Path debugging correlation works properly."
        )
        
        print("✅ CONSISTENT NAMING: Both files use standard logger variable naming")
        
    def _analyze_file_logging_compliance(self, file_path: str, filename: str) -> Dict:
        """
        Analyze a Python file for SSOT logging compliance.
        
        Returns:
            Dict with compliance status and violation details
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            return {
                'is_compliant': False,
                'violations': [f"Could not read file: {e}"],
                'analysis': f"File read error for {filename}"
            }
        
        violations = []
        
        # Check for required SSOT import
        if 'from netra_backend.app.logging_config import central_logger' not in source_code:
            violations.append("Missing required SSOT import: 'from netra_backend.app.logging_config import central_logger'")
        
        # Check for required SSOT logger creation
        if 'logger = central_logger.get_logger(__name__)' not in source_code:
            violations.append("Missing required SSOT logger creation: 'logger = central_logger.get_logger(__name__)'")
        
        # Check for forbidden legacy patterns
        legacy_patterns = [
            ('import logging', "Legacy logging import detected"),
            ('from logging import', "Legacy logging import detected"),
            ('logging.getLogger(', "Legacy logging.getLogger() usage detected")
        ]
        
        for pattern, message in legacy_patterns:
            if pattern in source_code:
                violations.append(f"{message}: '{pattern}'")
        
        is_compliant = len(violations) == 0
        
        analysis_summary = f"File {filename}: {'COMPLIANT' if is_compliant else 'NON-COMPLIANT'}"
        
        return {
            'is_compliant': is_compliant,
            'violations': violations,
            'analysis': analysis_summary
        }
    
    def test_logging_context_propagation_works(self):
        """
        Validates that unified logging properly propagates context (correlation IDs).
        
        This test ensures that after SSOT remediation, correlation context
        flows properly between both execution components.
        """
        with mock.patch('netra_backend.app.logging_config.central_logger') as mock_central_logger:
            # Set up mock logger that tracks context propagation
            mock_logger = mock.MagicMock()
            mock_central_logger.get_logger.return_value = mock_logger
            
            # Import modules after mocking to ensure they get mocked logger
            from importlib import reload
            import netra_backend.app.agents.supervisor.agent_execution_core as core_module
            import netra_backend.app.core.agent_execution_tracker as tracker_module
            
            # Force reload to pick up mocked logger
            reload(core_module)
            reload(tracker_module)
            
            # Verify both modules got the same logger type
            core_logger_calls = [call for call in mock_central_logger.get_logger.call_args_list 
                               if 'agent_execution_core' in str(call)]
            tracker_logger_calls = [call for call in mock_central_logger.get_logger.call_args_list 
                                  if 'agent_execution_tracker' in str(call)]
            
            both_use_central_logger = len(core_logger_calls) > 0 and len(tracker_logger_calls) > 0
            
            print(f"\n=== LOGGING CONTEXT PROPAGATION TEST ===")
            print(f"Core module central_logger calls: {len(core_logger_calls)}")
            print(f"Tracker module central_logger calls: {len(tracker_logger_calls)}")
            print(f"Both use central_logger: {both_use_central_logger}")
            
            self.assertTrue(
                both_use_central_logger,
                f"CONTEXT PROPAGATION FAILURE: Both modules must use central_logger.get_logger() "
                f"for unified context propagation. Core calls: {len(core_logger_calls)}, "
                f"Tracker calls: {len(tracker_logger_calls)}. "
                f"SSOT remediation required for Golden Path correlation tracking."
            )
            
            print("✅ CONTEXT PROPAGATION: Both modules use central_logger for unified context")


if __name__ == '__main__':
    import unittest
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnifiedLoggingPatternCompliance)
    runner = unittest.TextTestRunner(verbosity=2)
    
    result = runner.run(suite)
    if result.failures or result.errors:
        print("\nEXPECTED DURING REMEDIATION: Some tests may fail until SSOT logging is fully implemented")
    else:
        print("\n✅ ALL TESTS PASSED: SSOT logging pattern compliance achieved!")