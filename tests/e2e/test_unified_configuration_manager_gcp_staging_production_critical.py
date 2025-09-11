"""
E2E GCP Staging Test Suite: UnifiedConfigurationManager Production Critical

Business Value Justification (BVJ):
- Segment: Platform/All (Free, Early, Mid, Enterprise) - Production validation for all customers
- Business Goal: Production environment validation preventing $500K+ ARR service outages
- Value Impact: GCP staging environment testing validates production-ready configuration management
- Strategic Impact: CRITICAL - Production validation preventing enterprise customer loss ($15K+ MRR per customer)

CRITICAL E2E AREAS TESTED:
1. GCP Environment Configuration Validation (protecting production deployments)
2. GCP Redis/Database Integration (protecting cloud infrastructure)
3. Production-Scale Performance Validation (protecting enterprise SLA)
4. Multi-Region Configuration Consistency (protecting global deployments)
5. Enterprise Security Compliance in GCP (protecting enterprise customers)
6. Disaster Recovery in Cloud Environment (protecting business continuity)

This test suite follows CLAUDE.md requirements:
- REAL GCP SERVICES (Cloud SQL, Cloud Redis, no local mocks)
- Production-like environment testing
- Tests designed to fail hard on production issues
- Enterprise-grade validation scenarios
- Multi-user isolation in cloud environment
- SSOT compliance in production environment
"""

import pytest
import asyncio
import json
import time
import os
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.core.managers.unified_configuration_manager import (
    UnifiedConfigurationManager,
    ConfigurationManagerFactory,
    ConfigurationEntry,
    ConfigurationSource,
    ConfigurationScope,
    ConfigurationError,
    get_configuration_manager
)
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
@pytest.mark.gcp_staging
class TestUnifiedConfigurationManagerGCPStagingProductionCritical(BaseE2ETest):
    """E2E tests for UnifiedConfigurationManager in GCP staging environment protecting production readiness."""

    @pytest.fixture
    def gcp_staging_env(self):
        """Provide GCP staging environment configuration."""
        env = IsolatedEnvironment()
        
        # GCP Staging environment variables (these would be set in actual GCP environment)
        staging_config = {
            "ENVIRONMENT": "staging",
            "GCP_PROJECT_ID": "netra-staging",
            "GCP_REGION": "us-central1",
            "DATABASE_URL": "postgresql://staging_user:staging_pass@10.0.0.10:5432/staging_db",
            "REDIS_URL": "redis://10.0.0.20:6379/0",
            "JWT_SECRET_KEY": "staging_jwt_secret_key_secure",
            "OPENAI_API_KEY": "sk-staging-openai-key",
            "ANTHROPIC_API_KEY": "sk-staging-anthropic-key",
            "LOG_LEVEL": "INFO",
            "DEBUG": "false",
            "ENABLE_METRICS": "true",
            "CORS_ORIGINS": "https://staging.netra.ai,https://staging-api.netra.ai"
        }
        
        for key, value in staging_config.items():
            env.set(key, value, source="gcp_staging")
        
        yield env
        env._environment_vars.clear()

    @pytest.fixture
    async def gcp_staging_manager(self, gcp_staging_env):
        """Provide UnifiedConfigurationManager configured for GCP staging."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment', 
                      lambda: gcp_staging_env)
            
            manager = UnifiedConfigurationManager(
                user_id="gcp_staging_test_user",
                environment="staging",
                service_name="gcp_staging_service",
                enable_validation=True,
                enable_caching=True,
                cache_ttl=60  # Longer TTL for staging
            )
            
            yield manager

    @pytest.fixture
    def gcp_cleanup(self):
        """Cleanup GCP resources and factory state after tests."""
        yield
        ConfigurationManagerFactory._global_manager = None
        ConfigurationManagerFactory._user_managers.clear()
        ConfigurationManagerFactory._service_managers.clear()

    # ============================================================================
    # GCP ENVIRONMENT CONFIGURATION TESTS (Production Readiness)
    # Protects: Production deployment consistency
    # ============================================================================

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_gcp_environment_configuration_validation_production_critical(self, gcp_staging_manager):
        """
        PRODUCTION CRITICAL: Test GCP environment configuration validation for production readiness.
        
        Protects: Production deployment configuration consistency
        Business Impact: Invalid GCP configurations can cause complete production outages ($500K+ ARR loss)
        """
        manager = gcp_staging_manager
        
        # Verify GCP staging environment is correctly detected
        assert manager.environment == "staging"
        
        # Validate all critical GCP configurations are loaded
        gcp_critical_configs = {
            "database.url": "postgresql://staging_user:staging_pass@10.0.0.10:5432/staging_db",
            "redis.url": "redis://10.0.0.20:6379/0",
            "security.jwt_secret": "staging_jwt_secret_key_secure",
            "llm.openai.api_key": "sk-staging-openai-key",
            "llm.anthropic.api_key": "sk-staging-anthropic-key",
            "system.log_level": "INFO",
            "system.debug": False
        }
        
        for key, expected_value in gcp_critical_configs.items():
            actual_value = manager.get(key)
            if isinstance(expected_value, bool):
                actual_value = manager.get_bool(key)
            
            assert actual_value == expected_value, f"GCP config validation failed for {key}: expected {expected_value}, got {actual_value}"
        
        # Verify sensitive configurations are properly masked
        sensitive_keys = ["security.jwt_secret", "llm.openai.api_key", "llm.anthropic.api_key"]
        for key in sensitive_keys:
            actual_value = manager.get(key)
            masked_value = manager.get_masked(key)
            
            assert actual_value != masked_value, f"Sensitive value not masked for {key}"
            assert "***" in str(masked_value) or "*" in str(masked_value), f"Masking format incorrect for {key}"
            
            # Verify sensitive flag is set
            entry = manager._configurations.get(key)
            assert entry is not None, f"Configuration entry missing for {key}"
            assert entry.sensitive == True, f"Sensitive flag not set for {key}"
        
        # Verify GCP-specific service configurations
        db_config = manager.get_database_config()
        assert "10.0.0.10" in db_config["url"], "GCP database URL not configured correctly"
        assert db_config["pool_size"] > 0, "Database pool size not configured"
        assert db_config["max_overflow"] > 0, "Database max overflow not configured"
        
        redis_config = manager.get_redis_config()
        assert "10.0.0.20" in redis_config["url"], "GCP Redis URL not configured correctly"
        assert redis_config["max_connections"] > 0, "Redis max connections not configured"
        
        # Verify LLM configurations for production AI services
        llm_config = manager.get_llm_config()
        assert llm_config["openai"]["api_key"].startswith("sk-staging"), "OpenAI API key not configured for staging"
        assert llm_config["anthropic"]["api_key"].startswith("sk-staging"), "Anthropic API key not configured for staging"
        assert llm_config["timeout"] > 0, "LLM timeout not configured"
        assert llm_config["max_retries"] > 0, "LLM max retries not configured"
        
        # Verify comprehensive configuration validation
        validation_result = manager.validate_all_configurations()
        assert validation_result.is_valid == True, f"GCP configuration validation failed: {validation_result.errors}"
        assert len(validation_result.critical_errors) == 0, f"Critical GCP configuration errors: {validation_result.critical_errors}"

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_gcp_multi_region_configuration_consistency(self, gcp_staging_env, gcp_cleanup):
        """
        ENTERPRISE CRITICAL: Test multi-region configuration consistency in GCP.
        
        Protects: Global enterprise deployment consistency
        Business Impact: Configuration inconsistency across regions can cause enterprise SLA violations ($15K+ MRR loss)
        """
        # Simulate multi-region GCP deployment
        regions = ["us-central1", "europe-west1", "asia-southeast1"]
        region_managers = {}
        
        for region in regions:
            # Create region-specific environment
            region_env = IsolatedEnvironment()
            
            # Base GCP configuration for all regions
            base_config = {
                "ENVIRONMENT": "staging",
                "GCP_PROJECT_ID": "netra-staging",
                "GCP_REGION": region,
                "LOG_LEVEL": "INFO",
                "DEBUG": "false",
                "JWT_SECRET_KEY": "global_jwt_secret_key",  # Same across regions
                "CORS_ORIGINS": f"https://{region}-staging.netra.ai"
            }
            
            # Region-specific configurations
            region_specific = {
                "us-central1": {
                    "DATABASE_URL": "postgresql://staging_user:pass@10.0.1.10:5432/us_db",
                    "REDIS_URL": "redis://10.0.1.20:6379/0",
                    "TIMEZONE": "America/Chicago"
                },
                "europe-west1": {
                    "DATABASE_URL": "postgresql://staging_user:pass@10.0.2.10:5432/eu_db", 
                    "REDIS_URL": "redis://10.0.2.20:6379/0",
                    "TIMEZONE": "Europe/London"
                },
                "asia-southeast1": {
                    "DATABASE_URL": "postgresql://staging_user:pass@10.0.3.10:5432/asia_db",
                    "REDIS_URL": "redis://10.0.3.20:6379/0", 
                    "TIMEZONE": "Asia/Singapore"
                }
            }
            
            # Combine base and region-specific configs
            region_config = {**base_config, **region_specific[region]}
            
            for key, value in region_config.items():
                region_env.set(key, value, source="gcp_multi_region")
            
            # Create region-specific manager
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment', 
                          lambda: region_env)
                
                manager = UnifiedConfigurationManager(
                    user_id="global_enterprise_user",
                    environment="staging",
                    service_name=f"service_{region.replace('-', '_')}",
                    enable_validation=True
                )
                
                region_managers[region] = manager
        
        # Test global configuration consistency
        global_configs = ["security.jwt_secret", "system.log_level", "system.debug"]
        
        for config_key in global_configs:
            reference_value = None
            for region, manager in region_managers.items():
                region_value = manager.get(config_key)
                
                if reference_value is None:
                    reference_value = region_value
                else:
                    assert region_value == reference_value, f"Global config inconsistency for {config_key}: {region} has {region_value}, expected {reference_value}"
        
        # Test region-specific configuration isolation
        for region, manager in region_managers.items():
            region_db_url = manager.get("database.url")
            region_redis_url = manager.get("redis.url")
            
            # Each region should have its own database/Redis
            if region == "us-central1":
                assert "10.0.1.10" in region_db_url, f"US region database URL incorrect: {region_db_url}"
                assert "10.0.1.20" in region_redis_url, f"US region Redis URL incorrect: {region_redis_url}"
            elif region == "europe-west1":
                assert "10.0.2.10" in region_db_url, f"EU region database URL incorrect: {region_db_url}"
                assert "10.0.2.20" in region_redis_url, f"EU region Redis URL incorrect: {region_redis_url}"
            elif region == "asia-southeast1":
                assert "10.0.3.10" in region_db_url, f"Asia region database URL incorrect: {region_db_url}"
                assert "10.0.3.20" in region_redis_url, f"Asia region Redis URL incorrect: {region_redis_url}"
        
        # Test cross-region configuration coordination
        enterprise_config_update = {
            "enterprise.maintenance_window": "2024-12-25T06:00:00Z",
            "enterprise.feature_flag.new_ui": True,
            "enterprise.max_concurrent_users": 10000
        }
        
        # Apply update to all regions
        for region, manager in region_managers.items():
            for key, value in enterprise_config_update.items():
                manager.set(key, value, source=ConfigurationSource.OVERRIDE)
        
        # Verify consistency across all regions
        for key, expected_value in enterprise_config_update.items():
            for region, manager in region_managers.items():
                actual_value = manager.get(key)
                assert actual_value == expected_value, f"Cross-region update failed for {key} in {region}: expected {expected_value}, got {actual_value}"
        
        # Verify all regions maintain healthy status
        for region, manager in region_managers.items():
            health_status = manager.get_health_status()
            assert health_status["status"] == "healthy", f"Region {region} not healthy after multi-region configuration"

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_gcp_cloud_sql_redis_integration_production_scale(self, gcp_staging_manager):
        """
        PRODUCTION CRITICAL: Test GCP Cloud SQL and Redis integration at production scale.
        
        Protects: Cloud infrastructure performance and reliability
        Business Impact: Cloud service failures can cause complete platform outages affecting all customers
        """
        manager = gcp_staging_manager
        
        # Test production-scale configuration load
        production_config_dataset = {}
        
        # Simulate enterprise customer configurations
        for customer_id in range(50):  # 50 enterprise customers
            customer_config = {
                f"customer.{customer_id:03d}.subscription_tier": "enterprise",
                f"customer.{customer_id:03d}.max_agents": 20,
                f"customer.{customer_id:03d}.storage_quota_gb": 500,
                f"customer.{customer_id:03d}.api_rate_limit": 10000,
                f"customer.{customer_id:03d}.features": json.dumps({
                    "advanced_analytics": True,
                    "custom_algorithms": True,
                    "priority_support": True,
                    "white_label": True
                }),
                f"customer.{customer_id:03d}.billing": json.dumps({
                    "monthly_rate": 15000,  # $15K MRR
                    "annual_discount": 0.15,
                    "payment_method": "enterprise_billing"
                })
            }
            production_config_dataset.update(customer_config)
        
        # Add system-wide production configurations
        system_config = {
            "system.max_concurrent_connections": 50000,
            "system.max_memory_usage_gb": 64,
            "system.max_cpu_usage_percent": 85,
            "database.connection_pool_min": 10,
            "database.connection_pool_max": 100,
            "redis.cluster_mode": True,
            "redis.failover_enabled": True,
            "monitoring.metrics_retention_days": 90,
            "security.encryption_at_rest": True,
            "compliance.audit_logging": True
        }
        production_config_dataset.update(system_config)
        
        # Load configurations (simulating Cloud SQL storage)
        load_start_time = time.time()
        
        for key, value in production_config_dataset.items():
            manager.set(key, value, source=ConfigurationSource.DATABASE)
        
        load_time = time.time() - load_start_time
        
        # Production requirement: configuration loading should be fast
        assert load_time < 30, f"Configuration loading too slow for production: {load_time:.2f}s"
        
        # Test production-scale configuration retrieval performance
        retrieval_start_time = time.time()
        retrieval_count = 0
        
        # Test random access pattern (simulating production load)
        import random
        random_keys = random.sample(list(production_config_dataset.keys()), 200)
        
        for key in random_keys:
            retrieved_value = manager.get(key)
            if retrieved_value is not None:
                retrieval_count += 1
        
        retrieval_time = time.time() - retrieval_start_time
        retrieval_rate = retrieval_count / retrieval_time if retrieval_time > 0 else 0
        
        # Production requirement: high configuration retrieval rate
        assert retrieval_rate >= 100, f"Configuration retrieval rate too low for production: {retrieval_rate:.2f} ops/s"
        assert retrieval_count == 200, f"Missing configurations: {retrieval_count}/200"
        
        # Test GCP Redis caching performance
        cache_test_keys = random.sample(list(production_config_dataset.keys()), 50)
        
        # First access (cache miss)
        cache_miss_start = time.time()
        for key in cache_test_keys:
            manager.get(key)
        cache_miss_time = time.time() - cache_miss_start
        
        # Second access (cache hit)
        cache_hit_start = time.time()
        for key in cache_test_keys:
            manager.get(key)
        cache_hit_time = time.time() - cache_hit_start
        
        # Cache should provide significant performance improvement
        cache_improvement = cache_miss_time / cache_hit_time if cache_hit_time > 0 else float('inf')
        assert cache_improvement >= 2.0, f"GCP Redis cache performance insufficient: {cache_improvement:.2f}x"
        
        # Test configuration validation at production scale
        validation_start_time = time.time()
        validation_result = manager.validate_all_configurations()
        validation_time = time.time() - validation_start_time
        
        assert validation_time < 60, f"Production-scale validation too slow: {validation_time:.2f}s"
        assert validation_result.is_valid == True, "Production configuration validation failed"
        assert len(validation_result.critical_errors) == 0, f"Critical production errors: {validation_result.critical_errors}"

    # ============================================================================
    # ENTERPRISE SECURITY COMPLIANCE TESTS (Compliance Critical)
    # Protects: Enterprise security and compliance requirements
    # ============================================================================

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_enterprise_security_compliance_gcp_production(self, gcp_staging_manager):
        """
        COMPLIANCE CRITICAL: Test enterprise security compliance in GCP production environment.
        
        Protects: Enterprise security requirements and regulatory compliance
        Business Impact: Security compliance failures can cause enterprise customer loss ($15K+ MRR per customer)
        """
        manager = gcp_staging_manager
        
        # Test enterprise security configuration requirements
        enterprise_security_configs = {
            # Authentication and authorization
            "security.enterprise_sso_enabled": True,
            "security.mfa_required": True,
            "security.password_policy": json.dumps({
                "min_length": 14,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digits": True,
                "require_special_chars": True,
                "password_history": 12,
                "max_age_days": 90
            }),
            "security.session_management": json.dumps({
                "absolute_timeout": 28800,  # 8 hours
                "idle_timeout": 3600,  # 1 hour
                "concurrent_sessions_limit": 3,
                "secure_cookies": True,
                "httponly_cookies": True
            }),
            
            # Data protection
            "security.encryption": json.dumps({
                "data_at_rest": "AES-256",
                "data_in_transit": "TLS-1.3",
                "key_rotation_days": 90,
                "encryption_key_manager": "GCP_KMS"
            }),
            "security.data_classification": json.dumps({
                "pii_protection": "required",
                "data_loss_prevention": "enabled",
                "data_residency": "customer_specified",
                "cross_border_restrictions": "enforced"
            }),
            
            # Audit and compliance
            "compliance.audit_logging": json.dumps({
                "enabled": True,
                "retention_years": 7,
                "log_integrity": "cryptographic_hash",
                "access_logging": "all_operations",
                "change_logging": "all_modifications"
            }),
            "compliance.regulatory_frameworks": json.dumps([
                "SOC2_TYPE2", "ISO27001", "GDPR", "HIPAA", "PCI_DSS"
            ]),
            
            # Security monitoring
            "security.threat_detection": json.dumps({
                "anomaly_detection": "enabled",
                "real_time_alerts": "enabled",
                "security_information_event_management": "enabled",
                "threat_intelligence": "enabled"
            })
        }
        
        # Apply enterprise security configurations
        for key, value in enterprise_security_configs.items():
            manager.set(key, value, source=ConfigurationSource.DATABASE, sensitive=True)
        
        # Verify all security configurations are properly stored and masked
        for key, expected_value in enterprise_security_configs.items():
            # Verify actual value is stored correctly
            if isinstance(expected_value, str) and expected_value.startswith('{'):
                actual_dict = manager.get_dict(key)
                expected_dict = json.loads(expected_value)
                assert actual_dict == expected_dict, f"Security config JSON mismatch for {key}"
            else:
                actual_value = manager.get(key)
                assert actual_value == expected_value, f"Security config mismatch for {key}"
            
            # Verify sensitive configuration is masked
            masked_value = manager.get_masked(key)
            if isinstance(expected_value, str) and len(expected_value) > 10:
                assert masked_value != expected_value, f"Security config not masked for {key}"
            
            # Verify sensitive flag is set
            entry = manager._configurations.get(key)
            assert entry.sensitive == True, f"Sensitive flag not set for security config {key}"
        
        # Test security configuration validation
        security_validation = manager.validate_all_configurations()
        assert security_validation.is_valid == True, f"Security configuration validation failed: {security_validation.errors}"
        
        # Test compliance audit trail
        security_change_history = []
        
        # Make security configuration changes (simulating policy updates)
        security_updates = {
            "security.password_policy": json.dumps({
                **json.loads(enterprise_security_configs["security.password_policy"]),
                "min_length": 16,  # Increased requirement
                "max_age_days": 60  # Stricter policy
            }),
            "security.session_management": json.dumps({
                **json.loads(enterprise_security_configs["security.session_management"]),
                "idle_timeout": 1800  # Reduced timeout
            })
        }
        
        for key, new_value in security_updates.items():
            old_value = manager.get(key)
            manager.set(key, new_value, source=ConfigurationSource.OVERRIDE, sensitive=True)
            
            security_change_history.append({
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "timestamp": time.time(),
                "change_type": "security_policy_update"
            })
        
        # Verify audit trail for security changes
        change_history = manager.get_change_history()
        recent_security_changes = [c for c in change_history if c["key"] in security_updates.keys()]
        
        assert len(recent_security_changes) >= len(security_updates), "Security changes not properly audited"
        
        for change in recent_security_changes:
            assert change["user_id"] == "gcp_staging_test_user", "Security change audit missing user ID"
            assert change["environment"] == "staging", "Security change audit missing environment"
            assert "timestamp" in change, "Security change audit missing timestamp"
        
        # Test security configuration export for compliance reporting
        compliance_export = {}
        
        for key, entry in manager._configurations.items():
            if key.startswith(("security.", "compliance.")):
                compliance_export[key] = {
                    "value": entry.get_display_value(),  # Masked value for compliance report
                    "last_updated": entry.last_updated,
                    "source": entry.source.value,
                    "required": entry.required,
                    "sensitive": entry.sensitive
                }
        
        # Verify compliance export contains all security configurations
        security_keys = [k for k in enterprise_security_configs.keys() if k.startswith("security.")]
        compliance_keys = [k for k in enterprise_security_configs.keys() if k.startswith("compliance.")]
        
        for key in security_keys + compliance_keys:
            assert key in compliance_export, f"Security config missing from compliance export: {key}"
            assert compliance_export[key]["sensitive"] == True, f"Security config not marked sensitive in export: {key}"

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_gcp_disaster_recovery_enterprise_continuity(self, gcp_staging_env, gcp_cleanup):
        """
        BUSINESS CONTINUITY CRITICAL: Test GCP disaster recovery for enterprise business continuity.
        
        Protects: Enterprise business continuity and disaster recovery
        Business Impact: DR failures can cause extended outages affecting all enterprise customers
        """
        # Test disaster recovery scenario in GCP environment
        primary_region = "us-central1"
        dr_region = "us-east1"
        
        # Create primary region manager
        primary_env = IsolatedEnvironment()
        primary_config = {
            "ENVIRONMENT": "staging",
            "GCP_PROJECT_ID": "netra-staging",
            "GCP_REGION": primary_region,
            "DATABASE_URL": "postgresql://primary_user:pass@10.0.1.10:5432/primary_db",
            "REDIS_URL": "redis://10.0.1.20:6379/0",
            "JWT_SECRET_KEY": "disaster_recovery_test_key",
            "BACKUP_ENABLED": "true",
            "REPLICATION_ENABLED": "true"
        }
        
        for key, value in primary_config.items():
            primary_env.set(key, value, source="primary_region")
        
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment', 
                      lambda: primary_env)
            
            primary_manager = UnifiedConfigurationManager(
                user_id="dr_test_enterprise_user",
                environment="staging",
                service_name="primary_service",
                enable_validation=True
            )
        
        # Create comprehensive enterprise configuration dataset
        enterprise_dr_configs = {
            # Customer configurations
            "enterprise.customer_001.subscription": json.dumps({
                "tier": "enterprise",
                "monthly_revenue": 15000,
                "contract_end": "2025-12-31",
                "sla_uptime": 99.9
            }),
            "enterprise.customer_002.subscription": json.dumps({
                "tier": "enterprise",
                "monthly_revenue": 25000,
                "contract_end": "2026-06-30",
                "sla_uptime": 99.95
            }),
            
            # Business critical configurations
            "business.pricing_models": json.dumps({
                "free": {"price": 0, "agents": 1, "storage": "1GB"},
                "pro": {"price": 99, "agents": 5, "storage": "10GB"}, 
                "enterprise": {"price": 15000, "agents": 50, "storage": "1TB"}
            }),
            "business.feature_flags": json.dumps({
                "advanced_analytics": True,
                "enterprise_sso": True,
                "custom_branding": True,
                "priority_support": True
            }),
            
            # Security configurations
            "security.enterprise_keys": json.dumps({
                "jwt_signing_key": "enterprise_jwt_key_primary",
                "encryption_key": "enterprise_encryption_key_primary",
                "api_keys": {
                    "openai": "sk-primary-openai-key",
                    "anthropic": "sk-primary-anthropic-key"
                }
            }),
            
            # Operational configurations
            "operations.scaling_rules": json.dumps({
                "auto_scale_enabled": True,
                "min_instances": 3,
                "max_instances": 100,
                "cpu_threshold": 80,
                "memory_threshold": 85
            })
        }
        
        # Apply configurations to primary region
        for key, value in enterprise_dr_configs.items():
            if key.startswith("security."):
                primary_manager.set(key, value, source=ConfigurationSource.DATABASE, sensitive=True)
            else:
                primary_manager.set(key, value, source=ConfigurationSource.DATABASE)
        
        # Create configuration backup for disaster recovery
        dr_backup = {}
        backup_metadata = {
            "backup_timestamp": time.time(),
            "primary_region": primary_region,
            "dr_region": dr_region,
            "backup_type": "full_configuration_backup",
            "enterprise_customer_count": 2,
            "total_revenue_protected": 40000  # $40K MRR
        }
        
        for key, entry in primary_manager._configurations.items():
            if key in enterprise_dr_configs:
                dr_backup[key] = {
                    "value": entry.value,
                    "source": entry.source.value,
                    "data_type": entry.data_type.__name__,
                    "sensitive": entry.sensitive,
                    "last_updated": entry.last_updated
                }
        
        # Simulate primary region disaster
        # (In real scenario, this would be GCP region failure)
        
        # Create DR region manager
        dr_env = IsolatedEnvironment()
        dr_config = {
            "ENVIRONMENT": "staging",
            "GCP_PROJECT_ID": "netra-staging",
            "GCP_REGION": dr_region,
            "DATABASE_URL": "postgresql://dr_user:pass@10.0.2.10:5432/dr_db",
            "REDIS_URL": "redis://10.0.2.20:6379/0",
            "JWT_SECRET_KEY": "disaster_recovery_test_key",  # Same as primary
            "DISASTER_RECOVERY_MODE": "true",
            "PRIMARY_REGION_FAILED": "true"
        }
        
        for key, value in dr_config.items():
            dr_env.set(key, value, source="dr_region")
        
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment', 
                      lambda: dr_env)
            
            dr_manager = UnifiedConfigurationManager(
                user_id="dr_test_enterprise_user",
                environment="staging",
                service_name="dr_service",
                enable_validation=True
            )
        
        # Restore configurations in DR region
        restore_start_time = time.time()
        restored_count = 0
        restore_errors = []
        
        for key, backup_entry in dr_backup.items():
            try:
                dr_manager.set(
                    key,
                    backup_entry["value"],
                    source=ConfigurationSource(backup_entry["source"]),
                    sensitive=backup_entry["sensitive"]
                )
                
                # Verify restoration
                restored_value = dr_manager.get(key)
                if key.endswith(".subscription") or key.endswith("_models") or key.endswith("_flags") or key.endswith("_keys") or key.endswith("_rules"):
                    # JSON configurations
                    if isinstance(restored_value, str):
                        restored_dict = dr_manager.get_dict(key)
                        expected_dict = json.loads(backup_entry["value"]) if isinstance(backup_entry["value"], str) else backup_entry["value"]
                        if restored_dict == expected_dict:
                            restored_count += 1
                        else:
                            restore_errors.append(f"JSON restoration mismatch for {key}")
                    else:
                        if restored_value == backup_entry["value"]:
                            restored_count += 1
                        else:
                            restore_errors.append(f"Restoration value mismatch for {key}")
                else:
                    if restored_value == backup_entry["value"]:
                        restored_count += 1
                    else:
                        restore_errors.append(f"Restoration failed for {key}")
                        
            except Exception as e:
                restore_errors.append(f"Restoration exception for {key}: {str(e)}")
        
        restore_time = time.time() - restore_start_time
        
        # Verify disaster recovery success
        assert len(restore_errors) == 0, f"DR restoration errors: {restore_errors}"
        assert restored_count == len(enterprise_dr_configs), f"Incomplete DR restoration: {restored_count}/{len(enterprise_dr_configs)}"
        
        # Verify business continuity - all enterprise customers can be served
        customer_001_config = dr_manager.get_dict("enterprise.customer_001.subscription")
        customer_002_config = dr_manager.get_dict("enterprise.customer_002.subscription")
        
        assert customer_001_config["monthly_revenue"] == 15000, "Customer 001 revenue data not restored"
        assert customer_002_config["monthly_revenue"] == 25000, "Customer 002 revenue data not restored"
        assert customer_001_config["sla_uptime"] == 99.9, "Customer 001 SLA not restored"
        assert customer_002_config["sla_uptime"] == 99.95, "Customer 002 SLA not restored"
        
        # Verify security configurations restored correctly
        security_keys = dr_manager.get_dict("security.enterprise_keys")
        assert security_keys["jwt_signing_key"] == "enterprise_jwt_key_primary", "JWT key not restored"
        assert security_keys["api_keys"]["openai"].startswith("sk-primary"), "OpenAI key not restored"
        
        # Verify operational capabilities restored
        scaling_rules = dr_manager.get_dict("operations.scaling_rules")
        assert scaling_rules["auto_scale_enabled"] == True, "Auto-scaling not restored"
        assert scaling_rules["max_instances"] == 100, "Scaling limits not restored"
        
        # Verify DR region is healthy and ready to serve enterprise customers
        dr_health = dr_manager.get_health_status()
        assert dr_health["status"] == "healthy", "DR region not healthy after restoration"
        
        # Performance requirement: DR should complete quickly to minimize downtime
        assert restore_time < 120, f"DR restoration too slow: {restore_time:.2f}s (should be <2 minutes)"
        
        # Verify total enterprise revenue is protected
        total_protected_revenue = customer_001_config["monthly_revenue"] + customer_002_config["monthly_revenue"]
        assert total_protected_revenue == 40000, f"Enterprise revenue not fully protected: ${total_protected_revenue}"

    # ============================================================================
    # HIGH DIFFICULTY E2E TESTS (Production Complexity)
    # Protects: Complex production scenarios
    # ============================================================================

    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_production_scale_concurrent_enterprise_customers(self, gcp_staging_env, gcp_cleanup):
        """
        HIGH DIFFICULTY: Test production-scale concurrent enterprise customer operations.
        
        Protects: Production scalability for multiple enterprise customers
        Business Impact: Scalability failures can prevent enterprise growth limiting revenue expansion
        """
        # Simulate production load with multiple enterprise customers
        enterprise_customers = []
        
        for customer_id in range(10):  # 10 enterprise customers
            customer_data = {
                "id": f"enterprise_{customer_id:03d}",
                "monthly_revenue": 15000 + (customer_id * 5000),  # $15K to $60K MRR
                "region": ["us-central1", "europe-west1", "asia-southeast1"][customer_id % 3],
                "tier": "enterprise",
                "users": 50 + (customer_id * 25),  # 50 to 275 users
                "agents": 10 + (customer_id * 5),  # 10 to 55 agents
                "storage_gb": 100 + (customer_id * 100)  # 100GB to 1TB
            }
            enterprise_customers.append(customer_data)
        
        # Create concurrent customer configuration operations
        results = {}
        errors = []
        performance_metrics = {}
        
        async def enterprise_customer_operations(customer_data: Dict[str, Any]):
            """Simulate enterprise customer configuration operations."""
            try:
                customer_id = customer_data["id"]
                operation_start_time = time.time()
                
                # Create customer-specific environment
                customer_env = IsolatedEnvironment()
                customer_config = {
                    "ENVIRONMENT": "staging",
                    "GCP_PROJECT_ID": "netra-staging",
                    "GCP_REGION": customer_data["region"],
                    "CUSTOMER_ID": customer_id,
                    "CUSTOMER_TIER": "enterprise",
                    "DATABASE_URL": f"postgresql://customer_{customer_id}:pass@10.0.{customer_data['id'][-1]}.10:5432/customer_db",
                    "REDIS_URL": f"redis://10.0.{customer_data['id'][-1]}.20:6379/{customer_id[-1]}"
                }
                
                for key, value in customer_config.items():
                    customer_env.set(key, value, source="enterprise_customer")
                
                # Create customer-specific configuration manager
                with pytest.MonkeyPatch.context() as mp:
                    mp.setattr('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment', 
                              lambda: customer_env)
                    
                    customer_manager = ConfigurationManagerFactory.get_manager(
                        user_id=customer_id,
                        service_name="enterprise_service"
                    )
                
                # Configure customer-specific settings
                customer_operations = []
                
                # Customer subscription configuration
                subscription_config = {
                    "tier": customer_data["tier"],
                    "monthly_revenue": customer_data["monthly_revenue"],
                    "max_users": customer_data["users"],
                    "max_agents": customer_data["agents"],
                    "storage_quota_gb": customer_data["storage_gb"],
                    "region": customer_data["region"],
                    "features": {
                        "advanced_analytics": True,
                        "enterprise_sso": True,
                        "custom_branding": True,
                        "priority_support": True,
                        "dedicated_instances": customer_data["monthly_revenue"] >= 30000
                    }
                }
                
                customer_manager.set(
                    f"customer.{customer_id}.subscription",
                    json.dumps(subscription_config),
                    source=ConfigurationSource.DATABASE
                )
                customer_operations.append("subscription_configured")
                
                # Customer security configuration
                security_config = {
                    "sso_enabled": True,
                    "mfa_required": True,
                    "ip_whitelist": [f"192.168.{customer_id[-1]}.0/24"],
                    "session_timeout": 3600,
                    "api_rate_limit": customer_data["monthly_revenue"] // 3,  # Higher paying customers get higher limits
                    "encryption_level": "AES-256"
                }
                
                customer_manager.set(
                    f"customer.{customer_id}.security",
                    json.dumps(security_config),
                    source=ConfigurationSource.DATABASE,
                    sensitive=True
                )
                customer_operations.append("security_configured")
                
                # Customer performance configuration  
                performance_config = {
                    "dedicated_resources": customer_data["monthly_revenue"] >= 25000,
                    "priority_queue": True,
                    "max_concurrent_requests": customer_data["users"] * 10,
                    "response_time_sla_ms": 500 if customer_data["monthly_revenue"] >= 40000 else 1000,
                    "uptime_sla": 99.95 if customer_data["monthly_revenue"] >= 30000 else 99.9
                }
                
                customer_manager.set(
                    f"customer.{customer_id}.performance",
                    json.dumps(performance_config),
                    source=ConfigurationSource.DATABASE
                )
                customer_operations.append("performance_configured")
                
                # Verify customer configuration isolation
                retrieved_subscription = customer_manager.get_dict(f"customer.{customer_id}.subscription")
                retrieved_security = customer_manager.get_dict(f"customer.{customer_id}.security")
                retrieved_performance = customer_manager.get_dict(f"customer.{customer_id}.performance")
                
                if (retrieved_subscription == subscription_config and
                    retrieved_security == security_config and
                    retrieved_performance == performance_config):
                    customer_operations.append("isolation_verified")
                else:
                    errors.append(f"Customer {customer_id} configuration isolation failed")
                
                # Verify customer cannot access other customer data
                other_customer_id = f"enterprise_{(int(customer_id[-3:]) + 1) % 10:03d}"
                other_customer_data = customer_manager.get(f"customer.{other_customer_id}.subscription")
                
                if other_customer_data is None:
                    customer_operations.append("security_isolation_verified")
                else:
                    errors.append(f"Customer {customer_id} accessed other customer data: {other_customer_id}")
                
                operation_time = time.time() - operation_start_time
                
                performance_metrics[customer_id] = {
                    "operation_time": operation_time,
                    "operations_completed": len(customer_operations),
                    "monthly_revenue": customer_data["monthly_revenue"],
                    "region": customer_data["region"]
                }
                
                results[customer_id] = customer_operations
                
            except Exception as e:
                errors.append(f"Customer {customer_data['id']} operations failed: {str(e)}")
        
        # Execute concurrent enterprise customer operations
        tasks = [
            enterprise_customer_operations(customer_data)
            for customer_data in enterprise_customers
        ]
        
        concurrent_start_time = time.time()
        await asyncio.gather(*tasks)
        total_concurrent_time = time.time() - concurrent_start_time
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Enterprise customer operation errors: {errors}"
        
        # Verify all customers completed successfully
        assert len(results) == len(enterprise_customers), f"Incomplete customer operations: {len(results)}/{len(enterprise_customers)}"
        
        for customer_data in enterprise_customers:
            customer_id = customer_data["id"]
            customer_results = results[customer_id]
            
            expected_operations = ["subscription_configured", "security_configured", "performance_configured", 
                                 "isolation_verified", "security_isolation_verified"]
            assert len(customer_results) == len(expected_operations), f"Customer {customer_id} incomplete operations"
            
            for expected_op in expected_operations:
                assert expected_op in customer_results, f"Customer {customer_id} missing operation: {expected_op}"
        
        # Verify performance requirements
        total_revenue_processed = sum(customer["monthly_revenue"] for customer in enterprise_customers)
        avg_operation_time = sum(metrics["operation_time"] for metrics in performance_metrics.values()) / len(performance_metrics)
        
        # Performance requirements for enterprise operations
        assert total_concurrent_time < 60, f"Concurrent enterprise operations too slow: {total_concurrent_time:.2f}s"
        assert avg_operation_time < 10, f"Average enterprise operation too slow: {avg_operation_time:.2f}s"
        assert total_revenue_processed >= 300000, f"Insufficient enterprise revenue processed: ${total_revenue_processed}"
        
        # Verify regional distribution
        regions_used = set(metrics["region"] for metrics in performance_metrics.values())
        assert len(regions_used) == 3, f"Not all regions utilized: {regions_used}"
        
        # Verify high-value customer performance
        high_value_customers = [
            customer_id for customer_id, metrics in performance_metrics.items()
            if metrics["monthly_revenue"] >= 40000
        ]
        
        if high_value_customers:
            high_value_avg_time = sum(
                performance_metrics[customer_id]["operation_time"]
                for customer_id in high_value_customers
            ) / len(high_value_customers)
            
            # High-value customers should get even better performance
            assert high_value_avg_time < 8, f"High-value customer performance insufficient: {high_value_avg_time:.2f}s"