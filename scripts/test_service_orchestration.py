#!/usr/bin/env python3
"""
Test Service Orchestration Script

This script tests the E2E service orchestration system to ensure it can properly
start and health-check services for E2E testing.

Usage:
    python scripts/test_service_orchestration.py
    python scripts/test_service_orchestration.py --cleanup
    python scripts/test_service_orchestration.py --verbose
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.unified_docker_manager import (
    ServiceOrchestrator,
    OrchestrationConfig,
    orchestrate_e2e_services
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_service_orchestration(cleanup: bool = False, verbose: bool = False):
    """Test the E2E service orchestration system."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('test_framework.service_orchestrator').setLevel(logging.DEBUG)
        logging.getLogger('test_framework.docker_port_discovery').setLevel(logging.DEBUG)
    
    logger.info("[U+1F680] Testing E2E Service Orchestration System")
    
    # Configure orchestration for testing
    config = OrchestrationConfig(
        environment="test",
        required_services=["postgres", "redis"],  # Start with basic services
        startup_timeout=60.0,
        health_check_timeout=5.0,
        health_check_retries=10
    )
    
    orchestrator = ServiceOrchestrator(config)
    
    try:
        logger.info("=" * 60)
        logger.info("PHASE 1: Service Orchestration Test")
        logger.info("=" * 60)
        
        # Test service orchestration
        success, health_report = await orchestrator.orchestrate_services()
        
        if success:
            logger.info(" PASS:  Service orchestration PASSED")
            logger.info(orchestrator.get_health_report())
            
            logger.info("=" * 60)
            logger.info("PHASE 2: Service Connectivity Test")
            logger.info("=" * 60)
            
            # Test service connectivity
            connectivity_passed = await test_service_connectivity(orchestrator)
            
            if connectivity_passed:
                logger.info(" PASS:  Service connectivity PASSED")
                logger.info(" CELEBRATION:  All E2E service orchestration tests PASSED")
                return True
            else:
                logger.error(" FAIL:  Service connectivity FAILED")
                return False
        else:
            logger.error(" FAIL:  Service orchestration FAILED")
            logger.error(orchestrator.get_health_report())
            return False
            
    except Exception as e:
        logger.error(f" FAIL:  Service orchestration test failed: {e}")
        return False
    finally:
        if cleanup and orchestrator.started_services:
            logger.info("[U+1F9F9] Cleaning up test services...")
            await orchestrator.cleanup_services()
            logger.info(" PASS:  Cleanup completed")


async def test_service_connectivity(orchestrator: ServiceOrchestrator) -> bool:
    """Test connectivity to orchestrated services."""
    from test_framework.docker_port_discovery import DockerPortDiscovery
    
    port_discovery = DockerPortDiscovery(use_test_services=True)
    port_mappings = port_discovery.discover_all_ports()
    
    connectivity_results = []
    
    for service_name, health in orchestrator.service_health.items():
        if not health.is_healthy:
            logger.warning(f" WARNING: [U+FE0F]  Skipping connectivity test for unhealthy service: {service_name}")
            continue
        
        logger.info(f"[U+1F50C] Testing connectivity to {service_name}:{health.port}")
        
        try:
            if service_name in ["postgres", "redis"]:
                # Test port connectivity for database services
                connected = await test_port_connectivity(health.port, timeout=3.0)
                connectivity_results.append(connected)
                
                if connected:
                    logger.info(f" PASS:  {service_name} port {health.port} is connectable")
                else:
                    logger.error(f" FAIL:  {service_name} port {health.port} is not connectable")
                    
            elif service_name in ["backend", "auth"]:
                # Test HTTP connectivity for web services
                connected = await test_http_connectivity(health.port, timeout=5.0)
                connectivity_results.append(connected)
                
                if connected:
                    logger.info(f" PASS:  {service_name} HTTP port {health.port} is responsive")
                else:
                    logger.error(f" FAIL:  {service_name} HTTP port {health.port} is not responsive")
                    
        except Exception as e:
            logger.error(f" FAIL:  Connectivity test failed for {service_name}: {e}")
            connectivity_results.append(False)
    
    return all(connectivity_results) if connectivity_results else False


async def test_port_connectivity(port: int, host: str = "localhost", timeout: float = 3.0) -> bool:
    """Test if a port is connectable."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), 
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception as e:
        logger.debug(f"Port connectivity failed for {host}:{port}: {e}")
        return False


async def test_http_connectivity(port: int, host: str = "localhost", timeout: float = 5.0) -> bool:
    """Test if an HTTP service is responsive."""
    try:
        # Try to import aiohttp for HTTP testing
        import aiohttp
        
        url = f"http://{host}:{port}/health"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                return response.status in [200, 404]  # 404 is okay if /health doesn't exist
                
    except ImportError:
        # Fallback to port connectivity if aiohttp not available
        logger.debug(f"aiohttp not available, falling back to port test for {host}:{port}")
        return await test_port_connectivity(port, host, timeout)
    except Exception as e:
        logger.debug(f"HTTP connectivity failed for {host}:{port}: {e}")
        # Fallback to port connectivity
        return await test_port_connectivity(port, host, timeout)


async def quick_health_check():
    """Quick health check of the orchestration system."""
    logger.info("[U+1F3E5] Running Quick Health Check")
    
    try:
        success, orchestrator = await orchestrate_e2e_services(
            required_services=["postgres", "redis"],
            timeout=30.0
        )
        
        if success:
            logger.info(" PASS:  Quick health check PASSED")
            logger.info(orchestrator.get_health_report())
            return True
        else:
            logger.error(" FAIL:  Quick health check FAILED")
            logger.error(orchestrator.get_health_report())
            return False
            
    except Exception as e:
        logger.error(f" FAIL:  Quick health check failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test E2E Service Orchestration")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Cleanup services after testing")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick health check only")
    
    args = parser.parse_args()
    
    async def run_tests():
        if args.quick:
            success = await quick_health_check()
        else:
            success = await test_service_orchestration(
                cleanup=args.cleanup,
                verbose=args.verbose
            )
        
        if success:
            logger.info(" CELEBRATION:  Service orchestration test completed successfully")
            return 0
        else:
            logger.error(" FAIL:  Service orchestration test failed")
            return 1
    
    try:
        exit_code = asyncio.run(run_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()