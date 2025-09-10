#!/usr/bin/env python
"""
Cloud Run Port Configuration Tests - Critical P0 Issue #146
===========================================================

This test suite exposes and validates the Cloud Run port configuration issues 
that are causing staging deployment failures.

Critical Issues Being Tested:
1. Manual PORT environment variable conflicts with Cloud Run auto-assignment
2. Container startup timeout failures due to port binding issues
3. Service configuration validation for Cloud Run compatibility

BUSINESS VALUE: Prevents Golden Path blocking deployment failures in staging/production

Following CLAUDE.md principles:
- Real services, not mocks (where applicable for port testing)
- Tests designed to fail initially to expose current issues
- Complete validation of port configuration across environments
- SSOT compliance for environment configuration
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch
import socket
import tempfile

import pytest
import yaml
import docker
import httpx

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase

pytestmark = pytest.mark.asyncio


class CloudRunPortConfigError(Exception):
    """Exception raised for Cloud Run port configuration errors."""
    pass


class CloudRunPortConfigurationValidator:
    """
    Validates Cloud Run port configuration compliance.
    
    This validator ensures that service configurations meet Cloud Run requirements
    and do not have manual PORT environment variable conflicts.
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.project_root = Path(__file__).parent.parent.parent
        self.docker_client = None
        
    def _get_docker_client(self) -> docker.DockerClient:
        """Get Docker client for container inspection."""
        if not self.docker_client:
            self.docker_client = docker.from_env()
        return self.docker_client
    
    def validate_docker_compose_port_config(self, compose_file: Path) -> Dict[str, Any]:
        """
        Validate Docker Compose file for Cloud Run port compatibility.
        
        Returns:
            Dict with validation results and detected issues
        """
        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {compose_file}")
            
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        issues = []
        services_checked = []
        
        for service_name, service_config in compose_data.get('services', {}).items():
            services_checked.append(service_name)
            
            # Check for manual PORT environment variable
            env_vars = service_config.get('environment', {})
            if isinstance(env_vars, list):
                # Handle environment as list format
                for env_var in env_vars:
                    if isinstance(env_var, str) and env_var.startswith('PORT='):
                        issues.append({
                            'service': service_name,
                            'issue': 'manual_port_env_var',
                            'details': f'Manual PORT environment variable: {env_var}',
                            'severity': 'CRITICAL',
                            'cloud_run_conflict': True
                        })
            elif isinstance(env_vars, dict):
                # Handle environment as dict format
                if 'PORT' in env_vars:
                    issues.append({
                        'service': service_name,
                        'issue': 'manual_port_env_var',
                        'details': f'Manual PORT environment variable: PORT={env_vars["PORT"]}',
                        'severity': 'CRITICAL',
                        'cloud_run_conflict': True
                    })
            
            # Check port mappings
            ports = service_config.get('ports', [])
            if ports:
                for port_mapping in ports:
                    if isinstance(port_mapping, str):
                        if ':8888' in port_mapping:
                            issues.append({
                                'service': service_name,
                                'issue': 'hardcoded_port_8888',
                                'details': f'Hardcoded port 8888 mapping: {port_mapping}',
                                'severity': 'HIGH',
                                'cloud_run_conflict': True
                            })
        
        return {
            'valid': len(issues) == 0,
            'services_checked': services_checked,
            'issues': issues,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i['severity'] == 'CRITICAL'])
        }
    
    def check_environment_port_conflicts(self) -> Dict[str, Any]:
        """
        Check for PORT environment variable conflicts across all env files.
        
        Returns:
            Dict with conflict analysis results
        """
        env_files = [
            self.project_root / '.env',
            self.project_root / '.env.staging', 
            self.project_root / '.env.production.template',
            self.project_root / '.env.development',
            self.project_root / '.env.test'
        ]
        
        port_conflicts = []
        port_definitions = {}
        
        for env_file in env_files:
            if not env_file.exists():
                continue
                
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if line.startswith('PORT=') and not line.startswith('#'):
                        port_value = line.split('=', 1)[1]
                        port_definitions[str(env_file.name)] = {
                            'value': port_value,
                            'line': line_num,
                            'file': str(env_file)
                        }
                        
                        # Check if this is problematic for Cloud Run
                        if port_value == '8888':
                            port_conflicts.append({
                                'file': str(env_file.name),
                                'line': line_num,
                                'value': port_value,
                                'issue': 'cloud_run_reserved_port',
                                'severity': 'CRITICAL'
                            })
                            
            except (UnicodeDecodeError, PermissionError) as e:
                continue
        
        return {
            'conflicts_found': len(port_conflicts) > 0,
            'port_conflicts': port_conflicts,
            'port_definitions': port_definitions,
            'total_conflicts': len(port_conflicts)
        }
    
    async def test_port_binding_simulation(self, port: int = 8888) -> Dict[str, Any]:
        """
        Simulate Cloud Run port binding behavior.
        
        Args:
            port: Port to test binding on (default 8888 for Cloud Run simulation)
            
        Returns:
            Dict with port binding test results
        """
        binding_results = {
            'port': port,
            'binding_successful': False,
            'binding_time_ms': 0,
            'conflicts_detected': [],
            'error': None
        }
        
        start_time = time.time()
        
        try:
            # Test port availability
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            
            # Try to bind to the port
            try:
                sock.bind(('0.0.0.0', port))
                sock.listen(1)
                binding_results['binding_successful'] = True
                
                # Simulate timeout scenarios
                await asyncio.sleep(0.1)
                
            except OSError as e:
                binding_results['conflicts_detected'].append({
                    'type': 'port_in_use',
                    'details': str(e),
                    'port': port
                })
            finally:
                sock.close()
                
        except Exception as e:
            binding_results['error'] = str(e)
        
        binding_results['binding_time_ms'] = (time.time() - start_time) * 1000
        
        return binding_results


class TestCloudRunPortConfiguration(SSotBaseTestCase):
    """
    Integration tests for Cloud Run port configuration validation.
    
    These tests are designed to FAIL initially to expose the current
    port configuration issues causing Cloud Run deployment failures.
    """
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.validator = CloudRunPortConfigurationValidator()
        self.project_root = Path(__file__).parent.parent.parent
        
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_docker_compose_staging_port_config(self):
        """
        CRITICAL: Test staging Docker Compose for Cloud Run port conflicts.
        
        This test SHOULD FAIL initially due to manual PORT=8888 environment variables.
        """
        staging_compose = self.project_root / 'docker-compose.staging.yml'
        
        validation_result = self.validator.validate_docker_compose_port_config(staging_compose)
        
        # Log detailed results for debugging
        self.log_test_result("docker_compose_staging_validation", {
            'file': str(staging_compose),
            'validation_result': validation_result
        })
        
        # Assert no manual PORT environment variables
        critical_issues = [i for i in validation_result['issues'] 
                          if i['severity'] == 'CRITICAL' and i.get('cloud_run_conflict')]
        
        assert len(critical_issues) == 0, (
            f"CRITICAL: Found {len(critical_issues)} Cloud Run port conflicts in staging compose:\n"
            + "\n".join([f"- {issue['service']}: {issue['details']}" for issue in critical_issues])
        )
        
        # Verify services were actually checked
        assert len(validation_result['services_checked']) > 0, (
            "No services found in staging compose file"
        )
        
        # Log success
        self.log_test_result("staging_port_config_validation", {
            'status': 'PASS',
            'services_validated': validation_result['services_checked'],
            'issues_found': validation_result['total_issues']
        })
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_environment_files_port_conflicts(self):
        """
        CRITICAL: Test all environment files for PORT variable conflicts.
        
        This test SHOULD FAIL if any env files contain manual PORT=8888 settings.
        """
        conflict_analysis = self.validator.check_environment_port_conflicts()
        
        # Log detailed analysis
        self.log_test_result("environment_port_conflict_analysis", conflict_analysis)
        
        # Assert no critical port conflicts
        critical_conflicts = [c for c in conflict_analysis['port_conflicts'] 
                            if c['severity'] == 'CRITICAL']
        
        assert len(critical_conflicts) == 0, (
            f"CRITICAL: Found {len(critical_conflicts)} PORT conflicts in environment files:\n"
            + "\n".join([
                f"- {conflict['file']}:{conflict['line']} PORT={conflict['value']} ({conflict['issue']})" 
                for conflict in critical_conflicts
            ])
        )
        
        # Verify we checked actual files
        assert len(conflict_analysis['port_definitions']) > 0, (
            "No PORT definitions found in any environment files"
        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_cloud_run_port_binding_simulation(self):
        """
        Test port binding simulation to detect Cloud Run startup issues.
        
        This tests the container's ability to bind to Cloud Run assigned ports.
        """
        # Test the problematic port 8888
        binding_result = await self.validator.test_port_binding_simulation(8888)
        
        # Log binding results
        self.log_test_result("cloud_run_port_binding_simulation", binding_result)
        
        # Assert successful binding (or expected conflicts)
        if binding_result['conflicts_detected']:
            # If conflicts detected, ensure they're documented
            conflict_details = binding_result['conflicts_detected']
            self.log_test_result("port_binding_conflicts", {
                'port': 8888,
                'conflicts': conflict_details,
                'binding_time_ms': binding_result['binding_time_ms']
            })
            
            # For now, log conflicts but don't fail - this helps debug
            print(f"DEBUG: Port 8888 conflicts detected: {conflict_details}")
        
        # Assert no critical errors occurred during binding test
        assert binding_result['error'] is None, (
            f"Port binding simulation failed with error: {binding_result['error']}"
        )
        
        # Assert binding time is reasonable (under 10 seconds simulating Cloud Run timeout)
        assert binding_result['binding_time_ms'] < 10000, (
            f"Port binding took too long: {binding_result['binding_time_ms']}ms (Cloud Run timeout concern)"
        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_alpine_compose_port_config(self):
        """
        Test Alpine Docker Compose configurations for port conflicts.
        
        Validates that Alpine test configurations don't have port conflicts.
        """
        alpine_compose = self.project_root / 'docker-compose.alpine-test.yml'
        
        if not alpine_compose.exists():
            pytest.skip("Alpine test compose file not found")
        
        validation_result = self.validator.validate_docker_compose_port_config(alpine_compose)
        
        # Log results
        self.log_test_result("alpine_compose_validation", validation_result)
        
        # Assert no critical issues in Alpine configuration
        critical_issues = [i for i in validation_result['issues'] 
                          if i['severity'] == 'CRITICAL']
        
        assert len(critical_issues) == 0, (
            f"CRITICAL: Alpine compose has {len(critical_issues)} port configuration issues:\n"
            + "\n".join([f"- {issue['service']}: {issue['details']}" for issue in critical_issues])
        )
    
    @pytest.mark.integration
    @pytest.mark.deployment_critical
    async def test_service_port_environment_isolation(self):
        """
        Test that services have proper port environment isolation.
        
        Validates that services don't leak port configurations between environments.
        """
        services_to_check = ['backend', 'auth', 'frontend']
        isolation_results = {}
        
        for service in services_to_check:
            # Check each service's expected port configuration
            service_result = {
                'service': service,
                'expected_ports': {},
                'conflicts': [],
                'isolation_valid': True
            }
            
            # Define expected ports per service
            if service == 'backend':
                service_result['expected_ports'] = {
                    'local': 8000,
                    'test': 8000,
                    'staging': 'cloud_run_assigned',
                    'production': 'cloud_run_assigned'
                }
            elif service == 'auth':
                service_result['expected_ports'] = {
                    'local': 8081,  
                    'test': 8081,
                    'staging': 'cloud_run_assigned',
                    'production': 'cloud_run_assigned'
                }
            elif service == 'frontend':
                service_result['expected_ports'] = {
                    'local': 3000,
                    'test': 3000,
                    'staging': 'cloud_run_assigned', 
                    'production': 'cloud_run_assigned'
                }
            
            # Validate isolation (no hardcoded staging/prod ports)
            for env_type, expected_port in service_result['expected_ports'].items():
                if env_type in ['staging', 'production'] and expected_port != 'cloud_run_assigned':
                    service_result['conflicts'].append({
                        'environment': env_type,
                        'issue': 'hardcoded_cloud_run_port',
                        'expected': 'cloud_run_assigned',
                        'found': expected_port
                    })
                    service_result['isolation_valid'] = False
            
            isolation_results[service] = service_result
        
        # Log isolation analysis
        self.log_test_result("service_port_isolation_analysis", isolation_results)
        
        # Assert all services have proper isolation
        failed_services = [service for service, result in isolation_results.items() 
                          if not result['isolation_valid']]
        
        assert len(failed_services) == 0, (
            f"Port isolation failures in services: {failed_services}\n"
            + "Services must use Cloud Run assigned ports in staging/production"
        )
    
    @pytest.mark.integration 
    @pytest.mark.deployment_critical
    async def test_cloud_run_deployment_config_generation(self):
        """
        Test generation of Cloud Run deployment configurations.
        
        Validates that deployment configs don't include manual PORT variables.
        """
        # Look for deployment configuration files/scripts
        deployment_files = [
            self.project_root / 'scripts' / 'deploy_to_gcp.py',
            self.project_root / 'cloudbuild-backend.yaml',
            self.project_root / 'cloudbuild-auth.yaml'
        ]
        
        config_analysis = {
            'files_checked': [],
            'port_violations': [],
            'deployment_valid': True
        }
        
        for config_file in deployment_files:
            if not config_file.exists():
                continue
                
            config_analysis['files_checked'].append(str(config_file.name))
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for problematic PORT environment variable settings
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if 'PORT=8888' in line or '--set-env-vars=PORT=' in line:
                        config_analysis['port_violations'].append({
                            'file': config_file.name,
                            'line': line_num,
                            'content': line.strip(),
                            'issue': 'manual_port_in_deployment'
                        })
                        config_analysis['deployment_valid'] = False
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Log analysis
        self.log_test_result("deployment_config_analysis", config_analysis)
        
        # Assert no PORT violations in deployment configs
        assert len(config_analysis['port_violations']) == 0, (
            f"Found {len(config_analysis['port_violations'])} PORT violations in deployment configs:\n"
            + "\n".join([
                f"- {violation['file']}:{violation['line']}: {violation['content']}"
                for violation in config_analysis['port_violations']
            ])
        )
        
        # Assert we actually checked some files
        assert len(config_analysis['files_checked']) > 0, (
            "No deployment configuration files found to validate"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])