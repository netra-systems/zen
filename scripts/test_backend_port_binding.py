from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Test script to specifically check backend port 8000 binding.
This isolates the socket permission error from other dev launcher issues.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

env = get_env()
def test_basic_socket_binding():
    """Test basic socket binding to port 8000."""
    import socket
    
    logger.info("[U+1F9EA] Testing basic socket binding to port 8000...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', 8000))
            sock.listen(1)
            
            actual_port = sock.getsockname()[1]
            logger.info(f" PASS:  Successfully bound to port {actual_port}")
            return True
            
    except OSError as e:
        logger.error(f" FAIL:  Socket binding failed: {e}")
        if e.errno == 10013:
            logger.error("   This is the [WinError 10013] permission error!")
        elif e.errno == 10048:
            logger.error("   Port is already in use by another process")
        return False

def test_uvicorn_binding():
    """Test uvicorn binding directly without the full app."""
    logger.info("[U+1F9EA] Testing uvicorn binding to port 8000...")
    
    try:
        import uvicorn
        from fastapi import FastAPI
        
        # Create minimal test app
        app = FastAPI()
        
        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}
        
        # Test uvicorn config
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        # Try to start server (this will test the socket binding)
        logger.info("   Starting test uvicorn server...")
        
        import asyncio
        import threading
        import time
        
        def run_server():
            asyncio.run(server.serve())
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Give server time to start
        time.sleep(3)
        
        # Test if server is responding
        import requests
        try:
            response = requests.get("http://127.0.0.1:8000/test", timeout=5)
            if response.status_code == 200:
                logger.info(" PASS:  Uvicorn server started successfully and is responding")
                
                # Shutdown server
                server.should_exit = True
                server_thread.join(timeout=5)
                
                return True
            else:
                logger.error(f" FAIL:  Server responded with status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(" FAIL:  Could not connect to test server")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f" FAIL:  Request failed: {e}")
            return False
            
    except ImportError as e:
        logger.error(f" FAIL:  Missing required package: {e}")
        return False
    except Exception as e:
        logger.error(f" FAIL:  Uvicorn test failed: {e}")
        return False

def test_backend_main_directly():
    """Test importing and running the backend main module."""
    logger.info("[U+1F9EA] Testing backend main module import...")
    
    try:
        # Set environment variables needed for testing
        env.set('LLM_MODE', 'disabled', "test")  # Disable LLM for testing
        env.set('DATABASE_URL', 'sqlite:///test.db', "test")  # Use SQLite for testing
        env.set('ENVIRONMENT', 'test', "test")
        
        # Try importing the main module
        from netra_backend.app.main import app, _get_uvicorn_config
        
        logger.info(" PASS:  Successfully imported backend main module")
        
        # Get uvicorn config
        config = _get_uvicorn_config()
        logger.info(f"   Backend configured to run on: {config['host']}:{config['port']}")
        
        if config['port'] == 8000:
            logger.info(" PASS:  Backend is configured to use port 8000")
            return True
        else:
            logger.warning(f" WARNING: [U+FE0F]  Backend is configured to use port {config['port']} instead of 8000")
            return False
            
    except ImportError as e:
        logger.error(f" FAIL:  Failed to import backend main: {e}")
        return False
    except Exception as e:
        logger.error(f" FAIL:  Backend main test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests to identify the exact source of the port binding issue."""
    logger.info("[U+1F680] Starting comprehensive port 8000 binding test")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Socket Binding", test_basic_socket_binding),
        ("Backend Main Import", test_backend_main_directly),
        ("Uvicorn Binding", test_uvicorn_binding),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n[U+1F4CB] Running test: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            logger.info(f"   Result: {' PASS:  PASS' if result else ' FAIL:  FAIL'}")
        except Exception as e:
            logger.error(f"   [U+1F4A5] Exception: {e}")
            results.append((test_name, False))
    
    logger.info("\n" + "=" * 60)
    logger.info(" CHART:  TEST SUMMARY:")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = " PASS:  PASS" if result else " FAIL:  FAIL"
        logger.info(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("=" * 60)
    if all_passed:
        logger.info(" CELEBRATION:  ALL TESTS PASSED - Port 8000 should work for the backend!")
        logger.info("   The socket permission error may be resolved or intermittent.")
        logger.info("   Try running the dev launcher again.")
    else:
        logger.error("[U+1F4A5] SOME TESTS FAILED - Port 8000 binding has issues")
        logger.error("   This confirms there's a Windows socket permission problem.")
        logger.error("   Try running as Administrator or use the port cleanup script.")
    
    return all_passed

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)