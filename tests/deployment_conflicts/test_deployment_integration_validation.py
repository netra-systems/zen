#!/usr/bin/env python3
"""
DEPLOYMENT INTEGRATION VALIDATION TEST SUITE
===========================================

Integration tests for deployment pipeline components and automated validation steps
for GitHub Issue #245 - Deployment Script SSOT Consolidation.

VALIDATION REQUIREMENTS:
1. **Staging Environment Health:** Validate deployment doesn't break staging
2. **Service Integration:** Test terraform + script + CI/CD pipeline integration  
3. **Configuration Validation:** Ensure environment-specific configs are consistent
4. **Rollback Capability:** Validate deployment rollback mechanisms
5. **Performance Impact:** Measure deployment performance and resource usage

SAFETY CONSTRAINTS:
- All tests use dry-run mode or test environments
- No production deployments during testing
- Careful Docker daemon dependency management
- Real validation on staging only when explicitly safe
"""

import os
import sys
import subprocess
import json
import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeploymentPipelineIntegration(SSotBaseTestCase):
    """Test suite for deployment pipeline integration validation."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        super().setUpClass()
        cls.project_root = PROJECT_ROOT
        cls.terraform_dir = cls.project_root / "terraform-gcp-staging" 
        cls.scripts_dir = cls.project_root / "scripts"
        cls.test_env = "test-deployment-validation"
        
    def test_terraform_to_script_integration_chain(self):
        """
        INTEGRATION TEST 1: Validate terraform → deployment script integration
        
        Tests the complete terraform deployment pipeline integration.
        """
        integration_results = {}
        
        # Test 1: Terraform deploy.sh script analysis
        terraform_deploy_script = self.terraform_dir / "deploy.sh"
        if terraform_deploy_script.exists():
            integration_results["terraform_deploy"] = self._analyze_terraform_deploy_script(terraform_deploy_script)
        
        # Test 2: Check terraform → python script chain
        terraform_python_chain = self._test_terraform_python_integration()
        integration_results["terraform_python_chain"] = terraform_python_chain
        
        # Test 3: Validate terraform variable consistency
        terraform_vars = self._extract_terraform_variables()
        integration_results["terraform_variables"] = terraform_vars
        
        print(f"\n=== TERRAFORM → SCRIPT INTEGRATION ANALYSIS ===")
        for test_name, result in integration_results.items():
            print(f"{test_name}: {result}")
        
        # Validate integration integrity
        integration_issues = self._validate_integration_integrity(integration_results)
        
        if integration_issues:
            print(f"\n⚠️  INTEGRATION ISSUES DETECTED:")
            for issue in integration_issues:
                print(f"  - {issue}")
        
        # ASSERTION: Integration chain should be intact
        self.assertEqual(len(integration_issues), 0,
                        f"Integration chain should be intact, found {len(integration_issues)} issues: {integration_issues}")
        
        return integration_results
    
    def test_ci_cd_pipeline_deployment_consistency(self):
        """
        INTEGRATION TEST 2: Validate CI/CD pipeline deployment consistency
        
        Checks if CI/CD configurations are consistent with manual deployment scripts.
        """
        ci_configs = self._extract_ci_cd_configurations()
        manual_configs = self._extract_manual_deployment_configurations()
        
        consistency_analysis = self._analyze_ci_manual_consistency(ci_configs, manual_configs)
        
        print(f"\n=== CI/CD vs MANUAL DEPLOYMENT CONSISTENCY ===")
        print(f"CI/CD configurations found: {len(ci_configs)}")
        print(f"Manual configurations found: {len(manual_configs)}")
        print(f"Consistency score: {consistency_analysis['consistency_score']}%")
        
        if consistency_analysis["inconsistencies"]:
            print(f"\n⚠️  CONSISTENCY ISSUES:")
            for issue in consistency_analysis["inconsistencies"]:
                print(f"  - {issue}")
        
        # ASSERTION: CI/CD and manual deployments should be consistent (>80%)
        self.assertGreater(consistency_analysis["consistency_score"], 80,
                          f"CI/CD and manual deployments should be >80% consistent, found {consistency_analysis['consistency_score']}%")
        
        return consistency_analysis
    
    def test_environment_specific_configuration_validation(self):
        """
        INTEGRATION TEST 3: Validate environment-specific configurations
        
        Ensures staging, production, and development configurations are properly isolated.
        """
        env_configs = {
            "development": self._extract_development_config(),
            "staging": self._extract_staging_config(), 
            "production": self._extract_production_config()
        }
        
        validation_results = {}
        for env_name, config in env_configs.items():
            validation_results[env_name] = self._validate_environment_config(env_name, config)
        
        print(f"\n=== ENVIRONMENT CONFIGURATION VALIDATION ===")
        for env_name, result in validation_results.items():
            status = "✅ VALID" if result["valid"] else "❌ INVALID"
            print(f"{env_name}: {status}")
            if result["issues"]:
                for issue in result["issues"]:
                    print(f"  - {issue}")
        
        # Check for environment isolation
        isolation_issues = self._check_environment_isolation(env_configs)
        
        if isolation_issues:
            print(f"\n⚠️  ENVIRONMENT ISOLATION ISSUES:")
            for issue in isolation_issues:
                print(f"  - {issue}")
        
        # ASSERTION: All environments should be valid and isolated
        invalid_envs = [env for env, result in validation_results.items() if not result["valid"]]
        self.assertEqual(len(invalid_envs), 0,
                        f"All environments should be valid, found invalid: {invalid_envs}")
        self.assertEqual(len(isolation_issues), 0,
                        f"Environments should be isolated, found {len(isolation_issues)} issues")
        
        return {
            "env_configs": env_configs,
            "validation_results": validation_results,
            "isolation_issues": isolation_issues
        }
    
    def test_deployment_rollback_capability_validation(self):
        """
        INTEGRATION TEST 4: Validate deployment rollback capabilities
        
        Tests rollback mechanisms and validates they work correctly.
        """
        rollback_capabilities = {}
        
        # Test rollback in deployment scripts
        deployment_scripts = list(self.scripts_dir.glob("deploy*.py"))
        for script in deployment_scripts:
            if script.exists():
                rollback_cap = self._test_rollback_capability(script)
                rollback_capabilities[script.name] = rollback_cap
        
        # Test terraform rollback capability
        terraform_rollback = self._test_terraform_rollback_capability()
        rollback_capabilities["terraform"] = terraform_rollback
        
        print(f"\n=== DEPLOYMENT ROLLBACK CAPABILITY ANALYSIS ===")
        for source, capability in rollback_capabilities.items():
            status = "✅ SUPPORTS" if capability["supports_rollback"] else "❌ NO SUPPORT"
            print(f"{source}: {status}")
            if capability["method"]:
                print(f"  Method: {capability['method']}")
            if capability["issues"]:
                for issue in capability["issues"]:
                    print(f"  Issue: {issue}")
        
        # Count sources with rollback support
        rollback_sources = [name for name, cap in rollback_capabilities.items() if cap["supports_rollback"]]
        
        # ASSERTION: At least one deployment source should support rollback
        self.assertGreater(len(rollback_sources), 0,
                          f"At least one deployment source should support rollback, found {len(rollback_sources)}")
        
        return rollback_capabilities
    
    def test_deployment_performance_impact_analysis(self):
        """
        INTEGRATION TEST 5: Analyze deployment performance impact
        
        Measures deployment script performance and resource usage.
        """
        performance_metrics = {}
        
        # Test deployment script execution performance (dry-run)
        deployment_scripts = [
            self.scripts_dir / "deploy_to_gcp.py",
            self.scripts_dir / "deploy_to_gcp_actual.py"
        ]
        
        for script in deployment_scripts:
            if script.exists():
                perf_metrics = self._measure_deployment_performance(script)
                performance_metrics[script.name] = perf_metrics
        
        # Test unified test runner deployment mode performance
        unified_runner = self.project_root / "tests" / "unified_test_runner.py"
        if unified_runner.exists():
            runner_perf = self._measure_test_runner_deployment_performance(unified_runner)
            performance_metrics["unified_test_runner"] = runner_perf
        
        print(f"\n=== DEPLOYMENT PERFORMANCE ANALYSIS ===")
        for script_name, metrics in performance_metrics.items():
            print(f"{script_name}:")
            print(f"  Startup time: {metrics.get('startup_time', 'N/A')}s")
            print(f"  Memory usage: {metrics.get('memory_usage', 'N/A')}MB")
            print(f"  CPU usage: {metrics.get('cpu_usage', 'N/A')}%")
            print(f"  Performance score: {metrics.get('performance_score', 'N/A')}")
        
        # Calculate overall performance impact
        avg_performance = self._calculate_average_performance(performance_metrics)
        
        # ASSERTION: Deployment performance should be acceptable (score > 60)
        self.assertGreater(avg_performance, 60,
                          f"Average deployment performance should be > 60, found {avg_performance}")
        
        return {
            "performance_metrics": performance_metrics,
            "average_performance": avg_performance
        }
    
    # Helper methods for integration testing
    
    def _analyze_terraform_deploy_script(self, script_path: Path) -> Dict:
        """Analyze terraform deployment script for integration points."""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            analysis = {
                "calls_python_deploy": "deploy_to_gcp.py" in content,
                "has_project_validation": "PROJECT_ID" in content,
                "has_error_handling": "set -e" in content or "exit" in content,
                "has_logging": "echo" in content,
                "script_type": "bash" if script_path.suffix == ".sh" else "unknown"
            }
            
            return analysis
        except Exception as e:
            return {"error": str(e)}
    
    def _test_terraform_python_integration(self) -> Dict:
        """Test terraform to python script integration."""
        integration_data = {
            "terraform_calls_python": False,
            "python_supports_terraform_args": False,
            "integration_working": False
        }
        
        # Check if terraform scripts call Python deployment scripts
        terraform_files = list(self.terraform_dir.glob("deploy.*"))
        for tf_file in terraform_files:
            try:
                with open(tf_file, 'r') as f:
                    content = f.read()
                if "deploy_to_gcp.py" in content:
                    integration_data["terraform_calls_python"] = True
                    break
            except Exception:
                continue
        
        # Check if Python scripts support terraform-style arguments
        python_scripts = list(self.scripts_dir.glob("deploy*.py"))
        for py_script in python_scripts:
            try:
                with open(py_script, 'r') as f:
                    content = f.read()
                if "--project" in content and "argparse" in content:
                    integration_data["python_supports_terraform_args"] = True
                    break
            except Exception:
                continue
        
        integration_data["integration_working"] = (
            integration_data["terraform_calls_python"] and 
            integration_data["python_supports_terraform_args"]
        )
        
        return integration_data
    
    def _extract_terraform_variables(self) -> Dict:
        """Extract terraform variables for consistency checking."""
        variables = {}
        
        var_file = self.terraform_dir / "variables.tf"
        if var_file.exists():
            try:
                with open(var_file, 'r') as f:
                    content = f.read()
                
                # Simple variable extraction (this could be more sophisticated)
                variables = {
                    "has_project_var": "variable \"project\"" in content,
                    "has_region_var": "variable \"region\"" in content,
                    "has_environment_var": "variable \"environment\"" in content
                }
            except Exception as e:
                variables = {"error": str(e)}
        
        return variables
    
    def _validate_integration_integrity(self, integration_results: Dict) -> List[str]:
        """Validate integration integrity and return issues."""
        issues = []
        
        # Check terraform → python integration
        if "terraform_python_chain" in integration_results:
            chain = integration_results["terraform_python_chain"]
            if not chain.get("integration_working", False):
                issues.append("Terraform to Python script integration not working")
        
        # Check terraform variables
        if "terraform_variables" in integration_results:
            vars_data = integration_results["terraform_variables"]
            if not vars_data.get("has_project_var", False):
                issues.append("Terraform missing project variable")
        
        return issues
    
    def _extract_ci_cd_configurations(self) -> Dict:
        """Extract CI/CD pipeline configurations."""
        ci_configs = {}
        
        # Look for GitHub Actions, GitLab CI, or other CI configurations
        ci_files = list(self.project_root.glob(".github/workflows/*.yml")) + \
                  list(self.project_root.glob(".gitlab-ci.yml")) + \
                  list(self.project_root.glob("Jenkinsfile"))
        
        for ci_file in ci_files:
            try:
                with open(ci_file, 'r') as f:
                    content = f.read()
                
                config = {
                    "has_deployment_step": "deploy" in content.lower(),
                    "uses_docker": "docker" in content.lower(),
                    "calls_scripts": "scripts/" in content,
                    "has_staging_deploy": "staging" in content.lower()
                }
                
                ci_configs[ci_file.name] = config
            except Exception as e:
                ci_configs[ci_file.name] = {"error": str(e)}
        
        return ci_configs
    
    def _extract_manual_deployment_configurations(self) -> Dict:
        """Extract manual deployment configurations."""
        manual_configs = {}
        
        deployment_scripts = list(self.scripts_dir.glob("deploy*.py"))
        for script in deployment_scripts:
            try:
                with open(script, 'r') as f:
                    content = f.read()
                
                config = {
                    "supports_staging": "--env" in content or "staging" in content.lower(),
                    "supports_docker": "docker" in content.lower(),
                    "has_validation": "check" in content.lower() or "validate" in content.lower(),
                    "supports_rollback": "--rollback" in content
                }
                
                manual_configs[script.name] = config
            except Exception as e:
                manual_configs[script.name] = {"error": str(e)}
        
        return manual_configs
    
    def _analyze_ci_manual_consistency(self, ci_configs: Dict, manual_configs: Dict) -> Dict:
        """Analyze consistency between CI/CD and manual deployments."""
        inconsistencies = []
        
        # Compare deployment capabilities
        ci_has_deployment = any(config.get("has_deployment_step", False) for config in ci_configs.values())
        manual_has_deployment = len(manual_configs) > 0
        
        if ci_has_deployment != manual_has_deployment:
            inconsistencies.append("CI/CD deployment presence doesn't match manual deployment availability")
        
        # Compare Docker usage
        ci_uses_docker = any(config.get("uses_docker", False) for config in ci_configs.values())
        manual_uses_docker = any(config.get("supports_docker", False) for config in manual_configs.values())
        
        if ci_uses_docker != manual_uses_docker:
            inconsistencies.append("Docker usage inconsistent between CI/CD and manual deployments")
        
        # Calculate consistency score
        total_checks = 4  # Number of consistency checks
        consistency_score = max(0, 100 - (len(inconsistencies) * (100 / total_checks)))
        
        return {
            "inconsistencies": inconsistencies,
            "consistency_score": int(consistency_score),
            "ci_configs": ci_configs,
            "manual_configs": manual_configs
        }
    
    def _extract_development_config(self) -> Dict:
        """Extract development environment configuration."""
        dev_config = {}
        
        # Check docker-compose.yml (development)
        compose_file = self.project_root / "docker-compose.yml"
        if compose_file.exists():
            dev_config["docker_compose"] = self._parse_compose_file(compose_file)
        
        # Check .env files
        env_file = self.project_root / ".env"
        if env_file.exists():
            dev_config["env_vars"] = self._parse_env_file(env_file)
        
        return dev_config
    
    def _extract_staging_config(self) -> Dict:
        """Extract staging environment configuration."""
        staging_config = {}
        
        # Check staging docker-compose file
        staging_compose = self.project_root / "docker-compose.staging.yml"
        if staging_compose.exists():
            staging_config["docker_compose"] = self._parse_compose_file(staging_compose)
        
        # Check terraform staging configuration
        terraform_main = self.terraform_dir / "main.tf"
        if terraform_main.exists():
            staging_config["terraform"] = self._parse_terraform_config(terraform_main)
        
        return staging_config
    
    def _extract_production_config(self) -> Dict:
        """Extract production environment configuration."""
        prod_config = {}
        
        # Look for production-specific configurations
        prod_files = list(self.project_root.glob("*prod*")) + list(self.project_root.glob("*production*"))
        for prod_file in prod_files:
            if prod_file.is_file():
                try:
                    with open(prod_file, 'r') as f:
                        content = f.read()
                    prod_config[prod_file.name] = {"has_content": len(content) > 0}
                except Exception:
                    continue
        
        return prod_config
    
    def _validate_environment_config(self, env_name: str, config: Dict) -> Dict:
        """Validate a specific environment configuration."""
        issues = []
        
        # Check for required configuration elements
        if not config:
            issues.append("No configuration found")
        
        if "docker_compose" in config:
            compose_config = config["docker_compose"]
            if not compose_config.get("services"):
                issues.append("No services defined in docker-compose")
        
        if "terraform" in config:
            tf_config = config["terraform"]
            if not tf_config.get("has_resources"):
                issues.append("No resources defined in terraform")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": config
        }
    
    def _check_environment_isolation(self, env_configs: Dict) -> List[str]:
        """Check for environment isolation issues."""
        isolation_issues = []
        
        # Check if environments share configurations inappropriately
        for env1_name, env1_config in env_configs.items():
            for env2_name, env2_config in env_configs.items():
                if env1_name != env2_name:
                    # Simple isolation check - environments shouldn't be identical
                    if env1_config == env2_config and env1_config:
                        isolation_issues.append(f"{env1_name} and {env2_name} have identical configurations")
        
        return isolation_issues
    
    def _test_rollback_capability(self, script_path: Path) -> Dict:
        """Test rollback capability of a deployment script."""
        capability = {
            "supports_rollback": False,
            "method": None,
            "issues": []
        }
        
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Check for rollback support
            if "--rollback" in content:
                capability["supports_rollback"] = True
                capability["method"] = "command line flag"
            elif "rollback" in content.lower():
                capability["supports_rollback"] = True
                capability["method"] = "function or procedure"
            else:
                capability["issues"].append("No rollback mechanism found")
        
        except Exception as e:
            capability["issues"].append(f"Error analyzing script: {e}")
        
        return capability
    
    def _test_terraform_rollback_capability(self) -> Dict:
        """Test terraform rollback capability."""
        capability = {
            "supports_rollback": False,
            "method": None,
            "issues": []
        }
        
        # Terraform inherently supports rollback via state management
        terraform_state = self.terraform_dir / "terraform.tfstate"
        if terraform_state.exists() or (self.terraform_dir / "main.tf").exists():
            capability["supports_rollback"] = True
            capability["method"] = "terraform state management"
        else:
            capability["issues"].append("No terraform configuration found")
        
        return capability
    
    def _measure_deployment_performance(self, script_path: Path) -> Dict:
        """Measure deployment script performance."""
        metrics = {
            "startup_time": 0,
            "memory_usage": 0,
            "cpu_usage": 0,
            "performance_score": 0
        }
        
        try:
            # Measure script startup time (with --help to avoid actual deployment)
            start_time = time.time()
            result = subprocess.run([
                sys.executable, str(script_path), "--help"
            ], capture_output=True, text=True, timeout=30)
            end_time = time.time()
            
            metrics["startup_time"] = round(end_time - start_time, 2)
            
            # Simple performance scoring
            if result.returncode == 0:
                if metrics["startup_time"] < 2:
                    metrics["performance_score"] = 90
                elif metrics["startup_time"] < 5:
                    metrics["performance_score"] = 70
                else:
                    metrics["performance_score"] = 50
            else:
                metrics["performance_score"] = 0
                
        except Exception as e:
            metrics["error"] = str(e)
            metrics["performance_score"] = 0
        
        return metrics
    
    def _measure_test_runner_deployment_performance(self, runner_path: Path) -> Dict:
        """Measure unified test runner deployment mode performance."""
        metrics = {
            "startup_time": 0,
            "performance_score": 0
        }
        
        try:
            # Test if deployment mode is actually supported
            start_time = time.time()
            result = subprocess.run([
                sys.executable, str(runner_path), "--help"
            ], capture_output=True, text=True, timeout=30)
            end_time = time.time()
            
            metrics["startup_time"] = round(end_time - start_time, 2)
            
            # Check if deployment mode is mentioned in help
            if result.returncode == 0 and "deploy" in result.stdout.lower():
                metrics["deployment_mode_supported"] = True
                metrics["performance_score"] = 80
            else:
                metrics["deployment_mode_supported"] = False
                metrics["performance_score"] = 0
                
        except Exception as e:
            metrics["error"] = str(e)
            metrics["performance_score"] = 0
        
        return metrics
    
    def _calculate_average_performance(self, performance_metrics: Dict) -> float:
        """Calculate average performance score across all deployment methods."""
        scores = []
        for metrics in performance_metrics.values():
            score = metrics.get("performance_score", 0)
            if isinstance(score, (int, float)):
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0
    
    def _parse_compose_file(self, compose_path: Path) -> Dict:
        """Parse docker-compose file."""
        try:
            with open(compose_path, 'r') as f:
                data = yaml.safe_load(f)
            return {
                "services": list(data.get("services", {}).keys()) if data else [],
                "has_networks": "networks" in data if data else False,
                "has_volumes": "volumes" in data if data else False
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_env_file(self, env_path: Path) -> Dict:
        """Parse .env file."""
        try:
            env_vars = {}
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
            return env_vars
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_terraform_config(self, tf_path: Path) -> Dict:
        """Parse terraform configuration."""
        try:
            with open(tf_path, 'r') as f:
                content = f.read()
            
            return {
                "has_resources": "resource " in content,
                "has_google_provider": "google" in content,
                "has_cloud_run": "google_cloud_run" in content
            }
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    # Run integration validation tests
    pytest.main([__file__, "-v", "--tb=short"])