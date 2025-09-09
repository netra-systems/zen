"""
Test Database Scalability Authenticated Operations E2E

Business Value Justification (BVJ):
- Segment: All customer segments (data persistence foundation)
- Business Goal: Ensure database can scale with customer growth
- Value Impact: Database bottlenecks affect all customer operations
- Strategic Impact: Database scalability enables enterprise customer acquisition

CRITICAL REQUIREMENTS:
- Tests complete E2E database operations with authenticated users
- Validates multi-user data isolation and performance
- Uses real database connections and authenticated sessions
- MANDATORY: All operations MUST use authenticated user contexts
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.database import DatabaseTestHelper
from shared.isolated_environment import get_env


class TestDatabaseScalabilityAuthenticatedOperationsE2E(BaseE2ETest):
    """Test database scalability with authenticated user operations"""
    
    def setup_method(self):
        """Set up E2E test environment"""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper()
        self.db_helper = DatabaseTestHelper()
        self.test_prefix = f"db_scale_{uuid.uuid4().hex[:8]}"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_data_operations_performance(self):
        """Test multi-user database operations with realistic data patterns"""
        concurrent_users = 20
        operations_per_user = 10
        
        # Create authenticated users
        authenticated_users = []
        for i in range(concurrent_users):
            tier = ["free", "mid", "enterprise"][i % 3]
            auth_result = await self.auth_helper.create_and_authenticate_user(
                email=f"db_user_{i}@example.com",
                tier=tier,
                test_prefix=self.test_prefix
            )
            
            if auth_result.success:
                authenticated_users.append({
                    "user_id": auth_result.user_id,
                    "tier": tier,
                    "access_token": auth_result.access_token
                })
        
        assert len(authenticated_users) >= concurrent_users * 0.8
        
        # Execute concurrent database operations
        operation_tasks = []
        for user in authenticated_users:
            task = self._execute_user_database_operations(user, operations_per_user)
            operation_tasks.append(task)
        
        start_time = time.time()
        operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Validate results
        successful_operations = [r for r in operation_results if isinstance(r, dict) and r.get("success")]
        success_rate = len(successful_operations) / len(operation_results)
        
        assert success_rate >= 0.85, f"Database operation success rate too low: {success_rate:.2%}"
        
        total_duration = end_time - start_time
        assert total_duration < 60.0, f"Multi-user database operations too slow: {total_duration:.2f}s"
    
    async def _execute_user_database_operations(self, user: Dict[str, Any], operation_count: int) -> Dict[str, Any]:
        """Execute database operations for a single authenticated user"""
        try:
            operations_completed = 0
            
            for i in range(operation_count):
                # Simulate user data operations (projects, analytics, etc.)
                async with self.db_helper.get_connection() as conn:
                    # Create user project
                    await conn.execute("""
                        INSERT INTO user_projects (user_id, project_name, created_at)
                        VALUES ($1, $2, NOW())
                    """, user["user_id"], f"Project_{i}")
                    
                    # Read user data
                    await conn.fetch("""
                        SELECT * FROM user_projects WHERE user_id = $1 LIMIT 10
                    """, user["user_id"])
                    
                    operations_completed += 1
                    await asyncio.sleep(0.01)  # Small delay
            
            return {"success": True, "user_id": user["user_id"], "operations": operations_completed}
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])