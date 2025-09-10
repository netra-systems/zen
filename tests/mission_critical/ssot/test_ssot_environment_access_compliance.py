"""
P0 MISSION CRITICAL: Environment Access SSOT Compliance Test

Business Impact: Prevents configuration cascade failures affecting ALL platform operations.
Environment access SSOT violations can cause:
- Complete platform startup failures ($500K+ ARR impact)
- Service configuration mismatches leading to cross-service failures
- Environment-specific bugs that are impossible to reproduce consistently
- Production outages from configuration drift and cascade failures
- Silent failures where services fail to start properly in different environments

This test ensures ALL environment variable access goes through the canonical
IsolatedEnvironment pattern, preventing the critical configuration failures
that can bring down the entire platform.

SSOT Requirements:
- ALL environment access MUST use shared.isolated_environment.IsolatedEnvironment
- NO direct os.environ or os.getenv access bypassing isolation
- NO hardcoded environment values (URLs, secrets, database connections)
- Service-specific configuration through canonical config modules only
- NO cross-service environment variable access
"""

import ast
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


@pytest.mark.mission_critical
@pytest.mark.ssot
@pytest.mark.config
class TestEnvironmentAccessSSot(SSotBaseTestCase):
    """CRITICAL: Environment Access SSOT compliance testing.
    
    Business Impact: Prevents configuration cascade failures.
    Violations in Environment SSOT can cause:
    - Complete platform startup failures
    - Service configuration mismatches
    - Environment-specific bugs that are hard to reproduce
    - Production outages from configuration drift
    - Silent service failures due to missing environment variables
    """
    
    def setup_method(self, method=None):
        """Set up test with environment access patterns to detect."""
        super().setup_method(method)
        
        # Define canonical environment access patterns (ALLOWED)
        self.canonical_environment_imports = {
            "from shared.isolated_environment import IsolatedEnvironment",
            "from shared.isolated_environment import get_env",
            "from shared.isolated_environment import IsolatedEnvironment, get_env",
        }
        
        # Define service-specific canonical config paths (ALLOWED)
        self.canonical_config_paths = {
            "netra_backend/app/config.py",
            "netra_backend/app/core/configuration/base.py",
            "netra_backend/app/core/configuration/database.py", 
            "netra_backend/app/core/configuration/services.py",
            "netra_backend/app/core/configuration/secrets.py",
            "auth_service/auth_core/config.py",
            "analytics_service/analytics_core/config.py",
            "shared/cors_config.py",
            "dev_launcher/isolated_environment.py"  # Legacy exception during transition
        }
        
        # Forbidden direct environment access patterns
        self.forbidden_environment_patterns = [
            # Direct os.environ access
            r'os\.environ\[[\'"]\w+[\'"]\]',
            r'os\.environ\.get\s*\(',
            r'os\.getenv\s*\(',
            r'environ\.get\s*\(',
            r'environ\[[\'"]\w+[\'"]\]',
            
            # Environment variable assignment
            r'os\.environ\[[\'"]\w+[\'"]\]\s*=',
            r'environ\[[\'"]\w+[\'"]\]\s*=',
            
            # Common environment access without IsolatedEnvironment
            r'DATABASE_URL\s*=\s*os\.',
            r'REDIS_URL\s*=\s*os\.',
            r'JWT_SECRET\s*=\s*os\.',
            r'API_KEY\s*=\s*os\.',
        ]
        
        # Hardcoded configuration patterns (should use config instead)
        self.hardcoded_config_patterns = [
            # URLs
            r'https?://[a-zA-Z0-9.-]+\.(com|org|net|io|dev|local):[0-9]+',
            r'https?://[a-zA-Z0-9.-]+\.(com|org|net|io|dev|local)/',
            r'"https?://localhost:\d+"',
            r"'https?://localhost:\d+'",
            
            # Database connections  
            r'postgresql://[^"\']+',
            r'redis://[^"\']+',
            r'clickhouse://[^"\']+',
            
            # API keys and secrets (patterns that look like hardcoded secrets)
            r'["\'][A-Za-z0-9+/]{32,}={0,2}["\']',  # Base64-like strings
            r'["\'][a-f0-9]{32,64}["\']',  # Hex strings that could be tokens
            
            # Port hardcoding outside configuration
            r':8000[^0-9]',  # Backend port
            r':8001[^0-9]',  # Auth service port  
            r':8002[^0-9]',  # Analytics service port
            r':3000[^0-9]',  # Frontend port
            r':5432[^0-9]',  # PostgreSQL port
            r':6379[^0-9]',  # Redis port
            r':8123[^0-9]',  # ClickHouse port
        ]
        
        # Service boundary patterns (cross-service environment access)
        self.service_boundaries = {
            "netra_backend": ["AUTH_SERVICE_", "ANALYTICS_SERVICE_"],
            "auth_service": ["BACKEND_", "ANALYTICS_SERVICE_"], 
            "analytics_service": ["BACKEND_", "AUTH_SERVICE_"],
        }
        
        # Files that are exceptions (allowed limited violations)
        self.exception_files = {
            # Test files that legitimately test environment behavior
            "test_environment_",
            "test_isolated_environment",
            "test_configuration_",
            
            # Development and testing utilities
            "dev_launcher/",
            "test_framework/",
            "scripts/",
            ".github/",
            
            # Legacy files during migration (should be monitored)
            "backup/",
            ".git/",
        }

    def test_no_direct_os_environ_access(self):
        """CRITICAL: Detect direct os.environ access bypassing IsolatedEnvironment.
        
        Business Impact: Direct os.environ access bypasses the isolation layer
        and can cause configuration cascade failures in multi-environment setups.
        """
        violations = []
        
        for file_path in self._get_python_files():
            if self._is_exception_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for direct os.environ patterns
                for pattern in self.forbidden_environment_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'pattern': pattern,
                            'code': match.group(),
                            'severity': 'CRITICAL',
                            'business_impact': 'Can cause configuration cascade failures'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        if violations:
            violation_summary = self._format_environment_violations(violations)
            pytest.fail(
                f"CRITICAL: Found {len(violations)} direct os.environ access violations.\n"
                f"These bypass IsolatedEnvironment and can cause cascade failures.\n\n"
                f"{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"Replace with: from shared.isolated_environment import get_env\n"
                f"Then use: env = get_env(); value = env.get('VAR_NAME')\n\n"
                f"Business Impact: Configuration cascade failures can bring down entire platform"
            )

    def test_canonical_environment_access_patterns(self):
        """CRITICAL: Ensure all environment access uses IsolatedEnvironment.
        
        Business Impact: Non-canonical environment access patterns can cause
        inconsistent behavior across environments and testing scenarios.
        """
        files_with_env_access = []
        files_with_canonical_imports = []
        
        for file_path in self._get_python_files():
            if self._is_exception_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check if file has any environment access
                has_env_access = (
                    'os.environ' in content or 
                    'os.getenv' in content or
                    'environ.get' in content or
                    'environment' in content.lower()
                )
                
                if has_env_access:
                    files_with_env_access.append(str(file_path))
                    
                # Check if file has canonical imports
                has_canonical_import = any(
                    canonical_import in content 
                    for canonical_import in self.canonical_environment_imports
                )
                
                if has_canonical_import:
                    files_with_canonical_imports.append(str(file_path))
                    
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        # Files with environment access should use canonical imports
        non_canonical_files = set(files_with_env_access) - set(files_with_canonical_imports)
        
        if non_canonical_files:
            pytest.fail(
                f"CRITICAL: Found {len(non_canonical_files)} files with environment access "
                f"but no canonical IsolatedEnvironment imports.\n\n"
                f"Non-canonical files:\n" + 
                "\n".join(f"  - {f}" for f in sorted(non_canonical_files)[:10]) +
                f"\n\nREMEDIATION:\n"
                f"Add: from shared.isolated_environment import get_env\n"
                f"Use: env = get_env(); value = env.get('VAR_NAME')\n\n"
                f"Business Impact: Inconsistent environment handling causes unpredictable failures"
            )

    def test_no_environment_variable_hardcoding(self):
        """CRITICAL: Detect hardcoded environment values.
        
        Business Impact: Hardcoded configuration prevents proper environment
        isolation and causes failures when deploying to different environments.
        """
        violations = []
        
        for file_path in self._get_python_files():
            if self._is_exception_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for hardcoded configuration patterns
                for pattern in self.hardcoded_config_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Skip if this is in a comment or docstring
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_content = content[line_start:content.find('\n', match.start())]
                        if line_content.strip().startswith('#') or '"""' in line_content:
                            continue
                            
                        violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'pattern': pattern,
                            'code': match.group(),
                            'severity': 'HIGH',
                            'business_impact': 'Prevents environment portability'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        if violations:
            violation_summary = self._format_environment_violations(violations)
            pytest.fail(
                f"CRITICAL: Found {len(violations)} hardcoded configuration violations.\n"
                f"These prevent proper environment isolation.\n\n"
                f"{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"Move to service-specific configuration modules:\n"
                f"- netra_backend/app/config.py for backend config\n"  
                f"- auth_service/auth_core/config.py for auth config\n"
                f"- shared/cors_config.py for shared config\n\n"
                f"Business Impact: Environment-specific failures and deployment issues"
            )

    def test_service_environment_boundary_respect(self):
        """CRITICAL: Verify services don't access each other's environment variables.
        
        Business Impact: Cross-service environment access violates service boundaries
        and creates tight coupling that can cause cascade failures.
        """
        violations = []
        
        for file_path in self._get_python_files():
            if self._is_exception_file(file_path):
                continue
                
            # Determine which service this file belongs to
            service = self._get_service_from_path(file_path)
            if not service:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for cross-service environment variable access
                forbidden_prefixes = self.service_boundaries.get(service, [])
                for prefix in forbidden_prefixes:
                    pattern = rf'["\']({prefix}\w+)["\']'
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'service': service,
                            'forbidden_var': match.group(1),
                            'severity': 'HIGH',
                            'business_impact': 'Violates service boundaries'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
                
        if violations:
            violation_summary = self._format_service_boundary_violations(violations)
            pytest.fail(
                f"CRITICAL: Found {len(violations)} service boundary violations.\n"
                f"Services are accessing each other's environment variables.\n\n"
                f"{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"Use service-to-service communication instead of shared environment variables.\n"
                f"Each service should only access its own environment scope.\n\n"
                f"Business Impact: Service coupling causes cascade failures"
            )

    def test_configuration_ssot_compliance(self):
        """CRITICAL: Validate configuration comes from canonical sources.
        
        Business Impact: Non-canonical configuration sources can lead to
        inconsistent behavior and make debugging configuration issues impossible.
        """
        violations = []
        config_files_found = []
        
        for file_path in self._get_python_files():
            if self._is_exception_file(file_path):
                continue
                
            relative_path = str(file_path).replace(str(Path.cwd()), "").lstrip("/\\")
            
            # Check if this is a configuration file
            if any(keyword in relative_path.lower() for keyword in ['config', 'settings', 'environment']):
                config_files_found.append(relative_path)
                
                # Verify it's in canonical location
                if not any(canonical in relative_path for canonical in self.canonical_config_paths):
                    violations.append({
                        'file': relative_path,
                        'violation_type': 'non_canonical_config_location',
                        'severity': 'MEDIUM',
                        'business_impact': 'Creates configuration sprawl'
                    })
        
        # Check for missing canonical configuration usage
        service_roots = ['netra_backend', 'auth_service', 'analytics_service']
        for service_root in service_roots:
            service_files = [f for f in config_files_found if f.startswith(service_root)]
            canonical_config = f"{service_root}/app/config.py" if service_root == 'netra_backend' else f"{service_root}/auth_core/config.py"
            
            if service_files and canonical_config not in [f.replace('\\', '/') for f in service_files]:
                violations.append({
                    'service': service_root,
                    'violation_type': 'missing_canonical_config',
                    'expected_path': canonical_config,
                    'severity': 'HIGH',
                    'business_impact': 'No single source of truth for service configuration'
                })
        
        if violations:
            violation_summary = self._format_config_ssot_violations(violations)
            pytest.fail(
                f"CRITICAL: Found {len(violations)} configuration SSOT violations.\n\n"
                f"{violation_summary}\n\n"
                f"REMEDIATION:\n"
                f"Consolidate configuration into canonical service config modules.\n"
                f"Use get_config() functions to access configuration.\n\n"
                f"Business Impact: Configuration sprawl makes system unpredictable"
            )

    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the codebase."""
        python_files = []
        
        # Scan main source directories
        source_dirs = [
            Path.cwd() / "netra_backend",
            Path.cwd() / "auth_service", 
            Path.cwd() / "analytics_service",
            Path.cwd() / "shared",
            Path.cwd() / "test_framework",
            Path.cwd() / "tests",
        ]
        
        for source_dir in source_dirs:
            if source_dir.exists():
                python_files.extend(source_dir.glob("**/*.py"))
                
        return python_files

    def _is_exception_file(self, file_path: Path) -> bool:
        """Check if file is in exception list."""
        file_str = str(file_path).lower()
        return any(exception in file_str for exception in self.exception_files)

    def _get_service_from_path(self, file_path: Path) -> Optional[str]:
        """Determine which service a file belongs to."""
        file_str = str(file_path)
        if "netra_backend" in file_str:
            return "netra_backend"
        elif "auth_service" in file_str:
            return "auth_service"
        elif "analytics_service" in file_str:
            return "analytics_service"
        return None

    def _format_environment_violations(self, violations: List[Dict]) -> str:
        """Format environment access violations for reporting."""
        if not violations:
            return "No violations found."
            
        summary = []
        summary.append("ENVIRONMENT ACCESS VIOLATIONS:")
        summary.append("=" * 50)
        
        for violation in violations[:10]:  # Show first 10
            summary.append(f"File: {violation['file']}")
            summary.append(f"Line: {violation['line']}")
            summary.append(f"Code: {violation['code']}")
            summary.append(f"Severity: {violation['severity']}")
            summary.append(f"Impact: {violation['business_impact']}")
            summary.append("-" * 30)
            
        if len(violations) > 10:
            summary.append(f"... and {len(violations) - 10} more violations")
            
        return "\n".join(summary)

    def _format_service_boundary_violations(self, violations: List[Dict]) -> str:
        """Format service boundary violations for reporting."""
        if not violations:
            return "No violations found."
            
        summary = []
        summary.append("SERVICE BOUNDARY VIOLATIONS:")
        summary.append("=" * 50)
        
        for violation in violations[:10]:
            summary.append(f"Service: {violation['service']}")
            summary.append(f"File: {violation['file']}")
            summary.append(f"Line: {violation['line']}")
            summary.append(f"Forbidden Variable: {violation['forbidden_var']}")
            summary.append(f"Impact: {violation['business_impact']}")
            summary.append("-" * 30)
            
        return "\n".join(summary)

    def _format_config_ssot_violations(self, violations: List[Dict]) -> str:
        """Format configuration SSOT violations for reporting."""
        if not violations:
            return "No violations found."
            
        summary = []
        summary.append("CONFIGURATION SSOT VIOLATIONS:")
        summary.append("=" * 50)
        
        for violation in violations:
            if violation.get('file'):
                summary.append(f"File: {violation['file']}")
            if violation.get('service'):
                summary.append(f"Service: {violation['service']}")
            summary.append(f"Violation: {violation['violation_type']}")
            if violation.get('expected_path'):
                summary.append(f"Expected Path: {violation['expected_path']}")
            summary.append(f"Severity: {violation['severity']}")
            summary.append(f"Impact: {violation['business_impact']}")
            summary.append("-" * 30)
            
        return "\n".join(summary)