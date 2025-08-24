#!/usr/bin/env python3
"""
Debug script to test PostgreSQL connection exactly as the dev launcher does.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dev_launcher.database_connector import DatabaseConnector

async def test_database_connector():
    """Test the database connector directly."""
    print("Testing database connector...")
    
    # Create database connector (disable emoji for Windows compatibility)
    connector = DatabaseConnector(use_emoji=False)
    
    # Print discovered connections
    print(f"Discovered connections: {list(connector.connections.keys())}")
    
    for name, connection in connector.connections.items():
        print(f"\nConnection: {name}")
        print(f"  Type: {connection.db_type.value}")
        print(f"  URL: {connection.url}")
        
        # Test the specific connection
        if connection.db_type.value == 'postgresql':
            print(f"  Testing PostgreSQL connection...")
            
            try:
                result = await connector._test_postgresql_connection(connection)
                print(f"  Result: {result}")
                if connection.last_error:
                    print(f"  Last error: {connection.last_error}")
            except Exception as e:
                print(f"  Exception: {e}")
    
    # Clean up
    await connector.stop_health_monitoring()

if __name__ == "__main__":
    asyncio.run(test_database_connector())