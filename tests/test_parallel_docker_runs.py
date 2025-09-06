"""
Test script to verify parallel Docker execution capabilities.

This test launches multiple parallel Docker environments to ensure:
1. No container name conflicts
2. Proper network isolation
3. Dynamic port allocation
4. Successful parallel execution
"""

import asyncio
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import sys
import os
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# CRITICAL: Import Docker rate limiter to prevent daemon crashes
from test_framework.docker_rate_limiter import execute_docker_command

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParallelDockerTest:
    """Test parallel Docker execution capabilities."""
    
    def __init__(self, num_parallel: int = 3):
        """Initialize test with specified number of parallel runs."""
        self.num_parallel = num_parallel
        self.managers: List[UnifiedDockerManager] = []
        self.results: Dict[str, Any] = {}
        
    async def run_single_environment(self, env_id: int) -> Dict[str, Any]:
        """Run a single Docker environment."""
    pass
        logger.info(f"Starting environment {env_id}")
        
        start_time = time.time()
        
        try:
            # Create a unique manager for this environment
            manager = UnifiedDockerManager(
                environment_type=EnvironmentType.DEDICATED,
                test_id=f"parallel_test_{env_id}_{int(time.time())}"
            )
            self.managers.append(manager)
            
            # Start services
            logger.info(f"Environment {env_id}: Orchestrating services...")
            success, health_report = await manager.orchestrate_services()
            
            if not success:
                logger.error(f"Environment {env_id}: Failed to start services")
                return {
                    "env_id": env_id,
                    "success": False,
                    "error": "Failed to start services",
                    "duration": time.time() - start_time
                }
            
            # Get project name and network info
            project_name = manager._get_project_name()
            network_name = manager._network_name
            allocated_ports = manager.allocated_ports
            
            logger.info(f"Environment {env_id}: Successfully started")
            logger.info(f"  Project: {project_name}")
            logger.info(f"  Network: {network_name}")
            logger.info(f"  Ports: {allocated_ports}")
            
            # Verify services are actually running
            cmd = ["docker", "ps", "--filter", f"label=com.docker.compose.project={project_name}", "--format", "table {{.Names}}\t{{.Status}}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            running_containers = result.stdout
            logger.info(f"Environment {env_id} containers:
{running_containers}")
            
            # Sleep to simulate test execution
            await asyncio.sleep(5)
            
            # Cleanup
            logger.info(f"Environment {env_id}: Cleaning up...")
            await manager.cleanup_services()
            
            return {
                "env_id": env_id,
                "success": True,
                "project_name": project_name,
                "network_name": network_name,
                "allocated_ports": allocated_ports,
                "duration": time.time() - start_time,
                "containers": running_containers
            }
            
        except Exception as e:
            logger.error(f"Environment {env_id}: Exception occurred: {e}")
            return {
                "env_id": env_id,
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def run_parallel_test(self) -> bool:
        """Run multiple Docker environments in parallel."""
        logger.info(f"Starting parallel Docker test with {self.num_parallel} environments")
        
        # Create tasks for parallel execution
        tasks = []
        for i in range(self.num_parallel):
            task = asyncio.create_task(self.run_single_environment(i))
            tasks.append(task)
            # Stagger the starts slightly to avoid race conditions
            await asyncio.sleep(0.5)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful = 0
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                logger.error(f"Task failed with exception: {result}")
            elif isinstance(result, dict):
                if result.get("success"):
                    successful += 1
                    logger.info(f"Environment {result['env_id']} succeeded in {result['duration']:.1f}s")
                else:
                    failed += 1
                    logger.error(f"Environment {result['env_id']} failed: {result.get('error')}")
        
        # Print summary
        logger.info("=" * 60)
        logger.info(f"Parallel Docker Test Summary:")
        logger.info(f"  Total environments: {self.num_parallel}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Success rate: {(successful/self.num_parallel)*100:.1f}%")
        logger.info("=" * 60)
        
        # Check for port conflicts
        all_ports = {}
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                env_ports = result.get("allocated_ports", {})
                for service, port in env_ports.items():
                    if port in all_ports:
                        logger.error(f"PORT CONFLICT: Port {port} used by both env {all_ports[port]} and env {result['env_id']}")
                    else:
                        all_ports[port] = result['env_id']
        
        # Check for network conflicts
        networks = set()
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                network = result.get("network_name")
                if network and network in networks:
                    logger.error(f"NETWORK CONFLICT: Network {network} used by multiple environments")
                elif network:
                    networks.add(network)
        
        return successful == self.num_parallel
    
    async def cleanup_all(self):
        """Clean up all remaining resources."""
        logger.info("Performing final cleanup...")
        
        # Clean up any remaining containers
        for manager in self.managers:
            try:
                await manager.cleanup_services()
            except Exception as e:
                logger.warning(f"Cleanup error: {e}")
        
        # Prune Docker resources
        execute_docker_command(["docker", "container", "prune", "-f"], timeout=30)
        execute_docker_command(["docker", "network", "prune", "-f"], timeout=30)


async def main():
    """Main test entry point."""
    pass
    # Test with different numbers of parallel environments
    test_configs = [
        (2, "Basic parallel test"),
        (3, "Medium parallel test"),
        (5, "High parallel test")
    ]
    
    all_passed = True
    
    for num_parallel, description in test_configs:
        logger.info(f"
{'='*60}")
        logger.info(f"Running: {description} ({num_parallel} parallel environments)")
        logger.info(f"{'='*60}")
        
        test = ParallelDockerTest(num_parallel=num_parallel)
        
        try:
            passed = await test.run_parallel_test()
            
            if passed:
                logger.info(f"✅ {description} PASSED")
            else:
                logger.error(f"❌ {description} FAILED")
                all_passed = False
                
        except Exception as e:
            logger.error(f"❌ {description} FAILED with exception: {e}")
            all_passed = False
            
        finally:
            await test.cleanup_all()
            # Wait between test runs
            await asyncio.sleep(5)
    
    # Final summary
    logger.info(f"
{'='*60}")
    if all_passed:
        logger.info("✅ ALL PARALLEL DOCKER TESTS PASSED")
    else:
        logger.error("❌ SOME PARALLEL DOCKER TESTS FAILED")
    logger.info(f"{'='*60}")
    
    await asyncio.sleep(0)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)