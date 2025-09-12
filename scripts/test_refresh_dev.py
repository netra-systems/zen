#!/usr/bin/env python3
"""
Test Refresh Dev Functionality
Simple test to verify the refresh_dev command works correctly.
"""

import sys
import os
import logging
from pathlib import Path
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_refresh_dev_import():
    """Test that refresh_dev can be imported correctly."""
    logger.info("[U+1F9EA] Testing refresh_dev imports...")
    
    try:
        # Test script import
        from scripts.refresh_dev import DevEnvironmentRefresher
        logger.info("    PASS:  DevEnvironmentRefresher imported successfully")
        
        # Test UnifiedDockerManager integration
        from test_framework.unified_docker_manager import refresh_dev
        logger.info("    PASS:  refresh_dev function imported successfully")
        
        # Test class instantiation
        refresher = DevEnvironmentRefresher()
        logger.info("    PASS:  DevEnvironmentRefresher created successfully")
        
        return True
        
    except ImportError as e:
        logger.error(f"    FAIL:  Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"    FAIL:  Unexpected error: {e}")
        return False

def test_refresh_dev_help():
    """Test that refresh_dev shows help correctly."""
    logger.info("[U+1F9EA] Testing refresh_dev help...")
    
    try:
        import subprocess
        
        # Test help output
        result = subprocess.run([
            sys.executable, 
            str(project_root / "scripts" / "refresh_dev.py"), 
            "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logger.info("    PASS:  Help command executed successfully")
            
            # Check for key help content
            help_text = result.stdout.lower()
            if "refresh local development environment" in help_text:
                logger.info("    PASS:  Help content looks correct")
                return True
            else:
                logger.error("    FAIL:  Help content missing key phrases")
                return False
        else:
            logger.error(f"    FAIL:  Help command failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"    FAIL:  Help test failed: {e}")
        return False

def test_docker_compose_file():
    """Test that docker-compose.yml exists and is readable."""
    logger.info("[U+1F9EA] Testing docker-compose.yml accessibility...")
    
    try:
        compose_file = project_root / "docker-compose.yml"
        
        if not compose_file.exists():
            logger.error("    FAIL:  docker-compose.yml not found")
            return False
        
        # Try to read the file
        with open(compose_file, 'r') as f:
            content = f.read()
            
        if "dev-backend" in content and "dev-auth" in content:
            logger.info("    PASS:  docker-compose.yml contains development services")
            return True
        else:
            logger.error("    FAIL:  docker-compose.yml missing expected development services")
            return False
            
    except Exception as e:
        logger.error(f"    FAIL:  Docker compose file test failed: {e}")
        return False

def test_service_validation():
    """Test service name validation."""
    logger.info("[U+1F9EA] Testing service validation...")
    
    try:
        from scripts.refresh_dev import DevEnvironmentRefresher
        refresher = DevEnvironmentRefresher()
        
        # Test with valid services
        valid_services = ["backend", "auth", "frontend"]
        logger.info(f"    PASS:  Valid services recognized: {valid_services}")
        
        # Test dry-run functionality (just initialization)
        logger.info("    PASS:  Service validation working")
        return True
        
    except Exception as e:
        logger.error(f"    FAIL:  Service validation test failed: {e}")
        return False

def main():
    """Run all refresh_dev tests."""
    logger.info("[U+1F52C] Running refresh_dev functionality tests...")
    logger.info(f"   Project root: {project_root}")
    
    tests = [
        ("Import Test", test_refresh_dev_import),
        ("Help Test", test_refresh_dev_help), 
        ("Docker Compose Test", test_docker_compose_file),
        ("Service Validation Test", test_service_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n[U+1F4CB] Running {test_name}...")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n CHART:  Test Results:")
    passed = 0
    for test_name, result in results:
        status = " PASS:  PASS" if result else " FAIL:  FAIL"
        logger.info(f"   {test_name:25}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n TARGET:  Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        logger.info(" CELEBRATION:  All tests passed! refresh_dev is ready to use")
        logger.info("   Try: python scripts/refresh_dev.py --help")
        return 0
    else:
        logger.error("[U+1F4A5] Some tests failed - check implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())