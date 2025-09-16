"""
Test Suite: WebSocket Manager Import Path Violations Detection (Issue #1104)

MISSION: 20% NEW SSOT validation tests to detect files using LEGACY import paths
STATUS: FAILING TEST - Proves Issue #1104 exists

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: SSOT Compliance & Race Condition Prevention
- Value Impact: Protects $500K+ ARR WebSocket functionality from race conditions
- Strategic Impact: Prevents import path fragmentation causing initialization failures

This test suite detects files using legacy WebSocketManager import paths that cause
race conditions and initialization failures. The tests are designed to FAIL until
Issue #1104 is resolved through import path consolidation.

CRITICAL: These are FAILING tests that prove the issue exists.
They should fail until import paths are consolidated to use SSOT unified_manager.
"""

import pytest
import os
import re
from typing import Dict, List, Set
from pathlib import Path

import unittest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class WebSocketManagerImportPathViolationsTests(SSotBaseTestCase):
    """Test suite to detect WebSocket Manager import path violations."""

    # CRITICAL: Files with legacy import paths (should cause failures)
    LEGACY_IMPORT_FILES = {
        "dependencies.py": "netra_backend/app/dependencies.py",
        "agent_websocket_bridge.py": "netra_backend/app/services/agent_websocket_bridge.py", 
        "agent_instance_factory.py": "netra_backend/app/agents/supervisor/agent_instance_factory.py"
    }

    # SSOT import pattern (correct)
    SSOT_IMPORT_PATTERN = "from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager"
    
    # Legacy import patterns (violating SSOT)
    LEGACY_IMPORT_PATTERNS = [
        "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
        "from netra_backend.app.websocket_core import WebSocketManager"
    ]

    @classmethod
    def setUpClass(cls):
        """Set up test class environment."""
        super().setUpClass() if hasattr(super(), 'setUpClass') else None
        
        # Get project root from current working directory
        import os
        current_dir = Path(os.getcwd())
        
        # Navigate to project root (should be netra-apex)
        if current_dir.name == "netra-apex":
            cls.project_root = current_dir
        else:
            # Try to find netra-apex in parent directories
            potential_root = current_dir
            while potential_root.parent != potential_root:
                if potential_root.name == "netra-apex":
                    cls.project_root = potential_root
                    break
                potential_root = potential_root.parent
            else:
                # Fallback to absolute path
                cls.project_root = Path("/Users/anthony/Desktop/netra-apex")
        
        cls.backend_root = cls.project_root / "netra_backend"
        
        # Ensure project structure exists
        if not cls.backend_root.exists():
            raise unittest.SkipTest(f"Backend root not found: {cls.backend_root}. Test requires netra-apex project structure.")
        
        logger.info(f"Testing WebSocket Manager import violations in: {cls.backend_root}")

    def setUp(self):
        """Set up individual test."""
        super().setUp() if hasattr(super(), 'setUp') else None

    def test_detect_legacy_import_violations_in_dependencies(self):
        """FAILING TEST: Detect legacy WebSocket Manager imports in dependencies.py"""
        # Initialize paths if not set by setUpClass
        if not hasattr(self, 'backend_root'):
            import os
            current_dir = Path(os.getcwd())
            
            # Navigate to project root (should be netra-apex)
            if current_dir.name == "netra-apex":
                self.project_root = current_dir
            else:
                # Try to find netra-apex in parent directories
                potential_root = current_dir
                while potential_root.parent != potential_root:
                    if potential_root.name == "netra-apex":
                        self.project_root = potential_root
                        break
                    potential_root = potential_root.parent
                else:
                    # Fallback to absolute path
                    self.project_root = Path("/Users/anthony/Desktop/netra-apex")
            
            self.backend_root = self.project_root / "netra_backend"
        
        file_path = self.backend_root / "app" / "dependencies.py"
        
        if not file_path.exists():
            self.fail(f"Critical file not found: {file_path}")
        
        violations = self._scan_file_for_legacy_imports(file_path)
        
        # This test should FAIL because dependencies.py has legacy imports
        self.assertEqual(len(violations), 0, 
            f"ISSUE #1104: dependencies.py has {len(violations)} legacy WebSocket Manager import violations:\n" +
            "\n".join([f"  Line {line}: {import_line}" for line, import_line in violations]) +
            f"\n\nExpected: SSOT unified_manager import pattern" +
            f"\nFound: Legacy websocket_manager import patterns" +
            f"\nImpact: Causes race conditions during WebSocket initialization" +
            f"\nFix: Replace with 'from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager'"
        )

    def test_detect_legacy_import_violations_in_agent_websocket_bridge(self):
        """FAILING TEST: Detect legacy WebSocket Manager imports in agent_websocket_bridge.py"""
        file_path = self.backend_root / "app" / "services" / "agent_websocket_bridge.py"
        
        if not file_path.exists():
            self.fail(f"Critical file not found: {file_path}")
        
        violations = self._scan_file_for_legacy_imports(file_path)
        
        # This test should FAIL because agent_websocket_bridge.py has legacy imports
        self.assertEqual(len(violations), 0, 
            f"ISSUE #1104: agent_websocket_bridge.py has {len(violations)} legacy WebSocket Manager import violations:\n" +
            "\n".join([f"  Line {line}: {import_line}" for line, import_line in violations]) +
            f"\n\nExpected: SSOT unified_manager import pattern" +
            f"\nFound: Legacy websocket_manager import patterns" +
            f"\nImpact: Causes race conditions in WebSocket bridge initialization" +
            f"\nFix: Replace with 'from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager'"
        )

    def test_detect_legacy_import_violations_in_agent_instance_factory(self):
        """FAILING TEST: Detect legacy WebSocket Manager imports in agent_instance_factory.py"""
        file_path = self.backend_root / "app" / "agents" / "supervisor" / "agent_instance_factory.py"
        
        if not file_path.exists():
            self.fail(f"Critical file not found: {file_path}")
        
        violations = self._scan_file_for_legacy_imports(file_path)
        
        # This test should FAIL because agent_instance_factory.py has legacy imports
        self.assertEqual(len(violations), 0, 
            f"ISSUE #1104: agent_instance_factory.py has {len(violations)} legacy WebSocket Manager import violations:\n" +
            "\n".join([f"  Line {line}: {import_line}" for line, import_line in violations]) +
            f"\n\nExpected: SSOT unified_manager import pattern" +
            f"\nFound: Legacy websocket_manager import patterns" +
            f"\nImpact: Causes race conditions in agent instance creation" +
            f"\nFix: Replace with 'from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager'"
        )

    def test_comprehensive_legacy_import_scan(self):
        """FAILING TEST: Comprehensive scan for ALL legacy import violations."""
        # Initialize paths if not set
        if not hasattr(self, 'project_root'):
            import os
            current_dir = Path(os.getcwd())
            
            if current_dir.name == "netra-apex":
                self.project_root = current_dir
            else:
                potential_root = current_dir
                while potential_root.parent != potential_root:
                    if potential_root.name == "netra-apex":
                        self.project_root = potential_root
                        break
                    potential_root = potential_root.parent
                else:
                    self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        
        all_violations = {}
        total_violations = 0
        
        # Scan all known problematic files
        for file_name, relative_path in self.LEGACY_IMPORT_FILES.items():
            file_path = self.project_root / relative_path
            
            if file_path.exists():
                violations = self._scan_file_for_legacy_imports(file_path)
                if violations:
                    all_violations[relative_path] = violations
                    total_violations += len(violations)
        
        # This test should FAIL showing ALL violations across files
        self.assertEqual(total_violations, 0,
            f"ISSUE #1104: Found {total_violations} total legacy WebSocket Manager import violations across {len(all_violations)} files:\n\n" +
            self._format_violation_report(all_violations) +
            f"\n\nCRITICAL IMPACT:" +
            f"\n- Race conditions during WebSocket initialization" +
            f"\n- Inconsistent WebSocket manager instances" +
            f"\n- $500K+ ARR WebSocket functionality at risk" +
            f"\n\nREQUIRED FIX:" +
            f"\n- Consolidate ALL imports to use unified_manager SSOT pattern" +
            f"\n- Replace websocket_manager imports with unified_manager imports" +
            f"\n- Test WebSocket initialization after consolidation"
        )

    def test_ssot_import_compliance_validation(self):
        """Test that validates SSOT import compliance (this should pass when correct)."""
        # Check websocket_bridge_factory.py has correct SSOT import
        ssot_file = self.backend_root / "app" / "factories" / "websocket_bridge_factory.py"
        
        if not ssot_file.exists():
            self.fail(f"SSOT reference file not found: {ssot_file}")
        
        content = ssot_file.read_text()
        
        # This should pass - websocket_bridge_factory.py uses correct import
        ssot_import_found = self.SSOT_IMPORT_PATTERN in content
        
        self.assertTrue(ssot_import_found,
            f"SSOT reference file missing unified_manager import pattern!\n" +
            f"File: {ssot_file}\n" +
            f"Expected: {self.SSOT_IMPORT_PATTERN}\n" +
            f"This indicates the SSOT pattern itself may be incorrect."
        )
        
        # Count legacy patterns (should be 0 in SSOT file)
        legacy_violations = self._scan_file_for_legacy_imports(ssot_file)
        
        self.assertEqual(len(legacy_violations), 0,
            f"SSOT reference file has legacy import violations: {legacy_violations}\n" +
            f"File: {ssot_file}\n" +
            f"SSOT files must use unified patterns only."
        )

    def _scan_file_for_legacy_imports(self, file_path: Path) -> List[tuple]:
        """Scan a file for legacy WebSocket Manager import patterns.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            List of (line_number, import_line) tuples for violations
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for legacy import patterns
                for legacy_pattern in self.LEGACY_IMPORT_PATTERNS:
                    if legacy_pattern in line:
                        violations.append((line_num, line))
                        logger.warning(f"Legacy import found in {file_path}:{line_num}: {line}")
        
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            self.fail(f"Could not scan file {file_path}: {e}")
        
        return violations

    def _format_violation_report(self, violations: Dict[str, List[tuple]]) -> str:
        """Format a comprehensive violation report.
        
        Args:
            violations: Dict of {file_path: [(line_num, line)]}
            
        Returns:
            Formatted violation report string
        """
        report_lines = []
        
        for file_path, file_violations in violations.items():
            report_lines.append(f"FILE: {file_path}")
            for line_num, line in file_violations:
                report_lines.append(f"  Line {line_num}: {line}")
            report_lines.append("")
        
        return "\n".join(report_lines)

    def test_websocket_manager_import_fragmentation_analysis(self):
        """FAILING TEST: Analyze the fragmentation of WebSocket Manager imports."""
        fragmentation_analysis = {
            'legacy_patterns_found': [],
            'ssot_patterns_found': [],
            'total_files_scanned': 0,
            'files_with_violations': 0,
            'fragmentation_severity': 'LOW'
        }
        
        # Scan for both legacy and SSOT patterns across key files
        for file_name, relative_path in self.LEGACY_IMPORT_FILES.items():
            file_path = self.project_root / relative_path
            
            if not file_path.exists():
                continue
                
            fragmentation_analysis['total_files_scanned'] += 1
            
            try:
                content = file_path.read_text()
                
                # Check for legacy patterns
                legacy_found = any(pattern in content for pattern in self.LEGACY_IMPORT_PATTERNS)
                if legacy_found:
                    fragmentation_analysis['legacy_patterns_found'].append(relative_path)
                    fragmentation_analysis['files_with_violations'] += 1
                
                # Check for SSOT patterns  
                ssot_found = self.SSOT_IMPORT_PATTERN in content
                if ssot_found:
                    fragmentation_analysis['ssot_patterns_found'].append(relative_path)
                    
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
        
        # Determine fragmentation severity
        violation_ratio = fragmentation_analysis['files_with_violations'] / max(1, fragmentation_analysis['total_files_scanned'])
        if violation_ratio >= 0.5:
            fragmentation_analysis['fragmentation_severity'] = 'HIGH'
        elif violation_ratio >= 0.25:
            fragmentation_analysis['fragmentation_severity'] = 'MEDIUM'
        
        # This test should FAIL showing high fragmentation
        self.assertEqual(fragmentation_analysis['files_with_violations'], 0,
            f"ISSUE #1104: WebSocket Manager import fragmentation detected!\n\n" +
            f"FRAGMENTATION ANALYSIS:\n" +
            f"- Severity: {fragmentation_analysis['fragmentation_severity']}\n" +
            f"- Files scanned: {fragmentation_analysis['total_files_scanned']}\n" +
            f"- Files with violations: {fragmentation_analysis['files_with_violations']}\n" +
            f"- Violation ratio: {violation_ratio:.1%}\n\n" +
            f"FILES WITH LEGACY PATTERNS:\n" +
            "\n".join([f"  - {f}" for f in fragmentation_analysis['legacy_patterns_found']]) +
            f"\n\nFILES WITH SSOT PATTERNS:\n" +
            "\n".join([f"  - {f}" for f in fragmentation_analysis['ssot_patterns_found']]) +
            f"\n\nIMPACT:\n" +
            f"- Race conditions during WebSocket initialization\n" +
            f"- Inconsistent WebSocket manager instances\n" +
            f"- Import resolution conflicts\n" +
            f"- $500K+ ARR WebSocket functionality at risk\n\n" +
            f"CONSOLIDATION REQUIRED:\n" +
            f"- All files must use unified_manager SSOT import pattern\n" +
            f"- Remove websocket_manager legacy imports\n" +
            f"- Validate WebSocket initialization after consolidation"
        )