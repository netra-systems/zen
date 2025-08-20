"""
Test Terraform-Deployment Consistency

Validates that Terraform-provisioned resources match
deployment script expectations.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Set
from .base import StagingConfigTestBase


class TestTerraformDeploymentConsistency(StagingConfigTestBase):
    """Test consistency between Terraform and deployment configurations."""
    
    def setUp(self):
        """Load Terraform and deployment configurations."""
        super().setUp()
        
        # Load Terraform outputs
        self.terraform_dir = Path('organized_root/terraform/staging')
        self.deployment_dir = Path('organized_root/deployment_configs')
        
    def test_resource_naming_consistency(self):
        """Verify resource names match between Terraform and deployment."""
        self.skip_if_not_staging()
        
        # Expected resource mappings
        resource_mappings = {
            'terraform': {
                'cloud_sql': 'postgres-staging',
                'redis': 'redis-staging', 
                'secret_prefix': 'jwt-secret',
                'service_account': 'netra-staging-sa',
                'artifact_registry': 'netra-staging'
            },
            'deployment': {
                'cloud_sql': 'postgres-staging',
                'redis': 'redis-staging',
                'secret_prefix': 'jwt-secret-staging',  # Mismatch!
                'service_account': 'netra-staging-sa',
                'artifact_registry': 'netra-staging'
            }
        }
        
        mismatches = []
        for resource, tf_name in resource_mappings['terraform'].items():
            deploy_name = resource_mappings['deployment'][resource]
            if tf_name != deploy_name:
                mismatches.append({
                    'resource': resource,
                    'terraform': tf_name,
                    'deployment': deploy_name
                })
                
        if mismatches:
            mismatch_str = '\n'.join([
                f"  - {m['resource']}: Terraform='{m['terraform']}', "
                f"Deployment='{m['deployment']}'"
                for m in mismatches
            ])
            self.fail(f"Resource naming mismatches:\n{mismatch_str}")
            
    def test_environment_variable_mapping(self):
        """Verify environment variables map correctly to resources."""
        self.skip_if_not_staging()
        
        # Load deployment config
        deploy_config_path = self.deployment_dir / 'staging_config.yaml'
        if deploy_config_path.exists():
            with open(deploy_config_path) as f:
                deploy_config = yaml.safe_load(f)
        else:
            deploy_config = {}
            
        # Expected environment variable mappings
        expected_env_vars = {
            'DATABASE_URL': {
                'secret': 'database-url',
                'format': 'postgresql://{user}:{password}@/cloudsql/{connection_name}/{database}'
            },
            'REDIS_URL': {
                'secret': 'redis-url', 
                'format': 'redis://{host}:6379/0'
            },
            'JWT_SECRET': {
                'secret': 'jwt-secret-staging',  # Should be 'jwt-secret'
                'format': None
            },
            'GCP_PROJECT_ID': {
                'value': self.project_id,
                'format': None
            }
        }
        
        # Verify each environment variable
        issues = []
        for var_name, config in expected_env_vars.items():
            if 'secret' in config:
                # Check if secret exists
                try:
                    self.assert_secret_exists(config['secret'])
                except AssertionError:
                    issues.append(f"{var_name} references non-existent secret '{config['secret']}'")
                    
        if issues:
            self.fail(f"Environment variable issues:\n" + '\n'.join(f"  - {i}" for i in issues))
            
    def test_kubernetes_manifests_consistency(self):
        """Verify Kubernetes manifests reference correct resources."""
        self.skip_if_not_staging()
        
        k8s_dir = self.deployment_dir / 'k8s' / 'staging'
        if not k8s_dir.exists():
            self.skipTest("Kubernetes manifests not found")
            
        issues = []
        
        for manifest_path in k8s_dir.glob('*.yaml'):
            with open(manifest_path) as f:
                manifests = yaml.safe_load_all(f)
                
                for manifest in manifests:
                    if not manifest:
                        continue
                        
                    # Check ConfigMaps and Secrets
                    if manifest.get('kind') == 'ConfigMap':
                        data = manifest.get('data', {})
                        
                        # Check database connection string
                        if 'DATABASE_URL' in data:
                            if 'jwt-secret-staging' in data['DATABASE_URL']:
                                issues.append(f"{manifest_path.name}: DATABASE_URL references wrong secret")
                                
                    # Check Deployment env vars
                    if manifest.get('kind') == 'Deployment':
                        containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                        
                        for container in containers:
                            env_vars = container.get('env', [])
                            
                            for env in env_vars:
                                # Check secret references
                                if env.get('valueFrom', {}).get('secretKeyRef'):
                                    secret_name = env['valueFrom']['secretKeyRef']['name']
                                    if secret_name == 'jwt-secret' and env['name'] == 'JWT_SECRET':
                                        # Deployment expects 'jwt-secret-staging'
                                        issues.append(f"{manifest_path.name}: JWT_SECRET references 'jwt-secret' instead of 'jwt-secret-staging'")
                                        
        if issues:
            self.fail(f"Kubernetes manifest issues:\n" + '\n'.join(f"  - {i}" for i in issues))
            
    def test_terraform_outputs_availability(self):
        """Verify Terraform outputs are available for deployment."""
        self.skip_if_not_staging()
        
        # Check if terraform output file exists
        tf_output_file = self.terraform_dir / 'terraform.tfstate'
        
        if not tf_output_file.exists():
            # Try to get outputs from Terraform
            import subprocess
            
            try:
                result = subprocess.run(
                    ['terraform', 'output', '-json'],
                    cwd=self.terraform_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    outputs = json.loads(result.stdout)
                    
                    # Verify critical outputs
                    required_outputs = [
                        'cloud_sql_connection_name',
                        'redis_host',
                        'artifact_registry_url',
                        'service_account_email',
                        'load_balancer_ip'
                    ]
                    
                    missing_outputs = []
                    for output in required_outputs:
                        if output not in outputs:
                            missing_outputs.append(output)
                            
                    if missing_outputs:
                        self.fail(f"Missing Terraform outputs: {missing_outputs}")
                        
            except Exception as e:
                self.fail(f"Failed to get Terraform outputs: {e}")
                
    def test_iam_role_consistency(self):
        """Verify IAM roles match between Terraform and deployment needs."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        # Expected IAM roles from Terraform
        terraform_roles = [
            'roles/secretmanager.secretAccessor',
            'roles/cloudsql.client',
            'roles/redis.editor',
            'roles/artifactregistry.reader',
            'roles/logging.logWriter',
            'roles/monitoring.metricWriter'
        ]
        
        # Roles required by deployment
        deployment_roles = [
            'roles/secretmanager.secretAccessor',
            'roles/cloudsql.client',
            'roles/redis.editor',
            'roles/artifactregistry.reader',
            'roles/logging.logWriter',
            'roles/monitoring.metricWriter',
            'roles/cloudtrace.agent'  # Often missing!
        ]
        
        # Find missing roles
        missing_roles = set(deployment_roles) - set(terraform_roles)
        
        if missing_roles:
            self.fail(f"Deployment requires IAM roles not provisioned by Terraform: {missing_roles}")