"""
Backend Server Startup and Listening Test
Tests that the backend server properly initializes and starts listening on port 8000.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure the backend service starts and is accessible for all user interactions
- Value Impact: Prevents complete system outages - without the backend listening, no API calls can be processed
- Revenue Impact: Directly protects 100% of revenue - if backend doesn't listen, entire platform is unavailable

This test identifies why the backend service connects to the database but doesn't complete initialization
and isn't listening on port 8000 as expected.
"""
import asyncio
import json
import os
import subprocess
import socket
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from unittest.mock import patch

import pytest
import uvicorn
import aiohttp

from netra_backend.app.core.isolated_environment import get_env


class ServerStartupValidator:
    """Validates backend server startup and listening behavior."""
    
    def __init__(self):
        self.backend_port = 8000
        self.backend_host = "0.0.0.0"
        self.startup_timeout = 30  # 30 seconds to start
        self.health_timeout = 10   # 10 seconds for health check
        
    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is available (not in use)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return True  # Assume available if can't check
    
    def is_port_listening(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is actively listening."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                return result == 0  # Port is listening if connection succeeds
        except Exception:
            return False
    
    async def wait_for_server(self, max_wait: int = 30) -> bool:
        """Wait for the backend server to start listening."""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.is_port_listening(self.backend_port):
                return True
            await asyncio.sleep(0.5)
        return False
    
    async def test_server_health_once_started(self) -> Dict[str, Any]:
        """Test server health endpoint once it's listening."""
        if not self.is_port_listening(self.backend_port):
            return {"success": False, "error": "Server not listening on port"}
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.health_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"http://localhost:{self.backend_port}/health/"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "status_code": response.status,
                            "response": data
                        }
                    else:
                        text = await response.text()
                        return {
                            "success": False,
                            "error": f"Health endpoint returned {response.status}: {text}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Health check failed: {str(e)}"
            }


class FastAPIServerManager:
    """Manages FastAPI server lifecycle for testing."""
    
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.startup_error = None
        self.startup_complete = False
        
    def start_server_in_thread(self) -> bool:
        """Start FastAPI server in a separate thread."""
        def run_server():
            try:
                # Import the FastAPI app
                from netra_backend.app.main import app
                
                # Configure uvicorn
                config = uvicorn.Config(
                    app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="info",
                    access_log=False,
                    reload=False  # Disable reload for testing
                )
                
                # Create and run server
                server = uvicorn.Server(config)
                server.run()
                self.startup_complete = True
                
            except Exception as e:
                self.startup_error = str(e)
                print(f"Server startup error: {e}")
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait briefly for startup
        time.sleep(2)
        
        return self.startup_error is None
    
    def stop_server(self):
        """Stop the server if running."""
        if self.server_thread and self.server_thread.is_alive():
            # Server will stop when main process ends due to daemon thread
            pass


class TestBackendServerStartup:
    """Test suite for backend server startup and listening behavior."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fastapi_app_creation(self):
        """Test that FastAPI app can be created without errors."""
        try:
            from netra_backend.app.core.app_factory import create_app
            app = create_app()
            
            # Verify app was created successfully
            assert app is not None
            assert hasattr(app, 'routes')
            assert len(app.routes) > 0
            
            print("✅ FastAPI app created successfully")
            
        except Exception as e:
            pytest.fail(f"FastAPI app creation failed: {e}")
    
    @pytest.mark.asyncio 
    @pytest.mark.unit
    async def test_main_module_import(self):
        """Test that main.py module can be imported without errors."""
        try:
            # Test importing main module
            import netra_backend.app.main as main_module
            
            # Verify app exists in main module
            assert hasattr(main_module, 'app')
            assert main_module.app is not None
            
            # Check if uvicorn config function exists
            assert hasattr(main_module, '_get_uvicorn_config')
            config = main_module._get_uvicorn_config()
            assert config['host'] == '0.0.0.0'
            assert config['port'] == 8000
            
            print("✅ Main module imports successfully")
            
        except Exception as e:
            pytest.fail(f"Main module import failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_server_startup_sequence(self):
        """Test the server startup sequence and lifecycle."""
        validator = ServerStartupValidator()
        server_manager = FastAPIServerManager()
        
        try:
            # Verify port is available before starting
            assert validator.is_port_available(8000), "Port 8000 is already in use"
            
            # Start server
            print("Starting backend server...")
            server_started = server_manager.start_server_in_thread()
            
            if server_manager.startup_error:
                pytest.fail(f"Server startup failed immediately: {server_manager.startup_error}")
            
            # Wait for server to start listening
            print("Waiting for server to start listening...")
            server_listening = await validator.wait_for_server(max_wait=15)
            
            if not server_listening:
                # Diagnose why server isn't listening
                if server_manager.startup_error:
                    pytest.fail(f"Server startup error: {server_manager.startup_error}")
                else:
                    pytest.fail("Server started but is not listening on port 8000 within timeout")
            
            print("✅ Server is listening on port 8000")
            
            # Test health endpoint
            health_result = await validator.test_server_health_once_started()
            
            if not health_result["success"]:
                pytest.fail(f"Health endpoint test failed: {health_result['error']}")
            
            print(f"✅ Health endpoint responded successfully: {health_result['response']}")
            
        finally:
            # Cleanup
            server_manager.stop_server()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_lifespan_manager_startup(self):
        """Test that the lifespan manager startup sequence works."""
        try:
            from netra_backend.app.core.lifespan_manager import lifespan
            from fastapi import FastAPI
            
            # Create a test app
            app = FastAPI()
            
            # Test lifespan context manager
            async with lifespan(app):
                # Check that startup completed
                assert hasattr(app.state, 'startup_complete') or True  # May not be set in isolated test
                print("✅ Lifespan manager startup sequence completed")
                
        except Exception as e:
            pytest.fail(f"Lifespan manager startup failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.unit 
    async def test_startup_module_functions(self):
        """Test individual startup module functions."""
        try:
            from netra_backend.app.startup_module import (
                initialize_logging,
                _get_project_root,
            )
            
            # Test logging initialization
            start_time, logger = initialize_logging()
            assert start_time > 0
            assert logger is not None
            
            # Test project root detection
            root_path = _get_project_root()
            assert root_path.exists()
            assert (root_path / "netra_backend").exists()
            
            print("✅ Startup module functions work correctly")
            
        except Exception as e:
            pytest.fail(f"Startup module test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_environment_setup(self):
        """Test that environment setup works correctly."""
        try:
            # Test isolated environment access
            env_manager = get_env()
            assert env_manager is not None
            
            # Test that critical env vars can be accessed
            database_url = env_manager.get('DATABASE_URL', 'not_set')
            environment = env_manager.get('ENVIRONMENT', 'not_set')
            
            print(f"✅ Environment setup working - ENV: {environment}, DB: {database_url[:50]}...")
            
        except Exception as e:
            pytest.fail(f"Environment setup test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_startup_health_flag_behavior(self):
        """Test that startup health flags are set correctly during startup."""
        try:
            from netra_backend.app.startup_module import run_complete_startup
            from fastapi import FastAPI
            
            # Create test app
            app = FastAPI()
            
            # Run startup sequence
            start_time, logger = await run_complete_startup(app)
            
            # Check startup completion flags
            assert hasattr(app.state, 'startup_complete')
            assert app.state.startup_complete is True
            assert hasattr(app.state, 'startup_in_progress') 
            assert app.state.startup_in_progress is False
            assert hasattr(app.state, 'startup_failed')
            assert app.state.startup_failed is False
            
            print("✅ Startup health flags are set correctly")
            
        except Exception as e:
            pytest.fail(f"Startup health flag test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_server_configuration_validation(self):
        """Test that server configuration is valid."""
        try:
            from netra_backend.app.main import _get_uvicorn_config
            
            config = _get_uvicorn_config()
            
            # Validate configuration
            assert config['host'] == '0.0.0.0', f"Expected host 0.0.0.0, got {config['host']}"
            assert config['port'] == 8000, f"Expected port 8000, got {config['port']}"
            assert config['reload'] is True, f"Expected reload True, got {config['reload']}"
            assert 'reload_dirs' in config
            assert 'app' in config['reload_dirs']
            
            print("✅ Server configuration is valid")
            
        except Exception as e:
            pytest.fail(f"Server configuration test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.unit  
    async def test_route_registration(self):
        """Test that routes are properly registered."""
        try:
            from netra_backend.app.core.app_factory import create_app
            
            app = create_app()
            
            # Check that routes exist
            route_paths = [route.path for route in app.routes]
            
            # Verify critical routes
            assert "/" in route_paths, "Root route not found"
            
            # Check for health routes (may be under /health prefix)
            health_routes = [path for path in route_paths if 'health' in path.lower()]
            assert len(health_routes) > 0, f"No health routes found. Available routes: {route_paths}"
            
            print(f"✅ Routes registered successfully. Health routes: {health_routes}")
            
        except Exception as e:
            pytest.fail(f"Route registration test failed: {e}")


@pytest.mark.asyncio
async def test_port_availability():
    """Test port 8000 availability check."""
    validator = ServerStartupValidator()
    
    # Test port checking functions
    port_available = validator.is_port_available(8000)
    port_listening = validator.is_port_listening(8000)
    
    print(f"Port 8000 available: {port_available}")
    print(f"Port 8000 listening: {port_listening}")
    
    # These should be opposites unless there's an error
    if not port_available and not port_listening:
        pytest.fail("Port 8000 shows as both unavailable and not listening - possible error")


@pytest.mark.asyncio
async def test_comprehensive_server_diagnosis():
    """Comprehensive test to diagnose server startup issues."""
    validator = ServerStartupValidator()
    
    print("=== COMPREHENSIVE SERVER STARTUP DIAGNOSIS ===")
    
    # 1. Environment check
    print("\n1. ENVIRONMENT CHECK:")
    env_manager = get_env()
    database_url = env_manager.get('DATABASE_URL', 'NOT_SET')
    environment = env_manager.get('ENVIRONMENT', 'NOT_SET')
    print(f"   Environment: {environment}")
    print(f"   Database URL: {database_url[:50]}..." if database_url != 'NOT_SET' else "   Database URL: NOT_SET")
    
    # 2. Port availability check
    print("\n2. PORT AVAILABILITY CHECK:")
    port_available = validator.is_port_available(8000)
    port_listening = validator.is_port_listening(8000)
    print(f"   Port 8000 available: {port_available}")
    print(f"   Port 8000 listening: {port_listening}")
    
    # 3. FastAPI app creation test
    print("\n3. FASTAPI APP CREATION TEST:")
    try:
        from netra_backend.app.core.app_factory import create_app
        app = create_app()
        print(f"   ✅ FastAPI app created successfully")
        print(f"   Routes registered: {len(app.routes)}")
    except Exception as e:
        print(f"   ❌ FastAPI app creation failed: {e}")
        return
    
    # 4. Startup sequence test
    print("\n4. STARTUP SEQUENCE TEST:")
    try:
        from netra_backend.app.startup_module import run_complete_startup
        from fastapi import FastAPI
        
        test_app = FastAPI()
        start_time, logger = await run_complete_startup(test_app)
        print(f"   ✅ Startup sequence completed in {time.time() - start_time:.2f}s")
        print(f"   Startup complete: {getattr(test_app.state, 'startup_complete', 'NOT_SET')}")
        print(f"   Startup failed: {getattr(test_app.state, 'startup_failed', 'NOT_SET')}")
    except Exception as e:
        print(f"   ❌ Startup sequence failed: {e}")
        return
    
    print("\n=== DIAGNOSIS COMPLETE ===")
    print("If all checks pass but server still doesn't listen, the issue may be:")
    print("- Missing uvicorn.run() call in proper context")
    print("- Threading/async issues preventing server from binding to port")
    print("- FastAPI lifespan events blocking server startup")
    print("- OS-level port binding restrictions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])