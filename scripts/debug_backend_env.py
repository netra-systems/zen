#!/usr/bin/env python3
"""
Debug script to check what environment the backend thinks it's running in.
"""
import os
import sys
import requests

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Check backend environment configuration."""
    backend_url = "http://localhost:8000"
    
    print("="*60)
    print("BACKEND ENVIRONMENT DEBUG")
    print("="*60)
    
    # Test if we can get some configuration info from the backend
    try:
        # Try health endpoint first
        health_response = requests.get(f"{backend_url}/health", timeout=10)
        print(f"Health endpoint status: {health_response.status_code}")
        
        # Check if there are any configuration endpoints we can query
        # This is just a debugging attempt
        
        # Let's see what the backend logs show about the CORS configuration
        print("\nTrying to check CORS middleware setup...")
        
        # The issue might be in the middleware setup - let's check the actual config 
        # being used by directly importing it
        from shared.cors_config_builder import CORSConfigurationBuilder, get_cors_origins, get_fastapi_cors_config
        from netra_backend.app.core.configuration import get_configuration
        
        print("Direct config check:")
        cors_builder = CORSConfigurationBuilder()
        print(f"Detected environment: {cors_builder.environment}")
        
        config = get_configuration()
        print(f"Backend config environment: {config.environment}")
        
        origins = get_cors_origins(config.environment)
        print(f"CORS origins count: {len(origins)}")
        print(f"First 5 origins: {origins[:5]}")
        
        cors_config = get_fastapi_cors_config(config.environment)
        print(f"FastAPI CORS config keys: {list(cors_config.keys())}")
        print(f"Allow origins count: {len(cors_config.get('allow_origins', []))}")
        
        # Check if localhost:3000 is specifically in the list
        test_origin = "http://localhost:3000"
        is_in_origins = test_origin in cors_config.get('allow_origins', [])
        print(f"'{test_origin}' in allow_origins: {is_in_origins}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()