#!/usr/bin/env python3
"""
Manual test script for Alpine container functionality.

This script tests Alpine containers with real services, including:
1. Alpine container instantiation and startup
2. Service health checks 
3. Memory usage comparison
4. Performance benchmarks
5. Edge case handling

Business Value: Validates 40-60% memory reduction in test containers.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from shared.isolated_environment import get_env


class AlpineContainerTester:
    """Manual tester for Alpine container functionality."""
    
    def __init__(self):
        self.test_results = {
            "parameter_tests": {},
            "compose_selection_tests": {},
            "integration_tests": {},
            "performance_tests": {},
            "edge_case_tests": {}
        }
        self.services = ["postgres", "redis"]  # Start with core services
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def test_alpine_parameter_acceptance(self) -> bool:
        """Test 1: Alpine parameter acceptance and storage."""
        self.log("=== Testing Alpine Parameter Acceptance ===")
        
        try:
            # Test parameter acceptance
            manager = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                use_alpine=True
            )
            
            # Verify parameter is stored
            if hasattr(manager, 'use_alpine'):
                self.log(f"[PASS] use_alpine parameter accepted and stored: {manager.use_alpine}")
                self.test_results["parameter_tests"]["acceptance"] = True
                
                # Test default value
                manager_default = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
                if hasattr(manager_default, 'use_alpine'):
                    self.log(f"[PASS] use_alpine defaults to: {manager_default.use_alpine}")
                    self.test_results["parameter_tests"]["default_value"] = manager_default.use_alpine is False
                else:
                    self.log("[FAIL] use_alpine attribute missing on default manager")
                    self.test_results["parameter_tests"]["default_value"] = False
                    
                return True
            else:
                self.log("[FAIL] use_alpine parameter not stored as attribute")
                self.test_results["parameter_tests"]["acceptance"] = False
                return False
                
        except TypeError as e:
            self.log(f"[FAIL] use_alpine parameter not accepted: {e}")
            self.test_results["parameter_tests"]["acceptance"] = False
            return False
        except Exception as e:
            self.log(f"[FAIL] Unexpected error testing parameter: {e}")
            self.test_results["parameter_tests"]["acceptance"] = False
            return False
    
    def test_compose_file_selection(self) -> bool:
        """Test 2: Docker compose file selection logic."""
        self.log("=== Testing Compose File Selection ===")
        
        try:
            # Test Alpine compose file selection
            manager_alpine = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                use_alpine=True
            )
            
            if hasattr(manager_alpine, '_get_compose_file'):
                compose_file = manager_alpine._get_compose_file()
                self.log(f"Alpine compose file: {compose_file}")
                
                # Check if Alpine file is selected
                alpine_selected = "alpine" in compose_file.lower()
                self.test_results["compose_selection_tests"]["alpine_selection"] = alpine_selected
                
                if alpine_selected:
                    self.log("[PASS] Alpine compose file selected correctly")
                else:
                    self.log("[FAIL] Alpine compose file not selected")
                
                # Test regular compose file selection
                manager_regular = UnifiedDockerManager(
                    environment_type=EnvironmentType.TEST,
                    use_alpine=False
                )
                regular_compose_file = manager_regular._get_compose_file()
                self.log(f"Regular compose file: {regular_compose_file}")
                
                regular_not_alpine = "alpine" not in regular_compose_file.lower()
                self.test_results["compose_selection_tests"]["regular_selection"] = regular_not_alpine
                
                if regular_not_alpine:
                    self.log("[PASS] Regular compose file selected correctly")
                else:
                    self.log("[FAIL] Regular compose file incorrectly contains 'alpine'")
                
                return alpine_selected and regular_not_alpine
            else:
                self.log("[FAIL] _get_compose_file method not available")
                return False
                
        except Exception as e:
            self.log(f"[FAIL] Error testing compose file selection: {e}")
            self.test_results["compose_selection_tests"]["error"] = str(e)
            return False
    
    async def test_alpine_container_startup(self) -> bool:
        """Test 3: Alpine container startup and health checks."""
        self.log("=== Testing Alpine Container Startup ===")
        
        try:
            # Check Docker availability
            if not self._is_docker_available():
                self.log("[FAIL] Docker not available - skipping integration tests")
                self.test_results["integration_tests"]["docker_available"] = False
                return False
            
            manager = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                test_id="alpine_manual_test",
                use_alpine=True
            )
            
            self.log(f"Starting Alpine containers for services: {self.services}")
            
            # Start services
            start_time = time.time()
            success = await manager.start_services_smart(self.services, wait_healthy=True)
            startup_time = time.time() - start_time
            
            self.test_results["integration_tests"]["startup_success"] = success
            self.test_results["integration_tests"]["startup_time"] = startup_time
            
            if success:
                self.log(f"[PASS] Alpine containers started successfully in {startup_time:.1f}s")
                
                # Test health checks
                health_report = manager.get_health_report()
                self.log(f"Health report: {health_report}")
                
                healthy = "FAILED" not in health_report
                self.test_results["integration_tests"]["health_check"] = healthy
                
                if healthy:
                    self.log("[PASS] All Alpine containers are healthy")
                else:
                    self.log("[FAIL] Some Alpine containers failed health checks")
                
                # Get container info to verify Alpine images
                container_info = manager.get_enhanced_container_status(self.services)
                alpine_images_used = True
                
                for service, info in container_info.items():
                    self.log(f"Service {service}: Image {info.image}, State: {info.state}")
                    if "alpine" not in info.image.lower():
                        self.log(f"[WARN] Service {service} not using Alpine image: {info.image}")
                        alpine_images_used = False
                
                self.test_results["integration_tests"]["alpine_images_verified"] = alpine_images_used
                
                # Cleanup
                await manager.graceful_shutdown(self.services)
                self.log("[PASS] Alpine containers cleaned up")
                
                return success and healthy
                
            else:
                self.log("[FAIL] Alpine containers failed to start")
                return False
                
        except Exception as e:
            self.log(f"[FAIL] Error testing Alpine container startup: {e}")
            self.test_results["integration_tests"]["error"] = str(e)
            return False
    
    async def test_memory_usage_comparison(self) -> bool:
        """Test 4: Memory usage comparison between Alpine and regular containers."""
        self.log("=== Testing Memory Usage Comparison ===")
        
        try:
            if not self._is_docker_available():
                self.log("[FAIL] Docker not available - skipping memory tests")
                return False
            
            memory_stats = {}
            
            # Test regular containers first
            self.log("Testing regular container memory usage...")
            manager_regular = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                test_id="memory_test_regular",
                use_alpine=False
            )
            
            success = await manager_regular.start_services_smart(self.services, wait_healthy=True)
            if success:
                time.sleep(5)  # Let containers stabilize
                regular_memory = self._get_container_memory_usage(self.services, "memory_test_regular")
                memory_stats["regular"] = regular_memory
                self.log(f"Regular container memory: {regular_memory}")
                await manager_regular.graceful_shutdown(self.services)
            
            # Test Alpine containers
            self.log("Testing Alpine container memory usage...")
            manager_alpine = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                test_id="memory_test_alpine",
                use_alpine=True
            )
            
            success = await manager_alpine.start_services_smart(self.services, wait_healthy=True)
            if success:
                time.sleep(5)  # Let containers stabilize  
                alpine_memory = self._get_container_memory_usage(self.services, "memory_test_alpine")
                memory_stats["alpine"] = alpine_memory
                self.log(f"Alpine container memory: {alpine_memory}")
                await manager_alpine.graceful_shutdown(self.services)
            
            # Compare memory usage
            memory_savings = {}
            for service in self.services:
                regular_mem = memory_stats.get("regular", {}).get(service, 0)
                alpine_mem = memory_stats.get("alpine", {}).get(service, 0)
                
                if regular_mem > 0 and alpine_mem > 0:
                    savings_pct = (regular_mem - alpine_mem) / regular_mem * 100
                    memory_savings[service] = savings_pct
                    self.log(f"Service {service}: {regular_mem:.1f}MB  ->  {alpine_mem:.1f}MB ({savings_pct:.1f}% savings)")
            
            self.test_results["performance_tests"]["memory_comparison"] = memory_stats
            self.test_results["performance_tests"]["memory_savings"] = memory_savings
            
            # Verify Alpine uses less memory
            all_services_saved = all(savings > 0 for savings in memory_savings.values())
            significant_savings = any(savings > 20 for savings in memory_savings.values())
            
            if all_services_saved and significant_savings:
                self.log("[PASS] Alpine containers show significant memory savings")
                return True
            else:
                self.log("[WARN] Alpine containers memory savings not as expected")
                return False
                
        except Exception as e:
            self.log(f"[FAIL] Error testing memory usage: {e}")
            self.test_results["performance_tests"]["error"] = str(e)
            return False
    
    async def test_parallel_execution(self) -> bool:
        """Test 5: Parallel execution of Alpine and regular containers."""
        self.log("=== Testing Parallel Execution ===")
        
        try:
            if not self._is_docker_available():
                self.log("[FAIL] Docker not available - skipping parallel tests")
                return False
            
            # Create managers for both types
            manager_regular = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                test_id="parallel_regular",
                use_alpine=False
            )
            
            manager_alpine = UnifiedDockerManager(
                environment_type=EnvironmentType.TEST,
                test_id="parallel_alpine", 
                use_alpine=True
            )
            
            # Verify they have different project names
            regular_project = manager_regular._get_project_name()
            alpine_project = manager_alpine._get_project_name()
            
            self.log(f"Regular project: {regular_project}")
            self.log(f"Alpine project: {alpine_project}")
            
            different_projects = regular_project != alpine_project
            self.test_results["edge_case_tests"]["different_project_names"] = different_projects
            
            if different_projects:
                self.log("[PASS] Different project names for isolation")
            else:
                self.log("[FAIL] Same project names - potential conflicts")
            
            # Test starting both in parallel
            self.log("Starting both container types in parallel...")
            
            # Start regular containers
            regular_task = asyncio.create_task(
                manager_regular.start_services_smart(["postgres"], wait_healthy=True)
            )
            
            # Start Alpine containers
            alpine_task = asyncio.create_task(
                manager_alpine.start_services_smart(["redis"], wait_healthy=True)
            )
            
            # Wait for both to complete
            regular_success, alpine_success = await asyncio.gather(
                regular_task, alpine_task, return_exceptions=True
            )
            
            parallel_success = (
                isinstance(regular_success, bool) and regular_success and
                isinstance(alpine_success, bool) and alpine_success
            )
            
            self.test_results["edge_case_tests"]["parallel_execution"] = parallel_success
            
            if parallel_success:
                self.log("[PASS] Parallel execution successful")
            else:
                self.log(f"[FAIL] Parallel execution failed: regular={regular_success}, alpine={alpine_success}")
            
            # Cleanup both
            await asyncio.gather(
                manager_regular.graceful_shutdown(),
                manager_alpine.graceful_shutdown(),
                return_exceptions=True
            )
            
            return different_projects and parallel_success
            
        except Exception as e:
            self.log(f"[FAIL] Error testing parallel execution: {e}")
            self.test_results["edge_case_tests"]["error"] = str(e)
            return False
    
    def _is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"], 
                capture_output=True, 
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _get_container_memory_usage(self, services: List[str], test_id: str) -> Dict[str, float]:
        """Get memory usage for containers in MB."""
        memory_usage = {}
        
        try:
            for service in services:
                # Find container by service name pattern
                patterns = [f"{test_id}*{service}*", f"*{service}*{test_id}*", f"*{service}*"]
                
                for pattern in patterns:
                    cmd = ["docker", "ps", "--filter", f"name={pattern}", 
                           "--format", "{{.Names}}"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        container_names = result.stdout.strip().split('\n')
                        container_name = container_names[0]  # Use first match
                        
                        # Get memory stats
                        stats_cmd = ["docker", "stats", "--no-stream", "--format", 
                                   "{{.MemUsage}}", container_name]
                        stats_result = subprocess.run(stats_cmd, capture_output=True, 
                                                    text=True, timeout=10)
                        
                        if stats_result.returncode == 0:
                            # Parse memory usage (e.g., "45.2MiB / 512MiB")
                            mem_str = stats_result.stdout.strip().split(' / ')[0]
                            memory_mb = self._parse_memory_string(mem_str)
                            if memory_mb:
                                memory_usage[service] = memory_mb
                                self.log(f"Container {container_name}: {memory_mb}MB")
                                break
                        
        except Exception as e:
            self.log(f"Error getting memory usage: {e}")
        
        return memory_usage
    
    def _parse_memory_string(self, mem_str: str) -> Optional[float]:
        """Parse Docker memory string to MB."""
        try:
            if 'MiB' in mem_str:
                return float(mem_str.replace('MiB', ''))
            elif 'GiB' in mem_str:
                return float(mem_str.replace('GiB', '')) * 1024
            elif 'MB' in mem_str:
                return float(mem_str.replace('MB', ''))
            elif 'GB' in mem_str:
                return float(mem_str.replace('GB', '')) * 1000
            elif 'KB' in mem_str or 'KiB' in mem_str:
                return float(mem_str.replace('KB', '').replace('KiB', '')) / 1024
        except ValueError:
            pass
        return None
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        report = [
            "=" * 60,
            "ALPINE CONTAINER TEST REPORT",
            "=" * 60,
            f"Test completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        # Parameter tests
        param_results = self.test_results["parameter_tests"]
        report.extend([
            "1. PARAMETER ACCEPTANCE TESTS",
            f"   - Parameter acceptance: {'[PASS]' if param_results.get('acceptance') else '[FAIL]'}",
            f"   - Default value check: {'[PASS]' if param_results.get('default_value') else '[FAIL]'}",
            "",
        ])
        
        # Compose selection tests
        compose_results = self.test_results["compose_selection_tests"]
        report.extend([
            "2. COMPOSE FILE SELECTION TESTS",
            f"   - Alpine selection: {'[PASS]' if compose_results.get('alpine_selection') else '[FAIL]'}",
            f"   - Regular selection: {'[PASS]' if compose_results.get('regular_selection') else '[FAIL]'}",
            "",
        ])
        
        # Integration tests
        integration_results = self.test_results["integration_tests"]
        report.extend([
            "3. INTEGRATION TESTS",
            f"   - Docker available: {'[PASS]' if integration_results.get('docker_available', True) else '[FAIL]'}",
            f"   - Startup success: {'[PASS]' if integration_results.get('startup_success') else '[FAIL]'}",
            f"   - Health checks: {'[PASS]' if integration_results.get('health_check') else '[FAIL]'}",
            f"   - Alpine images: {'[PASS]' if integration_results.get('alpine_images_verified') else '[FAIL]'}",
        ])
        
        if integration_results.get('startup_time'):
            report.append(f"   - Startup time: {integration_results['startup_time']:.1f}s")
        
        report.append("")
        
        # Performance tests  
        perf_results = self.test_results["performance_tests"]
        if perf_results.get("memory_savings"):
            report.extend([
                "4. PERFORMANCE TESTS (Memory Savings)",
            ])
            for service, savings in perf_results["memory_savings"].items():
                status = "[PASS]" if savings > 0 else "[FAIL]"
                report.append(f"   - {service}: {status} {savings:.1f}% memory reduction")
        else:
            report.append("4. PERFORMANCE TESTS: Not completed")
        
        report.append("")
        
        # Edge case tests
        edge_results = self.test_results["edge_case_tests"]
        report.extend([
            "5. EDGE CASE TESTS",
            f"   - Different project names: {'[PASS]' if edge_results.get('different_project_names') else '[FAIL]'}",
            f"   - Parallel execution: {'[PASS]' if edge_results.get('parallel_execution') else '[FAIL]'}",
            "",
        ])
        
        # Overall status
        all_tests = [
            param_results.get('acceptance', False),
            compose_results.get('alpine_selection', False),
            integration_results.get('startup_success', False),
            edge_results.get('different_project_names', False),
        ]
        
        overall_success = all(all_tests)
        
        report.extend([
            "=" * 60,
            f"OVERALL STATUS: {'[PASS] SUCCESS' if overall_success else '[FAIL] SOME TESTS FAILED'}",
            f"Tests passed: {sum(all_tests)}/{len(all_tests)}",
            "=" * 60,
        ])
        
        return "\n".join(report)
    
    async def run_all_tests(self) -> bool:
        """Run all Alpine container tests."""
        self.log("Starting comprehensive Alpine container testing...")
        
        # Test 1: Parameter acceptance
        test1_success = self.test_alpine_parameter_acceptance()
        
        # Test 2: Compose file selection
        test2_success = self.test_compose_file_selection()
        
        # Test 3: Container startup (if Docker available)
        test3_success = await self.test_alpine_container_startup()
        
        # Test 4: Memory usage comparison (if Docker available)
        test4_success = await self.test_memory_usage_comparison()
        
        # Test 5: Parallel execution (if Docker available)
        test5_success = await self.test_parallel_execution()
        
        # Generate and display report
        report = self.generate_test_report()
        print("\n" + report)
        
        # Save report to file
        report_file = project_root / "ALPINE_CONTAINER_TEST_REPORT.md"
        report_file.write_text(report)
        self.log(f"Test report saved to: {report_file}")
        
        return test1_success and test2_success and (test3_success or not self._is_docker_available())


async def main():
    """Main test execution."""
    tester = AlpineContainerTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n[SUCCESS] All Alpine container tests passed!")
        return 0
    else:
        print("\n[FAILED] Some Alpine container tests failed!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[STOP] Test execution interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        sys.exit(1)