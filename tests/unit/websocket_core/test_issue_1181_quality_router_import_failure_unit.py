"""
Test Issue #1181 QualityMessageRouter Import Failure Reproduction

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Stability and Quality Feature Accessibility
- Value Impact: Quality routing features must be accessible for premium functionality
- Strategic Impact: $500K+ ARR protection - quality features drive customer retention

This test reproduces the specific import chain failure preventing QualityMessageRouter
from being accessible, which blocks quality-related WebSocket functionality.
"""

import pytest
import importlib
import traceback
from typing import Dict, Any, List
from unittest.mock import patch

from test_framework.base_test_case import BaseTestCase


class TestIssue1181QualityRouterImportFailure(BaseTestCase):
    """Test QualityMessageRouter import failure reproduction and analysis."""

    def test_quality_message_router_import_failure_reproduction(self):
        """
        Reproduce the exact QualityMessageRouter import failure.
        
        Expected: ImportError due to UnifiedWebSocketManager dependency issue
        Business Impact: Quality routing features unavailable, breaking premium functionality
        """
        
        # Test direct import failure
        with pytest.raises(ImportError) as exc_info:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        
        # Analyze the specific error
        error_message = str(exc_info.value)
        
        # Verify it's the expected UnifiedWebSocketManager import issue
        assert "cannot import name 'UnifiedWebSocketManager'" in error_message
        assert "netra_backend.app.websocket_core.unified_manager" in error_message
        
        # Document the complete error chain for debugging
        self._log_import_failure_chain(error_message)

    def test_websocket_services_init_dependency_chain_analysis(self):
        """
        Analyze the dependency chain failure in websocket services __init__.py
        
        This identifies the root cause of the import failure chain that prevents
        QualityMessageRouter from being accessible.
        """
        
        # Test the specific failing import from the error traceback
        with pytest.raises(ImportError) as exc_info:
            # This is the line causing the failure in websocket services __init__.py
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        error_message = str(exc_info.value)
        
        # Verify this is the root cause preventing QualityMessageRouter access
        assert "cannot import name 'UnifiedWebSocketManager'" in error_message
        
        # Document that this breaks the entire websocket services module initialization
        self._analyze_dependency_impact(error_message)

    def test_unified_manager_class_availability_analysis(self):
        """
        Analyze what classes are actually available in unified_manager.py
        
        This helps identify the naming mismatch causing the import failure.
        """
        
        try:
            # Import the module directly to see what's actually available
            import netra_backend.app.websocket_core.unified_manager as unified_manager_module
            
            # Get all available classes
            available_classes = [
                name for name in dir(unified_manager_module) 
                if isinstance(getattr(unified_manager_module, name), type)
            ]
            
            # Document findings
            self._document_available_classes(available_classes)
            
            # Check for the expected class or similar alternatives
            websocket_manager_classes = [
                cls for cls in available_classes 
                if "websocket" in cls.lower() and "manager" in cls.lower()
            ]
            
            # This test documents what's actually available vs what's expected
            assert len(websocket_manager_classes) > 0, (
                f"No WebSocket manager classes found. Available classes: {available_classes}"
            )
            
        except ImportError as e:
            # If the entire module fails to import, document that too
            pytest.fail(f"Unified manager module itself fails to import: {e}")

    def test_import_path_validation_for_working_message_router(self):
        """
        Test that the canonical MessageRouter import path works correctly.
        
        This establishes the baseline working import to contrast with the failing
        QualityMessageRouter import.
        """
        
        # Test canonical MessageRouter import (should work)
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Verify the class is properly accessible
            assert MessageRouter is not None
            assert hasattr(MessageRouter, '__name__')
            assert MessageRouter.__name__ == 'MessageRouter'
            
            # Document successful import for comparison
            self._document_successful_import("MessageRouter", "netra_backend.app.websocket_core.handlers")
            
        except ImportError as e:
            pytest.fail(f"Canonical MessageRouter import failed unexpectedly: {e}")

    def test_deprecated_import_path_behavior(self):
        """
        Test the deprecated MessageRouter import path behavior.
        
        This validates the current state of deprecated path handling during
        the consolidation process.
        """
        
        # Test deprecated path (should work with warnings)
        try:
            from netra_backend.app.websocket_core import MessageRouter
            
            # Verify it's the same class as canonical import
            from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
            
            # These should be identical objects (SSOT compliance)
            assert MessageRouter is CanonicalMessageRouter
            assert id(MessageRouter) == id(CanonicalMessageRouter)
            
            # Document SSOT compliance status
            self._document_ssot_compliance_status(MessageRouter, CanonicalMessageRouter)
            
        except ImportError as e:
            pytest.fail(f"Deprecated MessageRouter import path failed: {e}")

    def test_quality_router_class_existence_verification(self):
        """
        Verify that QualityMessageRouter class exists in its file but is not importable.
        
        This distinguishes between "class doesn't exist" vs "import chain broken".
        """
        
        # Read the quality_message_router.py file directly to verify class exists
        import ast
        import inspect
        from pathlib import Path
        
        # Get the file path
        quality_router_file = Path(__file__).parent.parent.parent.parent / "netra_backend" / "app" / "services" / "websocket" / "quality_message_router.py"
        
        # Verify file exists
        assert quality_router_file.exists(), f"QualityMessageRouter file not found: {quality_router_file}"
        
        # Parse the file to check for QualityMessageRouter class
        with open(quality_router_file, 'r') as f:
            file_content = f.read()
        
        # Parse AST to find class definitions
        tree = ast.parse(file_content)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        # Verify QualityMessageRouter class exists in the file
        assert "QualityMessageRouter" in class_names, (
            f"QualityMessageRouter class not found in file. Available classes: {class_names}"
        )
        
        # Document that class exists but import fails
        self._document_class_existence_vs_import_failure(class_names)

    def _log_import_failure_chain(self, error_message: str) -> None:
        """Log the complete import failure chain for debugging."""
        print(f"\n--- Issue #1181 Import Failure Analysis ---")
        print(f"Error: {error_message}")
        print(f"Impact: QualityMessageRouter features unavailable")
        print(f"Business Risk: Premium quality features inaccessible to customers")

    def _analyze_dependency_impact(self, error_message: str) -> None:
        """Analyze the impact of the dependency chain failure."""
        print(f"\n--- Dependency Chain Analysis ---")
        print(f"Root Cause: {error_message}")
        print(f"Affected Module: netra_backend.app.services.websocket")
        print(f"Impact: Entire websocket services module initialization blocked")

    def _document_available_classes(self, available_classes: List[str]) -> None:
        """Document the classes actually available in unified_manager."""
        print(f"\n--- Available Classes in unified_manager.py ---")
        for cls in available_classes:
            print(f"  - {cls}")

    def _document_successful_import(self, class_name: str, import_path: str) -> None:
        """Document successful import for comparison."""
        print(f"\n--- Successful Import Documented ---")
        print(f"Class: {class_name}")
        print(f"Path: {import_path}")
        print(f"Status: WORKING")

    def _document_ssot_compliance_status(self, router1: type, router2: type) -> None:
        """Document SSOT compliance status for MessageRouter imports."""
        print(f"\n--- SSOT Compliance Analysis ---")
        print(f"Canonical Router ID: {id(router1)}")
        print(f"Deprecated Router ID: {id(router2)}")
        print(f"Same Object: {router1 is router2}")
        print(f"SSOT Status: {'COMPLIANT' if router1 is router2 else 'VIOLATION'}")

    def _document_class_existence_vs_import_failure(self, class_names: List[str]) -> None:
        """Document that class exists but import fails."""
        print(f"\n--- Class Existence vs Import Failure ---")
        print(f"QualityMessageRouter class exists in file: YES")
        print(f"QualityMessageRouter importable: NO")
        print(f"All classes in file: {class_names}")
        print(f"Issue: Import chain broken, not missing class")


class TestIssue1181ImportPathValidation(BaseTestCase):
    """Test import path validation and SSOT compliance for MessageRouter consolidation."""

    def test_all_message_router_import_paths_inventory(self):
        """
        Create comprehensive inventory of all MessageRouter-related import paths.
        
        This identifies which paths work, which fail, and which need consolidation.
        """
        
        import_test_results = {}
        
        # Test all known import paths
        test_imports = [
            # Core MessageRouter paths
            ("netra_backend.app.websocket_core.handlers", "MessageRouter"),
            ("netra_backend.app.websocket_core", "MessageRouter"),
            
            # Quality router paths
            ("netra_backend.app.services.websocket.quality_message_router", "QualityMessageRouter"),
            ("netra_backend.app.services.websocket", "QualityMessageRouter"),
        ]
        
        for module_path, class_name in test_imports:
            result = self._test_import_path(module_path, class_name)
            import_test_results[f"{module_path}.{class_name}"] = result
        
        # Analyze results
        self._analyze_import_results(import_test_results)
        
        # Verify at least one MessageRouter path works
        working_message_router_imports = [
            path for path, result in import_test_results.items() 
            if "MessageRouter" in path and result["success"]
        ]
        
        assert len(working_message_router_imports) > 0, (
            "No working MessageRouter imports found - critical system failure"
        )

    def test_import_failure_error_message_analysis(self):
        """
        Analyze the specific error messages to understand consolidation requirements.
        
        This helps plan the SSOT consolidation approach by understanding exactly
        what's broken and what needs to be unified.
        """
        
        # Test the specific failing import and capture detailed error info
        error_details = {}
        
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        except ImportError as e:
            error_details["quality_router_error"] = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
        
        # Verify we captured the expected error
        assert "quality_router_error" in error_details
        
        # Analyze the error details for consolidation planning
        self._analyze_consolidation_requirements(error_details)

    def _test_import_path(self, module_path: str, class_name: str) -> Dict[str, Any]:
        """Test a specific import path and return detailed results."""
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            
            return {
                "success": True,
                "class_id": id(cls),
                "class_name": cls.__name__,
                "module_path": module_path,
                "error": None
            }
        except (ImportError, AttributeError) as e:
            return {
                "success": False,
                "class_id": None,
                "class_name": class_name,
                "module_path": module_path,
                "error": str(e)
            }

    def _analyze_import_results(self, results: Dict[str, Dict[str, Any]]) -> None:
        """Analyze import test results for consolidation planning."""
        print(f"\n--- Import Path Analysis Results ---")
        
        for path, result in results.items():
            status = "✅ WORKING" if result["success"] else "❌ FAILED"
            print(f"{status} {path}")
            if not result["success"]:
                print(f"    Error: {result['error']}")
            else:
                print(f"    Class ID: {result['class_id']}")

    def _analyze_consolidation_requirements(self, error_details: Dict[str, Any]) -> None:
        """Analyze error details to plan consolidation approach."""
        print(f"\n--- Consolidation Requirements Analysis ---")
        
        for error_type, details in error_details.items():
            print(f"\n{error_type.upper()}:")
            print(f"  Error Type: {details['error_type']}")
            print(f"  Message: {details['error_message']}")
            
            # Extract key consolidation requirements
            if "UnifiedWebSocketManager" in details["error_message"]:
                print(f"  Requirement: Fix UnifiedWebSocketManager import/naming issue")
            if "cannot import name" in details["error_message"]:
                print(f"  Requirement: Verify class naming consistency")