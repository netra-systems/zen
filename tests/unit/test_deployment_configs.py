#!/usr/bin/env python
"""
Deployment Configuration Unit Tests - Critical P0 Issue #146
============================================================

This test suite validates deployment configuration compliance
at the unit level to catch issues before deployment.

Critical Issues Being Tested:
1. Environment variable configuration validation
2. Docker and deployment configuration parsing
3. Port configuration compliance across environments
4. Service configuration consistency
5. Cloud Run compatibility checks

BUSINESS VALUE: Prevents deployment failures through configuration validation

Following CLAUDE.md principles:
- Unit-level configuration validation
- No external dependencies (files only)
- Fast feedback for configuration issues
- SSOT compliance for configuration patterns
"""

import json
import os
import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch, mock_open

import pytest

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase

pytestmark = pytest.mark.asyncio


class DeploymentConfigError(Exception):
    """Exception raised for deployment configuration errors."""
    pass


class DeploymentConfigValidator:
    """
    Validates deployment configurations for Cloud Run compatibility.
    
    This validator performs static analysis of configuration files
    to ensure they meet deployment requirements.
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.project_root = Path(__file__).parent.parent.parent
        
    def validate_environment_config(self, env_content: str, env_name: str) -> Dict[str, Any]:
        """
        Validate environment configuration content.
        
        Args:
            env_content: Content of the environment file
            env_name: Name of the environment (e.g., 'staging', 'production')
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'environment': env_name,
            'valid': True,
            'issues': [],
            'port_configurations': {},
            'cloud_run_compatible': True
        }
        
        lines = env_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
                
            # Check for PORT environment variable
            if line.startswith('PORT=') and not line.startswith('#'):
                port_value = line.split('=', 1)[1]
                validation_result['port_configurations'][line_num] = port_value
                
                # Check if this conflicts with Cloud Run
                if env_name in ['staging', 'production'] and port_value == '8888':
                    validation_result['issues'].append({
                        'line': line_num,
                        'issue': 'cloud_run_port_conflict',
                        'details': f'Manual PORT=8888 conflicts with Cloud Run auto-assignment',
                        'severity': 'CRITICAL',
                        'recommendation': 'Remove PORT variable for Cloud Run environments'
                    })
                    validation_result['cloud_run_compatible'] = False
                    validation_result['valid'] = False
            
            # Check for other problematic configurations
            if 'localhost' in line.lower() and env_name in ['staging', 'production']:
                validation_result['issues'].append({
                    'line': line_num,
                    'issue': 'localhost_in_production',
                    'details': f'Localhost reference in production environment: {line}',
                    'severity': 'HIGH',
                    'recommendation': 'Use proper production hostnames'
                })
                validation_result['valid'] = False
            
            # Check for development-specific configurations in production
            if 'debug' in line.lower() and '=true' in line.lower() and env_name in ['staging', 'production']:
                if not any(keyword in line.lower() for keyword in ['test', 'development']):
                    validation_result['issues'].append({
                        'line': line_num,
                        'issue': 'debug_enabled_production',
                        'details': f'Debug mode enabled in production: {line}',
                        'severity': 'MEDIUM',
                        'recommendation': 'Disable debug mode in production'
                    })
        
        return validation_result
    
    def validate_docker_compose_config(self, compose_content: str, compose_name: str) -> Dict[str, Any]:
        """
        Validate Docker Compose configuration for deployment compatibility.
        
        Args:
            compose_content: YAML content of the compose file
            compose_name: Name of the compose file
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'compose_file': compose_name,
            'valid': True,
            'issues': [],
            'services_analyzed': [],
            'cloud_run_compatible': True
        }
        
        try:
            compose_data = yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            validation_result['issues'].append({
                'issue': 'yaml_parse_error',
                'details': f'Failed to parse YAML: {str(e)}',
                'severity': 'CRITICAL'
            })
            validation_result['valid'] = False
            return validation_result
        
        services = compose_data.get('services', {})
        
        for service_name, service_config in services.items():
            validation_result['services_analyzed'].append(service_name)
            
            # Check environment variables
            environment = service_config.get('environment', {})
            
            if isinstance(environment, list):
                for env_var in environment:
                    if isinstance(env_var, str) and env_var.startswith('PORT='):
                        port_value = env_var.split('=', 1)[1]
                        
                        # Check for Cloud Run conflict
                        if port_value == '8888':
                            validation_result['issues'].append({
                                'service': service_name,
                                'issue': 'manual_port_env_var',
                                'details': f'Manual PORT=8888 in environment list',
                                'severity': 'CRITICAL',
                                'cloud_run_conflict': True
                            })
                            validation_result['cloud_run_compatible'] = False
                            validation_result['valid'] = False
                            
            elif isinstance(environment, dict):
                if 'PORT' in environment:
                    port_value = str(environment['PORT'])
                    
                    if port_value == '8888':
                        validation_result['issues'].append({
                            'service': service_name,
                            'issue': 'manual_port_env_var',
                            'details': f'Manual PORT=8888 in environment dict',
                            'severity': 'CRITICAL',
                            'cloud_run_conflict': True
                        })
                        validation_result['cloud_run_compatible'] = False
                        validation_result['valid'] = False
            
            # Check port mappings
            ports = service_config.get('ports', [])
            for port_mapping in ports:
                if isinstance(port_mapping, str) and '8888' in port_mapping:
                    validation_result['issues'].append({
                        'service': service_name,
                        'issue': 'hardcoded_port_mapping',
                        'details': f'Hardcoded 8888 port mapping: {port_mapping}',
                        'severity': 'HIGH',
                        'cloud_run_conflict': True
                    })
        
        return validation_result
    
    def validate_deployment_script_config(self, script_content: str, script_name: str) -> Dict[str, Any]:
        """
        Validate deployment script configuration.
        
        Args:
            script_content: Content of the deployment script
            script_name: Name of the script file
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'script_file': script_name,
            'valid': True,
            'issues': [],
            'port_references': [],
            'cloud_run_compatible': True
        }
        
        lines = script_content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check for manual PORT environment variable setting
            if '--set-env-vars=PORT=' in line or 'PORT=8888' in line:
                validation_result['port_references'].append({
                    'line': line_num,
                    'content': line.strip(),
                    'issue': 'manual_port_setting'
                })
                
                validation_result['issues'].append({
                    'line': line_num,
                    'issue': 'cloud_run_port_override',
                    'details': f'Manual PORT setting in deployment script: {line.strip()}',
                    'severity': 'CRITICAL',
                    'recommendation': 'Remove manual PORT setting - Cloud Run assigns ports automatically'
                })
                validation_result['cloud_run_compatible'] = False
                validation_result['valid'] = False
            
            # Check for other deployment issues
            if 'gcloud run deploy' in line and '--port=' in line:
                # Extract port value
                import re
                port_match = re.search(r'--port=(\d+)', line)
                if port_match and port_match.group(1) == '8888':
                    validation_result['issues'].append({
                        'line': line_num,
                        'issue': 'hardcoded_cloud_run_port',
                        'details': f'Hardcoded --port=8888 in Cloud Run deploy',
                        'severity': 'CRITICAL',
                        'recommendation': 'Let Cloud Run assign port automatically'
                    })
                    validation_result['cloud_run_compatible'] = False
                    validation_result['valid'] = False
        
        return validation_result
    
    def generate_configuration_recommendations(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate configuration recommendations based on validation results.
        
        Args:
            validation_results: List of validation result dictionaries
            
        Returns:
            Dict with consolidated recommendations
        """
        recommendations = {
            'critical_issues': [],
            'high_priority_fixes': [],
            'medium_priority_improvements': [],
            'cloud_run_compatibility_score': 1.0,
            'overall_deployment_ready': True
        }
        
        total_issues = 0
        critical_issues = 0
        
        for result in validation_results:
            issues = result.get('issues', [])
            total_issues += len(issues)
            
            for issue in issues:
                severity = issue.get('severity', 'UNKNOWN')
                
                if severity == 'CRITICAL':
                    critical_issues += 1
                    recommendations['critical_issues'].append({
                        'source': result.get('environment', result.get('compose_file', result.get('script_file', 'unknown'))),
                        'issue': issue
                    })
                    recommendations['overall_deployment_ready'] = False
                
                elif severity == 'HIGH':
                    recommendations['high_priority_fixes'].append({
                        'source': result.get('environment', result.get('compose_file', result.get('script_file', 'unknown'))),
                        'issue': issue
                    })
                
                elif severity == 'MEDIUM':
                    recommendations['medium_priority_improvements'].append({
                        'source': result.get('environment', result.get('compose_file', result.get('script_file', 'unknown'))),
                        'issue': issue
                    })
        
        # Calculate compatibility score
        if total_issues > 0:
            recommendations['cloud_run_compatibility_score'] = max(0.0, 1.0 - (critical_issues / total_issues))
        
        return recommendations


class TestDeploymentConfigs(SSotBaseTestCase):
    """
    Unit tests for deployment configuration validation.
    
    These tests validate configuration files to prevent deployment issues.
    """
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.validator = DeploymentConfigValidator()
        self.project_root = Path(__file__).parent.parent.parent
    
    @pytest.mark.unit
    @pytest.mark.deployment_critical
    def test_staging_environment_config_validation(self):
        """
        CRITICAL: Test staging environment configuration for Cloud Run compatibility.
        
        This test SHOULD FAIL if staging env contains manual PORT=8888 settings.
        """
        staging_env_file = self.project_root / '.env.staging'
        
        if not staging_env_file.exists():
            pytest.skip("Staging environment file not found")
        
        with open(staging_env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        validation_result = self.validator.validate_environment_config(env_content, 'staging')
        
        # Log validation results
        self.log_test_result("staging_env_config_validation", validation_result)
        
        # Assert staging environment is Cloud Run compatible
        assert validation_result['cloud_run_compatible'], (
            f"CRITICAL: Staging environment not Cloud Run compatible\n"
            f"Issues: {validation_result['issues']}\n"
            f"Port configs: {validation_result['port_configurations']}"
        )
        
        # Assert no critical issues
        critical_issues = [issue for issue in validation_result['issues'] 
                          if issue.get('severity') == 'CRITICAL']
        
        assert len(critical_issues) == 0, (
            f"CRITICAL: {len(critical_issues)} critical configuration issues in staging:\n"
            + "\n".join([f"Line {issue['line']}: {issue['details']}" for issue in critical_issues])
        )
    
    @pytest.mark.unit
    @pytest.mark.deployment_critical
    def test_production_environment_config_validation(self):
        """
        CRITICAL: Test production environment template for Cloud Run compatibility.
        """
        production_env_file = self.project_root / '.env.production.template'
        
        if not production_env_file.exists():
            pytest.skip("Production environment template not found")
        
        with open(production_env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        validation_result = self.validator.validate_environment_config(env_content, 'production')
        
        # Log validation results
        self.log_test_result("production_env_config_validation", validation_result)
        
        # Assert production template is Cloud Run compatible
        assert validation_result['cloud_run_compatible'], (
            f"CRITICAL: Production environment template not Cloud Run compatible\n"
            f"Issues: {validation_result['issues']}"
        )
        
        # Assert no critical or high severity issues
        severe_issues = [issue for issue in validation_result['issues'] 
                        if issue.get('severity') in ['CRITICAL', 'HIGH']]
        
        assert len(severe_issues) == 0, (
            f"CRITICAL/HIGH: {len(severe_issues)} severe configuration issues in production template:\n"
            + "\n".join([f"Line {issue['line']}: {issue['details']}" for issue in severe_issues])
        )
    
    @pytest.mark.unit
    @pytest.mark.deployment_critical
    def test_docker_compose_staging_config_validation(self):
        """
        CRITICAL: Test staging Docker Compose configuration.
        """
        staging_compose_file = self.project_root / 'docker-compose.staging.yml'
        
        if not staging_compose_file.exists():
            pytest.skip("Staging Docker Compose file not found")
        
        with open(staging_compose_file, 'r', encoding='utf-8') as f:
            compose_content = f.read()
        
        validation_result = self.validator.validate_docker_compose_config(compose_content, 'staging')
        
        # Log validation results
        self.log_test_result("staging_compose_config_validation", validation_result)
        
        # Assert compose file is valid
        assert validation_result['valid'], (
            f"CRITICAL: Staging Docker Compose configuration invalid\n"
            f"Issues: {validation_result['issues']}"
        )
        
        # Assert Cloud Run compatibility
        assert validation_result['cloud_run_compatible'], (
            f"CRITICAL: Staging Docker Compose not Cloud Run compatible\n"
            f"Issues with Cloud Run conflicts: {[i for i in validation_result['issues'] if i.get('cloud_run_conflict')]}"
        )
        
        # Assert services were analyzed
        assert len(validation_result['services_analyzed']) > 0, (
            "No services found in staging Docker Compose file"
        )
    
    @pytest.mark.unit
    @pytest.mark.deployment_critical
    def test_deployment_script_validation(self):
        """
        CRITICAL: Test deployment scripts for Cloud Run compatibility.
        """
        deployment_scripts = [
            self.project_root / 'scripts' / 'deploy_to_gcp.py',
            # Add other deployment scripts as needed
        ]
        
        validation_results = []
        
        for script_file in deployment_scripts:
            if not script_file.exists():
                continue
                
            with open(script_file, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            validation_result = self.validator.validate_deployment_script_config(
                script_content, script_file.name
            )
            validation_results.append(validation_result)
            
            # Log individual script validation
            self.log_test_result(f"deployment_script_validation_{script_file.name}", validation_result)
        
        if not validation_results:
            pytest.skip("No deployment scripts found to validate")
        
        # Assert all scripts are Cloud Run compatible
        incompatible_scripts = [result for result in validation_results 
                               if not result['cloud_run_compatible']]
        
        assert len(incompatible_scripts) == 0, (
            f"CRITICAL: {len(incompatible_scripts)} deployment scripts not Cloud Run compatible\n"
            f"Scripts: {[s['script_file'] for s in incompatible_scripts]}\n"
            f"Issues: {[(s['script_file'], s['issues']) for s in incompatible_scripts]}"
        )
    
    @pytest.mark.unit
    @pytest.mark.deployment_critical
    def test_environment_configuration_consistency(self):
        """
        Test consistency across different environment configurations.
        
        Ensures staging and production have consistent configuration patterns.
        """
        env_files_to_check = [
            ('.env.staging', 'staging'),
            ('.env.production.template', 'production'),
            ('.env.test', 'test')
        ]
        
        all_validation_results = []
        
        for env_file_name, env_type in env_files_to_check:
            env_file_path = self.project_root / env_file_name
            
            if not env_file_path.exists():
                continue
            
            with open(env_file_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
            
            validation_result = self.validator.validate_environment_config(env_content, env_type)
            all_validation_results.append(validation_result)
        
        if not all_validation_results:
            pytest.skip("No environment files found for consistency check")
        
        # Generate recommendations
        recommendations = self.validator.generate_configuration_recommendations(all_validation_results)
        
        # Log recommendations
        self.log_test_result("environment_config_recommendations", recommendations)
        
        # Assert overall deployment readiness
        assert recommendations['overall_deployment_ready'], (
            f"CRITICAL: Deployment not ready due to configuration issues\n"
            f"Critical issues: {len(recommendations['critical_issues'])}\n"
            f"Compatibility score: {recommendations['cloud_run_compatibility_score']}\n"
            f"Details: {recommendations['critical_issues']}"
        )
        
        # Assert reasonable compatibility score
        assert recommendations['cloud_run_compatibility_score'] >= 0.8, (
            f"Cloud Run compatibility score too low: {recommendations['cloud_run_compatibility_score']}\n"
            f"Need at least 0.8 for reliable deployment\n"
            f"Critical issues to fix: {recommendations['critical_issues']}"
        )
    
    @pytest.mark.unit
    @pytest.mark.deployment_critical
    def test_mock_environment_validation_patterns(self):
        """
        Test environment validation with mock configurations to ensure validator works.
        
        This tests the validator logic itself with known good/bad configurations.
        """
        # Mock bad staging environment (should fail)
        bad_staging_env = """
# Bad staging configuration
PORT=8888
DEBUG=true
DATABASE_URL=localhost:5432
"""
        
        bad_validation = self.validator.validate_environment_config(bad_staging_env, 'staging')
        
        # Assert bad config is detected
        assert not bad_validation['cloud_run_compatible'], (
            "Validator failed to detect Cloud Run incompatible configuration"
        )
        assert not bad_validation['valid'], (
            "Validator failed to detect invalid configuration"
        )
        assert len(bad_validation['issues']) > 0, (
            "Validator failed to identify configuration issues"
        )
        
        # Mock good staging environment (should pass)
        good_staging_env = """
# Good staging configuration
DATABASE_URL=postgresql://production-db:5432
REDIS_URL=redis://production-redis:6379
DEBUG=false
"""
        
        good_validation = self.validator.validate_environment_config(good_staging_env, 'staging')
        
        # Assert good config passes
        assert good_validation['cloud_run_compatible'], (
            f"Validator incorrectly flagged good configuration as incompatible: {good_validation['issues']}"
        )
        
        # Log validation results
        self.log_test_result("mock_environment_validation", {
            'bad_config_detected': not bad_validation['valid'],
            'good_config_passed': good_validation['valid'],
            'bad_issues_count': len(bad_validation['issues']),
            'good_issues_count': len(good_validation['issues'])
        })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])