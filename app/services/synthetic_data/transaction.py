"""
Transaction context manager for data operations
"""

from typing import Dict, List


class Transaction:
    """Transaction context manager"""
    
    async def insert_records(self, records: List[Dict]):
        """Insert records in transaction"""
        pass
    
    async def commit(self):
        """Commit transaction"""
        pass
    
    async def rollback(self):
        """Rollback transaction"""
        pass