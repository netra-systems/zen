#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket SSOT Multiple Managers Violation Detection Test

GitHub Issue: #844 SSOT-incomplete-migration-multiple-websocket-managers

THIS TEST VALIDATES SSOT VIOLATION DETECTION FOR MULTIPLE WEBSOCKET MANAGERS.
Business Value: $500K+ ARR - Detects WebSocket manager SSOT violations that break user isolation

PURPOSE:
- Detect current SSOT violation: multiple WebSocket managers exist (websocket_manager.py vs unified_manager.py)
- Test MUST INITIALLY FAIL to prove violation exists
- Test will PASS after SSOT remediation consolidates managers
- Validate import patterns detect dual manager implementations

CRITICAL VIOLATION DETECTED:
- websocket_manager.py: Acts as wrapper/facade around unified_manager.py
- unified_manager.py: Contains actual implementation
- This creates SSOT violation - two entry points for same functionality

TEST STRATEGY:
1. Scan filesystem for multiple WebSocket manager implementations
2. Detect import patterns that indicate dual managers
3. Validate that only ONE SSOT WebSocket manager should exist
4. This test should FAIL until remediation consolidates managers

BUSINESS IMPACT:
Multiple WebSocket managers create race conditions and inconsistent user isolation,
breaking the Golden Path user flow where users login and get AI responses.
"""

import os
import sys
import re
import ast
import importlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from unittest import mock

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger


class TestWebSocketSSotMultipleManagersViolationDetection(SSotBaseTestCase):
    """Mission Critical: WebSocket SSOT Multiple Managers Violation Detection
    
    This test detects the current SSOT violation where multiple WebSocket managers
    exist simultaneously, creating inconsistent behavior and user isolation failures.
    
    Expected Behavior:
    - This test SHOULD FAIL initially (proving violation exists)
    - This test SHOULD PASS after SSOT remediation (proving fix works)
    """
    
    def setup_method(self, method):
        """Set up test environment for SSOT violation detection."""
        super().setup_method(method)
        self.websocket_core_path = Path(project_root) / "netra_backend" / "app" / "websocket_core"
        self.violation_details = {}
    
    def test_detect_multiple_websocket_manager_files_violation(self):
        """CRITICAL: Detect multiple WebSocket manager file implementations (SHOULD FAIL initially)
        
        This test scans for multiple WebSocket manager files that violate SSOT.
        Expected to FAIL until remediation consolidates managers into single SSOT.
        """
        logger.info("🔍 Scanning for multiple WebSocket manager files...")
        
        # Define expected SSOT state (only ONE manager should exist)
        expected_single_manager = "unified_manager.py"
        violation_files = []
        
        # Scan websocket_core directory for manager files
        if self.websocket_core_path.exists():
            for file_path in self.websocket_core_path.glob("*manager*.py"):
                if file_path.name != expected_single_manager and file_path.name != "__init__.py":
                    violation_files.append(str(file_path))
                    logger.warning(f"🚨 VIOLATION DETECTED: Extra manager file {file_path.name}")
        
        # Check specific known violation
        websocket_manager_path = self.websocket_core_path / "websocket_manager.py"
        if websocket_manager_path.exists():
            violation_files.append(str(websocket_manager_path))
            logger.error(f"🚨 CRITICAL VIOLATION: websocket_manager.py exists alongside unified_manager.py")
        
        self.violation_details['multiple_manager_files'] = violation_files
        
        # ASSERTION: This should FAIL initially, proving violation exists
        assert len(violation_files) == 0, (
            f"SSOT VIOLATION: Multiple WebSocket manager files detected. "
            f"Expected only '{expected_single_manager}', but found: {violation_files}. "
            f"This violates SSOT principle - only ONE WebSocket manager should exist."
        )
    
    def test_detect_websocket_manager_import_duplication_violation(self):
        """CRITICAL: Detect import patterns showing dual manager access (SHOULD FAIL initially)
        
        This test analyzes import patterns to detect code accessing multiple WebSocket managers.
        Expected to FAIL until remediation eliminates dual import paths.
        """
        logger.info("🔍 Scanning for dual WebSocket manager import patterns...")
        
        dual_import_violations = []
        
        # Search for files importing from both managers
        search_paths = [
            Path(project_root) / "netra_backend" / "app",
            Path(project_root) / "tests"
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        
                        # Check for dual imports
                        has_websocket_manager_import = (
                            'from netra_backend.app.websocket_core.websocket_manager import' in content or
                            'import netra_backend.app.websocket_core.websocket_manager' in content
                        )
                        has_unified_manager_import = (
                            'from netra_backend.app.websocket_core.unified_manager import' in content or
                            'import netra_backend.app.websocket_core.unified_manager' in content
                        )
                        
                        if has_websocket_manager_import and has_unified_manager_import:
                            dual_import_violations.append({
                                'file': str(py_file),
                                'violation': 'dual_websocket_manager_imports'
                            })
                            logger.warning(f"🚨 DUAL IMPORT VIOLATION: {py_file}")
                            
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        self.violation_details['dual_import_violations'] = dual_import_violations
        
        # ASSERTION: This should FAIL initially if dual imports exist
        assert len(dual_import_violations) == 0, (
            f"SSOT VIOLATION: Found {len(dual_import_violations)} files with dual WebSocket manager imports. "
            f"Files violating SSOT: {[v['file'] for v in dual_import_violations]}. "
            f"SSOT requires single import path for WebSocket management."
        )
    
    def test_detect_websocket_manager_facade_pattern_violation(self):
        """CRITICAL: Detect facade pattern creating SSOT violation (SHOULD FAIL initially)
        
        This test analyzes websocket_manager.py to detect if it's acting as a facade
        around unified_manager.py, which creates SSOT violation.
        """
        logger.info("🔍 Analyzing websocket_manager.py for facade pattern violation...")
        
        websocket_manager_path = self.websocket_core_path / "websocket_manager.py"
        facade_violations = []
        
        if websocket_manager_path.exists():
            try:
                content = websocket_manager_path.read_text(encoding='utf-8')
                
                # Check for facade pattern indicators
                facade_indicators = [
                    'from netra_backend.app.websocket_core.unified_manager import',
                    'UnifiedWebSocketManager',
                    'import.*unified_manager'
                ]
                
                detected_indicators = []
                for indicator in facade_indicators:
                    if re.search(indicator, content):
                        detected_indicators.append(indicator)
                        logger.warning(f"🚨 FACADE INDICATOR: {indicator}")
                
                if detected_indicators:
                    facade_violations.append({
                        'file': str(websocket_manager_path),
                        'indicators': detected_indicators,
                        'violation_type': 'facade_pattern_ssot_violation'
                    })
                    
            except (UnicodeDecodeError, PermissionError):
                pass
        
        self.violation_details['facade_pattern_violations'] = facade_violations
        
        # ASSERTION: This should FAIL initially if facade pattern exists  
        assert len(facade_violations) == 0, (
            f"SSOT VIOLATION: websocket_manager.py acts as facade around unified_manager.py. "
            f"Detected indicators: {facade_violations}. "
            f"SSOT requires direct use of unified implementation, not wrapper facades."
        )
    
    def test_validate_ssot_websocket_manager_uniqueness(self):
        """CRITICAL: Validate only ONE WebSocket manager exists in SSOT state
        
        This test validates the target SSOT state where only unified_manager.py exists
        as the single source of truth for WebSocket management.
        """
        logger.info("🔍 Validating SSOT WebSocket manager uniqueness...")
        
        # Target SSOT state validation
        unified_manager_path = self.websocket_core_path / "unified_manager.py"
        websocket_manager_path = self.websocket_core_path / "websocket_manager.py"
        
        ssot_violations = []
        
        # Check unified_manager.py exists (required for SSOT)
        if not unified_manager_path.exists():
            ssot_violations.append("unified_manager.py missing - required for SSOT")
            logger.error("🚨 SSOT VIOLATION: unified_manager.py does not exist")
        
        # Check websocket_manager.py does NOT exist in SSOT state
        if websocket_manager_path.exists():
            ssot_violations.append("websocket_manager.py exists - violates SSOT uniqueness")
            logger.error("🚨 SSOT VIOLATION: websocket_manager.py should not exist in SSOT state")
        
        self.violation_details['ssot_uniqueness_violations'] = ssot_violations
        
        # ASSERTION: For SSOT compliance, only unified_manager.py should exist
        assert len(ssot_violations) == 0, (
            f"SSOT VIOLATION: WebSocket manager uniqueness violated. Issues: {ssot_violations}. "
            f"SSOT requires ONLY unified_manager.py to exist as single source of truth."
        )
    
    def test_websocket_manager_consolidation_readiness(self):
        """VALIDATION: Check system readiness for WebSocket manager consolidation
        
        This test validates that consolidation can proceed safely by checking
        dependencies and usage patterns.
        """
        logger.info("🔍 Checking WebSocket manager consolidation readiness...")
        
        consolidation_blockers = []
        
        # Check if websocket_manager.py has unique functionality
        websocket_manager_path = self.websocket_core_path / "websocket_manager.py"
        if websocket_manager_path.exists():
            try:
                content = websocket_manager_path.read_text(encoding='utf-8')
                
                # Look for unique classes/functions not in unified_manager
                unique_patterns = [
                    r'class\s+(?!UnifiedWebSocketManager)\w+',  # Classes other than imports
                    r'def\s+\w+.*:(?!\s*""")',  # Functions with implementation
                    r'async def\s+\w+.*:(?!\s*""")'  # Async functions with implementation
                ]
                
                for pattern in unique_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    if matches:
                        # Filter out simple imports/re-exports
                        real_implementations = [
                            match for match in matches 
                            if not any(keyword in match.lower() for keyword in ['import', 'from'])
                        ]
                        if real_implementations:
                            consolidation_blockers.append({
                                'file': 'websocket_manager.py',
                                'issue': f'Unique implementations found: {real_implementations}',
                                'pattern': pattern
                            })
                            
            except (UnicodeDecodeError, PermissionError):
                pass
        
        # Log consolidation readiness status
        if consolidation_blockers:
            logger.warning(f"⚠️ Consolidation blockers found: {len(consolidation_blockers)}")
            for blocker in consolidation_blockers:
                logger.warning(f"  - {blocker['issue']}")
        else:
            logger.info("✅ No consolidation blockers detected - ready for SSOT remediation")
        
        # This test should provide information but not fail
        # It helps guide the remediation process
        self.violation_details['consolidation_readiness'] = {
            'blockers': consolidation_blockers,
            'ready': len(consolidation_blockers) == 0
        }
    
    def teardown_method(self, method):
        """Clean up and log violation detection results."""
        if self.violation_details:
            logger.info("📊 SSOT Violation Detection Summary:")
            for violation_type, details in self.violation_details.items():
                if isinstance(details, list) and details:
                    logger.warning(f"  - {violation_type}: {len(details)} violations")
                elif isinstance(details, dict):
                    logger.info(f"  - {violation_type}: {details}")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test directly to check SSOT violations
    pytest.main([__file__, "-v", "-s"])