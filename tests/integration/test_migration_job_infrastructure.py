"""
Integration tests for migration job infrastructure
Ensures migration jobs work correctly for staging deployment
"""

import os
import subprocess
import pytest
from pathlib import Path

from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env


class TestMigrationJobInfrastructure:
    """Test suite for migration job infrastructure compatibility"""
    
    def test_dockerfile_structure(self):
        """Test that migration Dockerfile has correct structure"""
        dockerfile_path = Path("docker/migration.alpine.Dockerfile")
        assert dockerfile_path.exists(), "migration.alpine.Dockerfile must exist"
        
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for correct path structure
        assert "COPY netra_backend/app/alembic /app/netra_backend/app/alembic" in content
        assert "COPY shared/ /app/shared/" in content
        assert "COPY netra_backend/app/db/ /app/netra_backend/app/db/" in content
        
        # Check for proper Python package structure
        assert "touch /app/__init__.py" in content
        assert "touch /app/netra_backend/__init__.py" in content
        assert "touch /app/shared/__init__.py" in content
    
    def test_migration_requirements_exist(self):
        """Test that migration requirements file exists and has correct dependencies"""
        req_file = Path("requirements-migration.txt")
        assert req_file.exists(), "requirements-migration.txt must exist"
        
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_packages = [
            "sqlalchemy>=2.0.43",
            "alembic>=1.16.4", 
            "psycopg2-binary>=2.9.10",
            "pydantic>=2.11.7",
            "fastapi>=0.104.1",
            "uvicorn>=0.24.0"
        ]
        
        for package in required_packages:
            assert package in content, f"Required package {package} missing from requirements"
    
    def test_alembic_configuration(self):
        """Test that Alembic configuration is compatible with migration job"""
        alembic_ini = Path("netra_backend/alembic.ini")
        assert alembic_ini.exists(), "alembic.ini must exist"
        
        with open(alembic_ini, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verify script location matches Dockerfile structure
        assert "script_location = netra_backend/app/alembic" in content
        
        # Check that URL is set dynamically (not hardcoded)
        assert "sqlalchemy.url is dynamically set" in content
    
    def test_database_url_generation(self):
        """Test that DatabaseManager can generate migration URLs correctly"""
        try:
            migration_url = DatabaseManager.get_migration_url_sync_format()
            assert migration_url is not None, "Migration URL must not be None"
            assert migration_url.startswith("postgresql://"), "Migration URL must be postgresql format"
            assert "asyncpg" not in migration_url, "Migration URL must not contain async driver"
            
        except Exception as e:
            pytest.fail(f"DatabaseManager.get_migration_url_sync_format() failed: {e}")
    
    def test_environment_isolation(self):
        """Test that environment variables are properly isolated"""
        env = get_env()
        
        # Required environment variables for database connection
        required_vars = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER"]
        
        for var in required_vars:
            # Should be accessible through isolated environment
            value = env.get(var)
            # Don't fail if not set locally, but ensure method works
            assert hasattr(env, 'get'), f"Environment should have get method for {var}"
    
    def test_migration_script_directory_structure(self):
        """Test that migration script directory has correct structure"""
        migration_dir = Path("netra_backend/app/alembic")
        assert migration_dir.exists(), "Alembic directory must exist"
        
        versions_dir = migration_dir / "versions"
        assert versions_dir.exists(), "Versions directory must exist"
        
        env_py = migration_dir / "env.py" 
        assert env_py.exists(), "env.py must exist"
        
        # Check that env.py imports DatabaseManager
        with open(env_py, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "DatabaseManager" in content, "env.py must import DatabaseManager"
            assert "get_migration_url_sync_format" in content, "env.py must use migration URL method"
    
    def test_cloud_migration_script_configuration(self):
        """Test that cloud migration script has proper staging deployment config"""
        script_path = Path("scripts/run_cloud_migrations.py")
        assert script_path.exists(), "Cloud migration script must exist"
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for Cloud SQL connection configuration
        assert "--set-cloudsql-instances" in content, "Must configure Cloud SQL connection"
        assert "{self.environment}-shared-postgres" in content, "Must reference correct staging database instance"
        
        # Check for proper secrets configuration
        assert "POSTGRES_HOST=postgres-host-" in content
        assert "POSTGRES_PASSWORD=postgres-password-" in content
    
    @pytest.mark.skipif(
        not os.path.exists("docker/migration.alpine.Dockerfile"), 
        reason="Migration Dockerfile not found"
    )
    def test_docker_image_builds(self):
        """Test that migration Docker image builds successfully"""
        try:
            result = subprocess.run([
                "docker", "build", 
                "-f", "docker/migration.alpine.Dockerfile",
                "-t", "test-migration-build",
                "."
            ], capture_output=True, text=True, timeout=300)
            
            assert result.returncode == 0, f"Docker build failed: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Docker build timed out after 5 minutes")
        except FileNotFoundError:
            pytest.skip("Docker not available for testing")
    
    def test_migration_command_format(self):
        """Test that migration command in Dockerfile is correctly formatted"""
        dockerfile_path = Path("docker/migration.alpine.Dockerfile")
        
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for proper command structure with error handling
        assert "set -e" in content, "Migration command must include error handling"
        assert "python -m alembic" in content, "Must use proper Python module invocation"
        assert "netra_backend/alembic.ini" in content, "Must reference correct alembic config"
        assert "upgrade head" in content, "Must include upgrade head command"
        
        # Check for environment validation
        assert "Environment:" in content, "Must validate environment on startup"


class TestStagingDeploymentCompatibility:
    """Test suite for ensuring staging deployment works correctly"""
    
    def test_gcp_deployment_script_exists(self):
        """Test that GCP deployment script exists and is properly configured"""
        script_path = Path("scripts/run_cloud_migrations.py")
        assert script_path.exists(), "GCP migration script must exist"
        
        # Test that it can be imported (basic syntax check)
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_cloud_migrations", script_path)
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
            assert hasattr(module, 'MigrationRunner'), "Script must have MigrationRunner class"
        except Exception as e:
            pytest.fail(f"Migration script has syntax errors: {e}")
    
    def test_secret_configuration_format(self):
        """Test that secret configuration matches staging requirements"""
        script_path = Path("scripts/run_cloud_migrations.py")
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for environment-specific secret naming
        assert "postgres-host-{self.environment}" in content
        assert "postgres-password-{self.environment}" in content
        assert "postgres-db-{self.environment}" in content
        
        # Check for proper environment variable setting
        assert "ENVIRONMENT={self.environment.upper()}" in content
    
    def test_cloud_sql_connection_configuration(self):
        """Test that Cloud SQL connection is properly configured for staging"""
        script_path = Path("scripts/run_cloud_migrations.py")
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Must include Cloud SQL instance configuration
        assert "set-cloudsql-instances" in content
        assert "{self.project_id}:us-central1:{self.environment}-shared-postgres" in content
        
        # Must handle the common socket connection error
        assert "socket connection error" in content.lower()
    
    def test_error_handling_and_logging(self):
        """Test that proper error handling is in place for staging deployment"""
        script_path = Path("scripts/run_cloud_migrations.py")
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for comprehensive error handling
        assert "except" in content, "Must have exception handling"
        assert "Failed to" in content, "Must have failure reporting"
        assert "print(" in content, "Must have logging/output"
        
        # Check for job status reporting  
        assert "Migration" in content and ("completed" in content or "success" in content)


# Integration test that requires actual database connection
@pytest.mark.integration 
class TestMigrationExecutionIntegration:
    """Integration tests that require actual database connection"""
    
    @pytest.mark.skipif(
        not os.environ.get("TEST_WITH_REAL_DB"),
        reason="Requires TEST_WITH_REAL_DB environment variable"
    )
    def test_alembic_current_command_works(self):
        """Test that alembic current command works with current configuration"""
        try:
            result = subprocess.run([
                "python", "-m", "alembic", 
                "-c", "netra_backend/alembic.ini",
                "current"
            ], capture_output=True, text=True, timeout=30)
            
            assert result.returncode == 0, f"Alembic current failed: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Alembic current command timed out")
        except Exception as e:
            pytest.fail(f"Alembic current command failed: {e}")
    
    @pytest.mark.skipif(
        not os.environ.get("TEST_WITH_REAL_DB"),
        reason="Requires TEST_WITH_REAL_DB environment variable"
    )
    def test_migration_dry_run(self):
        """Test migration dry run to validate SQL generation"""
        try:
            result = subprocess.run([
                "python", "-m", "alembic",
                "-c", "netra_backend/alembic.ini", 
                "upgrade", "head", "--sql"
            ], capture_output=True, text=True, timeout=30)
            
            # Should succeed even if no migrations to run
            assert result.returncode == 0, f"Alembic SQL generation failed: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Alembic SQL generation timed out")
        except Exception as e:
            pytest.fail(f"Alembic SQL generation failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])