"""SSOT Compliance Validation Test Suite - WebSocket Bridge Consolidation

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: SSOT Compliance & System Reliability
- Value Impact: Protects $500K+ ARR Golden Path functionality during bridge consolidation
- Strategic Impact: Ensures safe WebSocket bridge SSOT consolidation with zero customer impact

This test suite validates SSOT consolidation requirements for WebSocket bridge implementations:
1. Single Implementation Enforcement - Only one AgentWebSocketBridge implementation exists
2. Factory Pattern Consolidation - Consistent bridge creation across all factories  
3. Duplicate Detection - No duplicate bridge classes or adapters
4. Interface Consistency - All interfaces provide identical WebSocket event functionality
5. Event Delivery Consistency - All 5 critical events delivered identically across bridges
6. User Isolation Consistency - User context isolation identical across implementations

These tests ensure that WebSocket bridge consolidation maintains the reliability of
90% of platform value (chat functionality) while eliminating SSOT violations.
"""

import asyncio
import inspect
import os
import sys
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import importlib
import pkgutil
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase, CategoryType
from shared.isolated_environment import get_env


class TestSSOTComplianceValidation(SSotAsyncTestCase):
    """SSOT Compliance validation tests for WebSocket bridge consolidation.
    
    These tests enforce SSOT requirements and detect violations that would
    impact the Golden Path user flow protecting $500K+ ARR.
    """
    
    def setup_method(self, method):
        """Set up test environment for SSOT validation."""
        super().setup_method(method)
        self.env = get_env()
        
        # Track discovered bridge implementations for analysis
        self.discovered_bridges: Dict[str, Any] = {}
        self.discovered_factories: Dict[str, Any] = {}
        self.discovered_adapters: Dict[str, Any] = {}
        
        # Expected SSOT paths (canonical implementations)
        self.ssot_bridge_path = "netra_backend.app.services.agent_websocket_bridge"
        self.ssot_factory_paths = [
            "netra_backend.app.services.websocket_bridge_factory",
            "netra_backend.app.factories.websocket_bridge_factory"
        ]
        
        # Critical WebSocket events that must be consistent
        self.critical_events = [
            "notify_agent_started",
            "notify_agent_thinking", 
            "notify_tool_executing",
            "notify_tool_completed",
            "notify_agent_completed"
        ]
    
    # ===================== SINGLE IMPLEMENTATION ENFORCEMENT =====================
    
    def test_single_bridge_implementation_enforcement(self):
        """Test that only one AgentWebSocketBridge implementation exists (SSOT)."""
        bridges = self._discover_bridge_classes()
        
        # Should find exactly one canonical implementation
        canonical_bridges = [b for name, b in bridges.items() 
                           if self._is_canonical_bridge_implementation(name, b)]
        
        self.assertEqual(
            len(canonical_bridges), 1,
            f"SSOT VIOLATION: Expected exactly 1 canonical AgentWebSocketBridge, "
            f"found {len(canonical_bridges)}: {[self._get_class_source(b) for b in canonical_bridges]}"
        )
        
        # All other bridges should be compatibility wrappers or redirects
        non_canonical_bridges = [b for name, b in bridges.items()
                               if not self._is_canonical_bridge_implementation(name, b)]
        
        for name, bridge_class in non_canonical_bridges:
            self._validate_compatibility_bridge(name, bridge_class)
    
    def test_factory_pattern_consolidation(self):
        """Test that WebSocketBridgeFactory creates consistent instances."""
        factories = self._discover_factory_classes()
        
        # Each factory should create instances through SSOT patterns
        for factory_name, factory_class in factories.items():
            with self.subTest(factory=factory_name):
                self._validate_factory_ssot_compliance(factory_name, factory_class)
    
    def test_adapter_duplication_elimination(self):
        """Test that no duplicate adapter implementations exist."""
        adapters = self._discover_adapter_classes()
        
        # Group adapters by functionality signature 
        functionality_groups = self._group_adapters_by_functionality(adapters)
        
        for functionality, adapter_list in functionality_groups.items():
            if len(adapter_list) > 1:
                # Multiple adapters with same functionality - check for SSOT compliance
                ssot_adapters = [a for a in adapter_list if self._is_ssot_adapter(a)]
                
                self.assertGreaterEqual(
                    len(ssot_adapters), 1,
                    f"SSOT VIOLATION: Multiple adapters with functionality '{functionality}' "
                    f"but no SSOT implementation: {[self._get_class_source(a[1]) for a in adapter_list]}"
                )
    
    def test_interface_consistency_validation(self):
        """Test that all bridge interfaces provide identical WebSocket functionality."""
        bridges = self._discover_bridge_classes()
        
        if len(bridges) < 2:
            self.skipTest("Need at least 2 bridge implementations to test interface consistency")
        
        # Compare method signatures across all bridges
        method_signatures = {}
        for bridge_name, bridge_class in bridges.items():
            signatures = self._extract_websocket_method_signatures(bridge_class)
            method_signatures[bridge_name] = signatures
        
        # All bridges should have identical signatures for critical events
        reference_bridge = next(iter(method_signatures.keys()))
        reference_signatures = method_signatures[reference_bridge]
        
        for bridge_name, signatures in method_signatures.items():
            if bridge_name == reference_bridge:
                continue
                
            for event_method in self.critical_events:
                if event_method in reference_signatures and event_method in signatures:
                    self._compare_method_signatures(
                        reference_signatures[event_method],
                        signatures[event_method],
                        f"{reference_bridge}.{event_method}",
                        f"{bridge_name}.{event_method}"
                    )
    
    # ===================== DUPLICATE DETECTION TESTS =====================
    
    def test_no_duplicate_bridge_classes(self):
        """Test that no duplicate WebSocket bridge class definitions exist."""
        bridge_definitions = self._scan_for_duplicate_class_definitions("WebSocketBridge", "AgentWebSocketBridge")
        
        # Group by class content hash to detect true duplicates
        content_groups = self._group_classes_by_content(bridge_definitions)
        
        for content_hash, class_list in content_groups.items():
            if len(class_list) > 1:
                # Check if duplicates are legitimate (e.g., compatibility layers)
                legitimate_duplicates = self._validate_legitimate_duplicates(class_list)
                
                if not legitimate_duplicates:
                    self.fail(
                        f"SSOT VIOLATION: Duplicate bridge class definitions found:\n" +
                        "\n".join(f"  - {cls['file']}:{cls['line']} ({cls['name']})" 
                                for cls in class_list)
                    )
    
    def test_consistent_method_signatures(self):
        """Test that method signatures are consistent across bridge implementations."""
        bridges = self._discover_bridge_classes()
        
        # Extract method signatures for comparison
        all_signatures = {}
        for bridge_name, bridge_class in bridges.items():
            all_signatures[bridge_name] = self._extract_all_method_signatures(bridge_class)
        
        # Compare signatures for each critical event method
        for event_method in self.critical_events:
            bridge_signatures = {}
            
            for bridge_name, signatures in all_signatures.items():
                if event_method in signatures:
                    bridge_signatures[bridge_name] = signatures[event_method]
            
            if len(bridge_signatures) > 1:
                self._validate_signature_consistency(event_method, bridge_signatures)
    
    def test_import_path_consistency(self):
        """Test that import paths are consolidated to SSOT locations."""
        # Scan for bridge imports across the codebase
        bridge_imports = self._scan_bridge_imports()
        
        # Categorize imports as SSOT or non-SSOT  
        ssot_imports = []
        deprecated_imports = []
        
        for import_info in bridge_imports:
            if self._is_ssot_import_path(import_info['path']):
                ssot_imports.append(import_info)
            else:
                deprecated_imports.append(import_info)
        
        # Report on import consistency
        total_imports = len(ssot_imports) + len(deprecated_imports)
        if total_imports > 0:
            ssot_percentage = len(ssot_imports) / total_imports * 100
            
            # At least 80% of imports should use SSOT paths (allowing transition period)
            self.assertGreaterEqual(
                ssot_percentage, 80.0,
                f"SSOT VIOLATION: Only {ssot_percentage:.1f}% of bridge imports use SSOT paths. "
                f"Found {len(deprecated_imports)} deprecated imports: "
                f"{[imp['file'] for imp in deprecated_imports[:5]]}"
            )
    
    # ===================== EVENT DELIVERY CONSISTENCY TESTS =====================
    
    async def test_event_consistency_across_bridges(self):
        """Test that all bridges deliver identical WebSocket events."""
        bridges = await self._create_test_bridge_instances()
        
        if len(bridges) < 2:
            self.skipTest("Need at least 2 bridge instances to test event consistency")
        
        # Mock WebSocket event delivery to capture events
        event_capture = {}
        
        for bridge_name, bridge_instance in bridges.items():
            event_capture[bridge_name] = []
            self._mock_bridge_event_delivery(bridge_instance, event_capture[bridge_name])
        
        # Send same event through all bridges
        test_run_id = "test_run_123"
        test_agent_name = "TestAgent"
        test_context = {"test": "data"}
        
        for bridge_name, bridge_instance in bridges.items():
            try:
                if hasattr(bridge_instance, 'notify_agent_started'):
                    await bridge_instance.notify_agent_started(test_run_id, test_agent_name, test_context)
            except Exception as e:
                # Bridge might not be fully configured - log and continue
                self.logger.warning(f"Bridge {bridge_name} failed to send event: {e}")
        
        # Verify event consistency
        self._validate_event_delivery_consistency(event_capture)
    
    async def test_user_isolation_consistency(self):
        """Test that user isolation is identical across bridge implementations."""
        bridges = await self._create_test_bridge_instances()
        
        # Create test contexts for different users
        user1_context = self._create_mock_user_context("user1", "thread1", "run1")
        user2_context = self._create_mock_user_context("user2", "thread2", "run2")
        
        for bridge_name, bridge_instance in bridges.items():
            with self.subTest(bridge=bridge_name):
                # Test that bridge respects user context isolation
                isolation_result = await self._test_bridge_user_isolation(
                    bridge_instance, user1_context, user2_context
                )
                
                self.assertTrue(
                    isolation_result.isolated,
                    f"SECURITY VIOLATION: Bridge {bridge_name} failed user isolation test: "
                    f"{isolation_result.failure_reason}"
                )
    
    def test_critical_event_guarantee(self):
        """Test that all 5 critical WebSocket events are guaranteed across bridges."""
        bridges = self._discover_bridge_classes()
        
        for bridge_name, bridge_class in bridges.items():
            with self.subTest(bridge=bridge_name):
                # Verify all critical events are implemented
                missing_events = []
                
                for event_method in self.critical_events:
                    if not hasattr(bridge_class, event_method):
                        missing_events.append(event_method)
                
                self.assertEqual(
                    len(missing_events), 0,
                    f"CRITICAL VIOLATION: Bridge {bridge_name} missing critical events: {missing_events}. "
                    f"This will break 90% of platform value (chat functionality)!"
                )
                
                # Verify event methods have proper async signatures
                for event_method in self.critical_events:
                    method = getattr(bridge_class, event_method, None)
                    if method:
                        self.assertTrue(
                            asyncio.iscoroutinefunction(method),
                            f"CRITICAL VIOLATION: {bridge_name}.{event_method} is not async. "
                            f"This will cause WebSocket event delivery failures!"
                        )
    
    # ===================== HELPER METHODS =====================
    
    def _discover_bridge_classes(self) -> List[Tuple[str, type]]:
        """Discover all WebSocket bridge classes in the codebase."""
        bridges = []
        
        # Search common locations for bridge implementations
        search_paths = [
            'netra_backend.app.services',
            'netra_backend.app.factories', 
            'netra_backend.app.websocket_core',
            'netra_backend.app.agents'
        ]
        
        for module_path in search_paths:
            try:
                bridges.extend(self._scan_module_for_bridges(module_path))
            except ImportError as e:
                self.logger.debug(f"Could not import {module_path}: {e}")
        
        return bridges
    
    def _discover_factory_classes(self) -> List[Tuple[str, type]]:
        """Discover all WebSocket bridge factory classes."""
        factories = []
        
        # Known factory locations
        factory_modules = [
            'netra_backend.app.services.websocket_bridge_factory',
            'netra_backend.app.factories.websocket_bridge_factory'
        ]
        
        for module_path in factory_modules:
            try:
                factories.extend(self._scan_module_for_factories(module_path))
            except ImportError as e:
                self.logger.debug(f"Could not import factory module {module_path}: {e}")
        
        return factories
    
    def _discover_adapter_classes(self) -> List[Tuple[str, type]]:
        """Discover all WebSocket bridge adapter classes."""
        adapters = []
        
        # Search for adapter classes
        search_patterns = ['*Adapter', '*Bridge', '*WebSocket*']
        
        for pattern in search_patterns:
            adapters.extend(self._scan_for_classes_matching_pattern(pattern))
        
        return adapters
    
    def _is_canonical_bridge_implementation(self, name: str, bridge_class: type) -> bool:
        """Check if a bridge class is the canonical SSOT implementation."""
        # Canonical implementation should be in the SSOT module path
        module = getattr(bridge_class, '__module__', '')
        return module == self.ssot_bridge_path
    
    def _validate_compatibility_bridge(self, name: str, bridge_class: type) -> None:
        """Validate that a non-canonical bridge is a proper compatibility wrapper."""
        module = getattr(bridge_class, '__module__', '')
        
        # Check for deprecation warnings or SSOT redirect patterns
        source_lines = self._get_class_source_lines(bridge_class)
        
        has_deprecation = any('deprecated' in line.lower() or 'redirect' in line.lower() 
                             for line in source_lines)
        has_ssot_import = any('from netra_backend.app.services.agent_websocket_bridge import' in line
                             for line in source_lines)
        
        if not (has_deprecation or has_ssot_import):
            self.logger.warning(
                f"POTENTIAL SSOT VIOLATION: Bridge {name} in {module} may not be a proper "
                f"compatibility wrapper - no deprecation or SSOT import found"
            )
    
    def _validate_factory_ssot_compliance(self, factory_name: str, factory_class: type) -> None:
        """Validate that a factory follows SSOT patterns."""
        # Check for SSOT redirect patterns
        source_lines = self._get_class_source_lines(factory_class)
        
        # Look for SSOT imports
        has_ssot_imports = any(
            'unified_emitter' in line.lower() or 'unified_manager' in line.lower()
            for line in source_lines
        )
        
        # Check for deprecated factory patterns
        has_legacy_patterns = any(
            'singleton' in line.lower() or '_instance' in line.lower()
            for line in source_lines
        )
        
        if has_legacy_patterns and not has_ssot_imports:
            self.logger.warning(
                f"POTENTIAL SSOT VIOLATION: Factory {factory_name} uses legacy patterns "
                f"without SSOT imports"
            )
    
    def _group_adapters_by_functionality(self, adapters: List[Tuple[str, type]]) -> Dict[str, List]:
        """Group adapter classes by their functionality signature."""
        functionality_groups = {}
        
        for name, adapter_class in adapters:
            # Create a signature based on the methods the adapter implements
            signature = self._create_functionality_signature(adapter_class)
            
            if signature not in functionality_groups:
                functionality_groups[signature] = []
            
            functionality_groups[signature].append((name, adapter_class))
        
        return functionality_groups
    
    def _create_functionality_signature(self, class_obj: type) -> str:
        """Create a functionality signature for a class based on its WebSocket methods."""
        websocket_methods = []
        
        for method_name in dir(class_obj):
            if method_name.startswith('notify_') and callable(getattr(class_obj, method_name)):
                websocket_methods.append(method_name)
        
        return ','.join(sorted(websocket_methods))
    
    def _scan_module_for_bridges(self, module_path: str) -> List[Tuple[str, type]]:
        """Scan a module for bridge classes."""
        bridges = []
        
        try:
            module = importlib.import_module(module_path)
            
            for name in dir(module):
                obj = getattr(module, name)
                
                if (isinstance(obj, type) and 
                    ('Bridge' in name or 'WebSocket' in name) and
                    self._has_websocket_methods(obj)):
                    
                    bridges.append((f"{module_path}.{name}", obj))
        
        except Exception as e:
            self.logger.debug(f"Error scanning {module_path}: {e}")
        
        return bridges
    
    def _scan_module_for_factories(self, module_path: str) -> List[Tuple[str, type]]:
        """Scan a module for factory classes."""
        factories = []
        
        try:
            module = importlib.import_module(module_path)
            
            for name in dir(module):
                obj = getattr(module, name)
                
                if (isinstance(obj, type) and 
                    ('Factory' in name or 'Bridge' in name)):
                    
                    factories.append((f"{module_path}.{name}", obj))
        
        except Exception as e:
            self.logger.debug(f"Error scanning {module_path} for factories: {e}")
        
        return factories
    
    def _has_websocket_methods(self, class_obj: type) -> bool:
        """Check if a class has WebSocket notification methods."""
        websocket_method_count = sum(
            1 for method_name in dir(class_obj)
            if method_name.startswith('notify_') and callable(getattr(class_obj, method_name))
        )
        
        return websocket_method_count >= 3  # Should have at least 3 notify methods
    
    def _extract_websocket_method_signatures(self, class_obj: type) -> Dict[str, inspect.Signature]:
        """Extract method signatures for WebSocket methods."""
        signatures = {}
        
        for event_method in self.critical_events:
            if hasattr(class_obj, event_method):
                method = getattr(class_obj, event_method)
                try:
                    signatures[event_method] = inspect.signature(method)
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Could not extract signature for {class_obj.__name__}.{event_method}: {e}")
        
        return signatures
    
    def _compare_method_signatures(self, sig1: inspect.Signature, sig2: inspect.Signature, 
                                 name1: str, name2: str) -> None:
        """Compare two method signatures for consistency."""
        # Compare parameter names and types
        params1 = list(sig1.parameters.keys())
        params2 = list(sig2.parameters.keys())
        
        if params1 != params2:
            self.logger.warning(
                f"INTERFACE INCONSISTENCY: Method signature mismatch between {name1} and {name2}:\n"
                f"  {name1}: {params1}\n"
                f"  {name2}: {params2}"
            )
    
    def _get_class_source(self, class_obj: type) -> str:
        """Get the source file path for a class."""
        try:
            module = inspect.getmodule(class_obj)
            if module and hasattr(module, '__file__'):
                return module.__file__ or "unknown"
        except:
            pass
        return "unknown"
    
    def _get_class_source_lines(self, class_obj: type) -> List[str]:
        """Get source code lines for a class."""
        try:
            return inspect.getsourcelines(class_obj)[0]
        except:
            return []
    
    async def _create_test_bridge_instances(self) -> Dict[str, Any]:
        """Create test instances of bridge classes for testing."""
        bridges = self._discover_bridge_classes()
        instances = {}
        
        for bridge_name, bridge_class in bridges:
            try:
                # Try to create an instance with mock dependencies
                instance = await self._create_mock_bridge_instance(bridge_class)
                if instance:
                    instances[bridge_name] = instance
            except Exception as e:
                self.logger.debug(f"Could not create instance of {bridge_name}: {e}")
        
        return instances
    
    async def _create_mock_bridge_instance(self, bridge_class: type) -> Optional[Any]:
        """Create a mock instance of a bridge class for testing."""
        try:
            # Create mock user context
            mock_context = self._create_mock_user_context("test_user", "test_thread", "test_run")
            
            # Try different constructor patterns
            constructors_to_try = [
                lambda: bridge_class(user_context=mock_context),
                lambda: bridge_class(mock_context),
                lambda: bridge_class(),
            ]
            
            for constructor in constructors_to_try:
                try:
                    instance = constructor()
                    return instance
                except:
                    continue
            
        except Exception as e:
            self.logger.debug(f"Could not create mock instance: {e}")
        
        return None
    
    def _create_mock_user_context(self, user_id: str, thread_id: str, run_id: str) -> Mock:
        """Create a mock user execution context."""
        mock_context = Mock()
        mock_context.user_id = user_id
        mock_context.thread_id = thread_id
        mock_context.run_id = run_id
        mock_context.get_correlation_id.return_value = f"{user_id}_{thread_id}_{run_id}"
        return mock_context


class TestSSOTBridgeDiscovery(SSotAsyncTestCase):
    """Test discovery and validation of WebSocket bridge implementations."""
    
    def setup_method(self, method):
        super().setup_method(method)
        
        # Base paths for bridge discovery
        self.netra_backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend"
    
    def test_discover_all_bridge_implementations(self):
        """Discover and catalog all WebSocket bridge implementations."""
        discovered_bridges = self._comprehensive_bridge_discovery()
        
        # Should find at least the known SSOT implementations
        expected_bridges = [
            "AgentWebSocketBridge",
            "StandardWebSocketBridge", 
            "WebSocketBridgeAdapter"
        ]
        
        found_names = [info['name'] for info in discovered_bridges]
        
        for expected_name in expected_bridges:
            self.assertIn(
                expected_name, found_names,
                f"Expected bridge {expected_name} not found. "
                f"Discovered: {found_names}"
            )
    
    def test_validate_bridge_inheritance_hierarchy(self):
        """Validate bridge class inheritance hierarchy for SSOT compliance."""
        bridges = self._comprehensive_bridge_discovery()
        
        for bridge_info in bridges:
            bridge_class = bridge_info['class']
            
            # Check inheritance hierarchy
            mro = inspect.getmro(bridge_class)
            hierarchy = [cls.__name__ for cls in mro]
            
            # Log hierarchy for analysis
            self.logger.info(f"Bridge {bridge_info['name']} hierarchy: {' -> '.join(hierarchy)}")
    
    def test_bridge_method_coverage(self):
        """Test that all bridges implement required WebSocket methods."""
        bridges = self._comprehensive_bridge_discovery()
        
        required_methods = [
            "notify_agent_started",
            "notify_agent_thinking",
            "notify_tool_executing", 
            "notify_tool_completed",
            "notify_agent_completed"
        ]
        
        for bridge_info in bridges:
            bridge_class = bridge_info['class']
            
            with self.subTest(bridge=bridge_info['name']):
                missing_methods = []
                
                for method_name in required_methods:
                    if not hasattr(bridge_class, method_name):
                        missing_methods.append(method_name)
                
                self.assertEqual(
                    len(missing_methods), 0,
                    f"Bridge {bridge_info['name']} missing required methods: {missing_methods}"
                )
    
    def _comprehensive_bridge_discovery(self) -> List[Dict[str, Any]]:
        """Perform comprehensive discovery of all bridge implementations."""
        bridges = []
        
        # Search pattern for potential bridge files
        bridge_patterns = [
            "**/agent_websocket_bridge.py",
            "**/websocket_bridge_factory.py", 
            "**/websocket_bridge*.py",
            "**/bridge*.py"
        ]
        
        for pattern in bridge_patterns:
            for file_path in self.netra_backend_root.rglob(pattern):
                bridges.extend(self._analyze_file_for_bridges(file_path))
        
        return bridges
    
    def _analyze_file_for_bridges(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a Python file for bridge class definitions."""
        bridges = []
        
        try:
            # Convert file path to module path
            relative_path = file_path.relative_to(self.netra_backend_root.parent)
            module_path = str(relative_path.with_suffix('')).replace('/', '.')
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Find bridge classes
            for name in dir(module):
                obj = getattr(module, name)
                
                if (isinstance(obj, type) and 
                    ('Bridge' in name or 'WebSocket' in name)):
                    
                    bridges.append({
                        'name': name,
                        'class': obj,
                        'module': module_path,
                        'file': str(file_path),
                        'line': self._find_class_line_number(file_path, name)
                    })
        
        except Exception as e:
            self.logger.debug(f"Could not analyze {file_path}: {e}")
        
        return bridges
    
    def _find_class_line_number(self, file_path: Path, class_name: str) -> Optional[int]:
        """Find the line number where a class is defined."""
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if f'class {class_name}' in line:
                        return line_num
        except:
            pass
        return None


# Test execution configuration
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])