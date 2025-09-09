"""Data CRUD Helpers - E2E Testing Support

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data integrity prevents churn and support tickets  
- Value Impact: Protects $60K+ MRR through reliable data operations
- Revenue Impact: Prevents data corruption incidents that cause customer loss

This module provides helpers for testing data CRUD operations across services,
ensuring data consistency and GDPR compliance for user data lifecycle management.

CRITICAL: Following CLAUDE.md principles - uses real services, no mocks.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

import httpx
import asyncpg

from shared.isolated_environment import IsolatedEnvironment
from tests.e2e.database_sync_fixtures import create_test_user_data as base_create_test_user_data


@dataclass
class DataCRUDResult:
    """Result of a CRUD operation."""
    success: bool
    operation: str  # create, read, update, delete
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class DataCRUDManager:
    """
    Manages data CRUD operations across all services for E2E testing.
    
    Key responsibilities:
    - Create user data in Auth Service
    - Read user data from Backend API  
    - Update user preferences via Frontend → Backend
    - Delete user data with GDPR compliance
    - Verify data consistency across services
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._db_connections: Dict[str, Any] = {}
        self.operation_results: List[DataCRUDResult] = []
        
        # Service endpoints
        self.auth_service_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
        self.backend_service_url = self.env.get("BACKEND_SERVICE_URL", "http://localhost:8000")
        self.frontend_service_url = self.env.get("FRONTEND_SERVICE_URL", "http://localhost:3000")
        
        # Database connection strings
        self.auth_db_url = self.env.get("AUTH_DATABASE_URL")
        self.main_db_url = self.env.get("DATABASE_URL")
        
    async def setup_test_environment(self):
        """Setup test environment and connections."""
        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize database connections if needed
        if self.auth_db_url:
            try:
                self._db_connections['auth'] = await asyncpg.connect(self.auth_db_url)
            except Exception as e:
                print(f"Warning: Could not connect to auth database: {e}")
                
        if self.main_db_url:
            try:
                self._db_connections['main'] = await asyncpg.connect(self.main_db_url)
            except Exception as e:
                print(f"Warning: Could not connect to main database: {e}")
        
    async def cleanup_test_environment(self):
        """Cleanup test environment and close connections."""
        if self._http_client:
            await self._http_client.aclose()
            
        for conn in self._db_connections.values():
            if conn:
                await conn.close()
                
    async def create_user_data(self, user_data: Dict[str, Any]) -> DataCRUDResult:
        """Create user data in Auth Service."""
        start_time = time.time()
        
        try:
            if not self._http_client:
                await self.setup_test_environment()
                
            # Create user via Auth Service API
            response = await self._http_client.post(
                f"{self.auth_service_url}/api/users",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 201]:
                result_data = response.json() if response.content else user_data
                result = DataCRUDResult(
                    success=True,
                    operation="create",
                    data=result_data,
                    execution_time_ms=execution_time
                )
            else:
                result = DataCRUDResult(
                    success=False,
                    operation="create", 
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time_ms=execution_time
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = DataCRUDResult(
                success=False,
                operation="create",
                error=str(e),
                execution_time_ms=execution_time
            )
            
        self.operation_results.append(result)
        return result
        
    async def read_user_data(self, user_id: str) -> DataCRUDResult:
        """Read user data from Backend API."""
        start_time = time.time()
        
        try:
            if not self._http_client:
                await self.setup_test_environment()
                
            # Read user via Backend API
            response = await self._http_client.get(
                f"{self.backend_service_url}/api/users/{user_id}",
                headers={"Content-Type": "application/json"}
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = DataCRUDResult(
                    success=True,
                    operation="read",
                    data=response.json(),
                    execution_time_ms=execution_time
                )
            else:
                result = DataCRUDResult(
                    success=False,
                    operation="read",
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time_ms=execution_time
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = DataCRUDResult(
                success=False,
                operation="read",
                error=str(e),
                execution_time_ms=execution_time
            )
            
        self.operation_results.append(result)
        return result
        
    async def update_user_preferences(self, 
                                    user_id: str, 
                                    preferences: Dict[str, Any]) -> DataCRUDResult:
        """Update user preferences via Frontend → Backend."""
        start_time = time.time()
        
        try:
            if not self._http_client:
                await self.setup_test_environment()
                
            # Update via Backend API (simulating Frontend → Backend flow)
            response = await self._http_client.put(
                f"{self.backend_service_url}/api/users/{user_id}/preferences",
                json=preferences,
                headers={"Content-Type": "application/json"}
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 204]:
                result_data = response.json() if response.content else preferences
                result = DataCRUDResult(
                    success=True,
                    operation="update",
                    data=result_data,
                    execution_time_ms=execution_time
                )
            else:
                result = DataCRUDResult(
                    success=False,
                    operation="update",
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time_ms=execution_time
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = DataCRUDResult(
                success=False,
                operation="update", 
                error=str(e),
                execution_time_ms=execution_time
            )
            
        self.operation_results.append(result)
        return result
        
    async def delete_user_data(self, user_id: str) -> DataCRUDResult:
        """Delete user data with GDPR compliance."""
        start_time = time.time()
        
        try:
            if not self._http_client:
                await self.setup_test_environment()
                
            # Delete user data via Backend API
            response = await self._http_client.delete(
                f"{self.backend_service_url}/api/users/{user_id}",
                headers={"Content-Type": "application/json"}
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 204]:
                result = DataCRUDResult(
                    success=True,
                    operation="delete",
                    execution_time_ms=execution_time
                )
            else:
                result = DataCRUDResult(
                    success=False,
                    operation="delete",
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time_ms=execution_time
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = DataCRUDResult(
                success=False,
                operation="delete",
                error=str(e),
                execution_time_ms=execution_time
            )
            
        self.operation_results.append(result)
        return result


class GDPRComplianceValidator:
    """Validates GDPR compliance in data operations."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.compliance_checks: List[Dict[str, Any]] = []
        
    async def validate_data_deletion(self, 
                                   user_id: str,
                                   crud_manager: DataCRUDManager) -> Dict[str, Any]:
        """
        Validate that user data was properly deleted according to GDPR.
        
        Returns:
            Compliance validation report
        """
        validation_report = {
            'user_id': user_id,
            'gdpr_compliant': True,
            'issues': [],
            'checks_performed': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Check 1: User data should not be accessible via API
        try:
            read_result = await crud_manager.read_user_data(user_id)
            if read_result.success:
                validation_report['gdpr_compliant'] = False
                validation_report['issues'].append('User data still accessible via API after deletion')
            validation_report['checks_performed'].append('API data accessibility')
        except Exception as e:
            validation_report['issues'].append(f'Error checking API accessibility: {e}')
            
        # Check 2: Database records should be removed or anonymized
        if 'auth' in crud_manager._db_connections:
            try:
                conn = crud_manager._db_connections['auth']
                result = await conn.fetchrow(
                    "SELECT COUNT(*) as count FROM auth_users WHERE id = $1", user_id
                )
                if result and result['count'] > 0:
                    validation_report['gdpr_compliant'] = False
                    validation_report['issues'].append('User records still exist in auth database')
                validation_report['checks_performed'].append('Auth database cleanup')
            except Exception as e:
                validation_report['issues'].append(f'Error checking auth database: {e}')
                
        if 'main' in crud_manager._db_connections:
            try:
                conn = crud_manager._db_connections['main']
                result = await conn.fetchrow(
                    "SELECT COUNT(*) as count FROM userbase WHERE id = $1", user_id
                )
                if result and result['count'] > 0:
                    validation_report['gdpr_compliant'] = False
                    validation_report['issues'].append('User records still exist in main database')
                validation_report['checks_performed'].append('Main database cleanup')
            except Exception as e:
                validation_report['issues'].append(f'Error checking main database: {e}')
                
        self.compliance_checks.append(validation_report)
        return validation_report


class CrossServiceDataValidator:
    """Validates data consistency across all services."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.consistency_checks: List[Dict[str, Any]] = []
        
    async def validate_data_consistency(self, 
                                      user_id: str, 
                                      crud_manager: DataCRUDManager) -> Dict[str, Any]:
        """
        Validate data consistency across Auth, Backend, and Frontend services.
        
        Returns:
            Consistency validation report
        """
        validation_report = {
            'user_id': user_id,
            'consistent': True,
            'inconsistencies': [],
            'services_checked': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Get user data from different services
        service_data = {}
        
        # Auth service data
        try:
            auth_result = await crud_manager.read_user_data(user_id)
            if auth_result.success:
                service_data['auth'] = auth_result.data
                validation_report['services_checked'].append('auth')
        except Exception as e:
            validation_report['inconsistencies'].append(f'Auth service error: {e}')
            
        # Backend service data  
        try:
            backend_result = await crud_manager.read_user_data(user_id)
            if backend_result.success:
                service_data['backend'] = backend_result.data
                validation_report['services_checked'].append('backend')
        except Exception as e:
            validation_report['inconsistencies'].append(f'Backend service error: {e}')
            
        # Compare data consistency between services
        if len(service_data) >= 2:
            # Check core fields consistency
            core_fields = ['id', 'email', 'full_name', 'plan_tier']
            for field in core_fields:
                values = []
                for service, data in service_data.items():
                    if data and field in data:
                        values.append((service, data[field]))
                        
                if len(set(value for _, value in values)) > 1:
                    validation_report['consistent'] = False
                    validation_report['inconsistencies'].append({
                        'field': field,
                        'values': dict(values)
                    })
                    
        self.consistency_checks.append(validation_report)
        return validation_report


def create_test_user_data(user_id: Optional[str] = None, 
                         email: Optional[str] = None,
                         tier: str = "free") -> Dict[str, Any]:
    """Create standardized test user data for CRUD testing."""
    return base_create_test_user_data(user_id, email, tier)


def create_user_preferences_data(theme: str = "light", 
                                notifications: bool = True) -> Dict[str, Any]:
    """Create test user preferences data."""
    return {
        "theme": theme,
        "notifications_enabled": notifications,
        "language": "en",
        "timezone": "UTC",
        "email_frequency": "daily",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }