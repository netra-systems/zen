"""
Integration tests to replicate issues identified from auth service staging logs.

These tests are designed to FAIL initially to demonstrate the staging issues:
1. HEAD method returns 405 on /health endpoint (monitoring compatibility issue)
2. Database schema initialization not idempotent (UniqueViolationError warnings)
"""

import asyncio
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from auth_service.main import app
from auth_service.auth_core.database.connection import auth_db
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_service,
    pytest.mark.staging_issues,
    pytest.mark.asyncio
]

class TestStagingLogIssues:
    """Test cases that replicate issues found in staging logs."""
    
    def setup_method(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    def test_health_endpoint_head_method_support(self):
        """
        Test that HEAD method is supported on /health endpoint.
        
        EXPECTED FAILURE: Currently returns 405 Method Not Allowed.
        Staging logs show monitoring systems using HEAD requests failing with 405.
        """
        # Test HEAD request to health endpoint
        response = self.client.head("/health")
        
        # This should pass but currently fails with 405
        assert response.status_code == 200, f"HEAD /health should return 200, got {response.status_code}"
        
        # HEAD requests should return same headers as GET but no body
        assert response.headers.get("content-type") is not None
        assert len(response.content) == 0  # HEAD should have empty body
    
    def test_auth_health_endpoint_head_method_support(self):
        """
        Test that HEAD method is supported on /auth/health endpoint.
        
        EXPECTED FAILURE: Currently returns 405 Method Not Allowed.
        """
        response = self.client.head("/auth/health")
        
        # This should pass but currently fails with 405
        assert response.status_code == 200, f"HEAD /auth/health should return 200, got {response.status_code}"
        
        # Verify headers are present but no body
        assert response.headers.get("content-type") is not None
        assert len(response.content) == 0
    
    def test_monitoring_endpoints_head_method_support(self):
        """
        Test that HEAD method works for other monitoring endpoints.
        
        EXPECTED FAILURE: These endpoints likely don't support HEAD method.
        """
        monitoring_endpoints = [
            "/docs",
            "/openapi.json",
            "/readiness", 
            "/health/ready"
        ]
        
        for endpoint in monitoring_endpoints:
            response = self.client.head(endpoint)
            
            # Monitoring systems commonly use HEAD requests
            # These should return 200 or at least not 405
            assert response.status_code != 405, f"HEAD {endpoint} should not return 405 Method Not Allowed"
    
    async def test_database_initialization_idempotency(self):
        """
        Test that database initialization can be run multiple times without errors.
        
        EXPECTED FAILURE: Currently raises UniqueViolationError on repeated initialization.
        Staging logs show warnings about duplicate constraint violations during startup.
        """
        try:
            # First initialization - should succeed
            await auth_db.initialize()
            first_init_success = True
        except Exception as e:
            first_init_success = False
            pytest.fail(f"First database initialization failed: {e}")
        
        try:
            # Second initialization - should be idempotent (not fail)
            await auth_db.initialize()
            second_init_success = True
        except IntegrityError as e:
            # This is the expected failure - UniqueViolationError
            second_init_success = False
            pytest.fail(f"Database initialization not idempotent - got IntegrityError: {e}")
        except Exception as e:
            second_init_success = False
            pytest.fail(f"Database initialization failed with unexpected error: {e}")
        
        assert first_init_success and second_init_success, "Database initialization should be idempotent"
    
    async def test_database_table_creation_idempotency(self):
        """
        Test that table creation handles existing tables gracefully.
        
        EXPECTED FAILURE: May raise errors when tables already exist.
        """
        from auth_service.auth_core.database.models import Base
        
        try:
            # Create tables first time
            async with auth_db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            pytest.fail(f"First table creation failed: {e}")
        
        try:
            # Create tables second time - should handle existing tables gracefully
            async with auth_db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            pytest.fail(f"Second table creation should be idempotent but failed: {e}")
    
    async def test_database_initialization_with_partial_schema(self):
        """
        Test database initialization when schema is partially present.
        
        EXPECTED FAILURE: May not handle partial schema states properly.
        """
        # This test simulates interrupted initialization scenarios
        try:
            # Initialize database
            await auth_db.initialize()
            
            # Simulate partial schema by dropping one table
            async with auth_db.engine.begin() as conn:
                await conn.execute("DROP TABLE IF EXISTS auth_sessions CASCADE")
            
            # Try to reinitialize - should handle missing tables
            await auth_db.initialize()
            
        except Exception as e:
            pytest.fail(f"Database initialization with partial schema failed: {e}")
    
    async def test_database_initialization_recovery_from_interruption(self):
        """
        Test that database can recover from interrupted initialization.
        
        EXPECTED FAILURE: May not handle interrupted states properly.
        """
        try:
            # Simulate interrupted initialization by creating some but not all objects
            async with auth_db.engine.begin() as conn:
                # Create just the schema/database but not all tables
                await conn.execute("CREATE SCHEMA IF NOT EXISTS auth")
            
            # Now try full initialization - should complete successfully
            await auth_db.initialize()
            
        except Exception as e:
            pytest.fail(f"Database recovery from interruption failed: {e}")

class TestHeadMethodSupport:
    """Comprehensive tests for HEAD method support across endpoints."""
    
    def setup_method(self):
        """Set up test client for each test."""
        self.client = TestClient(app)
    
    @pytest.mark.parametrize("endpoint", [
        "/",
        "/health", 
        "/readiness",
        "/health/ready",
        "/auth/health",
        "/docs",
        "/openapi.json"
    ])
    def test_head_method_support_comprehensive(self, endpoint):
        """
        Test HEAD method support across all public endpoints.
        
        EXPECTED FAILURE: Most endpoints likely don't explicitly support HEAD.
        """
        # First get the GET response for comparison
        get_response = self.client.get(endpoint)
        
        if get_response.status_code not in [200, 404]:
            pytest.skip(f"GET {endpoint} returned {get_response.status_code}, skipping HEAD test")
        
        # Now test HEAD method
        head_response = self.client.head(endpoint)
        
        # HEAD should return same status as GET
        assert head_response.status_code == get_response.status_code, \
            f"HEAD {endpoint} status {head_response.status_code} != GET status {get_response.status_code}"
        
        # HEAD should have same headers but empty body
        assert len(head_response.content) == 0, f"HEAD {endpoint} should have empty body"
        
        # Content-Type header should match if present
        get_content_type = get_response.headers.get("content-type")
        head_content_type = head_response.headers.get("content-type")
        if get_content_type:
            assert head_content_type == get_content_type, \
                f"HEAD {endpoint} Content-Type mismatch: {head_content_type} != {get_content_type}"

class TestDatabaseIdempotency:
    """Comprehensive tests for database initialization idempotency."""
    
    @pytest.mark.asyncio
    async def test_multiple_database_initializations(self):
        """
        Test running database initialization multiple times in sequence.
        
        EXPECTED FAILURE: May fail with constraint violations.
        """
        initialization_count = 5
        
        for i in range(initialization_count):
            try:
                await auth_db.initialize()
            except Exception as e:
                pytest.fail(f"Database initialization #{i+1} failed: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_database_initializations(self):
        """
        Test concurrent database initialization attempts.
        
        EXPECTED FAILURE: May fail with race conditions or constraint violations.
        """
        async def init_db():
            try:
                await auth_db.initialize()
                return True
            except Exception as e:
                return f"Failed: {e}"
        
        # Run 3 concurrent initializations
        tasks = [init_db() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least one should succeed, others should not fail catastrophically
        success_count = sum(1 for result in results if result is True)
        
        assert success_count >= 1, f"At least one initialization should succeed, got results: {results}"
        
        # No result should be an unhandled exception
        for i, result in enumerate(results):
            assert not isinstance(result, Exception) or "Failed:" in str(result), \
                f"Initialization #{i+1} had unhandled exception: {result}"

class TestAdditionalStagingIssues:
    """Test cases for additional issues that might be present."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_options_method_support_for_cors(self):
        """
        Test that OPTIONS method is supported for CORS preflight requests.
        
        May fail if CORS preflight is not properly configured.
        """
        response = self.client.options("/auth/login")
        
        # OPTIONS should not return 405 Method Not Allowed
        assert response.status_code != 405, "OPTIONS requests should be supported for CORS"
        
        # Should have CORS headers
        assert "access-control-allow-methods" in response.headers or \
               "Access-Control-Allow-Methods" in response.headers, \
               "OPTIONS response should include CORS headers"
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion_recovery(self):
        """
        Test that database connection pool can recover from exhaustion.
        
        May fail if connection pool management is not robust.
        """
        # This would require creating many connections to exhaust pool
        # For now, just test basic connection acquisition
        try:
            async with auth_db.get_session() as session:
                # Test that we can acquire a connection
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
        except Exception as e:
            pytest.fail(f"Basic database connection test failed: {e}")
    
    def test_health_check_under_load(self):
        """
        Test health check endpoint performance under repeated requests.
        
        May fail if health check is not optimized for frequent monitoring.
        """
        import time
        
        # Make multiple rapid health check requests
        start_time = time.time()
        for i in range(10):
            response = self.client.get("/health")
            assert response.status_code == 200, f"Health check #{i+1} failed"
        
        elapsed_time = time.time() - start_time
        
        # Health checks should be fast (less than 1 second for 10 requests)
        assert elapsed_time < 1.0, f"Health checks took too long: {elapsed_time:.2f}s for 10 requests"