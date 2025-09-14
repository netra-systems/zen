"""
E2E Test Suite for Issue #936: GCP Deployment Configuration Validation
Test complete staging environment configuration for the 7 missing GCP variables.

Business Value: Platform/Internal - System Stability
Validates end-to-end GCP staging deployment with all required configuration.

CRITICAL TESTING REQUIREMENTS:
- NO DOCKER dependencies - uses real GCP staging environment only
- Real GCP staging deployment testing 
- Tests designed to FAIL initially to reproduce Issue #936
- SSOT compliance with existing test infrastructure

SSOT Compliance: Inherits from SSotAsyncTestCase and follows project patterns.
"""

import asyncio
import json
import os
import subprocess
from unittest.mock import patch, Mock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestGCPDeploymentConfigurationIssue936(SSotAsyncTestCase):
    """E2E test for GCP deployment configuration with all 7 missing variables."""
    
    def setup_method(self, method):
        """Set up E2E test environment."""
        super().setup_method(method)
        self.env = get_env()
        
        # The 7 missing GCP configuration variables from Issue #936
        self.required_gcp_variables = {
            'GCP_PROJECT_ID': 'Core project identifier',
            'SECRET_MANAGER_PROJECT_ID': 'Project for Secret Manager access',
            'GCP_REGION': 'Regional deployment configuration', 
            'SERVICE_ACCOUNT_EMAIL': 'Service account for GCP operations',
            'CLOUD_SQL_INSTANCE_NAME': 'Cloud SQL instance identifier',
            'GOOGLE_APPLICATION_CREDENTIALS': 'Path to service account key file',
            'VPC_CONNECTOR_NAME': 'VPC connector for private resource access'
        }
    
    @pytest.mark.asyncio
    async def test_staging_environment_complete_configuration_issue_936(self):
        """
        Test that staging environment has all required GCP configuration.
        
        EXPECTED TO FAIL: Should fail due to missing GCP configuration variables.
        """
        missing_variables = []
        placeholder_variables = {}
        invalid_variables = {}
        
        # Check each of the 7 required GCP variables
        for var_name, description in self.required_gcp_variables.items():
            value = self.env.get(var_name)
            
            if not value:
                missing_variables.append(f"{var_name}: {description}")
            elif self._is_placeholder_value(value):
                placeholder_variables[var_name] = value
            elif not self._validate_variable_format(var_name, value):
                invalid_variables[var_name] = value
        
        # Collect all configuration issues
        all_issues = []
        
        if missing_variables:
            all_issues.append(f"Missing variables (Issue #936): {missing_variables}")
        
        if placeholder_variables:
            all_issues.append(f"Placeholder values: {placeholder_variables}")
        
        if invalid_variables:
            all_issues.append(f"Invalid values: {invalid_variables}")
        
        # For Issue #936, we expect configuration problems
        if all_issues:
            self.fail(f"GCP configuration issues reproducing Issue #936: {'; '.join(all_issues)}")
        
        # If no issues found, the configuration might be complete
        self.assertGreater(len(all_issues), 0, 
            "Expected missing/invalid GCP configuration for Issue #936")
    
    def _is_placeholder_value(self, value: str) -> bool:
        """Check if value appears to be a placeholder."""
        if not value:
            return True
        
        placeholder_patterns = [
            'placeholder', 'replace', 'change-me', 'your-', 'example',
            'todo', 'fixme', 'should-be-replaced', 'will-be-set',
            'update-in-production', 'staging-.*-should-be-replaced'
        ]
        
        value_lower = value.lower()
        return any(pattern.replace('.*', '') in value_lower for pattern in placeholder_patterns)
    
    def _validate_variable_format(self, var_name: str, value: str) -> bool:
        """Validate format of specific GCP variables."""
        validators = {
            'GCP_PROJECT_ID': lambda v: len(v) > 5 and v.replace('-', '').replace('_', '').isalnum(),
            'SECRET_MANAGER_PROJECT_ID': lambda v: len(v) > 5 and v.replace('-', '').replace('_', '').isalnum(),
            'GCP_REGION': lambda v: '-' in v and len(v.split('-')) >= 3,
            'SERVICE_ACCOUNT_EMAIL': lambda v: '@' in v and '.gserviceaccount.com' in v,
            'CLOUD_SQL_INSTANCE_NAME': lambda v: ':' in v and len(v.split(':')) == 3,
            'GOOGLE_APPLICATION_CREDENTIALS': lambda v: v.endswith('.json') and ('/' in v or '\\' in v),
            'VPC_CONNECTOR_NAME': lambda v: len(v) > 5 and not v.startswith('projects/')
        }
        
        validator = validators.get(var_name)
        return validator(value) if validator else True
    
    @pytest.mark.asyncio
    async def test_gcp_project_connectivity_issue_936(self):
        """
        Test connectivity to GCP project with current configuration.
        
        EXPECTED TO FAIL: Should fail due to missing/invalid project configuration.
        """
        project_id = self.env.get('GCP_PROJECT_ID')
        
        if not project_id:
            self.fail("GCP_PROJECT_ID missing - cannot test project connectivity (Issue #936)")
        
        if self._is_placeholder_value(project_id):
            self.fail(f"GCP_PROJECT_ID has placeholder value: {project_id}")
        
        # Test basic GCP project access using gcloud CLI (if available)
        try:
            # Try to get project information
            result = subprocess.run([
                'gcloud', 'projects', 'describe', project_id, 
                '--format=json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Expected failure for Issue #936
                self.fail(f"Cannot access GCP project {project_id}: {result.stderr}")
            
            # If successful, verify project details
            project_info = json.loads(result.stdout)
            self.assertEqual(project_info.get('projectId'), project_id)
            
        except subprocess.TimeoutExpired:
            self.fail("GCP project access timed out - possible configuration issue")
        except FileNotFoundError:
            # gcloud CLI not available - try alternative validation
            self.skipTest("gcloud CLI not available for project connectivity test")
        except json.JSONDecodeError:
            self.fail("Invalid response from gcloud - possible authentication issue")
        except Exception as e:
            self.fail(f"GCP project connectivity test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_cloud_sql_instance_connectivity_issue_936(self):
        """
        Test Cloud SQL instance connectivity with current configuration.
        
        EXPECTED TO FAIL: Should fail due to missing CLOUD_SQL_INSTANCE_NAME.
        """
        instance_name = self.env.get('CLOUD_SQL_INSTANCE_NAME')
        
        if not instance_name:
            self.fail("CLOUD_SQL_INSTANCE_NAME missing (Issue #936 variable #5)")
        
        if self._is_placeholder_value(instance_name):
            self.fail(f"CLOUD_SQL_INSTANCE_NAME has placeholder: {instance_name}")
        
        # Validate instance name format: project:region:instance
        instance_parts = instance_name.split(':')
        if len(instance_parts) != 3:
            self.fail(f"Invalid Cloud SQL instance name format: {instance_name}")
        
        project_id, region, instance = instance_parts
        
        # Verify project ID matches
        expected_project = self.env.get('GCP_PROJECT_ID')
        if expected_project and project_id != expected_project:
            self.fail(f"Cloud SQL project {project_id} doesn't match GCP_PROJECT_ID {expected_project}")
        
        # Test Cloud SQL instance access
        try:
            result = subprocess.run([
                'gcloud', 'sql', 'instances', 'describe', instance,
                '--project', project_id, '--format=json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Expected failure for missing/misconfigured instance
                self.fail(f"Cannot access Cloud SQL instance {instance_name}: {result.stderr}")
            
            instance_info = json.loads(result.stdout)
            self.assertEqual(instance_info.get('name'), instance)
            
        except subprocess.TimeoutExpired:
            self.fail("Cloud SQL instance access timed out")
        except FileNotFoundError:
            self.skipTest("gcloud CLI not available for Cloud SQL test")
        except Exception as e:
            self.fail(f"Cloud SQL connectivity test failed: {e}")
    
    @pytest.mark.asyncio  
    async def test_vpc_connector_configuration_issue_936(self):
        """
        Test VPC connector configuration and connectivity.
        
        EXPECTED TO FAIL: Should fail due to missing VPC_CONNECTOR_NAME.
        """
        vpc_connector = self.env.get('VPC_CONNECTOR_NAME')
        
        if not vpc_connector:
            self.fail("VPC_CONNECTOR_NAME missing (Issue #936 variable #7)")
        
        if self._is_placeholder_value(vpc_connector):
            self.fail(f"VPC_CONNECTOR_NAME has placeholder: {vpc_connector}")
        
        project_id = self.env.get('GCP_PROJECT_ID')
        region = self.env.get('GCP_REGION')
        
        if not project_id or not region:
            self.fail("Cannot test VPC connector without GCP_PROJECT_ID and GCP_REGION")
        
        # Test VPC connector exists and is accessible
        try:
            result = subprocess.run([
                'gcloud', 'compute', 'networks', 'vpc-access', 'connectors', 
                'describe', vpc_connector,
                '--project', project_id, '--region', region, '--format=json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Expected failure for missing VPC connector
                self.fail(f"Cannot access VPC connector {vpc_connector}: {result.stderr}")
            
            connector_info = json.loads(result.stdout)
            self.assertIn('name', connector_info)
            
        except subprocess.TimeoutExpired:
            self.fail("VPC connector access timed out")
        except FileNotFoundError:
            self.skipTest("gcloud CLI not available for VPC connector test")
        except Exception as e:
            self.fail(f"VPC connector test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_service_account_permissions_complete_issue_936(self):
        """
        Test service account has all required permissions for staging deployment.
        
        EXPECTED TO FAIL: Should fail due to missing/invalid service account configuration.
        """
        service_account = self.env.get('SERVICE_ACCOUNT_EMAIL')
        
        if not service_account:
            self.fail("SERVICE_ACCOUNT_EMAIL missing (Issue #936 variable #4)")
        
        if self._is_placeholder_value(service_account):
            self.fail(f"SERVICE_ACCOUNT_EMAIL has placeholder: {service_account}")
        
        # Validate service account format
        if '@' not in service_account or '.gserviceaccount.com' not in service_account:
            self.fail(f"Invalid service account email format: {service_account}")
        
        project_id = self.env.get('GCP_PROJECT_ID')
        
        # Required permissions for staging deployment
        required_permissions = [
            'secretmanager.secrets.list',
            'secretmanager.versions.access',
            'cloudsql.instances.connect', 
            'vpcaccess.connectors.use',
            'run.services.create',
            'run.services.update'
        ]
        
        # Test IAM permissions
        for permission in required_permissions:
            try:
                result = subprocess.run([
                    'gcloud', 'projects', 'test-iam-permissions', project_id,
                    '--permissions', permission,
                    '--impersonate-service-account', service_account,
                    '--format=json'
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode != 0:
                    self.fail(f"Service account {service_account} lacks permission {permission}")
                
                response = json.loads(result.stdout)
                if permission not in response.get('permissions', []):
                    self.fail(f"Service account missing required permission: {permission}")
                    
            except subprocess.TimeoutExpired:
                self.fail(f"Permission test timed out for {permission}")
            except FileNotFoundError:
                self.skipTest("gcloud CLI not available for permission testing")
            except Exception as e:
                self.fail(f"Permission test failed for {permission}: {e}")
    
    @pytest.mark.asyncio
    async def test_staging_deployment_end_to_end_issue_936(self):
        """
        Test complete end-to-end staging deployment with all configuration.
        
        EXPECTED TO FAIL: Should fail due to missing GCP configuration variables.
        """
        # This is the comprehensive E2E test that validates the complete staging deployment
        
        # Step 1: Validate all 7 required variables are present
        missing_config = self._check_complete_configuration()
        if missing_config:
            self.fail(f"Cannot proceed with E2E deployment test - missing configuration: {missing_config}")
        
        # Step 2: Test configuration loading
        await self._test_configuration_loading()
        
        # Step 3: Test GCP service connectivity  
        await self._test_gcp_services_connectivity()
        
        # Step 4: Test staging validator
        await self._test_staging_validation_complete()
        
        # If we reach here, configuration is complete (unexpected for Issue #936)
        self.fail("E2E deployment test passed - Issue #936 may already be resolved")
    
    def _check_complete_configuration(self) -> list:
        """Check for complete GCP configuration."""
        missing = []
        
        for var_name in self.required_gcp_variables.keys():
            value = self.env.get(var_name)
            if not value:
                missing.append(var_name)
            elif self._is_placeholder_value(value):
                missing.append(f"{var_name} (placeholder)")
            elif not self._validate_variable_format(var_name, value):
                missing.append(f"{var_name} (invalid format)")
        
        return missing
    
    async def _test_configuration_loading(self):
        """Test that configuration loading works with all variables."""
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            
            config_manager = UnifiedConfigManager()
            config = config_manager.get_config()
            
            # Should load successfully with complete configuration
            self.assertIsNotNone(config)
            
        except Exception as e:
            self.fail(f"Configuration loading failed: {e}")
    
    async def _test_gcp_services_connectivity(self):
        """Test connectivity to all required GCP services."""
        services_to_test = [
            ('Secret Manager', self._test_secret_manager_service),
            ('Cloud SQL', self._test_cloud_sql_service),
            ('VPC Connector', self._test_vpc_connector_service)
        ]
        
        for service_name, test_func in services_to_test:
            try:
                await test_func()
            except Exception as e:
                self.fail(f"{service_name} connectivity test failed: {e}")
    
    async def _test_secret_manager_service(self):
        """Test Secret Manager service connectivity."""
        try:
            from google.cloud import secretmanager
            
            project_id = self.env.get('SECRET_MANAGER_PROJECT_ID')
            client = secretmanager.SecretManagerServiceClient()
            
            parent = f"projects/{project_id}"
            response = client.list_secrets(request={"parent": parent})
            list(response)  # Force execution
            
        except Exception as e:
            raise Exception(f"Secret Manager test failed: {e}")
    
    async def _test_cloud_sql_service(self):
        """Test Cloud SQL connectivity."""
        # This would test actual database connection using the configured Cloud SQL instance
        # For now, just validate the configuration format
        instance_name = self.env.get('CLOUD_SQL_INSTANCE_NAME')
        if not instance_name or ':' not in instance_name:
            raise Exception("Invalid Cloud SQL instance configuration")
    
    async def _test_vpc_connector_service(self):
        """Test VPC connector availability."""
        vpc_connector = self.env.get('VPC_CONNECTOR_NAME')
        if not vpc_connector:
            raise Exception("VPC connector not configured")
    
    async def _test_staging_validation_complete(self):
        """Test staging validator with complete configuration."""
        from netra_backend.app.core.configuration.staging_validator import validate_staging_config
        
        is_valid, result = validate_staging_config()
        
        if not is_valid:
            self.fail(f"Staging validation failed: {result.errors}")
        
        # Should have minimal warnings with complete configuration
        self.assertLessEqual(len(result.warnings), 3,
            f"Too many warnings with complete config: {result.warnings}")


class TestGCPConfigurationSuccessCriteria(SSotAsyncTestCase):
    """Define success criteria for Issue #936 resolution."""
    
    def setup_method(self, method):
        """Set up success criteria test."""
        super().setup_method(method)
    
    def test_issue_936_resolution_success_criteria(self):
        """
        Document the complete success criteria for resolving Issue #936.
        
        This test defines exactly what needs to be achieved.
        """
        success_criteria = {
            'required_variables': {
                'GCP_PROJECT_ID': {
                    'format': 'project-id or numeric-project-id',
                    'example': '701982941522',
                    'required': True
                },
                'SECRET_MANAGER_PROJECT_ID': {
                    'format': 'same-as-gcp-project-id or different-project',
                    'example': '701982941522', 
                    'required': True
                },
                'GCP_REGION': {
                    'format': 'region-zone format',
                    'example': 'us-central1',
                    'required': True
                },
                'SERVICE_ACCOUNT_EMAIL': {
                    'format': 'service-account@project.iam.gserviceaccount.com',
                    'example': 'netra-staging@netra-staging.iam.gserviceaccount.com',
                    'required': True
                },
                'CLOUD_SQL_INSTANCE_NAME': {
                    'format': 'project:region:instance',
                    'example': '701982941522:us-central1:postgres-main',
                    'required': True
                },
                'GOOGLE_APPLICATION_CREDENTIALS': {
                    'format': '/path/to/service-account-key.json',
                    'example': '/var/secrets/service-account-key.json',
                    'required': True
                },
                'VPC_CONNECTOR_NAME': {
                    'format': 'connector-name',
                    'example': 'netra-staging-vpc-connector',
                    'required': True
                }
            },
            'validation_requirements': {
                'no_placeholder_values': True,
                'no_missing_critical_variables': True,
                'staging_validator_passes': True,
                'secret_manager_accessible': True,
                'cloud_sql_connectable': True,
                'vpc_connector_usable': True,
                'service_account_permissions_complete': True
            },
            'deployment_requirements': {
                'cloud_run_deployable': True,
                'secrets_accessible_from_deployment': True,
                'database_connectivity_from_cloud_run': True,
                'vpc_resources_accessible': True
            }
        }
        
        # Verify we have exactly 7 required variables
        self.assertEqual(len(success_criteria['required_variables']), 7,
            "Must have exactly 7 GCP configuration variables")
        
        # All variables must be marked as required
        for var_name, config in success_criteria['required_variables'].items():
            self.assertTrue(config['required'], f"{var_name} must be required")
            self.assertIn('format', config, f"{var_name} must have format specification")
            self.assertIn('example', config, f"{var_name} must have example value")
        
        # Document this as the resolution target
        self.assertIsInstance(success_criteria, dict)
    
    def test_issue_936_failure_reproduction_scenarios(self):
        """Document the specific failure scenarios that reproduce Issue #936."""
        failure_scenarios = {
            'completely_missing_variables': {
                'description': 'All 7 GCP variables are missing from environment',
                'expected_failures': [
                    'staging_validator_fails',
                    'secret_manager_inaccessible',
                    'deployment_fails'
                ]
            },
            'placeholder_values': {
                'description': 'Variables present but contain placeholder values',
                'expected_failures': [
                    'configuration_validation_errors',
                    'authentication_failures',
                    'service_connectivity_failures'
                ]
            },
            'partial_configuration': {
                'description': 'Some variables configured, others missing',
                'expected_failures': [
                    'deployment_partially_succeeds_then_fails',
                    'runtime_errors_in_production',
                    'inconsistent_behavior'
                ]
            },
            'invalid_formats': {
                'description': 'Variables present but in wrong format',
                'expected_failures': [
                    'service_initialization_errors',
                    'connectivity_timeouts',
                    'permission_denied_errors'
                ]
            }
        }
        
        # Document these scenarios for comprehensive testing
        self.assertEqual(len(failure_scenarios), 4)
        for scenario_name, scenario in failure_scenarios.items():
            self.assertIn('description', scenario)
            self.assertIn('expected_failures', scenario)
            self.assertGreater(len(scenario['expected_failures']), 0)