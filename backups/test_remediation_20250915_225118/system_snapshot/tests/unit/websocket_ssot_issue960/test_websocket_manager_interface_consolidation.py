#!/usr/bin/env python
"""Unit Test: Issue #960 WebSocket Manager Interface Consolidation

GitHub Issue: #960 WebSocket Manager SSOT fragmentation crisis

THIS TEST VALIDATES INTERFACE CONSISTENCY ACROSS WEBSOCKET MANAGERS.
Business Value: $500K+ ARR - Validates consistent interfaces across WebSocket managers

PURPOSE:
- Test validates consistent interfaces across all WebSocket manager implementations
- This test SHOULD FAIL initially (proving inconsistencies exist)
- This test SHOULD PASS after SSOT interface consolidation (proving fix works)
- Validates method signature consistency and async/sync interface compliance

CRITICAL INTERFACE VIOLATIONS DETECTED:
- Different WebSocket managers have inconsistent method signatures
- Async/sync method inconsistencies (related to Issue #1094)
- Inconsistent event delivery method signatures across implementations
- Interface fragmentation creating user isolation failures

TEST STRATEGY:
1. Scan all WebSocket manager implementations for method signatures
2. Compare method signatures across different managers
3. Detect async/sync inconsistencies that cause integration failures
4. Validate event delivery interface uniformity
5. This test should FAIL until interface consolidation is complete

BUSINESS IMPACT:
Interface inconsistencies create unpredictable WebSocket behavior, breaking
the Golden Path user flow where users login and receive AI responses.
"""

import os
import sys
import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Callable
from collections import defaultdict
import asyncio

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger


class WebSocketManagerInterfaceConsolidationTests(SSotBaseTestCase):
    """Issue #960: WebSocket Manager Interface Consolidation Validation

    This test validates consistent interfaces across all WebSocket manager
    implementations to detect SSOT violations.

    Expected Behavior:
    - This test SHOULD FAIL initially (proving interface inconsistencies exist)
    - This test SHOULD PASS after SSOT interface consolidation (proving fix works)
    """

    def setup_method(self, method):
        """Set up test environment for interface consolidation validation."""
        super().setup_method(method)

        # Define WebSocket manager classes to analyze
        self.manager_classes = {}
        self.interface_violations = defaultdict(list)

        # Attempt to import all known WebSocket manager implementations
        self.manager_import_specs = [
            ('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'),
            ('netra_backend.app.websocket_core.unified_manager', '_UnifiedWebSocketManagerImplementation'),
            ('netra_backend.app.websocket_core.manager', 'WebSocketManager'),
        ]

        # Load manager classes for analysis
        self._load_manager_classes()

    def test_method_signature_consistency(self):
        """CRITICAL: Detect inconsistent method signatures across managers (SHOULD FAIL initially)

        This test finds methods with same names but different signatures across
        different WebSocket manager implementations.
        """
        logger.info("🔍 Analyzing method signature consistency across WebSocket managers...")

        signature_inconsistencies = []
        method_signatures = defaultdict(list)

        # Collect method signatures from each manager class
        for manager_name, manager_class in self.manager_classes.items():
            if manager_class:
                methods = inspect.getmembers(manager_class, predicate=inspect.isfunction)
                methods.extend(inspect.getmembers(manager_class, predicate=inspect.ismethod))

                for method_name, method_obj in methods:
                    # Skip private and special methods
                    if method_name.startswith('_'):
                        continue

                    try:
                        signature = inspect.signature(method_obj)
                        method_signatures[method_name].append({
                            'manager': manager_name,
                            'signature': str(signature),
                            'signature_obj': signature,
                            'method': method_obj
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not get signature for {manager_name}.{method_name}: {e}")

        # Analyze signature consistency
        for method_name, signatures in method_signatures.items():
            if len(signatures) > 1:
                # Check if all signatures are identical
                unique_signatures = set(sig['signature'] for sig in signatures)
                if len(unique_signatures) > 1:
                    signature_inconsistencies.append({
                        'method_name': method_name,
                        'signatures': signatures,
                        'unique_count': len(unique_signatures),
                        'violation_type': 'signature_mismatch'
                    })

                    logger.error(f"🚨 SIGNATURE INCONSISTENCY: {method_name}")
                    for sig in signatures:
                        logger.error(f"  {sig['manager']}: {sig['signature']}")

        self.interface_violations['signature_inconsistencies'] = signature_inconsistencies

        # ASSERTION: This should FAIL initially if signature inconsistencies exist
        assert len(signature_inconsistencies) == 0, (
            f"Interface SSOT VIOLATION: Found {len(signature_inconsistencies)} methods with inconsistent signatures. "
            f"Methods with inconsistencies: {[v['method_name'] for v in signature_inconsistencies]}. "
            f"SSOT requires consistent method signatures across all WebSocket manager implementations."
        )

    def test_async_interface_compliance(self):
        """CRITICAL: Detect async/sync method inconsistencies (SHOULD FAIL initially)

        This test identifies methods that are async in some managers but sync in others,
        which causes integration failures (related to Issue #1094).
        """
        logger.info("🔍 Analyzing async/sync interface compliance across WebSocket managers...")

        async_sync_violations = []
        method_async_status = defaultdict(list)

        # Collect async/sync status for each method
        for manager_name, manager_class in self.manager_classes.items():
            if manager_class:
                methods = inspect.getmembers(manager_class, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x))

                for method_name, method_obj in methods:
                    # Skip private and special methods
                    if method_name.startswith('_'):
                        continue

                    is_async = asyncio.iscoroutinefunction(method_obj)
                    method_async_status[method_name].append({
                        'manager': manager_name,
                        'is_async': is_async,
                        'method': method_obj
                    })

        # Detect async/sync inconsistencies
        for method_name, async_statuses in method_async_status.items():
            if len(async_statuses) > 1:
                # Check if async status is consistent
                unique_async_statuses = set(status['is_async'] for status in async_statuses)
                if len(unique_async_statuses) > 1:
                    async_sync_violations.append({
                        'method_name': method_name,
                        'async_statuses': async_statuses,
                        'violation_type': 'async_sync_mismatch'
                    })

                    logger.error(f"🚨 ASYNC/SYNC VIOLATION: {method_name}")
                    for status in async_statuses:
                        async_label = "async" if status['is_async'] else "sync"
                        logger.error(f"  {status['manager']}: {async_label}")

        self.interface_violations['async_sync_violations'] = async_sync_violations

        # ASSERTION: This should FAIL initially if async/sync inconsistencies exist
        assert len(async_sync_violations) == 0, (
            f"Interface SSOT VIOLATION: Found {len(async_sync_violations)} methods with async/sync inconsistencies. "
            f"Methods with async/sync violations: {[v['method_name'] for v in async_sync_violations]}. "
            f"Related to Issue #1094 - SSOT requires consistent async/sync patterns across managers."
        )

    def test_event_delivery_interface_uniformity(self):
        """CRITICAL: Detect inconsistent event delivery method interfaces (SHOULD FAIL initially)

        This test validates that event delivery methods have consistent interfaces
        across all WebSocket manager implementations.
        """
        logger.info("🔍 Analyzing event delivery interface uniformity...")

        event_interface_violations = []

        # Define critical event delivery methods that must be consistent
        critical_event_methods = [
            'emit_agent_event',
            'send_agent_started',
            'send_agent_thinking',
            'send_tool_executing',
            'send_tool_completed',
            'send_agent_completed',
            'send_message',
            'broadcast_event'
        ]

        event_method_analysis = defaultdict(dict)

        # Analyze event delivery methods across managers
        for manager_name, manager_class in self.manager_classes.items():
            if manager_class:
                for method_name in critical_event_methods:
                    if hasattr(manager_class, method_name):
                        method_obj = getattr(manager_class, method_name)
                        try:
                            signature = inspect.signature(method_obj)
                            is_async = asyncio.iscoroutinefunction(method_obj)

                            event_method_analysis[method_name][manager_name] = {
                                'signature': str(signature),
                                'is_async': is_async,
                                'exists': True
                            }
                        except (ValueError, TypeError) as e:
                            event_method_analysis[method_name][manager_name] = {
                                'signature': None,
                                'is_async': None,
                                'exists': True,
                                'error': str(e)
                            }
                    else:
                        event_method_analysis[method_name][manager_name] = {
                            'signature': None,
                            'is_async': None,
                            'exists': False
                        }

        # Detect event delivery interface violations
        for method_name, manager_data in event_method_analysis.items():
            if len(manager_data) > 1:
                # Check existence consistency
                existence_values = [data['exists'] for data in manager_data.values()]
                if not all(existence_values) and any(existence_values):
                    event_interface_violations.append({
                        'method_name': method_name,
                        'violation_type': 'partial_implementation',
                        'managers': list(manager_data.keys()),
                        'details': manager_data
                    })

                    logger.error(f"🚨 EVENT METHOD PARTIAL IMPLEMENTATION: {method_name}")
                    for mgr, data in manager_data.items():
                        status = "EXISTS" if data['exists'] else "MISSING"
                        logger.error(f"  {mgr}: {status}")

                # Check signature consistency for existing methods
                existing_signatures = [
                    data['signature'] for data in manager_data.values()
                    if data['exists'] and data['signature']
                ]
                if len(set(existing_signatures)) > 1:
                    event_interface_violations.append({
                        'method_name': method_name,
                        'violation_type': 'signature_inconsistency',
                        'managers': list(manager_data.keys()),
                        'details': manager_data
                    })

                    logger.error(f"🚨 EVENT METHOD SIGNATURE INCONSISTENCY: {method_name}")

        self.interface_violations['event_interface_violations'] = event_interface_violations

        # ASSERTION: This should FAIL initially if event interface violations exist
        assert len(event_interface_violations) == 0, (
            f"Event Interface SSOT VIOLATION: Found {len(event_interface_violations)} event delivery interface violations. "
            f"Violating methods: {[v['method_name'] for v in event_interface_violations]}. "
            f"SSOT requires consistent event delivery interfaces across all WebSocket managers."
        )

    def test_validate_websocket_manager_interface_completeness(self):
        """VALIDATION: Check interface completeness across WebSocket managers

        This test validates that all WebSocket managers implement the complete
        interface required for Golden Path functionality.
        """
        logger.info("🔍 Validating WebSocket manager interface completeness...")

        # Define minimum required interface for Golden Path
        required_interface = [
            'add_connection',
            'remove_connection',
            'emit_agent_event',
            'get_active_connections',
            'send_message'
        ]

        interface_completeness = {}
        incomplete_interfaces = []

        for manager_name, manager_class in self.manager_classes.items():
            if manager_class:
                missing_methods = []
                for required_method in required_interface:
                    if not hasattr(manager_class, required_method):
                        missing_methods.append(required_method)

                interface_completeness[manager_name] = {
                    'complete': len(missing_methods) == 0,
                    'missing_methods': missing_methods,
                    'completeness_rate': (len(required_interface) - len(missing_methods)) / len(required_interface)
                }

                if missing_methods:
                    incomplete_interfaces.append({
                        'manager': manager_name,
                        'missing_methods': missing_methods
                    })

                    logger.warning(f"⚠️ INCOMPLETE INTERFACE: {manager_name}")
                    logger.warning(f"  Missing methods: {missing_methods}")

        # Log interface completeness statistics
        total_managers = len(self.manager_classes)
        complete_managers = sum(1 for comp in interface_completeness.values() if comp['complete'])
        completeness_rate = complete_managers / total_managers if total_managers > 0 else 1.0

        logger.info(f"📊 Interface Completeness Statistics:")
        logger.info(f"  Complete interfaces: {complete_managers}/{total_managers}")
        logger.info(f"  Completeness rate: {completeness_rate:.1%}")

        self.interface_violations['interface_completeness'] = {
            'incomplete_interfaces': incomplete_interfaces,
            'completeness_statistics': interface_completeness,
            'overall_completeness_rate': completeness_rate
        }

        # This test provides information but doesn't fail
        # It helps guide the remediation process
        if incomplete_interfaces:
            logger.warning(f"⚠️ {len(incomplete_interfaces)} managers have incomplete interfaces")
        else:
            logger.info("✅ All WebSocket managers have complete interfaces")

    def _load_manager_classes(self):
        """Load WebSocket manager classes for analysis."""
        for module_path, class_name in self.manager_import_specs:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    manager_class = getattr(module, class_name)
                    manager_key = f"{module_path}.{class_name}"
                    self.manager_classes[manager_key] = manager_class
                    logger.info(f"✓ Loaded manager class: {manager_key}")
                else:
                    logger.warning(f"⚠️ Class {class_name} not found in {module_path}")
                    self.manager_classes[f"{module_path}.{class_name}"] = None
            except ImportError as e:
                logger.warning(f"⚠️ Could not import {module_path}: {e}")
                self.manager_classes[f"{module_path}.{class_name}"] = None

    def teardown_method(self, method):
        """Clean up and log interface consolidation results."""
        if self.interface_violations:
            logger.info("📊 Interface Consolidation Analysis Summary:")

            total_violations = 0
            for violation_type, violations in self.interface_violations.items():
                if isinstance(violations, list) and violations:
                    count = len(violations)
                    total_violations += count
                    logger.warning(f"  {violation_type}: {count} violations")
                elif isinstance(violations, dict) and 'overall_completeness_rate' in violations:
                    rate = violations['overall_completeness_rate']
                    logger.info(f"  {violation_type}: {rate:.1%} complete")

            if total_violations > 0:
                logger.error(f"🚨 TOTAL INTERFACE VIOLATIONS: {total_violations}")
                logger.error("💡 Consolidation required to standardize WebSocket manager interfaces")
            else:
                logger.info("✅ No interface violations detected - interfaces are consistent")

        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test directly to check interface consistency
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution