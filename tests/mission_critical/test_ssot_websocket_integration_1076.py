"""
"""
SSOT WebSocket Integration Tests for Issue #1076

Test Plan: Verify WebSocket integration follows SSOT patterns and golden path works.
Should FAIL initially (detecting integration violations) and PASS after remediation.

Key violations to detect:
"""
"""
1. WebSocket manager imports not using SSOT patterns
2. Agent execution not properly integrated with SSOT WebSocket events
3. Auth integration in WebSocket not using SSOT auth service
4. Configuration access in WebSocket not using SSOT patterns

Related Issues: #1076 - SSOT compliance verification
Priority: CRITICAL - WebSocket is 90% of business value through chat functionality
"
"

import pytest
from pathlib import Path
import sys
import asyncio
from typing import Dict, List, Any
import importlib

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotWebSocketIntegrationTests(SSotBaseTestCase):
    "Tests to detect WebSocket SSOT integration violations."

    @property
    def project_root(self):
        "Get project root path."
        return Path(__file__).parent.parent.parent

    def test_websocket_manager_ssot_import_compliance(self):
        """
        "
        CRITICAL: Ensure WebSocket manager imports follow SSOT patterns.

        EXPECTED: Should FAIL initially - detects non-SSOT WebSocket imports
        REMEDIATION: Update all imports to use SSOT WebSocket manager
"
"
        websocket_import_violations = []

        # Check all files that import WebSocket functionality
        search_paths = [
            self.project_root / netra_backend / app" / routes,"
            self.project_root / netra_backend / app / agents","
            self.project_root / netra_backend / app / middleware,"
            self.project_root / netra_backend / app / middleware,"
            self.project_root / netra_backend" / app / tools"
        ]

        # Expected SSOT WebSocket import patterns
        expected_ssot_imports = [
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager,"
            from netra_backend.app.websocket_core.websocket_manager import,
        ]

        # Deprecated WebSocket import patterns
        deprecated_imports = [
            from netra_backend.app.websocket_core.manager import,"
            from netra_backend.app.websocket_core.manager import,"
            from netra_backend.app.websocket import","
            from websocket_manager import,
            import websocket_manager""
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob(*.py):
                if py_file.name.startswith(__) or "test in py_file.name.lower():"
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for deprecated WebSocket imports
                    for deprecated_import in deprecated_imports:
                        if deprecated_import in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if deprecated_import in line:
                                    websocket_import_violations.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'deprecated_import': deprecated_import,
                                        'content': line.strip(),
                                        'violation_type': 'deprecated_websocket_import'
                                    }

                    # Check if file uses WebSocket but doesn't use SSOT imports'
                    if ('websocket' in content.lower() or 'WebSocket' in content) and content.strip():
                        uses_ssot_import = any(ssot_import in content for ssot_import in expected_ssot_imports)
                        uses_deprecated_import = any(dep_import in content for dep_import in deprecated_imports)

                        if uses_deprecated_import and not uses_ssot_import:
                            websocket_import_violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': 1,
                                'deprecated_import': 'mixed_imports',
                                'content': 'File uses deprecated WebSocket imports without SSOT imports',
                                'violation_type': 'missing_ssot_websocket_import'
                            }

                except Exception as e:
                    continue

        # This test should FAIL initially if deprecated WebSocket imports exist
        if websocket_import_violations:
            violation_details = \n".join(["
                f  - {viol['file']}:{viol['line']} - {viol['content']}
                for viol in websocket_import_violations[:15]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(websocket_import_violations)} WebSocket import violations:\n"
                fSSOT VIOLATION: Found {len(websocket_import_violations)} WebSocket import violations:\n"
                f"{violation_details}\n"
                f{'... and more' if len(websocket_import_violations) > 15 else ''}\n\n
                fREMEDIATION REQUIRED:\n
                f1. Replace deprecated WebSocket imports with SSOT patterns\n""
                f2. Use 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'\n
                f3. Remove all references to deprecated websocket_core.manager
            )

    def test_websocket_auth_integration_ssot_compliance(self):
    """
        CRITICAL: Ensure WebSocket auth integration uses SSOT auth service.

        EXPECTED: Should FAIL initially - detects non-SSOT auth in WebSocket
        REMEDIATION: Update WebSocket auth to use SSOT auth service directly
        
        websocket_auth_violations = []

        # Check WebSocket files for auth integration patterns
        websocket_files = [
            self.project_root / netra_backend" / app / routes / websocket.py,"
            self.project_root / netra_backend / "app / routes / websocket_ssot.py,"
            self.project_root / netra_backend / app / websocket_core" / websocket_manager.py,"
            self.project_root / netra_backend / app / websocket_core / "auth.py"
        ]

        # Expected SSOT auth patterns
        expected_auth_imports = [
            from auth_service.auth_core.core.jwt_handler import","
            from auth_service.auth_core.core.token_validator import,
            from auth_service.auth_core.core.session_manager import""
        ]

        # Deprecated auth patterns in WebSocket
        deprecated_auth_patterns = [
            from netra_backend.app.auth_integration.auth import,
            from netra_backend.app.auth_integration import,"
            from netra_backend.app.auth_integration import,"
            "_validate_token_with_auth_service,  # Wrapper function"
            validate_jwt_token  # Legacy function
        ]

        for ws_file in websocket_files:
            if not ws_file.exists():
                continue

            try:
                with open(ws_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for deprecated auth patterns
                for deprecated_pattern in deprecated_auth_patterns:
                    if deprecated_pattern in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if deprecated_pattern in line:
                                websocket_auth_violations.append({
                                    'file': str(ws_file.relative_to(self.project_root)),
                                    'line': i,
                                    'pattern': deprecated_pattern,
                                    'content': line.strip(),
                                    'violation_type': 'deprecated_auth_in_websocket'
                                }

                # Check if WebSocket file does auth but doesn't use SSOT auth service'
                if any(auth_term in content for auth_term in ['token', 'auth', 'jwt', 'validate'] and content.strip():
                    uses_ssot_auth = any(ssot_auth in content for ssot_auth in expected_auth_imports)
                    uses_deprecated_auth = any(dep_auth in content for dep_auth in deprecated_auth_patterns)

                    if uses_deprecated_auth and not uses_ssot_auth:
                        websocket_auth_violations.append({
                            'file': str(ws_file.relative_to(self.project_root)),
                            'line': 1,
                            'pattern': 'mixed_auth_patterns',
                            'content': 'WebSocket file uses deprecated auth without SSOT auth service',
                            'violation_type': 'missing_ssot_auth_in_websocket'
                        }

            except Exception as e:
                continue

        # This test should FAIL initially if WebSocket auth violations exist
        if websocket_auth_violations:
            violation_details = "\n.join(["
                f  - {viol['file']}:{viol['line']} - {viol['content']}
                for viol in websocket_auth_violations[:10]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(websocket_auth_violations)} WebSocket auth integration violations:\n
                f{violation_details}\n""
                f{'... and more' if len(websocket_auth_violations) > 10 else ''}\n\n
                fREMEDIATION REQUIRED:\n
                f"1. Replace WebSocket auth integration with SSOT auth service\n"
                f2. Use direct auth_service imports in WebSocket code\n"
                f2. Use direct auth_service imports in WebSocket code\n"
                f3. Remove auth_integration wrapper functions from WebSocket
            )

    def test_websocket_configuration_ssot_compliance(self):
        """
        "
        CRITICAL: Ensure WebSocket configuration uses SSOT patterns.

        EXPECTED: Should FAIL initially - detects non-SSOT config in WebSocket
        REMEDIATION: Update WebSocket config to use SSOT configuration
"
"
        websocket_config_violations = []

        # Check WebSocket files for configuration patterns
        websocket_files = [
            self.project_root / netra_backend / app" / routes / websocket.py,"
            self.project_root / netra_backend / app / "routes / websocket_ssot.py,"
            self.project_root / netra_backend / app / websocket_core / websocket_manager.py","
            self.project_root / "netra_backend / app / websocket_core / auth.py"
        ]

        # Expected SSOT configuration patterns
        expected_config_imports = [
            "from netra_backend.app.core.configuration,"
            from dev_launcher.isolated_environment import IsolatedEnvironment,
            from shared.logging.unified_logging_ssot import get_logger"
            from shared.logging.unified_logging_ssot import get_logger"
        ]

        # Deprecated configuration patterns in WebSocket
        deprecated_config_patterns = [
            os.environ[","
            os.getenv(,
            from netra_backend.app.config import","
            from netra_backend.app.logging_config import
        ]

        for ws_file in websocket_files:
            if not ws_file.exists():
                continue

            try:
                with open(ws_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for deprecated config patterns
                for deprecated_pattern in deprecated_config_patterns:
                    if deprecated_pattern in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if deprecated_pattern in line and not line.strip().startswith('#'):
                                websocket_config_violations.append({
                                    'file': str(ws_file.relative_to(self.project_root)),
                                    'line': i,
                                    'pattern': deprecated_pattern,
                                    'content': line.strip(),
                                    'violation_type': 'deprecated_config_in_websocket'
                                }

            except Exception as e:
                continue

        # This test should FAIL initially if WebSocket config violations exist
        if websocket_config_violations:
            violation_details = \n.join(["
            violation_details = \n.join(["
                f"  - {viol['file']}:{viol['line']} - {viol['content']}"
                for viol in websocket_config_violations[:10]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(websocket_config_violations)} WebSocket configuration violations:\n
                f{violation_details}\n
                f{'... and more' if len(websocket_config_violations) > 10 else ''}\n\n""
                fREMEDIATION REQUIRED:\n
                f1. Replace direct environment access with IsolatedEnvironment\n
                f"2. Use SSOT configuration modules in WebSocket code\n"
                f3. Replace legacy logging with SSOT logging in WebSocket"
                f3. Replace legacy logging with SSOT logging in WebSocket"
            )

    def test_websocket_agent_event_integration_ssot_compliance(self):
        """
    "
        CRITICAL: Ensure agent-WebSocket event integration follows SSOT patterns.

        EXPECTED: Should FAIL initially - detects non-SSOT agent-WebSocket integration
        REMEDIATION: Ensure agents use SSOT WebSocket manager for events
        "
        "
        agent_websocket_violations = []

        # Check agent files for WebSocket event integration
        agent_files = [
            self.project_root / netra_backend / app / agents" / supervisor,"
            self.project_backend / app / agents / registry.py,"
            self.project_backend / app / agents / registry.py,"
            self.project_root / "netra_backend / app / tools"
        ]

        # Expected SSOT WebSocket event patterns
        expected_event_patterns = [
            websocket_manager.emit(","
            WebSocketManager,
            websocket_notifier.notify("
            websocket_notifier.notify("
        ]

        # Deprecated agent-WebSocket integration patterns
        deprecated_event_patterns = [
            "websocket.emit(,  # Direct websocket usage"
            emit_websocket_event(,  # Custom wrapper
            "send_websocket_message(,  # Legacy function"
            websocket_emit(  # Non-SSOT function
        ]

        for agent_path in agent_files:
            if not agent_path.exists():
                continue

            if agent_path.is_file():
                files_to_check = [agent_path]
            else:
                files_to_check = list(agent_path.rglob(*.py))"
                files_to_check = list(agent_path.rglob(*.py))"

            for agent_file in files_to_check:
                if agent_file.name.startswith(__") or test in agent_file.name.lower():"
                    continue

                try:
                    with open(agent_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for deprecated event patterns
                    for deprecated_pattern in deprecated_event_patterns:
                        if deprecated_pattern in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if deprecated_pattern in line:
                                    agent_websocket_violations.append({
                                        'file': str(agent_file.relative_to(self.project_root)),
                                        'line': i,
                                        'pattern': deprecated_pattern,
                                        'content': line.strip(),
                                        'violation_type': 'deprecated_websocket_event_in_agent'
                                    }

                    # Check if agent emits events but doesn't use SSOT WebSocket manager'
                    if any(event_term in content for event_term in ['emit', 'send', 'notify', 'websocket'] and content.strip():
                        uses_ssot_websocket = any(ssot_pattern in content for ssot_pattern in expected_event_patterns)
                        uses_deprecated_websocket = any(dep_pattern in content for dep_pattern in deprecated_event_patterns)

                        if uses_deprecated_websocket and not uses_ssot_websocket:
                            agent_websocket_violations.append({
                                'file': str(agent_file.relative_to(self.project_root)),
                                'line': 1,
                                'pattern': 'missing_ssot_websocket',
                                'content': 'Agent emits events without using SSOT WebSocket manager',
                                'violation_type': 'missing_ssot_websocket_in_agent'
                            }

                except Exception as e:
                    continue

        # This test should FAIL initially if agent-WebSocket violations exist
        if agent_websocket_violations:
            violation_details = \n.join([
                f"  - {viol['file']}:{viol['line']} - {viol['content']}"
                for viol in agent_websocket_violations[:10]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(agent_websocket_violations)} agent-WebSocket integration violations:\n"
                fSSOT VIOLATION: Found {len(agent_websocket_violations)} agent-WebSocket integration violations:\n"
                f{violation_details}\n
                f{'... and more' if len(agent_websocket_violations) > 10 else ''}\n\n"
                f{'... and more' if len(agent_websocket_violations) > 10 else ''}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f1. Ensure agents use SSOT WebSocket manager for event emission\n
                f2. Remove custom WebSocket wrapper functions from agents\n
                f3. Use WebSocketManager.emit() consistently across all agents""
            )

    def test_websocket_golden_path_ssot_integration(self):
        pass
        CRITICAL: Ensure WebSocket golden path integration follows SSOT patterns.

        EXPECTED: Should FAIL initially - detects golden path SSOT violations
        REMEDIATION: Ensure complete golden path uses SSOT patterns consistently
        ""
        golden_path_violations = []

        # Key files in the WebSocket golden path
        golden_path_files = [
            self.project_root / netra_backend / app / routes / "websocket.py,"
            self.project_root / netra_backend" / app / websocket_core / websocket_manager.py,"
            self.project_root / netra_backend" / "app / agents / supervisor / execution_engine.py,"
            self.project_root / netra_backend" / "app / agents / supervisor / execution_engine.py,"
            self.project_root / "netra_backend / app / tools / enhanced_dispatcher.py"
        ]

        # SSOT compliance requirements for golden path
        ssot_requirements = {
            'websocket_manager': [
                'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
                'WebSocketManager'
            ],
            'ssot_logging': [
                'from shared.logging.unified_logging_ssot import get_logger',
                'get_logger('
            ],
            'ssot_auth': [
                'from auth_service.auth_core.core',
                'auth_service'
            ],
            'ssot_config': [
                'from netra_backend.app.core.configuration',
                'IsolatedEnvironment'
            ]
        }

        for gp_file in golden_path_files:
            if not gp_file.exists():
                golden_path_violations.append({
                    'file': str(gp_file.relative_to(self.project_root)),
                    'line': 1,
                    'requirement': 'file_existence',
                    'content': 'Golden path file does not exist',
                    'violation_type': 'missing_golden_path_file'
                }
                continue

            try:
                with open(gp_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check each SSOT requirement
                for requirement_name, requirement_patterns in ssot_requirements.items():
                    # If file deals with this area, it should use SSOT patterns
                    area_keywords = {
                        'websocket_manager': ['websocket', 'WebSocket', 'emit', 'connect'],
                        'ssot_logging': ['logger', 'log', 'debug', 'info', 'error'],
                        'ssot_auth': ['auth', 'token', 'jwt', 'validate'],
                        'ssot_config': ['config', 'environ', 'setting']
                    }

                    keywords = area_keywords[requirement_name]
                    if any(keyword in content for keyword in keywords):
                        # File deals with this area - check if it uses SSOT patterns
                        uses_ssot = any(pattern in content for pattern in requirement_patterns)

                        if not uses_ssot:
                            golden_path_violations.append({
                                'file': str(gp_file.relative_to(self.project_root)),
                                'line': 1,
                                'requirement': requirement_name,
                                'content': f'Golden path file handles {requirement_name} without SSOT patterns',
                                'violation_type': f'missing_ssot_{requirement_name}_in_golden_path'
                            }

            except Exception as e:
                golden_path_violations.append({
                    'file': str(gp_file.relative_to(self.project_root)),
                    'line': 1,
                    'requirement': 'file_read_error',
                    'content': f'Could not read golden path file: {str(e)}',
                    'violation_type': 'golden_path_file_read_error'
                }

        # This test should FAIL initially if golden path SSOT violations exist
        if golden_path_violations:
            violation_details = "\n.join(["
                f  - {viol['file']} - {viol['requirement']}: {viol['content']}
                for viol in golden_path_violations[:10]  # Limit output
            ]

            self.fail(
                fSSOT VIOLATION: Found {len(golden_path_violations)} golden path SSOT violations:\n
                f{violation_details}\n""
                f{'... and more' if len(golden_path_violations) > 10 else ''}\n\n
                fREMEDIATION REQUIRED:\n
                f"1. Ensure all golden path files use SSOT patterns consistently\n"
                f2. Update WebSocket manager to use SSOT imports\n"
                f2. Update WebSocket manager to use SSOT imports\n"
                f3. Ensure agents and tools use SSOT WebSocket, auth, config, and logging\n
                f4. Verify complete golden path workflow uses SSOT architecture"
                f4. Verify complete golden path workflow uses SSOT architecture"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v')
))))))))))))))))))))))))))))
]]