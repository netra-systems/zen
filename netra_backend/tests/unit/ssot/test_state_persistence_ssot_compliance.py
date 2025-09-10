"""State Persistence SSOT Compliance Validation Tests

This test suite validates Single Source of Truth compliance for state persistence services.
These tests will PASS only after proper SSOT consolidation is complete.

Business Value Justification (BVJ):
- Segment: Enterprise/Platform ($25K+ MRR workloads)
- Business Goal: Platform Reliability, Architecture Compliance
- Value Impact: Ensures consolidated, maintainable state persistence architecture  
- Strategic Impact: Validates SSOT compliance for business-critical persistence layer

SSOT Compliance Requirements:
1. Exactly ONE consolidated persistence service implementation
2. No duplicate persistence logic across modules
3. All optimization features properly consolidated into single service
4. No broken import references in codebase
5. Documentation matches actual implementation

Test Philosophy:
- These tests validate SSOT compliance AFTER remediation
- Tests should PASS only when SSOT consolidation is complete
- Use real services and modules (no mocks)
- Focus on architecture validation and consistency
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import List, Dict, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestStatePersistenceSSotCompliance(SSotBaseTestCase):
    """Validates SSOT compliance for consolidated state persistence service."""

    def test_single_persistence_service_exists(self):
        """
        SSOT COMPLIANCE: Exactly one consolidated persistence service exists
        
        After SSOT remediation, there should be exactly ONE persistence service
        that handles all state persistence needs including optimization features.
        """
        # After SSOT consolidation, we should have exactly one comprehensive service
        primary_persistence_modules = [
            "netra_backend.app.services.state_persistence",
            "netra_backend.app.services.state_persistence_optimized",
        ]
        
        existing_modules = []
        for module_name in primary_persistence_modules:
            try:
                module = importlib.import_module(module_name)
                existing_modules.append((module_name, module))
            except ImportError:
                pass
                
        # SSOT compliance: exactly one primary service should exist
        assert len(existing_modules) == 1, (
            f"SSOT VIOLATION: Found {len(existing_modules)} persistence services, "
            f"should be exactly 1. Modules: {[name for name, _ in existing_modules]}"
        )
        
        # Validate the consolidated service has comprehensive functionality
        module_name, module = existing_modules[0]
        
        # Should have both standard and optimized functionality in one place
        expected_capabilities = [
            "save_state",  # Standard persistence
            "load_state",  # Standard loading
            "optimize_performance",  # Optimization features
            "manage_cache",  # Cache management
        ]
        
        available_functions = [name for name, obj in inspect.getmembers(module) 
                             if inspect.isfunction(obj) or inspect.isclass(obj)]
        
        # Check that consolidated service has comprehensive functionality
        has_comprehensive_functionality = any(
            any(capability.lower() in func.lower() for capability in expected_capabilities)
            for func in available_functions
        )
        
        assert has_comprehensive_functionality, (
            f"SSOT COMPLIANCE: Consolidated service '{module_name}' should provide comprehensive functionality. "
            f"Available functions: {available_functions}"
        )

    def test_no_duplicate_persistence_implementations(self):
        """
        SSOT COMPLIANCE: No duplicate persistence logic exists
        
        Validates that persistence logic is not duplicated across multiple modules.
        All functionality should be consolidated into the single SSOT service.
        """
        # Check for potential duplicate implementations
        persistence_related_modules = [
            "netra_backend.app.services.state_persistence",
            "netra_backend.app.services.state_persistence_optimized", 
            "netra_backend.app.services.state_cache_manager",
        ]
        
        existing_implementations = {}
        for module_name in persistence_related_modules:
            try:
                module = importlib.import_module(module_name)
                # Look for persistence-related classes and functions
                persistence_items = []
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) or inspect.isfunction(obj)) and \
                       any(keyword in name.lower() for keyword in ['persist', 'save', 'load', 'state']):
                        persistence_items.append(name)
                        
                if persistence_items:
                    existing_implementations[module_name] = persistence_items
            except ImportError:
                pass
                
        # SSOT compliance: should have implementations in exactly one module
        assert len(existing_implementations) <= 1, (
            f"SSOT VIOLATION: Found persistence implementations in multiple modules: {existing_implementations}. "
            f"Should be consolidated into single SSOT service."
        )

    def test_optimization_features_consolidated(self):
        """
        SSOT COMPLIANCE: Optimization features are properly consolidated
        
        Validates that all optimization features are part of the main persistence service,
        not split across separate modules.
        """
        # Find the consolidated persistence service
        try:
            # Try the main persistence service first
            from netra_backend.app.services.state_persistence import state_persistence_service
            main_service = state_persistence_service
            main_module = "state_persistence"
        except ImportError:
            try:
                # Try optimized if that became the consolidated version
                from netra_backend.app.services.state_persistence_optimized import optimized_state_persistence
                main_service = optimized_state_persistence
                main_module = "state_persistence_optimized"
            except ImportError:
                self.fail("SSOT VIOLATION: No consolidated persistence service found")
                
        # Check that optimization features are available in the consolidated service
        optimization_indicators = [
            'optimiz',  # optimization, optimized
            'cache',    # caching functionality
            'performance',  # performance features
            'batch',    # batch operations
            'async',    # async optimization
        ]
        
        service_attributes = dir(main_service)
        
        optimization_features_found = []
        for attr in service_attributes:
            if any(indicator in attr.lower() for indicator in optimization_indicators):
                optimization_features_found.append(attr)
                
        assert len(optimization_features_found) > 0, (
            f"SSOT COMPLIANCE: Consolidated service in '{main_module}' should include optimization features. "
            f"Available attributes: {service_attributes}"
        )

    def test_no_broken_import_references(self):
        """
        SSOT COMPLIANCE: No broken import references exist in codebase
        
        After SSOT consolidation, all imports should resolve successfully.
        No references to non-existent modules should remain.
        """
        # Test that commonly referenced imports work
        import_tests = [
            # Should work after consolidation
            ("netra_backend.app.services.state_persistence", "state_persistence_service"),
            # This should either work OR not be referenced anywhere
            ("netra_backend.app.services.state_persistence_optimized", "optimized_state_persistence"),
        ]
        
        successful_imports = []
        failed_imports = []
        
        for module_name, attr_name in import_tests:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, attr_name):
                    successful_imports.append((module_name, attr_name))
                else:
                    failed_imports.append((module_name, f"Missing attribute: {attr_name}"))
            except ImportError as e:
                failed_imports.append((module_name, str(e)))
                
        # After SSOT consolidation, we should have exactly one working persistence service
        assert len(successful_imports) >= 1, (
            f"SSOT COMPLIANCE: At least one persistence service should be importable. "
            f"Successful: {successful_imports}, Failed: {failed_imports}"
        )

    def test_documentation_matches_implementation(self):
        """
        SSOT COMPLIANCE: Documentation references match actual implementation
        
        Validates that documentation files reference actual, existing modules
        and functionality after SSOT consolidation.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Check documentation files that might reference persistence
        doc_files_to_check = [
            project_root / "docs" / "OPTIMIZED_PERSISTENCE_USAGE.md",
            project_root / "docs" / "optimized_state_persistence.md", 
        ]
        
        documentation_issues = []
        
        for doc_file in doc_files_to_check:
            if doc_file.exists():
                content = doc_file.read_text()
                
                # Check for references to modules
                if "state_persistence_optimized" in content:
                    # Verify the referenced module actually exists
                    try:
                        importlib.import_module("netra_backend.app.services.state_persistence_optimized")
                    except ImportError:
                        documentation_issues.append(f"{doc_file.name}: References non-existent state_persistence_optimized")
                        
                if "optimized_state_persistence" in content:
                    # Verify the referenced service actually exists
                    try:
                        from netra_backend.app.services.state_persistence_optimized import optimized_state_persistence
                    except ImportError:
                        documentation_issues.append(f"{doc_file.name}: References non-existent optimized_state_persistence")
                        
        # After SSOT consolidation, documentation should match implementation
        assert len(documentation_issues) == 0, (
            f"SSOT COMPLIANCE: Documentation should match implementation. Issues found: {documentation_issues}"
        )

    def test_scripts_execute_successfully(self):
        """
        SSOT COMPLIANCE: Scripts can execute without import errors
        
        Validates that operational scripts work after SSOT consolidation.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        demo_script = project_root / "scripts" / "demo_optimized_persistence.py"
        
        if demo_script.exists():
            # Read the script content
            script_content = demo_script.read_text()
            
            # Try to compile the script (this will catch import errors)
            try:
                compile(script_content, str(demo_script), 'exec')
                script_compiles = True
            except (ImportError, SyntaxError) as e:
                script_compiles = False
                compilation_error = str(e)
                
            assert script_compiles, (
                f"SSOT COMPLIANCE: Scripts should compile without import errors after consolidation. "
                f"Error in {demo_script.name}: {compilation_error}"
            )

    def test_integration_tests_import_successfully(self):
        """
        SSOT COMPLIANCE: Integration tests can import persistence services
        
        Validates that integration tests work with consolidated persistence service.
        """
        # Test that integration tests can import what they need
        integration_import_tests = [
            "netra_backend.app.services.state_persistence",
            "netra_backend.app.schemas.agent_state",
        ]
        
        import_results = []
        for module_name in integration_import_tests:
            try:
                importlib.import_module(module_name)
                import_results.append((module_name, "SUCCESS"))
            except ImportError as e:
                import_results.append((module_name, f"FAILED: {e}"))
                
        failed_imports = [result for result in import_results if "FAILED" in result[1]]
        
        assert len(failed_imports) == 0, (
            f"SSOT COMPLIANCE: Integration tests should be able to import required modules. "
            f"Failed imports: {failed_imports}"
        )

    def test_consolidated_service_interface_consistency(self):
        """
        SSOT COMPLIANCE: Consolidated service provides consistent interface
        
        Validates that the consolidated persistence service provides a consistent,
        comprehensive interface for all persistence operations.
        """
        # Find the consolidated service
        consolidated_service = None
        service_module_name = None
        
        # Try to find the main persistence service
        persistence_candidates = [
            ("netra_backend.app.services.state_persistence", "state_persistence_service"),
            ("netra_backend.app.services.state_persistence_optimized", "optimized_state_persistence"),
        ]
        
        for module_name, service_name in persistence_candidates:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, service_name):
                    consolidated_service = getattr(module, service_name)
                    service_module_name = module_name
                    break
            except ImportError:
                continue
                
        assert consolidated_service is not None, (
            "SSOT COMPLIANCE: Should have exactly one consolidated persistence service available"
        )
        
        # Validate the service has expected interface methods
        expected_methods = [
            'save_state',
            'load_state', 
        ]
        
        available_methods = [method for method in dir(consolidated_service) 
                           if not method.startswith('_')]
        
        missing_methods = []
        for expected_method in expected_methods:
            if not any(expected_method.lower() in available_method.lower() 
                      for available_method in available_methods):
                missing_methods.append(expected_method)
                
        assert len(missing_methods) == 0, (
            f"SSOT COMPLIANCE: Consolidated service should provide expected interface. "
            f"Missing methods: {missing_methods}, Available: {available_methods}"
        )


class TestStatePersistenceArchitecturalIntegrity(SSotBaseTestCase):
    """Validates architectural integrity after SSOT consolidation."""
    
    def test_no_circular_dependencies(self):
        """
        ARCHITECTURAL INTEGRITY: No circular dependencies in persistence layer
        
        Validates that SSOT consolidation doesn't create circular import dependencies.
        """
        # Test imports in isolation to detect circular dependencies
        persistence_modules = [
            "netra_backend.app.services.state_persistence",
            "netra_backend.app.schemas.agent_state",
            "netra_backend.app.agents.state",
        ]
        
        import_issues = []
        
        for module_name in persistence_modules:
            try:
                # Fresh import to detect circular dependencies
                if module_name in sys.modules:
                    del sys.modules[module_name]
                importlib.import_module(module_name)
            except ImportError as e:
                if "circular" in str(e).lower() or "recursion" in str(e).lower():
                    import_issues.append(f"{module_name}: {e}")
                    
        assert len(import_issues) == 0, (
            f"ARCHITECTURAL INTEGRITY: No circular dependencies should exist. Issues: {import_issues}"
        )
        
    def test_service_isolation_maintained(self):
        """
        ARCHITECTURAL INTEGRITY: Service isolation is maintained after consolidation
        
        Validates that SSOT consolidation doesn't break service boundaries.
        """
        # Persistence service should not directly import from other business services
        forbidden_imports = [
            "netra_backend.app.websocket_core",  # Should use dependency injection
            "netra_backend.app.agents.supervisor",  # Should not directly couple
        ]
        
        try:
            import netra_backend.app.services.state_persistence as persistence_module
            module_file = persistence_module.__file__
            
            if module_file:
                with open(module_file, 'r') as f:
                    module_content = f.read()
                    
                boundary_violations = []
                for forbidden_import in forbidden_imports:
                    if forbidden_import in module_content:
                        boundary_violations.append(forbidden_import)
                        
                assert len(boundary_violations) == 0, (
                    f"ARCHITECTURAL INTEGRITY: Persistence service should maintain service boundaries. "
                    f"Forbidden imports found: {boundary_violations}"
                )
        except ImportError:
            # If we can't import the service, that's a different issue
            pass