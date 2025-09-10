"""
Unit tests for detecting configuration drift between Alpine and GCP Dockerfiles.

CRITICAL: These tests are designed to FAIL until configuration parity is achieved
between Alpine and GCP Dockerfile implementations.

Issue #146: Cloud Run PORT Configuration Error - Configuration drift between
Alpine and GCP Dockerfiles causes deployment failures.
"""

import os
import re
import pytest
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Test utilities
from test_framework.ssot.test_base import BaseTestCase


class TestDockerfileConfigurationDrift(BaseTestCase):
    """Test suite to detect and validate configuration drift between Dockerfile variants.
    
    These tests are expected to FAIL until configuration drift is resolved.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with Dockerfile paths and configuration mappings."""
        super().setUpClass()
        cls.project_root = Path(__file__).parent.parent.parent
        
        # Map services to their Dockerfile variants
        cls.dockerfile_variants = {
            'backend': {
                'alpine': cls.project_root / "dockerfiles" / "backend.alpine.Dockerfile",
                'gcp': cls.project_root / "deployment" / "docker" / "backend.gcp.Dockerfile"
            },
            'auth': {
                'alpine': cls.project_root / "dockerfiles" / "auth.alpine.Dockerfile", 
                'gcp': cls.project_root / "deployment" / "docker" / "auth.gcp.Dockerfile"
            },
            'frontend': {
                'alpine': cls.project_root / "dockerfiles" / "frontend.alpine.Dockerfile",
                'gcp': cls.project_root / "deployment" / "docker" / "frontend.gcp.Dockerfile"
            }
        }
        
        # Validate all expected Dockerfiles exist
        for service, variants in cls.dockerfile_variants.items():
            for variant_type, path in variants.items():
                assert path.exists(), f"Missing {variant_type} Dockerfile for {service}: {path}"
    
    def test_port_configuration_consistency_across_variants(self):
        """
        FAILING TEST: Port configuration should be consistent between Alpine and GCP variants.
        
        Expected to FAIL: Alpine uses hardcoded ports while GCP uses dynamic PORT variable.
        """
        drift_issues = []
        
        for service, variants in self.dockerfile_variants.items():
            if service != 'backend':  # Focus on backend for port configuration
                continue
                
            alpine_config = self._extract_port_configuration(variants['alpine'])
            gcp_config = self._extract_port_configuration(variants['gcp'])
            
            # Check for port configuration drift
            if alpine_config['bind_method'] != gcp_config['bind_method']:
                drift_issues.append(
                    f"{service}: Port binding method drift - "
                    f"Alpine: {alpine_config['bind_method']}, GCP: {gcp_config['bind_method']}"
                )
            
            if alpine_config['uses_dynamic_port'] != gcp_config['uses_dynamic_port']:
                drift_issues.append(
                    f"{service}: Dynamic port usage drift - "
                    f"Alpine: {alpine_config['uses_dynamic_port']}, GCP: {gcp_config['uses_dynamic_port']}"
                )
            
            if alpine_config['health_check_port'] != gcp_config['health_check_port']:
                drift_issues.append(
                    f"{service}: Health check port drift - "
                    f"Alpine: {alpine_config['health_check_port']}, GCP: {gcp_config['health_check_port']}"
                )
        
        if drift_issues:
            self.fail(f"Configuration drift detected:\n" + "\n".join(drift_issues))
    
    def test_environment_variable_consistency(self):
        """
        FAILING TEST: Environment variables should be consistent between variants.
        
        Expected to FAIL: Alpine and GCP Dockerfiles may have different environment configurations.
        """
        for service, variants in self.dockerfile_variants.items():
            alpine_env = self._extract_environment_variables(variants['alpine'])
            gcp_env = self._extract_environment_variables(variants['gcp'])
            
            # Core environment variables that should be consistent
            core_env_vars = {'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED'}
            
            for env_var in core_env_vars:
                alpine_value = alpine_env.get(env_var)
                gcp_value = gcp_env.get(env_var)
                
                if alpine_value != gcp_value:
                    # Allow for reasonable differences but flag significant drift
                    if not self._is_acceptable_env_difference(env_var, alpine_value, gcp_value):
                        self.fail(
                            f"{service}: Environment variable drift for {env_var} - "
                            f"Alpine: {alpine_value}, GCP: {gcp_value}"
                        )
    
    def test_command_execution_pattern_consistency(self):
        """
        FAILING TEST: Command execution patterns should be equivalent between variants.
        
        Expected to FAIL: Alpine uses gunicorn while GCP uses uvicorn directly.
        """
        drift_issues = []
        
        for service, variants in self.dockerfile_variants.items():
            if service != 'backend':  # Focus on backend service
                continue
                
            alpine_cmd = self._extract_command_pattern(variants['alpine'])
            gcp_cmd = self._extract_command_pattern(variants['gcp'])
            
            # Check for fundamental differences in command execution
            if alpine_cmd['server_type'] != gcp_cmd['server_type']:
                # This is the expected drift we're testing for
                drift_issues.append(
                    f"{service}: Server type drift - "
                    f"Alpine: {alpine_cmd['server_type']}, GCP: {gcp_cmd['server_type']}"
                )
            
            # Check if both support the same critical parameters
            critical_params = {'host', 'port', 'workers', 'timeout'}
            alpine_params = set(alpine_cmd['parameters'].keys())
            gcp_params = set(gcp_cmd['parameters'].keys())
            
            missing_in_alpine = critical_params - alpine_params
            missing_in_gcp = critical_params - gcp_params
            
            if missing_in_alpine:
                drift_issues.append(
                    f"{service}: Alpine missing critical parameters: {missing_in_alpine}"
                )
            
            if missing_in_gcp:
                drift_issues.append(
                    f"{service}: GCP missing critical parameters: {missing_in_gcp}"
                )
        
        if drift_issues:
            self.fail(f"Command execution pattern drift:\n" + "\n".join(drift_issues))
    
    def test_health_check_compatibility(self):
        """
        FAILING TEST: Health check configurations should be compatible between variants.
        
        Expected to FAIL: Alpine health check uses hardcoded port while GCP may not have health check.
        """
        for service, variants in self.dockerfile_variants.items():
            if service != 'backend':
                continue
                
            alpine_health = self._extract_health_check_config(variants['alpine'])
            gcp_health = self._extract_health_check_config(variants['gcp'])
            
            # Both should have health checks for production readiness
            if alpine_health['has_health_check'] != gcp_health['has_health_check']:
                self.fail(
                    f"{service}: Health check presence mismatch - "
                    f"Alpine: {alpine_health['has_health_check']}, GCP: {gcp_health['has_health_check']}"
                )
            
            # If both have health checks, they should use compatible port configurations
            if alpine_health['has_health_check'] and gcp_health['has_health_check']:
                if alpine_health['uses_dynamic_port'] != gcp_health['uses_dynamic_port']:
                    self.fail(
                        f"{service}: Health check port configuration mismatch - "
                        f"Alpine dynamic port: {alpine_health['uses_dynamic_port']}, "
                        f"GCP dynamic port: {gcp_health['uses_dynamic_port']}"
                    )
    
    def _extract_port_configuration(self, dockerfile_path: Path) -> Dict:
        """Extract port configuration details from a Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        config = {
            'bind_method': 'unknown',
            'uses_dynamic_port': False,
            'health_check_port': 'unknown'
        }
        
        # Check for gunicorn bind
        gunicorn_match = re.search(r'gunicorn.*--bind\s+([^\s]+)', content, re.DOTALL)
        if gunicorn_match:
            bind_config = gunicorn_match.group(1)
            config['bind_method'] = 'gunicorn'
            config['uses_dynamic_port'] = '${PORT' in bind_config
        
        # Check for uvicorn port
        uvicorn_match = re.search(r'uvicorn.*--port\s+([^\s]+)', content, re.DOTALL)
        if uvicorn_match:
            port_config = uvicorn_match.group(1)
            config['bind_method'] = 'uvicorn'
            config['uses_dynamic_port'] = '${PORT' in port_config
        
        # Check health check port
        health_match = re.search(r'curl.*localhost:([^\s/]+)', content)
        if health_match:
            health_port = health_match.group(1)
            config['health_check_port'] = health_port
        
        return config
    
    def _extract_environment_variables(self, dockerfile_path: Path) -> Dict[str, str]:
        """Extract environment variables from a Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        env_vars = {}
        
        # Find ENV statements
        env_matches = re.finditer(r'ENV\s+(.+)', content, re.MULTILINE)
        for match in env_matches:
            env_line = match.group(1)
            
            # Handle both single and multi-line ENV formats
            if '\\' in env_line:
                # Multi-line format
                continue  # Skip complex parsing for now
            
            # Single line format: ENV KEY=value or ENV KEY value
            if '=' in env_line:
                parts = env_line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    env_vars[key] = value
        
        return env_vars
    
    def _extract_command_pattern(self, dockerfile_path: Path) -> Dict:
        """Extract command execution pattern from a Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = {
            'server_type': 'unknown',
            'parameters': {}
        }
        
        # Check for gunicorn
        if 'gunicorn' in content:
            pattern['server_type'] = 'gunicorn'
            # Extract common parameters
            if '--bind' in content:
                pattern['parameters']['host'] = True
                pattern['parameters']['port'] = True
            if '-w' in content or '--workers' in content:
                pattern['parameters']['workers'] = True
            if '--timeout' in content:
                pattern['parameters']['timeout'] = True
        
        # Check for uvicorn
        if 'uvicorn' in content:
            pattern['server_type'] = 'uvicorn'
            if '--host' in content:
                pattern['parameters']['host'] = True
            if '--port' in content:
                pattern['parameters']['port'] = True
            if '--workers' in content:
                pattern['parameters']['workers'] = True
        
        return pattern
    
    def _extract_health_check_config(self, dockerfile_path: Path) -> Dict:
        """Extract health check configuration from a Dockerfile."""
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        config = {
            'has_health_check': False,
            'uses_dynamic_port': False
        }
        
        if 'HEALTHCHECK' in content:
            config['has_health_check'] = True
            
            # Check if health check uses dynamic port
            health_match = re.search(r'HEALTHCHECK.*CMD.*curl.*localhost:([^\s/]+)', content, re.DOTALL)
            if health_match:
                port_config = health_match.group(1)
                config['uses_dynamic_port'] = '${PORT' in port_config or '$PORT' in port_config
        
        return config
    
    def _is_acceptable_env_difference(self, env_var: str, alpine_value: str, gcp_value: str) -> bool:
        """Determine if environment variable differences are acceptable."""
        # Both None/empty is acceptable
        if not alpine_value and not gcp_value:
            return True
        
        # PYTHONPATH differences might be acceptable due to different structures
        if env_var == 'PYTHONPATH':
            return True  # Allow differences for now
        
        # Boolean environment variables should match
        if env_var in {'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED'}:
            return alpine_value == gcp_value
        
        return False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])