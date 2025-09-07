#!/usr/bin/env python3
"""
Debug test for database validation failure
"""

from shared.isolated_environment import get_env

def test_database_validation():
    """Debug database validation"""
    env = get_env()
    env.reset()
    env.enable_isolation()
    
    # Set staging environment
    env.set("ENVIRONMENT", "staging", source="test")
    
    # Test missing variables first
    result = env.validate_staging_database_credentials()
    print("Missing vars result:", result)
    
    # Test with invalid credentials
    env.set("POSTGRES_HOST", "localhost", source="test")
    env.set("POSTGRES_USER", "postgres", source="test") 
    env.set("POSTGRES_PASSWORD", "password", source="test")
    env.set("POSTGRES_DB", "netra_staging", source="test")
    
    result = env.validate_staging_database_credentials()
    print("Invalid creds result:", result)
    print("Issues:", result["issues"])
    
    env.reset()

if __name__ == "__main__":
    test_database_validation()