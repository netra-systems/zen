#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket SSOT Import Violations Detection Test

GitHub Issue: #844 SSOT-incomplete-migration-multiple-websocket-managers

THIS TEST DETECTS SSOT IMPORT VIOLATIONS ACROSS THE CODEBASE.
Business Value: $500K+ ARR - Detects import patterns that violate WebSocket SSOT principles

PURPOSE:
- Detect files importing from multiple WebSocket managers (SSOT violation)
- Identify code that bypasses SSOT patterns through direct imports
- Test MUST INITIALLY FAIL to prove violations exist
- Test will PASS after SSOT remediation consolidates imports
- Validate import consistency across the entire codebase

CRITICAL IMPORT VIOLATIONS DETECTED:
- Files importing from both websocket_manager.py AND unified_manager.py
- Direct imports bypassing SSOT factory patterns
- Inconsistent import paths for WebSocket functionality
- Legacy imports that should use SSOT patterns

TEST STRATEGY:
1. Scan all Python files for WebSocket manager imports
2. Detect files using multiple import paths for same functionality
3. Identify non-SSOT import patterns
4. Report violations with specific file locations and line numbers
5. This test should FAIL until import consolidation is complete

BUSINESS IMPACT:
Import violations create inconsistent WebSocket behavior, race conditions,
and user isolation failures that break the Golden Path where users login
and receive AI responses.
"""

import os
import sys
import re
import ast
import importlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger


class TestWebSocketSSotImportViolationsDetection(SSotBaseTestCase):
    """Mission Critical: WebSocket SSOT Import Violations Detection
    
    This test scans the entire codebase to detect import patterns that violate
    SSOT principles for WebSocket management.
    
    Expected Behavior:
    - This test SHOULD FAIL initially (proving violations exist)  
    - This test SHOULD PASS after SSOT import consolidation (proving fix works)
    """
    
    def setup_method(self, method):
        """Set up test environment for SSOT import violation detection."""
        super().setup_method(method)
        
        # Define search paths for import scanning
        self.search_paths = [
            Path(project_root) / "netra_backend" / "app",
            Path(project_root) / "tests", 
            Path(project_root) / "scripts",
            Path(project_root) / "test_framework"
        ]
        
        # Define SSOT-compliant import patterns
        self.ssot_import_patterns = [
            r'from netra_backend\.app\.websocket_core\.unified_manager import',
            r'import netra_backend\.app\.websocket_core\.unified_manager',
        ]
        
        # Define SSOT-violating import patterns  
        self.violation_import_patterns = [
            r'from netra_backend\.app\.websocket_core\.websocket_manager import',
            r'import netra_backend\.app\.websocket_core\.websocket_manager',
            r'from.*websocket_manager_factory.*import',
            r'import.*websocket_manager_factory'
        ]
        
        self.violation_details = defaultdict(list)
    
    def test_detect_dual_websocket_manager_imports_violation(self):
        """CRITICAL: Detect files importing from multiple WebSocket managers (SHOULD FAIL initially)
        
        This test finds files that import from both websocket_manager.py and unified_manager.py,
        creating SSOT violations through inconsistent access patterns.
        """
        logger.info("🔍 Scanning for dual WebSocket manager import violations...")
        
        dual_import_files = []
        
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        
                        # Check for imports from both managers
                        websocket_manager_imports = []
                        unified_manager_imports = []
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for websocket_manager imports
                            if re.search(r'from.*websocket_core\.websocket_manager.*import|import.*websocket_core\.websocket_manager', line):
                                websocket_manager_imports.append({
                                    'line_num': line_num,
                                    'line': line.strip()
                                })
                            
                            # Check for unified_manager imports
                            if re.search(r'from.*websocket_core\.unified_manager.*import|import.*websocket_core\.unified_manager', line):
                                unified_manager_imports.append({
                                    'line_num': line_num, 
                                    'line': line.strip()
                                })
                        
                        # If file has both types of imports, it's a violation
                        if websocket_manager_imports and unified_manager_imports:
                            dual_import_files.append({
                                'file': str(py_file.relative_to(project_root)),
                                'websocket_manager_imports': websocket_manager_imports,
                                'unified_manager_imports': unified_manager_imports,
                                'violation_type': 'dual_websocket_manager_imports'
                            })
                            
                            logger.error(f"🚨 DUAL IMPORT VIOLATION: {py_file.relative_to(project_root)}")
                            logger.error(f"  websocket_manager imports: {len(websocket_manager_imports)}")
                            logger.error(f"  unified_manager imports: {len(unified_manager_imports)}")
                            
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        self.violation_details['dual_import_files'] = dual_import_files
        
        # ASSERTION: This should FAIL initially if dual imports exist
        assert len(dual_import_files) == 0, (
            f"SSOT VIOLATION: Found {len(dual_import_files)} files with dual WebSocket manager imports. "
            f"Violating files: {[f['file'] for f in dual_import_files]}. "
            f"SSOT requires single import path for WebSocket management."
        )
    
    def test_detect_legacy_websocket_manager_imports_violation(self):
        """CRITICAL: Detect legacy websocket_manager.py imports (SHOULD FAIL initially)
        
        This test identifies all files still importing from the legacy websocket_manager.py
        instead of using the SSOT unified_manager.py.
        """
        logger.info("🔍 Scanning for legacy websocket_manager.py import violations...")
        
        legacy_import_files = []
        
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    # Skip the websocket_manager.py file itself
                    if py_file.name == 'websocket_manager.py':
                        continue
                        
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        
                        legacy_imports = []
                        
                        for line_num, line in enumerate(lines, 1):
                            # Check for legacy websocket_manager imports
                            if re.search(r'from.*websocket_core\.websocket_manager.*import|import.*websocket_core\.websocket_manager', line):
                                legacy_imports.append({
                                    'line_num': line_num,
                                    'line': line.strip(),
                                    'import_type': 'direct_websocket_manager'
                                })
                            
                            # Check for factory imports (also legacy)
                            if re.search(r'from.*websocket_manager_factory.*import|import.*websocket_manager_factory', line):
                                legacy_imports.append({
                                    'line_num': line_num,
                                    'line': line.strip(),
                                    'import_type': 'websocket_manager_factory'
                                })
                        
                        if legacy_imports:
                            legacy_import_files.append({
                                'file': str(py_file.relative_to(project_root)),
                                'legacy_imports': legacy_imports,
                                'violation_count': len(legacy_imports),
                                'violation_type': 'legacy_websocket_manager_imports'
                            })
                            
                            logger.warning(f"🚨 LEGACY IMPORT VIOLATION: {py_file.relative_to(project_root)}")
                            for imp in legacy_imports:
                                logger.warning(f"  Line {imp['line_num']}: {imp['line']}")
                                
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        self.violation_details['legacy_import_files'] = legacy_import_files
        
        # ASSERTION: This should FAIL initially if legacy imports exist
        assert len(legacy_import_files) == 0, (
            f"SSOT VIOLATION: Found {len(legacy_import_files)} files with legacy websocket_manager imports. "
            f"Total violations: {sum(f['violation_count'] for f in legacy_import_files)}. "
            f"Files needing migration: {[f['file'] for f in legacy_import_files]}. "
            f"SSOT requires migration to unified_manager.py imports."
        )
    
    def test_detect_inconsistent_websocket_import_patterns_violation(self):
        """CRITICAL: Detect inconsistent import patterns across codebase (SHOULD FAIL initially)
        
        This test identifies files that use different import patterns for the same WebSocket
        functionality, indicating lack of SSOT consistency.
        """
        logger.info("🔍 Scanning for inconsistent WebSocket import patterns...")
        
        import_pattern_analysis = defaultdict(lambda: defaultdict(list))
        inconsistent_files = []
        
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        
                        file_imports = []
                        
                        for line_num, line in enumerate(lines, 1):
                            # Categorize different WebSocket import patterns
                            if 'websocket' in line.lower() and ('import' in line or 'from' in line):
                                import_category = self._categorize_websocket_import(line)
                                if import_category:
                                    file_imports.append({
                                        'line_num': line_num,
                                        'line': line.strip(),
                                        'category': import_category
                                    })
                                    
                                    import_pattern_analysis[import_category]['files'].append({
                                        'file': str(py_file.relative_to(project_root)),
                                        'line_num': line_num,
                                        'line': line.strip()
                                    })
                        
                        # Check if file uses multiple import patterns
                        unique_categories = set(imp['category'] for imp in file_imports)
                        if len(unique_categories) > 1:
                            inconsistent_files.append({
                                'file': str(py_file.relative_to(project_root)),
                                'import_patterns': file_imports,
                                'pattern_count': len(unique_categories),
                                'patterns': list(unique_categories)
                            })
                            
                            logger.error(f"🚨 INCONSISTENT PATTERNS: {py_file.relative_to(project_root)}")
                            logger.error(f"  Uses {len(unique_categories)} different patterns: {list(unique_categories)}")
                            
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        self.violation_details['inconsistent_import_files'] = inconsistent_files
        self.violation_details['import_pattern_analysis'] = dict(import_pattern_analysis)
        
        # Log pattern distribution for analysis
        logger.info("📊 WebSocket Import Pattern Distribution:")
        for pattern, data in import_pattern_analysis.items():
            file_count = len(set(f['file'] for f in data['files']))
            logger.info(f"  {pattern}: {file_count} files, {len(data['files'])} imports")
        
        # ASSERTION: This should FAIL initially if inconsistent patterns exist
        assert len(inconsistent_files) == 0, (
            f"SSOT VIOLATION: Found {len(inconsistent_files)} files with inconsistent WebSocket import patterns. "
            f"Files using multiple patterns: {[f['file'] for f in inconsistent_files]}. "
            f"SSOT requires consistent import patterns across all files."
        )
    
    def test_detect_websocket_import_bypass_patterns_violation(self):
        """CRITICAL: Detect imports that bypass SSOT factory patterns (SHOULD FAIL initially)
        
        This test identifies code that directly imports WebSocket classes instead of
        using SSOT factory patterns for user isolation.
        """
        logger.info("🔍 Scanning for WebSocket import patterns that bypass SSOT factories...")
        
        bypass_violations = []
        
        # Patterns that indicate bypassing SSOT factories
        direct_class_patterns = [
            r'from.*import.*WebSocketManager(?!Factory)',
            r'from.*import.*UnifiedWebSocketManager',
            r'WebSocketManager\s*\(',  # Direct instantiation
            r'UnifiedWebSocketManager\s*\('  # Direct instantiation  
        ]
        
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    # Skip factory files and manager files themselves
                    if py_file.name in ['websocket_manager.py', 'unified_manager.py', 'websocket_manager_factory.py']:
                        continue
                        
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        
                        file_violations = []
                        
                        for line_num, line in enumerate(lines, 1):
                            for pattern in direct_class_patterns:
                                if re.search(pattern, line):
                                    file_violations.append({
                                        'line_num': line_num,
                                        'line': line.strip(),
                                        'pattern': pattern,
                                        'violation_type': 'direct_class_access'
                                    })
                                    
                                    logger.warning(f"🚨 BYPASS VIOLATION: {py_file.relative_to(project_root)}:{line_num}")
                                    logger.warning(f"  Pattern: {pattern}")
                                    logger.warning(f"  Line: {line.strip()}")
                        
                        if file_violations:
                            bypass_violations.append({
                                'file': str(py_file.relative_to(project_root)),
                                'violations': file_violations,
                                'violation_count': len(file_violations)
                            })
                            
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        self.violation_details['bypass_violations'] = bypass_violations
        
        # ASSERTION: This should FAIL initially if bypass patterns exist
        assert len(bypass_violations) == 0, (
            f"SSOT VIOLATION: Found {len(bypass_violations)} files bypassing SSOT factory patterns. "
            f"Total bypass violations: {sum(f['violation_count'] for f in bypass_violations)}. "
            f"Files with violations: {[f['file'] for f in bypass_violations]}. "
            f"SSOT requires using factory patterns for user isolation."
        )
    
    def test_validate_ssot_import_consistency_target_state(self):
        """VALIDATION: Check target SSOT import consistency state
        
        This test validates what the SSOT import state should look like after
        successful consolidation.
        """
        logger.info("🔍 Validating target SSOT import consistency state...")
        
        ssot_compliance_issues = []
        ssot_compliant_files = []
        
        for search_path in self.search_paths:
            if search_path.exists():
                for py_file in search_path.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        
                        # Check for SSOT-compliant patterns
                        has_ssot_imports = any(
                            re.search(pattern, content) for pattern in self.ssot_import_patterns
                        )
                        
                        # Check for SSOT violation patterns  
                        has_violation_imports = any(
                            re.search(pattern, content) for pattern in self.violation_import_patterns
                        )
                        
                        # If file has WebSocket imports, check compliance
                        has_websocket_imports = 'websocket' in content.lower() and 'import' in content
                        
                        if has_websocket_imports:
                            if has_ssot_imports and not has_violation_imports:
                                ssot_compliant_files.append(str(py_file.relative_to(project_root)))
                            elif has_violation_imports:
                                ssot_compliance_issues.append({
                                    'file': str(py_file.relative_to(project_root)),
                                    'has_ssot_imports': has_ssot_imports,
                                    'has_violation_imports': has_violation_imports,
                                    'issue_type': 'mixed_imports' if has_ssot_imports else 'only_violation_imports'
                                })
                                
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # Log compliance statistics
        total_websocket_files = len(ssot_compliant_files) + len(ssot_compliance_issues)
        compliance_rate = len(ssot_compliant_files) / total_websocket_files if total_websocket_files > 0 else 1.0
        
        logger.info(f"📊 SSOT Import Compliance Statistics:")
        logger.info(f"  Compliant files: {len(ssot_compliant_files)}")
        logger.info(f"  Non-compliant files: {len(ssot_compliance_issues)}")  
        logger.info(f"  Compliance rate: {compliance_rate:.1%}")
        
        self.violation_details['ssot_compliance'] = {
            'compliant_files': ssot_compliant_files,
            'compliance_issues': ssot_compliance_issues,
            'compliance_rate': compliance_rate
        }
        
        # This test provides information about target state
        # It helps guide remediation but doesn't fail
        if ssot_compliance_issues:
            logger.warning(f"⚠️ {len(ssot_compliance_issues)} files need SSOT import migration")
        else:
            logger.info("✅ All WebSocket imports are SSOT compliant")
    
    def _categorize_websocket_import(self, import_line: str) -> Optional[str]:
        """Categorize a WebSocket import line into patterns."""
        import_line_lower = import_line.lower()
        
        if 'websocket_manager_factory' in import_line_lower:
            return 'factory_import'
        elif 'websocket_core.websocket_manager' in import_line_lower:
            return 'legacy_manager_import'
        elif 'websocket_core.unified_manager' in import_line_lower:
            return 'ssot_manager_import'
        elif 'websocket_core' in import_line_lower:
            return 'websocket_core_import'
        elif 'websocket' in import_line_lower:
            return 'other_websocket_import'
        
        return None
    
    def teardown_method(self, method):
        """Clean up and log import violation detection results."""
        if self.violation_details:
            logger.info("📊 SSOT Import Violation Detection Summary:")
            
            total_violations = 0
            for violation_type, details in self.violation_details.items():
                if isinstance(details, list) and details:
                    count = len(details)
                    total_violations += count
                    logger.warning(f"  {violation_type}: {count} violations")
                elif isinstance(details, dict) and 'compliance_rate' in details:
                    logger.info(f"  {violation_type}: {details['compliance_rate']:.1%} compliant")
            
            if total_violations > 0:
                logger.error(f"🚨 TOTAL SSOT IMPORT VIOLATIONS: {total_violations}")
            else:
                logger.info("✅ No SSOT import violations detected")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test directly to check SSOT import violations
    pytest.main([__file__, "-v", "-s"])