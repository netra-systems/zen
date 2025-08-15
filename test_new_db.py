"""Test new database connection."""
import asyncio
import asyncpg

async def test_connection():
    """Test PostgreSQL connection with new credentials."""
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='wL3hNia9peARTuEV6b5DMXZrEGaore4M',
            database='netra_dev'
        )
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"✅ PostgreSQL connection successful! Result: {result}")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())