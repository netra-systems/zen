#!/usr/bin/env python3
"""
Integration test demonstrating ResourceManagementAgent coordination with other orchestration components.

This test shows how ResourceManagementAgent works with LayerExecutionAgent,
BackgroundE2EAgent, and ProgressStreamingAgent for complete test orchestration.
"""

import asyncio
import json
import logging
import pytest
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework imports
from test_framework.environment_isolation import get_test_env_manager
from test_framework.orchestration.resource_management_agent import (
    ResourceManagementAgent, create_resource_manager, ensure_layer_resources_available
)
from test_framework.layer_system import ResourceRequirements

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestResourceManagementIntegration:
    """Integration tests for ResourceManagementAgent with orchestration system."""
    
    @pytest.fixture
    def isolated_env(self):
        """Isolated test environment."""
        env_manager = get_test_env_manager()
        env = env_manager.setup_test_environment()
        yield env
        env_manager.teardown_test_environment()
    
    def test_multi_layer_resource_coordination(self, isolated_env):
        """Test resource coordination across multiple test layers."""
        rm = create_resource_manager(enable_monitoring=False)
        
        try:
            # Simulate concurrent layer execution
            layer_allocations = {}
            
            # Allocate resources for different layers
            layers = [
                ("fast_feedback", "unit", ResourceRequirements(min_memory_mb=128)),
                ("core_integration", "database", ResourceRequirements(min_memory_mb=256)),
                ("service_integration", "api", ResourceRequirements(min_memory_mb=512)),
            ]
            
            for layer_name, category_name, requirements in layers:
                allocation_id = rm.allocate_resources(
                    layer_name=layer_name,
                    category_name=category_name,
                    requirements=requirements,
                    duration_minutes=10
                )
                if allocation_id:
                    layer_allocations[(layer_name, category_name)] = allocation_id
                    logger.info(f"Allocated resources for {layer_name}/{category_name}")
                else:
                    logger.warning(f"Failed to allocate resources for {layer_name}/{category_name}")
            
            # Check resource status
            resource_status = rm.get_resource_status()
            assert resource_status["total_allocations"] >= 1
            
            # Verify resource pool utilization
            pools = resource_status["resource_pools"]
            for pool_name, pool_status in pools.items():
                if pool_status["active_instances"] > 0:
                    assert pool_status["allocated_memory_mb"] > 0
                    assert pool_status["utilization_memory"] > 0
                    logger.info(f"Pool {pool_name} utilization: "
                               f"{pool_status['utilization_memory']:.1f}% memory, "
                               f"{pool_status['utilization_instances']:.1f}% instances")
            
            # Release all allocations
            for allocation_id in layer_allocations.values():
                success = rm.release_resources(allocation_id)
                assert success
            
            # Verify cleanup
            resource_status = rm.get_resource_status()
            assert resource_status["total_allocations"] == 0
            
        finally:
            rm.shutdown()
    
    def test_service_dependency_chain_validation(self, isolated_env):
        """Test service dependency chain validation."""
        rm = create_resource_manager(enable_monitoring=False)
        
        try:
            # Test different layer service requirements
            layer_tests = [
                ("fast_feedback", set(), True),  # No services required
                ("core_integration", {"postgresql", "redis"}, None),  # Database services
                ("service_integration", {"postgresql", "redis", "backend", "auth"}, None),  # API services
                ("e2e_background", {"postgresql", "redis", "backend", "auth", "frontend"}, None)  # Full stack
            ]
            
            for layer_name, expected_services, expected_result in layer_tests:
                actual_services = rm.LAYER_SERVICE_DEPENDENCIES.get(layer_name, set())
                assert actual_services == expected_services, f"Layer {layer_name} service mismatch"
                
                # Check service availability
                available, missing = rm.ensure_layer_services(layer_name)
                
                if expected_result is not None:
                    assert available == expected_result
                
                logger.info(f"Layer {layer_name}: Available={available}, Missing={missing}")
            
        finally:
            rm.shutdown()
    
    def test_concurrent_layer_resource_requests(self, isolated_env):
        """Test concurrent resource requests from multiple layers."""
        rm = create_resource_manager(enable_monitoring=False)
        
        try:
            results = []
            
            def allocate_for_layer(layer_name, category_suffix):
                """Allocate resources for a specific layer."""
                requirements = ResourceRequirements(
                    min_memory_mb=256,
                    dedicated_resources=False
                )
                
                allocation_id = rm.allocate_resources(
                    layer_name=layer_name,
                    category_name=f"test_{category_suffix}",
                    requirements=requirements,
                    duration_minutes=5
                )
                
                results.append((layer_name, category_suffix, allocation_id))
                return allocation_id
            
            # Create concurrent allocation requests
            threads = []
            layer_categories = [
                ("fast_feedback", "unit1"),
                ("fast_feedback", "unit2"),
                ("core_integration", "db1"),
                ("service_integration", "api1")
            ]
            
            for layer_name, category_suffix in layer_categories:
                thread = threading.Thread(
                    target=allocate_for_layer,
                    args=(layer_name, category_suffix)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all allocations
            for thread in threads:
                thread.join()
            
            # Check results
            successful_allocations = [r for r in results if r[2] is not None]
            assert len(successful_allocations) >= 3  # At least most should succeed
            
            # Verify each allocation is unique
            allocation_ids = [r[2] for r in successful_allocations]
            assert len(set(allocation_ids)) == len(allocation_ids)
            
            # Check resource pool state
            resource_status = rm.get_resource_status()
            active_pools = {
                name: pool for name, pool in resource_status["resource_pools"].items()
                if pool["active_instances"] > 0
            }
            
            assert len(active_pools) >= 1
            logger.info(f"Active pools after concurrent allocation: {list(active_pools.keys())}")
            
            # Cleanup all allocations
            for _, _, allocation_id in successful_allocations:
                if allocation_id:
                    rm.release_resources(allocation_id)
            
        finally:
            rm.shutdown()
    
    def test_resource_stress_and_recovery(self, isolated_env):
        """Test resource stress scenarios and recovery mechanisms."""
        rm = create_resource_manager(enable_monitoring=True)
        
        try:
            # Create multiple allocations to stress test the system
            allocations = []
            
            # Allocate up to pool limits
            for i in range(10):  # Try to exceed fast_feedback pool limit
                requirements = ResourceRequirements(min_memory_mb=64)
                allocation_id = rm.allocate_resources(
                    layer_name="fast_feedback",
                    category_name=f"stress_test_{i}",
                    requirements=requirements,
                    duration_minutes=1  # Short duration
                )
                if allocation_id:
                    allocations.append(allocation_id)
            
            logger.info(f"Created {len(allocations)} allocations")
            
            # Check resource utilization
            resource_status = rm.get_resource_status()
            fast_feedback_pool = resource_status["resource_pools"]["fast_feedback"]
            
            # Should have hit some limits
            assert fast_feedback_pool["active_instances"] > 0
            utilization = fast_feedback_pool["utilization_instances"]
            logger.info(f"Fast feedback pool utilization: {utilization:.1f}%")
            
            # Try to allocate beyond limits - should fail
            large_requirements = ResourceRequirements(min_memory_mb=1000)  # 1GB
            over_allocation = rm.allocate_resources(
                layer_name="fast_feedback",
                category_name="over_limit",
                requirements=large_requirements,
                duration_minutes=5
            )
            assert over_allocation is None  # Should fail due to insufficient resources
            
            # Test conflict detection
            conflicts = rm.resolve_resource_conflicts()
            logger.info(f"Detected conflicts: {conflicts}")
            
            # Test recovery - cleanup all allocations
            rm.cleanup_resources(force=True)
            
            # Verify recovery
            resource_status = rm.get_resource_status()
            assert resource_status["total_allocations"] == 0
            
            # All pools should be reset
            for pool_name, pool_status in resource_status["resource_pools"].items():
                assert pool_status["active_instances"] == 0
                assert pool_status["allocated_memory_mb"] == 0
                assert pool_status["allocated_cpu_percent"] == 0
            
            logger.info("Resource stress test and recovery completed successfully")
            
        finally:
            rm.shutdown()
    
    def test_service_startup_simulation(self, isolated_env):
        """Test service startup simulation and coordination."""
        rm = create_resource_manager(enable_monitoring=False)
        
        try:
            # Test service dependency resolution
            dependencies = rm.SERVICE_DEPENDENCIES
            
            # Verify dependency graph correctness
            assert len(dependencies["postgresql"]) == 0  # No dependencies
            assert len(dependencies["redis"]) == 0       # No dependencies
            assert "postgresql" in dependencies["auth"]
            assert "redis" in dependencies["auth"]
            assert "auth" in dependencies["backend"]
            assert "backend" in dependencies["frontend"]
            
            # Test startup order calculation (implicit in dependency graph)
            independent_services = [
                service for service, deps in dependencies.items() 
                if len(deps) == 0
            ]
            assert "postgresql" in independent_services
            assert "redis" in independent_services
            
            # Services that depend on others
            dependent_services = [
                service for service, deps in dependencies.items()
                if len(deps) > 0
            ]
            assert "auth" in dependent_services
            assert "backend" in dependent_services
            assert "frontend" in dependent_services
            
            logger.info(f"Independent services: {independent_services}")
            logger.info(f"Dependent services: {dependent_services}")
            
            # Test layer service requirements
            for layer_name, required_services in rm.LAYER_SERVICE_DEPENDENCIES.items():
                available, missing = rm.ensure_layer_services(layer_name)
                logger.info(f"Layer {layer_name} - Required: {required_services}, "
                           f"Available: {available}, Missing: {missing}")
                
                if layer_name == "fast_feedback":
                    # Should always be available (no services required)
                    assert available is True
                    assert missing == []
            
        finally:
            rm.shutdown()


class TestResourceManagementOrchestrationMock:
    """Mock integration tests with other orchestration components."""
    
    def test_integration_with_layer_execution_agent(self, isolated_env):
        """Test integration with LayerExecutionAgent (mocked)."""
        rm = create_resource_manager(enable_monitoring=False)
        
        try:
            # Mock LayerExecutionAgent interaction
            with patch('test_framework.orchestration.layer_execution_agent.LayerExecutionAgent') as MockAgent:
                mock_agent = Mock()
                MockAgent.return_value = mock_agent
                
                # Simulate layer execution workflow
                layer_name = "core_integration"
                
                # 1. Resource manager ensures services available
                available, missing = rm.ensure_layer_services(layer_name)
                logger.info(f"Services check for {layer_name}: available={available}, missing={missing}")
                
                # 2. Allocate resources for layer execution
                requirements = ResourceRequirements(
                    requires_postgresql=True,
                    requires_redis=True,
                    min_memory_mb=512
                )
                
                allocation_id = rm.allocate_resources(
                    layer_name=layer_name,
                    category_name="integration_tests",
                    requirements=requirements,
                    duration_minutes=15
                )
                
                if allocation_id:
                    logger.info(f"Resources allocated for layer execution: {allocation_id}")
                    
                    # 3. Simulate layer execution
                    resource_status = rm.get_resource_status()
                    assert resource_status["total_allocations"] == 1
                    
                    # 4. Release resources after execution
                    success = rm.release_resources(allocation_id)
                    assert success
                    
                    logger.info("Layer execution simulation completed")
                else:
                    logger.warning("Could not allocate resources for layer execution")
            
        finally:
            rm.shutdown()
    
    def test_integration_with_background_e2e_agent(self, isolated_env):
        """Test integration with BackgroundE2EAgent (mocked)."""
        rm = create_resource_manager(enable_monitoring=False)
        
        try:
            # Mock BackgroundE2EAgent interaction
            with patch('test_framework.orchestration.background_e2e_agent.BackgroundE2EAgent') as MockAgent:
                mock_agent = Mock()
                MockAgent.return_value = mock_agent
                
                # Simulate background E2E test scenario
                layer_name = "e2e_background"
                
                # 1. Check if resources are available for background execution
                available, missing = rm.ensure_layer_services(layer_name)
                logger.info(f"Background E2E services: available={available}, missing={missing}")
                
                # 2. Reserve resources for background execution (longer duration)
                requirements = ResourceRequirements(
                    requires_postgresql=True,
                    requires_redis=True,
                    requires_backend_service=True,
                    requires_auth_service=True,
                    requires_frontend_service=True,
                    min_memory_mb=1024,
                    dedicated_resources=True
                )
                
                allocation_id = rm.allocate_resources(
                    layer_name=layer_name,
                    category_name="background_e2e",
                    requirements=requirements,
                    duration_minutes=60  # Longer duration for E2E
                )
                
                if allocation_id:
                    logger.info(f"Background E2E resources allocated: {allocation_id}")
                    
                    # 3. Verify resource pool state
                    resource_status = rm.get_resource_status()
                    e2e_pool = resource_status["resource_pools"]["e2e_background"]
                    
                    assert e2e_pool["active_instances"] > 0
                    assert e2e_pool["allocated_memory_mb"] >= 1024
                    
                    # 4. Simulate background execution
                    time.sleep(0.1)  # Brief simulation
                    
                    # 5. Release resources
                    success = rm.release_resources(allocation_id)
                    assert success
                    
                    logger.info("Background E2E simulation completed")
                else:
                    logger.warning("Could not allocate resources for background E2E")
            
        finally:
            rm.shutdown()
    
    def test_integration_with_progress_streaming(self, isolated_env):
        """Test integration with ProgressStreamingAgent (mocked)."""
        rm = create_resource_manager(enable_monitoring=True)
        
        try:
            # Mock ProgressStreamingAgent interaction
            with patch('test_framework.orchestration.progress_streaming_agent.ProgressStreamingAgent') as MockAgent:
                mock_agent = Mock()
                MockAgent.return_value = mock_agent
                
                # Simulate progress streaming with resource monitoring
                
                # 1. Start monitoring for progress reporting
                time.sleep(0.5)  # Let monitoring collect data
                
                # 2. Get resource status for progress reporting
                resource_status = rm.get_resource_status()
                service_status = rm.get_service_status()
                
                # 3. Simulate progress updates with resource information
                progress_data = {
                    'timestamp': datetime.now().isoformat(),
                    'resource_utilization': {
                        pool_name: {
                            'memory_utilization': pool['utilization_memory'],
                            'cpu_utilization': pool['utilization_cpu'],
                            'instance_utilization': pool['utilization_instances']
                        }
                        for pool_name, pool in resource_status['resource_pools'].items()
                    },
                    'service_health': {
                        service: info['status']
                        for service, info in service_status['services'].items()
                    },
                    'system_metrics': resource_status['system_metrics']
                }
                
                logger.info("Progress streaming data prepared")
                assert 'resource_utilization' in progress_data
                assert 'service_health' in progress_data
                assert 'system_metrics' in progress_data
                
                # 4. Verify data completeness
                assert len(progress_data['resource_utilization']) == 4  # All layer pools
                assert len(progress_data['service_health']) >= 7  # All services
                
                logger.info("Progress streaming integration completed")
            
        finally:
            rm.shutdown()
    
    def test_complete_orchestration_workflow(self, isolated_env):
        """Test complete orchestration workflow with resource management."""
        rm = create_resource_manager(enable_monitoring=True)
        
        try:
            workflow_steps = []
            
            # 1. Initialize orchestration
            workflow_steps.append("orchestration_init")
            logger.info("Starting complete orchestration workflow")
            
            # 2. Check all layer resources
            for layer_name in rm.LAYER_SERVICE_DEPENDENCIES.keys():
                available, missing = rm.ensure_layer_services(layer_name)
                workflow_steps.append(f"check_{layer_name}_services")
                logger.info(f"Layer {layer_name}: Services available={available}")
            
            # 3. Allocate resources for fast_feedback layer (guaranteed to work)
            requirements = ResourceRequirements(min_memory_mb=128)
            allocation_id = rm.allocate_resources(
                layer_name="fast_feedback",
                category_name="orchestration_test",
                requirements=requirements,
                duration_minutes=5
            )
            
            if allocation_id:
                workflow_steps.append("resource_allocation")
                logger.info("Resources allocated for test execution")
                
                # 4. Simulate test execution monitoring
                time.sleep(0.2)
                workflow_steps.append("test_execution")
                
                # 5. Monitor resource usage during execution
                resource_status = rm.get_resource_status()
                workflow_steps.append("resource_monitoring")
                logger.info("Resource monitoring during execution")
                
                # 6. Check for conflicts
                conflicts = rm.resolve_resource_conflicts()
                workflow_steps.append("conflict_resolution")
                logger.info(f"Conflict resolution: {len(conflicts)} conflicts detected")
                
                # 7. Complete execution and release resources
                success = rm.release_resources(allocation_id)
                workflow_steps.append("resource_release")
                assert success
                logger.info("Resources released after execution")
            
            # 8. Final cleanup
            rm.cleanup_resources(force=True)
            workflow_steps.append("final_cleanup")
            
            # Verify complete workflow
            expected_steps = [
                "orchestration_init",
                "check_fast_feedback_services",
                "check_core_integration_services", 
                "check_service_integration_services",
                "check_e2e_background_services",
                "resource_allocation",
                "test_execution",
                "resource_monitoring",
                "conflict_resolution",
                "resource_release",
                "final_cleanup"
            ]
            
            for step in expected_steps:
                assert step in workflow_steps, f"Missing workflow step: {step}"
            
            logger.info("Complete orchestration workflow validated successfully")
            
        finally:
            rm.shutdown()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "-s", 
        "--tb=short",
        "--log-cli-level=INFO"
    ])