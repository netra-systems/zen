"""
Staging Configuration Integration Tests

Tests the integration between Terraform-provisioned resources,
deployment configurations, and runtime requirements in the
GCP staging environment.

These tests validate L3-L4 realism per testing.xml:
- L3: Real configurations, real GCP resources  
- L4: Full production-like staging environment
"""

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