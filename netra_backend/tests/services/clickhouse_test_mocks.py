"""
Mock classes for ClickHouse Query Fixer tests.
All functions ≤8 lines per requirements.
"""

from typing import Any, Dict, List


class MockClickHouseClient:
    """Mock ClickHouse client for testing"""
    
    def __init__(self):
        self.executed_queries = []
        self.query_results = {}
        self.execution_times = {}
        self._init_failure_settings()
        
    def _init_failure_settings(self) -> None:
        """Initialize failure simulation settings"""
        self.should_fail = False
        self.failure_message = "Mock ClickHouse error"
        
    async def execute(self, query: str, *args, **kwargs):
        """Mock query execution"""
        self.executed_queries.append(query)
        
        if self.should_fail:
            raise Exception(self.failure_message)
        
        return self._get_query_result(query)
    
    async def execute_query(self, query: str, *args, **kwargs):
        """Mock query execution (alternative method name)"""
        return await self.execute(query, *args, **kwargs)
    
    def _get_query_result(self, query: str) -> List[Dict[str, Any]]:
        """Get result for query"""
        if query in self.query_results:
            return self.query_results[query]
        
        return [{"result": "mock_data", "rows": 1}]
    
    def set_query_result(self, query: str, result: Any) -> None:
        """Set expected result for specific query"""
        self.query_results[query] = result
    
    def get_executed_queries(self) -> List[str]:
        """Get list of executed queries"""
        return self.executed_queries.copy()
    
    def clear_history(self) -> None:
        """Clear execution history"""
        self.executed_queries.clear()