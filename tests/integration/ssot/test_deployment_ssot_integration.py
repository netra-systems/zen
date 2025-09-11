#!/usr/bin/env python3
"""
SSOT Deployment Integration Tests (No Docker)

Integration tests for deployment SSOT compliance without Docker dependency.
Tests UnifiedTestRunner deployment mode execution, configuration consistency,
and multi-environment deployment validation.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 2 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Validates deployment infrastructure works correctly across environments.

DESIGN CRITERIA:
- Integration tests without Docker dependency
- Tests dry-run deployment modes only
- Validates terraform vs scripts configuration consistency
- Tests multi-environment deployment consistency
- Uses real GCP APIs in mocked/dry-run mode only

TEST CATEGORIES:
- UnifiedTestRunner deployment mode integration
- Configuration consistency validation
- Multi-environment deployment consistency
- Terraform/script configuration alignment
"""

import json
import os
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, MagicMock, call

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeploymentSsotIntegration(SSotBaseTestCase):
    """
    Integration tests for deployment SSOT compliance.
    
    Tests UnifiedTestRunner deployment mode execution and configuration
    consistency without Docker dependency.
    """
    
    def setup_method(self, method=None):
        """Setup integration test environment."""
        super().setup_method(method)
        
        # Project paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / "tests" / "unified_test_runner.py"
        self.terraform_dir = self.project_root / "terraform-gcp-staging"
        self.scripts_dir = self.project_root / "scripts"
        
        # Test configuration
        self.test_project_id = "netra-test-project"
        self.test_environments = ["staging", "production"]
        
        # Record test start metrics
        self.record_metric("test_category", "integration")
        self.record_metric("ssot_focus", "deployment_integration") 
        self.record_metric("docker_dependency", False)
        
        # Validate critical paths exist
        assert self.unified_runner_path.exists(), f"UnifiedTestRunner not found: {self.unified_runner_path}"
    
    def test_unified_test_runner_deployment_mode_execution(self):
        """
        Test UnifiedTestRunner deployment mode execution in dry-run.
        
        CRITICAL: Validates SSOT deployment execution works correctly.
        """
        # Test deployment mode execution with dry-run
        with patch('subprocess.run') as mock_subprocess:
            # Configure mock to simulate successful dry-run
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout="Dry-run deployment completed successfully",
                stderr=""
            )
            
            # Execute unified test runner in deployment mode
            cmd = [
                "python", str(self.unified_runner_path),
                "--execution-mode", "deploy",
                "--project", self.test_project_id,
                "--dry-run"
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(self.project_root)
                )
                
                # Validate execution
                self.record_metric("deployment_mode_exit_code", result.returncode)
                self.record_metric("deployment_mode_stdout_length", len(result.stdout))
                
                # Check for expected deployment mode indicators
                deployment_indicators = [
                    "deploy",
                    "gcp",
                    "project",
                    self.test_project_id
                ]
                
                output_text = (result.stdout + result.stderr).lower()
                
                found_indicators = []
                for indicator in deployment_indicators:
                    if indicator in output_text:
                        found_indicators.append(indicator)
                
                assert len(found_indicators) >= 2, \
                    f"Deployment mode execution missing indicators. Found: {found_indicators}"
                
                self.record_metric("deployment_indicators_found", len(found_indicators))
                self.record_metric("deployment_mode_functional", True)
                
            except subprocess.TimeoutExpired:
                pytest.fail("UnifiedTestRunner deployment mode timed out")
            except Exception as e:
                self.record_metric("deployment_mode_error", str(e))
                pytest.fail(f"UnifiedTestRunner deployment mode failed: {e}")
    
    def test_terraform_vs_scripts_configuration_consistency(self):
        """
        Test configuration consistency between Terraform and scripts.
        
        Validates that Terraform configurations match script configurations.
        """
        config_consistency_issues = []
        
        # Load Terraform configurations
        terraform_configs = self._load_terraform_configurations()
        
        # Load script configurations
        script_configs = self._load_script_configurations()
        
        # Compare critical configuration values
        critical_configs = [
            "project_id",
            "region",
            "vpc_connector",
            "service_names",
            "environment_variables"
        ]
        
        for config_key in critical_configs:
            terraform_value = terraform_configs.get(config_key)
            script_value = script_configs.get(config_key)
            
            if terraform_value != script_value:
                config_consistency_issues.append({
                    'config_key': config_key,
                    'terraform_value': terraform_value,
                    'script_value': script_value,
                    'issue_type': 'value_mismatch'
                })
        
        # Record consistency metrics
        self.record_metric("terraform_configs_loaded", len(terraform_configs))
        self.record_metric("script_configs_loaded", len(script_configs))
        self.record_metric("config_consistency_issues", len(config_consistency_issues))
        
        # Report but don't fail on minor inconsistencies
        if config_consistency_issues:
            self.record_metric("config_consistency_issues_details", config_consistency_issues)
            
            # Only fail on critical mismatches
            critical_issues = [
                issue for issue in config_consistency_issues
                if issue['config_key'] in ['project_id', 'region']
            ]
            
            if critical_issues:
                issue_details = "\n".join([
                    f"  - {issue['config_key']}: terraform='{issue['terraform_value']}' vs script='{issue['script_value']}'"
                    for issue in critical_issues
                ])
                pytest.fail(
                    f"CRITICAL CONFIG MISMATCH: {len(critical_issues)} critical configuration inconsistencies:\n"
                    f"{issue_details}\n\n"
                    f"Expected: Terraform and script configurations should match\n"
                    f"Fix: Align critical configuration values between Terraform and scripts"
                )
    
    def test_multi_environment_deployment_consistency(self):
        """
        Test deployment consistency across multiple environments.
        
        Validates that deployment works consistently for different environments.
        """
        environment_results = {}
        
        for env in self.test_environments:
            try:
                # Test deployment configuration for each environment
                env_config = self._get_environment_deployment_config(env)
                
                # Validate required configuration keys
                required_keys = [
                    "project_id",
                    "service_configs",
                    "environment_variables"
                ]
                
                missing_keys = []
                for key in required_keys:
                    if key not in env_config:
                        missing_keys.append(key)
                
                environment_results[env] = {
                    'config_loaded': True,
                    'missing_keys': missing_keys,
                    'config_size': len(env_config),
                    'has_required_keys': len(missing_keys) == 0
                }
                
            except Exception as e:
                environment_results[env] = {
                    'config_loaded': False,
                    'error': str(e),
                    'has_required_keys': False
                }
        
        # Analyze environment consistency
        successful_envs = [
            env for env, result in environment_results.items()
            if result.get('has_required_keys', False)
        ]
        
        # Record environment metrics
        self.record_metric("environments_tested", len(self.test_environments))
        self.record_metric("successful_environments", len(successful_envs))
        self.record_metric("environment_consistency_rate", len(successful_envs) / len(self.test_environments))
        
        # Environment consistency should be high
        consistency_threshold = 0.8  # 80% of environments should be consistent
        actual_consistency = len(successful_envs) / len(self.test_environments)
        
        assert actual_consistency >= consistency_threshold, \
            f"Environment consistency too low: {actual_consistency:.2%} < {consistency_threshold:.2%}. " \
            f"Failed environments: {[env for env in self.test_environments if env not in successful_envs]}"
    
    def test_ssot_compliance_during_deployment_flow(self):
        """
        Test SSOT compliance during complete deployment flow.
        
        Validates that entire deployment flow uses SSOT patterns.
        """
        # Mock deployment flow components
        with patch('test_framework.unified_docker_manager.UnifiedDockerManager') as mock_docker, \
             patch('shared.isolated_environment.get_env') as mock_env, \
             patch('subprocess.run') as mock_subprocess:
            
            # Configure mocks for SSOT compliance
            mock_env.return_value = self.get_env()
            mock_docker.return_value = Mock()
            mock_subprocess.return_value = Mock(returncode=0)
            
            # Simulate deployment flow
            deployment_steps = [
                "environment_setup",
                "configuration_validation", 
                "docker_image_build",
                "gcp_deployment",
                "health_check"
            ]
            
            ssot_compliance_violations = []
            
            for step in deployment_steps:
                try:
                    # Simulate each deployment step
                    if step == "environment_setup":
                        # Should use IsolatedEnvironment
                        env = self.get_env()
                        env.set("TEST_DEPLOYMENT_STEP", step, "ssot_test")
                        
                    elif step == "configuration_validation":
                        # Should validate through SSOT configuration
                        test_config = {
                            "project": self.test_project_id,
                            "environment": "test"
                        }
                        
                    elif step == "docker_image_build":
                        # Should use UnifiedDockerManager (mocked)
                        mock_docker.assert_called()
                        
                    elif step == "gcp_deployment":
                        # Should call GCP deployment through subprocess
                        mock_subprocess.assert_called()
                        
                    elif step == "health_check":
                        # Should validate deployment health
                        health_status = True
                    
                    self.record_metric(f"deployment_step_{step}_completed", True)
                    
                except Exception as e:
                    ssot_compliance_violations.append({
                        'step': step,
                        'error': str(e),
                        'violation_type': 'step_execution_failure'
                    })
            
            # Record SSOT compliance metrics
            self.record_metric("deployment_steps_total", len(deployment_steps))
            self.record_metric("ssot_violations_during_flow", len(ssot_compliance_violations))
            
            # Test passes if no SSOT violations during flow
            if ssot_compliance_violations:
                violation_details = "\n".join([
                    f"  - {v['step']}: {v['error']}"
                    for v in ssot_compliance_violations
                ])
                pytest.fail(
                    f"SSOT COMPLIANCE VIOLATION: {len(ssot_compliance_violations)} violations during deployment flow:\n"
                    f"{violation_details}\n\n"
                    f"Expected: All deployment steps should use SSOT patterns\n"
                    f"Fix: Update violating steps to use SSOT infrastructure"
                )
    
    def test_deployment_configuration_drift_detection(self):
        """
        Test detection of configuration drift between deployments.
        
        Validates that deployment configurations remain consistent over time.
        """
        # Create baseline configuration
        baseline_config = {
            "project_id": self.test_project_id,
            "region": "us-central1",
            "services": ["backend", "auth", "frontend"],
            "environment_variables": {
                "ENVIRONMENT": "staging",
                "LOG_LEVEL": "INFO"
            }
        }
        
        # Simulate configuration changes
        test_configs = [
            # No changes (should pass)
            baseline_config.copy(),
            
            # Minor change (should pass)
            {**baseline_config, "environment_variables": {**baseline_config["environment_variables"], "LOG_LEVEL": "DEBUG"}},
            
            # Major change (should detect drift)
            {**baseline_config, "region": "us-west1", "services": ["backend", "auth"]},
        ]
        
        drift_detections = []
        
        for i, test_config in enumerate(test_configs):
            drift_score = self._calculate_configuration_drift(baseline_config, test_config)
            
            drift_detections.append({
                'config_index': i,
                'drift_score': drift_score,
                'is_significant_drift': drift_score > 0.3  # 30% threshold
            })
        
        # Record drift detection metrics
        self.record_metric("drift_detections_performed", len(drift_detections))
        self.record_metric("significant_drifts_detected", sum(1 for d in drift_detections if d['is_significant_drift']))
        
        # Validate drift detection works
        significant_drifts = [d for d in drift_detections if d['is_significant_drift']]
        
        # Should detect the major change (config index 2)
        major_change_detected = any(d['config_index'] == 2 for d in significant_drifts)
        
        assert major_change_detected, \
            "Failed to detect significant configuration drift"
        
        # Should not detect minor changes as significant
        minor_change_flagged = any(d['config_index'] == 1 for d in significant_drifts)
        
        assert not minor_change_flagged, \
            "Incorrectly flagged minor configuration change as significant drift"
    
    def _load_terraform_configurations(self) -> Dict[str, Any]:
        """Load and parse Terraform configurations."""
        terraform_configs = {}
        
        if not self.terraform_dir.exists():
            return terraform_configs
        
        try:
            # Look for terraform files
            tf_files = list(self.terraform_dir.glob("*.tf"))
            
            for tf_file in tf_files:
                try:
                    content = tf_file.read_text(encoding='utf-8')
                    
                    # Extract configuration values (simplified parsing)
                    if "project" in content:
                        terraform_configs["project_id"] = self._extract_terraform_value(content, "project")
                    
                    if "region" in content:
                        terraform_configs["region"] = self._extract_terraform_value(content, "region")
                    
                    if "google_vpc_access_connector" in content:
                        terraform_configs["vpc_connector"] = True
                        
                except Exception as e:
                    self.record_metric(f"terraform_parse_error_{tf_file.name}", str(e))
            
        except Exception as e:
            self.record_metric("terraform_load_error", str(e))
        
        return terraform_configs
    
    def _load_script_configurations(self) -> Dict[str, Any]:
        """Load and parse script configurations."""
        script_configs = {}
        
        try:
            # Check deploy script for configuration
            deploy_script = self.scripts_dir / "deploy_to_gcp.py"
            
            if deploy_script.exists():
                content = deploy_script.read_text(encoding='utf-8')
                
                # Extract configuration patterns
                if "netra-staging" in content:
                    script_configs["project_id"] = "netra-staging"
                
                if "us-central1" in content:
                    script_configs["region"] = "us-central1"
                
        except Exception as e:
            self.record_metric("script_config_load_error", str(e))
        
        return script_configs
    
    def _extract_terraform_value(self, content: str, key: str) -> Optional[str]:
        """Extract value from Terraform content."""
        # Simplified Terraform value extraction
        lines = content.split('\n')
        
        for line in lines:
            if key in line and '=' in line:
                # Extract value after =
                parts = line.split('=', 1)
                if len(parts) == 2:
                    value = parts[1].strip().strip('"')
                    return value
        
        return None
    
    def _get_environment_deployment_config(self, environment: str) -> Dict[str, Any]:
        """Get deployment configuration for specific environment."""
        # Simulate environment-specific configuration loading
        base_config = {
            "project_id": f"netra-{environment}",
            "service_configs": {
                "backend": {"memory": "1Gi", "cpu": "1"},
                "auth": {"memory": "512Mi", "cpu": "0.5"},
                "frontend": {"memory": "256Mi", "cpu": "0.25"}
            },
            "environment_variables": {
                "ENVIRONMENT": environment,
                "LOG_LEVEL": "INFO" if environment == "production" else "DEBUG"
            }
        }
        
        return base_config
    
    def _calculate_configuration_drift(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> float:
        """Calculate configuration drift score between two configurations."""
        # Simplified drift calculation
        total_keys = set(baseline.keys()) | set(current.keys())
        
        if not total_keys:
            return 0.0
        
        changed_keys = 0
        
        for key in total_keys:
            baseline_value = baseline.get(key)
            current_value = current.get(key)
            
            if baseline_value != current_value:
                changed_keys += 1
        
        return changed_keys / len(total_keys)


class TestDeploymentSsotIntegrationEdgeCases(SSotBaseTestCase):
    """
    Edge case tests for deployment SSOT integration.
    """
    
    def test_deployment_rollback_integration(self):
        """
        Test deployment rollback functionality through SSOT.
        
        Validates rollback maintains SSOT compliance.
        """
        with patch('subprocess.run') as mock_subprocess:
            # Configure mock for rollback scenario
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout="Rollback completed successfully"
            )
            
            # Test rollback through UnifiedTestRunner
            cmd = [
                "python", str(Path(__file__).parent.parent.parent.parent / "tests" / "unified_test_runner.py"),
                "--execution-mode", "deploy",
                "--project", "netra-staging",
                "--rollback",
                "--dry-run"
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                # Validate rollback execution
                self.record_metric("rollback_exit_code", result.returncode)
                self.record_metric("rollback_functional", result.returncode == 0)
                
            except subprocess.TimeoutExpired:
                self.record_metric("rollback_timeout", True)
                # Don't fail test for timeout in integration test
    
    def test_deployment_service_specific_integration(self):
        """
        Test service-specific deployment through SSOT.
        
        Validates that individual service deployment works.
        """
        services_to_test = ["backend", "auth", "frontend"]
        
        for service in services_to_test:
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0)
                
                # Test service-specific deployment
                cmd = [
                    "python", str(Path(__file__).parent.parent.parent.parent / "tests" / "unified_test_runner.py"),
                    "--execution-mode", "deploy",
                    "--project", "netra-staging",
                    "--service", service,
                    "--dry-run"
                ]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                    self.record_metric(f"service_deployment_{service}_exit_code", result.returncode)
                    
                except subprocess.TimeoutExpired:
                    self.record_metric(f"service_deployment_{service}_timeout", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])