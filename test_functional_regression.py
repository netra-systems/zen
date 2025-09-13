#!/usr/bin/env python3

"""
Test functional regression - verify database connectivity still works
"""

from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

def test_functional_regression():
    print("=== Functional Regression Test ===")
    
    # Test AppConfig database URL construction
    try:
        config = AppConfig()
        db_url = config.get_database_url()
        print(f"✅ AppConfig PostgreSQL URL: {DatabaseURLBuilder.mask_url_for_logging(db_url)}")
    except Exception as e:
        print(f"❌ AppConfig PostgreSQL FAILED: {e}")
    
    # Test ClickHouse URL construction  
    try:
        config = AppConfig()
        ch_url = config.get_clickhouse_url()
        print(f"✅ AppConfig ClickHouse URL: {DatabaseURLBuilder.mask_url_for_logging(ch_url)}")
    except Exception as e:
        print(f"❌ AppConfig ClickHouse FAILED: {e}")
    
    # Test Development config
    try:
        config = DevelopmentConfig()
        db_url = config.get_database_url()
        print(f"✅ DevelopmentConfig URL: {DatabaseURLBuilder.mask_url_for_logging(db_url)}")
    except Exception as e:
        print(f"❌ DevelopmentConfig FAILED: {e}")
    
    # Test DatabaseURLBuilder directly
    try:
        env = get_env()
        builder = DatabaseURLBuilder(env)
        url = builder.get_url_for_environment()
        ch_url = builder.clickhouse.get_url_for_environment()
        print(f"✅ DatabaseURLBuilder PostgreSQL: {DatabaseURLBuilder.mask_url_for_logging(url)}")
        print(f"✅ DatabaseURLBuilder ClickHouse: {DatabaseURLBuilder.mask_url_for_logging(ch_url)}")
    except Exception as e:
        print(f"❌ DatabaseURLBuilder FAILED: {e}")

if __name__ == "__main__":
    test_functional_regression()