"""
Test Suite: WebSocket Manager SSOT Import Consolidation Validation (Issue #1104)

MISSION: 20% NEW SSOT validation tests to validate unified import consolidation
STATUS: FAILING TEST - Proves import path fragmentation exists

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: SSOT Compliance & Import Consolidation
- Value Impact: Ensures single source of truth for WebSocket Manager imports
- Strategic Impact: Protects $500K+ ARR by preventing import-related race conditions

This test suite validates that ALL WebSocket Manager imports use the canonical SSOT
unified_manager pattern. Tests are designed to FAIL until Issue #1104 is resolved
through complete import path consolidation.

CRITICAL: These are FAILING tests that prove import fragmentation exists.
They should fail until ALL imports are consolidated to the SSOT pattern.
"""

import pytest
import ast
import os
from typing import Dict, List, Set, Tuple
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class TestWebSocketManagerSSotCompliance(SSotBaseTestCase):
    """Test suite to validate SSOT compliance for WebSocket Manager imports."""

    # CANONICAL SSOT import patterns (these are the ONLY allowed patterns)
    SSOT_IMPORT_PATTERNS = {
        "unified_manager_import": "from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager",
        "unified_manager_alias": "from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as WebSocketManager"
    }

    # PROHIBITED legacy import patterns
    PROHIBITED_IMPORT_PATTERNS = {
        "websocket_manager_direct": "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
        "websocket_manager_module": "from netra_backend.app.websocket_core import WebSocketManager",
        "websocket_manager_star": "from netra_backend.app.websocket_core.websocket_manager import *",
        "websocket_core_star": "from netra_backend.app.websocket_core import *"
    }

    # Files that MUST comply with SSOT import patterns
    CRITICAL_FILES = [
        "netra_backend/app/dependencies.py",
        "netra_backend/app/services/agent_websocket_bridge.py",
        "netra_backend/app/agents/supervisor/agent_instance_factory.py",
        "netra_backend/app/factories/websocket_bridge_factory.py"
    ]

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.backend_root = self.project_root / "netra_backend"
        
        # Validate project structure
        if not self.backend_root.exists():
            self.fail(f"Backend root not found: {self.backend_root}")
        
        logger.info(f"Testing SSOT compliance for WebSocket Manager imports in: {self.backend_root}")

    def test_ssot_import_consolidation_enforcement(self):
        """FAILING TEST: Enforce that ALL WebSocket Manager imports use SSOT patterns."""
        
        consolidation_violations = {}
        total_violations = 0
        
        for file_path in self.CRITICAL_FILES:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                consolidation_violations[file_path] = [("FILE_MISSING", "Critical file not found")]
                total_violations += 1
                continue
            
            violations = self._analyze_import_consolidation(full_path)
            if violations:
                consolidation_violations[file_path] = violations
                total_violations += len(violations)
        
        # This test should FAIL until ALL files use SSOT imports
        self.assertEqual(total_violations, 0,
            f"ISSUE #1104: WebSocket Manager import consolidation violations detected!\n\n" +
            f"TOTAL VIOLATIONS: {total_violations} across {len(consolidation_violations)} files\n\n" +
            self._format_consolidation_report(consolidation_violations) +
            f"\n\nSSOT CONSOLIDATION REQUIREMENTS:\n" +
            f"✅ REQUIRED: {self.SSOT_IMPORT_PATTERNS['unified_manager_alias']}\n" +
            f"❌ PROHIBITED: All legacy websocket_manager imports\n\n" +
            f"BUSINESS IMPACT:\n" +
            f"- Import fragmentation causes race conditions\n" +
            f"- Multiple WebSocket manager instances created\n" +
            f"- $500K+ ARR WebSocket functionality compromised\n" +
            f"- Inconsistent initialization order\n\n" +
            f"CONSOLIDATION ACTIONS:\n" +
            f"1. Replace ALL websocket_manager imports with unified_manager imports\n" +
            f"2. Ensure WebSocket manager alias consistency\n" +
            f"3. Test WebSocket initialization after consolidation\n" +
            f"4. Validate no race conditions in integration tests"
        )

    def test_prohibit_legacy_websocket_manager_imports(self):
        """FAILING TEST: Ensure NO legacy websocket_manager imports exist."""
        
        legacy_violations = {}
        total_legacy_imports = 0
        
        for file_path in self.CRITICAL_FILES:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
                
            legacy_imports = self._scan_for_legacy_imports(full_path)
            if legacy_imports:
                legacy_violations[file_path] = legacy_imports
                total_legacy_imports += len(legacy_imports)
        
        # This test should FAIL showing ALL legacy imports that must be removed
        self.assertEqual(total_legacy_imports, 0,
            f"ISSUE #1104: {total_legacy_imports} legacy websocket_manager imports found!\n\n" +
            f"LEGACY IMPORT VIOLATIONS:\n" +
            self._format_legacy_violations_report(legacy_violations) +
            f"\n\nPROHIBITED PATTERNS:\n" +
            "\n".join([f"❌ {pattern}" for pattern in self.PROHIBITED_IMPORT_PATTERNS.values()]) +
            f"\n\nREQUIRED SSOT PATTERN:\n" +
            f"✅ {self.SSOT_IMPORT_PATTERNS['unified_manager_alias']}\n\n" +
            f"CRITICAL IMPACT:\n" +
            f"- Legacy imports create separate WebSocket manager instances\n" +
            f"- Race conditions during initialization\n" +
            f"- Event delivery inconsistencies\n" +
            f"- WebSocket connection state fragmentation\n\n" +
            f"IMMEDIATE ACTIONS REQUIRED:\n" +
            f"1. Remove ALL legacy websocket_manager imports\n" +
            f"2. Replace with unified_manager SSOT imports\n" +
            f"3. Test WebSocket manager singleton behavior\n" +
            f"4. Validate event delivery consistency"
        )

    def test_validate_ssot_import_pattern_usage(self):
        """FAILING TEST: Validate that SSOT import patterns are used correctly."""
        
        ssot_compliance = {}
        non_compliant_files = 0
        
        for file_path in self.CRITICAL_FILES:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            compliance_status = self._validate_ssot_pattern_usage(full_path)
            ssot_compliance[file_path] = compliance_status
            
            if not compliance_status['is_compliant']:
                non_compliant_files += 1
        
        # This test should FAIL until ALL files are SSOT compliant
        self.assertEqual(non_compliant_files, 0,
            f"ISSUE #1104: {non_compliant_files} files are not SSOT compliant!\n\n" +
            f"SSOT COMPLIANCE ANALYSIS:\n" +
            self._format_ssot_compliance_report(ssot_compliance) +
            f"\n\nSSOT REQUIREMENTS:\n" +
            f"✅ Use unified_manager import with WebSocketManager alias\n" +
            f"✅ Import exactly once per file (no duplicate imports)\n" +
            f"✅ Use consistent alias naming (WebSocketManager)\n" +
            f"❌ No websocket_manager legacy imports allowed\n\n" +
            f"COMPLIANCE BENEFITS:\n" +
            f"- Single source of truth for WebSocket manager\n" +
            f"- Consistent initialization patterns\n" +
            f"- Reduced race condition risk\n" +
            f"- Reliable WebSocket functionality\n\n" +
            f"COMPLIANCE ACTIONS:\n" +
            f"1. Standardize ALL imports to unified_manager pattern\n" +
            f"2. Remove duplicate or inconsistent imports\n" +
            f"3. Validate WebSocket manager behavior consistency\n" +
            f"4. Test multi-user WebSocket isolation"
        )

    def test_import_consolidation_across_websocket_modules(self):
        """FAILING TEST: Validate import consolidation across ALL WebSocket-related modules."""
        
        websocket_modules = self._discover_websocket_related_files()
        consolidation_status = {}
        fragmented_modules = 0
        
        for module_path in websocket_modules:
            full_path = self.project_root / module_path
            
            if not full_path.exists():
                continue
            
            module_analysis = self._analyze_websocket_imports(full_path)
            consolidation_status[module_path] = module_analysis
            
            if module_analysis['has_fragmentation']:
                fragmented_modules += 1
        
        # This test should FAIL showing widespread fragmentation
        self.assertEqual(fragmented_modules, 0,
            f"ISSUE #1104: WebSocket import fragmentation across {fragmented_modules} modules!\n\n" +
            f"FRAGMENTATION ANALYSIS:\n" +
            f"Total WebSocket modules analyzed: {len(websocket_modules)}\n" +
            f"Modules with fragmented imports: {fragmented_modules}\n" +
            f"Fragmentation rate: {fragmented_modules/max(1, len(websocket_modules)):.1%}\n\n" +
            self._format_module_fragmentation_report(consolidation_status) +
            f"\n\nFRAGMENTATION RISKS:\n" +
            f"- Multiple WebSocket manager instances\n" +
            f"- Inconsistent event delivery\n" +
            f"- Race conditions in initialization\n" +
            f"- Memory leaks from duplicate managers\n" +
            f"- WebSocket connection state corruption\n\n" +
            f"CONSOLIDATION STRATEGY:\n" +
            f"1. Identify ALL WebSocket manager import locations\n" +
            f"2. Replace with unified_manager SSOT pattern\n" +
            f"3. Validate singleton behavior across modules\n" +
            f"4. Test WebSocket functionality after consolidation\n" +
            f"5. Monitor for race conditions in integration tests"
        )

    def test_websocket_manager_alias_consistency(self):
        """FAILING TEST: Validate WebSocket Manager alias consistency across files."""
        
        alias_analysis = {}
        inconsistent_aliases = 0
        
        for file_path in self.CRITICAL_FILES:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                continue
            
            aliases = self._extract_websocket_manager_aliases(full_path)
            alias_analysis[file_path] = aliases
            
            # Check for inconsistent aliasing
            if len(set(aliases)) > 1:
                inconsistent_aliases += 1
        
        # This test should FAIL if aliases are inconsistent
        self.assertEqual(inconsistent_aliases, 0,
            f"ISSUE #1104: Inconsistent WebSocket Manager aliases detected!\n\n" +
            f"ALIAS CONSISTENCY ANALYSIS:\n" +
            self._format_alias_analysis_report(alias_analysis) +
            f"\n\nREQUIRED ALIAS CONSISTENCY:\n" +
            f"✅ Standard alias: WebSocketManager (from UnifiedWebSocketManager)\n" +
            f"❌ Inconsistent aliases cause import confusion\n\n" +
            f"INCONSISTENCY RISKS:\n" +
            f"- Developer confusion about correct import\n" +
            f"- Multiple aliases for same functionality\n" +
            f"- Potential for mixed usage patterns\n" +
            f"- Import resolution conflicts\n\n" +
            f"CONSISTENCY REQUIREMENTS:\n" +
            f"1. Use 'WebSocketManager' alias consistently\n" +
            f"2. Import from unified_manager module only\n" +
            f"3. Remove alternative aliases and imports\n" +
            f"4. Document the canonical import pattern"
        )

    def _analyze_import_consolidation(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """Analyze a file for import consolidation violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for prohibited patterns
                for pattern_name, pattern in self.PROHIBITED_IMPORT_PATTERNS.items():
                    if pattern in line_stripped:
                        violations.append((line_num, pattern_name, line_stripped))
                
                # Check for missing SSOT patterns (if WebSocket imports exist)
                if "websocket" in line_stripped.lower() and "import" in line_stripped:
                    # If this is a WebSocket import but not SSOT compliant
                    is_ssot = any(ssot_pattern in line_stripped for ssot_pattern in self.SSOT_IMPORT_PATTERNS.values())
                    if not is_ssot and any(prohibited in line_stripped for prohibited in self.PROHIBITED_IMPORT_PATTERNS.values()):
                        violations.append((line_num, "NON_SSOT_WEBSOCKET_IMPORT", line_stripped))
        
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            violations.append((0, "ANALYSIS_ERROR", str(e)))
        
        return violations

    def _scan_for_legacy_imports(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """Scan for legacy import patterns."""
        legacy_imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                for pattern_name, pattern in self.PROHIBITED_IMPORT_PATTERNS.items():
                    if pattern in line_stripped:
                        legacy_imports.append((line_num, pattern_name, line_stripped))
        
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            
        return legacy_imports

    def _validate_ssot_pattern_usage(self, file_path: Path) -> Dict:
        """Validate SSOT pattern usage in a file."""
        result = {
            'is_compliant': True,
            'ssot_imports_found': [],
            'legacy_imports_found': [],
            'issues': []
        }
        
        try:
            content = file_path.read_text()
            
            # Check for SSOT patterns
            for pattern_name, pattern in self.SSOT_IMPORT_PATTERNS.items():
                if pattern in content:
                    result['ssot_imports_found'].append(pattern_name)
            
            # Check for legacy patterns
            for pattern_name, pattern in self.PROHIBITED_IMPORT_PATTERNS.items():
                if pattern in content:
                    result['legacy_imports_found'].append(pattern_name)
                    result['is_compliant'] = False
                    result['issues'].append(f"Legacy pattern found: {pattern_name}")
            
            # Check if no WebSocket imports at all
            has_websocket_imports = any(pattern in content for pattern in self.SSOT_IMPORT_PATTERNS.values())
            has_legacy_imports = any(pattern in content for pattern in self.PROHIBITED_IMPORT_PATTERNS.values())
            
            if has_legacy_imports and not has_websocket_imports:
                result['is_compliant'] = False
                result['issues'].append("Has legacy imports but no SSOT imports")
        
        except Exception as e:
            result['is_compliant'] = False
            result['issues'].append(f"Analysis error: {e}")
        
        return result

    def _discover_websocket_related_files(self) -> List[str]:
        """Discover all WebSocket-related files in the project."""
        websocket_files = []
        
        # Add known critical files
        websocket_files.extend(self.CRITICAL_FILES)
        
        # Add additional WebSocket-related files
        additional_files = [
            "netra_backend/app/websocket_core/manager.py",
            "netra_backend/app/websocket_core/unified_manager.py", 
            "netra_backend/app/websocket_core/unified_emitter.py",
            "netra_backend/app/services/websocket_connection_pool.py",
            "netra_backend/app/services/websocket_bridge_factory.py"
        ]
        
        for file_path in additional_files:
            if (self.project_root / file_path).exists():
                websocket_files.append(file_path)
        
        return websocket_files

    def _analyze_websocket_imports(self, file_path: Path) -> Dict:
        """Analyze WebSocket imports in a file."""
        analysis = {
            'has_fragmentation': False,
            'ssot_imports': 0,
            'legacy_imports': 0,
            'total_websocket_imports': 0,
            'fragmentation_details': []
        }
        
        try:
            content = file_path.read_text()
            
            # Count SSOT imports
            for pattern in self.SSOT_IMPORT_PATTERNS.values():
                if pattern in content:
                    analysis['ssot_imports'] += 1
                    analysis['total_websocket_imports'] += 1
            
            # Count legacy imports
            for pattern in self.PROHIBITED_IMPORT_PATTERNS.values():
                if pattern in content:
                    analysis['legacy_imports'] += 1
                    analysis['total_websocket_imports'] += 1
                    analysis['fragmentation_details'].append(f"Legacy: {pattern}")
            
            # Determine fragmentation
            if analysis['legacy_imports'] > 0:
                analysis['has_fragmentation'] = True
            
            if analysis['ssot_imports'] > 1:
                analysis['has_fragmentation'] = True
                analysis['fragmentation_details'].append("Multiple SSOT imports (should be one)")
        
        except Exception as e:
            analysis['has_fragmentation'] = True
            analysis['fragmentation_details'].append(f"Analysis error: {e}")
        
        return analysis

    def _extract_websocket_manager_aliases(self, file_path: Path) -> List[str]:
        """Extract WebSocket Manager aliases from a file."""
        aliases = []
        
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for import aliases
                if 'import' in line and ('WebSocketManager' in line or 'UnifiedWebSocketManager' in line):
                    if ' as ' in line:
                        # Extract alias after 'as'
                        alias_part = line.split(' as ')[-1].strip()
                        alias = alias_part.split()[0].strip(',')  # Handle trailing commas
                        aliases.append(alias)
                    elif 'WebSocketManager' in line and 'UnifiedWebSocketManager' not in line:
                        aliases.append('WebSocketManager')
                    elif 'UnifiedWebSocketManager' in line and ' as ' not in line:
                        aliases.append('UnifiedWebSocketManager')
        
        except Exception as e:
            logger.error(f"Error extracting aliases from {file_path}: {e}")
        
        return aliases

    def _format_consolidation_report(self, violations: Dict) -> str:
        """Format consolidation violation report."""
        report_lines = []
        
        for file_path, file_violations in violations.items():
            report_lines.append(f"📁 FILE: {file_path}")
            for line_num, violation_type, line in file_violations:
                report_lines.append(f"  ❌ Line {line_num} [{violation_type}]: {line}")
            report_lines.append("")
        
        return "\n".join(report_lines)

    def _format_legacy_violations_report(self, violations: Dict) -> str:
        """Format legacy violations report."""
        report_lines = []
        
        for file_path, file_violations in violations.items():
            report_lines.append(f"📁 {file_path}:")
            for line_num, pattern_type, line in file_violations:
                report_lines.append(f"  ❌ Line {line_num} [{pattern_type}]: {line}")
            report_lines.append("")
        
        return "\n".join(report_lines)

    def _format_ssot_compliance_report(self, compliance: Dict) -> str:
        """Format SSOT compliance report."""
        report_lines = []
        
        for file_path, status in compliance.items():
            compliance_icon = "✅" if status['is_compliant'] else "❌"
            report_lines.append(f"{compliance_icon} {file_path}: {'COMPLIANT' if status['is_compliant'] else 'NON-COMPLIANT'}")
            
            if not status['is_compliant']:
                for issue in status['issues']:
                    report_lines.append(f"    - {issue}")
            
            if status['ssot_imports_found']:
                report_lines.append(f"    ✅ SSOT imports: {', '.join(status['ssot_imports_found'])}")
            
            if status['legacy_imports_found']:
                report_lines.append(f"    ❌ Legacy imports: {', '.join(status['legacy_imports_found'])}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)

    def _format_module_fragmentation_report(self, status: Dict) -> str:
        """Format module fragmentation report."""
        report_lines = []
        
        for module_path, analysis in status.items():
            frag_icon = "❌" if analysis['has_fragmentation'] else "✅"
            report_lines.append(f"{frag_icon} {module_path}:")
            report_lines.append(f"    SSOT imports: {analysis['ssot_imports']}")
            report_lines.append(f"    Legacy imports: {analysis['legacy_imports']}")
            
            if analysis['fragmentation_details']:
                report_lines.append("    Issues:")
                for detail in analysis['fragmentation_details']:
                    report_lines.append(f"      - {detail}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)

    def _format_alias_analysis_report(self, analysis: Dict) -> str:
        """Format alias analysis report."""
        report_lines = []
        
        for file_path, aliases in analysis.items():
            unique_aliases = list(set(aliases))
            consistency_icon = "✅" if len(unique_aliases) <= 1 else "❌"
            report_lines.append(f"{consistency_icon} {file_path}:")
            
            if aliases:
                report_lines.append(f"    Aliases found: {', '.join(aliases)}")
                if len(unique_aliases) > 1:
                    report_lines.append(f"    ⚠️ Inconsistent aliases: {', '.join(unique_aliases)}")
            else:
                report_lines.append("    No WebSocket Manager aliases found")
            
            report_lines.append("")
        
        return "\n".join(report_lines)