#!/usr/bin/env python3
"""Debug Database Connection Script - Cloud SQL Connector Version

Tests the database connection using the Cloud SQL Python Connector to properly
handle Cloud SQL connections and diagnose the authentication issue.
"""

import asyncio
import os
import logging
from google.cloud.sql.connector import Connector
import asyncpg
import urllib.parse

# Set up logging to see detailed errors
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_cloud_sql_connection():
    """Test Cloud SQL connection using the Python Connector."""
    
    # Cloud SQL instance details
    instance_connection_name = "netra-staging:us-central1:staging-shared-postgres"
    database_name = "postgres"
    username = "postgres"
    
    # Decode the password from the secret
    encoded_password = "qNdlZRHu%28Mlc%23%296K8LHm-lYi%5B7sc%7D25K"
    password = urllib.parse.unquote(encoded_password)
    
    logger.info(f"Testing Cloud SQL connection:")
    logger.info(f"  Instance: {instance_connection_name}")
    logger.info(f"  Database: {database_name}")
    logger.info(f"  Username: {username}")
    logger.info(f"  Password: {'*' * len(password)}")
    
    # Initialize Cloud SQL Python Connector
    connector = Connector()
    
    try:
        # Create connection using Cloud SQL Python Connector
        logger.info("Creating connection with Cloud SQL Connector...")
        
        # Get the async connection
        conn = await connector.connect_async(
            instance_connection_name,
            "asyncpg",
            user=username,
            password=password,
            db=database_name,
        )
        
        logger.info("Connection established successfully!")
        
        # Test the connection
        result = await conn.fetch("SELECT current_user, current_database(), version()")
        row = result[0]
        
        logger.info(f"Connection test successful!")
        logger.info(f"Current user: {row[0]}")
        logger.info(f"Current database: {row[1]}")
        logger.info(f"PostgreSQL version: {row[2]}")
        
        # Close the connection
        await conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Cloud SQL connection failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Check for specific error types
        error_str = str(e).lower()
        if "password authentication failed" in error_str:
            logger.error("AUTHENTICATION ERROR: The postgres user password is incorrect")
            logger.error("The password in netra-db-password secret does not match the postgres user password on the database")
        elif "user" in error_str and "does not exist" in error_str:
            logger.error("USER ERROR: The postgres user does not exist in the database")
        elif "permission denied" in error_str:
            logger.error("PERMISSION ERROR: Check service account permissions")
        elif "connection refused" in error_str:
            logger.error("CONNECTION ERROR: Cannot reach the database instance")
        
        return False
        
    finally:
        # Always close the connector
        await connector.close()

async def test_with_different_users():
    """Test connection with different users to see which ones exist and work."""
    
    instance_connection_name = "netra-staging:us-central1:staging-shared-postgres"
    database_name = "postgres"
    
    # List of users from gcloud sql users list
    users_to_test = [
        "postgres",
        "user_pr-2", 
        "user_pr-4",
        "user_pr_branch_8_15_evening_deploy",
        "user_pr_branch_8_16_afternoon"
    ]
    
    # Try the same password for all users
    encoded_password = "qNdlZRHu%28Mlc%23%296K8LHm-lYi%5B7sc%7D25K"
    password = urllib.parse.unquote(encoded_password)
    
    connector = Connector()
    successful_users = []
    
    try:
        for username in users_to_test:
            logger.info(f"Testing user: {username}")
            
            try:
                conn = await connector.connect_async(
                    instance_connection_name,
                    "asyncpg",
                    user=username,
                    password=password,
                    db=database_name,
                )
                
                # Test basic query
                result = await conn.fetch("SELECT current_user")
                current_user = result[0][0]
                
                logger.info(f"SUCCESS: User '{username}' connected successfully as '{current_user}'")
                successful_users.append(username)
                
                await conn.close()
                
            except Exception as e:
                logger.warning(f"FAILED: User '{username}' failed to connect: {e}")
                continue
    
    finally:
        await connector.close()
    
    return successful_users

async def get_actual_postgres_password():
    """Try to determine what the actual postgres password should be."""
    
    logger.info("Checking if there are other password secrets or if we need to reset the postgres password...")
    
    # This is where we'd check other possible password sources
    # For now, let's see if any users work with the current password
    
    successful_users = await test_with_different_users()
    
    if successful_users:
        logger.info(f"Found working users: {successful_users}")
        logger.info("We can either:")
        logger.info("1. Update the database URL to use one of these working users")
        logger.info("2. Reset the postgres user password to match our secret")
        return successful_users
    else:
        logger.error("No users work with the current password from netra-db-password secret")
        logger.error("This indicates either:")
        logger.error("1. The password in the secret is outdated")
        logger.error("2. The postgres user password was changed outside of our system")
        logger.error("3. There's a different password for postgres user")
        return []

def main():
    """Run all connection tests."""
    logger.info("Starting Cloud SQL connection debugging...")
    
    async def run_tests():
        logger.info("=" * 50)
        logger.info("Test 1: Direct Cloud SQL connection test")
        success = await test_cloud_sql_connection()
        
        logger.info("=" * 50)
        logger.info("Test 2: Testing all existing users")
        successful_users = await get_actual_postgres_password()
        
        logger.info("=" * 50)
        logger.info("SUMMARY:")
        logger.info(f"  Cloud SQL connection test: {'SUCCESS' if success else 'FAILED'}")
        logger.info(f"  Working users found: {successful_users}")
        
        if success:
            logger.info("The connection works - no changes needed")
        elif successful_users:
            logger.info(f"RECOMMENDATION: Update database URL to use user '{successful_users[0]}' instead of postgres")
        else:
            logger.error("RECOMMENDATION: Need to reset postgres user password or investigate further")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()