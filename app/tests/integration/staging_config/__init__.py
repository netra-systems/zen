"""
Staging Configuration Integration Tests

Tests the integration between Terraform-provisioned resources,
deployment configurations, and runtime requirements in the
GCP staging environment.

These tests validate L3-L4 realism per testing.xml:
- L3: Real configurations, real GCP resources  
- L4: Full production-like staging environment
"""

from .test_secret_manager_integration import TestSecretManagerIntegration
from .test_terraform_deployment_consistency import TestTerraformDeploymentConsistency
from .test_cloud_sql_proxy import TestCloudSQLProxyConnectivity
from .test_staging_startup import TestStagingStartup
from .test_environment_precedence import TestEnvironmentPrecedence
from .test_multi_service_secrets import TestMultiServiceSecrets
from .test_redis_lifecycle import TestRedisLifecycle
from .test_database_migrations import TestDatabaseMigrations
from .test_health_checks import TestHealthChecks
from .test_websocket_load_balancer import TestWebSocketLoadBalancer
from .test_cors_configuration import TestCORSConfiguration
from .test_llm_integration import TestLLMIntegration
from .test_deployment_rollback import TestDeploymentRollback
from .test_observability_pipeline import TestObservabilityPipeline
from .test_resource_limits import TestResourceLimits

__all__ = [
    'TestSecretManagerIntegration',
    'TestTerraformDeploymentConsistency',
    'TestCloudSQLProxyConnectivity',
    'TestStagingStartup',
    'TestEnvironmentPrecedence',
    'TestMultiServiceSecrets',
    'TestRedisLifecycle',
    'TestDatabaseMigrations',
    'TestHealthChecks',
    'TestWebSocketLoadBalancer',
    'TestCORSConfiguration',
    'TestLLMIntegration',
    'TestDeploymentRollback',
    'TestObservabilityPipeline',
    'TestResourceLimits'
]