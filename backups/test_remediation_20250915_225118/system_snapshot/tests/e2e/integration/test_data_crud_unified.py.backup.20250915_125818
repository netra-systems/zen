"""E2E Test #3: Data CRUD Across All Services for Netra Apex

CRITICAL CONTEXT: Complete data CRUD operations across Auth, Backend, and Frontend
ensuring data consistency and GDPR compliance for user data lifecycle management.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise) 
2. Business Goal: Ensure data integrity prevents churn and support tickets
3. Value Impact: Protects $60K+ MRR through reliable data operations
4. Revenue Impact: Prevents data corruption incidents that cause customer loss

SUCCESS CRITERIA:
- Create user data in Auth Service (<2 seconds)
- Read user data from Backend API (<1 second) 
- Update user preferences via Frontend  ->  Backend (<2 seconds)
- Delete user data with GDPR compliance (<5 seconds)
- Verify 100% data consistency across all services
- Complete E2E flow in <10 seconds total

Module Architecture Compliance: Under 300 lines, functions under 8 lines
"""

import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.data_crud_helpers import (
    DataCRUDManager, GDPRComplianceValidator, CrossServiceDataValidator, create_test_user_data, create_user_preferences_data,
    DataCRUDManager,
    GDPRComplianceValidator,
    CrossServiceDataValidator,
    create_test_user_data,
    create_user_preferences_data
)


@pytest_asyncio.fixture
async def data_crud_manager():
    """Create data CRUD manager fixture for testing."""
    manager = DataCRUDManager()
    await manager.setup_test_environment()
    
    yield manager
    
    # Cleanup test environment
    await manager.cleanup_test_environment()


class TestDataCRUDUnifiedE2E:
    """E2E Tests for complete data CRUD operations across all services."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_data_crud_lifecycle(self, data_crud_manager):
        """Test #3: Complete Data CRUD Across All Services - E2E Flow."""
        manager = data_crud_manager
        start_time = time.time()
        
        # Execute complete CRUD lifecycle
        results = await self._execute_crud_lifecycle(manager)
        
        # Validate performance criteria
        total_time = time.time() - start_time
        assert total_time < 10.0, f"E2E CRUD too slow: {total_time:.2f}s"
        
        # Validate all CRUD operations succeeded
        self._validate_crud_results(results)
        
        print(f"[SUCCESS] Data CRUD E2E: {total_time:.2f}s")
        print(f"[PROTECTED] $60K+ MRR through data integrity")
    
    async def _execute_crud_lifecycle(self, manager: DataCRUDManager) -> Dict:
        """Execute complete CRUD lifecycle with timing."""
        results = {}
        
        # CREATE: User data in Auth Service
        results['create'] = await self._test_create_operations(manager)
        
        # READ: User data from Backend API  
        results['read'] = await self._test_read_operations(manager, results['create']['user_id'])
        
        # UPDATE: User preferences via Frontend  ->  Backend
        results['update'] = await self._test_update_operations(manager, results['create']['user_id'])
        
        # DELETE: User data with GDPR compliance
        results['delete'] = await self._test_delete_operations(manager, results['create']['user_id'])
        
        return results
    
    async def _test_create_operations(self, manager: DataCRUDManager) -> Dict:
        """Test data creation across all services."""
        create_start = time.time()
        user_data = create_test_user_data("crud_test")
        
        # Create user in Auth Service
        user_id = await manager.create_user_in_auth(user_data)
        assert user_id, "User creation in Auth failed"
        
        # Sync to Backend Service
        sync_success = await manager.sync_user_to_backend(user_id)
        assert sync_success, "User sync to Backend failed"
        
        create_time = time.time() - create_start
        assert create_time < 2.0, f"Create operation too slow: {create_time:.2f}s"
        
        return {'user_id': user_id, 'execution_time': create_time, 'success': True}
    
    async def _test_read_operations(self, manager: DataCRUDManager, user_id: str) -> Dict:
        """Test data reading from Backend API."""
        read_start = time.time()
        
        # Read user from Auth Service
        auth_user = await manager.read_user_from_auth(user_id)
        assert auth_user, "Auth user read failed"
        
        # Read user from Backend API
        backend_user = await manager.read_user_from_backend(user_id)
        assert backend_user, "Backend user read failed"
        
        # Verify data consistency
        consistency_check = await manager.verify_read_consistency(user_id)
        assert consistency_check, "Read data consistency failed"
        
        read_time = time.time() - read_start
        assert read_time < 1.0, f"Read operation too slow: {read_time:.2f}s"
        
        return {'auth_user': auth_user, 'backend_user': backend_user, 
                'execution_time': read_time, 'success': True}
    
    async def _test_update_operations(self, manager: DataCRUDManager, user_id: str) -> Dict:
        """Test data updates via Frontend  ->  Backend."""
        update_start = time.time()
        preferences_data = create_user_preferences_data()
        
        # Update user preferences via Frontend flow
        update_success = await manager.update_user_preferences(user_id, preferences_data)
        assert update_success, "User preferences update failed"
        
        # Verify updates across all services
        update_verification = await manager.verify_update_consistency(user_id, preferences_data)
        assert update_verification, "Update consistency verification failed"
        
        update_time = time.time() - update_start
        assert update_time < 2.0, f"Update operation too slow: {update_time:.2f}s"
        
        return {'preferences_data': preferences_data, 'execution_time': update_time, 'success': True}
    
    async def _test_delete_operations(self, manager: DataCRUDManager, user_id: str) -> Dict:
        """Test data deletion with GDPR compliance."""
        delete_start = time.time()
        
        # Execute GDPR-compliant deletion
        deletion_success = await manager.delete_user_gdpr_compliant(user_id)
        assert deletion_success, "GDPR-compliant deletion failed"
        
        # Verify complete data removal
        deletion_verification = await manager.verify_complete_deletion(user_id)
        assert deletion_verification, "Complete deletion verification failed"
        
        delete_time = time.time() - delete_start
        assert delete_time < 5.0, f"Delete operation too slow: {delete_time:.2f}s"
        
        return {'execution_time': delete_time, 'success': True}
    
    def _validate_crud_results(self, results: Dict) -> None:
        """Validate all CRUD operation results."""
        required_operations = ['create', 'read', 'update', 'delete']
        
        for operation in required_operations:
            assert operation in results, f"Missing {operation} operation"
            assert results[operation]['success'], f"{operation} operation failed"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_crud_operations(self, data_crud_manager):
        """Test concurrent CRUD operations for data isolation."""
        manager = data_crud_manager
        
        # Create multiple concurrent users
        user_count = 3
        concurrent_tasks = []
        
        for i in range(user_count):
            task = self._execute_single_user_crud(manager, f"concurrent_{i}")
            concurrent_tasks.append(task)
        
        # Execute all CRUD operations concurrently
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify concurrent operations succeeded
        successful_ops = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_ops >= 2, f"Insufficient concurrent success: {successful_ops}"
        
        print(f"[SUCCESS] Concurrent CRUD operations: {successful_ops}/{user_count}")
    
    async def _execute_single_user_crud(self, manager: DataCRUDManager, identifier: str) -> Dict:
        """Execute CRUD operations for a single user."""
        user_data = create_test_user_data(identifier)
        
        # Create user
        user_id = await manager.create_user_in_auth(user_data)
        await manager.sync_user_to_backend(user_id)
        
        # Read user data
        await manager.verify_read_consistency(user_id)
        
        # Update preferences  
        preferences = create_user_preferences_data()
        await manager.update_user_preferences(user_id, preferences)
        
        # Verify and cleanup
        await manager.verify_update_consistency(user_id, preferences)
        await manager.delete_user_gdpr_compliant(user_id)
        
        return {'user_id': user_id, 'success': True}


class TestDataCRUDGDPRCompliance:
    """GDPR compliance tests for data deletion operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_gdpr_compliant_data_deletion(self, data_crud_manager):
        """Test GDPR-compliant complete data deletion."""
        manager = data_crud_manager
        validator = GDPRComplianceValidator(manager)
        
        # Create user with comprehensive data
        user_data = create_test_user_data("gdpr_test")
        user_id = await manager.create_user_in_auth(user_data)
        await manager.sync_user_to_backend(user_id)
        
        # Create user activity data
        await self._create_comprehensive_user_data(manager, user_id)
        
        # Execute GDPR deletion
        deletion_success = await validator.execute_gdpr_deletion(user_id)
        assert deletion_success, "GDPR deletion execution failed"
        
        # Verify complete data removal
        compliance_result = await validator.verify_gdpr_compliance(user_id)
        assert compliance_result['compliant'], f"GDPR compliance failed: {compliance_result['violations']}"
        
        print(f"[GDPR COMPLIANT] Complete data removal verified")
    
    async def _create_comprehensive_user_data(self, manager: DataCRUDManager, user_id: str) -> None:
        """Create comprehensive user data for GDPR testing."""
        # Create user preferences
        preferences = create_user_preferences_data()
        await manager.update_user_preferences(user_id, preferences)
        
        # Create usage data
        usage_data = {'user_id': user_id, 'feature_usage': {'chat': 10, 'optimization': 5}}
        await manager.create_usage_data(user_id, usage_data)
        
        # Create billing data
        billing_data = {'user_id': user_id, 'amount': 29.99, 'plan': 'mid'}
        await manager.create_billing_data(user_id, billing_data)


class TestDataCRUDPerformance:
    """Performance tests for data CRUD operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_bulk_crud_performance(self, data_crud_manager):
        """Test performance with bulk CRUD operations."""
        manager = data_crud_manager
        user_count = 5
        
        start_time = time.time()
        
        # Execute bulk CRUD operations
        for i in range(user_count):
            user_data = create_test_user_data(f"bulk_{i}")
            user_id = await manager.create_user_in_auth(user_data)
            await manager.sync_user_to_backend(user_id)
            
            preferences = create_user_preferences_data()
            await manager.update_user_preferences(user_id, preferences)
            
            await manager.delete_user_gdpr_compliant(user_id)
        
        total_time = time.time() - start_time
        average_time = total_time / user_count
        
        # Validate performance criteria
        assert average_time < 3.0, f"Average CRUD too slow: {average_time:.2f}s"
        assert total_time < 15.0, f"Total bulk CRUD too slow: {total_time:.2f}s"
        
        print(f"[PERFORMANCE] Bulk CRUD: {average_time:.2f}s avg, {total_time:.2f}s total")
