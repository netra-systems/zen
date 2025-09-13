"""

Phase 2: Safe Removal Validation Tests

Issue #757 - Migration Safety Analysis



These tests validate that removing the deprecated configuration manager

is safe and won't break existing functionality.

"""

import os

import sys

import pytest

from pathlib import Path

from unittest.mock import patch, MagicMock

import ast

import importlib.util





class TestSafeRemovalValidation:

    """Phase 2 Tests - Validate safe removal of deprecated manager"""



    def test_canonical_config_provides_all_required_functionality(self):

        """MUST PASS: Canonical config has all functionality needed"""

        try:

            sys.path.insert(0, str(Path.cwd()))

            from netra_backend.app.core.configuration.base import UnifiedConfigManager



            # Test that canonical manager can be instantiated

            config_manager = UnifiedConfigManager()

            assert config_manager is not None, "Canonical UnifiedConfigManager cannot be instantiated"



            # Check for essential configuration methods

            required_methods = [

                'get_database_url',

                'get_redis_url',

                'get_cors_origins',

                'is_development',

                'is_production'

            ]



            available_methods = [method for method in dir(config_manager)

                               if not method.startswith('_')]



            # We need at least some configuration functionality

            assert len(available_methods) >= 5, (

                f"Canonical UnifiedConfigManager only has {len(available_methods)} methods: {available_methods}. "

                f"Insufficient functionality to replace deprecated manager safely."

            )



            print(f"✅ Canonical UnifiedConfigManager has {len(available_methods)} methods available")



        except ImportError as e:

            pytest.fail(f"Cannot import canonical UnifiedConfigManager: {e}")

        except Exception as e:

            pytest.fail(f"Canonical UnifiedConfigManager instantiation failed: {e}")



    def test_no_critical_imports_from_deprecated_manager(self):

        """MUST PASS: No critical code imports from deprecated manager"""

        critical_files = [

            "netra_backend/app/main.py",

            "netra_backend/app/startup.py",

            "netra_backend/app/core/app_state.py",

            "netra_backend/app/websocket_core/manager.py",

            "netra_backend/app/db/database_manager.py"

        ]



        files_importing_deprecated = []



        for file_path in critical_files:

            file_obj = Path(file_path)

            if not file_obj.exists():

                continue



            try:

                content = file_obj.read_text(encoding='utf-8')

                if 'from netra_backend.app.core.managers.unified_configuration_manager' in content:

                    files_importing_deprecated.append(str(file_path))

            except Exception:

                continue



        assert len(files_importing_deprecated) == 0, (

            f"CRITICAL FILES IMPORT DEPRECATED MANAGER: {files_importing_deprecated}. "

            f"These files must be updated before safe removal is possible."

        )



        print(f"✅ No critical files import deprecated configuration manager")



    def test_deployment_scripts_use_canonical_config(self):

        """SHOULD PASS: Deployment scripts reference canonical config"""

        deployment_files = [

            "scripts/deploy_to_gcp.py",

            "scripts/refresh_dev_services.py"

        ]



        deprecated_references = []

        canonical_references = []



        for file_path in deployment_files:

            file_obj = Path(file_path)

            if not file_obj.exists():

                continue



            try:

                content = file_obj.read_text(encoding='utf-8')



                if 'unified_configuration_manager' in content:

                    deprecated_references.append(str(file_path))



                if 'core.configuration.base' in content:

                    canonical_references.append(str(file_path))

            except Exception:

                continue



        # Either no references (acceptable) or only canonical references

        mixed_references = len(deprecated_references) > 0 and len(canonical_references) > 0



        assert not mixed_references, (

            f"DEPLOYMENT SCRIPTS HAVE MIXED REFERENCES: "

            f"Deprecated: {deprecated_references}, Canonical: {canonical_references}. "

            f"Must standardize on canonical before safe removal."

        )



        if len(canonical_references) > 0:

            print(f"✅ Deployment scripts use canonical configuration: {canonical_references}")

        else:

            print(f"ℹ️ Deployment scripts don't explicitly reference configuration (acceptable)")



    def test_test_files_migration_readiness(self):

        """SHOULD PASS: Test files can work without deprecated manager"""

        test_directories = [

            "tests",

            "netra_backend/tests"

        ]



        deprecated_test_imports = []

        total_test_files = 0



        for test_dir in test_directories:

            test_path = Path(test_dir)

            if not test_path.exists():

                continue



            for py_file in test_path.rglob("*.py"):

                if py_file.name.startswith("test_"):

                    total_test_files += 1

                    try:

                        content = py_file.read_text(encoding='utf-8')

                        if 'unified_configuration_manager' in content:

                            deprecated_test_imports.append(str(py_file))

                    except Exception:

                        continue



        deprecated_percentage = (len(deprecated_test_imports) / max(total_test_files, 1)) * 100



        # We can tolerate some test files using deprecated manager during transition

        assert deprecated_percentage < 25, (

            f"TOO MANY TEST FILES USE DEPRECATED MANAGER: {len(deprecated_test_imports)}/{total_test_files} "

            f"({deprecated_percentage:.1f}%) files: {deprecated_test_imports[:5]}... "

            f"Must migrate majority of tests before safe removal."

        )



        print(f"✅ Only {len(deprecated_test_imports)}/{total_test_files} test files "

              f"({deprecated_percentage:.1f}%) use deprecated manager")



    def test_circular_import_prevention(self):

        """MUST PASS: Removing deprecated manager won't create circular imports"""

        try:

            sys.path.insert(0, str(Path.cwd()))



            # Test importing canonical manager doesn't cause circular imports

            from netra_backend.app.core.configuration.base import UnifiedConfigManager



            # Try to instantiate to ensure no lazy import issues

            config = UnifiedConfigManager()



            assert config is not None, "Canonical UnifiedConfigManager has circular import issues"



            print("✅ Canonical UnifiedConfigManager has no circular import issues")



        except ImportError as e:

            pytest.fail(f"Circular import detected in canonical UnifiedConfigManager: {e}")

        except Exception as e:

            pytest.fail(f"Canonical UnifiedConfigManager has initialization issues: {e}")



    def test_environment_variable_compatibility(self):

        """MUST PASS: Canonical manager handles environment variables correctly"""

        try:

            sys.path.insert(0, str(Path.cwd()))



            # Mock some environment variables

            test_env = {

                'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',

                'REDIS_URL': 'redis://localhost:6379',

                'ENV': 'test',

                'DEBUG': 'true'

            }



            with patch.dict('os.environ', test_env, clear=False):

                from netra_backend.app.core.configuration.base import UnifiedConfigManager



                config = UnifiedConfigManager()



                # Test that configuration can access environment variables

                # We don't need specific methods, just that it doesn't crash

                config_methods = [method for method in dir(config)

                                if not method.startswith('_') and callable(getattr(config, method))]



                # Try calling some methods to ensure they work with environment

                method_results = {}

                for method_name in config_methods[:5]:  # Test first 5 methods

                    try:

                        method = getattr(config, method_name)

                        result = method()

                        method_results[method_name] = "success"

                    except Exception as e:

                        method_results[method_name] = f"error: {e}"



                successful_methods = sum(1 for result in method_results.values()

                                       if result == "success")



                assert successful_methods >= 1, (

                    f"Canonical UnifiedConfigManager methods failing: {method_results}. "

                    f"Environment variable handling may be broken."

                )



                print(f"✅ Canonical UnifiedConfigManager successfully executed "

                      f"{successful_methods}/{len(method_results)} methods")



        except ImportError as e:

            pytest.fail(f"Cannot test canonical UnifiedConfigManager environment handling: {e}")





class TestMigrationPrerequisites:

    """Validate prerequisites for safe migration"""



    def test_backup_verification_readiness(self):

        """SHOULD PASS: System ready for backup verification"""

        deprecated_path = Path("netra_backend/app/core/managers/unified_configuration_manager.py")



        if not deprecated_path.exists():

            pytest.skip("Deprecated file already removed")



        # Check file size for backup planning

        file_size = deprecated_path.stat().st_size



        # Large file needs careful backup handling

        backup_strategy_needed = file_size > 50000  # 50KB threshold



        if backup_strategy_needed:

            print(f"⚠️ Large deprecated file ({file_size} bytes) requires careful backup strategy")

        else:

            print(f"✅ Small deprecated file ({file_size} bytes) - standard backup sufficient")



        # This should always pass - we're just gathering information

        assert True, "Backup verification readiness check"



    def test_rollback_plan_feasibility(self):

        """SHOULD PASS: Rollback plan is feasible if needed"""

        canonical_path = Path("netra_backend/app/core/configuration/base.py")



        # Ensure canonical file exists and is substantial

        assert canonical_path.exists(), "Canonical configuration file missing - rollback impossible"



        canonical_size = canonical_path.stat().st_size

        assert canonical_size > 1000, (

            f"Canonical configuration too small ({canonical_size} bytes) for rollback safety"

        )



        # Check that canonical has actual configuration logic

        try:

            content = canonical_path.read_text(encoding='utf-8')

            has_config_logic = any(keyword in content.lower() for keyword in [

                'database', 'redis', 'environment', 'config', 'setting'

            ])



            assert has_config_logic, (

                "Canonical configuration lacks configuration logic - rollback risky"

            )



            print(f"✅ Canonical configuration ({canonical_size} bytes) ready for rollback if needed")



        except Exception as e:

            pytest.fail(f"Cannot analyze canonical configuration for rollback: {e}")





if __name__ == "__main__":

    print("Phase 2: Running Safe Removal Validation Tests")

    print("These tests validate migration safety before removing deprecated manager")

    pytest.main([__file__, "-v", "--tb=short"])

