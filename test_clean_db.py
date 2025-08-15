"""Test database connection with clean approach."""
import asyncio
import asyncpg
import sys

async def test_connection():
    """Test PostgreSQL connection."""
    password = 'wL3hNia9peARTuEV6b5DMXZrEGaore4M'
    
    print(f"Testing connection with password: {password[:10]}...")
    
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=password,
            database='netra_dev'
        )
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"SUCCESS: PostgreSQL connection successful! Result: {result}")
        return True
    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"ERROR: Invalid password - {e}")
        return False
    except Exception as e:
        print(f"ERROR: Connection failed - {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)