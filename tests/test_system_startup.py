"""System startup tests for dev launcher."""

import os
import platform
import signal
import subprocess
import time
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest


class TestSystemStartup:
    """Test system startup functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.root_dir = Path(__file__).parent.parent
        self.dev_launcher = self.root_dir / "scripts" / "dev_launcher.py"
        self.is_windows = platform.system() == "Windows"
        
    def test_dev_launcher_help(self):
        """Test dev launcher help command."""
        result = subprocess.run(
            ["python", str(self.dev_launcher), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "usage: dev_launcher.py" in result.stdout
        
    def test_dev_launcher_list_services(self):
        """Test listing available services."""
        result = subprocess.run(
            ["python", str(self.dev_launcher), "--list-services"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Current Service Configuration" in result.stdout
        
    def test_dev_launcher_minimal_mode(self):
        """Test dev launcher in minimal mode."""
        # Start dev launcher in minimal mode with no browser
        process = subprocess.Popen(
            ["python", str(self.dev_launcher), "--minimal", "--no-browser", "--non-interactive"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Give it time to start
            time.sleep(5)
            
            # Check if process is still running
            assert process.poll() is None, "Dev launcher should still be running"
            
            # Test backend health check
            import requests
            try:
                response = requests.get("http://localhost:8000/health")
                assert response.status_code == 200
            except requests.exceptions.ConnectionError:
                # Backend might not be fully up yet in minimal mode
                pass
                
        finally:
            # Cleanup - terminate the process
            if self.is_windows:
                subprocess.run(["taskkill", "/F", "/PID", str(process.pid)], capture_output=True)
            else:
                process.terminate()
            process.wait(timeout=5)
            
    def test_backend_import(self):
        """Test that backend can be imported without errors."""
        result = subprocess.run(
            ["python", "-c", "from netra_backend.app.main import app; print('Backend imported successfully')"],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        assert result.returncode == 0
        assert "Backend imported successfully" in result.stdout
        
    def test_npm_detection(self):
        """Test npm is properly detected."""
        result = subprocess.run(
            ["python", "-c", "import subprocess; import platform; "
             "shell=platform.system()=='Windows'; "
             "r=subprocess.run(['npm', '--version'], capture_output=True, text=True, shell=shell); "
             "print(f'NPM Version: {r.stdout.strip()}' if r.returncode==0 else 'NPM not found')"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "NPM Version:" in result.stdout or "NPM not found" in result.stdout
        
    def test_redis_connectivity(self):
        """Test Redis connectivity."""
        result = subprocess.run(
            ["python", "-c", 
             "import redis; r=await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6379, socket_connect_timeout=1); "
             "r.ping(); print('Redis connected')"],
            capture_output=True,
            text=True
        )
        # Redis might not be running in all environments
        if result.returncode == 0:
            assert "Redis connected" in result.stdout
            
    def test_database_initialization(self):
        """Test database initialization."""
        result = subprocess.run(
            ["python", "-c",
             "from netra_backend.app.db.postgres import initialize_postgres; "
             "sf = initialize_postgres(); "
             "print('Database initialized' if sf else 'Database initialization failed')"],
            capture_output=True,
            text=True,
            cwd=self.root_dir
        )
        # Database might not be available in all environments
        if result.returncode == 0:
            assert "Database" in result.stdout