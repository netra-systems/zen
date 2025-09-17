"
SSOT Function Behavioral Consistency Tests for Issue #1076

Test Plan: Verify that SSOT functions behave consistently and don't have behavioral duplicates.
Should FAIL initially (detecting behavioral inconsistencies) and PASS after remediation.

Key violations to detect:
1. Functions with same name but different behavior across modules
2. SSOT functions that have non-SSOT alternatives still in use
3. Configuration functions returning different values
4. Auth functions with inconsistent validation logic

Related Issues: #1076 - SSOT compliance verification
Priority: CRITICAL - These tests ensure behavioral consistency in SSOT architecture
""

import pytest
from pathlib import Path
import sys
import importlib
import inspect
from typing import Dict, List, Any, Callable
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotBehavioralConsistencyTests(SSotBaseTestCase):
    ""Tests to detect SSOT behavioral consistency violations."

    @property
    def project_root(self):
        "Get project root path.""
        return Path(__file__).parent.parent.parent

    def test_logging_function_behavioral_consistency(self):
        ""
        CRITICAL: Ensure SSOT logging functions behave consistently.

        EXPECTED: Should FAIL initially - detects behavioral inconsistencies in logging
        REMEDIATION: Ensure all logging goes through unified SSOT logger
        "
        behavioral_violations = []

        try:
            # Test SSOT unified logging behavior
            from shared.logging.unified_logging_ssot import get_logger as ssot_get_logger

            # Test legacy logging behavior (if it still exists)
            try:
                from netra_backend.app.logging_config import central_logger
                legacy_exists = True
            except ImportError:
                legacy_exists = False

            if legacy_exists:
                # Both SSOT and legacy exist - this is a violation
                behavioral_violations.append({
                    'violation_type': 'dual_logging_systems',
                    'ssot_module': 'shared.logging.unified_logging_ssot',
                    'legacy_module': 'netra_backend.app.logging_config',
                    'reason': 'Both SSOT and legacy logging systems are available'
                }

                # Test if they behave differently
                ssot_logger = ssot_get_logger('test_module')
                legacy_logger = central_logger.get_logger('test_module')

                # Check if loggers have different class types
                if type(ssot_logger).__name__ != type(legacy_logger).__name__:
                    behavioral_violations.append({
                        'violation_type': 'logger_type_inconsistency',
                        'ssot_type': type(ssot_logger).__name__,
                        'legacy_type': type(legacy_logger).__name__,
                        'reason': 'SSOT and legacy loggers return different types'
                    }

            # Check for direct imports in production files
            production_files_with_legacy_logging = []
            search_paths = [
                self.project_root / "netra_backend / app",
                self.project_root / "auth_service,
                self.project_root / shared"
            ]

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                for py_file in search_path.rglob("*.py):
                    if py_file.name.startswith(__") or "test in py_file.name.lower():
                        continue

                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        if 'from netra_backend.app.logging_config import' in content:
                            production_files_with_legacy_logging.append(
                                str(py_file.relative_to(self.project_root))
                            )

                    except Exception:
                        continue

            if production_files_with_legacy_logging:
                behavioral_violations.append({
                    'violation_type': 'legacy_logging_in_production',
                    'files_count': len(production_files_with_legacy_logging),
                    'sample_files': production_files_with_legacy_logging[:5],
                    'reason': 'Production files still using legacy logging instead of SSOT'
                }

        except Exception as e:
            behavioral_violations.append({
                'violation_type': 'logging_import_error',
                'error': str(e),
                'reason': 'Could not import logging modules for behavioral testing'
            }

        # This test should FAIL initially if behavioral violations exist
        if behavioral_violations:
            violation_details = \n".join([
                f"  - {viol['violation_type']}: {viol['reason']}
                for viol in behavioral_violations
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(behavioral_violations)} logging behavioral inconsistencies:\n"
                f"{violation_details}\n\n
                fREMEDIATION REQUIRED:\n"
                f"1. Remove legacy logging module completely\n
                f2. Ensure all production code uses SSOT logging\n"
                f"3. Verify consistent logger behavior across codebase
            )

    def test_auth_function_behavioral_consistency(self):
        ""
        CRITICAL: Ensure auth functions behave consistently across SSOT and legacy systems.

        EXPECTED: Should FAIL initially - detects auth behavioral inconsistencies
        REMEDIATION: Remove legacy auth, ensure SSOT auth service is single source
        "
        auth_behavioral_violations = []

        try:
            # Check if both SSOT auth service and legacy auth integration exist
            ssot_auth_available = False
            legacy_auth_available = False

            try:
                from auth_service.auth_core.core.jwt_handler import JWTHandler
                ssot_auth_available = True
            except ImportError:
                pass

            try:
                from netra_backend.app.auth_integration.auth import validate_jwt_token
                legacy_auth_available = True
            except ImportError:
                pass

            if ssot_auth_available and legacy_auth_available:
                auth_behavioral_violations.append({
                    'violation_type': 'dual_auth_systems',
                    'ssot_module': 'auth_service.auth_core.core.jwt_handler',
                    'legacy_module': 'netra_backend.app.auth_integration.auth',
                    'reason': 'Both SSOT auth service and legacy auth integration are available'
                }

            # Check for files that import from auth_integration instead of auth_service
            files_using_legacy_auth = []
            search_paths = [
                self.project_root / "netra_backend / app" / "routes,
                self.project_root / netra_backend" / "app / middleware"
            ]

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                for py_file in search_path.rglob("*.py):
                    if py_file.name.startswith(__"):
                        continue

                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        if 'from netra_backend.app.auth_integration' in content:
                            files_using_legacy_auth.append(
                                str(py_file.relative_to(self.project_root))
                            )

                    except Exception:
                        continue

            if files_using_legacy_auth:
                auth_behavioral_violations.append({
                    'violation_type': 'legacy_auth_imports_in_routes',
                    'files_count': len(files_using_legacy_auth),
                    'sample_files': files_using_legacy_auth[:5],
                    'reason': 'Route/middleware files using legacy auth instead of SSOT auth service'
                }

        except Exception as e:
            auth_behavioral_violations.append({
                'violation_type': 'auth_import_error',
                'error': str(e),
                'reason': 'Could not import auth modules for behavioral testing'
            }

        # This test should FAIL initially if auth behavioral violations exist
        if auth_behavioral_violations:
            violation_details = "\n.join([
                f  - {viol['violation_type']}: {viol['reason']}"
                for viol in auth_behavioral_violations
            ]

            self.fail(
                f"SSOT VIOLATION: Found {len(auth_behavioral_violations)} auth behavioral inconsistencies:\n
                f{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n
                f1. Remove legacy auth integration module\n"
                f"2. Update all routes/middleware to use SSOT auth service\n
                f3. Ensure auth_service is the single source of truth for authentication"
            )

    def test_configuration_function_behavioral_consistency(self):
        "
        CRITICAL: Ensure configuration functions return consistent values.

        EXPECTED: Should FAIL initially - detects config behavioral inconsistencies
        REMEDIATION: Consolidate to SSOT configuration architecture
        ""
        config_behavioral_violations = []

        try:
            # Check for multiple configuration sources
            config_sources = []

            # Test SSOT configuration
            try:
                from netra_backend.app.core.configuration.base import ConfigurationManager
                config_sources.append('SSOT_config_manager')
            except ImportError:
                pass

            # Test legacy configuration
            try:
                from netra_backend.app.config import get_config
                config_sources.append('legacy_get_config')
            except ImportError:
                pass

            # Test isolated environment
            try:
                from dev_launcher.isolated_environment import IsolatedEnvironment
                config_sources.append('isolated_environment')
            except ImportError:
                pass

            if len(config_sources) > 1:
                config_behavioral_violations.append({
                    'violation_type': 'multiple_config_sources',
                    'sources': config_sources,
                    'count': len(config_sources),
                    'reason': 'Multiple configuration sources available instead of single SSOT'
                }

            # Check for direct os.environ usage in production files
            files_with_direct_env_access = []
            search_paths = [
                self.project_root / netra_backend" / "app,
                self.project_root / auth_service",
                self.project_root / "shared
            ]

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                for py_file in search_path.rglob(*.py"):
                    if (py_file.name.startswith("__) or
                        test" in py_file.name.lower() or
                        "isolated_environment in py_file.name):
                        continue

                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Check for direct environment access patterns
                        if any(pattern in content for pattern in [
                            'os.environ[', 'os.getenv(', 'import os'
                        ] and 'IsolatedEnvironment' not in content:
                            files_with_direct_env_access.append(
                                str(py_file.relative_to(self.project_root))
                            )

                    except Exception:
                        continue

            if files_with_direct_env_access:
                config_behavioral_violations.append({
                    'violation_type': 'direct_env_access_in_production',
                    'files_count': len(files_with_direct_env_access),
                    'sample_files': files_with_direct_env_access[:5],
                    'reason': 'Production files using direct environment access instead of SSOT patterns'
                }

        except Exception as e:
            config_behavioral_violations.append({
                'violation_type': 'config_import_error',
                'error': str(e),
                'reason': 'Could not import configuration modules for behavioral testing'
            }

        # This test should FAIL initially if config behavioral violations exist
        if config_behavioral_violations:
            violation_details = \n".join([
                f"  - {viol['violation_type']}: {viol['reason']}
                for viol in config_behavioral_violations
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(config_behavioral_violations)} configuration behavioral inconsistencies:\n"
                f"{violation_details}\n\n
                fREMEDIATION REQUIRED:\n"
                f"1. Consolidate to single SSOT configuration source\n
                f2. Replace direct environment access with IsolatedEnvironment\n"
                f"3. Ensure consistent configuration behavior across services
            )

    def test_websocket_function_behavioral_consistency(self):
        ""
        CRITICAL: Ensure WebSocket functions behave consistently.

        EXPECTED: Should FAIL initially - detects WebSocket behavioral inconsistencies
        REMEDIATION: Ensure SSOT WebSocket manager is single source
        "
        websocket_behavioral_violations = []

        try:
            # Check for multiple WebSocket manager implementations
            websocket_managers = []

            # Test SSOT WebSocket manager
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                websocket_managers.append('SSOT_websocket_manager')
            except ImportError:
                pass

            # Check for legacy WebSocket implementations
            try:
                from netra_backend.app.websocket_core.manager import WebSocketCoreManager
                websocket_managers.append('websocket_core_manager')
            except ImportError:
                pass

            # Check for files that might have duplicate WebSocket functionality
            files_with_websocket_implementations = []
            search_paths = [
                self.project_root / "netra_backend / app"
            ]

            websocket_implementation_patterns = [
                'class WebSocketManager',
                'class WebSocket',
                'def websocket_endpoint',
                'def handle_websocket',
                'async def websocket_handler'
            ]

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                for py_file in search_path.rglob("*.py):
                    if py_file.name.startswith(__") or "test in py_file.name.lower():
                        continue

                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for pattern in websocket_implementation_patterns:
                            if pattern in content:
                                files_with_websocket_implementations.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'pattern': pattern
                                }

                    except Exception:
                        continue

            # Check for multiple WebSocket handler implementations
            websocket_files = [f['file'] for f in files_with_websocket_implementations]
            unique_websocket_files = list(set(websocket_files))

            if len(unique_websocket_files) > 3:  # Allow core manager files
                websocket_behavioral_violations.append({
                    'violation_type': 'multiple_websocket_implementations',
                    'files_count': len(unique_websocket_files),
                    'files': unique_websocket_files[:5],
                    'reason': 'Multiple files implementing WebSocket functionality instead of using SSOT'
                }

            # Check for inconsistent WebSocket event patterns
            event_emission_patterns = []
            for search_path in search_paths:
                if not search_path.exists():
                    continue

                for py_file in search_path.rglob(*.py"):
                    if py_file.name.startswith("__) or test" in py_file.name.lower():
                        continue

                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for different event emission patterns
                        if 'emit(' in content and 'websocket' in content.lower():
                            event_emission_patterns.append(
                                str(py_file.relative_to(self.project_root))
                            )

                    except Exception:
                        continue

            if len(event_emission_patterns) > 2:  # Allow some core files
                websocket_behavioral_violations.append({
                    'violation_type': 'inconsistent_event_emission',
                    'files_count': len(event_emission_patterns),
                    'sample_files': event_emission_patterns[:3],
                    'reason': 'Multiple files implementing event emission instead of using SSOT WebSocket manager'
                }

        except Exception as e:
            websocket_behavioral_violations.append({
                'violation_type': 'websocket_import_error',
                'error': str(e),
                'reason': 'Could not import WebSocket modules for behavioral testing'
            }

        # This test should FAIL initially if WebSocket behavioral violations exist
        if websocket_behavioral_violations:
            violation_details = "\n.join([
                f  - {viol['violation_type']}: {viol['reason']}"
                for viol in websocket_behavioral_violations
            ]

            self.fail(
                f"SSOT VIOLATION: Found {len(websocket_behavioral_violations)} WebSocket behavioral inconsistencies:\n
                f{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n
                f1. Consolidate WebSocket functionality to SSOT WebSocket manager\n"
                f"2. Remove duplicate WebSocket implementations\n
                f3. Ensure consistent event emission patterns through SSOT manager"
            )

    def test_database_function_behavioral_consistency(self):
        "
        CRITICAL: Ensure database functions behave consistently.

        EXPECTED: Should FAIL initially - detects database behavioral inconsistencies
        REMEDIATION: Ensure SSOT database patterns are consistently used
        ""
        db_behavioral_violations = []

        try:
            # Check for multiple database connection patterns
            db_connection_files = []
            search_paths = [
                self.project_root / netra_backend" / "app,
                self.project_root / auth_service"
            ]

            db_connection_patterns = [
                'get_database_url',
                'create_connection',
                'connect_to_database',
                'DatabaseManager(',
                'get_db_connection'
            ]

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                for py_file in search_path.rglob("*.py):
                    if py_file.name.startswith(__") or "test in py_file.name.lower():
                        continue

                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for pattern in db_connection_patterns:
                            if pattern in content:
                                db_connection_files.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'pattern': pattern
                                }

                    except Exception:
                        continue

            # Check for files implementing their own database logic
            unique_db_files = list(set([f['file'] for f in db_connection_files])

            # Filter out expected SSOT database files
            expected_db_files = [
                'netra_backend/app/db/database_manager.py',
                'netra_backend/app/db/postgres.py',
                'netra_backend/app/db/clickhouse.py'
            ]

            unexpected_db_files = [f for f in unique_db_files if f not in expected_db_files]

            if len(unexpected_db_files) > 5:  # Allow some configuration files
                db_behavioral_violations.append({
                    'violation_type': 'multiple_db_implementations',
                    'files_count': len(unexpected_db_files),
                    'sample_files': unexpected_db_files[:5],
                    'reason': 'Multiple files implementing database logic instead of using SSOT database manager'
                }

        except Exception as e:
            db_behavioral_violations.append({
                'violation_type': 'database_import_error',
                'error': str(e),
                'reason': 'Could not analyze database modules for behavioral testing'
            }

        # This test should FAIL initially if database behavioral violations exist
        if db_behavioral_violations:
            violation_details = \n".join([
                f"  - {viol['violation_type']}: {viol['reason']}
                for viol in db_behavioral_violations
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(db_behavioral_violations)} database behavioral inconsistencies:\n"
                f"{violation_details}\n\n
                fREMEDIATION REQUIRED:\n"
                f"1. Consolidate database logic to SSOT database manager\n
                f2. Remove duplicate database connection implementations\n"
                f"3. Ensure consistent database access patterns"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])