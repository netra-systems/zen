"""
TEST SUITE 3: Registry Configuration SSOT Consistency (Issue #1034)

Business Value Protection: $500K+ ARR Golden Path configuration integrity
Test Type: Unit (No infrastructure needed)

PURPOSE: Validate unified configuration after consolidation
EXPECTED: FAILING initially (multiple paths), PASSING after consolidation

This test suite validates that registry configuration follows SSOT principles
after consolidation, ensuring consistent behavior across all system components
and eliminating configuration drift that could impact business functionality.

Critical Configuration Areas:
- Registry import paths SSOT compliance
- Registry configuration has no conflicts
- Unified configuration schema validation
- Import resolution consistency
"""

import pytest
import sys
import importlib
import inspect
from typing import Dict, Any, List, Set, Optional, Tuple
from unittest.mock import Mock, patch
from pathlib import Path

# SSOT TEST INFRASTRUCTURE - Use established testing patterns
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.isolated_environment import IsolatedEnvironment


class TestRegistryConfigurationSSoT(SSotBaseTestCase):
    """Test registry configuration SSOT compliance."""
    
    def setUp(self):
        """Set up configuration test environment with SSOT compliance."""
        super().setUp()
        
        # Create isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        
        # Track imports for cleanup
        self.imported_modules: Set[str] = set()
        
        # Configuration validation data
        self.registry_import_paths = [
            "netra_backend.app.agents.registry",
            "netra_backend.app.agents.supervisor.agent_registry",
        ]
        
        # Expected SSOT configuration after consolidation
        self.expected_ssot_config = {
            "single_registry_class": True,
            "consistent_interface": True,
            "no_import_conflicts": True,
            "unified_configuration": True,
            "backward_compatibility": True
        }
    
    def tearDown(self):
        """Clean up imported modules."""
        # Remove imported modules to prevent cross-test contamination
        for module_name in self.imported_modules:
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        super().tearDown()
    
    def _safe_import(self, module_name: str) -> Tuple[Any, Optional[Exception]]:
        """Safely import module and return module or exception."""
        try:
            # Remove from cache if present to force fresh import
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            module = importlib.import_module(module_name)
            self.imported_modules.add(module_name)
            return module, None
        except Exception as e:
            return None, e
    
    def test_registry_import_path_ssot_compliance(self):
        """
        Test registry import paths SSOT compliance.
        
        EXPECTED INITIAL BEHAVIOR: Should detect multiple import paths (SSOT violation)
        EXPECTED POST-CONSOLIDATION: Should have single authoritative import path
        """
        import_results = {}
        import_conflicts = []
        
        # Test all potential registry import paths
        for path in self.registry_import_paths:
            module, error = self._safe_import(path)
            import_results[path] = {
                "importable": error is None,
                "module": module,
                "error": str(error) if error else None
            }
            
            if module is not None:
                # Check if module has AgentRegistry class
                if hasattr(module, 'AgentRegistry'):
                    registry_class = getattr(module, 'AgentRegistry')
                    import_results[path]["has_registry_class"] = True
                    import_results[path]["registry_class"] = registry_class
                    import_results[path]["class_id"] = id(registry_class)
                    import_results[path]["module_file"] = getattr(module, '__file__', 'unknown')
                else:
                    import_results[path]["has_registry_class"] = False
        
        print("Registry Import Analysis:")
        for path, result in import_results.items():
            print(f"  {path}:")
            print(f"    Importable: {result['importable']}")
            print(f"    Has AgentRegistry: {result.get('has_registry_class', False)}")
            if result.get('module_file'):
                print(f"    File: {result['module_file']}")
            if result.get('error'):
                print(f"    Error: {result['error']}")
        
        # Check for SSOT violations (multiple AgentRegistry classes)
        registry_classes = []
        for path, result in import_results.items():
            if result.get('has_registry_class'):
                registry_classes.append({
                    "path": path,
                    "class": result["registry_class"],
                    "class_id": result["class_id"],
                    "module_file": result["module_file"]
                })
        
        # INITIAL EXPECTATION: Multiple registry classes indicate SSOT violation
        if len(registry_classes) > 1:
            # Check if they are actually different classes
            unique_class_ids = set(rc["class_id"] for rc in registry_classes)
            
            if len(unique_class_ids) > 1:
                conflict_details = [
                    f"{rc['path']} (ID: {rc['class_id']}, File: {rc['module_file']})"
                    for rc in registry_classes
                ]
                
                self.fail(
                    f"SSOT VIOLATION DETECTED: Multiple distinct AgentRegistry classes found:\n" +
                    "\n".join(f"  - {detail}" for detail in conflict_details) +
                    f"\n\nThis test is correctly detecting the consolidation requirement. "
                    f"After consolidation, only one AgentRegistry class should exist."
                )
        
        # POST-CONSOLIDATION: Should have exactly one registry class
        self.assertGreaterEqual(
            len(registry_classes), 1,
            "At least one AgentRegistry class should be importable after consolidation"
        )
        
        # Validate that there's a clear SSOT path
        ssot_paths = [path for path, result in import_results.items() 
                     if result['importable'] and result.get('has_registry_class')]
        
        self.assertGreater(
            len(ssot_paths), 0,
            "No valid AgentRegistry import path found - consolidation may have broken imports"
        )
    
    def test_registry_interface_consistency_validation(self):
        """
        Test registry interface consistency after consolidation.
        
        EXPECTED: All available registry classes should have consistent interfaces
        """
        registry_classes = []
        
        # Import available registry classes
        for path in self.registry_import_paths:
            module, error = self._safe_import(path)
            if module and hasattr(module, 'AgentRegistry'):
                registry_class = getattr(module, 'AgentRegistry')
                registry_classes.append({
                    "path": path,
                    "class": registry_class,
                    "name": f"{module.__name__}.AgentRegistry"
                })
        
        if not registry_classes:
            self.skipTest("No AgentRegistry classes available for interface testing")
        
        # Define expected interface methods for business functionality
        expected_methods = {
            # Core registry functionality
            "register": "method",
            "get": "method", 
            "has": "method",
            "list_keys": "method",
            
            # User isolation features (advanced registry)
            "get_user_session": "method",
            "create_agent_for_user": "method",
            "cleanup_user_session": "method",
            
            # WebSocket integration ($500K+ ARR critical)
            "set_websocket_manager": "method",
            "diagnose_websocket_wiring": "method",
            
            # Health and monitoring
            "get_registry_health": "method",
            "monitor_all_users": "method",
        }
        
        interface_analysis = {}
        
        for registry_info in registry_classes:
            registry_class = registry_info["class"]
            class_name = registry_info["name"]
            
            interface_analysis[class_name] = {}
            
            for method_name, expected_type in expected_methods.items():
                has_method = hasattr(registry_class, method_name)
                interface_analysis[class_name][method_name] = {
                    "present": has_method,
                    "callable": callable(getattr(registry_class, method_name, None)) if has_method else False
                }
                
                if has_method:
                    method_obj = getattr(registry_class, method_name)
                    # Check method signature for advanced analysis
                    try:
                        sig = inspect.signature(method_obj)
                        interface_analysis[class_name][method_name]["signature"] = str(sig)
                        interface_analysis[class_name][method_name]["param_count"] = len(sig.parameters)
                    except (ValueError, TypeError):
                        # Some methods might not have inspectable signatures
                        pass
        
        print("Registry Interface Analysis:")
        for class_name, methods in interface_analysis.items():
            print(f"  {class_name}:")
            for method_name, info in methods.items():
                status = "✓" if info["present"] and info["callable"] else "✗"
                print(f"    {status} {method_name}: present={info['present']}, callable={info['callable']}")
        
        # Validate critical methods are present in all registry classes
        critical_methods = ["register", "get", "has", "set_websocket_manager"]
        
        for registry_info in registry_classes:
            registry_class = registry_info["class"]
            class_name = registry_info["name"]
            
            for method_name in critical_methods:
                method_present = method_name in interface_analysis[class_name]
                if method_present:
                    method_info = interface_analysis[class_name][method_name]
                    self.assertTrue(
                        method_info["present"] and method_info["callable"],
                        f"Critical method '{method_name}' not properly implemented in {class_name}"
                    )
        
        # If multiple classes exist, validate they have compatible interfaces
        if len(registry_classes) > 1:
            print("\nInterface Compatibility Check:")
            
            base_interface = interface_analysis[registry_classes[0]["name"]]
            for i in range(1, len(registry_classes)):
                compare_interface = interface_analysis[registry_classes[i]["name"]]
                compare_name = registry_classes[i]["name"]
                
                # Check for missing critical methods
                missing_methods = []
                for method_name in critical_methods:
                    if method_name in base_interface and base_interface[method_name]["present"]:
                        if method_name not in compare_interface or not compare_interface[method_name]["present"]:
                            missing_methods.append(method_name)
                
                if missing_methods:
                    print(f"  WARNING: {compare_name} missing critical methods: {missing_methods}")
    
    def test_configuration_schema_validation(self):
        """
        Test unified configuration schema after consolidation.
        
        EXPECTED: Registry configuration should follow unified schema
        """
        # Import available registry for configuration testing
        registry_module = None
        registry_class = None
        
        for path in self.registry_import_paths:
            module, error = self._safe_import(path)
            if module and hasattr(module, 'AgentRegistry'):
                registry_module = module
                registry_class = getattr(module, 'AgentRegistry')
                break
        
        if not registry_class:
            self.skipTest("No AgentRegistry class available for configuration testing")
        
        # Test registry configuration schema
        try:
            # Create mock LLM manager for registry initialization
            mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
            
            # Test registry instantiation with different configurations
            test_configs = [
                {"llm_manager": mock_llm_manager},
                {"llm_manager": mock_llm_manager, "tool_dispatcher_factory": None},
                {"llm_manager": None},  # Backward compatibility test
            ]
            
            config_results = {}
            
            for i, config in enumerate(test_configs):
                config_name = f"config_{i}"
                try:
                    registry_instance = registry_class(**config)
                    
                    config_results[config_name] = {
                        "instantiable": True,
                        "error": None,
                        "has_llm_manager": hasattr(registry_instance, 'llm_manager'),
                        "has_websocket_manager": hasattr(registry_instance, 'websocket_manager'),
                        "has_user_sessions": hasattr(registry_instance, '_user_sessions'),
                    }
                    
                    # Test basic functionality
                    if hasattr(registry_instance, 'get_registry_health'):
                        try:
                            health = registry_instance.get_registry_health()
                            config_results[config_name]["health_check"] = isinstance(health, dict)
                        except Exception as e:
                            config_results[config_name]["health_check"] = f"Error: {e}"
                    
                    # Cleanup if possible
                    if hasattr(registry_instance, 'cleanup'):
                        try:
                            if inspect.iscoroutinefunction(registry_instance.cleanup):
                                # Can't await in sync test, just mark as available
                                config_results[config_name]["has_async_cleanup"] = True
                            else:
                                registry_instance.cleanup()
                        except Exception:
                            pass
                    
                except Exception as e:
                    config_results[config_name] = {
                        "instantiable": False,
                        "error": str(e)
                    }
            
            print("Configuration Schema Validation:")
            for config_name, result in config_results.items():
                print(f"  {config_name}: instantiable={result['instantiable']}")
                if result.get('error'):
                    print(f"    Error: {result['error']}")
                for key, value in result.items():
                    if key not in ['instantiable', 'error']:
                        print(f"    {key}: {value}")
            
            # Validate at least one configuration works
            successful_configs = [name for name, result in config_results.items() 
                                if result['instantiable']]
            
            self.assertGreater(
                len(successful_configs), 0,
                f"No configuration successfully instantiated registry. Errors: " +
                f"{[r['error'] for r in config_results.values() if not r['instantiable']]}"
            )
            
            # Validate backward compatibility (None llm_manager should work)
            if 'config_2' in config_results:
                if config_results['config_2']['instantiable']:
                    print("  ✓ Backward compatibility: Registry works with None llm_manager")
                else:
                    print(f"  ✗ Backward compatibility issue: {config_results['config_2']['error']}")
        
        except Exception as e:
            self.fail(f"Configuration schema validation failed: {e}")
    
    def test_import_resolution_conflicts(self):
        """
        Test import resolution conflicts between registry implementations.
        
        EXPECTED INITIAL: Should detect import resolution conflicts
        EXPECTED POST-CONSOLIDATION: No conflicts
        """
        import_conflicts = []
        symbol_conflicts = []
        
        # Test different import patterns that might cause conflicts
        import_patterns = [
            # Direct class imports
            ("from netra_backend.app.agents.registry import AgentRegistry", "registry.AgentRegistry"),
            ("from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry", "supervisor.AgentRegistry"),
            
            # Module imports
            ("import netra_backend.app.agents.registry as registry_module", "registry_module.AgentRegistry"),
            ("import netra_backend.app.agents.supervisor.agent_registry as supervisor_module", "supervisor_module.AgentRegistry"),
        ]
        
        imported_classes = {}
        
        for import_statement, accessor in import_patterns:
            try:
                # Execute import in isolated namespace
                namespace = {}
                exec(import_statement, globals(), namespace)
                
                # Try to access AgentRegistry through the accessor pattern
                class_path_parts = accessor.split('.')
                registry_class = namespace
                for part in class_path_parts:
                    if hasattr(registry_class, part):
                        registry_class = getattr(registry_class, part)
                    else:
                        registry_class = None
                        break
                
                if registry_class and inspect.isclass(registry_class):
                    class_info = {
                        "import_statement": import_statement,
                        "accessor": accessor,
                        "class": registry_class,
                        "class_id": id(registry_class),
                        "module_name": registry_class.__module__,
                        "class_name": registry_class.__name__
                    }
                    
                    imported_classes[accessor] = class_info
                else:
                    import_conflicts.append(f"Import pattern failed: {import_statement} -> {accessor}")
            
            except Exception as e:
                import_conflicts.append(f"Import error for '{import_statement}': {e}")
        
        print("Import Pattern Analysis:")
        for accessor, info in imported_classes.items():
            print(f"  {accessor}:")
            print(f"    Import: {info['import_statement']}")
            print(f"    Module: {info['module_name']}")
            print(f"    Class ID: {info['class_id']}")
        
        if import_conflicts:
            print("Import Conflicts Detected:")
            for conflict in import_conflicts:
                print(f"  - {conflict}")
        
        # Check for symbol conflicts (same name, different classes)
        if len(imported_classes) > 1:
            class_ids = set(info['class_id'] for info in imported_classes.values())
            
            if len(class_ids) > 1:
                # Multiple different AgentRegistry classes found
                conflict_details = []
                for accessor, info in imported_classes.items():
                    conflict_details.append(
                        f"{accessor} -> {info['module_name']}.{info['class_name']} (ID: {info['class_id']})"
                    )
                
                self.fail(
                    f"SSOT VIOLATION: Multiple different AgentRegistry classes accessible:\n" +
                    "\n".join(f"  - {detail}" for detail in conflict_details) +
                    f"\n\nThis indicates import resolution conflicts that should be resolved " +
                    f"by registry consolidation."
                )
        
        # Validate that at least one import pattern works
        self.assertGreater(
            len(imported_classes), 0,
            f"No AgentRegistry import patterns work. Import conflicts: {import_conflicts}"
        )
    
    def test_ssot_consolidation_completeness(self):
        """
        Test SSOT consolidation completeness.
        
        EXPECTED: After consolidation, should have single source of truth
        """
        # Check for remnants of old implementations
        potential_conflict_files = [
            "netra_backend/app/agents/registry.py",
            "netra_backend/app/agents/supervisor/agent_registry.py",
        ]
        
        file_analysis = {}
        
        # Analyze what's actually available vs what should be available
        for path in self.registry_import_paths:
            module, error = self._safe_import(path)
            
            file_analysis[path] = {
                "importable": error is None,
                "error": str(error) if error else None,
                "deprecated": False,
                "compatibility_layer": False,
                "ssot_compliant": False
            }
            
            if module:
                # Check for deprecation markers
                module_doc = getattr(module, '__doc__', '') or ''
                if 'deprecated' in module_doc.lower() or 'deprecation' in module_doc.lower():
                    file_analysis[path]["deprecated"] = True
                
                # Check for compatibility layer markers
                if 'compatibility' in module_doc.lower() or 'wrapper' in module_doc.lower():
                    file_analysis[path]["compatibility_layer"] = True
                
                # Check for SSOT compliance markers
                if 'ssot' in module_doc.lower() or 'single source' in module_doc.lower():
                    file_analysis[path]["ssot_compliant"] = True
                
                # Check if module has AgentRegistry
                if hasattr(module, 'AgentRegistry'):
                    registry_class = getattr(module, 'AgentRegistry')
                    
                    # Check class for SSOT features
                    if hasattr(registry_class, 'get_ssot_compliance_status'):
                        file_analysis[path]["has_ssot_methods"] = True
                        
                        # Try to get compliance status if it's not async
                        try:
                            # Create instance for testing
                            mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
                            registry_instance = registry_class(llm_manager=mock_llm_manager)
                            
                            if hasattr(registry_instance, 'get_ssot_compliance_status'):
                                compliance_status = registry_instance.get_ssot_compliance_status()
                                file_analysis[path]["ssot_compliance_score"] = compliance_status.get('compliance_score', 0)
                                file_analysis[path]["ssot_status"] = compliance_status.get('status', 'unknown')
                        except Exception as e:
                            file_analysis[path]["ssot_test_error"] = str(e)
        
        print("SSOT Consolidation Analysis:")
        for path, analysis in file_analysis.items():
            print(f"  {path}:")
            for key, value in analysis.items():
                print(f"    {key}: {value}")
        
        # Evaluate consolidation completeness
        importable_modules = [path for path, analysis in file_analysis.items() 
                            if analysis['importable']]
        
        deprecated_modules = [path for path, analysis in file_analysis.items() 
                            if analysis.get('deprecated', False)]
        
        ssot_compliant_modules = [path for path, analysis in file_analysis.items() 
                                if analysis.get('ssot_compliant', False)]
        
        print(f"\nConsolidation Summary:")
        print(f"  Importable modules: {len(importable_modules)}")
        print(f"  Deprecated modules: {len(deprecated_modules)}")
        print(f"  SSOT compliant modules: {len(ssot_compliant_modules)}")
        
        # Validate consolidation progress
        if len(importable_modules) > 1:
            # Check if extra modules are properly marked as deprecated/compatibility
            non_deprecated_count = len(importable_modules) - len(deprecated_modules)
            
            if non_deprecated_count > 1:
                active_modules = [path for path in importable_modules 
                                if path not in deprecated_modules]
                self.fail(
                    f"SSOT CONSOLIDATION INCOMPLETE: Multiple active registry modules found: "
                    f"{active_modules}. After consolidation, only one active module should exist "
                    f"(others should be marked deprecated or removed)."
                )
        
        # Validate at least one SSOT-compliant module exists
        self.assertGreaterEqual(
            len(ssot_compliant_modules), 1,
            "No SSOT-compliant registry module found. Consolidation should result in "
            "at least one module marked as SSOT compliant."
        )
        
        # Validate importable modules exist
        self.assertGreater(
            len(importable_modules), 0,
            "No registry modules are importable. Consolidation should not break all imports."
        )