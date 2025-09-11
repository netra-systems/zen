#!/usr/bin/env python
"""MISSION CRITICAL: DatabaseManager SSOT Consolidation Test Suite

THIS SUITE DETECTS DUPLICATE DATABASEMANAGER IMPLEMENTATIONS
Business Value: $500K+ ARR - Prevents cascade failures from inconsistent database access

CRITICAL VIOLATIONS TO DETECT:
1. Multiple DatabaseManager classes across different modules (SSOT violation)
2. Inconsistent database connection patterns between modules
3. Import conflicts causing WebSocket factory failures

DESIGNED TO FAIL PRE-SSOT REFACTOR:
- Tests will FAIL when multiple DatabaseManager implementations exist
- Tests will FAIL when imports are inconsistent across modules

DESIGNED TO PASS POST-SSOT REFACTOR:
- Tests will PASS when single DatabaseManager SSOT exists
- Tests will PASS when all modules use consistent database imports
- Tests will PASS when WebSocket factory can reliably access database

ANY FAILURE HERE INDICATES MULTIPLE DATABASE MANAGER IMPLEMENTATIONS.
"""

import ast
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import importlib.util

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# SSOT imports - all tests must use SSOT framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class TestDatabaseManagerSSOTConsolidation(SSotBaseTestCase):
    """
    Test suite to detect and validate DatabaseManager SSOT consolidation.
    
    These tests scan the codebase for duplicate DatabaseManager implementations
    and validate that all modules use consistent database access patterns.
    """
    
    def setup_method(self, method=None):
        """Setup with enhanced database consolidation tracking."""
        super().setup_method(method)
        self.record_metric("test_category", "database_manager_ssot_consolidation")
        
        # Track database manager findings
        self._database_manager_files = []
        self._database_manager_classes = []
        self._import_patterns = []
        self._ssot_violations = []
        
        # Define project paths to scan
        self._project_root = Path(project_root)
        self._scan_paths = [
            self._project_root / "netra_backend" / "app" / "db",
            self._project_root / "netra_backend" / "app" / "factories",
            self._project_root / "auth_service",
            self._project_root / "shared",
            self._project_root / "test_framework",
        ]
        
    def test_multiple_database_manager_classes_detected(self):
        """
        DESIGNED TO FAIL: Detect duplicate DatabaseManager implementations
        
        This test scans the codebase for multiple DatabaseManager class definitions
        which violate SSOT principles and cause WebSocket factory failures.
        """
        self.record_metric("violation_type", "multiple_database_manager_classes")
        
        database_manager_locations = self._find_database_manager_classes()
        
        # Record all found locations
        self.record_metric("database_manager_locations", database_manager_locations)
        self._database_manager_classes = database_manager_locations
        
        logger.info(f"Found DatabaseManager classes in: {database_manager_locations}")
        
        # CRITICAL CHECK: Multiple DatabaseManager classes indicate SSOT violation
        if len(database_manager_locations) > 1:
            violation_details = {
                "total_classes": len(database_manager_locations),
                "locations": database_manager_locations,
                "violation_type": "duplicate_database_manager_classes"
            }
            self._ssot_violations.append(violation_details)
            self.record_metric("ssot_violation_detected", violation_details)
            
            # This test is DESIGNED TO FAIL with SSOT violations
            assert False, (
                f"SSOT VIOLATION: Found {len(database_manager_locations)} DatabaseManager classes. "
                f"SSOT requires exactly 1. Locations: {database_manager_locations}. "
                "This causes WebSocket factory import conflicts and connection failures."
            )
        elif len(database_manager_locations) == 1:
            logger.info("SSOT compliance: Single DatabaseManager class found")
            self.record_metric("ssot_compliant", True)
        else:
            # No DatabaseManager found - this is also a problem
            assert False, (
                "CRITICAL: No DatabaseManager class found in codebase. "
                "WebSocket factory requires DatabaseManager for session creation."
            )
    
    def test_database_manager_import_consistency(self):
        """
        DESIGNED TO FAIL: Verify inconsistent imports across modules
        
        This test finds all imports of DatabaseManager and validates they
        point to the same source, preventing import conflicts.
        """
        self.record_metric("violation_type", "inconsistent_database_imports")
        
        import_patterns = self._find_database_manager_imports()
        
        # Record all import patterns found
        self.record_metric("import_patterns_found", import_patterns)
        self._import_patterns = import_patterns
        
        logger.info(f"Found DatabaseManager import patterns: {len(import_patterns)}")
        
        # Analyze import consistency
        unique_import_sources = set()
        for pattern in import_patterns:
            source_module = pattern.get('source_module', 'unknown')
            unique_import_sources.add(source_module)
        
        self.record_metric("unique_import_sources", list(unique_import_sources))
        
        # CRITICAL CHECK: Multiple import sources indicate inconsistency
        if len(unique_import_sources) > 1:
            inconsistency_details = {
                "total_sources": len(unique_import_sources),
                "sources": list(unique_import_sources),
                "import_count": len(import_patterns),
                "violation_type": "inconsistent_database_imports"
            }
            self._ssot_violations.append(inconsistency_details)
            self.record_metric("import_inconsistency_detected", inconsistency_details)
            
            # This test is DESIGNED TO FAIL with import inconsistencies
            assert False, (
                f"IMPORT INCONSISTENCY: DatabaseManager imported from {len(unique_import_sources)} "
                f"different sources: {list(unique_import_sources)}. "
                f"SSOT requires all imports from single source. Total imports: {len(import_patterns)}."
            )
        elif len(unique_import_sources) == 1:
            logger.info("Import consistency: All DatabaseManager imports from single source")
            self.record_metric("import_consistency_validated", True)
        else:
            logger.warning("No DatabaseManager imports found - this may indicate missing usage")
            self.record_metric("no_imports_found", True)
    
    def test_consolidated_database_manager_single_source(self):
        """
        DESIGNED TO PASS: Post-SSOT should have single DatabaseManager
        
        This test validates that after SSOT consolidation:
        1. Exactly one DatabaseManager class exists
        2. All imports point to the same source
        3. WebSocket factory can reliably import DatabaseManager
        """
        self.record_metric("validation_type", "ssot_consolidated_validation")
        
        # Re-run detection to get current state
        database_manager_locations = self._find_database_manager_classes()
        import_patterns = self._find_database_manager_imports()
        
        # Validate SSOT consolidation
        consolidation_success = True
        consolidation_issues = []
        
        # Check 1: Exactly one DatabaseManager class
        if len(database_manager_locations) != 1:
            consolidation_success = False
            consolidation_issues.append(
                f"Expected 1 DatabaseManager class, found {len(database_manager_locations)}"
            )
        else:
            canonical_location = database_manager_locations[0]
            self.record_metric("canonical_database_manager", canonical_location)
            logger.info(f"Canonical DatabaseManager location: {canonical_location}")
        
        # Check 2: All imports from single source
        unique_sources = set(p.get('source_module', 'unknown') for p in import_patterns)
        if len(unique_sources) > 1:
            consolidation_success = False
            consolidation_issues.append(
                f"Multiple import sources: {list(unique_sources)}"
            )
        
        # Check 3: WebSocket factory import capability
        websocket_import_success = False
        try:
            # Test the most common import pattern WebSocket factory would use
            from netra_backend.app.db.database_manager import DatabaseManager
            websocket_import_success = True
            self.record_metric("websocket_import_test_success", True)
        except ImportError as e:
            consolidation_issues.append(f"WebSocket factory import failed: {e}")
            self.record_metric("websocket_import_test_error", str(e))
        
        # Record consolidation status
        self.record_metric("consolidation_success", consolidation_success)
        self.record_metric("consolidation_issues", consolidation_issues)
        
        # Validate successful consolidation
        if not consolidation_success:
            assert False, (
                f"DatabaseManager SSOT consolidation failed. Issues: {consolidation_issues}. "
                f"Classes found: {database_manager_locations}. "
                f"Import sources: {list(unique_sources)}."
            )
        
        if not websocket_import_success:
            assert False, (
                "WebSocket factory cannot import DatabaseManager from expected location. "
                "This will cause connection failures."
            )
        
        logger.info("DatabaseManager SSOT consolidation validation passed")
    
    def _find_database_manager_classes(self) -> List[Dict[str, Any]]:
        """
        Find all DatabaseManager class definitions in the codebase.
        
        Returns:
            List of dictionaries with class location details
        """
        database_manager_classes = []
        
        for scan_path in self._scan_paths:
            if not scan_path.exists():
                continue
                
            for py_file in scan_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to find class definitions
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name == "DatabaseManager":
                            class_info = {
                                "file_path": str(py_file),
                                "class_name": node.name,
                                "line_number": node.lineno,
                                "relative_path": str(py_file.relative_to(self._project_root))
                            }
                            database_manager_classes.append(class_info)
                            logger.debug(f"Found DatabaseManager class: {class_info}")
                            
                except (SyntaxError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not parse {py_file}: {e}")
                except Exception as e:
                    logger.warning(f"Error scanning {py_file}: {e}")
        
        return database_manager_classes
    
    def _find_database_manager_imports(self) -> List[Dict[str, Any]]:
        """
        Find all DatabaseManager import statements in the codebase.
        
        Returns:
            List of dictionaries with import details
        """
        import_patterns = []
        
        for scan_path in self._scan_paths:
            if not scan_path.exists():
                continue
                
            for py_file in scan_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to find import statements
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        import_info = None
                        
                        if isinstance(node, ast.ImportFrom):
                            # from module import DatabaseManager
                            if node.names:
                                for alias in node.names:
                                    if alias.name == "DatabaseManager":
                                        import_info = {
                                            "file_path": str(py_file),
                                            "import_type": "from_import",
                                            "source_module": node.module,
                                            "imported_name": alias.name,
                                            "line_number": node.lineno,
                                            "relative_path": str(py_file.relative_to(self._project_root))
                                        }
                        
                        elif isinstance(node, ast.Import):
                            # import module.DatabaseManager
                            for alias in node.names:
                                if "DatabaseManager" in alias.name:
                                    import_info = {
                                        "file_path": str(py_file),
                                        "import_type": "direct_import",
                                        "source_module": alias.name,
                                        "imported_name": alias.name,
                                        "line_number": node.lineno,
                                        "relative_path": str(py_file.relative_to(self._project_root))
                                    }
                        
                        if import_info:
                            import_patterns.append(import_info)
                            logger.debug(f"Found DatabaseManager import: {import_info}")
                            
                except (SyntaxError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not parse {py_file}: {e}")
                except Exception as e:
                    logger.warning(f"Error scanning {py_file}: {e}")
        
        return import_patterns
    
    def teardown_method(self, method=None):
        """Enhanced teardown with consolidation metrics."""
        # Log final consolidation analysis
        logger.info(f"Database manager classes found: {len(self._database_manager_classes)}")
        logger.info(f"Import patterns found: {len(self._import_patterns)}")
        logger.info(f"SSOT violations detected: {len(self._ssot_violations)}")
        
        if self._ssot_violations:
            logger.warning(f"SSOT violations details: {self._ssot_violations}")
        
        super().teardown_method(method)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])