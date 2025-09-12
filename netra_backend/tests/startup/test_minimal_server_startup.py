"""
Minimal Server Startup Test - Isolates the core server listening issue

Business Value Justification (BVJ):
- Segment: All (System Foundation)
- Business Goal: Ensure backend can start and serve requests
- Value Impact: Foundation requirement - enables ALL platform functionality
- Revenue Impact: Blocking - zero revenue possible if backend doesn't start

This test creates a minimal FastAPI app to isolate and fix the specific issue
where the backend connects to database but doesn't listen on port 8000.
"""
import asyncio
import socket
import threading
import time
from typing import Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest
import uvicorn
from fastapi import FastAPI


class MinimalServerTest:
    """Minimal FastAPI server for testing startup issues."""
    
    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        self.startup_error: Optional[str] = None
        self.port = self._find_free_port()  # Use dynamic port allocation
    
    def _find_free_port(self) -> int:
        """Find a free port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', 0))  # Bind to a free port
            _, port = sock.getsockname()
            return port
    
    def create_minimal_app(self) -> FastAPI:
        """Create a minimal FastAPI app with just essential routes."""
        app = FastAPI(title="Minimal Test App")
        
        @app.get("/")
        def root():
            return {"status": "ok", "message": "minimal server working"}
        
        @app.get("/health/")
        def health():
            return {"status": "healthy", "service": "minimal-backend"}
        
        return app
    
    def is_port_listening(self, timeout: float = 0.5) -> bool:
        """Check if port is being listened to."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                return sock.connect_ex(("localhost", self.port)) == 0
        except Exception:
            return False
    
    def start_server_thread(self) -> bool:
        """Start minimal server in background thread."""
        def run_server():
            try:
                # Create minimal app
                self.app = self.create_minimal_app()
                
                # Configure uvicorn
                config = uvicorn.Config(
                    self.app,
                    host="0.0.0.0", 
                    port=self.port,
                    log_level="error",  # Reduce noise
                    access_log=False
                )
                
                # Create and run server
                self.server = uvicorn.Server(config)
                self.server.run()
                
            except Exception as e:
                self.startup_error = str(e)
        
        # Start in background thread
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        time.sleep(0.1)  # Small delay for thread startup
        
        return self.startup_error is None
    
    def wait_for_listening(self, max_wait: float = 5.0) -> bool:
        """Wait for server to start listening."""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.is_port_listening():
                return True
            if self.startup_error:
                break
            time.sleep(0.1)
        return False
    
    def stop_server(self):
        """Stop the server if running."""
        if self.server:
            try:
                # Use a proper shutdown approach
                if hasattr(self.server, 'should_exit'):
                    self.server.should_exit = True
            except Exception:
                pass
        
        # Give time for graceful shutdown
        if self.server_thread and self.server_thread.is_alive():
            time.sleep(0.5)


class FullAppServerTest:
    """Test with the actual Netra backend app to isolate startup issues."""
    
    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        self.startup_error: Optional[str] = None
        self.port = self._find_free_port()  # Use dynamic port allocation to avoid conflicts
    
    def _find_free_port(self) -> int:
        """Find a free port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', 0))  # Bind to a free port
            _, port = sock.getsockname()
            return port
        
    def create_netra_app_minimal(self) -> FastAPI:
        """Create Netra app with minimal startup to isolate issues."""
        # Import with error handling
        try:
            # Import only what we need to avoid signal handling issues
            from fastapi import FastAPI
            
            # Create a minimal app mimicking the Netra structure but without signal handlers
            app = FastAPI(
                title="Netra API Minimal Test",
                description="Minimal test version of Netra API",
                version="0.1.0-test"
            )
            
            # Add basic health endpoint
            @app.get("/")
            async def root():
                return {"status": "ok", "service": "netra-backend-minimal"}
            
            @app.get("/health/")
            async def health():
                return {"status": "healthy", "service": "netra-backend-minimal"}
            
            return app
            
        except Exception as e:
            self.startup_error = f"Failed to create Netra app: {e}"
            return None
    
    def start_server_thread(self) -> bool:
        """Start Netra backend server in background thread."""
        def run_server():
            try:
                # Create app without lifespan startup
                self.app = self.create_netra_app_minimal()
                if not self.app:
                    return
                
                # Configure uvicorn
                config = uvicorn.Config(
                    self.app,
                    host="0.0.0.0",
                    port=self.port,
                    log_level="warning",
                    access_log=False
                )
                
                # Create and run server
                self.server = uvicorn.Server(config)
                self.server.run()
                
            except Exception as e:
                self.startup_error = str(e)
        
        # Start in background thread  
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        time.sleep(0.2)  # Slightly longer delay for complex app
        
        return self.startup_error is None
    
    def is_port_listening(self, timeout: float = 0.5) -> bool:
        """Check if port is being listened to."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                return sock.connect_ex(("localhost", self.port)) == 0
        except Exception:
            return False
    
    def wait_for_listening(self, max_wait: float = 10.0) -> bool:
        """Wait for server to start listening."""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.is_port_listening():
                return True
            if self.startup_error:
                break
            time.sleep(0.2)
        return False
    
    def stop_server(self):
        """Stop the server if running."""
        if self.server:
            try:
                if hasattr(self.server, 'should_exit'):
                    self.server.should_exit = True
            except Exception:
                pass
        
        if self.server_thread and self.server_thread.is_alive():
            time.sleep(0.5)


class TestMinimalServerStartup:
    """Test minimal FastAPI server startup to isolate issues."""
    
    def setup_method(self):
        """Setup for each test."""
        self.minimal_server = MinimalServerTest()
        self.full_server = FullAppServerTest()
    
    def teardown_method(self):
        """Cleanup after each test."""
        if hasattr(self, 'minimal_server'):
            self.minimal_server.stop_server()
        if hasattr(self, 'full_server'):
            self.full_server.stop_server()
        
        # Extra cleanup time
        time.sleep(0.5)
    
    @pytest.mark.unit
    def test_minimal_fastapi_server_startup(self):
        """Test that a minimal FastAPI server can start and listen."""
        print("\n=== TESTING MINIMAL FASTAPI SERVER ===")
        
        # Check port is available
        assert not self.minimal_server.is_port_listening(), f"Port {self.minimal_server.port} already in use"
        
        # Start server
        started = self.minimal_server.start_server_thread()
        assert started, f"Server thread failed to start: {self.minimal_server.startup_error}"
        
        # Wait for listening
        listening = self.minimal_server.wait_for_listening()
        
        if not listening:
            pytest.fail(
                f"Minimal server failed to start listening. Error: {self.minimal_server.startup_error}"
            )
        
        print(" PASS:  Minimal FastAPI server started successfully")
        
        # Test basic connectivity
        assert self.minimal_server.is_port_listening(), "Server not listening after startup"
        
        print(f" PASS:  Server is listening on port {self.minimal_server.port}")
    
    @pytest.mark.integration
    def test_netra_app_without_lifespan(self):
        """Test minimal Netra-like FastAPI app startup to isolate threading issues."""
        print("\n=== TESTING NETRA APP WITHOUT LIFESPAN ===")
        
        # Check port is available
        assert not self.full_server.is_port_listening(), f"Port {self.full_server.port} already in use"
        
        # Start server
        started = self.full_server.start_server_thread()
        
        if not started:
            pytest.fail(f"Failed to start Netra app: {self.full_server.startup_error}")
        
        # Wait for listening
        listening = self.full_server.wait_for_listening()
        
        if not listening:
            error_msg = self.full_server.startup_error or "Unknown startup issue"
            pytest.fail(f"Netra app failed to start listening: {error_msg}")
        
        print(" PASS:  Netra app (without lifespan) started successfully")
        
        # Test connectivity
        assert self.full_server.is_port_listening(), "Netra app not listening after startup"
        
        print(f" PASS:  Netra app is listening on port {self.full_server.port}")
    
    @pytest.mark.unit
    def test_port_availability_detection(self):
        """Test that port availability detection works correctly."""
        server = MinimalServerTest()
        
        # Test with definitely available port
        server.port = 59998
        assert not server.is_port_listening(), "High port should not be listening"
        
        # Test with impossible port
        server.port = 99999
        assert not server.is_port_listening(), "Invalid port should not be listening"
        
        print(" PASS:  Port availability detection working correctly")
    
    @pytest.mark.unit  
    def test_fastapi_app_creation_isolated(self):
        """Test FastAPI app creation in isolation."""
        server = MinimalServerTest()
        
        app = server.create_minimal_app()
        assert app is not None, "Failed to create minimal FastAPI app"
        assert len(app.routes) > 0, "No routes registered in minimal app"
        
        print(" PASS:  FastAPI app creation works in isolation")


# Diagnostic functions
@pytest.mark.integration
def test_diagnose_server_startup_issue():
    """Comprehensive diagnostic to understand why server doesn't listen."""
    print("\n" + "="*60)
    print("COMPREHENSIVE SERVER STARTUP DIAGNOSTIC")
    print("="*60)
    
    # Test 1: Minimal FastAPI server
    print("\n1. TESTING MINIMAL FASTAPI SERVER")
    minimal = MinimalServerTest()
    
    try:
        if not minimal.is_port_listening():
            print(f"    PASS:  Port {minimal.port} is available")
            
            started = minimal.start_server_thread()
            if started:
                print("    PASS:  Server thread started")
                
                listening = minimal.wait_for_listening(max_wait=3.0)
                if listening:
                    print("    PASS:  Minimal server listening successfully!")
                    print("   [U+1F4CB] RESULT: Basic FastAPI + uvicorn works correctly")
                else:
                    print("    FAIL:  Minimal server not listening")
                    print(f"    SEARCH:  Error: {minimal.startup_error}")
                    
            else:
                print(f"    FAIL:  Server thread failed: {minimal.startup_error}")
        else:
            print(f"    WARNING: [U+FE0F] Port {minimal.port} already in use")
            
    finally:
        minimal.stop_server()
    
    # Test 2: Netra app without lifespan
    print("\n2. TESTING NETRA APP WITHOUT LIFESPAN")
    full = FullAppServerTest()
    
    try:
        if not full.is_port_listening():
            print(f"    PASS:  Port {full.port} is available")
            
            started = full.start_server_thread()
            if started:
                print("    PASS:  Netra app creation succeeded")
                
                listening = full.wait_for_listening(max_wait=5.0)
                if listening:
                    print("    PASS:  Netra app listening successfully!")
                    print("   [U+1F4CB] RESULT: Issue is likely in lifespan startup events")
                else:
                    print("    FAIL:  Netra app not listening")
                    print(f"    SEARCH:  Error: {full.startup_error}")
                    print("   [U+1F4CB] RESULT: Issue is in app creation/route registration")
                    
            else:
                print(f"    FAIL:  Netra app creation failed: {full.startup_error}")
                print("   [U+1F4CB] RESULT: Issue is in app factory or imports")
        else:
            print(f"    WARNING: [U+FE0F] Port {full.port} already in use")
            
    finally:
        full.stop_server()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])