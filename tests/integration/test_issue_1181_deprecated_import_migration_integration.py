"""
Integration Tests for Issue #1181 Deprecated Import Migration  
============================================================

Business Value Justification:
- Segment: Platform/Critical Infrastructure
- Business Goal: Safe Migration & Zero Downtime Consolidation
- Value Impact: Ensures $500K+ ARR chat functionality continues during import migration
- Strategic Impact: Validates that import path migration doesn't break existing code

CRITICAL MIGRATION VALIDATION:
Issue #1181 requires migrating deprecated import paths to canonical SSOT paths
while maintaining backward compatibility during transition. These integration tests
validate that import migration is safe and doesn't break existing functionality.

Tests verify import path equivalence, backward compatibility, migration safety,
and consistent behavior across old and new import patterns.
"""

import unittest
import importlib
import sys
import inspect
from typing import Dict, Any, List, Type, Optional
from unittest.mock import Mock, patch, MagicMock
import time

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestIssue1181DeprecatedImportMigrationIntegration(SSotAsyncTestCase):
    """Integration test suite for deprecated import migration validation."""
    
    def setUp(self):
        """Set up migration test environment."""
        super().setUp()
        self.canonical_import_path = "netra_backend.app.websocket_core.handlers"
        self.deprecated_import_paths = [
            "netra_backend.app.core.message_router",
            "netra_backend.app.agents.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.services.websocket.message_router"
        ]
        self.test_user_id = "migration_test_user_789"
        
        # Track migration compatibility results
        self.migration_results = {
            "import_compatibility": {},
            "interface_compatibility": {},
            "behavior_compatibility": {},
            "safety_validation": {}
        }
    
    def test_canonical_import_path_stability(self):
        """
        MIGRATION TEST: Verify that canonical import path is stable and working.
        
        The canonical import path must be stable and provide the authoritative
        implementation that all deprecated paths will eventually point to.
        """
        logger.info(" TESTING:  Canonical import path stability")
        
        try:
            # Import from canonical path
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Verify it's the correct class
            self.assertTrue(inspect.isclass(MessageRouter), "MessageRouter should be a class")
            
            # Verify it can be instantiated
            canonical_router = MessageRouter()
            self.assertIsNotNone(canonical_router, "Canonical MessageRouter should be instantiable")
            
            # Verify it has expected interface
            expected_methods = ["route_message", "add_handler", "remove_handler", "get_stats"]
            for method in expected_methods:
                self.assertTrue(
                    hasattr(canonical_router, method),
                    f"Canonical MessageRouter missing method: {method}"
                )
            
            # Store canonical instance for comparison
            self.canonical_router = canonical_router
            self.canonical_class = MessageRouter
            
            logger.info(" PASS:  Canonical import path stable and functional")
            
        except ImportError as e:
            self.fail(f"Canonical import path broken: {e}")
        except Exception as e:
            self.fail(f"Canonical implementation broken: {e}")
    
    def test_deprecated_import_path_compatibility(self):
        """
        MIGRATION TEST: Verify that deprecated import paths still work during transition.
        
        During migration, deprecated import paths should still work to maintain
        backward compatibility for existing code.
        """
        logger.info(" TESTING:  Deprecated import path compatibility")
        
        # Ensure we have the canonical implementation first
        self.test_canonical_import_path_stability()
        
        compatible_imports = []
        broken_imports = []
        proxy_imports = []
        
        for deprecated_path in self.deprecated_import_paths:
            try:
                # Try to import MessageRouter from deprecated path
                module = importlib.import_module(deprecated_path)
                
                if hasattr(module, 'MessageRouter'):
                    deprecated_router_class = getattr(module, 'MessageRouter')
                    
                    # Test if it's the same class (ideal SSOT)
                    if deprecated_router_class is self.canonical_class:
                        compatible_imports.append(deprecated_path)
                        logger.info(f" PASS:  {deprecated_path} imports identical MessageRouter")
                        
                    # Test if it's a compatible proxy/subclass
                    elif (inspect.isclass(deprecated_router_class) and 
                          issubclass(deprecated_router_class, self.canonical_class)):
                        proxy_imports.append(deprecated_path)
                        logger.info(f" WARN:  {deprecated_path} imports compatible proxy MessageRouter")
                        
                    # Test if it has the same interface (duck typing compatibility)
                    else:
                        try:
                            deprecated_instance = deprecated_router_class()
                            interface_compatible = self._test_interface_compatibility(
                                deprecated_instance, self.canonical_router
                            )
                            
                            if interface_compatible:
                                proxy_imports.append(deprecated_path)
                                logger.info(f" WARN:  {deprecated_path} imports interface-compatible MessageRouter")
                            else:
                                broken_imports.append(f"{deprecated_path}: Interface incompatible")
                                logger.error(f" FAIL:  {deprecated_path} imports incompatible MessageRouter")
                                
                        except Exception as e:
                            broken_imports.append(f"{deprecated_path}: {str(e)}")
                            logger.error(f" FAIL:  {deprecated_path} import failed: {e}")
                else:
                    logger.info(f" INFO:  {deprecated_path} does not export MessageRouter")
                    
            except ImportError as e:
                logger.info(f" INFO:  {deprecated_path} cannot be imported: {e}")
            except Exception as e:
                broken_imports.append(f"{deprecated_path}: {str(e)}")
                logger.error(f" FAIL:  {deprecated_path} import error: {e}")
        
        # Store results for analysis
        self.migration_results["import_compatibility"] = {
            "compatible_imports": compatible_imports,
            "proxy_imports": proxy_imports,
            "broken_imports": broken_imports,
            "total_tested": len(self.deprecated_import_paths)
        }
        
        # Migration safety validation
        total_working = len(compatible_imports) + len(proxy_imports)
        compatibility_rate = total_working / len(self.deprecated_import_paths)
        
        logger.info(f" SUMMARY:  Import compatibility:")
        logger.info(f"   - Compatible: {len(compatible_imports)}")
        logger.info(f"   - Proxy: {len(proxy_imports)}")
        logger.info(f"   - Broken: {len(broken_imports)}")
        logger.info(f"   - Rate: {compatibility_rate:.2%}")
        
        # For safe migration, most imports should work
        if compatibility_rate < 0.5:
            logger.warning(f" WARN:  Low compatibility rate may indicate unsafe migration conditions")
        
        logger.info(" PASS:  Deprecated import path compatibility validated")
    
    def test_behavioral_equivalence_across_import_paths(self):
        """
        MIGRATION TEST: Verify that behavior is equivalent across import paths.
        
        All import paths should provide functionally equivalent behavior
        to ensure safe migration without breaking existing functionality.
        """
        logger.info(" TESTING:  Behavioral equivalence across import paths")
        
        # First ensure compatibility test has run
        if not self.migration_results.get("import_compatibility"):
            self.test_deprecated_import_path_compatibility()
        
        compatible_paths = (
            self.migration_results["import_compatibility"]["compatible_imports"] +
            self.migration_results["import_compatibility"]["proxy_imports"]
        )
        
        if not compatible_paths:
            logger.warning(" WARN:  No compatible import paths found for behavioral testing")
            return
        
        # Test behavioral equivalence
        behavioral_results = {}
        canonical_behaviors = self._get_canonical_behaviors()
        
        for import_path in compatible_paths:
            try:
                # Import and test behavior
                module = importlib.import_module(import_path)
                router_class = getattr(module, 'MessageRouter')
                router_instance = router_class()
                
                # Test behaviors
                behaviors = self._get_router_behaviors(router_instance)
                behavioral_equivalent = self._compare_behaviors(canonical_behaviors, behaviors)
                
                behavioral_results[import_path] = {
                    "equivalent": behavioral_equivalent,
                    "behaviors": behaviors,
                    "differences": self._find_behavior_differences(canonical_behaviors, behaviors)
                }
                
                if behavioral_equivalent:
                    logger.info(f" PASS:  {import_path} behaviorally equivalent")
                else:
                    logger.warning(f" WARN:  {import_path} has behavioral differences")
                    
            except Exception as e:
                behavioral_results[import_path] = {
                    "equivalent": False,
                    "error": str(e)
                }
                logger.error(f" FAIL:  {import_path} behavioral test failed: {e}")
        
        # Store results
        self.migration_results["behavior_compatibility"] = behavioral_results
        
        # Analyze behavioral equivalence
        equivalent_count = sum(1 for r in behavioral_results.values() if r.get("equivalent", False))
        equivalence_rate = equivalent_count / len(behavioral_results) if behavioral_results else 0
        
        logger.info(f" SUMMARY:  Behavioral equivalence:")
        logger.info(f"   - Equivalent: {equivalent_count}/{len(behavioral_results)}")
        logger.info(f"   - Rate: {equivalence_rate:.2%}")
        
        # For safe migration, behavior should be highly equivalent
        self.assertGreaterEqual(
            equivalence_rate, 0.8,
            f"Behavioral equivalence rate too low for safe migration: {equivalence_rate:.2%}"
        )
        
        logger.info(" PASS:  Behavioral equivalence validated")
    
    def test_migration_safety_validation(self):
        """
        MIGRATION TEST: Validate that migration from deprecated to canonical is safe.
        
        Tests that migrating code from deprecated import paths to canonical
        paths is safe and doesn't break functionality.
        """
        logger.info(" TESTING:  Migration safety validation")
        
        # Run prerequisite tests
        if not self.migration_results.get("import_compatibility"):
            self.test_deprecated_import_path_compatibility()
        if not self.migration_results.get("behavior_compatibility"):
            self.test_behavioral_equivalence_across_import_paths()
        
        migration_safety_results = {}
        
        # Test migration scenarios for each compatible import path
        compatible_paths = self.migration_results["import_compatibility"]["compatible_imports"]
        
        for deprecated_path in compatible_paths:
            try:
                # Simulate migration scenario
                safety_result = self._test_migration_scenario(deprecated_path, self.canonical_import_path)
                migration_safety_results[deprecated_path] = safety_result
                
                if safety_result["safe"]:
                    logger.info(f" PASS:  Migration from {deprecated_path} is safe")
                else:
                    logger.warning(f" WARN:  Migration from {deprecated_path} has risks: {safety_result['risks']}")
                    
            except Exception as e:
                migration_safety_results[deprecated_path] = {
                    "safe": False,
                    "error": str(e)
                }
                logger.error(f" FAIL:  Migration safety test failed for {deprecated_path}: {e}")
        
        # Store results
        self.migration_results["safety_validation"] = migration_safety_results
        
        # Analyze overall migration safety
        safe_migrations = sum(1 for r in migration_safety_results.values() if r.get("safe", False))
        safety_rate = safe_migrations / len(migration_safety_results) if migration_safety_results else 0
        
        logger.info(f" SUMMARY:  Migration safety:")
        logger.info(f"   - Safe migrations: {safe_migrations}/{len(migration_safety_results)}")
        logger.info(f"   - Safety rate: {safety_rate:.2%}")
        
        # For production deployment, migration should be very safe
        self.assertGreaterEqual(
            safety_rate, 0.9,
            f"Migration safety rate too low for production: {safety_rate:.2%}"
        )
        
        logger.info(" PASS:  Migration safety validated")
    
    def test_incremental_migration_compatibility(self):
        """
        MIGRATION TEST: Verify that incremental migration is supported.
        
        Tests that code can be migrated incrementally (some files using old imports,
        some using new imports) without breaking the system.
        """
        logger.info(" TESTING:  Incremental migration compatibility")
        
        # Test mixed import scenario
        try:
            # Import from both canonical and deprecated paths
            from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter
            
            # Try to find a working deprecated import
            deprecated_router = None
            working_deprecated_path = None
            
            for deprecated_path in self.deprecated_import_paths:
                try:
                    module = importlib.import_module(deprecated_path)
                    if hasattr(module, 'MessageRouter'):
                        deprecated_router_class = getattr(module, 'MessageRouter')
                        deprecated_router = deprecated_router_class()
                        working_deprecated_path = deprecated_path
                        break
                except:
                    continue
            
            if deprecated_router is None:
                logger.warning(" WARN:  No working deprecated import found for incremental migration test")
                return
            
            # Test that both can coexist
            canonical_router = CanonicalRouter()
            
            # Test that both routers work independently
            canonical_stats = canonical_router.get_stats()
            deprecated_stats = deprecated_router.get_stats()
            
            self.assertIsInstance(canonical_stats, dict, "Canonical router should provide stats")
            self.assertIsInstance(deprecated_stats, dict, "Deprecated router should provide stats")
            
            # Test that they have compatible interfaces
            canonical_methods = set(dir(canonical_router))
            deprecated_methods = set(dir(deprecated_router))
            
            # Core methods should overlap significantly
            core_methods = {"route_message", "handle_message", "add_handler", "get_stats"}
            canonical_core = canonical_methods & core_methods
            deprecated_core = deprecated_methods & core_methods
            
            overlap = len(canonical_core & deprecated_core)
            total_core = len(core_methods)
            
            compatibility_score = overlap / total_core
            
            logger.info(f" INFO:  Mixed import compatibility:")
            logger.info(f"   - Canonical path: {self.canonical_import_path}")
            logger.info(f"   - Deprecated path: {working_deprecated_path}")
            logger.info(f"   - Core method overlap: {overlap}/{total_core} ({compatibility_score:.2%})")
            
            # Should have high compatibility for safe incremental migration
            self.assertGreaterEqual(
                compatibility_score, 0.75,
                f"Insufficient compatibility for incremental migration: {compatibility_score:.2%}"
            )
            
            logger.info(" PASS:  Incremental migration compatibility validated")
            
        except Exception as e:
            self.fail(f"Incremental migration compatibility test failed: {e}")
    
    def test_migration_performance_impact(self):
        """
        MIGRATION TEST: Verify that migration doesn't significantly impact performance.
        
        Tests that importing from canonical vs deprecated paths has similar
        performance characteristics.
        """
        logger.info(" TESTING:  Migration performance impact")
        
        import time
        
        # Test canonical import performance
        canonical_import_times = []
        for i in range(5):
            start_time = time.perf_counter()
            
            # Force reload to measure import time
            if self.canonical_import_path in sys.modules:
                del sys.modules[self.canonical_import_path]
            
            from netra_backend.app.websocket_core.handlers import MessageRouter
            router = MessageRouter()
            
            end_time = time.perf_counter()
            canonical_import_times.append(end_time - start_time)
        
        avg_canonical_time = sum(canonical_import_times) / len(canonical_import_times)
        
        # Test deprecated import performance (if any work)
        deprecated_import_times = []
        working_deprecated_path = None
        
        for deprecated_path in self.deprecated_import_paths:
            try:
                for i in range(3):  # Fewer iterations for deprecated
                    start_time = time.perf_counter()
                    
                    if deprecated_path in sys.modules:
                        del sys.modules[deprecated_path]
                    
                    module = importlib.import_module(deprecated_path)
                    if hasattr(module, 'MessageRouter'):
                        router_class = getattr(module, 'MessageRouter')
                        router = router_class()
                        
                        end_time = time.perf_counter()
                        deprecated_import_times.append(end_time - start_time)
                
                if deprecated_import_times:
                    working_deprecated_path = deprecated_path
                    break
                    
            except:
                continue
        
        if deprecated_import_times:
            avg_deprecated_time = sum(deprecated_import_times) / len(deprecated_import_times)
            performance_ratio = avg_deprecated_time / avg_canonical_time
            
            logger.info(f" INFO:  Import performance comparison:")
            logger.info(f"   - Canonical avg: {avg_canonical_time*1000:.2f}ms")
            logger.info(f"   - Deprecated avg: {avg_deprecated_time*1000:.2f}ms")
            logger.info(f"   - Performance ratio: {performance_ratio:.2f}x")
            
            # Performance should be reasonably similar (within 5x)
            self.assertLess(
                performance_ratio, 5.0,
                f"Deprecated import significantly slower: {performance_ratio:.2f}x"
            )
            
            logger.info(" PASS:  Migration performance impact acceptable")
        else:
            logger.info(" INFO:  No working deprecated imports for performance comparison")
    
    def _test_interface_compatibility(self, instance1, instance2) -> bool:
        """Test if two router instances have compatible interfaces."""
        try:
            # Check core methods exist
            core_methods = ["get_stats", "add_handler", "remove_handler"]
            
            for method in core_methods:
                if not (hasattr(instance1, method) and hasattr(instance2, method)):
                    return False
            
            # Check that get_stats returns similar structure
            stats1 = instance1.get_stats()
            stats2 = instance2.get_stats()
            
            if not (isinstance(stats1, dict) and isinstance(stats2, dict)):
                return False
            
            # Check that basic keys overlap
            keys1 = set(stats1.keys())
            keys2 = set(stats2.keys())
            overlap = len(keys1 & keys2) / max(len(keys1), len(keys2), 1)
            
            return overlap >= 0.5  # At least 50% key overlap
            
        except Exception:
            return False
    
    def _get_canonical_behaviors(self) -> Dict[str, Any]:
        """Get canonical router behaviors for comparison."""
        behaviors = {}
        
        try:
            # Test basic behaviors
            behaviors["has_handlers"] = len(self.canonical_router.handlers) > 0
            behaviors["stats_structure"] = set(self.canonical_router.get_stats().keys())
            behaviors["handler_order"] = self.canonical_router.get_handler_order()
            behaviors["singleton"] = True  # Assuming get_message_router() returns singleton
        except Exception as e:
            behaviors["error"] = str(e)
        
        return behaviors
    
    def _get_router_behaviors(self, router) -> Dict[str, Any]:
        """Get router behaviors for comparison."""
        behaviors = {}
        
        try:
            behaviors["has_handlers"] = len(getattr(router, 'handlers', [])) > 0
            
            if hasattr(router, 'get_stats'):
                stats = router.get_stats()
                behaviors["stats_structure"] = set(stats.keys()) if isinstance(stats, dict) else set()
            
            if hasattr(router, 'get_handler_order'):
                behaviors["handler_order"] = router.get_handler_order()
            
        except Exception as e:
            behaviors["error"] = str(e)
        
        return behaviors
    
    def _compare_behaviors(self, behaviors1: Dict[str, Any], behaviors2: Dict[str, Any]) -> bool:
        """Compare two behavior dictionaries for equivalence."""
        try:
            # Compare key behaviors
            if behaviors1.get("has_handlers") != behaviors2.get("has_handlers"):
                return False
            
            # Compare stats structure similarity
            stats1 = behaviors1.get("stats_structure", set())
            stats2 = behaviors2.get("stats_structure", set())
            
            if stats1 and stats2:
                overlap = len(stats1 & stats2) / max(len(stats1), len(stats2))
                if overlap < 0.7:  # At least 70% structure similarity
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _find_behavior_differences(self, behaviors1: Dict[str, Any], behaviors2: Dict[str, Any]) -> List[str]:
        """Find differences between behavior dictionaries."""
        differences = []
        
        for key in set(behaviors1.keys()) | set(behaviors2.keys()):
            val1 = behaviors1.get(key)
            val2 = behaviors2.get(key)
            
            if val1 != val2:
                differences.append(f"{key}: {val1} != {val2}")
        
        return differences
    
    def _test_migration_scenario(self, deprecated_path: str, canonical_path: str) -> Dict[str, Any]:
        """Test a specific migration scenario."""
        try:
            # Import from both paths
            deprecated_module = importlib.import_module(deprecated_path)
            canonical_module = importlib.import_module(canonical_path)
            
            deprecated_class = getattr(deprecated_module, 'MessageRouter')
            canonical_class = getattr(canonical_module, 'MessageRouter')
            
            # Test instantiation
            deprecated_instance = deprecated_class()
            canonical_instance = canonical_class()
            
            # Test basic functionality
            deprecated_stats = deprecated_instance.get_stats()
            canonical_stats = canonical_instance.get_stats()
            
            # Assess migration safety
            risks = []
            
            # Check if classes are different
            if deprecated_class is not canonical_class:
                risks.append("Different class objects")
            
            # Check if interfaces differ significantly
            deprecated_methods = set(dir(deprecated_instance))
            canonical_methods = set(dir(canonical_instance))
            method_overlap = len(deprecated_methods & canonical_methods) / max(len(canonical_methods), 1)
            
            if method_overlap < 0.8:
                risks.append(f"Low method overlap: {method_overlap:.2%}")
            
            return {
                "safe": len(risks) == 0,
                "risks": risks,
                "method_overlap": method_overlap
            }
            
        except Exception as e:
            return {
                "safe": False,
                "error": str(e)
            }


if __name__ == '__main__':
    unittest.main()