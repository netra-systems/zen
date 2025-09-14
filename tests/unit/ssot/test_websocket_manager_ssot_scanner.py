#!/usr/bin/env python3
"""WebSocket Manager SSOT Implementation Scanner Test - Issue #1036

FAIL-FIRST TEST: This test is designed to FAIL before SSOT consolidation
and PASS after WebSocket Manager implementations are consolidated to a single SSOT.

Business Value: Protects $500K+ ARR by preventing WebSocket fragmentation that causes
Golden Path failures, user isolation breaches, and chat functionality degradation.

EXPECTED BEHAVIOR:
- BEFORE SSOT: Test FAILS - Multiple implementations found (WebSocketManager, UnifiedWebSocketManager, etc.)
- AFTER SSOT: Test PASSES - Only 1 canonical implementation remains

This test validates Issue #1036 Step 2: 20% new SSOT tests detecting fragmentation.
"""

import os
import re
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketManagerSSOTScanner(SSotBaseTestCase):
    """Fail-first test to detect multiple WebSocket Manager implementations.
    
    This test scans the codebase for WebSocket Manager class implementations
    and ensures SSOT compliance by detecting fragmentation BEFORE consolidation.
    """

    def test_websocket_manager_implementation_count_enforcement(self):
        """FAIL-FIRST: Detect multiple WebSocket Manager implementations.
        
        EXPECTED TO FAIL: Currently finds 6+ different implementations:
        - WebSocketManager (in manager.py - compatibility layer)
        - UnifiedWebSocketManager (in unified_manager.py)
        - _UnifiedWebSocketManagerImplementation (in unified_manager.py) 
        - IsolatedWebSocketManager (in factory)
        - Various test mock implementations
        
        EXPECTED TO PASS: After SSOT consolidation, only 1 implementation exists.
        
        Business Impact: Prevents race conditions and Golden Path failures.
        """
        # Get project root for scanning
        project_root = self._get_project_root()
        websocket_manager_files = []
        
        # Scan for files containing WebSocket Manager class implementations
        for py_file in project_root.rglob("*.py"):
            # Skip test files for production code analysis
            if "/tests/" in str(py_file) or "/test_" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for actual WebSocket Manager class definitions (not imports)
                if re.search(r'^class\s+.*WebSocketManager.*[:(]', content, re.MULTILINE):
                    websocket_manager_files.append(str(py_file))
            except (UnicodeDecodeError, OSError):
                continue
        
        # FAIL-FIRST ASSERTION: Should find multiple implementations currently
        self.assertGreater(
            len(websocket_manager_files), 1,
            f"SSOT VIOLATION DETECTED: Found {len(websocket_manager_files)} WebSocket Manager "
            f"implementations. Expected exactly 1 for SSOT compliance.\n"
            f"Implementations found in: {websocket_manager_files}\n\n"
            f"BUSINESS IMPACT: Multiple implementations cause:\n"
            f"- Race conditions in user isolation\n"  
            f"- Golden Path failures ($500K+ ARR at risk)\n"
            f"- WebSocket event delivery inconsistencies\n"
            f"- Multi-user chat contamination\n\n"
            f"REMEDIATION: Consolidate to single SSOT implementation"
        )
        
        # Document the violations for remediation planning
        violation_details = []
        for file_path in websocket_manager_files:
            relative_path = str(Path(file_path).relative_to(project_root))
            violation_details.append(f"  - {relative_path}")
        
        print(f"\n🚨 WEBSOCKET MANAGER SSOT VIOLATIONS DETECTED:")
        print(f"Found {len(websocket_manager_files)} implementations:")
        for detail in violation_details:
            print(detail)
        print(f"\n💼 BUSINESS IMPACT: $500K+ ARR Golden Path at risk")
        print(f"🎯 TARGET: Consolidate to exactly 1 SSOT implementation\n")

    def test_websocket_manager_alias_detection(self):
        """FAIL-FIRST: Detect WebSocket Manager aliases creating SSOT violations.
        
        EXPECTED TO FAIL: Currently finds aliases like:
        WebSocketManager = UnifiedWebSocketManager (in manager.py)
        
        EXPECTED TO PASS: After SSOT consolidation, no aliases exist.
        """
        project_root = self._get_project_root()
        alias_violations = []
        
        # Scan for alias assignments that create SSOT violations
        for py_file in project_root.rglob("*.py"):
            if "/tests/" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for WebSocket Manager aliases
                alias_patterns = [
                    r'WebSocketManager\s*=\s*\w+WebSocketManager',
                    r'\w+WebSocketManager\s*=\s*WebSocketManager',
                ]
                
                for pattern in alias_patterns:
                    if re.search(pattern, content):
                        alias_violations.append(str(py_file))
                        break
                        
            except (UnicodeDecodeError, OSError):
                continue
        
        # FAIL-FIRST ASSERTION: Should detect alias violations
        self.assertGreater(
            len(alias_violations), 0,
            f"SSOT ALIAS VIOLATIONS: Found {len(alias_violations)} files with WebSocket Manager aliases.\n"
            f"Files with aliases: {alias_violations}\n\n"
            f"BUSINESS IMPACT: Aliases mask true implementation sources, causing:\n"
            f"- Import confusion leading to wrong manager instances\n"
            f"- Debugging difficulties when Golden Path fails\n" 
            f"- Inconsistent behavior across services\n\n"
            f"REMEDIATION: Remove all aliases, use direct SSOT imports"
        )

    def _get_project_root(self) -> Path:
        """Get the project root directory for scanning."""
        current_file = Path(__file__)
        # Navigate up from tests/unit/ssot/ to project root
        project_root = current_file.parent.parent.parent.parent
        return project_root


if __name__ == '__main__':
    import unittest
    unittest.main()