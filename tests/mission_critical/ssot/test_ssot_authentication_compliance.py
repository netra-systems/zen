"""
P0 MISSION CRITICAL: Authentication SSOT Compliance Test

Business Impact: Prevents auth cascade failures affecting ALL users.
Authentication SSOT violations can cause:
- Complete login failures across the platform ($500K+ ARR impact)
- JWT validation inconsistencies leading to session chaos
- Security vulnerabilities from improper token handling
- Service boundary violations compromising system security

This test ensures ONLY the auth service handles JWT operations and prevents
the critical vulnerabilities that caused platform-wide outages.

SSOT Requirements:
- Auth service MUST be the ONLY source for JWT operations
- NO local JWT decoding/validation outside auth service
- ALL JWT operations must use canonical auth service endpoints
- NO duplicate auth implementations across services
"""

import ast
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


@pytest.mark.mission_critical
@pytest.mark.ssot
@pytest.mark.auth_ssot
class TestAuthenticationSSot(SSotBaseTestCase):
    """CRITICAL: Authentication SSOT compliance testing.
    
    Business Impact: Prevents auth cascade failures affecting all users.
    Violations in Auth SSOT can cause:
    - Complete login failures across the platform
    - JWT validation inconsistencies  
    - Security vulnerabilities from improper token handling
    - Session management chaos
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with auth patterns to detect."""
        super().setUpClass()
        
        # Define the canonical auth service paths
        cls.auth_service_paths = {
            "auth_service/auth_core/core/jwt_handler.py",
            "auth_service/auth_core/core/token_validator.py", 
            "auth_service/auth_core/core/session_manager.py",
            "auth_service/auth_core/services/auth_service.py",
            "auth_service/auth_core/unified_auth_interface.py"
        }
        
        # Define backend integration (ONLY allowed auth integration)
        cls.allowed_backend_auth_integration = {
            "netra_backend/app/auth_integration/auth.py",
            "netra_backend/app/clients/auth_client_core.py"
        }
        
        # Forbidden JWT patterns outside auth service
        cls.forbidden_jwt_patterns = [
            r'jwt\.decode\s*\(',
            r'PyJWT\.decode\s*\(',
            r'_try_local_jwt_validation',
            r'def\s+validate_jwt_token',
            r'def\s+decode_jwt',
            r'def\s+verify_jwt',
            r'class\s+\w*JWT\w*Handler',
            r'class\s+\w*JWT\w*Validator',
            r'class\s+\w*TokenValidator',
            r'jwt\.encode\s*\(',
            r'PyJWT\.encode\s*\(',
            r'create_jwt_token',
            r'generate_jwt'
        ]
        
        # Forbidden direct secret access patterns
        self.forbidden_secret_patterns = [
            r'JWT_SECRET[^_]',  # JWT_SECRET but not JWT_SECRET_KEY
            r'os\.environ\[[\'"](JWT_SECRET)[\'\"]\]',
            r'getenv\s*\(\s*[\'"](JWT_SECRET)[\'\"]\s*\)',
            r'secret\s*=\s*[\'"][^\'\"]*[\'\"]\s*#.*jwt',
            r'self\.jwt_secret\s*=',
            r'jwt_secret\s*=.*os\.environ'
        ]
        
        # Forbidden auth duplicate implementations
        self.forbidden_auth_duplicates = [
            r'class\s+.*SessionManager.*:',
            r'class\s+.*AuthManager.*:',
            r'class\s+.*AuthService.*:',
            r'def\s+authenticate_user',
            r'def\s+validate_session',
            r'def\s+create_session'
        ]
        
        # OAuth configuration violations
        self.oauth_config_violations = [
            r'GOOGLE_CLIENT_ID\s*=',
            r'GOOGLE_CLIENT_SECRET\s*=',
            r'OAUTH_REDIRECT_URI\s*=',
            r'oauth_client_id\s*=',
            r'oauth_client_secret\s*='
        ]

    def test_no_local_jwt_validation(self):
        """CRITICAL: Detect forbidden local JWT decoding attempts.
        
        Local JWT validation was a critical vulnerability that caused auth
        cascade failures. This test ensures ALL JWT operations go through
        the canonical auth service.
        """
        violations = []
        
        # Scan all Python files excluding auth service and allowed integration
        for file_path in self._get_python_files():
            if self._is_auth_service_file(file_path) or self._is_allowed_integration(file_path):
                continue
                
            # Also exclude test files that legitimately decode for verification
            if self._is_test_file_with_verification(file_path):
                continue
            
            violations.extend(self._scan_file_for_jwt_violations(file_path))
        
        if violations:
            violation_summary = self._format_violation_summary(violations)
            pytest.fail(
                f"CRITICAL AUTH SSOT VIOLATION: Local JWT validation detected!\n\n"
                f"Business Impact: These violations can cause platform-wide auth failures\n"
                f"affecting $500K+ ARR. Local JWT validation bypasses the canonical auth service,\n"
                f"leading to token validation inconsistencies and security vulnerabilities.\n\n"
                f"Violations Found ({len(violations)}):\n{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"1. Remove ALL local JWT decode operations\n"
                f"2. Use auth_client.validate_token_jwt() instead\n"
                f"3. Import from netra_backend.app.auth_integration.auth\n"
                f"4. Ensure all auth operations go through auth service\n\n"
                f"Example Fix:\n"
                f"  BEFORE: jwt.decode(token, secret, algorithms=['HS256'])\n"
                f"  AFTER:  await auth_client.validate_token_jwt(token)\n"
            )

    def test_auth_service_ssot_enforcement(self):
        """CRITICAL: Ensure all JWT operations use auth service SSOT.
        
        This test validates that the auth service is the single source of truth
        for all JWT operations and no duplicate implementations exist.
        """
        violations = []
        auth_service_violations = []
        
        # Check for auth logic outside service boundaries
        for file_path in self._get_python_files():
            if self._is_auth_service_file(file_path) or self._is_allowed_integration(file_path):
                continue
                
            # Scan for forbidden auth implementations
            violations.extend(self._scan_file_for_auth_logic_violations(file_path))
        
        # Check auth service itself for SSOT compliance
        for auth_file in self.auth_service_paths:
            full_path = self._get_full_path(auth_file)
            if full_path.exists():
                auth_service_violations.extend(self._validate_auth_service_ssot(full_path))
        
        all_violations = violations + auth_service_violations
        
        if all_violations:
            violation_summary = self._format_violation_summary(all_violations)
            pytest.fail(
                f"CRITICAL AUTH SERVICE SSOT VIOLATION!\n\n"
                f"Business Impact: Auth logic outside service boundaries creates\n"
                f"inconsistent authentication behavior, leading to cascade failures.\n\n"
                f"Violations Found ({len(all_violations)}):\n{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"1. Move all auth logic to auth service\n"
                f"2. Use auth service APIs for all auth operations\n"
                f"3. Remove duplicate auth implementations\n"
                f"4. Ensure service boundary respect\n"
            )

    def test_no_duplicate_auth_components(self):
        """CRITICAL: Detect duplicate session managers, token validators.
        
        Multiple auth components create inconsistent behavior and race conditions
        that have historically caused platform outages.
        """
        violations = []
        component_locations = {}
        
        for file_path in self._get_python_files():
            if self._is_auth_service_file(file_path):
                continue  # Auth service is allowed to have these components
                
            duplicates = self._scan_file_for_duplicate_auth_components(file_path)
            
            for duplicate in duplicates:
                component_type = duplicate['component_type']
                if component_type not in component_locations:
                    component_locations[component_type] = []
                component_locations[component_type].append(duplicate)
                violations.append(duplicate)
        
        if violations:
            violation_summary = self._format_duplicate_component_summary(component_locations)
            pytest.fail(
                f"CRITICAL DUPLICATE AUTH COMPONENTS DETECTED!\n\n"
                f"Business Impact: Multiple auth components create race conditions\n"
                f"and inconsistent behavior leading to platform outages.\n\n"
                f"Duplicate Components Found:\n{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"1. Remove all duplicate auth components\n"
                f"2. Use ONLY auth service components\n"
                f"3. Import auth functionality from canonical locations\n"
                f"4. Consolidate auth logic in auth service\n"
            )

    def test_auth_service_boundary_respect(self):
        """CRITICAL: Verify auth logic stays within service boundaries.
        
        Auth logic outside service boundaries violates microservice architecture
        and creates maintenance nightmares with security implications.
        """
        violations = []
        
        # Check for cross-service auth imports
        for file_path in self._get_python_files():
            if self._is_auth_service_file(file_path):
                continue
                
            violations.extend(self._scan_file_for_boundary_violations(file_path))
        
        if violations:
            violation_summary = self._format_violation_summary(violations)
            pytest.fail(
                f"CRITICAL AUTH SERVICE BOUNDARY VIOLATIONS!\n\n"
                f"Business Impact: Cross-service auth dependencies create tight\n"
                f"coupling, deployment failures, and security vulnerabilities.\n\n"
                f"Boundary Violations Found ({len(violations)}):\n{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"1. Remove direct auth service imports from other services\n"
                f"2. Use auth client API instead of internal auth imports\n"
                f"3. Respect microservice boundaries\n"
                f"4. Use HTTP/API communication between services\n"
            )

    def test_oauth_configuration_ssot(self):
        """CRITICAL: Validate OAuth ports and configuration SSOT.
        
        Duplicate OAuth configurations cause redirect failures and auth chaos
        across environments.
        """
        violations = []
        config_duplicates = {}
        
        for file_path in self._get_python_files():
            oauth_violations = self._scan_file_for_oauth_violations(file_path)
            
            for violation in oauth_violations:
                config_key = violation['config_key']
                if config_key not in config_duplicates:
                    config_duplicates[config_key] = []
                config_duplicates[config_key].append(violation)
                violations.append(violation)
        
        if violations:
            violation_summary = self._format_oauth_violation_summary(config_duplicates)
            pytest.fail(
                f"CRITICAL OAUTH CONFIGURATION SSOT VIOLATIONS!\n\n"
                f"Business Impact: Duplicate OAuth configs cause redirect failures,\n"
                f"inconsistent auth flows, and environment-specific outages.\n\n"
                f"OAuth Violations Found ({len(violations)}):\n{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"1. Centralize OAuth configuration in auth service\n"
                f"2. Remove duplicate OAuth config definitions\n"
                f"3. Use environment-specific configuration management\n"
                f"4. Ensure consistent OAuth ports (3000, 8000, 8001, 8081)\n"
            )

    def test_forbidden_jwt_secret_access(self):
        """CRITICAL: Detect direct JWT_SECRET access bypassing auth service.
        
        Direct secret access creates security vulnerabilities and bypasses
        the canonical secret management in auth service.
        """
        violations = []
        
        for file_path in self._get_python_files():
            if self._is_auth_service_file(file_path) or self._is_allowed_integration(file_path):
                continue
                
            violations.extend(self._scan_file_for_secret_violations(file_path))
        
        if violations:
            violation_summary = self._format_violation_summary(violations)
            pytest.fail(
                f"CRITICAL JWT SECRET ACCESS VIOLATIONS!\n\n"
                f"Business Impact: Direct secret access bypasses canonical secret\n"
                f"management, creates security vulnerabilities, and violates SSOT.\n\n"
                f"Secret Access Violations ({len(violations)}):\n{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"1. Remove all direct JWT_SECRET access\n"
                f"2. Use AuthConfig.get_jwt_secret() in auth service only\n"
                f"3. Access tokens through auth service API\n"
                f"4. Never hardcode or directly access JWT secrets\n"
            )

    # Helper Methods
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the codebase."""
        root_path = Path.cwd()
        python_files = []
        
        # Skip common non-source directories
        skip_dirs = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules', 
            'venv', '.env', 'backup', '.vscode', 'logs'
        }
        
        for file_path in root_path.rglob("*.py"):
            # Skip if any parent directory is in skip_dirs
            if any(part in skip_dirs for part in file_path.parts):
                continue
            python_files.append(file_path)
            
        return python_files

    def _is_auth_service_file(self, file_path: Path) -> bool:
        """Check if file is part of the canonical auth service."""
        file_str = str(file_path).replace('\\', '/')
        return any(auth_path in file_str for auth_path in self.auth_service_paths)

    def _is_allowed_integration(self, file_path: Path) -> bool:
        """Check if file is allowed backend auth integration."""
        file_str = str(file_path).replace('\\', '/')
        return any(allowed_path in file_str for allowed_path in self.allowed_backend_auth_integration)

    def _is_test_file_with_verification(self, file_path: Path) -> bool:
        """Check if this is a test file that legitimately needs to decode for verification."""
        file_str = str(file_path).replace('\\', '/')
        
        # Test files that need to decode for verification purposes
        if '/tests/' not in file_str and '/test_' not in file_str.split('/')[-1]:
            return False
            
        # These test patterns are allowed to decode for verification
        allowed_test_patterns = [
            'test_jwt_',
            'test_token_',
            'test_auth_',
            'jwt_test_utils.py',
            'token_factory.py',
            'auth_test_helper.py'
        ]
        
        return any(pattern in file_str for pattern in allowed_test_patterns)

    def _scan_file_for_jwt_violations(self, file_path: Path) -> List[Dict]:
        """Scan file for forbidden JWT operations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in self.forbidden_jwt_patterns:
                    if re.search(pattern, line):
                        # Skip commented lines
                        if line.strip().startswith('#'):
                            continue
                            
                        violations.append({
                            'type': 'forbidden_jwt_operation',
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'severity': 'CRITICAL'
                        })
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations

    def _scan_file_for_auth_logic_violations(self, file_path: Path) -> List[Dict]:
        """Scan file for forbidden auth logic outside service boundaries."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in self.forbidden_auth_duplicates:
                    if re.search(pattern, line):
                        # Skip commented lines and test files
                        if line.strip().startswith('#'):
                            continue
                            
                        violations.append({
                            'type': 'forbidden_auth_logic',
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'severity': 'HIGH'
                        })
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations

    def _scan_file_for_duplicate_auth_components(self, file_path: Path) -> List[Dict]:
        """Scan for duplicate auth components like SessionManager, TokenValidator."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST to find class definitions
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name.lower()
                        
                        # Check for auth-related class names
                        auth_components = [
                            'sessionmanager', 'authmanager', 'authservice',
                            'tokenvalidator', 'jwthandler', 'authhandler',
                            'oauthmanager', 'authclient'
                        ]
                        
                        for component in auth_components:
                            if component in class_name:
                                violations.append({
                                    'type': 'duplicate_auth_component',
                                    'component_type': component,
                                    'file': str(file_path),
                                    'line': node.lineno,
                                    'class_name': node.name,
                                    'severity': 'CRITICAL'
                                })
                                
            except SyntaxError:
                # If AST parsing fails, fall back to regex
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in self.forbidden_auth_duplicates:
                        if re.search(pattern, line) and not line.strip().startswith('#'):
                            violations.append({
                                'type': 'duplicate_auth_component',
                                'component_type': 'unknown',
                                'file': str(file_path),
                                'line': line_num,
                                'content': line.strip(),
                                'severity': 'HIGH'
                            })
                            
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations

    def _scan_file_for_boundary_violations(self, file_path: Path) -> List[Dict]:
        """Scan for service boundary violations (direct auth service imports)."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for direct auth service imports
            forbidden_imports = [
                r'from\s+auth_service\.auth_core\.core',
                r'import\s+auth_service\.auth_core',
                r'from\s+auth_service\.core',
                r'import\s+.*JWTHandler',
                r'import\s+.*TokenValidator'
            ]
            
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in forbidden_imports:
                    if re.search(pattern, line) and not line.strip().startswith('#'):
                        violations.append({
                            'type': 'service_boundary_violation',
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'severity': 'HIGH'
                        })
                        
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations

    def _scan_file_for_oauth_violations(self, file_path: Path) -> List[Dict]:
        """Scan for OAuth configuration SSOT violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in self.oauth_config_violations:
                    if re.search(pattern, line) and not line.strip().startswith('#'):
                        config_key = re.search(r'(\w+(?:_CLIENT_ID|_CLIENT_SECRET|_REDIRECT_URI))', line)
                        key_name = config_key.group(1) if config_key else 'unknown'
                        
                        violations.append({
                            'type': 'oauth_config_violation',
                            'config_key': key_name,
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'severity': 'HIGH'
                        })
                        
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations

    def _scan_file_for_secret_violations(self, file_path: Path) -> List[Dict]:
        """Scan for direct JWT secret access violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in self.forbidden_secret_patterns:
                    if re.search(pattern, line) and not line.strip().startswith('#'):
                        violations.append({
                            'type': 'forbidden_secret_access',
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'severity': 'CRITICAL'
                        })
                        
        except Exception as e:
            logger.warning(f"Error scanning {file_path}: {e}")
            
        return violations

    def _validate_auth_service_ssot(self, file_path: Path) -> List[Dict]:
        """Validate that auth service itself follows SSOT principles."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for proper SSOT patterns in auth service
            ssot_indicators = [
                'Single Source of Truth',
                'CANONICAL',
                'SSOT',
                'def validate_token'
            ]
            
            has_ssot_indicators = any(indicator in content for indicator in ssot_indicators)
            
            if not has_ssot_indicators:
                violations.append({
                    'type': 'auth_service_ssot_missing',
                    'file': str(file_path),
                    'line': 1,
                    'content': 'Missing SSOT documentation/patterns',
                    'severity': 'MEDIUM'
                })
                
        except Exception as e:
            logger.warning(f"Error validating auth service SSOT {file_path}: {e}")
            
        return violations

    def _get_full_path(self, relative_path: str) -> Path:
        """Convert relative path to full path."""
        return Path.cwd() / relative_path

    def _format_violation_summary(self, violations: List[Dict]) -> str:
        """Format violations into readable summary."""
        if not violations:
            return "No violations found."
            
        summary_lines = []
        for i, violation in enumerate(violations[:10], 1):  # Limit to first 10
            file_short = str(violation['file']).split('/')[-2:]  # Show last 2 dirs
            file_display = '/'.join(file_short) if len(file_short) == 2 else violation['file']
            
            summary_lines.append(
                f"  {i}. {violation['severity']}: {file_display}:{violation['line']}\n"
                f"     Pattern: {violation.get('pattern', 'N/A')}\n"
                f"     Code: {violation['content'][:100]}{'...' if len(violation['content']) > 100 else ''}"
            )
            
        if len(violations) > 10:
            summary_lines.append(f"  ... and {len(violations) - 10} more violations")
            
        return '\n'.join(summary_lines)

    def _format_duplicate_component_summary(self, component_locations: Dict) -> str:
        """Format duplicate components summary."""
        summary_lines = []
        for component_type, duplicates in component_locations.items():
            summary_lines.append(f"\n  {component_type.upper()}:")
            for dup in duplicates[:5]:  # Limit to 5 per component
                file_short = str(dup['file']).split('/')[-2:]
                file_display = '/'.join(file_short) if len(file_short) == 2 else dup['file']
                summary_lines.append(f"    - {file_display}:{dup['line']} ({dup.get('class_name', 'unknown')})")
                
        return '\n'.join(summary_lines)

    def _format_oauth_violation_summary(self, config_duplicates: Dict) -> str:
        """Format OAuth configuration violations summary."""
        summary_lines = []
        for config_key, violations in config_duplicates.items():
            summary_lines.append(f"\n  {config_key}:")
            for violation in violations[:3]:  # Limit to 3 per config
                file_short = str(violation['file']).split('/')[-2:]
                file_display = '/'.join(file_short) if len(file_short) == 2 else violation['file']
                summary_lines.append(f"    - {file_display}:{violation['line']}")
                
        return '\n'.join(summary_lines)