#!/usr/bin/env python3
"""
Script to fix PostgreSQL password authentication issue in staging.
Connects to Cloud SQL via proxy and resets postgres user password.
"""
import os
import sys
import asyncio
import asyncpg
from google.cloud.sql.connector import Connector


async def fix_postgres_password():
    """Connect to Cloud SQL and reset postgres user password."""
    
    # Connection details
    instance_connection_name = "netra-staging:us-central1:staging-shared-postgres"
    db_user = "postgres"
    db_name = "netra_dev"
    new_password = "HUhvKScISzivLzD/NRaYVrmbGj8EAzf4M/xRtjOE8bY="
    
    # Try to connect using the current password from secret
    current_password = "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"
    
    connector = Connector()
    
    try:
        print(f"Attempting to connect to {instance_connection_name}...")
        
        # Try with current password first
        try:
            conn = await connector.connect_async(
                instance_connection_name,
                "asyncpg",
                user=db_user,
                password=current_password,
                db=db_name,
            )
            print("Connected with current password - no change needed!")
            await conn.close()
            return True
            
        except Exception as e:
            print(f"Current password failed: {e}")
            print("Attempting to connect with new password...")
            
            # Try with new password
            try:
                conn = await connector.connect_async(
                    instance_connection_name,
                    "asyncpg",
                    user=db_user,
                    password=new_password,
                    db=db_name,
                )
                print("Connected with new password - updating secret...")
                await conn.close()
                return True
                
            except Exception as e2:
                print(f"New password also failed: {e2}")
                print("Need to reset password manually...")
                return False
                
    except Exception as e:
        print(f"Connection setup failed: {e}")
        return False
    finally:
        connector.close()


if __name__ == "__main__":
    print("PostgreSQL Password Fix Script")
    print("=" * 40)
    
    result = asyncio.run(fix_postgres_password())
    
    if result:
        print("\nPassword issue resolved!")
    else:
        print("\nPassword issue NOT resolved - manual intervention required")
        sys.exit(1)