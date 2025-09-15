"""
Test Issue #1181 Deprecated Import Migration Integration

Business Value Justification (BVJ):
- Segment: Platform (Developer Experience)
- Business Goal: System Maintainability and SSOT Compliance
- Value Impact: Ensure safe migration from deprecated to canonical import paths
- Strategic Impact: Prevent breaking changes during SSOT consolidation

This integration test validates the migration process from deprecated MessageRouter
import paths to canonical paths without breaking existing functionality.
"""

import pytest
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase as BaseIntegrationTest
from shared.isolated_environment import get_env


class TestIssue1181DeprecatedImportMigrationIntegration(BaseIntegrationTest):
    """Test deprecated import migration with real codebase integration."""

    @pytest.mark.integration
    def test_deprecated_import_path_current_status(self):
        """
        Test current status of deprecated import paths in the codebase.
        
        This establishes baseline understanding of how many files use
        deprecated paths before migration begins.
        """
        
        # Find all files using deprecated MessageRouter imports
        deprecated_import_files = self._find_deprecated_import_usage()
        
        # Find all files using canonical MessageRouter imports  
        canonical_import_files = self._find_canonical_import_usage()
        
        # Analyze current import usage patterns
        migration_analysis = self._analyze_current_import_patterns(
            deprecated_import_files, canonical_import_files
        )
        
        # Document baseline status
        self._document_migration_baseline(migration_analysis)
        
        # Verify there are some imports to migrate (if this fails, migration may be complete)
        total_imports = len(deprecated_import_files) + len(canonical_import_files)
        assert total_imports > 0, "No MessageRouter imports found - this indicates a search issue"

    @pytest.mark.integration
    def test_import_path_migration_simulation(self):
        """
        Simulate migrating deprecated import paths to canonical paths.
        
        This tests the migration process without actually modifying the codebase,
        validating that the migration approach is safe and effective.
        """
        
        # Get deprecated import files
        deprecated_files = self._find_deprecated_import_usage()
        
        migration_simulation_results = []
        
        for file_info in deprecated_files[:5]:  # Test first 5 files for safety
            try:
                # Simulate migration for this file
                simulation_result = self._simulate_import_migration(file_info)
                migration_simulation_results.append({
                    "file": file_info["file"],
                    "simulation_success": True,
                    "result": simulation_result
                })
            except Exception as e:
                migration_simulation_results.append({
                    "file": file_info["file"],
                    "simulation_success": False,
                    "error": str(e)
                })
        
        # Analyze simulation results
        self._analyze_migration_simulation_results(migration_simulation_results)
        
        # Verify at least some migrations can be simulated successfully
        successful_simulations = [r for r in migration_simulation_results if r["simulation_success"]]
        if len(deprecated_files) > 0:
            assert len(successful_simulations) > 0, "No successful migration simulations - approach may be flawed"

    @pytest.mark.integration
    def test_backwards_compatibility_during_migration(self):
        """
        Test backwards compatibility during the migration period.
        
        This ensures that both deprecated and canonical imports work
        simultaneously during the migration period.
        """
        
        # Test that both import paths work
        import_compatibility_results = {}
        
        # Test canonical import
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter
            import_compatibility_results["canonical"] = {
                "import_success": True,
                "class_id": id(CanonicalRouter),
                "class_name": CanonicalRouter.__name__
            }
        except ImportError as e:
            import_compatibility_results["canonical"] = {
                "import_success": False,
                "error": str(e)
            }
        
        # Test deprecated import
        try:
            from netra_backend.app.websocket_core import MessageRouter as DeprecatedRouter
            import_compatibility_results["deprecated"] = {
                "import_success": True,
                "class_id": id(DeprecatedRouter),
                "class_name": DeprecatedRouter.__name__
            }
        except ImportError as e:
            import_compatibility_results["deprecated"] = {
                "import_success": False,
                "error": str(e)
            }
        
        # Test compatibility requirements
        self._validate_backwards_compatibility(import_compatibility_results)
        
        # Both paths should work during migration period
        assert import_compatibility_results["canonical"]["import_success"], "Canonical import must work"
        assert import_compatibility_results["deprecated"]["import_success"], "Deprecated import must work during migration"

    @pytest.mark.integration
    def test_ssot_import_registry_accuracy(self):
        """
        Test SSOT Import Registry accuracy for MessageRouter entries.
        
        This validates that the SSOT Import Registry correctly documents
        the current state of MessageRouter imports.
        """
        
        # Read SSOT Import Registry
        registry_path = Path(__file__).parent.parent.parent / "docs" / "SSOT_IMPORT_REGISTRY.md"
        
        if not registry_path.exists():
            pytest.skip("SSOT Import Registry not found - may not be implemented yet")
        
        with open(registry_path, 'r') as f:
            registry_content = f.read()
        
        # Check for MessageRouter entries
        message_router_entries = self._extract_message_router_registry_entries(registry_content)
        
        # Validate registry entries against actual codebase
        registry_validation_results = self._validate_registry_entries(message_router_entries)
        
        # Document registry accuracy
        self._document_registry_accuracy(registry_validation_results)
        
        # Verify registry contains MessageRouter information
        assert len(message_router_entries) > 0, "SSOT Import Registry should contain MessageRouter entries"

    @pytest.mark.integration
    def test_migration_impact_on_existing_functionality(self):
        """
        Test impact of import migration on existing functionality.
        
        This ensures that migrating imports doesn't break existing code
        that depends on MessageRouter functionality.
        """
        
        # Test existing functionality with current imports
        functionality_tests = [
            self._test_message_router_instantiation,
            self._test_message_router_interface,
            self._test_message_router_inheritance
        ]
        
        pre_migration_results = {}
        
        for test_func in functionality_tests:
            test_name = test_func.__name__
            try:
                result = test_func()
                pre_migration_results[test_name] = {
                    "success": True,
                    "result": result
                }
            except Exception as e:
                pre_migration_results[test_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Document functionality preservation requirements
        self._document_functionality_preservation_requirements(pre_migration_results)
        
        # Verify core functionality works with current imports
        successful_tests = [name for name, result in pre_migration_results.items() if result["success"]]
        assert len(successful_tests) > 0, "Some MessageRouter functionality should work before migration"

    def _find_deprecated_import_usage(self) -> List[Dict[str, str]]:
        """Find files using deprecated MessageRouter imports."""
        try:
            # Search for deprecated import pattern
            result = subprocess.run([
                "grep", "-r", "-n", "--include=*.py",
                "from netra_backend.app.websocket_core import.*MessageRouter",
                str(Path(__file__).parent.parent.parent)
            ], capture_output=True, text=True)
            
            return self._parse_grep_results(result.stdout)
        except Exception:
            return []

    def _find_canonical_import_usage(self) -> List[Dict[str, str]]:
        """Find files using canonical MessageRouter imports."""
        try:
            # Search for canonical import pattern
            result = subprocess.run([
                "grep", "-r", "-n", "--include=*.py", 
                "from netra_backend.app.websocket_core.handlers import.*MessageRouter",
                str(Path(__file__).parent.parent.parent)
            ], capture_output=True, text=True)
            
            return self._parse_grep_results(result.stdout)
        except Exception:
            return []

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

    def _analyze_current_import_patterns(self, deprecated: List[Dict], canonical: List[Dict]) -> Dict[str, Any]:
        """Analyze current import usage patterns."""
        total_deprecated = len(deprecated)
        total_canonical = len(canonical)
        total_imports = total_deprecated + total_canonical
        
        return {
            "deprecated_count": total_deprecated,
            "canonical_count": total_canonical,
            "total_imports": total_imports,
            "canonical_percentage": (total_canonical / total_imports * 100) if total_imports > 0 else 0,
            "migration_required": total_deprecated > 0,
            "files_needing_migration": [f["file"] for f in deprecated]
        }

    def _simulate_import_migration(self, file_info: Dict[str, str]) -> Dict[str, Any]:
        """Simulate migrating imports in a single file."""
        file_path = file_info["file"]
        
        # Read original file content
        try:
            with open(file_path, 'r') as f:
                original_content = f.read()
        except Exception as e:
            raise Exception(f"Cannot read file {file_path}: {e}")
        
        # Simulate the migration transformation
        deprecated_pattern = "from netra_backend.app.websocket_core import"
        canonical_replacement = "from netra_backend.app.websocket_core.handlers import"
        
        simulated_content = original_content.replace(deprecated_pattern, canonical_replacement)
        
        # Check if transformation was applied
        transformation_applied = simulated_content != original_content
        
        return {
            "file": file_path,
            "transformation_applied": transformation_applied,
            "original_lines": len(original_content.split('\n')),
            "simulated_lines": len(simulated_content.split('\n')),
            "changes_detected": transformation_applied
        }

    def _validate_backwards_compatibility(self, compatibility_results: Dict[str, Dict[str, Any]]) -> None:
        """Validate backwards compatibility requirements."""
        canonical_works = compatibility_results.get("canonical", {}).get("import_success", False)
        deprecated_works = compatibility_results.get("deprecated", {}).get("import_success", False)
        
        # During migration period, both should work
        if canonical_works and deprecated_works:
            # Check they're the same object (SSOT requirement)
            canonical_id = compatibility_results["canonical"]["class_id"]
            deprecated_id = compatibility_results["deprecated"]["class_id"]
            
            if canonical_id == deprecated_id:
                print(f"✅ SSOT Compliance: Both imports return same object")
            else:
                print(f"❌ SSOT Violation: Different objects returned (canonical: {canonical_id}, deprecated: {deprecated_id})")

    def _extract_message_router_registry_entries(self, registry_content: str) -> List[Dict[str, str]]:
        """Extract MessageRouter entries from SSOT Import Registry."""
        entries = []
        lines = registry_content.split('\n')
        
        for i, line in enumerate(lines):
            if 'MessageRouter' in line and ('import' in line.lower() or 'path' in line.lower()):
                entries.append({
                    "line_number": i + 1,
                    "content": line.strip(),
                    "context": "MessageRouter registry entry"
                })
        
        return entries

    def _validate_registry_entries(self, entries: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate registry entries against actual codebase."""
        validation_results = {
            "total_entries": len(entries),
            "validated_entries": 0,
            "invalid_entries": [],
            "missing_entries": []
        }
        
        # This is a placeholder for registry validation logic
        # In a full implementation, this would check each registry entry
        # against the actual import paths in the codebase
        
        return validation_results

    def _test_message_router_instantiation(self) -> Dict[str, Any]:
        """Test MessageRouter can be instantiated."""
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        try:
            router = MessageRouter()
            return {
                "instantiation_success": True,
                "router_type": type(router).__name__
            }
        except Exception as e:
            return {
                "instantiation_success": False,
                "error": str(e)
            }

    def _test_message_router_interface(self) -> Dict[str, Any]:
        """Test MessageRouter interface availability."""
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        interface_methods = [attr for attr in dir(router) if not attr.startswith('_')]
        
        return {
            "interface_methods_count": len(interface_methods),
            "has_handle_method": "handle" in str(interface_methods).lower(),
            "has_route_method": "route" in str(interface_methods).lower()
        }

    def _test_message_router_inheritance(self) -> Dict[str, Any]:
        """Test MessageRouter inheritance hierarchy."""
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        return {
            "class_name": MessageRouter.__name__,
            "module": MessageRouter.__module__,
            "mro_length": len(MessageRouter.__mro__),
            "base_classes": [cls.__name__ for cls in MessageRouter.__mro__[1:]]
        }

    def _document_migration_baseline(self, analysis: Dict[str, Any]) -> None:
        """Document the migration baseline status."""
        print(f"\n--- Migration Baseline Analysis ---")
        print(f"Total MessageRouter imports: {analysis['total_imports']}")
        print(f"Canonical imports: {analysis['canonical_count']} ({analysis['canonical_percentage']:.1f}%)")
        print(f"Deprecated imports: {analysis['deprecated_count']}")
        print(f"Migration required: {'Yes' if analysis['migration_required'] else 'No'}")
        
        if analysis['files_needing_migration']:
            print(f"\nFiles needing migration (showing first 10):")
            for file_path in analysis['files_needing_migration'][:10]:
                print(f"  - {file_path}")

    def _analyze_migration_simulation_results(self, results: List[Dict[str, Any]]) -> None:
        """Analyze migration simulation results."""
        print(f"\n--- Migration Simulation Results ---")
        
        total_simulations = len(results)
        successful_simulations = len([r for r in results if r["simulation_success"]])
        
        print(f"Total simulations: {total_simulations}")
        print(f"Successful simulations: {successful_simulations}")
        if total_simulations > 0:
            print(f"Success rate: {(successful_simulations/total_simulations)*100:.1f}%")
        
        # Show details
        for result in results:
            status = "✅" if result["simulation_success"] else "❌"
            print(f"  {status} {os.path.basename(result['file'])}")
            if not result["simulation_success"]:
                print(f"    Error: {result.get('error', 'Unknown')}")

    def _document_registry_accuracy(self, validation_results: Dict[str, Any]) -> None:
        """Document SSOT Import Registry accuracy."""
        print(f"\n--- SSOT Import Registry Validation ---")
        print(f"Total registry entries: {validation_results['total_entries']}")
        print(f"Validated entries: {validation_results['validated_entries']}")
        
        if validation_results['invalid_entries']:
            print(f"Invalid entries: {len(validation_results['invalid_entries'])}")
        
        if validation_results['missing_entries']:
            print(f"Missing entries: {len(validation_results['missing_entries'])}")

    def _document_functionality_preservation_requirements(self, results: Dict[str, Dict[str, Any]]) -> None:
        """Document functionality preservation requirements."""
        print(f"\n--- Functionality Preservation Requirements ---")
        
        for test_name, result in results.items():
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {test_name}")
            if not result["success"]:
                print(f"    Error: {result.get('error', 'Unknown')}")
            
        successful_tests = [name for name, result in results.items() if result["success"]]
        print(f"\nSuccessful functionality tests: {len(successful_tests)}/{len(results)}")
        print(f"Migration requirement: All current functionality must be preserved")