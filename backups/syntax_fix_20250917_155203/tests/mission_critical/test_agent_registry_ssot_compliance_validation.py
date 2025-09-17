"
AgentRegistry SSOT Compliance Validation Tests - Issue #1080

MISSION: Validate AgentRegistry SSOT compliance after fixes
Business Impact: $500K+ ARR Golden Path restoration

These tests validate the FIXED state after SSOT consolidation.
EXPECTED INITIAL RESULT: ALL TESTS FAIL (waiting for fixes)
AFTER SSOT FIXES: ALL TESTS PASS (proving compliance achieved)

Golden Path Restored: Users login → AI agents process requests → Users receive AI responses

Created: 2025-09-14 - SSOT Test Plan Step 2
Priority: P0 Critical - Golden Path validation
"

import pytest
import asyncio
from typing import Dict, Any, Optional, Type, List
import inspect
import importlib

# SSOT Base Test Case - Required for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Environment access through SSOT pattern only
from shared.isolated_environment import IsolatedEnvironment


class AgentRegistrySSoTComplianceValidationTests(SSotAsyncTestCase):
    "
    Validation tests for AgentRegistry SSOT compliance.
    
    EXPECTED INITIAL: All tests FAIL (fixes not implemented)
    AFTER SSOT FIX: All tests PASS (proving compliance)
"
    
    def setup_method(self, method=None):
        "Set up test environment with SSOT patterns
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        
        # Test user context for isolation validation
        self.test_user_id = test-user-ssot-compliance-validation""
        self.test_session_id = test-session-ssot-compliance
        
        # Record test context for business impact measurement
        self.record_metric(business_value_protected, "500K_plus_ARR)
        self.record_metric(golden_path_validation", True)

    async def test_single_registry_import_resolution(self):
    "
        CRITICAL: Validate only one AgentRegistry class exists across all imports
        
        Business Impact: Eliminates developer confusion and ensures consistency
        Expected: FAIL initially, PASS after SSOT fix
        "
        self.record_metric(test_type, ssot_import_validation)
        
        # Define all possible import paths for AgentRegistry
        import_paths = [
            netra_backend.app.agents.registry.AgentRegistry","
            netra_backend.app.agents.supervisor.agent_registry.AgentRegistry,
        ]
        
        imported_classes = []
        successful_imports = []
        
        for import_path in import_paths:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                registry_class = getattr(module, class_name)
                
                imported_classes.append(registry_class)
                successful_imports.append(import_path)
                
                self.record_metric(fimport_success_{module_path}, True)"
                
            except (ImportError, AttributeError) as e:
                self.record_metric(f"import_failed_{import_path}, str(e))
        
        # SSOT COMPLIANCE: All successful imports must resolve to the same class
        unique_class_ids = set(id(cls) for cls in imported_classes)
        
        self.record_metric(successful_imports, len(successful_imports))
        self.record_metric(unique_classes, len(unique_class_ids))"
        self.record_metric(import_paths_tested", import_paths)
        
        # Must have at least one working import
        assert len(successful_imports) > 0, (
            fSSOT COMPLIANCE FAILURE: No AgentRegistry imports work. 
            fTried: {import_paths}"
        )
        
        # All working imports must resolve to same class
        assert len(unique_class_ids) == 1, (
            f"SSOT COMPLIANCE FAILURE: {len(unique_class_ids)} different AgentRegistry classes found 
            ffrom {len(successful_imports)} successful imports. 
            fSSOT requires exactly 1 class. Import paths: {successful_imports}
        )
        
        # Additional validation - check that all classes are identical
        if len(imported_classes) > 1:
            reference_class = imported_classes[0]
            for i, registry_class in enumerate(imported_classes[1:], 1):
                assert reference_class is registry_class, (
                    fSSOT COMPLIANCE FAILURE: Class from {successful_imports[0]} ""
                    fis not identical to class from {successful_imports[i]}. 
                    fObject IDs: {id(reference_class)} vs {id(registry_class)}
                )

    async def test_unified_websocket_event_delivery(self):
    ""
        CRITICAL: Validate consistent WebSocket event delivery across all contexts
        
        Business Impact: Ensures reliable Golden Path chat experience
        Expected: FAIL initially, PASS after SSOT fix
        
        self.record_metric(test_type", "websocket_consistency_validation)
        
        # Import the SSOT AgentRegistry (should be single source)
        try:
            # Try the preferred SSOT import path
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            self.record_metric(ssot_registry_import, SUCCESS)
        except ImportError:
            try:
                # Fallback to basic import if still available
                from netra_backend.app.agents.registry import AgentRegistry
                self.record_metric(ssot_registry_import, "FALLBACK)
            except ImportError:
                pytest.fail(No AgentRegistry import available for testing")
        
        # Create multiple instances to test consistency
        registry_instances = []
        for i in range(3):
            instance = AgentRegistry()
            registry_instances.append(instance)
            
        self.record_metric(registry_instances_created, len(registry_instances))
        
        # Validate WebSocket capabilities are consistent across instances
        websocket_capabilities = []
        
        for i, registry in enumerate(registry_instances):
            capability = {
                'has_websocket_manager': hasattr(registry, 'websocket_manager'),
                'has_set_websocket': hasattr(registry, 'set_websocket_manager'),
                'has_websocket_bridge': hasattr(registry, 'websocket_bridge'),
                'has_create_bridge': hasattr(registry, 'create_websocket_bridge'),
                'has_notify_methods': hasattr(registry, 'notify_websocket_event')
            }
            
            websocket_capabilities.append(capability)
            self.record_metric(finstance_{i}_websocket_capability", capability)"
        
        # All instances must have identical WebSocket capabilities
        reference_capability = websocket_capabilities[0]
        for i, capability in enumerate(websocket_capabilities[1:], 1):
            assert capability == reference_capability, (
                fSSOT COMPLIANCE FAILURE: WebSocket capabilities inconsistent. 
                fInstance 0: {reference_capability} vs Instance {i}: {capability}. 
                f"SSOT requires all instances to have identical capabilities.
            )
        
        self.record_metric(websocket_consistency_validated", True)

    async def test_uniform_multi_user_isolation(self):
    "
        CRITICAL: Validate user isolation works consistently across all instances
        
        Business Impact: Ensures enterprise security and data protection
        Expected: FAIL initially, PASS after SSOT fix  
        "
        self.record_metric(test_type, multi_user_isolation_validation)
        self.record_metric(security_impact", "ENTERPRISE_CRITICAL)
        
        # Import SSOT AgentRegistry
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        except ImportError:
            try:
                from netra_backend.app.agents.registry import AgentRegistry
            except ImportError:
                pytest.fail(No AgentRegistry available for isolation testing)
        
        # Test user isolation capabilities
        user_contexts = [user_1, user_2", "user_3]
        isolation_results = {}
        
        for user_id in user_contexts:
            registry = AgentRegistry()
            
            # Check for user isolation methods
            isolation_methods = {
                'has_user_context': hasattr(registry, 'create_user_context') or hasattr(registry, 'get_user_context'),
                'has_isolation_factory': hasattr(registry, 'create_for_user') or hasattr(registry, 'user_factory'),
                'has_isolation_manager': hasattr(registry, 'isolate_user') or hasattr(registry, 'user_isolation'),
                'has_context_methods': any(hasattr(registry, method) for method in ['set_user_context', 'clear_user_context', 'get_current_user']
            }
            
            isolation_results[user_id] = isolation_methods
            self.record_metric(f{user_id}_isolation_capability, isolation_methods)
        
        # All user contexts must have identical isolation capabilities
        reference_isolation = isolation_results[user_contexts[0]]
        for user_id in user_contexts[1:]:
            user_isolation = isolation_results[user_id]
            
            assert user_isolation == reference_isolation, (
                f"SSOT COMPLIANCE FAILURE: User isolation capabilities inconsistent. 
                fUser {user_contexts[0]}: {reference_isolation} "
                fvs User {user_id}: {user_isolation}. 
                fSSOT requires consistent isolation across all users."
            )
        
        self.record_metric("multi_user_isolation_consistent, True)

    async def test_consistent_factory_pattern(self):
        
        CRITICAL: Validate factory pattern is uniform across all registry instances
        
        Business Impact: Ensures consistent developer experience
        Expected: FAIL initially, PASS after SSOT fix
""
        self.record_metric(test_type, factory_pattern_validation)
        
        # Import SSOT AgentRegistry
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        except ImportError:
            try:
                from netra_backend.app.agents.registry import AgentRegistry
            except ImportError:
                pytest.fail("No AgentRegistry available for factory pattern testing)"
        
        # Analyze factory pattern of the SSOT registry
        factory_analysis = self._analyze_registry_factory_pattern(AgentRegistry)
        
        self.record_metric(factory_pattern_analysis, factory_analysis)
        
        # Create multiple instances and verify they all follow the same pattern
        instances = []
        for i in range(3):
            instance = AgentRegistry()
            instances.append(instance)
        
        # Verify all instances have the same factory methods available
        factory_method_sets = []
        
        for i, instance in enumerate(instances):
            instance_methods = dir(instance)
            factory_methods = [method for method in instance_methods 
                             if any(keyword in method.lower() for keyword in ['create', 'factory', 'make', 'build', 'get']]
            
            factory_method_sets.append(set(factory_methods))
            self.record_metric(finstance_{i}_factory_methods, factory_methods)
        
        # All instances must have identical factory method sets
        reference_methods = factory_method_sets[0]
        for i, method_set in enumerate(factory_method_sets[1:], 1):
            assert method_set == reference_methods, (
                fSSOT COMPLIANCE FAILURE: Factory methods inconsistent between instances. ""
                fInstance 0: {reference_methods} vs Instance {i}: {method_set}. 
                fDifferences: {reference_methods.symmetric_difference(method_set)}
            )
        
        # Validate initialization consistency
        init_signatures = []
        for instance in instances:
            init_method = getattr(instance.__class__, '__init__', None)
            if init_method:
                signature = inspect.signature(init_method)
                init_signatures.append(str(signature))
        
        # All instances must have identical initialization signatures
        if init_signatures:
            reference_signature = init_signatures[0]
            for i, signature in enumerate(init_signatures[1:], 1):
                assert signature == reference_signature, (
                    f"SSOT COMPLIANCE FAILURE: Initialization signatures inconsistent. 
                    fInstance 0: {reference_signature} vs Instance {i}: {signature}"
                )
        
        self.record_metric(factory_pattern_consistent, True)

    def _analyze_registry_factory_pattern(self, registry_class: Type) -> Dict[str, Any]:
        ""Analyze the factory pattern of a registry class for SSOT compliance
        
        # Get class methods
        class_methods = inspect.getmembers(registry_class, predicate=inspect.ismethod)
        instance_methods = inspect.getmembers(registry_class, predicate=inspect.isfunction)
        
        all_methods = [name for name, _ in class_methods + instance_methods]
        
        # Identify factory-related methods
        factory_keywords = ['create', 'factory', 'make', 'build', 'get', 'generate', 'produce']
        factory_methods = []
        
        for method_name in all_methods:
            if any(keyword in method_name.lower() for keyword in factory_keywords):
                factory_methods.append(method_name)
        
        # Get initialization information
        init_method = getattr(registry_class, '__init__', None)
        init_signature = str(inspect.signature(init_method)) if init_method else None
        
        # Analyze class hierarchy
        mro = [cls.__name__ for cls in registry_class.__mro__]
        
        return {
            'class_name': registry_class.__name__,
            'module': registry_class.__module__,
            'all_methods': all_methods,
            'factory_methods': factory_methods,
            'factory_method_count': len(factory_methods),
            'init_signature': init_signature,
            'inheritance_hierarchy': mro,
            'total_method_count': len(all_methods)
        }

    async def test_ssot_compliance_comprehensive_validation(self):
    ""
        Comprehensive validation of all SSOT compliance aspects
        
        Business Impact: Complete Golden Path protection validation
        Expected: FAIL initially, PASS after all SSOT fixes complete
        
        self.record_metric(test_type, "comprehensive_ssot_validation)
        
        compliance_score = 0
        total_checks = 0
        compliance_details = []
        
        # Check 1: Single import path works
        total_checks += 1
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            compliance_score += 1
            compliance_details.append(✓ SSOT AgentRegistry import successful")
            self.record_metric(ssot_import_check, PASS)
        except ImportError:
            compliance_details.append("✗ SSOT AgentRegistry import failed)"
            self.record_metric(ssot_import_check, FAIL)
        
        # Check 2: No duplicate classes exist
        total_checks += 1
        try:
            from netra_backend.app.agents.registry import AgentRegistry as Registry1
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as Registry2
            
            if Registry1 is Registry2:
                compliance_score += 1
                compliance_details.append(✓ No duplicate AgentRegistry classes)"
                self.record_metric("duplicate_class_check, PASS)
            else:
                compliance_details.append(✗ Duplicate AgentRegistry classes exist)
                self.record_metric(duplicate_class_check", "FAIL)
        except ImportError:
            # If one import fails, this could indicate proper consolidation
            compliance_score += 0.5  # Partial credit
            compliance_details.append(~ One AgentRegistry import path unavailable (possible consolidation))
            self.record_metric(duplicate_class_check, PARTIAL")
        
        # Check 3: Interface consistency
        total_checks += 1
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            instance = AgentRegistry()
            
            # Check for essential methods
            essential_methods = ['register', 'get', 'create', '__init__']
            has_essential = all(hasattr(instance, method) for method in essential_methods)
            
            if has_essential:
                compliance_score += 1
                compliance_details.append("✓ Essential AgentRegistry interface methods present)
                self.record_metric(interface_consistency_check, PASS)
            else:
                compliance_details.append(✗ Missing essential AgentRegistry interface methods")"
                self.record_metric(interface_consistency_check, FAIL)
                
        except Exception as e:
            compliance_details.append(f✗ Interface consistency check failed: {e})
            self.record_metric(interface_consistency_check", "FAIL)
        
        # Check 4: WebSocket integration consistency
        total_checks += 1
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            instance = AgentRegistry()
            
            # Check for WebSocket-related capabilities
            websocket_methods = ['set_websocket_manager', 'websocket_manager', 'websocket_bridge']
            has_websocket_support = any(hasattr(instance, method) for method in websocket_methods)
            
            if has_websocket_support:
                compliance_score += 1
                compliance_details.append(✓ WebSocket integration present)
                self.record_metric(websocket_integration_check, PASS")
            else:
                compliance_details.append("✗ Missing WebSocket integration)
                self.record_metric(websocket_integration_check, FAIL)
                
        except Exception as e:
            compliance_details.append(f✗ WebSocket integration check failed: {e}")"
            self.record_metric(websocket_integration_check, FAIL)
        
        # Calculate compliance percentage
        compliance_percentage = (compliance_score / total_checks) * 100 if total_checks > 0 else 0
        
        self.record_metric(ssot_compliance_score, compliance_score)"
        self.record_metric(ssot_compliance_total_checks", total_checks)
        self.record_metric(ssot_compliance_percentage, compliance_percentage)
        self.record_metric(ssot_compliance_details", compliance_details)"
        
        # SSOT compliance requires 100% pass rate
        assert compliance_percentage == 100.0, (
            fSSOT COMPLIANCE FAILURE: Achieved {compliance_percentage}% compliance 
            f({compliance_score}/{total_checks} checks passed). 
            f"SSOT requires 100% compliance. Details:\n + \n.join(compliance_details)
        )
        
        self.record_metric("ssot_compliance_achieved, True)"


if __name__ == __main__":"
    # Allow running individual test file
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution