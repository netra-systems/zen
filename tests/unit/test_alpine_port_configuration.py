"""
Unit tests for Alpine Dockerfile port configuration validation.

CRITICAL: These tests are designed to FAIL until Alpine Dockerfiles are fixed
to use dynamic PORT environment variable instead of hardcoded ports.

Issue #146: Cloud Run PORT Configuration Error - Alpine Dockerfiles use hardcoded
ports while GCP Dockerfiles correctly use ${PORT} environment variable.
"""
import os
import re
import pytest
from pathlib import Path
from typing import Dict, List, Tuple
from test_framework.ssot.base_test_case import BaseTestCase

@pytest.mark.unit
class TestAlpinePortConfiguration(BaseTestCase):
    """Test suite to validate Alpine Dockerfile port configurations.
    
    These tests are expected to FAIL until the port configuration is fixed.
    """

    def setup_method(self, method=None):
        """Set up test method with Dockerfile paths."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        self.alpine_dockerfiles = list(self.project_root.glob('dockerfiles/*.alpine.Dockerfile'))
        self.gcp_dockerfiles = list(self.project_root.glob('deployment/docker/*.gcp.Dockerfile'))
        assert self.alpine_dockerfiles, 'No Alpine Dockerfiles found'
        assert self.gcp_dockerfiles, 'No GCP Dockerfiles found'

    def test_alpine_dockerfile_uses_dynamic_port_binding(self):
        """
        FAILING TEST: Alpine Dockerfiles should use ${PORT} environment variable.
        
        Expected to FAIL: Currently Alpine Dockerfiles use hardcoded port 8000
        in both gunicorn --bind and health check configurations.
        """
        failures = []
        for dockerfile_path in self.alpine_dockerfiles:
            if 'backend' not in dockerfile_path.name:
                continue
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            hardcoded_bind_pattern = '--bind\\s+0\\.0\\.0\\.0:8000'
            if re.search(hardcoded_bind_pattern, content):
                failures.append(f'{dockerfile_path.name}: Uses hardcoded port 8000 in gunicorn --bind. Should use --bind 0.0.0.0:${{PORT:-8000}}')
            hardcoded_health_pattern = 'curl.*localhost:8000'
            if re.search(hardcoded_health_pattern, content):
                failures.append(f'{dockerfile_path.name}: Uses hardcoded localhost:8000 in health check. Should use localhost:${{PORT:-8000}}')
        if failures:
            pytest.fail(f'Alpine Dockerfile port configuration failures:\n' + '\n'.join(failures))

    def test_alpine_dockerfile_health_check_port_configuration(self):
        """
        FAILING TEST: Health check should use dynamic port configuration.
        
        Expected to FAIL: Health check currently uses hardcoded localhost:8000
        instead of localhost:${PORT:-8000}.
        """
        for dockerfile_path in self.alpine_dockerfiles:
            if 'backend' not in dockerfile_path.name:
                continue
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            healthcheck_match = re.search('HEALTHCHECK.*CMD\\s+(.+)', content, re.MULTILINE)
            if healthcheck_match:
                healthcheck_cmd = healthcheck_match.group(1)
                assert 'localhost:8000' not in healthcheck_cmd, f'{dockerfile_path.name}: Health check uses hardcoded port 8000. Should use localhost:${{PORT:-8000}} for Cloud Run compatibility.'

    def test_alpine_vs_gcp_dockerfile_port_parity(self):
        """
        FAILING TEST: Alpine and GCP Dockerfiles should have port configuration parity.
        
        Expected to FAIL: GCP Dockerfiles correctly use ${PORT} while Alpine uses hardcoded ports.
        """
        alpine_configs = self._extract_port_configs(self.alpine_dockerfiles)
        gcp_configs = self._extract_port_configs(self.gcp_dockerfiles)
        if 'backend' in alpine_configs and 'backend' in gcp_configs:
            alpine_backend = alpine_configs['backend']
            gcp_backend = gcp_configs['backend']
            assert gcp_backend['uses_dynamic_port'], 'GCP Dockerfile should use dynamic PORT variable'
            assert alpine_backend['uses_dynamic_port'], f"Alpine Dockerfile should use dynamic PORT variable like GCP version. Currently: Alpine={alpine_backend['port_config']}, GCP={gcp_backend['port_config']}"

    def test_cloud_run_port_environment_compatibility(self):
        """
        FAILING TEST: Alpine Dockerfiles should be compatible with Cloud Run PORT env var.
        
        Expected to FAIL: Cloud Run sets PORT environment variable dynamically,
        but Alpine Dockerfiles ignore this and use hardcoded port 8000.
        """
        for dockerfile_path in self.alpine_dockerfiles:
            if 'backend' not in dockerfile_path.name:
                continue
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            cmd_match = re.search('CMD.*gunicorn.*--bind\\s+([^\\s]+)', content, re.DOTALL)
            if cmd_match:
                bind_config = cmd_match.group(1)
                assert re.search('\\$\\{PORT.*\\}', bind_config), f'{dockerfile_path.name}: gunicorn bind should use ${{PORT}} environment variable for Cloud Run compatibility. Current: {bind_config}'

    def _extract_port_configs(self, dockerfile_paths: List[Path]) -> Dict[str, Dict]:
        """Extract port configuration details from Dockerfiles."""
        configs = {}
        for dockerfile_path in dockerfile_paths:
            service_name = self._get_service_name(dockerfile_path.name)
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            port_config = {}
            cmd_match = re.search('CMD.*--bind\\s+([^\\s]+)', content, re.DOTALL)
            if cmd_match:
                bind_config = cmd_match.group(1)
                port_config['port_config'] = bind_config
                port_config['uses_dynamic_port'] = '${PORT' in bind_config
            else:
                port_match = re.search('--port\\s+\\$\\{PORT[^}]*\\}', content)
                if port_match:
                    port_config['port_config'] = port_match.group(0)
                    port_config['uses_dynamic_port'] = True
                else:
                    port_config['port_config'] = 'hardcoded'
                    port_config['uses_dynamic_port'] = False
            configs[service_name] = port_config
        return configs

    def _get_service_name(self, filename: str) -> str:
        """Extract service name from Dockerfile filename."""
        if 'backend' in filename:
            return 'backend'
        elif 'auth' in filename:
            return 'auth'
        elif 'frontend' in filename:
            return 'frontend'
        else:
            return 'unknown'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')