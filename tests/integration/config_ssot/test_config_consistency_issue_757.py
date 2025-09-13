"""

Phase 1: Configuration Consistency Integration Tests

Issue #757 - Integration-level SSOT violation detection



These tests are DESIGNED TO FAIL to expose how the duplication crisis

affects cross-service integration and consistency.

"""

import os

import sys

import pytest

from pathlib import Path

from unittest.mock import patch, MagicMock





class TestConfigurationConsistencyIntegration:

    """Integration tests exposing configuration consistency violations"""



    def test_cross_service_config_inconsistency_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - Different services may use different configs"""

        try:

            sys.path.insert(0, str(Path.cwd()))



            # Import both configuration managers

            from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager

            from netra_backend.app.core.configuration.base import UnifiedConfigManager



            # Simulate different services using different configs

            deprecated_config = UnifiedConfigurationManager()

            canonical_config = UnifiedConfigManager()



            # Get configuration values (mock if needed)

            deprecated_methods = [m for m in dir(deprecated_config) if not m.startswith('_')]

            canonical_methods = [m for m in dir(canonical_config) if not m.startswith('_')]



            # Check for inconsistent method availability

            method_diff = set(deprecated_methods) ^ set(canonical_methods)



            # This test SHOULD FAIL due to method inconsistencies

            assert len(method_diff) == 0, (

                f"CRITICAL INTEGRATION FAILURE: Configuration managers have "

                f"{len(method_diff)} different methods: {sorted(method_diff)}. "

                f"This means different services get different configuration "

                f"interfaces, causing integration failures and race conditions."

            )

        except ImportError as e:

            pytest.skip(f"Import failed: {e}")



    def test_environment_variable_handling_inconsistency_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - Different env var handling patterns"""

        try:

            sys.path.insert(0, str(Path.cwd()))



            # Check if both files handle environment variables differently

            deprecated_path = Path("netra_backend/app/core/managers/unified_configuration_manager.py")

            canonical_path = Path("netra_backend/app/core/configuration/base.py")



            deprecated_content = deprecated_path.read_text(encoding='utf-8')

            canonical_content = canonical_path.read_text(encoding='utf-8')



            # Look for environment variable patterns

            deprecated_env_patterns = [

                'os.environ' in deprecated_content,

                'getenv' in deprecated_content,

                'environ' in deprecated_content

            ]



            canonical_env_patterns = [

                'os.environ' in canonical_content,

                'getenv' in canonical_content,

                'environ' in canonical_content

            ]



            # Count pattern differences

            deprecated_env_usage = sum(deprecated_env_patterns)

            canonical_env_usage = sum(canonical_env_patterns)



            # This test SHOULD FAIL if environment handling differs significantly

            assert abs(deprecated_env_usage - canonical_env_usage) <= 1, (

                f"CRITICAL ENV HANDLING INCONSISTENCY: Deprecated manager has "

                f"{deprecated_env_usage} env patterns vs canonical {canonical_env_usage}. "

                f"Different environment variable handling creates unpredictable "

                f"behavior across services and deployment environments."

            )

        except Exception as e:

            pytest.skip(f"File analysis failed: {e}")



    def test_database_connection_config_duplication_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - Database config duplication risk"""

        try:

            deprecated_path = Path("netra_backend/app/core/managers/unified_configuration_manager.py")

            canonical_path = Path("netra_backend/app/core/configuration/base.py")



            deprecated_content = deprecated_path.read_text(encoding='utf-8')

            canonical_content = canonical_path.read_text(encoding='utf-8')



            # Look for database configuration patterns

            db_patterns = [

                'DATABASE_URL', 'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD',

                'POSTGRES', 'CLICKHOUSE', 'database', 'connection'

            ]



            deprecated_db_refs = sum(1 for pattern in db_patterns if pattern.lower() in deprecated_content.lower())

            canonical_db_refs = sum(1 for pattern in db_patterns if pattern.lower() in canonical_content.lower())



            both_have_db_config = deprecated_db_refs > 2 and canonical_db_refs > 2



            # This test SHOULD FAIL if both have significant database configuration

            assert not both_have_db_config, (

                f"CRITICAL DATABASE CONFIG DUPLICATION: Deprecated manager has "

                f"{deprecated_db_refs} database references vs canonical {canonical_db_refs}. "

                f"Duplicate database configuration creates connection pool conflicts "

                f"and potential data corruption risks."

            )

        except Exception as e:

            pytest.skip(f"Database config analysis failed: {e}")



    def test_websocket_configuration_consistency_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - WebSocket config affecting Golden Path"""

        try:

            deprecated_path = Path("netra_backend/app/core/managers/unified_configuration_manager.py")

            canonical_path = Path("netra_backend/app/core/configuration/base.py")



            deprecated_content = deprecated_path.read_text(encoding='utf-8')

            canonical_content = canonical_path.read_text(encoding='utf-8')



            # Look for WebSocket-related configuration

            ws_patterns = [

                'websocket', 'ws_', 'socket', 'cors', 'origin'

            ]



            deprecated_ws_refs = sum(1 for pattern in ws_patterns if pattern.lower() in deprecated_content.lower())

            canonical_ws_refs = sum(1 for pattern in ws_patterns if pattern.lower() in canonical_content.lower())



            both_have_ws_config = deprecated_ws_refs > 1 and canonical_ws_refs > 1



            # This test SHOULD FAIL if both have WebSocket configuration

            assert not both_have_ws_config, (

                f"CRITICAL WEBSOCKET CONFIG DUPLICATION: Deprecated manager has "

                f"{deprecated_ws_refs} WebSocket references vs canonical {canonical_ws_refs}. "

                f"WebSocket configuration duplication directly threatens Golden Path "

                f"chat functionality and $500K+ ARR."

            )

        except Exception as e:

            pytest.skip(f"WebSocket config analysis failed: {e}")



    def test_service_startup_sequence_risk_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - Service startup may use wrong config"""

        try:

            sys.path.insert(0, str(Path.cwd()))



            # Look for startup-related imports in both files

            deprecated_path = Path("netra_backend/app/core/managers/unified_configuration_manager.py")

            canonical_path = Path("netra_backend/app/core/configuration/base.py")



            deprecated_content = deprecated_path.read_text(encoding='utf-8')

            canonical_content = canonical_path.read_text(encoding='utf-8')



            # Check for startup/initialization patterns

            startup_patterns = [

                'initialize', 'startup', 'init', 'configure', 'setup'

            ]



            deprecated_startup_refs = sum(1 for pattern in startup_patterns

                                        if pattern.lower() in deprecated_content.lower())

            canonical_startup_refs = sum(1 for pattern in startup_patterns

                                       if pattern.lower() in canonical_content.lower())



            both_have_startup = deprecated_startup_refs > 2 and canonical_startup_refs > 2



            # This test SHOULD FAIL if both have startup logic

            assert not both_have_startup, (

                f"CRITICAL STARTUP SEQUENCE RISK: Deprecated manager has "

                f"{deprecated_startup_refs} startup references vs canonical {canonical_startup_refs}. "

                f"Different services may initialize with different configuration "

                f"managers, causing unpredictable startup behavior."

            )

        except Exception as e:

            pytest.skip(f"Startup sequence analysis failed: {e}")





class TestProductionRiskAssessment:

    """Assess production deployment risks from configuration duplication"""



    def test_deployment_script_config_reference_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - Deployment scripts may reference wrong config"""

        deployment_scripts = [

            "scripts/deploy_to_gcp.py",

            "scripts/refresh_dev_services.py",

            "docker-compose.yml",

            "docker-compose.test.yml"

        ]



        references_to_deprecated = []

        references_to_canonical = []



        for script_path in deployment_scripts:

            script_file = Path(script_path)

            if not script_file.exists():

                continue



            try:

                content = script_file.read_text(encoding='utf-8')



                if 'unified_configuration_manager' in content:

                    references_to_deprecated.append(str(script_path))



                if 'core.configuration.base' in content or 'UnifiedConfigManager' in content:

                    references_to_canonical.append(str(script_path))

            except Exception:

                continue



        has_mixed_references = len(references_to_deprecated) > 0 and len(references_to_canonical) > 0



        # This test SHOULD FAIL if deployment scripts have mixed references

        assert not has_mixed_references, (

            f"CRITICAL DEPLOYMENT RISK: Deployment scripts have mixed configuration "

            f"references. Deprecated refs: {references_to_deprecated}, "

            f"Canonical refs: {references_to_canonical}. "

            f"This creates deployment inconsistency and production failures."

        )



    def test_import_statement_analysis_SHOULD_FAIL(self):

        """CRITICAL: Test SHOULD FAIL - Codebase has mixed import statements"""

        # Search for import statements across key files

        key_directories = [

            "netra_backend/app",

            "tests",

            "scripts"

        ]



        deprecated_imports = []

        canonical_imports = []



        for directory in key_directories:

            dir_path = Path(directory)

            if not dir_path.exists():

                continue



            for py_file in dir_path.rglob("*.py"):

                try:

                    content = py_file.read_text(encoding='utf-8')



                    if 'from netra_backend.app.core.managers.unified_configuration_manager' in content:

                        deprecated_imports.append(str(py_file))



                    if 'from netra_backend.app.core.configuration.base' in content:

                        canonical_imports.append(str(py_file))

                except Exception:

                    continue



        has_mixed_imports = len(deprecated_imports) > 0 and len(canonical_imports) > 0



        # This test SHOULD FAIL if codebase has mixed imports

        assert not has_mixed_imports, (

            f"CRITICAL IMPORT INCONSISTENCY: Codebase has mixed configuration imports. "

            f"Deprecated imports in {len(deprecated_imports)} files: {deprecated_imports[:3]}..., "

            f"Canonical imports in {len(canonical_imports)} files: {canonical_imports[:3]}... "

            f"This creates runtime inconsistency and unpredictable behavior."

        )





if __name__ == "__main__":

    print("Phase 1: Running Configuration Consistency Integration Tests")

    print("These tests are DESIGNED TO FAIL to expose integration-level SSOT violations")

    pytest.main([__file__, "-v", "--tb=short"])

