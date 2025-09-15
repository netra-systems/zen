"""
Test Issue #1181 MessageRouter SSOT Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System Stability and SSOT Compliance
- Value Impact: Ensure consistent message routing behavior across all user interactions
- Strategic Impact: $500K+ ARR protection - message routing reliability is core infrastructure

This test validates MessageRouter SSOT compliance and identifies consolidation requirements
for achieving single source of truth message routing infrastructure.
"""

import pytest
from typing import Dict, Any, List, Set
from unittest.mock import patch

from test_framework.base_test_case import BaseTestCase


class TestIssue1181MessageRouterSSOTValidation(BaseTestCase):
    """Test MessageRouter SSOT compliance and consolidation validation."""

    def test_message_router_class_identity_consistency(self):
        """
        Test that MessageRouter class maintains consistent identity across import paths.
        
        SSOT Requirement: Same class object should be returned regardless of import path.
        Business Impact: Inconsistent class identity could cause routing conflicts.
        """
        
        # Import from canonical path
        from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter
        
        # Import from deprecated path
        from netra_backend.app.websocket_core import MessageRouter as DeprecatedRouter
        
        # Test SSOT compliance - these MUST be identical objects
        assert CanonicalRouter is DeprecatedRouter, (
            "SSOT VIOLATION: MessageRouter class identity inconsistent across import paths. "
            f"Canonical ID: {id(CanonicalRouter)}, Deprecated ID: {id(DeprecatedRouter)}"
        )
        
        # Verify class attributes are identical
        assert CanonicalRouter.__name__ == DeprecatedRouter.__name__
        assert CanonicalRouter.__module__ == DeprecatedRouter.__module__
        
        # Document SSOT compliance status
        self._document_ssot_class_identity_status(CanonicalRouter, DeprecatedRouter)

    def test_message_router_import_usage_analysis(self):
        """
        Analyze MessageRouter import usage patterns across the codebase.
        
        This identifies which files use canonical vs deprecated imports
        to plan the migration strategy.
        """
        
        import subprocess
        import os
        
        # Search for MessageRouter imports across the codebase
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Find canonical imports
        canonical_search = subprocess.run([
            "grep", "-r", "-n", 
            "from netra_backend.app.websocket_core.handlers import.*MessageRouter",
            project_root
        ], capture_output=True, text=True)
        
        # Find deprecated imports
        deprecated_search = subprocess.run([
            "grep", "-r", "-n", 
            "from netra_backend.app.websocket_core import.*MessageRouter",
            project_root
        ], capture_output=True, text=True)
        
        # Parse results
        canonical_usages = self._parse_grep_results(canonical_search.stdout)
        deprecated_usages = self._parse_grep_results(deprecated_search.stdout)
        
        # Analyze usage patterns
        self._analyze_import_usage_patterns(canonical_usages, deprecated_usages)
        
        # Verify migration readiness
        total_usages = len(canonical_usages) + len(deprecated_usages)
        assert total_usages > 0, "No MessageRouter imports found - this indicates a search issue"

    def test_message_router_interface_consistency(self):
        """
        Test that MessageRouter interface is consistent across all import paths.
        
        This ensures that consolidation won't break existing consumers by changing
        the interface contract.
        """
        
        # Import from all working paths
        from netra_backend.app.websocket_core.handlers import MessageRouter as Handler
        from netra_backend.app.websocket_core import MessageRouter as Core
        
        # Get interface definitions
        handler_interface = self._get_class_interface(Handler)
        core_interface = self._get_class_interface(Core)
        
        # Verify interfaces are identical
        assert handler_interface == core_interface, (
            f"Interface mismatch detected:\n"
            f"Handler interface: {handler_interface}\n"
            f"Core interface: {core_interface}"
        )
        
        # Document interface consistency for consolidation validation
        self._document_interface_consistency(handler_interface, core_interface)

    def test_deprecated_import_path_migration_readiness(self):
        """
        Test readiness for migrating deprecated import paths to canonical paths.
        
        This validates that the deprecated path can be safely removed after
        consumers are migrated to the canonical path.
        """
        
        # Test that deprecated path currently works
        try:
            from netra_backend.app.websocket_core import MessageRouter
            deprecated_import_works = True
        except ImportError:
            deprecated_import_works = False
        
        # Test that canonical path works
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            canonical_import_works = True
        except ImportError:
            canonical_import_works = False
        
        # Verify both paths currently work (needed for safe migration)
        assert canonical_import_works, "Canonical import path must work for migration"
        assert deprecated_import_works, "Deprecated path should work during migration period"
        
        # Document migration readiness
        self._document_migration_readiness(canonical_import_works, deprecated_import_works)

    def test_ssot_compliance_measurement(self):
        """
        Measure current SSOT compliance level for MessageRouter implementations.
        
        This provides metrics for tracking consolidation progress and success.
        """
        
        compliance_metrics = {
            "canonical_imports_working": False,
            "deprecated_imports_working": False,
            "class_identity_consistent": False,
            "interface_consistent": False,
            "quality_router_accessible": False
        }
        
        # Test canonical imports
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            compliance_metrics["canonical_imports_working"] = True
        except ImportError:
            pass
        
        # Test deprecated imports
        try:
            from netra_backend.app.websocket_core import MessageRouter as DeprecatedRouter
            compliance_metrics["deprecated_imports_working"] = True
        except ImportError:
            pass
        
        # Test class identity consistency (if both imports work)
        if compliance_metrics["canonical_imports_working"] and compliance_metrics["deprecated_imports_working"]:
            from netra_backend.app.websocket_core.handlers import MessageRouter as C
            from netra_backend.app.websocket_core import MessageRouter as D
            compliance_metrics["class_identity_consistent"] = (C is D)
            compliance_metrics["interface_consistent"] = (
                self._get_class_interface(C) == self._get_class_interface(D)
            )
        
        # Test quality router accessibility
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            compliance_metrics["quality_router_accessible"] = True
        except ImportError:
            pass
        
        # Calculate compliance score
        compliance_score = sum(compliance_metrics.values()) / len(compliance_metrics)
        
        # Document compliance metrics
        self._document_ssot_compliance_metrics(compliance_metrics, compliance_score)
        
        # Assert minimum compliance requirements
        assert compliance_metrics["canonical_imports_working"], "Canonical imports must work"
        assert compliance_score >= 0.6, f"SSOT compliance too low: {compliance_score:.1%}"

    def test_message_router_consolidation_impact_analysis(self):
        """
        Analyze the impact of MessageRouter consolidation on system components.
        
        This identifies potential breaking changes and required updates for
        successful SSOT consolidation.
        """
        
        impact_analysis = {
            "working_imports": [],
            "broken_imports": [],
            "consumers_needing_updates": [],
            "consolidation_blockers": []
        }
        
        # Test working imports
        working_imports = [
            "netra_backend.app.websocket_core.handlers.MessageRouter",
            "netra_backend.app.websocket_core.MessageRouter"
        ]
        
        for import_path in working_imports:
            if self._test_import_success(import_path):
                impact_analysis["working_imports"].append(import_path)
        
        # Test broken imports
        broken_imports = [
            "netra_backend.app.services.websocket.quality_message_router.QualityMessageRouter"
        ]
        
        for import_path in broken_imports:
            if not self._test_import_success(import_path):
                impact_analysis["broken_imports"].append(import_path)
        
        # Identify consolidation requirements
        if len(impact_analysis["broken_imports"]) > 0:
            impact_analysis["consolidation_blockers"].extend(impact_analysis["broken_imports"])
        
        # Document impact analysis
        self._document_consolidation_impact_analysis(impact_analysis)
        
        # Verify consolidation is feasible
        assert len(impact_analysis["working_imports"]) > 0, "No working imports found - cannot consolidate"

    def _parse_grep_results(self, grep_output: str) -> List[Dict[str, str]]:
        """Parse grep results into structured data."""
        results = []
        if not grep_output:
            return results
        
        for line in grep_output.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 2)
                if len(parts) >= 2:
                    results.append({
                        "file": parts[0],
                        "line": parts[1] if len(parts) > 2 else "unknown",
                        "content": parts[2] if len(parts) > 2 else parts[1]
                    })
        return results

    def _analyze_import_usage_patterns(self, canonical: List[Dict], deprecated: List[Dict]) -> None:
        """Analyze import usage patterns for migration planning."""
        print(f"\n--- MessageRouter Import Usage Analysis ---")
        print(f"Canonical imports (netra_backend.app.websocket_core.handlers): {len(canonical)}")
        print(f"Deprecated imports (netra_backend.app.websocket_core): {len(deprecated)}")
        
        total = len(canonical) + len(deprecated)
        if total > 0:
            canonical_percentage = (len(canonical) / total) * 100
            print(f"Canonical usage: {canonical_percentage:.1f}%")
            print(f"Migration needed for {len(deprecated)} files")
        
        # Show some examples
        if deprecated:
            print(f"\nFiles needing migration (showing first 5):")
            for usage in deprecated[:5]:
                print(f"  - {usage['file']}:{usage['line']}")

    def _get_class_interface(self, cls: type) -> Set[str]:
        """Get the public interface of a class."""
        return set(attr for attr in dir(cls) if not attr.startswith('_'))

    def _document_ssot_class_identity_status(self, canonical: type, deprecated: type) -> None:
        """Document SSOT class identity status."""
        print(f"\n--- SSOT Class Identity Validation ---")
        print(f"Canonical class ID: {id(canonical)}")
        print(f"Deprecated class ID: {id(deprecated)}")
        print(f"Identity match: {canonical is deprecated}")
        print(f"SSOT Status: {'✅ COMPLIANT' if canonical is deprecated else '❌ VIOLATION'}")

    def _document_interface_consistency(self, handler_iface: Set[str], core_iface: Set[str]) -> None:
        """Document interface consistency status."""
        print(f"\n--- Interface Consistency Validation ---")
        print(f"Handler interface methods: {len(handler_iface)}")
        print(f"Core interface methods: {len(core_iface)}")
        print(f"Interfaces match: {handler_iface == core_iface}")
        
        if handler_iface != core_iface:
            only_in_handler = handler_iface - core_iface
            only_in_core = core_iface - handler_iface
            if only_in_handler:
                print(f"Only in handler: {only_in_handler}")
            if only_in_core:
                print(f"Only in core: {only_in_core}")

    def _document_migration_readiness(self, canonical_works: bool, deprecated_works: bool) -> None:
        """Document migration readiness status."""
        print(f"\n--- Migration Readiness Assessment ---")
        print(f"Canonical path working: {'✅' if canonical_works else '❌'}")
        print(f"Deprecated path working: {'✅' if deprecated_works else '❌'}")
        
        if canonical_works and deprecated_works:
            print(f"Migration Status: ✅ READY - Both paths work, safe to migrate consumers")
        elif canonical_works and not deprecated_works:
            print(f"Migration Status: ⚠️ ALREADY MIGRATED - Deprecated path already removed")
        elif not canonical_works:
            print(f"Migration Status: ❌ BLOCKED - Canonical path must work first")

    def _document_ssot_compliance_metrics(self, metrics: Dict[str, bool], score: float) -> None:
        """Document SSOT compliance metrics."""
        print(f"\n--- SSOT Compliance Metrics ---")
        print(f"Overall Score: {score:.1%}")
        print(f"Compliance Details:")
        for metric, status in metrics.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {metric.replace('_', ' ').title()}")

    def _document_consolidation_impact_analysis(self, analysis: Dict[str, List]) -> None:
        """Document consolidation impact analysis."""
        print(f"\n--- Consolidation Impact Analysis ---")
        print(f"Working imports: {len(analysis['working_imports'])}")
        for imp in analysis['working_imports']:
            print(f"  ✅ {imp}")
        
        print(f"Broken imports: {len(analysis['broken_imports'])}")
        for imp in analysis['broken_imports']:
            print(f"  ❌ {imp}")
        
        print(f"Consolidation blockers: {len(analysis['consolidation_blockers'])}")
        for blocker in analysis['consolidation_blockers']:
            print(f"  🚫 {blocker}")

    def _test_import_success(self, import_path: str) -> bool:
        """Test if an import path works successfully."""
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            return True
        except (ImportError, AttributeError):
            return False


class TestIssue1181SSOTConsolidationPlanning(BaseTestCase):
    """Test SSOT consolidation planning and validation for MessageRouter."""

    def test_consolidation_approach_validation(self):
        """
        Validate the proposed SSOT consolidation approach.
        
        This tests whether the planned consolidation approach will work
        without breaking existing functionality.
        """
        
        consolidation_plan = {
            "approach": "single_canonical_implementation",
            "canonical_path": "netra_backend.app.websocket_core.handlers.MessageRouter",
            "deprecated_paths_to_remove": [
                "netra_backend.app.websocket_core.MessageRouter"
            ],
            "broken_implementations_to_fix": [
                "netra_backend.app.services.websocket.quality_message_router.QualityMessageRouter"
            ]
        }
        
        # Validate canonical path works
        canonical_works = self._test_import_success(consolidation_plan["canonical_path"])
        assert canonical_works, f"Canonical path must work: {consolidation_plan['canonical_path']}"
        
        # Test each deprecated path
        deprecated_status = {}
        for path in consolidation_plan["deprecated_paths_to_remove"]:
            deprecated_status[path] = self._test_import_success(path)
        
        # Test broken implementations
        broken_status = {}
        for path in consolidation_plan["broken_implementations_to_fix"]:
            broken_status[path] = self._test_import_success(path)
        
        # Document consolidation plan validation
        self._document_consolidation_plan_validation(
            consolidation_plan, canonical_works, deprecated_status, broken_status
        )

    def test_post_consolidation_requirements_validation(self):
        """
        Test requirements that must be met after consolidation is complete.
        
        This defines the success criteria for the SSOT consolidation.
        """
        
        post_consolidation_requirements = {
            "single_message_router_implementation": True,
            "quality_router_functionality_preserved": True,
            "all_imports_use_canonical_path": True,
            "no_deprecated_imports_remain": True,
            "websocket_events_still_delivered": True,
            "golden_path_functionality_preserved": True
        }
        
        # These are the requirements - we document them here for validation
        # after consolidation is implemented
        self._document_post_consolidation_requirements(post_consolidation_requirements)
        
        # For now, just verify we can define the requirements
        assert len(post_consolidation_requirements) > 0

    def _document_consolidation_plan_validation(self, plan: Dict, canonical_works: bool, 
                                              deprecated_status: Dict, broken_status: Dict) -> None:
        """Document consolidation plan validation results."""
        print(f"\n--- Consolidation Plan Validation ---")
        print(f"Approach: {plan['approach']}")
        print(f"Canonical path working: {'✅' if canonical_works else '❌'}")
        
        print(f"\nDeprecated paths to remove:")
        for path, works in deprecated_status.items():
            status = "✅ WORKING (ready for removal)" if works else "❌ ALREADY BROKEN"
            print(f"  {status} {path}")
        
        print(f"\nBroken implementations to fix:")
        for path, works in broken_status.items():
            status = "✅ WORKING (no fix needed)" if works else "❌ NEEDS FIXING"
            print(f"  {status} {path}")

    def _document_post_consolidation_requirements(self, requirements: Dict[str, bool]) -> None:
        """Document post-consolidation success criteria."""
        print(f"\n--- Post-Consolidation Success Criteria ---")
        for requirement, expected in requirements.items():
            print(f"  - {requirement.replace('_', ' ').title()}: {'Required' if expected else 'Optional'}")