#!/usr/bin/env python3

"""
Quick test to verify SSOT fix is working
"""

import os
from unittest.mock import patch
from netra_backend.app.schemas.config import DevelopmentConfig
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

def test_ssot_fix():
    test_env = {
        'POSTGRES_HOST': 'test-host',
        'POSTGRES_USER': 'test-user', 
        'POSTGRES_PASSWORD': 'test-pass',
        'POSTGRES_DB': 'test-db',
        'POSTGRES_PORT': '5433',
        'ENVIRONMENT': 'development'
    }
    
    print("=== Environment Isolation Test ===")
    with patch.dict(os.environ, test_env, clear=False):
        # Check what get_env() sees
        actual_env = get_env()
        print(f"get_env() POSTGRES_HOST: {actual_env.get('POSTGRES_HOST')}")
        print(f"get_env() POSTGRES_USER: {actual_env.get('POSTGRES_USER')}")
        print(f"get_env() ENVIRONMENT: {actual_env.get('ENVIRONMENT')}")
        
        # Direct DatabaseURLBuilder with test_env 
        builder1 = DatabaseURLBuilder(test_env)
        builder1_url = builder1.development.auto_url
        print(f"Builder (test_env): {builder1_url}")
        
        # Direct DatabaseURLBuilder with get_env()
        builder2 = DatabaseURLBuilder(actual_env)
        builder2_url = builder2.development.auto_url
        print(f"Builder (get_env): {builder2_url}")
        
        # AppConfig 
        config = DevelopmentConfig()
        print(f"AppConfig.database_url: {config.database_url}")
        appconfig_url = config.get_database_url()
        print(f"AppConfig URL: {appconfig_url}")
        
        print(f"Builder1 == AppConfig: {builder1_url == appconfig_url}")
        print(f"Builder2 == AppConfig: {builder2_url == appconfig_url}")
        
    print("=== Test with exact test scenario ===")
    test_env2 = {
        'POSTGRES_HOST': 'comparison-host',
        'POSTGRES_USER': 'comparison-user',
        'POSTGRES_PASSWORD': 'comparison-pass',
        'POSTGRES_DB': 'comparison-db',
        'POSTGRES_PORT': '5435',
        'ENVIRONMENT': 'development'
    }
    
    with patch.dict(os.environ, test_env2, clear=False):
        builder = DatabaseURLBuilder(test_env2)
        builder_url = builder.development.auto_url
        print(f"Test Builder URL: {builder_url}")
        
        config = DevelopmentConfig()
        appconfig_url = config.database_url or config.get_database_url()
        print(f"Test AppConfig URL: {appconfig_url}")
        
        print(f"Test Match: {builder_url == appconfig_url}")

if __name__ == "__main__":
    test_ssot_fix()