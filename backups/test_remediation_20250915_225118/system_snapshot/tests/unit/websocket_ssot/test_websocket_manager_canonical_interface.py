"""
Test WebSocket Manager Canonical Interface Validation (Issue #996)

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure
- Business Goal: Ensure consistent WebSocket Manager interface to protect $500K+ ARR
- Value Impact: Prevents interface fragmentation and runtime errors in Golden Path
- Revenue Impact: Guarantees reliable chat functionality through consistent API

CRITICAL PURPOSE: These tests FAIL FIRST to demonstrate interface inconsistencies,
then PASS after SSOT consolidation to validate unified interface.

INTERFACE CHAOS DETECTED (Issue #996):
1. Different import paths exposing different method signatures
2. Inconsistent async/sync method patterns
3. Missing methods in some implementations
4. Parameter signature mismatches causing runtime errors

TEST STRATEGY:
- Fail-first approach demonstrating actual interface fragmentation
- Validate ALL import paths expose consistent interface methods
- Verify method signatures match canonical interface
- Document expected failures for pre-fix validation

EXPECTED BEHAVIOR:
- BEFORE FIX: Tests FAIL with interface inconsistencies across imports
- AFTER FIX: Tests PASS with unified canonical interface from all paths
"""

import pytest
import asyncio
import importlib
import inspect
from typing import Dict, List, Set, Any, Optional, Type, Callable, Union
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field

# SSOT Test Framework (Required)
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ensure_user_id

logger = get_logger(__name__)


@dataclass
class MethodSignature:
    """Data class to track method signatures and their characteristics."""
    name: str
    is_async: bool
    parameters: Dict[str, str]  # param_name -> param_annotation
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False


@dataclass
class InterfaceAnalysis:
    """Analysis of a WebSocket Manager interface."""
    import_path: str
    class_type: Type
    methods: Dict[str, MethodSignature] = field(default_factory=dict)
    properties: Dict[str, MethodSignature] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None


class WebSocketManagerCanonicalInterfaceTests(SSotBaseTestCase):
    """
    Test WebSocket Manager canonical interface for Issue #996.

    CRITICAL: These tests demonstrate interface chaos and validate SSOT interface unification.
    """

    def setup_method(self, method):
        """Set up test environment with SSOT compliance."""
        super().setup_method(method)
        self.interface_analyses: List[InterfaceAnalysis] = []
        import uuid
        self.test_user_id = ensure_user_id(str(uuid.uuid4()))

    def get_canonical_interface_specification(self) -> Dict[str, MethodSignature]:
        """
        Define the canonical WebSocket Manager interface that all implementations must support.

        This represents the expected SSOT interface after consolidation.

        Returns:
            Dict of method_name -> MethodSignature for the canonical interface
        """
        return {
            # Core Connection Management
            "connect_user": MethodSignature(
                name="connect_user",
                is_async=True,
                parameters={
                    "user_id": "UserID",
                    "websocket": "WebSocket",
                    "connection_id": "Optional[ConnectionID]"
                },
                return_type="ConnectionID"
            ),

            "disconnect_user": MethodSignature(
                name="disconnect_user",
                is_async=True,
                parameters={
                    "user_id": "UserID",
                    "connection_id": "Optional[ConnectionID]"
                },
                return_type="bool"
            ),

            # Message Operations
            "send_message": MethodSignature(
                name="send_message",
                is_async=True,
                parameters={
                    "user_id": "UserID",
                    "message": "Dict[str, Any]",
                    "connection_id": "Optional[ConnectionID]"
                },
                return_type="bool"
            ),

            "broadcast_to_user": MethodSignature(
                name="broadcast_to_user",
                is_async=True,
                parameters={
                    "user_id": "UserID",
                    "message": "Dict[str, Any]",
                    "event_type": "Optional[str]"
                },
                return_type="int"  # Number of connections messaged
            ),

            "broadcast_user_event": MethodSignature(
                name="broadcast_user_event",
                is_async=True,
                parameters={
                    "user_id": "UserID",
                    "event_type": "str",
                    "data": "Dict[str, Any]",
                    "connection_id": "Optional[ConnectionID]"
                },
                return_type="bool"
            ),

            # Connection State Management
            "get_connection_count": MethodSignature(
                name="get_connection_count",
                is_async=False,
                parameters={
                    "user_id": "Optional[UserID]"
                },
                return_type="int"
            ),

            "get_user_connections": MethodSignature(
                name="get_user_connections",
                is_async=False,
                parameters={
                    "user_id": "UserID"
                },
                return_type="List[ConnectionID]"
            ),

            "is_user_connected": MethodSignature(
                name="is_user_connected",
                is_async=False,
                parameters={
                    "user_id": "UserID",
                    "connection_id": "Optional[ConnectionID]"
                },
                return_type="bool"
            ),

            # Health and Monitoring
            "get_health_status": MethodSignature(
                name="get_health_status",
                is_async=False,
                parameters={},
                return_type="Dict[str, Any]"
            ),

            "cleanup_stale_connections": MethodSignature(
                name="cleanup_stale_connections",
                is_async=True,
                parameters={
                    "max_age_seconds": "Optional[int]"
                },
                return_type="int"  # Number cleaned up
            )
        }

    def get_websocket_manager_import_paths(self) -> List[str]:
        """Get all import paths that should expose WebSocket Manager functionality."""
        return [
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "netra_backend.app.websocket_core.unified_manager._UnifiedWebSocketManagerImplementation",
            # Add more paths as discovered in Issue #996 analysis
        ]

    def _analyze_class_interface(self, import_path: str, class_type: Type) -> InterfaceAnalysis:
        """
        Analyze the interface of a WebSocket Manager class.

        Args:
            import_path: The import path used to get this class
            class_type: The class type to analyze

        Returns:
            InterfaceAnalysis with complete interface information
        """
        analysis = InterfaceAnalysis(
            import_path=import_path,
            class_type=class_type
        )

        try:
            # Get all methods and properties from the class
            for name in dir(class_type):
                # Skip private/dunder methods
                if name.startswith('_'):
                    continue

                try:
                    attr = getattr(class_type, name)

                    # Check if it's a method
                    if callable(attr):
                        signature = self._extract_method_signature(name, attr)
                        analysis.methods[name] = signature

                    # Check if it's a property
                    elif isinstance(attr, property):
                        prop_signature = MethodSignature(
                            name=name,
                            is_async=False,
                            parameters={},
                            is_property=True
                        )
                        analysis.properties[name] = prop_signature

                except Exception as e:
                    logger.debug(f"Error analyzing attribute {name} in {class_type}: {e}")

        except Exception as e:
            analysis.success = False
            analysis.error_message = str(e)

        return analysis

    def _extract_method_signature(self, method_name: str, method: Callable) -> MethodSignature:
        """
        Extract signature information from a method.

        Args:
            method_name: Name of the method
            method: The method object

        Returns:
            MethodSignature with extracted information
        """
        signature = MethodSignature(
            name=method_name,
            is_async=asyncio.iscoroutinefunction(method),
            parameters={},
            is_classmethod=isinstance(method, classmethod),
            is_staticmethod=isinstance(method, staticmethod)
        )

        try:
            # Extract function signature
            sig = inspect.signature(method)
            for param_name, param in sig.parameters.items():
                # Skip 'self' parameter
                if param_name == 'self':
                    continue

                param_annotation = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                signature.parameters[param_name] = param_annotation

            # Extract return type
            if sig.return_annotation != inspect.Signature.empty:
                signature.return_type = str(sig.return_annotation)

            # Extract docstring
            signature.docstring = inspect.getdoc(method)

        except Exception as e:
            logger.debug(f"Error extracting signature for {method_name}: {e}")

        return signature

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_canonical_interface_consistency(self):
        """
        FAIL-FIRST TEST: Validate WebSocket Manager canonical interface consistency.

        EXPECTED BEHAVIOR:
        - BEFORE FIX: Different imports expose different interfaces (SHOULD FAIL)
        - AFTER FIX: All imports expose the same canonical interface (SHOULD PASS)

        This test validates that all import paths provide the same interface methods
        with consistent signatures.
        """
        canonical_interface = self.get_canonical_interface_specification()
        import_paths = self.get_websocket_manager_import_paths()

        print(f"\n=== WEBSOCKET MANAGER CANONICAL INTERFACE VALIDATION ===")
        print(f"Canonical interface methods: {len(canonical_interface)}")
        print(f"Import paths to test: {len(import_paths)}")
        print()

        # Analyze each import path
        for import_path in import_paths:
            try:
                # Import the class
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                class_type = getattr(module, class_name)

                # Analyze its interface
                analysis = self._analyze_class_interface(import_path, class_type)
                self.interface_analyses.append(analysis)

                print(f"📊 ANALYZING: {import_path}")
                print(f"   Success: {analysis.success}")
                if not analysis.success:
                    print(f"   Error: {analysis.error_message}")
                else:
                    print(f"   Methods found: {len(analysis.methods)}")
                    print(f"   Properties found: {len(analysis.properties)}")
                print()

            except Exception as e:
                error_analysis = InterfaceAnalysis(
                    import_path=import_path,
                    class_type=None,
                    success=False,
                    error_message=str(e)
                )
                self.interface_analyses.append(error_analysis)
                print(f"❌ FAILED TO IMPORT: {import_path}")
                print(f"   Error: {str(e)}")
                print()

        # Analyze interface consistency
        successful_analyses = [a for a in self.interface_analyses if a.success]

        if len(successful_analyses) == 0:
            pytest.fail("No WebSocket Manager implementations could be imported for interface analysis")

        print(f"=== CANONICAL INTERFACE COMPLIANCE ANALYSIS ===")

        interface_violations = []
        missing_methods_by_import = {}

        for analysis in successful_analyses:
            print(f"\n🔍 INTERFACE ANALYSIS: {analysis.import_path}")

            missing_methods = []
            signature_mismatches = []

            # Check each canonical method
            for canonical_name, canonical_sig in canonical_interface.items():
                if canonical_name not in analysis.methods:
                    missing_methods.append(canonical_name)
                    print(f"   ❌ MISSING METHOD: {canonical_name}")
                else:
                    # Compare signatures
                    actual_sig = analysis.methods[canonical_name]
                    mismatches = self._compare_method_signatures(canonical_sig, actual_sig)
                    if mismatches:
                        signature_mismatches.extend(mismatches)
                        for mismatch in mismatches:
                            print(f"   ⚠️  SIGNATURE MISMATCH: {mismatch}")

            if missing_methods:
                missing_methods_by_import[analysis.import_path] = missing_methods
                interface_violations.append(f"{analysis.import_path}: missing {len(missing_methods)} methods")

            if signature_mismatches:
                interface_violations.append(f"{analysis.import_path}: {len(signature_mismatches)} signature mismatches")

            # Show available methods for debugging
            print(f"   📋 Available methods: {list(analysis.methods.keys())}")

        print(f"\n=== INTERFACE CONSISTENCY SUMMARY ===")
        print(f"Successful imports analyzed: {len(successful_analyses)}")
        print(f"Interface violations found: {len(interface_violations)}")

        if interface_violations:
            print("\n❌ INTERFACE VIOLATIONS DETECTED:")
            for violation in interface_violations:
                print(f"   - {violation}")

            print("\n📋 MISSING METHODS BY IMPORT:")
            for import_path, missing in missing_methods_by_import.items():
                print(f"   {import_path}:")
                for method in missing:
                    print(f"     - {method}")

            # This should FAIL before SSOT interface consolidation
            pytest.fail(
                f"CANONICAL INTERFACE VIOLATIONS: Found {len(interface_violations)} interface violations "
                f"across WebSocket Manager implementations. After SSOT consolidation, all import paths "
                f"should expose the same canonical interface. Violations: {interface_violations}"
            )

        print("✅ CANONICAL INTERFACE CONSISTENCY VALIDATED!")
        print("All import paths expose the same canonical interface methods.")

    def _compare_method_signatures(self, canonical: MethodSignature, actual: MethodSignature) -> List[str]:
        """
        Compare two method signatures and return list of mismatches.

        Args:
            canonical: The expected signature
            actual: The actual signature found

        Returns:
            List of mismatch descriptions
        """
        mismatches = []

        # Check async/sync consistency
        if canonical.is_async != actual.is_async:
            async_desc = "async" if canonical.is_async else "sync"
            actual_desc = "async" if actual.is_async else "sync"
            mismatches.append(f"{canonical.name}: expected {async_desc}, got {actual_desc}")

        # Check parameter names (we're lenient on types for now)
        canonical_params = set(canonical.parameters.keys())
        actual_params = set(actual.parameters.keys())

        missing_params = canonical_params - actual_params
        extra_params = actual_params - canonical_params

        if missing_params:
            mismatches.append(f"{canonical.name}: missing parameters {missing_params}")

        if extra_params:
            mismatches.append(f"{canonical.name}: unexpected parameters {extra_params}")

        return mismatches

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_method_signature_validation(self):
        """
        FAIL-FIRST TEST: Validate specific critical method signatures.

        EXPECTED BEHAVIOR:
        - BEFORE FIX: Critical methods have inconsistent signatures (SHOULD FAIL)
        - AFTER FIX: Critical methods have consistent signatures (SHOULD PASS)

        Focuses on the most business-critical methods for Golden Path functionality.
        """
        critical_methods = [
            "connect_user",
            "disconnect_user",
            "send_message",
            "broadcast_to_user",
            "broadcast_user_event"
        ]

        canonical_interface = self.get_canonical_interface_specification()
        successful_analyses = [a for a in self.interface_analyses if a.success]

        if not successful_analyses:
            # Run interface analysis first if not done
            self.test_websocket_manager_canonical_interface_consistency()
            successful_analyses = [a for a in self.interface_analyses if a.success]

        print(f"\n=== CRITICAL METHOD SIGNATURE VALIDATION ===")
        print(f"Critical methods to validate: {critical_methods}")
        print(f"Implementations to check: {len(successful_analyses)}")
        print()

        signature_violations = []

        for method_name in critical_methods:
            if method_name not in canonical_interface:
                continue

            canonical_sig = canonical_interface[method_name]
            print(f"🔍 VALIDATING METHOD: {method_name}")
            print(f"   Expected: {self._format_signature(canonical_sig)}")

            method_implementations = {}
            for analysis in successful_analyses:
                if method_name in analysis.methods:
                    actual_sig = analysis.methods[method_name]
                    method_implementations[analysis.import_path] = actual_sig
                    print(f"   {analysis.import_path}: {self._format_signature(actual_sig)}")

            # Check consistency across implementations
            if len(method_implementations) == 0:
                violation = f"{method_name}: NOT FOUND in any implementation"
                signature_violations.append(violation)
                print(f"   ❌ {violation}")
            elif len(method_implementations) == 1:
                print(f"   ⚠️  Only found in 1 implementation - need SSOT consolidation")
            else:
                # Compare all implementations for consistency
                signatures = list(method_implementations.values())
                base_sig = signatures[0]

                for i, sig in enumerate(signatures[1:], 1):
                    mismatches = self._compare_method_signatures(base_sig, sig)
                    if mismatches:
                        import_paths = list(method_implementations.keys())
                        violation = f"{method_name}: signature mismatch between {import_paths[0]} and {import_paths[i]}: {mismatches}"
                        signature_violations.append(violation)
                        print(f"   ❌ {violation}")

            print()

        print(f"=== SIGNATURE VALIDATION SUMMARY ===")
        print(f"Signature violations found: {len(signature_violations)}")

        if signature_violations:
            print("\n❌ CRITICAL METHOD SIGNATURE VIOLATIONS:")
            for violation in signature_violations:
                print(f"   - {violation}")

            # This should FAIL before SSOT consolidation
            pytest.fail(
                f"CRITICAL METHOD SIGNATURE VIOLATIONS: Found {len(signature_violations)} signature "
                f"violations in business-critical WebSocket Manager methods. These methods are "
                f"essential for Golden Path functionality and must have consistent signatures "
                f"across all implementations after SSOT consolidation. Violations: {signature_violations}"
            )

        print("✅ CRITICAL METHOD SIGNATURE CONSISTENCY VALIDATED!")

    def _format_signature(self, sig: MethodSignature) -> str:
        """Format a method signature for display."""
        async_prefix = "async " if sig.is_async else ""
        params = ", ".join(f"{name}: {typ}" for name, typ in sig.parameters.items())
        return_annotation = f" -> {sig.return_type}" if sig.return_type else ""
        return f"{async_prefix}def {sig.name}({params}){return_annotation}"

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_interface_completeness(self):
        """
        FAIL-FIRST TEST: Validate WebSocket Manager interface completeness.

        EXPECTED BEHAVIOR:
        - BEFORE FIX: Some implementations missing critical methods (SHOULD FAIL)
        - AFTER FIX: All implementations expose complete interface (SHOULD PASS)

        Ensures all WebSocket Manager implementations provide the full set of methods
        required for Golden Path functionality.
        """
        canonical_interface = self.get_canonical_interface_specification()
        successful_analyses = [a for a in self.interface_analyses if a.success]

        if not successful_analyses:
            # Run interface analysis first if not done
            self.test_websocket_manager_canonical_interface_consistency()
            successful_analyses = [a for a in self.interface_analyses if a.success]

        print(f"\n=== INTERFACE COMPLETENESS VALIDATION ===")
        print(f"Required canonical methods: {len(canonical_interface)}")
        print(f"Implementations to validate: {len(successful_analyses)}")
        print()

        completeness_violations = []

        for analysis in successful_analyses:
            print(f"🔍 COMPLETENESS CHECK: {analysis.import_path}")

            missing_methods = []
            available_methods = set(analysis.methods.keys())
            required_methods = set(canonical_interface.keys())

            missing = required_methods - available_methods
            if missing:
                missing_methods.extend(missing)
                print(f"   ❌ Missing {len(missing)} required methods: {missing}")
            else:
                print(f"   ✅ All {len(required_methods)} required methods present")

            extra_methods = available_methods - required_methods
            if extra_methods:
                print(f"   ℹ️  Extra methods (not in canonical): {extra_methods}")

            if missing_methods:
                violation = f"{analysis.import_path}: missing {len(missing_methods)} methods ({missing_methods})"
                completeness_violations.append(violation)

            print(f"   📊 Interface completeness: {(len(available_methods & required_methods)/len(required_methods)*100):.1f}%")
            print()

        print(f"=== COMPLETENESS SUMMARY ===")
        print(f"Completeness violations: {len(completeness_violations)}")

        if completeness_violations:
            print("\n❌ INTERFACE COMPLETENESS VIOLATIONS:")
            for violation in completeness_violations:
                print(f"   - {violation}")

            # This should FAIL before SSOT consolidation
            pytest.fail(
                f"INTERFACE COMPLETENESS VIOLATIONS: Found {len(completeness_violations)} implementations "
                f"with incomplete interfaces. After SSOT consolidation, all WebSocket Manager implementations "
                f"must expose the complete canonical interface required for Golden Path functionality. "
                f"Violations: {completeness_violations}"
            )

        print("✅ INTERFACE COMPLETENESS VALIDATED!")
        print("All implementations expose the complete canonical interface.")

    def teardown_method(self, method):
        """Clean up test environment."""
        self.interface_analyses.clear()
        super().teardown_method(method)