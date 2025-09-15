"""
Integration Test Issue #799: SSOT Database URL Construction Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Stability/Reliability
- Value Impact: Protects $120K+ MRR through consistent database connectivity
- Strategic Impact: Prevents cascade failures from configuration drift

This integration test validates that database URL construction works correctly
across all environments using SSOT patterns.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

class DatabaseURLSSOTIntegrationTests(BaseIntegrationTest):
    """Integration tests for SSOT database URL construction across environments."""

    @pytest.mark.integration
    async def test_appconfig_database_url_ssot_integration_development(self, real_services_fixture):
        """
        Test AppConfig database URL construction uses SSOT DatabaseURLBuilder in development.
        """
        env = get_env()
        env.enable_isolation()
        try:
            test_env_vars = {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'dev_user', 'POSTGRES_PASSWORD': 'dev_pass', 'POSTGRES_DB': 'netra_dev', 'POSTGRES_PORT': '5432'}
            for key, value in test_env_vars.items():
                env.set(key, value)
            config = DevelopmentConfig()
            config.database_url = None
            database_url = config.get_database_url()
            self.assertIsNotNone(database_url)
            self.assertIn('postgresql://', database_url)
            self.assertIn('dev_user', database_url)
            self.assertIn('localhost', database_url)
            self.assertIn('netra_dev', database_url)
        finally:
            env.disable_isolation()

    @pytest.mark.integration
    async def test_staging_config_database_url_ssot_integration(self, real_services_fixture):
        """
        Test StagingConfig database URL construction uses SSOT DatabaseURLBuilder.
        """
        env = get_env()
        env.enable_isolation()
        try:
            test_env_vars = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging-db-host', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'staging_pass', 'POSTGRES_DB': 'netra_staging', 'POSTGRES_PORT': '5432'}
            for key, value in test_env_vars.items():
                env.set(key, value)
            config = StagingConfig()
            config.database_url = None
            database_url = config.get_database_url()
            self.assertIsNotNone(database_url)
            self.assertIn('postgresql://', database_url)
            self.assertIn('staging_user', database_url)
            self.assertIn('staging-db-host', database_url)
            self.assertIn('netra_staging', database_url)
        finally:
            env.disable_isolation()

    @pytest.mark.integration
    async def test_database_url_builder_direct_integration(self, real_services_fixture):
        """
        Test DatabaseURLBuilder direct integration with real environment.
        """
        env = get_env()
        env.enable_isolation()
        try:
            test_env_vars = {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'test-host', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_pass', 'POSTGRES_DB': 'test_db', 'POSTGRES_PORT': '5433'}
            for key, value in test_env_vars.items():
                env.set(key, value)
            builder = DatabaseURLBuilder(env.get_all())
            sync_url = builder.get_url_for_environment(sync=True)
            self.assertIsNotNone(sync_url)
            self.assertIn('postgresql://', sync_url)
            self.assertIn('test_user', sync_url)
            self.assertIn('test-host', sync_url)
            self.assertIn('5433', sync_url)
            self.assertIn('test_db', sync_url)
            async_url = builder.get_url_for_environment(sync=False)
            if async_url:
                self.assertIn('postgresql+asyncpg://', async_url)
        finally:
            env.disable_isolation()

    @pytest.mark.integration
    async def test_appconfig_fallback_behavior_integration(self, real_services_fixture):
        """
        Test AppConfig fallback behavior in realistic error scenarios.
        
        This test validates that even fallback paths work correctly.
        """
        env = get_env()
        env.enable_isolation()
        try:
            test_env_vars = {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'fallback-host', 'POSTGRES_USER': 'fallback_user', 'POSTGRES_PASSWORD': 'fallback_pass', 'POSTGRES_DB': 'fallback_db', 'POSTGRES_PORT': '5434'}
            for key, value in test_env_vars.items():
                env.set(key, value)
            config = AppConfig()
            config.database_url = None
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder:
                mock_builder.side_effect = Exception('Simulated DatabaseURLBuilder failure')
                database_url = config.get_database_url()
                self.assertIsNotNone(database_url)
                self.assertIn('postgresql://', database_url)
                self.assertIn('fallback_user', database_url)
                self.assertIn('fallback-host', database_url)
                self.assertIn('5434', database_url)
                self.assertIn('fallback_db', database_url)
        finally:
            env.disable_isolation()

    @pytest.mark.integration
    async def test_multiple_environment_url_construction_consistency(self, real_services_fixture):
        """
        Test URL construction consistency across multiple environment configurations.
        """
        environments = [('development', 'dev-host', 'dev_user', 'dev_db'), ('staging', 'staging-host', 'staging_user', 'staging_db'), ('production', 'prod-host', 'prod_user', 'prod_db')]
        for env_name, host, user, db_name in environments:
            with self.subTest(environment=env_name):
                env = get_env()
                env.enable_isolation()
                try:
                    test_env_vars = {'ENVIRONMENT': env_name, 'POSTGRES_HOST': host, 'POSTGRES_USER': user, 'POSTGRES_PASSWORD': 'test_pass', 'POSTGRES_DB': db_name, 'POSTGRES_PORT': '5432'}
                    for key, value in test_env_vars.items():
                        env.set(key, value)
                    config = AppConfig()
                    config.database_url = None
                    database_url = config.get_database_url()
                    self.assertIsNotNone(database_url)
                    self.assertIn('postgresql://', database_url)
                    self.assertIn(host, database_url)
                    self.assertIn(user, database_url)
                    self.assertIn(db_name, database_url)
                finally:
                    env.disable_isolation()

    @pytest.mark.integration
    async def test_ssot_compliance_across_config_classes(self, real_services_fixture):
        """
        Test SSOT compliance across all configuration classes that use database URLs.
        """
        config_classes = [AppConfig, DevelopmentConfig, StagingConfig]
        for config_class in config_classes:
            with self.subTest(config_class=config_class.__name__):
                env = get_env()
                env.enable_isolation()
                try:
                    test_env_vars = {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'ssot-test-host', 'POSTGRES_USER': 'ssot_user', 'POSTGRES_PASSWORD': 'ssot_pass', 'POSTGRES_DB': 'ssot_db', 'POSTGRES_PORT': '5432'}
                    for key, value in test_env_vars.items():
                        env.set(key, value)
                    config = config_class()
                    config.database_url = None
                    database_url = config.get_database_url()
                    self.assertIsNotNone(database_url)
                    self.assertIn('postgresql://', database_url)
                    self.assertIn('ssot_user', database_url)
                    self.assertIn('ssot-test-host', database_url)
                    self.assertIn('ssot_db', database_url)
                finally:
                    env.disable_isolation()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')