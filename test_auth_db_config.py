#!/usr/bin/env python3
"""
Test Auth Service Database Configuration
Check what database configuration the auth service is actually using.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx


async def test_auth_service_db_info():
    """Get auth service database configuration info"""
    auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    
    async with httpx.AsyncClient() as client:
        try:
            # Try to trigger an action that uses the database
            response = await client.post(f"{auth_url}/auth/dev/login")
            print(f"Dev login response: {response.status_code}")
            
            if response.status_code == 500:
                error_details = response.json()
                print(f"Error details: {error_details}")
                
                # Check if it's a SQLite vs PostgreSQL issue
                error_msg = error_details.get("detail", "")
                if "sqlite3.OperationalError" in error_msg:
                    print("❌ Auth service is using SQLite but expected PostgreSQL")
                    print("This suggests the service started in test mode")
                elif "no such table" in error_msg:
                    print("❌ Database tables don't exist")
                else:
                    print("❌ Unknown database error")
            elif response.status_code == 200:
                print("✅ Dev login successful")
                print(f"Response: {response.json()}")
            else:
                print(f"❓ Unexpected response: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Failed to connect to auth service: {e}")

            
async def check_local_environment():
    """Check local environment variables"""
    print("Environment Variables:")
    print(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT', 'NOT SET')}")
    print(f"  AUTH_FAST_TEST_MODE: {os.getenv('AUTH_FAST_TEST_MODE', 'NOT SET')}")
    print(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')}")
    print(f"  AUTH_SERVICE_URL: {os.getenv('AUTH_SERVICE_URL', 'NOT SET')}")
    
    # Check if we're in a test environment
    import sys
    is_pytest = 'pytest' in sys.modules or 'pytest' in ' '.join(sys.argv)
    print(f"  Is pytest environment: {is_pytest}")


async def main():
    """Main test function"""
    print("Auth Service Database Configuration Test")
    print("=" * 50)
    
    await check_local_environment()
    print()
    await test_auth_service_db_info()


if __name__ == "__main__":
    asyncio.run(main())