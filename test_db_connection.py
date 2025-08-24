#!/usr/bin/env python3
"""Test database connection"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    """Test different connection strings"""
    
    connection_strings = [
        # Without password
        'postgresql+asyncpg://postgres@localhost:5433/netra_dev',
        # With password from .env
        'postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev',
    ]
    
    for conn_str in connection_strings:
        print(f"\nTesting: {conn_str[:50]}...")
        try:
            engine = create_async_engine(conn_str)
            async with engine.connect() as conn:
                result = await conn.execute(text('SELECT 1'))
                print(f"✅ Connection successful: {result.scalar()}")
            await engine.dispose()
        except Exception as e:
            print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())