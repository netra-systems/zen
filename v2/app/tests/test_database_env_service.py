"""Tests for Database Environment Service"""

import pytest
from app.services.database_env_service import DatabaseEnvironmentService

class TestDatabaseEnvironmentService:
    
    def test_validate_production_database_url(self):
        """Test validation for production environment"""
        # Valid production URL
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://produser:password@prod-db.example.com/netra_prod",
            "production"
        )
        assert result["valid"] is True
        assert result["database_name"] == "netra_prod"
        assert len(result["errors"]) == 0
        
        # Invalid - using localhost in production
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://user:password@localhost/netra_prod",
            "production"
        )
        assert result["valid"] is False
        assert any("localhost" in error for error in result["errors"])
        
        # Invalid - using test database in production
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://user:password@prod-db.example.com/netra_test",
            "production"
        )
        assert result["valid"] is False
        assert any("test" in error.lower() for error in result["errors"])
        
        # Warning - using postgres user
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:password@prod-db.example.com/netra_prod",
            "production"
        )
        assert result["valid"] is True
        assert any("postgres" in warning for warning in result["warnings"])
        
        # Invalid - no password
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://user:@prod-db.example.com/netra_prod",
            "production"
        )
        assert result["valid"] is False
        assert any("password" in error for error in result["errors"])
    
    def test_validate_development_database_url(self):
        """Test validation for development environment"""
        # Valid development URL
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:123@localhost/netra_dev",
            "development"
        )
        assert result["valid"] is True
        assert result["database_name"] == "netra_dev"
        
        # Also valid - just "netra" in development
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:123@localhost/netra",
            "development"
        )
        assert result["valid"] is True
        assert result["database_name"] == "netra"
        
        # Invalid - using production database
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:123@localhost/netra_prod",
            "development"
        )
        assert result["valid"] is False
        assert any("production" in error for error in result["errors"])
    
    def test_validate_testing_database_url(self):
        """Test validation for testing environment"""
        # Valid testing URL
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:123@localhost/netra_test",
            "testing"
        )
        assert result["valid"] is True
        assert result["database_name"] == "netra_test"
        
        # Invalid - using production database
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:123@localhost/netra_prod",
            "testing"
        )
        assert result["valid"] is False
        assert any("production" in error for error in result["errors"])
    
    def test_cross_environment_detection(self):
        """Test detection of cross-environment database usage"""
        # Development database in production
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://user:pass@prod-server/netra_dev",
            "production"
        )
        assert result["valid"] is False
        assert any("development" in error for error in result["errors"])
        
        # Test database in development
        result = DatabaseEnvironmentService.validate_database_url(
            "postgresql+asyncpg://postgres:123@localhost/netra_test",
            "development"
        )
        assert result["valid"] is False
        assert any("testing" in error for error in result["errors"])
    
    def test_get_safe_database_name(self):
        """Test safe database name generation"""
        assert DatabaseEnvironmentService.get_safe_database_name("production") == "netra_prod"
        assert DatabaseEnvironmentService.get_safe_database_name("development") == "netra_dev"
        assert DatabaseEnvironmentService.get_safe_database_name("testing") == "netra_test"
        assert DatabaseEnvironmentService.get_safe_database_name("unknown") == "netra"
    
    def test_environment_specific_connection_params(self):
        """Test environment-specific connection parameter validation"""
        service = DatabaseEnvironmentService()
        
        prod_params = service.get_connection_params("production")
        assert prod_params["pool_size"] > 10
        assert prod_params["max_overflow"] > 5
        assert prod_params["pool_timeout"] > 30
        
        dev_params = service.get_connection_params("development")
        assert dev_params["pool_size"] <= 5
        assert dev_params["echo"] is True
        
        test_params = service.get_connection_params("testing")
        assert test_params["pool_size"] == 1
        assert test_params["isolation_level"] == "AUTOCOMMIT"
    
    def test_connection_health_checks(self):
        """Test database connection health monitoring"""
        service = DatabaseEnvironmentService()
        
        health_check = service.create_health_check("production")
        assert health_check["timeout"] < 30
        assert health_check["retry_count"] >= 3
        
        dev_health_check = service.create_health_check("development")
        assert dev_health_check["timeout"] >= 30
        assert dev_health_check["detailed_logging"] is True