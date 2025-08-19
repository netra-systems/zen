import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.startup_checks.database_checks import DatabaseChecker
from app.core.config import config_with_secrets as settings

async def test():
    checker = DatabaseChecker(settings)
    result = await checker.check_postgres_migration()
    print(f'Migration check result: {result}')
    print(f'  Success: {result.success}')
    print(f'  Critical: {result.critical}')
    print(f'  Message: {result.message}')
    if result.details:
        print(f'  Details: {result.details}')

asyncio.run(test())