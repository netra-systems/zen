"""
Integration tests for static analysis of Dockerfile configurations.

CRITICAL: These tests perform static analysis of Dockerfiles to detect
configuration issues that would cause Cloud Run deployment failures.

Issue #146: Cloud Run PORT Configuration Error - Static analysis to identify
hardcoded port configurations and other deployment-blocking issues.
"""
import os
import re
import ast
import pytest
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from test_framework.ssot.base_test_case import BaseTestCase

@pytest.mark.integration
class DockerfileConfigurationAnalysisTests(BaseTestCase):
    """Test suite for static analysis of Dockerfile configurations.
    
    These tests analyze Dockerfile content to identify configuration issues
    that would prevent successful Cloud Run deployments.
    """

    def setUp(self):
        """Set up test environment with Dockerfile paths."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.critical_dockerfiles = {'backend.alpine': self.project_root / 'dockerfiles' / 'backend.alpine.Dockerfile', 'backend.gcp': self.project_root / 'deployment' / 'docker' / 'backend.gcp.Dockerfile', 'auth.alpine': self.project_root / 'dockerfiles' / 'auth.alpine.Dockerfile', 'auth.gcp': self.project_root / 'deployment' / 'docker' / 'auth.gcp.Dockerfile'}
        for name, path in self.critical_dockerfiles.items():
            if not path.exists():
                self.skipTest(f'Critical Dockerfile missing: {name} at {path}')

    def test_static_port_configuration_analysis(self):
        """
        FAILING TEST: Static analysis should detect hardcoded port configurations.
        
        Expected to FAIL: Alpine Dockerfiles contain hardcoded ports that will
        cause Cloud Run deployment failures.
        """
        analysis_results = {}
        for name, dockerfile_path in self.critical_dockerfiles.items():
            analysis = self._analyze_port_configuration(dockerfile_path)
            analysis_results[name] = analysis
            if 'alpine' in name:
                self.assertFalse(analysis['has_hardcoded_ports'], f"{name}: Contains hardcoded ports that will cause Cloud Run failures. Issues: {analysis['port_issues']}")
            if 'gcp' in name:
                self.assertFalse(analysis['has_hardcoded_ports'], f"{name}: Should not contain hardcoded ports. Issues: {analysis['port_issues']}")

    def test_cloud_run_compatibility_analysis(self):
        """
        FAILING TEST: Static analysis for Cloud Run deployment compatibility.
        
        Expected to FAIL: Alpine Dockerfiles lack proper Cloud Run compatibility features.
        """
        compatibility_issues = {}
        for name, dockerfile_path in self.critical_dockerfiles.items():
            issues = self._analyze_cloud_run_compatibility(dockerfile_path)
            compatibility_issues[name] = issues
            critical_issues = [issue for issue in issues if issue['severity'] == 'critical']
            self.assertEqual(len(critical_issues), 0, f'{name}: Critical Cloud Run compatibility issues detected:\n' + '\n'.join([f"- {issue['description']}" for issue in critical_issues]))

    def test_dockerfile_security_and_best_practices_analysis(self):
        """
        FAILING TEST: Static analysis for security and best practices.
        
        Expected to FAIL: May detect security or best practice violations
        that could affect Cloud Run deployment.
        """
        security_issues = {}
        for name, dockerfile_path in self.critical_dockerfiles.items():
            issues = self._analyze_security_practices(dockerfile_path)
            security_issues[name] = issues
            blocking_issues = [issue for issue in issues if issue['blocks_deployment']]
            self.assertEqual(len(blocking_issues), 0, f'{name}: Deployment-blocking security issues detected:\n' + '\n'.join([f"- {issue['description']}" for issue in blocking_issues]))

    def test_environment_variable_consistency_analysis(self):
        """
        FAILING TEST: Static analysis of environment variable consistency.
        
        Expected to FAIL: Alpine and GCP Dockerfiles may have inconsistent
        environment variable configurations.
        """
        env_analysis = {}
        for name, dockerfile_path in self.critical_dockerfiles.items():
            env_vars = self._analyze_environment_variables(dockerfile_path)
            env_analysis[name] = env_vars
        services = {'backend', 'auth'}
        for service in services:
            alpine_key = f'{service}.alpine'
            gcp_key = f'{service}.gcp'
            if alpine_key not in env_analysis or gcp_key not in env_analysis:
                continue
            alpine_env = env_analysis[alpine_key]
            gcp_env = env_analysis[gcp_key]
            inconsistencies = self._find_environment_inconsistencies(alpine_env, gcp_env)
            self.assertEqual(len(inconsistencies), 0, f'{service}: Environment variable inconsistencies between Alpine and GCP:\n' + '\n'.join(inconsistencies))

    def test_command_execution_security_analysis(self):
        """
        FAILING TEST: Static analysis of command execution patterns for security issues.
        
        Expected to FAIL: May detect insecure command execution patterns.
        """
        for name, dockerfile_path in self.critical_dockerfiles.items():
            security_issues = self._analyze_command_security(dockerfile_path)
            critical_security_issues = [issue for issue in security_issues if issue['severity'] in ['critical', 'high']]
            self.assertEqual(len(critical_security_issues), 0, f'{name}: Critical command security issues detected:\n' + '\n'.join([f"- {issue['description']}" for issue in critical_security_issues]))

    def _analyze_port_configuration(self, dockerfile_path: Path) -> Dict:
        """Analyze port configuration in a Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        analysis = {'has_hardcoded_ports': False, 'port_issues': [], 'exposed_ports': [], 'bind_configurations': []}
        expose_matches = re.finditer('EXPOSE\\s+(\\d+)', content)
        for match in expose_matches:
            port = int(match.group(1))
            analysis['exposed_ports'].append(port)
        bind_patterns = ['--bind\\s+[^:]+:(\\d+)', '--port\\s+(\\d+)', 'localhost:(\\d+)']
        for pattern in bind_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                port = int(match.group(1))
                analysis['bind_configurations'].append(port)
                context = content[max(0, match.start() - 50):match.end() + 50]
                if '${PORT' not in context and '$PORT' not in context:
                    analysis['has_hardcoded_ports'] = True
                    analysis['port_issues'].append(f'Hardcoded port {port} in: {match.group(0)}')
        return analysis

    def _analyze_cloud_run_compatibility(self, dockerfile_path: Path) -> List[Dict]:
        """Analyze Cloud Run compatibility issues."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        issues = []
        if '${PORT' not in content and '$PORT' not in content:
            if '--port' in content or '--bind' in content:
                issues.append({'severity': 'critical', 'description': 'Does not use PORT environment variable for dynamic port binding'})
        if 'tini' not in content and 'dumb-init' not in content:
            if 'ENTRYPOINT' in content:
                issues.append({'severity': 'medium', 'description': 'Missing proper signal handling (tini/dumb-init) for graceful shutdowns'})
        if 'HEALTHCHECK' not in content:
            issues.append({'severity': 'medium', 'description': 'Missing HEALTHCHECK instruction for Cloud Run readiness probes'})
        elif 'localhost:8000' in content:
            issues.append({'severity': 'critical', 'description': 'Health check uses hardcoded port instead of dynamic PORT variable'})
        if 'USER ' not in content:
            issues.append({'severity': 'high', 'description': 'Running as root user (security risk)'})
        return issues

    def _analyze_security_practices(self, dockerfile_path: Path) -> List[Dict]:
        """Analyze security practices in Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        issues = []
        env_patterns = ['ENV\\s+.*(?:password|secret|key|token).*=.*\\S', 'ENV\\s+.*=.*(?:password|secret|key|token)']
        for pattern in env_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                issues.append({'severity': 'high', 'description': f'Potential secret in ENV: {match.group(0)}', 'blocks_deployment': False})
        if 'USER root' in content or ('USER ' not in content and 'adduser' not in content):
            issues.append({'severity': 'medium', 'description': 'Container may run as root user', 'blocks_deployment': False})
        if 'apt-get update' in content and 'rm -rf /var/lib/apt/lists/*' not in content:
            issues.append({'severity': 'low', 'description': 'apt cache not cleaned up (increases image size)', 'blocks_deployment': False})
        return issues

    def _analyze_environment_variables(self, dockerfile_path: Path) -> Dict[str, str]:
        """Extract and analyze environment variables from Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        env_vars = {}
        env_matches = re.finditer('ENV\\s+(.+)', content, re.MULTILINE)
        for match in env_matches:
            env_line = match.group(1).strip()
            if env_line.endswith('\\'):
                continue
            if '=' in env_line:
                parts = env_line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    env_vars[key] = value
            else:
                parts = env_line.split(None, 1)
                if len(parts) == 2:
                    env_vars[parts[0]] = parts[1]
        return env_vars

    def _find_environment_inconsistencies(self, alpine_env: Dict, gcp_env: Dict) -> List[str]:
        """Find inconsistencies between Alpine and GCP environment configurations."""
        inconsistencies = []
        critical_vars = {'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED'}
        for var in critical_vars:
            alpine_val = alpine_env.get(var)
            gcp_val = gcp_env.get(var)
            if alpine_val != gcp_val:
                inconsistencies.append(f"{var}: Alpine='{alpine_val}', GCP='{gcp_val}'")
        alpine_only = set(alpine_env.keys()) - set(gcp_env.keys())
        gcp_only = set(gcp_env.keys()) - set(alpine_env.keys())
        if alpine_only:
            inconsistencies.append(f"Variables only in Alpine: {', '.join(sorted(alpine_only))}")
        if gcp_only:
            inconsistencies.append(f"Variables only in GCP: {', '.join(sorted(gcp_only))}")
        return inconsistencies

    def _analyze_command_security(self, dockerfile_path: Path) -> List[Dict]:
        """Analyze command execution patterns for security issues."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        issues = []
        risky_patterns = ['sh\\s+-c\\s+.*\\$\\{.*\\}', 'exec\\s+.*\\$\\{.*\\}']
        for pattern in risky_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append({'severity': 'low', 'description': f'Variable substitution in shell command: {match.group(0)[:50]}...'})
        cmd_matches = re.finditer('(CMD|ENTRYPOINT)\\s+(.+)', content)
        for match in matches:
            cmd_content = match.group(2)
            if '$' in cmd_content and '[' not in cmd_content:
                issues.append({'severity': 'medium', 'description': f'Shell form command with variables: {cmd_content[:50]}...'})
        return issues
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')